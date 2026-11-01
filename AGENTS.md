# AGENTS.md

Pipeline that renders NIKKE trading cards: `cards/<set>/<card>/<Variant>.json`
definitions → GPU viewer + Pillow + ffmpeg → finished cards under
`output/<set>/` (half resolution by default), `draft/` (drafts), and
BepInEx bundles under `bundles/`.

## Commands (run via `uv`)

- `generate [paths] [--draft | --ultra] [--force] [--no-video] [--jobs N]`
  — render and composite cards
- `test cards/<set>/<card> [--ultra] [--new-baseline]` — byte-for-byte
  regression check: a forced single-worker re-render compared by SHA-256
  against `tests/baselines/`
- `bundle`, `simulate <set>`, `spritesheet <set>`

## Conventions

- `uvx ruff check src/` must be clean.
- Only commit or push when explicitly asked.
- For quick iteration, `generate` a single card with the default
  settings; avoid `--ultra` (`generate` and `test`) until the very end —
  it renders at native resolution and is much slower.

## Don't break (verify with `uv run test cards/ELYSION/0001_Rapi [--ultra]`)

- The byte protocol: `--ultra` output is byte-for-byte the legacy bytes;
  the `nikke-reborn-source` hashes embedded in outputs fold in scale/size
  terms only when they deviate from the legacy defaults (1.0 / 1024²).
  Changing what goes into a hash requires re-recording the baselines
  (`test --new-baseline`).
- The GPU is shared: use `--jobs 1` for byte-protocol work, and retry
  transient `nikke-viewer` failures (truncated stream, crash).

## Dependencies

Python ≥ 3.14 (uv). On PATH: `nikke-viewer` and `unity-viewer` (Rust;
source in `unity-viewer/`), `ffmpeg`, `ffprobe`.
