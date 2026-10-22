#!/usr/bin/env python
"""One-off comparison matrix for card-name effects (dev tool, not shipped).

Renders each requested card once with nikke-viewer (deterministic, so the
artifact is reused) and writes the chosen effect combos (default:
trail; anything else via --combos) to
effects/<set>/<card>/<variant>/<combo>:

- base:    the title is filled with a subtle vertical metal gradient —
           the text color at the ink's top leaning into the per-frame
           trail tint at the ink's bottom (METAL_TRAIL_MIX, a faint
           hue lean that tracks the scene), with a bright sheen band
           (METAL_SHEEN_Y); the corner subtitle keeps the solid base
           color
- glow:    two-pass context-aware bloom under the crisp text; its color
           is sampled from the art behind the name (median hue of the
           colored pixels in the top-left sample box, per frame) and its
           brightness contrasts the art: bright glow on dark art (capped
           by GLOW_MAX_LUMA so it stays colored, not white), dark glow
           on bright art (target luminance = (1 - art luminance)^2,
           shifted toward violet at full saturation so it stays colorful)
- shadow:  soft dark halo for contrast over busy art
- trail:   the title extruded diagonally down-right (union of the
           stepped offsets — connected to the glyph edges, reads as 3D
           depth); the subtitle moves to the top-right corner
           (right-aligned, inset by the card's own padding — the 1.5x
           title inset stays title-only), the usual white
           with its own trail (SUBTITLE_TRAIL_OFFSET px) (TRAIL_OFFSET
           px for the title) — the trails are tinted with the art's
           own hue behind them (per frame, like the glow) at a shadow
           luminance (TRAIL_TARGET_LUMA) and TRAIL_ALPHA, so they
           blend into the scene
- blur:    frosted-glass core: the art behind the glyphs is blurred and
           the white text is semi-transparent over it (per frame)
- refract: black-hole style lens around the word: the scene inside an
           ellipse around the name (ink + REFRACT_MARGIN) is pulled
           radially toward the word's center — REFRACT_STRENGTH at full
           strength inside the plateau (REFRACT_PLATEAU), fading to 0 at
           the boundary — with a radial chromatic fringe (R and B gathered
           at slightly opposite radii), like light bending around a mass
           (needs numpy, dev-only)

The name is stamped *over* the rendered frame, matching the production
pipeline (logo/name/copyright overlay the card art). Static variants are
written as full-resolution PNGs; the animated variant as 820x1024
ultrafast MP4s (draft settings). After each run, a contact sheet is
written to effects/contact-sheet.png: one section per static variant on
disk (sampled glow color swatch + a grid of the effect combos on disk).

Cards are processed one at a time (a single nikke-viewer GPU render at
a time), but the effect combinations of each card run in parallel on
a thread pool (PIL releases the GIL for composites and blurs, and each
encode is its own ffmpeg process).

Run:  .venv/bin/python scripts/compare_effects.py [--combos a+b,c] [variant ...]
      (default cards: the 0001-rapi trio; tokens like '0004/silver'
      select other cards, 'silver' matches by variant name; default
      combo: trail)
"""

import colorsys
import itertools
import math
import os
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

try:
    import numpy as np  # refract only
except ModuleNotFoundError:
    np = None

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import nikke_reborn as nr

ALL_CARDS = sorted(nr.CARDS_DIR.rglob("*.json"))
DEFAULT_CARDS = [
    nr.CARDS_DIR / "ELYSION" / "0001_Rapi" / "Common.json",
    nr.CARDS_DIR / "ELYSION" / "0001_Rapi" / "Exotic.json",
    nr.CARDS_DIR / "ELYSION" / "0001_Rapi" / "Idle.json",
]


def _matches(rel: str, token: str) -> bool:
    """Match a token like '0004/silver' or 'silver' against a relative path."""
    if token in rel:
        return True
    if "/" in token:
        head, _, tail = token.partition("/")
        return Path(rel).parent.name.startswith(head) and Path(rel).stem == tail
    return Path(rel).stem == token


_args = sys.argv[1:]
COMBO_SPECS: list[str] | None = None
if "--combos" in _args:
    i = _args.index("--combos")
    COMBO_SPECS = [s for s in _args[i + 1].split(",") if s]
    del _args[i : i + 2]

if _args:
    CARDS = [
        p for p in ALL_CARDS
        if any(_matches(p.relative_to(nr.CARDS_DIR).as_posix(), t) for t in _args)
    ]
    if not CARDS:
        sys.exit(f"unknown card variant(s): {', '.join(_args)}")
else:
    CARDS = DEFAULT_CARDS
OUT_ROOT = nr.REPO_ROOT / "effects"

EFFECTS = ("glow", "shadow", "trail", "blur", "refract")

# --- effect tuning (reference viewport 1640x2048, padding 50) --------------
GLOW_FALLBACK = (170, 235, 255)  # hue/sat source when the art is (near) gray
GLOW_WIDE_RADIUS = 4.5
GLOW_WIDE_FACTOR = 0.70
GLOW_TIGHT_RADIUS = 2.5
GLOW_TIGHT_FACTOR = 1.00
# Glow color sampling: the box (in units of padding, from the top-left) of
# art to read, downsampled to GLOW_SAMPLE_PX x GLOW_SAMPLE_PX.
GLOW_SAMPLE_W = 6
GLOW_SAMPLE_H = 5
GLOW_SAMPLE_PX = 24
GLOW_MIN_QUALIFY = 0.25  # min fraction of sample pixels that must be colored
GLOW_SAT_BOOST = 1.4
GLOW_SAT_MIN = 0.45
GLOW_SAT_MAX = 0.90
GLOW_MAX_LUMA = 0.60  # cap on the glow target for dark art (bright, and deep enough to
                      # keep the white text's edge crisp instead of melting into the halo)

#: Below this glow target luminance (i.e. on bright art) the glow is
#: pushed toward violet and run at full saturation: at low brightness,
#: hues near green/yellow collapse to gray and read as a soft shadow,
#: while blue-violet keeps its color.
GLOW_COLORFUL_THRESHOLD = 0.35
#: Max hue rotation (degrees, toward violet) a dark glow receives; the
#: actual rotation scales with how far below GLOW_COLORFUL_THRESHOLD
#: the target sits.
GLOW_HUE_SHIFT = 60.0
SHADOW_COLOR = (0, 0, 0)
SHADOW_RADIUS = 8.0
SHADOW_FACTOR = 0.55
SHADOW_OFFSET = (0, 3)
#: The trails (title and subtitle) are semi-transparent, so the art
#: shows through them.
#: The trails are tinted with the art's own hue behind them (the same
#: per-frame sampler as the glow) at this target luminance — a colored
#: shadow that blends into the scene instead of sitting on it
TRAIL_TARGET_LUMA = 0.12
TRAIL_COLOR = (0, 0, 0)  # fallback when the sample region has no art
TRAIL_ALPHA = 0.75
TRAIL_OFFSET = 5  # px, equal x/y: the title trail runs diagonally down-right
#: px: the subtitle text's own trail (the title's is TRAIL_OFFSET)
SUBTITLE_TRAIL_OFFSET = 3
FROST_RADIUS = 6.0        # blur of the art seen through the text
FROST_WHITE_ALPHA = 0.75  # opacity of the base-color core when frosted
#: Metallic title fill: a vertical gradient from the text color at the
#: ink's top, leaning into the per-frame trail tint at the ink's
#: bottom by this fraction (a faint hue lean, not a darkening), with
#: a sheen band (METAL_SHEEN_*: center, brightness, and width in
#: ink-height fractions and RGB units)
METAL_TRAIL_MIX = 0.25
METAL_SHEEN_Y = 0.42
METAL_SHEEN_DELTA = 20
METAL_SHEEN_SIGMA = 0.07
FROST_MARGIN = 30         # crop margin around the name for the blur
REFRACT_MARGIN = 64       # px around the ink: the lens boundary (the ellipse
                          # is inscribed in this box, so the field is 0 there)
REFRACT_STRENGTH = 12.0   # px, inward pull at full strength
REFRACT_PLATEAU = 0.65    # lens radius fraction at full strength; linear fade
                          # to 0 at the boundary beyond it
REFRACT_FRINGE = 0.28     # radial chromatic spread: R at (1+f), B at (1-f)

# Effect combinations per card run this many in parallel. Each animated
# combo also drives an ffmpeg encode with 4 threads (8 x 4 fits 32 cores).
WORKERS = min(8, (os.cpu_count() or 4) // 4)

# Animated-variant preview MP4s: full resolution (the half-res draft
# settings are for the main pipeline's quick-iteration mode), but a
# fast preset — these judge effects, they are not shipped artifacts
EFFECTS_MP4_PRESET = "veryfast"
EFFECTS_MP4_SCALE = 1.0

# Contact-sheet layout, shared by _build_sheet and
# check_sheet_consistency (the cells must line up exactly).
#: A cell is two views side by side: the top-left (the name block) and
#: the top-right corner (the subtitle)
SHEET_VIEW_W, SHEET_VIEW_GAP = 520, 8
SHEET_CELL_W = 2 * SHEET_VIEW_W + SHEET_VIEW_GAP
SHEET_CELL_H, SHEET_CELL_LABEL = 220, 30
SHEET_TITLE_H, SHEET_OUTER_PAD, SHEET_SEC_PAD, SHEET_SWATCH = 44, 16, 16, 24
#: One combo cell per row: with the two-view cells, a second column
#: would leave the row half empty
SHEET_COLS = 1


def combo_name(effects: frozenset[str]) -> str:
    return "+".join(e for e in EFFECTS if e in effects) or "none"


def _parse_combo(spec: str) -> frozenset[str]:
    if spec == "none":
        return frozenset()
    parts = spec.split("+")
    unknown = [p for p in parts if p not in EFFECTS]
    if unknown:
        sys.exit(f"unknown effect(s) in {spec!r}: {', '.join(unknown)}")
    return frozenset(parts)


DEFAULT_COMBOS = ("trail",)  # the locked-in variant; anything else via --combos

COMBOS = (
    list(dict.fromkeys(_parse_combo(s) for s in COMBO_SPECS))
    if COMBO_SPECS is not None
    else list(dict.fromkeys(_parse_combo(s) for s in DEFAULT_COMBOS))
)


def _tint(mask: Image.Image, color: tuple[int, int, int], factor: float) -> Image.Image:
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


def _shift(mask: Image.Image, delta: tuple[int, int]) -> Image.Image:
    dx, dy = delta
    if dx == 0 and dy == 0:
        return mask
    return mask.transform(mask.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy))


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
    region: Image.Image, mask: Image.Image | None = None
) -> tuple[float, float, float | None]:
    """(hue, boosted sat, art luminance) sampled from *region*.

    Median hue/saturation of the colored pixels (medians dodge hue
    wrap-around and single-pixel outliers); the art luminance is the
    mean over all pixels. Pixels where *mask* is 0 are ignored.
    (Near)-gray art returns the GLOW_FALLBACK hue/sat, so muted art
    still gets a visible effect; a fully masked region has no art
    luminance (None).
    """
    small = region.resize((GLOW_SAMPLE_PX, GLOW_SAMPLE_PX)).convert("RGB")
    mdata = None
    if mask is not None:
        mdata = mask.resize((GLOW_SAMPLE_PX, GLOW_SAMPLE_PX)).tobytes()
    data = small.tobytes()
    hues: list[float] = []
    sats: list[float] = []
    luma_sum, count = 0.0, 0
    for i in range(0, len(data), 3):
        if mdata is not None and mdata[i // 3] == 0:
            continue
        r, g, b = data[i] / 255, data[i + 1] / 255, data[i + 2] / 255
        luma_sum += 0.2126 * r + 0.7152 * g + 0.0722 * b
        count += 1
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        if s > 0.15 and v > 0.15:
            hues.append(h)
            sats.append(s)
    if count == 0:
        h, s, _ = colorsys.rgb_to_hsv(*(c / 255 for c in GLOW_FALLBACK))
        return (h, s, None)
    if len(hues) < GLOW_SAMPLE_PX * GLOW_SAMPLE_PX * GLOW_MIN_QUALIFY:
        # near-gray art: the fallback hue/sat
        h, s, _ = colorsys.rgb_to_hsv(*(c / 255 for c in GLOW_FALLBACK))
        return (h, s, luma_sum / count)
    sat = min(GLOW_SAT_MAX, max(GLOW_SAT_MIN, statistics.median(sats) * GLOW_SAT_BOOST))
    return (statistics.median(hues), sat, luma_sum / count)


def _toward_violet(hue: float, degrees: float) -> float:
    """Rotate *hue* (0-1, colorsys scale) at most *degrees* toward
    violet (270 degrees), taking the short way around the wheel."""
    target = 270.0 / 360.0
    delta = (target - hue) % 1.0
    if delta > 0.5:
        delta -= 1.0
    step = min(degrees / 360.0, abs(delta))
    return (hue + (step if delta > 0 else -step)) % 1.0


def _glow_color(
    region: Image.Image, mask: Image.Image | None = None
) -> tuple[int, int, int]:
    """Context-aware glow color from *region*.

    The sampled hue/saturation at a brightness that contrasts the art:
    the target luminance is (1 - art luminance) squared, capped by
    GLOW_MAX_LUMA, so dark art gets a bright glow and bright art gets
    a dark one — the halo always stands off the scene instead of
    merging into it. The square steepens the bright side: a plain
    1 - luma target is barely darker than mid-bright art (0.42 on
    0.58 art), so the halo would read as invisible; squared it is
    0.18, a true dark rim. Dark art (luma <= 0.2 or so) hits the cap
    either way and is unaffected.

    Dark glows are also kept colorful (see GLOW_COLORFUL_THRESHOLD):
    shifted toward violet at full saturation, since at low brightness
    the sampled beach/sky teal would read as a soft shadow.
    """
    hue, sat, luma = _sample_context(region, mask)
    if luma is None:
        return GLOW_FALLBACK
    target = min((1.0 - luma) ** 2, GLOW_MAX_LUMA)
    if target < GLOW_COLORFUL_THRESHOLD:
        strength = (GLOW_COLORFUL_THRESHOLD - target) / GLOW_COLORFUL_THRESHOLD
        hue = _toward_violet(hue, strength * GLOW_HUE_SHIFT)
        sat = 1.0
    return _set_luma(hue, sat, target)


def _trail_color(region: Image.Image) -> tuple[int, int, int]:
    """Per-frame trail color: the art's own hue at a fixed dark
    luminance (a tinted shadow, not a glow). Black when the region
    has no readable art."""
    hue, sat, luma = _sample_context(region)
    if luma is None:
        return TRAIL_COLOR
    return _set_luma(hue, sat, TRAIL_TARGET_LUMA)


def _bilinear_gather(
    art: "np.ndarray", fx: "np.ndarray", fy: "np.ndarray", ch: int
) -> "np.ndarray":
    """Channel *ch* of *art* sampled at (x + fx, y + fy), bilinearly."""
    h, w = fx.shape
    sx = (np.arange(w)[None, :] + fx).clip(0, w - 1)
    sy = (np.arange(h)[:, None] + fy).clip(0, h - 1)
    x0 = sx.astype(np.intp)
    y0 = sy.astype(np.intp)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    ax = sx - x0
    ay = sy - y0
    a = art[..., ch]
    return (
        a[y0, x0] * (1 - ax) * (1 - ay)
        + a[y0, x1] * (1 - ay) * ax
        + a[y1, x0] * ay * (1 - ax)
        + a[y1, x1] * ay * ax
    )


def _refract_warp(art: "np.ndarray", field: tuple) -> "np.ndarray":
    """Bend *art* into a lens: the scene falls inward toward the word's
    center, with R and B gathered at slightly different radii (fringe)."""
    dx, dy = field
    f = REFRACT_FRINGE
    r = _bilinear_gather(art, dx * (1 + f), dy * (1 + f), 0)
    g = _bilinear_gather(art, dx, dy, 1)
    b = _bilinear_gather(art, dx * (1 - f), dy * (1 - f), 2)
    return np.stack([r, g, b], axis=-1).round().clip(0, 255).astype(np.uint8)


@dataclass
class _NameLayers:
    """Precomputed name-stack parts.

    ``sub_top`` (the solid subtitle core) and ``shadow`` (soft halo)
    are color-fixed; the title core is a per-frame metal gradient
    (``metal_box`` + ``metal_alpha``); the glow and trail masks are
    tinted per frame with the context colors; ``frost_*`` carry the
    frosted-glass geometry (the blur itself runs per frame on the
    live art); the refract field is a static radial lens displacement
    (the art is warped per frame).
    """

    sub_top: Image.Image | None  # subtitle core, solid base color
    metal_box: tuple[int, int, int, int]  # title ink bbox (gradient extent)
    metal_alpha: Image.Image  # factored title mask (per-frame fill's alpha)
    shadow: Image.Image | None
    trail: Image.Image | None
    sub_trail: Image.Image | None  # subtitle text trail (top-right corner)
    glow_wide: Image.Image | None
    glow_tight: Image.Image | None
    frost_mask: Image.Image | None  # core silhouette clipping the frost
    frost_box: tuple[int, int, int, int] | None  # art crop to blur per frame
    sample_box: tuple[int, int, int, int]  # art region to read the context from
    corner_sample_box: tuple[int, int, int, int]  # top-right (corner trail)
    refract_box: tuple[int, int, int, int] | None  # scene region to warp
    refract_field: tuple | None  # (dx, dy) displacement arrays (static)


def build_name_layers(
    size: tuple[int, int],
    name: str,
    subtitle: str,
    padding: int,
    combo: frozenset[str],
) -> _NameLayers:
    """Build the name stack for *combo*: fixed layers plus glow masks."""
    font_size = nr._name_font_size(name, round(padding * nr.NAME_SIZE_FACTOR))
    font = ImageFont.truetype(str(nr.FONT_NAME), font_size)
    font.set_variation_by_axes([nr.NAME_WEIGHT])
    left, top, bottom = nr._text_ink_offsets(name, font)
    inset = _name_inset(padding)

    title_mask = Image.new("L", size, 0)
    title_draw = ImageDraw.Draw(title_mask)
    title_draw.text((inset - left, inset - top), name, font=font, fill=255)
    core = title_mask.copy()
    sub_mask = None
    sub_trail = None
    if subtitle:
        sub_size = nr._subtitle_font_size(subtitle, padding)
        # Sheared into an oblique at SUBTITLE_SUPERSAMPLE times the
        # final size and downscaled, as in the production pipeline (see
        # the constants in nikke_reborn).
        ss = nr.SUBTITLE_SUPERSAMPLE
        sub_font = ImageFont.truetype(str(nr.FONT_NAME), sub_size * ss)
        sub_font.set_variation_by_axes([nr.NAME_WEIGHT])
        sub_left, sub_top, sub_bottom = nr._text_ink_offsets(subtitle, sub_font)
        ink_h = sub_bottom - sub_top
        drift = round(nr.SUBTITLE_SHEAR * ink_h)
        m4 = ((drift + ss - 1) // ss) * ss
        region = Image.new(
            "L", (round(sub_font.getlength(subtitle)) + m4 + 1, ink_h + 1), 0
        )
        ImageDraw.Draw(region).text(
            (m4 - sub_left, -sub_top), subtitle, font=sub_font, fill=255
        )
        w4 = (region.width + ss - 1) // ss * ss
        h4 = (region.height + ss - 1) // ss * ss
        padded = region
        if (region.width, region.height) != (w4, h4):
            padded = Image.new("L", (w4, h4), 0)
            padded.paste(region, (0, 0))
        small = nr._italicize(padded, 0).resize((w4 // ss, h4 // ss), Image.BILINEAR)
        if "trail" in combo:
            # Corner variant: the text sits in the top-right corner,
            # right-aligned and inset by the card's own padding (the
            # title's 1.5x inset stays title-only)
            bbox = small.getbbox()
            px, py = size[0] - padding - bbox[2], padding - bbox[1]
        else:
            sub_ink_top = inset + (bottom - top) + round(sub_size * nr.SUBTITLE_GAP_FACTOR)
            px, py = padding - m4 // ss, sub_ink_top
        sub_mask = Image.new("L", size, 0)
        sub_mask.paste(
            255, (px, py, px + small.width, py + small.height), small
        )
        core.paste(255, (0, 0, size[0], size[1]), sub_mask)

    # Title core: a vertical metal gradient whose bottom leans into
    # the per-frame trail tint — the RGB is built per frame in
    # apply_name; only the geometry and the (factored) alpha are
    # static. The corner subtitle keeps the solid base color. Both
    # cores go translucent when the frosted-glass blur is requested.
    factor = FROST_WHITE_ALPHA if "blur" in combo else 1.0
    metal_box = title_mask.getbbox()
    metal_alpha = title_mask.point(lambda v: int(v * factor))
    sub_top = (
        _tint(sub_mask, nr.NAME_TEXT_COLOR, factor) if sub_mask is not None else None
    )

    shadow = None
    if "shadow" in combo:
        shadow = _tint(
            _shift(core.filter(ImageFilter.GaussianBlur(SHADOW_RADIUS)), SHADOW_OFFSET),
            SHADOW_COLOR,
            SHADOW_FACTOR,
        )

    trail = None
    if "trail" in combo:
        # Title: extruded depth — the union of the text shifted one
        # step at a time along the diagonal, so every trail pixel
        # touches glyph ink (reads as 3D depth off the edges, not a
        # detached projection). The subtitle (top-right corner) gets
        # its own shorter trail. (Hard-edged L masks — tinted fixed
        # black in apply_name at TRAIL_ALPHA.)
        trail = Image.new("L", size, 0)
        for t in range(1, TRAIL_OFFSET + 1):
            trail.paste(255, (0, 0, size[0], size[1]), _shift(title_mask, (t, t)))
        if sub_mask is not None:
            sub_trail = Image.new("L", size, 0)
            for t in range(1, SUBTITLE_TRAIL_OFFSET + 1):
                sub_trail.paste(
                    255, (0, 0, size[0], size[1]), _shift(sub_mask, (t, t))
                )

    glow_wide = glow_tight = None
    if "glow" in combo:
        glow_wide = core.filter(ImageFilter.GaussianBlur(GLOW_WIDE_RADIUS))
        glow_tight = core.filter(ImageFilter.GaussianBlur(GLOW_TIGHT_RADIUS))

    frost_mask = None
    frost_box = None
    if "blur" in combo:
        frost_mask = core
        m = FROST_MARGIN
        ink_w = round(font.getlength(name))
        bottom_edge = inset + font_size
        if subtitle:
            sub_size = nr._subtitle_font_size(subtitle, padding)
            sub_font = ImageFont.truetype(str(nr.FONT_NAME), sub_size)
            sub_font.set_variation_by_axes([nr.NAME_WEIGHT])
            _sub_l, _sub_t, sub_b = nr._text_ink_offsets(subtitle, sub_font)
            bottom_edge = max(
                bottom_edge,
                inset + (bottom - top) + round(sub_size * nr.SUBTITLE_GAP_FACTOR) + (sub_b - _sub_t),
            )
            ink_w = max(ink_w, round(sub_font.getlength(subtitle)))
        # the box covers the title (inset) and the production
        # subtitle (card padding) — leftmost edge wins
        frost_box = (
            padding - m,
            inset - m,
            inset + ink_w + m,
            bottom_edge + m,
        )

    refract_box = None
    refract_field = None
    if "refract" in combo:
        if np is None:
            sys.exit(
                "the refract effect needs numpy: .venv/bin/python -m pip install numpy"
            )
        x0, y0, x1, y1 = core.getbbox()
        m = REFRACT_MARGIN
        rx0, ry0 = max(0, x0 - m), max(0, y0 - m)
        rx1, ry1 = min(size[0], x1 + m), min(size[1], y1 + m)
        h, w = ry1 - ry0, rx1 - rx0
        # Black-hole lens: one coherent ellipse inscribed in the box above
        # (so the field is exactly 0 at the box boundary); everything inside
        # is pulled radially toward the word's center, full strength within
        # the plateau, linear fade to the boundary. The tiny core ramps in
        # so the center is not a singularity (it sits under the text anyway).
        ccx = (x0 + x1) / 2 - rx0
        ccy = (y0 + y1) / 2 - ry0
        a = (x1 - x0) / 2 + m
        b = (y1 - y0) / 2 + m
        dx = np.arange(w)[None, :] - ccx
        dy = np.arange(h)[:, None] - ccy
        rho = np.sqrt((dx / a) ** 2 + (dy / b) ** 2)  # 1 at the boundary
        r = np.hypot(dx, dy)
        prof = np.clip((1.0 - rho) / (1.0 - REFRACT_PLATEAU), 0.0, 1.0)
        mag = REFRACT_STRENGTH * prof * np.minimum(1.0, r / 8.0)
        refract_box = (rx0, ry0, rx1, ry1)
        # Gather offset points AWAY from the center: each pixel shows the
        # content that sat further out, so the scene appears to fall inward.
        refract_field = (
            dx / np.maximum(r, 1e-6) * mag,
            dy / np.maximum(r, 1e-6) * mag,
        )

    # Sample the art behind the name: the corner boxes it sits inside
    # (top-left for the title, top-right for the corner subtitle).
    box = (
        0,
        0,
        min(size[0], round(padding * GLOW_SAMPLE_W)),
        min(size[1], round(padding * GLOW_SAMPLE_H)),
    )
    corner_box = (
        max(0, size[0] - round(padding * GLOW_SAMPLE_W)),
        0,
        size[0],
        min(size[1], round(padding * GLOW_SAMPLE_H)),
    )
    return _NameLayers(
        sub_top, metal_box, metal_alpha, shadow, trail, sub_trail,
        glow_wide, glow_tight,
        frost_mask, frost_box, box, corner_box,
        refract_box, refract_field,
    )


def apply_name(canvas: Image.Image, parts: _NameLayers, sample_from: Image.Image) -> None:
    """Stamp the name stack onto *canvas* (in place).

    The glow is tinted with the color of the art of *sample_from* behind
    the name, so animated cards get a glow that tracks the scene; the
    frost blurs whatever it shows behind the glyphs, per frame.
    """
    # Refraction bends the scene itself; everything else composites over it.
    if parts.refract_field is not None:
        x0, y0, x1, y1 = parts.refract_box
        art = np.asarray(canvas.crop((x0, y0, x1, y1)))
        canvas.paste(
            Image.fromarray(_refract_warp(art, parts.refract_field)), (x0, y0)
        )
    if parts.shadow is not None:
        canvas.alpha_composite(parts.shadow)
    # The glow sits under the trail: the strong glow would otherwise
    # tint the trail's dark edge into a soft halo and eat its hardness.
    if parts.glow_wide is not None:
        color = _glow_color(sample_from.crop(parts.sample_box))
        canvas.alpha_composite(_tint(parts.glow_wide, color, GLOW_WIDE_FACTOR))
        canvas.alpha_composite(_tint(parts.glow_tight, color, GLOW_TIGHT_FACTOR))
    # The title trail color is the trail tint and the metal gradient's
    # bottom lean — sample it once per frame.
    trail_color = _trail_color(sample_from.crop(parts.sample_box))
    if parts.trail is not None:
        canvas.alpha_composite(
            _tint(parts.trail, trail_color, TRAIL_ALPHA)
        )
    if parts.sub_trail is not None:
        canvas.alpha_composite(
            _tint(parts.sub_trail, _trail_color(sample_from.crop(parts.corner_sample_box)), TRAIL_ALPHA)
        )

    if parts.frost_box is not None:
        # frosted glass: blur the live art behind the glyphs only
        x0, y0, x1, y1 = parts.frost_box
        crop = sample_from.crop((x0, y0, x1, y1)).filter(
            ImageFilter.GaussianBlur(FROST_RADIUS)
        )
        frost = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        frost.paste(crop.convert("RGB"), (x0, y0))
        frost.putalpha(parts.frost_mask)
        canvas.alpha_composite(frost)

    # Title core: a vertical metal gradient — the text color at the
    # ink's top leaning into this frame's trail tint at the bottom
    # (METAL_TRAIL_MIX), with the bright sheen band — per frame,
    # tracking the scene like the trail itself.
    x0, y0, x1, y1 = parts.metal_box
    bottom = tuple(
        round(nr.NAME_TEXT_COLOR[i] + METAL_TRAIL_MIX * (trail_color[i] - nr.NAME_TEXT_COLOR[i]))
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
                        nr.NAME_TEXT_COLOR[i]
                        + (bottom[i] - nr.NAME_TEXT_COLOR[i]) * t
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


def _card_name_padding(rel_dir: Path) -> tuple[str, str, int]:
    """(name, subtitle, padding) of the card whose effects live in *rel_dir*."""
    json_path = nr.CARDS_DIR / rel_dir.with_name(rel_dir.name + ".json")
    try:
        card = nr._load_card(json_path)
        return (
            str(card["title"]),
            str(card.get("subtitle", "")),
            int(card["padding"]),
        )
    except Exception:
        return "", "", 50


def _name_inset(padding: int) -> int:
    """The title's inset from the card edges.

    Like the logo: 1.5x the card's padding (LOGO_PADDING_FACTOR). The
    subtitle keeps the card's own padding.
    """
    return round(nr.LOGO_PADDING_FACTOR * padding)


def _stamp_mask(
    size: tuple[int, int], name: str, subtitle: str, padding: int
) -> Image.Image:
    """L mask with 0 where the name stamp and its halo sit.

    Lets glow-color sampling read the art behind the name from a
    finished (stamped) image instead of a clean render.
    """
    font_size = nr._name_font_size(name, round(padding * nr.NAME_SIZE_FACTOR))
    font = ImageFont.truetype(str(nr.FONT_NAME), font_size)
    font.set_variation_by_axes([nr.NAME_WEIGHT])
    margin = 45  # clears the wide glow blur and the shadow halo
    inset = _name_inset(padding)
    ink_w = round(font.getlength(name))
    bottom_edge = inset + font_size
    if subtitle:
        sub_size = nr._subtitle_font_size(subtitle, padding)
        sub_font = ImageFont.truetype(str(nr.FONT_NAME), sub_size)
        sub_font.set_variation_by_axes([nr.NAME_WEIGHT])
        ink_w = max(ink_w, round(sub_font.getlength(subtitle)))
        bottom_edge += 2 * sub_size  # the italic subtitle block
    mask = Image.new("L", size, 255)
    ImageDraw.Draw(mask).rectangle(
        (padding - margin, inset - margin,
         inset + ink_w + margin, bottom_edge + margin),
        fill=0,
    )
    return mask


def _center_crop(
    size: tuple[int, int],
    name: str,
    subtitle: str,
    padding: int,
    cell_w: int,
    cell_h: int,
) -> tuple[int, int, int, int]:
    """A cell_w x cell_h window centered on the name block (title and
    subtitle), clamped to the image; falls back to a corner crop for an
    empty name."""
    w, h = size
    inset = _name_inset(padding)
    if not name:
        x0 = min(inset, w - cell_w)
        y0 = min(inset, h - cell_h)
    else:
        font_size = nr._name_font_size(name, round(padding * nr.NAME_SIZE_FACTOR))
        font = ImageFont.truetype(str(nr.FONT_NAME), font_size)
        font.set_variation_by_axes([nr.NAME_WEIGHT])
        _left, top, bottom = nr._text_ink_offsets(name, font)
        ink_w = round(font.getlength(name))
        bottom_edge = inset + (bottom - top)
        if subtitle:
            sub_size = nr._subtitle_font_size(subtitle, padding)
            sub_font = ImageFont.truetype(str(nr.FONT_NAME), sub_size)
            sub_font.set_variation_by_axes([nr.NAME_WEIGHT])
            ink_w = max(ink_w, round(sub_font.getlength(subtitle)))
            _sl, _st, sub_b = nr._text_ink_offsets(subtitle, sub_font)
            bottom_edge += round(sub_size * nr.SUBTITLE_GAP_FACTOR) + (sub_b - _st)
        cx = (padding + inset + ink_w) / 2  # the block's full extent
        cy = (inset + bottom_edge) / 2
        x0 = int(max(0, min(cx - cell_w / 2, w - cell_w)))
        y0 = int(max(0, min(cy - cell_h / 2, h - cell_h)))
    return (x0, y0, x0 + cell_w, y0 + cell_h)


def _corner_crop(
    size: tuple[int, int], cell_w: int, cell_h: int
) -> tuple[int, int, int, int]:
    """The top-right cell_w x cell_h window, clamped to the image."""
    w, h = size
    x0 = max(0, w - cell_w)
    return (x0, 0, x0 + cell_w, min(h, cell_h))


def _build_sheet(out_root: Path) -> Image.Image | None:
    """Contact sheet: the static variants on disk, stacked vertically
    (one section per card: title with sampled glow color swatch + a grid
    of the effect combos present for that card). Each cell shows two
    views of the card side by side: the top-left (name block) and the
    top-right corner (the subtitle).

    The swatch is sampled from none.png (clean art) when available,
    otherwise from the first present image with the stamp region masked
    out, so it reads the art rather than the name's own halo.
    """
    # Enumerate the full effect power set (not this run's selection), so
    # the sheet always shows every combo present on disk.
    all_names = [
        combo_name(frozenset(sub))
        for r in range(len(EFFECTS) + 1)
        for sub in itertools.combinations(EFFECTS, r)
    ]
    present: dict[Path, list[str]] = {}
    for d in sorted(out_root.rglob("*")):
        if not d.is_dir():
            continue
        names = [n for n in all_names if (d / f"{n}.png").is_file()]
        if names:
            present[d.relative_to(out_root)] = names
    if not present:
        return None

    font_title = ImageFont.truetype(str(nr.FONT), 22)
    font_cell = ImageFont.truetype(str(nr.FONT), 18)
    section_w = SHEET_COLS * SHEET_CELL_W + (SHEET_COLS + 1) * SHEET_SEC_PAD
    max_rows = max((len(v) + SHEET_COLS - 1) // SHEET_COLS for v in present.values())
    section_h = SHEET_TITLE_H + max_rows * (SHEET_CELL_H + SHEET_CELL_LABEL)
    width = section_w + 2 * SHEET_OUTER_PAD
    height = len(present) * section_h + (len(present) + 1) * SHEET_OUTER_PAD
    sheet = Image.new("RGB", (width, height), (16, 16, 20))
    draw = ImageDraw.Draw(sheet)
    for k, rel in enumerate(present):
        names = present[rel]
        x0 = SHEET_OUTER_PAD
        y0 = SHEET_OUTER_PAD + k * (section_h + SHEET_OUTER_PAD)
        base_dir = out_root / rel
        name, subtitle, padding = _card_name_padding(rel)
        plain = base_dir / "none.png"
        swatch_src = plain if plain.is_file() else base_dir / f"{names[0]}.png"
        img = Image.open(swatch_src)
        box = (
            0,
            0,
            min(img.width, round(padding * GLOW_SAMPLE_W)),
            min(img.height, round(padding * GLOW_SAMPLE_H)),
        )
        stamp_mask = (
            None if plain.is_file()
            else _stamp_mask(
                (box[2] - box[0], box[3] - box[1]), name, subtitle, padding
            )
        )
        glow_color = _glow_color(img.crop(box), stamp_mask)
        print(f"  sheet: {rel.as_posix()} -> glow {glow_color}", flush=True)
        draw.rectangle(
            (x0, y0, x0 + section_w - 1, y0 + SHEET_TITLE_H - 1), fill=(34, 38, 46)
        )
        draw.text((x0 + 12, y0 + 9), rel.as_posix(), font=font_title, fill=(230, 235, 245))
        draw.rectangle(
            (
                x0 + section_w - 12 - SHEET_SWATCH,
                y0 + 10,
                x0 + section_w - 12,
                y0 + 10 + SHEET_SWATCH,
            ),
            fill=glow_color,
        )
        draw.text(
            (x0 + section_w - 12 - SHEET_SWATCH - 150, y0 + 12),
            f"glow {glow_color}",
            font=font_cell,
            fill=(180, 190, 205),
        )
        for i, combo in enumerate(names):
            r, c = divmod(i, SHEET_COLS)
            x = x0 + SHEET_SEC_PAD + c * (SHEET_CELL_W + SHEET_SEC_PAD)
            yy = y0 + SHEET_TITLE_H + r * (SHEET_CELL_H + SHEET_CELL_LABEL)
            card_img = Image.open(base_dir / f"{combo}.png")
            left = card_img.crop(
                _center_crop(
                    card_img.size, name, subtitle, padding, SHEET_VIEW_W, SHEET_CELL_H
                )
            )
            right = card_img.crop(
                _corner_crop(card_img.size, SHEET_VIEW_W, SHEET_CELL_H)
            )
            draw.rectangle(
                (x, yy, x + SHEET_CELL_W - 1, yy + SHEET_CELL_LABEL - 1), fill=(40, 44, 52)
            )
            draw.text((x + 10, yy + 5), combo, font=font_cell, fill=(220, 225, 235))
            sheet.paste(left, (x, yy + SHEET_CELL_LABEL))
            sheet.paste(
                right, (x + SHEET_VIEW_W + SHEET_VIEW_GAP, yy + SHEET_CELL_LABEL)
            )
    return sheet


def _overlay_card(
    json_path: Path,
    artifact: Path,
    combos: tuple[frozenset[str], ...],
    workers: int,
) -> int:
    """CPU side of a card: build the base layers and run the combo
    overlays for a rendered *artifact*, writing to the out dir.
    Returns the number of files written. Raises RuntimeError if a
    combo task fails — unlike sys.exit, that propagates through a
    Future, so this is safe to call from a worker thread."""
    card = nr._load_card(json_path)
    name = str(card["title"])
    subtitle = str(card.get("subtitle", ""))
    padding = card["padding"]
    margin = round(nr.LOGO_PADDING_FACTOR * padding)
    copyright_color = (
        (0, 0, 0, 255) if card.get("invert_copyright", False) else (255, 255, 255, 255)
    )
    framerate = card["framerate"] or nr.DEFAULT_FRAMERATE
    logo = Image.open(nr.LOGO_PATHS[bool(card.get("invert_logo", False))]).convert(
        "RGBA"
    )
    background = Image.open(nr._background_path(card, json_path)).convert("RGBA")

    out_dir = OUT_ROOT / json_path.parent.relative_to(nr.CARDS_DIR) / json_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    errors: list[str] = []
    if artifact.is_file():
        # ---- static ----
        frame = nr._open_frame(artifact)
        base = nr._fit_background(background, frame.size)
        overlay, overlay_pos = nr._logo_copyright_overlay(
            frame.size, logo, margin, padding, copyright_color
        )

        art = nr._composite_frame(frame, base)
        art.alpha_composite(overlay, overlay_pos)

        def static_task(combo: frozenset[str]) -> frozenset[str]:
            parts = build_name_layers(frame.size, name, subtitle, padding, combo)
            canvas = art.copy()
            apply_name(canvas, parts, art)
            nr._save_atomic(canvas.convert("RGB"), out_dir / f"{combo_name(combo)}.png")
            return combo

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(static_task, c) for c in combos]
            for fut in as_completed(futures):
                try:
                    combo = fut.result()
                except Exception as exc:
                    errors.append(f"{json_path.stem}: {exc}")
                    continue
                written += 1
                print(f"  {json_path.stem}: {combo_name(combo)}", flush=True)
    else:
        # ---- animated ----
        paths = nr._frame_paths(artifact)
        first = nr._open_frame(paths[0])
        size = first.size
        first.close()
        base = nr._fit_background(background, size)
        overlay, overlay_pos = nr._logo_copyright_overlay(
            size, logo, margin, padding, copyright_color
        )
        # Composite every frame once (logo and copyright line included);
        # the overlays are the only per-combo work. (143 frames x 13.5 MB
        # fits easily.)
        frames = []
        for path in paths:
            frame = nr._composite_frame(nr._open_frame(path), base)
            frame.alpha_composite(overlay, overlay_pos)
            frames.append(frame)

        def animated_task(combo: frozenset[str]) -> frozenset[str]:
            parts = build_name_layers(size, name, subtitle, padding, combo)

            def frame_stream(parts=parts):
                # RGBA: the encoder declares -pix_fmt rgba (4 bytes/px);
                # RGB frames would shift the raw stream by a channel
                for art in frames:
                    canvas = art.copy()
                    apply_name(canvas, parts, art)
                    yield canvas

            nr._encode_mp4(
                frame_stream(),
                size,
                framerate,
                out_dir / f"{combo_name(combo)}.mp4",
                threads=4,
                preset=EFFECTS_MP4_PRESET,
                scale=EFFECTS_MP4_SCALE,
            )
            return combo

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(animated_task, c) for c in combos]
            for fut in as_completed(futures):
                try:
                    combo = fut.result()
                except Exception as exc:
                    errors.append(f"{json_path.stem}: {exc}")
                    continue
                written += 1
                print(f"  {json_path.stem}: {combo_name(combo)}", flush=True)

    if errors:
        raise RuntimeError("; ".join(errors))
    return written


def process_card(
    json_path: Path, combos: tuple[frozenset[str], ...], workers: int
) -> int:
    """Render and overlay one card, writing the combo outputs to its
    out dir. Returns the number of files written. The GPU render runs
    inline (see regen_cards.py for the serial-render / parallel-overlay
    split — concurrent nikke-viewer devices exhaust the GPU); the combo
    overlays are pooled."""
    with tempfile.TemporaryDirectory(prefix="nikke-reborn-") as workdir:
        artifact = nr._render_card(json_path, Path(workdir))
        return _overlay_card(json_path, artifact, combos, workers)


def check_sheet_consistency() -> bool:
    """True when every contact-sheet cell is byte-identical to its
    card's crop (the sheet is rebuilt from the cards, so the on-disk
    pair must agree; a mismatch means the two drifted)."""
    sheet_path = OUT_ROOT / "contact-sheet.png"
    if not sheet_path.is_file():
        return False
    all_names = [
        combo_name(frozenset(sub))
        for r in range(len(EFFECTS) + 1)
        for sub in itertools.combinations(EFFECTS, r)
    ]
    present: dict[Path, list[str]] = {}
    for d in sorted(OUT_ROOT.rglob("*")):
        if not d.is_dir():
            continue
        names = [n for n in all_names if (d / f"{n}.png").is_file()]
        if names:
            present[d.relative_to(OUT_ROOT)] = names
    if not present:
        return False
    sheet = Image.open(sheet_path).convert("RGB")
    max_rows = max((len(v) + SHEET_COLS - 1) // SHEET_COLS for v in present.values())
    section_h = SHEET_TITLE_H + max_rows * (SHEET_CELL_H + SHEET_CELL_LABEL)
    for k, rel in enumerate(present):
        x0 = SHEET_OUTER_PAD
        y0 = SHEET_OUTER_PAD + k * (section_h + SHEET_OUTER_PAD)
        name, subtitle, padding = _card_name_padding(rel)
        for i, combo in enumerate(present[rel]):
            r, c = divmod(i, SHEET_COLS)
            x = x0 + SHEET_SEC_PAD + c * (SHEET_CELL_W + SHEET_SEC_PAD)
            yy = (
                y0
                + SHEET_TITLE_H
                + r * (SHEET_CELL_H + SHEET_CELL_LABEL)
                + SHEET_CELL_LABEL
            )
            card = Image.open(OUT_ROOT / rel / f"{combo}.png").convert("RGB")
            left = sheet.crop((x, yy, x + SHEET_VIEW_W, yy + SHEET_CELL_H))
            if left.tobytes() != card.crop(
                _center_crop(card.size, name, subtitle, padding, SHEET_VIEW_W, SHEET_CELL_H)
            ).tobytes():
                return False
            right = sheet.crop(
                (x + SHEET_VIEW_W + SHEET_VIEW_GAP, yy, x + SHEET_CELL_W, yy + SHEET_CELL_H)
            )
            if right.tobytes() != card.crop(
                _corner_crop(card.size, SHEET_VIEW_W, SHEET_CELL_H)
            ).tobytes():
                return False
    return True


def main() -> None:
    started = time.time()
    total = 0
    for json_path in CARDS:
        try:
            total += process_card(json_path, COMBOS, WORKERS)
        except RuntimeError as exc:
            print(f"  ! {exc}", file=sys.stderr, flush=True)
            sys.exit(1)

    sheet = _build_sheet(OUT_ROOT)
    if sheet is not None:
        nr._save_atomic(sheet, OUT_ROOT / "contact-sheet.png")
        total += 1
        print("  contact-sheet rebuilt (one section per static variant on disk)", flush=True)
        if not check_sheet_consistency():
            print("  ! contact-sheet cell mismatch", file=sys.stderr, flush=True)
            sys.exit(1)

    print(f"Done: {total} file(s) in {time.time() - started:.1f}s -> {OUT_ROOT}/")


if __name__ == "__main__":
    main()
