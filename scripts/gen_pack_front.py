#!/usr/bin/env python3
"""Procedurally generate a pack's ``CardPack_Front.png`` from ``Expansion.json``.

This is the iteration workbench for the new pack-front pipeline. Instead of a
hand-made ``CardPack_Front.png``, the front is built from the expansion's
metadata:

* the ``pack`` field lists the NIKKES to feature (card-definition paths
  relative to the pack directory). The *first* one is the hero: it is centered
  in the front. The rest are placed behind it, to the left and right, at a
  lower scale, to read as a group in perspective/distance.
* Only ``nikke-viewer``'s output is used (the raw character render, not the
  finished card — no background fit, logo, name or copyright). When a featured
  NIKKE is animated, only its first frame is kept and the rest discarded.
* the ``background`` field is resized to the front's height and then
  center-cropped to the front's exact width.

The finished front is written to ``cards/<set>/CardPack_Front.png`` (replacing
the hand-made one), so the existing material and item composition consume it
unchanged. Unless ``--front-only`` is given, this script then runs the material
and item composition (via the package) so the full result is visible while
iterating — without re-rendering the set's cards.

Rendered first-frames are cached on disk (keyed by the card definition's hash)
so repeated runs do not pay the GPU render again.

Run:  .venv/bin/python scripts/gen_pack_front.py ELYSION
      .venv/bin/python scripts/gen_pack_front.py ELYSION --front-only
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import nikke_reborn as nr
from PIL import Image

EXPANSION_NAME = "Expansion.json"
FRONT_NAME = "CardPack_Front.png"
CACHE_DIR = nr.REPO_ROOT / ".pack_cache"

# --- front composition tuning (fractions of the front) ----------------------
# Every NIKKE's feet sit on the front's bottom edge (feet baseline = 1.0), so
# no one floats above a strip of background or gets clipped by the card frame.
# The hero is the first featured NIKKE: centered, the largest, in front.
HERO_HEIGHT = 0.78   # hero body height as a fraction of the front height
HERO_FEET_Y = 1.0    # hero feet baseline (the bottom edge)
# The remaining NIKKES read as a group behind the hero: smaller (the depth cue)
# and pushed to the left and right, still with their feet on the bottom edge.
BACK_HEIGHT = 0.42   # back body height fraction (base, before per-tier shrink)
BACK_FEET_Y = 1.0    # back feet baseline (the bottom edge)
BACK_OFFSET_X = 0.34 # first flank's center offset from the middle (width frac)
BACK_TIER_GAP = 0.5  # each further tier on a side steps out by this fraction
BACK_TIER_SHRINK = 0.9  # each further tier shrinks by this factor
ALPHA_TRIM = 24  # alpha threshold (0-255) for the content bounding box


def _front_size() -> tuple[int, int]:
    """The pack front's target size: the material template's *right* mask
    rectangle (the left one is the back). Generating at exactly this size means
    the material composition pastes it with no rescale."""
    with Image.open(nr.PACK_TEMPLATE) as opened:
        template = opened.convert("RGBA")
    rects = nr._pack_mask_rects(nr._pack_mask(template))
    if len(rects) != 2:
        raise nr.GenerationError(
            f"{nr.PACK_TEMPLATE.name} carries {len(rects)} pure-blue mask "
            f"rectangle(s), expected 2 (back, front)"
        )
    rect = rects[1]
    return rect[2] - rect[0], rect[3] - rect[1]


def _load_expansion(pack_dir: Path) -> dict:
    path = pack_dir / EXPANSION_NAME
    if not path.is_file():
        raise nr.GenerationError(f"no {EXPANSION_NAME} in {pack_dir}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise nr.GenerationError(f"cannot read {path}: {exc}") from exc


def _render_first_frame(json_path: Path) -> Image.Image:
    """Render the card's first frame via ``nikke-viewer --stdout`` (raw RGBA).

    The viewer streams every frame as a contiguous ``viewport``-sized RGBA
    block; only the first is kept and the stream is abandoned (the viewer is
    killed), so an animated NIKKE costs no more than a static one. Cached on
    disk by the definition's hash so unchanged NIKKES are not re-rendered.
    """
    card = nr._load_card(json_path)
    viewport = card.get("viewport")
    if not viewport:
        raise nr.GenerationError(
            f"{json_path.name}: missing 'viewport' (needed to size the raw "
            f"frames streamed by {nr.VIEWER} --stdout)"
        )
    width, height = int(viewport[0]), int(viewport[1])
    frame_bytes = width * height * 4

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{nr._source_hash(json_path)}.png"
    if cache_path.is_file():
        with Image.open(cache_path) as cached:
            return cached.convert("RGBA")

    viewer = subprocess.Popen(
        [nr.VIEWER, "--stdout", str(json_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    drain = nr._PipeDrain(viewer.stderr)
    try:
        data = nr._read_exact(viewer.stdout, frame_bytes)
        if len(data) != frame_bytes:
            raise nr.GenerationError(
                f"{nr.VIEWER} produced no frame for {json_path.name} "
                f"(got {len(data)} of {frame_bytes} bytes)"
            )
        frame = Image.frombytes("RGBA", (width, height), data)
    finally:
        # Abandon the stream early (we only want the first frame): the viewer
        # may be blocked writing the rest to a full pipe and is killed.
        nr._reap_viewer(viewer, drain, clean_exit_expected=False)
    frame.save(cache_path)
    return frame


def _content_box(image: Image.Image, threshold: int = ALPHA_TRIM) -> Image.Image:
    """Trim *image* to its opaque content bounding box (alpha > threshold)."""
    alpha = image.getchannel("A").point(lambda v: 255 if v > threshold else 0)
    box = alpha.getbbox()
    if box is None:
        raise nr.GenerationError("rendered frame is fully transparent")
    return image.crop(box)


def _paste_body(
    canvas: Image.Image,
    body: Image.Image,
    center_x: float,
    feet_y: float,
    height: int,
) -> None:
    """Scale *body* so its height is *height* px and composite it onto
    *canvas* with its horizontal center at *center_x* and its bottom (feet) at
    *feet_y*. Parts that run off the canvas edge are clipped."""
    scale = height / body.height
    new_width = max(1, round(body.width * scale))
    body = body.resize((new_width, height), Image.Resampling.LANCZOS)
    left = round(center_x - new_width / 2)
    top = round(feet_y - height)
    canvas.alpha_composite(body, (left, top))


def _fit_background(background: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Resize *background* to the front's height, then center-crop it to the
    front's exact width (the spec's treatment, distinct from the card's cover
    fit)."""
    width, height = size
    scale = height / background.height
    if scale != 1.0:
        background = background.resize(
            (round(background.width * scale), height),
            Image.Resampling.LANCZOS,
        )
    left = (background.width - width) // 2
    return background.crop((left, 0, left + width, height)).convert("RGBA")


def build_front(
    pack_dir: Path, expansion: dict, size: tuple[int, int]
) -> Image.Image:
    """Compose the pack front: the expansion's background with the featured
    NIKKES drawn over it (backs first, the hero on top)."""
    width, height = size

    bg_rel = expansion.get("background")
    if not bg_rel:
        raise nr.GenerationError(f"{pack_dir.name}: missing 'background'")
    bg_path = (pack_dir / bg_rel).resolve()
    if not bg_path.is_file():
        raise nr.GenerationError(f"{pack_dir.name}: background not found: {bg_rel}")
    canvas = _fit_background(Image.open(bg_path).convert("RGBA"), size)

    pack_rel = expansion.get("pack")
    if not pack_rel:
        raise nr.GenerationError(f"{pack_dir.name}: missing 'pack'")
    bodies = [
        _content_box(_render_first_frame((pack_dir / rel).resolve()))
        for rel in pack_rel
    ]

    # Backs first (behind the hero), left/right alternating, stepping further
    # out and shrinking per tier so any number of featured NIKKES lays out.
    for index, body in enumerate(bodies[1:], start=1):
        side = -1 if (index - 1) % 2 == 0 else 1  # left, right, left, ...
        tier = (index - 1) // 2  # 0 for the inner pair, 1 for the next, ...
        offset = BACK_OFFSET_X * width * (1.0 + BACK_TIER_GAP * tier)
        scale = BACK_TIER_SHRINK**tier
        _paste_body(
            canvas,
            body,
            center_x=width / 2 + side * offset,
            feet_y=BACK_FEET_Y * height,
            height=round(BACK_HEIGHT * height * scale),
        )
    # The hero on top: centered, the largest.
    _paste_body(
        canvas,
        bodies[0],
        center_x=width / 2,
        feet_y=HERO_FEET_Y * height,
        height=round(HERO_HEIGHT * height),
    )
    return canvas


def write_front(pack_dir: Path, expansion: dict) -> Path:
    front = build_front(pack_dir, expansion, _front_size())
    out = pack_dir / FRONT_NAME
    out.parent.mkdir(parents=True, exist_ok=True)
    front.convert("RGB").save(out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a pack's CardPack_Front.png from Expansion.json"
    )
    parser.add_argument("pack", nargs="?", default="ELYSION", help="pack name (default: %(default)s)")
    parser.add_argument(
        "--front-only",
        action="store_true",
        help="only write the front; skip the material and item composition",
    )
    args = parser.parse_args()

    pack_dir = nr.CARDS_DIR / args.pack
    if not pack_dir.is_dir():
        parser.error(f"pack directory not found: {pack_dir}")

    expansion = _load_expansion(pack_dir)
    started = time.monotonic()
    front = write_front(pack_dir, expansion)
    print(
        f"wrote {front.relative_to(nr.REPO_ROOT)} "
        f"({time.monotonic() - started:.1f}s)"
    )

    if args.front_only:
        return

    for process in (nr._process_pack_material, nr._process_pack_item):
        out_path, skipped = process(pack_dir, nr.OUTPUT_DIR)
        verb = "kept" if skipped else "wrote"
        print(f"{verb} {out_path.relative_to(nr.REPO_ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except nr.GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
