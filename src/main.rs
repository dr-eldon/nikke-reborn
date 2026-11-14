use nikke_reborn::{Expansion, Result};

#[tokio::main(flavor = "local")]
pub async fn main() -> Result<()> {
    let expansions = Expansion::list().await?;

    for expansion in expansions.iter() {
        println!("{}", expansion.name());

        for card in expansion.cards().await? {
            println!(
                "  {}{}",
                card.title(),
                if let Some(subtitle) = card.subtitle() {
                    format!(" - {subtitle}")
                } else {
                    String::new()
                }
            );
            println!("  {card:?}");
        }

        println!();
    }

    Ok(())
}
