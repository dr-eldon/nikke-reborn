"""Extend src/nikke_reborn/seed.bundle with the poster prototypes.

The cardpack seed (see the bundler docstring) carries one prototype of
every type the cardpack bundles emit. Posters need the game's deco
scaffolding instead: the quad meshes (verbatim geometry and UVs), the
three game scripts with a vanilla MonoBehaviour per script, the root
trigger collider, the animation component, the flip clip, the per-
poster and shared materials, the guide texture, and the deco shader the
shared materials bind. This distills one of each from the reference
cardpack mod's poster bundle into the seed, materializing the
stream-based mesh and texture data inline (the seed carries no resource
stream) and rewiring the PPtrs and the header's script type table to
the seed-local clones. Run once, from the repo root:

    uv run python scripts/distill_seed.py
"""

import pathlib

import UnityPy
from UnityPy.classes import PPtr
from UnityPy.files.ObjectReader import ObjectReader
from UnityPy.files.SerializedFile import LocalSerializedObjectIdentifier

SEED = pathlib.Path("src/nikke_reborn/seed.bundle")
REFERENCE = pathlib.Path(
    "reference/extracted/BepInEx/plugins/CRYPTON/cryptons_posters_prefabloader/cryptons_posters"
)

MARKER = "__proto_poster_mesh_square"


def find(sf, type_name, name=None, suffix=None):
    for obj in sf.objects.values():
        if obj.type.name != type_name:
            continue
        own_name = obj.peek_name() or ""
        if name is not None and own_name != name:
            continue
        if suffix is not None and not own_name.endswith(suffix):
            continue
        return obj
    wanted = name if name is not None else f"*{suffix}"
    raise SystemExit(f"no {type_name} named {wanted!r} in the given file")


def stream_bytes(resource, info):
    resource.seek(info.offset)
    return resource.read(info.size)


def zero_stream(info):
    info.path = ""
    info.offset = 0
    info.size = 0


def pptr(sf, path_id):
    return PPtr(m_FileID=0, m_PathID=path_id, assetsfile=sf)


def script_identifier(path_id):
    identifier = LocalSerializedObjectIdentifier.__new__(
        LocalSerializedObjectIdentifier
    )
    identifier.local_serialized_file_index = 0
    identifier.local_identifier_in_file = path_id
    return identifier


def poster_graph(sf, root_components):
    transform = next(c for c in root_components if c.type.name == "Transform")

    def walk(current):
        for child in current.read().m_Children:
            child_transform = sf.objects[child.m_PathID]
            go = sf.objects[child_transform.read().m_GameObject.m_PathID]
            for component in go.read().m_Component:
                obj = sf.objects[component.component.m_PathID]
                yield obj
                if obj.type.name == "Transform":
                    yield from walk(obj)

    return list(walk(transform))


class Distiller:
    def __init__(self, seed_sf, ref_sf, resource):
        self.seed_sf = seed_sf
        self.ref_sf = ref_sf
        self.resource = resource
        self.next_id = max(seed_sf.objects) + 1

    def type_id(self, src):
        if src.class_id == 114:
            for index, entry in enumerate(self.seed_sf.types):
                if entry is src.serialized_type:
                    return index
        else:
            for index, entry in enumerate(self.seed_sf.types):
                if entry.class_id == src.class_id:
                    return index
        self.seed_sf.types.append(src.serialized_type)
        return len(self.seed_sf.types) - 1

    def clone(self, src):
        path_id = self.next_id
        self.next_id += 1
        type_id = self.type_id(src)
        obj = ObjectReader(
            assets_file=self.seed_sf,
            reader=src.reader,
            path_id=path_id,
            type_id=type_id,
            serialized_type=self.seed_sf.types[type_id],
            class_id=src.class_id,
            type=src.type,
            byte_start=src.byte_start,
            byte_size=src.byte_size,
            is_destroyed=src.is_destroyed,
            is_stripped=src.is_stripped,
        )
        obj.set_raw_data(src.get_raw_data())
        self.seed_sf.objects[path_id] = obj
        return obj


def main() -> None:
    seed_env = UnityPy.load(SEED.read_bytes())
    seed_sf = next(f for f in seed_env.file.files.values() if hasattr(f, "objects"))
    reference_env = UnityPy.load(str(REFERENCE))
    reference_file = list(reference_env.files.values())[0]
    ref_sf = next(f for f in reference_file.files.values() if hasattr(f, "objects"))
    resource = next(v for v in reference_file.files.values() if hasattr(v, "seek"))

    if any((o.peek_name() or "") == MARKER for o in seed_sf.objects.values()):
        raise SystemExit("seed: the poster prototypes are already present")

    distiller = Distiller(seed_sf, ref_sf, resource)

    def ref(type_name, **kwargs):
        return find(ref_sf, type_name, **kwargs)

    mesh_square = distiller.clone(ref("Mesh", name="CRYPTONS_EPL_PosterSquareMesh"))
    mesh_portrait = distiller.clone(ref("Mesh", name="CRYPTONS_EPL_PosterPortraitMesh"))
    mesh_landscape = distiller.clone(
        ref("Mesh", name="CRYPTONS_EPL_PosterLandscapeMesh")
    )
    mesh_guide = distiller.clone(ref("Mesh", name="CRYPTONS_EPL_PosterGuideMesh"))
    for obj, name in (
        (mesh_square, MARKER),
        (mesh_portrait, "__proto_poster_mesh_portrait"),
        (mesh_landscape, "__proto_poster_mesh_landscape"),
        (mesh_guide, "__proto_poster_mesh_guide"),
    ):
        data = obj.read()
        data.m_Name = name
        data.m_VertexData.m_DataSize = stream_bytes(resource, data.m_StreamData)
        zero_stream(data.m_StreamData)
        # The reference stores this data in its resource stream and marks it
        # as not kept inline; we materialize it inline, so flip the flags or
        # Unity reads the (now empty) stream and drops the vertices.
        data.m_KeepVertices = True
        data.m_KeepIndices = True
        data.save()

    script_interactable = distiller.clone(
        ref("MonoScript", name="InteractableDecoration")
    )
    script_valid_area = distiller.clone(
        ref("MonoScript", name="ShelfMoveStateValidArea")
    )
    script_dashed_line = distiller.clone(ref("MonoScript", name="DashedLine"))

    placement_source = ref("Material", name="CRYPTONS_EPL_PosterPlacement")
    deco_shader = distiller.clone(
        ref_sf.objects[placement_source.read().m_Shader.m_PathID]
    )
    flip = distiller.clone(ref("AnimationClip"))
    data = flip.read()
    data.m_Name = "__proto_poster_flip"
    data.save()

    poster_material = distiller.clone(ref("Material", suffix="_001_Material"))
    data = poster_material.read()
    data.m_Name = "__proto_poster_material"
    for key, tex_env in data.m_SavedProperties.m_TexEnvs:
        if key == "_MainTex":
            tex_env.m_Texture = pptr(seed_sf, 0)
    data.save()

    material_placement = distiller.clone(placement_source)
    material_guides = distiller.clone(ref("Material", name="CRYPTONS_EPL_PosterGuides"))
    for obj, name in (
        (material_placement, "__proto_poster_material_placement"),
        (material_guides, "__proto_poster_material_guides"),
    ):
        data = obj.read()
        data.m_Name = name
        data.m_Shader = pptr(seed_sf, deco_shader.path_id)
        data.save()

    guide_texture = distiller.clone(
        ref("Texture2D", name="CRYPTONS_EPL_PosterGuideTexture")
    )
    data = guide_texture.read()
    data.m_Name = "__proto_poster_guide_tex"
    data.image_data = stream_bytes(resource, data.m_StreamData)
    zero_stream(data.m_StreamData)
    data.save()

    root = ref("GameObject", suffix="_001_Prefab")
    root_components = [
        ref_sf.objects[c.component.m_PathID] for c in root.read().m_Component
    ]
    trigger = distiller.clone(
        next(c for c in root_components if c.type.name == "BoxCollider")
    )
    data = trigger.read()
    data.m_GameObject = pptr(seed_sf, 0)
    data.save()

    graph = root_components + poster_graph(ref_sf, root_components)
    animation = distiller.clone(next(c for c in graph if c.type.name == "Animation"))
    data = animation.read()
    data.m_Animation = pptr(seed_sf, flip.path_id)
    data.m_Animations = [pptr(seed_sf, flip.path_id)]
    data.m_GameObject = pptr(seed_sf, 0)
    data.save()

    script_of = {
        o.path_id: (o.parse_as_dict().get("m_Name") or "")
        for o in ref_sf.objects.values()
        if o.type.name == "MonoScript"
    }

    def mono(script_name):
        return next(
            c
            for c in graph
            if c.type.name == "MonoBehaviour"
            and script_of[c.parse_as_dict()["m_Script"]["m_PathID"]] == script_name
        )

    script_of_index = {}
    for obj, script, name in (
        (
            distiller.clone(mono("InteractableDecoration")),
            script_interactable,
            "__proto_poster_mono_interactable",
        ),
        (
            distiller.clone(mono("ShelfMoveStateValidArea")),
            script_valid_area,
            "__proto_poster_mono_valid_area",
        ),
        (
            distiller.clone(mono("DashedLine")),
            script_dashed_line,
            "__proto_poster_mono_dashed_line",
        ),
    ):
        data = obj.read()
        data.m_Name = name
        data.m_Script = pptr(seed_sf, script.path_id)
        data.m_GameObject = pptr(seed_sf, 0)
        data.save()
        script_of_index[seed_sf.types[obj.type_id].script_type_index] = script.path_id

    seed_sf.script_types = [
        script_identifier(script_of_index[index]) for index in sorted(script_of_index)
    ]

    seed_sf.mark_changed()
    SEED.write_bytes(seed_env.file.save(packer="lz4"))
    print(
        f"wrote {SEED} ({SEED.stat().st_size:,} bytes, {len(seed_sf.objects)} objects)"
    )


if __name__ == "__main__":
    main()
