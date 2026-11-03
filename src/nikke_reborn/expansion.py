"""The expansion's source of truth and the shared front composition.

One TOML per expansion (``cards/<expansion>.toml``) is the single input
for its NIKKES (``cards`` — the viewer ids, in order; the card's stem is
its 1-based position plus the compact name from the game's data), its
rarities (``rarities`` — the subset of the presentations' names the set
generates, in the order the set carries them), its pack/box materials
(``pack`` — the featured characters, ``background`` — the
base/special/battle backgrounds, ``logo``) and its card names (the title
from ``characters.json``, the subtitle from ``models.json``). Every
character renders the expansion's ``rarities`` subset of the fixed set
of presentations (see :func:`presentations_for`): the standard tier,
the profile tier and the full-art tier.

The pack's front and the box's front are the same composition — the
expansion's background, the featured NIKKES drawn over it (backs first,
the hero on top), and the expansion's logo with its glow on top — so
the composition lives here, shared by :mod:`nikke_reborn.pack` and
:mod:`nikke_reborn.box`, which add only their own pieces (the material
template's sizing, their white NIKKE logo placement and their
background fit). Only ``nikke-viewer``'s output is used for the
featured NIKKES (their still frame, read off ``--stdout``).

The front's inputs — the expansion's file, the featured characters it
lists, its background, its logo, the white NIKKE logo, and the material
template that sizes it — are hashed (see :func:`front_source_digest`)
into the finished material, so when those inputs are unchanged the
front's render is skipped entirely rather than re-rendered.
"""

from __future__ import annotations

import colorsys
import hashlib
import io
import json
import subprocess
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from PIL import Image, ImageChops, ImageFilter

from nikke_reborn.config import (
    CARD_VIEWPORT,
    CARDS_DIR,
    DATABASE_DIR,
    REPO_ROOT,
    VIEWER,
)
from nikke_reborn.error import GenerationError
from nikke_reborn.file import hash_term
from nikke_reborn.video import _PipeDrain, _read_exact, _reap_viewer

# --- front composition tuning (fractions of the front) ----------------------
# Every NIKKE's feet sit on the front's bottom edge, so no one floats or
# gets clipped. The hero is the first featured NIKKE: centered, the
# largest, in front; the remaining NIKKES read as a group behind it
# (smaller — the depth cue — and pushed to the left and right).
HERO_HEIGHT = 0.78  # the hero's body height (front-height fraction)
HERO_FEET_Y = 1.0  # the hero's feet baseline (the bottom edge)
BACK_HEIGHT = 0.42  # the group's body height fraction (base, before per-tier shrink)
BACK_FEET_Y = 1.0  # the group's feet baseline (the bottom edge)
BACK_OFFSET_X = 0.34  # the first flank's center offset from the middle (width fraction)
BACK_TIER_GAP = 0.5  # each further tier on a side steps out by this fraction
BACK_TIER_SHRINK = 0.9  # each further tier shrinks by this factor
ALPHA_TRIM = 24  # alpha threshold (0-255) for the content bounding box

# --- expansion logo tuning --------------------------------------------------
# The expansion's logo is composited over the front with a glow, at its
# ``logo.placement``; every value is relative to the front, so it is the
# same for every expansion. The glow is tinted by the front's own
# background color (its hue and saturation, brightened), so the bloom
# matches the scene rather than a fixed white.
LOGO_WIDTH = 0.5  # the logo's width (front-width fraction; the box's front
# sizes by height — compose_front's expansion_logo_height)
LOGO_MARGIN = 0.05  # gap from the front's top/bottom edge (height fraction)
LOGO_GLOW_RADIUS = 0.012  # glow blur radius (front-height fraction)
LOGO_GLOW_INTENSITY = 1.0  # glow strength (alpha multiplier of the halo)
LOGO_GLOW_VALUE = 0.9  # target brightness of the glow tint (0-1)
LOGO_TRAIL = 0.008  # the solid trail: the mark's own silhouette in a
# darkened glow tint, offset down-right by this fraction of the mark's
# height — a tight drop-shadow that reads as a small trail
LOGO_TRAIL_DARKEN = 0.7  # the trail's tint darkened relative to the glow's
LOGO_PLACEMENTS = ("top", "center", "bottom")  # values for the `logo.placement` field

#: The keys every expansion's ``background`` table must carry (relative
#: paths, against the expansion's folder).
BACKGROUND_KEYS = ("base", "special", "battle")

#: An event's rarity (fixed, the game's top one — it carries the set's
#: highest).
EVENT_RARITY = "SSR"

# --- the presentations --------------------------------------------------------
#: The fixed per-character set of presentations, in the order the passes
#: run (the standard tier, the profile tier, the full-art tier). Each
#: row: the presentation's name (the output's suffix), its tier, the
#: viewer's ``--variant``, the ``--animation`` (None — the viewer's
#: default; REEL — the reel's pick, resolved at selection time), the
#: ``--time`` (0 — a still, None — the loop), the ``--half-body``
#: framing, the background's key (or ``black``), the composite's mask
#: (or None) and the two-stream profile flag.
REEL = "reel"

#: The photo reel's candidate animations (the first
#: :data:`PROFILE_REEL_COUNT` the character has, in this order, become
#: the reel's stills) and the ``Special`` presentations' animation (the
#: first the character has).
PROFILE_REEL_ANIMATIONS = (
    "think",
    "smile",
    "shy",
    "no",
    "delight",
    "surprise",
    "special_02",
    "special",
    "angry",
)
PROFILE_REEL_COUNT = 3

_PresentationSpec = tuple[
    str,  # the presentation's name (the output's suffix)
    str,  # the tier (standard | profile | full)
    str | None,  # the viewer's --variant
    str | None,  # the viewer's --animation (None = default; REEL = the pick)
    float | None,  # the viewer's --time (0 = a still, None = the loop)
    bool,  # the --half-body framing
    str,  # the background's key (base | special | battle | black)
    str | None,  # the composite's mask (standard | profile | None)
    bool,  # the two-stream profile (face + body)
]

PRESENTATION_SPECS: tuple[_PresentationSpec, ...] = (
    ("ClassicStandard", "standard", None, None, 0.0, True, "base", "standard", False),
    (
        "SpecialStandard",
        "standard",
        None,
        REEL,
        0.0,
        True,
        "special",
        "standard",
        False,
    ),
    (
        "ExoticStandard",
        "standard",
        None,
        "action",
        None,
        True,
        "base",
        "standard",
        False,
    ),
    ("ClassicProfile", "profile", None, None, 0.0, False, "base", "profile", True),
    ("IdleProfile", "profile", None, "idle", None, False, "base", "profile", True),
    ("CoverProfile", "profile", "cover", None, None, False, "battle", "profile", True),
    ("AimProfile", "profile", "aim", None, None, False, "battle", "profile", True),
    ("Classic", "full", None, None, 0.0, True, "base", None, False),
    ("Idle", "full", None, "idle", None, True, "base", None, False),
    ("Cover", "full", "cover", None, None, False, "battle", None, False),
    ("Aim", "full", "aim", None, None, False, "battle", None, False),
    ("Special", "full", None, REEL, 0.0, True, "special", None, False),
    ("Exotic", "full", None, "action", None, True, "base", None, False),
    ("Goddess", "full", "sc", "main", None, False, "black", None, False),
)

#: The event-only presentations: valid in a set's ``rarities`` but
#: rendered only by the event (a single full-art presentation on the
#: ``black`` background) — the characters never take them.
EVENT_ONLY_PRESENTATIONS: tuple[_PresentationSpec, ...] = (
    ("Classified", "full", None, None, None, False, "black", None, False),
)

#: The tiers a run's passes render (the ``--no-<tier>`` flags).
TIERS = ("standard", "profile", "full")


@dataclass(frozen=True)
class CardEntry:
    """One card of an expansion: its viewer id, its 1-based position
    in the expansion's ``cards`` (the card's number), the card's stem
    (``<number>_<id>_<name>``, the 1-based number, the viewer id and
    the compact — whitespace-free — name), the name it renders (the
    title, and the subtitle when the character is a skin), the rarity
    and manufacturer the game's data carry (the base character's when
    the id is suffixed; the event's fixed rarity and none for an event
    — an id that is not a character), and the per-presentation viewer
    framing overrides its ``cards`` table names (each a presentation's
    ``x``/``y``/``zoom``, plumbed to the viewer's ``--x``/``--y``/
    ``--zoom``)."""

    id: str
    number: int
    stem: str
    title: str
    subtitle: str
    rarity: str
    manufacturer: str | None
    framings: dict[str, dict[str, int | float]] = field(default_factory=dict)

    @property
    def name(self) -> str:
        """The character's display name (the bundle's ``Name``): the
        title, or the title and the subtitle."""
        return f"{self.title}: {self.subtitle}" if self.subtitle else self.title


@dataclass(frozen=True)
class Featured:
    """A featured character on the expansion's front: its viewer id, an
    optional horizontal nudge (*x*, in the material's native pixels, so
    it scales with the material; negative *x* nudges it left) applied to
    the character's position before it is composited, and
    per-character render overrides for its frame: *animation* (the
    viewer's default when absent), *time* (the second of that animation
    to still on; 0 when absent) and *zoom* (a multiplier on the framing;
    the viewer's default when absent)."""

    id: str
    x: int | float = 0
    animation: str | None = None
    time: int | float = 0
    zoom: int | float | None = None


@dataclass(frozen=True)
class Expansion:
    """A loaded ``cards/<expansion>.toml``: its rarities (the subset of
    the presentations' names the set generates, in the order the set
    carries them), its pack's featured characters, its cards (in file
    order), its backgrounds' paths (the ``background`` table's keys,
    relative to the expansion's folder) and its logo's path and
    placement."""

    path: Path
    name: str
    rarities: tuple[str, ...]
    pack: tuple[Featured, ...]
    cards: tuple[CardEntry, ...]
    backgrounds: dict[str, str]
    logo_path: str
    logo_placement: str


@dataclass(frozen=True)
class Presentation:
    """One presentation of one card (a row of the run's work): what the
    viewer renders (the variant, the animation, the time, and the
    presentation's *x*/*y*/*zoom* framing overrides when the TOML names
    them), how the frame composites (the background's key, the mask, the
    framing — the half-body flag or the two-stream profile) and where its
    output goes (the presentation's name, the output's suffix)."""

    expansion: Expansion
    card: CardEntry
    name: str
    tier: str
    variant: str | None
    animation: str | None
    time: float | None
    half_body: bool
    background: str
    mask: str | None
    face: bool
    x: int | float | None = None
    y: int | float | None = None
    zoom: int | float | None = None

    @property
    def animated(self) -> bool:
        """True when the render loops (an MP4, with its first-frame
        PNG): ``time`` is None."""
        return self.time is None

    @property
    def label(self) -> str:
        """The presentation's name in the run's messages (and errors):
        ``<card's stem> (<presentation>)``."""
        return f"{self.card.stem} ({self.name})"

    @property
    def rarity_index(self) -> int:
        """The presentation's 1-based position in the set's ``rarities``
        (its index in the set's rarity order, the output's prefix)."""
        return self.expansion.rarities.index(self.name) + 1


@dataclass(frozen=True)
class CharacterInfo:
    """What the viewer reports for one character: the variants it renders
    (the ``sc`` variant decides the goddess presentation) and the
    profile-reel's animation (the first of
    :data:`PROFILE_REEL_ANIMATIONS` it has — the ``Special``
    presentations' animation; a character with none has no
    ``Special`` presentations)."""

    variants: frozenset[str]
    reel: str | None


# --- the game's data ----------------------------------------------------------
# The characters' names, rarities and manufacturers (characters.json)
# and the models' names (models.json), read once per process (each
# worker reloads them).
_CHARACTERS: dict[str, Any] | None = None
_MODELS: dict[str, str] | None = None


def _characters_db() -> dict[str, Any]:
    global _CHARACTERS
    if _CHARACTERS is None:
        with (DATABASE_DIR / "characters.json").open(encoding="utf-8") as handle:
            _CHARACTERS = {
                character["id"]: character
                for character in json.load(handle)
                if isinstance(character, dict) and "id" in character
            }
    return _CHARACTERS


def _models_db() -> dict[str, str]:
    global _MODELS
    if _MODELS is None:
        with (DATABASE_DIR / "models.json").open(encoding="utf-8") as handle:
            _MODELS = {
                model["id"]: str(model["name"])
                for model in json.load(handle)
                if isinstance(model, dict) and "id" in model and "name" in model
            }
    return _MODELS


# --- the expansion's file ------------------------------------------------------


def load_expansion(path: Path) -> Expansion:
    """Parse and validate one expansion's TOML (its ``rarities``, its
    ``pack``, its ``cards``, its ``background`` table and its ``logo``),
    deriving each card's stem from its position and the game's data (see
    :func:`_card_entry`). Every referenced file must exist; the
    character ids must be in the game's data (the base character when
    the id is suffixed), the models must be named after their character
    (the subtitle is the model's name minus the character's) and the
    ``rarities`` entries must be names of the fixed presentations (no
    duplicates; the event-only ones among them render only for the
    event)."""
    path = path.resolve()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        try:
            shown = path.relative_to(REPO_ROOT)
        except ValueError:
            shown = path
        raise GenerationError(f"cannot read {shown}: {exc}") from exc

    rarities_data = data.get("rarities")
    if (
        not isinstance(rarities_data, list)
        or not rarities_data
        or not all(isinstance(name, str) for name in rarities_data)
    ):
        raise GenerationError(
            f"{path.name}: 'rarities' must be a non-empty list of the "
            "presentations' names"
        )
    known = [name for name, *_ in (*PRESENTATION_SPECS, *EVENT_ONLY_PRESENTATIONS)]
    unknown = [name for name in rarities_data if name not in known]
    if unknown:
        raise GenerationError(
            f"{path.name}: unknown presentation name(s) in 'rarities': "
            f"{', '.join(unknown)} (the known ones: {', '.join(known)})"
        )
    if len(set(rarities_data)) != len(rarities_data):
        raise GenerationError(
            f"{path.name}: duplicate presentation names in 'rarities'"
        )

    pack = data.get("pack")
    if (
        not isinstance(pack, list)
        or not pack
        or not all(
            isinstance(entry, dict) and isinstance(entry.get("id"), str)
            for entry in pack
        )
    ):
        raise GenerationError(
            f"{path.name}: 'pack' must be a non-empty list of tables, each with an 'id'"
        )
    featured: list[Featured] = []
    for entry in pack:
        char_id = entry["id"]
        x = entry.get("x", 0)
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            raise GenerationError(
                f"{path.name}: 'pack' entry for {char_id!r} carries a "
                f"non-numeric 'x' nudge: {x!r}"
            )
        animation = entry.get("animation")
        if animation is not None and not isinstance(animation, str):
            raise GenerationError(
                f"{path.name}: 'pack' entry for {char_id!r} carries a "
                f"non-string 'animation': {animation!r}"
            )
        time = entry.get("time", 0)
        if isinstance(time, bool) or not isinstance(time, (int, float)):
            raise GenerationError(
                f"{path.name}: 'pack' entry for {char_id!r} carries a "
                f"non-numeric 'time': {time!r}"
            )
        zoom = entry.get("zoom")
        if zoom is not None and (
            isinstance(zoom, bool) or not isinstance(zoom, (int, float))
        ):
            raise GenerationError(
                f"{path.name}: 'pack' entry for {char_id!r} carries a "
                f"non-numeric 'zoom': {zoom!r}"
            )
        featured.append(
            Featured(id=char_id, x=x, animation=animation, time=time, zoom=zoom)
        )

    cards_data = data.get("cards")
    if (
        not isinstance(cards_data, list)
        or not cards_data
        or not all(
            isinstance(entry, dict) and isinstance(entry.get("id"), str)
            for entry in cards_data
        )
    ):
        raise GenerationError(
            f"{path.name}: 'cards' must be a non-empty list of tables, "
            "each with an 'id'"
        )
    ids = [entry["id"] for entry in cards_data]
    if len(set(ids)) != len(ids):
        raise GenerationError(f"{path.name}: duplicate character ids in 'cards'")

    backgrounds = data.get("background")
    if not isinstance(backgrounds, dict) or any(
        not isinstance(backgrounds.get(key), str) for key in BACKGROUND_KEYS
    ):
        raise GenerationError(
            f"{path.name}: 'background' must be a table with a path for "
            f"every key: {', '.join(BACKGROUND_KEYS)}"
        )
    for key in BACKGROUND_KEYS:
        if not (path.parent / backgrounds[key]).resolve().is_file():
            raise GenerationError(
                f"{path.name}: background.{key} not found: {backgrounds[key]}"
            )

    logo = data.get("logo")
    if not isinstance(logo, dict) or not isinstance(logo.get("path"), str):
        raise GenerationError(
            f"{path.name}: 'logo' must be a table with a 'path' and a 'placement'"
        )
    if logo.get("placement") not in LOGO_PLACEMENTS:
        raise GenerationError(
            f"{path.name}: unknown logo placement {logo.get('placement')!r}; "
            f"expected one of {', '.join(LOGO_PLACEMENTS)}"
        )
    if not (path.parent / logo["path"]).resolve().is_file():
        raise GenerationError(f"{path.name}: logo not found: {logo['path']}")

    top = rarities_data[-1]
    return Expansion(
        path=path,
        name=path.stem,
        rarities=tuple(rarities_data),
        pack=tuple(featured),
        cards=tuple(
            _card_entry(
                path.name,
                number,
                entry["id"],
                _event_framings(entry, top)
                if is_event(entry["id"])
                else _card_framings(entry),
                EVENT_RARITY,
            )
            for number, entry in enumerate(cards_data, 1)
        ),
        backgrounds=dict(backgrounds),
        logo_path=logo["path"],
        logo_placement=logo["placement"],
    )


def is_event(char_id: str) -> bool:
    """True when the id is an event illustration CG (not a character: it
    does not start with ``c``)."""
    return not char_id.startswith("c")


def _event_framings(entry: dict, name: str) -> dict[str, dict[str, int | float]]:
    """The event's framing override (its top-level ``x``/``y``/``zoom``,
    its single presentation's), keyed by the presentation's name (the
    set's highest)."""
    framing = {key: entry[key] for key in ("x", "y", "zoom") if key in entry}
    return {name: framing} if framing else {}


def _spec_background(presentation: str) -> str:
    """The spec named *presentation*'s background key: an event's
    full-art presentation renders on its highest presentation's
    background (the event-only ones' — ``black``)."""
    for (
        name,
        _tier,
        _variant,
        _animation,
        _time,
        _half_body,
        background,
        _mask,
        _face,
    ) in (*PRESENTATION_SPECS, *EVENT_ONLY_PRESENTATIONS):
        if name == presentation:
            return background
    raise GenerationError(f"no presentation spec for {presentation!r}")


def _card_framings(entry: dict) -> dict[str, dict[str, int | float]]:
    """The character's per-presentation framing overrides: each non-``id``
    key of its ``cards`` table is a presentation name mapped to its viewer
    framing terms (``x``/``y``/``zoom``), plumbed raw to the viewer's
    ``--x``/``--y``/``--zoom``."""
    return {
        name: dict(table)
        for name, table in entry.items()
        if name != "id" and isinstance(table, dict)
    }


def _card_entry(
    file_name: str,
    number: int,
    char_id: str,
    framings: dict[str, dict[str, int | float]],
    highest_rarity: str,
) -> CardEntry:
    """The card's identity derived from *char_id*'s position and the
    game's data (the event's from ``models.json`` alone): the title
    (the character's name — the base character's when the id is suffixed;
    the event's model's name), the subtitle (the model's name minus the
    character's, empty when the model is the character itself or when the
    card is an event), the stem (the 1-based number plus the compact name)
    and the rarity/manufacturer (the character's own, the base's when the
    id is suffixed; the event's fixed rarity and none for an event)."""
    if is_event(char_id):
        title = _models_db().get(char_id)
        if title is None:
            raise GenerationError(
                f"{file_name}: no model {char_id!r} in models.json; cannot "
                "derive the event's name"
            )
        subtitle = ""
        rarity = highest_rarity
        manufacturer = None
    else:
        characters = _characters_db()
        base_id = char_id.split("_", 1)[0]
        record = characters.get(char_id) or characters.get(base_id)
        if record is None:
            raise GenerationError(
                f"{file_name}: no character {char_id!r} (or base {base_id!r}) "
                "in characters.json; cannot derive its name"
            )
        title = str(record["name"])
        model_name = _models_db().get(char_id)
        if model_name is None:
            raise GenerationError(
                f"{file_name}: no model {char_id!r} in models.json; cannot "
                "derive its subtitle"
            )
        if model_name == title:
            subtitle = ""
        elif model_name.startswith(title + " "):
            subtitle = model_name[len(title) + 1 :]
        else:
            raise GenerationError(
                f"{file_name}: {char_id!r}'s model name {model_name!r} does "
                f"not start with the character's name {title!r}; cannot "
                "derive its subtitle"
            )
        rarity = str(record.get("rarity") or "R")
        manufacturer = record.get("manufacturer")
    name_part = "".join(title.split())
    return CardEntry(
        id=char_id,
        number=number,
        stem=f"{number:04d}_{char_id}_{name_part}",
        title=title,
        subtitle=subtitle,
        rarity=rarity,
        manufacturer=manufacturer,
        framings=framings,
    )


def find_expansions() -> list[Expansion]:
    """Every expansion under ``cards/`` (its ``<set>.toml``), sorted by
    name and loaded (validated) in one pass."""
    return [load_expansion(path) for path in sorted(CARDS_DIR.glob("*.toml"))]


def resolve_expansion_path(raw: str | Path) -> Path:
    """The expansion's TOML the caller named (``ELYSION``,
    ``cards/ELYSION.toml`` or ``ELYSION.toml``), or a
    :class:`GenerationError` naming the known expansions."""
    raw = str(raw)
    if "/" in raw or raw.endswith(".toml"):
        candidates = (REPO_ROOT / raw, CARDS_DIR / raw)
    else:
        candidates = (CARDS_DIR / f"{raw}.toml",)
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate.parent == CARDS_DIR and candidate.suffix == ".toml":
            if candidate.is_file():
                return candidate
            break
    known = ", ".join(sorted(path.stem for path in CARDS_DIR.glob("*.toml")))
    raise GenerationError(
        f"no expansion {raw!r} under {CARDS_DIR.relative_to(REPO_ROOT)}/ "
        f"(the known expansions: {known})"
    )


# --- the viewer's introspection ------------------------------------------------
# The character's variants and animations, asked of the viewer.


def _run_viewer_list(flag: str, char_id: str) -> list[str]:
    """The ids the viewer lists for *char_id* (``--list-variants`` or
    ``--list-animations``, the default ``fb`` variant), one per line."""
    result = subprocess.run(
        [VIEWER, flag, char_id], capture_output=True, check=False, text=True
    )
    if result.returncode != 0:
        detail = result.stderr.strip()
        detail = f": {detail[-500:]}" if detail else ""
        raise GenerationError(
            f"{VIEWER} {flag} for {char_id!r} failed (exit {result.returncode}){detail}"
        )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _list_variants(char_id: str) -> list[str]:
    """The character's variants."""
    return _run_viewer_list("--list-variants", char_id)


def _list_animations(char_id: str) -> list[str]:
    """The character's animations (the default ``fb`` variant)."""
    return _run_viewer_list("--list-animations", char_id)


#: The viewer's per-character lists, cached per process: each
#: character's variants and animations are asked of the viewer at most
#: once.
_CHAR_LISTS: dict[str, tuple[frozenset[str], frozenset[str]]] = {}


def _character_lists(char_id: str) -> tuple[frozenset[str], frozenset[str]]:
    """The character's variants and animations (the viewer's
    ``--list-variants`` and ``--list-animations``, default variant), as
    sets, cached per process."""
    cached = _CHAR_LISTS.get(char_id)
    if cached is None:
        cached = (
            frozenset(_list_variants(char_id)),
            frozenset(_list_animations(char_id)),
        )
        _CHAR_LISTS[char_id] = cached
    return cached


def resolve_character(entry: CardEntry) -> CharacterInfo:
    """The character's renderability, asked of the viewer (once per
    process, see :func:`_character_lists`): its variants (the ``sc`` variant
    decides the goddess presentation) and the profile-reel's animation — the
    first of :data:`PROFILE_REEL_ANIMATIONS` the character has, which the
    ``Special`` presentations run. A character with no reel animation has no
    reel, so its ``Special`` presentations are dropped (see
    :func:`presentations_for`), mirroring the ``sc``/goddess skip."""
    variants, available = _character_lists(entry.id)
    reel = next(
        (animation for animation in PROFILE_REEL_ANIMATIONS if animation in available),
        None,
    )
    return CharacterInfo(variants=variants, reel=reel)


def reel_animations(char_id: str) -> list[str]:
    """The profile's photo-reel's animations: the first
    :data:`PROFILE_REEL_COUNT` of :data:`PROFILE_REEL_ANIMATIONS` (in the
    list's order) the character has, per the viewer's
    ``--list-animations`` (cached per process, see
    :func:`_character_lists`) — fewer (or none) when fewer of the list
    match."""
    _variants, available = _character_lists(char_id)
    return [
        animation for animation in PROFILE_REEL_ANIMATIONS if animation in available
    ][:PROFILE_REEL_COUNT]


def presentations_for(
    expansion: Expansion, entry: CardEntry, info: CharacterInfo
) -> list[Presentation]:
    """The character's presentations (the expansion's ``rarities``
    subset of :data:`PRESENTATION_SPECS`, the ``Goddess`` presentation
    dropped when the character carries no ``sc`` variant and the two
    ``Special`` presentations dropped when the character has no reel
    animation), the ``Special`` presentations' animation resolved to the
    reel's pick. An event (an id that is not a character) is a single
    full-art presentation at the set's highest presentation: its
    ``models.json`` name, that presentation's background and its
    top-level framing."""
    if is_event(entry.id):
        top = expansion.rarities[-1]
        framing = entry.framings.get(top) or {}
        return [
            Presentation(
                expansion=expansion,
                card=entry,
                name=top,
                tier="full",
                variant=None,
                animation=None,
                time=None,
                half_body=False,
                background=_spec_background(top),
                mask=None,
                face=False,
                x=framing.get("x"),
                y=framing.get("y"),
                zoom=framing.get("zoom"),
            )
        ]
    allowed = set(expansion.rarities)
    presentations = []
    for spec in PRESENTATION_SPECS:
        name, tier, variant, animation, time, half_body, background, mask, face = spec
        if name not in allowed:
            continue  # the expansion's rarities do not carry the presentation
        if name == "Goddess" and "sc" not in info.variants:
            continue
        if animation == REEL:
            if info.reel is None:
                continue  # no reel: the Special presentation is skipped
            animation = info.reel
        framing = entry.framings.get(name) or {}
        presentations.append(
            Presentation(
                expansion=expansion,
                card=entry,
                name=name,
                tier=tier,
                variant=variant,
                animation=animation,
                time=time,
                half_body=half_body,
                background=background,
                mask=mask,
                face=face,
                x=framing.get("x"),
                y=framing.get("y"),
                zoom=framing.get("zoom"),
            )
        )
    return presentations


# --- the expansion's materials -------------------------------------------------


def load_background(expansion: Expansion, key: str = "base") -> Image.Image:
    """The expansion's background (RGBA) for one of the ``background``
    table's keys (default ``base``), resolved against the expansion's
    folder."""
    if key not in expansion.backgrounds:
        raise GenerationError(
            f"{expansion.name}: unknown background key {key!r} (the table's "
            f"keys: {', '.join(sorted(expansion.backgrounds))})"
        )
    background_path = (expansion.path.parent / expansion.backgrounds[key]).resolve()
    if not background_path.is_file():
        raise GenerationError(
            f"{expansion.name}: background not found: {expansion.backgrounds[key]}"
        )
    return Image.open(background_path).convert("RGBA")


def load_logo(expansion: Expansion) -> tuple[Image.Image, str]:
    """The expansion's logo (RGBA) and its placement: its ``logo.path``
    (resolved against the expansion's folder) and its ``logo.placement``
    (one of :data:`LOGO_PLACEMENTS`)."""
    logo_path = (expansion.path.parent / expansion.logo_path).resolve()
    if not logo_path.is_file():
        raise GenerationError(
            f"{expansion.name}: logo not found: {expansion.logo_path}"
        )
    return Image.open(logo_path).convert("RGBA"), expansion.logo_placement


def _background_path(expansion: Expansion, key: str) -> Path:
    path = (expansion.path.parent / expansion.backgrounds[key]).resolve()
    if not path.is_file():
        raise GenerationError(
            f"{expansion.name}: background not found: {expansion.backgrounds[key]}"
        )
    return path


def _logo_path(expansion: Expansion) -> Path:
    path = (expansion.path.parent / expansion.logo_path).resolve()
    if not path.is_file():
        raise GenerationError(
            f"{expansion.name}: logo not found: {expansion.logo_path}"
        )
    return path


def front_source_digest(expansion: Expansion, logo: Path, template: Path) -> str:
    """A hash of an expansion front's *inputs* — everything the composed
    front depends on: the featured characters it lists (their ids, ``x``
    nudges and per-character ``animation``/``time``/``zoom`` overrides),
    its ``background.base``, its ``logo`` (and its ``placement``), the
    white NIKKE logo placed on the front (*logo*), and the material template
    that sizes it (*template*). It is computed without rendering the front,
    so the finished material can be skipped (and the front's render
    avoided) when those inputs are unchanged. The pack's and the box's
    front source hashes are this digest with their own *logo* and
    *template* (see :func:`nikke_reborn.pack.front_source_hash` /
    :func:`nikke_reborn.box.front_source_hash`)."""
    digest = hashlib.sha256()
    hash_term(digest, expansion.logo_placement.encode())
    for featured in expansion.pack:
        hash_term(digest, featured.id.encode())
        hash_term(digest, f"x:{featured.x}".encode())
        hash_term(digest, f"animation:{featured.animation}".encode())
        hash_term(digest, f"time:{featured.time}".encode())
        hash_term(digest, f"zoom:{featured.zoom}".encode())
    hash_term(digest, _background_path(expansion, "base").read_bytes())
    hash_term(digest, _logo_path(expansion).read_bytes())
    hash_term(digest, logo.read_bytes())
    hash_term(digest, template.read_bytes())
    return digest.hexdigest()


def back_source_hash(expansion: Expansion, template: Path) -> str:
    """A hash of the back's *inputs* — everything the composed back depends
    on: the expansion's ``background.base`` and the material template that
    sizes it (the back is the background's left crop). It is computed
    without composing the back, so the finished material can be skipped
    (and the back's composition avoided) when those inputs are unchanged."""
    digest = hashlib.sha256()
    hash_term(digest, _background_path(expansion, "base").read_bytes())
    hash_term(digest, template.read_bytes())
    return digest.hexdigest()


def fit_background(
    background: Image.Image, size: tuple[int, int], align: str = "center"
) -> Image.Image:
    """Resize *background* to the target's height, then crop it to the
    target's exact width, *align*-justified (``"center"`` for the front,
    ``"left"`` for the back)."""
    width, height = size
    scale = height / background.height
    if scale != 1.0:
        background = background.resize(
            (round(background.width * scale), height),
            Image.Resampling.LANCZOS,
        )
    if align == "left":
        left = 0
    elif align == "center":
        left = (background.width - width) // 2
    else:
        raise GenerationError(f"unknown background alignment {align!r}")
    return background.crop((left, 0, left + width, height)).convert("RGBA")


def _fit_cover(
    background: Image.Image,
    size: tuple[int, int],
    h_align: str = "center",
    v_align: str = "bottom",
) -> Image.Image:
    """Fit *background* over the box's faces: scaled just enough to
    cover the whole region, then cropped horizontally per *h_align* and
    vertically per *v_align* — the front and the side are
    bottom-aligned, the top top-aligned."""
    width, height = size
    scale = max(width / background.width, height / background.height)
    if scale != 1.0:
        background = background.resize(
            (round(background.width * scale), round(background.height * scale)),
            Image.Resampling.LANCZOS,
        )
    if h_align == "left":
        left = 0
    elif h_align == "center":
        left = (background.width - width) // 2
    elif h_align == "right":
        left = background.width - width
    else:
        raise GenerationError(f"unknown horizontal alignment {h_align!r}")
    if v_align == "top":
        top = 0
    elif v_align == "center":
        top = (background.height - height) // 2
    elif v_align == "bottom":
        top = background.height - height
    else:
        raise GenerationError(f"unknown vertical alignment {v_align!r}")
    return background.crop((left, top, left + width, top + height)).convert("RGBA")


def compose_front(
    expansion: Expansion,
    size: tuple[int, int],
    *,
    fit: str,
    place_logo: Callable[[Image.Image, tuple[int, int, int, int]], None],
    expansion_logo_height: float | None = None,
    hero_height: float | None = None,
    back_height: float | None = None,
    back_offset_x: float | None = None,
) -> Image.Image:
    """Compose an expansion's front: its background (fitted per *fit*),
    the featured NIKKES drawn over it (backs first, the hero on top,
    each with its optional horizontal ``x`` nudge — the material's own
    pixels), and the expansion's logo with its glow on top, at its
    ``logo.placement``; the caller's white NIKKE logo is placed last
    (*place_logo*, on the front's own bounds). The result is returned in
    memory and never written to disk: the caller pastes it into its
    material's front rectangle.

    *fit* selects the background's fit (``"crop"`` — the pack's front;
    ``"cover-bottom"`` — the box's front). *expansion_logo_height*, when
    given (the box's front), sizes the expansion's logo by height
    instead of by width (:data:`LOGO_WIDTH`). *hero_height*,
    *back_height* and *back_offset_x*, when given (the box's front),
    override the shared :data:`HERO_HEIGHT`, :data:`BACK_HEIGHT` and
    :data:`BACK_OFFSET_X` sizing — the box's landscape front wants
    bigger characters and the group a bit closer to the hero."""
    width, height = size

    background = load_background(expansion, "base")
    if fit == "crop":
        canvas = fit_background(background, size)
    elif fit == "cover-bottom":
        canvas = _fit_cover(background, size)
    else:
        raise GenerationError(f"unknown background fit {fit!r}")
    # Sample the background's color now — before the NIKKES are
    # composited — so the logo's glow is tinted by the scene, not by
    # the characters on top of it.
    glow_color = _background_glow_color(_image_average(canvas))

    featured = expansion.pack
    if not featured:
        raise GenerationError(f"{expansion.name}: 'pack' carries no characters")
    bodies = [_content_box(_render_featured_frame(entry)) for entry in featured]

    # Backs first (behind the hero), left/right alternating, stepping
    # further out and shrinking per tier; each character's ``x`` nudge
    # (the material's own pixels) is added to its center.
    back_scale = back_height if back_height is not None else BACK_HEIGHT
    offset_scale = back_offset_x if back_offset_x is not None else BACK_OFFSET_X
    for index, body in enumerate(bodies[1:], start=1):
        side = -1 if (index - 1) % 2 == 0 else 1  # left, right, left, ...
        tier = (index - 1) // 2  # 0 for the inner pair, 1 for the next, ...
        offset = offset_scale * width * (1.0 + BACK_TIER_GAP * tier)
        scale = BACK_TIER_SHRINK**tier
        _paste_body(
            canvas,
            body,
            center_x=width / 2 + side * offset + featured[index].x,
            feet_y=BACK_FEET_Y * height,
            height=round(back_scale * height * scale),
        )
    # The hero on top: centered, the largest.
    hero_scale = hero_height if hero_height is not None else HERO_HEIGHT
    _paste_body(
        canvas,
        bodies[0],
        center_x=width / 2 + featured[0].x,
        feet_y=HERO_FEET_Y * height,
        height=round(hero_scale * height),
    )

    mark, placement = load_logo(expansion)
    _composite_logo(
        canvas,
        mark,
        size,
        placement,
        glow_color,
        mark_height=expansion_logo_height,
    )
    place_logo(canvas, (0, 0, width, height))
    return canvas


def _render_featured_frame(featured: Featured) -> Image.Image:
    """Render the featured character's still frame via ``nikke-viewer
    --stdout`` (raw RGBA): the ``--time <time>`` still of its
    *animation* (the viewer's default when none is given), zoomed by
    *zoom* (the viewer's default when absent), framed with
    ``--half-body``, at the viewer's default viewport, read straight off
    the stream. The viewer exits once its single frame is written."""
    width, height = CARD_VIEWPORT
    frame_bytes = width * height * 4

    animation_args = (
        ["--animation", featured.animation] if featured.animation is not None else []
    )
    zoom_args = ["--zoom", str(featured.zoom)] if featured.zoom is not None else []
    viewer = subprocess.Popen(
        [
            VIEWER,
            *animation_args,
            "--time",
            str(featured.time),
            *zoom_args,
            "--half-body",
            "--stdout",
            featured.id,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert viewer.stdout is not None
    assert viewer.stderr is not None
    drain = _PipeDrain(cast(io.BufferedReader, viewer.stderr))
    try:
        data = _read_exact(viewer.stdout, frame_bytes)
    finally:
        _reap_viewer(viewer, drain, clean_exit_expected=True)
    if len(data) != frame_bytes:
        raise GenerationError(
            f"{VIEWER} produced no frame for {featured.id!r} "
            f"(got {len(data)} of {frame_bytes} bytes)"
        )
    return Image.frombytes("RGBA", (width, height), data)


def _content_box(image: Image.Image, threshold: int = ALPHA_TRIM) -> Image.Image:
    """Trim *image* to its opaque content bounding box (alpha > threshold)."""
    alpha = image.getchannel("A").point(lambda v: 255 if v > threshold else 0)
    box = alpha.getbbox()
    if box is None:
        raise GenerationError("rendered frame is fully transparent")
    return image.crop(box)


def _paste_body(
    canvas: Image.Image,
    body: Image.Image,
    center_x: float,
    feet_y: float,
    height: int,
) -> None:
    """Scale *body* so its height is *height* px and composite it onto
    *canvas* with its horizontal center at *center_x* and its bottom (feet) at
    *feet_y*. Parts that run off the canvas edge are clipped."""
    scale = height / body.height
    new_width = max(1, round(body.width * scale))
    body = body.resize((new_width, height), Image.Resampling.LANCZOS)
    left = round(center_x - new_width / 2)
    top = round(feet_y - height)
    canvas.alpha_composite(body, (left, top))


def _image_average(image: Image.Image) -> tuple[int, int, int]:
    """The area-averaged RGB of *image* (a single box-filtered pixel) — the
    image's representative color, cheap to compute at any size."""
    pixel = image.convert("RGB").resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
    assert isinstance(pixel, tuple)
    return (pixel[0], pixel[1], pixel[2])


def _background_glow_color(
    background: tuple[int, int, int], value: float = LOGO_GLOW_VALUE
) -> tuple[int, int, int]:
    """The glow tint from the front's *background* color: its hue and
    saturation, brightened to *value*. Keeping the background's hue lets the
    bloom match the scene's ambient color instead of a fixed white; a fixed
    target brightness keeps it visible no matter how dark the background is.
    A near-gray background yields a near-neutral glow."""
    hue, sat, _ = colorsys.rgb_to_hsv(*(c / 255 for c in background))
    r, g, b = colorsys.hsv_to_rgb(hue, sat, value)
    return round(r * 255), round(g * 255), round(b * 255)


def _logo_glow_layer(
    logo: Image.Image, radius: int, color: tuple[int, int, int], intensity: float
) -> tuple[Image.Image, int]:
    """A soft halo around *logo*: its alpha blurred by *radius* px,
    tinted *color*, scaled by *intensity*, on a transparent canvas
    padded by the blur's full visible extent (three sigma) on every
    side, so the halo is not clipped at the mark's edges. Returns the
    RGBA halo and the pad, so the caller can re-align it with the sharp
    mark."""
    pad = max(1, 3 * radius)
    halo = Image.new("L", (logo.width + 2 * pad, logo.height + 2 * pad), 0)
    halo.paste(logo.getchannel("A"), (pad, pad))
    halo = halo.filter(ImageFilter.GaussianBlur(radius))
    halo = halo.point(lambda v: min(255, round(v * intensity)))
    layer = Image.new("RGBA", halo.size, color + (0,))
    layer.putalpha(halo)
    return layer, pad


def _screen_composite(
    base: Image.Image, overlay: Image.Image, pos: tuple[int, int]
) -> None:
    """Screen-blend *overlay*'s color onto *base* at *pos*, masked by the
    overlay's alpha: the mark's bloom brightens the front without painting over
    it (unlike an opaque alpha paste). Clipped to *base*'s bounds; *base* is
    modified in place."""
    base_w, base_h = base.size
    over_w, over_h = overlay.size
    x, y = pos
    sx, sy = max(0, -x), max(0, -y)
    ex, ey = min(over_w, base_w - x), min(over_h, base_h - y)
    if ex <= sx or ey <= sy:
        return
    box = (x + sx, y + sy, x + ex, y + ey)
    region = base.crop(box)
    halo = overlay.crop((sx, sy, ex, ey))
    mask = halo.getchannel("A")
    blended = ImageChops.screen(region.convert("RGB"), halo.convert("RGB"))
    base.paste(Image.composite(blended, region.convert("RGB"), mask), box)


def _composite_logo(
    canvas: Image.Image,
    logo: Image.Image,
    size: tuple[int, int],
    placement: str,
    glow_color: tuple[int, int, int],
    mark_height: float | None = None,
    width_fraction: float | None = None,
) -> None:
    """Composite the expansion's *logo* over *canvas* at *placement*
    with a glow: the halo (tinted *glow_color*) is screen-blended for a
    light bloom, a solid trail — the mark's own silhouette in a
    darkened glow tint, offset down-right — is drawn behind it, and the
    sharp mark on top. The mark is scaled to :data:`LOGO_WIDTH` the
    front's width (or, when *mark_height* is given — the box's front
    and side — to that fraction of the face's height, its width
    proportional; or, when *width_fraction* is given — the box's top —
    to that fraction of the face's width, its height proportional) and
    centered horizontally; top/bottom placements inset it
    :data:`LOGO_MARGIN` from the edge, ``center`` centers it in the
    front. Modifies *canvas* in place."""
    width, height = size
    if mark_height is None:
        logo_w = round(
            (LOGO_WIDTH if width_fraction is None else width_fraction) * width
        )
        if logo_w < 1:
            return
        logo = logo.resize(
            (logo_w, round(logo_w * logo.height / logo.width)),
            Image.Resampling.LANCZOS,
        )
    else:
        logo_h = round(mark_height * height)
        if logo_h < 1:
            return
        logo = logo.resize(
            (round(logo_h * logo.width / logo.height), logo_h),
            Image.Resampling.LANCZOS,
        )
    cx = width // 2
    if placement == "top":
        cy = round(LOGO_MARGIN * height) + logo.height // 2
    elif placement == "bottom":
        cy = round(height - LOGO_MARGIN * height) - logo.height // 2
    elif placement == "center":
        cy = height // 2
    else:
        raise GenerationError(
            f"unknown logo placement {placement!r}; "
            f"expected one of {', '.join(LOGO_PLACEMENTS)}"
        )
    x = cx - logo.width // 2
    y = cy - logo.height // 2
    halo, pad = _logo_glow_layer(
        logo, round(LOGO_GLOW_RADIUS * height), glow_color, LOGO_GLOW_INTENSITY
    )
    _screen_composite(canvas, halo, (x - pad, y - pad))
    trail_offset = round(LOGO_TRAIL * logo.height)
    if trail_offset > 0:
        trail_tint = tuple(int(c * LOGO_TRAIL_DARKEN) for c in glow_color)
        trail = Image.new("RGBA", logo.size, trail_tint + (255,))
        trail.putalpha(logo.getchannel("A"))
        canvas.alpha_composite(trail, (x + trail_offset, y + trail_offset))
    canvas.alpha_composite(logo, (x, y))
