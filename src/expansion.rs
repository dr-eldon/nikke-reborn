use std::path::{Path, PathBuf};
use std::sync::{Arc, OnceLock};

use function::Binary;
use serde::{Deserialize, Serialize};
use serde_json::json;
use tokio::fs;
use tokio::process;

use crate::card;
use crate::environment;
use crate::model;
use crate::{Card, Deckbox, Error, Model, Poster, Quality, Result, Sleeve};

#[derive(Debug, Clone, PartialEq)]
pub struct Expansion {
    pub id: String,
    pub number: usize,
    pub logo: Option<String>,
    pub background: serde_json::Value,
    pub featured: Arc<[serde_json::Value]>,
    pub models: Arc<[_Model]>,
    pub cards: Arc<OnceLock<Vec<Card>>>,
    pub sleeves: Arc<[Sleeve]>,
    pub deckboxes: Arc<[Deckbox]>,
    pub posters: Arc<[Poster]>,
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

            let expansion = Self::load(entry.path()).await?;

            expansions.push(expansion);
        }

        expansions.sort_by_key(|expansion| expansion.number);

        Ok(Arc::from(expansions))
    }

    pub async fn load(path: impl AsRef<Path>) -> Result<Self> {
        #[derive(Debug, Deserialize)]
        struct _Expansion {
            logo: Option<String>,
            background: serde_json::Value,
            featured: Vec<serde_json::Value>,
            models: Vec<_Model>,
            #[serde(default)]
            sleeves: Vec<_Sleeve>,
            #[serde(default)]
            deckboxes: Vec<_Deckbox>,
            #[serde(default)]
            posters: Vec<_Poster>,
        }

        #[derive(Debug, Deserialize)]
        struct _Sleeve {
            id: String,
            background: String,
            skin: Option<String>,
            variant: Option<String>,
            animation: Option<String>,
            focus: Option<String>,
            zoom: Option<f32>,
            #[serde(default)]
            time: f32,
            #[serde(default)]
            offset_x: f32,
            portrait: String,
        }

        #[derive(Debug, Deserialize)]
        struct _Deckbox {
            id: String,
            skin: Option<String>,
            variant: Option<String>,
            animation: Option<String>,
            focus: Option<String>,
            zoom: Option<f32>,
            #[serde(default)]
            time: f32,
            #[serde(default)]
            offset_x: f32,
            #[serde(default)]
            offset_y: f32,
            color: Option<String>,
        }

        #[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
        struct _Poster {
            file: String,
            name: String,
            price: usize,
        }

        let path = path.as_ref();
        let metadata = fs::read_to_string(&path).await?;
        let expansion: _Expansion = toml::from_str(&metadata)?;

        let file_stem = path
            .file_stem()
            .expect("expansion must have file stem")
            .to_string_lossy();

        let (number, id) = file_stem
            .split_once('_')
            .expect("expansion must have number and name");

        let models = Model::map();

        let sleeves = expansion
            .sleeves
            .into_iter()
            .enumerate()
            .map(|(i, sleeve)| Sleeve {
                number: i + 1,
                model: models
                    .get(&sleeve.id)
                    .expect("sleeve model id must be valid")
                    .clone(),
                background: sleeve.background,
                skin: sleeve.skin,
                variant: sleeve.variant,
                animation: sleeve.animation,
                focus: sleeve.focus,
                time: sleeve.time,
                zoom: sleeve.zoom.unwrap_or(1.0),
                offset_x: sleeve.offset_x,
                portrait: sleeve.portrait,
            })
            .collect::<Vec<_>>();

        let deckboxes = expansion
            .deckboxes
            .into_iter()
            .enumerate()
            .map(|(i, deckbox)| Deckbox {
                number: i + 1,
                model: models
                    .get(&deckbox.id)
                    .expect("deckbox model id must be valid")
                    .clone(),
                skin: deckbox.skin,
                variant: deckbox.variant,
                animation: deckbox.animation,
                focus: deckbox.focus,
                time: deckbox.time,
                zoom: deckbox.zoom.unwrap_or(1.0),
                offset_x: deckbox.offset_x,
                offset_y: deckbox.offset_y,
                color: deckbox.color,
            })
            .collect::<Vec<_>>();

        let posters = expansion
            .posters
            .into_iter()
            .enumerate()
            .map(|(i, poster)| {
                Ok(Poster::new(
                    i + 1,
                    format!("{file_stem}/{}", poster.file),
                    poster.name,
                    poster.price,
                )?)
            })
            .collect::<Result<Vec<_>>>()?;

        Ok(Self {
            id: id.to_owned(),
            number: number.parse().expect("expansion number must be valid"),
            logo: expansion.logo,
            background: expansion.background,
            featured: Arc::from(expansion.featured),
            models: Arc::from(expansion.models),
            cards: Arc::default(),
            sleeves: Arc::from(sleeves),
            deckboxes: Arc::from(deckboxes),
            posters: Arc::from(posters),
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

        let models = model::Model::map();
        let mut cards = Vec::new();

        for (i, model) in self.models.iter().enumerate() {
            let Some(metadata) = models.get(&model.id) else {
                return Err(Error::ModelNotFound(model.id.clone()));
            };

            let number = i + 1;
            let skin = model.options.skin().map(str::to_owned);
            let animation = model.options.animation().map(str::to_owned);

            if metadata.is_event() {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    skin: skin.clone(),
                    animation: animation.clone(),
                    rarity: card::Rarity::Classified,
                    reel: Vec::new(),
                });
                continue;
            }

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

            if metadata.is_chibi() {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    skin: skin.clone(),
                    animation: animation.clone(),
                    rarity: card::Rarity::Profile,
                    reel: reel.clone(),
                });
                continue;
            }

            cards.push(Card {
                number,
                model: metadata.clone(),
                skin: skin.clone(),
                animation: animation.clone(),
                rarity: card::Rarity::Standard,
                reel: reel.clone(),
            });

            if let Some(animation) = reel.get(1) {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    skin: skin.clone(),
                    animation: Some(animation.clone()),
                    rarity: card::Rarity::Rare,
                    reel: reel.clone(),
                });
            }

            if model.profile.is_enabled() {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    skin: model
                        .profile
                        .skin()
                        .map(str::to_owned)
                        .or_else(|| skin.clone()),
                    animation: model
                        .profile
                        .animation()
                        .map(str::to_owned)
                        .or_else(|| animation.clone()),
                    rarity: card::Rarity::Profile,
                    reel: reel.clone(),
                });
            }

            if variants.contains(&"cover".to_owned()) {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    skin: skin.clone(),
                    animation: animation.clone(),
                    rarity: card::Rarity::Cover,
                    reel: reel.clone(),
                });
            }

            if variants.contains(&"aim".to_owned()) {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    skin: skin.clone(),
                    animation: animation.clone(),
                    rarity: card::Rarity::Aim,
                    reel: reel.clone(),
                });
            }

            if let Some(animation) = reel.first() {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    skin: skin.clone(),
                    animation: Some(animation.clone()),
                    rarity: card::Rarity::Special,
                    reel: reel.clone(),
                });
            }

            if model.exotic.is_enabled() && animations.contains(&"action".to_owned()) {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    skin: model
                        .exotic
                        .skin()
                        .map(str::to_owned)
                        .or_else(|| skin.clone()),
                    animation: Some(model.exotic.animation().unwrap_or("action").to_owned()),
                    rarity: card::Rarity::Exotic,
                    reel: reel.clone(),
                });
            }

            if variants.contains(&"sc".to_owned()) && model.goddess.is_enabled() {
                cards.push(Card {
                    number,
                    model: metadata.clone(),
                    skin: model
                        .goddess
                        .skin()
                        .map(str::to_owned)
                        .or_else(|| skin.clone()),
                    animation: Some(
                        model
                            .goddess
                            .animation()
                            .map(str::to_owned)
                            .or_else(|| animation.clone())
                            .unwrap_or_else(|| "main".to_owned()),
                    ),
                    rarity: card::Rarity::Goddess,
                    reel: reel.clone(),
                });
            }
        }

        let _ = self.cards.set(cards);

        Ok(self.cards.get().unwrap())
    }

    pub fn output_dir(&self, quality: Quality) -> PathBuf {
        environment::output_dir().join(format!(
            "{:<02}_{}{}",
            self.number,
            self.id,
            quality.suffix()
        ))
    }

    pub fn file_name(&self) -> String {
        format!("{:<02}_{}", self.number, self.id)
    }

    fn bundle_id(&self) -> String {
        format!("NIKKE_REBORN_{}", self.id)
    }

    pub async fn bundle(&self) -> Result<Bundle> {
        let bundle = self.bundle_id();

        let items = [pack(self), box_(self)]
            .into_iter()
            .chain(self.sleeves.iter().map(sleeve.with(self)))
            .chain(self.deckboxes.iter().map(deckbox.with(self)))
            .collect::<Vec<_>>();

        let prefabs = self
            .posters
            .iter()
            .map(poster.with(self))
            .collect::<Vec<_>>();

        Ok(Bundle(json!({
            "Name": bundle,
            "BundleId": bundle,
            "AutoCompressTextures": true,
            "MaxTextureSize": 2048,
            "TextureCompression": "BC7",
            "EnableMipMaps": false,
            "Assemblies": [],
            "Items": items,
            "CardExpansions": [expansion(self).await?],
            "CustomShops": [custom_shop()],
            "Prefabs": prefabs,
        })))
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
pub struct _Model {
    pub id: String,
    #[serde(flatten)]
    options: Options,
    #[serde(rename = "Profile", default)]
    profile: Options,
    #[serde(rename = "Exotic", default)]
    exotic: Options,
    #[serde(rename = "Goddess", default)]
    goddess: Options,
}

#[derive(Debug, Clone, PartialEq, Eq, Default, Deserialize)]
#[serde(untagged)]
pub enum Options {
    Toggled(bool),
    Customized {
        animation: Option<String>,
        skin: Option<String>,
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
            Options::Customized { animation, .. } => animation.as_deref(),
            Options::Toggled(_) | Options::Default => None,
        }
    }

    pub fn skin(&self) -> Option<&str> {
        match self {
            Options::Customized { skin, .. } => skin.as_deref(),
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
        no_standard: bool,
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

        let rest = 100.0 - total;

        let (standard, profile) = if slot.no_standard {
            (0.0, rest + slot.profile)
        } else {
            (rest, slot.profile)
        };

        json!({
            "Standard": standard,
            "Profile": profile,
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
        cover: 0.5,
        aim: 0.5,
        ..Slot::default()
    });

    let uncommon = slot(Slot {
        profile: 6.0,
        cover: 2.0,
        aim: 2.0,
        rare: 1.0,
        special: 0.5,
        exotic: 0.1,
        ..Slot::default()
    });

    let rare = slot(Slot {
        no_standard: true,
        cover: 25.0,
        aim: 15.0,
        rare: 10.0,
        special: 3.0,
        exotic: 1.0,
        goddess: 0.4,
        classified: 0.1,
        ..Slot::default()
    });

    let level = level(expansion);
    let level_big = level + 5;

    json!({
        "Name": format!("{} Packs", expansion.name()),
        "CardExpansion": bundle,
        "PackType": format!("{bundle}_CardPack"),
        "ItemType": format!("{bundle}_CardPack_Item"),
        "Material": "CardPack_Material",
        "SpriteName": "CardPack_Item",
        "BaseCost": 1 + expansion.number,
        "SmallBoxLicensePrice": 50 + progression(40.0, 1.2, level),
        "SmallBoxLicenseLevelRequirement": level,
        "BigBoxLicensePrice": progression(50.0, 1.2, level_big),
        "BigBoxLicenseLevelRequirement": level_big,
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
        "HasBigBox": true,
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

    let level = 3 + level(expansion);
    let level_big = level + 5;

    json!({
        "Name": format!("{} Boxes", expansion.name()),
        "Material": "CardBox_Material",
        "SpriteName": "CardBox_Item",
        "ItemType": format!("{bundle}_CardBox_Item"),
        "SpawnsPackType": format!("{bundle}_CardPack_Item"),
        "SmallBoxLicensePrice": 100 + progression(40.0, 1.3, level),
        "SmallBoxLicenseLevelRequirement": level,
        "BigBoxLicensePrice": progression(50.0, 1.3, level_big),
        "BigBoxLicenseLevelRequirement": level_big,
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
        "HasBigBox": true,
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
          "Cover",
          "Aim",
          "Rare",
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
        "RarityDrivenStepSize": 1.0,
        "RarityDrivenBorderMultiplierBase": 2.2,
        "RarityDrivenFoilMultiplier": 5.0,
        "PlayCardMaterials": []
    }))
}

fn card(card: &Card) -> serde_json::Value {
    json!({
        "Name": card.model.name(),
        "Rarity": card.rarity,
        "BorderType": card.border(),
        "Sprite": card.file_name(),
        "IsFoil": card.rarity.is_foil(),
        "ElementType": "None",
        "FoilMask": "",
        "CardBack": ""
    })
}

fn sleeve(expansion: &Expansion, sleeve: &Sleeve) -> serde_json::Value {
    let bundle = expansion.bundle_id();

    let level = level(expansion) + 3 * sleeve.number;
    let unlock_price = 100 + progression(20.0, 1.2, level);
    let base_cost = sigmoid(3, 20, level);

    json!({
        "Name": format!("{} Sleeves", sleeve.model.name()),
        "Material": format!("{}_Material",sleeve.file_name()),
        "SpriteName": format!("{}_Item", sleeve.file_name()),
        "ItemType": format!("{bundle}_{}_Item", sleeve.file_name()),
        "SmallBoxLicensePrice": unlock_price,
        "SmallBoxLicenseLevelRequirement": level,
        "BigBoxLicensePrice": unlock_price,
        "BigBoxLicenseLevelRequirement": level,
        "BaseCost": base_cost,
        "ItemCategory": "Sleeve",
        "SpawnsPackType": null,
        "AddItemAsAccessory": true,
        "AddItemAsFigurine": false,
        "AddItemAsBoardGame": false,
        "PhoneAppId": PHONE_APP_ID,
        "UsesBaseGameMesh": true,
        "MeshToUse": "CardSleeve_Clear",
        "Mesh": "",
        "MaterialList": [],
        "HasSmallBox": false,
        "HasBigBox": true,
        "BigBoxHideTillUnlocked": false,
        "BigBoxIgnoreDoubleImage": true,
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
        "IsCardPack": false,
        "IsCardBox": false,
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

fn deckbox(expansion: &Expansion, deckbox: &Deckbox) -> serde_json::Value {
    let bundle = expansion.bundle_id();

    let level = level(expansion) + 4 * deckbox.number;
    let unlock_price = 100 + progression(20.0, 1.2, level);
    let base_cost = sigmoid(20, 100, level);

    json!({
        "Name": format!("{} Deckboxes", deckbox.model.name()),
        "Material": format!("{}_Material", deckbox.file_name()),
        "SpriteName": format!("{}_Item", deckbox.file_name()),
        "ItemType": format!("{bundle}_{}_Item", deckbox.file_name()),
        "SmallBoxLicensePrice": unlock_price,
        "SmallBoxLicenseLevelRequirement": level,
        "BigBoxLicensePrice": unlock_price,
        "BigBoxLicenseLevelRequirement": level,
        "BaseCost": base_cost,
        "ItemCategory": "Deckbox",
        "SpawnsPackType": null,
        "AddItemAsAccessory": true,
        "AddItemAsFigurine": false,
        "AddItemAsBoardGame": false,
        "PhoneAppId": PHONE_APP_ID,
        "UsesBaseGameMesh": false,
        "MeshToUse": "",
        "Mesh": "DeckBox_Mesh_low_improved",
        "MaterialList": [],
        "HasSmallBox": false,
        "HasBigBox": true,
        "BigBoxHideTillUnlocked": false,
        "BigBoxIgnoreDoubleImage": true,
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
          "x": 1,
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
        "IsCardBox": false,
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

fn poster(expansion: &Expansion, poster: &Poster) -> serde_json::Value {
    let bundle = expansion.bundle_id();
    let level = level(expansion) + poster.number;
    let file_stem = poster.file_stem();

    json!({
        "Name": poster.name,
        "PrefabName": format!("{file_stem}_Prefab"),
        "SpriteName": format!("{file_stem}_Icon"),
        "DecoObject": format!("{bundle}_{file_stem}_Deco"),
        "DecoType": "Poster",
        "IsDecoObject": true,
        "AddItemToFurnitureShop": false,
        "Price": poster.price,
        "LevelRequirement": level,
        "VideoClips": []
    })
}

fn custom_shop() -> serde_json::Value {
    json!({
        "PhoneAppId": PHONE_APP_ID,
        "AppDisplayName": "NIKKE REBORN",
        "AppIcon": "Shop_Icon",
        "AppInnerBGImage": "Shop_IBG",
        "AppOuterBGImage": "Shop_OBG",
        "SiteLogo": "Shop_Logo",
        "SiteHeader": "Shop_Banner",
        "SiteBackground": "Shop_Wallpaper"
    })
}

fn progression(base: f32, growth: f32, level: usize) -> usize {
    100 * ((base * (level as f32).powf(growth)).round() / 100.0) as usize
}

fn sigmoid(min: usize, max: usize, current: usize) -> usize {
    min + ((max - min) as f32 / (1.0 + std::f32::consts::E.powf(-0.12 * (current as f32 - 40.0))))
        .round() as usize
}

fn level(expansion: &Expansion) -> usize {
    (10 * (expansion.number - 1)).max(1)
}
