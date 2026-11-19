#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Default)]
pub enum Quality {
    Low,
    #[default]
    Normal,
    Ultra,
}

impl Quality {
    pub fn suffix(self) -> &'static str {
        match self {
            Quality::Low => "_Low",
            Quality::Normal => "",
            Quality::Ultra => "_Ultra",
        }
    }

    pub fn scale(&self) -> f32 {
        match self {
            Quality::Low => 0.5,
            Quality::Normal => 0.5,
            Quality::Ultra => 1.0,
        }
    }
}
