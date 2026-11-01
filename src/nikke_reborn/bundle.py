"""Compose the game bundle from the rendered output.

Builds the ``bundles/`` directory that ships with the mod: each set's
rendered cards and metadata bundle are copied in and turned into a Unity
asset bundle by :func:`nikke_reborn.bundler.build`, and the shop images
are laid out under the phone-app plugin.
"""

from __future__ import annotations

import shutil

from nikke_reborn import bundler, metadata
from nikke_reborn.config import (
    BUNDLES_DIR,
    CARDS_DIR,
    OUTPUT_DIR,
    SHOP_DIR,
    ULTRA_SUFFIX,
)
from nikke_reborn.file import copy

MOD_NAME = "NIKKE REBORN"


def run() -> None:
    shutil.rmtree(BUNDLES_DIR, ignore_errors=True)
    BUNDLES_DIR.mkdir()

    for target in sorted(OUTPUT_DIR.iterdir()):
        if not target.is_dir():
            continue
        if target.name.endswith(ULTRA_SUFFIX):
            # The ``<set> (Ultra)`` twins (the ultra run's set folders):
            # the bundles ship the default-resolution sets.
            continue

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

        prefab = plugins / MOD_NAME / f"{target.name}_prefabloader"
        plugin = prefab / target.name
        animator = plugins / "EPLCardAnimator" / "animated"

        if (CARDS_DIR / target.name).is_dir():
            videos = [
                file
                for file in (OUTPUT_DIR / target.name).iterdir()
                if file.name.endswith(".mp4")
            ]

            videos_dir = animator / f"{metadata.BUNDLE_NAME}_{target.name}"

            if videos:
                videos_dir.mkdir(parents=True)

            for video in videos:
                copy(video, videos_dir / video.name)

        copy(target.with_suffix(".json"), plugin.with_suffix(".json"))
        bundler.build(
            assets_dir=target,
            name=f"{metadata.BUNDLE_NAME}_{plugin.name}",
            output=plugin,
            root=OUTPUT_DIR,
        )
