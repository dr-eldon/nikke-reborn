"""Compose the game bundle from the rendered output.

Builds the ``bundles/`` directory that ships with the mod: each set's
rendered cards and metadata bundle are copied in and turned into a Unity
asset bundle by :func:`nikke_reborn.bundler.build`, and the shop images
are laid out under the phone-app plugin. Every set folder under the output
root is bundled -- the ``<set> (Ultra)`` twins included -- so a set's
native-resolution cards ship as a ``<mod> - <set> (Ultra)`` folder
alongside the default one, with the same structure and the set's own
(un-suffixed) internal names.
"""

from __future__ import annotations

import argparse
import shutil

from nikke_reborn import bundler, metadata
from nikke_reborn.config import BUNDLES_DIR, CARDS_DIR, OUTPUT_DIR, SHOP_DIR
from nikke_reborn.file import copy
from nikke_reborn.preset import ULTRA_SUFFIX

MOD_NAME = "NIKKE REBORN"


def run() -> None:
    """Compose the game bundle from the rendered output."""
    # No options (the bundle always covers every set under output/); the
    # parser is here so --help works and a stray flag fails loudly instead
    # of silently triggering a full bundle build.
    argparse.ArgumentParser(
        prog="bundle",
        description=(
            "Compose the game bundle from the rendered output: every set "
            "folder under output/ (the default and the '<set> (Ultra)' "
            "twins) is copied in and turned into a Unity asset bundle under "
            "bundles/"
        ),
    ).parse_args()

    shutil.rmtree(BUNDLES_DIR, ignore_errors=True)
    BUNDLES_DIR.mkdir()

    for target in sorted(OUTPUT_DIR.iterdir()):
        if not target.is_dir():
            continue

        # The set the bundle's identity is named after: the output folder's
        # own name, minus the ultra run's " (Ultra)" twin suffix. The ultra
        # twins (``<set> (Ultra)``) bundle alongside the default sets -- the
        # same structure and names (the ultra metadata's BundleId is the
        # base name, not the suffixed one), carrying the native-resolution
        # content.
        set_name = target.name.removesuffix(ULTRA_SUFFIX)

        bundle = BUNDLES_DIR / f"{MOD_NAME} - {target.name}"
        bundle.mkdir(parents=True)

        plugins = bundle / "BepInEx" / "plugins"

        for file in ["Shop_Icon.png", "Shop_IBG.png", "Shop_OBG.png"]:
            copy(
                SHOP_DIR / file,
                plugins
                / "Phone - Overhaul"
                / "App Images"
                / f"{metadata.BUNDLE_NAME}"
                / file,
            )

        prefab = plugins / MOD_NAME / f"{set_name}_prefabloader"
        plugin = prefab / set_name
        animator = plugins / "EPLCardAnimator" / "animated"

        if (CARDS_DIR / f"{set_name}.toml").is_file():
            videos = [
                file
                for file in (OUTPUT_DIR / target.name).iterdir()
                if file.name.endswith(".mp4")
            ]

            videos_dir = animator / f"{metadata.BUNDLE_NAME}_{set_name}"

            if videos:
                videos_dir.mkdir(parents=True)

            for video in videos:
                copy(video, videos_dir / video.name)

        copy(target.with_suffix(".json"), plugin.with_suffix(".json"))
        bundler.build(
            assets_dir=target,
            name=f"{metadata.BUNDLE_NAME}_{set_name}",
            output=plugin,
            set_name=set_name,
        )
