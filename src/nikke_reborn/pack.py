"""Compose a pack's ``CardPack_Front`` and ``CardPack_Back`` on the
fly from its expansion's TOML.

The front and back are built procedurally — neither is stored. The
shared front composition lives in :mod:`nikke_reborn.expansion`; this
module adds the pack's own pieces: the sizes read from the material
template's mask rectangles, the pack's white NIKKE logo placement, and
the source hashes that let the finished material and item skip when
the inputs are unchanged."""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image

from nikke_reborn import expansion
from nikke_reborn.config import (
    IMAGES_DIR,
    ITEM_VIEWER_HEIGHT,
    ITEM_VIEWER_WIDTH,
    PACK_CONFIG,
    PACK_ITEM_NAME,
    PACK_MATERIAL_NAME,
    PACK_MESH,
    PACK_TEMPLATE,
    UNITY_VIEWER,
)
from nikke_reborn.error import GenerationError
from nikke_reborn.expansion import (
    back_source_hash as expansion_back_source_hash,
)
from nikke_reborn.expansion import (
    compose_front,
    fit_background,
    front_source_digest,
    load_item_background,
)
from nikke_reborn.file import (
    _material_hash,
    _save_atomic,
    _stored_hash,
    _viewer_hash,
)
from nikke_reborn.image import _pack_mask, _pack_mask_rects
from nikke_reborn.linear import _linear_over
from nikke_reborn.preset import Preset

# The white logo stamped on the pack's front (its width and top inset,
# as fractions of the front's width and height).
PACK_LOGO = IMAGES_DIR / "Logo_White.png"
PACK_LOGO_WIDTH = 0.6
PACK_LOGO_TOP = 0.04


def front_size() -> tuple[int, int]:
    """The pack front's target size: the material template's *right*
    mask rectangle (the left one is the back), so the material
    composition pastes it with no rescale."""
    with Image.open(PACK_TEMPLATE) as opened:
        template = opened.convert("RGBA")
    rects = _pack_mask_rects(_pack_mask(template))
    if len(rects) != 2:
        raise GenerationError(
            f"{PACK_TEMPLATE.name} carries {len(rects)} pure-blue mask "
            f"rectangle(s), expected 2 (back, front)"
        )
    rect = rects[1]
    return rect[2] - rect[0], rect[3] - rect[1]


def back_size() -> tuple[int, int]:
    """The pack back's target size: the material template's *left*
    mask rectangle (the right one is the front), so the material
    composition pastes it with no rescale."""
    with Image.open(PACK_TEMPLATE) as opened:
        template = opened.convert("RGBA")
    rects = _pack_mask_rects(_pack_mask(template))
    if len(rects) != 2:
        raise GenerationError(
            f"{PACK_TEMPLATE.name} carries {len(rects)} pure-blue mask "
            f"rectangle(s), expected 2 (back, front)"
        )
    rect = rects[0]
    return rect[2] - rect[0], rect[3] - rect[1]


def _nikke_logo_size(size: tuple[int, int]) -> tuple[int, int]:
    """The stamped mark's (width, height) at the pack front's *size*:
    its width is a fraction of the front's width, its height
    proportional (see :data:`PACK_LOGO_WIDTH`)."""
    with Image.open(PACK_LOGO) as opened:
        logo_w = round(PACK_LOGO_WIDTH * size[0])
        return logo_w, round(logo_w * opened.height / opened.width)


def place_logo(front: Image.Image, rect: tuple[int, int, int, int]) -> None:
    """Composite the white logo onto *front* at *rect* (its own bounds
    when placed on the front itself; right and bottom exclusive): its
    width is a fraction of the front's width (centered horizontally)
    and its top inset a fraction of the front's height — unslanted,
    since the material is the flat view. Modifies *front* in
    place."""
    left, top, right, bottom = rect
    rw, rh = right - left, bottom - top
    logo_w, logo_h = _nikke_logo_size((rw, rh))
    with Image.open(PACK_LOGO) as opened:
        logo = opened.convert("RGBA").resize((logo_w, logo_h), Image.Resampling.LANCZOS)
    front.alpha_composite(
        logo, (left + (rw - logo_w) // 2, top + round(PACK_LOGO_TOP * rh))
    )


def front_source_hash(exp: expansion.Expansion) -> str:
    """A hash of the front's inputs (see
    :func:`nikke_reborn.expansion.front_source_digest`), with the
    pack's logo and template: computed without rendering the front, so
    the finished material and item can be skipped when those inputs
    are unchanged."""
    return front_source_digest(exp, PACK_LOGO, PACK_TEMPLATE)


def back_source_hash(exp: expansion.Expansion) -> str:
    """A hash of the back's inputs (the background and the material
    template): computed without composing the back, so the finished
    material can be skipped when those inputs are unchanged."""
    return expansion_back_source_hash(exp, PACK_TEMPLATE)


def build_front(exp: expansion.Expansion, size: tuple[int, int]) -> Image.Image:
    """The pack front: the shared front composition with the pack's
    background fit, the expansion's logo covering the NIKKE logo (no
    smaller in either dimension) and the white NIKKE logo — or, when
    the expansion's logo is the NIKKE logo itself, the expansion's
    logo at the top (the NIKKE logo's slot), in memory (the
    material's right rectangle, never written to disk)."""
    if expansion.is_nikke_logo(exp):
        return compose_front(
            exp,
            size,
            fit="crop",
            place_logo=None,
            expansion_logo_placement="top",
        )
    # Fractions of the face that round-trip to the NIKKE mark's exact
    # pixel width and height (the composition multiplies them back by
    # the face's dimensions): the logo is scaled to cover the mark's
    # box, so neither dimension is ever smaller.
    nikke_w, nikke_h = _nikke_logo_size(size)
    return compose_front(
        exp,
        size,
        fit="crop",
        place_logo=place_logo,
        expansion_logo_height=nikke_h / size[1],
        expansion_logo_min_width=nikke_w / size[0],
    )


def build_back(exp: expansion.Expansion, size: tuple[int, int]) -> Image.Image:
    """The pack back: the expansion's items' background (see
    :func:`nikke_reborn.expansion.load_item_background`) resized to the
    back's height and left-cropped to its exact width (the front
    center-crops the same background), in memory (the material's left
    rectangle, never written to disk)."""
    return fit_background(load_item_background(exp), size, align="left")


def _process_pack_material(
    exp: expansion.Expansion,
    front: Image.Image,
    front_source: str,
    back: Image.Image,
    back_source: str,
    force: bool = False,
    preset: Preset = Preset.DEFAULT,
) -> tuple[Path, bool]:
    """Composite the pack's back and front onto the material template's
    mask rectangles (left: back, right: front) at the template's own
    size, and scale the finished material down to the run's size in
    one whole-image pass (nothing resampled twice). Written atomically
    to the output preset's set folder with the template and the
    back's and front's inputs embedded, like a finished card; returns
    ``(out_path, skipped)``."""
    source_hash = _material_hash(
        PACK_TEMPLATE,
        front_source=front_source,
        back_source=back_source,
        preset=preset,
    )
    out_path = preset.set_path(exp.name) / PACK_MATERIAL_NAME
    if not force and out_path.is_file() and _stored_hash(out_path) == source_hash:
        return out_path, True
    with Image.open(PACK_TEMPLATE) as opened:
        template = opened.convert("RGBA")
        rects = _pack_mask_rects(_pack_mask(template))
        if len(rects) != 2:
            raise GenerationError(
                f"pack material template {PACK_TEMPLATE.name} carries "
                f"{len(rects)} pure-blue mask rectangle(s), expected 2 (back, front)"
            )
        back_target = (rects[0][2] - rects[0][0], rects[0][3] - rects[0][1])
        if back.size != back_target:
            back = back.resize(back_target, Image.Resampling.LANCZOS)
        _linear_over(template, back, (rects[0][0], rects[0][1]))
        front_target = (rects[1][2] - rects[1][0], rects[1][3] - rects[1][1])
        if front.size != front_target:
            front = front.resize(front_target, Image.Resampling.LANCZOS)
        _linear_over(template, front, (rects[1][0], rects[1][1]))
        final = template.convert("RGB")
    if preset.scale != 1.0:
        final = final.resize(
            (
                round(final.width * preset.scale),
                round(final.height * preset.scale),
            ),
            Image.Resampling.LANCZOS,
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _save_atomic(final, out_path, source_hash)
    return out_path, False


def _process_pack_item(
    exp: expansion.Expansion,
    force: bool = False,
    preset: Preset = Preset.DEFAULT,
) -> tuple[Path, bool]:
    """Render the pack's item with :data:`UNITY_VIEWER`: the pack's mesh
    textured with the finished material (which must exist first — the
    item is rendered from its output file), posed by the viewer
    configuration, at the run's output size. The plain PNG the viewer
    writes is re-saved with the mesh, material and output size embedded
    and moved into place atomically; returns ``(out_path, skipped)``."""
    width = round(ITEM_VIEWER_WIDTH * preset.scale)
    height = round(ITEM_VIEWER_HEIGHT * preset.scale)
    set_path = preset.set_path(exp.name)
    material_path = set_path / PACK_MATERIAL_NAME
    source_hash = _viewer_hash(PACK_MESH, material_path, PACK_CONFIG, preset)
    out_path = set_path / PACK_ITEM_NAME
    if not force and out_path.is_file() and _stored_hash(out_path) == source_hash:
        return out_path, True
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(out_path.name + ".render")
    try:
        result = subprocess.run(
            [
                UNITY_VIEWER,
                str(PACK_MESH),
                str(material_path),
                "--config",
                str(PACK_CONFIG),
                "--width",
                str(width),
                "--height",
                str(height),
                "--out",
                str(tmp_path),
            ],
            capture_output=True,
            check=False,  # the exit code is checked below (with the stderr)
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        tmp_path.unlink(missing_ok=True)
        raise GenerationError(f"could not run {UNITY_VIEWER}: {exc}") from exc
    if result.returncode != 0 or not tmp_path.is_file():
        detail = result.stderr.strip()
        detail = f" ({detail[-500:]})" if detail else ""
        tmp_path.unlink(missing_ok=True)
        raise GenerationError(
            f"{UNITY_VIEWER} failed (exit {result.returncode}){detail}"
        )
    with Image.open(tmp_path) as rendered:
        _save_atomic(rendered, out_path, source_hash)
    tmp_path.unlink(missing_ok=True)
    return out_path, False
