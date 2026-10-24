//! Mesh loading: dispatch on the file extension — a `.obj` file goes to
//! the OBJ parser, anything else to the Unity `.asset` parser.

use std::path::Path;

use crate::unity::Mesh;

/// Load a mesh (`.obj` or Unity `.asset`) from *path*.
pub fn load(path: &Path) -> Result<Mesh, String> {
    if path.extension().is_some_and(|e| e.eq_ignore_ascii_case("obj")) {
        crate::obj::from_file(path).map_err(|e| e.to_string())
    } else {
        Mesh::from_file(path).map_err(|e| e.to_string())
    }
}
