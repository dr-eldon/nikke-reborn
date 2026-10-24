//! The unity-viewer library: mesh parsing (Unity `.asset` and Wavefront
//! `.obj`), the wgpu scene, the headless screenshot CLI, and the JSON
//! viewer configuration shared by the GUI and the CLI.
//!
//! Two binaries build on it: `unity-viewer` (the GUI plus the headless
//! screenshot mode) and `mesh-convert` (`.asset` → `.obj` conversion).

pub mod cli;
pub mod config;
pub mod mesh;
pub mod obj;
pub mod scene;
pub mod unity;

/// The repository root (the directory that holds `assets/`, `images/`, …).
pub const ROOT: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/..");
/// The `assets/` directory: meshes (`.asset`/`.obj`) and their viewer
/// configuration JSON files.
pub const ASSETS_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../assets");
/// The `images/` directory: material templates and shared artwork.
pub const IMAGES_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../images");
/// The `output/` directory: finished generated images.
pub const OUTPUT_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../output");
