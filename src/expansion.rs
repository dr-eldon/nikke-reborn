use std::path::Path;
use std::sync::Arc;

use serde::Deserialize;
use tokio::fs;
use tokio::process;

use crate::card;
use crate::model;
use crate::{Card, Character, Error, Result};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Expansion {
    pub id: String,
    pub models: Arc<[Model]>,
}

impl Expansion {
    pub async fn list() -> Result<Arc<[Self]>> {
        let mut expansions = Vec::new();

        let mut read_dir = fs::read_dir(format!("{}/cards", env!("CARGO_MANIFEST_DIR"))).await?;

        while let Some(entry) = read_dir.next_entry().await? {
            if !entry.metadata().await?.is_file() {
                continue;
            }

            if entry
                .path()
                .extension()
                .is_none_or(|extension| extension != "toml")
            {
                continue;
            }

            let Ok(expansion) = Self::load(entry.path()).await else {
                continue;
            };

            expansions.push(expansion);
        }

        Ok(Arc::from(expansions))
    }

    pub async fn load(path: impl AsRef<Path>) -> Result<Self> {
        #[derive(Debug, Deserialize)]
        struct _Expansion {
            cards: Vec<_Model>,
        }

        #[derive(Debug, Deserialize)]
        struct _Model {
            id: String,
            #[serde(flatten)]
            options: Options,
            #[serde(rename = "Goddess", default)]
            goddess: Options,
        }

        let path = path.as_ref();
        let metadata = fs::read_to_string(&path).await?;
        let expansion: _Expansion = toml::from_str(&metadata)?;

        let models = expansion
            .cards
            .into_iter()
            .map(|model| Model {
                id: model.id,
                options: model.options,
                goddess: model.goddess,
            })
            .collect();

        Ok(Self {
            id: path
                .file_stem()
                .expect("expansion must have file stem")
                .to_string_lossy()
                .into_owned(),
            models,
        })
    }

    pub fn name(&self) -> String {
        let mut name = String::new();

        let indices = self
            .id
            .char_indices()
            .filter_map(|(i, c)| (i > 0 && c.is_uppercase()).then_some(i));

        let mut start = 0;

        for index in indices {
            name.push_str(&self.id[start..index]);
            name.push(' ');

            start = index;
        }

        name.push_str(&self.id[start..]);
        name
    }

    pub async fn cards(&self) -> Result<Vec<Card>> {
        let characters = Character::map();
        let models = model::Model::map();
        let mut cards = Vec::new();

        for model in self.models.iter() {
            let Some(metadata) = models.get(&model.id) else {
                return Err(Error::ModelNotFound(model.id.clone()));
            };

            let animation = model.options.animation().map(str::to_owned);

            if model.is_event() {
                cards.push(Card {
                    model: metadata.clone(),
                    animation: animation.clone(),
                    rarity: card::Rarity::Classified,
                    character: None,
                });
                continue;
            }

            let character = characters.get(
                model
                    .id
                    .split("_")
                    .next()
                    .expect("character id must not be empty"),
            );

            let variants = nikke_viewer(&model.id, "--list-variants").await?;
            let animations = nikke_viewer(&model.id, "--list-animations").await?;

            cards.push(Card {
                model: metadata.clone(),
                animation: animation.clone(),
                rarity: card::Rarity::Standard,
                character: character.cloned(),
            });

            let reel: Vec<_> = {
                const CANDIDATES: &[&str] = &[
                    "special",
                    "special_02",
                    "shy",
                    "good",
                    "delight",
                    "surprise",
                    "surprised",
                    "smile",
                    "think",
                    "serious",
                    "no",
                    "etc",
                    "angry",
                    "worry",
                    "pain",
                    "cry",
                ];

                CANDIDATES
                    .iter()
                    .copied()
                    .map(str::to_owned)
                    .filter(|candidate| animations.contains(candidate))
                    .take(3)
                    .collect()
            };

            cards.push(Card {
                model: metadata.clone(),
                animation: animation.clone(),
                rarity: card::Rarity::Profile { reel: reel.clone() },
                character: character.cloned(),
            });

            if variants.contains(&"cover".to_owned()) {
                cards.push(Card {
                    model: metadata.clone(),
                    animation: animation.clone(),
                    rarity: card::Rarity::Cover,
                    character: character.cloned(),
                });
            }

            if variants.contains(&"aim".to_owned()) {
                cards.push(Card {
                    model: metadata.clone(),
                    animation: animation.clone(),
                    rarity: card::Rarity::Aim,
                    character: character.cloned(),
                });
            }

            if let Some(animation) = reel.get(1) {
                cards.push(Card {
                    model: metadata.clone(),
                    animation: Some(animation.clone()),
                    rarity: card::Rarity::Rare,
                    character: character.cloned(),
                });
            }

            if let Some(animation) = reel.first() {
                cards.push(Card {
                    model: metadata.clone(),
                    animation: Some(animation.clone()),
                    rarity: card::Rarity::Special,
                    character: character.cloned(),
                });
            }

            if variants.contains(&"sc".to_owned()) && model.goddess.is_enabled() {
                cards.push(Card {
                    model: metadata.clone(),
                    animation: model
                        .goddess
                        .animation()
                        .map(str::to_owned)
                        .or_else(|| animation.clone()),
                    rarity: card::Rarity::Goddess,
                    character: character.cloned(),
                });
            }
        }

        Ok(cards)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Model {
    pub id: String,
    pub options: Options,
    pub goddess: Options,
}

impl Model {
    pub fn is_event(&self) -> bool {
        self.id
            .strip_prefix('c')
            .is_none_or(|rest| rest.chars().next().is_some_and(|c| !c.is_ascii_digit()))
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Default, Deserialize)]
#[serde(untagged)]
pub enum Options {
    Toggled(bool),
    Customized {
        animation: Option<String>,
    },
    #[default]
    Default,
}

impl Options {
    pub fn is_enabled(&self) -> bool {
        match self {
            Options::Toggled(enabled) => *enabled,
            Options::Customized { .. } | Options::Default => true,
        }
    }

    pub fn animation(&self) -> Option<&str> {
        match self {
            Options::Customized { animation } => animation.as_deref(),
            Options::Toggled(_) | Options::Default => None,
        }
    }
}

async fn nikke_viewer(model: &str, flag: &str) -> Result<Vec<String>> {
    let output = process::Command::new("nikke-viewer")
        .arg(model)
        .arg(flag)
        .output()
        .await?;

    Ok(String::from_utf8_lossy_owned(output.stdout)
        .lines()
        .map(str::to_owned)
        .collect())
}
