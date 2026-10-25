"""Render and composite Nikke trading cards.

Walks :mod:`cards` for card definitions (``*.json``), renders each one with
the ``nikke-viewer`` executable, composites every rendered frame on top of
the card's ``background``, stamps the matching logo from ``images/`` at
the bottom right and the copyright line at the bottom left, and overlays
the card name on top of the art, per frame: the title (uppercase, in a
dark rectangle at three-quarters of the height, with a small slanted bar
and three slanted squares of the same fill above it) and the subtitle
above the title (uppercase, in a background-tinted rectangle). The
``Goddess`` and ``Classified`` variants are generated without any card
name. Packs (``cards/`` subdirectories carrying an
``Expansion.json``) additionally get their two artwork images, built from
the templates in ``images/``. The pack's front and back are composed on the
fly (by :mod:`nikke_reborn.pack`) from the expansion's metadata — the front
is its ``background`` with its featured NIKKES (``pack``) drawn over it and
its ``logo`` when the expansion names one; the back is the same
``background`` resized and left-cropped — and neither is stored. The
material (``CardPack_Material.png``) has two pure-blue mask rectangles
holding the composed back (left) and front (right); the item
(``CardPack_Item.png``) is the pack's mesh
(``assets/CardPackStatic_Mesh.obj``) textured with the finished
material and rendered by the ``unity-viewer`` executable with the
model rotation and camera zoom/pan from
``assets/CardPackStatic_Mesh.json`` — so it is generated after the
material, which it reads from disk. The box (``CardBox_Material.png``)
holds the same composed front in the blue rectangle of its three mask
rectangles (blue front, red top, green side), the top (a center-cropped
background with the expansion's logo and the white NIKKE logo) in the red
one and the side (the background with the expansion's logo and the white
NIKKE logo) in the green one; the box's item (``CardBox_Item.png``) is the
box's mesh (``assets/CardBox_Mesh.obj``) textured with the finished
material and rendered by the ``unity-viewer`` executable with the model
rotation and camera zoom/pan from ``assets/CardBox_Mesh.json``, so it is
generated after the box's material, which it reads from disk. The finished results are
written under ``output/``, with
the SHA-256 of their inputs embedded as metadata (a PNG text chunk, an
MP4 tag); a result whose stored hash matches the current inputs is
skipped instead of re-rendered.

* single-frame cards -> ``output/<set>/<card>_<variant>.png``
* animated cards     -> ``output/<set>/<card>_<variant>.mp4`` alongside
                       its first frame, ``output/<set>/<card>_<variant>.png``

(the card's directory is folded into the filename, so a set's cards
sit flat in ``output/<set>/``)

``--draft`` runs the same pipeline for quick iteration: ultrafast x264
preset, half-resolution MP4s (downscaled inside ffmpeg), and results
written to ``draft/`` instead of ``output/`` so draft runs never clobber
the final cards.

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

By default every ``*.json`` under ``cards/`` is generated; one or more card
paths (a set, a card, or a definition file, relative to the repo root or to
``cards/``) may be passed on the command line to generate only the selected
definitions — the profile and the standard presentations alike.
"""

from __future__ import annotations

import argparse
import colorsys
import hashlib
import io
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import threading
import time
import pathlib
from collections import deque
from collections.abc import Generator, Iterator
from concurrent.futures import (
    Future,
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from pathlib import Path
from typing import IO, cast
from nikke_reborn import bundler, metadata

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat
from PIL.PngImagePlugin import PngInfo

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
CARDS_DIR = REPO_ROOT / "cards"
IMAGES_DIR = REPO_ROOT / "images"
FONTS_DIR = REPO_ROOT / "fonts"
OUTPUT_DIR = REPO_ROOT / "output"
DRAFT_DIR = REPO_ROOT / "draft"
BUNDLES_DIR = REPO_ROOT / "bundles"
DATABASE_DIR = REPO_ROOT / "database"
SHOP_DIR = IMAGES_DIR / "shop"

VIEWER = "nikke-viewer"
UNITY_VIEWER = "unity-viewer"
ENCODER = "ffmpeg"
PROBER = "ffprobe"

#: Wide pipe buffer for the frame streams: the default 8 KiB buffer turns a
#: 13 MiB frame into ~1700 syscalls; 1 MiB reads at the kernel's pipe
#: quantum (~64 KiB), ~200.
PIPE_BUFSIZE = 1 << 20

#: Key of the embedded definition hash in the finished cards (a PNG
#: text chunk, an MP4 tag): a card whose stored hash matches the
#: current definition is skipped instead of re-rendered.
SOURCE_HASH_KEY = "nikke-reborn-source"

DEFAULT_FRAMERATE = 60

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
# right. Everything is composited in memory — no intermediate frame touches
# the disk; only the finished card is written (atomically).
#: Profile rarity stems that skip the standard pipeline entirely: only
#: their profile cards are rendered. Currently empty — every rarity
#: (including ``Aim`` and ``Cover``) also renders its standard card.
PROFILE_RARITIES = frozenset({})
#: Variant stems with no derived ``<variant>Profile`` card: the
#: ``Goddess`` and ``Classified`` presentations.
NO_PROFILE_STEMS = frozenset({"Goddess", "Classified"})
#: The profile card's mask (tinted with the background's dominant tint at
#: each pixel's own lightness, the white staying white; composited over
#: the diluted background, under the character), next to its GIMP source.
PROFILE_MASK_PATH = IMAGES_DIR / "designs" / "Card_Mask.png"
#: Opacity of the dominant-tint wash's top edge: laid over the monochrome
#: background and the face framing: the partial wash dilutes the
#: background toward its own main color and gently re-tints the face so
#: it settles into the card's palette.
PROFILE_TINT_TOP_OPACITY = 0.5
#: Opacity of the dominant-tint wash's bottom edge: the alpha ramps
#: linearly from PROFILE_TINT_TOP_OPACITY to this, so the darker bottom
#: anchors more firmly than the top.
PROFILE_TINT_BOTTOM_OPACITY = 1.0
#: The wash's bottom color is the background's tint scaled by this factor
#: (as a fraction of its brightness) in linear light — the channels are
#: linearized before scaling, so the tint keeps its hue instead of
#: shifting toward black — and the top edge is the tint itself: the wash
#: darkens linearly toward the bottom, its gradient ending at
#: PROFILE_TINT_GRADIENT_END of the height.
PROFILE_TINT_BOTTOM_FACTOR = 0.3
#: The point, as a fraction of the card's height, at which the
#: wash's gradient between the tint and its bottom color completes: the
#: bottom strip below it holds the bottom color (and the bottom opacity)
#: flat.
PROFILE_TINT_GRADIENT_END = 0.85
#: The ``--face`` zoom that renders the face framing composited over the
#: profile card's background, under its tint wash (ahead of the full body).
PROFILE_FACE_ZOOM = 2
#: The face framing's vertical centre, as a fraction of the frame height
#: (0.1). :func:`_face_offset` treats the face as a square of side
#: ``height * PROFILE_FACE_CENTER_Y * PROFILE_FACE_ZOOM`` centred at that height
#: when deciding which side leaves its footprint least occluded by the body.
PROFILE_FACE_CENTER_Y = 0.1
#: Brightness scale applied to the monochrome face (its value channel): 1.0
#: keeps the face's own brightness; below 1.0 darkens it so it sits quieter
#: against the tinted background.
PROFILE_FACE_BRIGHTNESS = 0.5
#: Horizontal shifts (px) that move the face framing aside from the centered
#: full body so it is not occluded by the body: the face is rendered
#: :data:`PROFILE_FACE_OFFSET_LEFT` px to the left or
#: :data:`PROFILE_FACE_OFFSET_RIGHT` px to the right (whichever leaves its
#: footprint least occluded by the body, see :func:`_face_offset`).
PROFILE_FACE_OFFSET_LEFT = 500
PROFILE_FACE_OFFSET_RIGHT = 420

#: ``nikke-viewer`` writes its frames from multiple threads and can
#: occasionally leave a truncated file behind while still exiting with
#: status 0; a card whose render cannot be processed is re-run up to this
#: many times before giving up.
RENDER_ATTEMPTS = 3

#: The logo sits this many times the card ``padding`` away from the corner.
LOGO_PADDING_FACTOR = 1.5

#: Reference card width (pixels): the nominal sizes below are expressed at
#: this width and scale proportionally for other viewport widths.
CARD_REFERENCE_WIDTH = 1640

#: Nominal logo width (pixels) at the reference card width: the logo is
#: scaled proportionally, preserving its aspect ratio (200 px wide on the
#: 1640 px cards we have).
LOGO_NOMINAL_WIDTH = 200

#: Nominal copyright text size (pixels) at the reference card width.
COPYRIGHT_NOMINAL_SIZE = 20
#: Oswald weight for the copyright line (variable axis 200-700; a light
#: weight reads quieter at this small size)
COPYRIGHT_WEIGHT = 300
#: The copyright is stamped at this multiple of its size and downscaled:
#: at the final size FreeType quantizes glyph advances unevenly (the
#: word spaces come out different widths), and the LANCZOS downscale
#: re-smooths them
COPYRIGHT_SUPERSAMPLE = 4

#: Copyright line rendered at the bottom left of the card.
COPYRIGHT_TEXT = "©PROXIMA BETA PTE. LTD. ©SHIFT UP CORP."

#: Oswald face for the copyright line (vendored variable font, SIL OFL).
FONT = FONTS_DIR / "Oswald.ttf"

#: Aire Exterior face for the card name (vendored static font, SIL OFL).
FONT_NAME = FONTS_DIR / "AireExterior.ttf"

#: ChocolateClassicalSans face for the title rectangle's arrow (vendored).
FONT_RECT_ARROW = FONTS_DIR / "ChocolateClassicalSans-Regular.ttf"

#: Card name placement: the ink's top-left corner sits at the card's padding
#: from the left edge and NAME_TITLE_Y of the height, left-aligned, with font
#: size padding * NAME_SIZE_FACTOR and, on variable fonts, weight
#: NAME_WEIGHT (700 = bold; static fonts have a fixed weight).
NAME_SIZE_FACTOR = 3.0
NAME_WEIGHT = 700

#: The title's vertical position, as a fraction of the card height: the
#: title's ink top sits at NAME_TITLE_Y of the height (its left inset is the
#: card's own padding).
NAME_TITLE_Y = 0.72

#: Names of NAME_REFERENCE_LENGTH characters or fewer get the full font
#: size; longer names are scaled down by NAME_REFERENCE_LENGTH / length
#: (truncated to the pixel), never below NAME_MIN_SIZE_FACTOR of the
#: base size.
NAME_REFERENCE_LENGTH = 17

#: Shrink floor: the font never drops below this fraction of its base
#: (NAME_SIZE_FACTOR) size.
NAME_MIN_SIZE_FACTOR = 0.6

#: Subtitle sizing: the font is padding * SUBTITLE_SIZE_FACTOR (short
#: subtitles), shrinking linearly to padding * SUBTITLE_MIN_SIZE_FACTOR
#: between SUBTITLE_FULL_LENGTH and SUBTITLE_FLOOR_LENGTH characters.
SUBTITLE_SIZE_FACTOR = 1.0
SUBTITLE_MIN_SIZE_FACTOR = 0.60
SUBTITLE_FULL_LENGTH = 18
SUBTITLE_FLOOR_LENGTH = 30

#: Base color of the name text (title and subtitle).
NAME_TEXT_COLOR = (255, 255, 255)

#: Fill of the title's enclosing rectangle: a flat dark gray. The
#: rectangle's left edge is the card's left edge and the ink sits inside
#: with NAME_RECT_PAD of room on the other three sides.
NAME_RECT_COLOR = (0x33, 0x33, 0x33)
#: Luminance (0..1) of the subtitle's enclosing rectangle's fill: the fill
#: takes the background's dominant hue at this dark level, so the
#: subtitle's panel picks up the scene's tint where the title's is a flat
#: NAME_RECT_COLOR.
NAME_RECT_LUMA = 0.3
#: Padding around the title's ink (top/right/bottom of its enclosing
#: rectangle), as a fraction of the ink's height.
NAME_RECT_PAD = 0.2
#: Padding around the subtitle's ink (top/bottom, and the right before
#: NAME_SUB_RECT_RIGHT_PAD_EXTRA), as a fraction of the ink's height:
#: roomier than the title's NAME_RECT_PAD, so the smaller bar does not
#: hug the text.
NAME_SUB_RECT_PAD = 0.4
#: Extra right-side room in the subtitle's enclosing rectangle, on top of
#: NAME_SUB_RECT_PAD (as a fraction of the subtitle ink's height): the
#: text's right edge gets a wider margin than the top/bottom.
NAME_SUB_RECT_RIGHT_PAD_EXTRA = 1.0

#: The title rectangle's top-right corner is cut off by a 45-degree diagonal
#: spanning NAME_RECT_CORNER of the rectangle's height (the diagonal is the
#: diagonal of a square with that side length).
NAME_RECT_CORNER = 1 / 3

#: The arrow (NAME_RECT_ARROW) sits in the rectangle's right padding, its
#: ink's bottom-right aligned NAME_RECT_ARROW_MARGIN from the rectangle's
#: right/bottom edges (each a fraction of the rectangle's height); the font
#: size is NAME_RECT_ARROW_SIZE of the rectangle's height.
NAME_RECT_ARROW = "\u2196"
NAME_RECT_ARROW_SIZE = 0.4
NAME_RECT_ARROW_MARGIN = 0.12

#: The manufacturer's logo above the title's bar: its width as a fraction
#: of the frame's width (its height proportional), its left edge at the
#: card's padding (the title's own inset), a gap of padding / 2 between
#: its bottom and the bar's top.
MANUFACTURER_LOGO_WIDTH = 0.11

# --- name stack effects -------------------------------------------------
# Context sampling for the subtitle rectangle's tint (the background's
# dominant hue at NAME_RECT_LUMA, via _sample_context).
NAME_SAMPLE_PX = 24  # sample resolution
CONTEXT_FALLBACK = (170, 235, 255)  # hue/sat source for (near)-gray art
CONTEXT_MIN_QUALIFY = 0.25  # min fraction of sample pixels that are colored
CONTEXT_SAT_BOOST = 1.4  # the sampled saturation is boosted...
CONTEXT_SAT_MIN = 0.45  # ...and clamped, so the tint stays visible...
CONTEXT_SAT_MAX = 0.90  # ...without washing out

#: H.264 quality settings for the MP4 output: visually lossless CRF,
#: yuv420p for compatibility and fast-start for streaming. The x264 preset
#: and the resolution scale are chosen per run: ``slow`` at full
#: resolution by default, ``ultrafast`` at half resolution for drafts
#: (``--draft``).
FFMPEG_QUALITY_ARGS = (
    "-crf",
    "16",
    "-pix_fmt",
    "yuv420p",
    "-movflags",
    "+faststart",
)

DEFAULT_PRESET = "slow"
DRAFT_PRESET = "ultrafast"
DEFAULT_SCALE = 1.0
DRAFT_SCALE = 0.5

#: ffmpeg encodes and frame compositing get at most this many threads
#: each, even when a single card uses all the cores.
MAX_STAGE_THREADS = 16

LOGO_PATHS = {
    False: IMAGES_DIR / "Logo_White.png",
    True: IMAGES_DIR / "Logo_Black.png",
}

#: Pack artwork: ``images/`` holds the material template, whose two
#: pure-blue mask rectangles hold the pack's back (left) and front
#: (right) — both composed on the fly (see :mod:`nikke_reborn.pack`) —
#: written to ``<out>/<pack>/CardPack_Material.png``. The item
#: (``CardPack_Item.png``) is rendered with :data:`UNITY_VIEWER` from
#: :data:`PACK_MESH` textured with the finished material.
PACK_TEMPLATE = IMAGES_DIR / "CardPack_Material.png"
PACK_MATERIAL_NAME = "CardPack_Material.png"
PACK_ITEM_NAME = "CardPack_Item.png"
PACK_MESH = REPO_ROOT / "assets" / "CardPackStatic_Mesh.obj"

#: The item's viewer configuration (model rotation and camera zoom/pan
#: as a JSON file, exported by the viewer's GUI), passed to
#: :data:`UNITY_VIEWER` with ``--config``; it sits next to the mesh.
PACK_CONFIG = REPO_ROOT / "assets" / "CardPackStatic_Mesh.json"


#: The box's material template: its three solid mask rectangles mark the
#: paste regions — blue for the front (the same composition as the pack's
#: front), red for the top and green for the side (see
#: :mod:`nikke_reborn.box`). The finished material is written to
#: ``<out>/<pack>/CardBox_Material.png``. The item
#: (``CardBox_Item.png``) is rendered with :data:`UNITY_VIEWER` from
#: :data:`BOX_MESH` textured with the finished material, the way the
#: pack's item is.
BOX_TEMPLATE = IMAGES_DIR / "CardBox_Material.png"
BOX_MATERIAL_NAME = "CardBox_Material.png"
BOX_ITEM_NAME = "CardBox_Item.png"
BOX_MESH = ASSETS_DIR / "CardBox_Mesh.obj"

#: The box item's viewer configuration (model rotation and camera
#: zoom/pan, as a JSON file exported by the viewer's GUI), passed to
#: :data:`UNITY_VIEWER` with ``--config``; it sits next to the mesh.
BOX_CONFIG = ASSETS_DIR / "CardBox_Mesh.json"


class GenerationError(RuntimeError):
    """A card definition could not be rendered or composed."""


def generate() -> None:
    """Render and composite the selected (or all) card definitions."""
    args = _parse_args()
    draft = args.draft
    out_dir = DRAFT_DIR if draft else OUTPUT_DIR
    preset = DRAFT_PRESET if draft else DEFAULT_PRESET
    scale = DRAFT_SCALE if draft else DEFAULT_SCALE
    try:
        selection = _selected_configs(args.paths)
        _generate_profiles(selection, args.jobs, preset, scale, out_dir)
        _generate_variants(selection, args.jobs, preset, scale, out_dir)
        _write_metadata(out_dir)
    except GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


def _write_metadata(out_dir: Path) -> None:
    """Write each set's metadata bundle (``<out>/<set>.json``) and copy the
    set's shared assets (foilmask, cardback, box mesh, shop images) to
    ``<out>/<set>/``."""
    characters = json.load((DATABASE_DIR / "characters.json").open())
    characters = {character["id"]: character for character in characters}

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

                if variant.stem not in PROFILE_RARITIES:
                    new_card = metadata.card(
                        name,
                        variant.stem,
                        rarity,
                        f"{card.stem}_{variant.stem}",
                    )
                    cards.append(new_card)

                if variant.stem not in NO_PROFILE_STEMS:
                    profile_stem = _profile_stem(variant)

                    new_card = metadata.card(
                        name,
                        profile_stem,
                        rarity,
                        f"{card.stem}_{profile_stem}",
                    )
                    cards.append(new_card)

        for missing in sorted(missing_ids):
            print(
                f"warning: no character {missing!r} in characters.json; "
                f"its cards default to rarity 'R'",
                file=sys.stderr,
            )

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

        bundle = BUNDLES_DIR / f"NIKKE - {target.name}"
        bundle.mkdir(parents=True)

        plugins = bundle / "BepInEx" / "plugins"

        for file in ["Shop_Icon.png", "Shop_IBG.png", "Shop_OBG.png"]:
            copy(
                SHOP_DIR / file,
                plugins / "Phone - Overhaul" / "App Images" / "NIKKE" / file,
            )

        prefab = plugins / "NIKKE" / f"{target.name}_prefabloader"
        plugin = prefab / f"NIKKE_{target.name}"
        animator = prefab / "VideoCardAnimator"

        if (CARDS_DIR / target.name).is_dir():
            videos = [
                file
                for file in (OUTPUT_DIR / target.name).iterdir()
                if file.name.endswith(".mp4")
            ]

            videos_dir = animator / f"NIKKE_{target.name}"

            if videos:
                videos_dir.mkdir(parents=True)

            for video in videos:
                copy(video, videos_dir / video.name)

        copy(target.with_suffix(".json"), plugin.with_suffix(".json"))
        bundler.build(target, plugin.name, plugin, OUTPUT_DIR)


def _require_executable(name: str) -> None:
    if shutil.which(name) is None:
        raise GenerationError(f"required executable not found in PATH: {name!r}")


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
    """The character's manufacturer logo: ``images/logos/<manufacturer>.png``
    (white on transparency, tinted to the bar's fill when placed) — None
    when the character has no manufacturer or its logo file is missing."""
    manufacturer = _character_manufacturer(card_id)
    if manufacturer is None:
        return None
    logo_path = IMAGES_DIR / "logos" / f"{manufacturer}.png"
    if not logo_path.is_file():
        return None
    return Image.open(logo_path).convert("RGBA")


def _read_exact(stream: IO[bytes], n: int) -> bytes:
    """Read exactly *n* bytes from *stream*; fewer only at end-of-stream.

    A buffered reader's ``read`` may return a partial chunk, so this loops until
    *n* bytes are gathered or the stream is exhausted. A raw frame is written
    whole by the viewer, so a full read is one call in practice — the loop
    just makes the frame boundary robust to partial reads.
    """
    chunks: list[bytes] = []
    remaining = n
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    if len(chunks) == 1:
        return chunks[0]  # a buffered read gathers the whole frame at once;
    return b"".join(chunks)  # joining would just copy it for no reason


class _PipeDrain:
    """Drain a pipe into a bounded in-memory buffer from a daemon thread.

    Keeps the writer from blocking on a full pipe (the viewer's stderr) while
    its stdout is streamed; only the tail is kept, for error reporting.
    """

    def __init__(self, stream: "io.BufferedReader", cap: int = 1 << 20) -> None:
        self._stream = stream
        self._cap = cap
        self._buf = bytearray()
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            while True:
                chunk = self._stream.read1(65536)
                if not chunk:
                    break
                with self._lock:
                    self._buf.extend(chunk)
                    if len(self._buf) > self._cap:
                        del self._buf[: len(self._buf) - self._cap]
        except (OSError, ValueError):
            pass

    def text(self) -> str:
        with self._lock:
            return bytes(self._buf).decode(errors="replace").strip()

    def join(self, timeout: float | None = None) -> None:
        self._thread.join(timeout)


def _reap_viewer(
    viewer: subprocess.Popen,
    drain: _PipeDrain,
    *,
    clean_exit_expected: bool,
) -> None:
    """Wait for *viewer* to exit, draining its stderr, and raise on failure.

    When the frame stream was fully read (``clean_exit_expected``) the viewer
    exits right after its last frame: a grace period is given before killing a
    hung process, and a non-zero exit is a :class:`GenerationError`. When the
    stream was abandoned early (the reader or the consumer errored), the viewer
    may be blocked writing to a full pipe and is killed; its exit code is not
    consulted (the caller already has the real exception).
    """
    if clean_exit_expected:
        try:
            viewer.wait(timeout=60)
        except subprocess.TimeoutExpired:
            viewer.kill()
            viewer.wait()
    else:
        if viewer.poll() is None:
            viewer.kill()
        viewer.wait()
    drain.join(timeout=5)
    if clean_exit_expected and viewer.returncode != 0:
        detail = drain.text()
        detail = f" ({detail[-500:]})" if detail else ""
        raise GenerationError(f"{VIEWER} failed (exit {viewer.returncode}){detail}")


def _stream_composited(
    viewer: subprocess.Popen,
    drain: _PipeDrain,
    json_path: Path,
    size: tuple[int, int],
    base: Image.Image,
    overlay: Image.Image,
    overlay_pos: tuple[int, int],
    composite_workers: int,
    first_frame: list[Image.Image],
    composite_time: list[float],
    stream_end: list[float],
) -> Generator[Image.Image]:
    """Composite the viewer's raw RGBA stdout frames and yield them in order.

    ``--stdout`` writes each frame as a contiguous ``width * height * 4`` byte
    block of raw RGBA, in presentation order. Frames are decoded and
    composited over *base*, then the *overlay* (the pre-stamped logo and
    copyright line) is stamped on top, in a sliding window of
    *composite_workers* threads — Pillow releases the GIL
    in its raster ops, so the reader stays ahead of the encode and the cores
    stay busy — and yielded in presentation order. At most ~2x the worker
    count of frames are in memory at once. The first composited frame is
    appended to *first_frame*. When the stream ends (or the consumer stops),
    the viewer is reaped and a non-zero exit surfaced. The wall seconds of
    composite work (summed across the worker threads) accumulate in
    *composite_time*, and the moment the stream reaches end-of-file is
    recorded in *stream_end*.
    """
    width, height = size
    frame_bytes = width * height * 4
    assert viewer.stdout is not None
    stdout = viewer.stdout
    # A fully opaque base lets the per-frame blend take the GIL-releasing
    # Image.composite path (see _composite_frame); the base's alpha band is
    # restored onto the result so the downstream stamps (logo, copyright)
    # composite against the same alpha as the alpha_composite path.
    # Computed once per card (None when the base is not fully opaque).
    base_alpha = base.getchannel("A")
    if base_alpha.getextrema() != (255, 255):
        base_alpha = None

    def composite(data: bytes) -> Image.Image:
        started = time.perf_counter()
        frame = Image.frombytes("RGBA", (width, height), data)
        art = _composite_frame(frame, base, base_alpha)
        art.alpha_composite(overlay, overlay_pos)
        with time_lock:
            composite_time[0] += time.perf_counter() - started
        return art

    time_lock = threading.Lock()
    workers = max(1, composite_workers)
    eof = False
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            pending: deque[Future[Image.Image]] = deque()
            yielded = 0

            def submit_next() -> None:
                nonlocal eof
                data = _read_exact(stdout, frame_bytes)
                if not data:
                    eof = True  # end of stream
                    stream_end[0] = time.perf_counter()
                    return
                if len(data) != frame_bytes:
                    raise GenerationError(
                        f"{VIEWER} stream for {json_path.name} truncated: "
                        f"{len(data)} of {frame_bytes} bytes"
                    )
                pending.append(pool.submit(composite, data))

            # Prime the window.
            for _ in range(workers):
                submit_next()

            while pending:
                future = pending.popleft()
                try:
                    frame = future.result()
                except Exception:
                    for pending_future in pending:
                        pending_future.cancel()
                    raise
                if yielded == 0:
                    # Keep the first composited frame: for animations it is
                    # written alongside the mp4, for a static card it is the
                    # card itself.
                    first_frame.append(frame)
                yielded += 1
                # Keep the window full (read ahead) before handing off.
                submit_next()
                yield frame

        if yielded == 0:
            raise GenerationError(f"{VIEWER} produced no frames for {json_path.name}")
    finally:
        _reap_viewer(viewer, drain, clean_exit_expected=eof)


def _stream_dual_composited(
    face_viewer: subprocess.Popen,
    face_drain: _PipeDrain,
    body_viewer: subprocess.Popen,
    body_drain: _PipeDrain,
    json_path: Path,
    size: tuple[int, int],
    background: Image.Image,
    tint: Image.Image,
    mask: Image.Image,
    overlay: Image.Image,
    overlay_pos: tuple[int, int],
    parts: _NameLayers | None,
    composite_workers: int,
    first_frame: list[Image.Image],
    composite_time: list[float],
    stream_end: list[float],
) -> Generator[Image.Image]:
    """Composite the two synchronized viewer streams and yield the frames in
    presentation order — the profile card, where the ``--face`` framing
    animates (as a monochrome of the tint's hue) over the background, under
    the tint wash, and the ``--full-body`` framing animates over the mask.

    Both streams come from the same definition at the same framerate, so frame
    *i* of the face stream pairs with frame *i* of the body stream and they
    are read in lockstep. Per frame the face — collapsed to a monochrome of
    the background's dominant tint (:func:`_monochrome`) — is composited over
    *background*, the dominant *tint* wash is laid over both, then the
    *mask* and the body frame, then the *overlay* and the name stack (if
    any), in a sliding window
    of *composite_workers* threads — as in :func:`_stream_composited` — and
    yielded in order. The first composited
    frame is appended to *first_frame*. When both streams reach end-of-file (or
    the consumer stops) the two viewers are reaped and a non-zero exit
    surfaced; *composite_time* and *stream_end* accumulate the composite wall
    seconds and the moment the streams reach EOF.
    """
    width, height = size
    frame_bytes = width * height * 4
    assert face_viewer.stdout is not None
    assert body_viewer.stdout is not None
    face_stdout = face_viewer.stdout
    body_stdout = body_viewer.stdout
    # The tint layer's top row is the background's dominant tint (the
    # gradient darkens toward the bottom); reuse it to key the face's
    # monochrome recolor (the vivid full-color face is collapsed to
    # single-hue shades of the tint so it blends into the card's palette).
    tint_pixel = tint.getpixel((0, 0))
    assert isinstance(tint_pixel, tuple)
    tint_rgb = (tint_pixel[0], tint_pixel[1], tint_pixel[2])
    # The background is a fully opaque card, so the per-frame blends take
    # the GIL-releasing Image.composite path (see _composite_frame): its
    # RGB is bit-identical to the alpha_composite chain, but its alpha
    # band is not, so the background's alpha is restored onto the result
    # before the stamps (logo, copyright, name) — the finished card is
    # byte-identical to the alpha_composite chain. The constant layers'
    # alpha channels are the blend masks, computed once.
    background_alpha = background.getchannel("A")
    base_opaque = background_alpha.getextrema() == (255, 255)
    tint_alpha = tint.getchannel("A")
    mask_alpha = mask.getchannel("A")

    def composite(face_data: bytes, body_data: bytes) -> Image.Image:
        started = time.perf_counter()
        face = _monochrome(
            Image.frombytes("RGBA", (width, height), face_data),
            tint_rgb,
            PROFILE_FACE_BRIGHTNESS,
        )
        body = Image.frombytes("RGBA", (width, height), body_data)
        # The face over the raw background, then the single dominant-tint
        # wash over both, then the mask and the body frame.
        if base_opaque:
            art = Image.composite(face, background, face.getchannel("A"))
            art = Image.composite(tint, art, tint_alpha)
            art = Image.composite(mask, art, mask_alpha)
            art = Image.composite(body, art, body.getchannel("A"))
            art.putalpha(background_alpha)
        else:
            art = background.copy()
            art.alpha_composite(face)
            art.alpha_composite(tint)
            art.alpha_composite(mask)
            art.alpha_composite(body)
        art.alpha_composite(overlay, overlay_pos)
        result = _apply_name(art, parts) if parts is not None else art
        with time_lock:
            composite_time[0] += time.perf_counter() - started
        return result

    time_lock = threading.Lock()
    workers = max(1, composite_workers)
    face_eof = False
    body_eof = False
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            pending: deque[Future[Image.Image]] = deque()
            yielded = 0

            def submit_next() -> None:
                nonlocal face_eof, body_eof
                if face_eof or body_eof:
                    return
                face_data = _read_exact(face_stdout, frame_bytes)
                if not face_data:
                    face_eof = True  # end of the face stream
                    stream_end[0] = time.perf_counter()
                    return
                if len(face_data) != frame_bytes:
                    raise GenerationError(
                        f"{VIEWER} face stream for {json_path.name} truncated: "
                        f"{len(face_data)} of {frame_bytes} bytes"
                    )
                body_data = _read_exact(body_stdout, frame_bytes)
                if not body_data:
                    body_eof = True  # end of the body stream
                    stream_end[0] = time.perf_counter()
                    return
                if len(body_data) != frame_bytes:
                    raise GenerationError(
                        f"{VIEWER} body stream for {json_path.name} truncated: "
                        f"{len(body_data)} of {frame_bytes} bytes"
                    )
                pending.append(pool.submit(composite, face_data, body_data))

            # Prime the window.
            for _ in range(workers):
                submit_next()

            while pending:
                future = pending.popleft()
                try:
                    frame = future.result()
                except Exception:
                    for pending_future in pending:
                        pending_future.cancel()
                    raise
                if yielded == 0:
                    # Keep the first composited frame: for animations it is
                    # written alongside the mp4, for a static card it is the
                    # card itself.
                    first_frame.append(frame)
                yielded += 1
                # Keep the window full (read ahead) before handing off.
                submit_next()
                yield frame

        if yielded == 0:
            raise GenerationError(f"{VIEWER} produced no frames for {json_path.name}")
    finally:
        # A stream is "clean" only if it was read to end-of-file; one that was
        # abandoned early (the consumer stopped or an error aborted the window)
        # may be blocked writing to a full pipe and is killed instead.
        _reap_viewer(face_viewer, face_drain, clean_exit_expected=face_eof)
        _reap_viewer(body_viewer, body_drain, clean_exit_expected=body_eof)


def _fit_background(background: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Fit *background* to *size* (cover) and center-crop it."""
    width, height = size
    scale = max(width / background.width, height / background.height)
    if scale != 1.0:
        background = background.resize(
            (round(background.width * scale), round(background.height * scale)),
            Image.Resampling.LANCZOS,
        )
    left = (background.width - width) // 2
    top = (background.height - height) // 2
    return background.crop((left, top, left + width, top + height)).convert("RGBA")


def _dominant_color(image: Image.Image) -> tuple[int, int, int]:
    """The main color tint of *image*: its mean RGB, sampled on a small
    downscale so a busy background still yields a stable representative
    tint."""
    small = image.convert("RGB").resize((32, 32))
    means = ImageStat.Stat(small).mean
    return (round(means[0]), round(means[1]), round(means[2]))


#: Per-channel value -> RGB lookup tables for :func:`_monochrome`, keyed by
#: (tint, brightness) — built once per card, not once per frame.
_MONOCHROME_LUTS: dict[
    tuple[tuple[int, int, int], float], tuple[bytes, bytes, bytes]
] = {}


def _monochrome_luts(
    tint_rgb: tuple[int, int, int], brightness: float
) -> tuple[bytes, bytes, bytes]:
    """The 256-entry per-channel tables mapping a value (V) channel to the
    RGB of the *tint*'s fixed (H, S) at that value, built through the same
    HSV -> RGB conversion a full-frame image would run (a 256-wide ramp
    image), so each lookup is pixel-identical to the per-pixel result.
    *brightness* is folded into the tables (the value is scaled before the
    RGB conversion, as before)."""
    key = (tint_rgb, brightness)
    luts = _MONOCHROME_LUTS.get(key)
    if luts is None:
        pixel = Image.new("RGB", (1, 1), tint_rgb).convert("HSV").getpixel((0, 0))
        assert isinstance(pixel, tuple)
        h, s, _ = pixel[0], pixel[1], pixel[2]
        hue = Image.new("L", (256, 1), h)
        sat = Image.new("L", (256, 1), s)
        value = Image.new("L", (256, 1))
        value.putdata(range(256))
        table = Image.merge("HSV", (hue, sat, value)).convert("RGB").split()
        r_raw, g_raw, b_raw = (channel.tobytes() for channel in table)
        if brightness != 1.0:
            luts = (
                bytes(r_raw[round(v * brightness)] for v in range(256)),
                bytes(g_raw[round(v * brightness)] for v in range(256)),
                bytes(b_raw[round(v * brightness)] for v in range(256)),
            )
        else:
            luts = (r_raw, g_raw, b_raw)
        _MONOCHROME_LUTS[key] = luts
    return luts


def _monochrome(
    image: Image.Image,
    tint_rgb: tuple[int, int, int],
    brightness: float = 1.0,
) -> Image.Image:
    """Collapse the full-color *image* (RGBA) to a single hue — the
    *tint*'s — while keeping the image's own brightness. Every pixel takes
    the *tint*'s hue and saturation; only its value (brightness) channel
    survives, so the shading and contrast remain but the vivid colors do
    not. The image thus reads as a monochrome of the tint and blends into
    the card's palette instead of standing out from it. *brightness* scales
    that value channel (1.0 keeps it; below 1.0 darkens). The alpha channel
    is passed through untouched.

    The value channel is max(R, G, B) — the value of the HSV conversion —
    and the recolor at the fixed (H, S) is a per-channel lookup
    (:func:`_monochrome_luts`), so no full-frame HSV round trip is needed."""
    lut_r, lut_g, lut_b = _monochrome_luts(tint_rgb, brightness)
    r, g, b, a = image.split()
    value = ImageChops.lighter(ImageChops.lighter(r, g), b)
    result = Image.merge(
        "RGB", (value.point(lut_r), value.point(lut_g), value.point(lut_b))
    )
    result.putalpha(a)
    return result


def _scale_linear_light(
    rgb: tuple[int, int, int], factor: float
) -> tuple[int, int, int]:
    """*rgb* scaled by *factor* in linear light: the channels are
    linearized (the sRGB gamma undone), scaled, and re-encoded, so the
    colour keeps its hue — its chromaticity is unchanged — instead of
    shifting toward black, as a direct sRGB scaling would."""

    def scale(value: int) -> int:
        v = value / 255
        v = v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        v *= factor
        v = v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
        return round(max(0.0, min(1.0, v)) * 255)

    return (scale(rgb[0]), scale(rgb[1]), scale(rgb[2]))


def _tint_wash(size: tuple[int, int], tint_rgb: tuple[int, int, int]) -> Image.Image:
    """The profile card's wash layer (built once, static): a vertical
    linear gradient from *tint_rgb* at the top edge to the tint scaled by
    :data:`PROFILE_TINT_BOTTOM_FACTOR` in linear light (so its hue is
    preserved), completing at :data:`PROFILE_TINT_GRADIENT_END` of the
    height — the bottom strip below it holds the bottom color and the
    bottom opacity — with the alpha ramping from
    :data:`PROFILE_TINT_TOP_OPACITY` to :data:`PROFILE_TINT_BOTTOM_OPACITY`
    along the same ramp."""
    width, height = size
    bottom = _scale_linear_light(tint_rgb, PROFILE_TINT_BOTTOM_FACTOR)
    # A 0..255 ramp: 0 at the top row, 255 from PROFILE_TINT_GRADIENT_END
    # of the way down on — the gradient ends short of the bottom edge, so
    # the bottom strip carries the bottom color (and opacity) flat.
    end = round((height - 1) * PROFILE_TINT_GRADIENT_END)
    ramp = Image.frombytes(
        "L", (1, height), bytes(min(255, round(255 * y / end)) for y in range(height))
    ).resize(size, Image.Resampling.NEAREST)
    top_alpha = round(PROFILE_TINT_TOP_OPACITY * 255)
    bottom_alpha = round(PROFILE_TINT_BOTTOM_OPACITY * 255)
    alpha = ramp.point(lambda v: top_alpha + (bottom_alpha - top_alpha) * v // 255)
    channels = [
        ramp.point(lambda v, top=c, bot=d: top + (bot - top) * v // 255)
        for c, d in zip(tint_rgb, bottom)
    ]
    return Image.merge("RGBA", (*channels, alpha))


def _tint_at_luma(image: Image.Image, tint_rgb: tuple[int, int, int]) -> Image.Image:
    """Tint *image*'s (RGBA) pixels with the *tint*'s hue at each pixel's
    own perceived brightness (L*): every pixel takes the tint's hue at the
    lightness it already has. White is a fixed point and stays white; a
    near-white pixel can only carry a slight chroma at its lightness, so
    it gets a faint cast of the tint, not the tint itself; levels darker
    than the tint continue the line past it (the channels clamping at
    zero), keeping their lightness and drifting redder as they darken.
    *image* is a pure grayscale (the profile card's mask), looked up per
    channel; the alpha channel is passed through untouched."""
    r, g, b, a = image.split()

    def lstar(rgb: tuple[int, int, int]) -> float:
        def lin(value: int) -> float:
            v = value / 255
            return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

        red, green, blue = (lin(channel) for channel in rgb)
        y = 0.2126729 * red + 0.7151522 * green + 0.0721750 * blue
        return 116 * y ** (1 / 3) - 16 if y > 0.008856 else 903.3 * y

    # The lerp from white toward the tint is monotone in L*: for each gray
    # level v, bisect the mix that lands on L*(v, v, v). v = 255 converges
    # to the mix's white end, so white stays white exactly.
    def mix(c: int, mid: float) -> int:
        return max(0, round(255 + mid * (c - 255)))

    def tinted_at(target: float) -> tuple[int, int, int]:
        lo, hi = 0.0, 5.0
        for _ in range(24):
            mid = (lo + hi) / 2
            pixel = (
                mix(tint_rgb[0], mid),
                mix(tint_rgb[1], mid),
                mix(tint_rgb[2], mid),
            )
            if lstar(pixel) > target:
                lo = mid
            else:
                hi = mid
        mid = (lo + hi) / 2
        return mix(tint_rgb[0], mid), mix(tint_rgb[1], mid), mix(tint_rgb[2], mid)

    lut = [tinted_at(lstar((v, v, v))) for v in range(256)]
    table = [channel for rgb in lut for channel in rgb]
    result = Image.merge(
        "RGB", (r.point(table[0::3]), r.point(table[1::3]), r.point(table[2::3]))
    )
    result.putalpha(a)
    return result


def _profile_layers(
    background: Image.Image, size: tuple[int, int]
) -> tuple[Image.Image, Image.Image, Image.Image]:
    """The profile card's static layers, composed in memory: the (fitted)
    *background* — a monochrome of its own dominant tint — the dominant-tint
    wash (a gradient from the background's dominant color to a darker, more
    opaque version of it), and the profile card mask
    (:data:`PROFILE_MASK_PATH`) — tinted with the same tint at each
    pixel's own lightness (the white staying white). The
    (animated) face framing is
    composited between the background and the tint, per frame and collapsed
    to a monochrome of the same tint's hue, by
    :func:`_stream_dual_composited`. Nothing touches the disk."""
    base = _fit_background(background, size)
    # The background's dominant color: it tints the (now monochrome)
    # background, colors the wash (a gradient darkening toward the
    # bottom) laid over the background and the face, and tints the mask
    # at each pixel's own lightness (the white stays white).
    tint_rgb = _dominant_color(base)
    base = _monochrome(base, tint_rgb)
    tint = _tint_wash(base.size, tint_rgb)
    with Image.open(PROFILE_MASK_PATH) as opened:
        mask = opened.convert("RGBA")
    if mask.size != base.size:
        mask = mask.resize(base.size, Image.Resampling.LANCZOS)
    # The mask takes the tint at its own lightness: every pixel gets the
    # tint's hue at its own L* (white is a fixed point, so the frame keeps
    # its white).
    mask = _tint_at_luma(mask, tint_rgb)
    return base, tint, mask


def _scale_logo(logo: Image.Image, card_width: int) -> Image.Image:
    """Scale *logo* to the nominal width for a *card_width* px-wide card.

    The nominal width is :data:`LOGO_NOMINAL_WIDTH` px at the
    :data:`CARD_REFERENCE_WIDTH` reference width, scaled proportionally for
    other viewport widths; the aspect ratio is preserved.
    """
    target = round(LOGO_NOMINAL_WIDTH * card_width / CARD_REFERENCE_WIDTH)
    if target == logo.width:
        return logo
    height = round(logo.height * target / logo.width)
    return logo.resize((target, height), Image.Resampling.LANCZOS)


def _with_logo(
    base: Image.Image, logo: Image.Image, margin: int, top: bool = False
) -> Image.Image:
    """Return a copy of *base* with *logo* stamped at the bottom right (or
    the top right when *top*)."""
    canvas = base.copy()
    y = margin if top else base.height - logo.height - margin
    canvas.alpha_composite(logo, (base.width - logo.width - margin, y))
    return canvas


def _set_weight(font: ImageFont.FreeTypeFont, weight: int) -> None:
    """Set *font*'s weight via its variation axes, if it is a variable
    font (static fonts have a fixed weight; FreeType raises OSError
    for them)."""
    try:
        font.set_variation_by_axes([weight])
    except OSError:
        pass


def _text_ink_offsets(text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int, int]:
    """Ink offsets (left, top, bottom) of *text* from its draw origin.

    Measured on a probe render, because the rasterized ink can differ from
    the font metrics by a pixel.
    """
    origin = 8
    probe = Image.new(
        "L",
        (
            round(font.getlength(text)) + 2 * origin,
            font.getmetrics()[0] + font.getmetrics()[1] + 2 * origin,
        ),
        0,
    )
    ImageDraw.Draw(probe).text((origin, origin), text, font=font, fill=255)
    bbox = probe.getbbox()
    assert bbox is not None  # the ink is drawn (fill 255 on a black probe)
    left, top, right, bottom = bbox
    return left - origin, top - origin, bottom - origin


def _name_font_size(name: str, base_size: int) -> int:
    """Size for *name*: the base size for names of at most
    NAME_REFERENCE_LENGTH characters, otherwise the base size scaled by
    NAME_REFERENCE_LENGTH / length (truncated), never below
    NAME_MIN_SIZE_FACTOR of the base size."""
    factor = min(1.0, max(NAME_REFERENCE_LENGTH / len(name), NAME_MIN_SIZE_FACTOR))
    return int(base_size * factor)


def _subtitle_font_size(subtitle: str, padding: int) -> int:
    """Font size for *subtitle*: padding * SUBTITLE_SIZE_FACTOR,
    shrinking linearly to padding * SUBTITLE_MIN_SIZE_FACTOR between
    SUBTITLE_FULL_LENGTH and SUBTITLE_FLOOR_LENGTH characters."""
    length = len(subtitle)
    if length <= SUBTITLE_FULL_LENGTH:
        factor = SUBTITLE_SIZE_FACTOR
    elif length >= SUBTITLE_FLOOR_LENGTH:
        factor = SUBTITLE_MIN_SIZE_FACTOR
    else:
        t = (length - SUBTITLE_FULL_LENGTH) / (
            SUBTITLE_FLOOR_LENGTH - SUBTITLE_FULL_LENGTH
        )
        factor = (
            SUBTITLE_SIZE_FACTOR + (SUBTITLE_MIN_SIZE_FACTOR - SUBTITLE_SIZE_FACTOR) * t
        )
    return round(padding * factor)


def _set_luma(hue: float, sat: float, target: float) -> tuple[int, int, int]:
    """(hue, sat) -> an rgb with perceived luminance of ~*target* (0..1).

    At a fixed hue, luminance is linear in both value and saturation,
    so the target is hit either by scaling the value (when the hue at
    this saturation is bright enough at full value) or by reducing the
    saturation at full value (for intrinsically dark hues like deep
    blues and reds).
    """
    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    luma_c = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mix = (1.0 - sat) + sat * luma_c  # luminance at full value
    if mix >= target:
        value = target / mix
    else:
        sat = (1.0 - target) / (1.0 - luma_c)
        value = 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, sat, value)
    return (round(r * 255), round(g * 255), round(b * 255))


def _sample_context(
    region: Image.Image,
) -> tuple[float, float, float | None]:
    """(hue, sat, art luminance) sampled from *region*.

    Median hue/saturation of the colored pixels (medians dodge hue
    wrap-around and single-pixel outliers); the art luminance is the
    mean over all pixels. (Near)-gray art returns the CONTEXT_FALLBACK
    hue/sat, so muted art still gets a visible tint; a fully
    transparent region has no art luminance (None).
    """
    small = region.resize((NAME_SAMPLE_PX, NAME_SAMPLE_PX)).convert("RGB")
    data = small.tobytes()
    hues: list[float] = []
    sats: list[float] = []
    luma_sum, count = 0.0, 0
    for i in range(0, len(data), 3):
        r, g, b = data[i] / 255, data[i + 1] / 255, data[i + 2] / 255
        luma_sum += 0.2126 * r + 0.7152 * g + 0.0722 * b
        count += 1
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        if s > 0.15 and v > 0.15:
            hues.append(h)
            sats.append(s)
    if count == 0:
        h, s, _ = colorsys.rgb_to_hsv(*(c / 255 for c in CONTEXT_FALLBACK))
        return h, s, None
    if len(hues) < NAME_SAMPLE_PX * NAME_SAMPLE_PX * CONTEXT_MIN_QUALIFY:
        # near-gray art: the fallback hue/sat
        h, s, _ = colorsys.rgb_to_hsv(*(c / 255 for c in CONTEXT_FALLBACK))
        return h, s, luma_sum / count
    sat = min(
        CONTEXT_SAT_MAX,
        max(CONTEXT_SAT_MIN, statistics.median(sats) * CONTEXT_SAT_BOOST),
    )
    return statistics.median(hues), sat, luma_sum / count


def _rect_tint(background: Image.Image) -> tuple[int, int, int]:
    """The subtitle rectangle's fill: the background's dominant hue at the
    rectangle's base luminance (NAME_RECT_LUMA), so the dark panel picks up
    the scene's tint instead of reading as a neutral gray."""
    hue, sat, _ = _sample_context(background)
    return _set_luma(hue, sat, NAME_RECT_LUMA)


def _tint_layer(
    mask: Image.Image, color: tuple[int, int, int], factor: float
) -> Image.Image:
    """Straight-alpha RGBA layer: *color* at alpha mask*factor."""
    alpha = mask.point(lambda v: int(v * factor))
    return Image.merge(
        "RGBA",
        (
            Image.new("L", mask.size, color[0]),
            Image.new("L", mask.size, color[1]),
            Image.new("L", mask.size, color[2]),
            alpha,
        ),
    )


class _NameLayers:
    """The static parts of the name stack (one per card).

    Each entry is the layer cropped to its ink's bounding box with the
    position to composite it at, or ``None`` when the layer is absent;
    :func:`_apply_name` composites the layers onto each frame's art, in
    order (compositing a cropped layer at its position is pixel-identical
    to compositing the full-size layer: outside the crop the alpha is 0,
    an exact no-op)."""

    def __init__(
        self,
        rect: tuple[Image.Image, tuple[int, int]] | None,
        sub_rect: tuple[Image.Image, tuple[int, int]] | None,
        title: tuple[Image.Image, tuple[int, int]] | None,
        arrow: tuple[Image.Image, tuple[int, int]] | None,
        sub_top: tuple[Image.Image, tuple[int, int]] | None,
    ) -> None:
        self.rect = rect
        self.sub_rect = sub_rect
        self.title = title
        self.arrow = arrow
        self.sub_top = sub_top


def _name_layers(
    size: tuple[int, int],
    name: str,
    subtitle: str,
    padding: int,
    rect_color: tuple[int, int, int],
    sub_rect_color: tuple[int, int, int],
    manufacturer_logo: Image.Image | None = None,
) -> _NameLayers:
    """Build the static name-stack layers for a card of *size*.

    The layers are static (one per card); :func:`_apply_name` composites
    them onto each frame's art.

    The title and the subtitle are always rendered uppercase (their
    length, and so their font size, is unaffected).

    *manufacturer_logo* (the character's manufacturer's mark, white on
    transparency, filled with the bar's own fill when placed) is put above
    the title's bar when given (see :data:`MANUFACTURER_LOGO_WIDTH`); it is
    part of the bar's layer, so it is only placed when the bar is.
    """
    name = name.upper()
    subtitle = subtitle.upper()
    font_size = _name_font_size(name, round(padding * NAME_SIZE_FACTOR))
    font = ImageFont.truetype(str(FONT_NAME), font_size)
    _set_weight(font, NAME_WEIGHT)
    left, top, bottom = _text_ink_offsets(name, font)
    # The title's ink top sits at NAME_TITLE_Y of the height; the left inset
    # is the card's own padding.
    title_top = round(size[1] * NAME_TITLE_Y)
    inset = padding

    title_mask = Image.new("L", size, 0)
    ImageDraw.Draw(title_mask).text(
        (inset - left, title_top - top), name, font=font, fill=255
    )
    # Title core: flat white (NAME_TEXT_COLOR), masked by the title's
    # alpha; only the geometry and the alpha are static.
    title_box = title_mask.getbbox()
    title_alpha = title_mask
    # The top and bottom of the title's enclosing rectangle (its ink's
    # top/bottom inset by NAME_RECT_PAD of the ink's height; None when
    # there is no title): the subtitle sits below the bottom.
    rect_top = (
        title_box[1] - round((title_box[3] - title_box[1]) * NAME_RECT_PAD)
        if title_box is not None
        else None
    )
    rect_bottom = (
        title_box[3] + round((title_box[3] - title_box[1]) * NAME_RECT_PAD)
        if title_box is not None
        else None
    )
    sub_mask = None
    sub_top = None
    sub_rect = None
    if subtitle:
        sub_size = _subtitle_font_size(subtitle, padding)
        sub_font = ImageFont.truetype(str(FONT_NAME), sub_size)
        _set_weight(sub_font, NAME_WEIGHT)
        sub_left, sub_top_off, sub_bottom = _text_ink_offsets(subtitle, sub_font)
        ink_h = sub_bottom - sub_top_off
        region = Image.new("L", (round(sub_font.getlength(subtitle)) + 1, ink_h + 1), 0)
        ImageDraw.Draw(region).text(
            (-sub_left, -sub_top_off), subtitle, font=sub_font, fill=255
        )
        small = region
        # Below the title: left-aligned with the title's own inset, its
        # rectangle's top edge on the title rectangle's bottom (the old
        # top-right corner placement when there is no title).
        bbox = small.getbbox()
        assert bbox is not None  # the ink is drawn (fill 255 on a black probe)
        if rect_top is not None:
            # rect_bottom is derived from title_box, like rect_top.
            assert rect_bottom is not None
            sub_pad = round((bbox[3] - bbox[1]) * NAME_SUB_RECT_PAD)
            px = inset - bbox[0]
            py = rect_bottom - bbox[1] + sub_pad
        else:
            px, py = size[0] - padding - bbox[2], padding - bbox[1]
        sub_mask = Image.new("L", size, 0)
        sub_mask.paste(255, (px, py, px + small.width, py + small.height), small)
        sub_top = _tint_layer(sub_mask, NAME_TEXT_COLOR, 1.0)
        # The subtitle's enclosing rectangle: the title's rectangle's
        # shape on the subtitle's ink — the background-tinted fill
        # (sub_rect_color, in place of the title's flat NAME_RECT_COLOR),
        # NAME_SUB_RECT_PAD of the subtitle's ink's height of room on the
        # top/bottom (NAME_SUB_RECT_PAD + NAME_SUB_RECT_RIGHT_PAD_EXTRA on
        # the right; the left edge is the card's left edge, as the title's),
        # and the same 45-degree diagonal cut off the bottom-right corner
        # (None when there is no title).
        if rect_top is not None:
            sub_bbox = sub_mask.getbbox()
            assert sub_bbox is not None  # the subtitle's ink was just pasted
            srx0, sry0, srx1, sry1 = sub_bbox
            sub_right_pad = sub_pad + round(
                (sry1 - sry0) * NAME_SUB_RECT_RIGHT_PAD_EXTRA
            )
            sub_rect_top = sry0 - sub_pad
            sub_rect_bottom = sry1 + sub_pad
            sub_right = srx1 + sub_right_pad
            sub_cut = round((sub_rect_bottom - sub_rect_top) * NAME_RECT_CORNER)
            sub_rect = Image.new("RGBA", size, (0, 0, 0, 0))
            ImageDraw.Draw(sub_rect).polygon(
                [
                    (0, sub_rect_top),
                    (sub_right, sub_rect_top),
                    (sub_right, sub_rect_bottom - sub_cut),
                    (sub_right - sub_cut, sub_rect_bottom),
                    (0, sub_rect_bottom),
                ],
                fill=(*sub_rect_color, 255),
            )

    # The title's enclosing rectangle: a flat NAME_RECT_COLOR fill,
    # starting at the card's left edge and extending past the ink by
    # NAME_RECT_PAD of the ink's height on the top/bottom, and by
    # NAME_RECT_PAD + the arrow's width + padding / 2 on the right; its
    # top-right corner is cut off by a 45-degree diagonal (None when
    # there is no title).
    rect = None
    arrow_alpha = None
    if title_box is not None:
        rx0, ry0, rx1, ry1 = title_box
        pad = round((ry1 - ry0) * NAME_RECT_PAD)
        # rect_top / rect_bottom were derived from title_box above.
        assert rect_top is not None
        assert rect_bottom is not None
        top = rect_top
        bottom = rect_bottom
        rect_height = bottom - top
        # The arrow's ink (NAME_RECT_ARROW in the rectangle's right padding),
        # measured before the rectangle so the right edge can account for its
        # width. A roomy probe (the glyph's ink can spill well past the font
        # size, e.g. a descender), with the glyph centered, so the ink is not
        # clipped.
        arrow_font = ImageFont.truetype(
            str(FONT_RECT_ARROW), round(rect_height * NAME_RECT_ARROW_SIZE)
        )
        probe = Image.new(
            "L", (round(arrow_font.size * 4), round(arrow_font.size * 4)), 0
        )
        ImageDraw.Draw(probe).text(
            (arrow_font.size * 2, arrow_font.size * 2),
            NAME_RECT_ARROW,
            font=arrow_font,
            fill=255,
        )
        ink_box = probe.getbbox()
        ink = probe.crop(ink_box) if ink_box is not None else None
        # The right edge is pad + the arrow's width + padding / 2 past the
        # title's ink.
        right = rx1 + pad + (ink.width if ink is not None else 0) + round(padding / 2)
        # The corner cut: NAME_RECT_CORNER of the rectangle's height, so the
        # diagonal is the diagonal of a square with that side length.
        cut = round(rect_height * NAME_RECT_CORNER)
        rect = Image.new("RGBA", size, (0, 0, 0, 0))
        ImageDraw.Draw(rect).polygon(
            [
                (0, top),
                (right - cut, top),
                (right, top + cut),
                (right, bottom),
                (0, bottom),
            ],
            fill=(*rect_color, 255),
        )
        # The small bar above the rectangle: padding * 3 wide and
        # padding / 2 tall, a gap of padding / 4 above the rectangle's
        # top edge; the same fill, aligned with the rectangle's left
        # edge, its right edge a 45-degree diagonal slanting back to
        # the left (the bottom-right corner pulled in by the same
        # number of pixels as the slant's vertical run, so the
        # diagonal is the diagonal of a square with that side).
        bar_h = round(padding / 2)
        bar_top = top - round(padding / 4) - bar_h
        ImageDraw.Draw(rect).polygon(
            [
                (0, bar_top),
                (padding * 3 - 1, bar_top),
                (padding * 3 - bar_h, bar_top + bar_h - 1),
                (0, bar_top + bar_h - 1),
            ],
            fill=(*rect_color, 255),
        )
        # Three squares next to the bar (to its right): a square of the
        # bar's height, a gap of padding / 4 from the bar and between the
        # squares (the even gaps stay even down the slant, all the edges
        # slanting alike); each square's edges slant the same 45 degrees
        # as the bar's (the same pull on both sides, so the slant is the
        # diagonal of a square with that side).
        side = bar_h
        gap = round(padding / 4)
        for i in range(3):
            x0 = padding * 3 + gap + i * (side + gap)
            ImageDraw.Draw(rect).polygon(
                [
                    (x0, bar_top),
                    (x0 + side - 1, bar_top),
                    (x0, bar_top + bar_h - 1),
                    (x0 - (bar_h - 1), bar_top + bar_h - 1),
                ],
                fill=(*rect_color, 255),
            )
        # The manufacturer's logo above the bar: MANUFACTURER_LOGO_WIDTH
        # the frame's width wide (its height proportional), its left edge
        # at the card's padding (the title's own inset), a gap of
        # padding / 2 between its bottom and the bar's top; its mark's
        # alpha filled with the bar's own fill (the title's background),
        # so the mark, the bar and the squares share one color.
        if manufacturer_logo is not None:
            logo_w = round(size[0] * MANUFACTURER_LOGO_WIDTH)
            logo_h = round(logo_w * manufacturer_logo.height / manufacturer_logo.width)
            mark = manufacturer_logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            rect.alpha_composite(
                _tint_layer(mark.getchannel("A"), rect_color, 1.0),
                (inset, bar_top - round(padding / 2) - logo_h),
            )
        if ink is not None:
            # The arrow: its ink's bottom-right aligned NAME_RECT_ARROW_MARGIN
            # from the rectangle's right/bottom edges.
            margin = round(rect_height * NAME_RECT_ARROW_MARGIN)
            # The arrow's alpha (a mask; flat white, like the title).
            arrow_alpha = Image.new("L", size, 0)
            arrow_alpha.paste(
                ink, (right - margin - ink.width, bottom - margin - ink.height)
            )

    # The layers are static (built once per card): tint the title core and
    # the arrow (flat white, NAME_TEXT_COLOR) here instead of per frame,
    # and crop every layer to its ink's bounding box so
    # :func:`_apply_name` composites the ink, not the whole frame.
    def cropped(layer: Image.Image) -> tuple[Image.Image, tuple[int, int]] | None:
        box = layer.getchannel("A").getbbox()
        if box is None:
            return None
        return (layer.crop(box), (box[0], box[1]))

    return _NameLayers(
        cropped(rect) if rect is not None else None,
        cropped(sub_rect) if sub_rect is not None else None,
        # The title core: flat white, masked by the title's alpha.
        cropped(_tint_layer(title_alpha, NAME_TEXT_COLOR, 1.0))
        if title_box is not None
        else None,
        # The arrow: flat white, like the title.
        cropped(_tint_layer(arrow_alpha, NAME_TEXT_COLOR, 1.0))
        if arrow_alpha is not None
        else None,
        cropped(sub_top) if sub_top is not None else None,
    )


def _apply_name(art: Image.Image, parts: _NameLayers) -> Image.Image:
    """Stamp the name stack onto *art* (the frame composited over the
    base) and return the result. The layers are static, each cropped to
    its ink (see :class:`_NameLayers`)."""
    for layer in (parts.rect, parts.sub_rect, parts.title, parts.arrow, parts.sub_top):
        if layer is not None:
            art.alpha_composite(layer[0], layer[1])
    return art


def _with_copyright(
    base: Image.Image, padding: int, color: tuple[int, int, int, int]
) -> Image.Image:
    """Return a copy of *base* with the copyright line at the bottom left.

    The ink of the text starts ``padding`` pixels from the left edge and
    is vertically centered inside the box of height ``padding`` at the
    bottom of the card; its size scales with the card width like the
    logo. The text is drawn at COPYRIGHT_SUPERSAMPLE times the final
    size and downscaled with LANCZOS, so the small letters stay evenly
    spaced.
    """
    canvas = base.copy()
    font_size = round(COPYRIGHT_NOMINAL_SIZE * base.width / CARD_REFERENCE_WIDTH)
    ss = COPYRIGHT_SUPERSAMPLE
    big = ImageFont.truetype(str(FONT), font_size * ss)
    big.set_variation_by_axes([COPYRIGHT_WEIGHT])
    left, top, bottom = _text_ink_offsets(COPYRIGHT_TEXT, big)
    region = Image.new(
        "L", (round(big.getlength(COPYRIGHT_TEXT)) + 1, bottom - top + 1), 0
    )
    ImageDraw.Draw(region).text((-left, -top), COPYRIGHT_TEXT, font=big, fill=255)
    small = region.resize(
        (round(region.width / ss), round(region.height / ss)),
        Image.Resampling.LANCZOS,
    )
    stamp = Image.new("RGBA", small.size, color)
    stamp.putalpha(small)
    canvas.alpha_composite(
        stamp,
        (
            padding,
            base.height - padding // 2 - round((bottom - top) / (2 * ss)),
        ),
    )
    return canvas


def _logo_copyright_overlay(
    size: tuple[int, int],
    logo: Image.Image,
    margin: int,
    padding: int,
    color: tuple[int, int, int, int],
    logo_top: bool = False,
) -> tuple[Image.Image, tuple[int, int]]:
    """Pre-stamp the logo and the copyright line onto a transparent layer.

    The logo sits at the bottom right (or the top right when *logo_top*)
    and the copyright line at the bottom left, at the same placement as
    when stamped directly, so the combined layer is cropped to its
    bounding box; the caller composites the crop onto each frame after the
    art is in place, keeping the stamps on top of the art.

    Returns the cropped layer and the coordinates at which to composite it
    on a card of *size*.
    """
    width, height = size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay = _with_logo(overlay, _scale_logo(logo, width), margin, logo_top)
    overlay = _with_copyright(overlay, padding, color)
    box = overlay.getbbox()
    assert box is not None, "the logo and copyright layer is empty"
    return overlay.crop(box), (box[0], box[1])


def _composite_frame(frame: Image.Image, base: Image.Image, base_alpha: Image.Image | None) -> Image.Image:
    """Composite *frame* over *base*; the result is RGBA.

    When *base_alpha* (the base's alpha channel) is given, the base is fully
    opaque and the blend takes the GIL-releasing ``Image.composite`` path:
    its RGB is bit-identical to ``base.alpha_composite(frame)`` (the two
    blend formulas agree whenever the destination is opaque), and the base's
    alpha band is restored afterwards so that the downstream stamps (the
    logo and copyright line) composite against the same alpha the
    ``alpha_composite`` path would have left — the finished card is
    byte-identical either way. *base_alpha* is computed once per card by
    the caller.
    """
    if frame.mode != "RGBA":
        frame = frame.convert("RGBA")
    if base_alpha is None:
        canvas = base.copy()
        canvas.alpha_composite(frame)
        return canvas
    art = Image.composite(frame, base, frame.getchannel("A"))
    art.putalpha(base_alpha)
    return art


def _encode_mp4(
    frames: Iterator[Image.Image],
    size: tuple[int, int],
    framerate: int,
    out_path: Path,
    threads: int,
    preset: str,
    scale: float,
    source_hash: str | None = None,
) -> None:
    """Encode an RGBA frame stream into an MP4 using ffmpeg."""
    width, height = size
    command = [
        ENCODER,
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgba",
        "-s",
        f"{width}x{height}",
        "-framerate",
        str(framerate),
        "-i",
        "-",
    ]
    if scale != 1.0:
        # Downscale inside ffmpeg (fast, SIMD-optimized swscale) rather
        # than resizing every frame in Python first.
        target = (
            round(width * scale) & ~1,
            round(height * scale) & ~1,
        )  # yuv420p needs even dims
        command += ["-vf", f"scale={target[0]}:{target[1]}"]
    command += [
        "-c:v",
        "libx264",
        "-preset",
        preset,
        *FFMPEG_QUALITY_ARGS,
        "-threads",
        str(max(1, threads)),
    ]
    if source_hash is not None:
        # Arbitrary metadata keys need use_metadata_tags to land in the
        # container (read back via ffprobe's format tags)
        command += [
            "-movflags",
            "use_metadata_tags",
            "-metadata",
            f"{SOURCE_HASH_KEY}={source_hash}",
        ]
    command += [
        "-f",
        "mp4",  # explicit format: the output name may carry a suffix (e.g. .part)
        str(out_path),
    ]
    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=PIPE_BUFSIZE,
        )
    except OSError as exc:
        raise GenerationError(f"could not run {ENCODER!r}: {exc}") from exc

    try:
        assert proc.stdin is not None
        for frame in frames:
            proc.stdin.write(frame.tobytes())
    except Exception as exc:  # includes a bad frame surfacing mid-stream
        proc.kill()
        proc.wait()
        detail = (
            proc.stderr.read().decode(errors="replace").strip() if proc.stderr else ""
        )
        detail = f" ({detail[-500:]})" if detail else ""
        raise GenerationError(f"frame stream failed: {exc}{detail}") from exc
    finally:
        if proc.stdin:
            proc.stdin.close()

    stderr = proc.communicate()[1]
    if proc.returncode != 0:
        raise GenerationError(
            f"{ENCODER} failed (exit {proc.returncode}): {stderr.decode(errors='replace').strip()}"
        )


def _save_atomic(
    image: Image.Image, out_path: Path, source_hash: str | None = None
) -> Path:
    """Save *image* to a ``.part`` file and atomically move it into place.

    A finished card therefore only ever exists in its complete form.
    *source_hash* is embedded as the SOURCE_HASH_KEY text chunk so a
    later run can tell the card is up to date.
    """
    tmp_path = out_path.with_name(out_path.name + ".part")
    pnginfo = None
    if source_hash is not None:
        pnginfo = PngInfo()
        pnginfo.add_text(SOURCE_HASH_KEY, source_hash)
    try:
        image.save(tmp_path, format="PNG", pnginfo=pnginfo)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    tmp_path.replace(out_path)
    return out_path


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
    """Write a composited frame stream to the final card.

    An animation is encoded to an MP4 alongside its first frame (the same
    composited frame, so it matches the mp4's opening frame exactly); a
    fixed-time card is written as a single PNG. *composited* is closed (so the
    viewer stream(s) are reaped) and the stage timings (in seconds) are
    returned: ``render`` (spawn until the frame stream is fully delivered),
    ``composite`` (the Pillow work summed across the worker threads) and
    ``encode`` (the ffmpeg wall time for animations, the PNG write for static
    cards). The stages overlap — the encode consumes frames while the viewer
    still renders and the compositing runs in its own threads — so the numbers
    are per-stage costs, not a sequential partition.
    """
    out_path = _card_out_path(out_base, json_path, "mp4" if animated else "png", stem)
    encode_time: float | None = None
    try:
        if animated:
            tmp_path = out_path.with_name(out_path.name + ".part")
            try:
                encode_started = time.perf_counter()
                _encode_mp4(
                    composited,
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
                raise
            tmp_path.replace(out_path)
            _save_atomic(
                first_frame[0].convert("RGB"),
                _card_out_path(out_base, json_path, "png", stem),
                source_hash,
            )
        else:
            # A single frame: take it from the stream and write it.
            frame = next(composited, None)
            if frame is None:
                raise GenerationError(
                    f"{VIEWER} produced no frame for {json_path.name}"
                )
            encode_started = time.perf_counter()
            _save_atomic(frame.convert("RGB"), out_path, source_hash)
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


def _render_profile(
    json_path: Path,
    size: tuple[int, int],
    animated: bool,
    background: Image.Image,
    tint: Image.Image,
    mask: Image.Image,
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
    the logo sits at the top right.

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
) -> tuple[Path, bool, dict[str, float | None] | None]:
    """Render, composite and encode a single card definition.

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
    # The standard presentations never carry the card name (only the
    # profile cards render the title and subtitle).
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
    animated = card.get("time") is None
    out_path = _card_out_path(out_base, json_path, "mp4" if animated else "png")
    source_hash = _source_hash(json_path)
    up_to_date = out_path.is_file() and _stored_hash(out_path) == source_hash
    if up_to_date and animated:
        # The animation's first frame is kept alongside it; a missing or
        # stale copy forces the card to be re-rendered.
        first_frame_path = _card_out_path(out_base, json_path, "png")
        up_to_date = (
            first_frame_path.is_file() and _stored_hash(first_frame_path) == source_hash
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


def _process_profile_card(
    json_path: Path,
    ffmpeg_threads: int = 1,
    composite_workers: int = 4,
    preset: str = DEFAULT_PRESET,
    scale: float = DEFAULT_SCALE,
    out_base: Path = OUTPUT_DIR,
) -> tuple[Path, bool, dict[str, float | None] | None]:
    """Render the ``<variant>Profile`` profile card for *json_path*
    (derived from its own definition — every rarity, ``Aim`` and
    ``Cover`` included, renders one, the ``Goddess`` and ``Classified``
    presentations excepted): the ``--face`` framing animates (as a
    monochrome of the tint's hue) over the background, under its dominant
    tint wash, and the ``--full-body`` framing animates over the card mask
    (both streamed in lockstep from the same definition). The name and
    subtitle overlays are applied as usual, like the other rarities; the
    logo sits at the top right.

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
    # frame (png); one with a `time` renders a single frame (png).
    animated = card.get("time") is None
    stem = _profile_stem(json_path)
    out_path = _card_out_path(out_base, json_path, "mp4" if animated else "png", stem)
    source_hash = _profile_source_hash(json_path)
    up_to_date = out_path.is_file() and _stored_hash(out_path) == source_hash
    if up_to_date and animated:
        # The animation's first frame is kept alongside it; a missing or
        # stale copy forces the card to be re-rendered.
        first_frame_path = _card_out_path(out_base, json_path, "png", stem)
        up_to_date = (
            first_frame_path.is_file() and _stored_hash(first_frame_path) == source_hash
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
    base, tint, mask = _profile_layers(background, size)
    for attempt in range(1, RENDER_ATTEMPTS + 1):
        try:
            finished, timings = _render_profile(
                json_path,
                size,
                animated,
                base,
                tint,
                mask,
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


def _pack_mask(template: Image.Image) -> Image.Image:
    """A binary mask of the template's pure-blue placeholder pixels."""
    r = template.getchannel("R").point(lambda v: 255 if v == 0 else 0)
    g = template.getchannel("G").point(lambda v: 255 if v == 0 else 0)
    b = template.getchannel("B").point(lambda v: 255 if v == 255 else 0)
    return ImageChops.darker(ImageChops.darker(r, g), b)


def _box_side_mask(template: Image.Image) -> Image.Image:
    """A binary mask of the template's pure-green placeholder pixels (the
    box's side)."""
    r = template.getchannel("R").point(lambda v: 255 if v == 0 else 0)
    g = template.getchannel("G").point(lambda v: 255 if v == 255 else 0)
    b = template.getchannel("B").point(lambda v: 255 if v == 0 else 0)
    return ImageChops.darker(ImageChops.darker(r, g), b)


def _box_top_mask(template: Image.Image) -> Image.Image:
    """A binary mask of the template's pure-red placeholder pixels (the
    box's top, shared with its bottom)."""
    r = template.getchannel("R").point(lambda v: 255 if v == 255 else 0)
    g = template.getchannel("G").point(lambda v: 255 if v == 0 else 0)
    b = template.getchannel("B").point(lambda v: 255 if v == 0 else 0)
    return ImageChops.darker(ImageChops.darker(r, g), b)


def _pack_mask_rects(mask: Image.Image) -> list[tuple[int, int, int, int]]:
    """Bounding boxes of the mask's solid rectangles, left to right.

    Each box is ``(left, top, right, bottom)`` with right and bottom
    exclusive, as PIL expects. A solid rectangle repeats the same pixel
    run on every row, so consecutive rows carrying the same run belong
    to the same rectangle.
    """
    flat = mask.convert("L")
    data = flat.tobytes()
    width, height = flat.size
    spans: dict[tuple[int, int], list[int]] = {}
    for y in range(height):
        row = data[y * width : (y + 1) * width]
        for match in re.finditer(b"\xff+", row):
            run = (match.start(), match.end())
            if spans.get(run, [None, None])[1] == y - 1:
                spans[run][1] = y
            else:
                spans[run] = [y, y]
    return sorted((x0, y0, x1, y1 + 1) for (x0, x1), (y0, y1) in spans.items())


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
) -> bool:
    """True when the pack's finished *out_name* already exists and its stored
    hash matches the current inputs (the template and the front's and back's
    *sources*) — computed without rendering the front or back, so their
    renders can be skipped when nothing has changed."""
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
    if out_path.is_file() and _stored_hash(out_path) == source_hash:
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
    if out_path.is_file() and _stored_hash(out_path) == source_hash:
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
    mesh: Path, material: Path, config: Path, out_path: Path
) -> bool:
    """True when the viewer's finished *out_path* already exists and its
    stored hash matches the current *mesh*, *material* and *config* —
    computed without rendering, so the render can be skipped when
    nothing has changed. A missing output or input (the material not
    generated yet) is simply not up to date."""
    if not (
        mesh.is_file()
        and material.is_file()
        and config.is_file()
        and out_path.is_file()
    ):
        return False
    return _stored_hash(out_path) == _viewer_hash(mesh, material, config)


def _process_pack_item(pack_dir: Path, out_base: Path) -> tuple[Path, bool]:
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
    if out_path.is_file() and _stored_hash(out_path) == source_hash:
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


def _process_box_item(pack_dir: Path, out_base: Path) -> tuple[Path, bool]:
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
    if out_path.is_file() and _stored_hash(out_path) == source_hash:
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
) -> None:
    """Render the profile cards — one for every rarity except the
    ``Goddess`` and ``Classified`` presentations (all written out as
    ``<variant>Profile``) — in a pool of worker processes.

    *paths* is passed to :func:`_find_card_configs` (a ``None`` selects every
    card definition); from the result every definition without a
    ``Goddess``/``Classified`` stem is kept (see
    :func:`_process_profile_card`). No pack artwork or metadata is produced.
    """
    _require_executable(VIEWER)
    _require_executable(ENCODER)
    _require_executable(PROBER)
    configs = _find_card_configs(paths)
    profile_configs = [
        path
        for path in configs
        if path.stem in PROFILE_RARITIES or path.stem not in NO_PROFILE_STEMS
    ]
    if not configs:
        raise GenerationError("no profile card definitions to render")
    if not profile_configs:
        # The selection has no profile-eligible definition (e.g. it only
        # selects a Goddess presentation): the standard presentations still
        # render.
        print("No profile card definitions selected; skipping the profile pass.")
        return
    start = time.monotonic()
    total = len(profile_configs)
    # Split the cores available to each card between the stages that run in
    # parallel: the frame compositing and the ffmpeg encode.
    per_card = (os.cpu_count() or 1) // max(1, min(jobs, total))
    ffmpeg_threads = max(2, min(MAX_STAGE_THREADS, per_card // 2))
    composite_workers = max(2, min(MAX_STAGE_THREADS, per_card - ffmpeg_threads))
    notes = []
    if preset != DEFAULT_PRESET:
        notes.append(f"x264 preset '{preset}'")
    if scale != 1.0:
        notes.append(f"{scale:g}x resolution")
    notes_text = f", {', '.join(notes)} (draft)" if notes else ""
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


def _generate_variants(
    paths: list[Path] | None,
    jobs: int,
    preset: str,
    scale: float,
    out_base: Path,
) -> None:
    """Process the selected cards in a pool of worker processes."""
    _require_executable(VIEWER)
    _require_executable(ENCODER)
    _require_executable(PROBER)
    # The profile rarities render through the profile pipeline (see
    # :func:`_generate_profiles`), not the standard one.
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
        )
        item_ok = _viewer_output_up_to_date(
            PACK_MESH,
            out_base / pack_dir.relative_to(CARDS_DIR) / PACK_MATERIAL_NAME,
            PACK_CONFIG,
            out_base / pack_dir.relative_to(CARDS_DIR) / PACK_ITEM_NAME,
        )
        box_ok = _pack_output_up_to_date(
            BOX_TEMPLATE,
            BOX_MATERIAL_NAME,
            pack_dir,
            out_base,
            box_front_source,
        )
        box_item_ok = _viewer_output_up_to_date(
            BOX_MESH,
            out_base / pack_dir.relative_to(CARDS_DIR) / BOX_MATERIAL_NAME,
            BOX_CONFIG,
            out_base / pack_dir.relative_to(CARDS_DIR) / BOX_ITEM_NAME,
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
    # Split the cores available to each card between the stages that run
    # in parallel: the frame compositing and the ffmpeg encode.
    per_card = (os.cpu_count() or 1) // max(1, min(jobs, total))
    ffmpeg_threads = max(2, min(MAX_STAGE_THREADS, per_card // 2))
    composite_workers = max(2, min(MAX_STAGE_THREADS, per_card - ffmpeg_threads))
    notes = []
    if preset != DEFAULT_PRESET:
        notes.append(f"x264 preset '{preset}'")
    if scale != 1.0:
        notes.append(f"{scale:g}x resolution")
    notes_text = f", {', '.join(notes)} (draft)" if notes else ""
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
            ): path.relative_to(CARDS_DIR)
            for path in card_configs
        }
        # The item is rendered from the material's output file, so each
        # pack's item starts only after its material has finished. Packs
        # whose material is already up to date need no wait: their item
        # renders from the material that is already on disk.
        item_futures: dict[Future[tuple[Path, bool]], Path] = {
            pool.submit(_process_pack_item, pack_dir, out_base): item_label(pack_dir)
            for pack_dir in sorted(item_needs - material_needs)
        }
        # The box's item is rendered from the box material's output file,
        # so each box's item starts only after its material has finished.
        box_item_futures: dict[Future[tuple[Path, bool]], Path] = {
            pool.submit(_process_box_item, pack_dir, out_base): box_item_label(pack_dir)
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
            ): pack_dir
            for pack_dir in sorted(box_needs)
        }
        for future in as_completed(material_futures):
            pack_dir = material_futures[future]
            report(future, material_label(pack_dir))
            if future.exception() is not None:
                continue  # no material -> no item for this pack
            if pack_dir in item_needs:
                item_futures[pool.submit(_process_pack_item, pack_dir, out_base)] = (
                    item_label(pack_dir)
                )
        for future in as_completed(box_futures):
            pack_dir = box_futures[future]
            report(future, box_label(pack_dir))
            if future.exception() is not None:
                continue  # no box material -> no box item for this pack
            if pack_dir in box_item_needs:
                box_item_futures[pool.submit(_process_box_item, pack_dir, out_base)] = (
                    box_item_label(pack_dir)
                )
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


def copy(source: pathlib.Path, dest: pathlib.Path, overwrite=False):
    if dest.exists():
        if not overwrite:
            return

        if source.is_dir():
            for entry in source.iterdir():
                copy(entry, dest / entry.name, overwrite=True)

            return

    if dest.is_relative_to(REPO_ROOT):
        print(dest.relative_to(REPO_ROOT))
    else:
        print(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)
    source.copy(dest)
