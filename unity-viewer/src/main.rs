//! A small Unity mesh + material viewer.
//!
//! Pick a `.asset` mesh from `../assets` and a PNG material (from `../images`
//! or `../output/*`, or any file via "Open…") and the viewer renders it with
//! a fixed camera: left-drag grabs and rotates the *asset* (a trackball —
//! the drag spins it about the screen's up/right axes, which are fixed to
//! the view, not to the model's own rotation), so the fixed world-space
//! lights sweep across the model as you aim it; scroll to zoom, right-drag
//! to pan. The Yaw/Pitch/Roll sliders set the same asset rotation precisely
//! (zoom/pan move the camera, not the asset).
//!
//! The asset rotation and camera zoom/pan can be imported from or exported
//! to a JSON configuration file (the Import/Export buttons in the sidebar;
//! the CLI takes the same file with `--config`).
//!
//! Skinned meshes are displayed in bind pose.
//!
//! With command-line arguments the app instead runs headless and writes a
//! PNG screenshot (no window):
//!
//! ```text
//! unity-viewer <mesh> <material> [options]
//! ```
//!
//! See `--help` for the full option list (`--rotation`, `--pitch`, `--roll`,
//! `--zoom`, `--width`, `--height`, `--out`).

use std::path::{Path, PathBuf};
use std::sync::Arc;

use iced::theme;
use iced::widget::shader::Action;
use iced::widget::{button, column, combo_box, container, image, row, shader, slider, space, text};
use iced::{Alignment, Bottom, Color, Fill, Font, Point, Right, Task, Theme, Vector, Widget};

use config::Config;
use scene::{Camera, Material, Model, Primitive};
use unity::Mesh;

mod cli;
mod config;
mod scene;
mod unity;

const ROOT: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/..");
const ASSETS_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../assets");
const IMAGES_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../images");
const OUTPUT_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../output");

/// Sensitivity of the drag trackball: degrees of asset rotation produced by
/// a drag spanning the full canvas width (a half turn — like grabbing the
/// object). The per-pixel rate is this divided by the canvas width, so the
/// feel is the same at any window size and stays gentle.
const DRAG_DEG_PER_FULL_WIDTH: f32 = 180.0;
/// Range of the pitch slider: ±90°. The pitch of the pose's canonical
/// decomposition always lies in this range, so the slider covers every
/// pose exactly.
const MODEL_PITCH_LIMIT: f32 = std::f32::consts::FRAC_PI_2;
const MODEL_PITCH_LIMIT_DEG: f32 = 90.0;
const ZOOM_MIN: f32 = 0.05;
const ZOOM_MAX: f32 = 16.0;
const ZOOM_STEP_LINES: f32 = 0.12;
const ZOOM_STEP_PIXELS: f32 = 0.0015;

/// Normalize degrees to (−180, 180] — the dial value: what the yaw/roll
/// sliders and readouts display. The state holds the pose's canonical
/// decomposition (yaw/roll in (−180°, 180°], pitch in [−90°, 90°]), so the
/// display is already in range and this only normalizes stragglers.
fn wrap_degrees(deg: f32) -> f32 {
    let d = deg.rem_euclid(360.0);
    if d > 180.0 { d - 360.0 } else { d }
}

/// The equivalent of `target` (degrees, −180..180) the model is already
/// closest to. Yaw/roll state is unbounded, so assigning `target` directly
/// would spin the model the long way around; this keeps it at most 180°
/// away from `current`.
fn nearest_equivalent(current: f32, target: f32) -> f32 {
    let t = std::f32::consts::TAU;
    let target_rad = target.to_radians();
    target_rad + ((current - target_rad) / t).round() * t
}

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
    /// Open a file dialog to import the model/camera configuration.
    ImportConfig,
    /// A configuration file was picked (or the dialog cancelled).
    ConfigImported(Option<PathBuf>),
    /// Open a file dialog to export the current model/camera configuration.
    ExportConfig,
    /// A destination was chosen for the configuration (or the dialog
    /// cancelled).
    ConfigExported(Option<PathBuf>),
    /// Asset trackball drag delta in degrees (Δx right, Δy down), already
    /// scaled by the canvas width (see `DRAG_DEG_PER_FULL_WIDTH`).
    Rotate(Vector),
    Pan(Vector),
    Zoom(f32),
    /// Asset-rotation slider values: yaw/pitch/roll in degrees. The camera
    /// stays put; turning the model aims the fixed world-space lights.
    YawChanged(f32),
    PitchChanged(f32),
    RollChanged(f32),
    /// Camera slider values: zoom as a distance factor.
    ZoomChanged(f32),
    /// Pan axis (0 = X, 1 = Y, 2 = Z) and its new world value.
    PanChanged(usize, f32),
    /// Reset the asset rotation (Model section).
    ResetModel,
    /// Reset the camera zoom/pan (View section; the viewing pose is fixed).
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
    /// Rotation of the asset (the Yaw/Pitch/Roll sliders and the left drag
    /// drive this; the lights are fixed in world space).
    model_rotation: Model,
    /// Fixed-pose camera; only zoom/pan are user-adjustable.
    camera: Camera,
    loading: bool,
    error: Option<String>,
}

fn main() -> iced::Result {
    let args: Vec<String> = std::env::args().collect();
    // With arguments we run the headless screenshot CLI; otherwise the GUI.
    if args.len() > 1 {
        match cli::run(&args[1..]) {
            Ok(()) => return Ok(()),
            Err(e) => {
                eprintln!("error: {e}");
                eprintln!("run with --help for usage");
                std::process::exit(1);
            }
        }
    }

    tracing_subscriber::fmt::init();

    iced::application(App::new, App::update, App::view)
        .style(App::style)
        .font(Font::MONOSPACE)
        .theme(Theme::CatppuccinMocha)
        .window_size((1280.0, 860.0))
        .run()
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
                        && (name == "Cardback.png"
                            || name.starts_with("CardPack_")
                            || name.starts_with("CardBox_"))
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
        let material_state =
            combo_box::State::new(material_entries.iter().map(|e| e.label.clone()).collect());

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
            model_rotation: Model::default(),
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
                    self.reset_view_state();
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

            Message::ImportConfig => Task::perform(
                async {
                    tokio::task::spawn_blocking(|| {
                        rfd::FileDialog::new()
                            .set_title("Import view configuration")
                            .add_filter("JSON configuration", &["json"])
                            .pick_file()
                    })
                    .await
                    .ok()
                    .flatten()
                },
                Message::ConfigImported,
            ),

            Message::ConfigImported(Some(path)) => {
                self.error = None;
                match Config::load(&path) {
                    Ok(config) => self.apply_config(config),
                    Err(e) => self.error = Some(e),
                }
                Task::none()
            }

            Message::ConfigImported(None) => Task::none(),

            Message::ExportConfig => {
                // Default the file name to the loaded mesh's (with a
                // .json suffix), so the configuration sits next to it.
                let file_name = self
                    .selected_mesh
                    .and_then(|i| self.mesh_entries.get(i))
                    .map(|e| {
                        Path::new(&e.label)
                            .with_extension("json")
                            .to_string_lossy()
                            .into_owned()
                    })
                    .unwrap_or_else(|| "view.json".to_string());
                Task::perform(
                    async {
                        tokio::task::spawn_blocking(|| {
                            rfd::FileDialog::new()
                                .set_title("Export view configuration")
                                .set_file_name(file_name)
                                .add_filter("JSON configuration", &["json"])
                                .save_file()
                        })
                        .await
                        .ok()
                        .flatten()
                    },
                    Message::ConfigExported,
                )
            }

            Message::ConfigExported(Some(path)) => {
                let config = Config::capture(self.model_rotation, self.camera);
                match config.save(&path) {
                    Ok(()) => self.error = None,
                    Err(e) => self.error = Some(e),
                }
                Task::none()
            }

            Message::ConfigExported(None) => Task::none(),

            Message::Rotate(delta) => {
                // Trackball of the *asset*, not a camera orbit: the drag
                // spins the model about the camera's screen axes (horiz.
                // about screen up, vert. about screen right), composed in
                // front of the current pose, so the model's camera-facing
                // side always moves with the cursor — no matter how the
                // model is already turned. The lights are fixed in world
                // space, so dragging sweeps them across the model.
                let (right, up) = self.camera.screen_axes();
                self.model_rotation = self.model_rotation.trackball(
                    up,
                    right,
                    (delta.x as f32).to_radians(),
                    (delta.y as f32).to_radians(),
                );
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

            Message::YawChanged(deg) => {
                // The slider shows the dial value (the pose modulo 360°),
                // so snap to the nearest equivalent angle: the model moves
                // the short way and lands exactly where the slider says.
                self.model_rotation.yaw = nearest_equivalent(self.model_rotation.yaw, deg);
                Task::none()
            }

            Message::PitchChanged(deg) => {
                self.model_rotation.pitch = deg
                    .to_radians()
                    .clamp(-MODEL_PITCH_LIMIT, MODEL_PITCH_LIMIT);
                Task::none()
            }

            Message::RollChanged(deg) => {
                self.model_rotation.roll = nearest_equivalent(self.model_rotation.roll, deg);
                Task::none()
            }

            Message::ZoomChanged(zoom) => {
                self.camera.zoom = zoom.clamp(ZOOM_MIN, ZOOM_MAX);
                Task::none()
            }

            Message::PanChanged(axis, value) => {
                self.camera.pan[axis] = value;
                Task::none()
            }

            Message::ResetModel => {
                self.model_rotation = Model::default();
                Task::none()
            }

            Message::ResetView => {
                self.camera = Camera::default();
                Task::none()
            }
        }
    }

    /// Reset both the asset rotation and the camera zoom/pan (on mesh
    /// change and implicitly via the section Reset buttons).
    fn reset_view_state(&mut self) {
        self.model_rotation = Model::default();
        self.camera = Camera::default();
    }

    /// Apply an imported configuration. The pose is normalized to its
    /// canonical decomposition, which the sliders can always represent
    /// exactly (decomposed pitch lies in ±90°, yaw/roll in ±180° — even
    /// when the file's angles do not); the camera keeps its fixed pose and
    /// zoom is clamped to the slider range (the CLI applies the file
    /// as-is).
    fn apply_config(&mut self, config: Config) {
        let (model, mut camera) = config.to_state();
        self.model_rotation = Model::from_matrix(&model.matrix());
        camera.zoom = camera.zoom.clamp(ZOOM_MIN, ZOOM_MAX);
        self.camera = camera;
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
                    self.reset_view_state();
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
                let preview = image::Handle::from_rgba(mat.width, mat.height, mat.pixels.clone());
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

    /// A labeled slider row: name, slider, and the formatted current value.
    /// The value is clamped into the range for display as a safety net: the
    /// mutation paths already keep the values in range (`wrap_degrees` for
    /// yaw/roll, clamping for pitch), so slider and readout never disagree.
    fn slider_row<'a>(
        label: &'a str,
        range: std::ops::RangeInclusive<f32>,
        value: f32,
        step: f32,
        display: String,
        on_change: impl Fn(f32) -> Message + 'a,
    ) -> impl Widget<Message> + 'a {
        let value = value.clamp(*range.start(), *range.end());
        row![
            text(label).size(12).width(44),
            slider(range, value, on_change).width(Fill).step(step),
            text(display).size(12).width(56).align_x(Right),
        ]
        .align_y(Alignment::Center)
    }

    fn view(&self) -> impl Widget<Message> {
        // Pan sliders: the orbit target, ranged per mesh (±2 bounding
        // radii, 1% step — a symmetric grid that always includes 0).
        let pan_radius = self.mesh.as_ref().map_or(1.0, |m| m.radius());
        let pan_range = -2.0 * pan_radius..=2.0 * pan_radius;
        let pan_step = pan_radius / 100.0;

        let details = column![
            self.mesh_info(),
            self.material_info(),
            self.loading.then(|| text("Loading…").size(12)),
            self.error
                .as_ref()
                .map(|error| text(error).color(Color::from_rgb8(235, 87, 87)).size(12))
        ]
        .spacing(4);

        let selector = column![
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
            .width(Fill)
            .size(12),
            text("Material").size(12),
            row![
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
                .width(Fill)
                .size(12),
                button(text("Open").size(12)).on_press(Message::OpenMaterial),
            ]
            .spacing(4),
        ]
        .spacing(4);

        let controls = column![
            // The asset rotation and camera zoom/pan as a JSON file
            // (shared with the CLI's --config).
            row![
                text("Config").size(14),
                space::horizontal(),
                button(text("Import").size(12))
                    .on_press(Message::ImportConfig)
                    .style(button::secondary),
                button(text("Export").size(12))
                    .on_press(Message::ExportConfig)
                    .style(button::secondary),
            ]
            .spacing(4)
            .align_y(Bottom),
            row![
                text("Model").size(14),
                space::horizontal(),
                button(text("Reset").size(12))
                    .on_press(Message::ResetModel)
                    .style(button::secondary)
            ]
            .align_y(Bottom),
            // Asset rotation, not the camera: the lights are fixed in world
            // space, so these sliders aim the light at the model's faces.
            // Yaw/roll are dials: the state accumulates full turns while
            // dragging, the row shows the pose modulo 360°.
            Self::slider_row(
                "Yaw",
                -180.0..=180.0,
                wrap_degrees(self.model_rotation.yaw.to_degrees()),
                1.0,
                format!("{:.0}°", wrap_degrees(self.model_rotation.yaw.to_degrees())),
                |deg| Message::YawChanged(deg),
            ),
            Self::slider_row(
                "Pitch",
                -MODEL_PITCH_LIMIT_DEG..=MODEL_PITCH_LIMIT_DEG,
                self.model_rotation.pitch.to_degrees(),
                1.0,
                format!("{:.0}°", self.model_rotation.pitch.to_degrees()),
                |deg| Message::PitchChanged(deg),
            ),
            Self::slider_row(
                "Roll",
                -180.0..=180.0,
                wrap_degrees(self.model_rotation.roll.to_degrees()),
                1.0,
                format!(
                    "{:.0}°",
                    wrap_degrees(self.model_rotation.roll.to_degrees())
                ),
                |deg| Message::RollChanged(deg),
            ),
            space::vertical().height(8),
            row![
                text("View").size(14),
                space::horizontal(),
                button(text("Reset").size(12))
                    .on_press(Message::ResetView)
                    .style(button::secondary)
            ]
            .align_y(Bottom),
            Self::slider_row(
                "Zoom",
                ZOOM_MIN..=ZOOM_MAX,
                self.camera.zoom,
                0.01,
                format!("{:.2}×", self.camera.zoom),
                Message::ZoomChanged,
            ),
            Self::slider_row(
                "Pan X",
                pan_range.clone(),
                self.camera.pan[0],
                pan_step,
                format!("{:.3}", self.camera.pan[0]),
                |v| Message::PanChanged(0, v),
            ),
            Self::slider_row(
                "Pan Y",
                pan_range.clone(),
                self.camera.pan[1],
                pan_step,
                format!("{:.3}", self.camera.pan[1]),
                |v| Message::PanChanged(1, v),
            ),
            Self::slider_row(
                "Pan Z",
                pan_range.clone(),
                self.camera.pan[2],
                pan_step,
                format!("{:.3}", self.camera.pan[2]),
                |v| Message::PanChanged(2, v),
            ),
        ]
        .spacing(4);

        let sidebar = column![
            details,
            selector,
            controls,
            space::vertical(),
            text("Left drag: rotate the asset\nScroll: zoom\nRight drag: pan").size(12),
        ]
        .spacing(32)
        .padding(8);

        let canvas = shader(Renderer {
            mesh: &self.mesh,
            material: &self.material,
            camera: &self.camera,
            rotation: &self.model_rotation,
        })
        .width(Fill)
        .height(Fill);

        row![container(sidebar).width(300u32).height(Fill), canvas,]
    }

    fn mesh_info(&self) -> impl Widget<Message> {
        match &self.mesh {
            Some(m) => column![
                text(m.name.clone()).size(14),
                text(format!(
                    "vertices {} · triangles {}",
                    m.vertices.len(),
                    m.triangle_count()
                ))
                .size(12),
                if m.is_skinned {
                    text(format!("skinned · {} bones (bind pose)", m.bone_count)).size(12)
                } else {
                    text("static").size(12)
                },
                text(format!(
                    "bounds {:.2} × {:.2} × {:.2}",
                    m.extent[0] * 2.0,
                    m.extent[1] * 2.0,
                    m.extent[2] * 2.0
                ))
                .size(12),
            ]
            .spacing(2),
            None => column![text("(no mesh loaded)").size(12)],
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
                text(format!("{} × {}", mat.width, mat.height)).size(12),
            ]
            .spacing(2),
            (Some(label), None) => column![text(format!("{label} (not loaded)")).size(12)],
            (None, _) => column![text("(none)").size(12)],
        }
    }

    fn style(&self, theme: &Theme) -> theme::Style {
        theme::Style {
            background_color: Color::BLACK,
            text_color: theme.seed().text,
        }
    }
}

// --- the shader widget ------------------------------------------------------

struct Renderer<'a> {
    mesh: &'a Option<Arc<Mesh>>,
    material: &'a Option<Arc<Material>>,
    rotation: &'a Model,
    camera: &'a Camera,
}

#[derive(Default)]
struct DragState {
    rotate: Option<Point>,
    pan: Option<Point>,
}

impl shader::Program<Message> for Renderer<'_> {
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
                // `update` receives every mouse event in the window, so a
                // drag only arms when the press lands over the canvas —
                // otherwise e.g. dragging the view sliders on the sidebar
                // would rotate/pan the camera at the same time.
                if cursor.is_over(bounds) {
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
                } else {
                    None
                }
            }
            iced::Event::Mouse(iced::mouse::Event::CursorMoved { .. }) => {
                let pos = cursor.position()?;
                if let Some(last) = state.rotate {
                    state.rotate = Some(pos);
                    // Scale by the canvas width so a full-width drag always
                    // turns the asset by `DRAG_DEG_PER_FULL_WIDTH` (a half
                    // turn), instead of a fixed degrees-per-pixel that would
                    // feel different at each window size.
                    let deg_per_px = DRAG_DEG_PER_FULL_WIDTH / bounds.size().width.max(1.0);
                    Some(Action::publish(Message::Rotate(Vector::new(
                        (pos.x - last.x) * deg_per_px,
                        (pos.y - last.y) * deg_per_px,
                    ))))
                } else if let Some(last) = state.pan {
                    state.pan = Some(pos);
                    let h = bounds.size().height.max(1.0);
                    let radius = self.mesh.as_ref().map(|m| m.radius()).unwrap_or(1.0);
                    let distance = self.camera.distance(radius);
                    let world_per_px = 2.0_f32 * distance * (scene::FOV_Y * 0.5).tan() / h;
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
            // Same guard as the buttons: don't zoom while scrolling over
            // the sidebar.
            iced::Event::Mouse(iced::mouse::Event::WheelScrolled { delta })
                if cursor.is_over(bounds) =>
            {
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
            rotation: *self.rotation,
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

#[cfg(test)]
mod tests {
    use super::*;
    use std::f32::consts::TAU;

    /// The pose depends on the angle only modulo 360°.
    fn same_pose(a: f32, b: f32) -> bool {
        (a - b).rem_euclid(TAU).min(TAU - (a - b).rem_euclid(TAU)) < 1e-3
    }

    #[test]
    fn wrap_degrees_normalizes_to_the_dial_range() {
        assert!((wrap_degrees(190.0) - (-170.0)).abs() < 1e-3);
        assert!((wrap_degrees(-190.0) - 170.0).abs() < 1e-3);
        assert!((wrap_degrees(360.0) - 0.0).abs() < 1e-3);
        assert!((wrap_degrees(-360.0) - 0.0).abs() < 1e-3);
        assert!((wrap_degrees(540.0) - 180.0).abs() < 1e-3);
        assert!((wrap_degrees(180.0) - 180.0).abs() < 1e-3);
        assert!((wrap_degrees(-179.9) - (-179.9)).abs() < 1e-3);
    }

    #[test]
    fn nearest_equivalent_keeps_the_pose_and_the_short_way() {
        // 400° ≡ 40°; asking for 30° must not spin a full turn.
        let got = nearest_equivalent(400.0 * std::f32::consts::PI / 180.0, 30.0);
        assert!(same_pose(got, 30.0 * std::f32::consts::PI / 180.0));
        assert!((got.to_degrees() - 390.0).abs() < 1e-3);

        // The result must always be at most a half turn from `current`.
        for current_deg in [
            -720.0f32, -350.0, -190.0, -10.0, 5.0, 179.9, 181.0, 359.9, 400.0, 730.0,
        ] {
            for target in [-170.0, -90.0, 0.0, 45.0, 170.0] {
                let current = current_deg.to_radians();
                let got = nearest_equivalent(current, target);
                assert!(
                    same_pose(got, target.to_radians()),
                    "current={current_deg} target={target}"
                );
                let away = (got - current).abs();
                assert!(
                    away <= std::f32::consts::PI + 1e-3,
                    "current={current_deg} target={target}: moved {away} rad (> 180°)"
                );
            }
        }
    }
}
