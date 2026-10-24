"""Render and composite Nikke trading cards.

Walks :mod:`cards` for card definitions (``*.json``), renders each one with
the ``nikke-viewer`` executable, composites every rendered frame on top of
the card's ``background``, stamps the matching logo from ``images/`` at
the bottom right and the copyright line at the bottom left, and overlays
the card name on top of the art, per frame: the title at the top left
(metallic vertical gradient, diagonal trail) and the subtitle in the
top-right corner (italic, with its own trail). The trails and the
gradient's bottom lean are tinted with the color of the art behind the
text each frame, so animated cards track the scene. The ``Goddess`` and ``Classified``
variants are generated without any
card name. Packs (``cards/`` subdirectories carrying an
``Expansion.json``) additionally get their two artwork images, built from
the templates in ``images/``. The pack's front and back are composed on the
fly (by :mod:`nikke_reborn.pack`) from the expansion's metadata — the front
is its ``background`` with its featured NIKKES (``pack``) drawn over it and
its ``logo`` when the expansion names a placement; the back is the same
``background`` resized and left-cropped — and neither is stored. The
material (``CardPack_Material.png``) has two pure-blue mask rectangles
holding the composed back (left) and front (right); the item
(``CardPack_Item.png``) is the pack's mesh
(``assets/CardPackStatic_Mesh.asset``) textured with the finished
material and rendered by the ``unity-viewer`` executable with the
model rotation and camera zoom/pan from
``assets/CardPackStatic_Mesh.json`` — so it is generated after the
material, which it reads from disk. The box (``CardBox_Material.png``)
holds the same composed front in the blue rectangle of its three mask
rectangles (blue front, red top, green side); the top and side are still
placeholders, so the box's item is not rendered yet. The finished results are
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
UNITY_VIEWER = "unity-viewer"
ENCODER = "ffmpeg"
PROBER = "ffprobe"

#: Key of the embedded definition hash in the finished cards (a PNG
#: text chunk, an MP4 tag): a card whose stored hash matches the
#: current definition is skipped instead of re-rendered.
SOURCE_HASH_KEY = "nikke-reborn-source"

DEFAULT_FRAMERATE = 60

#: Variant stems that never carry the card name: the ``Goddess`` and
#: ``Classified`` presentations are generated without title and subtitle.
NO_NAME_STEMS = frozenset({"Goddess", "Classified"})

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

#: Pack artwork: ``images/`` holds the material template, whose two
#: pure-blue mask rectangles hold the pack's back (left) and front
#: (right) — both composed on the fly (see :mod:`nikke_reborn.pack`) —
#: written to ``<out>/<pack>/CardPack_Material.png``. The item
#: (``CardPack_Item.png``) is rendered with :data:`UNITY_VIEWER` from
#: :data:`PACK_MESH` textured with the finished material.
PACK_TEMPLATE = IMAGES_DIR / "CardPack_Material.png"
PACK_MATERIAL_NAME = "CardPack_Material.png"
PACK_ITEM_NAME = "CardPack_Item.png"
PACK_MESH = REPO_ROOT / "assets" / "CardPackStatic_Mesh.asset"

#: The item's viewer configuration (model rotation and camera zoom/pan
#: as a JSON file, exported by the viewer's GUI), passed to
#: :data:`UNITY_VIEWER` with ``--config``; it sits next to the mesh.
PACK_CONFIG = REPO_ROOT / "assets" / "CardPackStatic_Mesh.json"


#: The box's material template: its three solid mask rectangles mark the
#: paste regions — blue for the front (the same composition as the pack's
#: front), red for the top and green for the side (still placeholders).
#: The finished material is written to ``<out>/<pack>/CardBox_Material.png``.
BOX_TEMPLATE = IMAGES_DIR / "CardBox_Material.png"
BOX_MATERIAL_NAME = "CardBox_Material.png"


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
    overlay: Image.Image,
    overlay_pos: tuple[int, int],
    parts: _NameLayers | None,
    composite_workers: int,
    first_frame: list[Image.Image],
    composite_time: list[float],
    stream_end: list[float],
) -> Iterator[Image.Image]:
    """Composite the viewer's raw RGBA stdout frames and yield them in order.

    ``--stdout`` writes each frame as a contiguous ``width * height * 4`` byte
    block of raw RGBA, in presentation order. Frames are decoded and
    composited over *base*, then the *overlay* (the pre-stamped logo and
    copyright line) is stamped on top and the name stack applied, if any, in
    a sliding window of *composite_workers* threads — Pillow releases the GIL
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

    def composite(data: bytes) -> Image.Image:
        started = time.perf_counter()
        frame = Image.frombytes("RGBA", (width, height), data)
        art = _composite_frame(frame, base)
        art.alpha_composite(overlay, overlay_pos)
        result = _apply_name(art, parts) if parts is not None else art
        with time_lock:
            composite_time[0] += time.perf_counter() - started
        return result

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


def _logo_copyright_overlay(
    size: tuple[int, int],
    logo: Image.Image,
    margin: int,
    padding: int,
    color: tuple[int, int, int, int],
) -> tuple[Image.Image, tuple[int, int]]:
    """Pre-stamp the logo and the copyright line onto a transparent layer.

    Both stamps sit at the bottom of the card (bottom right and bottom
    left, at the same placement as when stamped directly), so the combined
    layer is cropped to its bounding box; the caller composites the crop
    onto each frame after the art is in place, keeping the stamps on top
    of the art for the price of one small strip per frame.

    Returns the cropped layer and the coordinates at which to composite it
    on a card of *size*.
    """
    width, height = size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay = _with_logo(overlay, _scale_logo(logo, width), margin)
    overlay = _with_copyright(overlay, padding, color)
    box = overlay.getbbox()
    assert box is not None, "the logo and copyright layer is empty"
    return overlay.crop(box), (box[0], box[1])


def _composite_frame(frame: Image.Image, base: Image.Image) -> Image.Image:
    """Composite *frame* over *base*; the result is RGBA."""
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
) -> tuple[Path, dict[str, float | None]]:
    """Render *json_path* via the viewer's ``--stdout`` raw stream and write
    the final PNG, or the MP4 alongside its first frame as a PNG.

    Nothing intermediate touches the disk: the viewer's raw RGBA frames are
    piped straight into the in-memory compositing and (for animations) the
    ffmpeg encode. Only the finished card is written (atomically). A failure
    at any stage surfaces as a :class:`GenerationError` so the caller can
    re-render the card from scratch.

    Returns the finished card's path and the stage timings in seconds —
    ``render`` (spawn until the frame stream is fully delivered),
    ``composite`` (the Pillow work summed across the worker threads) and
    ``encode`` (the ffmpeg wall time for animations, the PNG write for
    static cards). The stages overlap — the encode consumes frames while
    the viewer still renders and the compositing runs in its own threads —
    so the numbers are per-stage costs, not a sequential partition. A raw
    frame is far larger than the pipe buffer, so the viewer blocks on
    write until the reader drains: under load ``render`` therefore
    reflects the slowest downstream stage (usually the encode) as much as
    the viewer itself; for the viewer's own cost, run it with its stdout
    redirected to /dev/null.
    """
    base = _fit_background(background, size)
    # The logo and copyright line sit on top of the art, not under it:
    # pre-stamp them onto a transparent layer and let _stream_composited
    # apply it to each frame after the art is composited over the
    # background.
    overlay, overlay_pos = _logo_copyright_overlay(
        size, logo, margin, padding, copyright_color
    )
    parts = _name_layers(size, name, subtitle, padding) if (name or subtitle) else None
    composite_time: list[float] = [0.0]
    encode_time: float | None = None
    stream_end: list[float] = [0.0]

    # Spawn the viewer streaming raw RGBA frames to stdout (no intermediate
    # files). stderr is drained in a thread so it never blocks the viewer.
    render_started = time.perf_counter()
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
        viewer,
        drain,
        json_path,
        size,
        base,
        overlay,
        overlay_pos,
        parts,
        composite_workers,
        first_frame,
        composite_time,
        stream_end,
    )

    out_path = _card_out_path(out_base, json_path, "mp4" if animated else "png")
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
            encode_started = time.perf_counter()
            _save_atomic(frame.convert("RGB"), out_path, source_hash)
            encode_time = time.perf_counter() - encode_started
    finally:
        # Stop consuming and make sure the viewer is reaped (its ``finally``
        # runs, waiting on / killing the process and checking its exit).
        composited.close()
    # Measured to stream EOF (not to the reap, which happens after the
    # encode and the save), so the number covers the frame delivery only.
    render_seconds = (stream_end[0] or time.perf_counter()) - render_started

    return out_path, {
        "render": render_seconds,
        "composite": composite_time[0],
        "encode": encode_time,
    }


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
    if not FONT_NAME.is_file():
        raise GenerationError(f"font not found: {FONT_NAME}")
    if json_path.stem in NO_NAME_STEMS:
        # These presentations never carry the card name
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
                name,
                subtitle,
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
    the bottom) is the background center-cropped with the white logo
    top-right. The finished material is
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
        raise GenerationError(f"{UNITY_VIEWER} failed (exit {result.returncode}){detail}")
    with Image.open(tmp_path) as rendered:
        _save_atomic(rendered, out_path, source_hash)
    tmp_path.unlink(missing_ok=True)
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
    start = time.monotonic()
    # Compose each pack's fronts in the main process: its featured NIKKES
    # are GPU-rendered here, so a front is produced once per material that
    # needs it (the pack's front for the pack's material, the box's front —
    # a different size — for the box's material). They are transient —
    # composed on the fly from the expansion's metadata and never written
    # to disk. The fronts' inputs are hashed up front (without rendering
    # them), so the renders are skipped entirely when the material, the
    # item and the box's material are all already up to date.
    from nikke_reborn import box, expansion, pack

    material_needs: set[Path] = set()
    item_needs: set[Path] = set()
    box_needs: set[Path] = set()
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
        if material_ok and item_ok and box_ok:
            continue  # nothing changed for this pack; skip the fronts' renders
        if not material_ok:
            material_needs.add(pack_dir)
        if not item_ok:
            item_needs.add(pack_dir)
        if not box_ok:
            box_needs.add(pack_dir)
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
                box_fronts[pack_dir] = box.build_front(
                    pack_dir, data, box.front_size()
                )
                box_sides[pack_dir] = box.build_side(
                    pack_dir, data, box.side_size()
                )
                box_tops[pack_dir] = box.build_top(
                    pack_dir, data, box.top_size()
                )
                box_front_sources[pack_dir] = box_front_source
    total = len(card_configs) + len(material_needs) + len(item_needs) + len(box_needs)
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
        f" and {len(material_needs) + len(item_needs) + len(box_needs)} pack image(s)"
        if material_needs or item_needs or box_needs
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
        def report(future: Future[tuple[Path, bool]], label: Path) -> None:
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

        card_futures: dict[Future[tuple[Path, bool]], Path] = {
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
            ): box_label(pack_dir)
            for pack_dir in sorted(box_needs)
        }
        for future in as_completed(material_futures):
            pack_dir = material_futures[future]
            report(future, material_label(pack_dir))
            if future.exception() is not None:
                continue  # no material -> no item for this pack
            if pack_dir in item_needs:
                item_futures[
                    pool.submit(_process_pack_item, pack_dir, out_base)
                ] = item_label(pack_dir)
        for future in as_completed(box_futures):
            report(future, box_futures[future])
        for future in as_completed(card_futures):
            report(future, card_futures[future])
        for future in as_completed(item_futures):
            report(future, item_futures[future])
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
