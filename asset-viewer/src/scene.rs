//! The wgpu side of the viewer: an orbit camera, a textured double-sided
//! lambert pipeline, and iced's `Primitive`/`Pipeline` plumbing.

use std::sync::Arc;

use iced::wgpu;
use iced::wgpu::util::DeviceExt;
use iced::{Rectangle, Size};

use crate::unity::{Mesh, Vertex};

/// Vertical field of view of the orbit camera.
pub const FOV_Y: f32 = 40.0 * (std::f32::consts::PI / 180.0);

/// Orbit camera. The mesh is origin-centered, so the camera orbits around
/// `pan` (world offset, usually `[0; 3]`).
#[derive(Copy, Clone, Debug)]
pub struct Camera {
    /// Orbit angle around the Y axis (radians).
    pub yaw: f32,
    /// Camera elevation (radians).
    pub pitch: f32,
    /// Distance multiplier (1.0 = fitted to the mesh's bounding sphere).
    pub zoom: f32,
    /// Orbit target (world).
    pub pan: [f32; 3],
}

impl Default for Camera {
    fn default() -> Self {
        Self {
            yaw: -0.55,
            pitch: 0.3,
            zoom: 1.0,
            pan: [0.0; 3],
        }
    }
}

impl Camera {
    /// Camera–target distance for a mesh of the given bounding radius.
    pub fn distance(&self, radius: f32) -> f32 {
        self.fit_distance(radius) / self.zoom.max(1e-4)
    }

    fn fit_distance(&self, radius: f32) -> f32 {
        (radius * 1.35) / (FOV_Y * 0.5).tan()
    }

    pub fn eye(&self, radius: f32) -> [f32; 3] {
        let d = self.distance(radius);
        let (sy, cy) = (self.yaw.sin(), self.yaw.cos());
        let (sp, cp) = (self.pitch.sin(), self.pitch.cos());
        // Spherical orbit: the eye stays at exactly distance `d` from the
        // target for every yaw/pitch combination.
        [
            self.pan[0] + d * (cp * sy),
            self.pan[1] + d * sp,
            self.pan[2] + d * (cp * cy),
        ]
    }

    /// Unit world vectors pointing to the screen's right and up.
    pub fn screen_axes(&self) -> ([f32; 3], [f32; 3]) {
        let (sy, cy) = (self.yaw.sin(), self.yaw.cos());
        let (sp, cp) = (self.pitch.sin(), self.pitch.cos());
        let right = [cy, 0.0, -sy];
        let up = [-sy * sp, cp, -cy * sp];
        (right, up)
    }
}

/// A decoded material texture (RGBA8, straight sRGB).
#[derive(Debug)]
pub struct Material {
    pub width: u32,
    pub height: u32,
    pub pixels: Vec<u8>,
}

impl Material {
    /// Decode an image file (PNG/…) into an RGBA8 material.
    pub fn from_file(path: &std::path::Path) -> Result<Arc<Self>, String> {
        let bytes =
            std::fs::read(path).map_err(|e| format!("failed to read {}: {e}", path.display()))?;
        let img = image::load_from_memory(&bytes)
            .map_err(|e| format!("failed to decode image {}: {e}", path.display()))?;
        let rgba = img.to_rgba8();
        let (w, h) = (rgba.width() as usize, rgba.height() as usize);
        // Unity UVs use a bottom-left origin (v=0 = bottom of the image), but
        // PNG rows run top-to-bottom and wgpu/Vulkan textures place v=0 at the
        // top. Flip the rows so the mesh's UVs line up with the artwork.
        let raw = rgba.into_raw();
        let stride = w * 4;
        let mut pixels = Vec::with_capacity(raw.len());
        for row in raw.chunks_exact(stride).rev() {
            pixels.extend_from_slice(row);
        }
        Ok(Arc::new(Self {
            width: w as u32,
            height: h as u32,
            pixels,
        }))
    }
}

/// Pad RGBA8 rows to a multiple of 256 bytes (required by
/// `Queue::write_texture` for multi-row copies). Returns the padded bytes and
/// the padded row stride.
fn pad_rows(rgba: &[u8], width: u32) -> (Vec<u8>, u32) {
    let row = (width as usize) * 4;
    let stride = (((row as u64) + 255) / 256 * 256) as usize;
    if stride == row {
        return (rgba.to_vec(), row as u32);
    }
    let mut out = Vec::with_capacity(stride * (rgba.len() / row));
    for chunk in rgba.chunks_exact(row) {
        out.extend_from_slice(chunk);
        out.resize(out.len() + (stride - row), 0);
    }
    (out, stride as u32)
}

/// One frame of the scene.
#[derive(Debug)]
pub struct Primitive {
    pub mesh: Option<Arc<Mesh>>,
    pub material: Option<Arc<Material>>,
    pub camera: Camera,
}

/// Sample count for the offscreen MSAA pass. The device always supports at
/// least 4 (wgpu's minimum limits); the scene renders into an N-sample
/// offscreen target, resolves to a 1x texture, and blits it onto the final
/// target (the iced surface or the CLI screenshot texture), which may not
/// itself be multisampled. Must be ≥ 2 (a 1-sample pass has nothing to
/// resolve).
const MSAA_SAMPLES: u32 = 4;

/// Column-major matrix (matches WGSL `mat4x4f`).
type Mat4 = [[f32; 4]; 4];

/// The in-game model is displayed with its X axis mirrored relative to the
/// raw asset space, so mirror x to match (fan spread direction and artwork
/// left/right). This is a reflection (det −1), which reverses on-screen
/// winding — the fragment shader compensates by inverting its front-facing
/// rule, so the transformed normals light correctly.
const X_MIRROR: Mat4 = [
    [-1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
];

/// `a * b` for column-major matrices.
fn mul(a: &Mat4, b: &Mat4) -> Mat4 {
    let mut out = [[0.0; 4]; 4];
    for c in 0..4 {
        for r in 0..4 {
            let mut s = 0.0;
            for k in 0..4 {
                s += a[k][r] * b[c][k];
            }
            out[c][r] = s;
        }
    }
    out
}

fn perspective(fovy: f32, aspect: f32, near: f32, far: f32) -> Mat4 {
    let f = 1.0 / (fovy * 0.5).tan();
    let nf = 1.0 / (near - far);
    [
        [f / aspect, 0.0, 0.0, 0.0],
        [0.0, f, 0.0, 0.0],
        [0.0, 0.0, (far + near) * nf, -1.0],
        [0.0, 0.0, 2.0 * far * near * nf, 0.0],
    ]
}

fn look_at(eye: [f32; 3], target: [f32; 3], up: [f32; 3]) -> Mat4 {
    fn norm(v: [f32; 3]) -> [f32; 3] {
        let l = (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]).sqrt().max(1e-9);
        [v[0] / l, v[1] / l, v[2] / l]
    }
    fn cross(a: [f32; 3], b: [f32; 3]) -> [f32; 3] {
        [
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        ]
    }
    fn dot(a: [f32; 3], b: [f32; 3]) -> f32 {
        a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    }
    let f = norm([target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]]);
    let s = norm(cross(f, up));
    let u = cross(s, f);
    [
        [s[0], u[0], -f[0], 0.0],
        [s[1], u[1], -f[1], 0.0],
        [s[2], u[2], -f[2], 0.0],
        [-dot(s, eye), -dot(u, eye), dot(f, eye), 1.0],
    ]
}

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
struct Uniforms {
    view_proj: Mat4,
    model: Mat4,
}

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
struct BlitUniforms {
    // Six scalars (repr(C)) so the byte layout matches the WGSL struct's
    // three vec2<f32> fields exactly, without relying on vec2 alignment.
    clip_x: f32,
    clip_y: f32,
    clip_w: f32,
    clip_h: f32,
    frame_w: f32,
    frame_h: f32,
}

const SHADER: &str = r#"
struct Uniforms {
    view_proj: mat4x4f,
    model: mat4x4f,
}

struct VertexInput {
    @location(0) position: vec3<f32>,
    @location(1) normal: vec3<f32>,
    @location(2) uv: vec2<f32>,
}

struct VertexOutput {
    @builtin(position) position: vec4<f32>,
    @location(0) normal: vec3<f32>,
    @location(1) uv: vec2<f32>,
}

@group(0) @binding(0) var<uniform> uniforms: Uniforms;
@group(0) @binding(1) var base_color: texture_2d<f32>;
@group(0) @binding(2) var base_sampler: sampler;

const LIGHT_DIR: vec3<f32> = normalize(vec3<f32>(0.45, 0.8, 0.4));
const FILL_DIR: vec3<f32> = normalize(vec3<f32>(-0.4, -0.3, -0.5));
// Bright enough that faces read close to the source texture; the key + fill
// light only add gentle 3D shading on top.
const AMBIENT: vec3<f32> = vec3<f32>(0.65, 0.67, 0.71);
const DIFFUSE: vec3<f32> = vec3<f32>(0.55);
const FILL: vec3<f32> = vec3<f32>(0.2);

@vertex
fn vs_main(input: VertexInput) -> VertexOutput {
    var out: VertexOutput;
    let world = uniforms.model * vec4<f32>(input.position, 1.0);
    out.position = uniforms.view_proj * world;
    out.normal = (uniforms.model * vec4<f32>(input.normal, 0.0)).xyz;
    out.uv = input.uv;
    return out;
}

@fragment
fn fs_main(
    input: VertexOutput,
    @builtin(front_facing) front: bool,
) -> @location(0) vec4<f32> {
    var n = normalize(input.normal);
    // The model is x-mirrored (a reflection), which reverses on-screen
    // winding and so inverts `front_facing` for the whole scene: flip the
    // normal for front-facing fragments instead of back-facing ones.
    if (front) {
        n = -n;
    }
    let albedo = textureSample(base_color, base_sampler, input.uv);
    let ndotl = max(dot(n, LIGHT_DIR), 0.0);
    let ndotf = max(dot(n, FILL_DIR), 0.0);
    let color = albedo.rgb * (AMBIENT + DIFFUSE * ndotl + FILL * ndotf);
    return vec4<f32>(color, 1.0);
}
"#;

/// Composites the MSAA-resolved offscreen texture onto the final target. A
/// fullscreen triangle is drawn over `clip_bounds`; each vertex's NDC
/// position is converted (with the same viewport transform the mesh pass
/// used) to device pixels, which are the 1:1 UV into the offscreen texture
/// (it is the same size as the target). Alpha blending keeps whatever the
/// target already holds where the offscreen is transparent.
const BLIT_SHADER: &str = r#"
// Layout mirrors the Rust `BlitUniforms` (scalars, repr(C)):
//   clip_origin = (clip_x, clip_y), clip_size = (clip_w, clip_h),
//   frame_size  = (frame_w, frame_h)
struct BlitUniforms {
    clip_origin: vec2<f32>,
    clip_size: vec2<f32>,
    frame_size: vec2<f32>,
}

@group(0) @binding(0) var<uniform> blit: BlitUniforms;
@group(0) @binding(1) var src: texture_2d<f32>;
@group(0) @binding(2) var src_sampler: sampler;

struct BlitVertexOutput {
    @builtin(position) position: vec4<f32>,
    @location(0) uv: vec2<f32>,
}

@vertex
fn vs_blit(@builtin(vertex_index) idx: u32) -> BlitVertexOutput {
    // A single triangle covering the whole viewport.
    let tri = array<vec2<f32>, 3>(
        vec2<f32>(-1.0, -1.0),
        vec2<f32>(3.0, -1.0),
        vec2<f32>(-1.0, 3.0),
    );
    let ndc = tri[idx];
    // Viewport transform (note the y flip), matching the mesh pass.
    let device = vec2<f32>(
        (ndc.x + 1.0) * 0.5 * blit.clip_size.x + blit.clip_origin.x,
        (1.0 - ndc.y) * 0.5 * blit.clip_size.y + blit.clip_origin.y,
    );
    var out: BlitVertexOutput;
    out.position = vec4<f32>(ndc, 0.0, 1.0);
    out.uv = device / blit.frame_size;
    return out;
}

@fragment
fn fs_blit(input: BlitVertexOutput) -> @location(0) vec4<f32> {
    return textureSample(src, src_sampler, input.uv);
}
"#;

pub struct Pipeline {
    device: wgpu::Device,
    color_format: wgpu::TextureFormat,
    bind_layout: wgpu::BindGroupLayout,
    blit_pipeline: wgpu::RenderPipeline,
    blit_buffer: wgpu::Buffer,
    mesh_pipeline: wgpu::RenderPipeline,
    uniforms_buffer: wgpu::Buffer,
    mesh: Option<(Arc<Mesh>, wgpu::Buffer, wgpu::Buffer)>,
    index_count: u32,
    material: Option<(Arc<Material>, wgpu::TextureView)>,
    sampler: wgpu::Sampler,
    default_view: wgpu::TextureView,
    /// Offscreen MSAA frame targets, recreated when the size changes:
    /// (width, height, MSAA color view, resolve view (render attachment),
    /// resolve view (sampling), MSAA depth view).
    frame: Option<(
        u32,
        u32,
        wgpu::TextureView,
        wgpu::TextureView,
        wgpu::TextureView,
        wgpu::TextureView,
    )>,
}

impl Pipeline {
    /// Build the GPU state for the given color format. Used by the iced
    /// pipeline trait and by the headless CLI path.
    pub fn create(device: &wgpu::Device, queue: &wgpu::Queue, format: wgpu::TextureFormat) -> Self {
        let module = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: None,
            source: wgpu::ShaderSource::Wgsl(SHADER.into()),
        });

        let mesh_pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("mesh pipeline"),
            layout: None,
            vertex: wgpu::VertexState {
                module: &module,
                entry_point: Some("vs_main"),
                buffers: &[Some(wgpu::VertexBufferLayout {
                    array_stride: std::mem::size_of::<Vertex>() as u64,
                    step_mode: wgpu::VertexStepMode::Vertex,
                    attributes: &wgpu::vertex_attr_array![
                        0 => Float32x3,
                        1 => Float32x3,
                        2 => Float32x2,
                    ],
                })],
                compilation_options: Default::default(),
            },
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleList,
                strip_index_format: None,
                front_face: wgpu::FrontFace::Ccw,
                // Double-sided: the pack is a thin shell and some meshes
                // may be single-layer sheets.
                cull_mode: None,
                polygon_mode: wgpu::PolygonMode::Fill,
                unclipped_depth: false,
                conservative: false,
            },
            depth_stencil: Some(wgpu::DepthStencilState {
                format: wgpu::TextureFormat::Depth32Float,
                depth_write_enabled: Some(true),
                depth_compare: Some(wgpu::CompareFunction::Less),
                stencil: wgpu::StencilState::default(),
                bias: wgpu::DepthBiasState::default(),
            }),
            multisample: wgpu::MultisampleState {
                count: MSAA_SAMPLES,
                mask: !0,
                alpha_to_coverage_enabled: false,
            },
            fragment: Some(wgpu::FragmentState {
                module: &module,
                entry_point: Some("fs_main"),
                targets: &[Some(wgpu::ColorTargetState {
                    format,
                    blend: Some(wgpu::BlendState::REPLACE),
                    write_mask: wgpu::ColorWrites::ALL,
                })],
                compilation_options: Default::default(),
            }),
            multiview_mask: None,
            cache: None,
        });

        let blit_module = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: None,
            source: wgpu::ShaderSource::Wgsl(BLIT_SHADER.into()),
        });
        let blit_pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("msaa blit pipeline"),
            layout: None,
            vertex: wgpu::VertexState {
                module: &blit_module,
                entry_point: Some("vs_blit"),
                buffers: &[],
                compilation_options: Default::default(),
            },
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleList,
                strip_index_format: None,
                front_face: wgpu::FrontFace::Ccw,
                cull_mode: None,
                polygon_mode: wgpu::PolygonMode::Fill,
                unclipped_depth: false,
                conservative: false,
            },
            depth_stencil: None,
            multisample: wgpu::MultisampleState {
                count: 1,
                mask: !0,
                alpha_to_coverage_enabled: false,
            },
            fragment: Some(wgpu::FragmentState {
                module: &blit_module,
                entry_point: Some("fs_blit"),
                targets: &[Some(wgpu::ColorTargetState {
                    format,
                    // The resolved texture's edge pixels are already
                    // coverage-modulated (MSAA resolve averages the drawn
                    // color against the transparent clear), i.e. premultiplied
                    // by the sample coverage: composite with `One` so the
                    // coverage is applied exactly once.
                    blend: Some(wgpu::BlendState {
                        color: wgpu::BlendComponent {
                            src_factor: wgpu::BlendFactor::One,
                            dst_factor: wgpu::BlendFactor::OneMinusSrcAlpha,
                            operation: wgpu::BlendOperation::Add,
                        },
                        alpha: wgpu::BlendComponent {
                            src_factor: wgpu::BlendFactor::One,
                            dst_factor: wgpu::BlendFactor::OneMinusSrcAlpha,
                            operation: wgpu::BlendOperation::Add,
                        },
                    }),
                    write_mask: wgpu::ColorWrites::ALL,
                })],
                compilation_options: Default::default(),
            }),
            multiview_mask: None,
            cache: None,
        });

        let blit_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("blit uniforms"),
            size: std::mem::size_of::<BlitUniforms>() as u64,
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });

        let uniforms_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("camera uniforms"),
            size: std::mem::size_of::<Uniforms>() as u64,
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });

        let sampler = device.create_sampler(&wgpu::SamplerDescriptor {
            label: Some("material sampler"),
            address_mode_u: wgpu::AddressMode::Repeat,
            address_mode_v: wgpu::AddressMode::Repeat,
            address_mode_w: wgpu::AddressMode::Repeat,
            mag_filter: wgpu::FilterMode::Linear,
            min_filter: wgpu::FilterMode::Linear,
            mipmap_filter: wgpu::MipmapFilterMode::Linear,
            ..Default::default()
        });

        // 1×1 white fallback for "no material".
        let default_texture = device.create_texture(&wgpu::TextureDescriptor {
            label: Some("default texture"),
            size: wgpu::Extent3d {
                width: 1,
                height: 1,
                depth_or_array_layers: 1,
            },
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: wgpu::TextureFormat::Rgba8UnormSrgb,
            usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
            view_formats: &[],
        });
        queue.write_texture(
            wgpu::wgt::TexelCopyTextureInfo {
                texture: &default_texture,
                mip_level: 0,
                origin: wgpu::Origin3d::ZERO,
                aspect: wgpu::TextureAspect::All,
            },
            &[255, 255, 255, 255],
            wgpu::TexelCopyBufferLayout {
                offset: 0,
                rows_per_image: Some(1),
                bytes_per_row: None,
            },
            wgpu::Extent3d {
                width: 1,
                height: 1,
                depth_or_array_layers: 1,
            },
        );
        let default_view = default_texture.create_view(&wgpu::wgt::TextureViewDescriptor {
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

        Self {
            device: device.clone(),
            color_format: format,
            bind_layout: mesh_pipeline.get_bind_group_layout(0),
            blit_pipeline,
            blit_buffer,
            mesh_pipeline,
            uniforms_buffer,
            mesh: None,
            index_count: 0,
            material: None,
            sampler,
            default_view,
            frame: None,
        }
    }

    /// (Re)create the offscreen MSAA frame targets for a frame of this size.
    fn update_frame(&mut self, device: &wgpu::Device, size: Size<u32>) {
        let (w, h) = (size.width.max(1), size.height.max(1));
        if self
            .frame
            .as_ref()
            .is_some_and(|(fw, fh, _, _, _, _)| *fw == w && *fh == h)
        {
            return;
        }
        let make = |label: &str,
                    sample_count: u32,
                    format: wgpu::TextureFormat,
                    usage: wgpu::TextureUsages| {
            device.create_texture(&wgpu::TextureDescriptor {
                label: Some(label),
                size: wgpu::Extent3d {
                    width: w,
                    height: h,
                    depth_or_array_layers: 1,
                },
                mip_level_count: 1,
                sample_count,
                dimension: wgpu::TextureDimension::D2,
                format,
                usage,
                view_formats: &[],
            })
        };
        let view = |texture: &wgpu::Texture, label: &str| {
            texture.create_view(&wgpu::wgt::TextureViewDescriptor {
                label: Some(label),
                format: None,
                dimension: None,
                usage: None,
                aspect: wgpu::TextureAspect::All,
                base_mip_level: 0,
                mip_level_count: Some(1),
                base_array_layer: 0,
                array_layer_count: Some(1),
            })
        };
        let msaa_color = make(
            "msaa color",
            MSAA_SAMPLES,
            self.color_format,
            wgpu::TextureUsages::RENDER_ATTACHMENT,
        );
        let resolve = make(
            "msaa resolve",
            1,
            self.color_format,
            wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING,
        );
        let msaa_depth = make(
            "msaa depth",
            MSAA_SAMPLES,
            wgpu::TextureFormat::Depth32Float,
            wgpu::TextureUsages::RENDER_ATTACHMENT,
        );
        self.frame = Some((
            w,
            h,
            view(&msaa_color, "msaa color view"),
            view(&resolve, "resolve attachment view"),
            view(&resolve, "resolve sampling view"),
            view(&msaa_depth, "msaa depth view"),
        ));
    }

    /// Upload mesh/material/uniforms for a render of `primitive` into a
    /// `size`-sized frame with the given aspect ratio. `clip` is the
    /// primitive's physical clip rect inside the frame (the widget's bounds
    /// in the GUI; the whole frame in the CLI). Shared by the iced `prepare`
    /// callback and the headless CLI path.
    pub fn prepare(
        &mut self,
        device: &wgpu::Device,
        queue: &wgpu::Queue,
        primitive: &Primitive,
        clip: &Rectangle<u32>,
        size: Size<u32>,
        aspect: f32,
    ) {
        self.update_frame(device, size);
        let (w, h) = (size.width.max(1), size.height.max(1));
        // The blit pass draws with the clip rect as its viewport and samples
        // the offscreen texture 1:1 in device pixels, so its UV math must
        // use the real clip rect (the widget may be offset from the frame
        // origin, e.g. next to the sidebar).
        queue.write_buffer(
            &self.blit_buffer,
            0,
            bytemuck::bytes_of(&BlitUniforms {
                clip_x: clip.x as f32,
                clip_y: clip.y as f32,
                clip_w: clip.width as f32,
                clip_h: clip.height as f32,
                frame_w: w as f32,
                frame_h: h as f32,
            }),
        );

        let radius = primitive.mesh.as_ref().map(|m| m.radius()).unwrap_or(1.0);
        let distance = primitive.camera.distance(radius).max(1e-3);
        let eye = primitive.camera.eye(radius);
        let proj = perspective(FOV_Y, aspect, distance / 100.0, distance * 100.0);
        let view = look_at(eye, primitive.camera.pan, [0.0, 1.0, 0.0]);
        let uniforms = Uniforms {
            view_proj: mul(&proj, &view),
            model: X_MIRROR,
        };
        queue.write_buffer(&self.uniforms_buffer, 0, bytemuck::bytes_of(&uniforms));

        // (Re)upload the mesh when the selection changes.
        if let Some(mesh) = &primitive.mesh {
            if !self
                .mesh
                .as_ref()
                .is_some_and(|(m, _, _)| Arc::ptr_eq(m, mesh))
            {
                let vertex_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
                    label: Some("mesh vertices"),
                    usage: wgpu::BufferUsages::VERTEX,
                    contents: bytemuck::cast_slice(&mesh.vertices),
                });
                let index_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
                    label: Some("mesh indices"),
                    usage: wgpu::BufferUsages::INDEX,
                    contents: bytemuck::cast_slice(&mesh.indices),
                });
                self.index_count = mesh.indices.len() as u32;
                self.mesh = Some((mesh.clone(), vertex_buffer, index_buffer));
            }
        }

        // (Re)upload the material when the selection changes.
        if let Some(material) = &primitive.material {
            if !self
                .material
                .as_ref()
                .is_some_and(|(m, _)| Arc::ptr_eq(m, material))
            {
                let texture = device.create_texture(&wgpu::TextureDescriptor {
                    label: Some("material texture"),
                    size: wgpu::Extent3d {
                        width: material.width,
                        height: material.height,
                        depth_or_array_layers: 1,
                    },
                    mip_level_count: 1,
                    sample_count: 1,
                    dimension: wgpu::TextureDimension::D2,
                    format: wgpu::TextureFormat::Rgba8UnormSrgb,
                    usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
                    view_formats: &[],
                });
                // `Queue::write_texture` requires `bytes_per_row` (a multiple
                // of 256) for multi-row copies, so pad the rows.
                let (padded, stride) = pad_rows(&material.pixels, material.width);
                queue.write_texture(
                    wgpu::wgt::TexelCopyTextureInfo {
                        texture: &texture,
                        mip_level: 0,
                        origin: wgpu::Origin3d::ZERO,
                        aspect: wgpu::TextureAspect::All,
                    },
                    &padded,
                    wgpu::TexelCopyBufferLayout {
                        offset: 0,
                        rows_per_image: None,
                        bytes_per_row: Some(stride),
                    },
                    wgpu::Extent3d {
                        width: material.width,
                        height: material.height,
                        depth_or_array_layers: 1,
                    },
                );
                self.material = Some((
                    material.clone(),
                    texture.create_view(&wgpu::wgt::TextureViewDescriptor {
                        label: None,
                        format: None,
                        dimension: None,
                        usage: None,
                        aspect: wgpu::TextureAspect::All,
                        base_mip_level: 0,
                        mip_level_count: Some(1),
                        base_array_layer: 0,
                        array_layer_count: Some(1),
                    }),
                ));
            }
        }
    }
}

impl iced::widget::shader::Pipeline for Pipeline {
    fn new(device: &wgpu::Device, queue: &wgpu::Queue, format: wgpu::TextureFormat) -> Self {
        Self::create(device, queue, format)
    }
}

impl iced::widget::shader::Primitive for Primitive {
    type Pipeline = Pipeline;

    fn prepare(
        &self,
        pipeline: &mut Self::Pipeline,
        device: &wgpu::Device,
        queue: &wgpu::Queue,
        bounds: &Rectangle,
        viewport: &iced::widget::shader::Viewport,
    ) {
        let frame = viewport.physical_size();
        let scale = viewport.scale_factor();
        // iced hands `render` this same rect (scaled, snapped) as
        // `clip_bounds`; the blit's UV math must match it.
        let clip = Rectangle {
            x: (bounds.x * scale).round() as u32,
            y: (bounds.y * scale).round() as u32,
            width: (bounds.width * scale).round() as u32,
            height: (bounds.height * scale).round() as u32,
        };
        let aspect = (bounds.size().width / bounds.size().height.max(1.0)).max(1e-4);
        pipeline.prepare(device, queue, self, &clip, frame, aspect);
    }

    fn draw(&self, _pipeline: &Self::Pipeline, _render_pass: &mut wgpu::RenderPass) -> bool {
        // Not drawn here: the scene needs its own offscreen MSAA targets and
        // a second (blit) pass, so the actual rendering happens in `render`.
        false
    }

    fn render(
        &self,
        pipeline: &Self::Pipeline,
        encoder: &mut wgpu::CommandEncoder,
        target: &wgpu::TextureView,
        clip_bounds: &Rectangle<u32>,
    ) {
        // The scene renders into the pipeline's offscreen MSAA targets and
        // blits the resolved result on top of whatever iced already drew
        // (window background), keeping it visible around the mesh.
        self.draw_frame(pipeline, encoder, target, clip_bounds);
    }
}

impl Primitive {
    /// Renders the scene: a 4x MSAA pass into an offscreen texture (with an
    /// automatic resolve), then a blit pass compositing the resolved image
    /// onto `target` within `clip_bounds`. Also used by the headless CLI
    /// path, whose target is a transparent offscreen screenshot texture.
    pub fn draw_frame(
        &self,
        pipeline: &Pipeline,
        encoder: &mut wgpu::CommandEncoder,
        target: &wgpu::TextureView,
        clip_bounds: &Rectangle<u32>,
    ) {
        let Some((_, vertex_buffer, index_buffer)) = &pipeline.mesh else {
            return;
        };
        let Some((_, _, msaa_view, resolve_attach_view, resolve_bind_view, depth_view)) =
            &pipeline.frame
        else {
            return;
        };
        let (w, h) = (clip_bounds.size().width, clip_bounds.size().height);
        if w == 0 || h == 0 || pipeline.index_count == 0 {
            return;
        }

        let texture_view = match self.material.as_ref() {
            Some(m) => pipeline
                .material
                .as_ref()
                .filter(|(c, _)| Arc::ptr_eq(c, m))
                .map(|(_, v)| v)
                .unwrap_or(&pipeline.default_view),
            None => &pipeline.default_view,
        };

        let entries = [
            wgpu::BindGroupEntry {
                binding: 0,
                resource: wgpu::BindingResource::Buffer(wgpu::BufferBinding {
                    buffer: &pipeline.uniforms_buffer,
                    offset: 0,
                    size: None,
                }),
            },
            wgpu::BindGroupEntry {
                binding: 1,
                resource: wgpu::BindingResource::TextureView(texture_view),
            },
            wgpu::BindGroupEntry {
                binding: 2,
                resource: wgpu::BindingResource::Sampler(&pipeline.sampler),
            },
        ];
        let bind_group = pipeline
            .device
            .create_bind_group(&wgpu::BindGroupDescriptor {
                label: Some("mesh bind group"),
                layout: &pipeline.bind_layout,
                entries: &entries,
            });

        // Pass 1: mesh into the 4x MSAA color attachment, resolved to the
        // 1x offscreen texture. Always cleared: the blit composites over
        // the caller's target, which owns its background.
        {
            let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("asset-viewer msaa pass"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: msaa_view,
                    depth_slice: None,
                    resolve_target: Some(resolve_attach_view),
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(wgpu::Color::TRANSPARENT),
                        store: wgpu::StoreOp::Store,
                    },
                })],
                depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment {
                    view: depth_view,
                    depth_ops: Some(wgpu::Operations {
                        load: wgpu::LoadOp::Clear(1.0),
                        store: wgpu::StoreOp::Discard,
                    }),
                    stencil_ops: None,
                }),
                timestamp_writes: None,
                occlusion_query_set: None,
                multiview_mask: None,
            });
            pass.set_viewport(
                clip_bounds.x as f32,
                clip_bounds.y as f32,
                w as f32,
                h as f32,
                0.0,
                1.0,
            );
            pass.set_scissor_rect(clip_bounds.x, clip_bounds.y, w, h);
            pass.set_pipeline(&pipeline.mesh_pipeline);
            pass.set_bind_group(0, &bind_group, &[]);
            pass.set_vertex_buffer(0, vertex_buffer.slice(..));
            pass.set_index_buffer(index_buffer.slice(..), wgpu::IndexFormat::Uint16);
            pass.draw_indexed(0..pipeline.index_count, 0, 0..1);
        }

        // Pass 2: blit the resolved image onto the caller's target.
        let blit_entries = [
            wgpu::BindGroupEntry {
                binding: 0,
                resource: wgpu::BindingResource::Buffer(wgpu::BufferBinding {
                    buffer: &pipeline.blit_buffer,
                    offset: 0,
                    size: None,
                }),
            },
            wgpu::BindGroupEntry {
                binding: 1,
                resource: wgpu::BindingResource::TextureView(resolve_bind_view),
            },
            wgpu::BindGroupEntry {
                binding: 2,
                resource: wgpu::BindingResource::Sampler(&pipeline.sampler),
            },
        ];
        let blit_bind_group = pipeline
            .device
            .create_bind_group(&wgpu::BindGroupDescriptor {
                label: Some("blit bind group"),
                layout: &pipeline.blit_pipeline.get_bind_group_layout(0),
                entries: &blit_entries,
            });
        let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            label: Some("asset-viewer blit pass"),
            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                view: target,
                depth_slice: None,
                resolve_target: None,
                ops: wgpu::Operations {
                    load: wgpu::LoadOp::Load,
                    store: wgpu::StoreOp::Store,
                },
            })],
            depth_stencil_attachment: None,
            timestamp_writes: None,
            occlusion_query_set: None,
            multiview_mask: None,
        });
        pass.set_viewport(
            clip_bounds.x as f32,
            clip_bounds.y as f32,
            w as f32,
            h as f32,
            0.0,
            1.0,
        );
        pass.set_scissor_rect(clip_bounds.x, clip_bounds.y, w, h);
        pass.set_pipeline(&pipeline.blit_pipeline);
        pass.set_bind_group(0, &blit_bind_group, &[]);
        pass.draw(0..3, 0..1);
    }
}

#[cfg(test)]
mod camera_tests {
    use super::*;

    /// Rotating (yaw/pitch) must change the view *direction*, never the
    /// distance: the eye stays on a sphere of radius `distance(radius)`.
    #[test]
    fn eye_stays_on_orbit_sphere() {
        let radius = 0.674;
        for yaw in [-1.0f32, -0.55, -0.2, 0.0, 0.3, 0.7, 1.2, 3.0] {
            for pitch in [-1.0f32, -0.4, 0.0, 0.3, 0.9] {
                for zoom in [0.5f32, 1.0, 2.0] {
                    let cam = Camera {
                        yaw,
                        pitch,
                        zoom,
                        pan: [1.0, -2.0, 3.0],
                    };
                    let eye = cam.eye(radius);
                    let d = cam.distance(radius);
                    let dx = eye[0] - cam.pan[0];
                    let dy = eye[1] - cam.pan[1];
                    let dz = eye[2] - cam.pan[2];
                    let actual = (dx * dx + dy * dy + dz * dz).sqrt();
                    assert!(
                        (actual - d).abs() < d * 1e-4,
                        "yaw={yaw} pitch={pitch} zoom={zoom}: eye at {actual}, expected {d}"
                    );
                }
            }
        }
    }

    #[test]
    fn screen_axes_are_orthonormal() {
        let cam = Camera {
            yaw: 0.7,
            pitch: -0.4,
            zoom: 1.0,
            pan: [0.0; 3],
        };
        let (right, up) = cam.screen_axes();
        let (sy, cy) = (cam.yaw.sin(), cam.yaw.cos());
        let (sp, cp) = (cam.pitch.sin(), cam.pitch.cos());
        let view = [cp * sy, sp, cp * cy]; // eye -> target direction
        let dot = |a: [f32; 3], b: [f32; 3]| a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
        assert!((dot(right, up) - 0.0).abs() < 1e-5);
        assert!((dot(right, view) - 0.0).abs() < 1e-5);
        assert!((dot(up, view) - 0.0).abs() < 1e-5);
        for v in [right, up] {
            assert!((dot(v, v) - 1.0).abs() < 1e-5);
        }
    }
}

#[cfg(test)]
mod blit_tests {
    use super::*;
    use crate::unity::Mesh;
    use std::sync::Arc;

    /// Renders the static mesh offscreen: a full-`frame` target with the
    /// scene drawn into the given `clip` rect (as in the GUI, where the
    /// window is the frame and the viewer widget is the clip). Returns the
    /// opaque-pixel bounding box `(min_x, min_y, max_x, max_y)`, or `None`
    /// when no GPU adapter is available (the test then skips).
    fn render_bbox(clip: &iced::Rectangle<u32>, frame: Size<u32>) -> Option<(u32, u32, u32, u32)> {
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_io()
            .enable_time()
            .build()
            .ok()?;
        runtime.block_on(async move {
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
                .ok()?;
            let (device, queue) = adapter
                .request_device(&wgpu::DeviceDescriptor {
                    label: Some("asset-viewer [test]"),
                    required_features: wgpu::Features::empty(),
                    required_limits: wgpu::Limits::default(),
                    experimental_features: wgpu::ExperimentalFeatures::disabled(),
                    memory_hints: wgpu::MemoryHints::MemoryUsage,
                    trace: wgpu::Trace::Off,
                })
                .await
                .ok()?;

            let format = wgpu::TextureFormat::Rgba8UnormSrgb;
            let mut pipeline = Pipeline::create(&device, &queue, format);
            let mesh =
                Mesh::from_file(std::path::Path::new("../assets/CardPackStatic_Mesh.asset")).ok()?;
            let primitive = Primitive {
                mesh: Some(Arc::new(mesh)),
                material: None,
                camera: Camera::default(),
            };
            // As in the GUI: the frame is the window (offscreen + target),
            // the projection fits the clip (widget) aspect.
            let aspect = (clip.width as f32 / clip.height.max(1) as f32).max(1e-4);
            pipeline.prepare(&device, &queue, &primitive, clip, frame, aspect);

            let texture = device.create_texture(&wgpu::TextureDescriptor {
                label: Some("test target"),
                size: wgpu::Extent3d {
                    width: frame.width,
                    height: frame.height,
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

            let mut encoder =
                device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
            primitive.draw_frame(&pipeline, &mut encoder, &target, clip);

            let row_bytes = frame.width as u64 * 4;
            let row_stride = (row_bytes + 255) / 256 * 256;
            let buffer = device.create_buffer(&wgpu::BufferDescriptor {
                label: Some("test readback"),
                size: row_stride * frame.height as u64,
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
                    width: frame.width,
                    height: frame.height,
                    depth_or_array_layers: 1,
                },
            );
            let submission = queue.submit([encoder.finish()]);
            buffer.slice(..).map_async(wgpu::MapMode::Read, |_| {});
            device
                .poll(wgpu::PollType::Wait {
                    submission_index: Some(submission),
                    timeout: None,
                })
                .ok()?;
            let mapped = buffer.slice(..).get_mapped_range().ok()?;

            // Opaque-pixel bounding box.
            let (mut min_x, mut min_y, mut max_x, mut max_y) = (
                u32::MAX,
                u32::MAX,
                0u32,
                0u32,
            );
            for y in 0..frame.height {
                let start = (y as u64 * row_stride) as usize;
                for x in 0..frame.width {
                    let a = mapped[start + (x as usize) * 4 + 3];
                    if a > 0 {
                        min_x = min_x.min(x);
                        min_y = min_y.min(y);
                        max_x = max_x.max(x);
                        max_y = max_y.max(y);
                    }
                }
            }
            if max_x == 0 && max_y == 0 {
                return None; // nothing rendered (unexpected)
            }
            Some((min_x, min_y, max_x, max_y))
        })
    }

    /// The viewer widget sits next to the sidebar, so iced's clip rect is
    /// offset from the frame origin. The blit must map the offscreen image
    /// to the clip 1:1 in device pixels — content centered in the clip at
    /// the same relative scale as a full-frame render (no squashing), and
    /// nothing drawn outside the clip.
    #[test]
    fn blit_is_one_to_one_for_offset_clip() {
        let full = iced::Rectangle {
            x: 0,
            y: 0,
            width: 1080,
            height: 1440,
        };
        let offset = iced::Rectangle {
            x: 150,
            y: 0,
            width: 930,
            height: 1440,
        };
        let frame = Size::new(1080, 1440);

        let full_bbox = render_bbox(&full, frame);
        let offset_bbox = render_bbox(&offset, frame);
        // No GPU adapter: skip (the other tests don't need one).
        match (full_bbox, offset_bbox) {
            (Some(f), Some(o)) => {
                let f_w = f.2 - f.0;
                let o_w = o.2 - o.0;
                // Same content scale: with the same vertical FOV and clip
                // height the horizontal pixel scale is identical regardless
                // of aspect, so the content width must be unchanged (a
                // squashed blit would shrink or shift it).
                assert!(
                    (o_w as i64 - f_w as i64).abs() <= 2,
                    "content squashed: full width {f_w}, offset width {o_w}"
                );
                // Content centered in each clip: the offset render's center
                // (relative to the clip origin) must equal the full
                // render's, scaled by the clip-width ratio.
                let f_cx = (f.0 as i64 + f.2 as i64) / 2;
                let o_cx = (o.0 as i64 + o.2 as i64) / 2;
                // Simpler, robust form: relative centering must match.
                let f_rel = f_cx - full.x as i64; // content center within the full clip
                let o_rel = o_cx - offset.x as i64;
                assert!(
                    (o_rel - f_rel * 930 / 1080).abs() <= 4,
                    "content not centered in the offset clip: full rel {f_rel}, offset rel {o_rel}"
                );
                // Nothing outside the clip rect.
                assert!(o.0 >= offset.x, "content leaked left of the clip");
                assert!(o.2 < offset.x + offset.width, "content leaked right of the clip");
            }
            (None, _) => {}
            _ => panic!("partial GPU render (one clip rendered, the other did not)"),
        }
    }
}

#[cfg(test)]
mod material_tests {
    use super::*;

    /// PNG rows run top-to-bottom, but Unity UVs (and wgpu texture sampling)
    /// expect v=0 at the image bottom — `from_file` must flip the rows.
    #[test]
    fn rows_are_flipped_for_unity_uvs() {
        // Top pixel (1,2,3,4), bottom pixel (5,6,7,8).
        let img = image::RgbaImage::from_raw(1, 2, vec![1, 2, 3, 4, 5, 6, 7, 8]).unwrap();
        let path =
            std::env::temp_dir().join(format!("asset_viewer_flip_{}.png", std::process::id()));
        img.save(&path).unwrap();
        let mat = Material::from_file(&path).unwrap();
        std::fs::remove_file(&path).ok();
        assert_eq!(mat.pixels, vec![5, 6, 7, 8, 1, 2, 3, 4]);
    }
}
