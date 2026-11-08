# ENGINE

The compositing engine renders a card (or a material — box, pack) by
executing a **Lua design script** against a fixed table of **ops**.
This document specifies the engine's design — the op API, the
execution model, the color-space and units conventions, and the fidelity invariant
(a bounded delta, not byte-exactness) — in a **language-agnostic**
way. The first-class engine will be implemented in a language other
than the current reference pipeline; the op API is the portability
boundary, and the same script must run unchanged on any conforming
engine.

A concrete design is `design/card/standard.lua`.

## The split

- **The script** (`design/<tier>/<presentation>.lua`) is the *design*:
  what is drawn, where, in what order, with what style. One script per
  presentation, **shared** by every card of that presentation. The
  per-card data (character id, title, subtitle, animation, time) is
  passed as **parameters** to the script's entry function. The script
  is **resolution-independent** — it positions everything relative to
  `width()`/`height()` (the logical canvas — see *Units*), so one
  script serves every run scale.
- **The engine** is a *generic interpreter*: it loads the script,
  binds the parameters, executes it, and encodes the yielded frames.
  It knows the op semantics and **nothing** about the content — no
  character data, no layout knowledge.
- **The op API** is the *contract*: each op's signature and exact
  semantics. A conforming engine implements the same API; the script
  is the portable artifact.

The design owns the *what*; the engine owns the *how*. A layout change
is a script edit; an op-behavior change is an engine edit.

## The op API

### Constructors

| op | signature | meaning |
|---|---|---|
| `image` | `image(path) → Image` | Load a bitmap (path resolved against the script's base). sRGB, with alpha. |
| `font` | `font(path) → Font` | Load a font (path resolved against the script's base); used by `text`. |
| `spawn` | `spawn(program, args) → Stream` | Run an external frame producer (`args`: an array of strings/numbers, numbers rendered for the command line). Returns a **lazy** stream of `Image` frames. |
| `rectangle` | `rectangle({x, y, size}) → Rectangle` | A rect; `x`/`y` top-left (px), `size` a scalar (w=h) or `{w, h}`. |
| `text` | `text(str, {font, size, weight, x, y, color}) → Text` | Lay out a string. `size`: px. `weight`: font weight. `x`/`y`: position. `color`: hex. Returns pixels + bounds. |

### Canvas queries

`width()`, `height()` — the canvas dims in logical px (the reference
image; see *Units*). `physical_width()`, `physical_height()` — the same
dims in physical px (the run scale): the only physical-px interface —
a frame producer renders in physical px and takes them as its viewport.
The top edge is `0`, the right edge `width()`, the bottom edge
`height()`. Origin top-left; +x right, +y down.

### Image methods

| op | signature | meaning |
|---|---|---|
| `contrast` | `img:contrast({auto=true}) → Image` | Histogram-stretch to full range, **tone-preserving** (no highlight/shadow clip). New buffer. |
| `resize` | `img:resize({width, height, mode}) → Image` | Scale to the target (logical px): exactly one of `width`/`height` — aspect preserved; both — the target box, `mode = "cover"` covers it and center-crops, no `mode` scales to it exactly. New buffer. |
| `blend` | `img:blend(other, {at, color_space}) → Image` | Alpha-composite `other` over `img`, `other`'s top-left at `at` (a `Rectangle`, default `(0, 0)`), clipped to the canvas. `color_space`: `"linear"` (default) / `"srgb"`. New buffer. |
| `fill` | `img:fill(region, color) → Image` | Paint `region` (a `Rectangle` or `Text`) with `color` (hex). The space is chosen by the region's kind: a `Text` region composites in sRGB, a `Rectangle` region in linear. New buffer. |
| `luma_at` | `img:luma_at(region) → number` | Mean luma of `region` (a `Rectangle`), 0–255 (see *Luma*). |
| `width` | `img:width() → number` | The image's width (px). |
| `height` | `img:height() → number` | The image's height (px). |
| `size` | `img:size() → {w, h}` | The image's pixel dims as a `{w, h}` pair — a convenience for `rectangle`'s `size`. |

### Text / Rectangle methods

| op | signature | meaning |
|---|---|---|
| `bounds` | `text:bounds() → Rectangle` | The tight ink box at the laid-out position. |
| `padded` | `rectangle:padded(n) → Rectangle` | The rect grown by `n` px on all sides. |

### Output

| op | signature | meaning |
|---|---|---|
| `yield` | `yield(frame)` | Emit one frame. The frame sequence becomes the output (one frame → a PNG; many → an MP4). |

## Execution model

- **Immutable buffers.** Every op returns a new buffer; the receiver
  is never mutated (`img:blend(x)` leaves `img` intact).
- **No hidden canvas.** The running composite is a value the script
  threads explicitly (`base` → `output`). There is no global state.
- **Streaming.** `spawn` is lazy. The `for frame in stream` loop is
  the sole driver: the engine produces exactly one frame per
  iteration, on demand. Nothing else advances the stream.
- **Prefix / suffix split.** Ops before `spawn` (the `base`) run
  **once**; ops inside the loop run **per frame**, each starting from
  `base` (a fresh prefix), never accumulated across frames. `yield`
  emits the frame at the loop's end.

## Color space

- **`blend` defaults to linear light; `fill` chooses by the region's
  kind** — a `Text` region composites in sRGB (text is sRGB, always), a
  `Rectangle` region in linear. For proper color handling, artwork composites
  in linear light by default. Implementors should likely keep
  pre-multiplied RGBA buffers in linear light for easy, correct
  compositing.
- **`text` is sRGB, always.** Type is authored in sRGB; no opt-out.
- **Opt-in sRGB.** `color_space = "srgb"` switches a `blend` to sRGB
  compositing — the logos (the NIKKE mark, the manufacturer mark) are
  sRGB over the linear artwork.

### The linear transfer function

Linear light uses the **IEC 61966-2-1 sRGB curve** on the 0–1 scale
(evaluated directly — no lookup tables):

- Decode (sRGB `x` → linear `L`): `x/12.92` if `x ≤ 0.04045`, else
  `((x + 0.055)/1.055)^2.4`.
- Encode (linear `L` → sRGB `x`): `12.92·L` if `L ≤ 0.0031308`, else
  `1.055·L^(1/2.4) − 0.055`.

Stored pixels are 8-bit: encoding rounds to the nearest 1/255 step,
ties away from zero (Rust's `round` — the first implementation's
native rounding; the reference's half-to-even is not carried) — the
one rounding a color value undergoes. The
8-bit decode/encode round-trip is exact: where a layer's alpha is 0 or
255 the linear result is byte-identical to an sRGB composite; the
difference is confined to partially transparent pixels.

### Luma

`luma_at` returns the **mean**, over the region, of the Rec. 709
luma `0.2126·R + 0.7152·G + 0.0722·B` per pixel (0–255). The
reference's face-pick threshold is **200**: a stamp is drawn dark when
the region's mean luma exceeds 200, light otherwise. (The threshold is
a *script* decision — the engine only supplies the mean luma — but the
value is fixed by the reference.)

## Units

- **Logical px.** Every value in the script — positions, sizes, font
  sizes, `rectangle` and `resize` targets, `padded` amounts — is in
  logical px: the scale of the reference image, the native canvas
  `width()`/`height()` report. The engine receives the run's scale and
  performs the logical → physical transform internally (the physical
  canvas is the logical canvas at that scale, each dim rounded to the
  px); the script never scales. One script renders at every run scale.
- **Physical px.** A frame producer renders in physical px, so
  `physical_width()`/`physical_height()` give the run-scale canvas for
  the `spawn`'s viewport arguments. They are the only physical-px
  interface; every other op takes and reports logical px.
- **Fractions.** A position may be a fraction of a dim
  (`height() * 0.72`).

## Fidelity (the invariant)

The engine is a re-implementation in a different language, on a
different image stack. We do **not** replicate the reference library's
implementation detail — its resampling filter, its font rasterization,
its encoders — because that would mean carrying the reference's cruft.
So the invariant is **not** byte-for-byte identity; it is a **bounded
delta**: for the same inputs and run scale, the engine's output must be
**within a maximum delta** of the reference's output.

The reference (the current pipeline's output) is **unchanged** — it is
still the ground truth. Only the *match criterion* relaxes, from an
exact file hash to a bounded difference on decoded pixels.

### Pinned vs. free

The delta budget is spent on the *free* ops; the *pinned* ops are
near-exact by construction and consume almost none of it.

- **Pinned (standard, library-independent)** — must land within
  rounding, so they must not be the thing eating the budget: the IEC
  61966-2-1 sRGB transfer function, the Porter-Duff `over` compositing,
  the Rec. 709 luma weights, and the autocontrast *intent* (full-range,
  tone-preserving stretch). These are mathematical; a conforming engine
  gets them right up to integer rounding.
- **Free (library-specific, allowed to drift within the delta)** —
  where the budget actually lives: the resampling/resize (background
  fit, any scaling), the font rasterization (hinting/antialiasing), and
  the encoders (PNG, MP4). A conforming engine may use any
  implementation here, provided the *result* stays within the delta.

### The metric

The delta is the **maximum per-pixel, per-channel absolute difference**
in sRGB (0–255), computed on **decoded pixels** — never on file bytes,
since the encoders are *free* ops and their bytes are not comparable.
It is reported **globally** (over the whole frame) and **per element**
(per op's / element's bounding box, for localization). A wrong element
(a wrong logo face, a mispositioned stamp) shows up as a large
per-element delta; a legitimate library difference (a text or silhouette
edge) shows up as a small, isolated one.

### The threshold

A named design constant, `MAX_DELTA`, per output kind. It is set
**just above the measured noise floor** (the delta distribution of the
free ops) with margin — **measured, not guessed**: once the engine
exists, render the same cards under both it and the reference, read off
the per-element delta distribution (max, p99.9, mean), and set
`MAX_DELTA` above the legitimate edge-outlier max. Per output kind:

- **Lossless still (PNG):** the clean per-op signal (no codec error),
  so a tighter bound.
- **Lossy video (MP4):** an end-to-end signal (op drift + codec
  error); the codec dominates, so per-op attribution is weak and the
  bound is looser. Prefer the lossless still for per-op checks.

The value is **TBD** until the engine exists and the distribution is
measured; until then `MAX_DELTA` is a named placeholder, not a target.

### The protocol

`test <set> <id>` re-renders under the engine, **decodes** both the
reference and the new output to raw pixels, and checks the delta
against `MAX_DELTA`. **Green** = within the threshold; **red** = a
delta exceeded it, and the report names the element/op that drifted.
The baselines change from **file hashes** to **reference artifacts**
(the actual PNG/MP4 files), because a delta needs the reference's
pixels, not their hash. `--new-baseline` re-records the reference
artifacts.
