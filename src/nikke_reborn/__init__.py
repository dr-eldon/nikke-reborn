"""Render and composite Nikke trading cards.

Walks :mod:`cards` for card definitions (``*.json``), renders each one with
the ``nikke-viewer`` executable, composites every rendered frame on top of
the card's ``background``, stamps the matching logo from ``images/`` at
the bottom right and the copyright line at the bottom left, and overlays
the card name on top of the art, per frame: the title at the top left
(metallic vertical gradient, diagonal trail) and the subtitle in the
top-right corner (italic, with its own trail). The trails and the
gradient's bottom lean are tinted with the color of the art behind the
text each frame, so animated cards track the scene. The full-art
variants (``FullArt``, ``FullArtAnimated``) are generated without any
card name. Packs (``cards/`` subdirectories carrying
``CardPack_Back.png`` and ``CardPack_Front.png``) additionally get their
two artwork images, built from the templates in ``images/``: the material
(``CardPack_Material.png``), whose two pure-blue mask rectangles hold
the pack's back (left) and front (right) images, and the item
(``CardPack_Item.png``), a perspective view whose single pure-blue mask
is a slanted quadrilateral that the front image is perspective-warped
to (corner to corner) and clipped into — its bottom border first
carrying a thin dark gradient, biased toward the bottom-right
corner. The white logo is
stamped on
the pack's front in both, at the same placement: unslanted on the
material's front rectangle, slanted over the item. The finished results are
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
definition paths may be passed on the command line to generate only those.
"""

from __future__ import annotations

import argparse
import colorsys
import hashlib
import io
import json
import math
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
from concurrent.futures import (
    Future,
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from pathlib import Path
from typing import Iterator
from nikke_reborn import bundler, metadata

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from PIL.PngImagePlugin import PngInfo

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CARDS_DIR = REPO_ROOT / "cards"
IMAGES_DIR = REPO_ROOT / "images"
FONTS_DIR = REPO_ROOT / "fonts"
OUTPUT_DIR = REPO_ROOT / "output"
DRAFT_DIR = REPO_ROOT / "draft"
BUNDLES_DIR = REPO_ROOT / "bundles"
DATABASE_DIR = REPO_ROOT / "database"
SHOP_DIR = IMAGES_DIR / "shop"

VIEWER = "nikke-viewer"
ENCODER = "ffmpeg"
PROBER = "ffprobe"

#: Key of the embedded definition hash in the finished cards (a PNG
#: text chunk, an MP4 tag): a card whose stored hash matches the
#: current definition is skipped instead of re-rendered.
SOURCE_HASH_KEY = "nikke-reborn-source"

DEFAULT_FRAMERATE = 60

#: Variant stems that never carry the card name: the full-art
#: presentations are generated without title and subtitle.
NO_NAME_STEMS = frozenset({"FullArt", "FullArtAnimated"})

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
COPYRIGHT_TEXT = "©SHIFT UP CORP."

#: Oswald face for the copyright line (vendored variable font, SIL OFL).
FONT = FONTS_DIR / "Oswald.ttf"

#: Orbitron face for the card name (vendored variable font, SIL OFL).
FONT_NAME = FONTS_DIR / "Orbitron.ttf"

#: Card name placement: the ink's top-left corner sits exactly at
#: (padding, padding), left-aligned, with font size
#: padding * NAME_SIZE_FACTOR and Orbitron weight NAME_WEIGHT (700 = bold).
NAME_SIZE_FACTOR = 1.5
NAME_WEIGHT = 700

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
SUBTITLE_SIZE_FACTOR = 0.60
SUBTITLE_MIN_SIZE_FACTOR = 0.40
SUBTITLE_FULL_LENGTH = 18
SUBTITLE_FLOOR_LENGTH = 30

#: Slant of the synthetic italic (subtitle) in horizontal px per
#: vertical px: the name font has no italic face, so the subtitle is
#: sheared into an oblique (see SUBTITLE_SUPERSAMPLE).
SUBTITLE_SHEAR = 0.2

#: Gap between the title's ink bottom and the subtitle's ink top, as a
#: fraction of the subtitle's font size.
SUBTITLE_GAP_FACTOR = 0.5

#: Supersampling factor for the italic subtitle: the text is rasterized
#: at SUBTITLE_SUPERSAMPLE times its size, sheared, and downscaled, so
#: the slanted edges stay anti-aliased without softening (a 1x shear
#: blurs every edge by 1-2 px). Shearing the font's outlines instead is
#: no good: FreeType's autohinter applies "slant correction" to slanted
#: stems, which shifts them off their true positions and opens up gaps
#: between letters.
SUBTITLE_SUPERSAMPLE = 4

#: Base color of the name text (title and subtitle).
NAME_TEXT_COLOR = (255, 255, 255)

# --- name stack effects -------------------------------------------------
# The name is stamped over the art, per frame, so its tints track the
# scene: the trails and the metallic gradient's bottom lean take the
# hue of the art behind the text, at a fixed dark luminance.
NAME_TRAIL_OFFSET = 5  # px: the title's diagonal (down-right) trail
SUBTITLE_TRAIL_OFFSET = 3  # px: the subtitle's own (shorter) trail
TRAIL_ALPHA = 0.75
TRAIL_TARGET_LUMA = 0.12  # the trail reads as a dark shadow tint
TRAIL_FALLBACK = (0, 0, 0)  # trail color when the sample has no art
NAME_SAMPLE_W = 6  # context sample box, in padding units
NAME_SAMPLE_H = 5
NAME_SAMPLE_PX = 24  # sample resolution
CONTEXT_FALLBACK = (170, 235, 255)  # hue/sat source for (near)-gray art
CONTEXT_MIN_QUALIFY = 0.25  # min fraction of sample pixels that are colored
CONTEXT_SAT_BOOST = 1.4  # the sampled saturation is boosted...
CONTEXT_SAT_MIN = 0.45  # ...and clamped, so the tint stays visible...
CONTEXT_SAT_MAX = 0.90  # ...without washing out
METAL_TRAIL_MIX = 0.25  # metallic title: how far the ink's bottom leans
# into the per-frame trail tint
METAL_SHEEN_Y = 0.42  # sheen band center (fraction of the ink height)
METAL_SHEEN_DELTA = 20  # band brightness (RGB units)
METAL_SHEEN_SIGMA = 0.07  # band width (fraction of the ink height)

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

#: Pack artwork: ``images/`` holds a template per finished image written
#: to ``<out>/<pack>/`` from a pack's images
#: (``cards/<pack>/CardPack_{Back,Front}.png``). The material template
#: carries two pure-blue mask rectangles, the left one holding the back
#: image and the right one the front; the item template is a perspective
#: view of the pack whose single pure-blue mask is a slanted
#: quadrilateral that the front image is scaled, rotated and clipped to.
PACK_TEMPLATE = IMAGES_DIR / "CardPack_Material.png"
PACK_ITEM_TEMPLATE = IMAGES_DIR / "CardPack_Item.png"
PACK_BACK_NAME = "CardPack_Back.png"
PACK_FRONT_NAME = "CardPack_Front.png"
PACK_MATERIAL_NAME = "CardPack_Material.png"
PACK_ITEM_NAME = "CardPack_Item.png"

#: The white logo stamped on the pack's front, at the same placement in
#: the material and the item: its width as a fraction of the front's
#: width (centered horizontally) and its top inset as a fraction of the
#: front's height.
PACK_LOGO = IMAGES_DIR / "Logo_White.png"
PACK_LOGO_WIDTH = 0.6
PACK_LOGO_TOP = 0.04

#: The item mask's corners are pulled this many px outward before the
#: perspective warp: the warped front then over-covers the mask's
#: anti-aliased edge (the mask clip trims it back), so no dark fringe
#: shows where the warp falls a pixel short of the blue.
PACK_ITEM_MARGIN = 3

#: The item's front carries a thin dark gradient along its bottom
#: border, biased toward the bottom-right corner: the strip hugs
#: the bottom edge (:data:`PACK_BOTTOM_BAND` of the face height)
#: and fades quadratically away from the edge, so the face above
#: the strip is untouched; within the strip, the brightness falls
#: along the edge from the bottom-left (down to
#: :data:`PACK_BOTTOM_BIAS` of the corner dip) to the bottom-right
#: corner, which drops to 1 - :data:`PACK_BOTTOM_SHADE` of its
#: normal brightness. The shading is multiplicative (a plain
#: gradient), so the art's texture is preserved everywhere — dark
#: regions darken in proportion and are never crushed to flat
#: black.
PACK_BOTTOM_SHADE = 0.85
PACK_BOTTOM_BAND = 0.05
PACK_BOTTOM_BIAS = 0.45


class GenerationError(RuntimeError):
    """A card definition could not be rendered or composed."""


def generate() -> None:
    """Render and composite the selected (or all) card definitions."""
    args = _parse_args()
    draft = args.draft
    out_dir = DRAFT_DIR if draft else OUTPUT_DIR
    try:
        _generate(
            args.paths,
            args.jobs,
            DRAFT_PRESET if draft else DEFAULT_PRESET,
            DRAFT_SCALE if draft else DEFAULT_SCALE,
            out_dir,
        )
    except GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

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

        expansion = metadata.expansion(set_dir.stem, cards)
        pack = metadata.pack(set_dir.stem)
        bundle = metadata.bundle(set_dir.stem, items=[pack], expansions=[expansion])

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


def _stored_hash(out_path: Path) -> str | None:
    """The SOURCE_HASH_KEY embedded in a finished card, or None when
    the file carries no readable tag (older cards, corrupt files)."""
    if out_path.suffix == ".png":
        try:
            with Image.open(out_path) as image:
                return image.text.get(SOURCE_HASH_KEY)
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
    (sorted for deterministic output). Explicit paths are resolved against
    the repo root, must be files that live under :data:`CARDS_DIR`, are
    de-duplicated and returned in the given order.
    """
    if not paths:
        return sorted(CARDS_DIR.rglob("*.json"))
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


def _read_exact(stream: "io.BufferedReader", n: int) -> bytes:
    """Read exactly *n* bytes from *stream*; fewer only at end-of-stream.

    ``BufferedReader.read`` may return a partial chunk, so this loops until
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
    return b"".join(chunks)


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
    parts: _NameLayers | None,
    composite_workers: int,
    first_frame: list[Image.Image],
) -> Iterator[Image.Image]:
    """Composite the viewer's raw RGBA stdout frames and yield them in order.

    ``--stdout`` writes each frame as a contiguous ``width * height * 4`` byte
    block of raw RGBA, in presentation order. Frames are decoded and
    composited over *base* (and the name stack, if any) in a sliding window of
    *composite_workers* threads — Pillow releases the GIL in its raster ops, so
    the reader stays ahead of the encode and the cores stay busy — and yielded
    in presentation order. At most ~2x the worker count of frames are in memory
    at once. The first composited frame is appended to *first_frame*. When the
    stream ends (or the consumer stops), the viewer is reaped and a non-zero
    exit surfaced.
    """
    width, height = size
    frame_bytes = width * height * 4
    assert viewer.stdout is not None
    stdout = viewer.stdout

    def composite(data: bytes) -> Image.Image:
        frame = Image.frombytes("RGBA", (width, height), data)
        art = _composite_frame(frame, base)
        return _apply_name(art, parts) if parts is not None else art

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


def _with_logo(base: Image.Image, logo: Image.Image, margin: int) -> Image.Image:
    """Return a copy of *base* with *logo* stamped at the bottom right."""
    canvas = base.copy()
    canvas.alpha_composite(
        logo, (base.width - logo.width - margin, base.height - logo.height - margin)
    )
    return canvas


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
    left, top, right, bottom = probe.getbbox()
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


def _italicize(image: Image.Image, anchor_y: float = 0.0) -> Image.Image:
    """Shear *image* into italics. Row *anchor_y* stays in place and the
    rows below it shift left, so the top of the text leans right.
    Bilinear resampling keeps the slanted edges anti-aliased."""
    return image.transform(
        image.size,
        Image.AFFINE,
        (1, SUBTITLE_SHEAR, -SUBTITLE_SHEAR * anchor_y, 0, 1, 0),
        resample=Image.BILINEAR,
    )


def _name_inset(padding: int) -> int:
    """The title's inset from the card's edges: 1.5x the padding, like
    the logo (LOGO_PADDING_FACTOR). The corner subtitle keeps the
    plain padding."""
    return round(LOGO_PADDING_FACTOR * padding)


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


def _trail_color(region: Image.Image) -> tuple[int, int, int]:
    """The trail tint for a frame: the art's own hue at a fixed dark
    luminance (a tinted shadow, not a glow). Black when the region
    has no readable art."""
    hue, sat, luma = _sample_context(region)
    if luma is None:
        return TRAIL_FALLBACK
    return _set_luma(hue, sat, TRAIL_TARGET_LUMA)


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


def _shift_mask(mask: Image.Image, delta: tuple[int, int]) -> Image.Image:
    """*mask* shifted by *delta* (a negative delta drags the ink
    down-right)."""
    dx, dy = delta
    if dx == 0 and dy == 0:
        return mask
    return mask.transform(mask.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy))


class _NameLayers:
    """The static parts of the name stack (one per card)."""

    def __init__(
        self,
        metal_box: tuple[int, int, int, int],
        metal_alpha: Image.Image,
        trail: Image.Image | None,
        sub_trail: Image.Image | None,
        sub_top: Image.Image | None,
        sample_box: tuple[int, int, int, int],
        corner_sample_box: tuple[int, int, int, int],
    ) -> None:
        self.metal_box = metal_box
        self.metal_alpha = metal_alpha
        self.trail = trail
        self.sub_trail = sub_trail
        self.sub_top = sub_top
        self.sample_box = sample_box
        self.corner_sample_box = corner_sample_box


def _name_layers(
    size: tuple[int, int], name: str, subtitle: str, padding: int
) -> _NameLayers:
    """Build the static name-stack layers for a card of *size*.

    The RGB tints are per-frame (the trail tint and the metallic
    gradient's bottom lean track the scene), so this stores the masks
    and geometry; :func:`_apply_name` does the per-frame compositing.
    """
    font_size = _name_font_size(name, round(padding * NAME_SIZE_FACTOR))
    font = ImageFont.truetype(str(FONT_NAME), font_size)
    font.set_variation_by_axes([NAME_WEIGHT])
    left, top, bottom = _text_ink_offsets(name, font)
    inset = _name_inset(padding)

    title_mask = Image.new("L", size, 0)
    ImageDraw.Draw(title_mask).text(
        (inset - left, inset - top), name, font=font, fill=255
    )
    sub_mask = None
    sub_trail = None
    sub_top = None
    if subtitle:
        sub_size = _subtitle_font_size(subtitle, padding)
        # Sheared into an oblique at SUBTITLE_SUPERSAMPLE times the
        # final size and downscaled (see SUBTITLE_SUPERSAMPLE), so the
        # slanted edges stay anti-aliased without softening.
        ss = SUBTITLE_SUPERSAMPLE
        sub_font = ImageFont.truetype(str(FONT_NAME), sub_size * ss)
        sub_font.set_variation_by_axes([NAME_WEIGHT])
        sub_left, sub_top_off, sub_bottom = _text_ink_offsets(subtitle, sub_font)
        ink_h = sub_bottom - sub_top_off
        drift = round(SUBTITLE_SHEAR * ink_h)
        m4 = ((drift + ss - 1) // ss) * ss
        region = Image.new(
            "L", (round(sub_font.getlength(subtitle)) + m4 + 1, ink_h + 1), 0
        )
        ImageDraw.Draw(region).text(
            (m4 - sub_left, -sub_top_off), subtitle, font=sub_font, fill=255
        )
        w4 = (region.width + ss - 1) // ss * ss
        h4 = (region.height + ss - 1) // ss * ss
        padded = region
        if (region.width, region.height) != (w4, h4):
            padded = Image.new("L", (w4, h4), 0)
            padded.paste(region, (0, 0))
        small = _italicize(padded, 0).resize((w4 // ss, h4 // ss), Image.BILINEAR)
        # Corner variant: the text sits in the top-right corner,
        # right-aligned and inset by the card's own padding (the
        # title's 1.5x inset stays title-only).
        bbox = small.getbbox()
        px, py = size[0] - padding - bbox[2], padding - bbox[1]
        sub_mask = Image.new("L", size, 0)
        sub_mask.paste(255, (px, py, px + small.width, py + small.height), small)
        # The subtitle's own, shorter trail (same diagonal union as
        # the title's).
        sub_trail = Image.new("L", size, 0)
        for t in range(1, SUBTITLE_TRAIL_OFFSET + 1):
            sub_trail.paste(
                255, (0, 0, size[0], size[1]), _shift_mask(sub_mask, (t, t))
            )
        sub_top = _tint_layer(sub_mask, NAME_TEXT_COLOR, 1.0)

    # Title trail: extruded depth — the union of the text shifted one
    # step at a time along the diagonal, so every trail pixel touches
    # glyph ink (reads as 3D depth off the edges, not a detached
    # projection).
    trail = Image.new("L", size, 0)
    for t in range(1, NAME_TRAIL_OFFSET + 1):
        trail.paste(255, (0, 0, size[0], size[1]), _shift_mask(title_mask, (t, t)))

    # Title core: a vertical metal gradient whose bottom leans into
    # the per-frame trail tint — the RGB is built per frame in
    # _apply_name; only the geometry and the alpha are static.
    metal_box = title_mask.getbbox()
    metal_alpha = title_mask

    # Sample the art behind the name: the corner boxes the text sits
    # inside (top-left for the title, top-right for the corner
    # subtitle).
    box = (
        0,
        0,
        min(size[0], round(padding * NAME_SAMPLE_W)),
        min(size[1], round(padding * NAME_SAMPLE_H)),
    )
    corner_box = (
        max(0, size[0] - round(padding * NAME_SAMPLE_W)),
        0,
        size[0],
        min(size[1], round(padding * NAME_SAMPLE_H)),
    )
    return _NameLayers(
        metal_box, metal_alpha, trail, sub_trail, sub_top, box, corner_box
    )


def _apply_name(art: Image.Image, parts: _NameLayers) -> Image.Image:
    """Stamp the name stack onto *art* (the frame composited over the
    base) and return the result.

    Per frame: the trail tint is sampled from the art behind the
    title, the corner subtitle's from the art behind it, and the
    metallic gradient's bottom leans into the title's tint — so the
    name tracks the scene of animated cards.
    """
    canvas = art
    trail_color = _trail_color(art.crop(parts.sample_box))
    if parts.trail is not None:
        canvas.alpha_composite(_tint_layer(parts.trail, trail_color, TRAIL_ALPHA))
    if parts.sub_trail is not None:
        corner_color = _trail_color(art.crop(parts.corner_sample_box))
        canvas.alpha_composite(_tint_layer(parts.sub_trail, corner_color, TRAIL_ALPHA))

    # Title core: a vertical metal gradient — the text color at the
    # ink's top leaning into this frame's trail tint at the bottom
    # (METAL_TRAIL_MIX), with the bright sheen band.
    x0, y0, x1, y1 = parts.metal_box
    bottom = tuple(
        round(
            NAME_TEXT_COLOR[i] + METAL_TRAIL_MIX * (trail_color[i] - NAME_TEXT_COLOR[i])
        )
        for i in range(3)
    )
    h = y1 - y0 + 1
    col = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        sheen = METAL_SHEEN_DELTA * math.exp(
            -((t - METAL_SHEEN_Y) ** 2) / (2 * METAL_SHEEN_SIGMA**2)
        )
        col.putpixel(
            (0, y),
            tuple(
                min(
                    255,
                    round(
                        NAME_TEXT_COLOR[i]
                        + (bottom[i] - NAME_TEXT_COLOR[i]) * t
                        + sheen
                    ),
                )
                for i in range(3)
            ),
        )
    grad = col.resize((x1 - x0 + 1, h), Image.NEAREST)
    metal = Image.new("RGB", canvas.size, bottom)
    metal.paste(grad, (x0, y0))
    layer = metal.convert("RGBA")
    layer.putalpha(parts.metal_alpha)
    canvas.alpha_composite(layer)
    if parts.sub_top is not None:
        canvas.alpha_composite(parts.sub_top)
    return canvas


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
        (round(region.width / ss), round(region.height / ss)), Image.LANCZOS
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


def _composite_frame(frame: Image.Image, base: Image.Image) -> Image.Image:
    """Composite *frame* over the pre-stamped *base*; the result is RGBA."""
    canvas = base.copy()
    if frame.mode != "RGBA":
        frame = frame.convert("RGBA")
    canvas.alpha_composite(frame)
    return canvas


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
    name: str,
    subtitle: str,
    framerate: int,
    ffmpeg_threads: int,
    composite_workers: int,
    preset: str,
    scale: float,
    out_base: Path,
    source_hash: str,
) -> Path:
    """Render *json_path* via the viewer's ``--stdout`` raw stream and write
    the final PNG, or the MP4 alongside its first frame as a PNG.

    Nothing intermediate touches the disk: the viewer's raw RGBA frames are
    piped straight into the in-memory compositing and (for animations) the
    ffmpeg encode. Only the finished card is written (atomically). A failure
    at any stage surfaces as a :class:`GenerationError` so the caller can
    re-render the card from scratch.
    """
    base = _fit_background(background, size)
    base = _with_logo(base, _scale_logo(logo, size[0]), margin)
    base = _with_copyright(base, padding, copyright_color)
    parts = _name_layers(size, name, subtitle, padding) if (name or subtitle) else None

    # Spawn the viewer streaming raw RGBA frames to stdout (no intermediate
    # files). stderr is drained in a thread so it never blocks the viewer.
    try:
        viewer = subprocess.Popen(
            [VIEWER, "--stdout", str(json_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise GenerationError(f"could not run {VIEWER!r}: {exc}") from exc
    assert viewer.stderr is not None
    drain = _PipeDrain(viewer.stderr)
    first_frame: list[Image.Image] = []
    composited = _stream_composited(
        viewer, drain, json_path, size, base, parts, composite_workers, first_frame
    )

    out_path = _card_out_path(out_base, json_path, "mp4" if animated else "png")
    try:
        if animated:
            tmp_path = out_path.with_name(out_path.name + ".part")
            try:
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
                if not first_frame:
                    raise GenerationError(
                        f"{VIEWER} produced no frames for {json_path.name}"
                    )
            except Exception:
                tmp_path.unlink(missing_ok=True)
                raise
            tmp_path.replace(out_path)
            # The animation's first frame, alongside the mp4 (the same
            # composited frame, so it matches the mp4's opening frame
            # exactly).
            _save_atomic(
                first_frame[0].convert("RGB"),
                _card_out_path(out_base, json_path, "png"),
                source_hash,
            )
        else:
            # A single frame: take it from the stream and write it.
            frame = next(composited, None)
            if frame is None:
                raise GenerationError(
                    f"{VIEWER} produced no frame for {json_path.name}"
                )
            _save_atomic(frame.convert("RGB"), out_path, source_hash)
    finally:
        # Stop consuming and make sure the viewer is reaped (its ``finally``
        # runs, waiting on / killing the process and checking its exit).
        composited.close()

    return out_path


def _card_out_path(out_base: Path, json_path: Path, suffix: str) -> Path:
    """The flat output path for a card definition: the card's
    directory is folded into the filename, so
    ``cards/<set>/<card>/<variant>.json`` renders to
    ``<out_base>/<set>/<card>_<variant>.<suffix>`` (deeper nesting,
    if ever used, is folded the same way, one dash per directory)."""
    card_rel = json_path.parent.relative_to(CARDS_DIR)
    return (
        out_base
        / card_rel.parts[0]
        / f"{'_'.join(card_rel.parts[1:])}_{json_path.stem}.{suffix}"
    )


def _process_card(
    json_path: Path,
    ffmpeg_threads: int = 1,
    composite_workers: int = 4,
    preset: str = DEFAULT_PRESET,
    scale: float = DEFAULT_SCALE,
    out_base: Path = OUTPUT_DIR,
) -> tuple[Path, bool]:
    """Render, composite and encode a single card definition.

    Returns ``(out_path, skipped)``; *skipped* is True when the output
    already exists and the definition hash it embeds matches the current
    one (nothing was re-rendered).
    """
    json_path = json_path.resolve()
    card = _load_card(json_path)
    background = Image.open(_background_path(card, json_path)).convert("RGBA")

    logo_path = LOGO_PATHS[bool(card.get("invert_logo", False))]
    if not logo_path.is_file():
        raise GenerationError(f"logo not found: {logo_path}")
    logo = Image.open(logo_path).convert("RGBA")
    if not FONT.is_file():
        raise GenerationError(f"font not found: {FONT}")
    if not FONT_NAME.is_file():
        raise GenerationError(f"font not found: {FONT_NAME}")
    if json_path.stem in NO_NAME_STEMS:
        # Full-art presentations never carry the card name
        name, subtitle = "", ""
    else:
        if "title" not in card:
            raise GenerationError(f"{json_path.name}: missing 'title'")
        name = str(card["title"])
        subtitle = str(card.get("subtitle", ""))
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
        return out_path, True
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # The GPU is shared with other tenants, so failures here can be
    # transient (render error, truncated frame stream, encode error); the
    # card is re-rendered from scratch up to RENDER_ATTEMPTS times before
    # giving up. Nothing intermediate is written to disk in between.
    for attempt in range(1, RENDER_ATTEMPTS + 1):
        try:
            return (
                _render_and_finish(
                    json_path,
                    size,
                    animated,
                    background,
                    logo,
                    margin,
                    padding,
                    copyright_color,
                    name,
                    subtitle,
                    framerate,
                    ffmpeg_threads,
                    composite_workers,
                    preset,
                    scale,
                    out_base,
                    source_hash,
                ),
                False,
            )
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


def _pack_mask(template: Image.Image) -> Image.Image:
    """A binary mask of the template's pure-blue placeholder pixels."""
    r = template.getchannel("R").point(lambda v: 255 if v == 0 else 0)
    g = template.getchannel("G").point(lambda v: 255 if v == 0 else 0)
    b = template.getchannel("B").point(lambda v: 255 if v == 255 else 0)
    return ImageChops.darker(ImageChops.darker(r, g), b)


def _pack_item_mask(template: Image.Image, threshold: int = 15) -> Image.Image:
    """The item template's blue region including its anti-aliased fringe.

    The pure-blue placeholder sits on an opaque grey shadow and carries a
    1px near-blue edge (anti-aliasing) that is *not* pure blue, so a plain
    :func:`_pack_mask` would leave that rim behind. This mask is the
    blue-dominant pixels (blue channel above the brighter of red/green by
    *threshold*) restricted to a 1px dilation of the core, so it spans the
    core plus the fringe while keeping out the grey shadow and any
    isolated bluish specks elsewhere."""
    r = template.getchannel("R")
    g = template.getchannel("G")
    b = template.getchannel("B")
    ring = _pack_mask(template).filter(ImageFilter.MaxFilter(3))
    excess = ImageChops.difference(b, ImageChops.lighter(r, g))
    bluish = excess.point(lambda v: 255 if v >= threshold else 0)
    return ImageChops.darker(bluish, ring)


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
    """``cards/`` subdirectories carrying both pack images (the pack
    material's inputs)."""
    return sorted(
        pack_dir
        for pack_dir in CARDS_DIR.iterdir()
        if pack_dir.is_dir()
        and (pack_dir / PACK_BACK_NAME).is_file()
        and (pack_dir / PACK_FRONT_NAME).is_file()
    )


def _pack_hash(template: Path, *images: Path) -> str:
    """The source hash of a finished pack image: the SHA-256 of its
    template and input images — every input byte the result depends on."""
    digest = hashlib.sha256()
    for path in (template, *images):
        if not path.is_file():
            raise GenerationError(f"pack template or image not found: {path}")
        digest.update(path.read_bytes())
    return digest.hexdigest()


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


def _pack_item_corners(mask: Image.Image) -> tuple[tuple[int, int], ...]:
    """The mask's four corners (top-left, top-right, bottom-right, bottom-
    left) as its diagonal extremes: the pixels minimizing/maximizing
    ``x + y`` (top-left / bottom-right) and ``x - y`` (bottom-left /
    top-right)."""
    data = mask.convert("L").tobytes()
    width, height = mask.size
    tl = tr = br = bl = None
    tl_s = math.inf
    br_s = tr_s = -math.inf
    bl_s = math.inf
    for y in range(height):
        row = data[y * width : (y + 1) * width]
        for x, value in enumerate(row):
            if value:
                s, d = x + y, x - y
                if s < tl_s:
                    tl_s, tl = s, (x, y)
                if s > br_s:
                    br_s, br = s, (x, y)
                if d > tr_s:
                    tr_s, tr = d, (x, y)
                if d < bl_s:
                    bl_s, bl = d, (x, y)
    if tl is None:
        raise GenerationError("pack item template carries no pure-blue mask")
    return tl, tr, br, bl


def _pack_item_band(
    corners: tuple[tuple[float, float], ...], front: tuple[int, int]
) -> tuple[float, ...]:
    """The ``Image.PERSPECTIVE`` band mapping the four *corners* (in
    template order: top-left, top-right, bottom-right, bottom-left) to
    the front's corners ``(0, 0), (W, 0), (W, H), (0, H)`` — the
    perspective that projects the front onto the item's slanted
    quadrilateral. The four point correspondences exactly determine the
    8 degrees of freedom (with the last coefficient fixed to 1)."""
    fw, fh = front
    rows = []
    for (x, y), (sx, sy) in zip(corners, ((0, 0), (fw, 0), (fw, fh), (0, fh))):
        rows.append([x, y, 1, 0, 0, 0, -sx * x, -sx * y, sx])
        rows.append([0, 0, 0, x, y, 1, -sy * x, -sy * y, sy])
    h11, h12, h13, h21, h22, h23, h31, h32 = _solve_linear(rows)
    return h11, h12, h13, h21, h22, h23, h31, h32, 1.0


def _process_pack_material(pack_dir: Path, out_base: Path) -> tuple[Path, bool]:
    """Composite a pack's images onto the material template.

    The template's pure-blue mask rectangles mark the paste regions: the
    left one holds the pack's back image, the right one its front, and
    the white logo is composited onto the front unslanted (the material
    is the flat view of the pack) at the item's placement:
    :data:`PACK_LOGO_WIDTH` the front's width, centered,
    :data:`PACK_LOGO_TOP` the front's height down. The finished material
    is written to ``<out>/<pack>/CardPack_Material.png`` (atomically,
    with the SHA-256 of the template, both images and the logo
    embedded, like a finished card); returns ``(out_path, skipped)``,
    where *skipped* is True when the output already exists and its
    stored hash matches the current inputs.
    """
    pack_dir = pack_dir.resolve()
    back_path = pack_dir / PACK_BACK_NAME
    front_path = pack_dir / PACK_FRONT_NAME
    source_hash = _pack_hash(PACK_TEMPLATE, back_path, front_path, PACK_LOGO)
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
        for path, rect in ((back_path, rects[0]), (front_path, rects[1])):
            with Image.open(path) as opened:
                image = opened.convert("RGBA")
            target = (rect[2] - rect[0], rect[3] - rect[1])
            if image.size != target:
                image = image.resize(target, Image.Resampling.LANCZOS)
            template.alpha_composite(image, (rect[0], rect[1]))
        # The white logo on the front, at the item's placement
        # (unslanted, since the material is the flat view):
        # PACK_LOGO_WIDTH the front's width, centered, PACK_LOGO_TOP the
        # front's height down.
        rx0, ry0, rx1, ry1 = rects[1]
        rw, rh = rx1 - rx0, ry1 - ry0
        with Image.open(PACK_LOGO) as opened:
            logo = opened.convert("RGBA")
        logo_w = round(PACK_LOGO_WIDTH * rw)
        logo = logo.resize(
            (logo_w, round(logo_w * logo.height / logo.width)),
            Image.Resampling.LANCZOS,
        )
        template.alpha_composite(
            logo, (rx0 + (rw - logo_w) // 2, ry0 + round(PACK_LOGO_TOP * rh))
        )
        final = template.convert("RGB")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _save_atomic(final, out_path, source_hash)
    return out_path, False


def _bottom_shade(front: Image.Image) -> Image.Image:
    """Darken a thin strip along the front's bottom border, biased
    toward the bottom-right corner: the strip hugs the bottom edge
    (:data:`PACK_BOTTOM_BAND` of the face height), fading
    quadratically away from the edge (zero slope at the strip's
    top, so no seam shows); within the strip, the brightness falls
    along the edge from the bottom-left (down to
    :data:`PACK_BOTTOM_BIAS` of the corner dip) to the bottom-right
    corner (down to 1 - :data:`PACK_BOTTOM_SHADE` of the normal
    brightness) — multiplicative, so the art's texture is
    preserved everywhere. Applied before the perspective warp, so
    it rides the warped face's bottom border."""
    width, height = front.size
    # Per-axis ramps; the dip is their product, so it hugs the
    # bottom edge, biased to the right, fading away from the edge.
    x = [
        round(
            255
            * PACK_BOTTOM_SHADE
            * (PACK_BOTTOM_BIAS + (1.0 - PACK_BOTTOM_BIAS) * i / (width - 1))
        )
        for i in range(width)
    ]
    y0 = round((1.0 - PACK_BOTTOM_BAND) * height)
    span = max(1, height - 1 - y0)
    y = [0 if j <= y0 else round(255 * ((j - y0) / span) ** 2) for j in range(height)]
    ax = Image.new("L", (width, 1))
    ax.putdata(x)
    ay = Image.new("L", (1, height))
    ay.putdata(y)
    ax = ax.resize((width, height), Image.Resampling.NEAREST)
    ay = ay.resize((width, height), Image.Resampling.NEAREST)
    # factor = 255 * (1 - SHADE * a * b) = 255 - ax*ay/255
    factor = ImageChops.invert(ImageChops.multiply(ax, ay))
    return Image.merge(
        "RGBA",
        [ImageChops.multiply(front.getchannel(c), factor) for c in "RGB"]
        + [front.getchannel("A")],
    )


def _process_pack_item(pack_dir: Path, out_base: Path) -> tuple[Path, bool]:
    """Composite a pack's front image onto the item template.

    The white logo (:data:`PACK_LOGO_WIDTH` the front's width, centered,
    :data:`PACK_LOGO_TOP` the front's height down — the material's
    placement) is slanted on its own at 2x and composited over the
    front, which is warped at 1x — so only the logo's edge is
    anti-aliased by supersampling while the front's detail is left
    untouched. The front's bottom border is darkened with a thin
    gradient first (:func:`_bottom_shade`), biased toward the
    bottom-right corner. The
    template's pure-blue mask is a
    slanted quadrilateral (the item is a slightly rotated 3D view of the
    pack), so the front is perspective-warped to it — its four corners
    mapped to the mask's four corners. That is the faithful 3D projection:
    it shows the whole front (no cropping, unlike a flat rotate-and-scale)
    and fills the mask exactly. The mask corners are pulled
    :data:`PACK_ITEM_MARGIN` px outward first so the warp over-covers the
    mask's anti-aliased edge. The front is given the quad's true coverage
    as its alpha and composited over the placeholder's background (the
    grey shadow, with the blue edge un-blended back to grey) so the
    slanted edge is anti-aliased rather than a hard binary cut. The
    finished item keeps
    the template's transparency and is written to
    ``<out>/<pack>/CardPack_Item.png`` (atomically, with the SHA-256 of
    the template and the front embedded, like a finished card); returns
    ``(out_path, skipped)``.
    """
    pack_dir = pack_dir.resolve()
    front_path = pack_dir / PACK_FRONT_NAME
    source_hash = _pack_hash(PACK_ITEM_TEMPLATE, front_path, PACK_LOGO)
    out_path = out_base / pack_dir.relative_to(CARDS_DIR) / PACK_ITEM_NAME
    if out_path.is_file() and _stored_hash(out_path) == source_hash:
        return out_path, True
    with Image.open(PACK_ITEM_TEMPLATE) as opened:
        template = opened.convert("RGBA")
        with Image.open(front_path) as opened:
            front = opened.convert("RGBA")
        # Shade a thin strip along the front's bottom border
        # (biased toward the bottom-right corner) before warping, so
        # the gradient rides the warped face's bottom edge (the logo
        # sits well above it, so it is unaffected).
        front = _bottom_shade(front)
        # The logo is NOT composited onto the front before warping: the
        # front's own art is warped once at 1x (never supersampled), and
        # the logo is slanted on its own and composited on top. That way
        # only the logo's edge gets the supersampling anti-aliasing while
        # the front's detail is left untouched.
        logo = Image.open(PACK_LOGO).convert("RGBA")
        fw, fh = front.size
        logo_w = round(PACK_LOGO_WIDTH * fw)
        logo_h = round(logo_w * logo.height / logo.width)
        logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
        logo_pos = ((fw - logo_w) // 2, round(PACK_LOGO_TOP * fh))
        mask = _pack_item_mask(template)
        corners = _pack_item_corners(mask)
        # Pull each corner outward from the quad's center so the warped
        # front over-covers the mask's anti-aliased edge.
        cx = sum(p[0] for p in corners) / 4
        cy = sum(p[1] for p in corners) / 4
        expanded = []
        for x, y in corners:
            dist = math.hypot(x - cx, y - cy)
            expanded.append(
                (
                    x + PACK_ITEM_MARGIN * (x - cx) / dist,
                    y + PACK_ITEM_MARGIN * (y - cy) / dist,
                )
            )
        # The front art is warped once, at 1x: its detail is never
        # supersampled.
        band = _pack_item_band(tuple(expanded), front.size)
        warped = front.transform(
            template.size, Image.PERSPECTIVE, band, resample=Image.BICUBIC
        ).convert("RGBA")
        # The logo is slanted on its own at 2x and downscaled, so its
        # anti-aliasing survives the slant. It sits on a front-sized
        # transparent canvas at the logo's position; the 2x band (built
        # from 2x corners, the same quad in the 2x output space) warps it
        # onto the same face as the front.
        logo_layer = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
        logo_layer.alpha_composite(logo, logo_pos)
        band2 = _pack_item_band(
            tuple((2 * x, 2 * y) for x, y in expanded), (fw * 2, fh * 2)
        )
        warped_logo = (
            logo_layer.resize((fw * 2, fh * 2), Image.LANCZOS)
            .transform(
                (template.size[0] * 2, template.size[1] * 2),
                Image.PERSPECTIVE,
                band2,
                resample=Image.BICUBIC,
            )
            .resize(template.size, Image.LANCZOS)
            .convert("RGBA")
        )
        warped.alpha_composite(warped_logo)
        # Give the front the quad's true coverage as its alpha so the slanted
        # edge is anti-aliased instead of a hard binary cut: where the
        # placeholder is translucent (the edge against transparency) that is
        # its alpha; where it is an opaque near-blue (the edge blended into
        # the grey shadow) it is the blue fraction of that blend.
        alpha = template.getchannel("A")
        blueness = ImageChops.difference(
            template.getchannel("B"),
            ImageChops.lighter(template.getchannel("R"), template.getchannel("G")),
        )
        warped.putalpha(ImageChops.darker(ImageChops.darker(alpha, blueness), mask))
        # Reveal the background the front composites over: keep the grey
        # shadow, clear the placeholder, and un-blend the opaque near-blue
        # edge back to the grey it was mixed from (fringe = t*blue + (1-t)*
        # grey, so grey = (fringe - t*blue) / (1-t)).
        background = template.copy()
        background.putalpha(ImageChops.multiply(alpha, ImageChops.invert(mask)))
        blue_d = mask.tobytes()
        blue_n = blueness.tobytes()
        alpha_n = alpha.tobytes()
        src = template.load()
        dst = background.load()
        width, height = template.size
        for y in range(height):
            row = y * width
            for x in range(width):
                i = row + x
                if blue_d[i] and alpha_n[i] == 255 and blue_n[i] < 255:
                    inv = 255 - blue_n[i]
                    r, g, b, _ = src[x, y]
                    dst[x, y] = (
                        round(r * 255 / inv),
                        round(g * 255 / inv),
                        round((b - blue_n[i]) * 255 / inv),
                        255,
                    )
        background.alpha_composite(warped)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _save_atomic(background, out_path, source_hash)
    return out_path, False


def _default_jobs() -> int:
    """A sensible default pool size: up to 8 cards at once, 1 per 4 cores."""
    return min(8, max(1, (os.cpu_count() or 4) // 4))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render and composite Nikke trading cards from cards/"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        metavar="CARD_JSON",
        help="card definition(s) to generate; default: all under cards/",
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


def _generate(
    paths: list[Path],
    jobs: int,
    preset: str,
    scale: float,
    out_base: Path,
) -> None:
    """Process the selected cards in a pool of worker processes."""
    _require_executable(VIEWER)
    _require_executable(ENCODER)
    _require_executable(PROBER)
    card_configs = _find_card_configs(paths)
    # An explicit selection renders those cards only; a full run also
    # produces each pack's artwork images (material and item).
    pack_dirs: list[Path] = [] if paths else _find_pack_dirs()
    total = len(card_configs) + 2 * len(pack_dirs)
    # Split the cores available to each card between the stages that run
    # in parallel: the frame compositing and the ffmpeg encode.
    per_card = (os.cpu_count() or 1) // max(1, min(jobs, total))
    ffmpeg_threads = max(2, min(MAX_STAGE_THREADS, per_card // 2))
    composite_workers = max(2, min(MAX_STAGE_THREADS, per_card - ffmpeg_threads))
    start = time.monotonic()
    notes = []
    if preset != DEFAULT_PRESET:
        notes.append(f"x264 preset '{preset}'")
    if scale != 1.0:
        notes.append(f"{scale:g}x resolution")
    notes_text = f", {', '.join(notes)} (draft)" if notes else ""
    what = f"{len(card_configs)} card(s)" + (
        f" and {2 * len(pack_dirs)} pack image(s)" if pack_dirs else ""
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
        futures: dict[Future[tuple[Path, bool]], Path] = {
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
        futures.update(
            {
                pool.submit(
                    _process_pack_material, pack_dir, out_base
                ): pack_dir.relative_to(CARDS_DIR) / PACK_MATERIAL_NAME
                for pack_dir in pack_dirs
            }
        )
        futures.update(
            {
                pool.submit(
                    _process_pack_item, pack_dir, out_base
                ): pack_dir.relative_to(CARDS_DIR) / PACK_ITEM_NAME
                for pack_dir in pack_dirs
            }
        )
        for future in as_completed(futures):
            done += 1
            label = futures[future]
            try:
                out_path, was_skipped = future.result()
                if was_skipped:
                    skipped += 1
                    print(
                        f"[{done}/{total}] {label} unchanged, "
                        f"kept {out_path.relative_to(REPO_ROOT)}",
                        flush=True,
                    )
                else:
                    print(
                        f"[{done}/{total}] {label} -> {out_path.relative_to(REPO_ROOT)}",
                        flush=True,
                    )
            except Exception as exc:
                # Let the other cards finish; failures are reported (and the
                # run exits non-zero) once everything has had its retries.
                failures.append((label, exc))
                print(
                    f"[{done}/{total}] {label} FAILED: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
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
