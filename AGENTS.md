# AGENTS.md

Pipeline that renders NIKKE trading cards: one `cards/<set>.toml` per
expansion (its characters, its `rarities` — the subset of presentations
to generate for the set — its backgrounds and logo) → GPU viewer + Pillow +
ffmpeg → finished cards under `output/<set>/` (half resolution by default),
`draft/` (drafts), and BepInEx bundles under `bundles/`.

## Commands (run via `uv`)

- `generate [paths] [--draft | --ultra] [--force] [--no-video] [--jobs N]`
  — render and composite cards (paths: an expansion's name or
  `cards/<set>.toml`; `--ids` restricts a run to the named characters)
- `test <set> [ids…] [--new-baseline]` — byte-for-byte
  regression check: a forced single-worker re-render of the character(s)'
  presentations (and the expansion's pack/box) compared by SHA-256 against
  `tests/baselines/<set>/`
- `bundle`, `simulate <set>`, `spritesheet <set>`

## Conventions

- `uvx ruff check src/` and `uvx ruff format --check src/` must be
  clean.
- Only commit or push when explicitly asked.
- Commit messages carry no co-author trailers (`Co-Authored-By: …` or
  similar).
- For quick iteration, `generate` a single character (`--ids`) with the
  default settings; avoid `--ultra` (`generate`) until the very
  end — it renders at native resolution and is much slower.
- Comments/docstrings cover only what the code does not say:
  invariants, protocol semantics, units, gotchas. Never values (numbers,
  named lists, restated defaults) or restated code (step-by-step
  narration, per-parameter docs). Write each fact once, at its defining
  site; reference it elsewhere.

## Don't break (verify with `uv run test ELYSION c010`)

- The byte protocol: a forced single-worker re-render is byte-for-byte
  identical to the recorded baselines (`test`); the `nikke-reborn-source`
  hash embedded in each output folds in the run's scale only when it
  deviates from 1.0 (the native/ultra resolution), so an ultra card's hash
  is the canonical one. Changing what goes into a hash requires
  re-recording the baselines (`test --new-baseline`).
- The GPU is shared: use `--jobs 1` for byte-protocol work, and retry
  transient `nikke-viewer` failures (truncated stream, crash).

## Dependencies

Python ≥ 3.14 (uv). On PATH: `nikke-viewer` and `unity-viewer` (Rust;
source in `unity-viewer/`), `ffmpeg`, `ffprobe`.
