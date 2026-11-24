"""Distill src/nikke_reborn/seed.bundle from the game's own asset files.

The seed is the container the bundler clones against: one prototype of
every object type a cardpack bundle emits. The cardpack scaffolding
(texture, sprite, default material, model mesh) and the poster
scaffolding (the game's three deco scripts with a vanilla
MonoBehaviour per script, the flip clip, the quad meshes, the
per-poster and shared materials, the guide texture) are each taken
from a vanilla deco and the game's assets. Objects keep the game's
serialization layout and the seed adopts the game's Unity version
string, so the bundles the bundler emits speak the exact version the
game's own assets use; the stream-based mesh and texture data is
materialized inline (the seed carries no resource stream) and the
PPtrs, the type table, and the script type table are rewired to the
seed-local clones. Run once, from the repo root:

    uv run python scripts/distill_seed.py
"""

import pathlib

import UnityPy
from UnityPy.classes import ChannelInfo, ComponentPair, PPtr, Quaternionf, Vector3f
from UnityPy.enums import BuildTarget, ClassIDType
from UnityPy.enums.BundleFile import ArchiveFlags
from UnityPy.files.BundleFile import BundleFile
from UnityPy.files.File import File
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.files.SerializedFile import (
    LocalSerializedObjectIdentifier,
    SerializedFile,
    SerializedFileHeader,
    SerializedType,
)
from UnityPy.helpers import TypeTreeHelper
from UnityPy.helpers.ContainerHelper import ContainerHelper
from UnityPy.helpers.Tpk import get_typetree_node
from UnityPy.helpers.TypeTreeNode import TypeTreeNode
from UnityPy.helpers.UnityVersion import UnityVersion
from UnityPy.streams import EndianBinaryReader, EndianBinaryWriter

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"
SEED = pathlib.Path("src/nikke_reborn/seed.bundle")


def game_path() -> pathlib.Path:
    """The game's data directory from ``.env`` (``GAME_PATH``)."""
    try:
        text = ENV_FILE.read_text(encoding="utf-8")
    except OSError:
        raise SystemExit(f"no {ENV_FILE.name} at the repo root (set GAME_PATH)")
    values = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, separator, value = line.partition("=")
            if separator:
                values[key.strip()] = value.strip()
    if not values.get("GAME_PATH"):
        raise SystemExit(".env is missing GAME_PATH")
    return pathlib.Path(values["GAME_PATH"])

SCRIPT_INDEX = {"ShelfMoveStateValidArea": 0, "InteractableDecoration": 1, "DashedLine": 2}
MONO_NAMES = {
    "InteractableDecoration": "__proto_poster_mono_interactable",
    "ShelfMoveStateValidArea": "__proto_poster_mono_valid_area",
    "DashedLine": "__proto_poster_mono_dashed_line",
}
CARDPACK_CHANNELS = (
    ChannelInfo(stream=0, offset=0, format=0, dimension=3),
    ChannelInfo(stream=0, offset=12, format=0, dimension=3),
    ChannelInfo(stream=0, offset=24, format=0, dimension=4),
    ChannelInfo(stream=0, offset=0, format=0, dimension=0),
    ChannelInfo(stream=0, offset=40, format=0, dimension=2),
) + (ChannelInfo(stream=0, offset=0, format=0, dimension=0),) * 9


def load_file(path):
    environment = UnityPy.load(str(path))
    file = environment.file
    if hasattr(file, "objects"):
        return environment, file
    return environment, next(f for f in file.files.values() if hasattr(f, "objects"))


def build_base():
    bundle = BundleFile.__new__(BundleFile)
    File.__init__(bundle, name="seed.base")
    bundle.signature = "UnityFS"
    bundle.version = 8
    bundle.version_player = "5.x.x"
    bundle.version_engine = "2021.3.38f1"
    bundle.dataflags = ArchiveFlags(194)
    bundle._uses_block_alignment = True

    header = SerializedFileHeader.__new__(SerializedFileHeader)
    header.metadata_size = 0
    header.file_size = 0
    header.version = 22
    header.data_offset = 0
    header.endian = "<"
    header.reserved = b"\x00\x00\x00"

    serialized_file = SerializedFile.__new__(SerializedFile)
    archive_name = "CAB-c2dd6717b87fc9677f57f07a83cf863d"
    File.__init__(serialized_file, parent=bundle, name=archive_name)
    serialized_file.flags = 4
    serialized_file.header = header
    serialized_file.unity_version = "6000.0.66f2"
    serialized_file.version = UnityVersion.from_str("6000.0.66f2")
    serialized_file._m_target_platform = 19
    serialized_file.target_platform = BuildTarget(19)
    serialized_file._enable_type_tree = True
    serialized_file.big_id_enabled = 0
    serialized_file.unknown = 0
    serialized_file.userInformation = ""
    serialized_file.types = []
    serialized_file.script_types = []
    serialized_file.externals = []
    serialized_file.ref_types = []
    serialized_file.objects = {}
    serialized_file._cache = {}
    serialized_file.assetbundle = None
    serialized_file._container = ContainerHelper([])

    bundle.files[archive_name] = serialized_file
    return bundle, serialized_file


def find(sf, type_name, name=None, prefix=None):
    for obj in sf.objects.values():
        if obj.type.name != type_name:
            continue
        own_name = obj.peek_name() or ""
        if name is not None and own_name != name:
            continue
        if prefix is not None and not own_name.startswith(prefix):
            continue
        return obj
    wanted = name if name is not None else f"{prefix}*"
    raise SystemExit(f"no {type_name} named {wanted!r}")


def stream_bytes(resource, info):
    resource.seek(info.offset)
    return resource.read(info.size)


def zero_stream(info):
    info.path = ""
    info.offset = 0
    info.size = 0


def prepare_node(node):
    counter = [0]

    def walk(n, depth):
        n.m_TypeFlags = n.m_TypeFlags or 0
        n.m_RefTypeHash = 0
        n.m_Index = counter[0]
        counter[0] += 1
        if n.m_Version is None or n.m_Version == 0:
            n.m_Version = 11 if depth == 0 else 1
        for child in n.m_Children:
            walk(child, depth + 1)

    walk(node, 0)


def pptr_node(level, name, type_name, flag=0, child_flag=8388609):
    return [
        {
            "m_Level": level,
            "m_Type": f"PPtr<{type_name}>",
            "m_Name": name,
            "m_ByteSize": 12,
            "m_MetaFlag": flag,
        },
        {
            "m_Level": level + 1,
            "m_Type": "int",
            "m_Name": "m_FileID",
            "m_ByteSize": 4,
            "m_MetaFlag": child_flag,
        },
        {
            "m_Level": level + 1,
            "m_Type": "SInt64",
            "m_Name": "m_PathID",
            "m_ByteSize": 8,
            "m_MetaFlag": child_flag,
        },
    ]


def bool_node(name):
    return {
        "m_Level": 1,
        "m_Type": "UInt8",
        "m_Name": name,
        "m_ByteSize": 1,
        "m_MetaFlag": 16640,
    }


def int_node(name):
    return {
        "m_Level": 1,
        "m_Type": "int",
        "m_Name": name,
        "m_ByteSize": 4,
        "m_MetaFlag": 0,
    }


def pptr_vector(name, element_type):
    return [
        {
            "m_Level": 1,
            "m_Type": "vector",
            "m_Name": name,
            "m_ByteSize": -1,
            "m_MetaFlag": 0,
        },
        {
            "m_Level": 2,
            "m_Type": "Array",
            "m_Name": "Array",
            "m_ByteSize": -1,
            "m_MetaFlag": 0,
            "m_TypeFlags": 1,
        },
        {"m_Level": 3, "m_Type": "int", "m_Name": "size", "m_ByteSize": 4, "m_MetaFlag": 0},
        {
            "m_Level": 3,
            "m_Type": f"PPtr<${element_type}>",
            "m_Name": "data",
            "m_ByteSize": 12,
            "m_MetaFlag": 0,
        },
        {
            "m_Level": 4,
            "m_Type": "int",
            "m_Name": "m_FileID",
            "m_ByteSize": 4,
            "m_MetaFlag": 8388609,
        },
        {
            "m_Level": 4,
            "m_Type": "SInt64",
            "m_Name": "m_PathID",
            "m_ByteSize": 8,
            "m_MetaFlag": 8388609,
        },
    ]


def int_vector(name):
    return [
        {
            "m_Level": 1,
            "m_Type": "vector",
            "m_Name": name,
            "m_ByteSize": -1,
            "m_MetaFlag": 32768,
        },
        {
            "m_Level": 2,
            "m_Type": "Array",
            "m_Name": "Array",
            "m_ByteSize": -1,
            "m_MetaFlag": 16384,
            "m_TypeFlags": 1,
        },
        {"m_Level": 3, "m_Type": "int", "m_Name": "size", "m_ByteSize": 4, "m_MetaFlag": 0},
        {"m_Level": 3, "m_Type": "int", "m_Name": "data", "m_ByteSize": 4, "m_MetaFlag": 0},
    ]


def monobehaviour_header():
    return [
        {
            "m_Level": 0,
            "m_Type": "MonoBehaviour",
            "m_Name": "MonoBehaviour Base",
            "m_ByteSize": -1,
            "m_MetaFlag": 32768,
        },
        {
            "m_Level": 1,
            "m_Type": "PPtr<GameObject>",
            "m_Name": "m_GameObject",
            "m_ByteSize": 12,
            "m_MetaFlag": 65,
        },
        {
            "m_Level": 2,
            "m_Type": "int",
            "m_Name": "m_FileID",
            "m_ByteSize": 4,
            "m_MetaFlag": 65,
        },
        {
            "m_Level": 2,
            "m_Type": "SInt64",
            "m_Name": "m_PathID",
            "m_ByteSize": 8,
            "m_MetaFlag": 65,
        },
        {
            "m_Level": 1,
            "m_Type": "UInt8",
            "m_Name": "m_Enabled",
            "m_ByteSize": 1,
            "m_MetaFlag": 16641,
        },
        {
            "m_Level": 1,
            "m_Type": "PPtr<MonoScript>",
            "m_Name": "m_Script",
            "m_ByteSize": 12,
            "m_MetaFlag": 0,
        },
        {
            "m_Level": 2,
            "m_Type": "int",
            "m_Name": "m_FileID",
            "m_ByteSize": 4,
            "m_MetaFlag": 8388609,
        },
        {
            "m_Level": 2,
            "m_Type": "SInt64",
            "m_Name": "m_PathID",
            "m_ByteSize": 8,
            "m_MetaFlag": 8388609,
        },
        {
            "m_Level": 1,
            "m_Type": "string",
            "m_Name": "m_Name",
            "m_ByteSize": -1,
            "m_MetaFlag": 557057,
        },
        {
            "m_Level": 2,
            "m_Type": "Array",
            "m_Name": "Array",
            "m_ByteSize": -1,
            "m_MetaFlag": 540673,
            "m_TypeFlags": 1,
        },
        {
            "m_Level": 3,
            "m_Type": "int",
            "m_Name": "size",
            "m_ByteSize": 4,
            "m_MetaFlag": 524289,
        },
        {
            "m_Level": 3,
            "m_Type": "char",
            "m_Name": "data",
            "m_ByteSize": 1,
            "m_MetaFlag": 524289,
        },
    ]


def mono_tree(name):
    if name == "InteractableDecoration":
        return TypeTreeNode.from_list(
            monobehaviour_header()
            + [
                int_node("m_ObjectType"),
                int_node("m_DecoObjectType"),
                *pptr_node(1, "m_HighlightGameObj", "$GameObject"),
                *pptr_node(1, "m_NavMeshCut", "$GameObject"),
                *pptr_node(1, "m_Mesh", "$MeshRenderer"),
                *pptr_node(1, "m_CullingCheckMesh", "$MeshRenderer"),
                *pptr_node(1, "m_SkinMesh", "$SkinnedMeshRenderer"),
                *pptr_vector("m_OverrideMeshDataList", "Mesh"),
                {
                    "m_Level": 1,
                    "m_Type": "float",
                    "m_Name": "m_HighlightOutlineWidth",
                    "m_ByteSize": 4,
                    "m_MetaFlag": 0,
                },
                bool_node("m_IsGenericObject"),
                bool_node("m_CanPickupMoveObject"),
                bool_node("m_CanBoxUpObject"),
                bool_node("m_CanScanByCounter"),
                bool_node("m_PlaceObjectInShopOnly"),
                bool_node("m_PlaceObjectInWarehouseOnly"),
                bool_node("m_AllowPlaceObjectNearShop"),
                bool_node("m_IsDecorationVertical"),
                bool_node("m_CanFlip"),
                bool_node("m_CanCatStandOnThis"),
                *pptr_node(1, "m_PickupObjectMesh", "$MeshFilter"),
                *pptr_node(1, "m_MoveStateValidArea", "$Transform"),
                *pptr_node(1, "m_ShelfMoveStateValidArea", "$ShelfMoveStateValidArea"),
                *pptr_node(1, "m_BoxCollider", "$BoxCollider"),
                *pptr_node(1, "m_OverrideCatStandAreaCollider", "$BoxCollider"),
                *pptr_vector("m_BoxColliderList", "BoxCollider"),
                *int_vector("m_GameActionInputDisplayList"),
                *int_vector("m_ControllerOnlyGameActionInputDisplayList"),
                bool_node("m_SoftPlaceObjectSFX"),
                *pptr_node(1, "m_SpecialMesh", "$MeshRenderer"),
                int_node("m_SpecialIndex"),
            ]
        )
    if name == "ShelfMoveStateValidArea":
        return TypeTreeNode.from_list(
            monobehaviour_header()
            + [bool_node("m_CanSnap"), *pptr_vector("m_SnapLocList", "Transform")]
        )
    if name == "DashedLine":
        return TypeTreeNode.from_list(
            monobehaviour_header()
            + [
                *pptr_node(1, "m_RendererHorizontal1", "$MeshRenderer"),
                *pptr_node(1, "m_RendererHorizontal2", "$MeshRenderer"),
                *pptr_node(1, "m_RendererVertical1", "$MeshRenderer"),
                *pptr_node(1, "m_RendererVertical2", "$MeshRenderer"),
            ]
        )
    raise SystemExit(f"no typetree for {name!r}")


def children(sf, transform):
    data = transform.parse_as_dict()
    result = []
    for child in data["m_Children"]:
        child_transform = sf.objects[child["m_PathID"]]
        go = sf.objects[child_transform.parse_as_dict()["m_GameObject"]["m_PathID"]]
        result.append((go, child_transform))
    return result


def components(sf, go):
    data = go.parse_as_dict()
    return [sf.objects[c["component"]["m_PathID"]] for c in data["m_Component"]]


def component(sf, go, type_name):
    return next(c for c in components(sf, go) if c.type.name == type_name)


class Distiller:
    def __init__(self, seed_sf, resource, game_version):
        self.seed_sf = seed_sf
        self.resource = resource
        self.game_version = game_version
        self.next_id = 2
        self.script_trees = {}

    def pptr(self, obj):
        return PPtr(m_FileID=0, m_PathID=obj.path_id if obj else 0, assetsfile=self.seed_sf)

    def type_id(self, src):
        wanted = src.serialized_type.script_type_index if src.class_id == 114 else None
        for index, entry in enumerate(self.seed_sf.types):
            if entry.class_id == src.class_id and (
                src.class_id != 114 or entry.script_type_index == wanted
            ):
                return index
        source = src.serialized_type
        entry = SerializedType.__new__(SerializedType)
        entry.class_id = source.class_id
        entry.is_stripped_type = source.is_stripped_type
        entry.script_type_index = source.script_type_index
        entry.script_id = source.script_id
        entry.old_type_hash = source.old_type_hash
        entry.type_dependencies = source.type_dependencies or ()
        if src.class_id == 114:
            entry.node = self.script_trees[wanted]
        else:
            entry.node = get_typetree_node(src.class_id, self.game_version)
        prepare_node(entry.node)
        self.seed_sf.types.append(entry)
        return len(self.seed_sf.types) - 1

    def clone(self, src):
        path_id = self.next_id
        self.next_id += 1
        type_id = self.type_id(src)
        raw = src.get_raw_data()
        obj = ObjectReader(
            assets_file=self.seed_sf,
            reader=EndianBinaryReader(raw, endian="<"),
            path_id=path_id,
            type_id=type_id,
            serialized_type=self.seed_sf.types[type_id],
            class_id=src.class_id,
            type=src.type,
            byte_start=0,
            byte_size=len(raw),
            is_destroyed=None,
            is_stripped=None,
        )
        obj.set_raw_data(raw)
        self.seed_sf.objects[path_id] = obj
        return obj

    def resync(self, obj):
        obj.reader = EndianBinaryReader(obj.data, endian="<")
        obj.byte_start = 0
        obj.byte_size = len(obj.data)


def manifest_bytes(version):
    node = get_typetree_node(ClassIDType.AssetBundle, version)
    value = {
        "m_Container": [],
        "m_MainAsset": {
            "preloadIndex": 0,
            "preloadSize": 0,
            "asset": {"m_FileID": 0, "m_PathID": 0},
        },
        "m_Name": "seed",
        "m_PreloadTable": [],
        "m_AssetBundleName": "",
        "m_ClassCompatibility": [],
        "m_ClassVersionMap": [],
        "m_Dependencies": [],
        "m_ExplicitDataLayout": 0,
        "m_IsStreamedSceneAssetBundle": False,
        "m_PathFlags": 7,
        "m_RuntimeCompatibility": 1,
        "m_SceneHashes": [],
        "m_ScriptCompatibility": [],
    }
    writer = EndianBinaryWriter(endian="<")
    TypeTreeHelper.write_typetree(value, node, writer, None)
    return writer.bytes


def deco(shared):
    for obj in shared.objects.values():
        if obj.type.name == "GameObject" and (obj.peek_name() or "").startswith(
            "Interactable_Poster"
        ):
            parts = components(shared, obj)
            if any(p.type.name == "BoxCollider" for p in parts) and any(
                p.type.name == "MonoBehaviour" for p in parts
            ):
                return obj, parts
    raise SystemExit("no poster deco")


def main():
    game = game_path()
    _, ggm = load_file(game / "globalgamemanagers.assets")
    _, shared = load_file(game / "sharedassets2.assets")
    version = shared.version

    seed_bundle, seed_sf = build_base()
    seed_sf.set_version(shared.unity_version)
    seed_sf.objects = {}
    seed_sf.types = []
    seed_sf.script_types = []
    seed_sf.externals = []
    seed_sf.ref_types = []
    resource = open(game / "sharedassets2.assets.resS", "rb")
    distiller = Distiller(seed_sf, resource, version)

    manifest_entry = SerializedType.__new__(SerializedType)
    manifest_entry.class_id = int(ClassIDType.AssetBundle)
    manifest_entry.is_stripped_type = False
    manifest_entry.script_type_index = -1
    manifest_entry.script_id = b"\x00" * 16
    manifest_entry.old_type_hash = b"\x00" * 16
    manifest_entry.node = get_typetree_node(ClassIDType.AssetBundle, version)
    prepare_node(manifest_entry.node)
    manifest_entry.type_dependencies = ()
    seed_sf.types.append(manifest_entry)
    manifest_raw = manifest_bytes(version)
    manifest = ObjectReader(
        assets_file=seed_sf,
        reader=EndianBinaryReader(manifest_raw, endian="<"),
        path_id=1,
        type_id=0,
        serialized_type=manifest_entry,
        class_id=int(ClassIDType.AssetBundle),
        type=ClassIDType.AssetBundle,
        byte_start=0,
        byte_size=len(manifest_raw),
        is_destroyed=None,
        is_stripped=None,
    )
    manifest.set_raw_data(manifest_raw)
    seed_sf.objects[1] = manifest

    root, root_parts = deco(shared)
    root_transform = component(shared, root, "Transform")
    trigger = component(shared, root, "BoxCollider")
    mono_interactable = component(shared, root, "MonoBehaviour")
    anim_go, anim_transform = next(
        c for c in children(shared, root_transform) if c[0].peek_name() == "AnimGrp"
    )
    animation = component(shared, anim_go, "Animation")
    art_go, art_transform = next(
        c for c in children(shared, anim_transform) if len(components(shared, c[0])) == 3
    )
    art_filter = component(shared, art_go, "MeshFilter")
    art_renderer = component(shared, art_go, "MeshRenderer")
    slab_go, slab_transform = next(
        c
        for c in children(shared, root_transform)
        if c[0].peek_name() == "MoveStateValidAreaGrp"
    )
    mono_valid_area = component(shared, slab_go, "MonoBehaviour")
    area_go, area_transform = next(
        c
        for c in children(shared, slab_transform)
        if c[0].peek_name() == "MoveStateValidArea"
    )
    snap_go, snap_transform = next(
        c for c in children(shared, area_transform) if c[0].peek_name() == "SnapLoc_L"
    )
    dashed_go, _ = next(
        c for c in children(shared, slab_transform) if c[0].peek_name() == "DashedLineGrp"
    )
    mono_dashed_line = component(shared, dashed_go, "MonoBehaviour")

    mono_sources = (
        (mono_interactable, "InteractableDecoration"),
        (mono_valid_area, "ShelfMoveStateValidArea"),
        (mono_dashed_line, "DashedLine"),
    )
    scripts = {
        name: distiller.clone(find(ggm, "MonoScript", name=name)) for name in SCRIPT_INDEX
    }
    distiller.script_trees = {
        src.serialized_type.script_type_index: mono_tree(name)
        for src, name in mono_sources
    }

    monos = {
        name: distiller.clone(src) for src, name in mono_sources
    }
    for name, mono in monos.items():
        data = mono.read()
        data.m_Name = MONO_NAMES[name]
        data.m_Script = distiller.pptr(scripts[name])
        data.m_GameObject = distiller.pptr(None)
        data.save()
        distiller.resync(mono)
    for name, mono in monos.items():
        seed_sf.types[mono.type_id].script_type_index = SCRIPT_INDEX[name]
    seed_sf.script_types = [
        LocalSerializedObjectIdentifier.__new__(LocalSerializedObjectIdentifier)
        for _ in SCRIPT_INDEX
    ]
    for identifier, name in zip(
        seed_sf.script_types, sorted(SCRIPT_INDEX, key=SCRIPT_INDEX.__getitem__)
    ):
        identifier.local_serialized_file_index = 0
        identifier.local_identifier_in_file = scripts[name].path_id

    mesh_square_src = find(shared, "Mesh", name="PosterSquare_Mesh")
    mesh_portrait_src = find(shared, "Mesh", name="Poster_Mesh")
    mesh_landscape_src = find(shared, "Mesh", name="PosterH_Mesh")
    mesh_guide_src = find(shared, "Mesh", name="Plane_1x1")
    poster_material_src = find(shared, "Material", prefix="MAT_Poster")
    material_placement_src = find(shared, "Material", name="MAT_PreviewTransparentGreen")
    material_guides_src = find(shared, "Material", name="MAT_Dashedline")
    guide_texture_src = find(shared, "Texture2D", name="T_DashedLine")

    shader_guides = distiller.clone(
        shared.objects[material_guides_src.read().m_Shader.m_PathID]
    )
    shader_placement = distiller.clone(
        shared.objects[material_placement_src.read().m_Shader.m_PathID]
    )
    display_pptr = poster_material_src.read().m_Shader
    resources = load_file(game / shared.externals[display_pptr.m_FileID - 1].path)[1]
    display_texture = distiller.clone(resources.objects[display_pptr.m_PathID])

    poster_array_material_src = find(shared, "Material", name="PosterMaterial")
    poster_shader_src = shared.objects[
        poster_array_material_src.read().m_Shader.m_PathID
    ]
    poster_shader_fallback = distiller.clone(
        shared.objects[
            next(
                dep.m_PathID
                for dep in poster_shader_src.read().m_Dependencies
                if dep.m_FileID == 0
            )
        ]
    )
    poster_shader = distiller.clone(poster_shader_src)
    poster_shader_data = poster_shader.read()
    poster_shader_data.m_Dependencies = [
        PPtr(
            m_FileID=dep.m_FileID,
            m_PathID=dep.m_PathID if dep.m_FileID else poster_shader_fallback.path_id,
            assetsfile=seed_sf,
        )
        for dep in poster_shader_src.read().m_Dependencies
    ]
    poster_shader_data.save()
    distiller.resync(poster_shader)

    main_texture = next(
        env.m_Texture
        for key, env in poster_material_src.read().m_SavedProperties.m_TexEnvs
        if key == "_MainTex"
    )
    texture_proto = distiller.clone(shared.objects[main_texture.m_PathID])
    sprite_proto = distiller.clone(find(resources, "Sprite", name="White1px"))

    child_object = distiller.clone(art_go)
    root_object = distiller.clone(snap_go)
    child_transform = distiller.clone(art_transform)
    root_transform_clone = distiller.clone(snap_transform)
    mesh_filter = distiller.clone(art_filter)
    mesh_renderer = distiller.clone(art_renderer)

    def materialize_mesh(src, name):
        obj = distiller.clone(src)
        data = obj.read()
        data.m_Name = name
        data.m_VertexData.m_DataSize = stream_bytes(resource, data.m_StreamData)
        zero_stream(data.m_StreamData)
        data.save()
        distiller.resync(obj)
        return obj

    default_mesh = materialize_mesh(mesh_guide_src, "default")
    data = default_mesh.read()
    data.m_VertexData.m_Channels = list(CARDPACK_CHANNELS)
    data.save()
    distiller.resync(default_mesh)
    mesh_square = materialize_mesh(mesh_square_src, "__proto_poster_mesh_square")
    mesh_portrait = materialize_mesh(mesh_portrait_src, "__proto_poster_mesh_portrait")
    mesh_landscape = materialize_mesh(mesh_landscape_src, "__proto_poster_mesh_landscape")
    mesh_guide = materialize_mesh(mesh_guide_src, "__proto_poster_mesh_guide")

    def materialize_texture(src, name):
        obj = distiller.clone(src)
        data = obj.read()
        data.m_Name = name
        data.image_data = stream_bytes(resource, data.m_StreamData)
        zero_stream(data.m_StreamData)
        data.save()
        distiller.resync(obj)
        return obj

    guide_texture = materialize_texture(guide_texture_src, "__proto_poster_guide_tex")

    def materialize_array(src, name):
        obj = distiller.clone(src)
        data = obj.read()
        data.m_Name = name
        data.image_data = b""
        data.m_DataSize = 0
        zero_stream(data.m_StreamData)
        data.save()
        distiller.resync(obj)
        return obj

    array_src = find(shared, "Texture2DArray", name="Posters")
    poster_array = materialize_array(array_src, "__proto_poster_array")

    def materialize_material(src, name, shader, texture=None):
        obj = distiller.clone(src)
        data = obj.read()
        data.m_Name = name
        data.m_Shader = distiller.pptr(shader)
        for key, env in data.m_SavedProperties.m_TexEnvs:
            if key == "_MainTex":
                env.m_Texture = distiller.pptr(texture)
        data.save()
        distiller.resync(obj)
        return obj

    def materialize_array_material(src, name, shader):
        obj = distiller.clone(src)
        data = obj.read()
        data.m_Name = name
        data.m_Shader = distiller.pptr(shader)
        for key, env in data.m_SavedProperties.m_TexEnvs:
            if key == "_MainTexArray":
                env.m_Texture = distiller.pptr(None)
        data.save()
        distiller.resync(obj)
        return obj

    default_material = materialize_material(
        poster_material_src, "defaultMat", display_texture
    )
    poster_material = materialize_array_material(
        poster_array_material_src, "__proto_poster_material", poster_shader
    )
    material_placement = materialize_material(
        material_placement_src, "__proto_poster_material_placement", shader_placement
    )
    material_guides = materialize_material(
        material_guides_src,
        "__proto_poster_material_guides",
        shader_guides,
        guide_texture,
    )

    child_data = child_object.read()
    child_data.m_Component = [
        ComponentPair(component=distiller.pptr(component))
        for component in (child_transform, mesh_filter, mesh_renderer)
    ]
    child_data.m_Layer = 0
    child_data.m_IsActive = True
    child_data.save()
    distiller.resync(child_object)

    root_data = root_object.read()
    root_data.m_Component = [ComponentPair(component=distiller.pptr(root_transform_clone))]
    root_data.m_Layer = 0
    root_data.m_IsActive = True
    root_data.save()
    distiller.resync(root_object)

    def wire_transform(transform, owner, father, children):
        data = transform.read()
        data.m_GameObject = distiller.pptr(owner)
        data.m_Father = distiller.pptr(father)
        data.m_Children = [distiller.pptr(child) for child in children]
        data.m_LocalPosition = Vector3f(0.0, 0.0, 0.0)
        data.m_LocalRotation = Quaternionf(0.0, 0.0, 0.0, 1.0)
        data.m_LocalScale = Vector3f(1.0, 1.0, 1.0)
        data.save()
        distiller.resync(transform)

    wire_transform(child_transform, child_object, root_transform_clone, ())
    wire_transform(root_transform_clone, root_object, None, (child_transform,))

    filter_data = mesh_filter.read()
    filter_data.m_GameObject = distiller.pptr(child_object)
    filter_data.m_Mesh = distiller.pptr(default_mesh)
    filter_data.save()
    distiller.resync(mesh_filter)

    renderer_data = mesh_renderer.read()
    renderer_data.m_GameObject = distiller.pptr(child_object)
    renderer_data.m_Materials = [distiller.pptr(default_material)]
    renderer_data.m_CastShadows = 1
    renderer_data.m_DynamicOccludee = 1
    renderer_data.m_LightProbeUsage = 1
    renderer_data.m_MotionVectors = 1
    renderer_data.m_ReflectionProbeUsage = 1
    renderer_data.m_ReceiveShadows = 1
    renderer_data.save()
    distiller.resync(mesh_renderer)

    flip_src = shared.objects[animation.read().m_Animation.m_PathID]
    flip = distiller.clone(flip_src)
    data = flip.read()
    data.m_Name = "__proto_poster_flip"
    data.save()
    distiller.resync(flip)
    animation = distiller.clone(animation)
    data = animation.read()
    data.m_Animation = distiller.pptr(flip)
    data.m_Animations = [distiller.pptr(flip)]
    data.m_GameObject = distiller.pptr(None)
    data.save()
    distiller.resync(animation)
    trigger = distiller.clone(trigger)
    data = trigger.read()
    data.m_GameObject = distiller.pptr(None)
    data.save()
    distiller.resync(trigger)

    seed_sf.externals = [
        external
        for external in shared.externals
        if external.path == "Resources/unity_builtin_extra"
    ]
    seed_sf.mark_changed()
    SEED.write_bytes(seed_bundle.save(packer="lz4"))

    verify(SEED)
    print(
        f"wrote {SEED} ({SEED.stat().st_size:,} bytes, {len(seed_sf.objects)} objects)"
    )


def verify(seed):
    _, sf = load_file(seed)
    for obj in sf.objects.values():
        original = obj.get_raw_data()
        obj.save_typetree(obj.read())
        if obj.get_raw_data() != original:
            raise SystemExit(f"round trip mismatch at pathID {obj.path_id}")
    print(f"verified {len(sf.objects)} objects byte-exact")


if __name__ == "__main__":
    main()
