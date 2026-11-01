# Design note: splitting `nikke_reborn/__init__.py` into modules

Status: **in progress** — migration steps 1 (leaves: `config.py`,
`error.py`, `file.py`), 2 (middle: `image.py`, `lettering.py`,
`video.py`), and 3 (domain: `card.py`, `render.py`, and the material/item
merge into `pack.py`/`box.py`/`file.py`/`expansion.py`) done and verified
(see §7); steps 4–5 remaining.
Scope: pure code movement plus the documented renames in §6.4.
No behavior changes.

Iterations so far: module names are singular (§3, §4); `pipeline.py` →
`generate.py` and new `bundle.py`, both with a `run` entrypoint,
`bundler.py` untouched; `util.py` → `file.py`; `material.py` merged into
`pack.py`/`box.py`/`file.py`/`expansion.py`; `frame.py` + `presentation.py`
→ `render.py`; all four console entrypoints normalized to `run`; the
material hash helpers renamed (§4–§8); the copyright stamping
(`_with_copyright`, `_logo_copyright_overlay`), its `COPYRIGHT_*` constants,
`_text_ink_offsets`, and `MANUFACTURER_LOGO_WIDTH` were placed in `lettering.py`
rather than `image.py`/`config.py` — they are stamp/typography concerns, and
co-locating them with the name stack keeps the import graph acyclic (§5).
Step 3 placed `_find_pack_dirs` in `expansion.py` (Appendix A) and, because the
encoder preset/scale selection and the ffmpeg-prober path are shared by at least
two modules, placed those too in `config.py` (§6.1) rather than the
`generate.py`/`video.py` homes Appendix A listed — the former would have put a
`render.py → generate.py → render.py` cycle back in. `_find_pack_dirs`'s
function-local `from nikke_reborn import expansion` became a self-import once it
moved, so it now reads the module-level `EXPANSION_NAME` directly; and the
function-local pack/box imports in `_generate_variants` were lifted to the top of
the function (a `from … import _find_pack_dirs` placed below its first call would
leave the name unbound).

## 1. Background

`src/nikke_reborn/__init__.py` has grown to 4,477 lines: the pipeline docstring,
~360 lines of constants, and the entire card-rendering pipeline (discovery,
hashing, viewer pipe streaming, compositing, typography, frame writing, MP4
encoding, pack/box materials and items, CLI, and the three generation passes).
It is time to split it into smaller, self-contained modules.

## 2. Current state

### 2.1 Inventory of `__init__.py` (line ranges)

| Region | Content |
|---|---|
| 1–103 | 103-line module docstring describing the whole pipeline |
| 104–140 | Imports (`argparse`…`PIL`, plus `bundler`, `metadata`) |
| 142–503 | Constants: paths, executables, presets, stems, masks, fonts, layout tuning, pack/box assets |
| 504–548 | `GenerationError`, `generate()` entry point |
| 549–724 | `_set_cards`, `_write_metadata`, `bundle()` entry point |
| 725–955 | `_require_executable`, source/output hashing, card discovery & selection, config loading |
| 956–1289 | Viewer pipe streaming: `_PipeDrain`, `_read_exact`, `_reap_viewer`, `_stream_composited`, `_stream_dual_composited` |
| 1290–1571 | PIL primitives: fit/dominant-color/monochrome/tint, profile & standard layers, logo & copyright stamping |
| 1572–2003 | Typography: font weight, text measurement, name/subtitle sizing, context sampling, `_NameLayers`, `_name_layers`, `_apply_name` |
| 2004–2510 | Frame output: `_with_copyright`, `_logo_copyright_overlay`, `_composite_frame`, `_encode_mp4`, `_save_atomic`, `_render_and_finish`, `_FirstFrameWriter`, `_write_final_card`, `_first_frame` |
| 2511–3382 | Presentations: `_face_offset`, `_reel_animations`, `_photo_reel`, `_render_profile`, `_render_standard`, `_card_out_path`, `_process_card`, `_profile_stem`, `_standard_stem`, `_process_profile_card`, `_process_standard_card` |
| 3383–3791 | Pack/box: mask helpers, `_find_pack_dirs`, `_pack_hash`, `_pack_output_up_to_date`, `_solve_linear`, `_process_pack_material`, `_process_box_material`, `_viewer_hash`, `_viewer_output_up_to_date`, `_process_pack_item`, `_process_box_item` |
| 3792–4459 | Orchestration: `_default_jobs`, `_stage_threads`, `_run_notes`, `_parse_args`, `_timings_suffix`, `_generate_profiles`, `_generate_standards`, `_generate_variants` |
| 4460–4477 | `copy()` file-copy helper |

### 2.2 The package root is a hub

Sibling modules (`box.py`, `pack.py`, `expansion.py`, `simulation.py`,
`spritesheet.py`) all do `import nikke_reborn as nr` and reach in for:

- **~20 constants** — `IMAGES_DIR`, `CARDS_DIR`, `REPO_ROOT`, `OUTPUT_DIR`,
  `DRAFT_DIR`, `FONT`, `VIEWER`, `PACK_TEMPLATE`, `BOX_TEMPLATE`,
  `STANDARD_STEMS`, `PROFILE_STEMS`, `PROFILE_RARITIES`, `SOURCE_HASH_KEY`,
  `MAX_STAGE_THREADS`, `CARD_REFERENCE_WIDTH`, `COPYRIGHT_*` (4 names)
- **~15 private helpers** — `_pack_mask`, `_pack_mask_rects`,
  `_box_side_mask`, `_box_top_mask`, `_load_card`, `_source_hash`,
  `_PipeDrain`, `_read_exact`, `_reap_viewer`, `_set_cards`, `_set_weight`,
  `_text_ink_offsets`, `_save_atomic`
- **`GenerationError`** — raised in 36 places across `box`, `pack`,
  `expansion`, and the `__init__` code itself

### 2.3 External surface

The only consumers outside the package are the console scripts in
`pyproject.toml`:

```toml
generate    = "nikke_reborn:generate"
bundle      = "nikke_reborn:bundle"
spritesheet = "nikke_reborn.spritesheet:spritesheet"
simulate    = "nikke_reborn.simulation:simulate"
```

Nothing else (scripts, docs, CI) imports `nikke_reborn`, so the internal
layout can change freely. All four console scripts must keep working.

## 3. Goals and non-goals

Goals:

- One module per concern; each module self-contained (its tuning constants
  live inside it).
- Module names are singular domain nouns (`image`, `render`, `card`),
  matching the existing `box`, `pack`, `expansion`, `spritesheet`.
- Acyclic import graph, layered leaves → orchestration.
- Console scripts keep working.
- Pure moves: no line is rewritten except its imports/docstring. Anything
  that looks like a bug gets a note, not an inline fix. The only
  deliberate rewrites are the documented renames in §6.4 (every
  entrypoint becomes `run`; two material helpers are corrected).
- Module docstrings in the style already set by `box.py`/`pack.py`.

Non-goals:

- No behavior changes, no new tests, no renames beyond the documented
  list in §6.4 (the "drop the underscore from cross-module helpers" pass
  is a possible follow-up). Existing modules `box.py`, `pack.py`,
  `expansion.py` gain functions but their current logic is unchanged
  (pure moves, verbatim).

## 4. Target layout

| Module | Gets | ~lines |
|---|---|---|
| `__init__.py` | The big docstring (it *is* the package doc) and nothing else | ~110 |
| `config.py` | Only the **shared** constants (used by ≥2 modules) — see Appendix A | 92 |
| `error.py` | `GenerationError` | ~5 |
| `file.py` | `copy()`, `_save_atomic`, `_require_executable`, output-hash freshness: `_stored_hash` (from `card.py`), `_material_hash` (was `_pack_hash`), `_material_output_up_to_date` (was `_pack_output_up_to_date`), `_viewer_hash`, `_viewer_output_up_to_date` | ~230 |
| `image.py` | PIL primitives: `_fit_background`, `_dominant_color`, `_monochrome_luts`, `_monochrome`, `_scale_linear_light`, `_tint_wash`, `_tint_at_luma`, `_fade_to_dominant`, `_scale_logo`, `_with_logo`, `_profile_layers`, `_standard_layers`, `_set_luma`, template-mask helpers (`_pack_mask`, `_pack_mask_rects`, `_box_side_mask`, `_box_top_mask`) + colocated constants (`PROFILE_MASK_PATH`, `STANDARD_MASK_PATH`, `PROFILE_TINT_*`, `LOGO_PADDING_FACTOR`, `LOGO_NOMINAL_WIDTH`) | 438 |
| `lettering.py` | `_set_weight`, `_text_ink_offsets`, `_name_font_size`, `_subtitle_font_size`, `_sample_context`, `_rect_tint`, `_tint_layer`, `_NameLayers`, `_name_layers`, `_apply_name`, `_with_copyright`, `_logo_copyright_overlay` + `NAME_*`, `SUBTITLE_*`, `CONTEXT_*`, `FONT_NAME`, `FONT_RECT_ARROW`, `COPYRIGHT_*`, `MANUFACTURER_LOGO_WIDTH` | 608 |
| `video.py` | `_PipeDrain`, `_read_exact`, `_reap_viewer`, `_stream_composited`, `_stream_dual_composited`, `_encode_mp4` + `PIPE_BUFSIZE`, `DEFAULT_FRAMERATE`, `FFMPEG_QUALITY_ARGS`, `ENCODER`, `PROBER` | 507 |
| `card.py` | Card-configuration domain: `_find_card_configs`, `_expand_card_paths`, `_selected_configs`, `_load_card`, `_background_path`, `_character_manufacturer`, `_manufacturer_logo`, `_profile_stem`, `_standard_stem`, `_card_out_path`, source hashes (`_source_hash`, `_profile_source_hash`, `_standard_source_hash`) + `LOGO_PATHS` | ~290 |
| `render.py` | One card → its output files and the two presentations: `_composite_frame`, `_render_and_finish`, `_FirstFrameWriter`, `_write_final_card`, `_first_frame`, `_face_offset`, `_reel_animations`, `_photo_reel`, `_render_profile`, `_render_standard`, `_process_card`, `_process_profile_card`, `_process_standard_card` + `RENDER_ATTEMPTS`, `PROFILE_FACE_*`, `PROFILE_REEL_*` | ~1,250 |
| `generate.py` | Orchestration: `run()` entrypoint, `_parse_args`, `_default_jobs`, `_stage_threads`, `_run_notes`, `_timings_suffix`, `_generate_profiles`, `_generate_standards`, `_generate_variants` + `DEFAULT_PRESET`, `DRAFT_PRESET`, `DEFAULT_SCALE`, `DRAFT_SCALE` | ~750 |
| `bundle.py` | The `bundle()` entrypoint as `run()`, plus `MOD_NAME` | ~110 |
| `metadata.py` | + `_set_cards`, `_write_metadata` | +175 |
| `pack.py` | + `_process_pack_material`, `_process_pack_item` (the pack's complete story: front/back composition, material, item) | +115 |
| `box.py` | + `_process_box_material`, `_process_box_item` (likewise for the box) | +145 |
| `expansion.py` | + `_find_pack_dirs` ("``cards/`` subdirectories carrying an ``Expansion.json``") | +15 |

Existing modules `box.py`, `pack.py`, `expansion.py` keep their logic and
gain the code above (pure moves); `simulation.py`, `spritesheet.py`
change their imports and rename their entrypoint to `run()` (Appendix B).

## 5. Dependency layering

All import edges point downward; the graph is acyclic:

```
__init__.py        (docstring only; no imports)
generate.py  ----->  render.py, card.py, box.py, pack.py,
                     expansion.py, metadata.py, file.py,
                     config.py, error.py
bundle.py         -->  bundler.py, metadata.py, file.py, config.py
render.py       -->  card.py, video.py, image.py, lettering.py,
                      file.py, error.py
card.py          -->  config.py, error.py
box.py, pack.py (existing) --> image.py, file.py, config.py, error.py
expansion.py (existing) --> card.py, video.py, config.py, error.py
image.py          -->  config.py
lettering.py      -->  image.py, config.py
video.py          -->  image.py, lettering.py, config.py, error.py
file.py           -->  config.py, error.py
config.py, error.py, bundler.py (leaves; no intra-package imports)
```

Notes:

- `_set_luma` is used only by `lettering.py` (`_rect_tint`, the name/subtitle
  bar fill). It lives in `image.py` (it is pure color math); `lettering.py`
  imports it.
- `lettering.py` therefore depends on `image.py`: `_rect_tint` uses its
  `_set_luma` (the bar-fill color math) and `_logo_copyright_overlay` uses
  its `_scale_logo`/`_with_logo` (the per-frame logo + copyright overlay).
  That direction is why the copyright stamp (`_with_copyright`,
  `_logo_copyright_overlay`), `_text_ink_offsets`, `MANUFACTURER_LOGO_WIDTH`
  and the `COPYRIGHT_*` constants live in `lettering.py`: `_logo_copyright_overlay`
  calls `_with_copyright`, so the two must sit in the same module, and
  keeping the whole stamping concern in the upper (`lettering`) module avoids an
  `image` ↔ `lettering` cycle.
- Once the layering exists, the function-local
  `from nikke_reborn import expansion` / `box, pack` imports inside
  `_find_card_configs`, `_expand_card_paths`, `_find_pack_dirs`, and
  `_generate_variants` can be hoisted to module top-level in
  `card.py`/`generate.py`.
- In the end state `import nikke_reborn` loads only the docstring module;
  the heavy graph loads when a console script imports its entry module —
  so the console scripts cost about what they do today, and a plain
  package import is cheaper than it is today.

## 6. Key decisions

1. **Co-locate constants with their consumers.** Only names used by ≥2
   modules go to `config.py`. The ~200 lines of presentation tuning
   (`PROFILE_TINT_*`, `NAME_*`, `FFMPEG_QUALITY_ARGS`, …) move next to the
   code they tune. Each module becomes genuinely self-contained;
   `config.py` holds only the shared vocabulary (dirs, stems, fonts,
   hash key, pack/box asset names).
2. **`GenerationError` in a tiny `error.py`.** It is raised at every layer
   (video, image, card discovery, expansion, box, pack), so it must live in
   a leaf module to keep the graph acyclic. Putting it in `generate.py` or
   `card.py` would create import cycles.
3. **Kill the `nr.` indirection.** Siblings switch to explicit imports
   (e.g. `from nikke_reborn.image import _pack_mask, _pack_mask_rects`).
   The `import nikke_reborn as nr` pattern is exactly what grew the hub; it
   is not carried into the new modules.
4. **Documented renames (the only non-pure-move edits).** Module names
   carry the domain words, so every console entrypoint is a plain `run`,
   and two misnamed material helpers are corrected. The full list:
   - `generate` → `generate.run`
   - `bundle` → `bundle.run`
   - `spritesheet` → `spritesheet.run`
   - `simulate` → `simulation.run`
   - `_pack_hash` → `_material_hash`
   - `_pack_output_up_to_date` → `_material_output_up_to_date`
   `pyproject.toml` targets update accordingly (Appendix B). No facade
   re-exports; `__init__.py` shrinks to the docstring. `bundler.py` stays
   untouched — `bundle.py` is a new module that imports it
   (`bundle.run` calls `bundler.build`).
5. **Docstrings migrate, not vanish.** The 103-line block stays as the
   package docstring in `__init__.py`; each new module gets a docstring
   extracted from the relevant paragraphs, in the style of `box.py`/`pack.py`.
6. **Pure moves only.** No behavior edits in this refactor. If a line looks
   wrong during the move: note it (see the §8 follow-ups), fix it in a
   follow-up. This
   keeps the diff reviewable.
7. **Optional follow-up (not this refactor):** several `_private` helpers
   are clearly cross-module APIs now (`_pack_mask_rects`, `_source_hash`,
   `_set_weight`, …). A later pass can drop the underscore where warranted.

## 7. Migration plan

Each step leaves the tree green and is a reviewable commit. Temporary
re-imports in `__init__.py` keep the siblings' `nr.X` references working
until step 5 removes them.

1. **Leaves.** Create `config.py`, `error.py`, `file.py`; move their
   contents (Appendix A). `__init__.py` re-imports the moved names.
2. **Middle.** Extract `image.py`, `lettering.py`, `video.py` (functions +
   colocated constants + docstring slices). Same temporary re-imports.
3. **Domain.** Extract `card.py` and `render.py` (frame output + the two
   presentations); merge the material/item processing:
   `_process_pack_material`/`_process_pack_item` → `pack.py`,
   `_process_box_material`/`_process_box_item` → `box.py`, the freshness
   helpers (`_material_hash`, `_material_output_up_to_date`,
   `_viewer_hash`, `_viewer_output_up_to_date`, and `_stored_hash` moving
   from `card.py`) → `file.py`, `_find_pack_dirs` → `expansion.py`,
   `UNITY_VIEWER` → `config.py`. Apply the §6.4 renames as the code lands.
4. **Orchestration.** Extract `generate.py` (entrypoint `run()`, passes,
   argparse); create `bundle.py` (the current `bundle()` as `run()`, plus
   `MOD_NAME`); move `_set_cards`/`_write_metadata` → `metadata.py`.
   `bundler.py` is untouched.
5. **Cut the hub.** Update the five sibling modules to direct imports
   (Appendix B); rename the `spritesheet()`/`simulate()` entrypoints to
   `run()`; point `pyproject.toml` at the new entry points; strip the
   re-imports from `__init__.py`. Hoist the function-local
   `expansion`/`box`/`pack` imports to top-level.

### Verification per step (no test suite exists)

- `ruff` clean.
- `generate --help` (all flags).
- A `--draft` run of one card path, with and without `--no-video`
  (exercises PNG + MP4 paths, the up-to-date/hash skip, and the
  ffmpeg-free path).
- A `bundle` run on one set.
- A `simulate` and a `spritesheet` smoke run (they import the moved names).
- `git diff --stat` sanity: every hunk is a move, not an edit.

## 8. Resolutions and follow-ups

Resolved in the iterations (reflected in §4–§7):

- `frame.py` + `presentation.py` → one `render.py` (~1,250 lines); split
  again later if a clean seam appears (frame output vs. presentation
  rendering).
- The shared-constants module is `config.py`.
- All four console entrypoints normalized to `run` (`generate`, `bundle`,
  `spritesheet`, `simulation`) — §6.4.
- `_pack_hash`/`_pack_output_up_to_date` → `_material_hash` /
  `_material_output_up_to_date` — they also serve the box material
  (`_pack_hash(BOX_TEMPLATE, …)`), so the "pack" prefix was wrong — §6.4.
- `material.py` merged into `pack.py`/`box.py` (processors), `file.py`
  (freshness helpers), `expansion.py` (`_find_pack_dirs`) and `config.py`
  (`UNITY_VIEWER`); the ~35 lines of unity-viewer subprocess boilerplate
  are duplicated between `_process_pack_item` and `_process_box_item`, in
  the project's existing symmetric pack/box style.

Follow-ups (separate commits, not this refactor):

1. Remove `_solve_linear` (line 3492) — dead code, no call sites anywhere.
2. Collect any suspected bugs noticed during the pure-move into a list.
3. Drop the leading underscore from cross-module helpers
   (`_pack_mask_rects`, `_source_hash`, `_set_weight`, …) where warranted.
4. Split `render.py` if a clean seam emerges.

## Appendix A: name-by-name move map

Current `__init__.py` line → new home.

### → `config.py` (shared)

| Lines | Names |
|---|---|
| 144–153 | `REPO_ROOT`, `ASSETS_DIR`, `CARDS_DIR`, `IMAGES_DIR`, `MESHES_DIR`, `FONTS_DIR`, `OUTPUT_DIR`, `DRAFT_DIR`, `BUNDLES_DIR`, `DATABASE_DIR`, `SHOP_DIR` |
| 156, 157 | `VIEWER`, `UNITY_VIEWER` |
| 169 | `SOURCE_HASH_KEY` |
| 200, 217, 223 | `PROFILE_RARITIES`, `STANDARD_STEMS`, `PROFILE_STEMS` |
| 326 | `CARD_REFERENCE_WIDTH` |
| 348 | `FONT` |
| 461 | `MAX_STAGE_THREADS` |
| 474–482 | `PACK_TEMPLATE`, `PACK_MATERIAL_NAME`, `PACK_ITEM_NAME`, `PACK_MESH`, `PACK_CONFIG` |
| 493–501 | `BOX_TEMPLATE`, `BOX_MATERIAL_NAME`, `BOX_ITEM_NAME`, `BOX_MESH`, `BOX_CONFIG` |

### → `error.py`

| Lines | Names |
|---|---|
| 504 | `GenerationError` |

### → `file.py`

| Lines | Names |
|---|---|
| 725 | `_require_executable` |
| 772 | `_stored_hash` (moved out of `card.py`: its users are `render.py`, `file.py`'s own freshness helpers, and `spritesheet.py`) |
| 2188 | `_save_atomic` |
| 3445 | `_pack_hash` → `_material_hash` (§6.4) |
| 3468 | `_pack_output_up_to_date` → `_material_output_up_to_date` (§6.4) |
| 3642 | `_viewer_hash` |
| 3655 | `_viewer_output_up_to_date` |
| 4460 | `copy` |

### → `image.py`

| Lines | Names |
|---|---|
| 227, 230 | `PROFILE_MASK_PATH`, `STANDARD_MASK_PATH` |
| 235–251 | `PROFILE_TINT_TOP_OPACITY`, `PROFILE_TINT_BOTTOM_OPACITY`, `PROFILE_TINT_BOTTOM_FACTOR`, `PROFILE_TINT_GRADIENT_END` |
| 322, 331 | `LOGO_PADDING_FACTOR`, `LOGO_NOMINAL_WIDTH` |
| 1290 | `_fit_background` |
| 1304 | `_dominant_color` |
| 1320 | `_monochrome_luts` |
| 1353 | `_monochrome` |
| 1380 | `_scale_linear_light` |
| 1398 | `_tint_wash` |
| 1426 | `_tint_at_luma` |
| 1478 | `_profile_layers` |
| 1512 | `_standard_layers` |
| 1530 | `_fade_to_dominant` |
| 1547 | `_scale_logo` |
| 1561 | `_with_logo` |
| 1632 | `_set_luma` (used only by `lettering.py`, which imports it) |
| 3383 | `_pack_mask` |
| 3391 | `_box_side_mask` |
| 3400 | `_box_top_mask` |
| 3409 | `_pack_mask_rects` |

### → `lettering.py`

| Lines | Names |
|---|---|
| 334–345 | `COPYRIGHT_NOMINAL_SIZE`, `COPYRIGHT_WEIGHT`, `COPYRIGHT_SUPERSAMPLE`, `COPYRIGHT_TEXT` |
| 351, 354 | `FONT_NAME`, `FONT_RECT_ARROW` |
| 360–438 | `NAME_*`, `SUBTITLE_*`, `CONTEXT_*` (18 names) |
| 428 | `MANUFACTURER_LOGO_WIDTH` |
| 1572 | `_set_weight` |
| 1582 | `_text_ink_offsets` |
| 1604 | `_name_font_size` |
| 1613 | `_subtitle_font_size` |
| 1653 | `_sample_context` |
| 1691 | `_rect_tint` |
| 1699 | `_tint_layer` |
| 1715 | `_NameLayers` |
| 1740 | `_name_layers` |
| 1994 | `_apply_name` |
| 2004 | `_with_copyright` |
| 2042 | `_logo_copyright_overlay` |

### → `video.py`

| Lines | Names |
|---|---|
| 158, 159 | `ENCODER`, `PROBER` |
| 164 | `PIPE_BUFSIZE` |
| 171 | `DEFAULT_FRAMERATE` |
| 445 | `FFMPEG_QUALITY_ARGS` |
| 935 | `_read_exact` |
| 956 | `_PipeDrain` |
| 992 | `_reap_viewer` |
| 1024 | `_stream_composited` |
| 1129 | `_stream_dual_composited` |
| 2096 | `_encode_mp4` |

### → `card.py`

| Lines | Names |
|---|---|
| 463 | `LOGO_PATHS` |
| 730 | `_source_hash` |
| 736 | `_profile_source_hash` |
| 754 | `_standard_source_hash` |
| 812 | `_find_card_configs` |
| 845 | `_expand_card_paths` |
| 880 | `_selected_configs` |
| 889 | `_load_card` |
| 900 | `_background_path` |
| 909 | `_character_manufacturer` |
| 921 | `_manufacturer_logo` |
| 2935 | `_card_out_path` |
| 3069 | `_profile_stem` |
| 3076 | `_standard_stem` |

### → `render.py`

| Lines | Names |
|---|---|
| 319 | `RENDER_ATTEMPTS` |
| 254–270 | `PROFILE_FACE_ZOOM`, `PROFILE_FACE_CENTER_Y`, `PROFILE_FACE_BRIGHTNESS`, `PROFILE_FACE_OFFSET_LEFT`, `PROFILE_FACE_OFFSET_RIGHT` |
| 284–303 | `PROFILE_REEL_COUNT`, `PROFILE_REEL_SIDE`, `PROFILE_REEL_TOP`, `PROFILE_REEL_MARGIN`, `PROFILE_REEL_BORDER`, `PROFILE_REEL_BORDER_ALPHA`, `PROFILE_REEL_ANIMATIONS` |
| 2070 | `_composite_frame` |
| 2211 | `_render_and_finish` |
| 2326 | `_FirstFrameWriter` |
| 2375 | `_write_final_card` |
| 2479 | `_first_frame` |
| 2511 | `_face_offset` |
| 2551 | `_reel_animations` |
| 2578 | `_photo_reel` |
| 2645 | `_render_profile` |
| 2801 | `_render_standard` |
| 2956 | `_process_card` |
| 3083 | `_process_profile_card` |
| 3226 | `_process_standard_card` |

### → `pack.py` (existing module, extended)

| Lines | Names |
|---|---|
| 3511 | `_process_pack_material` |
| 3680 | `_process_pack_item` |

### → `box.py` (existing module, extended)

| Lines | Names |
|---|---|
| 3563 | `_process_box_material` |
| 3736 | `_process_box_item` |

### → `expansion.py` (existing module, extended)

| Lines | Names |
|---|---|
| 3432 | `_find_pack_dirs` |

### → nowhere (dead code)

| Lines | Names |
|---|---|
| 3492 | `_solve_linear` — no call sites anywhere; remove in a follow-up (§8) |

### → `generate.py`

| Lines | Names |
|---|---|
| 454–457 | `DEFAULT_PRESET`, `DRAFT_PRESET`, `DEFAULT_SCALE`, `DRAFT_SCALE` |
| 508 | `generate` → `run` (entrypoint rename) |
| 3792 | `_default_jobs` |
| 3797 | `_stage_threads` |
| 3813 | `_run_notes` |
| 3831 | `_parse_args` |
| 3900 | `_timings_suffix` |
| 3912 | `_generate_profiles` |
| 4042 | `_generate_standards` |
| 4165 | `_generate_variants` |

### → `metadata.py` (existing module, extended)

| Lines | Names |
|---|---|
| 549 | `_set_cards` |
| 633 | `_write_metadata` |

### → `bundle.py` (new module)

| Lines | Names |
|---|---|
| 142 | `MOD_NAME` |
| 674 | `bundle` → `run` (entrypoint rename) |

### → `__init__.py` (kept)

| Lines | Names |
|---|---|
| 1–103 | module docstring (becomes the package docstring) |

## Appendix B: sibling import updates

What `import nikke_reborn as nr` + `nr.X` becomes:

| Module | Replacements |
|---|---|
| `box.py` | `nr.GenerationError` → `error`; `nr.BOX_TEMPLATE`, `nr.IMAGES_DIR` → `config`; `nr._box_side_mask`, `nr._box_top_mask`, `nr._pack_mask`, `nr._pack_mask_rects` → `image` |
| `pack.py` | `nr.GenerationError` → `error`; `nr.PACK_TEMPLATE`, `nr.IMAGES_DIR` → `config`; `nr._pack_mask`, `nr._pack_mask_rects` → `image` |
| `expansion.py` | `nr.GenerationError` → `error`; `nr.VIEWER` → `config`; `nr._load_card`, `nr._source_hash` → `card`; `nr._PipeDrain`, `nr._read_exact`, `nr._reap_viewer` → `video` |
| `simulation.py` | `nr.GenerationError` → `error`; `nr.CARDS_DIR`, `nr.OUTPUT_DIR`, `nr.REPO_ROOT` → `config`; `nr._set_cards` → `metadata` |
| `spritesheet.py` | `nr.GenerationError` → `error`; `nr._save_atomic` → `file`; `nr._set_weight`, `nr._text_ink_offsets`, `nr.COPYRIGHT_*` → `lettering`; `nr.CARD_REFERENCE_WIDTH`, `nr.CARDS_DIR`, `nr.DRAFT_DIR`, `nr.FONT`, `nr.IMAGES_DIR`, `nr.MAX_STAGE_THREADS`, `nr.OUTPUT_DIR`, `nr.PROFILE_RARITIES`, `nr.PROFILE_STEMS`, `nr.REPO_ROOT`, `nr.SOURCE_HASH_KEY`, `nr.STANDARD_STEMS` → `config` |

In addition, `spritesheet()` and `simulate()` are renamed to `run()`
(§6.4). And `pyproject.toml` becomes:

```toml
generate    = "nikke_reborn.generate:run"
bundle      = "nikke_reborn.bundle:run"
spritesheet = "nikke_reborn.spritesheet:run"
simulate    = "nikke_reborn.simulation:run"
```
