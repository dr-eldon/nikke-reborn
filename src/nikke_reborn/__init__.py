"""Pack-opening simulation, sprite sheets and the game bundle for NIKKE
REBORN.

Three commands (the ``[project.scripts]`` entry points): ``bundle`` composes
the BepInEx bundles the mod ships (every set's rendered cards and its
metadata bundle, under ``bundles/``); ``simulate`` opens packs of an
expansion's bundle — ``output/<set>.json``, what the Rust ``generate``
pipeline writes — and writes a self-contained HTML report with the
statistics for fine-tuning the pack odds and the card prices;
``spritesheet`` composes the expansion's rendered first frames into a
summary grid and paged sheets. The cards' rendering and the bundles'
metadata live in the Rust crate (this repository) and ``pikke``.
"""
