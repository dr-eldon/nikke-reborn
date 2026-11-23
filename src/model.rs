use std::collections::HashMap;
use std::sync::LazyLock;

use regex::Regex;
use serde::{Deserialize, Serialize};

use crate::Character;

static MODELS: LazyLock<HashMap<String, Model>> = LazyLock::new(|| {
    let models: Vec<Model> = serde_json::from_str(include_str!("../database/models.json"))
        .expect("models database must be valid");

    let characters = Character::map();

    HashMap::from_iter(models.into_iter().map(|model| {
        (
            model.id.clone(),
            Model {
                character: characters
                    .get(
                        model
                            .id
                            .split("_")
                            .next()
                            .expect("character id must not be empty"),
                    )
                    .cloned(),
                ..model
            },
        )
    }))
});

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
pub struct Model {
    pub id: String,
    pub name: String,
    pub date: String,
    #[serde(default, skip)]
    pub character: Option<Character>,
}

static SEPARATORS: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(":| - |_").expect("parse title separator regex"));

impl Model {
    pub fn map() -> &'static HashMap<String, Model> {
        &MODELS
    }

    pub fn title(&self) -> String {
        SEPARATORS
            .split(
                if let Some(character) = &self.character
                    && self.name.starts_with(&character.name)
                {
                    &character.name
                } else {
                    &self.name
                },
            )
            .next()
            .expect("model name must not be empty")
            .to_owned()
    }

    pub fn subtitle(&self) -> Option<String> {
        let subtitle = self
            .name
            .trim_prefix(&self.title())
            .trim()
            .trim_prefix(':')
            .trim_prefix(" - ")
            .trim_prefix('_')
            .trim();

        if subtitle.is_empty() {
            return None;
        }

        Some(subtitle.to_owned())
    }

    pub fn name(&self) -> String {
        if let Some(subtitle) = self.subtitle() {
            format!("{}: {subtitle}", self.title())
        } else {
            self.title()
        }
    }

    pub fn file_name(&self) -> String {
        let title = self
            .title()
            .chars()
            .filter(|&c| c.is_ascii_alphanumeric() || c == '-')
            .collect::<String>();

        format!("{}_{title}", self.id)
    }

    pub fn is_event(&self) -> bool {
        !self.is_chibi()
            && self
                .id
                .strip_prefix('c')
                .is_none_or(|rest| rest.chars().next().is_some_and(|c| !c.is_ascii_digit()))
    }

    pub fn is_chibi(&self) -> bool {
        self.id.starts_with("smol")
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(into = "String")]
pub enum Variant {
    FullBody,
    Cover,
    Aim,
    SkillCut,
}

impl From<Variant> for String {
    fn from(variant: Variant) -> Self {
        String::from(match variant {
            Variant::FullBody => "fb",
            Variant::Cover => "cover",
            Variant::Aim => "aim",
            Variant::SkillCut => "sc",
        })
    }
}
