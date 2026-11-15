use std::path::{Path, PathBuf};

use serde::Serialize;

use nikke_reborn::card;
use nikke_reborn::character;
use nikke_reborn::model;
use nikke_reborn::{Card, Character, Expansion, Result};

#[tokio::main(flavor = "local")]
pub async fn main() -> Result<()> {
    let mut standards = Vec::new();

    let expansions = Expansion::list().await?;

    for expansion in expansions.iter() {
        let cards = expansion.cards().await?;

        standards.extend(
            cards
                .iter()
                .filter_map(|card| Standard::new(expansion, card)),
        );
    }

    for standard in standards {
        if standard.output.is_file() {
            continue;
        }

        println!(
            "{}",
            serde_json::to_string(&standard).expect("standard design must be serializable")
        );
    }

    Ok(())
}

#[derive(Debug, Serialize)]
struct Standard {
    id: String,
    background: String,
    manufacturer: Option<character::Manufacturer>,
    title: String,
    subtitle: Option<String>,
    variant: model::Variant,
    animation: Option<String>,
    time: Option<f32>,
    output: PathBuf,
}

impl Standard {
    fn new(expansion: &Expansion, card: &Card) -> Option<Self> {
        if !matches!(
            card.rarity,
            card::Rarity::Standard | card::Rarity::Rare | card::Rarity::Cover | card::Rarity::Aim
        ) {
            return None;
        }

        Some(Self {
            id: card.model.id.clone(),
            background: card.rarity.background().unwrap_or("sky-night").to_owned(),
            manufacturer: card.character.as_ref().and_then(Character::manufacturer),
            title: card.title(),
            subtitle: card.subtitle(),
            variant: card.rarity.variant(),
            animation: card.animation.clone(),
            time: Some(0.0),
            output: output_dir()
                .join(format!("{}_Ultra", expansion.id.clone()))
                .join(card.file_name())
                .with_extension("png"),
        })
    }
}

fn output_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("output")
}
