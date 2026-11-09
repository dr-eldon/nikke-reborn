#!/usr/bin/env python3
"""How far is pikke's resize from the same-kernel arithmetic, on the fly.

One engine run per case (resize_check.lua loads, resizes, yields),
diffed against the reference arithmetic on the same assets — decoded
sRGB, max per-pixel per-channel delta, premultiplied (the RGB
channels weighted by their alpha: the engine's buffer form reads a
fully transparent pixel's color as zero, and that is the comparison
the pixels actually carry). No recorded vectors.

The cases diff against an independent implementation of the same
window arithmetic, run in the buffer's form (premultiplied linear)
— the cubic against GIMP's resize as-is (GEGL's cubic sampler: the
BC-spline b = 1/2, c = 1/4, the downsample's sub-block average of
its fixed 4-tap, the abyss at the edge), the lanczos against the
reference's (Pillow's) window arithmetic — measuring the engine's
arithmetic (the kernel, the window, the premultiplied handling), not
a filter choice; the reference pipeline's own resampler is Pillow's,
and the resize's drift from it is a free op tracked by the fidelity
budget, not here. The cases are one per target semantic — the
background's cover (its aspect is the canvas', so it degrades to a
plain resample: the downscale, the filter's work), the logo's cover
(a different aspect: the center crop), and the logo's aspect-preserved
width target — over both kernels: the default cubic, the lanczos on
the aspect case. The x1.25 cases' 2048×2560 outputs are too heavy
for a debug-build run.
"""

import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BIN = ROOT / "pikke/target/debug/pikke"
SCRIPT = ROOT / "pikke/tests/resize_check.lua"

CANVAS = (1640, 2048)  # the logical canvas the reference image sets
LOGO_TARGET_WIDTH = 200  # the logo's nominal logical width


def rel(path: Path) -> str:
    """Script-relative (the probe lives two levels below the root)."""
    return "../../" + path.relative_to(ROOT).as_posix()


# --- the reference resample arithmetic (the buffer's form) --------


def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1.0 / 2.4) - 0.055)


def encode_u8(x: np.ndarray) -> np.ndarray:
    """The single encode rounding, ties away from zero (0-1 in)."""
    return np.clip(np.floor(np.clip(x, 0.0, 1.0) * 255.0 + 0.5), 0, 255).astype(
        np.uint8
    )


def gegl_cubic_kernel(x: np.ndarray) -> np.ndarray:
    """GIMP's resize kernel (GEGL's cubic sampler: the BC-spline
    b = 1/2, c = 1/4), the |x| form (zero outside ±2)."""
    x = np.abs(x)
    inner = (12.0 * x**3 - 21.0 * x**2 + 10.0) / 12.0
    outer = (-4.0 * x**3 + 21.0 * x**2 - 36.0 * x + 20.0) / 12.0
    return np.where(x < 1.0, inner, np.where(x < 2.0, outer, 0.0))


def lanczos3_kernel(x: np.ndarray) -> np.ndarray:
    """The Lanczos-3: the 3-lobed sinc, zero at the window's edge."""
    x = np.abs(x)
    return np.where(x < 3.0, np.sinc(x) * np.sinc(x / 3.0), 0.0)


def pass_signals(src: np.ndarray, dst_len: int, kernel, support: float) -> np.ndarray:
    """One separable pass along the last axis of `src` (P, N): the
    reference's window arithmetic (out-of-range taps absent, the
    weights renormalized per output sample)."""
    src_len = src.shape[1]
    scale = src_len / dst_len
    filterscale = max(scale, 1.0)
    support = support * filterscale

    centers = (np.arange(dst_len) + 0.5) * scale
    start = np.clip(np.trunc(centers - support + 0.5), 0, src_len).astype(int)
    end = np.clip(np.trunc(centers + support + 0.5), 0, src_len).astype(int)

    acc = np.zeros((src.shape[0], dst_len), dtype=np.float64)
    weights = np.zeros(dst_len, dtype=np.float64)
    for k in range(int(2 * support) + 1):
        idx = start + k
        valid = idx < end
        idx = np.clip(idx, 0, src_len - 1)
        w = np.where(valid, kernel((idx + 0.5 - centers) / filterscale), 0.0)
        acc += w[None, :] * src[:, idx]
        weights += w
    return np.where(weights[None, :] == 0.0, 0.0, acc / weights)


def pass_gegl(src: np.ndarray, dst_len: int) -> np.ndarray:
    """One separable pass along the last axis of `src` (P, N):
    GIMP's window arithmetic (GEGL's cubic sampler: the downsample
    averages the fixed 4-tap at the sub-block centers, capped at 5;
    the out-of-range taps read the abyss, zero, no renormalization)."""
    src_len = src.shape[1]
    scale = src_len / dst_len
    n = max(1, min(int(scale), 5))
    u_dx = scale / n

    out = np.zeros((src.shape[0], dst_len), dtype=np.float64)
    for i in range(dst_len):
        x0 = (i + 0.5) * scale - (scale - u_dx) / 2.0
        acc = np.zeros(src.shape[0])
        for j in range(n):
            shifted = x0 + j * u_dx - 0.5
            ix = math.floor(shifted)
            frac = shifted - ix
            for d in (-1, 0, 1, 2):
                t = ix + d
                if 0 <= t < src_len:
                    acc += gegl_cubic_kernel(frac - d) * src[:, t]
        out[:, i] = acc / n
    return out


def resample_image(im: Image.Image, size: tuple[int, int], pass_fn) -> Image.Image:
    """A resize in the buffer's form: straight sRGB in, decoded to
    linear and premultiplied, the two separable passes (`pass_fn`
    per axis), the alpha clamped, demultiplied, re-encoded."""
    width, height = size
    arr = np.asarray(im.convert("RGBA")).astype(np.float64) / 255.0
    alpha = arr[..., 3:4]
    linear = np.concatenate((srgb_to_linear(arr[..., :3]) * alpha, alpha), axis=-1)
    (sh, sw, _) = linear.shape
    # The horizontal pass (per row, per channel: sw -> width), then the
    # vertical (per column: sh -> height).
    across = (
        pass_fn(
            np.ascontiguousarray(linear.transpose(0, 2, 1).reshape(sh * 4, sw)),
            width,
        )
        .reshape(sh, 4, width)
        .transpose(0, 2, 1)
    )
    out = (
        pass_fn(
            np.ascontiguousarray(across.transpose(2, 1, 0).reshape(4 * width, sh)),
            height,
        )
        .reshape(4, width, height)
        .transpose(2, 1, 0)
    )
    # The alpha clamp, then the demultiply (a zero alpha reads as 0).
    out[..., 3] = np.clip(out[..., 3], 0.0, 1.0)
    a = out[..., 3:4]
    rgb = np.divide(out[..., :3], a, out=np.zeros_like(out[..., :3]), where=a > 0.0)
    stored = np.concatenate((linear_to_srgb(rgb), a), axis=-1)
    return Image.fromarray(encode_u8(stored), mode="RGBA")


def cubic_resize(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    """GIMP's resize: GEGL's cubic arithmetic, the two passes."""
    return resample_image(im, size, pass_gegl)


def lanczos_pass(src: np.ndarray, dst_len: int) -> np.ndarray:
    return pass_signals(src, dst_len, lanczos3_kernel, 3.0)


def lanczos_resize(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    """The reference's window arithmetic, the Lanczos-3."""
    return resample_image(im, size, lanczos_pass)


def cubic_fit(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    """src/nikke_reborn/image.py::_fit_background, the cubic."""
    width, height = size
    scale = max(width / im.width, height / im.height)
    if scale != 1.0:
        im = cubic_resize(im, (round(im.width * scale), round(im.height * scale)))
    left = (im.width - width) // 2
    top = (im.height - height) // 2
    return im.crop((left, top, left + width, top + height)).convert("RGBA")


def lanczos_aspect(im: Image.Image, width: int) -> Image.Image:
    """The logo's one-dim resize: the height derived from the width."""
    return lanczos_resize(im, (width, round(width * im.height / im.width)))


def delta(ours: Image.Image, ref: Image.Image) -> tuple[int, int]:
    """(Max per-channel delta, pixels with any channel at 8 or more),
    premultiplied as above (the alpha channel compared straight)."""
    o = np.asarray(ours).astype(np.float64)
    r = np.asarray(ref).astype(np.float64)
    o[..., :3] *= o[..., 3:4] / 255.0
    r[..., :3] *= r[..., 3:4] / 255.0
    d = np.abs(o - r)
    return int(d.max()), int((d.max(axis=-1) >= 8).sum())  # per pixel


def run_engine(
    canvas: tuple[int, int], scale: float, params: dict[str, object]
) -> Image.Image:
    cmd = [
        str(BIN),
        str(SCRIPT),
        "--width",
        str(canvas[0]),
        "--height",
        str(canvas[1]),
        "--scale",
        repr(scale),
    ]
    for name, value in params.items():
        cmd += [f"--{name}", str(value)]
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
        if proc.returncode != 0:
            sys.stderr.write(proc.stderr)
            raise SystemExit(f"engine failed ({proc.returncode}): {cmd}")
        return Image.open(Path(tmp) / "output.png").convert("RGBA")


def main() -> int:
    sky = ROOT / "assets/images/backgrounds/sky-night.png"
    logo = ROOT / "assets/images/Logo_White.png"
    half = (round(CANVAS[0] * 0.5), round(CANVAS[1] * 0.5))
    logo_height = round(LOGO_TARGET_WIDTH * 260 / 512)  # the logo's file aspect

    cases: list[tuple[str, object, tuple[int, int], float, dict[str, object]]] = [
        (
            "sky-night cover x0.5 cubic",
            lambda: cubic_fit(Image.open(sky).convert("RGBA"), half),
            CANVAS,
            0.5,
            {
                "rw": CANVAS[0],
                "rh": CANVAS[1],
                "path": rel(sky),
                "mode": "cover",
                "filter": "cubic",
            },
        ),
        (
            "logo cover x0.5 cubic",
            lambda: cubic_fit(Image.open(logo).convert("RGBA"), half),
            CANVAS,
            0.5,
            {
                "rw": CANVAS[0],
                "rh": CANVAS[1],
                "path": rel(logo),
                "mode": "cover",
                "filter": "cubic",
            },
        ),
        (
            "logo aspect x1 lanczos",
            lambda: lanczos_aspect(Image.open(logo).convert("RGBA"), LOGO_TARGET_WIDTH),
            (LOGO_TARGET_WIDTH, logo_height),
            1.0,
            {"path": rel(logo), "rw": LOGO_TARGET_WIDTH, "filter": "lanczos"},
        ),
    ]

    far = 0
    for label, ref_fn, canvas, scale, params in cases:
        ref = ref_fn()
        ours = run_engine(canvas, scale, params)
        if ours.size != ref.size:
            print(f"{label:22} SIZE MISMATCH  ours {ours.size}  ref {ref.size}")
            far += 1
            continue
        worst, off = delta(ours, ref)
        verdict = "ok" if worst <= 5 else ("marginal" if worst <= 8 else "FAR")
        if worst > 8:
            far += 1
        print(f"{label:29} max {worst:3d}  >=8: {off:7d} px  {verdict}")

    print(f"\n{len(cases) - far}/{len(cases)} cases within a few units")
    return 1 if far else 0


if __name__ == "__main__":
    raise SystemExit(main())
