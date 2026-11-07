"""Compose a box's ``CardBox_Material`` faces on the fly from its
expansion's TOML.

The front is the shared front composition (see
:mod:`nikke_reborn.expansion`) at the box material template's size,
with the box's own pieces: its background fit, its NIKKE logo (the
white mark, with its drop shadow when the region it lands on is too
bright — see the ``BOX_LOGO*`` constants), its expansion-logo sizing,
and its character sizing — sized by the face's height, since the
box's front is landscape. The side and top (which
the bottom face shares) carry the expansion's items' background
(see :func:`nikke_reborn.expansion.load_item_background`), the
expansion's logo center-center and the NIKKE logo.

Like the pack's front they are built procedurally — never stored — and
their inputs are hashed (see :func:`front_source_hash`) into the
finished material so the render is skipped when nothing changed (the
side's and top's inputs are subsets of the front's)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image

from nikke_reborn import expansion
from nikke_reborn.config import (
    BOX_CONFIG,
    BOX_ITEM_NAME,
    BOX_MATERIAL_NAME,
    BOX_MESH,
    BOX_TEMPLATE,
    IMAGES_DIR,
    ITEM_VIEWER_HEIGHT,
    ITEM_VIEWER_WIDTH,
    UNITY_VIEWER,
)
from nikke_reborn.error import GenerationError
from nikke_reborn.expansion import (
    _background_glow_color,
    _composite_logo,
    _fit_cover,
    _image_average,
    _logo_glow_layer,
    compose_front,
    front_source_digest,
    load_item_background,
    load_logo,
)
from nikke_reborn.file import (
    _material_hash,
    _save_atomic,
    _stored_hash,
    _viewer_hash,
)
from nikke_reborn.image import (
    _at_oklch_lightness,
    _box_side_mask,
    _box_top_mask,
    _pack_mask,
    _pack_mask_rects,
)
from nikke_reborn.linear import _linear_over
from nikke_reborn.preset import Preset

# The NIKKE logo stamped on the box's faces (its height as a fraction
# of the face's height, its corner inset by that margin): always the
# white mark, which drops its shadow when the region it lands on is
# too bright for plain white (see
# :data:`BOX_LOGO_SHADOW_BRIGHTNESS`).
BOX_LOGO = IMAGES_DIR / "Logo_White.png"
BOX_LOGO_HEIGHT = 0.15
BOX_LOGO_MARGIN = 0.05

# The region's mean luminance (0-255) from which the white mark
# carries its drop shadow: a white mark carries no contrast against a
# region this bright (the shadow restores it).
BOX_LOGO_SHADOW_BRIGHTNESS = 180

# The mark's drop shadow — the mark's blurred silhouette behind it,
# tinted with the region it lands on at
# :data:`BOX_LOGO_SHADOW_LIGHTNESS`'s Oklch lightness — the summary
# grid's logo's treatment (see :mod:`nikke_reborn.spritesheet`, which
# offsets its shadow down-right): its blur radius and offset
# (fractions of the mark's height — a zero offset centers it on the
# mark) and its peak opacity.
BOX_LOGO_SHADOW_RADIUS = 0.05
BOX_LOGO_SHADOW_OFFSET = 0
BOX_LOGO_SHADOW_ALPHA = 1.0

# The shadow's tint, the region's representative color (see
# :func:`nikke_reborn.expansion._image_average`) at this Oklch
# lightness (hue and chroma kept — see
# :func:`nikke_reborn.image._at_oklch_lightness`): a tint in the
# scene's own hue at a constant depth blends the shadow into the
# background (a black shadow would cut a hole in it).
BOX_LOGO_SHADOW_LIGHTNESS = 0.5

# The expansion's logo's height on the box's front and side (a
# fraction of the face's height).
BOX_EXPANSION_LOGO_HEIGHT = 1 / 3

# The expansion's logo's minimum width on the box's front (a fraction
# of the front's width): a mark sized by
# :data:`BOX_EXPANSION_LOGO_HEIGHT` and narrower than this is scaled up
# to this width (its height growing proportionally).
BOX_FRONT_EXPANSION_LOGO_MIN_WIDTH = 2 / 5

# The expansion's logo's width on the box's top (a fraction of the
# top's width).
BOX_TOP_EXPANSION_LOGO_WIDTH = 2 / 5

# The hero and group sizing on the box's front (fractions of the
# front): in place of the pack's, the box's landscape front wants
# bigger characters and the group a bit closer to the hero — the
# hero/back ratio is kept roughly constant, so the group still reads
# as being behind the hero.
BOX_HERO_HEIGHT = 0.9
BOX_BACK_HEIGHT = 0.7
BOX_BACK_OFFSET_X = 0.30


def front_size() -> tuple[int, int]:
    """The box front's target size: the box material template's blue
    mask rectangle (the other two masks — red top and green side — are
    not pure blue, so the pack's pure-blue detection picks out exactly
    the front), so the material composition pastes it with no
    rescale."""
    with Image.open(BOX_TEMPLATE) as opened:
        template = opened.convert("RGBA")
    rects = _pack_mask_rects(_pack_mask(template))
    if len(rects) != 1:
        raise GenerationError(
            f"{BOX_TEMPLATE.name} carries {len(rects)} pure-blue mask "
            f"rectangle(s), expected 1 (front)"
        )
    rect = rects[0]
    return rect[2] - rect[0], rect[3] - rect[1]


def side_size() -> tuple[int, int]:
    """The box side's target size: the box material template's green
    mask rectangle, so the material composition pastes it with no
    rescale."""
    with Image.open(BOX_TEMPLATE) as opened:
        template = opened.convert("RGBA")
    rects = _pack_mask_rects(_box_side_mask(template))
    if len(rects) != 1:
        raise GenerationError(
            f"{BOX_TEMPLATE.name} carries {len(rects)} pure-green mask "
            f"rectangle(s), expected 1 (side)"
        )
    rect = rects[0]
    return rect[2] - rect[0], rect[3] - rect[1]


def top_size() -> tuple[int, int]:
    """The box top's target size: the box material template's red mask
    rectangle — the top's paste region, which the bottom face shares —
    so the material composition pastes it with no rescale."""
    with Image.open(BOX_TEMPLATE) as opened:
        template = opened.convert("RGBA")
    rects = _pack_mask_rects(_box_top_mask(template))
    if len(rects) != 1:
        raise GenerationError(
            f"{BOX_TEMPLATE.name} carries {len(rects)} pure-red mask "
            f"rectangle(s), expected 1 (top)"
        )
    rect = rects[0]
    return rect[2] - rect[0], rect[3] - rect[1]


def _nikke_logo_size(face_height: int) -> tuple[int, int]:
    """The stamped mark's (width, height) at *face_height* — the same
    for both variants (they share the mark's geometry)."""
    with Image.open(BOX_LOGO) as opened:
        logo_h = round(BOX_LOGO_HEIGHT * face_height)
        return round(logo_h * opened.width / opened.height), logo_h


def _region_brightness(color: tuple[int, int, int]) -> int:
    """The mean luminance (0-255) of *color*: the ITU-R BT.601 luma of
    a region's area-averaged color (see
    :func:`nikke_reborn.expansion._image_average`)."""
    r, g, b = color
    return round(0.299 * r + 0.587 * g + 0.114 * b)


def _nikke_logo(width: int, height: int) -> Image.Image:
    """The white NIKKE mark resized to (width, height) for stamping
    (see :data:`BOX_LOGO`)."""
    with Image.open(BOX_LOGO) as opened:
        return opened.convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)


def _stamp_logo(
    face: Image.Image, left: int, top: int, width: int, height: int
) -> None:
    """The white NIKKE mark at (left, top) on *face*, with its drop
    shadow (see the ``BOX_LOGO_SHADOW_*`` constants — its tint, the
    region's representative color at
    :data:`BOX_LOGO_SHADOW_LIGHTNESS`'s Oklch lightness, sampled
    before the mark is composited) when the region it lands on is too
    bright for plain white (see :data:`BOX_LOGO_SHADOW_BRIGHTNESS`).
    Modifies *face* in place."""
    logo = _nikke_logo(width, height)
    region = _image_average(face.crop((left, top, left + width, top + height)))
    if _region_brightness(region) >= BOX_LOGO_SHADOW_BRIGHTNESS:
        shadow, pad = _logo_glow_layer(
            logo,
            round(BOX_LOGO_SHADOW_RADIUS * height),
            _at_oklch_lightness(region, BOX_LOGO_SHADOW_LIGHTNESS),
            BOX_LOGO_SHADOW_ALPHA,
        )
        offset = round(BOX_LOGO_SHADOW_OFFSET * height)
        _linear_over(face, shadow, (left + offset - pad, top + offset - pad))
    _linear_over(face, logo, (left, top))


def place_logo(front: Image.Image, rect: tuple[int, int, int, int]) -> None:
    """Composite the NIKKE mark onto the front at *rect* (its own bounds
    when placed on the front itself; right and bottom exclusive): its
    height is a fraction of the front's height, at the front's top-left
    with its corner inset — unslanted, since the material is the flat
    view. Modifies *front* in place."""
    left, top, _, bottom = rect
    rh = bottom - top
    margin = round(BOX_LOGO_MARGIN * rh)
    _stamp_logo(front, left + margin, top + margin, *_nikke_logo_size(rh))


def place_side_logo(side: Image.Image) -> None:
    """Composite the NIKKE mark onto the side, bottom-center: its height
    is a fraction of the side's height (both faces share the box's
    vertical extent, so the logo lands at the same physical size as on
    the front), its bottom edge inset from the side's bottom edge,
    centered horizontally — unslanted, since the material is the flat
    view. Modifies *side* in place."""
    logo_w, logo_h = _nikke_logo_size(side.height)
    x = (side.width - logo_w) // 2
    y = side.height - round(BOX_LOGO_MARGIN * side.height) - logo_h
    _stamp_logo(side, x, y, logo_w, logo_h)


def place_top_logo(top: Image.Image) -> None:
    """Composite the NIKKE mark onto the top, top-right: its height is a
    fraction of the top's height, with its corner inset — unslanted,
    since the material is the flat view. Modifies *top* in place."""
    logo_w, logo_h = _nikke_logo_size(top.height)
    margin = round(BOX_LOGO_MARGIN * top.height)
    left = top.width - margin - logo_w
    _stamp_logo(top, left, margin, logo_w, logo_h)


def place_center_expansion_logo(
    face: Image.Image,
    exp: expansion.Expansion,
    width_fraction: float | None = None,
) -> None:
    """Composite the expansion's logo onto a face (the side or the
    top), center-center — the same glow treatment as the front's (see
    :func:`nikke_reborn.expansion._composite_logo`): its height is a
    fraction of the face's height (the side), or, when *width_fraction*
    is given (the top), its width is that fraction of the face's width
    (its height proportional). The glow is sampled from the face before
    the logos are composited, so it is tinted by the scene. Modifies
    *face* in place."""
    mark, _ = load_logo(exp)
    glow_color = _background_glow_color(_image_average(face))
    if width_fraction is None:
        _composite_logo(
            face,
            mark,
            (face.width, face.height),
            "center",
            glow_color,
            mark_height=BOX_EXPANSION_LOGO_HEIGHT,
        )
    else:
        _composite_logo(
            face,
            mark,
            (face.width, face.height),
            "center",
            glow_color,
            width_fraction=width_fraction,
        )


def front_source_hash(exp: expansion.Expansion) -> str:
    """A hash of the box front's inputs (see
    :func:`nikke_reborn.expansion.front_source_digest`), with the
    box's logo and template: computed without rendering the front, so
    the finished material can be skipped when those inputs are
    unchanged."""
    return front_source_digest(exp, BOX_LOGO, BOX_TEMPLATE)


def build_front(exp: expansion.Expansion, size: tuple[int, int]) -> Image.Image:
    """The box front: the shared front composition with the box's
    background fit, NIKKE logo, expansion-logo sizing and character
    sizing (see the ``BOX_*`` constants), in memory (the
    material's blue rectangle, never written to disk). When the
    expansion's logo is the NIKKE logo itself, the stamp is omitted and
    the expansion's logo sits in its slot (the top-left corner, the
    stamp's size and inset) instead."""
    if expansion.is_nikke_logo(exp):
        return compose_front(
            exp,
            size,
            fit="cover-bottom",
            place_logo=None,
            expansion_logo_height=BOX_LOGO_HEIGHT,
            expansion_logo_corner_inset=BOX_LOGO_MARGIN,
            hero_height=BOX_HERO_HEIGHT,
            back_height=BOX_BACK_HEIGHT,
            back_offset_x=BOX_BACK_OFFSET_X,
        )
    return compose_front(
        exp,
        size,
        fit="cover-bottom",
        place_logo=place_logo,
        expansion_logo_height=BOX_EXPANSION_LOGO_HEIGHT,
        expansion_logo_min_width=BOX_FRONT_EXPANSION_LOGO_MIN_WIDTH,
        hero_height=BOX_HERO_HEIGHT,
        back_height=BOX_BACK_HEIGHT,
        back_offset_x=BOX_BACK_OFFSET_X,
    )


def build_side(exp: expansion.Expansion, size: tuple[int, int]) -> Image.Image:
    """The box side: the expansion's items' background (see
    :func:`nikke_reborn.expansion.load_item_background`) fitted to cover
    the side, with the expansion's logo center-center and the NIKKE logo
    bottom-center (omitted when the expansion's logo is the NIKKE
    logo itself), in memory (the material's green rectangle, never
    written to disk). Its inputs are a subset of the front's, so the
    front's source hash covers it."""
    background = load_item_background(exp)
    side = _fit_cover(background, size)
    place_center_expansion_logo(side, exp)
    if not expansion.is_nikke_logo(exp):
        place_side_logo(side)
    return side


def build_top(exp: expansion.Expansion, size: tuple[int, int]) -> Image.Image:
    """The box top: the expansion's items' background (see
    :func:`nikke_reborn.expansion.load_item_background`) fitted to cover
    the top (center-cropped), with the expansion's logo center-center
    and the NIKKE logo top-right (omitted when the expansion's logo is
    the NIKKE logo itself), in memory (the material's red rectangle,
    never written to disk); it also serves the bottom face, which
    shares the red rectangle. Its inputs are a subset of the front's,
    so the front's source hash covers it."""
    top = _fit_cover(load_item_background(exp), size, v_align="center")
    place_center_expansion_logo(
        top,
        exp,
        width_fraction=BOX_TOP_EXPANSION_LOGO_WIDTH,
    )
    if not expansion.is_nikke_logo(exp):
        place_top_logo(top)
    return top


def _process_box_material(
    exp: expansion.Expansion,
    front: Image.Image,
    front_source: str,
    side: Image.Image,
    top: Image.Image,
    force: bool = False,
    preset: Preset = Preset.DEFAULT,
) -> tuple[Path, bool]:
    """Composite the box's front, side and top onto the box material
    template's mask rectangles at the template's own size, and scale
    the finished material down to the run's size in one whole-image
    pass (nothing resampled twice). Written atomically to the output
    preset's set folder with the template and the front's inputs
    embedded (the side's and top's inputs are subsets of the front's),
    like a finished card; returns ``(out_path, skipped)``."""
    source_hash = _material_hash(BOX_TEMPLATE, front_source=front_source, preset=preset)
    out_path = preset.set_path(exp.name) / BOX_MATERIAL_NAME
    if not force and out_path.is_file() and _stored_hash(out_path) == source_hash:
        return out_path, True
    with Image.open(BOX_TEMPLATE) as opened:
        template = opened.convert("RGBA")
        rects = _pack_mask_rects(_pack_mask(template))
        if len(rects) != 1:
            raise GenerationError(
                f"box material template {BOX_TEMPLATE.name} carries "
                f"{len(rects)} pure-blue mask rectangle(s), expected 1 (front)"
            )
        side_rects = _pack_mask_rects(_box_side_mask(template))
        if len(side_rects) != 1:
            raise GenerationError(
                f"box material template {BOX_TEMPLATE.name} carries "
                f"{len(side_rects)} pure-green mask rectangle(s), expected 1 (side)"
            )
        # Detected on the untouched template, like the blue and green ones:
        # the composed content may itself carry pure-red pixels.
        top_rects = _pack_mask_rects(_box_top_mask(template))
        if len(top_rects) != 1:
            raise GenerationError(
                f"box material template {BOX_TEMPLATE.name} carries "
                f"{len(top_rects)} pure-red mask rectangle(s), expected 1 (top)"
            )
        front_target = (rects[0][2] - rects[0][0], rects[0][3] - rects[0][1])
        if front.size != front_target:
            front = front.resize(front_target, Image.Resampling.LANCZOS)
        _linear_over(template, front, (rects[0][0], rects[0][1]))
        side_rect = side_rects[0]
        side_target = (
            side_rect[2] - side_rect[0],
            side_rect[3] - side_rect[1],
        )
        if side.size != side_target:
            side = side.resize(side_target, Image.Resampling.LANCZOS)
        _linear_over(template, side, (side_rect[0], side_rect[1]))
        top_rect = top_rects[0]
        top_target = (top_rect[2] - top_rect[0], top_rect[3] - top_rect[1])
        if top.size != top_target:
            top = top.resize(top_target, Image.Resampling.LANCZOS)
        _linear_over(template, top, (top_rect[0], top_rect[1]))
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


def _process_box_item(
    exp: expansion.Expansion,
    force: bool = False,
    preset: Preset = Preset.DEFAULT,
) -> tuple[Path, bool]:
    """Render the box's item with :data:`UNITY_VIEWER`: the box's mesh
    textured with the finished material (which must exist first — the
    item is rendered from its output file), posed by the box's viewer
    configuration, at the run's output size. The plain PNG the viewer
    writes is re-saved with the mesh, material and output size embedded
    and moved into place atomically; returns ``(out_path, skipped)``."""
    width = round(ITEM_VIEWER_WIDTH * preset.scale)
    height = round(ITEM_VIEWER_HEIGHT * preset.scale)
    set_path = preset.set_path(exp.name)
    material_path = set_path / BOX_MATERIAL_NAME
    source_hash = _viewer_hash(BOX_MESH, material_path, BOX_CONFIG, preset)
    out_path = set_path / BOX_ITEM_NAME
    if not force and out_path.is_file() and _stored_hash(out_path) == source_hash:
        return out_path, True
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(out_path.name + ".render")
    try:
        result = subprocess.run(
            [
                UNITY_VIEWER,
                str(BOX_MESH),
                str(material_path),
                "--config",
                str(BOX_CONFIG),
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
