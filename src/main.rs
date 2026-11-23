use std::env;
use std::path::{Path, PathBuf};
use std::process;
use std::sync::atomic::{self, AtomicBool};

use serde::Serialize;
use serde_json::json;

use nikke_reborn::card;
use nikke_reborn::environment;
use nikke_reborn::{Card, Character, Expansion, Quality, Result};

static DRY: AtomicBool = AtomicBool::new(false);

#[tokio::main(flavor = "local")]
pub async fn main() -> Result<()> {
    let mut args = env::args().peekable();
    let _process = args.next();

    let mut quality = Quality::default();

    while let Some(option) = args.peek().cloned()
        && option.starts_with("--")
    {
        let _ = args.next();

        match option.as_str() {
            "--dry" => {
                DRY.store(true, atomic::Ordering::Relaxed);
            }
            "--ultra" => {
                quality = Quality::Ultra;
            }
            "--low" => {
                quality = Quality::Low;
            }
            _ => {
                eprintln!("unknown option: {option}");
                process::exit(1);
            }
        }
    }

    let expansion_target = args.next();

    let mut server = server()?;

    let mut standards = Vec::new();
    let mut profiles = Vec::new();
    let mut full_arts = Vec::new();
    let mut packs = Vec::new();
    let mut boxes = Vec::new();
    let mut sleeves = Vec::new();
    let mut posters = Vec::new();
    let mut poster_icons = Vec::new();

    let expansions = Expansion::list().await?;

    for expansion in expansions.iter() {
        if let Some(target) = &expansion_target
            && expansion.id != *target
        {
            continue;
        }

        let output = expansion.output_dir(quality);
        tokio::fs::create_dir_all(&output).await?;

        let cards = expansion.cards().await?;

        standards.extend(
            cards
                .iter()
                .filter_map(|card| standard(expansion, card, quality))
                .filter(|standard| !standard.is_done()),
        );

        profiles.extend(
            cards
                .iter()
                .filter_map(|card| profile(expansion, card, quality))
                .filter(|profile| !profile.is_done()),
        );

        full_arts.extend(
            cards
                .iter()
                .filter_map(|card| full_art(expansion, card, quality))
                .filter(|full_art| !full_art.is_done()),
        );

        packs.push(job(
            output.join("CardPack_Material.png"),
            json!({
                "background": expansion.background.clone(),
                "characters": expansion.featured.to_vec(),
                "logo": expansion.logo.clone(),
            }),
        ));

        boxes.push(job(
            output.join("CardBox_Material.png"),
            json!({
                "background": expansion.background.clone(),
                "characters": expansion.featured.to_vec(),
                "logo": expansion.logo.clone(),
            }),
        ));

        sleeves.extend(expansion.sleeves.iter().map(|sleeve| {
            job(
                output
                    .join(format!("{}_Material", sleeve.file_name()))
                    .with_extension("png"),
                json!({
                    "id": sleeve.model.id,
                    "background": sleeve.background,
                    "title": sleeve.model.name(),
                    "skin": sleeve.skin,
                    "variant": sleeve.variant,
                    "animation": sleeve.animation,
                    "focus": sleeve.focus,
                    "zoom": sleeve.zoom,
                    "time": sleeve.time,
                    "offset_x": sleeve.offset_x,
                    "portrait": sleeve.portrait,
                }),
            )
        }));

        for poster in expansion.posters.iter() {
            posters.push(job(
                output
                    .join(format!("{}_Art", poster.file_stem()))
                    .with_extension("png"),
                json!({
                    "file": poster.file,
                    "aspect": poster.aspect,
                }),
            ));

            poster_icons.push(job(
                output
                    .join(format!("{}_Icon", poster.file_stem()))
                    .with_extension("png"),
                json!({ "file": poster.file }),
            ));
        }

        read_dir(environment::images_dir().join("shop"), async |file| {
            copy(file, &output).await
        })
        .await?;

        copy(environment::images_dir().join("Foilmask.png"), &output).await?;
        copy(environment::images_dir().join("Cardback.png"), &output).await?;

        let bundle = expansion.bundle().await?;

        tokio::fs::write(
            environment::output_dir()
                .join(expansion.file_name())
                .with_extension("json"),
            &serde_json::to_string_pretty(&bundle).expect("bundle must be serializable"),
        )
        .await?;
    }

    packs.retain(|pack| !pack.is_done());
    boxes.retain(|box_| !box_.is_done());
    sleeves.retain(|sleeve| !sleeve.is_done());
    posters.retain(|poster| !poster.is_done());
    poster_icons.retain(|icon| !icon.is_done());

    generate("standard", &standards, quality).await?;
    generate("profile", &profiles, quality).await?;
    generate("full_art", &full_arts, quality).await?;
    generate("box", &boxes, quality).await?;
    generate("pack", &packs, quality).await?;
    generate("sleeve", &sleeves, quality).await?;
    generate("poster", &posters, quality).await?;
    generate("poster_icon", &poster_icons, quality).await?;

    for box_ in boxes {
        snapshot(&box_.output, "CardBox_Mesh", true, quality).await?;
    }

    for pack in packs {
        snapshot(&pack.output, "CardPackStatic_Mesh_low", false, quality).await?;
    }

    for sleeve in sleeves {
        snapshot(&sleeve.output, "CardSleeve_Mesh_low", false, quality).await?;
    }

    server.kill().await?;

    Ok(())
}

fn standard(expansion: &Expansion, card: &Card, quality: Quality) -> Option<Job> {
    if !matches!(
        card.rarity,
        card::Rarity::Standard | card::Rarity::Rare | card::Rarity::Cover | card::Rarity::Aim
    ) {
        return None;
    }

    Some(job(
        expansion
            .output_dir(quality)
            .join(card.file_name())
            .with_extension("png"),
        json!({
            "id": card.model.id.clone(),
            "background": card.rarity.background().unwrap_or("sky-night").to_owned(),
            "manufacturer": card
                .model
                .character
                .as_ref()
                .and_then(Character::manufacturer),
            "title": card.model.title(),
            "subtitle": card.model.subtitle(),
            "variant": card.rarity.variant(),
            "animation": card.animation.clone(),
            "time": card.rarity.time(),
            "focus": card.focus().to_owned(),
        }),
    ))
}

fn profile(expansion: &Expansion, card: &Card, quality: Quality) -> Option<Job> {
    let card::Rarity::Profile = &card.rarity else {
        return None;
    };

    Some(job(
        expansion
            .output_dir(quality)
            .join(card.file_name())
            .with_extension("png"),
        json!({
            "id": card.model.id.clone(),
            "background": card.rarity.background().unwrap_or("sky-night").to_owned(),
            "manufacturer": card
                .model
                .character
                .as_ref()
                .and_then(Character::manufacturer),
            "title": card.model.title(),
            "subtitle": card.model.subtitle(),
            "reel": card.reel.join(","),
            "skin": card.skin.clone(),
        }),
    ))
}

fn full_art(expansion: &Expansion, card: &Card, quality: Quality) -> Option<Job> {
    if !matches!(
        card.rarity,
        card::Rarity::Special
            | card::Rarity::Exotic
            | card::Rarity::Goddess
            | card::Rarity::Classified,
    ) {
        return None;
    }

    Some(job(
        expansion
            .output_dir(quality)
            .join(card.file_name())
            .with_extension("png"),
        json!({
            "id": card.model.id.clone(),
            "background": card.rarity.background().map(str::to_owned),
            "variant": card.rarity.variant(),
            "skin": card.skin.clone(),
            "animation": card.animation.clone(),
            "time": card.rarity.time(),
            "focus": card.focus().to_owned(),
        }),
    ))
}

fn server() -> Result<tokio::process::Child> {
    Ok(tokio::process::Command::new("nikke-viewer")
        .arg("--server")
        .kill_on_drop(true)
        .spawn()?)
}

async fn generate(design: &str, jobs: &[Job], quality: Quality) -> Result<()> {
    use std::process;
    use tokio::io::AsyncWriteExt;

    if DRY.load(atomic::Ordering::Relaxed) {
        println!("{design}: {} jobs", jobs.len());
        return Ok(());
    }

    let mut pikke = tokio::process::Command::new("pikke")
        .arg(format!(
            "{}/design/{design}.lua",
            env!("CARGO_MANIFEST_DIR")
        ))
        .arg("--stdin")
        .arg("--release")
        .args(["--threads", "8"])
        .arg("--scale")
        .arg(format!("{:.2}", quality.scale()))
        .arg("--scale-video")
        .arg(format!("{:.2}", quality.scale_video()))
        .arg("--framerate")
        .arg(quality.framerate().to_string())
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

async fn snapshot(material: &Path, mesh: &str, copy: bool, quality: Quality) -> Result<()> {
    if DRY.load(atomic::Ordering::Relaxed) {
        println!("{}: {mesh} copy={copy}", material.display());
        return Ok(());
    }

    let mesh = PathBuf::from(format!(
        "{}/assets/meshes/{mesh}.obj",
        env!("CARGO_MANIFEST_DIR")
    ));

    let size = ((1024.0 * quality.scale()) as u32).to_string();

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
        .args(["--width", &size])
        .args(["--height", &size])
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

    let root = env!("CARGO_MANIFEST_DIR");

    if DRY.load(atomic::Ordering::Relaxed) {
        println!(
            "{} -> {}",
            source.strip_prefix(root).unwrap_or(source).display(),
            destination
                .strip_prefix(root)
                .unwrap_or(destination.as_path())
                .display()
        );
        return Ok(());
    }

    println!("{}", destination.display());
    let _ = tokio::fs::copy(source, destination).await?;

    Ok(())
}

#[derive(Debug, Serialize)]
struct Job {
    output: PathBuf,
    #[serde(flatten)]
    metadata: serde_json::Value,
}

impl Job {
    fn is_done(&self) -> bool {
        self.output.is_file()
    }
}

fn job(output: PathBuf, metadata: serde_json::Value) -> Job {
    Job { output, metadata }
}
