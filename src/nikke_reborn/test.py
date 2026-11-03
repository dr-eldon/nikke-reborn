"""The test command: the byte-for-byte regression check for a card.

Generates every presentation the expansion's ``rarities`` select for
the selected character(s) — each character's full-art, profile and
standard cards (with the animated cards' first-frame PNGs) — plus the
expansion's pack and box materials and items, with a forced,
single-worker :func:`generate.run`, and compares the finished files'
SHA-256 against the recorded baselines under
``tests/baselines/<set>/``. The run always forces the re-render and
uses one worker: the byte protocol — the same code, inputs and worker
count must produce the same bytes (the x264 threading must match for
the MP4s to be byte-comparable). ``--new-baseline`` records
(overwrites) the baselines from the run's outputs instead of
comparing.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from nikke_reborn import card, expansion, generate
from nikke_reborn.config import (
    BOX_ITEM_NAME,
    BOX_MATERIAL_NAME,
    PACK_ITEM_NAME,
    PACK_MATERIAL_NAME,
    REPO_ROOT,
)
from nikke_reborn.error import GenerationError
from nikke_reborn.preset import Preset

#: The recorded baselines: ``tests/baselines/<set>/<card>.<preset>.sha256``
#: (one file per card and preset) and
#: ``tests/baselines/<set>/expansion.<preset>.sha256`` (the expansion's
#: pack and box images), ``sha256sum``-compatible.
BASELINES_DIR = REPO_ROOT / "tests" / "baselines"


def run() -> None:
    """Generate every presentation of the selected character(s) and check
    the finished files against the recorded baselines (or record new
    baselines with ``--new-baseline``)."""
    args = _parse_args()
    preset = Preset.DEFAULT
    try:
        expansion_path = expansion.resolve_expansion_path(args.paths[0])
        exp = expansion.load_expansion(expansion_path)
        ids = args.paths[1:]
        entries = [entry for entry in exp.cards if not ids or entry.id in ids]
        if ids:
            known = {entry.id for entry in exp.cards}
            unknown = [char_id for char_id in ids if char_id not in known]
            if unknown:
                raise GenerationError(
                    f"{exp.name}: unknown character id(s) "
                    f"{', '.join(unknown)} (the roster: "
                    f"{', '.join(sorted(known))})"
                )
        if not args.new_baseline:
            # Fail before the (GPU-heavy) forced run.
            for entry in entries:
                _require_baseline(
                    f"{exp.name}/{entry.stem}",
                    _baseline_path(exp.name, entry.stem, preset),
                )
            _require_baseline(
                f"{exp.name}/expansion",
                _baseline_path(exp.name, "expansion", preset),
            )
        _generate(expansion_path, ids)
        for entry in entries:
            info = expansion.resolve_character(entry)
            actual = {
                path.relative_to(REPO_ROOT).as_posix(): _sha256(path)
                for path in _expected_outputs(
                    exp, entry, expansion.presentations_for(exp, entry, info), preset
                )
            }
            baseline = _baseline_path(exp.name, entry.stem, preset)
            label = f"{exp.name}/{entry.stem}"
            if args.new_baseline:
                _write_baseline(baseline, label, preset, actual)
                print(
                    "Recorded "
                    f"{len(actual)} file(s) to {baseline.relative_to(REPO_ROOT)}."
                )
            else:
                _compare(label, baseline, actual)
        # The expansion's pack and box images (one pair per expansion).
        set_path = preset.set_path(exp.name)
        expansion_actual = {
            path.relative_to(REPO_ROOT).as_posix(): _sha256(path)
            for path in (
                set_path / PACK_MATERIAL_NAME,
                set_path / PACK_ITEM_NAME,
                set_path / BOX_MATERIAL_NAME,
                set_path / BOX_ITEM_NAME,
            )
        }
        expansion_baseline = _baseline_path(exp.name, "expansion", preset)
        label = f"{exp.name}/expansion"
        if args.new_baseline:
            _write_baseline(expansion_baseline, label, preset, expansion_actual)
            print(
                "Recorded "
                f"{len(expansion_actual)} file(s) to "
                f"{expansion_baseline.relative_to(REPO_ROOT)}."
            )
        else:
            _compare(label, expansion_baseline, expansion_actual)
    except GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "byte-for-byte regression check: generate every presentation "
            "of a character (its full-art, profile and standard cards "
            "plus the expansion's pack and box images) with a forced, "
            "single-worker run and compare the finished files' SHA-256 "
            "against the recorded baselines "
            f"({BASELINES_DIR.relative_to(REPO_ROOT)}/<set>/)"
        )
    )
    parser.add_argument(
        "paths",
        type=str,
        nargs="+",
        metavar="ARG",
        help=(
            "the expansion (its name or path — cards/<set>.toml, "
            "<set>.toml or <set>) and, optionally, the characters' "
            "viewer ids (default: every character of the expansion)"
        ),
    )
    parser.add_argument(
        "--new-baseline",
        action="store_true",
        help=(
            "record (overwrite) the baselines from this run's outputs "
            "instead of comparing against the recorded ones"
        ),
    )
    return parser.parse_args()


def _generate(expansion_path: Path, ids: list[str]) -> None:
    """The forced, single-worker generate run behind the check (see the
    module docstring): the byte protocol — the same code, inputs and
    worker count produce the same bytes."""
    argv = [
        "--jobs",
        "1",
        "--force",
        expansion_path.relative_to(REPO_ROOT).as_posix(),
    ]
    if ids:
        argv += ["--ids", *ids]
    try:
        generate.run(argv)
    except SystemExit as exc:
        # A failed generate already reported the error; keep its code.
        if exc.code:
            sys.exit(exc.code)


def _expected_outputs(
    exp: expansion.Expansion,
    entry: expansion.CardEntry,
    presentations: list[expansion.Presentation],
    preset: Preset,
) -> list[Path]:
    """The finished files a forced generate of *entry* at *preset*
    writes: every presentation's card (plus the animated presentations'
    first-frame PNGs). Mirrors the pipeline's own selection (see
    :func:`generate.run`)."""
    outs: list[Path] = []
    for presentation in presentations:
        animated = presentation.animated
        suffix = "mp4" if animated else "png"
        outs.append(
            card.output_path(exp.name, entry.stem, presentation.name, suffix, preset)
        )
        if animated:
            # The animation's first frame is kept alongside it.
            outs.append(
                card.output_path(exp.name, entry.stem, presentation.name, "png", preset)
            )
    return outs


def _baseline_path(set_name: str, card_name: str, preset: Preset) -> Path:
    """The recorded baseline: ``tests/baselines/<set>/<name>.<preset>.sha256``
    (the character's, or the expansion's pack and box with *card_name*
    ``expansion``)."""
    return BASELINES_DIR / set_name / f"{card_name}.{preset.value}.sha256"


def _sha256(path: Path) -> str:
    """The file's SHA-256 (hex)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_baseline(
    baseline: Path, label: str, preset: Preset, actual: dict[str, str]
) -> None:
    """Write (overwriting) the recorded baseline from *actual* (repo-
    relative path -> SHA-256), in ``sha256sum``-compatible format
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
    """Fail when there is no recorded baseline yet."""
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
