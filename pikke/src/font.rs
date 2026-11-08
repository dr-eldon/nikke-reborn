use mlua::{Lua, Result, Table, UserData, UserDataFields};

pub struct Font;

impl UserData for Font {
    fn add_fields<F: UserDataFields<Font>>(fields: &mut F) {
        fields.add_meta_field("__name", "Font");
    }
}

pub fn install(lua: &Lua, env: &Table) -> anywho::Result<()> {
    env.set(
        "font",
        lua.create_function(|_lua, _path: String| -> Result<Font> { Ok(Font) })?,
    )?;
    Ok(())
}
