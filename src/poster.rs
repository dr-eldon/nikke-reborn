use std::fmt;
use std::fs::File;
use std::io::{self, BufReader};

use serde::Serialize;

use crate::environment;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Poster {
    pub number: usize,
    pub file: String,
    pub name: String,
    pub price: usize,
    pub aspect: Aspect,
}

impl Poster {
    pub fn new(number: usize, file: String, name: String, price: usize) -> io::Result<Self> {
        let mut decoder = png::Decoder::new(BufReader::new(File::open(
            environment::gallery_dir().join(&file).with_extension("png"),
        )?));

        let header = decoder.read_header_info()?;

        let ratio = header.width as f32 / header.height as f32;

        let aspect = if ratio > 1.3 {
            Aspect::Landscape
        } else if ratio < 0.7 {
            Aspect::Portrait
        } else {
            Aspect::Square
        };

        Ok(Self {
            number,
            file,
            name,
            price,
            aspect,
        })
    }

    pub fn file_stem(&self) -> String {
        format!(
            "Poster_{:<04}_{}_{}",
            self.number,
            self.name
                .chars()
                .filter(|c| c.is_ascii_alphanumeric())
                .collect::<String>(),
            self.aspect
        )
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum Aspect {
    Square,
    Portrait,
    Landscape,
}

impl fmt::Display for Aspect {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Aspect::Square => "Square",
            Aspect::Portrait => "Portrait",
            Aspect::Landscape => "Landscape",
        })
    }
}
