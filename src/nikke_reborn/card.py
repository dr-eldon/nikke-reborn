"""The card-configuration domain.

Discovering and loading card definitions from ``cards.json`` and the
database (and the derived profile/standard variants), the source hashes
that record what a finished card was rendered from, the logo paths, and
the output paths and stems of the rendered cards.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

from nikke_reborn.config import CARDS_DIR, DATABASE_DIR, IMAGES_DIR, REPO_ROOT
from nikke_reborn.error import GenerationError
from nikke_reborn.image import PROFILE_MASK_PATH, STANDARD_MASK_PATH
from nikke_reborn.preset import Preset

LOGO_PATHS = {
    False: IMAGES_DIR / "Logo_White.png",
    True: IMAGES_DIR / "Logo_Black.png",
}


def _source_hash(json_path: Path, preset: Preset) -> str:
    """SHA-256 of the card definition file and the output preset's
    scale: the inputs a finished card embeds under
    :data:`SOURCE_HASH_KEY`. The scale term is only mixed in when it
    deviates from 1.0 — the full-resolution default — so a scale-1.0
    card carries exactly the hash the code embedded before scales
    existed, and the ultra (native) output stays byte-for-byte the
    legacy bytes."""
    digest = hashlib.sha256()
    digest.update(json_path.read_bytes())
    scale = preset.scale
    if scale != 1.0:
        digest.update(f"{scale:g}".encode())
    return digest.hexdigest()


def _profile_source_hash(json_path: Path, preset: Preset) -> str:
    """SHA-256 of the profile card's inputs — the definition it renders,
    the output preset's scale (mixed in only when it deviates from 1.0,
    the full-resolution default, so a scale-1.0 card carries exactly
    the hash the code embedded before scales existed), the card mask,
    the characters database (for the character's manufacturer) and the
    manufacturer's logo (the files its pixels depend on). Embedded under
    :data:`SOURCE_HASH_KEY` so an unchanged profile card is skipped
    instead of re-rendered."""
    digest = hashlib.sha256()
    digest.update(json_path.read_bytes())
    scale = preset.scale
    if scale != 1.0:
        digest.update(f"{scale:g}".encode())
    digest.update(PROFILE_MASK_PATH.read_bytes())
    digest.update((DATABASE_DIR / "characters.json").read_bytes())
    manufacturer = _character_manufacturer(str(_load_card(json_path).get("id", "")))
    if manufacturer is not None:
        logo = IMAGES_DIR / "logos" / f"{manufacturer}.png"
        if logo.is_file():
            digest.update(logo.read_bytes())
    return digest.hexdigest()


def _standard_source_hash(json_path: Path, preset: Preset) -> str:
    """SHA-256 of the standard card's inputs — the definition it renders,
    the output preset's scale (mixed in only when it deviates from 1.0,
    the full-resolution default, so a scale-1.0 card carries exactly
    the hash the code embedded before scales existed), the standard
    card mask, the characters database (for the character's
    manufacturer) and the manufacturer's logo (the files its pixels
    depend on). Embedded under :data:`SOURCE_HASH_KEY` so an unchanged
    standard card is skipped instead of re-rendered."""
    digest = hashlib.sha256()
    digest.update(json_path.read_bytes())
    scale = preset.scale
    if scale != 1.0:
        digest.update(f"{scale:g}".encode())
    digest.update(STANDARD_MASK_PATH.read_bytes())
    digest.update((DATABASE_DIR / "characters.json").read_bytes())
    manufacturer = _character_manufacturer(str(_load_card(json_path).get("id", "")))
    if manufacturer is not None:
        logo = IMAGES_DIR / "logos" / f"{manufacturer}.png"
        if logo.is_file():
            digest.update(logo.read_bytes())
    return digest.hexdigest()


def _find_card_configs(paths: list[Path] | None = None) -> list[Path]:
    """Return the card definition files to generate.

    With no explicit *paths*, every ``*.json`` under :data:`CARDS_DIR`
    (sorted for deterministic output), excluding the pack's
    ``Expansion.json`` (the pack's metadata, not a card). Explicit paths are
    resolved against the repo root, must be files that live under
    :data:`CARDS_DIR`, are de-duplicated and returned in the given order.
    """
    if not paths:
        from nikke_reborn import expansion

        return sorted(
            path
            for path in CARDS_DIR.rglob("*.json")
            if path.name != expansion.EXPANSION_NAME
        )
    configs: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        json_path = (REPO_ROOT / raw).resolve() if not raw.is_absolute() else raw
        if not json_path.is_file():
            raise GenerationError(f"card definition not found: {raw}")
        if CARDS_DIR not in json_path.parents:
            raise GenerationError(
                f"card definition must be under {CARDS_DIR.relative_to(REPO_ROOT)}/: {raw}"
            )
        if json_path not in seen:
            seen.add(json_path)
            configs.append(json_path)
    return configs


def _expand_card_paths(paths: list[Path]) -> list[Path]:
    """Expand *paths* (each a set, a card, or a definition file, relative to
    the repo root or to ``cards/``) to the card definitions they contain:
    every ``*.json`` under each path (the pack's ``Expansion.json``
    excluded), validated and de-duplicated by :func:`_find_card_configs`."""
    from nikke_reborn import expansion

    files: list[Path] = []
    for raw in paths:
        root = (REPO_ROOT / raw).resolve()
        if not root.exists():
            root = (CARDS_DIR / raw).resolve()
        if not root.exists():
            raise GenerationError(f"no such card path: {raw}")
        if root != CARDS_DIR and CARDS_DIR not in root.parents:
            raise GenerationError(
                f"card path must be under {CARDS_DIR.relative_to(REPO_ROOT)}/: {raw}"
            )
        if root.is_file():
            if not root.name.endswith(".json") or root.name == expansion.EXPANSION_NAME:
                raise GenerationError(f"not a card definition: {raw}")
            files.append(root)
        else:
            files.extend(
                sorted(
                    path
                    for path in root.rglob("*.json")
                    if path.name != expansion.EXPANSION_NAME
                )
            )
    if not files:
        raise GenerationError("no card definitions selected")
    return _find_card_configs(files)


def _selected_configs(paths: list[Path]) -> list[Path] | None:
    """The card definitions to generate: None when nothing is selected
    (everything, as before), else the card definitions the selected
    *paths* expand to, in the given order."""
    if not paths:
        return None
    return _expand_card_paths(paths)


def _load_card(json_path: Path) -> dict:
    try:
        import json

        return json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GenerationError(
            f"cannot read card definition {json_path.name}: {exc}"
        ) from exc


def _background_path(card: dict, json_path: Path) -> Path:
    if "background" not in card:
        raise GenerationError(f"{json_path.name}: missing 'background'")
    background = (json_path.parent / card["background"]).resolve()
    if not background.is_file():
        raise GenerationError(f"{json_path.name}: background not found: {background}")
    return background


def _character_manufacturer(card_id: str) -> str | None:
    """The character's ``manufacturer`` from ``database/characters.json``
    (looked up by *card_id*; a skin variant's suffixed id, c010_02, falls
    back to the base character, as the rarity does). None when the
    character is unknown or carries no manufacturer."""
    characters = json.load((DATABASE_DIR / "characters.json").open())
    characters = {character["id"]: character for character in characters}
    character = characters.get(card_id) or characters.get(card_id.split("_", 1)[0])
    manufacturer = character.get("manufacturer") if character else None
    return manufacturer or None


def _manufacturer_logo(card_id: str) -> Image.Image | None:
    """The character's manufacturer logo:
    ``assets/images/logos/<manufacturer>.png`` (white on transparency,
    tinted to the bar's fill when placed) — None
    when the character has no manufacturer or its logo file is missing."""
    manufacturer = _character_manufacturer(card_id)
    if manufacturer is None:
        return None
    logo_path = IMAGES_DIR / "logos" / f"{manufacturer}.png"
    if not logo_path.is_file():
        return None
    return Image.open(logo_path).convert("RGBA")


def _card_out_path(
    out_base: Path,
    json_path: Path,
    suffix: str,
    stem: str | None = None,
    preset: Preset = Preset.DEFAULT,
) -> Path:
    """The flat output path for a card definition: the card's
    directory is folded into the filename, so
    ``cards/<set>/<card>/<variant>.json`` renders to
    ``<out_base>/<set>/<card>_<variant>.<suffix>`` (deeper nesting,
    if ever used, is folded the same way, one dash per directory).

    *stem* overrides the variant in the filename (defaults to the
    definition's own stem) — the profile cards pass their output stem, so a
    profile card writes out as ``<card>_<variant>Profile.<suffix>``.
    An ultra run writes to the ``<set> (Ultra)`` set folder instead of
    ``<set>`` (the output preset's set folder, :meth:`Preset.set_name`).
    """
    if stem is None:
        stem = json_path.stem
    card_rel = json_path.parent.relative_to(CARDS_DIR)
    return (
        out_base
        / preset.set_name(card_rel.parts[0])
        / f"{'_'.join(card_rel.parts[1:])}_{stem}.{suffix}"
    )


def _profile_stem(json_path: Path) -> str:
    """The output stem of the profile card rendered from *json_path*: the
    variant's stem with the ``Profile`` suffix (an ``Aim.json`` writes out
    as ``<card>_AimProfile.<suffix>``)."""
    return f"{json_path.stem}Profile"


def _standard_stem(json_path: Path) -> str:
    """The output stem of the standard card rendered from *json_path*: the
    variant's stem with the ``Standard`` suffix (a ``Rare.json`` writes out
    as ``<card>_RareStandard.<suffix>``)."""
    return f"{json_path.stem}Standard"
