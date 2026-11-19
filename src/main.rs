use std::path::{Path, PathBuf};

use serde::Serialize;

use nikke_reborn::card;
use nikke_reborn::character;
use nikke_reborn::environment;
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

        read_dir(environment::images_dir().join("shop"), async |file| {
            copy(file, expansion.output_dir()).await
        })
        .await?;

        copy(
            environment::images_dir().join("Foilmask.png"),
            expansion.output_dir(),
        )
        .await?;

        let bundle = expansion.bundle().await?;

        tokio::fs::write(
            environment::output_dir()
                .join(&expansion.id)
                .with_extension("json"),
            &serde_json::to_string_pretty(&bundle).expect("bundle must be serializable"),
        )
        .await?;
    }

    generate("standard", &standards).await?;
    generate("profile", &profiles).await?;
    generate("full_art", &full_arts).await?;
    generate("box", &boxes).await?;
    generate("pack", &packs).await?;

    for box_ in boxes {
        snapshot(&box_.output, "CardBox_Mesh", true).await?;
    }

    for pack in packs {
        snapshot(&pack.output, "CardPackStatic_Mesh_low", false).await?;
    }

    server.kill().await?;

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
        let card::Rarity::Profile = &card.rarity else {
            return None;
        };

        Some(Self {
            id: card.model.id.clone(),
            background: card.rarity.background().unwrap_or("sky-night").to_owned(),
            manufacturer: card.character.as_ref().and_then(Character::manufacturer),
            title: card.title(),
            subtitle: card.subtitle(),
            reel: card.reel.join(","),
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

fn server() -> Result<tokio::process::Child> {
    Ok(tokio::process::Command::new("nikke-viewer")
        .arg("--server")
        .kill_on_drop(true)
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
    pikke.wait().await?;

    Ok(())
}

async fn snapshot(material: &Path, mesh: &str, copy: bool) -> Result<()> {
    let mesh = PathBuf::from(format!(
        "{}/assets/meshes/{mesh}.obj",
        env!("CARGO_MANIFEST_DIR")
    ));

    let mut unity_viewer = tokio::process::Command::new("unity-viewer")
        .arg(&mesh)
        .arg(material)
        .arg("--config")
        .arg(mesh.with_extension("json"))
        .arg("--out")
        .arg(
            material
                .with_file_name(
                    material
                        .file_name()
                        .expect("material must have a filename")
                        .to_string_lossy()
                        .replace("_Material", "_Item"),
                )
                .with_extension("png"),
        )
        .spawn()?;

    unity_viewer.wait().await?;

    if copy {
        tokio::fs::copy(
            &mesh,
            material.with_file_name(mesh.file_name().expect("mesh must have a filename")),
        )
        .await?;
    }

    Ok(())
}

async fn read_dir(path: impl AsRef<Path>, f: impl AsyncFn(&Path) -> Result<()>) -> Result<()> {
    let mut read_dir = tokio::fs::read_dir(path).await?;

    while let Some(entry) = read_dir.next_entry().await? {
        f(&entry.path()).await?;
    }

    Ok(())
}

async fn copy(source: impl AsRef<Path>, destination: impl AsRef<Path>) -> Result<()> {
    let source = source.as_ref();
    let destination = destination
        .as_ref()
        .join(source.file_name().expect("source must have a filename"));

    println!("{}", destination.display());

    let _ = tokio::fs::copy(source, destination).await?;

    Ok(())
}
