// The encode, luma, and stretch consumers land with the compositing
// ops.
#[allow(dead_code)]
mod color;
mod encoder;
mod engine;
mod font;
mod image;
mod rectangle;
mod stream;
mod text;
mod viewport;

use std::collections::BTreeMap;

use anywho::anywho;

use engine::Engine;
pub use image::Image;
pub use viewport::Viewport;

fn main() -> anywho::Result<()> {
    let mut args = std::env::args();
    let _process = args.next();

    let Some(script) = args.next() else {
        println!("{}", help(None));
        std::process::exit(1);
    };

    if script == "--help" {
        println!("{}", help(None));
        std::process::exit(1);
    }

    let engine = Engine::load(script)?;

    let mut show_help = false;
    let mut width = None;
    let mut height = None;
    let mut scale = 1.0;
    let mut values = BTreeMap::new();

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--help" => {
                show_help = true;
            }
            "--width" => {
                let value = args
                    .next()
                    .ok_or_else(|| anywho!("--width requires a value"))?;

                let value: u32 = value
                    .parse()
                    .map_err(|_| anywho!("invalid --width value: {value}"))?;

                if value == 0 {
                    return Err(anywho!(
                        "invalid --width value: {value} (must be greater than 0)"
                    ));
                }

                width = Some(value);
            }
            "--height" => {
                let value = args
                    .next()
                    .ok_or_else(|| anywho!("--height requires a value"))?;

                let value: u32 = value
                    .parse()
                    .map_err(|_| anywho!("invalid --height value: {value}"))?;

                if value == 0 {
                    return Err(anywho!(
                        "invalid --height value: {value} (must be greater than 0)"
                    ));
                }

                height = Some(value);
            }
            "--scale" => {
                let value = args
                    .next()
                    .ok_or_else(|| anywho!("--scale requires a value"))?;

                let value: f32 = value
                    .parse()
                    .map_err(|_| anywho!("invalid --scale value: {value}"))?;

                if value <= 0.0 || !value.is_finite() {
                    return Err(anywho!(
                        "invalid --scale value: {value} (must be a positive number)"
                    ));
                }

                scale = value;
            }
            argument if argument.starts_with('-') => {
                let option = argument.trim_start_matches('-').to_owned();

                if !argument.starts_with("--") || !engine.arguments().contains(&option) {
                    return Err(anywho!("invalid option: {argument}"));
                }

                let value = args
                    .next()
                    .ok_or_else(|| anywho!("{argument} requires a value"))?;

                values.insert(option, value);
            }
            _ => {
                return Err(anywho!("invalid argument: {arg}"));
            }
        }
    }

    if show_help {
        println!("{}", help(Some(&engine)));
        return Ok(());
    }

    let arguments: Vec<_> = engine
        .arguments()
        .iter()
        .map(|argument| {
            (
                argument.clone(),
                values
                    .get(argument)
                    .cloned()
                    .filter(|value| !value.is_empty()),
            )
        })
        .collect();

    let width = width.ok_or_else(|| anywho!("--width is required (see --help)"))?;
    let height = height.ok_or_else(|| anywho!("--height is required (see --help)"))?;

    eprintln!(
        "run: {} {width}×{height} ×{scale} {}",
        engine.script().display(),
        arguments
            .iter()
            .map(|(name, value)| match value {
                Some(value) => format!("{name}={value}"),
                None => format!("{name}=nil"),
            })
            .collect::<Vec<_>>()
            .join(" ")
    );

    engine.run(width, height, scale, &arguments)
}

// --- helpers ---------------------------------------------------------------

fn help(engine: Option<&Engine>) -> String {
    let mut help = String::from(
        "pikke — a compositing engine for Lua design scripts

Usage:
  pikke <script> --width <px> --height <px> [--scale <s>] [options]

Arguments:
  <script>          Path to a design script (.lua)

Options:
  --width <px>      The viewport width in logical px (required)
  --height <px>     The viewport height in logical px (required)
  --scale <s>       The run's scale (default 1)
  --help            Print this help",
    );

    if let Some(engine) = engine {
        help.push_str(&format!(
            "\n\nOptions from the script's entry function ({}):\n",
            engine.script().display(),
        ));

        if engine.arguments().is_empty() {
            help.push_str("  (none)\n");
        } else {
            for argument in engine.arguments() {
                help.push_str(&format!("  --{argument}\n"));
            }
        }
    }

    help.push_str(
        "\nAn omitted or empty option binds nil; values are strings (the\nscript converts where it needs a number).",
    );

    help
}
