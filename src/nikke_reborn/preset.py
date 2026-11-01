"""The run's output preset: its resolution scale and set output folder.

A run renders at one preset — the default half resolution, or the
native (ultra) resolution — and the preset carries everything that
depends on the mode: the run's scale (the definition's viewport at
this scale is the run's final size — the final size drives the whole
pipeline) and the set's output folder name (``<set>``, or
``<set> (Ultra)`` under ultra). The pipeline therefore threads one
value (the preset) instead of a scale and a folder-suffix pair.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

#: The default preset's output scale: half the definition's native
#: viewport. (The draft's scale is the default's: a draft run is a
#: plain default-preset run in ``draft/`` with the draft x264 preset.)
DEFAULT_SCALE = 0.5

#: The ultra preset's output scale: twice the default — the native
#: resolution (the legacy default before scales existed). Written as a
#: multiple of the default so the "2x" is explicit.
ULTRA_SCALE = 2.0 * DEFAULT_SCALE

#: Suffix appended to each set's output folder name for an ultra run
#: (``output/<set>/`` -> ``output/<set> (Ultra)/``).
ULTRA_SUFFIX = " (Ultra)"


class Preset(Enum):
    """The run's output preset (see the module docstring)."""

    DEFAULT = "default"
    ULTRA = "ultra"

    @property
    def scale(self) -> float:
        """The preset's output scale: half the definition's native
        viewport by default, the native resolution (twice the default)
        under ultra."""
        return ULTRA_SCALE if self is Preset.ULTRA else DEFAULT_SCALE

    def set_name(self, set_name: str) -> str:
        """The set's output folder name: ``<set>``, or ``<set> (Ultra)``
        under ultra."""
        return f"{set_name}{ULTRA_SUFFIX}" if self is Preset.ULTRA else set_name

    def set_path(self, out_base: Path, set_name: str) -> Path:
        """The set's output folder under *out_base* (see
        :meth:`set_name`): ``<out>/<set>``, or ``<out>/<set> (Ultra)``
        under ultra."""
        return out_base / self.set_name(set_name)
