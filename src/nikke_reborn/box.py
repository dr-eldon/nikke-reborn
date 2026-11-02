"""Compose a box's ``CardBox_Material`` front on the fly from its
expansion's TOML.

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
:func:`nikke_reborn._generate_variants` composes it in memory and hands it to the
material composition, and its inputs are hashed (see
:func:`front_source_hash`) into the finished material so the render is
skipped when nothing changed.

The green (side) rectangle is filled with the expansion's background
(fitted to cover the side, taking the scene's center), the
expansion's logo center-center and the white NIKKE logo bottom-center;
the red (top) rectangle — shared with the bottom face — is filled with
the expansion's background (fitted to cover the top, center-cropped), the
expansion's logo center-center and the white NIKKE logo top-right.
"""

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
    compose_front,
    front_source_digest,
    load_background,
    load_logo,
)
from nikke_reborn.file import (
    _material_hash,
    _save_atomic,
    _stored_hash,
    _viewer_hash,
)
from nikke_reborn.image import (
    _box_side_mask,
    _box_top_mask,
    _pack_mask,
    _pack_mask_rects,
)
from nikke_reborn.preset import Preset

# --- the white NIKKE logo -----------------------------------------------------
#: The white logo stamped on the box's front (top-left), side
#: (bottom-center) and top (top-right): its height as a fraction of the
#: face's height, its corner inset by that margin (a fraction of the
#: face's height). Sized by height — the box's front is landscape, where
#: the pack's width-based sizing is far too big.
BOX_LOGO = IMAGES_DIR / "Logo_White.png"
BOX_LOGO_HEIGHT = 0.15
BOX_LOGO_MARGIN = 0.05

# --- the expansion's logo -----------------------------------------------------
#: The expansion's logo (the ``logo.path`` of the expansion's ``logo``
#: field) on the box's front and side:
#: its height as a fraction of the face's height (its width proportional)
#: — sized by height, where the pack's width-based sizing is far too big on
#: the landscape front.
BOX_EXPANSION_LOGO_HEIGHT = 1 / 3

#: The expansion's logo on the box's top: its width as a fraction of the
#: top's width (its height proportional).
BOX_TOP_EXPANSION_LOGO_WIDTH = 2 / 5

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
    """The box side's target size: the box material template's green mask
    rectangle (the pure-green placeholder, detected the way the front is
    detected in blue). Composing at exactly this size means the material
    composition pastes it with no rescale."""
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
    rectangle (the pure-red placeholder, detected the way the front is
    detected in blue and the side in green). It marks the top's paste
    region, which the bottom face shares. Composing at exactly this size
    means the material composition pastes it with no rescale."""
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


def place_logo(front: Image.Image, rect: tuple[int, int, int, int]) -> None:
    """Composite the white logo onto the front at *rect* (``(left, top,
    right, bottom)``, with right and bottom exclusive — the front's own
    bounds when placed on the front itself): its height is
    :data:`BOX_LOGO_HEIGHT` the front's height, placed at the front's
    top-left with its corner inset :data:`BOX_LOGO_MARGIN` the front's
    height — unslanted, since the material is the flat view. Sized by
    height, where the pack's width-based sizing is far too big on the
    landscape front. Modifies *front* in place."""
    left, top, _, bottom = rect
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


def place_top_logo(top: Image.Image) -> None:
    """Composite the white logo onto the top, top-right: its height is
    :data:`BOX_LOGO_HEIGHT` the top's height, placed at the top's
    top-right with its corner inset :data:`BOX_LOGO_MARGIN` the top's
    height — unslanted, since the material is the flat view. Modifies
    *top* in place."""
    with Image.open(BOX_LOGO) as opened:
        logo = opened.convert("RGBA")
    logo_h = round(BOX_LOGO_HEIGHT * top.height)
    logo = logo.resize(
        (round(logo_h * logo.width / logo.height), logo_h),
        Image.Resampling.LANCZOS,
    )
    margin = round(BOX_LOGO_MARGIN * top.height)
    top.alpha_composite(logo, (top.width - margin - logo.width, margin))


def place_center_expansion_logo(
    face: Image.Image,
    exp: expansion.Expansion,
    width_fraction: float | None = None,
) -> None:
    """Composite the expansion's logo (its ``logo.path`` image) onto a face
    (the side or the top), center-center — the same glow treatment as the
    front's (see :func:`nikke_reborn.expansion._composite_logo`): its
    height is :data:`BOX_EXPANSION_LOGO_HEIGHT` the face's height (the
    side), or, when *width_fraction* is given (the top), its width is that
    fraction of the face's width (its height proportional) — centered on
    the face both horizontally and vertically. The placement is always
    ``"center"``. The glow is sampled from the face before the logos are
    composited, so it is tinted by the scene. Modifies *face* in place."""
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
    """A hash of the box front's inputs: the expansion's file, the featured
    characters it lists, the background and the expansion's logo, the white
    NIKKE logo placed on the front, and the box material template that sizes
    it (the shared digest from
    :func:`nikke_reborn.expansion.front_source_digest`, with the box's logo
    and template). It is computed without rendering the front, so the
    finished material can be skipped (and the front's render avoided) when
    those inputs are unchanged."""
    return front_source_digest(exp, BOX_LOGO, BOX_TEMPLATE)


def build_front(exp: expansion.Expansion, size: tuple[int, int]) -> Image.Image:
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
        exp,
        size,
        fit="cover-bottom",
        place_logo=place_logo,
        expansion_logo_height=BOX_EXPANSION_LOGO_HEIGHT,
        hero_height=BOX_HERO_HEIGHT,
        back_height=BOX_BACK_HEIGHT,
        back_offset_x=BOX_BACK_OFFSET_X,
    )


def build_side(exp: expansion.Expansion, size: tuple[int, int]) -> Image.Image:
    """The box side: the expansion's background fitted to cover the side
    (like the front — scaled to cover, bottom-aligned, center-cropped),
    with the expansion's logo center-center (see
    :func:`place_center_expansion_logo`) and the white NIKKE logo
    bottom-center (see :func:`place_side_logo`). The result is returned in
    memory, like the front: it is the box material's green rectangle and is
    never written to disk. The side's inputs (the background, the
    expansion's logo when a logo is set, the white logo and the
    template) are a subset of the front's, so the front's source hash (see
    :func:`front_source_hash`) covers it."""
    background = load_background(exp)
    side = _fit_cover(background, size)
    place_center_expansion_logo(side, exp)
    place_side_logo(side)
    return side


def build_top(exp: expansion.Expansion, size: tuple[int, int]) -> Image.Image:
    """The box top: the expansion's background fitted to cover the top —
    like the front's and side's cover fit, but centered vertically as well
    as horizontally (see :func:`nikke_reborn.expansion._fit_cover`) — with
    the expansion's logo center-center (see
    :func:`place_center_expansion_logo`, sized by the top's width:
    :data:`BOX_TOP_EXPANSION_LOGO_WIDTH`) and the white NIKKE logo
    top-right (see :func:`place_top_logo`). It also serves the bottom
    face, which shares the red rectangle. The result is returned in
    memory, like the front: it is the box material's red rectangle and is
    never written to disk. The top's inputs (the background, the
    expansion's logo when a logo is set, the white logo and the
    template) are a subset of the front's, so the front's source hash (see
    :func:`front_source_hash`) covers it."""
    top = _fit_cover(load_background(exp), size, v_align="center")
    place_center_expansion_logo(
        top,
        exp,
        width_fraction=BOX_TOP_EXPANSION_LOGO_WIDTH,
    )
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
    template.

    The template's blue mask rectangle marks the front's paste region and
    its green mask rectangle the side's — the front is composed on the
    fly, with its white logo placed by :func:`box.place_logo`, and the
    side is the background's center slice with the expansion's logo
    center-center and the white logo bottom-center; the top (shared with
    the bottom) is the background center-cropped with the expansion's
    logo center-center and the white logo top-right. The composition
    happens at native (the template's) size — into the exact mask
    rectangles — and only the finished material is scaled, in one
    whole-image pass, to the run's size and written to
    ``<out>/<pack>/CardBox_Material.png`` (the output preset's set
    folder — the ``<pack> (Ultra)`` twin for the ultra preset),
    atomically, with the SHA-256 of the template, the output preset's
    scale and the front's inputs embedded, like a finished card (the
    side's and top's inputs are subsets of the front's); returns
    ``(out_path, skipped)``, where *skipped* is True when the output
    already exists and its stored hash matches the current inputs.
    """
    source_hash = _material_hash(
        BOX_TEMPLATE, front_source=front_source, preset=preset
    )
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
        # The front and side are the in-memory images (composed on the
        # fly), each already sized to its rectangle.
        front_target = (rects[0][2] - rects[0][0], rects[0][3] - rects[0][1])
        if front.size != front_target:
            front = front.resize(front_target, Image.Resampling.LANCZOS)
        template.alpha_composite(front, (rects[0][0], rects[0][1]))
        side_rect = side_rects[0]
        side_target = (
            side_rect[2] - side_rect[0],
            side_rect[3] - side_rect[1],
        )
        if side.size != side_target:
            side = side.resize(side_target, Image.Resampling.LANCZOS)
        template.alpha_composite(side, (side_rect[0], side_rect[1]))
        top_rect = top_rects[0]
        top_target = (top_rect[2] - top_rect[0], top_rect[3] - top_rect[1])
        if top.size != top_target:
            top = top.resize(top_target, Image.Resampling.LANCZOS)
        template.alpha_composite(top, (top_rect[0], top_rect[1]))
        final = template.convert("RGB")
    if preset.scale != 1.0:
        # One whole-image pass down to the run's size: the composition
        # stayed native (into the exact mask rectangles), so nothing is
        # resampled twice and the paste edges carry no bleed.
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
    (:data:`BOX_MESH`) textured with the box's finished material
    (``<out>/<pack>/CardBox_Material.png`` in the output preset's set
    folder — the ``<pack> (Ultra)`` twin for the ultra preset), posed by
    the box's viewer configuration (:data:`BOX_CONFIG`): the model
    rotation and camera zoom/pan from that JSON file, the camera's fixed
    viewing pose and an output size of ``round(ITEM_VIEWER_WIDTH *
    preset.scale)`` by ``round(ITEM_VIEWER_HEIGHT * preset.scale)``
    pixels (the viewer's own defaults at the full scale). The material
    must have been generated first — the item is rendered from its
    output file.

    The viewer writes a plain PNG, which is re-saved with the SHA-256 of
    the mesh, the material and the output size embedded (a PNG text
    chunk, like a finished card) and moved into place atomically, so a
    finished item only ever exists in its complete form; returns
    ``(out_path, skipped)``, where *skipped* is True when the output
    already exists and its stored hash matches the current inputs.
    """
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
