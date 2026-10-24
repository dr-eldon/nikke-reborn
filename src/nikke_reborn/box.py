"""Compose a box's ``CardBox_Material`` front on the fly from its
``Expansion.json``.

The box's front is the pack's front (:mod:`nikke_reborn.pack`) at the box
material template's size, with the box's background fit
(``fit="cover-bottom"``): the background is scaled down just enough to cover
the whole front and bottom-aligned, so its bottom touches the front's bottom
edge and any excess height is cropped off the top. Like the pack's front it
is built procedurally — never stored: :func:`nikke_reborn._generate`
composes it in memory and hands it to the material composition, and its
inputs are hashed (see :func:`front_source_hash`) into the finished material
so the render is skipped when nothing changed.

The box material template's other two mask rectangles (red top, green side)
are still placeholders; only the blue (front) rectangle is filled.
"""

from __future__ import annotations

from pathlib import Path

import nikke_reborn as nr
from nikke_reborn import pack
from PIL import Image


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


def build_front(
    pack_dir: Path, expansion: dict, size: tuple[int, int]
) -> Image.Image:
    """The box's front: the pack's front (:func:`pack.build_front`) at the
    box's size with the box's background fit (``"cover-bottom"``). The
    result is returned in memory; it is the box material's blue rectangle
    and is never written to disk."""
    return pack.build_front(pack_dir, expansion, size, fit="cover-bottom")


def front_source_hash(pack_dir: Path) -> str:
    """A hash of the box front's inputs: the expansion's
    ``Expansion.json``, the featured NIKKE definitions it lists, the
    background and (when a placement is set) the logo, and the box material
    template that sizes the front. It is computed without rendering the
    front, so the finished material can be skipped (and the front's render
    avoided) when those inputs are unchanged."""
    return pack.front_source_hash(pack_dir, template=nr.BOX_TEMPLATE)
