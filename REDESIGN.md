# REDESIGN.md — expansion-driven card generation

The per-variant card-definition JSONs (`cards/<set>/<card>/<Variant>.json`) are
gone. A single `cards/<expansion>.toml` file is now the source of truth for
everything expansion-related: the cards, the pack/box materials, and the
pack/box items. This document is the design for rewiring the pipeline; it
supersedes the `Expansion.json` era. No code has been changed yet.

## 1. Source of truth

| Input | Role |
|---|---|
| `cards/<expansion>.toml` | expansion metadata: featured (`pack`), roster (`cards`), `background` table, `logo` table |
| `database/characters.json` | per character: `name` (→ title), `rarity`, `manufacturer` |
| `database/models.json` | per model id: `name` (→ subtitle: the model name minus the character name) |
| `nikke-viewer` listers | `--list-animations <id>` (photo reel + the Special pick) |
| Pipeline constants | viewport 1640×2048 (the viewer's default), padding 50, 60 fps (viewer default) |

Per-card tuning fields no longer exist anywhere: `pan`, `zoom`, `viewport`,
`padding`, `framerate`, `invert_logo`, `invert_copyright`, per-variant
`background`, per-variant `time`. Framing is fixed per presentation by the
viewer flags; backgrounds come from the expansion's `background` table.

## 2. Data model (`cards/<expansion>.toml`)

```toml
# featured characters (first = hero); each has an id and optional
# per-character overrides: a horizontal nudge x (the material's native
# pixels, applied before the downscale), an animation (which of the
# character's animations to show), a time (the second to still on; 0) and a
# zoom (a multiplier on the framing; 1.0)
pack = [
    { id = "c010", animation = "action", time = 1.247, zoom = 0.9 },
    { id = "c011" },
    { id = "c013" },
]
cards = [ { id = "c010" }, … ]           # the full roster, in set order

[logo]
path = "../assets/images/logos/ELYSION.png"
placement = "bottom"                     # top | center | bottom

[background]
base = "../assets/images/backgrounds/sky-night.png"
special = "../assets/images/backgrounds/sky-sunset.png"
battle = "../assets/images/backgrounds/smoke-pink.png"
```

- `pack`: the featured characters. Each entry is a table with the
  character's `id` and optional per-character overrides: an `x` (a
  horizontal nudge in the material's native pixels, applied to the
  character's position before compositing, before the downscale, so it
  scales with the material), an `animation` (which of the character's
  animations to show; the viewer's default when absent), a `time` (the
  second of that animation to still on; 0, the first frame, when absent)
  and a `zoom` (a multiplier on the framing; the viewer's default 1.0 when
  absent). The first entry is the hero (centered on the front); the rest
  flank it (unchanged composition rules).
- `cards`: one table per character, in set order. `id` is the character id;
  suffixed ids (c010_02) are skins, treated as their own character. The list
  order drives the card numbering (section 4).
- All paths resolve **relative to the file's directory** (`cards/`) — not to
  a set directory (there is no set directory any more).
- `background.base`: the expansion's scene; used by every presentation
  unless stated otherwise, and by the pack/box front and back.
- `background.special`: the Standard/Full-art Special presentations.
- `background.battle`: the Profile and Full-art Cover/Aim presentations.

## 3. Unit of work: (expansion, character, presentation)

A card is a triple. For every entry in `cards`, the pipeline generates the
presentations of section 3.1 — 14 when the character has an `sc` variant and
a reel animation (23 files: 14 PNGs + 9 MP4s), 13 when it has a reel but no
`sc` (21 files), and 11 when it has neither (19 files): the Goddess
presentation is skipped when the character has no `sc` variant (the viewer
has no `sc` variant to frame), and the two Special presentations are skipped
when the character has no reel animation. Each MP4 keeps its first-frame PNG
sidecar, as today.

### 3.1 Presentation matrix

Viewer flags for `nikke-viewer <id>` (flags precede the id; `--width/--height`
= the run size, native × preset scale, even dims; `--stdout` always).
"default" animation = the variant's preferred one (no `--animation` flag).

| Presentation | Output stem suffix | Framing flags | Variant | Animation | Time | Background | Mask |
|---|---|---|---|---|---|---|---|
| Classic standard | `_ClassicStandard` | `--half-body` | fb | default | `0` | `base` | standard |
| Special standard | `_SpecialStandard` | `--half-body` | fb | reel pick | `0` | `special` | standard |
| Exotic standard | `_ExoticStandard` | `--half-body` | fb | `action` | loop | `base` | standard |
| Classic profile | `_ClassicProfile` | face + body | fb | default | `0` | `base` | profile |
| Idle profile | `_IdleProfile` | face + body | fb | `idle` | loop | `base` | profile |
| Cover profile | `_CoverProfile` | face + body | `--variant cover` | default | loop | `battle` | profile |
| Aim profile | `_AimProfile` | face + body | `--variant aim` | default | loop | `battle` | profile |
| Classic full art | `_Classic` | `--half-body` | fb | default | `0` | `base` | none |
| Idle full art | `_Idle` | `--half-body` | fb | `idle` | loop | `base` | none |
| Cover full art | `_Cover` | (default fit) | `--variant cover` | default | loop | `battle` | none |
| Aim full art | `_Aim` | (default fit) | `--variant aim` | default | loop | `battle` | none |
| Special full art | `_Special` | `--half-body` | fb | reel pick | `0` | `special` | none |
| Exotic full art | `_Exotic` | `--half-body` | fb | `action` | loop | `base` | none |
| Goddess full art | `_Goddess` | (default fit) | `--variant sc` | default | loop | solid black | none *(only when the character has an `sc` variant)* |

- "face + body" = the profile's two lockstepped streams (unchanged design):
  the face stream adds `--face 2 --offset-x N` (N from the occlusion
  measurement, section 5.3); the body stream uses the **default framing** —
  the `--full-body` flag is gone (full body is now the viewer's default).
- `--time 0` → one frame (PNG). No `--time` → the whole animation (MP4 +
  first-frame PNG).
- "like Standard but without the mask" (full art) = the Standard pipeline
  with the mask compositing step, the auto-contrast and the fade-to-dominant
  removed; the background is the scene fitted to the frame and left as-is.
- Goddess: `--variant sc` only, per decision — the `sc` variant's preferred
  animation. Solid black background (no fit/fade).
- **Goddess is conditional**: availability is checked per character with
  `nikke-viewer --list-variants <id>`; when `sc` is absent the presentation
  is skipped entirely (no output, no metadata entry — section 5.7). In
  ELYSION six of the 21 characters lack `sc` (Delta, Soldier EG/FA/OW, and
  the two skins).
- **The Special presentations are conditional on the reel**: their
  animation is the reel's pick (section 3.2). A character with none of the
  `PROFILE_REEL_ANIMATIONS` has no reel, so its two Special presentations
  are skipped the same way. In ELYSION c300, c301 and c306 have no reel
  animation.
- All 21 have `aim` and `cover` and the `idle`/`action` animations, so no
  other presentation is conditional. The set yields 15 × 23 + 3 × 21 +
  3 × 19 = 465 card files.
- `--no-video` behavior is unchanged: animated presentations render their
  first frame alone.

### 3.2 Animation resolution

- **default**: omit `--animation`; the viewer uses the variant's preferred
  animation (fb / aim / cover / sc each have their own).
- **reel pick** (Special, both tiers): the first of the existing
  `PROFILE_REEL_ANIMATIONS` preference list
  (`think`, `smile`, `shy`, `no`, `delight`, `surprise`, `special_02`,
  `special`, `angry`) that appears in `nikke-viewer --list-animations <id>`
  (the fb variant's list). Error when none match. (For c010: `think`.)
- **explicit**: `action` (the Exotic and ExoticStandard), `idle` (the Idle
  profile and the Idle full-art).
- The photo reel itself is unchanged: the first 3 available reel animations,
  one `--portrait 1 --time 0 --animation <a>` still each, from the **fb**
  list for every profile presentation (including Cover/Aim).

## 4. Naming

Card stems stay in the legacy shape (`0001_Rapi_…`), derived from data:

```
title             = the character's `name` from `characters.json`
                    (a suffixed id falls back to its base character's name,
                     as the rarity does)
subtitle          = the model's `name` from `models.json` for the same id,
                    minus the leading character name ("Rapi White Promise"
                    − "Rapi" → "White Promise"); a base model's name equals
                    the character's name, so its subtitle is empty
compact(s)        = s with all whitespace removed
stem_name         = compact(title) + ("_" + compact(subtitle) if subtitle)
number            = the entry's 1-based position in the expansion's `cards` list
stem              = f"{number:04d}_{stem_name}"          e.g. "0001_Rapi"
```

- The name part is verified against the deleted definitions for all 26
  characters (ELYSION 21, TETRA 4, MISSILIS 1), including `Soldier EG` →
  `SoldierEG` and the two skins (`Rapi_WhitePromise`,
  `Diesel_BlackSunday`). For ELYSION, position + name part reproduces every
  one of the 21 legacy stems exactly.
- An id missing from `models.json`, or a model name that does not start
  with the character's name, is a hard error (the subtitle cannot be
  derived).
- Numbering is always positional: TETRA and MISSILIS have no TOMLs yet
  (their legacy card content was partial leftovers), so their stems number
  from 1 and differ from the legacy filenames (section 7).
- Profile/standard suffixes are unchanged: `<stem>_ClassicProfile`,
  `<stem>_ExoticStandard`, …; full art is bare `<stem>_<Variant>`.
- Output paths: `preset.set_path(<set>) / f"{stem}_{presentation}.{ext}"`
  (e.g. `output/ELYSION/0001_Rapi_Exotic.mp4`,
  `draft/ELYSION/0020_Rapi_WhitePromise_CoverProfile.png`).
- The bundle metadata `Sprite` field follows: `f"{stem}_{presentation}"`
  (legacy-compatible, e.g. `0001_Rapi_ExoticStandard`).
- The name plate (profile + standard cards) shows `title` and `subtitle`;
  the metadata `Name` field is `f"{title}: {subtitle}"` when there is a
  subtitle, else `title` (legacy format).

## 5. Pipeline design

### 5.1 Expansion loading and discovery

- `load_expansion(path)`: `tomllib`-parse `cards/<set>.toml`; validate the
  fields (`pack`/`cards` non-empty id lists, `background.{base,special,battle}`,
  `logo.{path,placement}` with `placement` in `top|center|bottom`).
- Discovery: `cards/*.toml` (sorted) replaces the set-directory scan and
  `EXPANSION_NAME`; the set name is the file stem.
- All relative paths (backgrounds, logo) resolve against the TOML's parent
  (`cards/`).

### 5.2 Viewer invocation

One helper builds the argument list:

```
nikke-viewer [<framing>] [--variant V] [--animation A] [--time T]
             --width W --height H --stdout <id>
```

- Framing: `--half-body` (the standard's, and the full-art's classic, idle,
  special and exotic) or `--face 2 --offset-x N` (the profile's face stream);
  the profile's body stream and the full-art's cover, aim and Goddess use no
  framing flag (the default full-body fit).
- Lister calls become id-based: `--list-animations <id>` (the photo reel,
  the Special pick) and `--list-variants <id>` (the Goddess condition,
  section 3.1).
- Retries and stream handling are unchanged: `RENDER_ATTEMPTS = 3`,
  `_read_exact`/`_reap_viewer`/`_PipeDrain` (shared GPU — transient failures
  happen; the first frame of a truncated stream is never trusted).
- `--framerate` is not passed (viewer default 60 = `DEFAULT_FRAMERATE`);
  viewport defaults (1640×2048) are the native size; the run size is
  `native × preset.scale`, rounded to even dims, exactly as today.

### 5.3 Card rendering

- `render.py`'s three entry points (`_process_card`, `_process_profile_card`,
  `_process_standard_card`) become presentation-driven: they take a
  `Presentation` (the row of section 3.1, precomputed per
  (expansion, character, presentation)) instead of a definition file.
- What disappears from their inputs: definition loading
  (`_load_card`/`_background_path`), `pan`/`zoom` (the flags replace them),
  `viewport`/`padding`/`framerate`/`invert_*` (constants and tier defaults).
- What is unchanged: the in-memory compositing
  (`_stream_composited`, `_stream_dual_composited`, `image.py`,
  `lettering.py`, `video.py`), the profile's tint/mask/face-offset/photo-reel
  machinery, the standard's contrast/fade, the name plates, the
  manufacturer logo (DB `manufacturer` → `assets/images/logos/<m>.png`),
  the first-frame sidecar, atomic writes.
- Logo/copyright colors: full art uses the white logo + white copyright
  (the legacy default); profile and standard keep black.
- The profile's `_face_offset` measures the body's first frame with the
  default framing (it used to pass `--full-body`).

### 5.4 Backgrounds and masks

- `base`/`special`/`battle`: loaded once per (expansion, key), fitted per
  tier (standard: fit → auto-contrast(cutoff 20) → fade-to-dominant →
  standard mask; profile: `_profile_layers`; full art: fit —
  no auto-contrast, no fade, no mask).
- Solid black (Goddess): a filled RGB frame; no fit/fade.
- Masks (`STANDARD_MASK_PATH`, `PROFILE_MASK_PATH`), the white NIKKE logo,
  the font: unchanged assets.

### 5.5 Source hashes and up-to-date checks

The `nikke-reborn-source` hash embedded in each finished file becomes a
SHA-256 over, in fixed order:

1. the expansion TOML's bytes,
2. the card stem (e.g. `0001_Rapi`),
3. the presentation name,
4. the canonical viewer arguments (variant, animation or `default`,
   `time 0` or `loop`),
5. the background's bytes (the resolved file; a fixed `solid-black` marker
   for Goddess),
6. the mask's bytes (standard/profile; omitted for full art),
7. the NIKKE logo's bytes (the black/white face used),
8. the manufacturer logo's bytes (when the character has one),
9. `database/characters.json`'s and `database/models.json`'s bytes
   (name/rarity/manufacturer, the subtitle derivation),
10. the font's bytes (the name plate),
11. the scale term `f"{scale:g}"` — **mixed in only when the scale ≠ 1.0**
    (the legacy convention, so the ultra outputs stay the canonical bytes).

This replaces `_source_hash` / `_profile_source_hash` /
`_standard_source_hash` (which hashed the definition file's bytes). The
up-to-date check is unchanged in shape: skip when the stored hash matches;
animated outputs also require the fresh first-frame sidecar.

Pack/box (section 5.6) digests:

- front digest: the TOML's bytes + the featured entries (their ids, `x`
  nudges and `animation`/`time`/`zoom` overrides) + the `base` background
  bytes + the expansion logo's bytes + the white NIKKE logo's bytes + the
  template's bytes (the featured renders' pixels are not hashed, same trust
  model as the legacy definition hashes).
- back digest: `base` background bytes + template (as today).
- item hashes: mesh + finished material + viewer config + scale (unchanged).

### 5.6 Pack and box

Mechanically "mostly unaffected":

- `pack.py`/`box.py` take the expansion (TOML path + data) instead of a
  pack directory; the set name is the TOML stem.
- `load_background`/`load_logo` read the `background` table (`base`) and the
  `logo` table; paths resolve against `cards/`.
- The featured NIKKEs render via the new viewer: `nikke-viewer
  [--animation <a>] --time <t> [--zoom <z>] --half-body --stdout <id>` — one
  raw RGBA frame per featured id (that character's `time`, default 0, on its
  `animation`, the viewer's default, zoomed by its `zoom`, the viewer's
  default 1.0 — the half-body framing, the viewer's default 1640×2048
  viewport), then the existing content-box trim and front composition (backs
  first, hero on top, each with its `x` nudge, glow logo at `placement`).
- Everything else (mask rectangles, item rendering via `unity-viewer`,
  atomic saves) is unchanged.

### 5.7 Metadata, bundle, simulate

- `metadata.cards()`: built from the TOML's `cards` list × the
  presentations the character supports (section 3.1 — the Goddess entry is
  omitted for characters without an `sc` variant, so the bundle never
  references a missing sprite). No per-card variant subsets any more.
  Per entry: `Name` from title/subtitle, `Rarity` = the presentation
  (unchanged convention), border via the existing `VARIANT_BORDER` +
  character-rarity bonus (from the DB; a suffixed id falls back to its base
  character, as today; unknown ids still default to `R` with a warning),
  `IsFoil` for Exotic/Goddess (+ ExoticStandard), `Sprite` per section 4.
- The `RARITIES` list, price strategy, pack slot weights (uniform across
  sets today) and `bundle()`/`pack()`/`box()` shapes are unchanged.
- `metadata.write()` iterates `cards/*.toml`.
- `simulation`: `_load_expansion(name)` resolves `cards/<name>.toml`
  (accepting the `cards/` prefix as today); the rest of the simulation is
  untouched.

### 5.8 Spritesheet

Adapts lookups only: expansion data from the TOML (background `base`, logo),
set name from the stem, output stems per section 4. The sheet composition is
unchanged.

### 5.9 CLI

- `generate [paths] [--ids ID …] [--draft | --ultra] [--force]
  [--no-video] [--jobs N]`
  - paths: an expansion — `cards/<set>.toml`, `<set>.toml`, or the bare set
    name — resolved against the repo root / `cards/`; no paths = every
    `cards/*.toml`.
  - `--ids`: optional character filter; ids must exist in every selected
    expansion (error otherwise).
  - Scope: an expansion in scope ⇒ its pack + box + metadata bundle are in
    scope too (the legacy runs always picked up the set's pack/box).
- `test <expansion> [ID …] [--ultra] [--new-baseline]` — same selection
  rules; forces a single-worker re-render (section 6).
- `bundle`, `simulate <set>`, `spritesheet <set>`: unchanged surfaces,
  TOML-backed internals.

## 6. Tests and baselines

- Baselines move to per-character files plus one expansion file:
  - `tests/baselines/<set>/<stem>.<preset>.sha256` — the character's
    presentation files (23 when it has the `sc` variant and a reel, 21
    without the `sc`, 19 without the `sc` and the reel; same format and
    naming as today's `<card>` files).
  - `tests/baselines/<set>/expansion.<preset>.sha256` — the 4 pack/box
    files (today they are duplicated into every card's baseline; the
    expansion baseline replaces that duplication).
- `test` compares exactly the files a forced `--jobs 1` run writes (the
  legacy check shape), and re-records with `--new-baseline`.
- The byte protocol keeps its determinism rule: same code + inputs +
  single worker ⇒ identical bytes; `--ultra` outputs are the canonical
  bytes (scale term folded in only at non-1.0 scales).
- Legacy byte-for-byte equivalence with the pre-redesign outputs is **not
  achievable for the cards** (the per-variant inputs and the viewer itself
  changed; some animations differ by design). All baselines are
  re-recorded after the rewrite, default preset first, `--ultra` last.
  AGENTS.md's byte-protocol section gets a matching update at the end.

## 7. Other sets

ELYSION is the pilot. TETRA and MISSILIS need their TOMLs created (data
work, with the roster known from the deleted definitions):

| Set | Roster (legacy order → id) |
|---|---|
| TETRA | 0006_Alice → c191, 0015_Aria → c432, 0016_Anis → c012, 0017_Belorta → c060 |
| MISSILIS | 0009_Admi → c172 |

Their legacy card content was partial leftovers (sparse, non-contiguous
prefixes: 6/15/16/17 and 9); the new TOMLs number from 1 by position
(section 4), so their stems differ from the legacy filenames and their
baselines are recorded fresh. Their `background`/`logo` tables are chosen
from the assets the legacy definitions referenced when the TOMLs are
authored.

## 8. Execution plan

1. **Core**: `expansion.py` (TOML load/validate/discovery, backgrounds,
   logo, front digest) + the `Presentation` model and naming (sections 3–4)
   + the new source hashes (section 5.5).
2. **Render**: the viewer argument builder (section 5.2) and the
   presentation-driven `_process_*` / profile / standard / reel / face-
   offset adaptations (section 5.3). Verify end-to-end on one character at
   draft scale.
3. **Selection & CLI**: expansion/ids selection for `generate` and `test`
   (sections 5.9, 6); retire the JSON-discovery code in `card.py`.
4. **Pack & box** (section 5.6).
5. **Metadata / simulate / spritesheet / bundle** (sections 5.7–5.8).
6. **Verify**: full ELYSION generate (default), eyeball pass,
   `uvx ruff check src/` clean, re-record baselines (`--jobs 1`), then the
   `--ultra` pass; update AGENTS.md (command forms, byte-protocol wording).
7. **TETRA + MISSILIS**: author the TOMLs (section 7), generate + baseline.

Throughout: `--jobs 1` for byte-protocol work, retry transient
`nikke-viewer` failures, and no `--ultra` until step 7.
