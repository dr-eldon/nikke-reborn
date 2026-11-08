use std::cell::RefCell;

use mlua::{
    Lua, MetaMethod, ObjectLike, Result, Table, UserData, UserDataFields, UserDataMethods, Value,
};

use crate::{Image, Viewport};

/// The `spawn`'d producer; the frame's (the viewport's physical) dims.
pub struct Stream {
    viewport: Viewport,
    done: RefCell<bool>,
}

impl UserData for Stream {
    fn add_fields<F: UserDataFields<Stream>>(fields: &mut F) {
        fields.add_meta_field("__name", "Stream");
    }

    fn add_methods<M: UserDataMethods<Stream>>(methods: &mut M) {
        // `for frame in stream` calls the stream as the per-iteration
        // iterator (the nil state/control args): the first call yields
        // the frame, the next nil.
        methods.add_meta_method(
            MetaMethod::Call,
            |lua, this: &Stream, _args: ()| -> Result<Value> {
                if *this.done.borrow() {
                    return Ok(Value::Nil);
                }
                *this.done.borrow_mut() = true;
                let frame = lua.create_userdata(Image::transparent(
                    this.viewport.physical_width(),
                    this.viewport.physical_height(),
                    this.viewport,
                ))?;
                Ok(frame.to_value())
            },
        );
    }
}

pub fn install(lua: &Lua, env: &Table, viewport: Viewport) -> anywho::Result<()> {
    env.set(
        "spawn",
        lua.create_function(
            move |_lua, (_program, _args): (String, Table)| -> Result<Stream> {
                Ok(Stream {
                    viewport,
                    done: RefCell::new(false),
                })
            },
        )?,
    )?;
    Ok(())
}
