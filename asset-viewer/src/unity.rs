//! Minimal parser for Unity `Mesh` asset files (as produced by the Nikke
//! Reborn card pipeline).
//!
//! The files are plain YAML with two hex blobs:
//!
//! * `m_IndexBuffer` — little-endian `u16` triangle indices,
//! * `m_VertexData._typelessdata` — the concatenated vertex attribute blob.
//!
//! The blob holds one array per *stream*: stream starts are 8-byte aligned
//! and each vertex within a stream is `round4(max(offset + dim * elem_size))`
//! bytes wide. Attributes are listed by channel slot in `m_Channels`
//! (`stream`, `offset`, `format`, `dimension`); formats seen: `0` = f32,
//! `1` = f16, `10` = f32 (blend weights).
//!
//! We decode position (slot 0), normal (slot 1, whose `dimension` field is
//! bogus in these files) and uv0. Skinned meshes carry blend indices/weights;
//! they are rendered in **bind pose** (identity bone matrices), so those
//! attributes are ignored.

use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

use thiserror::Error;

#[derive(Debug, Error)]
pub enum Error {
    #[error("io error: {0}")]
    Io(#[from] std::io::Error),
    #[error("parse error: {0}")]
    Parse(String),
    #[error("vertex layout error: {0}")]
    Layout(String),
}

/// A GPU-ready vertex: origin-centered position, normal, uv0.
#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct Vertex {
    pub position: [f32; 3],
    pub normal: [f32; 3],
    pub uv: [f32; 2],
}

/// A parsed mesh (vertex positions already centered on the origin).
#[derive(Debug)]
pub struct Mesh {
    pub name: String,
    pub vertices: Vec<Vertex>,
    pub indices: Vec<u16>,
    /// Half-extents of the local AABB.
    pub extent: [f32; 3],
    pub is_skinned: bool,
    pub bone_count: usize,
}

impl Mesh {
    /// Largest AABB half-extent — used to frame the orbit camera.
    pub fn radius(&self) -> f32 {
        self.extent.iter().copied().fold(0.0, f32::max)
    }

    pub fn triangle_count(&self) -> usize {
        self.indices.len() / 3
    }

    pub fn from_file(path: &Path) -> Result<Self, Error> {
        let raw = fs::read_to_string(path)?;
        Self::parse(&raw)
    }

    fn parse(raw: &str) -> Result<Self, Error> {
        let text = raw.replace('\r', "");
        let d = Doc(&text);

        let name = d.scalar("m_Name").unwrap_or("mesh").trim().to_string();
        let usage_flags: i64 = d
            .scalar("m_MeshUsageFlags")
            .and_then(|s| s.trim().parse().ok())
            .unwrap_or(0);
        let center = vec3(
            d.scalar("m_Center")
                .ok_or_else(|| Error::Parse("missing localAABB m_Center".into()))?,
        )
        .ok_or_else(|| Error::Parse("bad m_Center value".into()))?;
        let extent = vec3(
            d.scalar("m_Extent")
                .ok_or_else(|| Error::Parse("missing localAABB m_Extent".into()))?,
        )
        .ok_or_else(|| Error::Parse("bad m_Extent value".into()))?;
        let index_count: usize = d
            .scalar("indexCount")
            .and_then(|s| s.trim().parse().ok())
            .ok_or_else(|| Error::Parse("missing submesh indexCount".into()))?;
        let vertex_count: usize = d
            .scalar("m_VertexCount")
            .and_then(|s| s.trim().parse().ok())
            .ok_or_else(|| Error::Parse("missing m_VertexCount".into()))?;
        let bone_count = bone_count(&text);
        let is_skinned = usage_flags != 0 || bone_count > 0;

        // --- index buffer -------------------------------------------------
        let index_hex = d
            .scalar("m_IndexBuffer")
            .ok_or_else(|| Error::Parse("missing m_IndexBuffer".into()))?;
        let indices = decode_u16_le(index_hex, index_count, vertex_count)?;

        // --- vertex data --------------------------------------------------
        let Some(vd) = d.index_of("m_VertexData:") else {
            return Err(Error::Parse("missing m_VertexData".into()));
        };
        let Some(ds) = d.index_from(vd, "m_DataSize:") else {
            return Err(Error::Parse("missing m_DataSize".into()));
        };
        let data_size: usize = d
            .scalar_from(ds, "m_DataSize")
            .and_then(|s| s.trim().parse().ok())
            .ok_or_else(|| Error::Parse("bad m_DataSize".into()))?;
        let Some(tx) = d.index_from(ds, "_typelessdata:") else {
            return Err(Error::Parse("missing _typelessdata".into()));
        };
        let line_end = text[tx..].find('\n').map(|i| tx + i).unwrap_or(text.len());
        let hex = text[tx + "_typelessdata:".len()..line_end].trim();
        let data =
            decode_hex(hex).ok_or_else(|| Error::Parse("_typelessdata is not valid hex".into()))?;
        if data.len() != data_size {
            return Err(Error::Layout(format!(
                "vertex data size mismatch: got {} bytes, m_DataSize = {}",
                data.len(),
                data_size
            )));
        }

        // Channel table: `(stream, offset, format, dimension)` per slot, in
        // slot order. The normal slot's dimension is bogus in these files
        // (52), so pick the attributes we care about by shape.
        let channels = parse_channels(&text[vd..ds]);
        if channels.len() < 2 {
            return Err(Error::Parse("m_Channels too short".into()));
        }
        let (pos, normal, uv) = pick_channels(&channels)?;

        // Per-vertex span of each stream = the end (offset + dim*elem) of the
        // highest-offset attribute in that stream. All channels are considered
        // (not just pos/normal/uv) so the blend index/weight streams stay in the
        // layout; a non-highest attribute with a bogus dimension (the normal's
        // "52") can never exceed the last attribute, so it cannot inflate it.
        let mut highest: BTreeMap<u32, (u32, u32)> = BTreeMap::new(); // stream -> (offset, end)
        for (stream, offset, format, dim) in &channels {
            if *offset == 0 && *dim == 0 {
                continue; // empty slot
            }
            let end = offset.saturating_add(dim.saturating_mul(elem_size(*format)?));
            match highest.get_mut(stream) {
                Some((best_off, best_end)) => {
                    if *offset >= *best_off {
                        *best_off = *offset;
                        *best_end = end;
                    }
                }
                None => {
                    highest.insert(*stream, (*offset, end));
                }
            }
        }
        let stream_span: BTreeMap<u32, u32> =
            highest.into_iter().map(|(s, (_, end))| (s, end)).collect();
        if stream_span.is_empty() {
            return Err(Error::Parse("no vertex attribute channels".into()));
        }

        // Stream placement: 8-byte aligned starts, per-stream stride = round4(span).
        let n_streams = stream_span.len();
        let mut starts = vec![0u64; n_streams];
        let mut cursor = 0u64;
        for (k, (_stream, span)) in stream_span.iter().enumerate() {
            starts[k] = cursor;
            let stride = round4(*span) as u64;
            cursor += stride * vertex_count as u64;
            if k + 1 < n_streams {
                cursor = round8(cursor);
            }
        }
        if cursor > data_size as u64 {
            return Err(Error::Layout(format!(
                "vertex streams ({cursor} bytes) exceed the blob ({data_size} bytes)"
            )));
        }
        let tail = data_size as u64 - cursor;
        if tail > 256 || tail % 8 != 0 {
            return Err(Error::Layout(format!(
                "suspicious {tail}-byte tail after the vertex streams"
            )));
        }
        // Decode positions / normals / uvs. Each attribute steps by its
        // *stream's* per-vertex stride and is read at its own offset.
        let (p_stream, p_off, p_fmt, p_dim) = pos;
        let (n_stream, n_off, n_fmt, n_dim) = normal;
        let (u_stream, u_off, u_fmt, u_dim) = uv;
        let span_of = |s: u32| round4(*stream_span.get(&s).unwrap_or(&0)) as u64;
        let p_stride = span_of(p_stream);
        let n_stride = span_of(n_stream);
        let u_stride = span_of(u_stream);
        let p_base = stream_starts(
            stream_span.keys().position(|s| s == &p_stream).unwrap_or(0),
            &starts,
        );
        let n_base = stream_starts(
            stream_span.keys().position(|s| s == &n_stream).unwrap_or(0),
            &starts,
        );
        let u_base = stream_starts(
            stream_span.keys().position(|s| s == &u_stream).unwrap_or(0),
            &starts,
        );

        let mut vertices = Vec::with_capacity(vertex_count);
        let mut out_of_bounds = 0usize;
        let eps = extent.iter().copied().fold(0.0, f32::max).max(1e-4) * 1e-3 + 1e-4;
        for v in 0..vertex_count {
            let position = read_floats(
                &data,
                (p_base + p_stride * v as u64) as usize,
                p_off as usize,
                p_fmt,
                p_dim as usize,
            )?;
            let normal = read_floats(
                &data,
                (n_base + n_stride * v as u64) as usize,
                n_off as usize,
                n_fmt,
                n_dim as usize,
            )?;
            let uv = read_floats(
                &data,
                (u_base + u_stride * v as u64) as usize,
                u_off as usize,
                u_fmt,
                u_dim as usize,
            )?;

            let in_aabb = (0..3).all(|i| {
                position[i] <= center[i] + extent[i] + eps
                    && position[i] >= center[i] - extent[i] - eps
            });
            if !in_aabb {
                out_of_bounds += 1;
            }

            vertices.push(Vertex {
                position: [
                    position[0] - center[0],
                    position[1] - center[1],
                    position[2] - center[2],
                ],
                normal,
                uv: [uv[0], uv[1]],
            });
        }
        if out_of_bounds > vertex_count / 50 {
            return Err(Error::Layout(format!(
                "vertex layout sanity check failed: {out_of_bounds}/{vertex_count} positions outside localAABB"
            )));
        }

        Ok(Mesh {
            name,
            vertices,
            indices,
            extent,
            is_skinned,
            bone_count,
        })
    }
}

/// `key: value` — the value is the rest of the line, trimmed.
struct Doc<'a>(&'a str);

impl<'a> Doc<'a> {
    fn scalar(&self, key: &str) -> Option<&'a str> {
        self.scalar_from(0, key)
    }

    fn scalar_from(&self, from: usize, key: &str) -> Option<&'a str> {
        let needle = format!("{key}:");
        let idx = self.index_from(from, &needle)? + needle.len();
        let end = self.0[idx..]
            .find('\n')
            .map(|i| idx + i)
            .unwrap_or(self.0.len());
        Some(self.0[idx..end].trim())
    }

    fn index_of(&self, needle: &str) -> Option<usize> {
        self.index_from(0, needle)
    }

    fn index_from(&self, from: usize, needle: &str) -> Option<usize> {
        self.0[from..].find(needle).map(|i| from + i)
    }
}

/// `{x: 0.0, y: -0.0, z: 0.0}` → `[x, y, z]`.
fn vec3(value: &str) -> Option<[f32; 3]> {
    let value = value.trim().trim_start_matches('{').trim_end_matches('}');
    let mut out = [0.0f32; 3];
    for (i, part) in value.split(',').take(3).enumerate() {
        out[i] = part
            .trim()
            .split_once(':')
            .and_then(|(_, v)| v.trim().parse().ok())?;
    }
    Some(out)
}

/// Entry count of the `m_BoneNameHashes:` block (0 for `[]`).
fn bone_count(text: &str) -> usize {
    let Some(idx) = text.find("m_BoneNameHashes:") else {
        return 0;
    };
    let rest = &text[idx + "m_BoneNameHashes:".len()..];
    let mut count = 0usize;
    for line in rest.lines() {
        let t = line.trim();
        if t.starts_with("- ") {
            count += 1;
        } else if !t.is_empty() && !t.starts_with('[') {
            break;
        }
    }
    count
}

/// `(stream, offset, format, dimension)` entries of the last `m_Channels`.
fn parse_channels(block: &str) -> Vec<(u32, u32, u32, u32)> {
    let mut out = Vec::new();
    let mut cur = [0u32; 4];
    let mut have = [false; 4];
    for line in block.lines() {
        let t = line.trim();
        if let Some(v) = t.strip_prefix("- stream:") {
            cur[0] = v.trim().parse().unwrap_or(0);
            have = [true, false, false, false];
        } else if let Some(v) = t.strip_prefix("offset:") {
            cur[1] = v.trim().parse().unwrap_or(0);
            have[1] = true;
        } else if let Some(v) = t.strip_prefix("format:") {
            cur[2] = v.trim().parse().unwrap_or(0);
            have[2] = true;
        } else if let Some(v) = t.strip_prefix("dimension:") {
            cur[3] = v.trim().parse().unwrap_or(0);
            have[3] = true;
            if have.iter().all(|&h| h) {
                out.push((cur[0], cur[1], cur[2], cur[3]));
            }
        } else if t.starts_with("m_DataSize") {
            break;
        }
    }
    out
}

/// Pick (position, normal, uv0) from the channel list, correcting the
/// bogus dimensions along the way.
fn pick_channels(
    channels: &[(u32, u32, u32, u32)],
) -> Result<
    (
        (u32, u32, u32, u32),
        (u32, u32, u32, u32),
        (u32, u32, u32, u32),
    ),
    Error,
> {
    // Position: first channel (f32 × 3 in these files).
    let pos = channels
        .iter()
        .find(|c| c.3 == 3 && c.2 != 1)
        .or_else(|| channels.first())
        .ok_or_else(|| Error::Parse("no position channel".into()))?;
    // Normal: dim 3 (or the bogus 52) channel that is not the position.
    let normal = channels
        .iter()
        .find(|c| (c.3 == 3 || c.3 == 52) && !(c.0 == pos.0 && c.1 == pos.1 && c.2 == pos.2))
        .ok_or_else(|| Error::Parse("no normal channel".into()))?;
    // UV0: the (first) dim 2 channel.
    let uv = channels
        .iter()
        .find(|c| c.3 == 2)
        .ok_or_else(|| Error::Parse("no uv0 channel".into()))?;

    Ok((
        (pos.0, pos.1, pos.2, 3),
        (normal.0, normal.1, normal.2, 3),
        (uv.0, uv.1, uv.2, 2),
    ))
}

fn elem_size(format: u32) -> Result<u32, Error> {
    match format {
        0 | 10 => Ok(4),
        1 => Ok(2),
        other => Err(Error::Parse(format!("unsupported channel format {other}"))),
    }
}

fn round4(x: u32) -> u32 {
    (x + 3) & !3
}

fn round8(x: u64) -> u64 {
    (x + 7) & !7
}

/// Start offset of the k-th stream (streams are sorted by id).
fn stream_starts(k: usize, starts: &[u64]) -> u64 {
    starts[k.min(starts.len() - 1)]
}

/// Read `count` little-endian f32/f16 values.
fn read_floats(
    data: &[u8],
    base: usize,
    offset: usize,
    format: u32,
    count: usize,
) -> Result<[f32; 3], Error> {
    let elem = elem_size(format)? as usize;
    let start = base + offset;
    if start + elem * count > data.len() {
        return Err(Error::Layout(
            "vertex attribute read would go out of bounds".into(),
        ));
    }
    let mut out = [0.0f32; 3];
    for i in 0..count.min(3) {
        let at = start + i * elem;
        out[i] = if format == 1 {
            f16_to_f32(u16::from_le_bytes([data[at], data[at + 1]]))
        } else {
            f32::from_bits(u32::from_le_bytes([
                data[at],
                data[at + 1],
                data[at + 2],
                data[at + 3],
            ]))
        };
    }
    Ok(out)
}

fn f16_to_f32(bits: u16) -> f32 {
    let sign = (bits >> 15) & 1;
    let exp = (bits >> 10) & 0x1f;
    let frac = (bits & 0x3ff) as f32;
    let magnitude = if exp == 0 {
        frac * 2f32.powi(-24)
    } else if exp == 0x1f {
        if frac == 0.0 { f32::INFINITY } else { f32::NAN }
    } else {
        (1.0 + frac / 1024.0) * 2f32.powi(exp as i32 - 15)
    };
    if sign == 1 { -magnitude } else { magnitude }
}

fn decode_hex(hex: &str) -> Option<Vec<u8>> {
    let hex = hex.trim();
    if hex.len() % 2 != 0 {
        return None;
    }
    Some(
        (0..hex.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&hex[i..i + 2], 16))
            .collect::<Result<_, _>>()
            .ok()?,
    )
}

/// Decode the hex index blob into `u16` LE indices.
fn decode_u16_le(hex: &str, expected: usize, vertex_count: usize) -> Result<Vec<u16>, Error> {
    let bytes = decode_hex(hex).ok_or_else(|| Error::Parse("bad m_IndexBuffer hex".into()))?;
    if bytes.len() < expected * 2 {
        return Err(Error::Parse(format!(
            "index buffer too short: {} bytes for {expected} indices",
            bytes.len()
        )));
    }
    let mut out = Vec::with_capacity(expected);
    for i in 0..expected {
        let idx = u16::from_le_bytes([bytes[i * 2], bytes[i * 2 + 1]]) as usize;
        if idx >= vertex_count {
            return Err(Error::Layout(format!(
                "index {idx} out of range (vertex_count = {vertex_count})"
            )));
        }
        out.push(idx as u16);
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn repo_assets(name: &str) -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../assets")
            .join(name)
    }

    fn assert_sane(mesh: &Mesh, expected_vertex_count: usize) {
        assert_eq!(mesh.vertices.len(), expected_vertex_count);
        assert!(!mesh.indices.is_empty(), "mesh has indices");
        assert!(
            mesh.indices.len() % 3 == 0,
            "index count must be multiple of 3"
        );
        for idx in mesh.indices.iter() {
            assert!((*idx as usize) < mesh.vertices.len(), "index in range");
        }
        // Normals should be roughly unit length and finite.
        for v in mesh.vertices.iter() {
            assert!(v.normal.iter().all(|c| c.is_finite()), "normal finite");
            let len =
                (v.normal[0] * v.normal[0] + v.normal[1] * v.normal[1] + v.normal[2] * v.normal[2])
                    .sqrt();
            assert!(len > 0.05 && len < 20.0, "normal length {len} sane");
            assert!(v.position.iter().all(|c| c.is_finite()), "position finite");
            assert!(v.uv.iter().all(|c| c.is_finite()), "uv finite");
        }
        // Positions should be origin-centered: max |position| ~ within extent.
        let max_extent = mesh.extent.iter().cloned().fold(0.0, f32::max);
        let max_pos = mesh
            .vertices
            .iter()
            .map(|v| v.position[0].abs() + v.position[1].abs() + v.position[2].abs())
            .fold(0.0f32, f32::max);
        // Sum of abs can be up to ~3*extent; be generous.
        assert!(
            max_pos < max_extent * 4.0 + 1e-3,
            "positions centered (max {max_pos} vs extent {max_extent})"
        );
    }

    #[test]
    fn parses_cardpack_static_mesh() {
        let mesh = Mesh::from_file(&repo_assets("CardPackStatic_Mesh.asset")).unwrap();
        println!(
            "static: name={} verts={} tris={} skinned={} bones={} extent={:?}",
            mesh.name,
            mesh.vertices.len(),
            mesh.triangle_count(),
            mesh.is_skinned,
            mesh.bone_count,
            mesh.extent
        );
        assert_eq!(mesh.vertices.len(), 525, "static mesh vertex count");
        assert!(!mesh.is_skinned);
        assert_sane(&mesh, 525);
    }

    #[test]
    fn parses_cardpack_skinned_mesh() {
        let mesh = Mesh::from_file(&repo_assets("CardPack_Mesh.asset")).unwrap();
        println!(
            "skinned: name={} verts={} tris={} skinned={} bones={} extent={:?}",
            mesh.name,
            mesh.vertices.len(),
            mesh.triangle_count(),
            mesh.is_skinned,
            mesh.bone_count,
            mesh.extent
        );
        assert_eq!(mesh.vertices.len(), 1325, "skinned mesh vertex count");
        assert!(mesh.is_skinned);
        assert_eq!(mesh.bone_count, 7);
        assert_sane(&mesh, 1325);
    }
}

#[cfg(test)]
mod material_tests {
    use std::path::Path;

    #[test]
    fn decodes_a_png_material() {
        let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("../images/Cardback.png");
        if !path.exists() {
            eprintln!("skipping: {}", path.display());
            return;
        }
        let bytes = std::fs::read(&path).unwrap();
        let img = ::image::load_from_memory(&bytes).unwrap();
        let rgba = img.to_rgba8();
        assert!(rgba.width() > 0 && rgba.height() > 0);
        assert_eq!(
            rgba.as_raw().len(),
            (rgba.width() * rgba.height() * 4) as usize
        );
        eprintln!(
            "Cardback.png decoded: {}x{} ({} RGBA bytes)",
            rgba.width(),
            rgba.height(),
            rgba.as_raw().len()
        );
    }
}
