/// A 0-1 RGBA color (straight alpha): linear light or sRGB, by context.
#[derive(Clone, Copy, Debug)]
pub struct Color {
    pub r: f32,
    pub g: f32,
    pub b: f32,
    pub a: f32,
}

impl Color {
    /// A stored sRGB pixel (0-255) as a 0-1 sRGB color.
    pub fn from_rgba_u8(pixel: [u8; 4]) -> Self {
        Self {
            r: pixel[0] as f32 / 255.0,
            g: pixel[1] as f32 / 255.0,
            b: pixel[2] as f32 / 255.0,
            a: pixel[3] as f32 / 255.0,
        }
    }

    /// This color in linear light (the IEC 61966-2-1 decode of the
    /// channels); the alpha is untouched.
    pub fn srgb_to_linear(self) -> Self {
        Self {
            r: srgb_to_linear(self.r),
            g: srgb_to_linear(self.g),
            b: srgb_to_linear(self.b),
            a: self.a,
        }
    }

    /// This color in sRGB (the IEC 61966-2-1 encode of the channels);
    /// the alpha is untouched.
    pub fn linear_to_srgb(self) -> Self {
        Self {
            r: linear_to_srgb(self.r),
            g: linear_to_srgb(self.g),
            b: linear_to_srgb(self.b),
            a: self.a,
        }
    }

    /// The 8-bit stored pixel: each channel through the single encode
    /// rounding.
    pub fn to_rgba_u8(self) -> [u8; 4] {
        [
            encode_u8(self.r),
            encode_u8(self.g),
            encode_u8(self.b),
            encode_u8(self.a),
        ]
    }

    /// The buffer's premultiplied form.
    pub fn premultiply(self) -> Self {
        Self {
            r: self.r * self.a,
            g: self.g * self.a,
            b: self.b * self.a,
            a: self.a,
        }
    }

    /// The straight form from the buffer's premultiplied one. A fully
    /// transparent pixel's color is unrecoverable and reads as 0.
    pub fn demultiply(self) -> Self {
        if self.a == 0.0 {
            return Self {
                r: 0.0,
                g: 0.0,
                b: 0.0,
                a: 0.0,
            };
        }

        Self {
            r: self.r / self.a,
            g: self.g / self.a,
            b: self.b / self.a,
            a: self.a,
        }
    }

    /// Porter-Duff 'over' in the buffer's premultiplied form (the
    /// caller's domain: linear light or sRGB): no division, and a 0
    /// or 1 alpha on either side falls out of the formula exactly.
    pub fn over(self, layer: Color) -> Color {
        let retain = 1.0 - layer.a;

        Color {
            r: layer.r + self.r * retain,
            g: layer.g + self.g * retain,
            b: layer.b + self.b * retain,
            a: layer.a + self.a * retain,
        }
    }
}

/// 0-1 sRGB (stored) -> 0-1 linear light, the IEC 61966-2-1 curve.
pub fn srgb_to_linear(stored: f32) -> f32 {
    if stored <= 0.04045 {
        stored / 12.92
    } else {
        ((stored + 0.055) / 1.055).powf(2.4)
    }
}

/// 0-1 linear light -> 0-1 sRGB (stored), the IEC 61966-2-1 curve;
/// out-of-range linear clamps to 0-1 here, the encode path's only
/// clamp.
pub fn linear_to_srgb(linear: f32) -> f32 {
    let linear = linear.clamp(0.0, 1.0);
    if linear <= 0.0031308 {
        linear * 12.92
    } else {
        1.055 * linear.powf(1.0 / 2.4) - 0.055
    }
}

/// The single encode rounding: a 0-1 stored value to 8 bits (nearest
/// 1/255, ties away from zero).
pub fn encode_u8(stored: f32) -> u8 {
    (stored * 255.0).round() as u8
}

/// The Rec. 709 luma of a stored sRGB pixel (0-255 channels), 0-255.
pub fn luma(pixel: [u8; 3]) -> f64 {
    0.2126 * pixel[0] as f64 + 0.7152 * pixel[1] as f64 + 0.0722 * pixel[2] as f64
}

/// The ITU-R 601 luma of a stored sRGB pixel — the stretch's histogram
/// channel (the reference's `convert("L")` integer path).
pub fn luma601(pixel: [u8; 3]) -> u8 {
    (((pixel[0] as u32) * 19595 + (pixel[1] as u32) * 38470 + (pixel[2] as u32) * 7471 + 0x8000)
        >> 16) as u8
}

/// The tone-preserving stretch's point map: the stored 8-bit values
/// over [lo, hi] (the histogram's extent on the 601 luma channel)
/// mapped to [0, 255]; degenerate (hi <= lo) is the identity.
pub fn stretch_lut(lo: u32, hi: u32) -> [u8; 256] {
    let map: Vec<u8> = if hi <= lo {
        (0u8..=255).collect()
    } else {
        let scale = 255.0 / (hi - lo) as f64;
        let offset = -(lo as f64) * scale;
        (0u8..=255)
            .map(|value| ((value as f64) * scale + offset).trunc().clamp(0.0, 255.0) as u8)
            .collect()
    };
    map.try_into().unwrap()
}

/// The resize's resampling kernel.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Filter {
    #[default]
    Bicubic,
    Lanczos,
}

/// The buffer's form (the filter over premultiplied light is
/// alpha-blind); an unchanged axis copies (the unit-scale kernel is
/// the identity).
pub fn resize(
    filter: Filter,
    src: &[f32],
    src_w: u32,
    src_h: u32,
    dst_w: u32,
    dst_h: u32,
) -> Vec<f32> {
    match filter {
        Filter::Lanczos => resample(lanczos3, 3.0, src, src_w, src_h, dst_w, dst_h),
        Filter::Bicubic => resample(bicubic, 2.0, src, src_w, src_h, dst_w, dst_h),
    }
}

fn resample(
    kernel: impl Fn(f64) -> f64,
    support: f64,
    src: &[f32],
    src_w: u32,
    src_h: u32,
    dst_w: u32,
    dst_h: u32,
) -> Vec<f32> {
    /// One separable pass: `src_len` samples, `src_stride` apart, in
    /// `src`, scaled to `dst_len` (`dst_stride` apart in `out`), the
    /// weights normalized per output sample; out-of-range taps are
    /// absent (the weights renormalize over the window that remains).
    fn pass(
        src: &[f32],
        src_stride: usize,
        out: &mut [f32],
        dst_stride: usize,
        src_len: usize,
        dst_len: usize,
        kernel: impl Fn(f64) -> f64,
        support: f64,
    ) {
        // Source samples per target sample; the reference's filter scale
        // is the ratio on a downscale and 1 on an upscale (the window
        // stays at the kernel's width, the kernel argument unscaled).
        let scale = src_len as f64 / dst_len as f64;
        let filterscale = scale.max(1.0);
        let support = support * filterscale;

        for i in 0..dst_len {
            // The kernel's zero: the target sample's center in source
            // samples (the pixel-center convention, tap j at j + 0.5).
            // At unit scale the arguments are integral and only the
            // center tap carries weight: the identity, the reference's.
            let center = (i as f64 + 0.5) * scale;
            // The reference's tap bounds: half-up, clamped to the source.
            let start = (center - support + 0.5).trunc().clamp(0.0, src_len as f64) as usize;
            let end = (center + support + 0.5).trunc().clamp(0.0, src_len as f64) as usize;

            let mut acc = 0.0f32;
            let mut weights = 0.0f32;
            for j in start..end {
                let w = kernel((j as f64 + 0.5 - center) / filterscale) as f32;
                acc += w * src[j * src_stride];
                weights += w;
            }
            out[i * dst_stride] = if weights == 0.0 { 0.0 } else { acc / weights };
        }
    }

    let (sw, sh, dw, dh) = (
        src_w as usize,
        src_h as usize,
        dst_w as usize,
        dst_h as usize,
    );

    let mut across = vec![0.0f32; dw * sh];
    if dw == sw {
        across.copy_from_slice(src);
    } else {
        for y in 0..sh {
            pass(
                &src[y * sw..(y + 1) * sw],
                1,
                &mut across[y * dw..(y + 1) * dw],
                1,
                sw,
                dw,
                &kernel,
                support,
            );
        }
    }

    let mut out = vec![0.0f32; dw * dh];
    if dh == sh {
        out.copy_from_slice(&across);
    } else {
        for x in 0..dw {
            pass(
                &across[x..],
                dw,
                &mut out[x..],
                dw,
                sh,
                dh,
                &kernel,
                support,
            );
        }
    }

    out
}

/// The Lanczos-3 kernel: the 3-lobed sinc, zero at the window's edge.
fn lanczos3(x: f64) -> f64 {
    if x.abs() >= 3.0 {
        return 0.0;
    }
    if x == 0.0 {
        return 1.0;
    }
    let pi_x = std::f64::consts::PI * x;
    let pi_x3 = pi_x / 3.0;
    (pi_x.sin() / pi_x) * (pi_x3.sin() / pi_x3)
}

/// The a = -0.5 cubic convolution, zero outside ±2.
fn bicubic(x: f64) -> f64 {
    let a = -0.5;
    let x = if x < 0.0 { -x } else { x };
    if x < 1.0 {
        ((a + 2.0) * x - (a + 3.0)) * x * x + 1.0
    } else if x < 2.0 {
        (((x - 5.0) * x + 8.0) * x - 4.0) * a
    } else {
        0.0
    }
}

/// The `out_w`×`out_h` region `left`/`top` into a `src_w`-wide
/// row-major plane.
pub fn crop(src: &[f32], src_w: u32, left: u32, top: u32, out_w: u32, out_h: u32) -> Vec<f32> {
    let (sw, ow, oh) = (src_w as usize, out_w as usize, out_h as usize);
    let (left, top) = (left as usize, top as usize);
    let mut out = vec![0.0f32; ow * oh];
    for y in 0..oh {
        let row = (top + y) * sw + left;
        out[y * ow..(y + 1) * ow].copy_from_slice(&src[row..row + ow]);
    }
    out
}

#[cfg(test)]
mod vectors {
    use super::*;

    // Recorded from the reference pipeline (tests/vectors/gen.py, run
    // via uv from the repo root).
    fn read(name: &str) -> Vec<u8> {
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("tests")
            .join("vectors")
            .join(name);
        std::fs::read(path).unwrap()
    }

    #[test]
    fn encode_matches_the_reference_within_one() {
        let reference = read("encode_ref.bin");
        assert_eq!(reference.len(), 65_536);
        let mut differing = 0;
        for step in 0..65_536u32 {
            let ours = encode_u8(linear_to_srgb((step as f32) / 65_535.0));
            let theirs = reference[step as usize];
            let diff = ours.abs_diff(theirs);
            assert!(diff <= 1, "step {step}: ours {ours}, theirs {theirs}");
            differing += usize::from(diff > 0);
        }
        eprintln!("encode: {differing}/65536 steps differ (all within one)");
    }

    #[test]
    fn the_round_trip_is_exact_for_all_stored_values() {
        for value in 0..=255u8 {
            let linear = srgb_to_linear(value as f32 / 255.0);
            assert_eq!(encode_u8(linear_to_srgb(linear)), value);
        }
    }

    // over.txt lines: base(4) layer(4) linear_out(4) srgb_out(4).
    // Both columns through the buffer's form — in linear for the
    // first, in sRGB for the second. The one line skipped is both
    // alphas 0: the reference keeps the layer's color where a
    // straight composite would leave it, and the premultiplied
    // form discards it.
    #[test]
    fn over_matches_the_reference() {
        let text = String::from_utf8(read("over.txt")).unwrap();
        let mut lines = 0;
        for line in text.lines() {
            let values: Vec<u8> = line
                .split_whitespace()
                .map(|token| token.parse().unwrap())
                .collect();
            assert_eq!(values.len(), 16);
            let base = Color::from_rgba_u8([values[0], values[1], values[2], values[3]]);
            let layer = Color::from_rgba_u8([values[4], values[5], values[6], values[7]]);

            if base.a == 0.0 && layer.a == 0.0 {
                continue;
            }

            let linear = base
                .srgb_to_linear()
                .premultiply()
                .over(layer.srgb_to_linear().premultiply())
                .demultiply()
                .linear_to_srgb()
                .to_rgba_u8();
            let reference = [values[8], values[9], values[10], values[11]];

            let srgb = base
                .premultiply()
                .over(layer.premultiply())
                .demultiply()
                .to_rgba_u8();
            let srgb_reference = [values[12], values[13], values[14], values[15]];

            // The round-trip cases are byte-exact on both columns.
            let exact = layer.a == 0.0 || layer.a == 1.0 || base.a == 0.0;
            for channel in 0..4 {
                for (ours, theirs, path) in [
                    (linear[channel], reference[channel], "linear"),
                    (srgb[channel], srgb_reference[channel], "srgb"),
                ] {
                    if exact {
                        assert_eq!(
                            ours, theirs,
                            "line {lines}: {path} channel {channel} (base {base:?} layer {layer:?})"
                        );
                    } else {
                        assert!(
                            ours.abs_diff(theirs) <= 1,
                            "line {lines}: {path} channel {channel} (base {base:?} layer {layer:?})"
                        );
                    }
                }
            }
            lines += 1;
        }
        eprintln!("over: {lines} pairs");
    }

    // luma.txt lines: height width mean, then the row-major pixels.
    #[test]
    fn luma_is_the_709_mean() {
        let text = String::from_utf8(read("luma.txt")).unwrap();
        for line in text.lines() {
            let tokens: Vec<&str> = line.split_whitespace().collect();
            let height: usize = tokens[0].parse().unwrap();
            let width: usize = tokens[1].parse().unwrap();
            let mean: f64 = tokens[2].parse().unwrap();
            let pixels: Vec<u8> = tokens[3..]
                .iter()
                .map(|token| token.parse().unwrap())
                .collect();
            assert_eq!(pixels.len(), height * width * 3);
            let count = height * width;
            // RGB: 3-byte pixels, so no remainder.
            let mut sum = 0.0;
            for pixel in pixels.as_chunks::<3>().0 {
                sum += luma(*pixel);
            }
            let ours = sum / count as f64;
            assert!(
                (ours - mean).abs() < 1e-3,
                "luma: ours {ours}, theirs {mean} ({count} pixels)"
            );
        }
    }

    // stretch.txt lines: lo hi, then the 256 point map.
    #[test]
    fn stretch_matches_the_reference() {
        let text = String::from_utf8(read("stretch.txt")).unwrap();
        for line in text.lines() {
            let values: Vec<u32> = line
                .split_whitespace()
                .map(|token| token.parse().unwrap())
                .collect();
            assert_eq!(values.len(), 258);
            let (lo, hi) = (values[0], values[1]);
            let reference: Vec<u8> = values[2..].iter().map(|value| *value as u8).collect();
            let ours = stretch_lut(lo, hi);
            assert_eq!(ours.to_vec(), reference, "stretch: lo {lo}, hi {hi}");
        }
    }
}

#[cfg(test)]
mod kernels {
    use super::{bicubic, lanczos3};

    #[test]
    fn the_kernels_match_their_defining_values() {
        // Unit weight at the center (both).
        assert_eq!(lanczos3(0.0), 1.0);
        assert_eq!(bicubic(0.0), 1.0);
        // The bicubic is a polynomial: exact zeros at its grid (the
        // sinc is not), and the negative lobe (the ringing behind
        // the alpha clamp).
        for x in [1.0, 2.0] {
            assert_eq!(bicubic(x), 0.0);
            assert_eq!(bicubic(-x), 0.0);
        }
        assert!(bicubic(1.5) < 0.0);
    }
}
