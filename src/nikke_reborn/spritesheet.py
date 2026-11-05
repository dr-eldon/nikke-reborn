"""Compose an expansion's sprite sheet: an overview of all its rendered
cards, fitted to the grid — over the expansion's background (dimmed
toward black so the grid reads against it).

The sheet composites the finished first frames
(``output/<set>/<stem>_<rarity index>_<presentation>.png``) into a
grid: the
expansion's logo at the top, one row per character (a label column
with the card's number and name) and one column per presentation
(the expansion's ``rarities`` subset, in its order; a column only
when the roster carries it). The animated cards (an ``.mp4`` next to
their first frame) are marked with a white ▶ in a black circle, and
the cards' copyright line sits at the bottom left.

The grid is windowed into images of at most :data:`SHEET_ROWS` rows
each — ``<set>_{n}.png``, 1-based (``draft/<set>_{n}.png`` for
``--draft``) — each self-contained (its own header and copyright) and
carrying the same geometry: the label column is sized from the full
roster's labels, so the images are equally wide and the grid keeps
its column positions across them.

Besides the pages, the run writes the summary grid — ``<set>.png``,
:data:`SHEET_TARGET`: every first frame tiled across the whole canvas
in the roster's order (each character's presentations in the
expansion's rarity order), each card's corners rounded, the tiling's
empty cells past the last card split between the first and the last row
(both centered, so they carry the same empty space), and the
expansion's logo at the sheet's center — no labels, no footer.

The cells are the first frames only — the PNGs the pipeline writes
for every card; no video is read or decoded. Every cell must already
be on disk, so the sheet is composed after ``generate`` (missing
cards are rendered as placeholders, named).

Like the finished cards, every sheet image embeds the SHA-256 of its
inputs under the source-hash key, and an image whose stored hash
matches the current inputs is skipped instead of re-composed. The
rows' first frames are decoded and resized in parallel threads; the
canvas is assembled on the main thread. ``--force`` skips the
up-to-date check.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import os
import re
import sys
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from nikke_reborn import card, expansion
from nikke_reborn.config import (
    CARD_REFERENCE_WIDTH,
    CARD_VIEWPORT,
    FONT,
    IMAGES_DIR,
    MAX_STAGE_THREADS,
    REPO_ROOT,
    SOURCE_HASH_KEY,
)
from nikke_reborn.error import GenerationError
from nikke_reborn.file import _save_atomic, hash_term
from nikke_reborn.lettering import (
    COPYRIGHT_NOMINAL_SIZE,
    COPYRIGHT_SUPERSAMPLE,
    COPYRIGHT_TEXT,
    COPYRIGHT_WEIGHT,
    _set_weight,
    _text_ink_offsets,
)
from nikke_reborn.preset import Preset

# --- the finished sheet's geometry ----------------------------------------
#: The sheet's margin around the header and the grid (on every side); the
#: sheet is fitted to its content on both axes.
MARGIN = 48
#: The header's logo is scaled to fit a box of 60% of the sheet's width by
#: LOGO_MAX_HEIGHT, aspect preserved (the height cap is in pixels, since
#: the sheet's height is derived from its content).
HEADER_LOGO_FRACTION_W = 0.6
LOGO_MAX_HEIGHT = 324
#: The padding above the logo inside the header band.
HEADER_PADDING = 48
#: The gap between the logo's bottom and the grid: more air than the
#: sheet's margin, so the header reads as its own band.
HEADER_GRID_GAP = 96
#: The label column's inset from the longest label's ink (left and right).
LABEL_PAD = 16
#: The label column's cap, as a fraction of the grid's card width
#: (capping against the sheet's width would be circular): the label
#: font shrinks until the longest prefix fits it.
LABEL_MAX_FRACTION = 0.30
#: The label font's weight (Oswald's variable axis).
LABEL_WEIGHT = 500
#: The label font sizes tried, largest first: the first whose longest
#: prefix fits the label column's cap is used.
LABEL_FONT_SIZES = (48, 44, 40, 36, 32, 28, 24, 20)
#: The height of every grid row (px): the cell's width is derived from
#: it, by the card's aspect.
ROW_HEIGHT = 160
#: The rows per sheet image (the last one shorter): the grid is
#: windowed into ``<set>_{n}.png`` (1-based) images, each self-
#: contained (its own header and copyright) and equally wide (the
#: label column is sized from the full roster's labels).
SHEET_ROWS = 20
#: The summary grid's canvas (px): every first frame tiled
#: across it, in the roster's order, the dimmed background
#: showing between the cards.
SHEET_TARGET = (3840, 2160)
#: The spacing between the summary grid's cards (px): each card is
#: inset by half of it on every side, so adjacent cards are this far
#: apart — the dimmed background shows through the gaps.
SUMMARY_CELL_GAP = 12
#: The summary grid's cards' corner rounding: the radius is this
#: fraction of the card's smaller side, so the rounding scales with
#: the cards (the dimmed background shows through the corners).
SUMMARY_CORNER_RADIUS_FRACTION = 0.05
#: The summary grid's logo's height, as a fraction of the sheet's:
#: the logo is composited over the grid, at the sheet's center, with
#: the pack's and box's fronts' treatment (see
#: ``expansion._composite_logo``).
SUMMARY_LOGO_FRACTION = 1 / 5
#: The summary grid's logo's drop shadow — a darkened, blurred copy of
#: the mark, offset down-right, behind it: its blur radius and offset
#: (sheet-height fractions) and its peak opacity.
SUMMARY_LOGO_SHADOW_RADIUS = 0.01
SUMMARY_LOGO_SHADOW_OFFSET = 0.005
SUMMARY_LOGO_SHADOW_ALPHA = 0.9
#: The gutter between the label column and the grid.
LABEL_GAP = 32
#: The gutter between the grid's cells.
CELL_GAP = 8
#: The fraction of the background's brightness kept (the background is
#: dimmed toward black so the grid and the labels read against it).
BACKGROUND_DIM = 0.45
#: The row-label color.
LABEL_COLOR = (235, 238, 245)
#: The column-label font sizes tried, largest first: the first whose
#: longest label fits the cell's width is used.
COLUMN_LABEL_SIZES = (24, 22, 20, 18, 16, 14, 12, 10)
#: The column-labels' weight (Oswald's variable axis).
COLUMN_LABEL_WEIGHT = 700
#: The gap between the column-label row and the grid's first row.
COLUMN_LABEL_GAP = 16
#: The marker's height (px): the ▶ symbol, a filled white triangle.
ANIMATED_MARKER_SIZE = 13
#: The black circle's clearance around the glyph (px, on each side).
ANIMATED_MARKER_PAD = 4
#: The black circle's alpha: a bit translucent, so the card's art shows
#: through softly.
ANIMATED_MARKER_CIRCLE_ALPHA = 180
#: The legend's text (beside the ▶ badge, in the sheet's top-right
#: corner).
LEGEND_TEXT = "= Animated"
#: The legend's font size (px, Oswald).
LEGEND_FONT_SIZE = 20
#: The gap between the legend's badge and its text (px).
LEGEND_GAP = 10
#: The copyright line's size relative to the cards' width-proportional
#: size (a bit smaller on the sheet).
COPYRIGHT_FRACTION = 0.75
#: The text drawn in a cell whose card is missing: a missing first frame
#: renders as a black placeholder box with this text, instead of failing
#: the whole sheet.
MISSING_TEXT = "MISSING!"
#: The font sizes tried for the missing placeholder, largest first: the first
#: whose text fits the cell's width is used.
MISSING_FONT_SIZES = (28, 24, 20, 18, 16, 14, 12, 10)


_Part = tuple[Path, int, int, tuple[int, int] | None, bool]


def run() -> None:
    """Compose the selected expansion's sprite sheet (the ``spritesheet``
    command)."""
    args = _parse_args()
    preset = Preset.DRAFT if args.draft else Preset.DEFAULT
    try:
        parts = _build(args.expansion, preset, args.force)
    except GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    for out_path, rows, columns, size, skipped in parts:
        if skipped:
            print(
                f"{out_path.relative_to(REPO_ROOT)}: up to date; "
                f"skipping (use --force to rebuild)"
            )
        else:
            print(
                f"Done. Wrote {out_path.relative_to(REPO_ROOT)} "
                f"({size[0]}x{size[1]}, {rows} row(s) x {columns} column(s))"
            )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compose an expansion's sprite sheet: the summary grid "
            "(every first frame tiled across one "
            f"{SHEET_TARGET[0]}x{SHEET_TARGET[1]} image) and the grid's "
            "pages (the expansion's logo on top, one row per character, "
            f"one column per presentation, windowed into {SHEET_ROWS}-row "
            "images)"
        )
    )
    parser.add_argument(
        "expansion",
        help=(
            "the expansion's name or path (cards/<set>.toml, <set>.toml "
            "or <set>, e.g. ELYSION)"
        ),
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help=(
            "read the first frames from draft/ and write draft/<set>.png "
            "and draft/<set>_{n}.png"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="rebuild the sheet images even when the ones on disk are up to date",
    )
    return parser.parse_args()


def _build(name: str, preset: Preset, force: bool) -> list[_Part]:
    """Compose the expansion *name*'s sheet images: the summary grid
    (``<name>.png``, every first frame tiled across
    :data:`SHEET_TARGET`) and its pages (``<name>_{n}.png`` in the
    preset's output root, one per :data:`SHEET_ROWS` rows of the grid,
    1-based).

    Returns one entry per image: its path, its grid's row and column
    counts, its canvas size (None when the image was skipped) and
    whether it was skipped (up to date)."""
    exp = expansion.load_expansion(expansion.resolve_expansion_path(name))
    rows, columns, cells = _card_grid(exp)
    if not rows:
        raise GenerationError(f"{exp.name}: the expansion's roster is empty")
    # Every presentation's first frame (the still card's PNG or the
    # video card's PNG sidecar) at the pipeline's own output path.
    paths = {
        (prefix, column): card.output_path(
            exp.name, prefix, column, exp.rarities.index(column) + 1, "png", preset
        )
        for prefix, column in sorted(cells)
    }
    # A cell whose first frame is not on disk renders as a placeholder
    # (below) instead of failing the whole sheet.
    missing = {key for key, path in paths.items() if not path.is_file()}
    if missing:
        shown = ", ".join(
            str(paths[key].relative_to(REPO_ROOT)) for key in sorted(missing)[:10]
        )
        more = f" (+{len(missing) - 10} more)" if len(missing) > 10 else ""
        print(
            f"warning: {len(missing)} rendered card(s) missing for "
            f"{exp.name} (run 'generate' first); rendering them as a "
            f"'{MISSING_TEXT}' placeholder: {shown}{more}",
            file=sys.stderr,
        )
    background, background_path = _expansion_background(exp)
    logo, logo_path = _expansion_logo(exp)
    aspect = _card_aspect()
    # The label column is sized from the full roster's labels, so every
    # image carries the same geometry (the same width, the same font)
    # and the grid keeps its positions across the images.
    labels = _row_labels(exp.cards)
    cell_w = round(ROW_HEIGHT * aspect)
    font, label_w = _label_font(
        labels, len(columns) * cell_w + (len(columns) - 1) * CELL_GAP
    )
    parts: list[_Part] = []
    # The summary grid: the first frames tiled across SHEET_TARGET
    # in the roster's order, the cards flowing around the logo's
    # keep-out at the sheet's center — no labels or footer.
    ordered = _ordered_cells(exp.cards, columns, cells)
    logo_box = _summary_logo_box(
        SHEET_TARGET[0],
        SHEET_TARGET[1],
        logo.width / logo.height,
        SUMMARY_LOGO_FRACTION,
    )
    keep_out = _summary_keep_out(SHEET_TARGET[1])
    summary_rows, summary_cols = _summary_dimensions(len(ordered), logo_box, keep_out)
    summary_path = preset.base / f"{exp.name}.png"
    summary_hash = _summary_source_hash(exp, logo_path, background_path, ordered, paths)
    if not force and _stored_hash(summary_path) == summary_hash:
        parts.append((summary_path, summary_rows, summary_cols, None, True))
    else:
        size = _summary_grid(
            ordered,
            paths,
            missing,
            background,
            logo,
            summary_path,
            summary_hash,
            summary_rows,
            summary_cols,
            logo_box,
            keep_out,
        )
        parts.append((summary_path, summary_rows, summary_cols, size, False))
    for n, start in enumerate(range(0, len(rows), SHEET_ROWS), 1):
        part_rows = rows[start : start + SHEET_ROWS]
        part_cells = {key for key in cells if key[0] in part_rows}
        part_paths = {key: paths[key] for key in part_cells}
        out_path = preset.base / f"{exp.name}_{n}.png"
        source_hash = _source_hash(exp, logo_path, background_path, rows, part_paths)
        if not force and _stored_hash(out_path) == source_hash:
            parts.append((out_path, len(part_rows), len(columns), None, True))
            continue
        size = _compose(
            exp.cards[start : start + SHEET_ROWS],
            columns,
            part_cells,
            part_paths,
            logo,
            background,
            out_path,
            source_hash,
            missing & part_cells,
            aspect,
            labels[start : start + SHEET_ROWS],
            font,
            label_w,
        )
        parts.append((out_path, len(part_rows), len(columns), size, False))
    return parts


def _card_grid(
    exp: expansion.Expansion,
) -> tuple[list[str], list[str], set[tuple[str, str]]]:
    """The sheet's grid: its rows (the card's stems, in the roster's
    order), its columns (every presentation the roster carries, in the
    order of the expansion's ``rarities``) and its cells (the
    stem/presentation pairs the roster actually has).

    The cells mirror the pipeline's eligibility exactly (each
    character's presentations come from
    :func:`nikke_reborn.expansion.presentations_for`, the same source
    the run's selection uses), so a sheet composed after ``generate``
    never asks for a card the pipeline does not render."""
    rows: list[str] = []
    present: set[str] = set()
    cells: set[tuple[str, str]] = set()
    for entry in exp.cards:
        rows.append(entry.stem)
        info = expansion.resolve_character(entry)
        for presentation in expansion.presentations_for(exp, entry, info):
            present.add(presentation.name)
            cells.add((entry.stem, presentation.name))
    columns = [name for name in exp.rarities if name in present]
    return rows, columns, cells


def _ordered_cells(
    entries: Sequence[expansion.CardEntry],
    columns: list[str],
    cells: set[tuple[str, str]],
) -> list[tuple[str, str]]:
    """The grid's cells as a flat sequence in the roster's order (each
    character's presentations in the expansion's rarity order) — the
    order the summary grid tiles them."""
    return [
        (stem, column)
        for stem in (entry.stem for entry in entries)
        for column in columns
        if (stem, column) in cells
    ]


def _card_aspect() -> float:
    """The cards' width/height ratio: the pipeline's card viewport
    (every half-body card in a set shares it — the goddess presentation
    renders the card's full body on the square viewport, and its cells
    read at the same ratio). Not read from the rendered PNGs: a first
    frame might be missing."""
    return CARD_VIEWPORT[0] / CARD_VIEWPORT[1]


def _expansion_background(
    exp: expansion.Expansion,
) -> tuple[Image.Image, Path]:
    """The expansion's background (RGBA) and its file: its
    ``background.base``, resolved against the expansion's folder."""
    path = (exp.path.parent / exp.backgrounds["base"]).resolve()
    if not path.is_file():
        raise GenerationError(
            f"{exp.name}: background not found: {exp.backgrounds['base']}"
        )
    return expansion.load_background(exp), path


def _expansion_logo(exp: expansion.Expansion) -> tuple[Image.Image, Path]:
    """The expansion's logo (RGBA) and its file: its ``logo.path``
    (resolved against the expansion's folder) when the file exists, else
    ``assets/images/logos/<set>.png``."""
    path = (exp.path.parent / exp.logo_path).resolve()
    if path.is_file():
        return Image.open(path).convert("RGBA"), path
    fallback = IMAGES_DIR / "logos" / f"{exp.name}.png"
    if fallback.is_file():
        return Image.open(fallback).convert("RGBA"), fallback
    raise GenerationError(
        f"no logo for expansion {exp.name!r}: {exp.logo_path!r} (against "
        f"the expansion's folder) is not a file and neither is "
        f"{fallback.relative_to(REPO_ROOT)}"
    )


def _source_hash(
    exp: expansion.Expansion,
    logo_path: Path,
    background_path: Path,
    rows: list[str],
    paths: dict[tuple[str, str], Path],
) -> str:
    """SHA-256 of the sheet image's inputs: the expansion's name, its logo,
    its background, the full roster's stems (the image's label column is
    sized from them, so a roster change re-composes every image) and the
    image's own first frames (a missing card hashes a sentinel, so the
    image re-composes when it appears) and each cell's animated state (an
    ``.mp4`` next to the first frame; it drives the ▶ markers) — embedded
    under :data:`nikke_reborn.SOURCE_HASH_KEY` so an unchanged image is
    skipped instead of re-composed."""
    digest = hashlib.sha256()
    digest.update(exp.name.encode())
    digest.update(logo_path.read_bytes())
    digest.update(background_path.read_bytes())
    for stem in rows:
        digest.update(stem.encode())
    for key in sorted(paths):
        path = paths[key]
        digest.update(path.name.encode())
        if path.is_file():
            digest.update(path.read_bytes())
        else:
            digest.update(b"missing")
        digest.update(b"1" if path.with_suffix(".mp4").is_file() else b"0")
    return digest.hexdigest()


def _summary_source_hash(
    exp: expansion.Expansion,
    logo_path: Path,
    background_path: Path,
    ordered: list[tuple[str, str]],
    paths: dict[tuple[str, str], Path],
) -> str:
    """SHA-256 of the summary grid's inputs — everything it draws: the
    expansion's name, its logo and background and the ordered cells'
    first frames (a missing card hashes a sentinel, so the grid
    re-composes when the card appears; the labels and the animated
    state do not enter it — the grid draws neither). Embedded under
    :data:`nikke_reborn.SOURCE_HASH_KEY` so an unchanged grid is
    skipped instead of re-composed."""
    digest = hashlib.sha256()
    hash_term(digest, exp.name.encode())
    hash_term(digest, logo_path.read_bytes())
    hash_term(digest, background_path.read_bytes())
    for stem, column in ordered:
        hash_term(digest, stem.encode())
        hash_term(digest, column.encode())
        path = paths[(stem, column)]
        hash_term(digest, path.read_bytes() if path.is_file() else b"missing")
    return digest.hexdigest()


def _stored_hash(out_path: Path) -> str | None:
    """The source-hash key embedded in an existing sheet, or None when the
    file is absent or carries no readable tag."""
    if not out_path.is_file():
        return None
    try:
        with Image.open(out_path) as image:
            return image.info.get(SOURCE_HASH_KEY)
    except Exception:  # noqa: BLE001 — older/corrupt cards simply
        # carry no readable tag: treat the file as stale (None)
        return None


def _split_camel(text: str) -> str:
    """Whitespace between each capital letter of *text*'s CamelCase
    (``BlackSunday`` reads as ``Black Sunday``; single words unchanged)."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)


def _column_label(column: str) -> str:
    """The column's header label: the rarity's name with whitespace
    between each capital letter (``CoverProfile`` reads as
    ``Cover Profile``)."""
    return _split_camel(column)


def _row_label(entry: expansion.CardEntry, width: int) -> str:
    """The row's label: the card's number as ``#<number>`` (zero-padded
    to *width* digits, so the labels' numbers align) and its words'
    CamelCase split by whitespace — the character's name, and its
    subtitle after a colon when it has one."""
    label = f"#{entry.number:0{width}d} {_split_camel(entry.title)}"
    if entry.subtitle:
        label += ": " + _split_camel(entry.subtitle)
    return label


def _row_labels(entries: Sequence[expansion.CardEntry]) -> list[str]:
    """The row labels for *entries* (:func:`_row_label`, the numbers padded
    to the longest number's digit count, so the column aligns)."""
    width = max(len(str(entry.number)) for entry in entries)
    return [_row_label(entry, width) for entry in entries]


def _column_label_font(labels: list[str], max_w: int) -> ImageFont.FreeTypeFont:
    """The column-label font: the largest of :data:`COLUMN_LABEL_SIZES`
    whose longest label fits *max_w* px (the cell's width)."""
    for size in COLUMN_LABEL_SIZES:
        font = ImageFont.truetype(str(FONT), size)
        _set_weight(font, COLUMN_LABEL_WEIGHT)
        if max(font.getlength(label) for label in labels) <= max_w:
            return font
    raise GenerationError(
        f"column labels do not fit the cells at the smallest label font "
        f"({COLUMN_LABEL_SIZES[-1]} px); the longest is {max(labels, key=len)!r}"
    )


def _missing_font(cell_w: int) -> ImageFont.FreeTypeFont:
    """The font for the *MISSING_TEXT* placeholder: the largest of
    :data:`MISSING_FONT_SIZES` whose text fits the cell's width (*cell_w*,
    with a little side padding); the smallest is used as a last resort."""
    for size in MISSING_FONT_SIZES:
        font = ImageFont.truetype(str(FONT), size)
        _set_weight(font, COLUMN_LABEL_WEIGHT)
        if font.getlength(MISSING_TEXT) <= cell_w - 8:
            return font
    return ImageFont.truetype(str(FONT), MISSING_FONT_SIZES[-1])


def _label_font(labels: list[str], card_w: int) -> tuple[ImageFont.FreeTypeFont, int]:
    """The row-label font and the label column's width: the largest of
    :data:`LABEL_FONT_SIZES` whose longest label fits the column's cap
    (LABEL_MAX_FRACTION of the grid's card width *card_w*, including the
    padding)."""
    cap = round(LABEL_MAX_FRACTION * card_w) - 2 * LABEL_PAD
    for size in LABEL_FONT_SIZES:
        font = ImageFont.truetype(str(FONT), size)
        _set_weight(font, LABEL_WEIGHT)
        longest = max(round(font.getlength(label)) for label in labels)
        if longest <= cap:
            return font, longest + 2 * LABEL_PAD
    raise GenerationError(
        f"row labels do not fit the sheet at the smallest label font "
        f"({LABEL_FONT_SIZES[-1]} px); the longest is {max(labels, key=len)!r}"
    )


def _row_cards(
    prefix: str,
    paths: dict[tuple[str, str], Path],
    columns: list[str],
    cells: set[tuple[str, str]],
    size: tuple[int, int],
    missing: set[tuple[str, str]],
) -> tuple[str, dict[str, Image.Image]]:
    """The row's first frames, each converted and resized to the cell's
    *size*: one image per column the row has (the *missing* cells are not
    loaded here — the placeholder box is drawn by :func:`_compose`). Runs in
    a worker thread — Pillow releases the GIL in the decode and the LANCZOS
    resize — and only ever produces its own images, never touching the shared
    canvas (Pillow images are not thread-safe)."""
    cell_w, cell_h = size
    cards = {}
    for column in columns:
        key = (prefix, column)
        if key not in cells or key in missing:
            continue
        with Image.open(paths[key]) as card:
            cards[column] = card.convert("RGBA").resize(
                (cell_w, cell_h), Image.Resampling.LANCZOS
            )
    return prefix, cards


def _dimmed_background(background: Image.Image, size: tuple[int, int]) -> Image.Image:
    """The expansion's *background* fitted to *size* and dimmed toward
    black (the sheets' canvas, so the grid and the labels read against
    it)."""
    canvas = expansion._fit_cover(background, size)
    return Image.blend(
        canvas, Image.new("RGBA", canvas.size, (0, 0, 0, 255)), 1 - BACKGROUND_DIM
    )


def _compose(
    entries: Sequence[expansion.CardEntry],
    columns: list[str],
    cells: set[tuple[str, str]],
    paths: dict[tuple[str, str], Path],
    logo: Image.Image,
    background: Image.Image,
    out_path: Path,
    source_hash: str,
    missing: set[tuple[str, str]],
    aspect: float,
    labels: list[str],
    font: ImageFont.FreeTypeFont,
    label_w: int,
) -> tuple[int, int]:
    """Draw one sheet image — the logo header (the logo with the pack's
    and box's glow and trail treatment), the column labels, the label
    column and the rows of first frames (the animated cards' cells
    marked with a white ▶ in a black circle, a black *MISSING_TEXT*
    placeholder box for the cells in *missing*, and a legend — the
    badge and ``= Animated`` — in the top-right corner) — over the
    expansion's *background* (resized to cover the canvas without
    deformation, bottom edges aligned, and dimmed toward black), on a
    canvas fitted to its content, the cards' copyright line (a bit
    smaller) in white at the bottom left, and write it to *out_path*
    (atomically, the *source_hash* embedded). *entries* is the image's
    rows (a window of the expansion's roster, in the roster's order)
    and *labels* their labels, in the same order (*font* and *label_w*
    being the label font and column width sized from the full roster,
    so the images align); the rows' first frames are decoded and
    resized in parallel threads; the finished canvas is assembled on
    the main thread. Returns the canvas's size."""
    rows = [entry.stem for entry in entries]
    row_count = len(rows)
    col_count = len(columns)
    gutter_total = (col_count - 1) * CELL_GAP

    # --- the grid's geometry --------------------------------------------
    cell_w = round(ROW_HEIGHT * aspect)
    cell_h = ROW_HEIGHT
    grid_h = row_count * cell_h + (row_count - 1) * CELL_GAP
    card_w = col_count * cell_w + gutter_total
    width = label_w + LABEL_GAP + card_w + 2 * MARGIN

    # --- the header: the expansion's logo, centered ---------------------
    box_w = round(HEADER_LOGO_FRACTION_W * width)
    scale = min(box_w / logo.width, LOGO_MAX_HEIGHT / logo.height)
    logo = logo.resize(
        (max(1, round(logo.width * scale)), max(1, round(logo.height * scale))),
        Image.Resampling.LANCZOS,
    )
    header = logo.height + HEADER_PADDING + HEADER_GRID_GAP

    # --- the column labels (above the grid) -----------------------------
    col_labels = [_column_label(column) for column in columns]
    col_font = _column_label_font(col_labels, cell_w)
    label_h = sum(col_font.getmetrics())

    missing_font = _missing_font(cell_w)

    # The ▶ markers: the cells whose card is animated (an .mp4 next to
    # its first frame) get one centered in the cell. The symbol is a
    # filled white triangle drawn at 4x and downscaled, so the LANCZOS
    # downscale stays crisp.
    marker_draw = ANIMATED_MARKER_SIZE * 4
    scratch = Image.new("RGBA", (marker_draw, marker_draw))
    tri_w = round(marker_draw * 0.866)  # an equilateral triangle's width
    left = (marker_draw - tri_w) // 2
    ImageDraw.Draw(scratch).polygon(
        (
            (left, 0),
            (left + tri_w, marker_draw // 2),
            (left, marker_draw),
        ),
        fill=(255, 255, 255, 255),
    )
    marker = scratch.resize(
        (round(ANIMATED_MARKER_SIZE * 0.866), ANIMATED_MARKER_SIZE),
        Image.Resampling.LANCZOS,
    )
    # The badge: a translucent black circle enclosing the glyph, drawn
    # at 4x and downscaled — Pillow's ellipse is not anti-aliased.
    badge_d = marker.height + 2 * ANIMATED_MARKER_PAD
    badge_draw = badge_d * 4
    badge = Image.new("RGBA", (badge_draw, badge_draw))
    ImageDraw.Draw(badge).ellipse(
        (0, 0, badge_draw - 1, badge_draw - 1),
        fill=(0, 0, 0, ANIMATED_MARKER_CIRCLE_ALPHA),
    )
    badge = badge.resize((badge_d, badge_d), Image.Resampling.LANCZOS)
    # The triangle's mass sits on its base (the left edge), so its ink is
    # nipped 1 px right of the geometric center — shifting it 1 px right
    # reads as optically centered in the circle.
    badge.alpha_composite(
        marker,
        ((badge_d - marker.width) // 2 + 1, (badge_d - marker.height) // 2),
    )
    animated = {
        key for key, path in paths.items() if path.with_suffix(".mp4").is_file()
    }

    height = header + label_h + COLUMN_LABEL_GAP + grid_h + MARGIN
    canvas = _dimmed_background(background, (width, height))
    draw = ImageDraw.Draw(canvas)

    # --- the header's logo, the way the pack's and box's fronts render --
    # it (see expansion._composite_logo for the treatment).
    glow_color = expansion._background_glow_color(expansion._image_average(canvas))
    logo_x = (width - logo.width) // 2
    halo, pad = expansion._logo_glow_layer(
        logo,
        round(expansion.LOGO_GLOW_RADIUS * height),
        glow_color,
        expansion.LOGO_GLOW_INTENSITY,
    )
    expansion._screen_composite(canvas, halo, (logo_x - pad, HEADER_PADDING - pad))
    trail_offset = round(expansion.LOGO_TRAIL * logo.height)
    if trail_offset > 0:
        trail_tint = tuple(int(c * expansion.LOGO_TRAIL_DARKEN) for c in glow_color)
        trail = Image.new("RGBA", logo.size, trail_tint + (255,))
        trail.putalpha(logo.getchannel("A"))
        canvas.alpha_composite(
            trail, (logo_x + trail_offset, HEADER_PADDING + trail_offset)
        )
    canvas.alpha_composite(logo, (logo_x, HEADER_PADDING))
    x0 = MARGIN
    grid_x = x0 + label_w + LABEL_GAP
    grid_y = header + label_h + COLUMN_LABEL_GAP

    # --- the column labels: each rarity centered over its column ---------
    for j, label in enumerate(col_labels):
        x = grid_x + j * (cell_w + CELL_GAP) + cell_w // 2
        draw.text(
            (x, header + label_h // 2),
            label,
            font=col_font,
            fill=LABEL_COLOR,
            anchor="mm",
        )

    # --- the legend: the ▶ badge and its meaning, top right --------------
    legend_font = ImageFont.truetype(str(FONT), LEGEND_FONT_SIZE)
    _set_weight(legend_font, LABEL_WEIGHT)
    legend_w = round(legend_font.getlength(LEGEND_TEXT))
    legend_x = width - MARGIN - legend_w
    draw.text(
        (legend_x, MARGIN + badge.height // 2),
        LEGEND_TEXT,
        font=legend_font,
        fill=LABEL_COLOR,
        anchor="lm",
    )
    canvas.alpha_composite(badge, (legend_x - LEGEND_GAP - badge.width, MARGIN))

    # --- the rows: rendered in worker threads, assembled on the main ----
    workers = min(len(rows), os.cpu_count() or 1, MAX_STAGE_THREADS)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rendered = pool.map(
            _row_cards,
            rows,
            itertools.repeat(paths),
            itertools.repeat(columns),
            itertools.repeat(cells),
            itertools.repeat((cell_w, cell_h)),
            itertools.repeat(missing),
        )
        for i, (prefix, cards) in enumerate(rendered):
            y = grid_y + i * (cell_h + CELL_GAP)
            draw.text(
                (x0, y + cell_h // 2),
                labels[i],
                font=font,
                fill=LABEL_COLOR,
                anchor="lm",
            )
            for j, column in enumerate(columns):
                x = grid_x + j * (cell_w + CELL_GAP)
                key = (prefix, column)
                if key in missing:
                    draw.rectangle(
                        (x, y, x + cell_w - 1, y + cell_h - 1), fill=(0, 0, 0, 255)
                    )
                    draw.text(
                        (x + cell_w // 2, y + cell_h // 2),
                        MISSING_TEXT,
                        font=missing_font,
                        fill=(255, 255, 255, 255),
                        anchor="mm",
                    )
                    continue
                card = cards.get(column)
                if card is None:
                    continue
                if key in animated:
                    card.alpha_composite(
                        badge,
                        (
                            (card.width - badge.width) // 2,
                            (card.height - badge.height) // 2,
                        ),
                    )
                canvas.alpha_composite(card, (x, y))

    # --- the copyright line: the cards' notice, bottom left, white -----
    font_size = round(
        COPYRIGHT_NOMINAL_SIZE * width / CARD_REFERENCE_WIDTH * COPYRIGHT_FRACTION
    )
    ss = COPYRIGHT_SUPERSAMPLE
    big = ImageFont.truetype(str(FONT), font_size * ss)
    _set_weight(big, COPYRIGHT_WEIGHT)
    left, top, bottom = _text_ink_offsets(COPYRIGHT_TEXT, big)
    region = Image.new(
        "L", (round(big.getlength(COPYRIGHT_TEXT)) + 1, bottom - top + 1), 0
    )
    ImageDraw.Draw(region).text((-left, -top), COPYRIGHT_TEXT, font=big, fill=255)
    small = region.resize(
        (round(region.width / ss), round(region.height / ss)),
        Image.Resampling.LANCZOS,
    )
    stamp = Image.new("RGBA", small.size, (255, 255, 255, 255))
    stamp.putalpha(small)
    canvas.alpha_composite(
        stamp,
        (
            MARGIN,
            height - MARGIN // 2 - round((bottom - top) / (2 * ss)),
        ),
    )

    _save_atomic(canvas, out_path, source_hash)
    return canvas.size


def _summary_logo_box(
    W: int, H: int, logo_aspect: float, f: float
) -> tuple[int, int, int, int]:
    """The logo's box (x0, y0, x1, y1): *f* of the sheet's height tall, its
    width proportional, centered — the box ``expansion._composite_logo``
    scales the mark to for ``mark_height=f`` and centers, so the void lines
    up with the mark that gets drawn."""
    logo_h = round(f * H)
    logo_w = round(logo_h * logo_aspect)
    x0 = W // 2 - logo_w // 2
    y0 = H // 2 - logo_h // 2
    return x0, y0, x0 + logo_w, y0 + logo_h


def _summary_keep_out(H: int) -> int:
    """The keep-out margin (px) around the logo's box: how far the mark's
    screen-blended glow and its drop shadow reach past the box, so the void
    leaves the mark and its bloom and shadow card-free. The shadow is offset
    down-right, so its far (down-right) reach is the offset plus its blur's
    three sigma; the glow is symmetric. The larger of the two bounds both."""
    glow = 3 * round(expansion.LOGO_GLOW_RADIUS * H)
    shadow = round(SUMMARY_LOGO_SHADOW_OFFSET * H) + 3 * round(
        SUMMARY_LOGO_SHADOW_RADIUS * H
    )
    return max(glow, shadow)


def _summary_void(
    rows: int, cols: int, logo_box: tuple[int, int, int, int], keep_out: int
) -> tuple[int, int, int, int] | None:
    """The void's (row0, row1, col0, col1) inclusive range: the cells that
    intersect the logo's box grown by *keep_out* px on every side. The grown
    box is a rectangle and the cells tile the canvas, so the intersecting
    cells form a rectangle too. None when the region touches no cell (a logo
    smaller than a cell — not the case at the sheet's scale)."""
    W, H = SHEET_TARGET
    x0, y0, x1, y1 = logo_box
    x0 -= keep_out
    x1 += keep_out
    y0 -= keep_out
    y1 += keep_out
    cell_w = W / cols
    cell_h = H / rows
    c0 = max(0, int(x0 // cell_w))
    c1 = min(cols - 1, int((x1 - 1e-9) // cell_w))
    r0 = max(0, int(y0 // cell_h))
    r1 = min(rows - 1, int((y1 - 1e-9) // cell_h))
    if r0 > r1 or c0 > c1:
        return None
    return r0, r1, c0, c1


def _summary_available(
    rows: int, cols: int, void: tuple[int, int, int, int] | None
) -> int:
    """The tiling's card-holding cells: every cell but the void's."""
    if void is None:
        return rows * cols
    r0, r1, c0, c1 = void
    return rows * cols - (r1 - r0 + 1) * (c1 - c0 + 1)


def _summary_dimensions(
    n: int, logo_box: tuple[int, int, int, int], keep_out: int
) -> tuple[int, int]:
    """The summary grid's tiling (rows, columns) for *n* cards flowing
    around the logo: the smallest rows*cols (largest cells) whose
    card-holding cells — the tiling minus the void the logo's keep-out carves
    out of its center — hold all *n*, with each cell's aspect matching the
    cards' (so the cover fit crops only a sliver off each card)."""
    W, H = SHEET_TARGET
    card_aspect = CARD_VIEWPORT[0] / CARD_VIEWPORT[1]
    best: tuple[int, int] | None = None
    for cols in range(15, 70):
        base = cols * H * card_aspect / W
        for rows in (
            max(1, round(base) - 1),
            max(1, round(base)),
            max(1, round(base) + 1),
        ):
            if abs((W / cols) / (H / rows) - card_aspect) / card_aspect > 0.06:
                continue
            void = _summary_void(rows, cols, logo_box, keep_out)
            if _summary_available(rows, cols, void) < n:
                continue
            if best is None or rows * cols < best[0] * best[1]:
                best = (rows, cols)
    if best is None:
        raise GenerationError(f"no summary tiling fits {n} cards around the logo")
    return best


def _summary_positions(
    rows: int, cols: int, n: int, void: tuple[int, int, int, int] | None
) -> list[tuple[int, int]]:
    """The (row, col) of each of the *n* cards, in reading order: row by row,
    left to right, skipping the void's cells, so the cards flow around the
    logo. The leftover empty cells (the card-holding cells past the last
    card) are split between the first and the last row, both centered — the
    two rows sit outside the void, so they stay full-width and center the way
    the full grid did. Returns exactly *n* positions."""
    if rows < 2:
        cols0 = _row_cols(0, cols, void)
        k = min(n, len(cols0))
        start = (len(cols0) - k) // 2
        return [(0, cols0[i]) for i in range(start, start + k)]

    def card_cols(r: int) -> list[int]:
        return _row_cols(r, cols, void)

    avail = sum(len(card_cols(r)) for r in range(rows))
    leftover = avail - n
    first_empty = leftover // 2
    last_empty = leftover - first_empty
    positions: list[tuple[int, int]] = []
    for r in range(rows):
        cc = card_cols(r)
        if r == 0:
            k = len(cc) - first_empty
            start = (len(cc) - k) // 2
            positions.extend((r, cc[i]) for i in range(start, start + k))
        elif r == rows - 1:
            k = len(cc) - last_empty
            start = (len(cc) - k) // 2
            positions.extend((r, cc[i]) for i in range(start, start + k))
        else:
            positions.extend((r, c) for c in cc)
    return positions[:n]


def _row_cols(r: int, cols: int, void: tuple[int, int, int, int] | None) -> list[int]:
    """The card-holding columns of row *r*: every column but the void's, when
    the row crosses the void."""
    if void is not None:
        r0, r1, c0, c1 = void
        if r0 <= r <= r1:
            return [c for c in range(cols) if c < c0 or c > c1]
    return list(range(cols))


def _cell_box(row: int, col: int, rows: int, cols: int) -> tuple[int, int, int, int]:
    """The box (left, top, right, bottom) of the cell (row, col) of the
    rows x cols tiling of :data:`SHEET_TARGET`: the cells split the canvas by
    exact integer division (they tile it without gaps or overlaps)."""
    W, H = SHEET_TARGET
    top, bottom = row * H // rows, (row + 1) * H // rows
    left, right = col * W // cols, (col + 1) * W // cols
    return left, top, right, bottom


def _cover_fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """*image* scaled to cover *size* and center-cropped to it (no
    letterboxing: the cell is filled edge-to-edge)."""
    w, h = size
    scale = max(w / image.width, h / image.height)
    if scale != 1.0:
        image = image.resize(
            (round(image.width * scale), round(image.height * scale)),
            Image.Resampling.LANCZOS,
        )
    left = (image.width - w) // 2
    top = (image.height - h) // 2
    return image.crop((left, top, left + w, top + h))


def _rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    """A rounded-rectangle alpha mask for *size* (255 inside, 0 at the
    corners) with corner *radius*: the hard-edged
    ``ImageDraw.rounded_rectangle`` is aliased at 1x, so it is drawn
    supersampled and downscaled (the LANCZOS downscale anti-aliases the
    corners, the way the pages' ▶ badge is drawn)."""
    w, h = size
    ss = 4
    big = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, w * ss - 1, h * ss - 1), radius=radius * ss, fill=255
    )
    return big.resize((w, h), Image.Resampling.LANCZOS)


def _summary_frame(
    pos: tuple[int, int],
    key: tuple[str, str],
    paths: dict[tuple[str, str], Path],
    missing: set[tuple[str, str]],
    rows: int,
    cols: int,
) -> tuple[Image.Image | None, int, int]:
    """One cell of the summary grid: the first frame of *key* (at the
    tiling's cell *pos*, see :func:`_summary_positions`) cover-cropped to
    its box and inset by half of :data:`SUMMARY_CELL_GAP` on every side, so
    the dimmed background shows as the spacing between the cards, and rounded
    at the corners by :data:`SUMMARY_CORNER_RADIUS_FRACTION` — with its
    top-left corner, or (None, 0, 0) for a card in *missing*. Runs in a worker
    thread — Pillow releases the GIL in the decode, the LANCZOS resize and the
    crop — and only ever produces its own image, never touching the shared
    canvas (Pillow images are not thread-safe)."""
    if key in missing:
        return None, 0, 0
    left, top, right, bottom = _cell_box(pos[0], pos[1], rows, cols)
    # Inset the card within its cell: the inset is clamped to a quarter
    # of the cell so tiny cells still leave a positive card box.
    g = min(SUMMARY_CELL_GAP // 2, (right - left) // 4, (bottom - top) // 4)
    left += g
    top += g
    right -= g
    bottom -= g
    w, h = right - left, bottom - top
    radius = round(SUMMARY_CORNER_RADIUS_FRACTION * min(w, h))
    with Image.open(paths[key]) as card:
        frame = _cover_fit(card.convert("RGBA"), (w, h))
    # The cards' alpha is opaque: the rounded mask replaces it (the
    # multiply keeps it if a card ever carries transparency).
    frame.putalpha(
        ImageChops.multiply(frame.getchannel("A"), _rounded_mask((w, h), radius))
    )
    return frame, left, top


def _summary_grid(
    ordered: list[tuple[str, str]],
    paths: dict[tuple[str, str], Path],
    missing: set[tuple[str, str]],
    background: Image.Image,
    logo: Image.Image,
    out_path: Path,
    source_hash: str,
    rows: int,
    cols: int,
    logo_box: tuple[int, int, int, int],
    keep_out: int,
) -> tuple[int, int]:
    """Draw the summary grid: the expansion's first frames tiled
    across :data:`SHEET_TARGET` — *ordered* (the roster's order, see
    :func:`_ordered_cells`), each cover-cropped to its cell (the cells'
    aspect matching the cards', so the crop is a sliver) and inset
    within it with its corners rounded, the cards flowing around the
    logo's keep-out (the void at the sheet's center) and the leftover
    empty cells split between the first and the last row (both
    centered) — over the dimmed *background* (fitted to the canvas and
    dimmed toward black, showing between the cards, at the corners,
    in the void and in the cells of *missing*), with *logo* over the
    void, at the sheet's center (at :data:`SUMMARY_LOGO_FRACTION` of
    the sheet's height, the pack's and box's fronts' treatment — see
    ``expansion._composite_logo`` — plus a soft drop shadow behind the
    mark) — and write it to *out_path*
    (atomically, the *source_hash* embedded). The cells' frames are
    decoded and cropped in parallel threads; the finished canvas is
    assembled on the main thread. Returns the canvas's size."""
    void = _summary_void(rows, cols, logo_box, keep_out)
    positions = _summary_positions(rows, cols, len(ordered), void)
    canvas = _dimmed_background(background, SHEET_TARGET)
    # The logo's glow color, derived from the dimmed canvas (before the
    # cards), the way the pack's and box's fronts derive it.
    glow_color = expansion._background_glow_color(expansion._image_average(canvas))
    if ordered:
        workers = min(len(ordered), os.cpu_count() or 1, MAX_STAGE_THREADS)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            rendered = pool.map(
                _summary_frame,
                positions,
                ordered,
                itertools.repeat(paths),
                itertools.repeat(missing),
                itertools.repeat(rows),
                itertools.repeat(cols),
            )
            for frame, left, top in rendered:
                if frame is not None:
                    canvas.alpha_composite(frame, (left, top))
    # The logo's drop shadow, behind the mark: a darkened, blurred
    # copy offset down-right, drawn before the mark so the glow and the
    # mark composite over it. The shadow uses the mark's box (the one
    # expansion._composite_logo scales to for mark_height), so the mark
    # is pre-scaled to it and _composite_logo's resize is a no-op.
    logo_h = round(SUMMARY_LOGO_FRACTION * SHEET_TARGET[1])
    mark = logo.resize(
        (round(logo_h * logo.width / logo.height), logo_h),
        Image.Resampling.LANCZOS,
    )
    shadow, pad = expansion._logo_glow_layer(
        mark,
        round(SUMMARY_LOGO_SHADOW_RADIUS * SHEET_TARGET[1]),
        (0, 0, 0),
        SUMMARY_LOGO_SHADOW_ALPHA,
    )
    offset = round(SUMMARY_LOGO_SHADOW_OFFSET * SHEET_TARGET[1])
    x = SHEET_TARGET[0] // 2 - mark.width // 2
    y = SHEET_TARGET[1] // 2 - mark.height // 2
    canvas.alpha_composite(shadow, (x + offset - pad, y + offset - pad))
    expansion._composite_logo(
        canvas,
        mark,
        SHEET_TARGET,
        "center",
        glow_color,
        mark_height=SUMMARY_LOGO_FRACTION,
    )
    _save_atomic(canvas, out_path, source_hash)
    return canvas.size
