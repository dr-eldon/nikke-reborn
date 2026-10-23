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
const AMBIENT: vec3<f32> = vec3<f32>(0.5, 0.52, 0.56);
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

pub struct Pipeline {
    device: wgpu::Device,
    bind_layout: wgpu::BindGroupLayout,
    mesh_pipeline: wgpu::RenderPipeline,
    uniforms_buffer: wgpu::Buffer,
    mesh: Option<(Arc<Mesh>, wgpu::Buffer, wgpu::Buffer)>,
    index_count: u32,
    material: Option<(Arc<Material>, wgpu::TextureView)>,
    sampler: wgpu::Sampler,
    default_view: wgpu::TextureView,
    depth: Option<(u32, u32, wgpu::TextureView)>,
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
                count: 1,
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
            bind_layout: mesh_pipeline.get_bind_group_layout(0),
            mesh_pipeline,
            uniforms_buffer,
            mesh: None,
            index_count: 0,
            material: None,
            sampler,
            default_view,
            depth: None,
        }
    }

    /// (Re)create the full-frame depth attachment.
    fn update_depth(&mut self, device: &wgpu::Device, size: Size<u32>) {
        if self
            .depth
            .as_ref()
            .is_some_and(|(w, h, _)| *w == size.width && *h == size.height)
        {
            return;
        }
        let texture = device.create_texture(&wgpu::TextureDescriptor {
            label: Some("depth"),
            size: wgpu::Extent3d {
                width: size.width.max(1),
                height: size.height.max(1),
                depth_or_array_layers: 1,
            },
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: wgpu::TextureFormat::Depth32Float,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
            view_formats: &[],
        });
        self.depth = Some((
            size.width.max(1),
            size.height.max(1),
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

    /// Upload mesh/material/uniforms for a render of `primitive` into a
    /// `size`-sized frame with the given aspect ratio. Shared by the iced
    /// `prepare` callback and the headless CLI path.
    pub fn prepare(
        &mut self,
        device: &wgpu::Device,
        queue: &wgpu::Queue,
        primitive: &Primitive,
        size: Size<u32>,
        aspect: f32,
    ) {
        self.update_depth(device, size);

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
        let aspect = (bounds.size().width / bounds.size().height.max(1.0)).max(1e-4);
        pipeline.prepare(device, queue, self, frame, aspect);
    }

    fn draw(&self, _pipeline: &Self::Pipeline, _render_pass: &mut wgpu::RenderPass) -> bool {
        // Not drawn here: we need our own depth attachment, so the actual
        // rendering happens in `render` (the fallback pass).
        false
    }

    fn render(
        &self,
        pipeline: &Self::Pipeline,
        encoder: &mut wgpu::CommandEncoder,
        target: &wgpu::TextureView,
        clip_bounds: &Rectangle<u32>,
    ) {
        // Keep whatever iced already drew (window background) and draw the
        // mesh on top of it.
        self.draw_frame(pipeline, encoder, target, clip_bounds, wgpu::LoadOp::Load);
    }
}

impl Primitive {
    /// The actual render pass; also used by the headless CLI path, which
    /// passes a clear load op for its offscreen target.
    pub fn draw_frame(
        &self,
        pipeline: &Pipeline,
        encoder: &mut wgpu::CommandEncoder,
        target: &wgpu::TextureView,
        clip_bounds: &Rectangle<u32>,
        color_load: wgpu::LoadOp<wgpu::Color>,
    ) {
        let Some((_, vertex_buffer, index_buffer)) = &pipeline.mesh else {
            return;
        };
        let Some((_, _, depth_view)) = &pipeline.depth else {
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

        let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            label: Some("asset-viewer pass"),
            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                view: target,
                depth_slice: None,
                resolve_target: None,
                ops: wgpu::Operations {
                    load: color_load,
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
