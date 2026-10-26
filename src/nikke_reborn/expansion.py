"""Shared composition of an expansion's front, from its ``Expansion.json``.

The pack's front and the box's front are the same composition — the
expansion's background, the featured NIKKES drawn over it (backs first, the
hero on top), and — when the expansion names a ``logo`` — the expansion's
logo (its ``logo.path`` image, relative to the pack directory) with its
glow on top, at its ``logo.placement`` — so the composition lives here,
shared by
:mod:`nikke_reborn.pack` and :mod:`nikke_reborn.box` (which add only their
own pieces: the material template's sizing, their white NIKKE logo placement
and their background fit). The two must therefore stay in sync with nothing
here: the shared code is written once.

* the ``pack`` field lists the NIKKES to feature (card-definition paths
  relative to the pack directory). The *first* one is the hero: it is
  centered in the front. The rest are placed behind it, to the left and
  right, at a lower scale, to read as a group in perspective/distance.
* Only ``nikke-viewer``'s output is used (the raw character render, not the
  finished card — no background fit, logo, name or copyright). When a
  featured NIKKE is animated, only its first frame is kept and the rest
  discarded.
* when the ``logo`` field is set, the expansion's logo (its ``path``,
  relative to the pack directory) is composited on top at its ``placement``
  with a glow:
  the halo is screen-blended for a light bloom, a solid trail in a
  darkened glow tint — the mark's own silhouette, offset slightly
  down-right — sits behind it, and the sharp mark is drawn over both. The
  glow's tint is derived from the front's background color (its hue and
  saturation, brightened), so the bloom matches the scene rather than a
  fixed white.
* the background's fit is the caller's to choose (:func:`compose_front`'s
  *fit*): the pack's front resizes the background to the front's height and
  center-crops it to the front's exact width; the box's front scales it down
  just enough to cover the whole front and bottom-aligns it, so its bottom
  touches the front's bottom edge and any excess is cropped off the top.

The front's inputs — its ``Expansion.json``, the featured NIKKE definitions
it lists, its background, its logo, the white NIKKE logo, and the material
template that sizes it — are hashed (see :func:`front_source_digest`) into
the finished material, so when those inputs are unchanged the front's render
is skipped entirely rather than re-rendered.
"""

from __future__ import annotations

import colorsys
import hashlib
import io
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

import nikke_reborn as nr
from PIL import Image, ImageChops, ImageFilter

EXPANSION_NAME = "Expansion.json"

# --- front composition tuning (fractions of the front) ----------------------
# Every NIKKE's feet sit on the front's bottom edge (feet baseline = 1.0), so
# no one floats above a strip of background or gets clipped by the card frame.
# The hero is the first featured NIKKE: centered, the largest, in front.
HERO_HEIGHT = 0.78  # hero body height as a fraction of the front height
HERO_FEET_Y = 1.0  # hero feet baseline (the bottom edge)
# The remaining NIKKES read as a group behind the hero: smaller (the depth cue)
# and pushed to the left and right, still with their feet on the bottom edge.
BACK_HEIGHT = 0.42  # back body height fraction (base, before per-tier shrink)
BACK_FEET_Y = 1.0  # back feet baseline (the bottom edge)
BACK_OFFSET_X = 0.34  # first flank's center offset from the middle (width frac)
BACK_TIER_GAP = 0.5  # each further tier on a side steps out by this fraction
BACK_TIER_SHRINK = 0.9  # each further tier shrinks by this factor
ALPHA_TRIM = 24  # alpha threshold (0-255) for the content bounding box

# --- expansion logo tuning --------------------------------------------------
# The expansion's logo (the ``logo.path`` of the expansion's ``logo`` field,
# relative to the pack directory) is composited over the front with a glow,
# at its ``placement``. Every value is relative to the front, so it is the
# same for every expansion: the mark is scaled to :data:`LOGO_WIDTH` the
# front's width, inset :data:`LOGO_MARGIN` from the edge (top/bottom
# placements), and haloed with a glow tinted by the front's own background
# color — its hue and saturation, brightened to :data:`LOGO_GLOW_VALUE` — so
# the bloom matches the scene (a night sky glows cool violet, a bright day
# scene glows warm) rather than a fixed white.
LOGO_WIDTH = 0.5  # logo width as a fraction of the front width (the pack's
# front; the box's front sizes by height — compose_front's
# expansion_logo_height)
LOGO_MARGIN = 0.05  # gap from the front's top/bottom edge (height fraction)
LOGO_GLOW_RADIUS = 0.012  # glow blur radius (fraction of the front height)
LOGO_GLOW_INTENSITY = 1.0  # glow strength (alpha multiplier of the halo)
LOGO_GLOW_VALUE = 0.9  # target brightness of the glow tint (0-1)
LOGO_TRAIL = 0.008  # the solid diagonal trail: the mark's own silhouette,
# filled solid (a darkened glow tint) and offset
# down-right by this fraction of the mark's height, drawn
# behind the mark — a tight drop-shadow that reads as a
# small trail
LOGO_TRAIL_DARKEN = 0.7  # how much the trail's tint is darkened relative to
# the glow's tint (1.0 would be the full glow tint)
LOGO_PLACEMENTS = ("top", "center", "bottom")  # values for the `logo.placement` field


def load_expansion(pack_dir: Path) -> dict:
    """The pack's ``Expansion.json`` (its ``pack`` characters, ``background``
    and ``logo``) — the metadata the front is composed from."""
    path = pack_dir / EXPANSION_NAME
    if not path.is_file():
        raise nr.GenerationError(f"no {EXPANSION_NAME} in {pack_dir}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise nr.GenerationError(f"cannot read {path}: {exc}") from exc


def front_source_digest(pack_dir: Path, logo: Path, template: Path) -> str:
    """A hash of an expansion front's *inputs* — everything the composed
    front depends on: the expansion's ``Expansion.json``, the featured NIKKE
    definitions it lists, its background and (when a logo is set) the
    expansion's logo, the white NIKKE logo placed on the front (*logo*), and
    the material
    template that sizes it (*template*). It is computed without rendering the
    front, so the finished material can be skipped (and the front's render
    avoided) when those inputs are unchanged. The pack's and the box's front
    source hashes are this digest with their own *logo* and *template* (see
    :func:`nikke_reborn.pack.front_source_hash` /
    :func:`nikke_reborn.box.front_source_hash`)."""
    expansion = load_expansion(pack_dir)
    digest = hashlib.sha256()
    digest.update((pack_dir / EXPANSION_NAME).read_bytes())
    for rel in expansion.get("pack", []):
        digest.update(nr._source_hash((pack_dir / rel).resolve()).encode())
    background = expansion.get("background")
    if background:
        digest.update((pack_dir / background).resolve().read_bytes())
    logo_field = expansion.get("logo")
    if isinstance(logo_field, dict) and logo_field.get("path"):
        logo_path = (pack_dir / logo_field["path"]).resolve()
        if logo_path.is_file():
            digest.update(logo_path.read_bytes())
    digest.update(logo.read_bytes())
    digest.update(template.read_bytes())
    return digest.hexdigest()


def load_background(pack_dir: Path, expansion: dict) -> Image.Image:
    """The expansion's ``background`` image (RGBA), resolved relative to the
    pack directory."""
    bg_rel = expansion.get("background")
    if not bg_rel:
        raise nr.GenerationError(f"{pack_dir.name}: missing 'background'")
    bg_path = (pack_dir / bg_rel).resolve()
    if not bg_path.is_file():
        raise nr.GenerationError(f"{pack_dir.name}: background not found: {bg_rel}")
    return Image.open(bg_path).convert("RGBA")


def load_logo(pack_dir: Path, expansion: dict) -> tuple[Image.Image, str]:
    """The expansion's ``logo``: its ``logo.path`` image (RGBA, resolved
    relative to the pack directory) and its ``logo.placement`` (one of
    :data:`LOGO_PLACEMENTS`)."""
    logo = expansion.get("logo")
    if not isinstance(logo, dict):
        raise nr.GenerationError(
            f"{pack_dir.name}: 'logo' must be an object with a 'path' and a 'placement'"
        )
    logo_rel = logo.get("path")
    if not logo_rel:
        raise nr.GenerationError(f"{pack_dir.name}: missing 'logo.path'")
    logo_path = (pack_dir / logo_rel).resolve()
    if not logo_path.is_file():
        raise nr.GenerationError(f"{pack_dir.name}: logo not found: {logo_rel}")
    placement = logo.get("placement")
    if placement not in LOGO_PLACEMENTS:
        raise nr.GenerationError(
            f"{pack_dir.name}: unknown logo placement {placement!r}; "
            f"expected one of {', '.join(LOGO_PLACEMENTS)}"
        )
    return Image.open(logo_path).convert("RGBA"), placement


def fit_background(
    background: Image.Image, size: tuple[int, int], align: str = "center"
) -> Image.Image:
    """Resize *background* to the target's height, then crop it to the
    target's exact width, *align*-justified: ``"center"`` for the front,
    ``"left"`` for the back (the back takes the background's left side)."""
    width, height = size
    scale = height / background.height
    if scale != 1.0:
        background = background.resize(
            (round(background.width * scale), height),
            Image.Resampling.LANCZOS,
        )
    if align == "left":
        left = 0
    elif align == "center":
        left = (background.width - width) // 2
    else:
        raise nr.GenerationError(f"unknown background alignment {align!r}")
    return background.crop((left, 0, left + width, height)).convert("RGBA")


def _fit_cover(
    background: Image.Image,
    size: tuple[int, int],
    h_align: str = "center",
    v_align: str = "bottom",
) -> Image.Image:
    """Fit *background* over the box's faces: scaled down just enough for
    it to cover the whole region (the larger of the two dimension ratios —
    the width for a portrait background), then cropped: horizontally per
    *h_align* (``"left"``, ``"center"`` or ``"right"``) and vertically per
    *v_align* (``"top"``, ``"center"`` or ``"bottom"``) — the front and the
    side are bottom-aligned and the top top-aligned, the excess cropped
    off the opposite side."""
    width, height = size
    scale = max(width / background.width, height / background.height)
    if scale != 1.0:
        background = background.resize(
            (round(background.width * scale), round(background.height * scale)),
            Image.Resampling.LANCZOS,
        )
    if h_align == "left":
        left = 0
    elif h_align == "center":
        left = (background.width - width) // 2
    elif h_align == "right":
        left = background.width - width
    else:
        raise nr.GenerationError(f"unknown horizontal alignment {h_align!r}")
    if v_align == "top":
        top = 0
    elif v_align == "center":
        top = (background.height - height) // 2
    elif v_align == "bottom":
        top = background.height - height
    else:
        raise nr.GenerationError(f"unknown vertical alignment {v_align!r}")
    return background.crop((left, top, left + width, top + height)).convert("RGBA")


def compose_front(
    pack_dir: Path,
    expansion: dict,
    size: tuple[int, int],
    *,
    fit: str,
    place_logo: Callable[[Image.Image, tuple[int, int, int, int]], None],
    expansion_logo_height: float | None = None,
    hero_height: float | None = None,
    back_height: float | None = None,
    back_offset_x: float | None = None,
) -> Image.Image:
    """Compose an expansion's front: its background (fitted per *fit*), the
    featured NIKKES drawn over it (backs first, the hero on top), and — when
    the expansion names a ``logo`` — the expansion's logo (its ``logo.path``
    image) with its glow on top, at its ``logo.placement``. The
    caller's white NIKKE logo is placed last (*place_logo*, on the front's
    own bounds). The result is returned in memory and never written to disk:
    the caller pastes it into its material's front rectangle.

    *fit* selects the background's fit: ``"crop"`` (the pack's front) resizes
    the background to the front's height and center-crops it to the front's
    width; ``"cover-bottom"`` (the box's front) scales it down just enough to
    cover the whole front and bottom-aligns it, so its bottom touches the
    front's bottom edge and any excess is cropped off the top.

    *expansion_logo_height*, when given (the box's front), sizes the
    expansion's logo by height — that fraction of the front's height, its
    width proportional — instead of by width (:data:`LOGO_WIDTH` the front's
    width, the pack's front).

    *hero_height*, when given (the box's front), sets the hero's body height
    to that fraction of the front's height instead of the shared
    :data:`HERO_HEIGHT` — the box's landscape front wants a bigger hero than
    the pack's portrait one. *back_height* does the same for the group
    behind the hero (instead of the shared :data:`BACK_HEIGHT` base), and
    *back_offset_x* sets the group's center offset from the middle (width
    fraction, instead of the shared :data:`BACK_OFFSET_X` — smaller brings
    the group closer to the hero)."""
    width, height = size

    background = load_background(pack_dir, expansion)
    if fit == "crop":
        canvas = fit_background(background, size)
    elif fit == "cover-bottom":
        canvas = _fit_cover(background, size)
    else:
        raise nr.GenerationError(f"unknown background fit {fit!r}")
    # Sample the background's color now — before the NIKKES are composited — so
    # the logo's glow is tinted by the scene, not by the characters on top of it.
    glow_color = _background_glow_color(_image_average(canvas))

    pack_rel = expansion.get("pack")
    if not pack_rel:
        raise nr.GenerationError(f"{pack_dir.name}: missing 'pack'")
    bodies = [
        _content_box(_render_first_frame((pack_dir / rel).resolve()))
        for rel in pack_rel
    ]

    # Backs first (behind the hero), left/right alternating, stepping further
    # out and shrinking per tier so any number of featured NIKKES lays out.
    back_scale = back_height if back_height is not None else BACK_HEIGHT
    offset_scale = back_offset_x if back_offset_x is not None else BACK_OFFSET_X
    for index, body in enumerate(bodies[1:], start=1):
        side = -1 if (index - 1) % 2 == 0 else 1  # left, right, left, ...
        tier = (index - 1) // 2  # 0 for the inner pair, 1 for the next, ...
        offset = offset_scale * width * (1.0 + BACK_TIER_GAP * tier)
        scale = BACK_TIER_SHRINK**tier
        _paste_body(
            canvas,
            body,
            center_x=width / 2 + side * offset,
            feet_y=BACK_FEET_Y * height,
            height=round(back_scale * height * scale),
        )
    # The hero on top: centered, the largest.
    hero_scale = hero_height if hero_height is not None else HERO_HEIGHT
    _paste_body(
        canvas,
        bodies[0],
        center_x=width / 2,
        feet_y=HERO_FEET_Y * height,
        height=round(hero_scale * height),
    )

    # The expansion's logo (only when the expansion names one): the mark's
    # image and its placement come from the expansion's ``logo`` field —
    # nothing here is specific to any one expansion.
    if expansion.get("logo") is not None:
        mark, placement = load_logo(pack_dir, expansion)
        _composite_logo(
            canvas,
            mark,
            size,
            placement,
            glow_color,
            mark_height=expansion_logo_height,
        )

    # The caller's white NIKKE logo on top: on the front's own bounds.
    place_logo(canvas, (0, 0, width, height))
    return canvas


def _render_first_frame(json_path: Path) -> Image.Image:
    """Render the card's first frame via ``nikke-viewer --stdout`` (raw RGBA).

    The viewer streams every frame as a contiguous ``viewport``-sized RGBA
    block; only the first is kept and the stream is abandoned (the viewer is
    killed), so an animated NIKKE costs no more than a static one.
    """
    card = nr._load_card(json_path)
    viewport = card.get("viewport")
    if not viewport:
        raise nr.GenerationError(
            f"{json_path.name}: missing 'viewport' (needed to size the raw "
            f"frames streamed by {nr.VIEWER} --stdout)"
        )
    width, height = int(viewport[0]), int(viewport[1])
    frame_bytes = width * height * 4

    viewer = subprocess.Popen(
        [nr.VIEWER, "--stdout", str(json_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert viewer.stdout is not None
    assert viewer.stderr is not None
    # A Popen pipe is a buffered reader (needed for read1).
    drain = nr._PipeDrain(cast("io.BufferedReader", viewer.stderr))
    try:
        data = nr._read_exact(viewer.stdout, frame_bytes)
        if len(data) != frame_bytes:
            raise nr.GenerationError(
                f"{nr.VIEWER} produced no frame for {json_path.name} "
                f"(got {len(data)} of {frame_bytes} bytes)"
            )
        frame = Image.frombytes("RGBA", (width, height), data)
    finally:
        # Abandon the stream early (we only want the first frame): the viewer
        # may be blocked writing the rest to a full pipe and is killed.
        nr._reap_viewer(viewer, drain, clean_exit_expected=False)
    return frame


def _content_box(image: Image.Image, threshold: int = ALPHA_TRIM) -> Image.Image:
    """Trim *image* to its opaque content bounding box (alpha > threshold)."""
    alpha = image.getchannel("A").point(lambda v: 255 if v > threshold else 0)
    box = alpha.getbbox()
    if box is None:
        raise nr.GenerationError("rendered frame is fully transparent")
    return image.crop(box)


def _paste_body(
    canvas: Image.Image,
    body: Image.Image,
    center_x: float,
    feet_y: float,
    height: int,
) -> None:
    """Scale *body* so its height is *height* px and composite it onto
    *canvas* with its horizontal center at *center_x* and its bottom (feet) at
    *feet_y*. Parts that run off the canvas edge are clipped."""
    scale = height / body.height
    new_width = max(1, round(body.width * scale))
    body = body.resize((new_width, height), Image.Resampling.LANCZOS)
    left = round(center_x - new_width / 2)
    top = round(feet_y - height)
    canvas.alpha_composite(body, (left, top))


def _image_average(image: Image.Image) -> tuple[int, int, int]:
    """The area-averaged RGB of *image* (a single box-filtered pixel) — the
    image's representative color, cheap to compute at any size."""
    pixel = image.convert("RGB").resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
    assert isinstance(pixel, tuple)
    return (pixel[0], pixel[1], pixel[2])


def _background_glow_color(
    background: tuple[int, int, int], value: float = LOGO_GLOW_VALUE
) -> tuple[int, int, int]:
    """The glow tint from the front's *background* color: its hue and
    saturation, brightened to *value*. Keeping the background's hue lets the
    bloom match the scene's ambient color instead of a fixed white; a fixed
    target brightness keeps it visible no matter how dark the background is.
    A near-gray background yields a near-neutral glow."""
    hue, sat, _ = colorsys.rgb_to_hsv(*(c / 255 for c in background))
    r, g, b = colorsys.hsv_to_rgb(hue, sat, value)
    return round(r * 255), round(g * 255), round(b * 255)


def _logo_glow_layer(
    logo: Image.Image, radius: int, color: tuple[int, int, int], intensity: float
) -> tuple[Image.Image, int]:
    """A soft halo around *logo*: its alpha blurred by *radius* px, tinted
    *color*, scaled by *intensity*, on a transparent canvas padded by the
    blur's full visible extent (three sigma) on every side, so the Gaussian
    decays to zero inside the canvas and the halo is not clipped at the
    mark's edges. Returns the RGBA halo and the pad, so the caller can
    re-align it with the sharp mark."""
    pad = max(1, 3 * radius)
    halo = Image.new("L", (logo.width + 2 * pad, logo.height + 2 * pad), 0)
    halo.paste(logo.getchannel("A"), (pad, pad))
    halo = halo.filter(ImageFilter.GaussianBlur(radius))
    halo = halo.point(lambda v: min(255, round(v * intensity)))
    layer = Image.new("RGBA", halo.size, color + (0,))
    layer.putalpha(halo)
    return layer, pad


def _screen_composite(
    base: Image.Image, overlay: Image.Image, pos: tuple[int, int]
) -> None:
    """Screen-blend *overlay*'s color onto *base* at *pos*, masked by the
    overlay's alpha: the mark's bloom brightens the front without painting over
    it (unlike an opaque alpha paste). Clipped to *base*'s bounds; *base* is
    modified in place."""
    base_w, base_h = base.size
    over_w, over_h = overlay.size
    x, y = pos
    sx, sy = max(0, -x), max(0, -y)
    ex, ey = min(over_w, base_w - x), min(over_h, base_h - y)
    if ex <= sx or ey <= sy:
        return
    box = (x + sx, y + sy, x + ex, y + ey)
    region = base.crop(box)
    halo = overlay.crop((sx, sy, ex, ey))
    mask = halo.getchannel("A")
    blended = ImageChops.screen(region.convert("RGB"), halo.convert("RGB"))
    base.paste(Image.composite(blended, region.convert("RGB"), mask), box)


def _composite_logo(
    canvas: Image.Image,
    logo: Image.Image,
    size: tuple[int, int],
    placement: str,
    glow_color: tuple[int, int, int],
    mark_height: float | None = None,
    width_fraction: float | None = None,
) -> None:
    """Composite the expansion's *logo* over *canvas* at *placement* with a
    glow: the halo (tinted *glow_color*) is screen-blended for a light bloom,
    and a solid trail — the mark's own silhouette filled with a darkened
    glow tint (:data:`LOGO_TRAIL_DARKEN` of *glow_color*), offset down-right
    by :data:`LOGO_TRAIL` the mark's height — is drawn behind the sharp mark
    (a tight drop-shadow that reads as a small diagonal trail), which is
    then drawn on top. The mark is scaled to
    :data:`LOGO_WIDTH` the front's width (or, when *mark_height* is given —
    the box's front and side — to that fraction of the face's height, its
    width proportional; or, when *width_fraction* is given — the box's
    top — to that fraction of the face's width, its height proportional)
    and centered horizontally; top/bottom placements inset it
    :data:`LOGO_MARGIN` from the edge, ``center`` centers it in the front.
    Modifies *canvas* in place."""
    width, height = size
    if mark_height is None:
        logo_w = round(
            (LOGO_WIDTH if width_fraction is None else width_fraction) * width
        )
        if logo_w < 1:
            return
        logo = logo.resize(
            (logo_w, round(logo_w * logo.height / logo.width)),
            Image.Resampling.LANCZOS,
        )
    else:
        logo_h = round(mark_height * height)
        if logo_h < 1:
            return
        logo = logo.resize(
            (round(logo_h * logo.width / logo.height), logo_h),
            Image.Resampling.LANCZOS,
        )
    cx = width // 2
    if placement == "top":
        cy = round(LOGO_MARGIN * height) + logo.height // 2
    elif placement == "bottom":
        cy = round(height - LOGO_MARGIN * height) - logo.height // 2
    elif placement == "center":
        cy = height // 2
    else:
        raise nr.GenerationError(
            f"unknown logo placement {placement!r}; "
            f"expected one of {', '.join(LOGO_PLACEMENTS)}"
        )
    x = cx - logo.width // 2
    y = cy - logo.height // 2
    halo, pad = _logo_glow_layer(
        logo, round(LOGO_GLOW_RADIUS * height), glow_color, LOGO_GLOW_INTENSITY
    )
    _screen_composite(canvas, halo, (x - pad, y - pad))
    # The solid trail, behind the mark: the mark's own silhouette in a
    # darkened glow tint (solid, no bloom), offset down-right (the trail
    # runs top-left to bottom-right), so a sliver of it shows along the
    # mark's bottom-right edge; the rest is painted over by the mark.
    trail_offset = round(LOGO_TRAIL * logo.height)
    if trail_offset > 0:
        trail_tint = tuple(int(c * LOGO_TRAIL_DARKEN) for c in glow_color)
        trail = Image.new("RGBA", logo.size, trail_tint + (255,))
        trail.putalpha(logo.getchannel("A"))
        canvas.alpha_composite(trail, (x + trail_offset, y + trail_offset))
    canvas.alpha_composite(logo, (x, y))
