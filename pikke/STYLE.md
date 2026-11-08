# Style — conventions for the `pikke` crate

## Positioning

The engine is generic: it interprets Lua design scripts and is not
tied to NIKKE. NIKKE-specific concerns (sets, assets, the viewer)
live in the design scripts and the rest of the repo.

## Comments and doc comments

Cover only what the code does not say: invariants, protocol
semantics, units, gotchas.

- Never values: numbers, named lists, restated defaults.
- Never restated code: step-by-step narration, per-parameter docs,
  restated names.
- Write each fact once, at its defining site; reference it
  elsewhere.
- No history: do not justify a choice by negating a previous or
  rejected approach. Decision rationale belongs in
  `ENGINE-PLAN.md`, not in the code.
- Keep them as concise as possible: only the important ones.

## Rust

- Modules around single-noun types; no `ops`/`utils` catch-alls.
- Shadowing is fine: a function may share its name with the value
  it reads or produces, and a local may shadow a function name.
  Name things by what they are; do not rename to dodge a
  collision.
- Inference carries the types: no annotation where the use fixes
  them; a value keeps its name through conversion
  (`let value: u32 = value.parse()…`).
- The standard's iterators and combinators over hand-rolled index
  management (`sequence_values().enumerate()`, `transpose`);
  `std::env::args()` directly, not collected.
- Make unbuildable states unrepresentable: a constructor that
  returns the built value (`Engine::load`) over a `new()` plus
  `Option` fields.
- Errors are user-facing `anywho!` messages; `main` returns
  `anywho::Result` (the default rendering, exit 1).

## CLI

Hand-rolled, mirroring `nikke-viewer`:

- No argument-parsing crate; a single pass over the arguments;
  `--flag value` only (no `--flag=value`).
- `--help` is handled after the pass (it may list the script's
  dynamic flags).
- Unknown options and stray positionals are errors:
  `invalid option: {x}`, `invalid argument: {x}`; a flag missing
  its value: `{flag} requires a value`.
- The script is the first argument: its parameters (one dynamic flag
  each) exist only once it is loaded, so it is read before the pass.

## Hygiene

`cargo fmt --check` and `cargo clippy` must be clean.
