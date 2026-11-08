use std::cell::RefCell;
use std::path::{Path, PathBuf};
use std::rc::Rc;

use crate::{font, image, image::Image, rectangle, stream, text};
use anywho::anywho;
use mlua::{AnyUserData, Function, Lua, Table};

/// The compositing engine: the Lua state and the loaded design script.
pub struct Engine {
    script: PathBuf,
    lua: Lua,
    render: Function,
    arguments: Vec<String>,
    /// The script's environment: the op table's home (§6).
    env: Table,
}

impl Engine {
    pub fn load(script: impl AsRef<Path>) -> anywho::Result<Engine> {
        let script = script.as_ref().to_path_buf();
        let source = std::fs::read_to_string(&script)
            .map_err(|e| anywho!("failed to read {}: {e}", script.display()))?;

        let lua = Lua::new();

        // A dedicated environment: the script's globals (and, later,
        // the op table) live here, separate from the engine's.
        let env = lua.create_table()?;
        env.set("_G", env.clone())?;

        let chunk = lua
            .load(source)
            .set_name(script.display().to_string())
            .set_environment(env.clone());

        chunk.call::<()>(())?;

        let render: Function = env.get("render").map_err(|_| {
            anywho!(
                "script {}: 'render' is missing or not a function",
                script.display()
            )
        })?;

        let arguments = arguments(&script, &env)?;

        Ok(Engine {
            script,
            lua,
            render,
            arguments,
            env,
        })
    }

    pub fn script(&self) -> &Path {
        &self.script
    }

    pub fn arguments(&self) -> &[String] {
        &self.arguments
    }

    /// Call the entry with the bound parameters as a single table
    /// keyed by name (`None` binds `nil`), on the canvas of logical
    /// `width`/`height` at the run's `scale`.
    pub fn run(
        &self,
        width: u32,
        height: u32,
        scale: f32,
        params: &[(String, Option<String>)],
    ) -> anywho::Result<()> {
        // The op table (§6): each global is bound by its type's module.
        image::install(&self.lua, &self.env)?;
        font::install(&self.lua, &self.env)?;
        rectangle::install(&self.lua, &self.env)?;
        text::install(&self.lua, &self.env)?;
        stream::install(&self.lua, &self.env, width, height)?;

        self.env.set(
            "width",
            self.lua
                .create_function(move |_lua, _args: ()| -> mlua::Result<u32> { Ok(width) })?,
        )?;
        self.env.set(
            "height",
            self.lua
                .create_function(move |_lua, _args: ()| -> mlua::Result<u32> { Ok(height) })?,
        )?;

        // Logical → physical: × the run's scale, each dim rounded (§5).
        self.env.set(
            "physical_width",
            self.lua
                .create_function(move |_lua, _args: ()| -> mlua::Result<u32> {
                    Ok((width as f32 * scale).round() as u32)
                })?,
        )?;
        self.env.set(
            "physical_height",
            self.lua
                .create_function(move |_lua, _args: ()| -> mlua::Result<u32> {
                    Ok((height as f32 * scale).round() as u32)
                })?,
        )?;

        let yielded = Rc::new(RefCell::new(0u32));
        self.env.set(
            "yield",
            self.lua
                .create_function(move |_lua, frame: AnyUserData| -> mlua::Result<()> {
                    // A frame is canvas-sized (§3b).
                    let frame = frame.borrow::<Image>()?;
                    if (frame.width, frame.height) != (width, height) {
                        return Err(mlua::Error::RuntimeError(format!(
                            "yield: the frame is {}×{}, the canvas is {}×{}",
                            frame.width, frame.height, width, height
                        )));
                    }

                    let n = *yielded.borrow_mut() + 1;
                    eprintln!("yield: frame {n} ({}×{})", frame.width, frame.height);
                    Ok(())
                })?,
        )?;

        let args = self.lua.create_table()?;
        for (name, value) in params {
            args.set(name.as_str(), value.clone())?;
        }
        self.render.call::<()>(args)?;
        Ok(())
    }
}

/// The entry's parameter declaration (§3b).
fn arguments(script: &Path, env: &Table) -> anywho::Result<Vec<String>> {
    let arguments: Table = env
        .get("arguments")
        .map_err(|_| anywho!("script {}: 'arguments' is missing", script.display()))?;

    let mut names = Vec::new();

    for (i, argument) in arguments.sequence_values().enumerate() {
        match argument {
            Ok(name) => names.push(name),
            Err(error) => {
                return Err(anywho!(
                    "script {}: 'arguments' entry {} must be a string ({error})",
                    i + 1,
                    script.display()
                ));
            }
        }
    }

    Ok(names)
}
