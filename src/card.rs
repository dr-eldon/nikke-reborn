use crate::model;
use crate::{Character, Model};

#[derive(Debug, Clone, PartialEq)]
pub struct Card {
    pub model: Model,
    pub animation: Option<String>,
    pub rarity: Rarity,
    pub character: Option<Character>,
}

impl Card {
    const SEPARATORS: &[char] = &[':', '-', '_'];

    pub fn title(&self) -> String {
        if let Some(character) = &self.character
            && self.model.name.starts_with(&character.name)
        {
            &character.name
        } else {
            &self.model.name
        }
        .split(Self::SEPARATORS)
        .next()
        .expect("model name must not be empty")
        .to_owned()
    }

    pub fn subtitle(&self) -> Option<String> {
        let subtitle = self
            .model
            .name
            .trim_prefix(&self.title())
            .trim()
            .trim_matches(Self::SEPARATORS)
            .trim();

        if subtitle.is_empty() {
            return None;
        }

        Some(subtitle.to_owned())
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Rarity {
    Standard,
    Profile { reel: Vec<String> },
    Rare,
    Cover,
    Aim,
    Special,
    Exotic,
    Goddess,
    Classified,
}

impl Rarity {
    pub fn variant(&self) -> model::Variant {
        match self {
            Rarity::Standard => model::Variant::FullBody,
            Rarity::Profile { .. } => model::Variant::FullBody,
            Rarity::Rare => model::Variant::FullBody,
            Rarity::Cover => model::Variant::Cover,
            Rarity::Aim => model::Variant::Aim,
            Rarity::Special => model::Variant::FullBody,
            Rarity::Exotic => model::Variant::FullBody,
            Rarity::Goddess => model::Variant::SkillCut,
            Rarity::Classified => model::Variant::FullBody,
        }
    }

    pub fn time(&self) -> Option<f32> {
        match self {
            Rarity::Standard
            | Rarity::Profile { .. }
            | Rarity::Rare
            | Rarity::Cover
            | Rarity::Aim
            | Rarity::Special => Some(0.0),
            Rarity::Exotic | Rarity::Goddess | Rarity::Classified => None,
        }
    }

    pub fn background(&self) -> Option<&'static str> {
        Some(match self {
            Rarity::Standard | Rarity::Profile { .. } => "sky-night",
            Rarity::Cover | Rarity::Aim => "bubble-maker",
            Rarity::Rare | Rarity::Special => "pink-smoke",
            Rarity::Exotic => "sky-night",
            Rarity::Goddess | Rarity::Classified => return None,
        })
    }
}
