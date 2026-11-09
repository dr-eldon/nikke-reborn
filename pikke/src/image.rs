use std::path::Path;
use std::sync::Arc;

use anywho::anywho;
use image::{ColorType, ImageFormat};
use mlua::{AnyUserData, Lua, Result, Table, UserData, UserDataFields, UserDataMethods};

use crate::Viewport;
use crate::color::{Color, Filter, crop, resize};

/// The RGBA buffer: premultiplied f32 linear (0-1) planes, the pixel
/// dims at `scale`; the API reports logical.
#[derive(Clone, Debug)]
pub struct Image {
    buffer: Arc<Buffer>,
    width: u32,
    height: u32,
    scale: f32,
    viewport: Viewport,
}

#[derive(Clone, Debug)]
struct Buffer {
    r: Vec<f32>,
    g: Vec<f32>,
    b: Vec<f32>,
    a: Vec<f32>,
}

/// How a resize target is met.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Mode {
    /// Stretch to the target box itself.
    #[default]
    Stretch,
    /// Center-crop the target.
    Cover,
}

impl Image {
    pub fn transparent(width: u32, height: u32, viewport: Viewport) -> Image {
        let count = (width * height) as usize;
        Image {
            buffer: Arc::new(Buffer {
                r: vec![0.0; count],
                g: vec![0.0; count],
                b: vec![0.0; count],
                a: vec![0.0; count],
            }),
            width,
            height,
            scale: viewport.scale,
            viewport,
        }
    }

    pub fn physical_width(&self) -> u32 {
        self.width
    }

    pub fn physical_height(&self) -> u32 {
        self.height
    }

    pub fn logical_width(&self) -> u32 {
        (self.width as f32 / self.scale).round() as u32
    }

    pub fn logical_height(&self) -> u32 {
        (self.height as f32 / self.scale).round() as u32
    }

    pub fn to_rgba8(&self) -> Vec<u8> {
        let count = (self.width * self.height) as usize;
        let mut out = Vec::with_capacity(count * 4);
        for i in 0..count {
            let color = Color {
                r: self.buffer.r[i],
                g: self.buffer.g[i],
                b: self.buffer.b[i],
                a: self.buffer.a[i],
            }
            .demultiply()
            .linear_to_srgb()
            .to_rgba_u8();
            out.extend_from_slice(&color);
        }
        out
    }

    pub fn resize(&mut self, new_width: f32, new_height: f32, filter: Filter, mode: Mode) {
        let scale = self.viewport.scale;
        let (target_w, target_h) = (
            self.viewport.physical(new_width),
            self.viewport.physical(new_height),
        );
        assert!(
            target_w != 0 && target_h != 0,
            "resize: the physical target is {target_w}×{target_h}; it must be at least 1×1"
        );

        let (box_w, box_h) = match mode {
            Mode::Cover => {
                let factor = f32::max(
                    target_w as f32 / self.width as f32,
                    target_h as f32 / self.height as f32,
                );
                (
                    (self.width as f32 * factor).round() as u32,
                    (self.height as f32 * factor).round() as u32,
                )
            }
            Mode::Stretch => (target_w, target_h),
        };

        // The center crop's halves (the box is ≥ the target: the cover
        // box is built from the max of the per-axis ratios).
        let left = (box_w - target_w) / 2;
        let top = (box_h - target_h) / 2;

        // A no-op resize still settles the buffer at the run scale.
        if (box_w, box_h) == (self.width, self.height) && left == 0 && top == 0 {
            self.scale = scale;
            return;
        }

        // The first in-place write forks a shared buffer (CoW).
        let buffer = Arc::make_mut(&mut self.buffer);
        let resized = (box_w, box_h) != (self.width, self.height);
        if resized {
            let (w, h) = (self.width, self.height);
            buffer.r = resize(filter, &buffer.r, w, h, box_w, box_h);
            buffer.g = resize(filter, &buffer.g, w, h, box_w, box_h);
            buffer.b = resize(filter, &buffer.b, w, h, box_w, box_h);
            buffer.a = resize(filter, &buffer.a, w, h, box_w, box_h);
        }
        if left != 0 || top != 0 {
            buffer.r = crop(&buffer.r, box_w, left, top, target_w, target_h);
            buffer.g = crop(&buffer.g, box_w, left, top, target_w, target_h);
            buffer.b = crop(&buffer.b, box_w, left, top, target_w, target_h);
            buffer.a = crop(&buffer.a, box_w, left, top, target_w, target_h);
        }

        // Alpha is a 0-1 ratio, not light: the resample's
        // out-of-range ringing is meaningless there (the light
        // channels keep it to the encode's clamp).
        if resized {
            for value in buffer.a.iter_mut() {
                *value = value.clamp(0.0, 1.0);
            }
        }

        self.width = target_w;
        self.height = target_h;
        self.scale = scale;
    }

    /// The buffer as `output.png` (the working directory): the straight
    /// RGBA8 sRGB form, the buffer's alpha as-is, written atomically.
    pub fn write(&self) -> anywho::Result<()> {
        let rgba8 = self.to_rgba8();
        let target = Path::new("output.png");
        let temp = Path::new("output.png.tmp");
        image::save_buffer_with_format(
            temp,
            &rgba8,
            self.width,
            self.height,
            ColorType::Rgba8,
            ImageFormat::Png,
        )
        .map_err(|error| {
            let _ = std::fs::remove_file(temp);
            anywho!("failed to write output.png: {error}")
        })?;
        std::fs::rename(temp, target)
            .map_err(|error| anywho!("failed to finalize output.png: {error}"))?;
        Ok(())
    }
}

/// A bitmap at the reference's scale (logical): the straight RGBA8
/// sRGB boundary decoded and premultiplied into the buffer's form.
fn load(path: &Path, viewport: Viewport) -> anywho::Result<Image> {
    let rgba = image::open(path)
        .map_err(|error| anywho!("failed to load {}: {error}", path.display()))?
        .to_rgba8();
    let (width, height) = (rgba.width(), rgba.height());
    let count = (width * height) as usize;
    let (mut r, mut g, mut b, mut a) = (
        Vec::with_capacity(count),
        Vec::with_capacity(count),
        Vec::with_capacity(count),
        Vec::with_capacity(count),
    );
    // RGBA8: 4-byte pixels, so no remainder.
    for pixel in rgba.as_chunks::<4>().0 {
        let color = Color::from_rgba_u8([pixel[0], pixel[1], pixel[2], pixel[3]])
            .srgb_to_linear()
            .premultiply();
        r.push(color.r);
        g.push(color.g);
        b.push(color.b);
        a.push(color.a);
    }
    Ok(Image {
        buffer: Arc::new(Buffer { r, g, b, a }),
        width,
        height,
        scale: 1.0,
        viewport,
    })
}

impl UserData for Image {
    fn add_fields<F: UserDataFields<Image>>(fields: &mut F) {
        fields.add_meta_field("__name", "Image");
    }

    fn add_methods<M: UserDataMethods<Image>>(methods: &mut M) {
        methods.add_method("width", |_lua, this, _args: ()| -> Result<u32> {
            Ok(this.logical_width())
        });
        methods.add_method("height", |_lua, this, _args: ()| -> Result<u32> {
            Ok(this.logical_height())
        });
        methods.add_method("size", |_lua, this, _args: ()| -> Result<(u32, u32)> {
            Ok((this.logical_width(), this.logical_height()))
        });
        methods.add_method("clone", |_lua, this, _args: ()| -> Result<Image> {
            // Cheap (shares the buffer's Arc); the pixel copy is deferred
            // to the first in-place write (CoW).
            Ok(this.clone())
        });
        methods.add_method_mut("resize", |_lua, this, opts: Table| -> Result<()> {
            let width: Option<f32> = opts.get("width")?;
            let height: Option<f32> = opts.get("height")?;
            let filter: Option<String> = opts.get("filter")?;
            let mode: Option<String> = opts.get("mode")?;

            // A one-dim target: the missing dim follows the image's aspect.
            let (width, height) = match (width, height) {
                (Some(width), Some(height)) => (width, height),
                (Some(width), None) => (
                    width,
                    (width * this.height as f32 / this.width as f32).round(),
                ),
                (None, Some(height)) => (
                    (height * this.width as f32 / this.height as f32).round(),
                    height,
                ),
                (None, None) => {
                    return Err(mlua::Error::RuntimeError(
                        "resize: needs width or height".to_owned(),
                    ));
                }
            };

            let filter = match filter.as_deref() {
                None => Filter::default(),
                Some("cubic") => Filter::Cubic,
                Some("lanczos") => Filter::Lanczos,
                Some(other) => {
                    return Err(mlua::Error::RuntimeError(format!(
                        "resize: unknown filter: {other}"
                    )));
                }
            };

            let mode = match mode.as_deref() {
                None => Mode::default(),
                Some("cover") => Mode::Cover,
                Some(other) => {
                    return Err(mlua::Error::RuntimeError(format!(
                        "resize: unknown mode: {other}"
                    )));
                }
            };

            this.resize(width, height, filter, mode);
            Ok(())
        });
        methods.add_method_mut("contrast", |_lua, _this, _opts: Table| -> Result<()> {
            Ok(())
        });
        methods.add_method_mut(
            "blend",
            |_lua, this, (_layer, _opts): (AnyUserData, Option<Table>)| -> Result<()> {
                // A blend's receiver is the physical viewport (§3b).
                let (width, height) = (this.physical_width(), this.physical_height());
                let (physical_width, physical_height) =
                    (this.viewport.physical_width(), this.viewport.physical_height());
                if (width, height) != (physical_width, physical_height) {
                    return Err(mlua::Error::RuntimeError(format!(
                        "blend: the receiver is {width}×{height}, the viewport is {physical_width}×{physical_height}"
                    )));
                }
                Ok(())
            },
        );
        methods.add_method_mut(
            "fill",
            |_lua, _this, (_region, _color): (mlua::Value, String)| -> Result<()> { Ok(()) },
        );
        methods.add_method(
            "luma_at",
            |_lua, _this, _region: mlua::Value| -> Result<f64> { Ok(0.0) },
        );
    }
}

pub fn install(
    lua: &Lua,
    env: &Table,
    script_dir: &Path,
    viewport: Viewport,
) -> anywho::Result<()> {
    let script_dir = script_dir.to_path_buf();
    env.set(
        "image",
        lua.create_function(move |_lua, path: String| -> Result<Image> {
            load(&script_dir.join(&path), viewport)
                .map_err(|error| mlua::Error::RuntimeError(error.to_string()))
        })?,
    )?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::load;
    use crate::Viewport;
    use std::path::Path;

    #[test]
    fn the_base_background_loads_at_its_file_dims() {
        let path = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../assets/images/backgrounds/sky-night.png");
        let file = std::fs::read(&path).unwrap();

        // The PNG's IHDR: the width and height after the 8-byte
        // signature and the chunk header.
        let file_width = u32::from_be_bytes([file[16], file[17], file[18], file[19]]);
        let file_height = u32::from_be_bytes([file[20], file[21], file[22], file[23]]);

        let viewport = Viewport {
            width: 1640,
            height: 2048,
            scale: 1.0,
        };

        let image = load(&path, viewport).unwrap();
        assert_eq!(
            (image.logical_width(), image.logical_height()),
            (file_width, file_height)
        );

        let count = (file_width * file_height) as usize;

        for plane in [
            &image.buffer.r,
            &image.buffer.g,
            &image.buffer.b,
            &image.buffer.a,
        ] {
            assert_eq!(plane.len(), count);
        }
    }

    #[test]
    fn resize_lands_on_its_targets_and_forks() {
        use super::{Filter, Mode};

        let path = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../assets/images/backgrounds/sky-night.png");
        let mut image = load(
            &path,
            Viewport {
                width: 1640,
                height: 2048,
                scale: 0.5,
            },
        )
        .unwrap();
        let first_pixel = image.buffer.r[0];

        let mut fork = image.clone();

        // Stretch: the caller resolves the aspect (200 logical wide
        // at the file's 2048/1640: 250 tall) — 100×125 physical at
        // run scale 0.5.
        image.resize(200.0, 250.0, Filter::Lanczos, Mode::Stretch);
        assert_eq!(
            (image.physical_width(), image.physical_height()),
            (100, 125)
        );

        // The fork keeps the original: the resize forked it (CoW).
        assert_eq!(
            (fork.physical_width(), fork.physical_height()),
            (1640, 2048)
        );
        assert_eq!(fork.buffer.r[0], first_pixel);

        // Cover: logical 400×100 → the 200×50 target out of the
        // 200×250 box, cropped 100 from the top.
        fork.resize(400.0, 100.0, Filter::Cubic, Mode::Cover);
        assert_eq!((fork.physical_width(), fork.physical_height()), (200, 50));

        // A no-op target (the file already at the physical target,
        // here at run scale 2) only moves the buffer to the run's
        // scale: the same pixels now read as half the logical size.
        let mut image = load(
            &path,
            Viewport {
                width: 1640,
                height: 2048,
                scale: 2.0,
            },
        )
        .unwrap();
        image.resize(820.0, 1024.0, Filter::Cubic, Mode::Stretch);
        assert_eq!(image.scale, 2.0);
        assert_eq!((image.logical_width(), image.logical_height()), (820, 1024));
        assert_eq!(
            (image.physical_width(), image.physical_height()),
            (1640, 2048)
        );
    }
}
