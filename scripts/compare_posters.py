"""Compare the emitted poster graph against the vanilla deco graph."""

import difflib
import sys
import pathlib

import attrs

sys.path.insert(0, "scripts")
import distill_seed as d
from UnityPy.helpers import TypeTreeHelper

BUNDLE = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else "/tmp/test_bundle.bundle"
PREFAB = sys.argv[2] if len(sys.argv) > 2 else "poster_0001_syuenchapter2_square_art.prefab"

_, shared = d.load_file(d.GAME / "sharedassets2.assets")
root, _ = d.deco(shared)

SCRIPT_NAMES = {
    "ShelfMoveStateValidArea": 0,
    "InteractableDecoration": 1,
    "DashedLine": 2,
}
GAME_SCRIPT_INDEX = {
    "ShelfMoveStateValidArea": 32,
    "InteractableDecoration": 13,
    "DashedLine": 64,
}


def obj_name(sf, obj):
    try:
        return obj.peek_name() or obj.read().m_Name or ""
    except Exception:
        return ""


def script_name_for(index, table):
    return {value: key for key, value in table.items()}[index]


def read_mono(mono, script_name):
    node = d.mono_tree(script_name)
    mono.reset()
    return TypeTreeHelper.read_typetree(
        node,
        mono.reader,
        as_dict=True,
        assetsfile=mono.assets_file,
        byte_size=mono.byte_size,
        check_read=True,
    )


def read_mono_stored(mono, script_name):
    return mono.parse_as_dict()


def ref_label(sf, ref):
    file_id = ref["m_FileID"] if isinstance(ref, dict) else ref.m_FileID
    path_id = ref["m_PathID"] if isinstance(ref, dict) else ref.m_PathID
    if not path_id:
        return "null"
    if file_id:
        return f"ext({file_id},{path_id})"
    target = sf.objects.get(path_id)
    if target is None:
        return f"missing({path_id})"
    name = obj_name(sf, target)
    if target.type.name in (
        "Transform",
        "MeshFilter",
        "MeshRenderer",
        "MonoBehaviour",
        "BoxCollider",
        "Animation",
    ):
        try:
            owner = sf.objects[
                target.parse_as_dict()["m_GameObject"]["m_PathID"]
            ]
            return f"{target.type.name}@{owner.peek_name()}"
        except Exception:
            return f"{target.type.name}@?"
    return name or target.type.name


def dump_graph(sf, root_go, script_table, mono_reader=read_mono):
    out = []

    def components(go):
        data = go.parse_as_dict()
        return [sf.objects[c["component"]["m_PathID"]] for c in data["m_Component"]]

    def rec(go, depth):
        data = go.parse_as_dict()
        comps = components(go)
        transform = next((c for c in comps if c.type.name == "Transform"), None)
        line = (
            f"GO [{data['m_Name']}] L{data['m_Layer']} act={data['m_IsActive']} <"
            + ",".join(c.type.name for c in comps)
            + ">"
        )
        if transform is not None:
            td = transform.parse_as_dict()
            line += (
                f" pos=({td['m_LocalPosition']['x']:.4f},"
                f"{td['m_LocalPosition']['y']:.4f},"
                f"{td['m_LocalPosition']['z']:.4f})"
                f" rot=({td['m_LocalRotation']['x']:.4f},"
                f"{td['m_LocalRotation']['y']:.4f},"
                f"{td['m_LocalRotation']['z']:.4f},"
                f"{td['m_LocalRotation']['w']:.4f})"
                f" scl=({td['m_LocalScale']['x']:.4f},"
                f"{td['m_LocalScale']['y']:.4f},"
                f"{td['m_LocalScale']['z']:.4f})"
            )
        out.append("  " * depth + line)
        for component in comps:
            if component.type.name == "MonoBehaviour":
                try:
                    script_name = script_name_for(
                        component.serialized_type.script_type_index, script_table
                    )
                except KeyError:
                    script_name = "(unknown)"
                fields = mono_reader(component, script_name)
                if script_name == "(unknown)":
                    ref = fields.get("m_Script")
                    if ref and ref.get("m_PathID"):
                        target = sf.objects.get(ref["m_PathID"])
                        script_name = obj_name(sf, target) if target else "(unknown)"
                rendered = []
                for key, value in fields.items():
                    if key in ("m_GameObject", "m_Script"):
                        continue
                    if isinstance(value, (list, tuple)):
                        if value and all(
                            isinstance(v, dict) and "m_PathID" in v for v in value
                        ):
                            rendered.append(
                                f"{key}=[{len(value)}] "
                                + " ".join(ref_label(sf, v) for v in value)
                            )
                        else:
                            rendered.append(f"{key}={value!r}")
                    elif isinstance(value, dict) and "m_PathID" in value:
                        rendered.append(f"{key}={ref_label(sf, value)}")
                    else:
                        rendered.append(f"{key}={value!r}")
                out.append(
                    "  " * (depth + 1)
                    + f"MONO {script_name}: " + " ".join(rendered)
                )
                continue
            cd = component.parse_as_dict()
            if component.type.name == "BoxCollider":
                out.append(
                    "  " * (depth + 1)
                    + f"COL center=({cd['m_Center']['x']:.4f},"
                    f"{cd['m_Center']['y']:.4f},{cd['m_Center']['z']:.4f})"
                    f" size=({cd['m_Size']['x']:.4f},{cd['m_Size']['y']:.4f},"
                    f"{cd['m_Size']['z']:.4f}) trig={cd.get('m_IsTrigger')}"
                )
            elif component.type.name == "MeshFilter":
                ref = cd.get("m_Mesh")
                out.append("  " * (depth + 1) + f"FIL mesh={ref_label(sf, ref)}")
            elif component.type.name == "MeshRenderer":
                for m in cd.get("m_Materials") or []:
                    out.append(
                        "  " * (depth + 1)
                        + f"REN mat={ref_label(sf, m)}"
                        f" cast={cd.get('m_CastShadows')} recv={cd.get('m_ReceiveShadows')}"
                        f" dyn={cd.get('m_DynamicOccludee')}"
                        f" lp={cd.get('m_LightProbeUsage')} mv={cd.get('m_MotionVectors')}"
                        f" rp={cd.get('m_ReflectionProbeUsage')}"
                    )
            elif component.type.name == "Animation":
                ref = cd.get("m_Animation")
                out.append("  " * (depth + 1) + f"ANIM clip={ref_label(sf, ref)}")
        if transform is not None:
            td = transform.parse_as_dict()
            for child in td["m_Children"]:
                child_tf = sf.objects[child["m_PathID"]]
                child_go = sf.objects[
                    child_tf.parse_as_dict()["m_GameObject"]["m_PathID"]
                ]
                rec(child_go, depth + 1)

    rec(root_go, 0)
    return out


vanilla = dump_graph(shared, root, GAME_SCRIPT_INDEX)

import UnityPy

env = UnityPy.load(str(BUNDLE))
sf = next(f for f in env.file.files.values() if hasattr(f, "objects"))
manifest = next(o for o in sf.objects.values() if o.type.name == "AssetBundle")
mdata = manifest.read()
entry = next(i for p, i in mdata.m_Container if p.endswith(PREFAB))
prefab_go = sf.objects[entry.asset.m_PathID]
bundle = dump_graph(sf, prefab_go, SCRIPT_NAMES)

with open("/tmp/vanilla_graph.txt", "w") as f:
    f.write("\n".join(vanilla) + "\n")
with open("/tmp/bundle_graph.txt", "w") as f:
    f.write("\n".join(bundle) + "\n")

diff = list(difflib.unified_diff(vanilla, bundle, "vanilla", "bundle", lineterm=""))
if diff:
    print("DIFFERENCES:")
    for line in diff:
        print(line)
else:
    print("identical")
