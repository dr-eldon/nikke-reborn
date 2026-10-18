#!/usr/bin/env python3
"""Regenerate every card variant on disk, in parallel where it's safe.

The one-command replacement for running compare_effects.py with the
card tokens plus the manual sheet-consistency check:

- every card dir under effects/ whose JSON exists in CARDS_DIR is
  re-run with the default combo (glow+trail);
- the GPU render phase runs serially (concurrent nikke-viewer wgpu
  devices exhaust the GPU), then the CPU overlay phase (base
  composites, effect layers, PNG saves) runs one card per worker —
  that is where the parallelism pays;
- the contact sheet is rebuilt;
- every sheet cell is verified byte-identical to its card crop.

Run:  .venv/bin/python scripts/regen_cards.py
"""

import os
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_effects as ce
import nikke_reborn as nr


def _standard_cards() -> list[Path]:
    """Card JSONs for every card dir on disk (empty dirs included —
    e.g. right after dropping a combo's outputs)."""
    cards: list[Path] = []
    for d in sorted(ce.OUT_ROOT.rglob("*")):
        if not d.is_dir():
            continue
        rel = d.relative_to(ce.OUT_ROOT)
        json_path = ce.nr.CARDS_DIR / rel.parent / f"{rel.name}.json"
        if json_path.is_file():
            cards.append(json_path)
    return cards


def main() -> None:
    cards = _standard_cards()
    if not cards:
        print("no card dirs on disk; run compare_effects.py first", file=sys.stderr)
        sys.exit(1)
    workers = min(len(cards), os.cpu_count() or 1)
    print(
        f"regenerating {len(cards)} card(s) with {workers} overlay worker(s): "
        + ", ".join(p.relative_to(ce.nr.CARDS_DIR).as_posix() for p in cards),
        flush=True,
    )
    started = time.time()

    workdirs = [Path(tempfile.mkdtemp(prefix="nikke-reborn-")) for _ in cards]
    try:
        # ---- serial GPU: one nikke-viewer device at a time ----
        artifacts = []
        for json_path, workdir in zip(cards, workdirs):
            print(f"  render {json_path.stem}", flush=True)
            try:
                artifacts.append(nr._render_card(json_path, workdir))
            except Exception as exc:
                print(f"  ! {json_path.stem}: {exc}", file=sys.stderr, flush=True)
                sys.exit(1)

        # ---- parallel CPU: overlays + saves, one card per worker ----
        total = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(ce._overlay_card, jp, a, ce.COMBOS, ce.WORKERS): jp
                for jp, a in zip(cards, artifacts)
            }
            for fut in as_completed(futures):
                try:
                    total += fut.result()
                except RuntimeError as exc:
                    print(f"  ! {exc}", file=sys.stderr, flush=True)
                    sys.exit(1)
    finally:
        for workdir in workdirs:
            shutil.rmtree(workdir, ignore_errors=True)

    sheet = ce._build_sheet(ce.OUT_ROOT)
    if sheet is not None:
        nr._save_atomic(sheet, ce.OUT_ROOT / "contact-sheet.png")
        total += 1
        print("  contact-sheet rebuilt (one section per static variant on disk)", flush=True)
        if not ce.check_sheet_consistency():
            print("  ! contact-sheet cell mismatch", file=sys.stderr, flush=True)
            sys.exit(1)

    print(f"Done: {total} file(s) in {time.time() - started:.1f}s -> {ce.OUT_ROOT}/")


if __name__ == "__main__":
    main()
