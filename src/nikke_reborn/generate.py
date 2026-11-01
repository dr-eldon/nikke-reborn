"""The generate orchestration: one `generate` run of the card pipeline.

Parses the command line, sizes the worker pool, and drives the three
render passes the pipeline is made of — the full-art cards and the
pack/box materials and items (:func:`_generate_variants`), the Profile
cards (:func:`_generate_profiles`) and the Standard cards
(:func:`_generate_standards`) — then writes each set's metadata bundle.
The per-card work itself lives in :mod:`nikke_reborn.render`; this module
only schedules it across the pool of worker processes.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

from nikke_reborn import box, expansion, metadata, pack
from nikke_reborn.box import _process_box_item, _process_box_material
from nikke_reborn.card import (
    _find_card_configs,
    _profile_stem,
    _selected_configs,
    _standard_stem,
)
from nikke_reborn.config import (
    BOX_CONFIG,
    BOX_ITEM_NAME,
    BOX_MATERIAL_NAME,
    BOX_MESH,
    BOX_TEMPLATE,
    CARDS_DIR,
    MAX_STAGE_THREADS,
    PACK_CONFIG,
    PACK_ITEM_NAME,
    PACK_MATERIAL_NAME,
    PACK_MESH,
    PACK_TEMPLATE,
    PROBER,
    PROFILE_RARITIES,
    PROFILE_STEMS,
    REPO_ROOT,
    STANDARD_STEMS,
    VIEWER,
)
from nikke_reborn.error import GenerationError
from nikke_reborn.expansion import _find_pack_dirs
from nikke_reborn.file import (
    _material_output_up_to_date,
    _require_executable,
    _viewer_output_up_to_date,
)
from nikke_reborn.pack import _process_pack_item, _process_pack_material
from nikke_reborn.preset import Preset
from nikke_reborn.render import (
    _process_card,
    _process_profile_card,
    _process_standard_card,
)
from nikke_reborn.video import ENCODER


def run(argv: list[str] | None = None) -> None:
    """Render and composite the selected (or all) card definitions.

    *argv* overrides the command line (the process's by default) — the
    test command drives a forced, single-worker run through this entry
    point.
    """
    args = _parse_args(argv)
    draft = args.draft
    ultra = args.ultra
    force = args.force
    no_video = args.no_video
    no_profile = args.no_profile
    no_standard = args.no_standard
    no_full_art = args.no_full_art
    # One run, one mode (draft and ultra are mutually exclusive): the
    # preset carries the run's output scale, its output root (draft/
    # for a draft, output/ otherwise) and its encoding settings.
    preset = (
        Preset.DRAFT
        if draft
        else Preset.ULTRA if ultra else Preset.DEFAULT
    )
    try:
        selection = _selected_configs(args.paths)
        if no_profile:
            print("Skipping the profile pass (--no-profile).")
        else:
            _generate_profiles(
                selection, args.jobs, preset, force, no_video
            )
        if no_standard:
            print("Skipping the standard pass (--no-standard).")
        else:
            _generate_standards(
                selection, args.jobs, preset, force, no_video
            )
        if no_full_art:
            print(
                "Skipping the full-art pass (--no-full-art): no full-art "
                "cards, no pack images."
            )
        else:
            _generate_variants(
                selection, args.jobs, preset, force, no_video
            )
        metadata.write(preset)
    except GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


def _default_jobs() -> int:
    """A sensible default pool size: up to 4 cards at once, 1 per 4 cores."""
    return min(4, max(1, (os.cpu_count() or 4) // 4))


def _stage_threads(jobs: int, total: int, no_video: bool) -> tuple[int, int]:
    """``(ffmpeg_threads, composite_workers)`` for a run of *jobs* workers
    over *total* outputs: the split of the cores available to each card
    between the stages that run in parallel — the frame compositing and
    the ffmpeg encode: half each (at least 2 each, capped at
    :data:`MAX_STAGE_THREADS`) — or all of it to the compositing when
    there is no encode (*no_video*): the returned encode count is then a
    placeholder the encode never sees."""
    per_card = (os.cpu_count() or 1) // max(1, min(jobs, total))
    if no_video:
        return 1, max(2, min(MAX_STAGE_THREADS, per_card))
    ffmpeg_threads = max(2, min(MAX_STAGE_THREADS, per_card // 2))
    composite_workers = max(2, min(MAX_STAGE_THREADS, per_card - ffmpeg_threads))
    return ffmpeg_threads, composite_workers


def _run_notes(preset: Preset, no_video: bool) -> str:
    """The run-mode notes for the ``Rendering ...`` line — the draft's
    x264 preset and the skipped MP4 (``--no-video``) — as ``', x264
    preset ..., (draft)'``; ultra runs carry an ``(ultra)`` suffix."""
    notes = []
    if preset is Preset.DRAFT:
        notes.append(f"x264 preset '{preset.x264_preset}'")
    if no_video:
        notes.append("no MP4")
    suffix = (
        " (draft)"
        if preset is Preset.DRAFT
        else " (ultra)" if preset is Preset.ULTRA else ""
    )
    if not notes:
        return f",{suffix}" if suffix else ""
    return f", {', '.join(notes)}{suffix}"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render and composite Nikke trading cards from cards/"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        metavar="CARD_PATH",
        help=(
            "card path(s) to generate — a set, a card, or a definition "
            "file, relative to the repo root or to cards/; default: all "
            "under cards/"
        ),
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=_default_jobs(),
        help="number of cards to process in parallel (default: %(default)s)",
    )
    # --draft and --ultra pick the run mode (its output scale, its
    # output root and its encoding settings): one run, one mode.
    run_mode = parser.add_mutually_exclusive_group()
    run_mode.add_argument(
        "--draft",
        action="store_true",
        help=(
            "draft mode for quick iteration: ultrafast x264 preset, "
            "half-resolution MP4s, results written to draft/ instead of output/"
        ),
    )
    run_mode.add_argument(
        "--ultra",
        action="store_true",
        help=(
            "ultra mode: twice the default resolution (the native "
            "resolution), results written to the '<set> (Ultra)' set "
            "folders inside output/ instead of '<set>'"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "force regeneration: skip the up-to-date (hash) check and "
            "re-render every selected card, profile card, standard card "
            "and pack image"
        ),
    )
    parser.add_argument(
        "--no-video",
        action="store_true",
        help=(
            "skip the MP4 generation: animated cards are written out as "
            "their first frame (PNG) alone, and the run never needs "
            "ffmpeg (quick iteration)"
        ),
    )
    parser.add_argument(
        "--no-profile",
        action="store_true",
        help="skip the profile pass: render no <variant>Profile cards",
    )
    parser.add_argument(
        "--no-standard",
        action="store_true",
        help="skip the standard pass: render no <variant>Standard cards",
    )
    parser.add_argument(
        "--no-full-art",
        action="store_true",
        help=("skip the full-art pass: render no full-art cards and no pack images"),
    )
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    return args


def _timings_suffix(timings: dict[str, float | None] | None) -> str:
    """The per-stage timings as a ``(render 1.20s, composite 0.30s,
    encode 0.85s, total 2.10s)``-style suffix; empty for results that
    carry none."""
    if not timings:
        return ""
    parts = [
        f"{stage} {value:.2f}s" for stage, value in timings.items() if value is not None
    ]
    return f" ({', '.join(parts)})" if parts else ""


def _generate_profiles(
    paths: list[Path] | None,
    jobs: int,
    preset: Preset,
    force: bool = False,
    no_video: bool = False,
) -> None:
    """Render the profile cards — one for each of the ``Classic``,
    ``Idle``, ``Cover`` and ``Aim`` presentations (all written out as
    ``<variant>Profile``) — in a pool of worker processes. The ``Rare``,
    ``Special`` and ``Exotic`` presentations render a standard card instead
    (see :func:`_generate_standards`), and the ``Goddess`` and
    ``Classified`` presentations render no derived card.

    *paths* is passed to :func:`_find_card_configs` (a ``None`` selects every
    card definition); from the result every definition with a
    :data:`PROFILE_STEMS` stem is kept (see
    :func:`_process_profile_card`). No pack artwork or metadata is produced.

    With *no_video* (``--no-video``) the animated profile cards skip their
    MP4 and write out their first frame (PNG) alone — and the run needs
    only the viewer, no ffmpeg.
    """
    _require_executable(VIEWER)
    if not no_video:
        # The encode (and the mp4's stored-hash probe) are the run's only
        # ffmpeg users; a --no-video run needs the viewer alone.
        _require_executable(ENCODER)
        _require_executable(PROBER)
    configs = _find_card_configs(paths)
    profile_configs = [
        path
        for path in configs
        if path.stem in PROFILE_RARITIES or path.stem in PROFILE_STEMS
    ]
    if not configs:
        raise GenerationError("no profile card definitions to render")
    if not profile_configs:
        # The selection has no profile-eligible definition (e.g. it only
        # selects a Goddess or a Rare presentation): the standard and the
        # full-art presentations still render.
        print("No profile card definitions selected; skipping the profile pass.")
        return
    start = time.monotonic()
    total = len(profile_configs)
    # The per-card split of the cores between the stages that run in
    # parallel (see _stage_threads).
    ffmpeg_threads, composite_workers = _stage_threads(jobs, total, no_video)
    notes_text = _run_notes(preset, no_video)
    print(
        f"Rendering {total} profile card(s) (written out as "
        f"<variant>Profile) with {jobs} worker(s){notes_text} ..."
    )
    for path in profile_configs:
        print(f"  - {path.relative_to(REPO_ROOT)}")

    failures: list[tuple[Path, Exception]] = []
    done = 0
    skipped = 0
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        # Report one finished future. Failures are collected here and reported
        # (the run exits non-zero) once everything has had its turn, so one
        # bad card never aborts the rest.
        def report(
            future: Future[tuple[Path, bool, dict[str, float | None] | None]],
            label: Path,
        ) -> None:
            nonlocal done, skipped
            done += 1
            # Every profile output's stem differs from its definition's
            # (the Profile suffix); tag it.
            tag = f" ({_profile_stem(label)})"
            try:
                out_path, was_skipped, *rest = future.result()
                timings = rest[0] if rest else None
                if was_skipped:
                    skipped += 1
                    print(
                        f"[{done}/{total}] {label}{tag} unchanged, "
                        f"kept {out_path.relative_to(REPO_ROOT)}",
                        flush=True,
                    )
                else:
                    print(
                        f"[{done}/{total}] {label}{tag} -> "
                        f"{out_path.relative_to(REPO_ROOT)}"
                        f"{_timings_suffix(timings)}",
                        flush=True,
                    )
            except Exception as exc:
                failures.append((label, exc))
                print(
                    f"[{done}/{total}] {label}{tag} FAILED: {exc}",
                    file=sys.stderr,
                    flush=True,
                )

        card_futures: dict[
            Future[tuple[Path, bool, dict[str, float | None] | None]], Path
        ] = {
            pool.submit(
                _process_profile_card,
                path,
                ffmpeg_threads,
                composite_workers,
                preset,
                force,
                no_video,
            ): path
            for path in profile_configs
        }
        for future in as_completed(card_futures):
            report(future, card_futures[future].relative_to(CARDS_DIR))

    if failures:
        for label, exc in failures:
            print(f"error: {label} ({_profile_stem(label)}): {exc}", file=sys.stderr)
        sys.exit(1)
    word = (
        "drafts"
        if preset is Preset.DRAFT
        else "final cards (ultra)" if preset is Preset.ULTRA else "final cards"
    )
    skipped_text = f", {skipped} unchanged" if skipped else ""
    print(
        f"Done. {total} profile card(s) in {time.monotonic() - start:.1f}s, "
        f"{word} written to {preset.base.relative_to(REPO_ROOT)}/{skipped_text}"
    )


def _generate_standards(
    paths: list[Path] | None,
    jobs: int,
    preset: Preset,
    force: bool = False,
    no_video: bool = False,
) -> None:
    """Render the standard cards — one for each of the ``Classic``,
    ``Rare``, ``Special`` and ``Exotic`` presentations (all written out as
    ``<variant>Standard``) — in a pool of worker processes.

    *paths* is passed to :func:`_find_card_configs` (a ``None`` selects every
    card definition); from the result every definition with a
    :data:`STANDARD_STEMS` stem is kept (see
    :func:`_process_standard_card`). No pack artwork or metadata is produced.

    With *no_video* (``--no-video``) the animated standard cards skip their
    MP4 and write out their first frame (PNG) alone — and the run needs
    only the viewer, no ffmpeg.
    """
    _require_executable(VIEWER)
    if not no_video:
        # The encode (and the mp4's stored-hash probe) are the run's only
        # ffmpeg users; a --no-video run needs the viewer alone.
        _require_executable(ENCODER)
        _require_executable(PROBER)
    configs = _find_card_configs(paths)
    standard_configs = [path for path in configs if path.stem in STANDARD_STEMS]
    if not configs:
        raise GenerationError("no standard card definitions to render")
    if not standard_configs:
        # The selection has no standard-eligible definition (e.g. it only
        # selects an Idle presentation): the profile and the full-art
        # presentations still render.
        print("No standard card definitions selected; skipping the standard pass.")
        return
    start = time.monotonic()
    total = len(standard_configs)
    # The per-card split of the cores between the stages that run in
    # parallel (see _stage_threads).
    ffmpeg_threads, composite_workers = _stage_threads(jobs, total, no_video)
    notes_text = _run_notes(preset, no_video)
    print(
        f"Rendering {total} standard card(s) (written out as "
        f"<variant>Standard) with {jobs} worker(s){notes_text} ..."
    )
    for path in standard_configs:
        print(f"  - {path.relative_to(REPO_ROOT)}")

    failures: list[tuple[Path, Exception]] = []
    done = 0
    skipped = 0
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        # Report one finished future. Failures are collected here and reported
        # (the run exits non-zero) once everything has had its turn, so one
        # bad card never aborts the rest.
        def report(
            future: Future[tuple[Path, bool, dict[str, float | None] | None]],
            label: Path,
        ) -> None:
            nonlocal done, skipped
            done += 1
            # Every standard output's stem differs from its definition's
            # (the Standard suffix); tag it.
            tag = f" ({_standard_stem(label)})"
            try:
                out_path, was_skipped, *rest = future.result()
                timings = rest[0] if rest else None
                if was_skipped:
                    skipped += 1
                    print(
                        f"[{done}/{total}] {label}{tag} unchanged, "
                        f"kept {out_path.relative_to(REPO_ROOT)}",
                        flush=True,
                    )
                else:
                    print(
                        f"[{done}/{total}] {label}{tag} -> "
                        f"{out_path.relative_to(REPO_ROOT)}"
                        f"{_timings_suffix(timings)}",
                        flush=True,
                    )
            except Exception as exc:
                failures.append((label, exc))
                print(
                    f"[{done}/{total}] {label}{tag} FAILED: {exc}",
                    file=sys.stderr,
                    flush=True,
                )

        card_futures: dict[
            Future[tuple[Path, bool, dict[str, float | None] | None]], Path
        ] = {
            pool.submit(
                _process_standard_card,
                path,
                ffmpeg_threads,
                composite_workers,
                preset,
                force,
                no_video,
            ): path
            for path in standard_configs
        }
        for future in as_completed(card_futures):
            report(future, card_futures[future].relative_to(CARDS_DIR))

    if failures:
        for label, exc in failures:
            print(f"error: {label} ({_standard_stem(label)}): {exc}", file=sys.stderr)
        sys.exit(1)
    word = (
        "drafts"
        if preset is Preset.DRAFT
        else "final cards (ultra)" if preset is Preset.ULTRA else "final cards"
    )
    skipped_text = f", {skipped} unchanged" if skipped else ""
    print(
        f"Done. {total} standard card(s) in {time.monotonic() - start:.1f}s, "
        f"{word} written to {preset.base.relative_to(REPO_ROOT)}/{skipped_text}"
    )


def _generate_variants(
    paths: list[Path] | None,
    jobs: int,
    preset: Preset,
    force: bool = False,
    no_video: bool = False,
) -> None:
    """Process the selected cards in a pool of worker processes.

    With *no_video* (``--no-video``) the animated cards skip their MP4 and
    write out their first frame (PNG) alone — and the run needs only the
    viewer, no ffmpeg.
    """

    _require_executable(VIEWER)
    if not no_video:
        # The encode (and the mp4's stored-hash probe) are the run's only
        # ffmpeg users; a --no-video run needs the viewer alone.
        _require_executable(ENCODER)
        _require_executable(PROBER)
    # Every definition renders its full-art card here (the profile and the
    # standard presentations render through :func:`_generate_profiles` and
    # :func:`_generate_standards` respectively); a PROFILE_RARITIES stem, if
    # any, would skip the full-art card and render only its profile card.
    card_configs = [
        path for path in _find_card_configs(paths) if path.stem not in PROFILE_RARITIES
    ]
    pack_dirs: list[Path] = _find_pack_dirs()
    start = time.monotonic()
    # Compose each pack's fronts in the main process: its featured NIKKES
    # are GPU-rendered here, so a front is produced once per material that
    # needs it (the pack's front for the pack's material, the box's front —
    # a different size — for the box's material). They are transient —
    # composed on the fly from the expansion's metadata and never written
    # to disk. The fronts' inputs are hashed up front (without rendering
    # them), so the renders are skipped entirely when the materials and
    # the items — the pack's and the box's — are all already up to date.

    material_needs: set[Path] = set()
    item_needs: set[Path] = set()
    box_needs: set[Path] = set()
    box_item_needs: set[Path] = set()
    fronts: dict[Path, Image.Image] = {}
    front_sources: dict[Path, str] = {}
    backs: dict[Path, Image.Image] = {}
    back_sources: dict[Path, str] = {}
    box_fronts: dict[Path, Image.Image] = {}
    box_front_sources: dict[Path, str] = {}
    box_sides: dict[Path, Image.Image] = {}
    box_tops: dict[Path, Image.Image] = {}
    for pack_dir in pack_dirs:
        front_source = pack.front_source_hash(pack_dir)
        back_source = pack.back_source_hash(pack_dir)
        box_front_source = box.front_source_hash(pack_dir)
        # The run's set folder (the "<set> (Ultra)" twin for the ultra
        # preset).
        set_path = preset.set_path(pack_dir.relative_to(CARDS_DIR).name)
        material_ok = _material_output_up_to_date(
            PACK_TEMPLATE,
            PACK_MATERIAL_NAME,
            pack_dir,
            front_source,
            back_source,
            force,
            preset,
        )
        item_ok = _viewer_output_up_to_date(
            PACK_MESH,
            set_path / PACK_MATERIAL_NAME,
            PACK_CONFIG,
            set_path / PACK_ITEM_NAME,
            force,
            preset,
        )
        box_ok = _material_output_up_to_date(
            BOX_TEMPLATE,
            BOX_MATERIAL_NAME,
            pack_dir,
            box_front_source,
            "",  # the box's material has no back
            force,
            preset,
        )
        box_item_ok = _viewer_output_up_to_date(
            BOX_MESH,
            set_path / BOX_MATERIAL_NAME,
            BOX_CONFIG,
            set_path / BOX_ITEM_NAME,
            force,
            preset,
        )
        if material_ok and item_ok and box_ok and box_item_ok:
            continue  # nothing changed for this pack; skip the fronts' renders
        if not material_ok:
            material_needs.add(pack_dir)
        if not item_ok:
            item_needs.add(pack_dir)
        if not box_ok:
            box_needs.add(pack_dir)
        if not box_item_ok:
            box_item_needs.add(pack_dir)
        # The materials need the composed fronts (the item is rendered by
        # unity-viewer from the material's output file): the pack's front
        # and back, and the box's front — its own size, the box template's
        # blue rectangle, so its own composition.
        if not material_ok or not box_ok:
            data = expansion.load_expansion(pack_dir)
            if not material_ok:
                fronts[pack_dir] = pack.build_front(pack_dir, data, pack.front_size())
                front_sources[pack_dir] = front_source
                backs[pack_dir] = pack.build_back(pack_dir, data, pack.back_size())
                back_sources[pack_dir] = back_source
            if not box_ok:
                box_fronts[pack_dir] = box.build_front(pack_dir, data, box.front_size())
                box_sides[pack_dir] = box.build_side(pack_dir, data, box.side_size())
                box_tops[pack_dir] = box.build_top(pack_dir, data, box.top_size())
                box_front_sources[pack_dir] = box_front_source
    total = (
        len(card_configs)
        + len(material_needs)
        + len(item_needs)
        + len(box_needs)
        + len(box_item_needs)
    )
    # The per-card split of the cores between the stages that run in
    # parallel (see _stage_threads).
    ffmpeg_threads, composite_workers = _stage_threads(jobs, total, no_video)
    notes_text = _run_notes(preset, no_video)
    what = f"{len(card_configs)} card(s)" + (
        f" and {len(material_needs) + len(item_needs) + len(box_needs) + len(box_item_needs)} pack image(s)"
        if material_needs or item_needs or box_needs or box_item_needs
        else ""
    )
    if paths:
        print(
            f"Rendering {total} selected card(s) with {jobs} worker(s){notes_text} ..."
        )
        for path in card_configs:
            print(f"  - {path.relative_to(REPO_ROOT)}")
    else:
        print(
            f"Rendering {what} from {CARDS_DIR.relative_to(REPO_ROOT)}/ "
            f"with {jobs} worker(s){notes_text} ..."
        )

    failures: list[tuple[Path, Exception]] = []
    done = 0
    skipped = 0
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        # Report one finished future. Failures are collected here and
        # reported (the run exits non-zero) once everything has had its
        # turn, so one bad card never aborts the rest.
        # The cards' futures carry a timings dict (the third element); the
        # material/item/box futures carry only (out_path, skipped).
        def report(
            future: (
                Future[tuple[Path, bool]]
                | Future[tuple[Path, bool, dict[str, float | None] | None]]
            ),
            label: Path,
        ) -> None:
            nonlocal done, skipped
            done += 1
            try:
                out_path, was_skipped, *rest = future.result()
                timings = rest[0] if rest else None
                if was_skipped:
                    skipped += 1
                    print(
                        f"[{done}/{total}] {label} unchanged, "
                        f"kept {out_path.relative_to(REPO_ROOT)}",
                        flush=True,
                    )
                else:
                    print(
                        f"[{done}/{total}] {label} -> "
                        f"{out_path.relative_to(REPO_ROOT)}"
                        f"{_timings_suffix(timings)}",
                        flush=True,
                    )
            except Exception as exc:
                failures.append((label, exc))
                print(
                    f"[{done}/{total}] {label} FAILED: {exc}",
                    file=sys.stderr,
                    flush=True,
                )

        def material_label(pack_dir: Path) -> Path:
            return pack_dir.relative_to(CARDS_DIR) / PACK_MATERIAL_NAME

        def item_label(pack_dir: Path) -> Path:
            return pack_dir.relative_to(CARDS_DIR) / PACK_ITEM_NAME

        def box_label(pack_dir: Path) -> Path:
            return pack_dir.relative_to(CARDS_DIR) / BOX_MATERIAL_NAME

        def box_item_label(pack_dir: Path) -> Path:
            return pack_dir.relative_to(CARDS_DIR) / BOX_ITEM_NAME

        card_futures: dict[
            Future[tuple[Path, bool, dict[str, float | None] | None]], Path
        ] = {
            pool.submit(
                _process_card,
                path,
                ffmpeg_threads,
                composite_workers,
                preset,
                force,
                no_video,
            ): path.relative_to(CARDS_DIR)
            for path in card_configs
        }
        # The item is rendered from the material's output file, so each
        # pack's item starts only after its material has finished. Packs
        # whose material is already up to date need no wait: their item
        # renders from the material that is already on disk.
        item_futures: dict[Future[tuple[Path, bool]], Path] = {
            pool.submit(
                _process_pack_item, pack_dir, force, preset
            ): item_label(pack_dir)
            for pack_dir in sorted(item_needs - material_needs)
        }
        # The box's item is rendered from the box material's output file,
        # so each box's item starts only after its material has finished.
        box_item_futures: dict[Future[tuple[Path, bool]], Path] = {
            pool.submit(
                _process_box_item, pack_dir, force, preset
            ): box_item_label(pack_dir)
            for pack_dir in sorted(box_item_needs - box_needs)
        }
        material_futures: dict[Future[tuple[Path, bool]], Path] = {
            pool.submit(
                _process_pack_material,
                pack_dir,
                fronts[pack_dir],
                front_sources[pack_dir],
                backs[pack_dir],
                back_sources[pack_dir],
                force,
                preset,
            ): pack_dir
            for pack_dir in material_needs
        }
        # The box's material is independent of the pack's: it starts at
        # once, from its own composed front.
        box_futures: dict[Future[tuple[Path, bool]], Path] = {
            pool.submit(
                _process_box_material,
                pack_dir,
                box_fronts[pack_dir],
                box_front_sources[pack_dir],
                box_sides[pack_dir],
                box_tops[pack_dir],
                force,
                preset,
            ): pack_dir
            for pack_dir in sorted(box_needs)
        }
        for future in as_completed(material_futures):
            pack_dir = material_futures[future]
            report(future, material_label(pack_dir))
            if future.exception() is not None:
                continue  # no material -> no item for this pack
            if pack_dir in item_needs:
                item_futures[
                    pool.submit(
                        _process_pack_item, pack_dir, force, preset
                    )
                ] = item_label(pack_dir)
        for future in as_completed(box_futures):
            pack_dir = box_futures[future]
            report(future, box_label(pack_dir))
            if future.exception() is not None:
                continue  # no box material -> no box item for this pack
            if pack_dir in box_item_needs:
                box_item_futures[
                    pool.submit(
                        _process_box_item, pack_dir, force, preset
                    )
                ] = box_item_label(pack_dir)
        for future in as_completed(card_futures):
            report(future, card_futures[future])
        for future in as_completed(item_futures):
            report(future, item_futures[future])
        for future in as_completed(box_item_futures):
            report(future, box_item_futures[future])
    if failures:
        for label, exc in failures:
            print(f"error: {label}: {exc}", file=sys.stderr)
        sys.exit(1)
    word = (
        "drafts"
        if preset is Preset.DRAFT
        else "final cards (ultra)" if preset is Preset.ULTRA else "final cards"
    )
    skipped_text = f", {skipped} unchanged" if skipped else ""
    print(
        f"Done. {what} in {time.monotonic() - start:.1f}s, "
        f"{word} written to {preset.base.relative_to(REPO_ROOT)}/{skipped_text}"
    )
