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
            Quality::Low => " (Low)",
            Quality::Normal => "",
            Quality::Ultra => " (Ultra)",
        }
    }

    pub fn scale(&self) -> f32 {
        match self {
            Quality::Low => 0.5,
            Quality::Normal => 0.5,
            Quality::Ultra => 1.0,
        }
    }

    pub fn scale_video(&self) -> f32 {
        match self {
            Quality::Low => 0.75,
            Quality::Normal | Quality::Ultra => 1.0,
        }
    }

    pub fn framerate(&self) -> u32 {
        match self {
            Quality::Low => 30,
            Quality::Normal | Quality::Ultra => 60,
        }
    }
}
