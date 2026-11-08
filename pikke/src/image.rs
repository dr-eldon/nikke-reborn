use std::path::Path;

use anywho::anywho;
use mlua::{AnyUserData, Lua, Result, Table, UserData, UserDataFields, UserDataMethods};

use crate::Viewport;
use crate::color::Color;

/// The RGBA buffer: premultiplied f32 linear (0-1) planes, the pixel
/// dims at `scale`; the API reports logical.
// The planes' read consumers (the compositing ops) land with them.
#[allow(dead_code)]
#[derive(Clone, Debug)]
pub struct Image {
    r: Vec<f32>,
    g: Vec<f32>,
    b: Vec<f32>,
    a: Vec<f32>,
    width: u32,
    height: u32,
    /// The scale of these pixel dims (a loaded asset: the
    /// reference's; a resampled buffer: the run's).
    scale: f32,
    /// The run's viewport (the op-boundary transform, the receiver
    /// assertion).
    viewport: Viewport,
}

impl Image {
    /// A fully transparent buffer at the run's scale (the `spawn`
    /// mock's frame).
    pub fn transparent(width: u32, height: u32, viewport: Viewport) -> Image {
        let count = (width * height) as usize;
        Image {
            r: vec![0.0; count],
            g: vec![0.0; count],
            b: vec![0.0; count],
            a: vec![0.0; count],
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
        r,
        g,
        b,
        a,
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
        methods.add_method("resize", |_lua, this, opts: Table| -> Result<Image> {
            // Mock: the target's dims (transformed at the op
            // boundary) with a transparent buffer; the real resize
            // resamples.
            let width = match opts.get::<Option<f64>>("width")? {
                Some(logical) => this.viewport.physical(logical as f32),
                None => this.viewport.physical(this.logical_width() as f32),
            };
            let height = match opts.get::<Option<f64>>("height")? {
                Some(logical) => this.viewport.physical(logical as f32),
                None => this.viewport.physical(this.logical_height() as f32),
            };
            Ok(Image::transparent(width, height, this.viewport))
        });
        methods.add_method("contrast", |_lua, this, _opts: Table| -> Result<Image> {
            Ok(this.clone())
        });
        methods.add_method(
            "blend",
            |_lua, this, (_layer, _opts): (AnyUserData, Option<Table>)| -> Result<Image> {
                // A blend's receiver is the physical viewport (§3b).
                let (width, height) = (this.physical_width(), this.physical_height());
                let (physical_width, physical_height) =
                    (this.viewport.physical_width(), this.viewport.physical_height());
                if (width, height) != (physical_width, physical_height) {
                    return Err(mlua::Error::RuntimeError(format!(
                        "blend: the receiver is {width}×{height}, the viewport is {physical_width}×{physical_height}"
                    )));
                }
                Ok(this.clone())
            },
        );
        methods.add_method(
            "fill",
            |_lua, this, (_region, _color): (mlua::Value, String)| -> Result<Image> {
                Ok(this.clone())
            },
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
        for plane in [&image.r, &image.g, &image.b, &image.a] {
            assert_eq!(plane.len(), count);
        }
    }
}
