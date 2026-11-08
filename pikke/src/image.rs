use mlua::{AnyUserData, Lua, Result, Table, UserData, UserDataFields, UserDataMethods};

/// The RGBA buffer (physical px; the API reports logical).
#[derive(Clone, Debug)]
pub struct Image {
    pub width: u32,
    pub height: u32,
}

impl UserData for Image {
    fn add_fields<F: UserDataFields<Image>>(fields: &mut F) {
        fields.add_meta_field("__name", "Image");
    }

    fn add_methods<M: UserDataMethods<Image>>(methods: &mut M) {
        methods.add_method("width", |_lua, this, _args: ()| -> Result<u32> {
            Ok(this.width)
        });
        methods.add_method("height", |_lua, this, _args: ()| -> Result<u32> {
            Ok(this.height)
        });
        methods.add_method("size", |_lua, this, _args: ()| -> Result<(u32, u32)> {
            Ok((this.width, this.height))
        });
        methods.add_method("resize", |_lua, this, opts: Table| -> Result<Image> {
            let width = opts
                .get::<Option<f64>>("width")?
                .unwrap_or(this.width as f64)
                .round() as u32;
            let height = opts
                .get::<Option<f64>>("height")?
                .unwrap_or(this.height as f64)
                .round() as u32;
            Ok(Image { width, height })
        });
        methods.add_method("contrast", |_lua, this, _opts: Table| -> Result<Image> {
            Ok(this.clone())
        });
        methods.add_method(
            "blend",
            |_lua, this, (_layer, _opts): (AnyUserData, Option<Table>)| -> Result<Image> {
                Ok(this.clone())
            },
        );
        methods.add_method(
            "fill",
            |_lua, this, (_region, _color): (mlua::Value, String)| -> Result<Image> {
                Ok(this.clone())
            },
        );
        methods.add_method(
            "luma_at",
            |_lua, _this, _region: mlua::Value| -> Result<f64> { Ok(0.0) },
        );
    }
}

pub fn install(lua: &Lua, env: &Table) -> anywho::Result<()> {
    env.set(
        "image",
        lua.create_function(|_lua, _path: String| -> Result<Image> {
            Ok(Image {
                width: 1,
                height: 1,
            })
        })?,
    )?;
    Ok(())
}
