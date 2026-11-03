#!/usr/bin/env python3
"""The coverage check for the date validation (run: ``python3 scripts/validate_coverage.py``).

Verifies that the bucket files' tables cover ``database/models.json``
exactly: every model id appears in one and only one bucket table, and
no table row names an id that models.json does not know. The pending
buckets' placeholder tables count (their ids are part of the same
planned partition even though their dates are unverified).

Only each file's main table is read — the one headed
``| # | id | name | date | evidence | verdict |``. The Corrections
table (five cells: recorded/corrected dates, no evidence/verdict)
re-lists corrected ids as cross-references and must not be counted,
or every correction would read as a duplicate.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The main table's header cells. The Corrections table's header
#: (recorded/corrected dates instead of evidence/verdict) never
#: matches, so its re-listed ids are excluded from the coverage.
HEADER = ("#", "id", "name", "date", "evidence", "verdict")


def _cells(line: str) -> list[str]:
    # The evidence cell may hold an escaped pipe (``\|``) inside a
    # quoted wiki link; split on the unescaped pipes only.
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def _table_ids(path: Path) -> list[str]:
    """The ids of *path*'s main table, in row order (empty when the
    file has no such table)."""
    ids: list[str] = []
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not in_table:
            in_table = line.startswith("|") and _cells(line) == list(HEADER)
            continue
        if not line.startswith("|"):
            break
        cells = _cells(line)
        if cells[0].isdigit():  # the ``|---|`` separator row fails this
            ids.append(cells[1])
    return ids


def _model_ids(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as handle:
        models = json.load(handle)
    return [model["id"] for model in models if isinstance(model, dict) and "id" in model]


def run() -> None:
    models = _model_ids(REPO_ROOT / "database" / "models.json")
    model_set = set(models)
    bucket_paths = sorted(REPO_ROOT.glob("BUCKET_*.md"))
    problems = 0

    for dup in sorted(i for i, n in Counter(models).items() if n > 1):
        print(f"DUPLICATE in models.json: {dup}")
        problems += 1

    occurrences: dict[str, list[str]] = {}
    for path in bucket_paths:
        ids = _table_ids(path)
        print(f"{path.name}: {len(ids)} rows")
        for dup in sorted(i for i, n in Counter(ids).items() if n > 1):
            print(f"DUPLICATE in {path.name}: {dup}")
            problems += 1
        for model_id in ids:
            occurrences.setdefault(model_id, []).append(path.name)

    for unknown in sorted(set(occurrences) - model_set):
        print(f"UNKNOWN {unknown} (in {', '.join(occurrences[unknown])}, not in models.json)")
        problems += 1
    for missing in sorted(model_set - set(occurrences)):
        print(f"MISSING {missing} (in models.json, in no bucket table)")
        problems += 1
    for dup in sorted(i for i, files in occurrences.items() if len(files) > 1):
        print(f"DUPLICATE {dup} (in {', '.join(dict.fromkeys(files))})")
        problems += 1

    if problems:
        print(
            f"error: {problems} coverage defect(s) — the bucket tables do not "
            "cover models.json exactly.",
            file=sys.stderr,
        )
        sys.exit(1)
    print(
        f"OK: {len(models)} model ids, one row each across {len(bucket_paths)} "
        "bucket files — models.json covered exactly."
    )


if __name__ == "__main__":
    run()
