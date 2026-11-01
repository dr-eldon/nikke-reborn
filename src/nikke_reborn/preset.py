"""The run's output preset: its resolution scale, its output root and
its video's encoding settings.

A run renders at one preset -- the default half resolution, the native
(ultra) resolution, or a draft (the default's scale, the draft's x264
preset, the ``draft/`` output root) -- and the preset carries everything
that depends on the mode: the run's scale (the definition's viewport at
this scale is the run's final size -- the final size drives the whole
pipeline), the set's output path (``draft/<set>`` for a draft,
``output/<set>`` by default, ``output/<set> (Ultra)`` under ultra) and
the video's encoding settings (the x264 preset -- ``ultrafast`` for a
draft, ``slow`` otherwise). The pipeline therefore threads one value
(the preset) instead of a scale, an output root and an x264-preset
triple.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from nikke_reborn.config import DRAFT_DIR, OUTPUT_DIR

#: The default preset's output scale: half the definition's native
#: viewport. (A draft renders at the default's scale.)
DEFAULT_SCALE = 0.5

#: The ultra preset's output scale: twice the default -- the native
#: resolution (the legacy default before scales existed). Written as a
#: multiple of the default so the "2x" is explicit.
ULTRA_SCALE = 2.0 * DEFAULT_SCALE

#: Suffix appended to each set's output folder name for an ultra run
#: (``output/<set>/`` -> ``output/<set> (Ultra)/``).
ULTRA_SUFFIX = " (Ultra)"

#: The x264 encoder preset per run mode: ``slow`` by default and
#: ``ultrafast`` for a draft.
DEFAULT_X264_PRESET = "slow"
DRAFT_X264_PRESET = "ultrafast"


class Preset(Enum):
    """The run's output preset (see the module docstring)."""

    DEFAULT = "default"
    DRAFT = "draft"
    ULTRA = "ultra"

    @property
    def base(self) -> Path:
        """The preset's output root: ``draft/`` for a draft run,
        ``output/`` otherwise."""
        return DRAFT_DIR if self is Preset.DRAFT else OUTPUT_DIR

    @property
    def scale(self) -> float:
        """The preset's output scale: half the definition's native
        viewport by default and for a draft, the native resolution
        (twice the default) under ultra."""
        return ULTRA_SCALE if self is Preset.ULTRA else DEFAULT_SCALE

    @property
    def x264_preset(self) -> str:
        """The video's x264 encoding preset: ``ultrafast`` for a draft,
        ``slow`` otherwise."""
        return DRAFT_X264_PRESET if self is Preset.DRAFT else DEFAULT_X264_PRESET

    def set_name(self, set_name: str) -> str:
        """The set's output folder name: ``<set>``, or ``<set> (Ultra)``
        under ultra."""
        return f"{set_name}{ULTRA_SUFFIX}" if self is Preset.ULTRA else set_name

    def set_path(self, set_name: str) -> Path:
        """The set's output folder: ``<base>/<set>`` -- ``output/<set>``
        by default, ``draft/<set>`` for a draft, ``output/<set>
        (Ultra)`` under ultra."""
        return self.base / self.set_name(set_name)
