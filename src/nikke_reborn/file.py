"""Filesystem helpers shared by the pipeline.

:func:`_save_atomic` saves a finished result through a ``.part`` file
and atomically moves it into place with its source hash embedded, so a
result only ever exists in its complete form; :func:`copy` is the
print-on-copy used when the metadata bundles and the BepInEx tree are
assembled; :func:`_require_executable` checks the external executables
against ``PATH`` before a run needs them.
"""

from __future__ import annotations

import pathlib
import shutil
from pathlib import Path

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from nikke_reborn.config import REPO_ROOT, SOURCE_HASH_KEY
from nikke_reborn.error import GenerationError


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
