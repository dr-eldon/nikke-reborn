"""The card's lettering: the name stack (title, subtitle and their
bars) and the copyright line.

The name stack is rasterized once per card into static layers and
composited onto every frame; the font size, weight and ink offsets are
measured on probe renders. The copyright line is stamped, with the
logo, into a pre-composited per-frame overlay."""

from __future__ import annotations

import colorsys
import statistics

from PIL import Image, ImageDraw, ImageFont, ImageStat

from nikke_reborn.config import CARD_REFERENCE_WIDTH, FONT, FONTS_DIR
from nikke_reborn.image import _scale_logo, _set_luma, _with_logo

#: The card name's face (vendored static font, SIL OFL).
FONT_NAME = FONTS_DIR / "AireExterior.ttf"

#: The title rectangle's arrow face (vendored).
FONT_RECT_ARROW = FONTS_DIR / "ChocolateClassicalSans-Regular.ttf"

#: The manufacturer's logo's width (a fraction of the frame's width,
#: its height proportional).
MANUFACTURER_LOGO_WIDTH = 0.11

#: The name's font size (in multiples of the card's padding).
NAME_SIZE_FACTOR = 3.0
#: The name's weight (variable fonts only; static fonts have a fixed
#: weight).
NAME_WEIGHT = 700

#: The title's vertical position (a fraction of the card's height).
NAME_TITLE_Y = 0.72

#: The name length (in characters) that still gets the full font size;
#: longer names shrink proportionally.
NAME_REFERENCE_LENGTH = 17

#: The shrink floor (a fraction of the base size).
NAME_MIN_SIZE_FACTOR = 0.6

#: The subtitle's font size (in multiples of the card's padding): the
#: full size up to SUBTITLE_FULL_LENGTH characters, shrinking linearly
#: to the floor at SUBTITLE_FLOOR_LENGTH.
SUBTITLE_SIZE_FACTOR = 1.0
SUBTITLE_MIN_SIZE_FACTOR = 0.60
SUBTITLE_FULL_LENGTH = 18
SUBTITLE_FLOOR_LENGTH = 30

#: The name text's color.
NAME_TEXT_COLOR = (255, 255, 255)

#: The title rectangle's fill.
NAME_RECT_COLOR = (0x33, 0x33, 0x33)
#: The subtitle rectangle's fill's luminance (0..1): its hue is the
#: background's dominant one.
NAME_RECT_LUMA = 0.3
#: The padding around the title's ink (a fraction of the ink's height).
NAME_RECT_PAD = 0.2
#: The padding around the subtitle's ink (a fraction of the ink's
#: height): roomier than the title's.
NAME_SUB_RECT_PAD = 0.4
#: The extra right-side room in the subtitle's rectangle (a fraction of
#: the ink's height).
NAME_SUB_RECT_RIGHT_PAD_EXTRA = 1.0

#: The rectangle's corner cut (a fraction of its height).
NAME_RECT_CORNER = 1 / 3

#: The arrow's glyph, size and margin (fractions of the rectangle's
#: height); it sits in the rectangle's right padding.
NAME_RECT_ARROW = "\u2196"
NAME_RECT_ARROW_SIZE = 0.4
NAME_RECT_ARROW_MARGIN = 0.12

# Context sampling for the subtitle rectangle's tint.
NAME_SAMPLE_PX = 24  # the sample's resolution (px)
CONTEXT_FALLBACK = (170, 235, 255)  # the (near)-gray art's fallback tint
CONTEXT_MIN_QUALIFY = 0.25  # min fraction of sample pixels that are colored
CONTEXT_SAT_BOOST = 1.4  # the sampled saturation is boosted...
CONTEXT_SAT_MIN = 0.45  # ...and clamped, so the tint stays visible...
CONTEXT_SAT_MAX = 0.90  # ...without washing out

#: The copyright text's nominal size (px at the reference card width).
COPYRIGHT_NOMINAL_SIZE = 20
#: The copyright's weight (a light weight reads quieter at its small
#: size).
COPYRIGHT_WEIGHT = 300
#: The copyright's supersampling factor: at the final size FreeType
#: quantizes glyph advances unevenly (the word spaces come out
#: different widths), and the LANCZOS downscale re-smooths them.
COPYRIGHT_SUPERSAMPLE = 4

COPYRIGHT_TEXT = "©PROXIMA BETA PTE. LTD. ©SHIFT UP CORP."

#: The luma (0..255) of a stamp's own region — the first frame's mean
#: under where the stamp lands — at and above which the stamp (the
#: NIKKE logo, the copyright line) is drawn in black, below which in
#: white.
STAMP_LUMA_THRESHOLD = 200.0

#: The stamps' two colors.
STAMP_BLACK = (0, 0, 0, 255)
STAMP_WHITE = (255, 255, 255, 255)


def _set_weight(font: ImageFont.FreeTypeFont, weight: int) -> None:
    """Set *font*'s weight via its variation axes (variable fonts only:
    FreeType raises OSError for static fonts)."""
    try:
        font.set_variation_by_axes([weight])
    except OSError:
        pass


def _text_ink_offsets(text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int, int]:
    """The ink offsets (left, top, bottom) of *text* from its draw
    origin — measured on a probe render, since the rasterized ink can
    differ from the font metrics."""
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
    left, top, _, bottom = bbox
    return left - origin, top - origin, bottom - origin


def _name_font_size(name: str, base_size: int) -> int:
    factor = min(1.0, max(NAME_REFERENCE_LENGTH / len(name), NAME_MIN_SIZE_FACTOR))
    return int(base_size * factor)


def _subtitle_font_size(subtitle: str, padding: int) -> int:
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


def _sample_context(
    region: Image.Image,
) -> tuple[float, float, float | None]:
    """(hue, sat, art luminance) sampled from *region*: the median
    hue/saturation of the colored pixels (medians dodge hue wrap-around
    and single-pixel outliers) and the mean luminance over all pixels.
    (Near)-gray art returns the fallback tint; a fully transparent
    region has no art luminance (None)."""
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
    """The subtitle rectangle's fill: the background's dominant hue at
    the rectangle's base luminance, so the panel picks up the scene's
    tint."""
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
    """The static parts of the name stack (one per card): each entry is
    the layer cropped to its ink's bounding box with the position to
    composite it at, or ``None`` when the layer is absent. Compositing
    the crop is pixel-identical to compositing the full-size layer
    (outside the crop the alpha is 0)."""

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
    """Build the static name-stack layers for a card of *size* (the
    title and the subtitle rendered uppercase). *manufacturer_logo*
    (white on transparency) is placed above the title's bar when given,
    filled with the bar's own fill; it is part of the bar's layer, so it
    is only placed when the bar is."""
    name = name.upper()
    subtitle = subtitle.upper()
    font_size = _name_font_size(name, round(padding * NAME_SIZE_FACTOR))
    font = ImageFont.truetype(str(FONT_NAME), font_size)
    _set_weight(font, NAME_WEIGHT)
    left, top, bottom = _text_ink_offsets(name, font)
    title_top = round(size[1] * NAME_TITLE_Y)
    inset = padding

    title_mask = Image.new("L", size, 0)
    ImageDraw.Draw(title_mask).text(
        (inset - left, title_top - top), name, font=font, fill=255
    )
    # The title core's alpha (the flat-white core is tinted at the end).
    title_box = title_mask.getbbox()
    title_alpha = title_mask
    # The title's enclosing rectangle's top/bottom (None when there is
    # no title): the subtitle sits below the bottom.
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
        # Below the title (top-right when there is no title):
        # left-aligned with the title's own inset, its rectangle's top
        # edge on the title rectangle's bottom.
        bbox = small.getbbox()
        assert bbox is not None  # the ink is drawn (fill 255 on a black probe)
        if rect_top is not None:
            assert rect_bottom is not None  # derived from title_box, like rect_top
            sub_pad = round((bbox[3] - bbox[1]) * NAME_SUB_RECT_PAD)
            px = inset - bbox[0]
            py = rect_bottom - bbox[1] + sub_pad
        else:
            px, py = size[0] - padding - bbox[2], padding - bbox[1]
        sub_mask = Image.new("L", size, 0)
        sub_mask.paste(255, (px, py, px + small.width, py + small.height), small)
        sub_top = _tint_layer(sub_mask, NAME_TEXT_COLOR, 1.0)
        # The subtitle's enclosing rectangle: the title's rectangle's
        # shape on the subtitle's ink (None when there is no title).
        if rect_top is not None:
            sub_bbox = sub_mask.getbbox()
            assert sub_bbox is not None  # the subtitle's ink was just pasted
            _, sry0, srx1, sry1 = sub_bbox
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

    # The title's enclosing rectangle (None when there is no title): its
    # top-right corner is cut off by a diagonal.
    rect = None
    arrow_alpha = None
    if title_box is not None:
        _, ry0, rx1, ry1 = title_box
        pad = round((ry1 - ry0) * NAME_RECT_PAD)
        assert rect_top is not None
        assert rect_bottom is not None
        top = rect_top
        bottom = rect_bottom
        rect_height = bottom - top
        # The arrow's ink, measured before the rectangle so its width can
        # shape the right edge. A roomy probe (the glyph's ink can spill
        # well past the font size), glyph centered, so the ink is not
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
        right = rx1 + pad + (ink.width if ink is not None else 0) + round(padding / 2)
        # The corner cut (the diagonal of a square, so 45 degrees).
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
        # The small bar above the rectangle: its right edge slants back
        # (a 45-degree diagonal).
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
        # Three squares to the bar's right, slanted the same 45 degrees.
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
        # The manufacturer's logo above the bar, its mark filled with the
        # bar's own fill, so the mark, the bar and the squares share one
        # color.
        if manufacturer_logo is not None:
            logo_w = round(size[0] * MANUFACTURER_LOGO_WIDTH)
            logo_h = round(logo_w * manufacturer_logo.height / manufacturer_logo.width)
            mark = manufacturer_logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            rect.alpha_composite(
                _tint_layer(mark.getchannel("A"), rect_color, 1.0),
                (inset, bar_top - round(padding / 2) - logo_h),
            )
        if ink is not None:
            margin = round(rect_height * NAME_RECT_ARROW_MARGIN)
            # The arrow's alpha (flat white, like the title).
            arrow_alpha = Image.new("L", size, 0)
            arrow_alpha.paste(
                ink, (right - margin - ink.width, bottom - margin - ink.height)
            )

    # Tint the title core and the arrow here (once per card, not per
    # frame) and crop every layer to its ink, so _apply_name composites
    # the ink, not the whole frame.
    def cropped(layer: Image.Image) -> tuple[Image.Image, tuple[int, int]] | None:
        box = layer.getchannel("A").getbbox()
        if box is None:
            return None
        return (layer.crop(box), (box[0], box[1]))

    return _NameLayers(
        cropped(rect) if rect is not None else None,
        cropped(sub_rect) if sub_rect is not None else None,
        cropped(_tint_layer(title_alpha, NAME_TEXT_COLOR, 1.0))
        if title_box is not None
        else None,
        cropped(_tint_layer(arrow_alpha, NAME_TEXT_COLOR, 1.0))
        if arrow_alpha is not None
        else None,
        cropped(sub_top) if sub_top is not None else None,
    )


def _apply_name(art: Image.Image, parts: _NameLayers) -> Image.Image:
    for layer in (parts.rect, parts.sub_rect, parts.title, parts.arrow, parts.sub_top):
        if layer is not None:
            art.alpha_composite(layer[0], layer[1])
    return art


def _with_copyright(
    base: Image.Image, padding: int, color: tuple[int, int, int, int]
) -> Image.Image:
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
    """Pre-stamp the logo and the copyright line onto a transparent
    layer, cropped to its bounding box: the caller composites the crop
    onto each frame after the art is in place, so the stamps stay on top
    of the art. Returns the crop and its position."""
    width, height = size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay = _with_logo(overlay, _scale_logo(logo, width), margin, logo_top)
    overlay = _with_copyright(overlay, padding, color)
    box = overlay.getbbox()
    assert box is not None, "the logo and copyright layer is empty"
    return overlay.crop(box), (box[0], box[1])


def _luma(art: Image.Image, box: tuple[int, int, int, int]) -> float:
    """The mean luma (0..255) of *art* over *box* (the region a stamp
    will cover, deciding its face)."""
    return ImageStat.Stat(art.crop(box).convert("L")).mean[0]


def _overlay_for(
    art: Image.Image,
    size: tuple[int, int],
    black_face: Image.Image,
    white_face: Image.Image,
    margin: int,
    padding: int,
    logo_top: bool = False,
) -> tuple[Image.Image, tuple[int, int]]:
    """The logo and copyright overlay for *art* — the card's first
    composited frame, the art before the stamps. Each stamp's face is
    chosen from the luma of the region it will cover, probed with the
    stamp's own placement (so the sample region and the stamped ink
    cannot drift apart), and the overlay is then built as in
    :func:`_logo_copyright_overlay`."""
    logo_box = _with_logo(
        Image.new("RGBA", size, (0, 0, 0, 0)),
        _scale_logo(white_face, size[0]),
        margin,
        logo_top,
    ).getbbox()
    assert logo_box is not None, "the logo's probe is empty"
    copyright_box = _with_copyright(
        Image.new("RGBA", size, (0, 0, 0, 0)), padding, STAMP_WHITE
    ).getbbox()
    assert copyright_box is not None, "the copyright's probe is empty"
    logo = black_face if _luma(art, logo_box) >= STAMP_LUMA_THRESHOLD else white_face
    color = (
        STAMP_BLACK
        if _luma(art, copyright_box) >= STAMP_LUMA_THRESHOLD
        else STAMP_WHITE
    )
    return _logo_copyright_overlay(size, logo, margin, padding, color, logo_top)
