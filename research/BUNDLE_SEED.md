# BUNDLE_SEED

`src/nikke_reborn/seed.bundle` is the container the bundler clones
against: one prototype of every object type a cardpack bundle emits.
The bundler loads it, clones the prototypes (renaming each and rewiring
the PPtrs to the clones), and fills in the per-set content (the
textures, the model meshes, the poster array). Nothing in the seed is
set-specific — it is a fixed template, regenerated only when the game's
assets change.

## How it's built

`scripts/distill_seed.py` rebuilds it from the game's own asset files
(`GAME_PATH` in `.env`). It builds the minimal seed container directly in
code (a `UnityFS` `BundleFile` holding an empty `SerializedFile`) as the
base, then rebuilds every object from the game's assets. The full
`seed.bundle` is a pure output — the distiller never reads a prior seed,
so the file is regenerable from scratch. The game inputs:

- `sharedassets2.assets` — one vanilla poster deco + its materials,
  meshes, shaders and textures.
- `globalgamemanagers.assets` — the three game MonoScripts.
- the external `resources` file — the `display_texture` shader.

Steps:

1. Clone one vanilla deco's objects (the MonoScripts from
   `globalgamemanagers`, the rest from `sharedassets2` + the external
   `resources` file).
2. Materialize the stream-based mesh / texture / array data inline —
   the seed carries no resource stream.
3. Embed a typetree per class. The game's files carry none (they
   resolve types through the engine's type tree package), so the
   distiller embeds the stock class nodes straight from the type tree
   package and builds a synthesized node per script class (the three
   MonoBehaviours) — which is what lets the bundler read and write the
   mono fields.
4. Rewire the PPtrs to the seed-local clones: mono → script, animation
   → clip, materials → shader, the model GO pair's components and
   transforms.
5. Adopt the game's Unity version string and native serialization
   layout; rebase `script_type_index` to a dense 0/1/2.
6. Byte-exact verify every object's round-trip.

The path IDs are the distillation order (1 = the manifest, 2..34 the
rest); they are stable but incidental.

## Summary

| | |
|---|---|
| `unity_version` | `6000.0.66f2` (the game's) |
| objects | 34 |
| type entries | 18 (each embeds a typetree) |
| `script_types` | 3 (rebased to 0/1/2) |
| externals | 1 (`unity_builtin_extra`) |
| size | ~200 KB (the embedded typetrees account for most) |

## Object inventory

### Manifest

| pid | type | name | role |
|---|---|---|---|
| 1 | AssetBundle | `seed` | the bundle manifest |

### Model template (cardpack items, figurines, posters)

The bundler clones this pair for every `add_mesh` / `add_poster`: a
root GameObject (Transform only) parenting a child GameObject (Transform
+ MeshFilter + MeshRenderer). The child's filter uses the `default`
mesh; its renderer uses `defaultMat`. `SnapLoc_L` is a snap-location
placeholder in the deco (one of L/R/Up/Down under `MoveStateValidArea`)
used as the root because it is a clean Transform-only GameObject; both
names are sourcing artifacts and are renamed on clone.

| pid | type | name | role |
|---|---|---|---|
| 15 | GameObject | `PosterHorizontal` | the child (3 components) |
| 16 | GameObject | `SnapLoc_L` | the root (Transform only) |
| 17 | Transform | — | the child's transform |
| 18 | Transform | — | the root's transform |
| 19 | MeshFilter | — | the child's filter → `default` mesh (pid 21) |
| 20 | MeshRenderer | — | the child's renderer → `defaultMat` (pid 28) |
| 21 | Mesh | `default` | the cardpack model mesh (the deco's `Plane_1x1`, cardpack channel table) |
| 28 | Material | `defaultMat` | the display material → `display_texture` shader (pid 10); `_MainTex` nulled, set on clone |
| 10 | Shader | — | the `display_texture` shader (the cardpack's display shader) |

### Texture / sprite prototypes

The bundler clones these for every texture / icon it emits.

| pid | type | name | role |
|---|---|---|---|
| 13 | Texture2D | `PosterArtComp1` | the Texture2D prototype |
| 14 | Sprite | `White1px` | the Sprite prototype |

### Poster scaffolding (shared constants)

Kept once per bundle (not per poster). The three MonoBehaviours bind the
game's own scripts; the quad meshes carry the verbatim geometry and UVs
(including the transversed landscape set).

| pid | type | name | role |
|---|---|---|---|
| 3 | MonoScript | `InteractableDecoration` | the game's script |
| 2 | MonoScript | `ShelfMoveStateValidArea` | the game's script |
| 4 | MonoScript | `DashedLine` | the game's script |
| 5 | MonoBehaviour | `__proto_poster_mono_interactable` | the `InteractableDecoration` mono → script 3 (carries the game-typetree `m_SpecialMesh` / `m_SpecialIndex`) |
| 6 | MonoBehaviour | `__proto_poster_mono_valid_area` | the `ShelfMoveStateValidArea` mono → script 2 |
| 7 | MonoBehaviour | `__proto_poster_mono_dashed_line` | the `DashedLine` mono → script 4 |
| 22 | Mesh | `__proto_poster_mesh_square` | the square quad |
| 23 | Mesh | `__proto_poster_mesh_portrait` | the portrait quad |
| 24 | Mesh | `__proto_poster_mesh_landscape` | the landscape quad (transversed) |
| 25 | Mesh | `__proto_poster_mesh_guide` | the guide strip |
| 26 | Texture2D | `__proto_poster_guide_tex` | the guide texture (512²) |
| 32 | AnimationClip | `__proto_poster_flip` | the flip clip |
| 33 | Animation | — | the animation component → the flip clip |
| 34 | BoxCollider | — | the root trigger |

### Poster materials

| pid | type | name | role |
|---|---|---|---|
| 29 | Material | `__proto_poster_material` | the shared poster material → array shader (pid 12), `_MainTexArray` |
| 30 | Material | `__proto_poster_material_placement` | the placement material → placement shader (pid 9) |
| 31 | Material | `__proto_poster_material_guides` | the guides material → guides shader (pid 8), `_MainTex` → guide tex (pid 26) |

### Array scaffolding

The `Posters` `Texture2DArray` and the shader the shared poster material
binds. The array is an empty template — `m_DataSize` 0, the vanilla
`m_Format` / `m_Depth` — that `add_texture_array` overwrites with the
set's width / height / depth / `m_Format` / data (slice-major; `POSTERS`
depth = the poster count).

| pid | type | name | role |
|---|---|---|---|
| 27 | Texture2DArray | `__proto_poster_array` | the `Posters` array template |
| 12 | Shader | — | the array shader (bound by `__proto_poster_material`, pid 29) |
| 11 | Shader | — | the array shader's fallback (a dependency of pid 12) |

## How the bundler uses it

`Bundle._extract_prototypes` maps each seed object to its role (the
`role` column above). Some are found by type — the first of the type in
pid order — the texture prototype (`PosterArtComp1`), the sprite
prototype (`White1px`), the `default` mesh, the MeshFilter /
MeshRenderer, the model GO pair (the 3-component child + the
1-component root), and the BoxCollider / Animation; the rest are found
by `__proto_*` name (the poster constants). `Bundle.__init__` keeps the
shared constants plus the model template and the texture / sprite
prototypes and drops the rest; when a set has no posters,
`Bundle.save` prunes the array shader + its fallback.
