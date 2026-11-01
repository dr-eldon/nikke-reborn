"""The card's lettering: the name stack (title, subtitle and their bars)
and the copyright line.

The name and subtitle are rasterized once per card into static layers
(:func:`_name_layers`, gathered in :class:`_NameLayers`) and composited
onto every frame (:func:`_apply_name`): the title in a flat dark bar with
its top-right corner cut off at 45 degrees, the slanted bar and the three
slanted squares above it, the manufacturer's logo above the bar, the
subtitle in a bar filled with the background's dominant hue at a fixed
dark level (:func:`_sample_context` for the hue, :func:`_set_luma` for
the level), and the arrow in the title bar's right padding.
The font size (:func:`_name_font_size`, :func:`_subtitle_font_size`), the
weight (:func:`_set_weight`, variable fonts only) and the ink offsets
(:func:`_text_ink_offsets`) are measured on probe renders. The copyright
line is stamped by :func:`_with_copyright` and, with the logo, pre-composited
into a per-frame overlay by :func:`_logo_copyright_overlay`.
"""

from __future__ import annotations

import colorsys
import statistics

from PIL import Image, ImageDraw, ImageFont

from nikke_reborn.config import CARD_REFERENCE_WIDTH, FONT, FONTS_DIR
from nikke_reborn.image import _scale_logo, _set_luma, _with_logo

#: Aire Exterior face for the card name (vendored static font, SIL OFL).
FONT_NAME = FONTS_DIR / "AireExterior.ttf"

#: ChocolateClassicalSans face for the title rectangle's arrow (vendored).
FONT_RECT_ARROW = FONTS_DIR / "ChocolateClassicalSans-Regular.ttf"

#: The manufacturer's logo above the title's bar: its width as a fraction
#: of the frame's width (its height proportional), its left edge at the
#: card's padding (the title's own inset), a gap of padding / 2 between
#: its bottom and the bar's top.
MANUFACTURER_LOGO_WIDTH = 0.11

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

# --- name stack effects -------------------------------------------------
# Context sampling for the subtitle rectangle's tint (the background's
# dominant hue at NAME_RECT_LUMA, via _sample_context).
NAME_SAMPLE_PX = 24  # sample resolution
CONTEXT_FALLBACK = (170, 235, 255)  # hue/sat source for (near)-gray art
CONTEXT_MIN_QUALIFY = 0.25  # min fraction of sample pixels that are colored
CONTEXT_SAT_BOOST = 1.4  # the sampled saturation is boosted...
CONTEXT_SAT_MIN = 0.45  # ...and clamped, so the tint stays visible...
CONTEXT_SAT_MAX = 0.90  # ...without washing out

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
