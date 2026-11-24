# POSTERS

Research notes and plan for the poster feature (roadmap item).
Source: the game's own asset files under `Card Shop Simulator_Data/`
(`sharedassets2`, `resources`, `globalgamemanagers`), which the seed
distillation and the bundler use directly. Every number below was
measured from the game, not assumed.

## 1. How the game adds posters

The game's posters are **decoration objects (decos)** driven by the
game's native deco system — the same structure this repo replicates.
We deliver the posters we render as **data for Enhanced Prefab Loader
(EPL)** — no code of our own. EPL scans
`BepInEx/plugins/**/*_prefabloader/` folders; each holds an EPL
manifest (`.json`) and a same-named, extensionless Unity AssetBundle:

```
BepInEx/plugins/<publisher>/nikke_reborn_<set>_prefabloader/
├── nikke_reborn_<set>          # Unity AssetBundle
└── nikke_reborn_<set>.json     # EPL manifest
```

### 1.1 The EPL manifest

Top level: `Name` (the set's display name), `BundleId` (the bundle's
unique id), `AutoCompressTextures: false`, `MaxTextureSize: 1024`
(`2048` if any ultra texture), and `TextureCompression`. `Items`,
`CardExpansions`, `CustomShops` and `Assemblies` are empty — the
bundle is posters only.

`Prefabs` has one entry per poster:

| Field | Value |
|---|---|
| `Name` | the poster's display name |
| `PrefabName` | the root object in the bundle |
| `SpriteName` | the UI icon sprite |
| `DecoObject` | the id the loader registers in the game's deco database |
| `DecoType` | `"Poster"` |
| `IsDecoObject` | `true` |
| `AddItemToFurnitureShop` | `false` |
| `Price` | the poster's price |
| `LevelRequirement` | the poster's level requirement |
| `VideoClips` | `[]` |

### 1.2 The AssetBundle

UnityFS, LZ4 compressed, one internal `CAB-…` file + a `.resS`
resource stream (mesh vertex data). The version string is the game's
own `6000.0.66f2` (the seed and the bundles this repo emits match it).

Per poster, the bundle holds the deco's 15 GameObjects / Transforms,
7 MeshRenderers / MeshFilters, 3 MonoBehaviours, 2 BoxColliders,
1 Animation (on `AnimGrp`, bound to the shared flip clip) and
1 icon Texture2D + Sprite. The shared constants are kept once per
bundle: the 3 quad meshes + guide strip, the 3 MonoScripts, the 2
shared materials, the `Posters` `Texture2DArray` and its shader, the
`display_texture` shader, the guide texture and the flip clip.

There are no top-level `Prefab` assets: the root GameObjects are stored
as scene objects, named exactly like the manifest's `PrefabName`
values.

### 1.3 The per-poster scene graph

15 GameObjects per poster, the game's poster deco structure with the
art swapped:

```
<name>_Prefab                       BoxCollider (trigger) + InteractableDecoration
├── AnimGrp                          Animation → the shared flip clip
│   ├── Poster / PosterHorizontal / PosterSquare
│   │                                MeshFilter + MeshRenderer → the shared PosterMaterial (array slice, §3.5)
│   └── PreviewMesh                  MeshFilter + MeshRenderer
└── MoveStateValidAreaGrp            ShelfMoveStateValidArea (scaled to the poster's slab, §2.5)
    └── MoveStateValidArea           MeshFilter (null mesh) + MeshRenderer + BoxCollider (1×1×1)
        ├── SnapLoc_L / SnapLoc_R / SnapLoc_Up / SnapLoc_Down
        └── DashedLineGrp            DashedLine
            ├── Line1 … Line4        MeshFilter (PosterGuideMesh) + MeshRenderer
```

The art node's name is per aspect (§2.2). Its `MeshRenderer` uses the
shared `PosterMaterial`, bound to the `Posters` `Texture2DArray` — the
slice is chosen by `m_SpecialIndex` (§3.5), so no per-poster material
or texture. The three MonoBehaviours are the game's own scripts from
`Assembly-CSharp.dll`:

- `InteractableDecoration` — on the root
- `ShelfMoveStateValidArea` — on `MoveStateValidAreaGrp`
- `DashedLine` — on `DashedLineGrp`

No custom code: the game's native deco system drives grab/drag/snap/flip
because the components are the game's own, pre-filled with vanilla poster
values.

### 1.4 The `InteractableDecoration` fields (serialized, identical per aspect)

| Field | Value |
|---|---|
| `m_DecoObjectType` | per-poster unique — 1..N in registration order |
| `m_ObjectType` | `-1` |
| `m_HighlightOutlineWidth` | `5.0` |
| `m_IsGenericObject` | `1` |
| `m_CanPickupMoveObject` | `1` |
| `m_CanBoxUpObject` | `1` |
| `m_CanScanByCounter` | `0` |
| `m_PlaceObjectInShopOnly` | `1` |
| `m_PlaceObjectInWarehouseOnly` | `0` |
| `m_AllowPlaceObjectNearShop` | `0` |
| `m_IsDecorationVertical` | `1` |
| `m_CanFlip` | `1` (hence the flip clip) |
| `m_CanCatStandOnThis` | `0` |
| `m_SoftPlaceObjectSFX` | `1` |
| `m_GameActionInputDisplayList` | `[14]` |
| `m_PickupObjectMesh` | PPtr → the `PreviewMesh` **MeshFilter** |
| `m_MoveStateValidArea` | PPtr → the `MoveStateValidArea` Transform |
| `m_ShelfMoveStateValidArea` | PPtr → the `ShelfMoveStateValidArea` MonoBehaviour |
| `m_BoxCollider` | PPtr → the root trigger |
| `m_SpecialMesh` | PPtr → the deco's own art **MeshRenderer** (a game-typetree field) |
| `m_SpecialIndex` | `m_DecoObjectType − 1` (a game-typetree field) — the **array slice** the poster samples; the game copies it into the shared `PosterMaterial`'s `_TexIndex` (§3.5) |
| everything else (`m_Mesh`, `m_SkinMesh`, lists, …) | null / empty |

Root layer: `12`. Root BoxCollider: `m_IsTrigger: true`,
size `(0.6, 0.47, 0.02)`, center `(0, 0.08, 0)` — **identical on all 72**
(sized to the largest poster; §2.5).

### 1.5 Script binding

In the binary bundle the MonoBehaviours reference **bundled MonoScript
objects by direct PPtr**; the MonoScript typetree carries
`m_ClassName` / `m_Namespace` / `m_AssemblyName` / `m_PropertiesHash`
and **no GUID** — GUIDs are only needed by the YAML (`.prefab`) format,
which is why that route was dropped (§3). The seed follows this
binding exactly, sourcing the MonoScript objects from the game's own
`globalgamemanagers.assets` (§3.4).

## 2. Aspect and sizing (measured)

### 2.1 Base geometry

Three shared thin-box quads (~0.8 mm thick; 24 vertices, 6 faces,
sequential indexing) plus a guide strip. Vertex data from the `.resS`
stream:

| Mesh | x range | y range | w | h | ratio |
|---|---|---|---|---|---|
| `…_PosterSquareMesh` | ±0.0737 | −0.0706 … +0.0734 | 0.1473 | 0.1441 | ≈ 1:1 |
| `…_PosterPortraitMesh` | ±0.0737 | ±0.0999 | 0.1473 | 0.1998 | ≈ 3:4 |
| `…_PosterLandscapeMesh` | ±0.0999 | ±0.0737 | 0.1998 | 0.1473 | ≈ 4:3 |
| `…_PosterGuideMesh` | — | 0 | 1.0000 | 0 | unit line strip (9 verts, 8 tris) |

The square's y range is slightly asymmetric (center offset +0.0014).

### 2.2 Aspect = bucketing to the nearest quad

The artwork's `w/h` is bucketed to the nearest quad — {1:1, 3:4, 4:3}
(square, portrait, landscape). The art node is named per aspect:
`Poster` (portrait mesh), `PosterHorizontal` (landscape mesh),
`PosterSquare` (square mesh).

The art is **cropped** to the bucket's aspect when packed into the
texture (≤ ~4% of one dimension), so display is essentially
undistorted. A per-poster valid-area slab override is the escape valve
for off-bucket outliers.

### 2.3 World size = one fixed uniform scale

Every `Poster`/`PreviewMesh` node carries
**localScale = (3.0683, 3.0683, 3.0683)**, regardless of
aspect (root and `AnimGrp` scale 1; position (0,0,0)). The preview's
z scale is 3.1 (a depth nudge). Final sizes:

| Aspect | w × h (game units) |
|---|---|
| square | ≈ 0.45 × 0.44 |
| portrait | ≈ 0.45 × 0.61 |
| landscape | ≈ 0.61 × 0.45 |

### 2.4 The texture pipeline

The art is **not** stretched anywhere (an earlier "pre-stretched
square" reading of this was wrong). The verified mechanism:

- **Art** (one slice of the `Posters` array, 1024² / 2048²): a small
  packed atlas — the front artwork sits in its **aspect-matched
  content box at its native aspect, undistorted**, with painted
  content in the back / edge rects and the rest opaque padding (near
  white, alpha 255 — which is why the texture corners read white).
- **The mesh UVs do the crop.** Vertex layout: pos (3 float) + tangent
  (4 half) + uv0 (2 half) = 24 B stride; uv0 is channel 4 of the
  14-slot channel table (@12 is the tangent — clean ±1.0 axis values).
  **Three UV sets, one per aspect mesh** (exact values measured via
  the `m_StreamData` offsets). The content box is where the packer
  paints the art; the front UV rect sits inside it
  (margin-bleed convention — the display crops a few px off the box;
  the total crop is ~1.2–4.1% of a dimension, worst case the square's
  vertical margin):

  | Mesh | Content box (1024²) | Front UV rect (px) | Orientation |
  |---|---|---|---|
  | Square | 700×716 @ (24, 156) | 690×687 @ (29, 169) | plain (u→w, v→h) |
  | Portrait | 700×970 @ (24, 35) | 690×958 @ (29, 42) | plain |
  | Landscape | 700×970 @ (24, 35), stored transversed | 690×958 @ (29, 42) | **swapped** (u→h, v→w) |

  (texture top-left pixel coords; the exact half-float UVs live in the
  meshes — we distill them verbatim, §4). The landscape reuses the
  portrait's rect with the axes swapped: its art is stored transversed
  (rotated 90° + mirrored) in the texture and un-transversed on
  display. No stretching anywhere. Back faces
  sample a ~206×221 px rect (square; ~206×307 portrait / landscape;
  u 748.5–954.0, v 158.4–379.5 / 113.4–420.0 in 1/1024 units), edge
  faces a ~125×9 px strip (u 762.7–887.7 × v 113.4–122.6); the guide
  mesh has its own trivial 0–1 UVs.
- **No material-side aspect params**: the shared `PosterMaterial`'s
  `m_SavedProperties` carry no per-aspect values (no `_MainTex_ST`), so
  the same material serves every aspect.
- **Icon** (512² + Sprite): the artwork uniformly scaled and
  letterboxed on transparent at its native aspect for the UI.
- **Material**: the shared `PosterMaterial`, bound to the `Posters`
  `Texture2DArray` (§3.5); the slice is chosen by `m_SpecialIndex`.
- Shared: the placement and guides materials, the guide texture
  (512²), and the `Posters` array.
- Animation: each poster's `Animation` component on `AnimGrp` is bound
  to the single shared flip clip (the placement flip, matching
  `m_CanFlip: 1`).

Texture inventory: one `Texture2D` per icon (512²), the `Posters` array
(the poster art, 1024² / 2048²), and the guide texture (512²).

Consequence: we replicate the game's deco layout exactly — the three
quad Mesh objects are distilled verbatim (UVs included), and the
final texture arrives already matching that layout (art in the
content boxes, back / edge rects painted); the bundler embeds it
as-is. UVs are normalized, so the same quads serve the 1024² and
2048² canvases (content boxes ×2 at 2048²).

### 2.5 Interaction geometry

- **Root trigger** (aspect-independent): BoxCollider
  `0.6 × 0.47 × 0.02`, center `(0, 0.08, 0)`, trigger — sized to the
  largest poster so any poster is easy to grab.
- **`MoveStateValidAreaGrp`** (the valid wall slab): local position
  `(0, 0, −0.0005)` plus a small hand-tuned y nudge per aspect (0.0
  portrait / 0.001 landscape / 0.004 square), **rotated 90° about X**,
  scale `(w, 0.0076, h)` **per poster to its own footprint**. The 90°
  rotation maps local z to world −y, so `scale.z` is the poster's
  vertical height and `scale.y` the 7.6 mm wall thickness. The slab is
  derived from the world sizes (measured ~1% under the footprint).
- **`MoveStateValidArea`** (layer 27): scale 1, local position
  `(0, 0.469, 0)`, unit BoxCollider (trigger), **no mesh** — the
  MeshFilter holds an external-file PPtr to the built-in cube mesh
  (fileID 1, pathID 10202) — an invisible placement volume.
- **`SnapLoc_L/R/Up/Down`**: four snap points under
  `MoveStateValidArea`, identity rotation/scale, fixed local positions
  on the back face of the unit box — L `(0, −0.469, +0.5)`,
  R `(0, −0.469, −0.5)`, Up `(+0.5, −0.469, 0)`,
  Down `(−0.5, −0.469, 0)`; the `m_SnapLocList` order is L, R, Up,
  Down.
- **`DashedLineGrp`**: local position `(0, 0.05, 0)`; the `DashedLine`
  script binds the four line renderers (H1 → `Line1`, H2 → `Line2`,
  V1 → `Line3`, V2 → `Line4`). Each `LineN` sits on the unit-width
  `PosterGuideMesh` at fixed local positions — `Line1/2` at
  `(0, 0, ±0.5)`, `Line3/4` at `(±0.5, 0, 0)` rotated 90° about Y —
  all with scale `(1, 1, 0.1)`. The slab's scale and rotation map them
  onto the poster's edges, so there are no per-poster line values.
- Renderers: `m_ReceiveShadows` 1 on the art / preview nodes, 0 on the
  placement volume and the guide lines. The icon sprite's
  pixels-per-unit is 100.

## 3. Design decisions

### 3.1 The question trail

1. Original ask: `poster.rs::generate(image, output)` → a `.asset` file.
2. `.prefab` (multi-document Unity YAML) is the natural container for the
   full scaffolding; a single-document `.asset` (the existing
   `assets/meshes/ItemCardSleeveMesh_low.asset` is one `!u!43` Mesh)
   cannot hold the 15-node graph.
3. Neutral interchange formats (glTF/USD/Collada) deliberately stop at
   3D content — colliders, script components, clip semantics are engine
   semantics; no standard carries a full game object.
4. Constraint settled: **`bundle` (the composition step) stays
   game-agnostic; the scaffolding must not be inferred downstream.**
5. Resolution: build the posters **directly into the bundle** — an
   `add_poster` method on the `Bundle` class in
   `src/nikke_reborn/bundler.py`. The scaffolding lives in code + seed
   fixtures; the per-poster input is the final texture + icon PNGs
   (plus the chosen aspect). No intermediate asset
   file at all.

### 3.2 Why `add_poster` in the bundler is the easier route

- **No YAML→bundle lowering.** UnityPy 1.25.4 has no YAML loader
  (verified: a test `.prefab` is read as a raw binary stream), and
  `unity-viewer`'s parser only handles single Mesh documents. The
  scaffolding as Python code reuses the bundler's existing
  clone-and-wire machinery (`add_mesh` is the precedent: clone
  prototype, set fields, wire PPtrs, return the graph for preload).
- **No MonoScript GUID problem.** That only exists in the YAML format;
  binary bundles bind scripts via bundled MonoScript objects + direct
  PPtrs, exactly as the game's own decos do.
- **One language, one library, one proven mechanism.** The Python
  bundler already loads `seed.bundle`, clones prototypes, embeds
  textures (BC7 via `Texture2DConverter`, with the `nkTx` lossless
  shortcut), and emits LZ4 AssetBundles.

### 3.3 Architecture

- `bundle` (command) — game-agnostic composition: copies set folders,
  builds bundles, lays out the BepInEx tree, zips.
- `bundler` (library) — the Unity construction layer: the only place
  with game-format knowledge. `add_poster` belongs here.
- Per-poster input: the final art texture (1024² / 2048²) and the final
  icon (512²) PNGs. The aspect is the poster name's final segment, and
  the icon ships as a plain Texture2D + Sprite in the cardpack bundle —
  not part of the poster graph. The poster's art is one slice of the
  shared `Posters` `Texture2DArray` behind one shared `PosterMaterial`
  (§3.5) — no per-poster material or texture is emitted. The EPL
  manifest JSON (per set, one `Prefabs` entry per poster) is emitted
  alongside the bundle (same layer).

### 3.4 Prototype gap

`seed.bundle` holds prototypes for: Transform, GameObject, Texture2D,
Sprite, Shader, MeshFilter, Material, Mesh, MeshRenderer (+ the
AssetBundle manifest). Posters need **five more types** — and the
game's own files contain all of them, with the vanilla field values
already set (the deco is the game's own poster implementation) — plus
the `Posters` `Texture2DArray` and the array shader the shared
`PosterMaterial` binds (§3.5):

| Needed | In the game files |
|---|---|
| BoxCollider | the deco's root trigger + placement volume |
| Animation | on `AnimGrp`, bound to the flip clip |
| AnimationClip | the shared flip clip (bound by every deco) |
| MonoBehaviour | 3 per deco, vanilla values |
| MonoScript | the three scripts, in `globalgamemanagers` |
| Texture2DArray | the game's `Posters` array — empty-templated in the seed, filled per bundle |
| Shader | the array shader + its fallback (§3.5) |

The constant content (shared materials, guide texture, flip clip) and
the three quad meshes are distilled verbatim — the Mesh objects carry
the exact geometry and UVs (including the transversed landscape set),
so nothing is reconstructed.
`scripts/distill_seed.py` rebuilds the seed from the game's own asset
files: it clones one vanilla deco's objects (the MonoScripts from
`globalgamemanagers`, the rest from `sharedassets2` and the external
`resources` file), materializes the stream-based mesh / texture data
inline (the seed carries no resource stream), and rewires the PPtrs
(mono → script, animation → clip, materials → shader, the deco GO
pair's components and transforms) to the seed-local clones. The game's
files carry no embedded typetrees (they resolve types through the
engine's type tree package), so the distiller embeds one per class:
the stock class nodes straight from the type tree package, and a
synthesized node per script class (the three MonoBehaviours), which is
what lets the bundler read and write the mono fields. The seed adopts
the game's Unity version string and native serialization layout, and
its `script_type_index` values are rebased to a dense 0/1/2. Every
seed object round-trips byte-exact.

### 3.5 The texture array (the vanilla mechanism)

The game's posters share one `PosterMaterial` bound to a `Posters`
**`Texture2DArray`**; each deco's art node samples it, and the slice is
chosen by `m_SpecialIndex`, which the game copies into the material's
`_TexIndex` uniform. One array + one shared material per bundle — no
per-poster material or texture.

- **The array** — `add_texture_array` packs one slice per poster (the
  set's poster count; not the vanilla's 72) into a `Texture2DArray`,
  slice-major: each slice's full mip chain (mip 0 first) is one
  contiguous block, `m_DataSize // m_Depth` bytes long. `m_Format` is
  the **GraphicsFormat** for the payload (`RGBA_BC7_UNorm` for BC7),
  not the `TextureFormat` — the array's `m_Format` field is a
  GraphicsFormat, and writing the `TextureFormat` value (e.g. `25` for
  BC7) makes the GPU decode the blocks as a different format. The
  vanilla array is DXT5 (`GraphicsFormat 100`); ours is BC7, the
  bundler's format for all textures.
- **The shared material** — `add_array_material` clones the seed's
  `__proto_poster_material` (the game's `PosterMaterial`) and binds
  `_MainTexArray` to the array.
- **Slice selection** — `add_poster` sets `m_SpecialIndex` to
  `m_DecoObjectType − 1` (the 0-based slice, in registration order) and
  `m_SpecialMesh` to the poster's own art renderer. The art node's
  `MeshRenderer` uses the shared material; the game picks the slice at
  runtime.

## 4. Plan

1. **Extend the seed distillation** — done. `scripts/distill_seed.py`
   rebuilds the seed from the game's own asset files (§3.4): the five
   prototype types, the three quad meshes plus the guide strip mesh
   (verbatim — stream vertex data materialized inline), and the
   constant content (the game's `MAT_PreviewTransparentGreen` and
   `MAT_Dashedline` materials with their own shaders, guide texture
   inline, flip clip), plus the cardpack scaffolding (the
   `display_texture` shader from the external `resources` file, the
   `defaultMat` material, the cardpack mesh proto — the deco's
   `Plane_1x1` with the cardpack's channel table — and the deco's
   `PosterHorizontal` / `SnapLoc_L` GameObject pair, wired exactly as
   the deco wires them: the 3-component child under the 1-component
   root, filter on the `default` mesh, renderer on `defaultMat`) — and
   the array scaffolding (§3.5): the game's `Posters` `Texture2DArray`
   (empty-templated — `m_DataSize` 0; the bundler fills width / height /
   depth / `m_Format` / data) and the game's `PosterMaterial` (bound to
   the array shader, `_MainTexArray` nulled). Seed is now 34 objects /
   18 type entries / ~200 KB (the embedded typetrees account for most
   of the size); every object round-trips byte-exact. BoxCollider /
   Animation prototypes stay unnamed (their typetrees carry no
   `m_Name`) and are found by type; the rest by name.
2. **`add_poster(name, material)` on `Bundle`** — done. The aspect is
   `name`'s final segment (square / portrait / landscape) and the root
   object name derives from `name` (`{name}_Prefab`); the aspect
   selects the kept quad mesh and the art node name (`Poster` /
   `PosterHorizontal` / `PosterSquare`). `material` is the shared
   `PosterMaterial` (bound to the `Posters` array's `_MainTexArray`,
   §3.5) — the art node samples it and `m_SpecialIndex` picks the
   slice, so no per-poster material or texture is emitted. The icon is
   not part of the poster — it ships as a plain Texture2D + Sprite in
   the cardpack bundle. Builds the 15-GameObject graph from the
   prototypes with the §2.5 constants (art scale 3.0683, preview z
   3.1, trigger verbatim from the seed, layers 12 / 27, PPtrs per
   §1.4); `m_DecoObjectType` increments per bundle (1..N in
   registration order), `m_SpecialIndex` is `m_DecoObjectType − 1`
   (the array slice) and `m_SpecialMesh` the poster's own art renderer
   (the game-typetree-only pair, verified on the vanilla decos). The
   shared constants (flip clip, quad meshes, guide mesh + texture, the
   3 scripts, the 2 shared materials, the array shader + its fallback,
   the `Posters` array) are kept once per bundle and renamed from
   `__proto_*`. Returns `(root, graph)` for `register()` — `graph` is
   the whole poster plus the shared constants, for the preload list.
   Two quirks normalized: the `MoveStateValidArea` mesh is bound as an
   external-file PPtr to the built-in cube mesh (fileID 1, pathID
   10202 — the game's own binding, resolved through the externals
   table), and the slab keeps the deco's per-aspect y nudge (0 /
   0.001 / 0.004).
3. **EPL manifest emitter**: the JSON of §1.1 with our naming
   (`Name`, `PrefabName`, `SpriteName`, `DecoObject`, `DecoType:
   "Poster"`, `IsDecoObject: true`, `AddItemToFurnitureShop`, `Price`,
   `LevelRequirement`, `VideoClips`), top-level bundle metadata
   (`BundleId`, `MaxTextureSize: 1024` — or `2048` if any ultra
   texture —, `TextureCompression`).
4. **Naming convention** for the objects: a per-set prefix + number
   (e.g. `NIKKE_REBORN_<Set>_<NNN>_Prefab`), mirroring the game's
   `<name>_Prefab` root naming.
5. **Wire into `bundle`**: build the poster bundle, place it as
   `<name>_prefabloader/` (bundle + manifest) in the BepInEx tree, ship
   in the per-set zip.
6. **BC7 mip chains for the room props** — done. `compress_mip_levels`
   (full chain: box-filter halving to 1×1, block levels padded to the
   4×4 grid; `compress_mipmapped` wraps it into one concatenated
   payload) feeds `add_texture(mipmapped=True)` /
   `add_raw_texture(..., mip_count)` and the `Posters` array — each
   slice carries the full chain (§3.5). `build` mips every `*_Material`
   texture; card art and icons stay single-mip. Art stores the full
   chain (11 mips at 1024²), icons 1; level-0 decodes within BC7 noise
   of the source.

### Constants to bake in

- Quad base sizes: 0.1473 (short) × 0.1441 / 0.1998 (long), thickness
  0.0008; guide mesh unit-width.
- Art scale 3.0683 (preview z 3.1) → world
  sizes 0.4520 (short) / 0.6130 (long): square 0.4520 × 0.4421,
  portrait 0.4520 × 0.6130, landscape 0.6130 × 0.4520.
- Slab thickness 0.0076, slab = `(w_world, 0.0076, h_world)` (kept
  within ~2% of the footprint); placement volume
  1×1×1 @
  local y 0.469.
- Root trigger 0.6 × 0.47 × 0.02 @ (0, 0.08, 0), layer 12 — must stay
  at least the largest poster's footprint.
- `InteractableDecoration` fields (§1.4); scripts (§1.3); flip clip
  shared across all posters.
- Textures: final images supplied to `add_poster` (1024², or 2048²
  ultra — content boxes per §2.4; landscape stored
  transposed), packed into the `Posters` array (BC7, each slice the
  full mip chain, §3.5); icon 512² letterboxed on transparent. The
  quads' UVs are the game's verbatim (distilled), sampling the
  inner margin-bleed rect.

### Decisions

- **In-game delivery** — no work: a dedicated decoration shop
  auto-appends the posters; `AddItemToFurnitureShop: false` stands.
- **Scale** — the game's 3.0683 / preview z 3.1, verbatim. Safe
  either way: the scripts bind by PPtr and serialized flags; none
  reads the scale. The trigger and slabs are re-derived from the
  world sizes above.
- **`m_DecoObjectType`** — the game keys deco identity on it, so it
  must be unique per poster; `add_poster` increments it per bundle
  (1..N in registration order).
- **Shared material + array, not per-poster** — the game ships one
  `PosterMaterial` bound to a `Posters` `Texture2DArray`, each deco
  picking its slice via `m_SpecialIndex` → `_TexIndex` (§3.5). One
  array + one shared material per bundle, so no per-poster material /
  texture objects are emitted and the slice selection is the game's
  own runtime mechanism. The array is named `Posters` (the game's
  name) and its depth is the set's poster count (compact); slice
  order is the registration order.
- **Equivalence against the game's decos** — since the seed is
  distilled from the game's own files, the emitted poster graph is
  compared object-by-object to a vanilla deco in
  `sharedassets2` (`scripts/compare_posters.py`): same 15-GameObject
  hierarchy, component orders, layers, transforms, and
  `InteractableDecoration` fields (including the
  `m_SpecialMesh` / `m_SpecialIndex` pair); the shared material, the
  `Posters` array (compact depth, BC7) and the names differ by design.
- **Quads and UVs verbatim** — the three quad Mesh objects are
  distilled from the game's files as-is (geometry, UVs, indices —
  including the transversed landscape set); the textures reuse the
  game's content boxes + margin bleed (§2.4), so the display matches
  the game exactly and no UV transcription is needed.
- **Art prep is upstream** — `add_poster` takes the final texture,
  final icon, and the chosen aspect; no image processing beyond the
  BC7 embedding. Cropping to the bucket, resize, transversed
  landscape storage, placement in the game's content boxes, the
  back / edge rects, the 2048² "ultra" canvas (source ≥ the 2048 box
  size), and icon generation happen in a stage before `bundle` — not
  built yet; just `bundle` for now.
- **Texture format / mips** — BC7 (the bundler's existing
  `compress_texture` path; 1024²/2048²/512² are multiples of 4, so no
  RGBA32 fallback). Mip policy across the bundle: the room props (the
  poster art in the `Posters` array, the cardpack `*_Material` box /
  sleeve textures) store the full BC7
  chain (`compress_mip_levels` — box-filter halving to 1×1, block
  levels padded to the 4×4 grid), card art and icons stay single-mip.
  The array's `m_Format` is the **GraphicsFormat** for the payload
  (`RGBA_BC7_UNorm`), not the `TextureFormat` — the field is a
  GraphicsFormat, and writing the `TextureFormat` value makes the GPU
  decode the BC7 blocks as a different format (every mip garbage,
  shifting with distance).
- **No `poster.rs`** — `add_poster` keeps the bundling in-process:
  embed the final texture (BC7), build the graph, wire the constants.
- **MonoScripts** — the seed clones the game's own MonoScript objects
  (from `globalgamemanagers.assets`) — the exact assemblies the game
  loads — so there is no staleness question; the MonoBehaviour
  typetrees are synthesized per script class (§3.4).
- **Off-bucket ratios** — the artwork's ratio rarely equals a bucket
  exactly; the difference is absorbed with a center crop at pack time
  (≤ ~4% of one dimension — invisible). Our upstream stage does the
  same; a per-poster slab override (the slab matched to the art's
  true ratio) is the escape valve for > ~3% outliers.
- **Dashed-line tint** — the guides material is the game's own
  `MAT_Dashedline` (cloned verbatim, green `_Color`
  (0.176, 1.0, 0.0, 60/255) and all), bound to the game's
  `Mobile/Particles/Additive` shader, which never reads `_Color`
  (additive `_MainTex` only) — so the line renders white exactly like
  the game's posters, and no normalization is needed.

### Remaining

- **In-game size check**: like the figurine axis/winding note in
  `build_mesh_buffers`, the poster's real-world size and orientation
  need one in-game verification pass.
