"""The Phase 3 test vectors (the tests in color.rs), recorded from the
reference pipeline. Run from the repo root:
uv run python pikke/tests/vectors/gen.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from nikke_reborn import linear

HERE = Path(__file__).parent


def reference_over(base: tuple[int, ...], layer: tuple[int, ...]) -> tuple[int, ...]:
    """The reference's linear over and Pillow's sRGB over of one pixel."""
    layer_image = Image.new("RGBA", (1, 1), layer)

    linear_base = Image.new("RGBA", (1, 1), base)
    linear._linear_over(linear_base, layer_image)
    linear_out = linear_base.getpixel((0, 0))

    srgb_base = Image.new("RGBA", (1, 1), base)
    srgb_base.alpha_composite(layer_image)
    srgb_out = srgb_base.getpixel((0, 0))

    return linear_out, srgb_out


def over_rows() -> list[str]:
    random = np.random.default_rng(0).integers(
        0, 256, size=(4096, 8), dtype=np.uint8
    )
    curated = [
        (10, 200, 30, 255, 90, 10, 250, 0),  # a clear layer leaves the base
        (10, 200, 30, 255, 90, 10, 250, 255),  # an opaque layer replaces it
        (0, 0, 0, 0, 5, 6, 7, 200),  # a transparent base receives it straight
        (3, 4, 5, 0, 9, 8, 7, 0),  # both clear
        (100, 100, 100, 128, 200, 200, 200, 128),  # half over half
        (10, 10, 10, 255, 11, 11, 11, 128),  # across the decode threshold
        (244, 244, 244, 255, 254, 254, 254, 128),  # near white
        (1, 2, 3, 255, 4, 5, 6, 1),  # a one-step layer
    ]
    rows = []
    for pair in [tuple(p) for p in random] + curated:
        base, layer = pair[0:4], pair[4:8]
        linear_out, srgb_out = reference_over(base, layer)
        # The round-trip cases are byte-exact in the reference itself.
        if layer[3] == 0:
            assert linear_out == base and srgb_out == base, pair
        elif layer[3] == 255:
            assert linear_out == layer and srgb_out == layer, pair
        elif base[3] == 0:
            assert linear_out == layer, pair
        rows.append(" ".join(str(v) for v in (*base, *layer, *linear_out, *srgb_out)))
    return rows


def luma_mean(rgb: np.ndarray) -> float:
    f = rgb.astype(np.float64)
    return float((0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]).mean())


def luma_rows() -> list[str]:
    rng = np.random.default_rng(1)
    images = [rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8) for _ in range(3)]
    images += [np.full((1, 1, 3), v, dtype=np.uint8) for v in (0, 128, 255)]
    images += [
        np.array([[[255, 0, 0]]], dtype=np.uint8),
        np.array([[[0, 255, 0]]], dtype=np.uint8),
        np.array([[[0, 0, 255]]], dtype=np.uint8),
        np.full((8, 8, 3), 128, dtype=np.uint8),
    ]
    ramp = np.zeros((1, 32, 3), dtype=np.uint8)
    ramp[0, :, 0] = np.arange(32, dtype=np.uint8) * 8
    images.append(ramp)
    return [
        f"{image.shape[0]} {image.shape[1]} {luma_mean(image)!r} "
        + " ".join(map(str, image.reshape(-1, 3).ravel().tolist()))
        for image in images
    ]


def pillow_lut(lo: int, hi: int) -> list[int]:
    """The stretch's point map through Pillow's own autocontrast: each
    value probed on a pixel whose histogram extent (the mask keeps the
    lo/hi pixels in and the probe out) is exactly [lo, hi]."""
    if hi <= lo:
        return list(range(256))
    mask = Image.fromarray(np.array([[0, 255, 255]], dtype=np.uint8), mode="L")
    luts = []
    for value in range(256):
        image = Image.fromarray(
            np.array([[value, lo, hi]], dtype=np.uint8), mode="L"
        )
        luts.append(ImageOps.autocontrast(image, preserve_tone=True, mask=mask).tobytes()[0])
    return luts


def stretch_rows() -> list[str]:
    rng = np.random.default_rng(2)
    cases = [(0, 255), (128, 128), (5, 250), (10, 200), (0, 1), (17, 240), (1, 0)]
    cases += [tuple(v) for v in rng.integers(0, 256, size=(8, 2), dtype=np.uint32)]
    rows = []
    for lo, hi in cases:
        if hi <= lo:
            lut = list(range(256))
        else:
            lut = pillow_lut(lo, hi)
        rows.append(f"{lo} {hi} " + " ".join(map(str, lut)))
    return rows


def main() -> None:
    (HERE / "encode_ref.bin").write_bytes(linear.ENCODE.tobytes())
    (HERE / "over.txt").write_text("\n".join(over_rows()) + "\n")
    (HERE / "luma.txt").write_text("\n".join(luma_rows()) + "\n")
    (HERE / "stretch.txt").write_text("\n".join(stretch_rows()) + "\n")
    print("vectors written to", HERE)


if __name__ == "__main__":
    main()
