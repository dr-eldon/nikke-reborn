"""Shared configuration for the card pipeline.

The constants more than one part of the pipeline needs: the repository
and asset directories, the external executables, the source-hash key,
the shared variant stems, the reference card width, the copyright line
and its face, the stage-thread cap, and the pack's and the box's asset
names, the encoder preset and the run-mode output scales (default,
ultra and draft) with the ultra set-folder suffix and the item's
viewer size, and ffprobe. Everything that only one part needs (masks, tints, name
placement, encode flags) lives with the code that uses it.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
CARDS_DIR = REPO_ROOT / "cards"
IMAGES_DIR = ASSETS_DIR / "images"
MESHES_DIR = ASSETS_DIR / "meshes"
FONTS_DIR = REPO_ROOT / "fonts"
OUTPUT_DIR = REPO_ROOT / "output"
DRAFT_DIR = REPO_ROOT / "draft"
BUNDLES_DIR = REPO_ROOT / "bundles"
DATABASE_DIR = REPO_ROOT / "database"
SHOP_DIR = IMAGES_DIR / "shop"

VIEWER = "nikke-viewer"
UNITY_VIEWER = "unity-viewer"
#: The ffprobe executable: reading the hash tag out of a finished
#: MP4 card (see :func:`file._stored_hash`).
PROBER = "ffprobe"

#: Key of the embedded definition hash in the finished cards (a PNG
#: text chunk, an MP4 tag): a card whose stored hash matches the
#: current definition is skipped instead of re-rendered.
SOURCE_HASH_KEY = "nikke-reborn-source"

#: Profile rarity stems that skip the full-art pipeline entirely: only
#: their profile cards are rendered. Currently empty — every rarity
#: (including ``Aim`` and ``Cover``) also renders its full-art card.
PROFILE_RARITIES = frozenset({})

#: Variant stems that render a ``<variant>Standard`` card: the
#: ``Classic``, ``Rare``, ``Special`` and ``Exotic`` presentations.
STANDARD_STEMS = frozenset({"Classic", "Rare", "Special", "Exotic"})
#: Variant stems that render a ``<variant>Profile`` card: the
#: ``Classic``, ``Idle``, ``Cover`` and ``Aim`` presentations. The
#: ``Rare``, ``Special`` and ``Exotic`` presentations moved to the
#: ``Standard`` tier (they no longer render a profile card), and the
#: ``Goddess`` and ``Classified`` presentations render no derived card.
PROFILE_STEMS = frozenset({"Classic", "Idle", "Cover", "Aim"})

#: Reference card width (pixels): the nominal sizes below are expressed at
#: this width and scale proportionally for other viewport widths.
CARD_REFERENCE_WIDTH = 1640

#: Oswald face for the copyright line (vendored variable font, SIL OFL).
FONT = FONTS_DIR / "Oswald.ttf"

#: ffmpeg encodes and frame compositing get at most this many threads
#: each, even when a single card uses all the cores.
MAX_STAGE_THREADS = 16

#: The encoder preset and the output scales for the run modes: the
#: default renders at ``DEFAULT_SCALE`` of the definition's native
#: viewport (half resolution), ``--ultra`` at ``ULTRA_SCALE`` (twice
#: the default — the native resolution, written to the
#: ``<set> (Ultra)`` set folders), and a draft (``--draft``) at
#: ``DRAFT_SCALE`` with the faster ``DRAFT_PRESET``.
DEFAULT_PRESET = "slow"
DRAFT_PRESET = "ultrafast"
DEFAULT_SCALE = 0.5
ULTRA_SCALE = 2.0 * DEFAULT_SCALE
DRAFT_SCALE = 0.5

#: Suffix appended to each set's output folder name for an ``--ultra``
#: run (``output/<set>/`` -> ``output/<set> (Ultra)/``).
ULTRA_SUFFIX = " (Ultra)"

#: The item's (pack's and box's) viewer output size in pixels: the
#: unity-viewer's defaults, mirrored here so the pipeline computes the
#: scaled sizes (``round(·scale)``) explicitly instead of relying on
#: the viewer's implicit ones.
ITEM_VIEWER_WIDTH = 1024
ITEM_VIEWER_HEIGHT = 1024

#: Pack artwork: ``assets/images/`` holds the material template, whose two
#: pure-blue mask rectangles hold the pack's back (left) and front
#: (right) — both composed on the fly (see :mod:`nikke_reborn.pack`) —
#: written to ``<out>/<pack>/CardPack_Material.png``. The item
#: (``CardPack_Item.png``) is rendered with :data:`UNITY_VIEWER` from
#: :data:`PACK_MESH` textured with the finished material.
PACK_TEMPLATE = IMAGES_DIR / "CardPack_Material.png"
PACK_MATERIAL_NAME = "CardPack_Material.png"
PACK_ITEM_NAME = "CardPack_Item.png"
PACK_MESH = MESHES_DIR / "CardPackStatic_Mesh.obj"

#: The item's viewer configuration (model rotation and camera zoom/pan
#: as a JSON file, exported by the viewer's GUI), passed to
#: :data:`UNITY_VIEWER` with ``--config``; it sits next to the mesh.
PACK_CONFIG = MESHES_DIR / "CardPackStatic_Mesh.json"


#: The box's material template: its three solid mask rectangles mark the
#: paste regions — blue for the front (the same composition as the pack's
#: front), red for the top and green for the side (see
#: :mod:`nikke_reborn.box`). The finished material is written to
#: ``<out>/<pack>/CardBox_Material.png``. The item
#: (``CardBox_Item.png``) is rendered with :data:`UNITY_VIEWER` from
#: :data:`BOX_MESH` textured with the finished material, the way the
#: pack's item is.
BOX_TEMPLATE = IMAGES_DIR / "CardBox_Material.png"
BOX_MATERIAL_NAME = "CardBox_Material.png"
BOX_ITEM_NAME = "CardBox_Item.png"
BOX_MESH = MESHES_DIR / "CardBox_Mesh.obj"

#: The box item's viewer configuration (model rotation and camera
#: zoom/pan, as a JSON file exported by the viewer's GUI), passed to
#: :data:`UNITY_VIEWER` with ``--config``; it sits next to the mesh.
BOX_CONFIG = MESHES_DIR / "CardBox_Mesh.json"
