use std::cell::RefCell;

use crate::image::Image;
use mlua::{
    Lua, MetaMethod, ObjectLike, Result, Table, UserData, UserDataFields, UserDataMethods, Value,
};

/// The `spawn`'d producer; the frame's (logical canvas) dims.
pub struct Stream {
    pub width: u32,
    pub height: u32,
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
                let frame = lua.create_userdata(Image {
                    width: this.width,
                    height: this.height,
                })?;
                Ok(frame.to_value())
            },
        );
    }
}

pub fn install(lua: &Lua, env: &Table, width: u32, height: u32) -> anywho::Result<()> {
    env.set(
        "spawn",
        lua.create_function(
            move |_lua, (_program, _args): (String, Table)| -> Result<Stream> {
                Ok(Stream {
                    width,
                    height,
                    done: RefCell::new(false),
                })
            },
        )?,
    )?;
    Ok(())
}
