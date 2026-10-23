//! A small Unity mesh + material viewer.
//!
//! Pick a `.asset` mesh from `../assets` and a PNG material (from `../images`
//! or `../output/*`, or any file via "Open…") and the viewer renders it with
//! an orbit camera: left-drag to rotate, scroll to zoom, right-drag to pan.
//!
//! Skinned meshes are displayed in bind pose.
//!
//! With command-line arguments the app instead runs headless and writes a
//! PNG screenshot (no window):
//!
//! ```text
//! asset-viewer <mesh> <material> --rotation <deg> --zoom <factor> [options]
//! ```
//!
//! See `--help` for the full option list (`--pitch`, `--width`, `--height`,
//! `--out`).

use std::path::{Path, PathBuf};
use std::sync::Arc;

use iced::widget::shader::Action;
use iced::widget::{
    button, column, combo_box, container, image, responsive, row, rule, shader, space, text,
};
use iced::{widget, Background, Color, Font, Length, Point, Task, Theme, Vector, Widget};

use scene::{Camera, Material, Primitive};
use unity::Mesh;

mod cli;
mod scene;
mod unity;

const ROOT: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/..");
const ASSETS_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../assets");
const IMAGES_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../images");
const OUTPUT_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../output");

const ROTATE_SPEED: f32 = 0.008;
const PITCH_LIMIT: f32 = 1.5;
const ZOOM_MIN: f32 = 0.05;
const ZOOM_MAX: f32 = 16.0;
const ZOOM_STEP_LINES: f32 = 0.12;
const ZOOM_STEP_PIXELS: f32 = 0.0015;

struct MeshEntry {
    label: String,
    path: PathBuf,
    geometry: Option<Arc<Mesh>>,
}

struct MaterialEntry {
    label: String,
    path: PathBuf,
    data: Option<Arc<Material>>,
    preview: Option<image::Handle>,
}

#[derive(Debug, Clone)]
enum Message {
    InitLoaded(
        Option<usize>,
        Result<Option<Arc<Mesh>>, String>,
        usize,
        Result<Option<Arc<Material>>, String>,
    ),
    MeshSelected(usize),
    MeshLoaded(usize, Result<Arc<Mesh>, String>),
    MaterialSelected(usize),
    MaterialLoaded(usize, Result<Arc<Material>, String>),
    OpenMaterial,
    MaterialPicked(Option<PathBuf>),
    Rotate(Vector),
    Pan(Vector),
    Zoom(f32),
    ResetView,
}

struct App {
    mesh_entries: Vec<MeshEntry>,
    mesh_state: combo_box::State<String>,
    material_entries: Vec<MaterialEntry>,
    material_state: combo_box::State<String>,
    selected_mesh: Option<usize>,
    selected_material: usize,
    mesh: Option<Arc<Mesh>>,
    material: Option<Arc<Material>>,
    material_preview: Option<image::Handle>,
    camera: Camera,
    loading: bool,
    error: Option<String>,
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    // With arguments we run the headless screenshot CLI; otherwise the GUI.
    if args.len() > 1 {
        match cli::run(&args[1..]) {
            Ok(()) => return,
            Err(e) => {
                eprintln!("error: {e}");
                eprintln!("run with --help for usage");
                std::process::exit(1);
            }
        }
    }

    tracing_subscriber::fmt::init();

    if let Err(e) = iced::application(App::new, App::update, App::view)
        .font(Font::MONOSPACE)
        .theme(Theme::CatppuccinMocha)
        .window_size((1280.0, 860.0))
        .run()
    {
        eprintln!("error: {e}");
        std::process::exit(1);
    }
}

// --- scanning -------------------------------------------------------------

fn scan_meshes() -> Vec<MeshEntry> {
    let Some(rd) = std::fs::read_dir(ASSETS_DIR).ok() else {
        return Vec::new();
    };
    let mut entries: Vec<MeshEntry> = rd
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|e| e == "asset"))
        .filter_map(|p| {
            let label = p.file_stem()?.to_string_lossy().into_owned();
            Some(MeshEntry {
                label,
                path: p,
                geometry: None,
            })
        })
        .collect();
    entries.sort_by(|a, b| a.label.cmp(&b.label));
    entries
}

fn scan_materials() -> Vec<(String, PathBuf)> {
    let mut out: Vec<(String, PathBuf)> = Vec::new();

    // Top-level textures.
    if let Ok(rd) = std::fs::read_dir(IMAGES_DIR) {
        for e in rd.flatten() {
            let p = e.path();
            if p.extension().is_some_and(|e| e == "png") {
                out.push((relative(&p), p));
            }
        }
    }

    // Per-pack card textures.
    if let Ok(rd) = std::fs::read_dir(OUTPUT_DIR) {
        for e in rd.flatten() {
            let dir = e.path();
            if !dir.is_dir() {
                continue;
            }
            if let Ok(rd2) = std::fs::read_dir(&dir) {
                for e2 in rd2.flatten() {
                    let p = e2.path();
                    let name = match p.file_name().and_then(|s| s.to_str()) {
                        Some(s) => s.to_string(),
                        None => continue,
                    };
                    if p.extension().is_some_and(|e| e == "png")
                        && (name == "Cardback.png" || name.starts_with("CardPack_"))
                    {
                        out.push((relative(&p), p));
                    }
                }
            }
        }
    }

    out.sort();
    out
}

fn relative(p: &Path) -> String {
    p.strip_prefix(ROOT)
        .unwrap_or(p)
        .to_string_lossy()
        .replace('\\', "/")
}

// --- async loading ---------------------------------------------------------

async fn load_mesh(path: PathBuf) -> Result<Arc<Mesh>, String> {
    tokio::task::spawn_blocking(move || {
        Mesh::from_file(&path)
            .map(Arc::new)
            .map_err(|e| e.to_string())
    })
    .await
    .map_err(|e| format!("mesh load failed: {e}"))?
}

async fn load_material(path: PathBuf) -> Result<Arc<Material>, String> {
    tokio::task::spawn_blocking(move || Material::from_file(&path))
        .await
        .map_err(|e| format!("material load failed: {e}"))?
}

// --- App -------------------------------------------------------------------

impl App {
    fn new() -> (Self, Task<Message>) {
        let mesh_entries = scan_meshes();
        let material_entries: Vec<MaterialEntry> = std::iter::once(MaterialEntry {
            label: "(none)".to_string(),
            path: PathBuf::new(),
            data: None,
            preview: None,
        })
        .chain(
            scan_materials()
                .into_iter()
                .map(|(label, path)| MaterialEntry {
                    label,
                    path,
                    data: None,
                    preview: None,
                }),
        )
        .collect();

        let mesh_state =
            combo_box::State::new(mesh_entries.iter().map(|e| e.label.clone()).collect());
        let material_state = combo_box::State::new(
            material_entries
                .iter()
                .map(|e| e.label.clone())
                .collect(),
        );

        let selected_mesh = mesh_entries.first().map(|_| 0);
        let app = App {
            mesh_entries,
            mesh_state,
            material_entries,
            material_state,
            selected_mesh,
            selected_material: 0,
            mesh: None,
            material: None,
            material_preview: None,
            camera: Camera::default(),
            loading: false,
            error: None,
        };

        let mesh_path = app
            .selected_mesh
            .and_then(|i| app.mesh_entries.get(i).map(|e| e.path.clone()));
        let material_path = app.material_entries.iter().nth(1).map(|e| e.path.clone());
        let (mesh_idx, material_idx) = (app.selected_mesh, 1usize);

        let init = Task::perform(
            async move {
                let (mesh, material) = tokio::join!(
                    async {
                        match mesh_path {
                            Some(path) => load_mesh(path).await.map(Some),
                            None => Ok::<Option<Arc<Mesh>>, String>(None),
                        }
                    },
                    async {
                        match material_path {
                            Some(path) => load_material(path).await.map(Some),
                            None => Ok::<Option<Arc<Material>>, String>(None),
                        }
                    },
                );
                (mesh_idx, mesh, material_idx, material)
            },
            |r| match r {
                (mi, m, xi, x) => Message::InitLoaded(mi, m, xi, x),
            },
        );

        (app, init)
    }

    fn update(&mut self, message: Message) -> Task<Message> {
        match message {
            Message::InitLoaded(mi, mres, xi, xres) => {
                self.loading = false;
                if let Some(i) = mi {
                    self.apply_mesh_load(i, mres);
                }
                self.apply_material_load(xi, xres);
                Task::none()
            }

            Message::MeshSelected(i) => {
                if self.mesh_entries.get(i).is_none() {
                    return Task::none();
                }
                self.selected_mesh = Some(i);
                self.error = None;
                if let Some(geo) = &self.mesh_entries[i].geometry {
                    self.mesh = Some(geo.clone());
                    self.camera = Camera::default();
                    return Task::none();
                }
                self.loading = true;
                let path = self.mesh_entries[i].path.clone();
                Task::perform(load_mesh(path), move |res| Message::MeshLoaded(i, res))
            }

            Message::MeshLoaded(i, res) => {
                self.loading = false;
                self.apply_mesh_load(i, res.map(Some));
                Task::none()
            }

            Message::MaterialSelected(i) => {
                if self.material_entries.get(i).is_none() {
                    return Task::none();
                }
                self.selected_material = i;
                self.error = None;
                if i == 0 {
                    self.material = None;
                    self.material_preview = None;
                    return Task::none();
                }
                if let Some(data) = &self.material_entries[i].data {
                    self.material = Some(data.clone());
                    self.material_preview = self.material_entries[i].preview.clone();
                    return Task::none();
                }
                self.loading = true;
                let path = self.material_entries[i].path.clone();
                Task::perform(load_material(path), move |res| {
                    Message::MaterialLoaded(i, res)
                })
            }

            Message::MaterialLoaded(i, res) => {
                self.loading = false;
                self.apply_material_load(i, res.map(Some));
                Task::none()
            }

            Message::OpenMaterial => {
                self.loading = true;
                Task::perform(
                    async {
                        tokio::task::spawn_blocking(|| {
                            rfd::FileDialog::new()
                                .set_title("Select a material texture")
                                .add_filter("PNG images", &["png"])
                                .pick_file()
                        })
                        .await
                        .ok()
                        .flatten()
                    },
                    Message::MaterialPicked,
                )
            }

            Message::MaterialPicked(Some(path)) => {
                self.loading = false;
                let label = path
                    .file_name()
                    .map(|s| s.to_string_lossy().into_owned())
                    .unwrap_or_else(|| path.display().to_string());
                self.material_entries.push(MaterialEntry {
                    label,
                    path: path.clone(),
                    data: None,
                    preview: None,
                });
                let i = self.material_entries.len() - 1;
                self.selected_material = i;
                self.error = None;
                self.loading = true;
                Task::perform(load_material(path), move |res| {
                    Message::MaterialLoaded(i, res)
                })
            }

            Message::MaterialPicked(None) => {
                self.loading = false;
                Task::none()
            }

            Message::Rotate(delta) => {
                // Screen y grows downward, and positive pitch = camera above
                // the model, so a downward drag (delta.y > 0) must raise the
                // camera to tilt the model's top toward you (grab feel).
                self.camera.yaw -= delta.x as f32 * ROTATE_SPEED;
                self.camera.pitch =
                    (self.camera.pitch + delta.y as f32 * ROTATE_SPEED).clamp(-PITCH_LIMIT, PITCH_LIMIT);
                Task::none()
            }

            Message::Pan(delta) => {
                let (wx, wy) = (delta.x as f32, delta.y as f32);
                let (right, up) = self.camera.screen_axes();
                self.camera.pan[0] += up[0] * wy - right[0] * wx;
                self.camera.pan[1] += up[1] * wy - right[1] * wx;
                self.camera.pan[2] += up[2] * wy - right[2] * wx;
                Task::none()
            }

            Message::Zoom(factor) => {
                self.camera.zoom = (self.camera.zoom * factor).clamp(ZOOM_MIN, ZOOM_MAX);
                Task::none()
            }

            Message::ResetView => {
                self.camera = Camera::default();
                Task::none()
            }
        }
    }

    /// Cache the parsed mesh and activate it if it is the current selection.
    fn apply_mesh_load(&mut self, i: usize, res: Result<Option<Arc<Mesh>>, String>) {
        match res {
            Ok(Some(geo)) => {
                if let Some(entry) = self.mesh_entries.get_mut(i) {
                    entry.geometry = Some(geo.clone());
                }
                if self.selected_mesh == Some(i) {
                    self.mesh = Some(geo);
                    self.camera = Camera::default();
                }
            }
            Ok(None) => {}
            Err(e) if self.selected_mesh == Some(i) => self.error = Some(e),
            Err(_) => {}
        }
    }

    /// Cache the decoded material (+ preview) and activate it if it is the
    /// current selection.
    fn apply_material_load(&mut self, i: usize, res: Result<Option<Arc<Material>>, String>) {
        match res {
            Ok(Some(mat)) => {
                let preview =
                    image::Handle::from_rgba(mat.width, mat.height, mat.pixels.clone());
                if let Some(entry) = self.material_entries.get_mut(i) {
                    entry.data = Some(mat.clone());
                    entry.preview = Some(preview);
                }
                if self.selected_material == i {
                    self.material = Some(mat);
                }
            }
            Ok(None) => {}
            Err(e) if self.selected_material == i => self.error = Some(e),
            Err(_) => {}
        }
    }

    fn view(&self) -> impl Widget<Message> {
        let sidebar = column![
            text("Asset Viewer").size(18),
            space::vertical(),
            text("Mesh").size(12),
            combo_box(
                &self.mesh_state,
                "select a mesh…",
                self.selected_mesh
                    .and_then(|i| self.mesh_entries.get(i))
                    .map(|e| &e.label),
                |label| {
                    let i = self
                        .mesh_entries
                        .iter()
                        .position(|e| e.label == label)
                        .unwrap_or_default();
                    Message::MeshSelected(i)
                },
            )
            .width(Length::Fill),
            space::vertical(),
            text("Material").size(12),
            combo_box(
                &self.material_state,
                "select a texture…",
                self.material_entries
                    .get(self.selected_material)
                    .map(|e| &e.label),
                |label| {
                    let i = self
                        .material_entries
                        .iter()
                        .position(|e| e.label == label)
                        .unwrap_or_default();
                    Message::MaterialSelected(i)
                },
            )
            .width(Length::Fill),
            button(text("Open…").size(12))
                .width(Length::Fill)
                .on_press(Message::OpenMaterial),
            space::vertical().height(8u32),
            rule::horizontal(1u32),
            space::vertical().height(8u32),
            self.mesh_info(),
            space::vertical().height(6u32),
            self.material_info(),
            if self.loading {
                text("Loading…").size(11)
            } else {
                text(" ").size(1)
            },
            if let Some(error) = &self.error {
                text(error).color(Color::from_rgb8(235, 87, 87)).size(11)
            } else {
                text(" ").size(1)
            },
            space::vertical().height(Length::Fill),
            button(text("Reset view").size(12))
                .width(Length::Fill)
                .on_press(Message::ResetView),
            space::vertical().height(6u32),
            text("Left drag: rotate\nScroll: zoom\nRight drag: pan").size(11),
        ]
        .spacing(6)
        .padding(12);

        let canvas = responsive(|size| {
            let renderer = shader(Renderer {
                mesh: &self.mesh,
                material: &self.material,
                camera: &self.camera,
            });
            container(renderer.width(Length::Fill).height(Length::Fill))
                .width(size.width)
                .height(size.height)
                .style(|_| canvas_style())
        });

        row![
            container(sidebar)
                .width(300u32)
                .height(Length::Fill)
                .style(|_| panel_style()),
            canvas,
        ]
    }

    fn mesh_info(&self) -> impl Widget<Message> {
        match &self.mesh {
            Some(m) => column![
                text(m.name.clone()).size(13),
                text(format!(
                    "vertices {} · triangles {}",
                    m.vertices.len(),
                    m.triangle_count()
                ))
                .size(11),
                if m.is_skinned {
                    text(format!("skinned · {} bones (bind pose)", m.bone_count)).size(11)
                } else {
                    text("static").size(11)
                },
                text(format!(
                    "bounds {:.2} × {:.2} × {:.2}",
                    m.extent[0] * 2.0,
                    m.extent[1] * 2.0,
                    m.extent[2] * 2.0
                ))
                .size(11),
            ]
            .spacing(2),
            None => column![text("(no mesh loaded)").size(11)],
        }
    }

    fn material_info(&self) -> impl Widget<Message> {
        match (
            self.material_entries
                .get(self.selected_material)
                .map(|e| e.label.clone()),
            self.material.as_ref(),
        ) {
            (Some(label), Some(mat)) => column![
                text(label).size(13),
                text(format!("{} × {}", mat.width, mat.height)).size(11),
            ]
            .spacing(2),
            (Some(label), None) => column![text(format!("{label} (not loaded)")).size(11)],
            (None, _) => column![text("(none)").size(11)],
        }
    }
}

// --- the shader widget ------------------------------------------------------

struct Renderer<'a> {
    mesh: &'a Option<Arc<Mesh>>,
    material: &'a Option<Arc<Material>>,
    camera: &'a Camera,
}

#[derive(Default)]
struct DragState {
    rotate: Option<Point>,
    pan: Option<Point>,
}

impl widget::shader::Program<Message> for Renderer<'_> {
    type State = DragState;
    type Primitive = Primitive;

    fn update(
        &self,
        state: &mut Self::State,
        event: &iced::Event,
        bounds: iced::Rectangle,
        cursor: iced::mouse::Cursor,
    ) -> Option<Action<Message>> {
        match event {
            iced::Event::Mouse(iced::mouse::Event::ButtonPressed(button)) => {
                match button {
                    iced::mouse::Button::Left => {
                        state.rotate = cursor.position();
                        Some(Action::capture())
                    }
                    iced::mouse::Button::Right => {
                        state.pan = cursor.position();
                        Some(Action::capture())
                    }
                    _ => None,
                }
            }
            iced::Event::Mouse(iced::mouse::Event::CursorMoved { .. }) => {
                let pos = cursor.position()?;
                if let Some(last) = state.rotate {
                    state.rotate = Some(pos);
                    Some(Action::publish(Message::Rotate(Vector::new(
                        pos.x - last.x,
                        pos.y - last.y,
                    ))))
                } else if let Some(last) = state.pan {
                    state.pan = Some(pos);
                    let h = bounds.size().height.max(1.0);
                    let radius = self.mesh.as_ref().map(|m| m.radius()).unwrap_or(1.0);
                    let distance = self.camera.distance(radius);
                    let world_per_px =
                        2.0_f32 * distance * (scene::FOV_Y * 0.5).tan() / h;
                    Some(Action::publish(Message::Pan(Vector::new(
                        (pos.x - last.x) * world_per_px,
                        (pos.y - last.y) * world_per_px,
                    ))))
                } else {
                    None
                }
            }
            iced::Event::Mouse(iced::mouse::Event::ButtonReleased(button)) => {
                if *button == iced::mouse::Button::Left {
                    state.rotate = None;
                }
                if *button == iced::mouse::Button::Right {
                    state.pan = None;
                }
                None
            }
            iced::Event::Mouse(iced::mouse::Event::WheelScrolled { delta }) => {
                let step = match delta {
                    iced::mouse::ScrollDelta::Lines { y, .. } => *y * ZOOM_STEP_LINES,
                    iced::mouse::ScrollDelta::Pixels { y, .. } => *y * ZOOM_STEP_PIXELS,
                };
                if step == 0.0 {
                    None
                } else {
                    Some(Action::publish(Message::Zoom(1.0 + step)).and_capture())
                }
            }
            _ => None,
        }
    }

    fn draw(
        &self,
        _state: &Self::State,
        _cursor: iced::mouse::Cursor,
        _bounds: iced::Rectangle,
    ) -> Self::Primitive {
        Primitive {
            mesh: self.mesh.clone(),
            material: self.material.clone(),
            camera: *self.camera,
        }
    }

    fn mouse_interaction(
        &self,
        state: &Self::State,
        _bounds: iced::Rectangle,
        _cursor: iced::mouse::Cursor,
    ) -> iced::mouse::Interaction {
        if state.rotate.is_some() || state.pan.is_some() {
            iced::mouse::Interaction::Grabbing
        } else {
            iced::mouse::Interaction::None
        }
    }
}

// --- styles ------------------------------------------------------------------

fn panel_style() -> widget::container::Style {
    widget::container::Style {
        background: Some(Background::Color(Color::from_rgb8(32, 34, 42))),
        ..Default::default()
    }
}

fn canvas_style() -> widget::container::Style {
    widget::container::Style {
        background: Some(Background::Color(Color::from_rgb8(20, 22, 27))),
        ..Default::default()
    }
}
