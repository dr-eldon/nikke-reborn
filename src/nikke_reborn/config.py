"""Shared configuration for the card pipeline: the directories, the
external executables and the constants more than one part of the
pipeline needs. The run's output preset lives in
:mod:`nikke_reborn.preset`; what a single part of the pipeline needs
lives with the code that uses it."""

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
#: ffprobe: reads the source-hash tag out of a finished MP4.
PROBER = "ffprobe"

#: The key of the hash embedded in every finished card (a PNG text
#: chunk, an MP4 tag): a card whose stored hash matches the current
#: inputs is skipped instead of re-rendered.
SOURCE_HASH_KEY = "nikke-reborn-source"

#: The card's native viewport (the viewer's default) in pixels: the
#: run's final size is this at the run's scale.
CARD_VIEWPORT = (1640, 2048)

CARD_PADDING = 50

#: The viewport width the nominal sizes are expressed at (they scale
#: proportionally for other widths).
CARD_REFERENCE_WIDTH = 1640

#: The copyright line's face (vendored variable font, SIL OFL).
FONT = FONTS_DIR / "Oswald.ttf"

#: Cap on the threads one stage (the encode, the compositing) may take.
MAX_STAGE_THREADS = 16

#: The unity-viewer's default output size, mirrored here so the
#: pipeline computes the scaled sizes explicitly instead of relying on
#: the viewer's implicit ones.
ITEM_VIEWER_WIDTH = 1024
ITEM_VIEWER_HEIGHT = 1024

#: The pack's material template: its two mask rectangles mark the
#: pack's back's (left) and front's (right) paste regions, composed on
#: the fly (see :mod:`nikke_reborn.pack`). The item is rendered from
#: the mesh textured with the finished material.
PACK_TEMPLATE = IMAGES_DIR / "CardPack_Material.png"
PACK_MATERIAL_NAME = "CardPack_Material.png"
PACK_ITEM_NAME = "CardPack_Item.png"
PACK_MESH = MESHES_DIR / "CardPackStatic_Mesh_low.obj"

#: The pack item's viewer configuration (model rotation and camera
#: zoom/pan, exported by the viewer's GUI).
PACK_CONFIG = MESHES_DIR / "CardPackStatic_Mesh_low.json"


#: The box's material template: its mask rectangles mark the paste
#: regions — front (blue), top (red) and side (green). The item is
#: rendered from the mesh textured with the finished material.
BOX_TEMPLATE = IMAGES_DIR / "CardBox_Material.png"
BOX_MATERIAL_NAME = "CardBox_Material.png"
BOX_ITEM_NAME = "CardBox_Item.png"
BOX_MESH = MESHES_DIR / "CardBox_Mesh.obj"

#: The box item's viewer configuration (model rotation and camera
#: zoom/pan, exported by the viewer's GUI).
BOX_CONFIG = MESHES_DIR / "CardBox_Mesh.json"
