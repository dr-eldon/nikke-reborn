"""The run's output preset: the resolution scale, the output root and
the video's encoding settings of one run. A run renders at one preset —
the default scale, the native resolution (ultra), a draft (the
default's scale, a faster encode, the ``draft/`` output root) or low
(the default's settings at a lower framerate, the ``<set> (Low)`` set
folders) — and the preset carries
everything that depends on the mode, so the pipeline threads one value
instead of a triple."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from nikke_reborn.config import DRAFT_DIR, OUTPUT_DIR

#: The default preset's scale (a draft renders at it).
DEFAULT_SCALE = 0.5

#: The ultra preset's scale: the native resolution.
ULTRA_SCALE = 2.0 * DEFAULT_SCALE

#: The ultra run's set-folder name suffix.
ULTRA_SUFFIX = " (Ultra)"

#: The low run's set-folder name suffix.
LOW_SUFFIX = " (Low)"

DEFAULT_X264_PRESET = "slow"
DRAFT_X264_PRESET = "ultrafast"

DEFAULT_FRAMERATE = 60
LOW_FRAMERATE = 30


class Preset(Enum):
    """The run's output preset."""

    DEFAULT = "default"
    DRAFT = "draft"
    ULTRA = "ultra"
    LOW = "low"

    @property
    def base(self) -> Path:
        return DRAFT_DIR if self is Preset.DRAFT else OUTPUT_DIR

    @property
    def scale(self) -> float:
        return ULTRA_SCALE if self is Preset.ULTRA else DEFAULT_SCALE

    @property
    def x264_preset(self) -> str:
        return DRAFT_X264_PRESET if self is Preset.DRAFT else DEFAULT_X264_PRESET

    @property
    def framerate(self) -> int:
        return LOW_FRAMERATE if self is Preset.LOW else DEFAULT_FRAMERATE

    @property
    def suffix(self) -> str:
        return (
            ULTRA_SUFFIX
            if self is Preset.ULTRA
            else LOW_SUFFIX
            if self is Preset.LOW
            else ""
        )

    def set_name(self, set_name: str) -> str:
        return f"{set_name}{self.suffix}"

    @classmethod
    def strip_suffix(cls, set_name: str) -> str:
        """The base set name a run's set folder belongs to (the
        run-mode's suffix removed)."""
        for preset in cls:
            stripped = set_name.removesuffix(preset.suffix)
            if stripped != set_name:
                return stripped
        return set_name

    def set_path(self, set_name: str) -> Path:
        return self.base / self.set_name(set_name)
