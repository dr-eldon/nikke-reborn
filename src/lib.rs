#![recursion_limit = "512"]
mod deckbox;
mod error;
mod poster;
mod quality;
mod sleeve;

pub mod card;
pub mod character;
pub mod environment;
pub mod expansion;
pub mod model;

pub use card::Card;
pub use character::Character;
pub use deckbox::Deckbox;
pub use error::Error;
pub use expansion::Expansion;
pub use model::Model;
pub use poster::Poster;
pub use quality::Quality;
pub use sleeve::Sleeve;

pub type Result<T> = core::result::Result<T, Error>;
