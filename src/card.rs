use std::fmt;

use serde::Serialize;

use crate::Model;
use crate::model;

#[derive(Debug, Clone, PartialEq)]
pub struct Card {
    pub number: usize,
    pub model: Model,
    pub skin: Option<String>,
    pub animation: Option<String>,
    pub rarity: Rarity,
    pub reel: Vec<String>,
}

impl Card {
    pub fn file_name(&self) -> String {
        format!(
            "{number:<04}_{model}_{rarity_index:<02}_{rarity}",
            number = self.number,
            model = self.model.file_name(),
            rarity_index = self.rarity.index(),
            rarity = self.rarity
        )
    }

    pub fn focus(&self) -> &'static str {
        if self.model.is_chibi() {
            return "full-body";
        }

        match self.rarity {
            Rarity::Standard | Rarity::Rare | Rarity::Special | Rarity::Exotic => "half-body",
            Rarity::Profile
            | Rarity::Cover
            | Rarity::Aim
            | Rarity::Goddess
            | Rarity::Classified => "full-body",
        }
    }

    pub fn border(&self) -> Border {
        let border = self.rarity.border() as usize;

        let bonus = self
            .model
            .character
            .as_ref()
            .and_then(|character| character.rarity)
            .map(|rarity| match rarity {
                crate::character::Rarity::R => 0,
                crate::character::Rarity::SR => 1,
                crate::character::Rarity::SSR => 2,
            })
            .unwrap_or(0);

        let bonus = if border > 0 {
            (bonus as f32 / border as f32 + 0.5).floor() as usize
        } else {
            bonus
        };

        Border::ALL[(border + bonus).min(Border::ALL.len() - 1)]
    }

    pub fn is_monochrome(&self) -> bool {
        matches!(self.rarity, Rarity::Rare | Rarity::Special | Rarity::Exotic)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum Rarity {
    Standard,
    Profile,
    Rare,
    Cover,
    Aim,
    Special,
    Exotic,
    Goddess,
    Classified,
}

impl Rarity {
    pub fn variant(self) -> model::Variant {
        match self {
            Rarity::Standard => model::Variant::FullBody,
            Rarity::Profile => model::Variant::FullBody,
            Rarity::Rare => model::Variant::FullBody,
            Rarity::Cover => model::Variant::Cover,
            Rarity::Aim => model::Variant::Aim,
            Rarity::Special => model::Variant::FullBody,
            Rarity::Exotic => model::Variant::FullBody,
            Rarity::Goddess => model::Variant::SkillCut,
            Rarity::Classified => model::Variant::FullBody,
        }
    }

    pub fn time(self) -> Option<f32> {
        match self {
            Rarity::Standard
            | Rarity::Profile
            | Rarity::Rare
            | Rarity::Cover
            | Rarity::Aim
            | Rarity::Special => Some(0.0),
            Rarity::Exotic | Rarity::Goddess | Rarity::Classified => None,
        }
    }

    pub fn background(self) -> Option<&'static str> {
        Some(match self {
            Rarity::Standard | Rarity::Profile => "sky-night",
            Rarity::Cover | Rarity::Aim => "bubble-maker",
            Rarity::Rare | Rarity::Special | Rarity::Exotic => "sparks-red",
            Rarity::Goddess | Rarity::Classified => return None,
        })
    }

    pub fn index(self) -> usize {
        match self {
            Rarity::Standard => 1,
            Rarity::Profile => 2,
            Rarity::Rare => 3,
            Rarity::Cover => 4,
            Rarity::Aim => 5,
            Rarity::Special => 6,
            Rarity::Exotic => 7,
            Rarity::Goddess => 8,
            Rarity::Classified => 9,
        }
    }

    pub fn is_foil(self) -> bool {
        matches!(
            self,
            Self::Special | Self::Exotic | Self::Goddess | Self::Classified
        )
    }

    pub fn border(self) -> Border {
        match self {
            Rarity::Standard | Rarity::Profile | Rarity::Rare => Border::Base,
            Rarity::Cover | Rarity::Aim => Border::FirstEdition,
            Rarity::Special => Border::Silver,
            Rarity::Exotic => Border::Gold,
            Rarity::Goddess => Border::EX,
            Rarity::Classified => Border::FullArt,
        }
    }
}

impl fmt::Display for Rarity {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Rarity::Standard => "Standard",
            Rarity::Profile => "Profile",
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

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum Border {
    Base,
    FirstEdition,
    Silver,
    Gold,
    EX,
    FullArt,
}

impl Border {
    pub const ALL: &[Self] = &[
        Self::Base,
        Self::FirstEdition,
        Self::Silver,
        Self::Gold,
        Self::EX,
        Self::FullArt,
    ];
}
