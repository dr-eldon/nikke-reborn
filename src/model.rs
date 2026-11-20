use std::collections::HashMap;
use std::sync::LazyLock;

use serde::{Deserialize, Serialize};

static MODELS: LazyLock<HashMap<String, Model>> = LazyLock::new(|| {
    let models: Vec<Model> = serde_json::from_str(include_str!("../database/models.json"))
        .expect("models database must be valid");

    HashMap::from_iter(
        models
            .into_iter()
            .map(|character| (character.id.clone(), character)),
    )
});

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
pub struct Model {
    pub id: String,
    pub name: String,
    pub date: String,
}

impl Model {
    pub fn map() -> &'static HashMap<String, Model> {
        &MODELS
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
