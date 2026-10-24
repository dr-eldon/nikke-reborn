"""Compose a box's ``CardBox_Material`` front on the fly from its
``Expansion.json``.

The box's front is the shared front composition (see
:mod:`nikke_reborn.expansion`) at the box material template's size, with the
box's own pieces: the box's background fit (``"cover-bottom"``: the
background scaled down just enough to cover the whole front and
bottom-aligned, so its bottom touches the front's bottom edge and any excess
height is cropped off the top), the box's white NIKKE logo, the box's
expansion-logo sizing, and the box's character sizing (hero and group) —
the latter two sized by the front's height rather than its width (the box's
front is landscape, where the pack's width-based sizing is far too big).

Like the pack's front it is built procedurally — never stored:
:func:`nikke_reborn._generate` composes it in memory and hands it to the
material composition, and its inputs are hashed (see
:func:`front_source_hash`) into the finished material so the render is
skipped when nothing changed.

The green (side) rectangle is filled with the expansion's background
(fitted to cover the side, taking the scene's right side), the
expansion's logo top-centered and the white NIKKE logo bottom-center;
the red (top) rectangle is still a placeholder.
"""

from __future__ import annotations

from pathlib import Path

import nikke_reborn as nr
from nikke_reborn.expansion import (
    LOGO_NAME,
    _background_glow_color,
    _composite_logo,
    _fit_cover_bottom,
    _image_average,
    compose_front,
    front_source_digest,
    load_background,
)
from PIL import Image

# --- the white NIKKE logo -----------------------------------------------------
#: The white logo stamped on the box's front (top-left) and side
#: (bottom-center): its height as a fraction of the face's height, its
#: corner inset by that margin (a fraction of the face's height). Sized by
#: height — the box's front is landscape, where the pack's width-based
#: sizing is far too big.
BOX_LOGO = nr.IMAGES_DIR / "Logo_White.png"
BOX_LOGO_HEIGHT = 0.15
BOX_LOGO_MARGIN = 0.05

# --- the expansion's logo -----------------------------------------------------
#: The expansion's logo (``<pack>/Logo.png``) on the box's front and side:
#: its height as a fraction of the face's height (its width proportional)
#: — sized by height, where the pack's width-based sizing is far too big on
#: the landscape front.
BOX_EXPANSION_LOGO_HEIGHT = 1 / 3

# --- the featured NIKKES (the hero and the group behind it) -------------------
#: The sizing on the box's front, as fractions of the front — in place of the
#: shared :data:`nikke_reborn.expansion.HERO_HEIGHT`,
#: :data:`nikke_reborn.expansion.BACK_HEIGHT` and
#: :data:`nikke_reborn.expansion.BACK_OFFSET_X` (the pack's portrait front):
#: the box's landscape front wants bigger characters, and the group a bit
#: closer to the hero than the pack's offset. The hero/back ratio is kept
#: roughly constant, so the group still reads as being behind the hero.
BOX_HERO_HEIGHT = 0.9
BOX_BACK_HEIGHT = 0.7
BOX_BACK_OFFSET_X = 0.30


def front_size() -> tuple[int, int]:
    """The box front's target size: the box material template's blue mask
    rectangle (its other two masks — red top and green side — are not pure
    blue, so the pack's pure-blue detection picks out exactly the front).
    Composing at exactly this size means the material composition pastes it
    with no rescale."""
    with Image.open(nr.BOX_TEMPLATE) as opened:
        template = opened.convert("RGBA")
    rects = nr._pack_mask_rects(nr._pack_mask(template))
    if len(rects) != 1:
        raise nr.GenerationError(
            f"{nr.BOX_TEMPLATE.name} carries {len(rects)} pure-blue mask "
            f"rectangle(s), expected 1 (front)"
        )
    rect = rects[0]
    return rect[2] - rect[0], rect[3] - rect[1]


def side_size() -> tuple[int, int]:
    """The box side's target size: the box material template's green mask
    rectangle (the pure-green placeholder, detected the way the front is
    detected in blue). Composing at exactly this size means the material
    composition pastes it with no rescale."""
    with Image.open(nr.BOX_TEMPLATE) as opened:
        template = opened.convert("RGBA")
    rects = nr._pack_mask_rects(nr._box_side_mask(template))
    if len(rects) != 1:
        raise nr.GenerationError(
            f"{nr.BOX_TEMPLATE.name} carries {len(rects)} pure-green mask "
            f"rectangle(s), expected 1 (side)"
        )
    rect = rects[0]
    return rect[2] - rect[0], rect[3] - rect[1]


def place_logo(front: Image.Image, rect: tuple[int, int, int, int]) -> None:
    """Composite the white logo onto the front at *rect* (``(left, top,
    right, bottom)``, with right and bottom exclusive — the front's own
    bounds when placed on the front itself): its height is
    :data:`BOX_LOGO_HEIGHT` the front's height, placed at the front's
    top-left with its corner inset :data:`BOX_LOGO_MARGIN` the front's
    height — unslanted, since the material is the flat view. Sized by
    height, where the pack's width-based sizing is far too big on the
    landscape front. Modifies *front* in place."""
    left, top, right, bottom = rect
    rh = bottom - top
    with Image.open(BOX_LOGO) as opened:
        logo = opened.convert("RGBA")
    logo_h = round(BOX_LOGO_HEIGHT * rh)
    logo = logo.resize(
        (round(logo_h * logo.width / logo.height), logo_h),
        Image.Resampling.LANCZOS,
    )
    margin = round(BOX_LOGO_MARGIN * rh)
    front.alpha_composite(logo, (left + margin, top + margin))


def place_side_logo(side: Image.Image) -> None:
    """Composite the white logo onto the side, bottom-center: its height is
    :data:`BOX_LOGO_HEIGHT` the side's height (both faces share the box's
    vertical extent, so the logo lands at the same physical size as on the
    front), its bottom edge inset :data:`BOX_LOGO_MARGIN` the side's height
    from the side's bottom edge, and it is centered horizontally —
    unslanted, since the material is the flat view. Modifies *side* in
    place."""
    with Image.open(BOX_LOGO) as opened:
        logo = opened.convert("RGBA")
    logo_h = round(BOX_LOGO_HEIGHT * side.height)
    logo = logo.resize(
        (round(logo_h * logo.width / logo.height), logo_h),
        Image.Resampling.LANCZOS,
    )
    x = (side.width - logo.width) // 2
    y = side.height - round(BOX_LOGO_MARGIN * side.height) - logo_h
    side.alpha_composite(logo, (x, y))


def place_side_expansion_logo(
    side: Image.Image, pack_dir: Path, expansion: dict
) -> None:
    """Composite the expansion's logo (``<pack>/Logo.png``) onto the side,
    top-centered — the same glow treatment as the front's (see
    :func:`nikke_reborn.expansion._composite_logo`): its height is
    :data:`BOX_EXPANSION_LOGO_HEIGHT` the side's height (the same physical
    size as on the front, since both faces share the box's vertical
    extent), inset :data:`nikke_reborn.expansion.LOGO_MARGIN` the side's
    height from the top edge. Only when the expansion names a ``logo``
    placement; the side's placement is always ``"top"``. The glow is
    sampled from the side before the logos are composited, so it is tinted
    by the scene. Modifies *side* in place."""
    placement = expansion.get("logo")
    if placement is None:
        return
    logo_path = pack_dir / LOGO_NAME
    if not logo_path.is_file():
        raise nr.GenerationError(
            f"{pack_dir.name}: logo placement {placement!r} is set but "
            f"{LOGO_NAME!r} is missing"
        )
    glow_color = _background_glow_color(_image_average(side))
    _composite_logo(
        side,
        Image.open(logo_path).convert("RGBA"),
        (side.width, side.height),
        "top",
        glow_color,
        mark_height=BOX_EXPANSION_LOGO_HEIGHT,
    )


def front_source_hash(pack_dir: Path) -> str:
    """A hash of the box front's inputs: the expansion's
    ``Expansion.json``, the featured NIKKE definitions it lists, the
    background and (when a placement is set) the logo, the white NIKKE logo
    placed on the front, and the box material template that sizes it (the
    shared digest from
    :func:`nikke_reborn.expansion.front_source_digest`, with the box's logo
    and template). It is computed without rendering the front, so the
    finished material can be skipped (and the front's render avoided) when
    those inputs are unchanged."""
    return front_source_digest(pack_dir, BOX_LOGO, nr.BOX_TEMPLATE)


def build_front(
    pack_dir: Path, expansion: dict, size: tuple[int, int]
) -> Image.Image:
    """The box front: the shared front composition
    (:func:`nikke_reborn.expansion.compose_front`) with the box's background
    fit, the box's white NIKKE logo, the box's expansion-logo sizing
    (:data:`BOX_EXPANSION_LOGO_HEIGHT` the front's height, instead of the
    pack's width-based sizing), and the box's character sizing
    (:data:`BOX_HERO_HEIGHT`, :data:`BOX_BACK_HEIGHT` and
    :data:`BOX_BACK_OFFSET_X`, instead of the shared
    :data:`nikke_reborn.expansion.HERO_HEIGHT`,
    :data:`nikke_reborn.expansion.BACK_HEIGHT` and
    :data:`nikke_reborn.expansion.BACK_OFFSET_X`). The result is returned in
    memory; it is the box material's blue rectangle and is never written to
    disk."""
    return compose_front(
        pack_dir,
        expansion,
        size,
        fit="cover-bottom",
        place_logo=place_logo,
        expansion_logo_height=BOX_EXPANSION_LOGO_HEIGHT,
        hero_height=BOX_HERO_HEIGHT,
        back_height=BOX_BACK_HEIGHT,
        back_offset_x=BOX_BACK_OFFSET_X,
    )


def build_side(
    pack_dir: Path, expansion: dict, size: tuple[int, int]
) -> Image.Image:
    """The box side: the expansion's background fitted to cover the side
    (like the front's ``"cover-bottom"``), but right-aligned instead of
    center-cropped — the side takes the scene's right side — with the
    expansion's logo top-centered (see
    :func:`place_side_expansion_logo`) and the white NIKKE logo
    bottom-center (see :func:`place_side_logo`). The result is returned in
    memory, like the front: it is the box material's green rectangle and is
    never written to disk. The side's inputs (the background, the
    expansion's logo when a placement is set, the white logo and the
    template) are a subset of the front's, so the front's source hash (see
    :func:`front_source_hash`) covers it."""
    background = load_background(pack_dir, expansion)
    side = _fit_cover_bottom(background, size, align="right")
    place_side_expansion_logo(side, pack_dir, expansion)
    place_side_logo(side)
    return side
