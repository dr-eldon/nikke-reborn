"""Render and composite Nikke trading cards.

Walks :mod:`cards` for card definitions (``*.json``), renders each one with
the ``nikke-viewer`` executable, composites every rendered frame on top of
the card's ``background``, stamps the matching logo from ``assets/images/``
at the bottom right and the copyright line at the bottom left, and overlays
the card name on top of the art, per frame: the title (uppercase, in a
dark rectangle at three-quarters of the height, with a small slanted bar
and three slanted squares of the same fill above it) and the subtitle
above the title (uppercase, in a background-tinted rectangle). The
``Goddess`` and ``Classified`` variants are generated without any card
name. Packs (``cards/`` subdirectories carrying an
``Expansion.json``) additionally get their two artwork images, built from
the templates in ``assets/images/``. The pack's front and back are composed
on the fly (by :mod:`nikke_reborn.pack`) from the expansion's metadata —
the front is its ``background`` with its featured NIKKES (``pack``) drawn
over it and its ``logo`` when the expansion names one; the back is the
same ``background`` resized and left-cropped — and neither is stored. The
material (``CardPack_Material.png``) has two pure-blue mask rectangles
holding the composed back (left) and front (right); the item
(``CardPack_Item.png``) is the pack's mesh
(``assets/meshes/CardPackStatic_Mesh.obj``) textured with the finished
material and rendered by the ``unity-viewer`` executable with the
model rotation and camera zoom/pan from
``assets/meshes/CardPackStatic_Mesh.json`` — so it is generated after the
material, which it reads from disk. The box (``CardBox_Material.png``)
holds the same composed front in the blue rectangle of its three mask
rectangles (blue front, red top, green side), the top (a center-cropped
background with the expansion's logo and the white NIKKE logo) in the red
one and the side (the background with the expansion's logo and the white
NIKKE logo) in the green one; the box's item (``CardBox_Item.png``) is the
box's mesh (``assets/meshes/CardBox_Mesh.obj``) textured with the finished
material and rendered by the ``unity-viewer`` executable with the model
rotation and camera zoom/pan from ``assets/meshes/CardBox_Mesh.json``, so it
is generated after the box's material, which it reads from disk. The
finished results are written under ``output/``, with
the SHA-256 of their inputs embedded as metadata (a PNG text chunk, an
MP4 tag); a result whose stored hash matches the current inputs is
skipped instead of re-rendered.

* single-frame cards -> ``output/<set>/<card>_<variant>.png``
* animated cards     -> ``output/<set>/<card>_<variant>.mp4`` alongside
                       its first frame, ``output/<set>/<card>_<variant>.png``
                       (with ``--no-video``: the first frame alone)

(the card's directory is folded into the filename, so a set's cards
sit flat in ``output/<set>/``)

``--draft`` runs the same pipeline for quick iteration: ultrafast x264
preset, half-resolution MP4s (downscaled inside ffmpeg), and results
written to ``draft/`` instead of ``output/`` so draft runs never clobber
the final cards.

``--no-video`` skips the MP4 generation altogether: an animated card is
written out as its first frame alone (the same PNG an animation keeps
alongside its MP4), the viewer stream is abandoned after that frame and
the viewer reaped, and the run never invokes ffmpeg or ffprobe — the
fastest pass through the pipeline, for iterating on the frames themselves.
The up-to-date check then covers the first frame alone; a run without the
flag generates the MP4 as usual whenever it is missing or stale.

``--no-profile``, ``--no-standard`` and ``--no-full-art`` disable the
three generation passes outright — the ``Profile`` presentation (the
``<variant>Profile`` cards), the ``Standard`` presentation (the
``<variant>Standard`` cards) and the full-art cards with the pack's
artwork (the pack's and the box's materials and items) — so a run renders
only the presentations it is not told to skip. The metadata bundle is
written either way, and a later run without the flag renders the skipped
outputs whenever they are missing or stale.

``--force`` skips the up-to-date (hash) check and re-renders every selected
card, profile card, standard card and pack image, even when the finished
result on disk is already current.

``nikke-viewer --stdout`` streams its frames as raw RGBA pixels (no
intermediate files), so each card is rendered straight into the pipeline:
the raw frames are piped out of the viewer's stdout, composited in memory,
and — for animations — fed to the ffmpeg encode through a pipe. Nothing
intermediate ever touches the disk; only the finished card is written
(atomically).

Cards are independent of each other, so they are processed by a pool of
worker processes (see ``--jobs``); within an animated card, the frames are
composited in parallel threads, and the cores are split between that stage
and the ffmpeg encode so the parallel work stays within the core count.

Beyond the full-art card, two derived presentations are rendered from a
definition: the ``Profile`` presentation (the ``Classic``, ``Idle``,
``Cover`` and ``Aim`` variants, written out with a ``Profile`` suffix; see
the profile presentation section below) and the ``Standard`` presentation
(the ``Classic``, ``Rare``, ``Special`` and ``Exotic`` variants, written out
with a ``Standard`` suffix; the standard card keeps the definition's
``background`` (faded a bit toward its dominant color), composites the
standard card mask over it, and frames the character's upper body with the
viewer's ``--half-body`` flag).

By default every ``*.json`` under ``cards/`` is generated; one or more card
paths (a set, a card, or a definition file, relative to the repo root or to
``cards/``) may be passed on the command line to generate only the selected
definitions — the full-art, the ``Profile`` and the ``Standard``
presentations alike.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from concurrent.futures import (
    Future,
    ProcessPoolExecutor,
    as_completed,
)
from pathlib import Path
from nikke_reborn import bundler, metadata
from nikke_reborn.config import (
    BOX_CONFIG,
    BOX_ITEM_NAME,
    BOX_MATERIAL_NAME,
    BOX_MESH,
    BOX_TEMPLATE,
    BUNDLES_DIR,
    CARDS_DIR,
    CARD_REFERENCE_WIDTH,  # noqa: F401 (re-export for spritesheet)
    DATABASE_DIR,
    DRAFT_DIR,
    DEFAULT_PRESET,
    DEFAULT_SCALE,
    DRAFT_PRESET,
    DRAFT_SCALE,
    FONT,
    IMAGES_DIR,
    MAX_STAGE_THREADS,
    OUTPUT_DIR,
    PACK_CONFIG,
    PACK_ITEM_NAME,
    PACK_MATERIAL_NAME,
    PACK_MESH,
    PACK_TEMPLATE,
    PROFILE_RARITIES,
    PROFILE_STEMS,
    PROBER,
    REPO_ROOT,
    SHOP_DIR,
    SOURCE_HASH_KEY,
    STANDARD_STEMS,
    UNITY_VIEWER,
    VIEWER,
)
from nikke_reborn.error import GenerationError
from nikke_reborn.file import (
    _material_output_up_to_date,
    _require_executable,
    _save_atomic,
    _viewer_output_up_to_date,
    copy,
)
from nikke_reborn.image import (
    LOGO_PADDING_FACTOR,
    PROFILE_MASK_PATH,
    STANDARD_MASK_PATH,
    _box_side_mask,
    _box_top_mask,
    _fade_to_dominant,
    _fit_background,
    _pack_mask,
    _pack_mask_rects,
    _profile_layers,
    _standard_layers,
)
from nikke_reborn.lettering import (
    COPYRIGHT_NOMINAL_SIZE,  # noqa: F401 (re-export for spritesheet)
    COPYRIGHT_SUPERSAMPLE,  # noqa: F401 (re-export for spritesheet)
    COPYRIGHT_TEXT,  # noqa: F401 (re-export for spritesheet)
    COPYRIGHT_WEIGHT,  # noqa: F401 (re-export for spritesheet)
    FONT_NAME,
    MANUFACTURER_LOGO_WIDTH,
    NAME_RECT_COLOR,
    _logo_copyright_overlay,
    _name_layers,
    _rect_tint,
    _set_weight,  # noqa: F401 (kept for spritesheet.py's nr._set_weight)
    _text_ink_offsets,  # noqa: F401 (kept for spritesheet.py's nr._text_ink_offsets)
    _tint_layer,
)
from nikke_reborn.video import (
    DEFAULT_FRAMERATE,
    ENCODER,
    PIPE_BUFSIZE,
    _PipeDrain,
    _encode_mp4,
    _read_exact,
    _reap_viewer,
    _stream_composited,
    _stream_dual_composited,
)
from nikke_reborn.card import (
    _find_card_configs,
    _load_card,
    _profile_stem,
    _selected_configs,
    _source_hash,
    _standard_stem,
)
from nikke_reborn.render import (
    _process_card,
    _process_profile_card,
    _process_standard_card,
)

from PIL import Image
MOD_NAME = "NIKKE REBORN"
def generate() -> None:
    """Render and composite the selected (or all) card definitions."""
    args = _parse_args()
    draft = args.draft
    force = args.force
    no_video = args.no_video
    no_profile = args.no_profile
    no_standard = args.no_standard
    no_full_art = args.no_full_art
    out_dir = DRAFT_DIR if draft else OUTPUT_DIR
    preset = DRAFT_PRESET if draft else DEFAULT_PRESET
    scale = DRAFT_SCALE if draft else DEFAULT_SCALE
    try:
        selection = _selected_configs(args.paths)
        if no_profile:
            print("Skipping the profile pass (--no-profile).")
        else:
            _generate_profiles(
                selection, args.jobs, preset, scale, out_dir, force, no_video
            )
        if no_standard:
            print("Skipping the standard pass (--no-standard).")
        else:
            _generate_standards(
                selection, args.jobs, preset, scale, out_dir, force, no_video
            )
        if no_full_art:
            print(
                "Skipping the full-art pass (--no-full-art): no full-art "
                "cards, no pack images."
            )
        else:
            _generate_variants(
                selection, args.jobs, preset, scale, out_dir, force, no_video
            )
        _write_metadata(out_dir)
    except GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


def _set_cards(set_dir: Path) -> list[dict]:
    """The card entries of *set_dir*'s metadata bundle: every variant
    definition under the set, expanded into the derived presentations the
    way the finished cards are written out (the ``Standard`` cards of
    :data:`STANDARD_STEMS`, the ``Profile`` cards of :data:`PROFILE_STEMS`
    and the full-art card of every variant outside :data:`PROFILE_RARITIES`),
    each carrying the character's rarity from ``database/characters.json``
    (a skin variant's suffixed id, c010_02, inherits the base character's
    rarity; an unknown id defaults to ``R`` with a warning). Shared by
    :func:`_write_metadata` (which writes the bundle to ``output/``) and
    :mod:`nikke_reborn.simulation` (which simulates pack openings against
    the current tuning)."""
    characters = json.load((DATABASE_DIR / "characters.json").open())
    characters = {character["id"]: character for character in characters}

    cards = []
    missing_ids: set[str] = set()

    for card in sorted(set_dir.iterdir()):
        if not card.is_dir():
            continue

        for variant in sorted(card.iterdir()):
            if not variant.name.endswith(".json"):
                continue

            config = json.load(variant.open())

            id = config["id"]
            title = config["title"]
            subtitle = config["subtitle"]

            name = f"{title}: {subtitle}" if subtitle else title

            # Skin variants carry a suffixed id (c010_02); strip the
            # suffix so they inherit the base character's rarity.
            character = characters.get(id) or characters.get(id.split("_", 1)[0])
            if character is None:
                missing_ids.add(id)
                rarity = "R"
            else:
                rarity = character["rarity"]

            if variant.stem in STANDARD_STEMS:
                standard_stem = _standard_stem(variant)

                new_card = metadata.card(
                    name,
                    standard_stem,
                    rarity,
                    f"{card.stem}_{standard_stem}",
                )
                cards.append(new_card)

            if variant.stem in PROFILE_STEMS:
                profile_stem = _profile_stem(variant)

                new_card = metadata.card(
                    name,
                    profile_stem,
                    rarity,
                    f"{card.stem}_{profile_stem}",
                )
                cards.append(new_card)

            if variant.stem not in PROFILE_RARITIES:
                new_card = metadata.card(
                    name,
                    variant.stem,
                    rarity,
                    f"{card.stem}_{variant.stem}",
                )
                cards.append(new_card)

    for missing in sorted(missing_ids):
        print(
            f"warning: no character {missing!r} in characters.json; "
            f"its cards default to rarity 'R'",
            file=sys.stderr,
        )

    return cards


def _write_metadata(out_dir: Path) -> None:
    """Write each set's metadata bundle (``<out>/<set>.json``) and copy the
    set's shared assets (foilmask, cardback, box mesh, shop images) to
    ``<out>/<set>/``."""
    for set_dir in CARDS_DIR.iterdir():
        if not set_dir.is_dir():
            continue

        if (set_dir / "Foilmask.png").is_file():
            copy(set_dir / "Foilmask.png", out_dir / set_dir.stem / "Foilmask.png")
        else:
            copy(IMAGES_DIR / "Foilmask.png", out_dir / set_dir.stem / "Foilmask.png")

        if (set_dir / "Cardback.png").is_file():
            copy(set_dir / "Cardback.png", out_dir / set_dir.stem / "Cardback.png")
        else:
            copy(IMAGES_DIR / "Cardback.png", out_dir / set_dir.stem / "Cardback.png")

        copy(BOX_MESH, out_dir / set_dir.stem / BOX_MESH.name)

        for file in SHOP_DIR.iterdir():
            if not file.is_file():
                continue

            copy(file, out_dir / set_dir.stem / file.name)

        cards = _set_cards(set_dir)

        expansion = metadata.expansion(set_dir.stem, cards)
        pack = metadata.pack(set_dir.stem)
        box = metadata.box(set_dir.stem)
        bundle = metadata.bundle(
            set_dir.stem, items=[pack, box], expansions=[expansion]
        )

        with (out_dir / f"{set_dir.stem}.json").open(
            "w", newline="\n", encoding="utf-8"
        ) as file:
            json.dump(bundle, file, indent=2)


def bundle() -> None:
    shutil.rmtree(BUNDLES_DIR, ignore_errors=True)
    BUNDLES_DIR.mkdir()

    for target in sorted(OUTPUT_DIR.iterdir()):
        if not target.is_dir():
            continue

        bundle = BUNDLES_DIR / f"{MOD_NAME} - {target.name}"
        bundle.mkdir(parents=True)

        plugins = bundle / "BepInEx" / "plugins"

        for file in ["Shop_Icon.png", "Shop_IBG.png", "Shop_OBG.png"]:
            copy(
                SHOP_DIR / file,
                plugins
                / "Phone - Overhaul"
                / "App Images"
                / f"{metadata.BUNDLE_NAME}"
                / file,
            )

        prefab = plugins / MOD_NAME / f"{target.name}_prefabloader"
        plugin = prefab / target.name
        animator = plugins / "EPLCardAnimator" / "animated"

        if (CARDS_DIR / target.name).is_dir():
            videos = [
                file
                for file in (OUTPUT_DIR / target.name).iterdir()
                if file.name.endswith(".mp4")
            ]

            videos_dir = animator / f"{metadata.BUNDLE_NAME}_{target.name}"

            if videos:
                videos_dir.mkdir(parents=True)

            for video in videos:
                copy(video, videos_dir / video.name)

        copy(target.with_suffix(".json"), plugin.with_suffix(".json"))
        bundler.build(
            assets_dir=target,
            name=f"{metadata.BUNDLE_NAME}_{plugin.name}",
            output=plugin,
            root=OUTPUT_DIR,
        )


def _solve_linear(rows: list[list[float]]) -> list[float]:
    """Solve a square linear system by Gaussian elimination with partial
    pivoting and back-substitution. *rows* is an augmented matrix
    ``n x (n + 1)``; returns the *n* solutions."""
    m = [row[:] for row in rows]
    n = len(m)
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[pivot] = m[pivot], m[col]
        for r in range(col + 1, n):
            factor = m[r][col] / m[col][col]
            for j in range(col, n + 1):
                m[r][j] -= factor * m[col][j]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (m[r][n] - sum(m[r][j] * x[j] for j in range(r + 1, n))) / m[r][r]
    return x


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


def _run_notes(preset: str, scale: float, no_video: bool) -> str:
    """The run-mode notes for the ``Rendering ...`` line — the draft's
    x264 preset and resolution (when not the defaults) and the skipped
    MP4 (``--no-video``) — as ``', x264 preset ..., (draft)'``: empty
    when the run is a plain full-quality pass."""
    notes = []
    if preset != DEFAULT_PRESET:
        notes.append(f"x264 preset '{preset}'")
    if scale != 1.0:
        notes.append(f"{scale:g}x resolution")
    if no_video:
        notes.append("no MP4")
    if not notes:
        return ""
    suffix = " (draft)" if preset != DEFAULT_PRESET else ""
    return f", {', '.join(notes)}{suffix}"


def _parse_args() -> argparse.Namespace:
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
    parser.add_argument(
        "--draft",
        action="store_true",
        help=(
            "draft mode for quick iteration: ultrafast x264 preset, "
            "half-resolution MP4s, results written to draft/ instead of output/"
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
    args = parser.parse_args()
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
    preset: str,
    scale: float,
    out_base: Path,
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
    notes_text = _run_notes(preset, scale, no_video)
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
                scale,
                out_base,
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
    word = "drafts" if out_base == DRAFT_DIR else "final cards"
    skipped_text = f", {skipped} unchanged" if skipped else ""
    print(
        f"Done. {total} profile card(s) in {time.monotonic() - start:.1f}s, "
        f"{word} written to {out_base.relative_to(REPO_ROOT)}/{skipped_text}"
    )


def _generate_standards(
    paths: list[Path] | None,
    jobs: int,
    preset: str,
    scale: float,
    out_base: Path,
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
    notes_text = _run_notes(preset, scale, no_video)
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
                scale,
                out_base,
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
    word = "drafts" if out_base == DRAFT_DIR else "final cards"
    skipped_text = f", {skipped} unchanged" if skipped else ""
    print(
        f"Done. {total} standard card(s) in {time.monotonic() - start:.1f}s, "
        f"{word} written to {out_base.relative_to(REPO_ROOT)}/{skipped_text}"
    )


def _generate_variants(
    paths: list[Path] | None,
    jobs: int,
    preset: str,
    scale: float,
    out_base: Path,
    force: bool = False,
    no_video: bool = False,
) -> None:
    """Process the selected cards in a pool of worker processes.

    With *no_video* (``--no-video``) the animated cards skip their MP4 and
    write out their first frame (PNG) alone — and the run needs only the
    viewer, no ffmpeg.
    """
    from nikke_reborn import box, expansion, pack
    from nikke_reborn.box import _process_box_item, _process_box_material
    from nikke_reborn.expansion import _find_pack_dirs
    from nikke_reborn.pack import _process_pack_item, _process_pack_material

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
        material_ok = _material_output_up_to_date(
            PACK_TEMPLATE,
            PACK_MATERIAL_NAME,
            pack_dir,
            out_base,
            front_source,
            back_source,
            force,
        )
        item_ok = _viewer_output_up_to_date(
            PACK_MESH,
            out_base / pack_dir.relative_to(CARDS_DIR) / PACK_MATERIAL_NAME,
            PACK_CONFIG,
            out_base / pack_dir.relative_to(CARDS_DIR) / PACK_ITEM_NAME,
            force,
        )
        box_ok = _material_output_up_to_date(
            BOX_TEMPLATE,
            BOX_MATERIAL_NAME,
            pack_dir,
            out_base,
            box_front_source,
            "",  # the box's material has no back
            force,
        )
        box_item_ok = _viewer_output_up_to_date(
            BOX_MESH,
            out_base / pack_dir.relative_to(CARDS_DIR) / BOX_MATERIAL_NAME,
            BOX_CONFIG,
            out_base / pack_dir.relative_to(CARDS_DIR) / BOX_ITEM_NAME,
            force,
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
    notes_text = _run_notes(preset, scale, no_video)
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
                scale,
                out_base,
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
            pool.submit(_process_pack_item, pack_dir, out_base, force): item_label(
                pack_dir
            )
            for pack_dir in sorted(item_needs - material_needs)
        }
        # The box's item is rendered from the box material's output file,
        # so each box's item starts only after its material has finished.
        box_item_futures: dict[Future[tuple[Path, bool]], Path] = {
            pool.submit(_process_box_item, pack_dir, out_base, force): box_item_label(
                pack_dir
            )
            for pack_dir in sorted(box_item_needs - box_needs)
        }
        material_futures: dict[Future[tuple[Path, bool]], Path] = {
            pool.submit(
                _process_pack_material,
                pack_dir,
                out_base,
                fronts[pack_dir],
                front_sources[pack_dir],
                backs[pack_dir],
                back_sources[pack_dir],
                force,
            ): pack_dir
            for pack_dir in material_needs
        }
        # The box's material is independent of the pack's: it starts at
        # once, from its own composed front.
        box_futures: dict[Future[tuple[Path, bool]], Path] = {
            pool.submit(
                _process_box_material,
                pack_dir,
                out_base,
                box_fronts[pack_dir],
                box_front_sources[pack_dir],
                box_sides[pack_dir],
                box_tops[pack_dir],
                force,
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
                    pool.submit(_process_pack_item, pack_dir, out_base, force)
                ] = item_label(pack_dir)
        for future in as_completed(box_futures):
            pack_dir = box_futures[future]
            report(future, box_label(pack_dir))
            if future.exception() is not None:
                continue  # no box material -> no box item for this pack
            if pack_dir in box_item_needs:
                box_item_futures[
                    pool.submit(_process_box_item, pack_dir, out_base, force)
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
    word = "drafts" if out_base == DRAFT_DIR else "final cards"
    skipped_text = f", {skipped} unchanged" if skipped else ""
    print(
        f"Done. {what} in {time.monotonic() - start:.1f}s, "
        f"{word} written to {out_base.relative_to(REPO_ROOT)}/{skipped_text}"
    )
