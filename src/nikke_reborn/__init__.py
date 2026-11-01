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
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Generator, Iterator
from concurrent.futures import (
    Future,
    ProcessPoolExecutor,
    as_completed,
)
from pathlib import Path
from typing import cast
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
    REPO_ROOT,
    SHOP_DIR,
    SOURCE_HASH_KEY,
    STANDARD_STEMS,
    UNITY_VIEWER,
    VIEWER,
)
from nikke_reborn.error import GenerationError
from nikke_reborn.file import _require_executable, _save_atomic, copy
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
    PROBER,
    _PipeDrain,
    _encode_mp4,
    _read_exact,
    _reap_viewer,
    _stream_composited,
    _stream_dual_composited,
)

from PIL import Image, ImageStat, ImageOps
MOD_NAME = "NIKKE REBORN"


# --- the profile presentation -------------------------------------------
# The profile cards render a rarity through the shared profile pipeline:
# one card is derived from every definition (except the ``Goddess`` and
# ``Classified`` presentations); all are written out with the
# variant's stem plus the ``Profile`` suffix. The background is a
# monochrome of its own dominant tint, the face framing (the viewer's
# ``--face`` at :data:`PROFILE_FACE_ZOOM`) animates over it, under the
# dominant tint wash, as a monochrome of the same hue, shifted aside from
# the body so it is not occluded, and the full body (the viewer's
# ``--full-body`` flag, ignoring the definition's pan/zoom) animates over
# the card mask (tinted at each pixel's own lightness, the white staying
# white) — the two framings are streamed in lockstep from the same
# definition. The name and subtitle overlays are applied as usual, like the
# other rarities, and the logo sits at the top right instead of the bottom
# right. The card also carries a photo reel down its right edge: the first
# PROFILE_REEL_COUNT of PROFILE_REEL_ANIMATIONS the character has (per the
# viewer's ``--list-animations``) become face stills — one at time 0 per
# animation (the viewer's ``--portrait 1`` framing in a square viewport),
# taken once per card and reused for every frame — fewer squares, or none,
# when fewer animations match. Each still sits on a white background and
# is framed by a border of the background's dominant tint
# (PROFILE_REEL_BORDER of the side). Everything is composited in memory —
# no intermediate frame touches the disk; only the finished card is
# written (atomically).
# --- the standard presentation -------------------------------------------
# The ``Standard`` tier is a derived presentation, like the profile cards,
# rendered through its own pipeline: one card is derived from each of the
# ``Classic``, ``Rare``, ``Special`` and ``Exotic`` definitions and written
# out with the variant's stem plus the ``Standard`` suffix. The card keeps
# the definition's ``background`` (in color, no monochrome, but faded a bit
# toward its dominant color, :data:`STANDARD_BG_FADE`), the standard card
# mask (:data:`STANDARD_MASK_PATH`) is composited over it, and the
# character's upper body (the viewer's ``--half-body`` flag, ignoring the
# definition's pan/zoom) animates over the mask. The name and subtitle
# overlays are applied as usual, like the profile cards; the manufacturer's
# logo sits at the top right (its corner inset by ``padding * 1.5``, in
# black), the NIKKE logo at the bottom right and the copyright at the bottom
# left, both in black.
#: The ``--face`` zoom that renders the face framing composited over the
#: profile card's background, under its tint wash (ahead of the full body).
PROFILE_FACE_ZOOM = 2
#: The face framing's vertical centre, as a fraction of the frame height
#: (0.1). :func:`_face_offset` treats the face as a square of side
#: ``height * PROFILE_FACE_CENTER_Y * PROFILE_FACE_ZOOM`` centred at that height
#: when deciding which side leaves its footprint least occluded by the body.
PROFILE_FACE_CENTER_Y = 0.1
#: Horizontal shifts (px) that move the face framing aside from the centered
#: full body so it is not occluded by the body: the face is rendered
#: :data:`PROFILE_FACE_OFFSET_LEFT` px to the left or
#: :data:`PROFILE_FACE_OFFSET_RIGHT` px to the right (whichever leaves its
#: footprint least occluded by the body, see :func:`_face_offset`).
PROFILE_FACE_OFFSET_LEFT = 500
PROFILE_FACE_OFFSET_RIGHT = 420
#: The profile card's "photo reel": the face stills stacked down the card's
#: right edge. The reel holds the first PROFILE_REEL_COUNT of
#: PROFILE_REEL_ANIMATIONS the character has (per the viewer's
#: ``--list-animations``); fewer stills — or none at all — when fewer of
#: the list match. Each still is the time 0 frame of its animation (the
#: viewer's ``--portrait 1`` framing in a square viewport of side
#: ``frame_width * PROFILE_REEL_SIDE``, see :func:`_photo_reel`), taken
#: once per card and reused for every frame, framed by a border of
#: ``side * PROFILE_REEL_BORDER`` filled with the background's dominant
#: tint: the framed squares run down the right edge, inset by
#: ``padding * PROFILE_REEL_MARGIN``, the first square's top edge at
#: ``frame_height * PROFILE_REEL_TOP`` and the card's padding of gap
#: between the squares.
PROFILE_REEL_COUNT = 3
#: The photo-reel square's side, as a fraction of the frame width
PROFILE_REEL_SIDE = 1 / 7
#: The first photo-reel square's top edge, as a fraction of the frame
PROFILE_REEL_TOP = 3 / 7
#: The photo reel's inset from the card's right edge, as a multiple of
#: the card's padding (padding * 1.5).
PROFILE_REEL_MARGIN = 1.5
#: The photo-reel border's width, as a fraction of the photo's side
#: (side * 0.005): a frame of the background's dominant tint
#: (PROFILE_REEL_BORDER_ALPHA) around each still, so the positioned block
#: is the framed still (side + 2 * the border across).
PROFILE_REEL_BORDER = 0.005
#: The photo-reel border's opacity (0.5): the tint frame is
#: semi-transparent, so the card art behind it shows through.
PROFILE_REEL_BORDER_ALPHA = 0.8
#: The photo reel's candidate animations, in order: the first
#: PROFILE_REEL_COUNT of these the character has become the reel's stills
#: (fewer, or none, when fewer match).
PROFILE_REEL_ANIMATIONS = (
    "think",
    "smile",
    "shy",
    "no",
    "delight",
    "surprise",
    "special_02",
    "special",
    "angry",
)

#: ``nikke-viewer`` writes its frames from multiple threads and can
#: occasionally leave a truncated file behind while still exiting with
#: status 0; a card whose render cannot be processed is re-run up to this
#: many times before giving up.
RENDER_ATTEMPTS = 3


DEFAULT_PRESET = "slow"
DRAFT_PRESET = "ultrafast"
DEFAULT_SCALE = 1.0
DRAFT_SCALE = 0.5

LOGO_PATHS = {
    False: IMAGES_DIR / "Logo_White.png",
    True: IMAGES_DIR / "Logo_Black.png",
}


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


def _source_hash(json_path: Path) -> str:
    """SHA-256 of the card definition file: the input the finished
    card embeds under :data:`SOURCE_HASH_KEY`."""
    return hashlib.sha256(json_path.read_bytes()).hexdigest()


def _profile_source_hash(json_path: Path) -> str:
    """SHA-256 of the profile card's inputs — the definition it renders,
    the card mask, the characters database (for the character's
    manufacturer) and the manufacturer's logo (the files its pixels
    depend on). Embedded under :data:`SOURCE_HASH_KEY` so an unchanged
    profile card is skipped instead of re-rendered."""
    digest = hashlib.sha256()
    digest.update(json_path.read_bytes())
    digest.update(PROFILE_MASK_PATH.read_bytes())
    digest.update((DATABASE_DIR / "characters.json").read_bytes())
    manufacturer = _character_manufacturer(str(_load_card(json_path).get("id", "")))
    if manufacturer is not None:
        logo = IMAGES_DIR / "logos" / f"{manufacturer}.png"
        if logo.is_file():
            digest.update(logo.read_bytes())
    return digest.hexdigest()


def _standard_source_hash(json_path: Path) -> str:
    """SHA-256 of the standard card's inputs — the definition it renders,
    the standard card mask, the characters database (for the character's
    manufacturer) and the manufacturer's logo (the files its pixels
    depend on). Embedded under :data:`SOURCE_HASH_KEY` so an unchanged
    standard card is skipped instead of re-rendered."""
    digest = hashlib.sha256()
    digest.update(json_path.read_bytes())
    digest.update(STANDARD_MASK_PATH.read_bytes())
    digest.update((DATABASE_DIR / "characters.json").read_bytes())
    manufacturer = _character_manufacturer(str(_load_card(json_path).get("id", "")))
    if manufacturer is not None:
        logo = IMAGES_DIR / "logos" / f"{manufacturer}.png"
        if logo.is_file():
            digest.update(logo.read_bytes())
    return digest.hexdigest()


def _stored_hash(out_path: Path) -> str | None:
    """The SOURCE_HASH_KEY embedded in a finished card, or None when
    the file carries no readable tag (older cards, corrupt files)."""
    if out_path.suffix == ".png":
        try:
            with Image.open(out_path) as image:
                return image.info.get(SOURCE_HASH_KEY)
        except Exception:
            return None
    try:
        result = subprocess.run(
            [
                PROBER,
                "-v",
                "error",
                "-show_entries",
                "format_tags",
                "-of",
                "json",
                str(out_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        return (
            json.loads(result.stdout)
            .get("format", {})
            .get("tags", {})
            .get(SOURCE_HASH_KEY)
        )
    except ValueError:
        return None


def _find_card_configs(paths: list[Path] | None = None) -> list[Path]:
    """Return the card definition files to generate.

    With no explicit *paths*, every ``*.json`` under :data:`CARDS_DIR`
    (sorted for deterministic output), excluding the pack's
    ``Expansion.json`` (the pack's metadata, not a card). Explicit paths are
    resolved against the repo root, must be files that live under
    :data:`CARDS_DIR`, are de-duplicated and returned in the given order.
    """
    if not paths:
        from nikke_reborn import expansion

        return sorted(
            path
            for path in CARDS_DIR.rglob("*.json")
            if path.name != expansion.EXPANSION_NAME
        )
    configs: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        json_path = (REPO_ROOT / raw).resolve() if not raw.is_absolute() else raw
        if not json_path.is_file():
            raise GenerationError(f"card definition not found: {raw}")
        if CARDS_DIR not in json_path.parents:
            raise GenerationError(
                f"card definition must be under {CARDS_DIR.relative_to(REPO_ROOT)}/: {raw}"
            )
        if json_path not in seen:
            seen.add(json_path)
            configs.append(json_path)
    return configs


def _expand_card_paths(paths: list[Path]) -> list[Path]:
    """Expand *paths* (each a set, a card, or a definition file, relative to
    the repo root or to ``cards/``) to the card definitions they contain:
    every ``*.json`` under each path (the pack's ``Expansion.json``
    excluded), validated and de-duplicated by :func:`_find_card_configs`."""
    from nikke_reborn import expansion

    files: list[Path] = []
    for raw in paths:
        root = (REPO_ROOT / raw).resolve()
        if not root.exists():
            root = (CARDS_DIR / raw).resolve()
        if not root.exists():
            raise GenerationError(f"no such card path: {raw}")
        if root != CARDS_DIR and CARDS_DIR not in root.parents:
            raise GenerationError(
                f"card path must be under {CARDS_DIR.relative_to(REPO_ROOT)}/: {raw}"
            )
        if root.is_file():
            if not root.name.endswith(".json") or root.name == expansion.EXPANSION_NAME:
                raise GenerationError(f"not a card definition: {raw}")
            files.append(root)
        else:
            files.extend(
                sorted(
                    path
                    for path in root.rglob("*.json")
                    if path.name != expansion.EXPANSION_NAME
                )
            )
    if not files:
        raise GenerationError("no card definitions selected")
    return _find_card_configs(files)


def _selected_configs(paths: list[Path]) -> list[Path] | None:
    """The card definitions to generate: None when nothing is selected
    (everything, as before), else the card definitions the selected
    *paths* expand to, in the given order."""
    if not paths:
        return None
    return _expand_card_paths(paths)


def _load_card(json_path: Path) -> dict:
    try:
        import json

        return json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GenerationError(
            f"cannot read card definition {json_path.name}: {exc}"
        ) from exc


def _background_path(card: dict, json_path: Path) -> Path:
    if "background" not in card:
        raise GenerationError(f"{json_path.name}: missing 'background'")
    background = (json_path.parent / card["background"]).resolve()
    if not background.is_file():
        raise GenerationError(f"{json_path.name}: background not found: {background}")
    return background


def _character_manufacturer(card_id: str) -> str | None:
    """The character's ``manufacturer`` from ``database/characters.json``
    (looked up by *card_id*; a skin variant's suffixed id, c010_02, falls
    back to the base character, as the rarity does). None when the
    character is unknown or carries no manufacturer."""
    characters = json.load((DATABASE_DIR / "characters.json").open())
    characters = {character["id"]: character for character in characters}
    character = characters.get(card_id) or characters.get(card_id.split("_", 1)[0])
    manufacturer = character.get("manufacturer") if character else None
    return manufacturer or None


def _manufacturer_logo(card_id: str) -> Image.Image | None:
    """The character's manufacturer logo:
    ``assets/images/logos/<manufacturer>.png`` (white on transparency,
    tinted to the bar's fill when placed) — None
    when the character has no manufacturer or its logo file is missing."""
    manufacturer = _character_manufacturer(card_id)
    if manufacturer is None:
        return None
    logo_path = IMAGES_DIR / "logos" / f"{manufacturer}.png"
    if not logo_path.is_file():
        return None
    return Image.open(logo_path).convert("RGBA")


def _render_and_finish(
    json_path: Path,
    size: tuple[int, int],
    animated: bool,
    background: Image.Image,
    logo: Image.Image,
    margin: int,
    padding: int,
    copyright_color: tuple[int, int, int, int],
    framerate: int,
    ffmpeg_threads: int,
    composite_workers: int,
    preset: str,
    scale: float,
    out_base: Path,
    source_hash: str,
    base: Image.Image | None = None,
    render_path: Path | None = None,
    stem: str | None = None,
    full_body: bool = False,
) -> tuple[Path, dict[str, float | None]]:
    """Render *json_path* via the viewer's ``--stdout`` raw stream and write
    the final PNG, or the MP4 alongside its first frame as a PNG.

    *base* overrides the composited-over background (defaults to
    ``_fit_background(background, size)``); *render_path* is the config the
    viewer reads (defaults to *json_path* itself); *stem* overrides the
    variant in the output filename (defaults to the definition's stem);
    *full_body* passes the viewer's ``--full-body`` flag, which ignores the
    config's pan/zoom to render the full body (the profile cards).

    Nothing intermediate touches the disk: the viewer's raw RGBA frames are
    piped straight into the in-memory compositing and (for animations) the
    ffmpeg encode. Only the finished card is written (atomically). A failure
    at any stage surfaces as a :class:`GenerationError` so the caller can
    re-render the card from scratch.

    Returns the finished card's path and the stage timings in seconds (see
    :func:`_write_final_card`, which performs the write and the reap). A raw
    frame is far larger than the pipe buffer, so the viewer blocks on
    write until the reader drains: under load ``render`` therefore
    reflects the slowest downstream stage (usually the encode) as much as
    the viewer itself; for the viewer's own cost, run it with its stdout
    redirected to /dev/null.
    """
    if base is None:
        base = _fit_background(background, size)
    if render_path is None:
        render_path = json_path
    if stem is None:
        stem = json_path.stem
    # The logo and copyright line sit on top of the art, not under it:
    # pre-stamp them onto a transparent layer and let _stream_composited
    # apply it to each frame after the art is composited over the
    # background.
    overlay, overlay_pos = _logo_copyright_overlay(
        size, logo, margin, padding, copyright_color
    )
    composite_time: list[float] = [0.0]
    stream_end: list[float] = [0.0]

    # Spawn the viewer streaming raw RGBA frames to stdout (no intermediate
    # files). --full-body, when set, ignores the config's pan/zoom and
    # renders the full body. stderr is drained in a thread so it never
    # blocks the viewer.
    render_started = time.perf_counter()
    viewer_args = [VIEWER]
    if full_body:
        viewer_args.append("--full-body")
    viewer_args += ["--stdout", str(render_path)]
    try:
        viewer = subprocess.Popen(
            viewer_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=PIPE_BUFSIZE,
        )
    except OSError as exc:
        raise GenerationError(f"could not run {VIEWER!r}: {exc}") from exc
    assert viewer.stderr is not None
    # A Popen pipe is a buffered reader (needed for read1).
    drain = _PipeDrain(cast("io.BufferedReader", viewer.stderr))
    first_frame: list[Image.Image] = []
    composited = _stream_composited(
        viewer,
        drain,
        json_path,
        size,
        base,
        overlay,
        overlay_pos,
        composite_workers,
        first_frame,
        composite_time,
        stream_end,
    )
    return _write_final_card(
        composited,
        json_path,
        out_base,
        stem,
        animated,
        size,
        framerate,
        ffmpeg_threads,
        preset,
        scale,
        source_hash,
        first_frame,
        composite_time,
        stream_end,
        render_started,
    )


class _FirstFrameWriter:
    """The animation's first-frame PNG sidecar, written in a background
    thread.

    Started with the first consumed frame (mid-encode, see
    :func:`_write_final_card`), so the PNG's save overlaps the encode
    instead of following it. *join* waits for the write and re-raises its
    failure — a finished card only exists in its complete form (both the
    mp4 and the sidecar), and a failed write still surfaces as the card's
    failure so the caller re-renders it from scratch."""

    def __init__(self, out_path: Path, source_hash: str) -> None:
        self._out_path = out_path
        self._source_hash = source_hash
        self._thread: threading.Thread | None = None
        self._exc: BaseException | None = None
        self._done = False

    @property
    def started(self) -> bool:
        return self._thread is not None

    def start(self, image: Image.Image) -> None:
        if self._thread is not None:
            return
        self._image = image
        self._thread = threading.Thread(
            target=self._run, name="first-frame-png", daemon=True
        )
        self._thread.start()

    def _run(self) -> None:
        try:
            _save_atomic(self._image.convert("RGB"), self._out_path, self._source_hash)
            self._done = True
        except BaseException as exc:  # noqa: BLE001 — re-raised by join
            self._exc = exc

    def join(self, *, fail: bool = True) -> None:
        """Wait for the write; when *fail*, re-raise its failure (or the
        write not completing at all). A no-op when never started."""
        if self._thread is None:
            return
        self._thread.join()
        self._thread = None
        if fail and (self._exc is not None or not self._done):
            raise self._exc or GenerationError("first-frame PNG write did not complete")


def _write_final_card(
    composited: Generator[Image.Image],
    json_path: Path,
    out_base: Path,
    stem: str,
    animated: bool,
    size: tuple[int, int],
    framerate: int,
    ffmpeg_threads: int,
    preset: str,
    scale: float,
    source_hash: str,
    first_frame: list[Image.Image],
    composite_time: list[float],
    stream_end: list[float],
    render_started: float,
) -> tuple[Path, dict[str, float | None]]:
    """Write a composited frame stream (raw RGBA bytes) to the final card.

    An animation is encoded to an MP4 alongside its first frame (the same
    composited frame, so it matches the mp4's opening frame exactly); a
    fixed-time card is written as a single PNG. For animations the
    first-frame PNG is written in a background thread that starts with the
    first consumed frame, so the sidecar's save overlaps the encode instead
    of following it. *composited* is closed (so the viewer stream(s) are
    reaped) and the stage timings (in seconds) are returned: ``render``
    (spawn until the frame stream is fully delivered), ``composite`` (the
    per-frame Pillow work — decode, blend, stamps — summed across the worker
    threads) and ``encode`` (the ffmpeg wall time
    for animations, the PNG write for static cards). The stages overlap —
    the encode consumes frames while the viewer still renders, the
    compositing runs in its own threads, and the first-frame sidecar runs in
    its own thread — so the numbers are per-stage costs, not a sequential
    partition.
    """
    out_path = _card_out_path(out_base, json_path, "mp4" if animated else "png", stem)
    encode_time: float | None = None
    try:
        if animated:
            tmp_path = out_path.with_name(out_path.name + ".part")
            png_writer = _FirstFrameWriter(
                _card_out_path(out_base, json_path, "png", stem), source_hash
            )

            def feed(frames: Iterator[Image.Image]) -> Iterator[Image.Image]:
                # Fire the sidecar's write at the first frame, so it runs
                # under the encode instead of after it.
                for frame in frames:
                    if not png_writer.started and first_frame:
                        png_writer.start(first_frame[0])
                    yield frame

            try:
                encode_started = time.perf_counter()
                _encode_mp4(
                    feed(composited),
                    size,
                    framerate,
                    tmp_path,
                    ffmpeg_threads,
                    preset,
                    scale,
                    source_hash,
                )
                encode_time = time.perf_counter() - encode_started
                if not first_frame:
                    raise GenerationError(
                        f"{VIEWER} produced no frames for {json_path.name}"
                    )
            except Exception:
                tmp_path.unlink(missing_ok=True)
                # Let the sidecar's write settle before the retry starts
                # (both write the same .part); its error does not shadow
                # the encode's.
                png_writer.join(fail=False)
                raise
            tmp_path.replace(out_path)
            png_writer.join()
        else:
            # A single frame: consume the stream (the frame's image landed
            # in first_frame while it was composited) and write it.
            next(composited, None)
            if not first_frame:
                raise GenerationError(
                    f"{VIEWER} produced no frame for {json_path.name}"
                )
            encode_started = time.perf_counter()
            _save_atomic(first_frame[0].convert("RGB"), out_path, source_hash)
            encode_time = time.perf_counter() - encode_started
    finally:
        # Stop consuming and make sure the viewer stream is reaped (the
        # compositor's ``finally`` runs, reaping the viewer(s) and checking
        # their exit).
        composited.close()
    # Measured to stream EOF (not to the reap, which happens after the
    # encode and the save), so the number covers the frame delivery only.
    render_seconds = (stream_end[0] or time.perf_counter()) - render_started
    return out_path, {
        "render": render_seconds,
        "composite": composite_time[0],
        "encode": encode_time,
    }


def _first_frame(
    json_path: Path, size: tuple[int, int], *viewer_flags: str
) -> Image.Image:
    """The first frame of *json_path* rendered by the viewer with
    *viewer_flags* — one raw RGBA frame read from the ``--stdout`` stream.
    The viewer is reaped; for an animation only the opening frame is needed."""
    width, height = size
    viewer = subprocess.Popen(
        [VIEWER, *viewer_flags, "--stdout", str(json_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=PIPE_BUFSIZE,
    )
    assert viewer.stdout is not None
    assert viewer.stderr is not None
    # A Popen pipe is a buffered reader (needed for read1).
    drain = _PipeDrain(cast("io.BufferedReader", viewer.stderr))
    try:
        data = _read_exact(viewer.stdout, width * height * 4)
    finally:
        # One frame is all we need; stop consuming and reap the viewer, which
        # may still be mid-stream for animations.
        _reap_viewer(viewer, drain, clean_exit_expected=False)
    frame_bytes = width * height * 4
    if len(data) != frame_bytes:
        raise GenerationError(
            f"{VIEWER} stream for {json_path.name} truncated: "
            f"{len(data)} of {frame_bytes} bytes"
        )
    return Image.frombytes("RGBA", (width, height), data)


def _face_offset(json_path: Path, size: tuple[int, int]) -> int:
    """The face framing's ``--offset-x``: :data:`PROFILE_FACE_OFFSET_LEFT` px to
    the left or :data:`PROFILE_FACE_OFFSET_RIGHT` px to the right, whichever
    leaves the face's footprint least occluded by the full body, so the face
    sits clear rather than behind it.

    The face's centre always sits at :data:`PROFILE_FACE_CENTER_Y` of the frame
    height, so the face is treated as a square of side
    ``height * PROFILE_FACE_CENTER_Y * :data:`PROFILE_FACE_ZOOM```. Each candidate
    footprint — the left at the card centre minus the left offset, the right at
    the card centre plus the right offset — is measured against the body's
    opaque pixels and the face is sent to the emptier one (fewer body pixels
    behind it). A bodyless frame leaves the face centered (0).
    """
    width, height = size
    body = _first_frame(json_path, size, "--full-body")
    # The face's footprint: a square centred at the face's fixed vertical
    # centre, one for each candidate horizontal position (left / right).
    alpha = body.getchannel("A").point(lambda v: 255 if v > 32 else 0)
    centre_y = int(height * PROFILE_FACE_CENTER_Y)
    half = int(height * PROFILE_FACE_CENTER_Y * PROFILE_FACE_ZOOM) // 2

    def occlusion(cx: int) -> int:
        x0, y0, x1, y1 = cx - half, centre_y - half, cx + half, centre_y + half
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(width, x1), min(height, y1)
        if x0 >= x1 or y0 >= y1:
            return 0
        return ImageStat.Stat(alpha.crop((x0, y0, x1, y1))).sum[0]

    if not ImageStat.Stat(alpha).sum[0]:
        return 0  # no body at all; keep the face centered
    left = occlusion(width // 2 - PROFILE_FACE_OFFSET_LEFT)
    right = occlusion(width // 2 + PROFILE_FACE_OFFSET_RIGHT)
    # Both footprints empty means the body sits *between* them, so the face
    # still shifts (a tie defaults to the left); never leave it centered on
    # top of the body.
    return -PROFILE_FACE_OFFSET_LEFT if left < right else PROFILE_FACE_OFFSET_RIGHT


def _reel_animations(json_path: Path) -> list[str]:
    """The photo reel's animations: the first PROFILE_REEL_COUNT of
    PROFILE_REEL_ANIMATIONS (in the list's order) the character has, per
    the viewer's ``--list-animations`` for *json_path* — fewer (or none)
    when fewer of the list match."""
    result = subprocess.run(
        [VIEWER, "--list-animations", str(json_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = result.stderr.decode(errors="replace").strip()
        detail = f": {detail[-500:]}" if detail else ""
        raise GenerationError(
            f"{VIEWER} --list-animations for {json_path.name} "
            f"failed (exit {result.returncode}){detail}"
        )
    available = {
        line.strip()
        for line in result.stdout.decode(errors="replace").splitlines()
        if line.strip()
    }
    return [
        animation for animation in PROFILE_REEL_ANIMATIONS if animation in available
    ][:PROFILE_REEL_COUNT]


def _photo_reel(
    json_path: Path,
    size: tuple[int, int],
    padding: int,
    tint_rgb: tuple[int, int, int],
) -> list[tuple[Image.Image, tuple[int, int]]]:
    """The profile card's photo reel (see :data:`PROFILE_REEL_COUNT`):
    one face still per animation of :func:`_reel_animations`, as
    (still, position) pairs for the compositor.

    Each still is the time 0 frame of its animation, rendered in the
    viewer's ``--portrait 1`` framing (the face exactly inside the
    viewport bounds) in a square viewport of side
    ``frame_width * PROFILE_REEL_SIDE`` (``--width``/``--height``,
    ``--time 0`` and ``--animation``) and flattened onto a white
    background (the viewer's frames are transparent where the character
    does not cover): the stills are taken once per card and reused for
    every frame. Each is framed by a border of
    ``side * PROFILE_REEL_BORDER`` filled with *tint_rgb* (the
    background's dominant tint, at PROFILE_REEL_BORDER_ALPHA) — the
    positioned block is the framed still. The blocks run down the right
    edge, inset by ``*padding* * PROFILE_REEL_MARGIN``, the first block's
    top edge at ``frame_height * PROFILE_REEL_TOP`` and a gap of *padding*
    between them. Empty (no reel) when the character has none of
    PROFILE_REEL_ANIMATIONS.
    """
    animations = _reel_animations(json_path)
    if not animations:
        return []
    side = round(size[0] * PROFILE_REEL_SIDE)
    border = round(side * PROFILE_REEL_BORDER)
    block = side + 2 * border
    left = size[0] - round(padding * PROFILE_REEL_MARGIN) - block
    top = round(size[1] * PROFILE_REEL_TOP)
    step = block + padding
    reel: list[tuple[Image.Image, tuple[int, int]]] = []
    for index, animation in enumerate(animations):
        still = _first_frame(
            json_path,
            (side, side),
            "--portrait",
            "1",
            "--width",
            str(side),
            "--height",
            str(side),
            "--time",
            "0",
            "--animation",
            animation,
        )
        # The still's background: the viewer's frames are transparent where
        # the character does not cover, so flatten them to white.
        white = Image.new("RGBA", still.size, (255, 255, 255, 255))
        white.paste(still, (0, 0), still)
        still = white
        # The border (PROFILE_REEL_BORDER of the photo's side, the
        # background's dominant tint at PROFILE_REEL_BORDER_ALPHA) frames
        # the still.
        framed = Image.new(
            "RGBA", (block, block), (*tint_rgb, round(255 * PROFILE_REEL_BORDER_ALPHA))
        )
        framed.paste(still, (border, border))
        reel.append((framed, (left, top + index * step)))
    return reel


def _render_profile(
    json_path: Path,
    size: tuple[int, int],
    animated: bool,
    background: Image.Image,
    tint: Image.Image,
    mask: Image.Image,
    tint_rgb: tuple[int, int, int],
    logo: Image.Image,
    margin: int,
    padding: int,
    copyright_color: tuple[int, int, int, int],
    name: str,
    subtitle: str,
    manufacturer_logo: Image.Image | None,
    framerate: int,
    ffmpeg_threads: int,
    composite_workers: int,
    preset: str,
    scale: float,
    out_base: Path,
    source_hash: str,
    face_zoom: float,
) -> tuple[Path, dict[str, float | None]]:
    """Render the profile card (a presentation of *json_path*, written out
    as ``<card>_<variant>Profile.<suffix>``): the ``--face <face_zoom>``
    framing animates (as a monochrome of the tint's hue, shifted aside from
    the body) over the background, under the tint wash, and the
    ``--full-body`` framing animates over the mask, both streamed from the
    same definition so the two stay in lockstep. The name and subtitle
    overlays are applied as usual, like the other rarities (with the
    character's manufacturer's logo above the name's bar, *manufacturer_logo*);
    the logo sits at the top right. The card's photo reel (the face stills
    down the right edge, :func:`_photo_reel`) is composited onto every
    frame as well.

    Like :func:`_render_and_finish`, nothing intermediate touches the disk —
    the two raw RGBA streams are piped straight into the in-memory
    compositing and (for animations) the ffmpeg encode; only the finished
    card is written (atomically, as ``<card>_<stem>.<suffix>``). Returns the
    finished card's path and the stage timings (see
    :func:`_write_final_card`).
    """
    stem = _profile_stem(json_path)
    # The logo and copyright line sit on top of the art: pre-stamp them onto
    # a transparent layer and let the compositor apply it to each frame.
    # The profile card's logo sits at the top right instead of the bottom
    # right.
    overlay, overlay_pos = _logo_copyright_overlay(
        size, logo, margin, padding, copyright_color, logo_top=True
    )
    parts = (
        _name_layers(
            size,
            name,
            subtitle,
            padding,
            NAME_RECT_COLOR,
            _rect_tint(background),
            manufacturer_logo,
        )
        if (name or subtitle)
        else None
    )
    composite_time: list[float] = [0.0]
    stream_end: list[float] = [0.0]

    # The face is shifted to the side the body leaves most room on (measured
    # from the body's first frame), so it is not occluded by the centered
    # body.
    face_offset = _face_offset(json_path, size)

    # The photo reel (the face stills down the right edge): the stills are
    # taken once — one frame at time 0 per animation — and reused for
    # every frame of the card.
    reel = _photo_reel(json_path, size, padding, tint_rgb)

    # Spawn the two viewers streaming raw RGBA frames to stdout (no
    # intermediate files): the face framing (over the background, under the
    # tint wash, shifted aside from the body) and the full body (over the
    # mask). stderr is drained in a thread so it never blocks a viewer.
    render_started = time.perf_counter()
    face_args = [
        VIEWER,
        "--face",
        str(face_zoom),
        "--offset-x",
        str(face_offset),
        "--stdout",
        str(json_path),
    ]
    body_args = [VIEWER, "--full-body", "--stdout", str(json_path)]
    try:
        face_viewer = subprocess.Popen(
            face_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=PIPE_BUFSIZE,
        )
    except OSError as exc:
        raise GenerationError(f"could not run {VIEWER!r} (face): {exc}") from exc
    try:
        body_viewer = subprocess.Popen(
            body_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=PIPE_BUFSIZE,
        )
    except OSError as exc:
        face_viewer.kill()
        face_viewer.wait()
        raise GenerationError(f"could not run {VIEWER!r} (body): {exc}") from exc
    assert face_viewer.stderr is not None
    assert body_viewer.stderr is not None
    # A Popen pipe is a buffered reader (needed for read1).
    face_drain = _PipeDrain(cast("io.BufferedReader", face_viewer.stderr))
    body_drain = _PipeDrain(cast("io.BufferedReader", body_viewer.stderr))
    first_frame: list[Image.Image] = []
    composited = _stream_dual_composited(
        face_viewer,
        face_drain,
        body_viewer,
        body_drain,
        json_path,
        size,
        background,
        tint,
        mask,
        overlay,
        overlay_pos,
        parts,
        reel,
        composite_workers,
        first_frame,
        composite_time,
        stream_end,
    )
    return _write_final_card(
        composited,
        json_path,
        out_base,
        stem,
        animated,
        size,
        framerate,
        ffmpeg_threads,
        preset,
        scale,
        source_hash,
        first_frame,
        composite_time,
        stream_end,
        render_started,
    )


def _render_standard(
    json_path: Path,
    size: tuple[int, int],
    animated: bool,
    base: Image.Image,
    sub_rect_color: tuple[int, int, int],
    name: str,
    subtitle: str,
    manufacturer_logo: Image.Image | None,
    logo: Image.Image,
    margin: int,
    padding: int,
    copyright_color: tuple[int, int, int, int],
    framerate: int,
    ffmpeg_threads: int,
    composite_workers: int,
    preset: str,
    scale: float,
    out_base: Path,
    source_hash: str,
) -> tuple[Path, dict[str, float | None]]:
    """Render the standard card (a presentation of *json_path*, written out
    as ``<card>_<variant>Standard.<suffix>``): the definition's
    *background* (faded toward its dominant color, no monochrome) carries
    the standard card mask
    (:data:`STANDARD_MASK_PATH`, already composited into *base*), and the
    character's upper body (the viewer's ``--half-body`` flag, ignoring the
    definition's pan/zoom) animates over it. The name and subtitle overlays
    are applied as usual, like the profile cards; the manufacturer's logo
    (*manufacturer_logo*) sits at the top right, its corner inset by
    ``padding * 1.5`` and drawn in black (the white face would hide the white
    version); the NIKKE logo sits at the bottom right and the copyright at
    the bottom left, both in black.

    Like :func:`_render_and_finish` and :func:`_render_profile`, nothing
    intermediate touches the disk — the raw RGBA stream is piped straight
    into the in-memory compositing and (for animations) the ffmpeg encode;
    only the finished card is written (atomically, as
    ``<card>_<stem>.<suffix>``). Returns the finished card's path and the
    stage timings (see :func:`_write_final_card`).
    """
    stem = _standard_stem(json_path)
    # The logo, the copyright line and the manufacturer's logo sit on top of
    # the art: pre-stamp them onto a transparent layer and let the
    # compositor apply them to each frame. The NIKKE logo sits at the bottom
    # right (the copyright at the bottom left), both in black; the
    # manufacturer's logo sits at the top right, its corner inset by
    # padding * 1.5, in black (the standard card's white face would hide the
    # white version).
    overlay, overlay_pos = _logo_copyright_overlay(
        size, logo, margin, padding, copyright_color
    )
    if manufacturer_logo is not None:
        inset = round(padding * 1.5)
        mark_w = round(size[0] * MANUFACTURER_LOGO_WIDTH)
        mark_h = round(mark_w * manufacturer_logo.height / manufacturer_logo.width)
        mark = manufacturer_logo.resize((mark_w, mark_h), Image.Resampling.LANCZOS)
        mark = _tint_layer(mark.getchannel("A"), (0, 0, 0), 1.0)
        # Rebuild on a full frame so both the (already cropped) logo/copyright
        # overlay and the new top-right mark land at their card positions,
        # then crop back to the combined ink.
        full = Image.new("RGBA", size, (0, 0, 0, 0))
        full.alpha_composite(overlay, overlay_pos)
        full.alpha_composite(mark, (size[0] - inset - mark_w, inset))
        box = full.getbbox()
        assert box is not None, "the standard card's overlay is empty"
        overlay, overlay_pos = full.crop(box), (box[0], box[1])
    parts = (
        _name_layers(
            size,
            name,
            subtitle,
            padding,
            NAME_RECT_COLOR,
            sub_rect_color,
        )
        if (name or subtitle)
        else None
    )
    composite_time: list[float] = [0.0]
    stream_end: list[float] = [0.0]

    # Spawn the viewer streaming raw RGBA frames to stdout (no intermediate
    # files): the half body over the mask. --half-body ignores the
    # definition's pan/zoom and frames the upper body. stderr is drained in
    # a thread so it never blocks the viewer.
    render_started = time.perf_counter()
    viewer_args = [VIEWER, "--half-body", "--stdout", str(json_path)]
    try:
        viewer = subprocess.Popen(
            viewer_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=PIPE_BUFSIZE,
        )
    except OSError as exc:
        raise GenerationError(f"could not run {VIEWER!r} (half body): {exc}") from exc
    assert viewer.stderr is not None
    # A Popen pipe is a buffered reader (needed for read1).
    drain = _PipeDrain(cast("io.BufferedReader", viewer.stderr))
    first_frame: list[Image.Image] = []
    composited = _stream_composited(
        viewer,
        drain,
        json_path,
        size,
        base,
        overlay,
        overlay_pos,
        composite_workers,
        first_frame,
        composite_time,
        stream_end,
        parts,
    )
    return _write_final_card(
        composited,
        json_path,
        out_base,
        stem,
        animated,
        size,
        framerate,
        ffmpeg_threads,
        preset,
        scale,
        source_hash,
        first_frame,
        composite_time,
        stream_end,
        render_started,
    )


def _card_out_path(
    out_base: Path, json_path: Path, suffix: str, stem: str | None = None
) -> Path:
    """The flat output path for a card definition: the card's
    directory is folded into the filename, so
    ``cards/<set>/<card>/<variant>.json`` renders to
    ``<out_base>/<set>/<card>_<variant>.<suffix>`` (deeper nesting,
    if ever used, is folded the same way, one dash per directory).

    *stem* overrides the variant in the filename (defaults to the
    definition's own stem) — the profile cards pass their output stem, so a
    profile card writes out as ``<card>_<variant>Profile.<suffix>``.
    """
    if stem is None:
        stem = json_path.stem
    card_rel = json_path.parent.relative_to(CARDS_DIR)
    return (
        out_base / card_rel.parts[0] / f"{'_'.join(card_rel.parts[1:])}_{stem}.{suffix}"
    )


def _process_card(
    json_path: Path,
    ffmpeg_threads: int = 1,
    composite_workers: int = 4,
    preset: str = DEFAULT_PRESET,
    scale: float = DEFAULT_SCALE,
    out_base: Path = OUTPUT_DIR,
    force: bool = False,
    no_video: bool = False,
) -> tuple[Path, bool, dict[str, float | None] | None]:
    """Render, composite and encode a single card definition.

    With *no_video* (``--no-video``) an animated definition renders its
    first frame alone — its MP4 is skipped and the viewer reaped right
    after that frame — so the output, and the up-to-date check, cover the
    first-frame PNG.

    Returns ``(out_path, skipped, timings)``; *skipped* is True when the
    output already exists and the definition hash it embeds matches the
    current one (nothing was re-rendered), in which case *timings* is None;
    otherwise it is the stage-timing dict from :func:`_render_and_finish`
    plus ``total``, the card's overall wall-clock seconds.
    """
    total_started = time.perf_counter()
    json_path = json_path.resolve()
    card = _load_card(json_path)
    background = Image.open(_background_path(card, json_path)).convert("RGBA")

    logo_path = LOGO_PATHS[bool(card.get("invert_logo", False))]
    if not logo_path.is_file():
        raise GenerationError(f"logo not found: {logo_path}")
    logo = Image.open(logo_path).convert("RGBA")
    if not FONT.is_file():
        raise GenerationError(f"font not found: {FONT}")
    # The full-art cards never carry the card name (the profile and
    # standard cards render the title and subtitle).
    padding = card["padding"]
    margin = round(LOGO_PADDING_FACTOR * padding)
    copyright_color = (
        (0, 0, 0, 255) if card.get("invert_copyright", False) else (255, 255, 255, 255)
    )
    framerate = card["framerate"] or DEFAULT_FRAMERATE

    viewport = card.get("viewport")
    if not viewport:
        raise GenerationError(
            f"{json_path.name}: missing 'viewport' (needed to size the raw "
            f"frames streamed by {VIEWER} --stdout)"
        )
    size = (int(viewport[0]), int(viewport[1]))

    # A definition without a `time` renders an animation (mp4) plus its
    # first frame (png); one with a `time` renders a single frame (png).
    # With --no-video an animation renders its first frame (png) alone:
    # the mp4 is skipped and the viewer reaped right after that frame.
    animated = card.get("time") is None and not no_video
    out_path = _card_out_path(out_base, json_path, "mp4" if animated else "png")
    source_hash = _source_hash(json_path)
    if not force:
        up_to_date = out_path.is_file() and _stored_hash(out_path) == source_hash
        if up_to_date and animated:
            # The animation's first frame is kept alongside it; a missing or
            # stale copy forces the card to be re-rendered.
            first_frame_path = _card_out_path(out_base, json_path, "png")
            up_to_date = (
                first_frame_path.is_file()
                and _stored_hash(first_frame_path) == source_hash
            )
        if up_to_date:
            # The definition is unchanged since the card was written: skip
            # the render
            return out_path, True, None
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # The GPU is shared with other tenants, so failures here can be
    # transient (render error, truncated frame stream, encode error); the
    # card is re-rendered from scratch up to RENDER_ATTEMPTS times before
    # giving up. Nothing intermediate is written to disk in between.
    for attempt in range(1, RENDER_ATTEMPTS + 1):
        try:
            finished, timings = _render_and_finish(
                json_path,
                size,
                animated,
                background,
                logo,
                margin,
                padding,
                copyright_color,
                framerate,
                ffmpeg_threads,
                composite_workers,
                preset,
                scale,
                out_base,
                source_hash,
            )
            timings["total"] = time.perf_counter() - total_started
            return finished, False, timings
        except Exception as exc:
            if attempt >= RENDER_ATTEMPTS:
                raise GenerationError(
                    f"render of {json_path.name} still failing after "
                    f"{RENDER_ATTEMPTS} attempts: {exc}"
                ) from exc
            print(
                f"    ! {json_path.name}: {exc}; re-rendering "
                f"(attempt {attempt}/{RENDER_ATTEMPTS})",
                flush=True,
            )
    raise AssertionError("unreachable")  # pragma: no cover


def _profile_stem(json_path: Path) -> str:
    """The output stem of the profile card rendered from *json_path*: the
    variant's stem with the ``Profile`` suffix (an ``Aim.json`` writes out
    as ``<card>_AimProfile.<suffix>``)."""
    return f"{json_path.stem}Profile"


def _standard_stem(json_path: Path) -> str:
    """The output stem of the standard card rendered from *json_path*: the
    variant's stem with the ``Standard`` suffix (a ``Rare.json`` writes out
    as ``<card>_RareStandard.<suffix>``)."""
    return f"{json_path.stem}Standard"


def _process_profile_card(
    json_path: Path,
    ffmpeg_threads: int = 1,
    composite_workers: int = 4,
    preset: str = DEFAULT_PRESET,
    scale: float = DEFAULT_SCALE,
    out_base: Path = OUTPUT_DIR,
    force: bool = False,
    no_video: bool = False,
) -> tuple[Path, bool, dict[str, float | None] | None]:
    """Render the ``<variant>Profile`` profile card for *json_path*
    (derived from its own definition — one of the ``Classic``, ``Idle``,
    ``Cover`` and ``Aim`` presentations, see :data:`PROFILE_STEMS`; the
    ``Rare``, ``Special`` and ``Exotic`` presentations render a standard
    card instead, and the ``Goddess`` and ``Classified`` presentations
    render no derived card): the ``--face`` framing animates (as a
    monochrome of the tint's hue) over the background, under its dominant
    tint wash, and the ``--full-body`` framing animates over the card mask
    (both streamed in lockstep from the same definition). The name and
    subtitle overlays are applied as usual, like the other rarities; the
    logo sits at the top right. The card's photo reel (the face stills down
    the right edge, :func:`_photo_reel`) is composited onto every frame.

    With *no_video* (``--no-video``) an animated profile card renders its
    first frame alone — its MP4 is skipped and the viewers reaped right
    after that frame — so the output, and the up-to-date check, cover the
    first-frame PNG.

    Everything is composited in memory — the viewer's raw frames stream
    straight into the pipeline and nothing intermediate touches the disk
    (only the finished card is written). Returns ``(out_path, skipped,
    timings)`` like :func:`_process_card` (written out as
    ``<card>_<stem>.<suffix>``).
    """
    total_started = time.perf_counter()
    json_path = json_path.resolve()
    card = _load_card(json_path)
    background = Image.open(_background_path(card, json_path)).convert("RGBA")

    # The profile presentation always carries the black logo and black
    # copyright — the profile card's white mask would wash out the white
    # versions — while the name stays white, as the other rarities.
    logo_path = LOGO_PATHS[True]
    if not logo_path.is_file():
        raise GenerationError(f"logo not found: {logo_path}")
    logo = Image.open(logo_path).convert("RGBA")
    if not FONT.is_file():
        raise GenerationError(f"font not found: {FONT}")
    if not FONT_NAME.is_file():
        raise GenerationError(f"font not found: {FONT_NAME}")
    # The profile presentation carries the card name, as the other rarities
    # do (a nameless definition renders without the name stack).
    name = str(card.get("title", ""))
    subtitle = str(card.get("subtitle", ""))
    # The character's manufacturer's logo (tinted to the title's
    # background; None when the character or its manufacturer is
    # unknown): it sits above the name's bar.
    manufacturer_logo = _manufacturer_logo(str(card.get("id", "")))
    padding = card["padding"]
    margin = round(LOGO_PADDING_FACTOR * padding)
    copyright_color = (0, 0, 0, 255)
    framerate = card["framerate"] or DEFAULT_FRAMERATE

    viewport = card.get("viewport")
    if not viewport:
        raise GenerationError(
            f"{json_path.name}: missing 'viewport' (needed to size the raw "
            f"frames streamed by {VIEWER} --stdout)"
        )
    size = (int(viewport[0]), int(viewport[1]))

    # A definition without a `time` renders an animation (mp4) plus its first
    # frame (png); one with a `time` renders a single frame (png). With
    # --no-video an animation renders its first frame (png) alone: the mp4
    # is skipped and the viewers reaped right after that frame.
    animated = card.get("time") is None and not no_video
    stem = _profile_stem(json_path)
    out_path = _card_out_path(out_base, json_path, "mp4" if animated else "png", stem)
    source_hash = _profile_source_hash(json_path)
    if not force:
        up_to_date = out_path.is_file() and _stored_hash(out_path) == source_hash
        if up_to_date and animated:
            # The animation's first frame is kept alongside it; a missing or
            # stale copy forces the card to be re-rendered.
            first_frame_path = _card_out_path(out_base, json_path, "png", stem)
            up_to_date = (
                first_frame_path.is_file()
                and _stored_hash(first_frame_path) == source_hash
            )
        if up_to_date:
            # The definition and the mask are unchanged since the card was
            # written: skip the render.
            return out_path, True, None
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # The static layers (the fitted background, the dominant tint, the mask)
    # are prepared once, ahead of the render (a failure at any stage
    # re-renders from scratch, up to RENDER_ATTEMPTS times; the two viewer
    # framings stream directly, so nothing intermediate is written to disk in
    # between).
    base, tint, mask, tint_rgb = _profile_layers(background, size)
    for attempt in range(1, RENDER_ATTEMPTS + 1):
        try:
            finished, timings = _render_profile(
                json_path,
                size,
                animated,
                base,
                tint,
                mask,
                tint_rgb,
                logo,
                margin,
                padding,
                copyright_color,
                name,
                subtitle,
                manufacturer_logo,
                framerate,
                ffmpeg_threads,
                composite_workers,
                preset,
                scale,
                out_base,
                source_hash,
                PROFILE_FACE_ZOOM,
            )
            timings["total"] = time.perf_counter() - total_started
            return finished, False, timings
        except Exception as exc:
            if attempt >= RENDER_ATTEMPTS:
                raise GenerationError(
                    f"render of {json_path.name} ({stem}) still failing after "
                    f"{RENDER_ATTEMPTS} attempts: {exc}"
                ) from exc
            print(
                f"    ! {json_path.name} ({stem}): {exc}; re-rendering "
                f"(attempt {attempt}/{RENDER_ATTEMPTS})",
                flush=True,
            )
    raise AssertionError("unreachable")  # pragma: no cover


def _process_standard_card(
    json_path: Path,
    ffmpeg_threads: int = 1,
    composite_workers: int = 4,
    preset: str = DEFAULT_PRESET,
    scale: float = DEFAULT_SCALE,
    out_base: Path = OUTPUT_DIR,
    force: bool = False,
    no_video: bool = False,
) -> tuple[Path, bool, dict[str, float | None] | None]:
    """Render the ``<variant>Standard`` standard card for *json_path*
    (derived from its own definition — the ``Classic``, ``Rare``,
    ``Special`` and ``Exotic`` presentations): the definition's
    ``background`` (faded toward its dominant color, no monochrome) carries
    the standard card mask
    (:data:`STANDARD_MASK_PATH`), and the ``--half-body`` framing animates
    over it. The name and subtitle overlays are applied as usual, like the
    profile cards; the manufacturer's logo sits at the top right, its corner
    inset by ``padding * 1.5`` and drawn in black (the white face would hide
    the white version); the NIKKE logo sits at the bottom right and the
    copyright at the bottom left, both in black.

    With *no_video* (``--no-video``) an animated standard card renders its
    first frame alone — its MP4 is skipped and the viewer reaped right
    after that frame — so the output, and the up-to-date check, cover the
    first-frame PNG.

    Everything is composited in memory — the viewer's raw frames stream
    straight into the pipeline and nothing intermediate touches the disk
    (only the finished card is written). Returns ``(out_path, skipped,
    timings)`` like :func:`_process_card` (written out as
    ``<card>_<stem>.<suffix>``).
    """
    total_started = time.perf_counter()
    json_path = json_path.resolve()
    card = _load_card(json_path)
    background = Image.open(_background_path(card, json_path)).convert("RGBA")

    # The standard presentation always carries the black logo and black
    # copyright — the standard card's white face would wash out the white
    # versions — while the name stays white, as the other rarities.
    logo_path = LOGO_PATHS[True]
    if not logo_path.is_file():
        raise GenerationError(f"logo not found: {logo_path}")
    logo = Image.open(logo_path).convert("RGBA")
    if not FONT.is_file():
        raise GenerationError(f"font not found: {FONT}")
    if not FONT_NAME.is_file():
        raise GenerationError(f"font not found: {FONT_NAME}")
    # The standard presentation carries the card name, as the profile cards
    # do (a nameless definition renders without the name stack).
    name = str(card.get("title", ""))
    subtitle = str(card.get("subtitle", ""))
    # The character's manufacturer's logo (None when the character or its
    # manufacturer is unknown): it sits at the top right, its corner inset by
    # padding * 1.5, drawn in black.
    manufacturer_logo = _manufacturer_logo(str(card.get("id", "")))
    padding = card["padding"]
    margin = round(LOGO_PADDING_FACTOR * padding)
    copyright_color = (0, 0, 0, 255)
    framerate = card["framerate"] or DEFAULT_FRAMERATE

    viewport = card.get("viewport")
    if not viewport:
        raise GenerationError(
            f"{json_path.name}: missing 'viewport' (needed to size the raw "
            f"frames streamed by {VIEWER} --stdout)"
        )
    size = (int(viewport[0]), int(viewport[1]))

    # A definition without a `time` renders an animation (mp4) plus its first
    # frame (png); one with a `time` renders a single frame (png). With
    # --no-video an animation renders its first frame (png) alone: the mp4
    # is skipped and the viewer reaped right after that frame.
    animated = card.get("time") is None and not no_video
    stem = _standard_stem(json_path)
    out_path = _card_out_path(out_base, json_path, "mp4" if animated else "png", stem)
    source_hash = _standard_source_hash(json_path)
    if not force:
        up_to_date = out_path.is_file() and _stored_hash(out_path) == source_hash
        if up_to_date and animated:
            # The animation's first frame is kept alongside it; a missing or
            # stale copy forces the card to be re-rendered.
            first_frame_path = _card_out_path(out_base, json_path, "png", stem)
            up_to_date = (
                first_frame_path.is_file()
                and _stored_hash(first_frame_path) == source_hash
            )
        if up_to_date:
            # The definition and the mask are unchanged since the card was
            # written: skip the render.
            return out_path, True, None
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # The static base (the fitted background, faded toward its dominant
    # color, carrying the standard card mask) is prepared once, ahead of the
    # render (a failure at any stage re-renders from scratch, up to
    # RENDER_ATTEMPTS times; the viewer framing streams directly, so nothing
    # intermediate is written to disk in between). The subtitle rectangle's
    # tint is sampled from the unmasked fitted background, so the mask's
    # white does not wash the scene's color out.
    background = _fit_background(background, size)
    sub_rect_color = _rect_tint(background)

    background = ImageOps.autocontrast(
        background.convert("RGB"),
        cutoff=(20, 0),
        preserve_tone=True,
    ).convert("RGBA")
    brightness = ImageStat.Stat(background).mean[0]

    background = _fade_to_dominant(
        background,
        factor=min(4.0 * max(brightness - 80, 0) / 255, 1.0),
    )

    base = _standard_layers(background)

    for attempt in range(1, RENDER_ATTEMPTS + 1):
        try:
            finished, timings = _render_standard(
                json_path,
                size,
                animated,
                base,
                sub_rect_color,
                name,
                subtitle,
                manufacturer_logo,
                logo,
                margin,
                padding,
                copyright_color,
                framerate,
                ffmpeg_threads,
                composite_workers,
                preset,
                scale,
                out_base,
                source_hash,
            )
            timings["total"] = time.perf_counter() - total_started
            return finished, False, timings
        except Exception as exc:
            if attempt >= RENDER_ATTEMPTS:
                raise GenerationError(
                    f"render of {json_path.name} ({stem}) still failing after "
                    f"{RENDER_ATTEMPTS} attempts: {exc}"
                ) from exc
            print(
                f"    ! {json_path.name} ({stem}): {exc}; re-rendering "
                f"(attempt {attempt}/{RENDER_ATTEMPTS})",
                flush=True,
            )
    raise AssertionError("unreachable")  # pragma: no cover


def _find_pack_dirs() -> list[Path]:
    """``cards/`` subdirectories carrying an ``Expansion.json`` (the pack's
    inputs). The front and back are composed from the expansion on the fly
    (see :mod:`nikke_reborn.pack`), so neither is stored."""
    from nikke_reborn import expansion

    return sorted(
        pack_dir
        for pack_dir in CARDS_DIR.iterdir()
        if pack_dir.is_dir() and (pack_dir / expansion.EXPANSION_NAME).is_file()
    )


def _pack_hash(
    template: Path,
    front_source: str = "",
    back_source: str = "",
) -> str:
    """The source hash of a finished pack image: the SHA-256 of its
    template and — when *front_source* / *back_source* are given — those
    hashes of the composed front's and back's inputs (see
    :func:`pack.front_source_hash` / :func:`pack.back_source_hash` /
    :func:`box.front_source_hash`), every input the result depends on.
    Using the front's and back's *inputs* rather than their pixels lets the
    hash be computed without rendering them."""
    digest = hashlib.sha256()
    if not template.is_file():
        raise GenerationError(f"pack template not found: {template}")
    digest.update(template.read_bytes())
    if front_source:
        digest.update(front_source.encode())
    if back_source:
        digest.update(back_source.encode())
    return digest.hexdigest()


def _pack_output_up_to_date(
    template: Path,
    out_name: str,
    pack_dir: Path,
    out_base: Path,
    front_source: str = "",
    back_source: str = "",
    force: bool = False,
) -> bool:
    """True when the pack's finished *out_name* already exists and its stored
    hash matches the current inputs (the template and the front's and back's
    *sources*) — computed without rendering the front or back, so their
    renders can be skipped when nothing has changed. Always False when
    *force* is set (everything is re-rendered)."""
    if force:
        return False
    pack_dir = pack_dir.resolve()
    out_path = out_base / pack_dir.relative_to(CARDS_DIR) / out_name
    source_hash = _pack_hash(
        template, front_source=front_source, back_source=back_source
    )
    return out_path.is_file() and _stored_hash(out_path) == source_hash


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


def _process_pack_material(
    pack_dir: Path,
    out_base: Path,
    front: Image.Image,
    front_source: str,
    back: Image.Image,
    back_source: str,
    force: bool = False,
) -> tuple[Path, bool]:
    """Composite a pack's images onto the material template.

    The template's pure-blue mask rectangles mark the paste regions: the
    left one holds the pack's back and the right one its front — both
    in-memory images composed on the fly (the front with its white logo,
    placed by :func:`pack.place_logo`) and never stored. The finished
    material is written to ``<out>/<pack>/CardPack_Material.png``
    (atomically, with the SHA-256 of the template and the back's and
    front's inputs embedded, like a finished card); returns
    ``(out_path, skipped)``, where *skipped* is True when the output
    already exists and its stored hash matches the current inputs.
    """
    pack_dir = pack_dir.resolve()
    source_hash = _pack_hash(
        PACK_TEMPLATE, front_source=front_source, back_source=back_source
    )
    out_path = out_base / pack_dir.relative_to(CARDS_DIR) / PACK_MATERIAL_NAME
    if not force and out_path.is_file() and _stored_hash(out_path) == source_hash:
        return out_path, True
    with Image.open(PACK_TEMPLATE) as opened:
        template = opened.convert("RGBA")
        rects = _pack_mask_rects(_pack_mask(template))
        if len(rects) != 2:
            raise GenerationError(
                f"pack material template {PACK_TEMPLATE.name} carries "
                f"{len(rects)} pure-blue mask rectangle(s), expected 2 (back, front)"
            )
        # The back and front are the in-memory images (composed on the fly),
        # each already sized to its rectangle.
        back_target = (rects[0][2] - rects[0][0], rects[0][3] - rects[0][1])
        if back.size != back_target:
            back = back.resize(back_target, Image.Resampling.LANCZOS)
        template.alpha_composite(back, (rects[0][0], rects[0][1]))
        front_target = (rects[1][2] - rects[1][0], rects[1][3] - rects[1][1])
        if front.size != front_target:
            front = front.resize(front_target, Image.Resampling.LANCZOS)
        template.alpha_composite(front, (rects[1][0], rects[1][1]))
        final = template.convert("RGB")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _save_atomic(final, out_path, source_hash)
    return out_path, False


def _process_box_material(
    pack_dir: Path,
    out_base: Path,
    front: Image.Image,
    front_source: str,
    side: Image.Image,
    top: Image.Image,
    force: bool = False,
) -> tuple[Path, bool]:
    """Composite the box's front, side and top onto the box material
    template.

    The template's blue mask rectangle marks the front's paste region and
    its green mask rectangle the side's — the front is composed on the
    fly, with its white logo placed by :func:`box.place_logo`, and the
    side is the background's center slice with the expansion's logo
    center-center and the white logo bottom-center; the top (shared with
    the bottom) is the background center-cropped with the expansion's
    logo center-center and the white logo top-right. The finished
    material is
    written to
    ``<out>/<pack>/CardBox_Material.png`` (atomically, with the SHA-256 of
    the template and the front's inputs embedded, like a finished card —
    the side's and top's inputs are subsets of the front's); returns
    ``(out_path, skipped)``, where *skipped* is True when the output
    already exists and its stored hash matches the current inputs.
    """
    pack_dir = pack_dir.resolve()
    source_hash = _pack_hash(BOX_TEMPLATE, front_source=front_source)
    out_path = out_base / pack_dir.relative_to(CARDS_DIR) / BOX_MATERIAL_NAME
    if not force and out_path.is_file() and _stored_hash(out_path) == source_hash:
        return out_path, True
    with Image.open(BOX_TEMPLATE) as opened:
        template = opened.convert("RGBA")
        rects = _pack_mask_rects(_pack_mask(template))
        if len(rects) != 1:
            raise GenerationError(
                f"box material template {BOX_TEMPLATE.name} carries "
                f"{len(rects)} pure-blue mask rectangle(s), expected 1 (front)"
            )
        side_rects = _pack_mask_rects(_box_side_mask(template))
        if len(side_rects) != 1:
            raise GenerationError(
                f"box material template {BOX_TEMPLATE.name} carries "
                f"{len(side_rects)} pure-green mask rectangle(s), expected 1 (side)"
            )
        # Detected on the untouched template, like the blue and green ones:
        # the composed content may itself carry pure-red pixels.
        top_rects = _pack_mask_rects(_box_top_mask(template))
        if len(top_rects) != 1:
            raise GenerationError(
                f"box material template {BOX_TEMPLATE.name} carries "
                f"{len(top_rects)} pure-red mask rectangle(s), expected 1 (top)"
            )
        # The front and side are the in-memory images (composed on the
        # fly), each already sized to its rectangle.
        front_target = (rects[0][2] - rects[0][0], rects[0][3] - rects[0][1])
        if front.size != front_target:
            front = front.resize(front_target, Image.Resampling.LANCZOS)
        template.alpha_composite(front, (rects[0][0], rects[0][1]))
        side_rect = side_rects[0]
        side_target = (
            side_rect[2] - side_rect[0],
            side_rect[3] - side_rect[1],
        )
        if side.size != side_target:
            side = side.resize(side_target, Image.Resampling.LANCZOS)
        template.alpha_composite(side, (side_rect[0], side_rect[1]))
        top_rect = top_rects[0]
        top_target = (top_rect[2] - top_rect[0], top_rect[3] - top_rect[1])
        if top.size != top_target:
            top = top.resize(top_target, Image.Resampling.LANCZOS)
        template.alpha_composite(top, (top_rect[0], top_rect[1]))
        final = template.convert("RGB")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _save_atomic(final, out_path, source_hash)
    return out_path, False


def _viewer_hash(mesh: Path, material: Path, config: Path) -> str:
    """SHA-256 of the item's inputs: the pack's mesh, its generated
    material (whose bytes change whenever the material does), and the
    viewer configuration (model rotation and camera zoom/pan), so a
    finished item whose stored hash matches them is up to date."""
    digest = hashlib.sha256()
    for path in (mesh, material, config):
        if not path.is_file():
            raise GenerationError(f"item input not found: {path}")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _viewer_output_up_to_date(
    mesh: Path,
    material: Path,
    config: Path,
    out_path: Path,
    force: bool = False,
) -> bool:
    """True when the viewer's finished *out_path* already exists and its
    stored hash matches the current *mesh*, *material* and *config* —
    computed without rendering, so the render can be skipped when
    nothing has changed. A missing output or input (the material not
    generated yet) is simply not up to date. Always False when *force* is
    set (everything is re-rendered)."""
    if force:
        return False
    if not (
        mesh.is_file()
        and material.is_file()
        and config.is_file()
        and out_path.is_file()
    ):
        return False
    return _stored_hash(out_path) == _viewer_hash(mesh, material, config)


def _process_pack_item(
    pack_dir: Path, out_base: Path, force: bool = False
) -> tuple[Path, bool]:
    """Render a pack's item with :data:`UNITY_VIEWER`: the pack's mesh
    (:data:`PACK_MESH`) textured with the pack's finished material
    (``<out>/<pack>/CardPack_Material.png``), posed by the viewer
    configuration (:data:`PACK_CONFIG`): the model rotation and camera
    zoom/pan from that JSON file, the camera's fixed viewing pose and
    the viewer's default output size. The material must have been
    generated first — the item is rendered from its output file.

    The viewer writes a plain PNG, which is re-saved with the SHA-256 of
    the mesh and the material embedded (a PNG text chunk, like a finished
    card) and moved into place atomically, so a finished item only ever
    exists in its complete form; returns ``(out_path, skipped)``, where
    *skipped* is True when the output already exists and its stored hash
    matches the current inputs.
    """
    pack_dir = pack_dir.resolve()
    material_path = out_base / pack_dir.relative_to(CARDS_DIR) / PACK_MATERIAL_NAME
    source_hash = _viewer_hash(PACK_MESH, material_path, PACK_CONFIG)
    out_path = out_base / pack_dir.relative_to(CARDS_DIR) / PACK_ITEM_NAME
    if not force and out_path.is_file() and _stored_hash(out_path) == source_hash:
        return out_path, True
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(out_path.name + ".render")
    try:
        result = subprocess.run(
            [
                UNITY_VIEWER,
                str(PACK_MESH),
                str(material_path),
                "--config",
                str(PACK_CONFIG),
                "--out",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        tmp_path.unlink(missing_ok=True)
        raise GenerationError(f"could not run {UNITY_VIEWER}: {exc}") from exc
    if result.returncode != 0 or not tmp_path.is_file():
        detail = result.stderr.strip()
        detail = f" ({detail[-500:]})" if detail else ""
        tmp_path.unlink(missing_ok=True)
        raise GenerationError(
            f"{UNITY_VIEWER} failed (exit {result.returncode}){detail}"
        )
    with Image.open(tmp_path) as rendered:
        _save_atomic(rendered, out_path, source_hash)
    tmp_path.unlink(missing_ok=True)
    return out_path, False


def _process_box_item(
    pack_dir: Path, out_base: Path, force: bool = False
) -> tuple[Path, bool]:
    """Render the box's item with :data:`UNITY_VIEWER`: the box's mesh
    (:data:`BOX_MESH`) textured with the box's finished material
    (``<out>/<pack>/CardBox_Material.png``), posed by the box's viewer
    configuration (:data:`BOX_CONFIG`): the model rotation and camera
    zoom/pan from that JSON file, the camera's fixed viewing pose and
    the viewer's default output size. The material must have been
    generated first — the item is rendered from its output file.

    The viewer writes a plain PNG, which is re-saved with the SHA-256 of
    the mesh and the material embedded (a PNG text chunk, like a finished
    card) and moved into place atomically, so a finished item only ever
    exists in its complete form; returns ``(out_path, skipped)``, where
    *skipped* is True when the output already exists and its stored hash
    matches the current inputs.
    """
    pack_dir = pack_dir.resolve()
    material_path = out_base / pack_dir.relative_to(CARDS_DIR) / BOX_MATERIAL_NAME
    source_hash = _viewer_hash(BOX_MESH, material_path, BOX_CONFIG)
    out_path = out_base / pack_dir.relative_to(CARDS_DIR) / BOX_ITEM_NAME
    if not force and out_path.is_file() and _stored_hash(out_path) == source_hash:
        return out_path, True
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(out_path.name + ".render")
    try:
        result = subprocess.run(
            [
                UNITY_VIEWER,
                str(BOX_MESH),
                str(material_path),
                "--config",
                str(BOX_CONFIG),
                "--out",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        tmp_path.unlink(missing_ok=True)
        raise GenerationError(f"could not run {UNITY_VIEWER}: {exc}") from exc
    if result.returncode != 0 or not tmp_path.is_file():
        detail = result.stderr.strip()
        detail = f" ({detail[-500:]})" if detail else ""
        tmp_path.unlink(missing_ok=True)
        raise GenerationError(
            f"{UNITY_VIEWER} failed (exit {result.returncode}){detail}"
        )
    with Image.open(tmp_path) as rendered:
        _save_atomic(rendered, out_path, source_hash)
    tmp_path.unlink(missing_ok=True)
    return out_path, False


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
    from nikke_reborn import box, expansion, pack

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
        material_ok = _pack_output_up_to_date(
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
        box_ok = _pack_output_up_to_date(
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
