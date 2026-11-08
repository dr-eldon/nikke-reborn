use crate::rectangle::Rectangle;
use mlua::{Lua, Result, Table, UserData, UserDataFields, UserDataMethods};

pub struct Text;

impl UserData for Text {
    fn add_fields<F: UserDataFields<Text>>(fields: &mut F) {
        fields.add_meta_field("__name", "Text");
    }

    fn add_methods<M: UserDataMethods<Text>>(methods: &mut M) {
        methods.add_method("bounds", |_lua, _this, _args: ()| -> Result<Rectangle> {
            Ok(Rectangle)
        });
    }
}

pub fn install(lua: &Lua, env: &Table) -> anywho::Result<()> {
    env.set(
        "text",
        lua.create_function(|_lua, (_s, _opts): (String, Table)| -> Result<Text> { Ok(Text) })?,
    )?;
    Ok(())
}
