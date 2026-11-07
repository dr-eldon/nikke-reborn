"""The PIL image primitives of the card pipeline: the card's static
layers (background fitting and dominant tint, the monochrome and
tint-wash color math, the mask compositing, the logo) and the
template-mask helpers the pack's and the box's materials use. The
layers are composed in memory; nothing here writes to the disk."""

from __future__ import annotations

import colorsys
import re

from PIL import Image, ImageChops, ImageStat

from nikke_reborn import linear
from nikke_reborn.config import CARD_REFERENCE_WIDTH, IMAGES_DIR
from nikke_reborn.linear import _linear_over

#: The profile card's mask, next to its GIMP source.
PROFILE_MASK_PATH = IMAGES_DIR / "designs" / "Card_Mask_Profile.png"
#: The standard card's mask, next to its GIMP source.
STANDARD_MASK_PATH = IMAGES_DIR / "designs" / "Card_Mask_Standard.png"
#: The dominant-tint wash's top-edge opacity (partial, so the
#: background dilutes toward its own tint and the face settles into the
#: card's palette).
PROFILE_TINT_TOP_OPACITY = 0.0
#: The dominant-tint wash's bottom-edge opacity: the darker bottom
#: anchors more firmly than the top.
PROFILE_TINT_BOTTOM_OPACITY = 0.5
#: The wash's bottom color: the background's tint scaled by this in
#: linear light (the hue preserved).
PROFILE_TINT_BOTTOM_FACTOR = 0.3
#: The point (a fraction of the card's height) at which the wash's
#: gradient completes; below it the bottom color holds flat.
PROFILE_TINT_GRADIENT_END = 0.85

#: The logo's corner inset, in multiples of the card's padding.
LOGO_PADDING_FACTOR = 1.5

#: The logo's nominal width at the reference card width (scaled
#: proportionally, aspect preserved).
LOGO_NOMINAL_WIDTH = 200


def _fit_background(background: Image.Image, size: tuple[int, int]) -> Image.Image:
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
    """The image's dominant tint: its mean RGB, sampled on a small
    downscale so a busy background still yields a stable tint."""
    small = image.convert("RGB").resize((32, 32))
    means = ImageStat.Stat(small).mean
    return (round(means[0]), round(means[1]), round(means[2]))


#: Per-channel value -> RGB lookup tables for :func:`_monochrome`,
#: built once per card, not per frame.
_MONOCHROME_LUTS: dict[
    tuple[tuple[int, int, int], float], tuple[bytes, bytes, bytes]
] = {}


def _monochrome_luts(
    tint_rgb: tuple[int, int, int], brightness: float
) -> tuple[bytes, bytes, bytes]:
    """The 256-entry per-channel tables mapping a value channel to the
    *tint*'s RGB at that value (its fixed hue and saturation, with
    *brightness* folded in): built through the same HSV -> RGB
    conversion a full-frame image would run, so each lookup is
    pixel-identical to the per-pixel result."""
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
    """Collapse *image* (RGBA) to the *tint*'s hue, keeping the image's
    own brightness: only each pixel's value channel survives, so the
    shading remains but the vivid colors do not — the image reads as a
    monochrome of the tint and blends into the card's palette.
    *brightness* scales the value channel; the alpha is passed through
    untouched.

    The recolor is a per-channel lookup (:func:`_monochrome_luts`), so no
    full-frame HSV round trip is needed."""
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
    """*rgb* scaled by *factor* in linear light (the sRGB gamma undone),
    so the colour keeps its hue instead of shifting toward black, as a
    direct sRGB scaling would."""

    def scale(value: int) -> int:
        v = value / 255
        v = v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        v *= factor
        v = v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
        return round(max(0.0, min(1.0, v)) * 255)

    return (scale(rgb[0]), scale(rgb[1]), scale(rgb[2]))


def _at_oklch_lightness(
    rgb: tuple[int, int, int], lightness: float
) -> tuple[int, int, int]:
    """*rgb* at Oklch *lightness*: converted to Oklab, its L set to
    *lightness* (Oklch's L is Oklab's L, hue and chroma kept) and back,
    so the result targets a constant perceptual lightness instead of
    scaling the color's own. Out-of-gamut results are clamped per
    channel."""

    def srgb_to_linear(value: int) -> float:
        v = value / 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    def linear_to_srgb(v: float) -> int:
        v = max(0.0, min(1.0, v))
        return round(
            (v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055) * 255
        )

    r, g, b = (srgb_to_linear(c) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    a = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    b = 0.0259040371 * l + 0.7827717600 * m - 0.8086757971 * s
    l = lightness + 0.3963377774 * a + 0.2158037573 * b
    m = lightness - 0.1055613458 * a - 0.0638541728 * b
    s = lightness - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l**3, m**3, s**3
    return (
        linear_to_srgb(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
        linear_to_srgb(-1.2684380046 * l + 2.6132493084 * m - 0.3448113038 * s),
        linear_to_srgb(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s),
    )


def _tint_wash(size: tuple[int, int], tint_rgb: tuple[int, int, int]) -> Image.Image:
    """The profile card's static wash layer: a vertical gradient of the
    tint (its ``PROFILE_TINT_*`` constants), darkening and opacifying
    toward the bottom, completing short of the bottom edge — the bottom
    strip below it holds the bottom color and opacity flat."""
    _, height = size
    bottom = _scale_linear_light(tint_rgb, PROFILE_TINT_BOTTOM_FACTOR)
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
    """Tint *image*'s (pure-grayscale) pixels with the *tint*'s hue at
    each pixel's own perceived brightness (L*): white is a fixed point
    and stays white; near-white levels carry only a faint cast of the
    tint, and darker levels continue the white -> tint line (clamped).
    The alpha is passed through untouched."""
    r, _, _, a = image.split()

    def lstar(rgb: tuple[int, int, int]) -> float:
        def lin(value: int) -> float:
            v = value / 255
            return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

        red, green, blue = (lin(channel) for channel in rgb)
        y = 0.2126729 * red + 0.7151522 * green + 0.0721750 * blue
        return 116 * y ** (1 / 3) - 16 if y > 0.008856 else 903.3 * y

    # White is a fixed point: v = 255 converges to the mix's white end,
    # so it stays white exactly.
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
    """The profile card's static layers, composed in memory: the
    background (a monochrome of its own dominant tint), the tint wash,
    the profile mask (tinted at each pixel's own lightness) and the
    dominant tint itself (the photo reel's border color). Nothing
    touches the disk."""
    base = _fit_background(background, size)
    tint_rgb = _dominant_color(base)
    base = _monochrome(base, tint_rgb)
    tint = _tint_wash(base.size, tint_rgb)
    with Image.open(PROFILE_MASK_PATH) as opened:
        mask = opened.convert("RGBA")
    if mask.size != base.size:
        mask = mask.resize(base.size, Image.Resampling.LANCZOS)
    mask = _tint_at_luma(mask, tint_rgb)
    return base, tint, mask, tint_rgb


def _standard_layers(base: Image.Image) -> Image.Image:
    """The standard card's static base: *base* (the fitted background)
    with the standard mask over it. Applied to a copy, so the caller
    keeps the unmasked background to sample its tints from — the mask's
    white would wash the scene's color out."""
    with Image.open(STANDARD_MASK_PATH) as opened:
        mask = opened.convert("RGBA")
    if mask.size != base.size:
        mask = mask.resize(base.size, Image.Resampling.LANCZOS)
    face = base.copy()
    _linear_over(face, mask)
    return face


def _fade_to_dominant(image: Image.Image, factor: float = 0.5) -> Image.Image:
    """*image* faded *factor* of the way toward its own dominant color
    (the standard tier's gentle version of :func:`_monochrome`). The
    alpha is passed through untouched."""
    dominant = _dominant_color(image)
    # The fade blends in linear light (see nikke_reborn.linear).
    faded = linear._from_linear(
        linear._to_linear(image) * (1 - factor) + linear.DECODE[list(dominant)] * factor
    )
    faded.putalpha(image.getchannel("A"))
    return faded


def _scale_logo(logo: Image.Image, card_width: int) -> Image.Image:
    target = round(LOGO_NOMINAL_WIDTH * card_width / CARD_REFERENCE_WIDTH)
    if target == logo.width:
        return logo
    height = round(logo.height * target / logo.width)
    return logo.resize((target, height), Image.Resampling.LANCZOS)


def _with_logo(
    base: Image.Image, logo: Image.Image, margin: int, top: bool = False
) -> Image.Image:
    canvas = base.copy()
    y = margin if top else base.height - logo.height - margin
    canvas.alpha_composite(logo, (base.width - logo.width - margin, y))
    return canvas


def _set_luma(hue: float, sat: float, target: float) -> tuple[int, int, int]:
    """(hue, sat) -> an rgb with perceived luminance of ~*target* (0..1).

    At a fixed hue, luminance is linear in both value and saturation:
    the target is hit either by scaling the value (bright hues) or by
    reducing the saturation at full value (intrinsically dark ones)."""
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


def _pack_mask(template: Image.Image) -> Image.Image:
    r = template.getchannel("R").point(lambda v: 255 if v == 0 else 0)
    g = template.getchannel("G").point(lambda v: 255 if v == 0 else 0)
    b = template.getchannel("B").point(lambda v: 255 if v == 255 else 0)
    return ImageChops.darker(ImageChops.darker(r, g), b)


def _box_side_mask(template: Image.Image) -> Image.Image:
    r = template.getchannel("R").point(lambda v: 255 if v == 0 else 0)
    g = template.getchannel("G").point(lambda v: 255 if v == 255 else 0)
    b = template.getchannel("B").point(lambda v: 255 if v == 0 else 0)
    return ImageChops.darker(ImageChops.darker(r, g), b)


def _box_top_mask(template: Image.Image) -> Image.Image:
    r = template.getchannel("R").point(lambda v: 255 if v == 255 else 0)
    g = template.getchannel("G").point(lambda v: 255 if v == 0 else 0)
    b = template.getchannel("B").point(lambda v: 255 if v == 0 else 0)
    return ImageChops.darker(ImageChops.darker(r, g), b)


def _pack_mask_rects(mask: Image.Image) -> list[tuple[int, int, int, int]]:
    """Bounding boxes of the mask's solid rectangles, left to right
    (``(left, top, right, bottom)``, right and bottom exclusive). A
    solid rectangle repeats the same pixel run on every row, so
    consecutive rows with the same run form one rectangle."""
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
