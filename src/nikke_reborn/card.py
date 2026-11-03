"""The card's identity and its work: the per-presentation source hash
(embedded in a finished card so it is skipped when nothing changed),
the card's output path, the character's manufacturer's logo, and the
run's selection (the expansions' presentations, filtered by the
characters the caller named)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image

from nikke_reborn import expansion
from nikke_reborn.config import (
    CARD_VIEWPORT,
    DATABASE_DIR,
    FONT,
    IMAGES_DIR,
)
from nikke_reborn.error import GenerationError
from nikke_reborn.file import hash_term
from nikke_reborn.image import PROFILE_MASK_PATH, STANDARD_MASK_PATH
from nikke_reborn.lettering import FONT_NAME, FONT_RECT_ARROW
from nikke_reborn.preset import Preset

#: The NIKKE logo's two faces: the white one (the full-art cards) and the
#: black one (the standard's and profile's cards).
LOGO_PATHS = {
    False: IMAGES_DIR / "Logo_White.png",
    True: IMAGES_DIR / "Logo_Black.png",
}

#: The card's padding, scaled to the run's final size: the lettering's,
#: the logo's and the reel's offsets are expressed at this padding.
PADDING = 50


def padding(preset: Preset) -> int:
    """The run's padding (the card's native padding at the run's
    scale), rounded to the px."""
    return round(PADDING * preset.scale)


def run_size(preset: Preset) -> tuple[int, int]:
    """The run's final size: the viewer's default viewport
    (:data:`nikke_reborn.CARD_VIEWPORT`) at the run's scale, each
    dimension rounded and forced even (the video's encoder requires even
    dimensions)."""
    return (
        round(CARD_VIEWPORT[0] * preset.scale) & ~1,
        round(CARD_VIEWPORT[1] * preset.scale) & ~1,
    )


def output_path(
    set_name: str,
    card_stem: str,
    presentation: str,
    rarity_index: int,
    suffix: str,
    preset: Preset,
) -> Path:
    """A card's finished output path:
    ``<card's stem>_<rarity index>_<presentation>.<suffix>`` under the
    output preset's set folder (the rarity index the presentation's
    1-based position in the set's ``rarities``)."""
    return (
        preset.set_path(set_name)
        / f"{card_stem}_{rarity_index:02d}_{presentation}.{suffix}"
    )


def _manufacturer_logo_path(card_id: str) -> Path | None:
    """The manufacturer's logo's path for the character, or None when the
    character's manufacturer carries no logo file (the logo is then
    skipped): the character's own manufacturer's, the base character's
    when the id is suffixed."""
    characters = expansion._characters_db()
    record = characters.get(card_id) or characters.get(card_id.split("_", 1)[0])
    if record is None:
        return None
    manufacturer = record.get("manufacturer")
    if not manufacturer:
        return None
    path = DATABASE_DIR / "images" / "manufacturers" / f"{manufacturer}.png"
    return path if path.is_file() else None


def _manufacturer_logo(card_id: str) -> Image.Image | None:
    """The character's manufacturer's logo (RGBA), opened for the
    composite (the nameplate's logo), or None (see
    :func:`_manufacturer_logo_path`)."""
    path = _manufacturer_logo_path(card_id)
    if path is None:
        return None
    return Image.open(path).convert("RGBA")


def presentation_source_hash(
    presentation: expansion.Presentation, preset: Preset
) -> str:
    """The SHA-256 of a presentation's inputs — everything the finished
    card depends on: the card's id and stem, the
    presentation's name and its viewer terms (in canonical form, plus the
    framing overrides when the TOML names them), the background's bytes
    (the solid black's marker for the goddess
    presentation), the mask's bytes, the NIKKE logo's face, the
    manufacturer's logo (when the character has one), the game's data
    (``characters.json`` and ``models.json``) and the fonts the lettering
    stamps — plus the run's scale (mixed in only when it deviates from
    1.0, the full-resolution default, so an ultra card's hash is the
    canonical one)."""
    digest = hashlib.sha256()
    card = presentation.card
    hash_term(digest, card.id.encode())
    hash_term(digest, card.stem.encode())
    hash_term(digest, presentation.name.encode())
    flags = "|".join(
        (
            presentation.variant or "default",
            presentation.animation or "default",
            f"time {presentation.time}" if presentation.time is not None else "loop",
            "half-body" if presentation.half_body else "default-framing",
        )
    )
    hash_term(digest, flags.encode())
    for flag, value in (
        ("x", presentation.x),
        ("y", presentation.y),
        ("zoom", presentation.zoom),
    ):
        if value is not None:
            hash_term(digest, f"{flag}:{value}".encode())
    if presentation.background == "black":
        hash_term(digest, b"solid-black")
    else:
        hash_term(
            digest,
            expansion._background_path(
                presentation.expansion, presentation.background
            ).read_bytes(),
        )
    if presentation.mask == "standard":
        hash_term(digest, STANDARD_MASK_PATH.read_bytes())
    elif presentation.mask == "profile":
        hash_term(digest, PROFILE_MASK_PATH.read_bytes())
    hash_term(digest, LOGO_PATHS[presentation.tier != "full"].read_bytes())
    logo_path = _manufacturer_logo_path(card.id)
    if logo_path is not None:
        hash_term(digest, logo_path.read_bytes())
    for db_name in ("characters.json", "models.json"):
        hash_term(digest, (DATABASE_DIR / db_name).read_bytes())
    for font_path in (FONT, FONT_NAME, FONT_RECT_ARROW):
        hash_term(digest, font_path.read_bytes())
    scale = preset.scale
    if scale != 1.0:
        hash_term(digest, f"{scale:g}".encode())
    return digest.hexdigest()


def select_expansions(paths: list[str] | None) -> list[expansion.Expansion]:
    """The expansions a run renders: the caller's (resolved against the
    repo's or the ``cards/`` root, de-duplicated in order) or every
    expansion under ``cards/`` when none are given."""
    if not paths:
        return expansion.find_expansions()
    selected: list[expansion.Expansion] = []
    seen: set[Path] = set()
    for raw in paths:
        path = expansion.resolve_expansion_path(raw)
        if path in seen:
            continue
        seen.add(path)
        selected.append(expansion.load_expansion(path))
    return selected


def build_selection(
    expansions: list[expansion.Expansion], ids: list[str] | None = None
) -> list[expansion.Presentation]:
    """The run's work: every selected expansion's cards' presentations (the
    expansion's ``rarities`` subset, the ``Goddess`` presentation dropped
    when the character carries no ``sc`` variant and the two ``Special``
    presentations dropped when the character has no reel animation),
    filtered to the characters the caller named when *ids* is given (an id
    that is not in an expansion's roster errors, naming the known ids).
    Every selected character is resolved against the viewer (its variants,
    its reel's animation) before the run starts, so a character that cannot
    render a presentation fails before anything is rendered."""
    if ids:
        known: dict[str, set[str]] = {
            e.name: {c.id for c in e.cards} for e in expansions
        }
        for expansion_name, roster in known.items():
            unknown = [char_id for char_id in ids if char_id not in roster]
            if unknown:
                raise GenerationError(
                    f"{expansion_name}: unknown character id(s) "
                    f"{', '.join(unknown)} (the roster: {', '.join(sorted(roster))})"
                )
    presentations: list[expansion.Presentation] = []
    for exp in expansions:
        for entry in exp.cards:
            if ids and entry.id not in ids:
                continue
            info = expansion.resolve_character(entry)
            presentations.extend(expansion.presentations_for(exp, entry, info))
    return presentations
