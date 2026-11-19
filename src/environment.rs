use std::path::{Path, PathBuf};

fn root_dir() -> &'static Path {
    Path::new(env!("CARGO_MANIFEST_DIR"))
}

pub fn output_dir() -> PathBuf {
    root_dir().join("output")
}

pub fn assets_dir() -> PathBuf {
    root_dir().join("assets")
}

pub fn images_dir() -> PathBuf {
    assets_dir().join("images")
}
