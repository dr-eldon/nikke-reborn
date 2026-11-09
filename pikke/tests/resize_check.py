#!/usr/bin/env python3
"""How far is pikke's resize from Pillow's LANCZOS, on the fly.

One engine run per case (resize_check.lua loads, resizes, yields),
diffed against the reference pipeline's own arithmetic on the same
assets — decoded sRGB, max per-pixel per-channel delta, premultiplied
(the RGB channels weighted by their alpha: the reference resamples
straight and bleeds color into fully transparent pixels, where the
color is undefined — the engine's buffer form reads it as zero, and
that is the comparison the pixels actually carry). No recorded
vectors.

The cases are one per target semantic: the background's cover (its
aspect is the canvas', so it degrades to a plain resample — the
downscale, the filter's work), the logo's cover (a different aspect —
the center crop), and the logo's aspect-preserved width target. The
x1.25 cases' 2048×2560 outputs are too heavy for a debug-build run.
"""

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


def fit_background(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    """src/nikke_reborn/image.py::_fit_background."""
    width, height = size
    scale = max(width / im.width, height / im.height)
    if scale != 1.0:
        im = im.resize(
            (round(im.width * scale), round(im.height * scale)),
            Image.Resampling.LANCZOS,
        )
    left = (im.width - width) // 2
    top = (im.height - height) // 2
    return im.crop((left, top, left + width, top + height)).convert("RGBA")


def aspect(im: Image.Image, width: int) -> Image.Image:
    """The logo's one-dim resize: the height derived from the width."""
    return im.resize(
        (width, round(width * im.height / im.width)), Image.Resampling.LANCZOS
    ).convert("RGBA")


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
            "sky-night cover x0.5",
            lambda: fit_background(Image.open(sky).convert("RGBA"), half),
            CANVAS,
            0.5,
            {"rw": CANVAS[0], "rh": CANVAS[1], "path": rel(sky), "mode": "cover"},
        ),
        (
            "logo cover x0.5",
            lambda: fit_background(Image.open(logo).convert("RGBA"), half),
            CANVAS,
            0.5,
            {"rw": CANVAS[0], "rh": CANVAS[1], "path": rel(logo), "mode": "cover"},
        ),
        (
            "logo aspect x1",
            lambda: aspect(Image.open(logo).convert("RGBA"), LOGO_TARGET_WIDTH),
            (LOGO_TARGET_WIDTH, logo_height),
            1.0,
            {"path": rel(logo), "rw": LOGO_TARGET_WIDTH},
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
        print(f"{label:22} max {worst:3d}  >=8: {off:7d} px  {verdict}")

    print(f"\n{len(cases) - far}/{len(cases)} cases within a few units")
    return 1 if far else 0


if __name__ == "__main__":
    raise SystemExit(main())
