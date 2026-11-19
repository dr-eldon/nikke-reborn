use std::path::{Path, PathBuf};
use std::sync::{Arc, OnceLock};

use serde::{Deserialize, Serialize};
use serde_json::json;
use tokio::fs;
use tokio::process;

use crate::card;
use crate::character;
use crate::environment;
use crate::model;
use crate::{Card, Character, Error, Quality, Result};

#[derive(Debug, Clone, PartialEq)]
pub struct Expansion {
    pub id: String,
    pub logo: Option<String>,
    pub background: String,
    pub featured: Arc<[character::Featured]>,
    pub models: Arc<[Model]>,
    pub cards: Arc<OnceLock<Vec<Card>>>,
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
            logo: Option<String>,
            background: String,
            featured: Vec<character::Featured>,
            models: Vec<_Model>,
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
            .models
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
            logo: expansion.logo,
            background: expansion.background,
            featured: Arc::from(expansion.featured),
            models,
            cards: Arc::default(),
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

    pub async fn cards(&self) -> Result<&[Card]> {
        if let Some(cards) = self.cards.get() {
            return Ok(cards);
        }

        let characters = Character::map();
        let models = model::Model::map();
        let mut cards = Vec::new();

        for (i, model) in self.models.iter().enumerate() {
            let Some(metadata) = models.get(&model.id) else {
                return Err(Error::ModelNotFound(model.id.clone()));
            };

            let number = i + 1;
            let animation = model.options.animation().map(str::to_owned);

            if model.is_event() {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    animation: animation.clone(),
                    rarity: card::Rarity::Classified,
                    character: None,
                    reel: Vec::new(),
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
                number,
                model: metadata.clone(),
                animation: animation.clone(),
                rarity: card::Rarity::Standard,
                character: character.cloned(),
                reel: reel.clone(),
            });

            if let Some(animation) = reel.get(1) {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    animation: Some(animation.clone()),
                    rarity: card::Rarity::Rare,
                    character: character.cloned(),
                    reel: reel.clone(),
                });
            }

            cards.push(Card {
                number,
                model: metadata.clone(),
                animation: animation.clone(),
                rarity: card::Rarity::Profile,
                character: character.cloned(),
                reel: reel.clone(),
            });

            if variants.contains(&"cover".to_owned()) {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    animation: animation.clone(),
                    rarity: card::Rarity::Cover,
                    character: character.cloned(),
                    reel: reel.clone(),
                });
            }

            if variants.contains(&"aim".to_owned()) {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    animation: animation.clone(),
                    rarity: card::Rarity::Aim,
                    character: character.cloned(),
                    reel: reel.clone(),
                });
            }

            if let Some(animation) = reel.first() {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    animation: Some(animation.clone()),
                    rarity: card::Rarity::Special,
                    character: character.cloned(),
                    reel: reel.clone(),
                });
            }

            if animations.contains(&"action".to_owned()) {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    animation: Some("action".to_owned()),
                    rarity: card::Rarity::Exotic,
                    character: character.cloned(),
                    reel: reel.clone(),
                });
            }

            if variants.contains(&"sc".to_owned()) && model.goddess.is_enabled() {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    animation: Some(
                        model
                            .goddess
                            .animation()
                            .map(str::to_owned)
                            .or_else(|| animation.clone())
                            .unwrap_or_else(|| "main".to_owned()),
                    ),
                    rarity: card::Rarity::Goddess,
                    character: character.cloned(),
                    reel: reel.clone(),
                });
            }
        }

        let _ = self.cards.set(cards);

        Ok(self.cards.get().unwrap())
    }

    pub fn output_dir(&self, quality: Quality) -> PathBuf {
        environment::output_dir().join(format!("{}{}", self.id.clone(), quality.suffix()))
    }

    fn bundle_id(&self) -> String {
        format!("NIKKE_REBORN_{}", self.id)
    }

    pub async fn bundle(&self) -> Result<Bundle> {
        let bundle = self.bundle_id();

        Ok(Bundle(json!({
            "Name": bundle,
            "BundleId": bundle,
            "AutoCompressTextures": true,
            "MaxTextureSize": 2048,
            "TextureCompression": "BC7",
            "EnableMipMaps": false,
            "Assemblies": [],
            "Items": [pack(self), box_(self)],
            "CardExpansions": [expansion(self).await?],
            "CustomShops": [custom_shop()],
        })))
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

#[derive(Debug, Clone, Serialize)]
pub struct Bundle(serde_json::Value);

const PHONE_APP_ID: &str = "NIKKE_REBORN";

fn pack(expansion: &Expansion) -> serde_json::Value {
    let bundle = expansion.bundle_id();

    #[derive(Default)]
    struct Slot {
        profile: f64,
        rare: f64,
        cover: f64,
        aim: f64,
        special: f64,
        exotic: f64,
        goddess: f64,
        classified: f64,
    }

    fn slot(slot: Slot) -> serde_json::Value {
        let total = slot.profile
            + slot.rare
            + slot.cover
            + slot.aim
            + slot.special
            + slot.exotic
            + slot.goddess
            + slot.classified;

        json!({
            "Standard": 100.0 - total,
            "Profile": slot.profile,
            "Rare": slot.rare,
            "Cover": slot.cover,
            "Aim": slot.aim,
            "Special": slot.special,
            "Exotic": slot.exotic,
            "Goddess": slot.goddess,
            "Classified": slot.classified,
        })
    }

    let common = slot(Slot {
        profile: 2.0,
        rare: 0.5,
        ..Slot::default()
    });

    let uncommon = slot(Slot {
        profile: 6.0,
        rare: 2.0,
        cover: 1.0,
        aim: 1.0,
        special: 0.5,
        exotic: 0.1,
        ..Slot::default()
    });

    let rare = slot(Slot {
        rare: 4.0,
        cover: 3.0,
        aim: 3.0,
        special: 1.5,
        exotic: 1.0,
        goddess: 0.2,
        classified: 0.1,
        ..Slot::default()
    });

    json!({
        "Name": format!("{} Packs", expansion.name()),
        "CardExpansion": bundle,
        "PackType": format!("{bundle}_CardPack"),
        "ItemType": format!("{bundle}_CardPack_Item"),
        "Material": "CardPack_Material",
        "SpriteName": "CardPack_Item",
        "BaseCost": 2,
        "SmallBoxLicensePrice": 50,
        "SmallBoxLicenseLevelRequirement": 1,
        "LicensePrice": 300,
        "LicenseLevelRequirement": 5,
        "SlotWeights": {
          "Slot1": common,
          "Slot2": common,
          "Slot3": common,
          "Slot4": common,
          "Slot5": uncommon,
          "Slot6": uncommon,
          "Slot7": rare,
        },
        "ItemCategory": "TCG",
        "AddItemAsAccessory": false,
        "AddItemAsFigurine": false,
        "AddItemAsBoardGame": false,
        "PhoneAppId": PHONE_APP_ID,
        "UsesBaseGameMesh": true,
        "MeshToUse": "BasicCardPack",
        "Mesh": "",
        "MaterialList": [],
        "IsBigBox": true,
        "BigBoxHideTillUnlocked": false,
        "IgnoreDoubleImage": false,
        "HasSmallBox": true,
        "SmallBoxHideTillUnlocked": false,
        "SmallBoxIgnoreDoubleImage": false,
        "IsBulkBox": false,
        "MinMarketPricePercent": 1,
        "MaxMarketPricePercent": 1.20000005,
        "FollowItemPrice": "None",
        "AutoSetBoxPrice": false,
        "IsTallItem": false,
        "InBoxOffsetY": 0,
        "InBoxOffsetScale": 0,
        "ItemDeminsion": {
          "x": 1,
          "y": 1,
          "z": 1
        },
        "CollidorPosOffset": {
          "x": 0,
          "y": 0,
          "z": 0
        },
        "ColliderScale": {
          "x": 1,
          "y": 1,
          "z": 1
        },
        "PriceAffectedBy": [],
        "IsCardPack": true,
        "IsCardBox": false,
        "MinValue": 0,
        "CanHaveDuplicates": false,
        "CanHaveGodPacks": false,
        "GodPackPercentage": 0.000199999995,
        "PackGenerationStrategy": "Guaranteed",
        "SpawnsPackType": "",
        "NormalWeights": {},
        "GodWeights": {}
    })
}

fn box_(expansion: &Expansion) -> serde_json::Value {
    let bundle = expansion.bundle_id();

    json!({
        "Name": format!("{} Box", expansion.name()),
        "Material": "CardBox_Material",
        "SpriteName": "CardBox_Item",
        "ItemType": format!("{bundle}_CardBox_Item"),
        "SpawnsPackType": format!("{bundle}_CardPack_Item"),
        "SmallBoxLicensePrice": 100,
        "SmallBoxLicenseLevelRequirement": 3,
        "LicensePrice": 500,
        "LicenseLevelRequirement": 8,
        "ItemCategory": "TCG",
        "BaseCost": 0,
        "AddItemAsAccessory": false,
        "AddItemAsFigurine": false,
        "AddItemAsBoardGame": false,
        "PhoneAppId": PHONE_APP_ID,
        "UsesBaseGameMesh": false,
        "MeshToUse": "",
        "Mesh": "CardBox_Mesh",
        "MaterialList": [],
        "IsBigBox": true,
        "BigBoxHideTillUnlocked": false,
        "IgnoreDoubleImage": false,
        "HasSmallBox": true,
        "SmallBoxHideTillUnlocked": false,
        "SmallBoxIgnoreDoubleImage": false,
        "IsBulkBox": false,
        "MinMarketPricePercent": 1,
        "MaxMarketPricePercent": 1.20000005,
        "FollowItemPrice": "None",
        "AutoSetBoxPrice": true,
        "IsTallItem": false,
        "InBoxOffsetY": 0,
        "InBoxOffsetScale": -0.2,
        "ItemDeminsion": {
          "x": 2,
          "y": 4,
          "z": 1
        },
        "CollidorPosOffset": {
          "x": 0,
          "y": 0,
          "z": 0
        },
        "ColliderScale": {
          "x": 0.18,
          "y": 0.15,
          "z": 0.1
        },
        "PriceAffectedBy": [],
        "IsCardPack": false,
        "IsCardBox": true,
        "MinValue": 0,
        "CardExpansion": "",
        "CanHaveDuplicates": false,
        "CanHaveGodPacks": false,
        "GodPackPercentage": 0.0,
        "PackGenerationStrategy": "Guaranteed",
        "PackType": "",
        "NormalWeights": {},
        "GodWeights": {},
        "SlotWeights": {}
    })
}

async fn expansion(expansion: &Expansion) -> Result<serde_json::Value> {
    let bundle = expansion.bundle_id();

    let cards = expansion
        .cards()
        .await?
        .iter()
        .map(card)
        .collect::<Vec<_>>();

    Ok(json!({
        "Name": format!("{} Set", expansion.name()),
        "CardExpansion": bundle,
        "Cards": cards,
        "MenuCategory": "NIKKE",
        "CardbackSprite": "Cardback",
        "FoilMask": "Foilmask",
        "Rarities": [
          "Standard",
          "Profile",
          "Rare",
          "Cover",
          "Aim",
          "Special",
          "Exotic",
          "Goddess",
          "Classified"
        ],
        "HasRandomFoils": false,
        "FoilChance": 0,
        "CardPriceStrategy": "RarityDriven",
        "DefaultBorderMultiplierBase": 3.15,
        "DefaultFoilMultiplier": 10.0,
        "RarityDrivenFloor": 0.03,
        "RarityDrivenStepSize": 0.2,
        "RarityDrivenBorderMultiplierBase": 5.0,
        "RarityDrivenFoilMultiplier": 2.0,
        "PlayCardMaterials": []
    }))
}

fn card(card: &Card) -> serde_json::Value {
    json!({
        "Name": card.name(),
        "Rarity": card.rarity,
        "BorderType": card.border(),
        "Sprite": card.file_name(),
        "IsFoil": card.rarity.is_foil(),
        "ElementType": "None",
        "FoilMask": "",
        "CardBack": ""
    })
}

fn custom_shop() -> serde_json::Value {
    json!({
        "PhoneAppId": PHONE_APP_ID,
        "AppDisplayName": "NIKKE",
        "AppIcon": "Shop_Icon",
        "AppInnerBGImage": "Shop_IBG",
        "AppOuterBGImage": "Shop_OBG",
        "SiteLogo": "Shop_Logo",
        "SiteHeader": "Shop_Banner",
        "SiteBackground": "Shop_Wallpaper"
    })
}
