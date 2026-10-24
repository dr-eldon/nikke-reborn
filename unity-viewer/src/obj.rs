//! Minimal parser for Wavefront `.obj` meshes (as produced by the
//! `mesh-convert` tool from Unity `Mesh` assets, or by Blender).
//!
//! The file holds `v` (position), `vn` (normal) and `vt` (uv0) records and
//! `f` face records in the `a/b/c` (vertex/uv/normal) index form; indices
//! are 1-based (a negative index is relative to the end of its list).
//! Faces may be n-gons; they are fan-triangulated.
//!
//! Coordinate conventions. The `.asset` parser hands the shader raw Unity
//! (left-handed) positions, which the vertex shader turns into the render
//! space with `world = (-x, y, z)`; UVs it converts at load time (Unity
//! UVs have a bottom-left origin; wgpu/Vulkan textures place v=0 at the
//! top row). OBJ files hold the standard right-handed positions with a
//! bottom-left UV origin — the OBJ/Blender convention the in-game assets
//! (e.g. BatA_Mesh.obj) carry. The shader samples UVs verbatim, so to
//! render an OBJ exactly as the equivalent `.asset` renders, this loader
//! inverts the shader's position mapping at load time (file coordinates
//! `(x, y, z)` become shader-input `(x, y, -z)`) and converts the file UV
//! `(u, v)` to `(u, 1 - v)`. The file on disk keeps the standard
//! convention (a converted mesh opens in Blender unmirrored); a mesh
//! converted by `mesh-convert` round-trips through this exactly.
//!
//! Each face corner (a vertex/uv/normal triple) is exploded into its own
//! vertex — the same representation as the `.asset` parser's output — so
//! a vertex shared by different UV seams keeps both sets of attributes.
//!
//! Like the `.asset` parser, the positions are re-centered on the origin
//! (the AABB center subtracted) and the half-extents reported, so both
//! formats feed the orbit camera the same way.

use std::fs;
use std::path::Path;

use thiserror::Error;

use crate::unity::{Mesh, Vertex};

/// Default normal for a corner without a `vn` index (file space: up).
const DEFAULT_NORMAL: [f32; 3] = [0.0, 1.0, 0.0];

/// Default uv0 for a corner without a `vt` index.
const DEFAULT_UV: [f32; 2] = [0.0, 0.0];

#[derive(Debug, Error)]
pub enum Error {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("parse error: {0}")]
    Parse(String),
    #[error("mesh error: {0}")]
    Mesh(String),
}

/// Parse a `.obj` file into a GPU-ready mesh.
pub fn from_file(path: &Path) -> Result<Mesh, Error> {
    let raw = fs::read_to_string(path)?;
    let name = path
        .file_stem()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_else(|| "mesh".to_string());
    parse(&raw, &name)
}

/// One face corner: 0-based vertex index, plus the uv/normal indices or
/// `None` when the corner omits that component.
type Corner = (usize, Option<usize>, Option<usize>);

/// Parse OBJ *text*; *name* is the mesh's display name (a `o` line in the
/// file overrides it).
pub fn parse(raw: &str, name: &str) -> Result<Mesh, Error> {
    let mut name = name.to_string();
    let mut positions: Vec<[f32; 3]> = Vec::new();
    let mut normals: Vec<[f32; 3]> = Vec::new();
    let mut uvs: Vec<[f32; 2]> = Vec::new();
    let mut faces: Vec<Vec<Corner>> = Vec::new();

    for (n, line) in raw.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let (tag, rest) = match line.split_once(' ') {
            Some((t, r)) => (t, r.trim()),
            None => (line, ""),
        };
        match tag {
            "v" => {
                let [x, y, z] = three(rest, "v")?;
                // Invert the shader's .asset mapping (world = (-x, y, z)):
                // the file's right-handed (x, y, z) becomes the shader
                // input (x, y, -z).
                positions.push([x, y, -z]);
            }
            "vn" => {
                let [x, y, z] = three(rest, "vn")?;
                normals.push([x, y, -z]);
            }
            "vt" => {
                let [u, v] = two(rest, "vt")?;
                // The file's bottom-left-origin (u, v) becomes (u, 1 - v):
                // the shader samples UVs verbatim and wgpu/Vulkan textures
                // place v=0 at the top row.
                uvs.push([u, 1.0 - v]);
            }
            "o" => {
                if !rest.is_empty() {
                    name = rest.to_string();
                }
            }
            "f" => {
                let mut corners = Vec::new();
                for part in rest.split_whitespace() {
                    corners.push(corner(part, n, positions.len(), uvs.len(), normals.len())?);
                }
                if corners.len() < 3 {
                    return Err(Error::Parse(format!(
                        "line {n}: face has {} corners, need at least 3",
                        corners.len()
                    )));
                }
                faces.push(corners);
            }
            // g, s, usemtl, mtllib, … — ignored.
            _ => {}
        }
    }

    if positions.is_empty() {
        return Err(Error::Parse("no vertices (v) found".into()));
    }
    if faces.is_empty() {
        return Err(Error::Parse("no faces (f) found".into()));
    }

    // Center on the origin, like the .asset parser.
    let mut min = [f32::INFINITY; 3];
    let mut max = [f32::NEG_INFINITY; 3];
    for p in &positions {
        for i in 0..3 {
            min[i] = min[i].min(p[i]);
            max[i] = max[i].max(p[i]);
        }
    }
    let center = [
        (min[0] + max[0]) / 2.0,
        (min[1] + max[1]) / 2.0,
        (min[2] + max[2]) / 2.0,
    ];
    let extent = [
        (max[0] - min[0]) / 2.0,
        (max[1] - min[1]) / 2.0,
        (max[2] - min[2]) / 2.0,
    ];

    // Explode every face corner into its own vertex (fan-triangulating
    // n-gons along the way).
    let corner_count: usize = faces.iter().map(|f| f.len()).sum();
    if corner_count > u16::MAX as usize {
        return Err(Error::Mesh(format!(
            "{corner_count} face corners exceed the u16 index limit (65536)"
        )));
    }
    let mut vertices: Vec<Vertex> = Vec::with_capacity(corner_count);
    let mut indices: Vec<u16> = Vec::with_capacity(corner_count);
    for face in &faces {
        for k in 1..face.len() - 1 {
            for c in [face[0], face[k], face[k + 1]] {
                let (vi, ti, ni) = c;
                vertices.push(Vertex {
                    position: [
                        positions[vi][0] - center[0],
                        positions[vi][1] - center[1],
                        positions[vi][2] - center[2],
                    ],
                    normal: match ni {
                        Some(i) => normals.get(i).copied().unwrap_or(DEFAULT_NORMAL),
                        None => DEFAULT_NORMAL,
                    },
                    uv: match ti {
                        Some(i) => uvs.get(i).copied().unwrap_or(DEFAULT_UV),
                        None => DEFAULT_UV,
                    },
                });
                indices.push((vertices.len() - 1) as u16);
            }
        }
    }

    Ok(Mesh {
        name,
        vertices,
        indices,
        extent,
        is_skinned: false,
        bone_count: 0,
    })
}

/// `(a/b/c)` — the three 1-based indices of one face corner (a negative
/// index is relative to the end of its list; a missing component is
/// `None`).
fn corner(
    part: &str,
    line: usize,
    v_count: usize,
    t_count: usize,
    n_count: usize,
) -> Result<Corner, Error> {
    let resolve =
        |idx: &str, count: usize, what: &str| -> Result<Option<usize>, Error> {
            if idx.is_empty() {
                return Ok(None);
            }
            let mut i: i64 = idx.parse().map_err(|_| {
                Error::Parse(format!("line {line}: bad {what} index {idx:?}"))
            })?;
            if i <= 0 {
                i += count as i64;
            }
            if i < 1 || i > count as i64 {
                return Err(Error::Mesh(format!(
                    "line {line}: {what} index {i} out of range (1..{count})"
                )));
            }
            Ok(Some(i as usize - 1))
        };
    let mut it = part.splitn(3, '/');
    let vi = resolve(
        it.next().ok_or_else(|| Error::Parse(format!("line {line}: bad face corner {part:?}")))?,
        v_count,
        "vertex",
    )?
    .ok_or_else(|| Error::Parse(format!("line {line}: face corner {part:?} has no vertex index")))?;
    let ti = resolve(it.next().unwrap_or(""), t_count, "uv")?;
    let ni = resolve(it.next().unwrap_or(""), n_count, "normal")?;
    Ok((vi, ti, ni))
}

fn three(s: &str, tag: &str) -> Result<[f32; 3], Error> {
    let nums: Vec<&str> = s.split_whitespace().collect();
    if nums.len() < 3 {
        return Err(Error::Parse(format!("{tag} needs 3 numbers, got {nums:?}")));
    }
    let mut out = [0.0f32; 3];
    for (i, n) in nums.iter().take(3).enumerate() {
        out[i] = n.parse().map_err(|_| {
            Error::Parse(format!("bad {tag} number {}", n))
        })?;
    }
    Ok(out)
}

fn two(s: &str, tag: &str) -> Result<[f32; 2], Error> {
    let nums: Vec<&str> = s.split_whitespace().collect();
    if nums.len() < 2 {
        return Err(Error::Parse(format!("{tag} needs 2 numbers, got {nums:?}")));
    }
    Ok([
        nums[0].parse().map_err(|_| {
            Error::Parse(format!("bad {tag} number {}", nums[0]))
        })?,
        nums[1].parse().map_err(|_| {
            Error::Parse(format!("bad {tag} number {}", nums[1]))
        })?,
    ])
}
