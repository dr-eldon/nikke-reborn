use std::collections::HashMap;
use std::sync::LazyLock;

use serde::Deserialize;

use crate::Error;

static CHARACTERS: LazyLock<HashMap<String, Character>> = LazyLock::new(|| {
    let characters: Vec<Character> =
        serde_json::from_str(include_str!("../database/characters.json"))
            .expect("character database must be valid");

    HashMap::from_iter(
        characters
            .into_iter()
            .map(|character| (character.id.clone(), character)),
    )
});

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct Character {
    pub id: String,
    pub name: String,
    pub manufacturer: Option<Manufacturer>,
    pub rarity: Option<Rarity>,
}

impl Character {
    pub fn map() -> &'static HashMap<String, Character> {
        &CHARACTERS
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(try_from = "String")]
pub enum Manufacturer {
    Elysion,
    Tetra,
    Missilis,
    Pilgrim,
    Abnormal,
}

impl TryFrom<String> for Manufacturer {
    type Error = Error;

    fn try_from(value: String) -> Result<Self, Self::Error> {
        Ok(match value.to_lowercase().as_str() {
            "elysion" => Self::Elysion,
            "tetra" => Self::Tetra,
            "missilis" => Self::Missilis,
            "pilgrim" => Self::Pilgrim,
            "abnormal" => Self::Abnormal,
            _ => return Err(Error::InvalidManufacturer(value.clone())),
        })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Deserialize)]
#[serde(try_from = "String")]
pub enum Rarity {
    R,
    SR,
    SSR,
}

impl TryFrom<String> for Rarity {
    type Error = Error;

    fn try_from(value: String) -> Result<Self, Self::Error> {
        Ok(match value.to_lowercase().as_str() {
            "r" => Self::R,
            "sr" => Self::SR,
            "ssr" => Self::SSR,
            _ => return Err(Error::InvalidRarity(value.clone())),
        })
    }
}
