#![recursion_limit = "512"]
mod error;
mod quality;

pub mod card;
pub mod character;
pub mod environment;
pub mod expansion;
pub mod model;

pub use card::Card;
pub use character::Character;
pub use error::Error;
pub use expansion::Expansion;
pub use model::Model;
pub use quality::Quality;

pub type Result<T> = core::result::Result<T, Error>;
