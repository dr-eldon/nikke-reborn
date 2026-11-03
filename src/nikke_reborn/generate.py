"""The generate orchestration: one `generate` run of the card pipeline.

Parses the command line, sizes the worker pool, and drives the three
render passes the pipeline is made of — the full-art cards and the
pack/box materials and items (:func:`_generate_variants`), the profile
presentations (:func:`_generate_profiles`) and the standard presentations
(:func:`_generate_standards`) — then writes each expansion's metadata
bundle. The per-presentation work itself lives in
:mod:`nikke_reborn.render`; this module only schedules it across the pool
of worker processes.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from pathlib import Path

from PIL import Image

from nikke_reborn import box, card, expansion, metadata, pack
from nikke_reborn.box import _process_box_item, _process_box_material
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
    REPO_ROOT,
    VIEWER,
)
from nikke_reborn.error import GenerationError
from nikke_reborn.file import (
    _material_output_up_to_date,
    _require_executable,
    _viewer_output_up_to_date,
)
from nikke_reborn.pack import _process_pack_item, _process_pack_material
from nikke_reborn.preset import Preset
from nikke_reborn.render import (
    _process_full_art,
    _process_profile_card,
    _process_standard_card,
)
from nikke_reborn.video import ENCODER


def run(argv: list[str] | None = None) -> None:
    """Render and composite the selected (or every) expansion's cards.

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
        expansions = card.select_expansions(args.paths)
        # The run's work: the selected expansions' cards' presentations
        # (the expansions' rarities subsets, the goddess presentation
        # dropped for the characters without the sc variant), filtered to
        # the characters the caller named. Every selected character is
        # resolved against the viewer (its variants, its reel's
        # animation) before anything is rendered, so a character that
        # cannot render a presentation fails before the run starts.
        presentations = card.build_selection(expansions, args.ids)
        if no_profile:
            print("Skipping the profile pass (--no-profile).")
        else:
            _generate_profiles(
                [p for p in presentations if p.tier == "profile"],
                args.jobs,
                preset,
                force,
                no_video,
            )
        if no_standard:
            print("Skipping the standard pass (--no-standard).")
        else:
            _generate_standards(
                [p for p in presentations if p.tier == "standard"],
                args.jobs,
                preset,
                force,
                no_video,
            )
        if no_full_art:
            print(
                "Skipping the full-art pass (--no-full-art): no full-art "
                "cards, no pack images."
            )
        else:
            _generate_variants(
                expansions,
                [p for p in presentations if p.tier == "full"],
                args.jobs,
                preset,
                force,
                no_video,
                selected=bool(args.paths),
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
        metavar="EXPANSION",
        help=(
            "expansion(s) to generate — an expansion's name or path "
            "(cards/<set>.toml, <set>.toml or <set>), relative to the "
            "repo root or to cards/; default: every expansion under cards/"
        ),
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        metavar="ID",
        help=(
            "only the characters with these viewer ids (one per "
            "expansion's roster; the expansions' packs and boxes still "
            "render)"
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
            "re-render every selected presentation and pack image"
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
        help="skip the profile pass: render no profile presentations",
    )
    parser.add_argument(
        "--no-standard",
        action="store_true",
        help="skip the standard pass: render no standard presentations",
    )
    parser.add_argument(
        "--no-full-art",
        action="store_true",
        help=("skip the full-art pass: render no full-art cards and no pack images"),
    )
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    if args.ids and not args.paths:
        parser.error("--ids selects characters within the expansions: name at least one expansion")
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


_Presentation = expansion.Presentation
_Result = tuple[Path, bool, dict[str, float | None] | None]


def _generate_profiles(
    presentations: list[_Presentation],
    jobs: int,
    preset: Preset,
    force: bool = False,
    no_video: bool = False,
) -> None:
    """Render the profile presentations (the ``Classic``, ``Idle``,
    ``Cover`` and ``Aim`` presentations, on the profile's mask) in a pool
    of worker processes. No pack artwork or metadata is produced.

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
    if not presentations:
        print("No profile presentations selected; skipping the profile pass.")
        return
    start = time.monotonic()
    total = len(presentations)
    # The per-presentation split of the cores between the stages that run
    # in parallel (see _stage_threads).
    ffmpeg_threads, composite_workers = _stage_threads(jobs, total, no_video)
    notes_text = _run_notes(preset, no_video)
    print(
        f"Rendering {total} profile card(s) (the profile's presentations) "
        f"with {jobs} worker(s){notes_text} ..."
    )
    for p in presentations:
        print(f"  - {p.expansion.name} {p.label}")

    failures: list[tuple[str, Exception]] = []
    done = 0
    skipped = 0
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        # Report one finished future. Failures are collected here and reported
        # (the run exits non-zero) once everything has had its turn, so one
        # bad presentation never aborts the rest.
        def report(future: Future[_Result], label: str) -> None:
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
            except Exception as exc:  # noqa: BLE001 — one bad card must
                # not abort the run: collect it and report it at the end
                failures.append((label, exc))
                print(
                    f"[{done}/{total}] {label} FAILED: {exc}",
                    file=sys.stderr,
                    flush=True,
                )

        card_futures: dict[Future[_Result], str] = {
            pool.submit(
                _process_profile_card,
                p,
                ffmpeg_threads,
                composite_workers,
                preset,
                force,
                no_video,
            ): f"{p.expansion.name} {p.label}"
            for p in presentations
        }
        for future in as_completed(card_futures):
            report(future, card_futures[future])

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
        f"Done. {total} profile card(s) in {time.monotonic() - start:.1f}s, "
        f"{word} written to {preset.base.relative_to(REPO_ROOT)}/{skipped_text}"
    )


def _generate_standards(
    presentations: list[_Presentation],
    jobs: int,
    preset: Preset,
    force: bool = False,
    no_video: bool = False,
) -> None:
    """Render the standard presentations (the ``Classic``, ``Special`` and
    ``Exotic`` presentations, on the standard's mask) in a pool of worker
    processes. No pack artwork or metadata is produced.

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
    if not presentations:
        print("No standard presentations selected; skipping the standard pass.")
        return
    start = time.monotonic()
    total = len(presentations)
    # The per-presentation split of the cores between the stages that run
    # in parallel (see _stage_threads).
    ffmpeg_threads, composite_workers = _stage_threads(jobs, total, no_video)
    notes_text = _run_notes(preset, no_video)
    print(
        f"Rendering {total} standard card(s) (the standard's presentations) "
        f"with {jobs} worker(s){notes_text} ..."
    )
    for p in presentations:
        print(f"  - {p.expansion.name} {p.label}")

    failures: list[tuple[str, Exception]] = []
    done = 0
    skipped = 0
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        # Report one finished future. Failures are collected here and reported
        # (the run exits non-zero) once everything has had its turn, so one
        # bad presentation never aborts the rest.
        def report(future: Future[_Result], label: str) -> None:
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
            except Exception as exc:  # noqa: BLE001 — one bad card must
                # not abort the run: collect it and report it at the end
                failures.append((label, exc))
                print(
                    f"[{done}/{total}] {label} FAILED: {exc}",
                    file=sys.stderr,
                    flush=True,
                )

        card_futures: dict[Future[_Result], str] = {
            pool.submit(
                _process_standard_card,
                p,
                ffmpeg_threads,
                composite_workers,
                preset,
                force,
                no_video,
            ): f"{p.expansion.name} {p.label}"
            for p in presentations
        }
        for future in as_completed(card_futures):
            report(future, card_futures[future])

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
        f"Done. {total} standard card(s) in {time.monotonic() - start:.1f}s, "
        f"{word} written to {preset.base.relative_to(REPO_ROOT)}/{skipped_text}"
    )


def _generate_variants(
    expansions: list[expansion.Expansion],
    presentations: list[_Presentation],
    jobs: int,
    preset: Preset,
    force: bool = False,
    no_video: bool = False,
    selected: bool = False,
) -> None:
    """Process the full-art presentations (the ``Classic``, ``Special``,
    ``Exotic`` and ``Goddess`` presentations, no mask) in a pool of worker
    processes, and the selected expansions' pack and box materials and
    items (the expansion in scope renders its pack and box).

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
    start = time.monotonic()
    # Compose each pack's fronts in the main process: its featured NIKKES
    # are GPU-rendered here, so a front is produced once per material that
    # needs it (the pack's front for the pack's material, the box's front —
    # a different size — for the box's material). They are transient —
    # composed on the fly from the expansion's TOML and never written to
    # disk. The fronts' inputs are hashed up front (without rendering
    # them), so the renders are skipped entirely when the materials and
    # the items — the pack's and the box's — are all already up to date.

    material_needs: set[str] = set()
    item_needs: set[str] = set()
    box_needs: set[str] = set()
    box_item_needs: set[str] = set()
    fronts: dict[str, Image.Image] = {}
    front_sources: dict[str, str] = {}
    backs: dict[str, Image.Image] = {}
    back_sources: dict[str, str] = {}
    box_fronts: dict[str, Image.Image] = {}
    box_front_sources: dict[str, str] = {}
    box_sides: dict[str, Image.Image] = {}
    box_tops: dict[str, Image.Image] = {}
    for exp in expansions:
        front_source = pack.front_source_hash(exp)
        back_source = pack.back_source_hash(exp)
        box_front_source = box.front_source_hash(exp)
        # The run's set folder (the "<set> (Ultra)" twin for the ultra
        # preset).
        set_path = preset.set_path(exp.name)
        material_ok = _material_output_up_to_date(
            PACK_TEMPLATE,
            PACK_MATERIAL_NAME,
            exp.name,
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
            exp.name,
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
            continue  # nothing changed for this expansion; skip the fronts' renders
        if not material_ok:
            material_needs.add(exp.name)
        if not item_ok:
            item_needs.add(exp.name)
        if not box_ok:
            box_needs.add(exp.name)
        if not box_item_ok:
            box_item_needs.add(exp.name)
        # The materials need the composed fronts (the item is rendered by
        # unity-viewer from the material's output file): the pack's front
        # and back, and the box's front — its own size, the box template's
        # blue rectangle, so its own composition.
        if not material_ok:
            fronts[exp.name] = pack.build_front(exp, pack.front_size())
            front_sources[exp.name] = front_source
            backs[exp.name] = pack.build_back(exp, pack.back_size())
            back_sources[exp.name] = back_source
        if not box_ok:
            box_fronts[exp.name] = box.build_front(exp, box.front_size())
            box_sides[exp.name] = box.build_side(exp, box.side_size())
            box_tops[exp.name] = box.build_top(exp, box.top_size())
            box_front_sources[exp.name] = box_front_source
    total = (
        len(presentations)
        + len(material_needs)
        + len(item_needs)
        + len(box_needs)
        + len(box_item_needs)
    )
    # The per-presentation split of the cores between the stages that run
    # in parallel (see _stage_threads).
    ffmpeg_threads, composite_workers = _stage_threads(jobs, total, no_video)
    notes_text = _run_notes(preset, no_video)
    what = f"{len(presentations)} full-art card(s)" + (
        f" and {len(material_needs) + len(item_needs) + len(box_needs) + len(box_item_needs)} pack image(s)"
        if material_needs or item_needs or box_needs or box_item_needs
        else ""
    )
    if selected:
        print(
            f"Rendering {total} selected card(s) with {jobs} worker(s){notes_text} ..."
        )
        for p in presentations:
            print(f"  - {p.expansion.name} {p.label}")
    else:
        print(
            f"Rendering {what} from {CARDS_DIR.relative_to(REPO_ROOT)}/ "
            f"with {jobs} worker(s){notes_text} ..."
        )

    failures: list[tuple[str, Exception]] = []
    done = 0
    skipped = 0
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        # Report one finished future. Failures are collected here and
        # reported (the run exits non-zero) once everything has had its
        # turn, so one bad card never aborts the rest.
        # The cards' futures carry a timings dict (the third element); the
        # material/item/box futures carry only (out_path, skipped).
        def report(future: Future[_Result] | Future[tuple[Path, bool]], label: str) -> None:
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
            except Exception as exc:  # noqa: BLE001 — one bad card must
                # not abort the run: collect it and report it at the end
                failures.append((label, exc))
                print(
                    f"[{done}/{total}] {label} FAILED: {exc}",
                    file=sys.stderr,
                    flush=True,
                )

        def material_label(expansion_name: str) -> str:
            return f"{expansion_name} {PACK_MATERIAL_NAME}"

        def item_label(expansion_name: str) -> str:
            return f"{expansion_name} {PACK_ITEM_NAME}"

        def box_label(expansion_name: str) -> str:
            return f"{expansion_name} {BOX_MATERIAL_NAME}"

        def box_item_label(expansion_name: str) -> str:
            return f"{expansion_name} {BOX_ITEM_NAME}"

        card_futures: dict[Future[_Result], str] = {
            pool.submit(
                _process_full_art,
                p,
                ffmpeg_threads,
                composite_workers,
                preset,
                force,
                no_video,
            ): f"{p.expansion.name} {p.label}"
            for p in presentations
        }
        # The item is rendered from the material's output file, so each
        # expansion's item starts only after its material has finished.
        # Expansions whose material is already up to date need no wait:
        # their item renders from the material that is already on disk.
        exp_by_name = {e.name: e for e in expansions}
        item_futures: dict[Future[tuple[Path, bool]], str] = {
            pool.submit(
                _process_pack_item, exp_by_name[name], force, preset
            ): item_label(name)
            for name in sorted(item_needs - material_needs)
        }
        # The box's item is rendered from the box material's output file,
        # so each box's item starts only after its material has finished.
        box_item_futures: dict[Future[tuple[Path, bool]], str] = {
            pool.submit(
                _process_box_item, exp_by_name[name], force, preset
            ): box_item_label(name)
            for name in sorted(box_item_needs - box_needs)
        }
        material_futures: dict[Future[tuple[Path, bool]], str] = {
            pool.submit(
                _process_pack_material,
                exp_by_name[name],
                fronts[name],
                front_sources[name],
                backs[name],
                back_sources[name],
                force,
                preset,
            ): name
            for name in material_needs
        }
        # The box's material is independent of the pack's: it starts at
        # once, from its own composed front.
        box_futures: dict[Future[tuple[Path, bool]], str] = {
            pool.submit(
                _process_box_material,
                exp_by_name[name],
                box_fronts[name],
                box_front_sources[name],
                box_sides[name],
                box_tops[name],
                force,
                preset,
            ): name
            for name in sorted(box_needs)
        }
        for future in as_completed(material_futures):
            name = material_futures[future]
            report(future, material_label(name))
            if future.exception() is not None:
                continue  # no material -> no item for this expansion
            if name in item_needs:
                item_futures[
                    pool.submit(
                        _process_pack_item, exp_by_name[name], force, preset
                    )
                ] = item_label(name)
        for future in as_completed(box_futures):
            name = box_futures[future]
            report(future, box_label(name))
            if future.exception() is not None:
                continue  # no box material -> no box item for this expansion
            if name in box_item_needs:
                box_item_futures[
                    pool.submit(
                        _process_box_item, exp_by_name[name], force, preset
                    )
                ] = box_item_label(name)
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
