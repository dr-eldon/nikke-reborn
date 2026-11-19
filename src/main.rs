use std::path::PathBuf;

use serde::Serialize;

use nikke_reborn::card;
use nikke_reborn::character;
use nikke_reborn::model;
use nikke_reborn::{Card, Character, Expansion, Result};

#[tokio::main(flavor = "local")]
pub async fn main() -> Result<()> {
    let mut server = server()?;

    let mut standards = Vec::new();
    let mut profiles = Vec::new();
    let mut full_arts = Vec::new();
    let mut boxes = Vec::new();
    let mut packs = Vec::new();

    let expansions = Expansion::list().await?;

    for expansion in expansions.iter() {
        let cards = expansion.cards().await?;

        standards.extend(
            cards
                .iter()
                .filter_map(|card| Standard::new(expansion, card))
                .filter(|standard| !standard.output.is_file()),
        );

        profiles.extend(
            cards
                .iter()
                .filter_map(|card| Profile::new(expansion, card))
                .filter(|profile| !profile.output.is_file()),
        );

        full_arts.extend(
            cards
                .iter()
                .filter_map(|card| FullArt::new(expansion, card))
                .filter(|full_art| !full_art.output.is_file()),
        );

        boxes.push(Box {
            background: expansion.background.clone(),
            characters: expansion.featured.to_vec(),
            logo: expansion.logo.clone(),
            output: expansion.output_dir().join("CardBox_Material.png"),
        });

        packs.push(Pack {
            background: expansion.background.clone(),
            characters: expansion.featured.to_vec(),
            logo: expansion.logo.clone(),
            output: expansion.output_dir().join("CardPack_Material.png"),
        });
    }

    generate("standard", &standards).await?;
    generate("profile", &profiles).await?;
    generate("full_art", &full_arts).await?;
    generate("box", &boxes).await?;
    generate("pack", &packs).await?;

    server.kill().await?;

    Ok(())
}

fn server() -> Result<tokio::process::Child> {
    Ok(tokio::process::Command::new("nikke-viewer")
        .arg("--server")
        .spawn()?)
}

async fn generate(design: &str, jobs: &[impl Serialize]) -> Result<()> {
    use std::process;
    use tokio::io::AsyncWriteExt;

    let mut pikke = tokio::process::Command::new("pikke")
        .arg(format!(
            "{}/design/{design}.lua",
            env!("CARGO_MANIFEST_DIR")
        ))
        .arg("--stdin")
        .args(["--threads", "8"])
        .stdin(process::Stdio::piped())
        .spawn()?;

    let mut stdin = pikke.stdin.take().expect("stdin must be piped");

    for job in jobs {
        stdin
            .write_all(&serde_json::to_vec(job).expect("job must be serializable"))
            .await?;
        stdin.write_all(b"\n").await?;
        stdin.flush().await?;
    }

    drop(stdin);
    dbg!(pikke.wait().await?);

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
            time: card.rarity.time(),
            output: expansion
                .output_dir()
                .join(card.file_name())
                .with_extension("png"),
        })
    }
}

#[derive(Debug, Serialize)]
struct Profile {
    id: String,
    background: String,
    manufacturer: Option<character::Manufacturer>,
    title: String,
    subtitle: Option<String>,
    reel: String,
    output: PathBuf,
}

impl Profile {
    fn new(expansion: &Expansion, card: &Card) -> Option<Self> {
        let card::Rarity::Profile { reel } = &card.rarity else {
            return None;
        };

        Some(Self {
            id: card.model.id.clone(),
            background: card.rarity.background().unwrap_or("sky-night").to_owned(),
            manufacturer: card.character.as_ref().and_then(Character::manufacturer),
            title: card.title(),
            subtitle: card.subtitle(),
            reel: reel.join(","),
            output: expansion
                .output_dir()
                .join(card.file_name())
                .with_extension("png"),
        })
    }
}

#[derive(Debug, Serialize)]
struct FullArt {
    id: String,
    background: Option<String>,
    variant: model::Variant,
    animation: Option<String>,
    time: Option<f32>,
    focus: String,
    output: PathBuf,
}

impl FullArt {
    fn new(expansion: &Expansion, card: &Card) -> Option<Self> {
        if !matches!(
            card.rarity,
            card::Rarity::Special
                | card::Rarity::Exotic
                | card::Rarity::Goddess
                | card::Rarity::Classified,
        ) {
            return None;
        }

        Some(Self {
            id: card.model.id.clone(),
            background: card.rarity.background().map(str::to_owned),
            variant: card.rarity.variant(),
            animation: card.animation.clone(),
            time: card.rarity.time(),
            focus: card.rarity.focus().to_owned(),
            output: expansion
                .output_dir()
                .join(card.file_name())
                .with_extension("png"),
        })
    }
}

#[derive(Debug, Serialize)]
struct Box {
    background: String,
    characters: Vec<character::Featured>,
    logo: Option<String>,
    output: PathBuf,
}

#[derive(Debug, Serialize)]
struct Pack {
    background: String,
    characters: Vec<character::Featured>,
    logo: Option<String>,
    output: PathBuf,
}
