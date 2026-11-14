use std::io;
use std::sync::Arc;

#[derive(Debug, Clone, thiserror::Error)]
pub enum Error {
    #[error("an io operation failed: {0}")]
    IoFailed(Arc<io::Error>),
    #[error("a toml file failed to parse: {0}")]
    TomlParsingFailed(Arc<toml::de::Error>),
    #[error("invalid manufacturer: {0}")]
    InvalidManufacturer(String),
    #[error("invalid rarity: {0}")]
    InvalidRarity(String),
    #[error("model not found: {0}")]
    ModelNotFound(String),
}

impl From<io::Error> for Error {
    fn from(error: io::Error) -> Self {
        Self::IoFailed(Arc::new(error))
    }
}

impl From<toml::de::Error> for Error {
    fn from(error: toml::de::Error) -> Self {
        Self::TomlParsingFailed(Arc::new(error))
    }
}
