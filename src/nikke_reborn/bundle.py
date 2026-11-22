"""Compose the game bundle from the rendered output.

Builds the ``bundles/`` directory that ships with the mod: each set's
rendered cards and metadata bundle are copied in and turned into a Unity
asset bundle by :func:`nikke_reborn.bundler.build`, the shop images are
laid out under the phone-app plugin, and the set's BepInEx tree is
zipped into one archive per set (the ``BepInEx`` folder at the
archive's root). Every set folder under the output root is bundled —
the suffixed run-modes' twins (``<set> (Ultra)``, ``<set> (Low)``)
included — so a set's native-resolution and low-framerate cards ship
alongside the default one, with the same structure and the set's own
(un-suffixed) internal names.
"""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

from nikke_reborn import bundler
from nikke_reborn.config import BUNDLES_DIR, MOD_NAME, OUTPUT_DIR, SHOP_DIR
from nikke_reborn.file import copy
from nikke_reborn.preset import Preset, spaced


def run() -> None:
    """Compose the game bundle from the rendered output."""
    # No options (the bundle always covers every set under output/); the
    # parser is here so --help works and a stray flag fails loudly instead
    # of silently triggering a full bundle build.
    argparse.ArgumentParser(
        prog="bundle",
        description=(
            "Compose the game bundle from the rendered output: every set "
            "folder under output/ (the default and the run-modes' twins, "
            "'<set> (Ultra)' and '<set> (Low)') is copied in and turned "
            "into a Unity asset bundle, and the set's BepInEx tree is "
            "zipped into one archive per set under bundles/"
        ),
    ).parse_args()

    BUNDLES_DIR.mkdir(exist_ok=True)

    for target in sorted(OUTPUT_DIR.iterdir()):
        if not target.is_dir():
            continue

        # The set the bundle's identity is named after: the output
        # folder's own name, minus its run-mode's twin suffix (the
        # twins carry the set's own internal names).
        number, variant = target.name.split("_", 1)
        set_name = Preset.strip_suffix(variant)

        # The bundle's identity comes from the set's metadata bundle
        # (the JSON copied in below): its asset-bundle name (the game
        # resolves the assets by it) and the phone app's id (the shop
        # images' folder).
        bundle_json = json.loads(
            target.with_name(f"{number}_{set_name}.json").read_text(encoding="utf-8")
        )
        bundle_id = bundle_json["BundleId"]
        app_id = bundle_json["CustomShops"][0]["PhoneAppId"]

        bundle = BUNDLES_DIR / f"{MOD_NAME} - {spaced(variant)}"

        if bundle.with_suffix(".zip").is_file():
            print(f"{bundle.name} already bundled. Skipping...")
            continue

        shutil.rmtree(bundle, ignore_errors=True)
        bundle.mkdir(parents=True)

        plugins = bundle / "BepInEx" / "plugins"

        for file in ["Shop_Icon.png", "Shop_IBG.png", "Shop_OBG.png"]:
            copy(
                SHOP_DIR / file,
                plugins / "Phone - Overhaul" / "App Images" / app_id / file,
            )

        prefab = plugins / MOD_NAME / f"{set_name}_prefabloader"
        plugin = prefab / set_name
        animator = plugins / "EPLCardAnimator" / "animated"

        videos = [
            file
            for file in (OUTPUT_DIR / target.name).iterdir()
            if file.name.endswith(".mp4")
        ]

        videos_dir = animator / bundle_id

        if videos:
            videos_dir.mkdir(parents=True)

        for video in videos:
            copy(video, videos_dir / video.name)

        copy(
            target.with_name(f"{number}_{set_name}.json"),
            plugin.with_suffix(".json"),
        )
        bundler.build(
            assets_dir=target,
            name=bundle_id,
            output=plugin,
            set_name=set_name,
        )

        zip_directory(bundle, BUNDLES_DIR / f"{bundle.name}.zip")
        shutil.rmtree(bundle)


def zip_directory(directory: Path, archive: Path) -> None:
    """Zip `directory`'s tree into `archive`, rooted at `directory`
    (the ``BepInEx`` folder at the archive's root)."""
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file in sorted(directory.rglob("*")):
            if file.is_file():
                zip_file.write(file, file.relative_to(directory).as_posix())
