"""Compose a pack's ``CardPack_Front`` and ``CardPack_Back`` on the fly from
its ``Expansion.json``.

The front and back are built procedurally from the expansion's metadata —
neither is stored: :func:`nikke_reborn._generate` composes them in memory and
hands them to the material composition. The shared front composition
(background, the featured NIKKES, the expansion's logo with its glow) lives in
:mod:`nikke_reborn.expansion`; this module adds the pack's own pieces: the
sizes read from the material template's mask rectangles, the pack's white
NIKE logo placement, and the source hashes that let the finished material and
item skip when the inputs are unchanged.

* the front is the shared composition at the material template's *right* mask
  rectangle's size, with the pack's background fit (``"crop"``: the
  background resized to the front's height and center-cropped to the front's
  width) and the pack's white NIKKE logo.
* the back is the expansion's ``background`` resized to the back's height and
  left-cropped to its exact width (the front center-crops the same
  background), at the material template's *left* mask rectangle's size.
* the white NIKKE logo is stamped on the front at the same placement in the
  material and the item: its width as a fraction of the front's width
  (centered horizontally) and its top inset as a fraction of the front's
  height.

The front's inputs — its ``Expansion.json``, the featured NIKKE definitions
it lists, its background, its logo, the white NIKKE logo, and the material
template that sizes it — are hashed (see :func:`front_source_hash`) into the
finished material and item, so when those inputs are unchanged the front's
render is skipped entirely rather than re-rendered. The back's inputs (the
background and the material template) are hashed the same way (see
:func:`back_source_hash`).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import nikke_reborn as nr
from nikke_reborn.expansion import (
    compose_front,
    fit_background,
    front_source_digest,
    load_background,
    load_expansion,
)
from PIL import Image

# --- the white NIKKE logo -----------------------------------------------------
#: The white logo stamped on the pack's front, at the same placement in the
#: material and the item: its width as a fraction of the front's width
#: (centered horizontally) and its top inset as a fraction of the front's
#: height.
PACK_LOGO = nr.IMAGES_DIR / "Logo_White.png"
PACK_LOGO_WIDTH = 0.6
PACK_LOGO_TOP = 0.04


def front_size() -> tuple[int, int]:
    """The pack front's target size: the material template's *right* mask
    rectangle (the left one is the back). Composing at exactly this size means
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


def back_size() -> tuple[int, int]:
    """The pack back's target size: the material template's *left* mask
    rectangle (the right one is the front). Composing at exactly this size
    means the material composition pastes it with no rescale."""
    with Image.open(nr.PACK_TEMPLATE) as opened:
        template = opened.convert("RGBA")
    rects = nr._pack_mask_rects(nr._pack_mask(template))
    if len(rects) != 2:
        raise nr.GenerationError(
            f"{nr.PACK_TEMPLATE.name} carries {len(rects)} pure-blue mask "
            f"rectangle(s), expected 2 (back, front)"
        )
    rect = rects[0]
    return rect[2] - rect[0], rect[3] - rect[1]


def place_logo(front: Image.Image, rect: tuple[int, int, int, int]) -> None:
    """Composite the white logo onto the front at *rect* (``(left, top,
    right, bottom)``, with right and bottom exclusive — the front's own
    bounds when placed on the front itself): its width is
    :data:`PACK_LOGO_WIDTH` the front's width (centered horizontally) and its
    top inset :data:`PACK_LOGO_TOP` the front's height — unslanted, since the
    material is the flat view. Modifies *front* in place."""
    left, top, right, bottom = rect
    rw, rh = right - left, bottom - top
    with Image.open(PACK_LOGO) as opened:
        logo = opened.convert("RGBA")
    logo_w = round(PACK_LOGO_WIDTH * rw)
    logo = logo.resize(
        (logo_w, round(logo_w * logo.height / logo.width)),
        Image.Resampling.LANCZOS,
    )
    front.alpha_composite(
        logo, (left + (rw - logo_w) // 2, top + round(PACK_LOGO_TOP * rh))
    )


def front_source_hash(pack_dir: Path) -> str:
    """A hash of the front's *inputs* — everything the composed front depends
    on: the expansion's ``Expansion.json``, the featured NIKKE definitions it
    lists, its background and (when a placement is set) its logo, the white
    NIKKE logo, and the material template that sizes it (the shared digest
    from :func:`nikke_reborn.expansion.front_source_digest`, with the pack's
    logo and template). It is computed without rendering the front, so the
    finished material and item can be skipped (and the front's render
    avoided) when those inputs are unchanged."""
    return front_source_digest(pack_dir, PACK_LOGO, nr.PACK_TEMPLATE)


def back_source_hash(pack_dir: Path) -> str:
    """A hash of the back's *inputs* — everything the composed back depends on:
    its ``background`` and the material template that sizes it. It is computed
    without composing the back, so the finished material can be skipped (and
    the back's composition avoided) when those inputs are unchanged."""
    expansion = load_expansion(pack_dir)
    background = expansion.get("background")
    if not background:
        raise nr.GenerationError(f"{pack_dir.name}: missing 'background'")
    digest = hashlib.sha256()
    digest.update((pack_dir / background).resolve().read_bytes())
    digest.update(nr.PACK_TEMPLATE.read_bytes())
    return digest.hexdigest()


def build_front(
    pack_dir: Path,
    expansion: dict,
    size: tuple[int, int],
) -> Image.Image:
    """The pack front: the shared front composition
    (:func:`nikke_reborn.expansion.compose_front`) with the pack's background
    fit and the pack's white NIKKE logo. The result is returned in memory; it
    is the material's right rectangle and is never written to disk."""
    return compose_front(
        pack_dir, expansion, size, fit="crop", place_logo=place_logo
    )


def build_back(
    pack_dir: Path, expansion: dict, size: tuple[int, int]
) -> Image.Image:
    """Compose the pack back from the expansion's ``background``: resized to
    the back's height and left-cropped to its exact width (the front
    center-crops the same background). The result is returned in memory; it is
    the material's left rectangle and is never written to disk."""
    return fit_background(
        load_background(pack_dir, expansion), size, align="left"
    )
