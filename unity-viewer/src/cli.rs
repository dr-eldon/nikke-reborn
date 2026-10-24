//! Headless screenshot mode.
//!
//! ```text
//! unity-viewer <mesh> <material> [options]
//! ```
//!
//! Renders the given mesh (with the given material) offscreen at the requested
//! asset rotation and zoom, then writes the result as a PNG. The camera keeps
//! its fixed default viewing pose (only the zoom changes); rotating the asset
//! is what aims the fixed world-space lights at the model's faces. No window
//! is opened. Skinned meshes are rendered in bind pose, same as the GUI.
//!
//! `--config` loads the asset rotation and camera zoom/pan from the same
//! JSON file the GUI's Import/Export buttons use; explicit flags override
//! the file's values.

use std::path::{Path, PathBuf};
use std::sync::Arc;

use crate::config::Config;
use crate::scene::{Camera, Material, Model, Pipeline, Primitive};
use crate::unity::Mesh;
use iced::Rectangle;

use crate::{ASSETS_DIR, IMAGES_DIR, OUTPUT_DIR, ROOT};

const DEFAULT_WIDTH: u32 = 1024;
const DEFAULT_HEIGHT: u32 = 1024;

const DEG: f32 = std::f32::consts::PI / 180.0;

/// Radians to degrees.
fn to_deg() -> f32 {
    180.0 / std::f32::consts::PI
}

/// Camera angle (radians) as degrees, trimmed for display (e.g. `-140`).
fn fmt_deg(rad: f32) -> String {
    format!("{}", (rad * to_deg() * 100.0).round() / 100.0)
}

/// The usage text. The asset-rotation defaults come from
/// `Model::default` and the camera (zoom/pan) defaults from
/// `Camera::default`, so the CLI and the GUI can never drift apart.
pub fn help() -> String {
    let model = Model::default();
    let cam = Camera::default();
    format!(
        "unity-viewer — take a headless screenshot of a mesh with a material

Usage:
  unity-viewer <mesh> <material> [options]

Arguments:
  <mesh>            Path to a .asset mesh, or its name inside assets/
  <material>        Path to a PNG, or its name inside images/ or output/
                    (use 'none' to render without a material)

Options:
      --rotation <deg>   Model yaw in degrees: turntable around world up
                         (default {rotation})
      --pitch <deg>      Model pitch in degrees: tilt of the asset
                         (default {pitch})
      --roll <deg>       Model roll in degrees: twist in the asset's plane
                         (default {roll})
      --config <path>    Load model/camera settings from a JSON file (the
                         GUI's Import/Export format); explicit flags
                         override the file's values
      --zoom <factor>    Camera zoom factor (default {zoom}; 1.0 = fitted
                         framing)
      --width <px>       Output width in pixels (default {DEFAULT_WIDTH})
      --height <px>      Output height in pixels (default {DEFAULT_HEIGHT})
      --out <path>       Output PNG path (default <mesh-stem>.png)
  -h, --help             Show this help

The camera keeps its fixed default viewing pose; the rotation options turn
the asset itself so the fixed world-space lights land where you want them.

Examples:
  unity-viewer CardPackStatic_Mesh Cardback
  unity-viewer CardPackStatic_Mesh Cardback --rotation -30 --zoom 1.2
  unity-viewer assets/CardPack_Mesh.asset images/Cardback.png \\
      --rotation 20 --zoom 0.9 --pitch 10 --out /tmp/shot.png
",
        rotation = fmt_deg(model.yaw),
        pitch = fmt_deg(model.pitch),
        roll = fmt_deg(model.roll),
        zoom = cam.zoom,
    )
}

#[derive(Debug)]
struct Options {
    mesh: String,
    material: Option<String>,
    rotation: f32,
    pitch: f32,
    roll: f32,
    zoom: f32,
    width: u32,
    height: u32,
    out: PathBuf,
}

/// Run the CLI, given the arguments after the program name.
pub fn run(args: &[String]) -> Result<(), String> {
    let opts = parse(args)?;

    let mesh_path = resolve_mesh(&opts.mesh)?;
    let material_path = match &opts.material {
        Some(name) => Some(resolve_material(name)?),
        None => None,
    };

    let mesh = Mesh::from_file(&mesh_path).map_err(|e| e.to_string())?;
    let material = match material_path {
        Some(p) => Some(Material::from_file(&p)?),
        None => None,
    };

    eprintln!(
        "mesh: {} ({} vertices, {} triangles{})",
        mesh.name,
        mesh.vertices.len(),
        mesh.indices.len() / 3,
        if mesh.is_skinned {
            format!(", skinned with {} bones (bind pose)", mesh.bone_count)
        } else {
            String::new()
        }
    );
    eprintln!(
        "material: {}",
        material
            .as_ref()
            .map(|m| format!("{}x{}", m.width, m.height))
            .unwrap_or_else(|| "(none)".to_string())
    );

    // The camera keeps the GUI's fixed viewing pose (only the zoom
    // changes); the asset rotation is separate, so the fixed world-space
    // lights can be aimed at any face.
    let camera = Camera {
        zoom: opts.zoom,
        ..Camera::default()
    };
    let rotation = Model {
        yaw: opts.rotation * DEG,
        pitch: opts.pitch * DEG,
        roll: opts.roll * DEG,
    };
    let primitive = Primitive {
        mesh: Some(Arc::new(mesh)),
        material,
        camera,
        rotation,
    };

    let runtime = tokio::runtime::Builder::new_current_thread()
        .enable_io()
        .enable_time()
        .build()
        .map_err(|e| format!("failed to start tokio runtime: {e}"))?;

    runtime.block_on(async move {
        let (width, height) = (opts.width, opts.height);

        let instance = wgpu::Instance::new(wgpu::InstanceDescriptor {
            backends: wgpu::Backends::from_env().unwrap_or(wgpu::Backends::PRIMARY),
            flags: wgpu::InstanceFlags::empty(),
            ..wgpu::InstanceDescriptor::new_without_display_handle()
        });

        let adapter = instance
            .request_adapter(&wgpu::RequestAdapterOptions {
                power_preference: wgpu::PowerPreference::HighPerformance,
                force_fallback_adapter: false,
                compatible_surface: None,
                apply_limit_buckets: false,
            })
            .await
            .map_err(|e| format!("no GPU adapter available: {e}"))?;
        eprintln!("adapter: {}", adapter.get_info().name);

        let (device, queue) = adapter
            .request_device(&wgpu::DeviceDescriptor {
                label: Some("unity-viewer [cli]"),
                required_features: wgpu::Features::empty(),
                required_limits: wgpu::Limits::default(),
                experimental_features: wgpu::ExperimentalFeatures::disabled(),
                memory_hints: wgpu::MemoryHints::MemoryUsage,
                trace: wgpu::Trace::Off,
            })
            .await
            .map_err(|e| format!("failed to create device: {e}"))?;

        // sRGB target so the readback bytes can be written straight to PNG.
        let format = wgpu::TextureFormat::Rgba8UnormSrgb;
        let mut pipeline = Pipeline::create(&device, &queue, format);

        let size = iced::Size::new(width, height);
        let aspect = (width as f32 / height.max(1) as f32).max(1e-4);
        let clip = iced::Rectangle {
            x: 0,
            y: 0,
            width,
            height,
        };
        pipeline.prepare(&device, &queue, &primitive, &clip, size, aspect);

        let texture = device.create_texture(&wgpu::TextureDescriptor {
            label: Some("screenshot target"),
            size: wgpu::Extent3d {
                width,
                height,
                depth_or_array_layers: 1,
            },
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::COPY_SRC,
            view_formats: &[],
        });
        let target = texture.create_view(&wgpu::wgt::TextureViewDescriptor {
            label: None,
            format: None,
            dimension: None,
            usage: None,
            aspect: wgpu::TextureAspect::All,
            base_mip_level: 0,
            mip_level_count: Some(1),
            base_array_layer: 0,
            array_layer_count: Some(1),
        });

        // The scene renders into the pipeline's offscreen MSAA targets and
        // blits the result onto this transparent target, so the PNG's alpha
        // channel isolates the mesh and composites cleanly onto any
        // background.
        let mut encoder =
            device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        primitive.draw_frame(
            &pipeline,
            &mut encoder,
            &target,
            &Rectangle {
                x: 0,
                y: 0,
                width,
                height,
            },
        );

        // Read the rendered texture back into a buffer. `copy_texture_to_buffer`
        // requires `bytes_per_row` to be a multiple of 256, so rows are padded.
        let row_bytes = width as u64 * 4;
        let row_stride = (row_bytes + 255) / 256 * 256;
        let buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("screenshot readback"),
            size: row_stride * height as u64,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        encoder.copy_texture_to_buffer(
            texture.as_image_copy(),
            wgpu::TexelCopyBufferInfo {
                buffer: &buffer,
                layout: wgpu::TexelCopyBufferLayout {
                    offset: 0,
                    bytes_per_row: Some(row_stride as u32),
                    rows_per_image: None,
                },
            },
            wgpu::Extent3d {
                width,
                height,
                depth_or_array_layers: 1,
            },
        );
        let submission = queue.submit([encoder.finish()]);

        let slice = buffer.slice(..);
        slice.map_async(wgpu::MapMode::Read, |_| {});
        device
            .poll(wgpu::PollType::Wait {
                submission_index: Some(submission),
                timeout: None,
            })
            .map_err(|e| format!("timed out waiting for the render to complete: {e}"))?;
        let mapped = slice
            .get_mapped_range()
            .map_err(|e| format!("failed to map the readback buffer: {e}"))?;

        // Strip the per-row padding.
        let mut rgba = Vec::with_capacity((row_bytes * height as u64) as usize);
        for y in 0..height {
            let start = (y as u64 * row_stride) as usize;
            rgba.extend_from_slice(&mapped[start..start + row_bytes as usize]);
        }

        // The MSAA-resolved silhouette edges are premultiplied by sample
        // coverage (the resolve averages the drawn color against the
        // transparent clear), but PNGs store straight alpha: divide the
        // partially covered pixels back out.
        for px in rgba.chunks_mut(4) {
            let a = px[3];
            if a > 0 && a < 255 {
                for c in 0..3 {
                    px[c] = (px[c] as u32 * 255 / a as u32).min(255) as u8;
                }
            }
        }

        save_png(&opts.out, width, height, &rgba)?;
        eprintln!("saved: {} ({}x{})", opts.out.display(), width, height);
        Ok(())
    })
}

fn save_png(path: &Path, width: u32, height: u32, rgba: &[u8]) -> std::result::Result<(), String> {
    // Encode as PNG explicitly: the output is a PNG no matter what
    // extension (or lack of one) the path carries.
    image::save_buffer_with_format(
        path,
        rgba,
        width,
        height,
        image::ExtendedColorType::Rgba8,
        image::ImageFormat::Png,
    )
    .map_err(|e| format!("failed to write {}: {e}", path.display()))
}

// --- argument parsing ------------------------------------------------------

fn parse(args: &[String]) -> Result<Options, String> {
    let mut positional: Vec<String> = Vec::new();
    let mut rotation: Option<f32> = None;
    let mut zoom: Option<f32> = None;
    let mut pitch: Option<f32> = None;
    let mut roll: Option<f32> = None;
    let mut width: u32 = DEFAULT_WIDTH;
    let mut height: u32 = DEFAULT_HEIGHT;
    let mut out: Option<PathBuf> = None;

    let mut config_path: Option<PathBuf> = None;

    let mut i = 0;
    while i < args.len() {
        let arg = args[i].as_str();
        // Accept both `--flag value` and `--flag=value`.
        let (flag, inline) = match arg.split_once('=') {
            Some((f, v)) if f.starts_with('-') => (f, Some(v)),
            _ => (arg, None),
        };
        match flag {
            "-h" | "--help" => {
                print!("{}", help());
                std::process::exit(0);
            }
            "--rotation" => {
                rotation = Some(parse_num(flag_value(args, &mut i, flag, inline)?, flag)?)
            }
            "--zoom" => zoom = Some(parse_num(flag_value(args, &mut i, flag, inline)?, flag)?),
            "--pitch" => pitch = Some(parse_num(flag_value(args, &mut i, flag, inline)?, flag)?),
            "--roll" => roll = Some(parse_num(flag_value(args, &mut i, flag, inline)?, flag)?),
            "--config" => {
                config_path = Some(PathBuf::from(flag_value(args, &mut i, flag, inline)?))
            }
            "--width" => width = parse_num(flag_value(args, &mut i, flag, inline)?, flag)?,
            "--height" => height = parse_num(flag_value(args, &mut i, flag, inline)?, flag)?,
            "--out" => out = Some(PathBuf::from(flag_value(args, &mut i, flag, inline)?)),
            f if f.starts_with('-') => {
                return Err(format!("unknown option {f} (see --help)"));
            }
            _ => positional.push(arg.to_string()),
        }
        i += 1;
    }

    let mesh = positional
        .get(0)
        .cloned()
        .ok_or_else(|| "missing <mesh> argument (see --help)".to_string())?;
    let material = match positional.get(1) {
        Some(m) if !m.eq_ignore_ascii_case("none") && m != "-" => Some(m.clone()),
        Some(_) => None,
        None => {
            return Err(
                "missing <material> argument (use 'none' for no material; see --help)".to_string(),
            );
        }
    };
    // Precedence: explicit flag > --config file > the GUI's defaults
    // (neutral asset pose, fixed camera with its default zoom).
    let config = config_path
        .as_ref()
        .map(|path| Config::load(path))
        .transpose()?;
    let angles = config.as_ref().map(|c| c.model).unwrap_or_default();
    let default = Camera::default();
    let rotation = rotation.unwrap_or(angles.yaw);
    let pitch = pitch.unwrap_or(angles.pitch);
    let roll = roll.unwrap_or(angles.roll);
    let zoom = zoom
        .unwrap_or(config.map(|c| c.camera.zoom).unwrap_or(default.zoom));
    if zoom <= 0.0 {
        return Err("--zoom must be greater than 0".to_string());
    }
    if width == 0 || height == 0 {
        return Err("--width and --height must be greater than 0".to_string());
    }

    let out = out.unwrap_or_else(|| {
        let stem = Path::new(&mesh)
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("screenshot");
        PathBuf::from(format!("{stem}.png"))
    });

    Ok(Options {
        mesh,
        material,
        rotation,
        pitch,
        roll,
        zoom,
        width,
        height,
        out,
    })
}

/// Value of `--flag`: the inline `=value` part, or the next argument.
fn flag_value(
    args: &[String],
    i: &mut usize,
    flag: &str,
    inline: Option<&str>,
) -> Result<String, String> {
    match inline {
        Some(v) => Ok(v.to_string()),
        None => {
            *i += 1;
            args.get(*i)
                .cloned()
                .ok_or_else(|| format!("{flag} requires a value"))
        }
    }
}

fn parse_num<T>(s: String, flag: &str) -> Result<T, String>
where
    T: std::str::FromStr,
    T::Err: std::fmt::Display,
{
    s.parse::<T>()
        .map_err(|e: T::Err| format!("{flag} expects a number, got {s:?} ({e})"))
}

// --- path resolution -------------------------------------------------------

fn resolve_mesh(name: &str) -> Result<PathBuf, String> {
    // Accept a full path (cwd- or repo-root-relative) or a bare mesh name.
    let candidates = [
        Path::new(name).to_path_buf(),
        Path::new(ROOT).join(name),
        Path::new(ASSETS_DIR).join(name),
        Path::new(ASSETS_DIR).join(format!("{name}.asset")),
    ];
    candidates
        .iter()
        .find(|p| p.is_file())
        .cloned()
        .ok_or_else(|| format!("mesh not found: {name} (tried the given path and {ASSETS_DIR}/)"))
}

fn resolve_material(name: &str) -> Result<PathBuf, String> {
    // Accept a full path (cwd- or repo-root-relative) or a bare texture name.
    let mut candidates = vec![
        Path::new(name).to_path_buf(),
        Path::new(ROOT).join(name),
        Path::new(IMAGES_DIR).join(name),
        Path::new(IMAGES_DIR).join(format!("{name}.png")),
    ];
    // Per-pack textures: output/<bundle>/<name>.png
    if let Ok(rd) = std::fs::read_dir(OUTPUT_DIR) {
        for e in rd.flatten() {
            let dir = e.path();
            if !dir.is_dir() {
                continue;
            }
            candidates.push(dir.join(name));
            candidates.push(dir.join(format!("{name}.png")));
        }
    }
    candidates
        .into_iter()
        .find(|p| p.is_file())
        .ok_or_else(|| {
            format!(
                "material not found: {name} (tried the given path, {IMAGES_DIR}/ and {OUTPUT_DIR}/*/; pass a full path or use 'none')"
            )
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parse3(s: &str) -> Result<Options, String> {
        let args: Vec<String> = s.split_whitespace().map(String::from).collect();
        parse(&args)
    }

    #[test]
    fn parses_basic_invocation() {
        let o = parse3("mesh.asset texture.png --rotation -30 --zoom 1.2").unwrap();
        assert_eq!(o.mesh, "mesh.asset");
        assert_eq!(o.material.as_deref(), Some("texture.png"));
        assert!((o.rotation - (-30.0)).abs() < 1e-3);
        assert!((o.zoom - 1.2).abs() < 1e-3);
        assert!((o.pitch - Model::default().pitch * to_deg()).abs() < 1e-3);
        assert!((o.roll - Model::default().roll * to_deg()).abs() < 1e-3);
        assert_eq!((o.width, o.height), (DEFAULT_WIDTH, DEFAULT_HEIGHT));
        assert_eq!(o.out, PathBuf::from("mesh.png"));
    }

    #[test]
    fn material_none_is_accepted() {
        let o = parse3("m none --rotation 0 --zoom 1").unwrap();
        assert!(o.material.is_none());
    }

    #[test]
    fn asset_defaults_match_the_gui() {
        let o = parse3("m t").unwrap();
        let model = Model::default();
        let cam = Camera::default();
        let d = to_deg();
        // The asset rotation defaults to the neutral pose (the GUI's Model
        // section at zero), the zoom to the GUI's fixed camera.
        assert!((o.rotation - model.yaw * d).abs() < 1e-3);
        assert!((o.pitch - model.pitch * d).abs() < 1e-3);
        assert!((o.roll - model.roll * d).abs() < 1e-3);
        assert!((o.zoom - cam.zoom).abs() < 1e-3);
    }

    #[test]
    fn inline_equals_form() {
        let o = parse3("m t --rotation=10 --zoom=2 --pitch=5 --width=800 --height=600 --out=x.png")
            .unwrap();
        assert!((o.rotation - 10.0).abs() < 1e-3);
        assert!((o.zoom - 2.0).abs() < 1e-3);
        assert!((o.pitch - 5.0).abs() < 1e-3);
        assert_eq!((o.width, o.height), (800, 600));
        assert_eq!(o.out, PathBuf::from("x.png"));
    }

    fn write_temp_config(name: &str, json: &str) -> String {
        let path = std::env::temp_dir().join(format!(
            "unity-viewer-cli-config-{name}-{}.json",
            std::process::id()
        ));
        std::fs::write(&path, json).expect("write temp config");
        path.to_string_lossy().into_owned()
    }

    #[test]
    fn config_file_provides_defaults_and_flags_override() {
        let json = r#"{"model":{"yaw":30.0,"pitch":10.0,"roll":-5.0},"camera":{"zoom":1.5,"pan":[1.0,2.0,3.0]}}"#;
        let path = write_temp_config("defaults", json);
        let o = parse3(&format!("m t --config {path}")).unwrap();
        assert!((o.rotation - 30.0).abs() < 1e-3);
        assert!((o.pitch - 10.0).abs() < 1e-3);
        assert!((o.roll - (-5.0)).abs() < 1e-3);
        assert!((o.zoom - 1.5).abs() < 1e-3);
        // Explicit flags win over the file; unspecified values still come
        // from the file.
        let o = parse3(&format!("m t --config {path} --rotation 90 --zoom 2")).unwrap();
        assert!((o.rotation - 90.0).abs() < 1e-3);
        assert!((o.zoom - 2.0).abs() < 1e-3);
        assert!((o.pitch - 10.0).abs() < 1e-3);
        std::fs::remove_file(&path).ok();
    }

    #[test]
    fn missing_config_file_is_an_error() {
        let e = parse3("m t --config /nonexistent/uv-config.json").unwrap_err();
        assert!(e.contains("/nonexistent/uv-config.json"), "{e}");
    }
}
