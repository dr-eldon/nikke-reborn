"""Linear-light (sRGB-decoded) compositing.

Pillow composites on the stored sRGB values, and a partially
transparent colour mix on that scale lands darker and hue-shifted
than the same mix of light (mid-alpha blends sag toward the dark
side, and the channels' ratios drift). The functions here decode
both operands to linear light (the IEC 61966-2-1 sRGB curve),
composite there, and re-encode. The 8-bit decode/encode round-trip
is exact, so where a layer's alpha is 0 or 255 the result is
byte-identical to Pillow's sRGB composite: the difference is
confined to the partially transparent pixels, which are exactly
the pixels Pillow gets wrong.

Linear values are carried on the 0..65535 scale: f32 holds every
integer of it exactly, and the tables index it directly. The
element-wise numpy work releases the GIL, so the per-frame
composers' thread pool still runs in parallel.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

#: The linear scale's maximum (see the module docstring).
_LIN_MAX = 65535.0


def _decode_table() -> np.ndarray:
    out = np.empty(256, dtype=np.float32)
    for v in range(256):
        x = v / 255
        linear = x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
        out[v] = linear * _LIN_MAX
    return out


def _encode_table() -> np.ndarray:
    out = np.empty(65536, dtype=np.uint8)
    for q in range(65536):
        x = q / _LIN_MAX
        encoded = x * 12.92 if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
        out[q] = round(encoded * 255)
    return out


#: sRGB value -> linear light on the 0..65535 scale.
DECODE = _decode_table()

#: Linear light on the 0..65535 scale -> sRGB value.
ENCODE = _encode_table()


def _alpha(image: Image.Image) -> np.ndarray:
    """The image's alpha channel as a 0..1 f32 array."""
    return np.asarray(image.getchannel("A"), dtype=np.float32) / 255.0


def _to_linear(image: Image.Image) -> np.ndarray:
    """The image's RGB, sRGB-decoded, as an (h, w, 3) f32 array on the
    0..65535 scale (see the module docstring)."""
    flat = np.frombuffer(image.convert("RGB").tobytes(), dtype=np.uint8)
    return DECODE[flat].reshape(image.size[1], image.size[0], 3)


def _from_linear(array: np.ndarray) -> Image.Image:
    """An (h, w, 3) f32 array on the 0..65535 scale back to an 8-bit
    sRGB RGB image (clipped)."""
    index = np.clip(array, 0.0, _LIN_MAX).astype(np.uint16)
    return Image.frombytes(
        "RGB", (array.shape[1], array.shape[0]), ENCODE[index].tobytes()
    )


def _clip_box(
    base_size: tuple[int, int], layer_size: tuple[int, int], pos: tuple[int, int]
) -> tuple[int, int, int, int] | None:
    """The overlap of a *layer* at *pos* on a canvas of *base_size*
    (both (width, height)), as (x, y, w, h) in canvas coordinates, or
    None when there is none."""
    x, y = pos
    left, top = max(0, x), max(0, y)
    right = min(base_size[0], x + layer_size[0])
    bottom = min(base_size[1], y + layer_size[1])
    if right <= left or bottom <= top:
        return None
    return (left, top, right - left, bottom - top)


def _linear_over(
    base: Image.Image, layer: Image.Image, pos: tuple[int, int] = (0, 0)
) -> None:
    """Composite *layer* over *base* in linear light (Porter-Duff
    'over', the layer's straight alpha as the coverage; the alpha
    channels composite the same way) at *pos*, clipped to *base*'s
    bounds; modifies *base* in place. Valid for any base alpha: the
    destination contributes premultiplied and the result is
    renormalised to straight colour, so a transparent base receives the
    layer's straight colour exactly as ``alpha_composite`` does.
    Where the base is opaque the blend is ``l*a + base*(1 - a)`` —
    byte-identical to ``base.alpha_composite(layer, pos)`` wherever the
    layer's alpha is 0 or 255 (see the module docstring)."""
    box = _clip_box(base.size, layer.size, pos)
    if box is None:
        return
    x, y, w, h = box
    src = (x - pos[0], y - pos[1], x - pos[0] + w, y - pos[1] + h)
    dst = base.crop((x, y, x + w, y + h))
    region = _to_linear(dst)
    dst_alpha = _alpha(dst)
    coverage = _alpha(layer.crop(src))
    out_alpha = coverage + dst_alpha * (1.0 - coverage)
    straight = _to_linear(layer.crop(src))
    # The general blend divides by the output alpha; the degenerate
    # pixels take their exact, un-divided values instead (a clear layer
    # leaves the base untouched, a transparent base receives the layer
    # straight) so no pixel ever pays a second rounding.
    denom = np.where(out_alpha > 0.0, out_alpha, 1.0)
    general = (
        straight * coverage[..., None]
        + region * dst_alpha[..., None] * (1.0 - coverage[..., None])
    ) / denom[..., None]
    out = np.where(
        coverage[..., None] == 0.0,
        region,
        np.where(dst_alpha[..., None] == 0.0, straight, general),
    )
    image = _from_linear(out)
    image.putalpha(_encode_alpha(out_alpha, dst.size))
    base.paste(image, (x, y))


def _linear_screen(
    base: Image.Image, layer: Image.Image, pos: tuple[int, int] = (0, 0)
) -> None:
    """Screen *layer*'s colour into *base* in linear light, the layer's
    straight alpha as the coverage (the logo glow's treatment), at
    *pos*, clipped to *base*'s bounds; modifies *base* in place."""
    box = _clip_box(base.size, layer.size, pos)
    if box is None:
        return
    x, y, w, h = box
    src = (x - pos[0], y - pos[1], x - pos[0] + w, y - pos[1] + h)
    region = _to_linear(base.crop((x, y, x + w, y + h)))
    coverage = _alpha(layer.crop(src))
    # Screen (1 - (1 - b)(1 - g)) on the 0..1 scale, back to 0..65535.
    screened = region + _to_linear(layer.crop(src)) * (1.0 - region / _LIN_MAX)
    out = screened * coverage[..., None] + region * (1.0 - coverage[..., None])
    base.paste(_from_linear(out), (x, y))


def _affine_init(size: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """The identity linear stack: out = A*x + B with A = 1, B = 0
    (A an (h, w, 1) f32, B an (h, w, 3) f32 on the 0..65535 scale)."""
    height, width = size[1], size[0]
    return np.ones((height, width, 1), dtype=np.float32), np.zeros(
        (height, width, 3), dtype=np.float32
    )


def _affine_over(
    affine: tuple[np.ndarray, np.ndarray],
    layer: Image.Image,
    pos: tuple[int, int] = (0, 0),
) -> tuple[np.ndarray, np.ndarray]:
    """Fold a static *layer* (in linear light) over the *affine*'s stack
    at *pos*, in place: composing 'over' composites keeps the result an
    affine in the base, so a run of static layers (the tint wash, the
    mask, the photo reel, the stamps) precomputes into one multiply-add
    the per-frame frames pay for it."""
    a_coeff, b_coeff = affine
    box = _clip_box((b_coeff.shape[1], b_coeff.shape[0]), layer.size, pos)
    if box is None:
        return affine
    x, y, w, h = box
    src = (x - pos[0], y - pos[1], x - pos[0] + w, y - pos[1] + h)
    # 'over': the layer carries its own coverage; the stack beneath
    # carries the rest (out = a*l + (1 - a)*(A*x + B)).
    coverage = _alpha(layer.crop(src))[..., None]
    colour = _to_linear(layer.crop(src))
    a_view = a_coeff[y : y + h, x : x + w]
    b_view = b_coeff[y : y + h, x : x + w]
    a_view *= 1.0 - coverage
    b_view[:] = coverage * colour + (1.0 - coverage) * b_view
    return affine


def _affine_apply(
    affine: tuple[np.ndarray, np.ndarray], base: np.ndarray
) -> np.ndarray:
    """The *affine*'s stack applied to *base* (an (h, w, ...) f32 array
    on the affine's scale): out = A*base + B."""
    return affine[0] * base + affine[1]


def _affine_alpha_init(size: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """The identity linear alpha stack: out = A*a + B with A = 1, B = 0
    (both (h, w) f32 on the 0..1 scale)."""
    height, width = size[1], size[0]
    return np.ones((height, width), dtype=np.float32), np.zeros(
        (height, width), dtype=np.float32
    )


def _affine_alpha_over(
    affine: tuple[np.ndarray, np.ndarray],
    layer: Image.Image,
    pos: tuple[int, int] = (0, 0),
) -> tuple[np.ndarray, np.ndarray]:
    """Fold a static *layer*'s alpha over the *affine*'s stack at *pos*,
    in place: the alpha channels composite with the same 'over' law as
    the colours (a_out = a_l + (1 - a_l)*a_below), so the fold applies
    unchanged."""
    a_coeff, b_coeff = affine
    box = _clip_box((a_coeff.shape[1], a_coeff.shape[0]), layer.size, pos)
    if box is None:
        return affine
    x, y, w, h = box
    coverage = _alpha(
        layer.crop((x - pos[0], y - pos[1], x - pos[0] + w, y - pos[1] + h))
    )
    a_view = a_coeff[y : y + h, x : x + w]
    b_view = b_coeff[y : y + h, x : x + w]
    a_view *= 1.0 - coverage
    b_view[:] = coverage + (1.0 - coverage) * b_view
    return affine


def _encode_alpha(alpha: np.ndarray, size: tuple[int, int]) -> Image.Image:
    """A 0..1 f32 alpha as an 8-bit L channel."""
    return Image.frombytes(
        "L",
        (size[0], size[1]),
        np.rint(np.clip(alpha, 0.0, 1.0) * 255).astype(np.uint8).tobytes(),
    )
