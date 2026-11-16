use std::fmt;

use crate::model;
use crate::{Character, Model};

#[derive(Debug, Clone, PartialEq)]
pub struct Card {
    pub number: usize,
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

    pub fn file_name(&self) -> String {
        format!(
            "{number:<04}_{model}_{title}_{rarity_index:<02}_{rarity}",
            number = self.number,
            model = self.model.id,
            title = self.title(),
            rarity_index = self.rarity.index(),
            rarity = self.rarity
        )
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
            Rarity::Rare | Rarity::Special => "smoke-pink",
            Rarity::Exotic => "sky-night",
            Rarity::Goddess | Rarity::Classified => return None,
        })
    }

    pub fn index(&self) -> usize {
        match self {
            Rarity::Standard => 1,
            Rarity::Profile { .. } => 2,
            Rarity::Rare => 3,
            Rarity::Cover => 4,
            Rarity::Aim => 5,
            Rarity::Special => 6,
            Rarity::Exotic => 7,
            Rarity::Goddess => 8,
            Rarity::Classified => 9,
        }
    }

    pub fn focus(&self) -> &'static str {
        match self {
            Rarity::Standard | Rarity::Rare | Rarity::Special | Rarity::Exotic => "half-body",
            Rarity::Profile { .. }
            | Rarity::Cover
            | Rarity::Aim
            | Rarity::Goddess
            | Rarity::Classified => "full-body",
        }
    }
}

impl fmt::Display for Rarity {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Rarity::Standard => "Standard",
            Rarity::Profile { .. } => "Profile",
            Rarity::Rare => "Rare",
            Rarity::Cover => "Cover",
            Rarity::Aim => "Aim",
            Rarity::Special => "Special",
            Rarity::Exotic => "Exotic",
            Rarity::Goddess => "Goddess",
            Rarity::Classified => "Classified",
        })
    }
}
