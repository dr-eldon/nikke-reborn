"""The test command: the byte-for-byte regression check for a card.

Generates every variant of the selected card(s) — each definition's
full-art card (with the animated cards' first-frame PNGs), the profile
and standard derived cards, and the set's pack and box materials and
items — with a forced, single-worker :func:`generate.run`, and compares
the finished files' SHA-256 against the card's recorded baseline under
``tests/baselines/<set>/``. The run always forces the re-render (the
check is against what the current code produces, not against files that
happen to be up to date) and uses one worker: the byte protocol — the
same code, inputs and worker count must produce the same bytes (the
x264 threading must match for the MP4s to be byte-comparable).
``--new-baseline`` records (overwrites) the baseline from the run's
outputs instead of comparing.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from nikke_reborn import generate
from nikke_reborn.card import (
    _card_out_path,
    _load_card,
    _profile_stem,
    _standard_stem,
)
from nikke_reborn.config import (
    BOX_ITEM_NAME,
    BOX_MATERIAL_NAME,
    CARDS_DIR,
    PACK_ITEM_NAME,
    PACK_MATERIAL_NAME,
    PROFILE_RARITIES,
    PROFILE_STEMS,
    REPO_ROOT,
    STANDARD_STEMS,
)
from nikke_reborn.error import GenerationError
from nikke_reborn.expansion import EXPANSION_NAME
from nikke_reborn.preset import Preset

#: The recorded baselines: ``tests/baselines/<set>/<card>.<preset>.sha256``
#: (one file per card and preset, ``sha256sum``-compatible).
BASELINES_DIR = REPO_ROOT / "tests" / "baselines"


def run() -> None:
    """Generate every variant of the selected card(s) and check the
    finished files against the recorded baselines (or record new
    baselines with ``--new-baseline``)."""
    args = _parse_args()
    preset = Preset.ULTRA if args.ultra else Preset.DEFAULT
    try:
        cards = [_resolve_card_dir(raw) for raw in args.paths]
        if not args.new_baseline:
            # Fail before the (GPU-heavy) forced run.
            for card_dir in cards:
                _require_baseline(
                    f"{card_dir.parent.name}/{card_dir.name}",
                    _baseline_path(card_dir, preset),
                )
        for card_dir in cards:
            label = f"{card_dir.parent.name}/{card_dir.name}"
            _generate(card_dir, preset)
            actual = {
                path.relative_to(REPO_ROOT).as_posix(): _sha256(path)
                for path in _expected_outputs(card_dir, preset)
            }
            baseline = _baseline_path(card_dir, preset)
            if args.new_baseline:
                _write_baseline(baseline, label, preset, actual)
                print(
                    "Recorded "
                    f"{len(actual)} file(s) to {baseline.relative_to(REPO_ROOT)}."
                )
            else:
                _compare(label, baseline, actual)
    except GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "byte-for-byte regression check: generate every variant of a "
            "card (its full-art, profile and standard cards plus the "
            "set's pack images) with a forced, single-worker run and "
            "compare the finished files' SHA-256 against the recorded "
            f"baseline ({BASELINES_DIR.relative_to(REPO_ROOT)}/<set>/)"
        )
    )
    parser.add_argument(
        "paths",
        type=Path,
        nargs="+",
        metavar="CARD_PATH",
        help=(
            "card directorie(s), each relative to the repo root or to "
            "cards/ (e.g. cards/ELYSION/0001_Rapi)"
        ),
    )
    parser.add_argument(
        "--ultra",
        action="store_true",
        help=(
            "the ultra preset: the native resolution, written to the "
            "'<set> (Ultra)' set folders (the default preset — the half "
            "resolution, output/ — is checked otherwise)"
        ),
    )
    parser.add_argument(
        "--new-baseline",
        action="store_true",
        help=(
            "record (overwrite) the baseline from this run's outputs "
            "instead of comparing against the recorded one"
        ),
    )
    return parser.parse_args()


def _resolve_card_dir(raw: Path) -> Path:
    """Resolve *raw* to a card directory (``cards/<set>/<card>``),
    relative to the repo root or to ``cards/``."""
    root = (REPO_ROOT / raw).resolve() if not raw.is_absolute() else raw
    if not root.is_dir():
        root = (CARDS_DIR / raw).resolve()
    if not root.is_dir() or root.parent.parent != CARDS_DIR:
        raise GenerationError(
            "test takes a card directory (e.g. cards/ELYSION/0001_Rapi): "
            f"{raw}"
        )
    return root


def _generate(card_dir: Path, preset: Preset) -> None:
    """The forced, single-worker generate run behind the check (see the
    module docstring): the byte protocol — the same code, inputs and
    worker count produce the same bytes."""
    argv = ["--jobs", "1", "--force", str(card_dir.relative_to(REPO_ROOT))]
    if preset is Preset.ULTRA:
        argv.append("--ultra")
    try:
        generate.run(argv)
    except SystemExit as exc:
        # A failed generate already reported the error; keep its code.
        if exc.code:
            sys.exit(exc.code)


def _expected_outputs(card_dir: Path, preset: Preset) -> list[Path]:
    """The finished files a forced generate of *card_dir* at *preset*
    writes: every definition's full-art card (plus the animated cards'
    first-frame PNGs), the profile and standard derived cards, and —
    when the set carries an ``Expansion.json`` — the set's pack and box
    materials and items. Mirrors the pipeline's own selection (see
    :func:`generate.run`)."""
    set_name = card_dir.parent.name
    outs: list[Path] = []
    for definition in sorted(card_dir.glob("*.json")):
        if definition.name == EXPANSION_NAME:
            continue
        card = _load_card(definition)
        animated = card.get("time") is None
        suffix = "mp4" if animated else "png"
        # The full-art card (the profile-rarity stems, if ever any,
        # render their profile card alone).
        if definition.stem not in PROFILE_RARITIES:
            outs.append(_card_out_path(definition, suffix, preset=preset))
            if animated:
                # The animation's first frame is kept alongside it.
                outs.append(_card_out_path(definition, "png", preset=preset))
        if definition.stem in STANDARD_STEMS:
            stem = _standard_stem(definition)
            outs.append(_card_out_path(definition, suffix, stem, preset))
            if animated:
                outs.append(_card_out_path(definition, "png", stem, preset))
        if definition.stem in PROFILE_STEMS or definition.stem in PROFILE_RARITIES:
            stem = _profile_stem(definition)
            outs.append(_card_out_path(definition, suffix, stem, preset))
            if animated:
                outs.append(_card_out_path(definition, "png", stem, preset))
    if (card_dir.parent / EXPANSION_NAME).is_file():
        # The set's pack and box images (one pair per set).
        set_path = preset.set_path(set_name)
        for name in (
            PACK_MATERIAL_NAME,
            PACK_ITEM_NAME,
            BOX_MATERIAL_NAME,
            BOX_ITEM_NAME,
        ):
            outs.append(set_path / name)
    return outs


def _baseline_path(card_dir: Path, preset: Preset) -> Path:
    """The card's recorded baseline:
    ``tests/baselines/<set>/<card>.<preset>.sha256``."""
    return (
        BASELINES_DIR / card_dir.parent.name / f"{card_dir.name}.{preset.value}.sha256"
    )


def _sha256(path: Path) -> str:
    """The file's SHA-256 (hex)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_baseline(
    baseline: Path, label: str, preset: Preset, actual: dict[str, str]
) -> None:
    """Write (overwriting) the card's recorded baseline from *actual*
    (repo-relative path -> SHA-256), in ``sha256sum``-compatible format
    (``sha256sum -c`` from the repo root verifies it)."""
    baseline.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# nikke-reborn test baseline",
        f"# card:   {label}",
        f"# preset: {preset.value}",
        f"# files:  {len(actual)}",
        "# recorded by: test --new-baseline (generate --force --jobs 1)",
        (
            "# verify from the repo root: sha256sum -c "
            f"{baseline.relative_to(REPO_ROOT)}"
        ),
        "",
    ]
    lines += [f"{digest}  {path}" for path, digest in sorted(actual.items())]
    baseline.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_baseline(baseline: Path) -> dict[str, str]:
    """The recorded baseline (repo-relative path -> SHA-256)."""
    expected: dict[str, str] = {}
    for line in baseline.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, _, path = line.partition("  ")
        expected[path] = digest
    return expected


def _require_baseline(label: str, baseline: Path) -> None:
    """Fail when the card has no recorded baseline yet."""
    if baseline.is_file():
        return
    print(
        f"error: no recorded baseline for {label} "
        f"({baseline.relative_to(REPO_ROOT)}): record one with --new-baseline",
        file=sys.stderr,
    )
    sys.exit(1)


def _compare(label: str, baseline: Path, actual: dict[str, str]) -> None:
    """Compare *actual* (repo-relative path -> SHA-256) against the
    recorded *baseline*; the run fails when the two disagree."""
    _require_baseline(label, baseline)
    expected = _read_baseline(baseline)
    problems = 0
    for path, digest in sorted(actual.items()):
        if path not in expected:
            print(f"UNEXPECTED {path} (not in the baseline)")
            problems += 1
        elif expected[path] != digest:
            print(f"MISMATCH {path}:")
            print(f"  baseline  {expected[path]}")
            print(f"  actual    {digest}")
            problems += 1
    for path in sorted(set(expected) - set(actual)):
        print(f"MISSING {path} (in the baseline, not generated)")
        problems += 1
    if problems:
        print(
            f"error: {label}: {problems} of {len(actual)} file(s) "
            f"differ from the baseline (record a new one with --new-baseline)",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"OK: {label} — all {len(actual)} file(s) match the baseline.")
