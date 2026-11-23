use crate::Model;

#[derive(Debug, Clone, PartialEq)]
pub struct Sleeve {
    pub number: usize,
    pub model: Model,
    pub background: String,
    pub skin: Option<String>,
    pub variant: Option<String>,
    pub animation: Option<String>,
    pub focus: Option<String>,
    pub zoom: f32,
    pub time: f32,
    pub offset_x: f32,
    pub portrait: String,
}

impl Sleeve {
    pub fn file_name(&self) -> String {
        format!("CardSleeve_{:<04}_{}", self.number, self.model.file_name())
    }
}
