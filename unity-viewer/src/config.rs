//! Import/export of the viewer's adjustable state — the asset rotation and
//! the camera's zoom/pan — as a small JSON file:
//!
//! ```json
//! {
//!   "model":  { "yaw": 60.0, "pitch": 15.0, "roll": -10.0 },
//!   "camera": { "zoom": 1.18, "pan": [0.0, -0.02, 0.0] }
//! }
//! ```
//!
//! Angles are in degrees. The camera's viewing pose (yaw/pitch/roll) is
//! fixed by `scene::Camera::default` and intentionally not part of the
//! configuration: the file captures exactly what the GUI can set, and the
//! CLI renders the same state.

use std::path::Path;

use crate::scene;

/// Asset rotation in degrees (the GUI's Yaw/Pitch/Roll sliders). Missing
/// fields (or a missing `model` key) are zero.
#[derive(Debug, Clone, Copy, Default, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(default)]
pub struct Model {
    /// Turntable around world up.
    pub yaw: f32,
    /// Tilt of the asset.
    pub pitch: f32,
    /// Twist in the asset's plane.
    pub roll: f32,
}

/// The camera's adjustable state. Missing fields (or a missing `camera`
/// key entirely) fall back to the GUI's fixed default camera.
#[derive(Debug, Clone, Copy, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(default)]
pub struct Camera {
    #[serde(default = "default_zoom")]
    /// Zoom factor (1.0 = fitted framing).
    pub zoom: f32,
    #[serde(default = "default_pan")]
    /// Orbit target (world).
    pub pan: [f32; 3],
}

fn default_zoom() -> f32 {
    scene::Camera::default().zoom
}

fn default_pan() -> [f32; 3] {
    scene::Camera::default().pan
}

impl Default for Camera {
    fn default() -> Self {
        Self {
            zoom: default_zoom(),
            pan: default_pan(),
        }
    }
}

/// The viewer configuration: the asset rotation and the camera's zoom/pan.
/// Any missing key or field falls back to the GUI's defaults.
#[derive(Debug, Clone, Copy, Default, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(default)]
pub struct Config {
    pub model: Model,
    pub camera: Camera,
}

impl Config {
    /// Capture the current state: the asset rotation (degrees) and the
    /// camera's zoom/pan.
    pub fn capture(model: scene::Model, camera: scene::Camera) -> Self {
        Self {
            model: Model {
                yaw: model.yaw.to_degrees(),
                pitch: model.pitch.to_degrees(),
                roll: model.roll.to_degrees(),
            },
            camera: Camera {
                zoom: camera.zoom,
                pan: camera.pan,
            },
        }
    }

    /// The state this configuration describes: the asset rotation, and a
    /// camera at its fixed default pose with the given zoom/pan.
    pub fn to_state(&self) -> (scene::Model, scene::Camera) {
        (
            scene::Model {
                yaw: self.model.yaw.to_radians(),
                pitch: self.model.pitch.to_radians(),
                roll: self.model.roll.to_radians(),
            },
            scene::Camera {
                zoom: self.camera.zoom,
                pan: self.camera.pan,
                ..scene::Camera::default()
            },
        )
    }

    /// Read and validate a configuration file.
    pub fn load(path: &Path) -> Result<Self, String> {
        let bytes = std::fs::read(path)
            .map_err(|e| format!("failed to read {}: {e}", path.display()))?;
        let config: Self = serde_json::from_slice(&bytes)
            .map_err(|e| format!("invalid configuration {}: {e}", path.display()))?;
        if config.camera.zoom <= 0.0 {
            return Err(format!(
                "invalid configuration {}: camera.zoom must be > 0",
                path.display()
            ));
        }
        Ok(config)
    }

    /// Write the configuration as pretty-printed JSON.
    pub fn save(&self, path: &Path) -> Result<(), String> {
        let json = serde_json::to_string_pretty(self)
            .map_err(|e| format!("failed to encode configuration: {e}"))?;
        std::fs::write(path, json + "\n")
            .map_err(|e| format!("failed to write {}: {e}", path.display()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_path(name: &str) -> std::path::PathBuf {
        std::env::temp_dir().join(format!(
            "unity-viewer-config-{name}-{}.json",
            std::process::id()
        ))
    }

    fn sample() -> Config {
        Config {
            model: Model {
                yaw: 60.0,
                pitch: 15.0,
                roll: -10.0,
            },
            camera: Camera {
                zoom: 1.5,
                pan: [1.0, -2.0, 3.0],
            },
        }
    }

    #[test]
    fn round_trips_through_a_file() {
        let path = temp_path("roundtrip");
        sample().save(&path).expect("save");
        let text = std::fs::read_to_string(&path).expect("read");
        // Human-readable JSON with the documented shape.
        assert!(text.contains("\"yaw\": 60.0"), "{text}");
        assert!(text.contains("\"pan\": ["), "{text}");
        let loaded = Config::load(&path).expect("load");
        std::fs::remove_file(&path).ok();
        assert_eq!(loaded.model, sample().model);
        assert_eq!(loaded.camera, sample().camera);
    }

    #[test]
    fn capture_and_to_state_round_trip() {
        let model = scene::Model {
            yaw: 1.0,
            pitch: -0.5,
            roll: 0.25,
        };
        let camera = scene::Camera {
            zoom: 2.0,
            pan: [1.0, 2.0, 3.0],
            ..scene::Camera::default()
        };
        let (m2, c2) = Config::capture(model, camera).to_state();
        // The degrees round-trip is exact to well within a slider step.
        assert!((m2.yaw - model.yaw).abs() < 1e-4);
        assert!((m2.pitch - model.pitch).abs() < 1e-4);
        assert!((m2.roll - model.roll).abs() < 1e-4);
        assert_eq!(c2.zoom, 2.0);
        assert_eq!(c2.pan, [1.0, 2.0, 3.0]);
        // The fixed viewing pose always comes from the default.
        assert_eq!(c2.yaw, scene::Camera::default().yaw);
    }

    #[test]
    fn missing_fields_fall_back_to_the_gui_defaults() {
        // Model only.
        let cfg: Config = serde_json::from_str(r#"{"model":{"yaw":30.0}}"#).expect("parse");
        assert_eq!(
            cfg.model,
            Model {
                yaw: 30.0,
                pitch: 0.0,
                roll: 0.0
            }
        );
        assert_eq!(cfg.camera.zoom, scene::Camera::default().zoom);
        assert_eq!(cfg.camera.pan, scene::Camera::default().pan);
        // Camera only, pan omitted.
        let cfg: Config = serde_json::from_str(r#"{"camera":{"zoom":2.0}}"#).expect("parse");
        assert_eq!(cfg.model, Model::default());
        assert_eq!(cfg.camera.zoom, 2.0);
        assert_eq!(cfg.camera.pan, scene::Camera::default().pan);
        // Empty object: the whole GUI default state.
        let cfg: Config = serde_json::from_str("{}").expect("parse");
        assert_eq!(cfg.model, Model::default());
        assert_eq!(cfg.camera, Camera::default());
    }

    #[test]
    fn load_reports_errors() {
        // Missing file.
        assert!(Config::load(Path::new("/nonexistent/uv-config.json")).is_err());
        // Bad JSON.
        let path = temp_path("bad");
        std::fs::write(&path, "{ not json").expect("write");
        assert!(Config::load(&path).is_err());
        // Valid JSON, but zoom must be > 0.
        std::fs::write(
            &path,
            r#"{"model":{"yaw":0,"pitch":0,"roll":0},"camera":{"zoom":0,"pan":[0,0,0]}}"#,
        )
        .expect("write");
        let err = Config::load(&path).expect_err("zoom 0 must be rejected");
        assert!(err.contains("zoom"), "{err}");
        std::fs::remove_file(&path).ok();
    }
}
