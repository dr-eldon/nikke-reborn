"""The run's output preset: the resolution scale, the output root and
the video's encoding settings of one run. A run renders at one preset —
the default scale, the native resolution (ultra) or a draft (the
default's scale, a faster encode, the ``draft/`` output root) — and the
preset carries everything that depends on the mode, so the pipeline
threads one value instead of a triple."""

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

DEFAULT_X264_PRESET = "slow"
DRAFT_X264_PRESET = "ultrafast"


class Preset(Enum):
    """The run's output preset."""

    DEFAULT = "default"
    DRAFT = "draft"
    ULTRA = "ultra"

    @property
    def base(self) -> Path:
        return DRAFT_DIR if self is Preset.DRAFT else OUTPUT_DIR

    @property
    def scale(self) -> float:
        return ULTRA_SCALE if self is Preset.ULTRA else DEFAULT_SCALE

    @property
    def x264_preset(self) -> str:
        return DRAFT_X264_PRESET if self is Preset.DRAFT else DEFAULT_X264_PRESET

    def set_name(self, set_name: str) -> str:
        return f"{set_name}{ULTRA_SUFFIX}" if self is Preset.ULTRA else set_name

    def set_path(self, set_name: str) -> Path:
        return self.base / self.set_name(set_name)
