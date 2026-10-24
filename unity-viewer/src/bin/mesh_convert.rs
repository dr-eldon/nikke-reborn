//! Convert a Unity `Mesh` `.asset` to a Wavefront `.obj`.
//!
//! ```text
//! mesh-convert <mesh.asset> [--out <path.obj>]
//! ```
//!
//! The mesh is read through the same parser the viewer uses (origin-
//! centered positions, normals and uv0), then written in the standard OBJ
//! convention — right-handed coordinates, bottom-left UV origin (the
//! OBJ/Blender convention) — so a converted mesh renders identically to
//! the original `.asset` and opens in Blender unmirrored.

use std::path::{Path, PathBuf};
use std::process::ExitCode;

use unity_viewer::unity::Mesh;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut input: Option<String> = None;
    let mut out: Option<PathBuf> = None;
    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "-h" | "--help" => {
                print_help();
                return ExitCode::SUCCESS;
            }
            "--out" => {
                i += 1;
                match args.get(i) {
                    Some(p) => out = Some(PathBuf::from(p)),
                    None => {
                        eprintln!("error: --out expects a path");
                        return ExitCode::FAILURE;
                    }
                }
            }
            other if other.starts_with("--out=") => out = Some(PathBuf::from(&other[6..])),
            other => {
                if input.is_none() {
                    input = Some(other.to_string());
                } else {
                    eprintln!("error: unexpected argument: {other}");
                    print_help();
                    return ExitCode::FAILURE;
                }
            }
        }
        i += 1;
    }
    let input = match input {
        Some(p) => p,
        None => {
            eprintln!("error: missing <mesh.asset>");
            print_help();
            return ExitCode::FAILURE;
        }
    };
    match run(Path::new(&input), out) {
        Ok((written, vertices, triangles)) => {
            eprintln!("{input} -> {written} ({vertices} vertices, {triangles} triangles)");
        }
        Err(e) => {
            eprintln!("error: {e}");
            return ExitCode::FAILURE;
        }
    }
    ExitCode::SUCCESS
}

fn print_help() {
    println!(
        "mesh-convert — convert a Unity Mesh .asset to a Wavefront .obj

Usage:
  mesh-convert <mesh.asset> [--out <path.obj>]

The .obj keeps the standard convention (right-handed coordinates,
bottom-left UV origin, as in the in-game .obj assets): unity-viewer's
loaders convert it to the render space, so the converted mesh renders
identically and opens in Blender unmirrored.
The output path defaults to the input's path with the .obj extension.
"
    );
}

fn run(input: &Path, out: Option<PathBuf>) -> Result<(String, usize, usize), String> {
    let mesh = Mesh::from_file(input).map_err(|e| e.to_string())?;
    let out_path = out.unwrap_or_else(|| {
        let mut p = input.to_path_buf();
        p.set_extension("obj");
        p
    });
    let text = obj_text(&mesh);
    if let Some(parent) = out_path.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("could not create {}: {e}", parent.display()))?;
    }
    std::fs::write(&out_path, text)
        .map_err(|e| format!("could not write {}: {e}", out_path.display()))?;
    Ok((
        out_path.display().to_string(),
        mesh.vertices.len(),
        mesh.indices.len() / 3,
    ))
}

/// The mesh as OBJ text: positions/normals in the file's right-handed
/// convention (the shader input's Z negated) and UVs at the bottom-left
/// origin (the shader input's Vulkan-native v negated), with 1-based
/// `f a/b/c` triangles.
fn obj_text(mesh: &Mesh) -> String {
    let mut out = String::new();
    let name = &mesh.name;
    out.push_str(&format!("# {name}\n"));
    out.push_str("# Converted from Unity .asset by mesh-convert: right-handed\n");
    out.push_str("# (Blender) coordinates, bottom-left UV origin — the standard\n");
    out.push_str("# OBJ convention; unity-viewer's loaders convert it to the\n");
    out.push_str("# render space (world = (-x, y, z), uv = (u, 1 - v)).\n");
    out.push_str(&format!("o {name}\n"));
    for v in &mesh.vertices {
        out.push_str(&format!(
            "v {} {} {}\n",
            v.position[0],
            v.position[1],
            -v.position[2]
        ));
    }
    for v in &mesh.vertices {
        out.push_str(&format!(
            "vn {} {} {}\n",
            v.normal[0],
            v.normal[1],
            -v.normal[2]
        ));
    }
    for v in &mesh.vertices {
        out.push_str(&format!("vt {} {}\n", v.uv[0], 1.0 - v.uv[1]));
    }
    for i in (0..mesh.indices.len()).step_by(3) {
        let (a, b, c) = (
            mesh.indices[i] + 1,
            mesh.indices[i + 1] + 1,
            mesh.indices[i + 2] + 1,
        );
        out.push_str(&format!("f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n"));
    }
    out
}
