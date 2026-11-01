"""The PIL image primitives of the card pipeline.

Everything that turns a definition's inputs into the card's static layers:
fitting the background and extracting its dominant tint, the monochrome and
tint-wash color math (the profile card's background, face and mask), the
standard card's mask compositing, the logo (scaled and stamped; the
copyright line and the combined per-frame overlay live in
:mod:`nikke_reborn.lettering`), and the template-mask helpers the pack's and
the box's materials use to locate their pure-color placeholder
rectangles, and the per-frame composite
itself (:func:`_composite_frame`, the GIL-releasing blend of a raw frame
over the opaque base). The layers are composed in memory; nothing here
writes to the disk.
"""

from __future__ import annotations

import colorsys
import re

from PIL import Image, ImageChops, ImageStat

from nikke_reborn.config import CARD_REFERENCE_WIDTH, IMAGES_DIR

#: The profile card's mask (tinted with the background's dominant tint at
#: each pixel's own lightness, the white staying white; composited over
#: the diluted background, under the character), next to its GIMP source.
PROFILE_MASK_PATH = IMAGES_DIR / "designs" / "Card_Mask_Profile.png"
#: The standard card's mask (the white card face, composited over the
#: background, under the character), next to its GIMP source.
STANDARD_MASK_PATH = IMAGES_DIR / "designs" / "Card_Mask_Standard.png"
#: Opacity of the dominant-tint wash's top edge: laid over the monochrome
#: background and the face framing: the partial wash dilutes the
#: background toward its own main color and gently re-tints the face so
#: it settles into the card's palette.
PROFILE_TINT_TOP_OPACITY = 0.3
#: Opacity of the dominant-tint wash's bottom edge: the alpha ramps
#: linearly from PROFILE_TINT_TOP_OPACITY to this, so the darker bottom
#: anchors more firmly than the top.
PROFILE_TINT_BOTTOM_OPACITY = 0.5
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

#: The logo sits this many times the card ``padding`` away from the corner.
LOGO_PADDING_FACTOR = 1.5

#: Nominal logo width (pixels) at the reference card width: the logo is
#: scaled proportionally, preserving its aspect ratio (200 px wide on the
#: 1640 px cards we have).
LOGO_NOMINAL_WIDTH = 200


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
) -> tuple[Image.Image, Image.Image, Image.Image, tuple[int, int, int]]:
    """The profile card's static layers, composed in memory: the (fitted)
    *background* — a monochrome of its own dominant tint — the dominant-tint
    wash (a gradient from the background's dominant color to a darker, more
    opaque version of it), the profile card mask
    (:data:`PROFILE_MASK_PATH`) — tinted with the same tint at each
    pixel's own lightness (the white staying white) — and the background's
    dominant *tint* itself (the photo reel's border color). The
    (animated) face framing is
    composited between the background and the tint, per frame and collapsed
    to a monochrome of the same tint's hue, by
    :func:`_stream_dual_composited`. Nothing touches the disk."""
    base = _fit_background(background, size)
    # The background's dominant color: it tints the (now monochrome)
    # background, colors the wash (a gradient darkening toward the
    # bottom) laid over the background and the face, tints the mask
    # at each pixel's own lightness (the white stays white), and colors
    # the photo reel's border.
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
    return base, tint, mask, tint_rgb


def _standard_layers(base: Image.Image) -> Image.Image:
    """The standard card's static base, composed in memory: *base* (the
    fitted background, faded toward its dominant color by the caller) with
    the standard card mask (:data:`STANDARD_MASK_PATH`) composited over it
    (the white card face, under the character). The mask is applied to a
    copy, so *base* is left untouched — the caller still has the unmasked
    fitted background to sample the subtitle rectangle's tint from (as the
    profile cards sample their fitted background), so the mask's white does
    not wash the scene's color out. Nothing touches the disk."""
    with Image.open(STANDARD_MASK_PATH) as opened:
        mask = opened.convert("RGBA")
    if mask.size != base.size:
        mask = mask.resize(base.size, Image.Resampling.LANCZOS)
    face = base.copy()
    face.alpha_composite(mask)
    return face


def _fade_to_dominant(image: Image.Image, factor: float = 0.5) -> Image.Image:
    """*image* faded *factor* of the way toward its own dominant color: its
    colors blended with a solid fill of :func:`_dominant_color` (its mean
    tint, sampled on a small downscale) — a busy scene diluted a little
    toward its main color while keeping its content (the standard tier's
    gentle version of the profile cards' full monochrome,
    :func:`_monochrome`). 0.0 keeps *image* as-is, 1.0 a flat fill of its
    dominant tint. The alpha channel is passed through untouched (a fully
    opaque background stays fully opaque)."""
    dominant = _dominant_color(image)
    faded = Image.blend(
        image.convert("RGB"), Image.new("RGB", image.size, dominant), factor
    )
    faded.putalpha(image.getchannel("A"))
    return faded


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


def _composite_frame(
    frame: Image.Image, base: Image.Image, base_alpha: Image.Image | None
) -> Image.Image:
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
