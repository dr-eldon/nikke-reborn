use std::path::{Path, PathBuf};

use anywho::anywho;
use mlua::{Function, Lua, Table};

/// The compositing engine: the Lua state and the loaded design script.
pub struct Engine {
    script: PathBuf,
    lua: Lua,
    render: Function,
    arguments: Vec<String>,
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
        })
    }

    pub fn script(&self) -> &Path {
        &self.script
    }

    pub fn arguments(&self) -> &[String] {
        &self.arguments
    }

    /// Call the entry with the bound parameters as a single table
    /// keyed by name (`None` binds `nil`).
    pub fn run(&self, params: &[(String, Option<String>)]) -> anywho::Result<()> {
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
