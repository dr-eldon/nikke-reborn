"""Build Unity AssetBundles without Unity.

The bundles are consumed by TCG Card Shop Simulator: the game resolves
assets by name/container path, so a structurally faithful bundle loads
the same. UnityPy can't author a SerializedFile from nothing, so we
build on top of ``seed.bundle`` — a distillation of a real
Unity-built bundle holding the container scaffolding, the embedded
built-in Standard shader, and one prototype of each object type. We
clone those prototypes (so Unity's field defaults come along for free)
and override only what matters: name, image, size, and the PPtr wiring
between them."""

from __future__ import annotations

import concurrent.futures
import dataclasses
import hashlib
import importlib.resources
import math
import os
import pathlib
import struct
import sys

import UnityPy
from PIL import Image
from UnityPy.enums import TextureFormat
from UnityPy.export import Texture2DConverter
from UnityPy.files.BundleFile import BundleFile
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.files.SerializedFile import SerializedFile

# The seed bundle (see the module docstring; distilled by
# scripts/distill_seed.py).
SEED = importlib.resources.files(__package__) / "seed.bundle"

# The GPU format the original Builder baked in; UnityPy encodes it via
# etcpak.compress_bc7.
TEXTURE_FORMAT = TextureFormat.BC7

# The sprite import default Unity used (pixels per unit); the pivot and
# extrude come from the prototype unchanged.
SPRITE_PIXELS_TO_UNITS = 100.0

# The suffix that marks a texture that also gets a Standard material
# (Texture2D + Material); every other PNG is Texture2D + Sprite.
MATERIAL_SUFFIX = "_Material"

POSTER_SUFFIX = "_Art"

POSTER_SCALE = 3.0683

BUILTIN_SHADER_FILE_ID = 2
BUILTIN_SHADER_PATH_ID = 6
BUILTIN_CUBE_MESH_FILE_ID = 1
BUILTIN_CUBE_MESH_PATH_ID = 10202
BUILTIN_DEFAULT_RESOURCES_GUID = b"\x00" * 8 + b"\x0e\x00\x00\x00" + b"\x00" * 4

# The private PNG chunk `extract` stashes an already-encoded source
# texture in (format + dimensions + raw bytes), so `build` can embed it
# untouched — avoiding a lossy decode -> PNG -> re-encode round-trip.
RAW_TEXTURE_CHUNK = b"nkTx"


def pack_raw_texture(
    texture_format: int, width: int, height: int, data: bytes
) -> bytes:
    return struct.pack("<iii", int(texture_format), width, height) + data


def read_raw_texture(png: pathlib.Path):
    """(format, width, height, data) from a PNG's raw-texture chunk, or
    None."""
    blob = png.read_bytes()
    if blob[:8] != b"\x89PNG\r\n\x1a\n":
        return None

    offset = 8
    while offset + 12 <= len(blob):
        (length,) = struct.unpack(">I", blob[offset : offset + 4])
        if blob[offset + 4 : offset + 8] == RAW_TEXTURE_CHUNK:
            payload = blob[offset + 8 : offset + 8 + length]
            texture_format, width, height = struct.unpack("<iii", payload[:12])
            return texture_format, width, height, payload[12:]
        offset += 12 + length
    return None


def compress_texture(image: Image.Image) -> tuple[int, bytes]:
    """Compress an RGBA image to GPU texture bytes the way Unity's
    importer does.

    Block formats need both dimensions to be multiples of 4; otherwise
    Unity falls back to uncompressed RGBA32, so match that — forcing BC7
    would store a texture Unity never produces (and lose quality: RGBA32
    is lossless). The encoding is delegated to UnityPy's
    Texture2DConverter, so the bytes are identical to what
    ``Texture2D.set_image`` would write for the same image."""
    width, height = image.size
    fmt = (
        TEXTURE_FORMAT if (width % 4 == 0 and height % 4 == 0) else TextureFormat.RGBA32
    )
    data, _ = Texture2DConverter.image_to_texture2d(image, fmt)
    return int(fmt), data


def compress_mipmapped(image: Image.Image) -> tuple[int, int, int, int, bytes]:
    """Compress an RGBA image with its full mip chain, the way the
    reference stores its room props (poster art, box / sleeve
    materials). Card art and icons stay single-mip.

    Level 0 is `image`; each further level halves both dimensions
    (floor, minimum 1) with a box filter — the same sizes the GPU
    derives from the stored width/height. Block levels are padded to
    the 4×4 block grid by the encoder, so a 103×128 level stores
    104×128 of BC7 while the stored sizes stay the true ones. Levels
    are concatenated mip 0 first. Returns
    (format, width, height, mip_count, bytes)."""
    width, height = image.size
    fmt = (
        TEXTURE_FORMAT if (width % 4 == 0 and height % 4 == 0) else TextureFormat.RGBA32
    )
    data, _ = Texture2DConverter.image_to_texture2d(image, fmt)
    levels = [data]
    level = image
    level_width, level_height = width, height
    while level_width > 1 or level_height > 1:
        level_width, level_height = max(1, level_width // 2), max(1, level_height // 2)
        level = level.resize((level_width, level_height), Image.BOX)
        data, _ = Texture2DConverter.image_to_texture2d(level, fmt)
        levels.append(data)
    return int(fmt), width, height, len(levels), b"".join(levels)


# Unity's imported-model mesh vertex layout (position, normal, tangent,
# uv0); matches the seed's mesh prototype.
VERTEX_STRIDE = 48


def _parse_obj(path: pathlib.Path):
    positions, normals, uvs, faces = [], [], [], []
    for line in path.read_text().splitlines():
        tag, _, rest = line.partition(" ")
        if tag == "v":
            x, y, z = rest.split()[:3]
            positions.append((float(x), float(y), float(z)))
        elif tag == "vn":
            x, y, z = rest.split()[:3]
            normals.append((float(x), float(y), float(z)))
        elif tag == "vt":
            u, v = rest.split()[:2]
            uvs.append((float(u), float(v)))
        elif tag == "f":
            face = []
            for token in rest.split():
                v, _, vt_vn = token.partition("/")
                vt, _, vn = vt_vn.partition("/")
                face.append(
                    (
                        int(v) - 1,
                        int(vt) - 1 if vt else None,
                        int(vn) - 1 if vn else None,
                    )
                )
            faces.append(face)
    return positions, normals, uvs, faces


def build_mesh_buffers(path: pathlib.Path):
    """Convert a Wavefront .obj to Unity mesh buffers.

    Returns (vertex_count, vertex_bytes, index_bytes, index_count,
    index_format, center, extent). Unity's importer converts the .obj's
    right-handed Y-up space to its own left-handed system: we negate X
    and reverse triangle winding to match. Tangents are a placeholder
    (figurine materials sample only albedo). NOTE: the axis/winding is
    the one thing that needs an in-game check; flip it here if a
    figurine renders mirrored/inside-out."""
    positions, normals, uvs, faces = _parse_obj(path)

    seen: dict = {}
    pos, nrm, uv = [], [], []

    def vertex(key):
        if key in seen:
            return seen[key]
        vi, ti, ni = key
        index = len(pos)
        x, y, z = positions[vi]
        pos.append((-x, y, z))
        nx, ny, nz = normals[ni] if ni is not None else (0.0, 0.0, 1.0)
        nrm.append((-nx, ny, nz))
        uv.append(uvs[ti] if ti is not None else (0.0, 0.0))
        seen[key] = index
        return index

    indices: list = []
    for face in faces:
        corner = [vertex(key) for key in face]
        for i in range(
            1, len(corner) - 1
        ):  # fan-triangulate; reversed winding for the X flip
            indices += (corner[0], corner[i + 1], corner[i])

    vertex_bytes = bytearray()
    for i in range(len(pos)):
        vertex_bytes += struct.pack("<3f", *pos[i])
        vertex_bytes += struct.pack("<3f", *nrm[i])
        vertex_bytes += struct.pack("<4f", 1.0, 0.0, 0.0, -1.0)  # placeholder tangent
        vertex_bytes += struct.pack("<2f", *uv[i])

    if len(pos) <= 65535:
        index_bytes, index_format = struct.pack(f"<{len(indices)}H", *indices), 0
    else:
        index_bytes, index_format = struct.pack(f"<{len(indices)}I", *indices), 1

    xs, ys, zs = ([p[a] for p in pos] for a in range(3))
    center = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2)
    extent = ((max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2, (max(zs) - min(zs)) / 2)
    return (
        len(pos),
        bytes(vertex_bytes),
        index_bytes,
        len(indices),
        index_format,
        center,
        extent,
    )


@dataclasses.dataclass
class Prototypes:
    """Known-good objects lifted from the reference bundle, used as clone templates."""

    texture: ObjectReader
    sprite: ObjectReader
    material: ObjectReader  # a Standard-shader material (`defaultMat`)
    shader_path_id: int  # the embedded built-in Standard shader
    poster_shader_path_id: (
        int  # the CRYPTION overlay shader PosterPlacement/PosterGuides bind to
    )
    # A figurine model: root GameObject -> child GameObject (MeshFilter + MeshRenderer),
    # a Transform each, and the Mesh.
    mesh: ObjectReader
    mesh_filter: ObjectReader
    mesh_renderer: ObjectReader
    child_object: ObjectReader
    root_object: ObjectReader
    child_transform: ObjectReader
    root_transform: ObjectReader
    poster_mesh_square: ObjectReader
    poster_mesh_portrait: ObjectReader
    poster_mesh_landscape: ObjectReader
    poster_mesh_guide: ObjectReader
    poster_script_interactable: ObjectReader
    poster_script_valid_area: ObjectReader
    poster_script_dashed_line: ObjectReader
    poster_mono_interactable: ObjectReader
    poster_mono_valid_area: ObjectReader
    poster_mono_dashed_line: ObjectReader
    poster_trigger: ObjectReader
    poster_animation: ObjectReader
    poster_flip: ObjectReader
    poster_material: ObjectReader
    poster_material_placement: ObjectReader
    poster_material_guides: ObjectReader
    poster_guide_texture: ObjectReader


class Bundle:
    """A single AssetBundle under construction, templated from the reference bundle."""

    def __init__(self, name: str):
        self._env = UnityPy.load(SEED.read_bytes())
        # The seed is a Unity-built AssetBundle, so its top-level file is a
        # BundleFile (not a bare SerializedFile or raw reader).
        bundle_file = self._env.file
        assert isinstance(bundle_file, BundleFile)
        self._bundle_file = bundle_file
        self._sf: SerializedFile = next(
            f for f in self._bundle_file.files.values() if isinstance(f, SerializedFile)
        )
        self._protos = self._extract_prototypes()
        self._manifest = self._find(lambda o: o.type.name == "AssetBundle")

        # Assign PathIDs that can't collide with the objects we keep
        # (shader + manifest).
        self._next_path_id = max(self._sf.objects) + 1
        self._deco_object_type = 0

        # Start from a clean slate: keep the manifest, the Standard
        # shader, and the poster scaffolding's shared constants (one
        # copy per bundle, as in the reference), drop everything else.
        poster = self._protos
        keep = {
            self._manifest.path_id,
            poster.shader_path_id,
            poster.poster_material_placement.read().m_Shader.m_PathID,
            poster.poster_flip.path_id,
            poster.poster_guide_texture.path_id,
            poster.poster_material_placement.path_id,
            poster.poster_material_guides.path_id,
            poster.poster_mesh_square.path_id,
            poster.poster_mesh_portrait.path_id,
            poster.poster_mesh_landscape.path_id,
            poster.poster_mesh_guide.path_id,
            poster.poster_script_interactable.path_id,
            poster.poster_script_valid_area.path_id,
            poster.poster_script_dashed_line.path_id,
        }
        self._sf.objects = {
            path_id: obj for path_id, obj in self._sf.objects.items() if path_id in keep
        }
        for obj, obj_name in (
            (poster.poster_flip, "PosterFlip"),
            (poster.poster_guide_texture, "PosterGuideTexture"),
            (poster.poster_material_placement, "PosterPlacement"),
            (poster.poster_material_guides, "PosterGuides"),
            (poster.poster_mesh_square, "PosterSquareMesh"),
            (poster.poster_mesh_portrait, "PosterPortraitMesh"),
            (poster.poster_mesh_landscape, "PosterLandscapeMesh"),
            (poster.poster_mesh_guide, "PosterGuideMesh"),
        ):
            data = obj.read()
            data.m_Name = obj_name
            if obj.type.name == "Mesh":
                data.m_KeepIndices = False
                data.m_KeepVertices = False
            if obj is poster.poster_material_guides:
                for key, tex_env in data.m_SavedProperties.m_TexEnvs:
                    if key == "_MainTex":
                        tex_env.m_Texture = self._pptr(poster.poster_guide_texture)
            data.save()

        # Rebuild the bundle's file table with one entry: our
        # SerializedFile under a unique internal name. Two things happen
        # here: the seed's `.resS` resource stream is dropped (our
        # textures store data inline, and carrying the stream would bloat
        # the bundle), and the `CAB-<hash>` archive name is made unique
        # per bundle — Unity keys loaded SerializedFiles by that name and
        # silently refuses to load a second bundle whose name it already
        # holds. blake2b is just a stable Unity-style identifier here,
        # not a security hash.
        cab = "CAB-" + hashlib.blake2b(name.encode(), digest_size=16).hexdigest()
        self._bundle_file.files = {cab: self._sf}

        self._name = name
        self._references_external = False
        self._container: list[tuple[str, ObjectReader, list[ObjectReader]]] = []

    def _find(self, predicate):
        return next(o for o in self._sf.objects.values() if predicate(o))

    def _proto(self, type_name: str, name: str) -> ObjectReader:
        """The poster scaffolding prototype (scripts/distill_seed.py), by name."""
        return self._find(lambda o: o.type.name == type_name and o.peek_name() == name)

    def _extract_prototypes(self) -> Prototypes:
        texture = self._find(lambda o: o.type.name == "Texture2D")
        sprite = self._find(lambda o: o.type.name == "Sprite")
        # `defaultMat`: the one reference material bound to the built-in
        # Standard shader.
        material = self._find(
            lambda o: o.type.name == "Material" and o.read().m_Name == "defaultMat"
        )
        shader_path_id = material.read().m_Shader.m_PathID

        mesh = self._find(lambda o: o.type.name == "Mesh")
        mesh_filter = self._find(lambda o: o.type.name == "MeshFilter")
        mesh_renderer = self._find(lambda o: o.type.name == "MeshRenderer")
        # The child carries the mesh (Transform + MeshFilter +
        # MeshRenderer); the root just parents it (Transform only) and is
        # the asset the game loads by name.
        objects = [o for o in self._sf.objects.values() if o.type.name == "GameObject"]
        child_object = next(o for o in objects if len(o.read().m_Component) == 3)
        root_object = next(o for o in objects if len(o.read().m_Component) == 1)
        child_transform = self._find(
            lambda o: (
                o.type.name == "Transform"
                and o.read().m_GameObject.m_PathID == child_object.path_id
            )
        )
        root_transform = self._find(
            lambda o: (
                o.type.name == "Transform"
                and o.read().m_GameObject.m_PathID == root_object.path_id
            )
        )
        poster_mesh_square = self._proto("Mesh", "__proto_poster_mesh_square")
        poster_mesh_portrait = self._proto("Mesh", "__proto_poster_mesh_portrait")
        poster_mesh_landscape = self._proto("Mesh", "__proto_poster_mesh_landscape")
        poster_mesh_guide = self._proto("Mesh", "__proto_poster_mesh_guide")
        poster_script_interactable = self._proto("MonoScript", "InteractableDecoration")
        poster_script_valid_area = self._proto("MonoScript", "ShelfMoveStateValidArea")
        poster_script_dashed_line = self._proto("MonoScript", "DashedLine")
        poster_mono_interactable = self._proto(
            "MonoBehaviour", "__proto_poster_mono_interactable"
        )
        poster_mono_valid_area = self._proto(
            "MonoBehaviour", "__proto_poster_mono_valid_area"
        )
        poster_mono_dashed_line = self._proto(
            "MonoBehaviour", "__proto_poster_mono_dashed_line"
        )
        poster_trigger = self._find(lambda o: o.type.name == "BoxCollider")
        poster_animation = self._find(lambda o: o.type.name == "Animation")
        poster_flip = self._proto("AnimationClip", "__proto_poster_flip")
        poster_material = self._proto("Material", "__proto_poster_material")
        poster_material_placement = self._proto(
            "Material", "__proto_poster_material_placement"
        )
        poster_shader_path_id = poster_material_placement.read().m_Shader.m_PathID
        poster_material_guides = self._proto(
            "Material", "__proto_poster_material_guides"
        )
        poster_guide_texture = self._proto("Texture2D", "__proto_poster_guide_tex")
        return Prototypes(
            texture,
            sprite,
            material,
            shader_path_id,
            poster_shader_path_id,
            mesh,
            mesh_filter,
            mesh_renderer,
            child_object,
            root_object,
            child_transform,
            root_transform,
            poster_mesh_square,
            poster_mesh_portrait,
            poster_mesh_landscape,
            poster_mesh_guide,
            poster_script_interactable,
            poster_script_valid_area,
            poster_script_dashed_line,
            poster_mono_interactable,
            poster_mono_valid_area,
            poster_mono_dashed_line,
            poster_trigger,
            poster_animation,
            poster_flip,
            poster_material,
            poster_material_placement,
            poster_material_guides,
            poster_guide_texture,
        )

    def _clone(self, proto: ObjectReader) -> ObjectReader:
        path_id = self._next_path_id
        self._next_path_id += 1

        clone = ObjectReader(
            assets_file=self._sf,
            reader=proto.reader,
            path_id=path_id,
            type_id=proto.type_id,
            serialized_type=proto.serialized_type,
            class_id=proto.class_id,
            type=proto.type,
            byte_start=proto.byte_start,
            byte_size=proto.byte_size,
            is_destroyed=proto.is_destroyed,
            is_stripped=proto.is_stripped,
        )
        clone.set_raw_data(proto.get_raw_data())
        self._sf.objects[path_id] = clone
        return clone

    def _pptr(self, obj: ObjectReader | None):
        """A same-file PPtr (m_FileID = 0) pointing at one of our objects (or null)."""
        from UnityPy.classes import PPtr

        return PPtr(m_FileID=0, m_PathID=obj.path_id if obj else 0, assetsfile=self._sf)

    def _external_pptr(self, file_id: int, path_id: int):
        """A PPtr at a built-in object the game provides (file_id != 0)."""
        from UnityPy.classes import PPtr

        return PPtr(m_FileID=file_id, m_PathID=path_id, assetsfile=self._sf)

    def add_texture(
        self, name: str, image: Image.Image, mipmapped: bool = False
    ) -> ObjectReader:
        """Add a texture from a PIL image: compress it and embed.
        `mipmapped` stores the full mip chain (the room props the
        reference mipmaps); card art and icons stay single-mip."""
        if mipmapped:
            texture_format, width, height, mip_count, data = compress_mipmapped(image)
        else:
            texture_format, data = compress_texture(image)
            width, height = image.size
            mip_count = 1
        return self.add_raw_texture(
            name, texture_format, width, height, data, mip_count
        )

    def add_raw_texture(
        self,
        name: str,
        texture_format: int,
        width: int,
        height: int,
        data_bytes: bytes,
        mip_count: int = 1,
    ) -> ObjectReader:
        """Embed an already-encoded texture verbatim (no decode/re-encode,
        so lossless). `mip_count` is how many levels the data holds: 1 for
        a single level, the chain length for mipmapped data."""
        obj = self._clone(self._protos.texture)
        data = obj.read()
        data.m_Name = name
        data.m_Width = width
        data.m_Height = height
        data.image_data = data_bytes
        data.m_CompleteImageSize = len(data_bytes)
        data.m_TextureFormat = TextureFormat(texture_format)
        data.m_MipCount = mip_count
        data.m_IsReadable = False
        data.m_TextureSettings.m_FilterMode = 1  # Bilinear
        if data.m_StreamData is not None:
            data.m_StreamData.path = ""
            data.m_StreamData.offset = 0
            data.m_StreamData.size = 0
        data.save()
        return obj

    def add_sprite(self, name: str, texture: ObjectReader, size: tuple[int, int]):
        obj = self._clone(self._protos.sprite)
        data = obj.read()
        width, height = size
        data.m_Name = name
        data.m_Rect.width = data.m_RD.textureRect.width = float(width)
        data.m_Rect.height = data.m_RD.textureRect.height = float(height)
        data.m_PixelsToUnits = SPRITE_PIXELS_TO_UNITS
        data.m_RD.texture = self._pptr(texture)
        data.save()
        return obj

    def add_material(self, name: str, texture: ObjectReader):
        obj = self._clone(self._protos.material)
        data = obj.read()
        data.m_Name = name
        for key, tex_env in data.m_SavedProperties.m_TexEnvs:
            if key == "_MainTex":
                tex_env.m_Texture = self._pptr(texture)
        data.save()
        return obj

    def add_mesh(self, name: str, obj_path: pathlib.Path):
        """Build a figurine model from a .obj: a Mesh and the GameObject
        hierarchy Unity imports for it. Returns (root_object, objects) —
        the root GameObject is what the game loads by `name`; `objects`
        is the whole graph, for the container preload.

        The MeshRenderer gets a placeholder `defaultMat` (what Unity's
        importer assigns to a material-less .obj); the figurine's real
        material is a separate asset the loader applies at runtime, so it
        is not wired here."""
        mesh = self._clone(self._protos.mesh)
        mesh_filter = self._clone(self._protos.mesh_filter)
        mesh_renderer = self._clone(self._protos.mesh_renderer)
        child = self._clone(self._protos.child_object)
        root = self._clone(self._protos.root_object)
        child_transform = self._clone(self._protos.child_transform)
        root_transform = self._clone(self._protos.root_transform)
        default_material = self._clone(
            self._protos.material
        )  # already named "defaultMat"

        count, vertices, indices, index_count, index_format, center, extent = (
            build_mesh_buffers(obj_path)
        )
        data = mesh.read()
        data.m_Name = "default"
        data.m_IndexFormat = index_format
        data.m_VertexData.m_VertexCount = count
        data.m_VertexData.m_DataSize = vertices
        data.m_IndexBuffer = indices
        submesh = data.m_SubMeshes[0]
        submesh.firstByte = submesh.firstVertex = submesh.baseVertex = 0
        submesh.indexCount = index_count
        submesh.vertexCount = count
        submesh.topology = 0
        for box in (data.m_LocalAABB, submesh.localAABB):
            box.m_Center.x, box.m_Center.y, box.m_Center.z = center
            box.m_Extent.x, box.m_Extent.y, box.m_Extent.z = extent
        data.save()

        data = child.read()
        data.m_Name = "default"
        data.m_Component[0].component = self._pptr(child_transform)
        data.m_Component[1].component = self._pptr(mesh_filter)
        data.m_Component[2].component = self._pptr(mesh_renderer)
        data.save()

        data = child_transform.read()
        data.m_GameObject = self._pptr(child)
        data.m_Father = self._pptr(root_transform)
        data.m_Children = []
        data.save()

        data = mesh_filter.read()
        data.m_GameObject = self._pptr(child)
        data.m_Mesh = self._pptr(mesh)
        data.save()

        data = mesh_renderer.read()
        data.m_GameObject = self._pptr(child)
        data.m_Materials = [self._pptr(default_material)]
        data.save()

        data = root.read()
        data.m_Name = name
        data.m_Component[0].component = self._pptr(root_transform)
        data.save()

        data = root_transform.read()
        data.m_GameObject = self._pptr(root)
        data.m_Children = [self._pptr(child_transform)]
        data.m_Father = self._pptr(None)
        data.save()

        graph = [
            root,
            root_transform,
            child,
            child_transform,
            mesh_filter,
            mesh_renderer,
            mesh,
            default_material,
        ]
        return root, graph

    def add_poster(
        self,
        name: str,
        texture: ObjectReader,
    ):
        """Build one poster from the embedded art `texture`. `name` is the
        poster's base name (without the `_Art` texture suffix): the aspect
        is its final segment (square / portrait / landscape), the root
        becomes `<name>_Prefab`, and the per-poster material
        `<name>_Material`. The quad mesh is chosen by the aspect, and the
        game's deco scaffolding (grab trigger, flip animation, valid-area
        slab, dashed guide lines) wraps it. Returns
        (root_object, material, graph) — the root GameObject is what the
        game loads by name; `graph` is the whole poster plus its shared
        constants, for the container preload."""
        from UnityPy.classes import ComponentPair, PPtr

        aspect = name.rsplit("_")[-1].lower()

        mesh_proto, node_name = {
            "square": (self._protos.poster_mesh_square, "PosterSquare"),
            "portrait": (self._protos.poster_mesh_portrait, "Poster"),
            "landscape": (
                self._protos.poster_mesh_landscape,
                "PosterHorizontal",
            ),
        }[aspect]
        slab_position, slab_scale = {
            "square": ((0.0, 0.004, -0.0005), (0.44898, 0.007603, 0.43929)),
            "portrait": ((0.0, 0.0, -0.0005), (0.44898, 0.007603, 0.60661)),
            "landscape": ((0.0, 0.001, -0.0005), (0.60168, 0.007603, 0.44651)),
        }[aspect]
        self._references_external = True
        diagonal = math.sqrt(0.5)
        identity = (0.0, 0.0, 0.0, 1.0)
        rotation_x = (diagonal, 0.0, 0.0, diagonal)
        rotation_y = (0.0, diagonal, 0.0, diagonal)
        uniform = (POSTER_SCALE, POSTER_SCALE, POSTER_SCALE)
        preview = (POSTER_SCALE, POSTER_SCALE, 3.1)

        material = self._clone(self._protos.poster_material)
        data = material.read()
        data.m_Name = f"{name}_Material"
        for key, tex_env in data.m_SavedProperties.m_TexEnvs:
            if key == "_MainTex":
                tex_env.m_Texture = self._pptr(texture)
        data.save()

        def make_object(obj, object_name, layer, components, active: bool = True):
            data = obj.read()
            data.m_Name = object_name
            data.m_Layer = layer
            data.m_IsActive = active
            data.m_Component = [
                ComponentPair(component=self._pptr(component))
                for component in components
            ]
            data.save()

        def make_transform(obj, owner, father, children, position, rotation, scale):
            data = obj.read()
            data.m_GameObject = self._pptr(owner)
            data.m_Father = self._pptr(father)
            data.m_Children = [self._pptr(child) for child in children]
            data.m_LocalPosition.x, data.m_LocalPosition.y, data.m_LocalPosition.z = (
                position
            )
            (
                data.m_LocalRotation.x,
                data.m_LocalRotation.y,
                data.m_LocalRotation.z,
                data.m_LocalRotation.w,
            ) = rotation
            data.m_LocalScale.x, data.m_LocalScale.y, data.m_LocalScale.z = scale
            data.save()

        def wire(obj, owner):
            data = obj.read()
            data.m_GameObject = self._pptr(owner)
            return data

        def wire_filter(obj, owner, mesh):
            data = wire(obj, owner)
            data.m_Mesh = mesh if isinstance(mesh, PPtr) else self._pptr(mesh)
            data.save()

        def wire_renderer(obj, owner, mat, receive_shadows, overlay: bool = False):
            data = wire(obj, owner)
            data.m_Materials = [self._pptr(mat)]
            data.m_ReceiveShadows = receive_shadows
            if overlay:
                data.m_CastShadows = 0
                data.m_DynamicOccludee = 0
                data.m_LightProbeUsage = 0
                data.m_MotionVectors = 0
                data.m_ReflectionProbeUsage = 0
            data.save()

        root_go = self._clone(self._protos.root_object)
        anim_go = self._clone(self._protos.root_object)
        art_go = self._clone(self._protos.root_object)
        preview_go = self._clone(self._protos.root_object)
        slab_go = self._clone(self._protos.root_object)
        volume_go = self._clone(self._protos.root_object)
        snap_left_go = self._clone(self._protos.root_object)
        snap_right_go = self._clone(self._protos.root_object)
        snap_up_go = self._clone(self._protos.root_object)
        snap_down_go = self._clone(self._protos.root_object)
        dashed_go = self._clone(self._protos.root_object)
        line_goes = [self._clone(self._protos.root_object) for _ in (1, 2, 3, 4)]

        root_transform = self._clone(self._protos.root_transform)
        anim_transform = self._clone(self._protos.root_transform)
        art_transform = self._clone(self._protos.root_transform)
        preview_transform = self._clone(self._protos.root_transform)
        slab_transform = self._clone(self._protos.root_transform)
        volume_transform = self._clone(self._protos.root_transform)
        snap_left_transform = self._clone(self._protos.root_transform)
        snap_right_transform = self._clone(self._protos.root_transform)
        snap_up_transform = self._clone(self._protos.root_transform)
        snap_down_transform = self._clone(self._protos.root_transform)
        dashed_transform = self._clone(self._protos.root_transform)
        line_transforms = [
            self._clone(self._protos.root_transform) for _ in (1, 2, 3, 4)
        ]

        root_trigger = self._clone(self._protos.poster_trigger)
        volume_collider = self._clone(self._protos.poster_trigger)
        art_filter = self._clone(self._protos.mesh_filter)
        preview_filter = self._clone(self._protos.mesh_filter)
        volume_filter = self._clone(self._protos.mesh_filter)
        line_filters = [self._clone(self._protos.mesh_filter) for _ in (1, 2, 3, 4)]
        art_renderer = self._clone(self._protos.mesh_renderer)
        preview_renderer = self._clone(self._protos.mesh_renderer)
        volume_renderer = self._clone(self._protos.mesh_renderer)
        line_renderers = [self._clone(self._protos.mesh_renderer) for _ in (1, 2, 3, 4)]
        animation = self._clone(self._protos.poster_animation)
        shelf = self._clone(self._protos.poster_mono_valid_area)
        interactable = self._clone(self._protos.poster_mono_interactable)
        dashed = self._clone(self._protos.poster_mono_dashed_line)

        make_object(
            root_go, f"{name}_Prefab", 12, (root_transform, root_trigger, interactable)
        )
        make_object(anim_go, "AnimGrp", 0, (anim_transform, animation))
        make_object(art_go, node_name, 12, (art_transform, art_filter, art_renderer))
        make_object(
            preview_go,
            "PreviewMesh",
            12,
            (preview_transform, preview_filter, preview_renderer),
            active=False,
        )
        make_object(slab_go, "MoveStateValidAreaGrp", 0, (slab_transform, shelf))
        make_object(
            volume_go,
            "MoveStateValidArea",
            27,
            (volume_transform, volume_filter, volume_renderer, volume_collider),
        )
        snap_names = ("SnapLoc_L", "SnapLoc_R", "SnapLoc_Up", "SnapLoc_Down")
        snap_positions = (
            (0.0, -0.469, 0.5),
            (0.0, -0.469, -0.5),
            (0.5, -0.469, 0.0),
            (-0.5, -0.469, 0.0),
        )
        for snap_go, snap_transform, snap_name, position in zip(
            (snap_left_go, snap_right_go, snap_up_go, snap_down_go),
            (
                snap_left_transform,
                snap_right_transform,
                snap_up_transform,
                snap_down_transform,
            ),
            snap_names,
            snap_positions,
        ):
            make_object(snap_go, snap_name, 0, (snap_transform,))
            make_transform(
                snap_transform,
                snap_go,
                volume_transform,
                (),
                position,
                identity,
                (1.0, 1.0, 1.0),
            )
        make_object(dashed_go, "DashedLineGrp", 0, (dashed_transform, dashed))
        line_specs = (
            ((0.0, 0.0, 0.5), identity),
            ((0.0, 0.0, -0.5), identity),
            ((0.5, 0.0, 0.0), rotation_y),
            ((-0.5, 0.0, 0.0), rotation_y),
        )
        for number, line_set, (position, rotation) in zip(
            (1, 2, 3, 4),
            zip(line_goes, line_transforms, line_filters, line_renderers),
            line_specs,
        ):
            line_go, line_transform, line_filter, line_renderer = line_set
            make_object(
                line_go,
                f"Line{number}",
                0,
                (line_transform, line_filter, line_renderer),
            )
            make_transform(
                line_transform,
                line_go,
                dashed_transform,
                (),
                position,
                rotation,
                (1.0, 1.0, 0.1),
            )
            wire_filter(line_filter, line_go, self._protos.poster_mesh_guide)
            wire_renderer(
                line_renderer,
                line_go,
                self._protos.poster_material_guides,
                0,
                overlay=True,
            )

        make_transform(
            root_transform,
            root_go,
            None,
            (anim_transform, slab_transform),
            (0.0, 0.0, 0.0),
            identity,
            (1.0, 1.0, 1.0),
        )
        make_transform(
            anim_transform,
            anim_go,
            root_transform,
            (art_transform, preview_transform),
            (0.0, 0.0, 0.0),
            identity,
            (1.0, 1.0, 1.0),
        )
        make_transform(
            art_transform,
            art_go,
            anim_transform,
            (),
            (0.0, 0.0, 0.0),
            identity,
            uniform,
        )
        make_transform(
            preview_transform,
            preview_go,
            anim_transform,
            (),
            (0.0, 0.0, 0.0),
            identity,
            preview,
        )
        make_transform(
            slab_transform,
            slab_go,
            root_transform,
            (volume_transform, dashed_transform),
            slab_position,
            rotation_x,
            slab_scale,
        )
        make_transform(
            volume_transform,
            volume_go,
            slab_transform,
            (
                snap_left_transform,
                snap_right_transform,
                snap_up_transform,
                snap_down_transform,
            ),
            (0.0, 0.469, 0.0),
            identity,
            (1.0, 1.0, 1.0),
        )
        make_transform(
            dashed_transform,
            dashed_go,
            slab_transform,
            tuple(line_transforms),
            (0.0, 0.05, 0.0),
            identity,
            (1.0, 1.0, 1.0),
        )

        wire(root_trigger, root_go).save()
        data = wire(volume_collider, volume_go)
        data.m_Size.x, data.m_Size.y, data.m_Size.z = 1.0, 1.0, 1.0
        data.m_Center.x, data.m_Center.y, data.m_Center.z = 0.0, 0.0, 0.0
        data.save()
        wire_filter(art_filter, art_go, mesh_proto)
        wire_filter(preview_filter, preview_go, mesh_proto)
        wire_filter(
            volume_filter,
            volume_go,
            self._external_pptr(BUILTIN_CUBE_MESH_FILE_ID, BUILTIN_CUBE_MESH_PATH_ID),
        )
        wire_renderer(art_renderer, art_go, material, 1)
        wire_renderer(preview_renderer, preview_go, material, 1)
        wire_renderer(
            volume_renderer,
            volume_go,
            self._protos.poster_material_placement,
            0,
            overlay=True,
        )
        wire(animation, anim_go).save()

        data = wire(shelf, slab_go)
        data.m_Name = ""
        data.m_SnapLocList = [
            self._pptr(snap_transform)
            for snap_transform in (
                snap_left_transform,
                snap_right_transform,
                snap_up_transform,
                snap_down_transform,
            )
        ]
        data.save()

        self._deco_object_type += 1
        data = wire(interactable, root_go)
        data.m_Name = ""
        data.m_DecoObjectType = self._deco_object_type
        data.m_PickupObjectMesh = self._pptr(preview_filter)
        data.m_MoveStateValidArea = self._pptr(volume_transform)
        data.m_ShelfMoveStateValidArea = self._pptr(shelf)
        data.m_BoxCollider = self._pptr(root_trigger)
        data.save()

        data = wire(dashed, dashed_go)
        data.m_Name = ""
        data.m_RendererHorizontal1 = self._pptr(line_renderers[0])
        data.m_RendererHorizontal2 = self._pptr(line_renderers[1])
        data.m_RendererVertical1 = self._pptr(line_renderers[2])
        data.m_RendererVertical2 = self._pptr(line_renderers[3])
        data.save()

        line_objects = [
            obj
            for group in zip(line_goes, line_transforms, line_filters, line_renderers)
            for obj in group
        ]
        shared = (
            self._protos.poster_flip,
            mesh_proto,
            self._protos.poster_mesh_guide,
            self._protos.poster_script_interactable,
            self._protos.poster_script_valid_area,
            self._protos.poster_script_dashed_line,
            self._protos.poster_material_placement,
            self._protos.poster_material_guides,
            self._protos.poster_guide_texture,
            self.shader,
            self.poster_shader,
        )
        graph = [
            root_go,
            root_transform,
            root_trigger,
            interactable,
            anim_go,
            anim_transform,
            animation,
            art_go,
            art_transform,
            art_filter,
            art_renderer,
            preview_go,
            preview_transform,
            preview_filter,
            preview_renderer,
            slab_go,
            slab_transform,
            shelf,
            volume_go,
            volume_transform,
            volume_filter,
            volume_renderer,
            volume_collider,
            snap_left_go,
            snap_left_transform,
            snap_right_go,
            snap_right_transform,
            snap_up_go,
            snap_up_transform,
            snap_down_go,
            snap_down_transform,
            dashed_go,
            dashed_transform,
            dashed,
            *line_objects,
            material,
            texture,
            *shared,
        ]
        return root_go, material, graph

    @property
    def shader(self) -> ObjectReader:
        """The embedded Standard shader materials bind to (kept from the seed)."""
        return self._sf.objects[self._protos.shader_path_id]

    @property
    def poster_shader(self) -> ObjectReader:
        return self._sf.objects[self._protos.poster_shader_path_id]

    def _prune_types(self) -> None:
        """Drop m_Types entries for classes no surviving object uses.

        The seed declares every prototype class; dropping the prototype
        *objects* leaves the declarations behind — harmless at load time,
        but they surface as phantom entries in tools and don't match what
        Unity emits. Rebuild m_Types from the types still in use and
        reindex each object's type_id (an index into m_Types for these
        files)."""
        used = sorted({obj.type_id for obj in self._sf.objects.values()})
        remap = {old: new for new, old in enumerate(used)}
        self._sf.types = [self._sf.types[old] for old in used]
        for obj in self._sf.objects.values():
            obj.type_id = remap[obj.type_id]

    def register(self, container_path: str, primary: ObjectReader, preload: list):
        """Expose `primary` at `container_path`, preloading it and its dependencies."""
        self._container.append((container_path.lower(), primary, preload))

    def save(self, output: pathlib.Path):
        from UnityPy.classes import AssetInfo, PPtr
        from UnityPy.files.SerializedFile import FileIdentifier

        # Unity omits the Standard shader from bundles with no materials;
        # drop the seed shader when nothing references it, to match.
        has_material = any(o.type.name == "Material" for o in self._sf.objects.values())
        if not has_material:
            self._sf.objects.pop(self._protos.shader_path_id, None)

        self._prune_types()

        if self._references_external:
            default_resources = FileIdentifier.__new__(FileIdentifier)
            default_resources.temp_empty = ""
            default_resources.guid = BUILTIN_DEFAULT_RESOURCES_GUID
            default_resources.type = 0
            default_resources.path = "Library/unity default resources"
            self._sf.externals = [default_resources, *self._sf.externals]

        manifest = self._manifest.read()
        manifest.m_Name = self._name
        manifest.m_AssetBundleName = self._name
        manifest.m_Dependencies = []

        preload_table: list = []
        container: list = []
        for path, primary, preload in self._container:
            index = len(preload_table)
            preload_table.extend(
                entry
                if isinstance(entry, PPtr)
                else PPtr(m_FileID=0, m_PathID=entry.path_id, assetsfile=self._sf)
                for entry in preload
            )
            # attrs generates AssetInfo.__init__ at runtime, so the
            # checker can't see its signature; the kwargs match the
            # class's fields.
            # ty: ignore[unknown-argument]
            info = AssetInfo(
                preloadIndex=index,
                preloadSize=len(preload),
                asset=PPtr(m_FileID=0, m_PathID=primary.path_id, assetsfile=self._sf),
            )
            container.append((path, info))

        manifest.m_PreloadTable = preload_table
        manifest.m_Container = container
        manifest.save()
        self._sf.mark_changed()

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(self._bundle_file.save(packer="lz4"))


def progress(items: list, label: str):
    """Yield each of `items`, reporting `label: done/total (pct%)` as it
    goes: in place via a carriage return in a terminal, once per
    percent in a CI log."""
    total = len(items)

    if not total:
        return

    live = sys.stdout.isatty()

    for done, item in enumerate(items, start=1):
        yield item

        percent = done * 100 // total

        if live:
            print(f"\r  {label}: {done}/{total} ({percent}%)", end="", flush=True)
        else:
            print(f"  {label}: {done}/{total} ({percent}%)", flush=True)

    if live:
        print()


def parallel_map(items: list, worker, label: str, workers: int | None = None) -> list:
    """Run `worker(item)` over `items` across a process pool, returning
    the results in input order and reporting progress as items complete.

    A process pool, not threads: the payload here (the BC7 encode) holds
    the GIL while it searches for each block's best mode, so threads
    would serialize it. `worker` and each item must be picklable.
    Progress prints as in `progress`, keyed off completion order. The
    first worker exception is re-raised; one worker per CPU by default
    (the pool spawns lazily, so more workers than items costs nothing).
    """
    total = len(items)

    if not total:
        return []

    workers = workers or (os.cpu_count() or 4)
    live = sys.stdout.isatty()
    last_percent = -1

    results: list = [None] * total

    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(worker, item): index for index, item in enumerate(items)}

        for done, future in enumerate(
            concurrent.futures.as_completed(futures), start=1
        ):
            results[futures[future]] = future.result()

            percent = done * 100 // total

            if live:
                print(f"\r  {label}: {done}/{total} ({percent}%)", end="", flush=True)
            elif percent != last_percent:
                last_percent = percent
                print(f"  {label}: {done}/{total} ({percent}%)", flush=True)

    if live:
        print()

    return results


def _texture_payload(asset: pathlib.Path) -> tuple[int, int, int, int, bytes]:
    """The (format, width, height, mip_count, bytes) `asset` embeds into
    the bundle: already-encoded textures pass through the raw chunk
    verbatim (single mip), the room props (`*_Material`, and the poster
    art, `*_Art`) get the full mip chain, every other PNG stays
    single-mip. Runs in a worker process (picklable, fresh per-call
    state)."""
    raw = read_raw_texture(asset)
    if raw is not None:
        return raw[0], raw[1], raw[2], 1, raw[3]

    image = Image.open(asset).convert("RGBA")
    if asset.stem.endswith(MATERIAL_SUFFIX) or asset.stem.endswith(POSTER_SUFFIX):
        return compress_mipmapped(image)
    texture_format, data = compress_texture(image)
    width, height = image.size
    return texture_format, width, height, 1, data


def build(
    assets_dir: pathlib.Path,
    name: str,
    output: pathlib.Path,
    set_name: str | None = None,
    jobs: int | None = None,
) -> None:
    """Build one AssetBundle named `name` from the PNGs under
    `assets_dir`.

    Mirrors Unity's Builder.Run: `*_Material` PNGs become Texture2D +
    Standard Material (the room props), `*_Art` PNGs become posters,
    and the room props' textures — materials and poster art alike —
    get the full mip chain, as the reference mipmaps its props; every
    other PNG becomes Texture2D + Sprite (single-mip, like the
    reference's card art and icons).
    Container paths are `assets/<set_name>/` + the path relative to
    `assets_dir`, lowercased — exactly what Unity emitted — so the game
    resolves assets the same. `set_name` defaults to `assets_dir.name`;
    pass it when the on-disk folder differs from the set's identity
    (the ultra run's twin keeps the base set's names and container
    paths).

    `jobs` is the process-pool size for the texture compression."""
    bundle = Bundle(name)
    set_name = set_name or assets_dir.name
    assets = sorted(p for p in assets_dir.rglob("*") if p.is_file())
    textures = [p for p in assets if p.suffix == ".png"]
    meshes = [p for p in assets if p.suffix == ".obj"]

    # The slow part is the texture data (the BC7 encode holds the GIL),
    # so gather it across a process pool. Object construction stays
    # serial, in asset order, so path IDs and container order — and thus
    # the bundle's bytes — stay deterministic.
    payloads = parallel_map(textures, _texture_payload, name, jobs)

    for asset, (texture_format, width, height, mip_count, data) in zip(
        textures, payloads
    ):
        container = (
            f"assets/{set_name}/{asset.relative_to(assets_dir).as_posix()}".lower()
        )

        texture = bundle.add_raw_texture(
            asset.stem, texture_format, width, height, data, mip_count
        )
        bundle.register(container, texture, [texture])

        if asset.stem.endswith(MATERIAL_SUFFIX):
            material = bundle.add_material(asset.stem, texture)
            mat_path = container.removesuffix(".png") + ".mat"
            bundle.register(mat_path, material, [material, texture, bundle.shader])
        elif asset.stem.endswith(POSTER_SUFFIX):
            poster_name = asset.stem.removesuffix(POSTER_SUFFIX)
            poster, material, graph = bundle.add_poster(poster_name, texture)
            bundle.register(
                f"assets/{set_name}/{poster_name}_material.mat".lower(),
                material,
                [
                    bundle._external_pptr(
                        BUILTIN_SHADER_FILE_ID, BUILTIN_SHADER_PATH_ID
                    ),
                    bundle.shader,
                    material,
                    texture,
                ],
            )
            bundle.register(
                container.removesuffix(".png") + ".prefab",
                poster,
                [
                    bundle._external_pptr(
                        BUILTIN_SHADER_FILE_ID, BUILTIN_SHADER_PATH_ID
                    ),
                    bundle._external_pptr(
                        BUILTIN_CUBE_MESH_FILE_ID, BUILTIN_CUBE_MESH_PATH_ID
                    ),
                    *graph,
                ],
            )
        else:
            sprite = bundle.add_sprite(asset.stem, texture, (width, height))
            bundle.register(container, sprite, [sprite, texture])

    for asset in progress(meshes, f"{name} meshes"):
        container = (
            f"assets/{set_name}/{asset.relative_to(assets_dir).as_posix()}".lower()
        )
        root_object, graph = bundle.add_mesh(asset.stem, asset)
        preload = graph + [bundle.shader]
        # Unity's model importer makes the GameObject, its placeholder
        # material, and its mesh all addressable at the .obj path;
        # without these sub-asset entries the loader's lookup returns
        # null and the figurine renders invisibly. Each shares the full
        # dependency graph as its preload.
        default_material = next(o for o in graph if o.type.name == "Material")
        mesh_object = next(o for o in graph if o.type.name == "Mesh")
        bundle.register(container, root_object, preload)
        bundle.register(container, default_material, preload)
        bundle.register(container, mesh_object, preload)

    bundle.save(output)
    print(
        f"  {name}: {len(textures)} textures, {len(meshes)} meshes, "
        f"{output.stat().st_size / 1e6:.1f} MB"
    )
