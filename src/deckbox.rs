use crate::Model;

#[derive(Debug, Clone, PartialEq)]
pub struct Deckbox {
    pub number: usize,
    pub model: Model,
    pub skin: Option<String>,
    pub variant: Option<String>,
    pub animation: Option<String>,
    pub focus: Option<String>,
    pub zoom: f32,
    pub time: f32,
    pub offset_x: f32,
    pub offset_y: f32,
    pub color: Option<String>,
}

impl Deckbox {
    pub fn file_name(&self) -> String {
        format!("DeckBox_{:<04}_{}", self.number, self.model.file_name())
    }
}
