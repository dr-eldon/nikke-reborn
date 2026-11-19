# AGENTS.md

Pipeline that renders NIKKE trading cards: one `cards/<set>.toml` per
expansion.

## Rust

- Modules around single-noun types; no `ops`/`utils` catch-alls.
- Shadowing is fine: a function may share its name with the value
  it reads or produces, and a local may shadow a function name.
  Name things by what they are; do not rename to dodge a
  collision.
- No shortened names: `width` and `height`, not `w` and `h`.
- Inference carries the types: no annotation where the use fixes
  them; a value keeps its name through conversion
  (`let value: u32 = value.parse()…`).
- The standard's iterators and combinators over hand-rolled index
  management (`sequence_values().enumerate()`, `transpose`);
  `std::env::args()` directly, not collected.
- Import groups, separated by blank lines: `std`, external crates,
  `crate` (last). Shared types are importable from the crate root
  (`pub use`).

## Comments

No comments allowed, unless explicitly requested during review.

## Commits

- Every change must be reviewed by the user. Under no circumstance
  you are allowed to commit or push until explicitly asked to.

- **Short subjects:** one imperative clause, backticked identifiers;
  details in the body.

## Hygiene

`cargo fmt --check` and `cargo lint` must be clean.
