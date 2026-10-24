"""Compose a box's ``CardBox_Material`` front on the fly from its
``Expansion.json``.

The box's front is the shared front composition (see
:mod:`nikke_reborn.expansion`) at the box material template's size, with the
box's own pieces: the box's background fit (``"cover-bottom"``: the
background scaled down just enough to cover the whole front and
bottom-aligned, so its bottom touches the front's bottom edge and any excess
height is cropped off the top), the box's white NIKKE logo, and the box's
expansion-logo sizing — both sized by the front's height rather than its
width (the box's front is landscape, where the pack's width-based sizing is
far too big).

Like the pack's front it is built procedurally — never stored:
:func:`nikke_reborn._generate` composes it in memory and hands it to the
material composition, and its inputs are hashed (see
:func:`front_source_hash`) into the finished material so the render is
skipped when nothing changed.

The box material template's other two mask rectangles (red top, green side)
are still placeholders; only the blue (front) rectangle is filled.
"""

from __future__ import annotations

from pathlib import Path

import nikke_reborn as nr
from nikke_reborn.expansion import compose_front, front_source_digest
from PIL import Image

# --- the white NIKKE logo -----------------------------------------------------
#: The white logo stamped on the box's front: its height as a fraction of
#: the front's height, placed at the front's top-left with its corner inset
#: by that margin (a fraction of the front's height). Sized by height — the
#: box's front is landscape, where the pack's width-based sizing is far too
#: big.
BOX_LOGO = nr.IMAGES_DIR / "Logo_White.png"
BOX_LOGO_HEIGHT = 0.25
BOX_LOGO_MARGIN = 0.1

# --- the expansion's logo -----------------------------------------------------
#: The expansion's logo (``<pack>/Logo.png``) on the box's front: its height
#: as a fraction of the front's height (its width proportional) — sized by
#: height, where the pack's width-based sizing is far too big on the
#: landscape front.
BOX_EXPANSION_LOGO_HEIGHT = 0.25


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
    fit, the box's white NIKKE logo, and the box's expansion-logo sizing
    (:data:`BOX_EXPANSION_LOGO_HEIGHT` the front's height, instead of the
    pack's width-based sizing). The result is returned in memory; it is the
    box material's blue rectangle and is never written to disk."""
    return compose_front(
        pack_dir,
        expansion,
        size,
        fit="cover-bottom",
        place_logo=place_logo,
        expansion_logo_height=BOX_EXPANSION_LOGO_HEIGHT,
    )
