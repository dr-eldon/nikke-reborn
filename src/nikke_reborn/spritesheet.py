"""Compose an expansion's sprite sheet: an overview of all its rendered
cards, fitted to the grid — every row is 160 px tall, and the sheet's
width (the label column + the grid + the margins) and height (the header +
the grid + the margin) grow with the content — over the expansion's
background (its ``Expansion.json`` ``background``, resized to cover the
sheet without deformation, bottom edges aligned, and dimmed toward black
so the grid reads against it).

The sheet composites the finished first frames
(``output/<set>/<card>_<variant>.png``) into a grid:

* the expansion's logo at the top, centered — from the set's
  ``Expansion.json`` ``logo.path`` (resolved against the pack directory)
  when the file exists, else ``images/logos/<set>.png``;
* one row per card prefix (``<number>_<card>`` — the card's directory, the
  rarity stripped), rendered in a label column on the left as
  ``#<number> <character>[: <skin>]`` — the number zero-padded so the
  labels' numbers align, its words' CamelCase split by whitespace (``#01
  Rapi`` … ``#21 Diesel: Black Sunday``);
* one column per rarity/variant: every rarity the set carries, in the order
  of ``metadata.RARITIES`` (the game's own rarity order — profiles first,
  then the base rarities from the commonest to the rarest), the ``Goddess``
  and ``Classified`` presentations carrying no profile, each column labeled
  above the grid with its rarity (whitespace between its capital letters —
  ``ClassicProfile`` reads as ``Classic Profile``). A cell the character
  does not have (a rarity it does not carry) stays empty.
* the animated cards (an ``.mp4`` next to their first frame) are marked
  with a white ▶ in a black circle, centered in their cell; a legend
  (the badge and ``= Animated``) sits in the sheet's top-right corner.
* the cards' copyright line (a bit smaller), in white, at the bottom
  left.

The cells are the first frames only — the PNGs the pipeline writes for
every card (alongside the MP4 for the animated ones); no video is read or
decoded. Every cell must already be on disk, so the sheet is composed after
``generate`` (missing cards are reported, named).

Like the finished cards, the sheet embeds the SHA-256 of its inputs (the
frames it composites and the expansion's logo) under the source-hash key,
and a sheet whose stored hash matches the current inputs is skipped
instead of re-composed. The rows' first frames are decoded and resized in
parallel threads (one row per worker, up to
:data:`nikke_reborn.MAX_STAGE_THREADS`), the canvas assembled on the main
thread. ``--draft`` reads the first frames from ``draft/`` and writes
``draft/<set>.png``; ``--force`` skips the up-to-date check.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import nikke_reborn as nr
from nikke_reborn import expansion, metadata
from PIL import Image, ImageDraw, ImageFont

# --- the finished sheet's geometry ----------------------------------------
# The sheet is fitted to its content on both axes: the width is the label
# column + the grid + 2 * MARGIN, the height the header + the grid +
# MARGIN (every row is ROW_HEIGHT tall).
#: The sheet's margin around the header and the grid (on every side).
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
#: The label column's cap, as a fraction of the grid's card width (the
#: cells and their gutters, not the label column — the sheet's width fits
#: the content, so capping against it would be circular): the label font
#: shrinks until the longest prefix fits it.
LABEL_MAX_FRACTION = 0.30
#: The label font's weight (Oswald's variable axis).
LABEL_WEIGHT = 500
#: The label font sizes tried, largest first: the first whose longest
#: prefix fits the label column's cap is used.
LABEL_FONT_SIZES = (48, 44, 40, 36, 32, 28, 24, 20)
#: The height of every grid row (px): the rows keep this height and the
#: sheet grows vertically to fit them (the cell's width is derived from it,
#: by the card's aspect).
ROW_HEIGHT = 160
#: The gutter between the label column and the grid.
LABEL_GAP = 32
#: The gutter between the grid's cells.
CELL_GAP = 8
#: The fraction of the background's brightness kept: the background is
#: dimmed toward black by the rest, so the grid and the labels read
#: against it.
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


def spritesheet() -> None:
    """Compose the selected expansion's sprite sheet (the ``spritesheet``
    command)."""
    args = _parse_args()
    out_dir = nr.DRAFT_DIR if args.draft else nr.OUTPUT_DIR
    try:
        out_path, rows, columns, skipped = _build(args.expansion, out_dir, args.force)
    except nr.GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    if skipped:
        print(
            f"{out_path.relative_to(nr.REPO_ROOT)}: up to date; "
            f"skipping (use --force to rebuild)"
        )
        return
    with Image.open(out_path) as sheet:
        size = sheet.size
    print(
        f"Done. Wrote {out_path.relative_to(nr.REPO_ROOT)} "
        f"({size[0]}x{size[1]}, {rows} row(s) x {columns} column(s))"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compose an expansion's sprite sheet (a grid of its rendered "
            "first frames, fitted to its content — 160 px rows: the "
            "expansion's logo on top, one row per card prefix, one column "
            "per rarity/variant)"
        )
    )
    parser.add_argument(
        "expansion",
        help="expansion name (a directory under cards/, e.g. ELYSION)",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help="read the first frames from draft/ and write draft/<set>.png",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="rebuild the sheet even when the one on disk is up to date",
    )
    return parser.parse_args()


def _build(name: str, out_dir: Path, force: bool) -> tuple[Path, int, int, bool]:
    """Compose ``<out_dir>/<name>.png`` for the expansion *name*.

    Returns the sheet's path, its grid's row and column counts and whether
    the sheet was skipped (up to date)."""
    pack_dir = nr.CARDS_DIR / name
    if not pack_dir.is_dir():
        known = sorted(p.name for p in nr.CARDS_DIR.iterdir() if p.is_dir())
        raise nr.GenerationError(
            f"unknown expansion {name!r} (expected a directory under "
            f"cards/; the known sets: {', '.join(known)})"
        )
    rows, columns, cells = _card_grid(pack_dir)
    if not rows:
        raise nr.GenerationError(
            f"no card definitions under {pack_dir.relative_to(nr.REPO_ROOT)}/"
        )
    card_dir = out_dir / pack_dir.name
    paths = {
        (prefix, column): card_dir / f"{prefix}_{column}.png"
        for prefix, column in sorted(cells)
    }
    missing = [path for path in paths.values() if not path.is_file()]
    if missing:
        shown = ", ".join(
            str(path.relative_to(nr.REPO_ROOT)) for path in missing[:10]
        )
        more = f" (+{len(missing) - 10} more)" if len(missing) > 10 else ""
        raise nr.GenerationError(
            f"{len(missing)} rendered card(s) missing for {pack_dir.name} "
            f"(run 'generate' first): {shown}{more}"
        )
    out_path = out_dir / f"{pack_dir.name}.png"
    background, background_path = _expansion_background(pack_dir)
    logo, logo_path = _expansion_logo(pack_dir)
    source_hash = _source_hash(pack_dir, logo_path, background_path, paths)
    if not force and _stored_hash(out_path) == source_hash:
        return out_path, len(rows), len(columns), True
    _compose(
        rows, columns, cells, paths, logo, background, out_path, source_hash
    )
    return out_path, len(rows), len(columns), False


def _card_grid(pack_dir: Path) -> tuple[list[str], list[str], set[tuple[str, str]]]:
    """The sheet's grid: its rows (the card prefixes, sorted), its columns
    (every rarity/variant the set carries, in the order of
    :data:`nikke_reborn.metadata.RARITIES` — the game's own rarity order,
    the ``Goddess`` and ``Classified`` presentations carrying no profile)
    and its cells (the prefix/column pairs the set actually has)."""
    cards: list[tuple[str, list[str]]] = []
    stems: set[str] = set()
    for card_dir in sorted(pack_dir.iterdir()):
        if not card_dir.is_dir():
            continue
        variants = sorted(
            variant.stem
            for variant in card_dir.iterdir()
            if variant.is_file() and variant.suffix == ".json"
        )
        cards.append((card_dir.name, variants))
        stems.update(variants)
    rows = [prefix for prefix, _ in cards]
    present: set[str] = set()
    for stem in stems:
        if stem not in nr.PROFILE_RARITIES:
            present.add(stem)
        if stem not in nr.NO_PROFILE_STEMS:
            present.add(f"{stem}Profile")
    columns = [rarity for rarity in metadata.RARITIES if rarity in present]
    cells: set[tuple[str, str]] = set()
    for prefix, variants in cards:
        for stem in variants:
            if stem not in nr.PROFILE_RARITIES:
                cells.add((prefix, stem))
            if stem not in nr.NO_PROFILE_STEMS:
                cells.add((prefix, f"{stem}Profile"))
    return rows, columns, cells


def _expansion_background(pack_dir: Path) -> tuple[Image.Image, Path]:
    """The expansion's background (RGBA) and its file: its
    ``Expansion.json`` ``background``, resolved against the pack
    directory."""
    data = expansion.load_expansion(pack_dir)
    rel = data.get("background")
    if not rel:
        raise nr.GenerationError(f"{pack_dir.name}: missing 'background'")
    path = (pack_dir / rel).resolve()
    if not path.is_file():
        raise nr.GenerationError(f"{pack_dir.name}: background not found: {rel}")
    return Image.open(path).convert("RGBA"), path


def _expansion_logo(pack_dir: Path) -> tuple[Image.Image, Path]:
    """The expansion's logo (RGBA) and its file: its ``Expansion.json``
    ``logo.path`` (resolved against the pack directory) when the file
    exists, else ``images/logos/<set>.png``."""
    expansion_json = pack_dir / expansion.EXPANSION_NAME
    if expansion_json.is_file():
        try:
            field = json.loads(expansion_json.read_text(encoding="utf-8")).get("logo")
        except ValueError:
            field = None
        if isinstance(field, dict) and field.get("path"):
            path = (pack_dir / field["path"]).resolve()
            if path.is_file():
                return Image.open(path).convert("RGBA"), path
    fallback = nr.IMAGES_DIR / "logos" / f"{pack_dir.name}.png"
    if fallback.is_file():
        return Image.open(fallback).convert("RGBA"), fallback
    raise nr.GenerationError(
        f"no logo for expansion {pack_dir.name!r}: no usable 'logo' field in "
        f"{pack_dir.name}/{expansion.EXPANSION_NAME} and no "
        f"{fallback.relative_to(nr.REPO_ROOT)}"
    )


def _source_hash(
    pack_dir: Path,
    logo_path: Path,
    background_path: Path,
    paths: dict[tuple[str, str], Path],
) -> str:
    """SHA-256 of the sheet's inputs: the expansion's name, its logo, its
    background, every first frame it composites and each cell's animated
    state (an ``.mp4`` next to the first frame; it drives the 📹 markers)
    — embedded under :data:`nikke_reborn.SOURCE_HASH_KEY` so an unchanged
    sheet is skipped instead of re-composed."""
    digest = hashlib.sha256()
    digest.update(pack_dir.name.encode())
    digest.update(logo_path.read_bytes())
    digest.update(background_path.read_bytes())
    for key in sorted(paths):
        path = paths[key]
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
        digest.update(b"1" if path.with_suffix(".mp4").is_file() else b"0")
    return digest.hexdigest()


def _stored_hash(out_path: Path) -> str | None:
    """The source-hash key embedded in an existing sheet, or None when the
    file is absent or carries no readable tag."""
    if not out_path.is_file():
        return None
    try:
        with Image.open(out_path) as image:
            return image.info.get(nr.SOURCE_HASH_KEY)
    except Exception:
        return None


def _split_camel(text: str) -> str:
    """Whitespace between each capital letter of *text*'s CamelCase
    (``BlackSunday`` reads as ``Black Sunday``; single words unchanged)."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)


def _column_label(column: str) -> str:
    """The column's header label: the rarity's name with whitespace
    between each capital letter (``ClassicProfile`` reads as
    ``Classic Profile``)."""
    return _split_camel(column)


def _row_label(prefix: str, width: int) -> str:
    """The row's label: the prefix with its number as ``#<number>``
    (zero-padded to *width* digits, so the labels' numbers align) and its
    words' CamelCase split by whitespace — the character, and its skin
    after a colon when it has one (``0021_Diesel_BlackSunday`` reads as
    ``#21 Diesel: Black Sunday``; with *width* 2, ``#01 Rapi``)."""
    number, character, *skin = prefix.split("_")
    label = f"#{int(number):0{width}d} {_split_camel(character)}"
    if skin:
        label += ": " + " ".join(_split_camel(word) for word in skin)
    return label


def _row_labels(rows: list[str]) -> list[str]:
    """The row labels for *rows* (:func:`_row_label`, the numbers padded
    to the longest number's digit count, so the column aligns)."""
    width = max(len(str(int(prefix.split("_")[0]))) for prefix in rows)
    return [_row_label(prefix, width) for prefix in rows]


def _column_label_font(labels: list[str], max_w: int) -> ImageFont.FreeTypeFont:
    """The column-label font: the largest of :data:`COLUMN_LABEL_SIZES`
    whose longest label fits *max_w* px (the cell's width)."""
    for size in COLUMN_LABEL_SIZES:
        font = ImageFont.truetype(str(nr.FONT), size)
        nr._set_weight(font, COLUMN_LABEL_WEIGHT)
        if max(font.getlength(label) for label in labels) <= max_w:
            return font
    raise nr.GenerationError(
        f"column labels do not fit the cells at the smallest label font "
        f"({COLUMN_LABEL_SIZES[-1]} px); the longest is {max(labels, key=len)!r}"
    )


def _label_font(labels: list[str], card_w: int) -> tuple[ImageFont.FreeTypeFont, int]:
    """The row-label font and the label column's width: the largest of
    :data:`LABEL_FONT_SIZES` whose longest label fits the column's cap
    (LABEL_MAX_FRACTION of the grid's card width *card_w*, including the
    padding)."""
    cap = round(LABEL_MAX_FRACTION * card_w) - 2 * LABEL_PAD
    for size in LABEL_FONT_SIZES:
        font = ImageFont.truetype(str(nr.FONT), size)
        nr._set_weight(font, LABEL_WEIGHT)
        longest = max(round(font.getlength(label)) for label in labels)
        if longest <= cap:
            return font, longest + 2 * LABEL_PAD
    raise nr.GenerationError(
        f"row labels do not fit the sheet at the smallest label font "
        f"({LABEL_FONT_SIZES[-1]} px); the longest is {max(labels, key=len)!r}"
    )


def _row_cards(
    prefix: str,
    paths: dict[tuple[str, str], Path],
    columns: list[str],
    cells: set[tuple[str, str]],
    size: tuple[int, int],
) -> tuple[str, dict[str, Image.Image]]:
    """The row's first frames, each converted and resized to the cell's
    *size*: one image per column the row has. Runs in a worker thread —
    Pillow releases the GIL in the decode and the LANCZOS resize — and
    only ever produces its own images, never touching the shared canvas
    (Pillow images are not thread-safe)."""
    cell_w, cell_h = size
    cards = {}
    for column in columns:
        key = (prefix, column)
        if key not in cells:
            continue
        with Image.open(paths[key]) as card:
            cards[column] = card.convert("RGBA").resize(
                (cell_w, cell_h), Image.Resampling.LANCZOS
            )
    return prefix, cards


def _compose(
    rows: list[str],
    columns: list[str],
    cells: set[tuple[str, str]],
    paths: dict[tuple[str, str], Path],
    logo: Image.Image,
    background: Image.Image,
    out_path: Path,
    source_hash: str,
) -> None:
    """Draw the sheet — the logo header, the column labels, the label
    column and the grid of first frames (the animated cards' cells
    marked with a white ▶ in a black circle, centered in the cell, and
    a legend — the badge and ``= Animated`` — in the top-right corner) —
    over the expansion's *background* (resized to cover the canvas
    without deformation, bottom edges aligned, the excess cropped off
    the top, and dimmed toward black so the grid reads against it) on
    a canvas fitted to its content (label column + grid + the margins
    wide; header + labels + grid + the margin tall), the cards'
    copyright line (a bit smaller) in white at the bottom left, and
    write it to *out_path* (atomically, the *source_hash* embedded). The rows'
    first frames are decoded and resized in parallel threads (up to
    :data:`nikke_reborn.MAX_STAGE_THREADS` of them, one row per worker);
    the finished canvas is assembled on the main thread."""
    row_count = len(rows)
    col_count = len(columns)
    gutter_total = (col_count - 1) * CELL_GAP

    # --- the grid's geometry --------------------------------------------
    # Every card shares the pipeline's viewport: the row's fixed height
    # sizes its cells (the sheet grows to fit the grid, never the other
    # way around).
    with Image.open(min(paths.values())) as first:
        aspect = first.width / first.height
    cell_w = round(ROW_HEIGHT * aspect)
    cell_h = ROW_HEIGHT
    grid_h = row_count * cell_h + (row_count - 1) * CELL_GAP
    card_w = col_count * cell_w + gutter_total
    labels = _row_labels(rows)
    font, label_w = _label_font(labels, card_w)
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

    # The ▶ markers: the cells whose card is animated (an .mp4 next to
    # its first frame) get one centered in the cell. The symbol is a
    # filled white equilateral triangle pointing right, drawn at 4x the
    # marker's size (so the LANCZOS downscale stays crisp).
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
    # The badge: a translucent black circle enclosing the glyph
    # (ANIMATED_MARKER_PAD of clearance on each side), the glyph centered
    # in it. The circle is drawn at 4x and downscaled — Pillow's ellipse
    # is not anti-aliased.
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
    # The expansion's background as the canvas's base: scaled to cover the
    # sheet (aspect preserved) with its bottom edge on the sheet's (the
    # excess cropped off the top, centered horizontally), then dimmed
    # toward black (BACKGROUND_DIM of its brightness kept) so the grid
    # and the labels read against it.
    canvas = expansion._fit_cover(background, (width, height))
    canvas = Image.blend(
        canvas, Image.new("RGBA", canvas.size, (0, 0, 0, 255)), 1 - BACKGROUND_DIM
    )
    draw = ImageDraw.Draw(canvas)
    canvas.alpha_composite(logo, ((width - logo.width) // 2, HEADER_PADDING))
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
    legend_font = ImageFont.truetype(str(nr.FONT), LEGEND_FONT_SIZE)
    nr._set_weight(legend_font, LABEL_WEIGHT)
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
    # thread: each worker decodes and resizes its row's first frames (the
    # GIL-releasing part), while the shared canvas is only ever stamped by
    # the main thread (Pillow images are not thread-safe).
    workers = min(len(rows), os.cpu_count() or 1, nr.MAX_STAGE_THREADS)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rendered = pool.map(
            _row_cards,
            rows,
            itertools.repeat(paths),
            itertools.repeat(columns),
            itertools.repeat(cells),
            itertools.repeat((cell_w, cell_h)),
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
                card = cards.get(column)
                if card is None:
                    continue
                if (prefix, column) in animated:
                    card.alpha_composite(
                        badge,
                        (
                            (card.width - badge.width) // 2,
                            (card.height - badge.height) // 2,
                        ),
                    )
                canvas.alpha_composite(card, (grid_x + j * (cell_w + CELL_GAP), y))

    # --- the copyright line: the cards' notice, bottom left, white -----
    # (the cards' rendering — supersampled, light-weight Oswald, ink
    # centered in the bottom margin — a bit smaller than the cards').
    font_size = round(
        nr.COPYRIGHT_NOMINAL_SIZE * width / nr.CARD_REFERENCE_WIDTH * COPYRIGHT_FRACTION
    )
    ss = nr.COPYRIGHT_SUPERSAMPLE
    big = ImageFont.truetype(str(nr.FONT), font_size * ss)
    nr._set_weight(big, nr.COPYRIGHT_WEIGHT)
    left, top, bottom = nr._text_ink_offsets(nr.COPYRIGHT_TEXT, big)
    region = Image.new(
        "L", (round(big.getlength(nr.COPYRIGHT_TEXT)) + 1, bottom - top + 1), 0
    )
    ImageDraw.Draw(region).text((-left, -top), nr.COPYRIGHT_TEXT, font=big, fill=255)
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

    nr._save_atomic(canvas, out_path, source_hash)
