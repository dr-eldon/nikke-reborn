"""Compose a pack's ``CardPack_Front`` and ``CardPack_Back`` on the fly from
its ``Expansion.json``.

The front and back are built procedurally from the expansion's metadata —
neither is stored: :func:`nikke_reborn._generate_variants` composes them in memory and
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
import subprocess
from pathlib import Path

from PIL import Image

from nikke_reborn.config import (
    CARDS_DIR,
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
    compose_front,
    fit_background,
    front_source_digest,
    load_background,
    load_expansion,
)
from nikke_reborn.file import (
    _material_hash,
    _save_atomic,
    _stored_hash,
    _viewer_hash,
)
from nikke_reborn.image import _pack_mask, _pack_mask_rects
from nikke_reborn.preset import Preset

# --- the white NIKKE logo -----------------------------------------------------
#: The white logo stamped on the pack's front, at the same placement in the
#: material and the item: its width as a fraction of the front's width
#: (centered horizontally) and its top inset as a fraction of the front's
#: height.
PACK_LOGO = IMAGES_DIR / "Logo_White.png"
PACK_LOGO_WIDTH = 0.6
PACK_LOGO_TOP = 0.04


def front_size() -> tuple[int, int]:
    """The pack front's target size: the material template's *right* mask
    rectangle (the left one is the back). Composing at exactly this size means
    the material composition pastes it with no rescale."""
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
    """The pack back's target size: the material template's *left* mask
    rectangle (the right one is the front). Composing at exactly this size
    means the material composition pastes it with no rescale."""
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
    return front_source_digest(pack_dir, PACK_LOGO, PACK_TEMPLATE)


def back_source_hash(pack_dir: Path) -> str:
    """A hash of the back's *inputs* — everything the composed back depends on:
    its ``background`` and the material template that sizes it. It is computed
    without composing the back, so the finished material can be skipped (and
    the back's composition avoided) when those inputs are unchanged."""
    expansion = load_expansion(pack_dir)
    background = expansion.get("background")
    if not background:
        raise GenerationError(f"{pack_dir.name}: missing 'background'")
    digest = hashlib.sha256()
    digest.update((pack_dir / background).resolve().read_bytes())
    digest.update(PACK_TEMPLATE.read_bytes())
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
    return compose_front(pack_dir, expansion, size, fit="crop", place_logo=place_logo)


def build_back(pack_dir: Path, expansion: dict, size: tuple[int, int]) -> Image.Image:
    """Compose the pack back from the expansion's ``background``: resized to
    the back's height and left-cropped to its exact width (the front
    center-crops the same background). The result is returned in memory; it is
    the material's left rectangle and is never written to disk."""
    return fit_background(load_background(pack_dir, expansion), size, align="left")


def _process_pack_material(
    pack_dir: Path,
    front: Image.Image,
    front_source: str,
    back: Image.Image,
    back_source: str,
    force: bool = False,
    preset: Preset = Preset.DEFAULT,
) -> tuple[Path, bool]:
    """Composite a pack's images onto the material template.

    The template's pure-blue mask rectangles mark the paste regions: the
    left one holds the pack's back and the right one its front — both
    in-memory images composed on the fly (the front with its white logo,
    placed by :func:`pack.place_logo`) and never stored. The composition
    happens at native (the template's) size — into the exact mask
    rectangles — and only the finished material is scaled, in one
    whole-image pass, to the run's size and written to the output
    preset's set folder (the ``<pack> (Ultra)`` twin for the ultra
    preset), atomically, with the SHA-256 of the template, the output
    preset's scale and the back's and front's inputs embedded, like a
    finished card; returns ``(out_path, skipped)``, where *skipped* is
    True when the output already exists and its stored hash matches the
    current inputs.
    """
    pack_dir = pack_dir.resolve()
    source_hash = _material_hash(
        PACK_TEMPLATE,
        front_source=front_source,
        back_source=back_source,
        preset=preset,
    )
    out_path = preset.set_path(pack_dir.relative_to(CARDS_DIR).name) / PACK_MATERIAL_NAME
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
        # The back and front are the in-memory images (composed on the fly),
        # each already sized to its rectangle.
        back_target = (rects[0][2] - rects[0][0], rects[0][3] - rects[0][1])
        if back.size != back_target:
            back = back.resize(back_target, Image.Resampling.LANCZOS)
        template.alpha_composite(back, (rects[0][0], rects[0][1]))
        front_target = (rects[1][2] - rects[1][0], rects[1][3] - rects[1][1])
        if front.size != front_target:
            front = front.resize(front_target, Image.Resampling.LANCZOS)
        template.alpha_composite(front, (rects[1][0], rects[1][1]))
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


def _process_pack_item(
    pack_dir: Path,
    force: bool = False,
    preset: Preset = Preset.DEFAULT,
) -> tuple[Path, bool]:
    """Render a pack's item with :data:`UNITY_VIEWER`: the pack's mesh
    (:data:`PACK_MESH`) textured with the pack's finished material
    (``<out>/<pack>/CardPack_Material.png`` in the output preset's set
    folder — the ``<pack> (Ultra)`` twin for the ultra preset), posed by
    the viewer configuration (:data:`PACK_CONFIG`): the model rotation
    and camera zoom/pan from that JSON file, the camera's fixed viewing
    pose and an output size of ``round(ITEM_VIEWER_WIDTH *
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
    pack_dir = pack_dir.resolve()
    width = round(ITEM_VIEWER_WIDTH * preset.scale)
    height = round(ITEM_VIEWER_HEIGHT * preset.scale)
    set_path = preset.set_path(pack_dir.relative_to(CARDS_DIR).name)
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
