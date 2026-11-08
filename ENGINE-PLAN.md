# ENGINE — build plan (v1)

The engine design is `ENGINE.md` (the spec: op API, execution model,
color space, units, fidelity). This is the build plan for the first
conforming engine: a Rust binary that runs the standard-tier design
(`design/card/standard.lua`) end to end. It records the settled
decisions, the contract deltas still owed to the spec, the v1 harness
and architecture, and the phase breakdown with its verification gates.

## 1. Scope

**Goal.** A Rust engine, `pikke`, that loads a design script,
binds its parameters, executes it against the op table, and encodes the
yielded frames: one frame → `output.png`, many → `output.mp4`, within
the fidelity invariant (bounded delta against the reference, decoded
pixels).

**Non-goals for v1** (explicit):

- the profile and full-art tiers (their designs need op extensions the
  current API lacks: lockstep/dual-stream pulls, monochrome, tint wash);
- the pack/box materials;
- `size = "auto"` (dropped from the API; sizing is a Lua-side
  computation);
- producer retry (a failed `spawn` is an error; the GPU is shared and a
  transient failure is re-run by hand);
- embedding the source hash in outputs (the reference's skip check is
  untouched — the reference pipeline and its byte protocol are
  unchanged);
- the `test` command's delta protocol (artifact baselines,
  `MAX_DELTA` enforcement, per-element red reports) and the standing
  measurement tooling (the per-element delta checker, the engine's
  `--report` sidecar) — deferred; v1's Phase 10 comparison is manual,
  at that time;
- the presets (draft/ultra/low) — the run is a `--scale` against the
  logical canvas;
- automatic TOML-driven runs — v1 is invoked per card from the command
  line; a driver reusing `cards/*.toml` and the database resolution is
  v2.

## 2. Settled decisions

From the design review (2026-11-08):

- **Language: Rust** (one language for the whole binary stack, with
  `nikke-viewer`/`unity-viewer`).
- **Scope: the standard tier only** for v1. All four standard-tier
  presentations (Standard, Rare, Cover, Aim) are stills (`time` given),
  so v1's real outputs are PNGs; the MP4 path exists and is verified
  with a synthetic producer.
- **Units: the script is in logical px** — the scale of the reference
  image, the native canvas `width()`/`height()` report. The engine
  receives the run's scale and performs the logical → physical
  transform internally; the script never scales.
  `physical_width()`/`physical_height()` are the only physical-px
  interface: a frame producer renders in physical px and takes them as
  its viewport.
- **`spawn` protocol:** the script passes the producer's protocol flag
  (`--stdout`); frames are raw RGBA8 on the producer's stdout, canvas-
  sized. No retry.
- **Internal buffer: premultiplied** RGBA, f32 linear (0–1) — the op
  boundary stays straight RGBA8 sRGB (§3b). The linear composite is
  `layer + base·(1 − layer.a)`: no division, and a 0 or 1 alpha on either
  side exact. Premultiplication discards a fully transparent pixel's
  color — the stored-channel ops (`luma_at`, the contrast histogram)
  read it as colorless — exact on the standard tier (the regions are
  opaque), a representation limit otherwise.
- **`text` anchor:** the tight ink box's top-left lands at `(x, y)`.
- **No `size = "auto"`** — numeric px only.
- **`fill`'s space is automatic:** a `Text` region composites in sRGB,
  a `Rectangle` region in linear — no parameter (the best strategy per
  region kind). `blend` keeps its explicit `color_space` (default
  linear).
- **Outputs hardcoded:** `output.png` / `output.mp4` in the working
  directory (the reference artifacts live under `output/<set>/`; no
  collision).
- **ffmpeg flags hardcoded**, mirroring the reference's default run.
- The draft script's simplifications (the 127 face-pick threshold, the
  missing subtitle/corner-cut/arrow/manufacturer pieces, the stamp
  geometry) stand for now — it is an example, and the Phase 10
  comparison (manual, at that time) is what distinguishes its
  legitimate differences from engine bugs.

## 3. Contract deltas

**(a) Folded into ENGINE.md.** The op-level decisions the script's
evolution settled: `resize` (the target semantics), `blend`'s `at`,
the physical canvas queries, the logical/physical units model (the
engine takes the run's scale and transforms internally; the script is
logical px throughout), `fill`'s automatic space, and the `auto`-size
removal.

**(b) Open spec deltas** (op-level details ENGINE.md does not yet pin
down). The spec is expected to evolve as the engine is implemented —
**deviations from these are allowed**: they are noted in the phase
record where they occur and folded back into ENGINE.md later:

- **`spawn`'s protocol:** args are strings/numbers (numbers rendered in
  decimal; a `nil` arg is an engine error). Frames: raw RGBA8, the
  canvas's physical dims, straight alpha, sRGB; the iterator yields one
  frame per step; a truncated stream (a partial frame) or a non-zero
  exit is an error carrying the producer's drained stderr tail. The
  producer's own protocol flag is the script's business.
- **`text`'s anchor and value:** the tight ink box's top-left is at
  `(x, y)` (the engine measures the rasterized ink's offsets and
  compensates, as the reference does). A `Text` value carries its
  ink-cropped pixels plus the laid-out ink position; `bounds()` is that
  ink box as a `Rectangle`. `weight` sets the variable font's `wght` axis; a
  static font ignores it.
- **`luma_at`:** the mean over the region (clipped to the canvas) of
  the Rec. 709 luma of the region's **stored sRGB** RGB channels (alpha
  ignored), 0–255. (The reference samples with ITU-R 601 weights; the
  spec wins — near the face-pick threshold a face can legitimately
  differ, and the threshold is a script decision anyway.)
- **Geometry rounding:** positions, sizes and resize targets are real
  px; every geometric result — and the logical → physical transform
  itself — rounds to integer px, ties away from zero (Rust's
  `round` — the first implementation's native rounding; the
  reference's half-to-even is not carried).
- **`yield`'s invariant:** a frame is canvas-sized — every op
  preserves the receiver's dims (`resize` is the only dim-changing op),
  so the engine asserts canvas dims on `yield` and on `blend`'s
  receiver.
- **Buffer representation:** at the op boundary a buffer is straight-
  alpha RGBA8 sRGB; internally the buffer is f32 linear (0–1),
  premultiplied (§2), and
  the sRGB ↔ linear transfer is evaluated directly at the boundaries
  (load, yield) and in the small sRGB-composite and `luma_at` regions
  — no LUTs (deviation from the reference's 0–65535 LUTs). Rounding
  happens exactly once, at the linear → 8-bit encode (nearest 1/255
  step, ties away from zero — Rust's `round`; out-of-range linear
  values clamp).
- **Parameters and entry:** the script's globals expose the op table
  and an `arguments` table declaring the entry's parameters (in CLI
  order) — a table read, so the engine needs no `debug` library. The
  engine loads the script (paths — `image`/`font`/`require` — resolve
  against the script's directory), creates a `--<name>` CLI flag for
  each declared parameter (the CLI, §5), and calls `render(args)`
  with a single table of the bound values. v1: a flag's value is a
  string; an omitted or empty flag binds `nil` (optionality is the
  script's — it guards the optional ones); the script converts where
  it needs a number.

## 4. The script's state

- **Fixed this round:** the spawn args' `[...]` → `{...}` (Lua arrays
  are brace-delimited); the `resize` calls' `.` → `:` (the spec's
  method call syntax); the optional `--animation`/`--time` args are
  appended only when the parameter is present — `nil`, bound from the
  omitted or empty flag of that name ("the presentation names no
  value") — so an absent term omits the flag; a `nil` that ever
  reaches `spawn` is the backstop error (§3b).
- **Fixed by the script's evolution:** `height = height()` in the mask's
  `resize`; the producer's viewport via `physical_width()`/
  `physical_height()`.
- **Subsumed, no change needed:** the logos' `resize({width=200})` —
  200 is now a logical constant, correct at every scale; the
  copyright's `fill` — sRGB by the region's kind.

## 5. The v1 harness

- **CLI:**
  `pikke <script> --width <W> --height <H> [--scale <s>]
  [--<param> <value>]...` — the script is the first argument (its
  parameter flags only exist once it is loaded); one named flag per
  entry-function parameter, created on the fly from the introspected
  names (§3b; for the Standard draft: `--id --title --subtitle
  --animation --time`).
  `--width`/`--height` are the **logical** canvas (the reference
  image's dims) — required: the engine is generic and holds no
  content defaults (not even the card's native viewport); `--scale`
  the run's scale, defaulting to 1 (the default run is the canvas at
  native scale). The physical canvas is `W×s`/`H×s`, each dim rounded
  (Rust's `round`); the MP4 path needs even physical dims (the
  driver's choice; 1640×2048 at 0.5/1.0/2.0 are all even). A flag's
  value is a string; an omitted or empty flag binds `nil`. Errors go to stderr
  with a non-zero exit.
- **Run size:** the default run is without `--scale` (i.e. 1); the
  reference artifact comparison (Phase 10) runs `--width 1640
  --height 2048 --scale 0.5` (physical 820×1024). The engine supplies
  `width()`/`height()` = the logical canvas and
  `physical_width()`/`physical_height()` = the derived physical.
- **Outputs:** `output.png` / `output.mp4` in the working directory.
  The engine does not know the kind in advance: frame 1 is held, and
  frame 2's arrival starts the MP4 path (flushing frame 1 into the
  encoder). One yielded frame → the PNG.
- **PNG:** RGBA — the buffer's alpha as-is, no need to drop it (the
  base is opaque, so 255 throughout); the reference's artifacts are
  RGB, so comparisons against them look at the RGB channels. Written
  atomically.
- **MP4:** the frame stream piped to ffmpeg, hardcoded to the
  reference's default run:
  `-f rawvideo -pix_fmt rgba -s <W>x<H> -framerate 60 -i - -c:v libx264
  -preset slow -crf 16 -pix_fmt yuv420p -movflags +faststart -f mp4
  output.mp4`
  (the reference's variable `-threads` is omitted in v1; it joins when
  the MP4 delta is measured).

## 6. Architecture

A standalone crate, `pikke/` (sibling of `unity-viewer/`), one
binary. Each module is built around the single type it carries (the
type's Lua bindings included) — a noun, no underscores, no
`ops`/`utils` catch-alls. Hygiene mirrors the Python side: `cargo fmt
--check` and `cargo clippy` clean.

```
pikke/
  Cargo.toml
  src/
    main.rs      the binary's entry: the CLI (the named flags created
                 from the introspected entry parameters, §3b) and the
                 dispatch into the Engine
    engine.rs    the `Engine`: the Lua VM (mlua) and the script's
                 environment — the op table (each global bound to its
                 type's userdata methods; the binding lives with the
                 type), the canvas queries (`width`/`height` logical,
                 `physical_width`/`physical_height` the derived
                 physical) —, the entry's parameter introspection
                 (§3b), the execution, and the logical → physical
                 transform at the op boundary (× the scale, Rust's
                 `round`)
    image.rs     the `Image`: the RGBA buffer — buffers are physical
                 px (the run scale); the API reports logical. Its ops:
                 load (PNG, straight-alpha), resize / contrast / blend
                 / fill / luma_at / width / height / size. Resampling
                 between scales is a free op (Lanczos): a layer is
                 resampled to the run scale at the first op that needs
                 it there (a `resize`, or the composite when the layer
                 is still at its file scale), so the reference's
                 single-resize paths are reproduced (no double
                 resampling)
    color.rs     the `Color` and the pinned transfer math: the IEC
                 61966-2-1 sRGB ↔ linear conversion (evaluated
                 directly — no LUTs), the single encode rounding
                 (nearest 1/255, ties away from zero — Rust's
                 `round`), Porter-Duff over
                 in linear and sRGB, the Rec. 709 luma, the
                 tone-preserving full-range stretch
    font.rs      the `Font`: the file loaded via cosmic-text's
                 `FontSet` (from the file's bytes; the path relative
                 to the script), the `wght` weight axis (a swash
                 variation, set when the file carries it)
    text.rs      the `Text`: the layout (the ink-offset probe, the
                 anchor), the ink-cropped pixels, `bounds`
    rectangle.rs the `Rectangle` and `padded`
    stream.rs    the `Stream`: the `spawn`'d producer protocol — the
                 stdout frame reader, the stderr drain thread (bounded
                 tail, 1 MiB, for error reports), the lazy iterator,
                 the failure semantics
    encoder.rs   the `Encoder`: the PNG writer (RGBA, atomic) and the
                 ffmpeg MP4 pipe
```

Dependencies: `mlua` with the vendored Lua 5.4 (no system Lua),
`image` (PNG codec + the Lanczos resize filter), `cosmic-text` for the
text (swash shaping/rasterization + fontdb file loading — pure Rust;
the same stack `unity-viewer`'s lock pins).
No argument-parsing crate: the CLI is hand-rolled, in the style of
`nikke-viewer` — one `while let` pass over `std::env::args()` with a
`match` per argument: boolean flags, `--flag value` arms (the value is
the next argument), unknown options and extra positionals are errors,
`--help` prints after the pass; the script is the first argument
(loaded before the pass, for the dynamic flags); the dynamic
parameter flags enter the match as a membership test against the
introspected names.

Frame flow: the script threads `base` → `output` explicitly (no hidden
canvas); the engine only interprets. Compositing is single-threaded in
v1 (no thread-count-dependent behavior; the byte-stability concerns are
v2's). Memory: the standard tier's stills keep one frame; the animation
case is bounded by the viewer's loop, and the MP4 path streams frames
to the encoder as they are yielded.

## 7. Phases

Each phase is a small, self-contained step with its gate — the
verification that closes it.

**Phase 0 — the open spec deltas.** The script is fixed (§4);
ENGINE.md carries the settled op semantics (§3a). §3b (the spawn
protocol, the text anchor and value, the luma note, the rounding, the
yield invariant, the buffer boundary, the parameters and entry) stays
open for now: the spec evolves with the implementation, and
deviations from it are allowed — noted where they occur, folded back
into ENGINE.md later.
*Gate:* ENGINE.md and the script agree on every op the script uses;
`luac5.4 -p` clean.

**Phase 1 — the CLI, the VM, and the flags.** The `pikke` crate
(mlua); the script loads into a dedicated environment; the entry's
parameters are read from the script's `arguments` declaration (§3b)
and the hand-rolled CLI is built from them (the `nikke-viewer`
style — the dependencies, §6). The script is the first argument, so
the flags exist before the pass (and the help text) happens; flag
values bind to the parameters as strings (an omitted or empty flag
binds `nil`).
*Gate:* `pikke design/card/standard.lua --help` prints the
`--id --title --subtitle --animation --time` flags alongside
`--width`/`--height`/`--scale`; `pikke design/card/standard.lua
--width 1640 --height 2048 --id c010` binds the values and fails
cleanly at the entry's first op (the op table does not exist yet —
expected here).

**Phase 2 — the API surface, mocked.** Scaffold the crate's final
structure (§6) and draft the entire Lua API with empty mocks: every op
returns a placeholder; the mock `spawn` returns a lazy stream that
yields one canvas-sized frame; `yield` records the frame (asserting
the canvas dims, §3b) and writes no file, encodes nothing.
*Gate:* `pikke design/card/standard.lua --width 1640 --height 2048
--id c010 --title Rapi --time 0` invokes the script end to end —
every op is called, and `yield` was called with the right output (the
mock's one canvas-sized frame) — producing no image.

**Phase 3 — the pinned color math.** `color.rs`: the IEC 61966-2-1
sRGB ↔ linear conversion (evaluated directly, 0–1 — no LUTs),
Porter-Duff over (linear and sRGB), the single encode rounding
(nearest 1/255 step, ties away from zero — Rust's `round`), the Rec.
709 luma, the
tone-preserving full-range stretch.
*Gate:* test vectors from the reference pipeline
(`nikke_reborn.linear`, `nikke_reborn.image`) — the encode matching
the reference's at its 65536 sample points (±1 at rounding
boundaries — our tie-break and the last-ulp evaluation noise differ);
the decode/encode round-trip exact for all 256 stored values;
over within ±1 of the reference on random RGBA pairs, exact on the
round-trip cases (alpha 0/255) — pinned math is right up to integer
rounding; the luma matching the 709 mean.

**Phase 4 — the real Image buffer.** `image.rs` replaces its mock: the
straight-alpha RGBA8 buffer, `image(path)` load (PNG decode),
`width`/`height`/`size`, and the logical → physical transform at the
op boundary (× the scale, Rust's `round`).
*Gate:* a real asset (a Base background) loads at its file dims; at
`--scale 0.5` the canvas is 820×1024 and the op-boundary transform is
exact against the reference's scaled values (the logo 200 → 100, the
copyright 20 → 10, the title 150 → 75).

**Phase 5 — `resize` and `contrast`.** The real resize (the three
target semantics; Lanczos — a free op) and the real contrast (auto,
the tone-preserving stretch). Both run in linear — the reference does
both on stored sRGB (free-op drift, small).
*Gate:* on the three Base backgrounds, headless: `resize` (all three
modes) within a few units of the reference's
`_fit_background`/mask-stretch; `contrast` within a few units of the
reference's `autocontrast(preserve_tone)` (free ops).

**Phase 6 — compositing: `blend`, `fill`, `luma_at`, the
Rectangle.** The real blend (over, `color_space`, `at` + the canvas
clip), fill (the space by the region's kind), luma_at (the region
mean), and `rectangle.rs` (the Rectangle + `padded`).
*Gate:* `blend` and `fill` byte-identical to the reference on real
pairs (pinned math: exact at 8-bit); `luma_at` matching the reference
mean on the three Base backgrounds.

**Phase 7 — text.** `font.rs` + `text.rs` on `cosmic-text` (the face
via `FontSet` from the file's bytes — the path relative to the
script —, swash shaping + rasterization at the run scale): the `wght`
axis (a swash variation, set when the file carries it — Oswald is
variable, AireExterior static), the layout, the ink-offset probe (the
union of the glyphs' ink), the anchor (the tight ink box's top-left
at `(x, y)`), `bounds`. Shaping hint `Basic` — plain advances,
matching the reference's non-GPOS layout (swash kerns by default).
*Gate:* the script's two texts (Oswald 300 at the copyright size,
AireExterior 700 at the title size): the ink box's top-left exactly
`(x, y)` (pinned), the ink box's size within ~1 px of the reference's
`_text_ink_offsets` probe, the rasterized copyright line a small
per-pixel delta against the reference's stamp (free).

**Phase 8 — the real Stream.** `spawn`'s producer protocol: the stdout
frame reader (raw RGBA8, the canvas's physical dims), the stderr drain
(the bounded 1 MiB tail), the lazy iterator (one frame per step), the
failure semantics (a truncated stream or a non-zero exit → an error
carrying the stderr tail).
*Gate (no GPU):* a synthetic producer (a small script writing N raw
RGBA8 frames to stdout) — N frames yielded byte-for-byte; a truncated
stream and a non-zero exit each surface as an error carrying the
stderr tail. With the GPU: one real still (`nikke-viewer --stdout …
--time 0 c010` through a minimal `background:blend(frame)` script, the
viewport from `physical_width()`/`physical_height()`) — the yielded
frame equals the raw stream's frame byte-for-byte (no free op between
them).

**Phase 9 — the encoder.** `encoder.rs`: the PNG writer (RGBA, atomic)
and the ffmpeg MP4 pipe (the reference's default flags, §5); the
PNG/MP4 decision at frame 2 (§5) replaces the Phase 2 yield recorder.
*Gate:* one frame → `output.png` decoding back to the frame
byte-for-byte (lossless); N frames → `output.mp4` with N frames
(ffprobe).

**Phase 10 — the standard card, end to end.** Run
`design/card/standard.lua` for c010:
`pikke design/card/standard.lua --width 1640 --height 2048
--scale 0.5 --id c010 --title Rapi --time 0` (`--subtitle` and
`--animation` omitted, so they bind `nil` and the script omits the
`--animation` flag — the Standard presentation's is the viewer's
default) and compare `output.png` against the reference artifact
`output/Base/0001_c010_Rapi_01_Standard.png` — manually at that time
(the standing measurement tooling is deferred, below).
*Gate:* the background and character regions (everything the engine
owns: the fit, the contrast, the mask, the frame composite) sit at the
free-op noise floor — a few units, no structure, judged by eye and an
ad-hoc diff at that time. The stamp elements show the *expected*
script-level differences, recorded as the known-differences list (all
logical px):

- the logo at top-right, y 50, margin 50 — the reference's standard
  tier stamps it bottom-right at 1.5× the padding (75);
- the face-pick threshold 127 vs the reference's 200 (a face can
  legitimately flip);
- the title bar: a flat `padded(30)` rect vs the reference's
  0.2×ink-height bar with its corner cut, arrow, bar and squares;
- the copyright line's vertical position (the script's flat 50 vs the
  reference's scale-adjusted, ink-centered placement);
- the title glyphs, subtitle, and the manufacturer's logo absent (the
  script's TODOs).

(The title's 150 and the copyright's 20 now agree with the reference
exactly — logical px on both sides — so they are not differences.)

**After v1 (preview, not scheduled here):** the standing measurement
tooling (the per-element delta checker, the engine's `--report`
sidecar, the `MAX_DELTA` thresholds — the Phase 10 comparison becomes
a standing protocol), the `test` delta protocol (artifact baselines,
`--new-baseline`, per-element enforcement), the profile/full-art
designs and the op extensions they need, the presets, the TOML
driver, and the hash-embedding question for engine outputs.

## 8. Risks and notes

- **Free ops chosen for parity, not copied.** The Lanczos resize,
  swash rasterization and the reference's
  ffmpeg flags are chosen to sit the noise floor low — the invariant is
  the bounded delta, not byte identity, and none of these is replicated
  detail for its own sake.
- **No text supersampling for now:** the glyphs rasterize directly at
  the run scale. Swash is unhinted, so the small text (the copyright
  line, ~10 physical px at 0.5×) is the risk case — if its per-pixel
  delta against the reference's stamp exceeds the Phase 7 gate, the
  first fix is 4× supersampling with a Lanczos downscale.
- **The engine runs on mlua's safe standard-library subset:**
  parameter introspection is a table read of the script's `arguments`
  declaration (§3b), so no `debug` library is needed — and `package`
  (for `require`) is in the safe set. Isolation from the base
  libraries (`os`, `io`, `debug`) comes from the dedicated
  environment (a fresh globals table), not the subset.
- **The resample happens once.** A layer is resampled to the run scale
  at the first op that needs it there (the `resize`, or the composite
  when the layer is still at its file scale); the reference's
  single-resize paths are reproduced, so no path pays a double
  resampling.
- **luma weights:** the spec's Rec. 709 vs the reference's ITU-R 601
  (on stored sRGB values) can flip a face-pick near the threshold. The
  spec wins; the threshold is a script decision; a flip shows up as a
  localized per-element difference against the reference, visible in
  the Phase 10 comparison (and, later, the deferred checker).
- **`contrast` order:** the reference stretches before the fit; the
  script resizes (cover) then stretches. Free-op drift, small — the
  histogram's tail moves slightly with the crop.
- **The GPU is shared and there is no retry** (settled): a transient
  viewer failure (truncated stream, crash) fails the run and is re-run
  by hand.
- **No system-Lua dependency** (mlua's vendored 5.4); the text stack
  (`cosmic-text`/`swash`/`fontdb`) is pure Rust — no fontconfig, no
  libfreetype.
- **The standard tier is stills-only,** so the MP4 path is exercised
  synthetically in v1; its measured delta (codec-dominated, per
  ENGINE.md) waits for a real animated run in v2.

## 9. Next

The phase ladder is settled (§7); the next working step is Phase 1
(the CLI, the VM, and the flags).
