"""Filesystem helpers shared by the pipeline.

:func:`_save_atomic` saves a finished result through a ``.part`` file
and atomically moves it into place with its source hash embedded, so a
result only ever exists in its complete form; :func:`copy` is the
print-on-copy used when the metadata bundles and the BepInEx tree are
assembled; :func:`_require_executable` checks the external executables
against ``PATH`` before a run needs them.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
from pathlib import Path

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from nikke_reborn.config import (
    CARDS_DIR,
    ITEM_VIEWER_HEIGHT,
    ITEM_VIEWER_WIDTH,
    PROBER,
    REPO_ROOT,
    SOURCE_HASH_KEY,
)
from nikke_reborn.error import GenerationError
from nikke_reborn.preset import Preset


def _require_executable(name: str) -> None:
    if shutil.which(name) is None:
        raise GenerationError(f"required executable not found in PATH: {name!r}")


def _save_atomic(
    image: Image.Image, out_path: Path, source_hash: str | None = None
) -> Path:
    """Save *image* to a ``.part`` file and atomically move it into place.

    A finished card therefore only ever exists in its complete form.
    *source_hash* is embedded as the SOURCE_HASH_KEY text chunk so a
    later run can tell the card is up to date.
    """
    tmp_path = out_path.with_name(out_path.name + ".part")
    pnginfo = None
    if source_hash is not None:
        pnginfo = PngInfo()
        pnginfo.add_text(SOURCE_HASH_KEY, source_hash)
    try:
        image.save(tmp_path, format="PNG", pnginfo=pnginfo)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    tmp_path.replace(out_path)
    return out_path


def copy(source: pathlib.Path, dest: pathlib.Path, overwrite=False):
    if dest.exists():
        if not overwrite:
            return

        if source.is_dir():
            for entry in source.iterdir():
                copy(entry, dest / entry.name, overwrite=True)

            return

    if dest.is_relative_to(REPO_ROOT):
        print(dest.relative_to(REPO_ROOT))
    else:
        print(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)
    source.copy(dest)


def _stored_hash(out_path: Path) -> str | None:
    """The SOURCE_HASH_KEY embedded in a finished card, or None when
    the file carries no readable tag (older cards, corrupt files)."""
    if out_path.suffix == ".png":
        try:
            with Image.open(out_path) as image:
                return image.info.get(SOURCE_HASH_KEY)
        except Exception:  # noqa: BLE001 — older/corrupt cards simply
            # carry no readable tag: treat the file as stale (None)
            return None
    try:
        result = subprocess.run(
            [
                PROBER,
                "-v",
                "error",
                "-show_entries",
                "format_tags",
                "-of",
                "json",
                str(out_path),
            ],
            capture_output=True,
            check=False,  # the exit code is checked below
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        return (
            json.loads(result.stdout)
            .get("format", {})
            .get("tags", {})
            .get(SOURCE_HASH_KEY)
        )
    except ValueError:
        return None


def _material_hash(
    template: Path,
    front_source: str = "",
    back_source: str = "",
    preset: Preset = Preset.DEFAULT,
) -> str:
    """The source hash of a finished pack image: the SHA-256 of its
    template, the output preset's scale (mixed in only when it deviates
    from 1.0, the full-resolution default, so a scale-1.0 material
    carries exactly the hash the code embedded before scales existed)
    and — when *front_source* / *back_source* are given — those hashes
    of the composed front's and back's inputs (see
    :func:`pack.front_source_hash` / :func:`pack.back_source_hash` /
    :func:`box.front_source_hash`), every input the result depends on.
    Using the front's and back's *inputs* rather than their pixels lets
    the hash be computed without rendering them."""
    digest = hashlib.sha256()
    if not template.is_file():
        raise GenerationError(f"pack template not found: {template}")
    digest.update(template.read_bytes())
    scale = preset.scale
    if scale != 1.0:
        digest.update(f"{scale:g}".encode())
    if front_source:
        digest.update(front_source.encode())
    if back_source:
        digest.update(back_source.encode())
    return digest.hexdigest()


def _material_output_up_to_date(
    template: Path,
    out_name: str,
    pack_dir: Path,
    front_source: str = "",
    back_source: str = "",
    force: bool = False,
    preset: Preset = Preset.DEFAULT,
) -> bool:
    """True when the pack's finished *out_name* already exists and its stored
    hash matches the current inputs (the template, the output preset's scale
    and the front's and back's *sources*) — computed without rendering the
    front or back, so their renders can be skipped when nothing has changed.
    Always False when *force* is set (everything is re-rendered). The output
    is looked up in the output preset's set folder
    (:meth:`Preset.set_path`)."""
    if force:
        return False
    pack_dir = pack_dir.resolve()
    out_path = preset.set_path(pack_dir.relative_to(CARDS_DIR).name) / out_name
    source_hash = _material_hash(
        template,
        front_source=front_source,
        back_source=back_source,
        preset=preset,
    )
    return out_path.is_file() and _stored_hash(out_path) == source_hash


def _viewer_hash(
    mesh: Path, material: Path, config: Path, preset: Preset = Preset.DEFAULT
) -> str:
    """SHA-256 of the item's inputs: the pack's mesh, its generated
    material (whose bytes change whenever the material does), the viewer
    configuration (model rotation and camera zoom/pan) and the output
    size — the viewer's defaults (:data:`ITEM_VIEWER_WIDTH` by
    :data:`ITEM_VIEWER_HEIGHT`) at the output preset's scale — the size
    term mixed in only when it deviates from the viewer's own defaults,
    so an item rendered at the defaults carries exactly the hash the
    code embedded before sizes existed, and a finished item whose stored
    hash matches them is up to date."""
    digest = hashlib.sha256()
    for path in (mesh, material, config):
        if not path.is_file():
            raise GenerationError(f"item input not found: {path}")
        digest.update(path.read_bytes())
    width = round(ITEM_VIEWER_WIDTH * preset.scale)
    height = round(ITEM_VIEWER_HEIGHT * preset.scale)
    if (width, height) != (ITEM_VIEWER_WIDTH, ITEM_VIEWER_HEIGHT):
        digest.update(f"{width}x{height}".encode())
    return digest.hexdigest()


def _viewer_output_up_to_date(
    mesh: Path,
    material: Path,
    config: Path,
    out_path: Path,
    force: bool = False,
    preset: Preset = Preset.DEFAULT,
) -> bool:
    """True when the viewer's finished *out_path* already exists and its
    stored hash matches the current *mesh*, *material*, *config* and
    output size (the viewer's defaults at the output preset's scale) —
    computed without rendering, so the render can be skipped when
    nothing has changed. A missing output or input (the material not
    generated yet) is simply not up to date. Always False when *force*
    is set (everything is re-rendered)."""
    if force:
        return False
    if not (
        mesh.is_file()
        and material.is_file()
        and config.is_file()
        and out_path.is_file()
    ):
        return False
    return _stored_hash(out_path) == _viewer_hash(mesh, material, config, preset)
