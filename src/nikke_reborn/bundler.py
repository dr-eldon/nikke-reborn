"""Build Unity AssetBundles without Unity.

The pipeline used to drive the Unity editor (an ExpansionBuilder project) to import each
PNG as a BC7 Texture2D (+ Sprite), create a Standard-shader Material for every `*_Material`
texture, and pack them into a per-set AssetBundle. This reproduces that output with UnityPy
so the pipeline no longer needs Unity (and its licensing, Windows-only, DLL and caching
problems).

The bundles are consumed by TCG Card Shop Simulator (Unity 2021.3.38f1). We can't author
a byte-identical file, but the game resolves assets by name/container path, so a
structurally faithful bundle loads the same. UnityPy also can't author a SerializedFile
from nothing, so we build on top of `seed.bundle` -- a ~47 KB distillation of a real
Unity-built bundle holding the container scaffolding, the embedded built-in Standard
shader, and one prototype of each object type. We clone those prototypes (so Unity's
field defaults come along for free) and override only what matters: name, image, size,
and the PPtr wiring between them.
"""

from __future__ import annotations

import concurrent.futures
import dataclasses
import hashlib
import importlib.resources
import os
import pathlib
import struct
import sys

import UnityPy
from PIL import Image
from UnityPy.enums import TextureFormat
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.files.SerializedFile import SerializedFile

# UnityPy cannot author a SerializedFile from nothing, so we ship a ~47 KB seed bundle:
# the irreducible container scaffolding plus one prototype of each object we build
# (Texture2D/Sprite/Material) and the built-in Standard shader materials bind to. It was
# distilled once from a real Unity-built bundle; see scripts/distill_seed.py.
SEED = importlib.resources.files(__package__) / "seed.bundle"

# GPU format Builder.cs bakes with (TextureImporterFormat.BC7, best quality). BC7 is
# 1 byte/px; UnityPy encodes it via etcpak.compress_bc7.
TEXTURE_FORMAT = TextureFormat.BC7

# Sprite import default Unity used (pixels-per-unit 100); centre pivot / extrude come
# from the prototype unchanged.
SPRITE_PIXELS_TO_UNITS = 100.0

# Builder.GenerateMaterials created a Standard material for every `*_Material` texture.
# Those become Texture2D + Material; every other PNG becomes Texture2D + Sprite.
MATERIAL_SUFFIX = "_Material"

# Static card art comes from an already-encoded source texture that `bundle` only relocates.
# To avoid a lossy decode->PNG->re-encode round-trip, `extract` stashes the source texture
# (format + dimensions + raw bytes) verbatim in this private PNG chunk, and `build` embeds it
# untouched. Private/ancillary/safe-to-copy PNG chunk name, so it survives a byte copy.
RAW_TEXTURE_CHUNK = b"nkTx"


def pack_raw_texture(
    texture_format: int, width: int, height: int, data: bytes
) -> bytes:
    return struct.pack("<iii", int(texture_format), width, height) + data


def read_raw_texture(png: pathlib.Path):
    """Return (format, width, height, data) from a PNG's raw-texture chunk, or None."""
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


# Unity's mesh vertex layout for an imported model: position + normal + tangent + uv0,
# interleaved as floats (channels 0/1/2/4), 48-byte stride. Matches the seed's mesh prototype.
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

    Returns (vertex_count, vertex_bytes, index_bytes, index_count, index_format, center,
    extent). Unity's importer converts the .obj's right-handed Y-up space to its own
    left-handed system; we negate X and reverse triangle winding to match. Tangents are a
    placeholder -- figurine materials sample only albedo. NOTE: the axis/winding is the one
    thing that needs an in-game check; flip it here if a figurine renders mirrored/inside-out.
    """
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
    # A figurine model: root GameObject -> child GameObject (MeshFilter + MeshRenderer),
    # a Transform each, and the Mesh.
    mesh: ObjectReader
    mesh_filter: ObjectReader
    mesh_renderer: ObjectReader
    child_object: ObjectReader
    root_object: ObjectReader
    child_transform: ObjectReader
    root_transform: ObjectReader


class Bundle:
    """A single AssetBundle under construction, templated from the reference bundle."""

    def __init__(self, name: str):
        self._env = UnityPy.load(SEED.read_bytes())
        self._sf: SerializedFile = next(
            f for f in self._env.file.files.values() if isinstance(f, SerializedFile)
        )
        self._protos = self._extract_prototypes()
        self._manifest = self._find(lambda o: o.type.name == "AssetBundle")

        # Assign PathIDs that can't collide with the objects we keep (shader + manifest).
        self._next_path_id = max(self._sf.objects) + 1

        # Start from a clean slate: keep only the manifest and the Standard shader,
        # drop every Pokémon-specific object. We re-add our own below.
        keep = {self._manifest.path_id, self._protos.shader_path_id}
        self._sf.objects = {
            path_id: obj for path_id, obj in self._sf.objects.items() if path_id in keep
        }

        # Rebuild the bundle's file table with exactly one entry: our SerializedFile under a
        # unique internal name. Two things happen here:
        #  * The reference's `.resS` resource stream is dropped (~all its texture pixel data
        #    lives there via m_StreamData). Our textures store data inline via set_image, so
        #    nothing references the stream and carrying it would bloat the bundle to ~240 MB.
        #  * The `CAB-<hash>` archive name is made unique per bundle. Every bundle is cloned
        #    from one seed, so they'd otherwise all share the seed's name -- and Unity keys
        #    loaded SerializedFiles by that name, silently refusing to load a second bundle
        #    whose name it already holds (only the first of ours would load at runtime).
        # blake2b is just a stable Unity-style identifier here, not a security hash.
        cab = "CAB-" + hashlib.blake2b(name.encode(), digest_size=16).hexdigest()
        self._env.file.files = {cab: self._sf}

        self._name = name
        self._container: list[tuple[str, ObjectReader, list[ObjectReader]]] = []

    def _find(self, predicate):
        return next(o for o in self._sf.objects.values() if predicate(o))

    def _extract_prototypes(self) -> Prototypes:
        texture = self._find(lambda o: o.type.name == "Texture2D")
        sprite = self._find(lambda o: o.type.name == "Sprite")
        # `defaultMat` is the one reference material bound to the built-in Standard shader
        # (the others use a third-party shader Nikke doesn't use).
        material = self._find(
            lambda o: o.type.name == "Material" and o.read().m_Name == "defaultMat"
        )
        shader_path_id = material.read().m_Shader.m_PathID

        mesh = self._find(lambda o: o.type.name == "Mesh")
        mesh_filter = self._find(lambda o: o.type.name == "MeshFilter")
        mesh_renderer = self._find(lambda o: o.type.name == "MeshRenderer")
        # The child carries the mesh (Transform + MeshFilter + MeshRenderer); the root just
        # parents it (Transform only) and is the asset the game loads by name.
        objects = [o for o in self._sf.objects.values() if o.type.name == "GameObject"]
        child_object = next(o for o in objects if len(o.read().m_Component) == 3)
        root_object = next(o for o in objects if len(o.read().m_Component) == 1)
        child_transform = self._find(
            lambda o: o.type.name == "Transform"
            and o.read().m_GameObject.m_PathID == child_object.path_id
        )
        root_transform = self._find(
            lambda o: o.type.name == "Transform"
            and o.read().m_GameObject.m_PathID == root_object.path_id
        )
        return Prototypes(
            texture,
            sprite,
            material,
            shader_path_id,
            mesh,
            mesh_filter,
            mesh_renderer,
            child_object,
            root_object,
            child_transform,
            root_transform,
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

    def add_texture(self, name: str, image: Image.Image) -> ObjectReader:
        obj = self._clone(self._protos.texture)
        data = obj.read()
        data.m_Name = name
        # BC7 (like all block formats) needs both dimensions to be multiples of 4. Unity
        # falls back to uncompressed RGBA32 otherwise -- as the source assets confirm -- so
        # match that: forcing BC7 would pad the block grid and store a texture the game's
        # runtime never sees Unity produce (and lose quality, since RGBA32 is lossless).
        width, height = image.size
        block_compressible = width % 4 == 0 and height % 4 == 0
        fmt = TEXTURE_FORMAT if block_compressible else TextureFormat.RGBA32
        # set_image re-encodes and fixes m_Width/Height/CompleteImageSize/format.
        data.set_image(image, target_format=fmt)
        data.m_MipCount = 1
        data.m_IsReadable = False
        data.m_TextureSettings.m_FilterMode = 1  # Bilinear
        data.save()
        return obj

    def add_raw_texture(
        self, name: str, texture_format: int, width: int, height: int, data_bytes: bytes
    ) -> ObjectReader:
        """Embed an already-encoded texture verbatim (no decode/re-encode, so lossless)."""
        obj = self._clone(self._protos.texture)
        data = obj.read()
        data.m_Name = name
        data.m_Width = width
        data.m_Height = height
        data.image_data = data_bytes
        data.m_CompleteImageSize = len(data_bytes)
        data.m_TextureFormat = TextureFormat(texture_format)
        data.m_MipCount = 1
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
        """Build a figurine model from a .obj: a Mesh and the GameObject hierarchy Unity
        imports for it. Returns (root_object, objects) -- the root GameObject is what the
        game loads by `name`; `objects` is the whole graph, for the container preload.

        The MeshRenderer gets a placeholder `defaultMat` (what Unity's importer assigns to
        a material-less .obj); the figurine's real material lives as a separate asset that
        the mod loader applies at runtime from its JSON, so we don't wire it here.
        """
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

    @property
    def shader(self) -> ObjectReader:
        """The embedded Standard shader materials bind to (kept from the seed)."""
        return self._sf.objects[self._protos.shader_path_id]

    def _prune_types(self) -> None:
        """Drop m_Types entries for classes no surviving object uses.

        Bundles are cloned from one seed whose SerializedFile declares every prototype class
        (Mesh, GameObject, MeshFilter, MeshRenderer, Transform, ...). Dropping the prototype
        *objects* leaves those declarations behind in m_Types -- harmless at load time, but
        they surface as phantom entries in tools (e.g. AssetStudio's "Asset Classes" tab) and
        don't match what Unity emits. Rebuild m_Types from the types still in use and reindex
        each object's type_id (an index into m_Types for these files).
        """
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

        # Unity omits the Standard shader from bundles with no materials (e.g. the animated
        # frame bundles). Drop our seed shader when nothing references it so we match.
        has_material = any(o.type.name == "Material" for o in self._sf.objects.values())
        if not has_material:
            self._sf.objects.pop(self._protos.shader_path_id, None)

        self._prune_types()

        manifest = self._manifest.read()
        manifest.m_Name = self._name
        manifest.m_AssetBundleName = self._name
        manifest.m_Dependencies = []

        preload_table: list = []
        container: list = []
        for path, primary, preload in self._container:
            index = len(preload_table)
            preload_table.extend(
                PPtr(m_FileID=0, m_PathID=o.path_id, assetsfile=self._sf)
                for o in preload
            )
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
        output.write_bytes(self._env.file.save(packer="lz4"))


def progress(items: list, label: str):
    """Yield each of `items`, reporting `label: done/total (pct%)` as it goes.

    In a terminal the line updates in place via a carriage return; CI logs don't collapse
    those, so there it prints once per percent instead of once per item.
    """
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


def parallel(items: list, worker, label: str, workers: int | None = None) -> None:
    """Run `worker(item)` over `items` across a thread pool, reporting progress as it goes.

    Progress is printed the same way as `progress`, just keyed off completion order rather
    than iteration order. The work must be thread-safe; the first worker exception is
    re-raised. Defaults to one thread per CPU -- the payload here (texture decode, PNG
    encode, image compositing) is C code that drops the GIL, so it scales with cores.
    """
    total = len(items)

    if not total:
        return

    workers = workers or (os.cpu_count() or 4)
    live = sys.stdout.isatty()
    last_percent = -1

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(worker, item) for item in items]

        for done, future in enumerate(
            concurrent.futures.as_completed(futures), start=1
        ):
            future.result()

            percent = done * 100 // total

            if live:
                print(f"\r  {label}: {done}/{total} ({percent}%)", end="", flush=True)
            elif percent != last_percent:
                last_percent = percent
                print(f"  {label}: {done}/{total} ({percent}%)", flush=True)

    if live:
        print()


def build(
    assets_dir: pathlib.Path, name: str, output: pathlib.Path, root: pathlib.Path
) -> None:
    """Build one AssetBundle named `name` from the PNGs under `assets_dir`.

    Mirrors Unity's Builder.Run: `*_Material` PNGs become Texture2D + Standard Material,
    every other PNG becomes Texture2D + Sprite. Container paths are `assets/` + the path
    relative to `root` (the Assets-equivalent), lowercased -- exactly what Unity emitted
    when `root` was copied into the project's Assets/ -- so the game resolves assets the same.
    """
    bundle = Bundle(name)
    assets = sorted(p for p in assets_dir.rglob("*") if p.is_file())
    textures = [p for p in assets if p.suffix == ".png"]
    meshes = [p for p in assets if p.suffix == ".obj"]

    for asset in progress(textures, name):
        container = "assets/" + asset.relative_to(root).as_posix().lower()

        raw = read_raw_texture(asset)
        if raw is not None:
            texture_format, width, height, data_bytes = raw
            texture = bundle.add_raw_texture(
                asset.stem, texture_format, width, height, data_bytes
            )
            size = (width, height)
        else:
            image = Image.open(asset).convert("RGBA")
            texture = bundle.add_texture(asset.stem, image)
            size = image.size
        bundle.register(container, texture, [texture])

        if asset.stem.endswith(MATERIAL_SUFFIX):
            material = bundle.add_material(asset.stem, texture)
            mat_path = container.removesuffix(".png") + ".mat"
            bundle.register(mat_path, material, [material, texture, bundle.shader])
        else:
            sprite = bundle.add_sprite(asset.stem, texture, size)
            bundle.register(container, sprite, [sprite, texture])

    # A figurine .obj imports as a model whose MeshRenderer uses a placeholder defaultMat;
    # its real material is a separate asset above, applied by the loader from the JSON.
    for asset in progress(meshes, f"{name} meshes"):
        container = "assets/" + asset.relative_to(root).as_posix().lower()
        root_object, graph = bundle.add_mesh(asset.stem, asset)
        preload = graph + [bundle.shader]
        # Unity's model importer makes the GameObject, its placeholder material, and its mesh
        # all addressable at the .obj path. EPL resolves a figurine's mesh (and material) by
        # name from the bundle container, so without these sub-asset entries the lookup
        # returns null and the figurine renders invisibly. Register all three (matching the
        # Unity-built reference bundle); each shares the full dependency graph as its preload.
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
