use mlua::{Lua, Result, Table, UserData, UserDataFields, UserDataMethods};

pub struct Rectangle;

impl UserData for Rectangle {
    fn add_fields<F: UserDataFields<Rectangle>>(fields: &mut F) {
        fields.add_meta_field("__name", "Rectangle");
    }

    fn add_methods<M: UserDataMethods<Rectangle>>(methods: &mut M) {
        methods.add_method("padded", |_lua, _this, _pad: f64| -> Result<Rectangle> {
            Ok(Rectangle)
        });
    }
}

pub fn install(lua: &Lua, env: &Table) -> anywho::Result<()> {
    env.set(
        "rectangle",
        lua.create_function(|_lua, _opts: Table| -> Result<Rectangle> { Ok(Rectangle) })?,
    )?;
    Ok(())
}
