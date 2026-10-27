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

/// The repository root (the directory that holds `assets/`, `cards/`, …).
pub const ROOT: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/..");
/// The `assets/` directory (the assets submodule): `images/` and `meshes/`
/// below it.
pub const ASSETS_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../assets");
/// The `assets/images/` directory: material templates and shared artwork.
pub const IMAGES_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../assets/images");
/// The `assets/meshes/` directory: meshes (`.asset`/`.obj`) and their
/// viewer configuration JSON files.
pub const MESHES_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../assets/meshes");
/// The `output/` directory: finished generated images.
pub const OUTPUT_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../output");
