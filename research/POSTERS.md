# POSTERS

Research notes and plan for the poster feature (roadmap item).
Source: the reference cardpack mod in `reference/` (extracted to
`reference/extracted/`), analyzed with UnityPy. Every number below was
measured from the reference bundle, not assumed.

## 1. How the reference mod adds posters

The mod ships posters as **data for Enhanced Prefab Loader (EPL)** — no
code of its own is involved. EPL scans `BepInEx/plugins/**/*_prefabloader/`
folders; each holds an EPL manifest (`.json`) and a same-named,
extensionless Unity AssetBundle:

```
BepInEx/plugins/CRYPTON/cryptons_posters_prefabloader/
├── cryptons_posters          # Unity AssetBundle (33.5 MB)
└── cryptons_posters.json     # EPL manifest
```

### 1.1 The EPL manifest

Top level: `Name: "CRYPTONS Posters"`, `BundleId:
cryptons_posters_829a02c885fc473496cc700d0383546c`,
`AutoCompressTextures: false`, `MaxTextureSize: 1024`,
`TextureCompression: DXT5`. `Items`, `CardExpansions`, `CustomShops`,
`Assemblies` are all empty — this bundle is posters only.

`Prefabs` has 72 entries, one per poster (numbered 001–072):

| Field | Value |
|---|---|
| `Name` | `CRYPTONS Poster NNN` |
| `PrefabName` | `CRYPTONS_EPL_Posters_829a02c885_NNN_Prefab` — the root object in the bundle |
| `SpriteName` | `..._NNN_Icon` — the UI icon sprite |
| `DecoObject` | `..._NNN_Deco` — the id the loader registers in the game's deco database |
| `DecoType` | `"Poster"` |
| `IsDecoObject` | `true` |
| `AddItemToFurnitureShop` | `false` |
| `Price` | `500.0` |
| `LevelRequirement` | `25` |
| `VideoClips` | `[]` |

### 1.2 The AssetBundle

UnityFS, Unity 2021.3.38f1 (the game's engine), LZ4-compressed, one
internal `CAB-…` file + a `.resS` resource stream (mesh vertex data).
3902 objects:

| Type | Count | Note |
|---|---|---|
| GameObject / Transform | 1080 / 1080 | 15 per poster |
| MeshRenderer / MeshFilter | 504 / 504 | 7 per poster |
| MonoBehaviour | 216 | 3 per poster |
| Texture2D | 145 | 72 art + 72 icon + 1 guide |
| BoxCollider | 144 | 2 per poster |
| Material | 74 | 72 per-poster + 2 shared |
| Sprite | 72 | the icons |
| Animation | 72 | on `AnimGrp`, all bound to the shared flip clip |
| Mesh | 4 | square / portrait / landscape quads + guide strip |
| MonoScript | 3 | the game's own scripts (see 1.4) |
| Shader | 2 | empty names — resolved game-side |
| AnimationClip | 1 | `CRYPTONS_EPL_PosterFlip` |
| AssetBundle | 1 | the bundle manifest object |

There are no top-level `Prefab` assets: the 72 root GameObjects are stored
as scene objects, named exactly like the manifest's `PrefabName` values
(verified: bundle names == manifest names, 72/72).

### 1.3 The per-poster scene graph

15 GameObjects per poster, a clone of the game's vanilla poster deco
structure with only the art swapped:

```
CRYPTONS_EPL_Posters_…_NNN_Prefab      BoxCollider (trigger) + InteractableDecoration
├── AnimGrp                            Animation → CRYPTONS_EPL_PosterFlip
│   ├── Poster / PosterHorizontal / PosterSquare
│   │                                  MeshFilter + MeshRenderer → NNN_Material → NNN_Art
│   └── PreviewMesh                    MeshFilter + MeshRenderer
└── MoveStateValidAreaGrp              ShelfMoveStateValidArea (scaled to the poster's slab, §2.5)
    └── MoveStateValidArea             MeshFilter (null mesh) + MeshRenderer + BoxCollider (1×1×1)
        ├── SnapLoc_L / SnapLoc_R / SnapLoc_Up / SnapLoc_Down
        └── DashedLineGrp              DashedLine
            ├── Line1 … Line4          MeshFilter (PosterGuideMesh) + MeshRenderer
```

The art node's name is per aspect (§2.2). The three MonoBehaviours are the
game's own scripts from `Assembly-CSharp.dll`:

- `InteractableDecoration` — on the root
- `ShelfMoveStateValidArea` — on `MoveStateValidAreaGrp`
- `DashedLine` — on `DashedLineGrp`

No custom code: the game's native deco system drives grab/drag/snap/flip
because the components are the game's own, pre-filled with vanilla poster
values.

### 1.4 The `InteractableDecoration` fields (serialized, identical per aspect)

| Field | Value |
|---|---|
| `m_DecoObjectType` | per-poster unique — 1..72 (the poster index) in the reference |
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
| everything else (`m_Mesh`, `m_SkinMesh`, lists, …) | null / empty |

Root layer: `12`. Root BoxCollider: `m_IsTrigger: true`,
size `(0.6, 0.47, 0.02)`, center `(0, 0.08, 0)` — **identical on all 72**
(sized to the largest poster; §2.5).

### 1.5 Script binding

In the binary bundle the MonoBehaviours reference **bundled MonoScript
objects by direct PPtr**; the MonoScript typetree carries
`m_ClassName` / `m_Namespace` / `m_AssemblyName` / `m_PropertiesHash`
and **no GUID** — GUIDs are only needed by the YAML (`.prefab`) format,
which is why that route was dropped (§3). The reference bundle is a
shipped, working mod for the same game, so its MonoScripts are a
drop-in prototype source.

### 1.6 The rest of the reference mod (not posters)

For context: four cardpack bundles (`CRYPTONS_CARDPACK` with 66 items,
4 expansions, 1 custom shop; plus Halloween/NSFW/SEX/SFW album sets of
300 cards each), each with its own `_prefabloader` folder, EPL manifest,
`.ctpacks` (pack ids, card numbers, foils) and `CRYPTONPackPools.pool`
(price profile, gacha weights). Two DLLs — `CryptonsCompanion.dll`
v1.4.28 (`com.cryptons.cardpack.companion`) and `CRYPTONAlbumPackPools.dll`
— both depend on `EnhancedPrefabLoader.API.*`; EPL core itself is a
separate install. Configs cover ghost drops, album/cardback integration,
and vanilla pricing (`ExpansionPrefix = Crypton`). A `Phone - Overhaul`
plugin adds the shop app's icon/backgrounds.

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

The artwork's `w/h` is bucketed to {1:1, 3:4, 4:3}. Across the 72:
**39 portrait / 20 landscape / 13 square**, and the art node is named
per aspect: `Poster` (portrait mesh) ×39, `PosterHorizontal` (landscape
mesh) ×20, `PosterSquare` (square mesh) ×13. The icons confirm the source
ratios: `001` content 377×505 (w/h 0.747 → 3:4), `017` 507×376
(1.348 → 4:3), `049` 374×366 (1.022 → 1:1).

The art is **cropped** to the bucket's aspect when packed into the
texture (≤ ~4% of one dimension for these 72, e.g. 001's 0.747 source
fills a 0.722 content box, 700×970), so display is essentially
undistorted. Two landscape posters (045, 046) additionally got
hand-tweaked valid-area slabs (0.5564 × 0.4098, matching their 2.8
scale) instead of a fourth aspect.

### 2.3 World size = one fixed uniform scale

Every `Poster`/`PreviewMesh` node carries
**localScale = (3.0683, 3.0683, 3.0683)** — 70 of 72, regardless of
aspect (root and `AnimGrp` scale 1; position (0,0,0)). The preview's
z scale is 3.1 (a depth nudge). Two legacy landscape posters (045,
046 — a consecutive pair, same series) are authored at **2.8** with
preview z **2.831** instead. Final sizes:

| Aspect | w × h (game units) |
|---|---|
| square | ≈ 0.45 × 0.44 |
| portrait | ≈ 0.45 × 0.61 |
| landscape | ≈ 0.61 × 0.45 |

### 2.4 The texture pipeline

The art is **not** stretched anywhere (an earlier "pre-stretched
square" reading of this was wrong). The verified mechanism:

- **Art** (`…_NNN_Art`, 1024², DXT1): a small packed atlas — the
  front artwork sits in its **aspect-matched content box at its
  native aspect, undistorted**, with painted content in the back /
  edge rects and the rest opaque padding (near white, alpha 255 —
  which is why the texture corners read white). Verified by cropping
  the front region out of the exported textures:
  `poster049_front.png` (square) and `poster001_front.png` (portrait)
  are clean, undistorted posters; the corner padding averages
  (252, 251, 254).
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
  display — verified by transversing the `017` crop back: 970×700,
  ratio 1.386 vs the icon's 1.348. No stretching anywhere. Back faces
  sample a ~206×221 px rect (square; ~206×307 portrait / landscape;
  u 748.5–954.0, v 158.4–379.5 / 113.4–420.0 in 1/1024 units), edge
  faces a ~125×9 px strip (u 762.7–887.7 × v 113.4–122.6); the guide
  mesh has its own trivial 0–1 UVs.
- **No material-side aspect params**: `m_SavedProperties` is only
  `_Color` (gray 0.684) + `_EmissionColor` (0); no `_MainTex_ST`.
- **Icon** (`…_NNN_Icon`, 512², DXT5 + Sprite): the artwork uniformly
  scaled and letterboxed on transparent at its native aspect (e.g.
  `001` content bbox 64,4 – 441,509) for the UI.
- **Material** (`…_NNN_Material`): 72/72 verified to bind their own
  `_NNN_Art` texture via `_MainTex`.
- Shared: `CRYPTONS_EPL_PosterPlacement`, `CRYPTONS_EPL_PosterGuides`
  materials; `CRYPTONS_EPL_PosterGuideTexture` (512²).
- Animation: the 72 `Animation` components on `AnimGrp` are 72/72 bound
  to the single shared clip `CRYPTONS_EPL_PosterFlip` (the placement
  flip, matching `m_CanFlip: 1`).

Texture inventory: 72 × 1024² + 73 × 512² (72 icons + 1 guide).

Consequence: we replicate the reference layout exactly — the three
quad Mesh objects are distilled verbatim (UVs included), and the
final texture arrives already matching that layout (art in the
content boxes, back / edge rects painted); the bundler embeds it
as-is. UVs are normalized, so the same quads serve the 1024² and
2048² canvases (content boxes ×2 at 2048²).

### 2.5 Interaction geometry

- **Root trigger** (all 72, aspect-independent): BoxCollider
  `0.6 × 0.47 × 0.02`, center `(0, 0.08, 0)`, trigger — sized to the
  largest poster so any poster is easy to grab.
- **`MoveStateValidAreaGrp`** (the valid wall slab): local position
  `(0, 0, −0.0005)` plus a small hand-tuned y nudge per aspect (0.0
  portrait / 0.001 landscape / 0.004 square), **rotated 90° about X**,
  scale `(w, 0.0076, h)` **per poster to its own footprint**. The 90°
  rotation maps local z to world −y, so `scale.z` is the poster's
  vertical height and `scale.y` the 7.6 mm wall thickness. Measured
  ~1% under the world footprint:

  | Slab scale | Count | Aspect |
  |---|---|---|
  | (0.449, 0.0076, 0.6066) | 39 | portrait |
  | (0.449, 0.0076, 0.4393) | 13 | square |
  | (0.6017, 0.0076, 0.4465) | 18 | landscape |
  | (0.5564, 0.0076, 0.4098) | 2 | landscape (hand-tweaked) |

  (x = width, z = height along the wall.)
- **`MoveStateValidArea`** (layer 27): scale 1, local position
  `(0, 0.469, 0)`, unit BoxCollider (trigger), **no mesh** — the
  reference's MeshFilter holds an external-file PPtr (fileID 1,
  pathID 10202, an authoring-scene object that resolves to nothing
  outside it) — an invisible placement volume.
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
  PPtrs, exactly as the shipped reference mod does.
- **One language, one library, one proven mechanism.** The Python
  bundler already loads `seed.bundle`, clones prototypes, embeds
  textures (BC7 via `Texture2DConverter`, with the `nkTx` lossless
  shortcut), and emits LZ4 AssetBundles.

### 3.3 Architecture

- `bundle` (command) — game-agnostic composition: copies set folders,
  builds bundles, lays out the BepInEx tree, zips.
- `bundler` (library) — the Unity construction layer: the only place
  with game-format knowledge. `add_poster` belongs here.
- Per-poster input: the final texture (1024² / 2048²) and final icon
  (512²) PNGs plus the chosen aspect. The EPL manifest JSON is emitted
  alongside the bundle (same layer).

### 3.4 Prototype gap

`seed.bundle` holds prototypes for: Transform, GameObject, Texture2D,
Sprite, Shader, MeshFilter, Material, Mesh, MeshRenderer (+ the
AssetBundle manifest). Posters need **five more types** — and the
reference bundle contains all of them with the vanilla field values
already set:

| Needed | In reference bundle |
|---|---|
| BoxCollider | 144 (root triggers + placement volumes) |
| Animation | 72 (bound to the flip clip) |
| AnimationClip | 1 (`CRYPTONS_EPL_PosterFlip`) |
| MonoBehaviour | 216 (3 scripts, vanilla values) |
| MonoScript | 3 (`InteractableDecoration`, `ShelfMoveStateValidArea`, `DashedLine`) |

The constant content (shared materials, guide texture, flip clip) and
the three quad meshes are distilled from the reference bundle as-is —
the Mesh objects carry the exact geometry and UVs (including the
transversed landscape set), so nothing is reconstructed.
`scripts/distill_seed.py` recreates the distillation (the original
distiller filtered a whole reference bundle whose source no longer
exists): it extends the current seed in place, cloning the prototypes
across files — copying the type-table entries (the three MonoBehaviour
entries carry one typetree per script class), materializing the
stream-based mesh / texture data inline, and rewiring the PPtrs (mono
→ script, animation → clip, materials → shader) to the seed-local
clones.

## 4. Plan

1. **Extend the seed distillation** — done. `scripts/distill_seed.py`
   adds the five prototype types, the three quad meshes plus the guide
   strip mesh (verbatim — stream vertex data materialized inline), and
   the constant content (2 shared materials + their deco shader, guide
   texture inline, flip clip), plus the per-poster material prototype
   (001's, `_MainTex` nulled — it binds the seed's built-in Standard
   shader, so no shader remap was needed). Seed is now 30 objects /
   17 type entries / 62 KB; the quad UVs round-trip exactly.
   BoxCollider / Animation prototypes stay unnamed (their reference
   typetrees carry no `m_Name`) and are found by type; the rest by
   name.
2. **`add_poster(name, texture, icon, aspect)` on `Bundle`** — done.
   Derives every object name from `name` (`{name}_Prefab` root,
   `{name}_Art` texture, `{name}_Icon` texture + sprite,
   `{name}_Material`); `aspect` selects the kept quad mesh, the art
   node name (`Poster` / `PosterHorizontal` / `PosterSquare`), and the
   slab scale. BC7-embeds the final images, builds the 15-GameObject
   graph from the prototypes with the §2.5 constants (art scale
   3.0683, preview z 3.1, trigger verbatim from the seed, layers
   12 / 27, PPtrs per §1.4); `m_DecoObjectType` increments per
   bundle (1..N in registration order). The shared constants (flip clip, quad meshes,
   guide mesh + texture, the 3 scripts, the 2 shared materials, the
   deco shader) are kept once per bundle like the Standard shader
   (~360 KB, mostly the guide mips) and renamed from `__proto_*` to
   the reference-style names. Returns `(root, graph)` for
   `register()` — `graph` is the whole poster plus the shared
   constants, for the preload list. Two reference quirks normalized:
   the `MoveStateValidArea` mesh is a plain null (the reference's
   external-file PPtr is unresolvable outside the authoring scene),
   and the slab's per-aspect y nudge (0 / 0.001 / 0.004) is dropped —
   the slab is derived exactly from the world sizes per the Decisions.
3. **EPL manifest emitter**: the JSON of §1.1 with our naming
   (`Name`, `PrefabName`, `SpriteName`, `DecoObject`, `DecoType:
   "Poster"`, `IsDecoObject: true`, `AddItemToFurnitureShop`, `Price`,
   `LevelRequirement`, `VideoClips`), top-level bundle metadata
   (`BundleId`, `MaxTextureSize: 1024` — or `2048` if any ultra
   texture —, `TextureCompression`).
4. **Naming convention** for the objects (the reference's
   `CRYPTONS_EPL_Posters_<hash>_NNN_*` pattern; pick the NIKKE REBORN
   equivalent, e.g. per-set prefix + number).
5. **Wire into `bundle`**: build the poster bundle, place it as
   `<name>_prefabloader/` (bundle + manifest) in the BepInEx tree, ship
   in the per-set zip.
6. **BC7 mip chains for the room props** — done. `compress_mipmapped`
   (full chain: box-filter halving to 1×1, block levels padded to the
   4×4 grid) feeds `add_texture(mipmapped=True)` /
   `add_raw_texture(..., mip_count)`; `add_poster` mips the poster art
   and `build` mips every `*_Material` texture; card art and icons
   stay single-mip. Rebuilt 72/72 against the reference: art 11 = 11,
   icons 1 = 1, guide 10 = 10; level-0 decode within BC7 noise of the
   reference mip0.

### Constants to bake in

- Quad base sizes: 0.1473 (short) × 0.1441 / 0.1998 (long), thickness
  0.0008; guide mesh unit-width.
- Art scale 3.0683 (preview z 3.1, per the reference §2.3) → world
  sizes 0.4520 (short) / 0.6130 (long): square 0.4520 × 0.4421,
  portrait 0.4520 × 0.6130, landscape 0.6130 × 0.4520.
- Slab thickness 0.0076, slab = `(w_world, 0.0076, h_world)` (the
  reference keeps it within ~2% of the footprint); placement volume
  1×1×1 @
  local y 0.469.
- Root trigger 0.6 × 0.47 × 0.02 @ (0, 0.08, 0), layer 12 — must stay
  at least the largest poster's footprint.
- `InteractableDecoration` fields (§1.4); scripts (§1.3); flip clip
  shared across all posters.
- Textures: final images supplied to `add_poster` (1024², or 2048²
  ultra — content boxes per the reference, §2.4; landscape stored
  transposed), embedded via BC7 — poster art with the full mip chain
  (`compress_mipmapped`, as the reference mipmaps its room props);
  icon 512²
  letterboxed on transparent. The quads' UVs are the reference's
  verbatim (distilled), sampling the inner margin-bleed rect.

### Decisions

- **In-game delivery** — no work: a dedicated decoration shop
  auto-appends the posters; `AddItemToFurnitureShop: false` stands.
- **Scale** — the reference's 3.0683 / preview z 3.1, verbatim: a
  72/72 rebuild comparison found the reference uniform on 70 of 72,
  so there is no reason to deviate (the two 2.8 legacy posters are
  not reproduced). Safe either way: the scripts bind by PPtr and
  serialized flags; none reads the scale. The trigger and slabs are
  re-derived from the world sizes above.
- **`m_DecoObjectType`** — the game keys deco identity on it, so it
  must be unique per poster; `add_poster` increments it per bundle
  (1..N in registration order — matching the reference's 1..72).
- **Equivalence check** — the full reference set rebuilt through
  `add_poster` and compared object-by-object: 3902 = 3902 objects,
  every name / layer / component order / mono field / PPtr wiring /
  mesh / UV identical, textures within encoding noise (BC7 vs DXT1 /
  DXT5), mip structure identical (art 11 = 11, icons 1 = 1, guide
  10 = 10).
  Remaining deltas: the 045/046 legacy 2.8 variant, the derived slab
  vs the reference's hand-tuned one (~1%), and the slab y-nudge.
- **Quads and UVs verbatim** — the three quad Mesh objects are
  distilled from the reference as-is (geometry, UVs, indices —
  including the transversed landscape set); the textures reuse the
  reference positions (content boxes + margin bleed, §2.4), so the
  display matches the reference exactly and no UV transcription is
  needed.
- **Art prep is upstream** — `add_poster` takes the final texture,
  final icon, and the chosen aspect; no image processing beyond the
  BC7 embedding. Cropping to the bucket, resize, transversed
  landscape storage, placement in the reference content boxes, the
  back / edge rects, the 2048² "ultra" canvas (source ≥ the 2048 box
  size), and icon generation happen in a stage before `bundle` — not
  built yet; just `bundle` for now.
- **Texture format / mips** — BC7 (the bundler's existing
  `compress_texture` path; 1024²/2048²/512² are multiples of 4, so no
  RGBA32 fallback). Mip policy mirrors the reference across the whole
  mod family: the room props (poster art, the cardpack `*_Material`
  box / sleeve textures) store the full BC7 chain
  (`compress_mipmapped` — box-filter halving to 1×1, block levels
  padded to the 4×4 grid), card art and icons stay single-mip.
- **No `poster.rs`** — `add_poster` keeps the bundling in-process:
  embed the final texture (BC7), build the graph, wire the constants.
- **MonoScripts** — the reference mod is recently updated; its
  MonoScripts are current.
- **Off-bucket ratios** — the artwork's ratio rarely equals a bucket
  exactly (017: 1.348 vs 1.333; 049: 1.022 vs 1.0); the reference
  absorbs the difference with a center crop at pack time (≤ ~4% of
  one dimension for all 72 — invisible). Our upstream stage does the
  same; a per-poster slab override (the reference hand-tweaked two
  landscape slabs to the art's true ratio: 0.5564 × 0.4098 = 1.358 vs
  1.348) is the escape valve for > ~3% outliers.

### Remaining

- **In-game size check**: like the figurine axis/winding note in
  `build_mesh_buffers`, the poster's real-world size and orientation
  need one in-game verification pass.
