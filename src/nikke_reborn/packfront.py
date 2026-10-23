"""Compose a pack's ``CardPack_Front`` on the fly from its ``Expansion.json``.

The front is built procedurally from the expansion's metadata — it is never
stored: :func:`generate` composes it in memory and hands it to the material and
item composition. Everything is driven by the expansion (its ``pack``
characters, ``background`` and ``logo``), so the same code composes any
expansion's front without per-pack changes.

* the ``pack`` field lists the NIKKES to feature (card-definition paths
  relative to the pack directory). The *first* one is the hero: it is centered
  in the front. The rest are placed behind it, to the left and right, at a
  lower scale, to read as a group in perspective/distance.
* Only ``nikke-viewer``'s output is used (the raw character render, not the
  finished card — no background fit, logo, name or copyright). When a featured
  NIKKE is animated, only its first frame is kept and the rest discarded.
* the ``background`` field is resized to the front's height and then
  center-cropped to the front's exact width.
* when the ``logo`` field names a placement, the expansion's logo
  (``<pack>/Logo.png``) is composited on top at that placement with a glow:
  the halo is screen-blended for a light bloom and the sharp mark is drawn
  over it. The glow's tint is derived from the front's background color (its
  hue and saturation, brightened), so the bloom matches the scene rather than
  a fixed white.

Rendered first-frames are cached on disk (keyed by the card definition's hash)
so repeated runs do not pay the GPU render again.
"""

from __future__ import annotations

import colorsys
import json
import subprocess
from pathlib import Path

import nikke_reborn as nr
from PIL import Image, ImageChops, ImageFilter

EXPANSION_NAME = "Expansion.json"
CACHE_DIR = nr.REPO_ROOT / ".pack_cache"

# --- front composition tuning (fractions of the front) ----------------------
# Every NIKKE's feet sit on the front's bottom edge (feet baseline = 1.0), so
# no one floats above a strip of background or gets clipped by the card frame.
# The hero is the first featured NIKKE: centered, the largest, in front.
HERO_HEIGHT = 0.78   # hero body height as a fraction of the front height
HERO_FEET_Y = 1.0    # hero feet baseline (the bottom edge)
# The remaining NIKKES read as a group behind the hero: smaller (the depth cue)
# and pushed to the left and right, still with their feet on the bottom edge.
BACK_HEIGHT = 0.42   # back body height fraction (base, before per-tier shrink)
BACK_FEET_Y = 1.0    # back feet baseline (the bottom edge)
BACK_OFFSET_X = 0.34 # first flank's center offset from the middle (width frac)
BACK_TIER_GAP = 0.5  # each further tier on a side steps out by this fraction
BACK_TIER_SHRINK = 0.9  # each further tier shrinks by this factor
ALPHA_TRIM = 24  # alpha threshold (0-255) for the content bounding box

# --- expansion logo tuning --------------------------------------------------
# The expansion's logo (``<pack>/Logo.png``) is composited over the front with
# a glow, at the placement named by the expansion's ``logo`` field. Every value
# is relative to the front, so it is the same for every expansion: the mark is
# scaled to :data:`LOGO_WIDTH` the front's width, inset :data:`LOGO_MARGIN`
# from the edge (top/bottom placements), and haloed with a glow tinted by the
# front's own background color — its hue and saturation, brightened to
# :data:`LOGO_GLOW_VALUE` — so the bloom matches the scene (a night sky glows
# cool violet, a bright day scene glows warm) rather than a fixed white.
LOGO_NAME = "Logo.png"  # the expansion's logo, relative to the pack directory
LOGO_WIDTH = 0.5   # logo width as a fraction of the front width
LOGO_MARGIN = 0.05  # gap from the front's top/bottom edge (height fraction)
LOGO_GLOW_RADIUS = 0.012  # glow blur radius (fraction of the front height)
LOGO_GLOW_INTENSITY = 1.0  # glow strength (alpha multiplier of the halo)
LOGO_GLOW_VALUE = 0.9  # target brightness of the glow tint (0-1)
LOGO_PLACEMENTS = ("top", "center", "bottom")  # values for the `logo` field


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


def _render_first_frame(json_path: Path) -> Image.Image:
    """Render the card's first frame via ``nikke-viewer --stdout`` (raw RGBA).

    The viewer streams every frame as a contiguous ``viewport``-sized RGBA
    block; only the first is kept and the stream is abandoned (the viewer is
    killed), so an animated NIKKE costs no more than a static one. Cached on
    disk by the definition's hash so unchanged NIKKES are not re-rendered.
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

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{nr._source_hash(json_path)}.png"
    if cache_path.is_file():
        with Image.open(cache_path) as cached:
            return cached.convert("RGBA")

    viewer = subprocess.Popen(
        [nr.VIEWER, "--stdout", str(json_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    drain = nr._PipeDrain(viewer.stderr)
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
    frame.save(cache_path)
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


def _fit_background(background: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Resize *background* to the front's height, then center-crop it to the
    front's exact width (the spec's treatment, distinct from the card's cover
    fit)."""
    width, height = size
    scale = height / background.height
    if scale != 1.0:
        background = background.resize(
            (round(background.width * scale), height),
            Image.Resampling.LANCZOS,
        )
    left = (background.width - width) // 2
    return background.crop((left, 0, left + width, height)).convert("RGBA")


def _image_average(image: Image.Image) -> tuple[int, int, int]:
    """The area-averaged RGB of *image* (a single box-filtered pixel) — the
    image's representative color, cheap to compute at any size."""
    return image.convert("RGB").resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))


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
    *color*, scaled by *intensity*, on a transparent canvas padded by *radius*
    on every side so the blur is not clipped at the mark's edges. Returns the
    RGBA halo and the pad, so the caller can re-align it with the sharp mark."""
    pad = max(1, radius)
    halo = Image.new("L", (logo.width + 2 * pad, logo.height + 2 * pad), 0)
    halo.paste(logo.getchannel("A"), (pad, pad))
    halo = halo.filter(ImageFilter.GaussianBlur(radius))
    halo = halo.point(lambda v: min(255, round(v * intensity)))
    layer = Image.new("RGBA", halo.size, color + (0,))
    layer.putalpha(halo)
    return layer, pad


def _screen_composite(base: Image.Image, overlay: Image.Image, pos: tuple[int, int]) -> None:
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
) -> None:
    """Composite the expansion's *logo* over *canvas* at *placement* with a
    glow: the halo (tinted *glow_color*) is screen-blended for a light bloom
    and the sharp mark is drawn on top. The mark is scaled to :data:`LOGO_WIDTH`
    the front's width and centered horizontally; top/bottom placements inset it
    :data:`LOGO_MARGIN` from the edge, ``center`` centers it in the front.
    Modifies *canvas* in place."""
    width, height = size
    logo_width = round(LOGO_WIDTH * width)
    if logo_width < 1:
        return
    logo = logo.resize(
        (logo_width, round(logo_width * logo.height / logo.width)),
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
    canvas.alpha_composite(logo, (x, y))


def build_front(
    pack_dir: Path, expansion: dict, size: tuple[int, int]
) -> Image.Image:
    """Compose the pack front entirely from the expansion's metadata: its
    background, the featured NIKKES drawn over it (backs first, the hero on
    top), and — when the expansion names a ``logo`` placement — the expansion's
    logo (``<pack>/Logo.png``) with its glow on top, at the named placement.
    The result is returned in memory; it is the material's right rectangle and
    is never written to disk."""
    width, height = size

    bg_rel = expansion.get("background")
    if not bg_rel:
        raise nr.GenerationError(f"{pack_dir.name}: missing 'background'")
    bg_path = (pack_dir / bg_rel).resolve()
    if not bg_path.is_file():
        raise nr.GenerationError(f"{pack_dir.name}: background not found: {bg_rel}")
    canvas = _fit_background(Image.open(bg_path).convert("RGBA"), size)
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
    for index, body in enumerate(bodies[1:], start=1):
        side = -1 if (index - 1) % 2 == 0 else 1  # left, right, left, ...
        tier = (index - 1) // 2  # 0 for the inner pair, 1 for the next, ...
        offset = BACK_OFFSET_X * width * (1.0 + BACK_TIER_GAP * tier)
        scale = BACK_TIER_SHRINK**tier
        _paste_body(
            canvas,
            body,
            center_x=width / 2 + side * offset,
            feet_y=BACK_FEET_Y * height,
            height=round(BACK_HEIGHT * height * scale),
        )
    # The hero on top: centered, the largest.
    _paste_body(
        canvas,
        bodies[0],
        center_x=width / 2,
        feet_y=HERO_FEET_Y * height,
        height=round(HERO_HEIGHT * height),
    )

    # The expansion's logo (only when the expansion names a placement): the
    # mark's image comes from the pack directory, its placement from the
    # expansion — nothing here is specific to any one expansion.
    placement = expansion.get("logo")
    if placement is not None:
        logo_path = pack_dir / LOGO_NAME
        if not logo_path.is_file():
            raise nr.GenerationError(
                f"{pack_dir.name}: logo placement {placement!r} is set but "
                f"{LOGO_NAME!r} is missing"
            )
        _composite_logo(
            canvas,
            Image.open(logo_path).convert("RGBA"),
            size,
            placement,
            glow_color,
        )

    return canvas
