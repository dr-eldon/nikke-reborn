"""Render and composite Nikke trading cards.

Walks :mod:`cards` for card definitions (``*.json``), renders each one with
the ``nikke-viewer`` executable, composites every rendered frame on top of
the card's ``background``, overlays the card name at the top left, the
matching logo from ``images/`` at the bottom right and the copyright line
at the bottom left, then writes the finished result under ``output/``:

* single-frame cards -> ``output/<set>/<card>/<variant>.png``
* animated cards     -> ``output/<set>/<card>/<variant>.mp4``

``--draft`` runs the same pipeline for quick iteration: ultrafast x264
preset, half-resolution MP4s (downscaled inside ffmpeg), and results
written to ``draft/`` instead of ``output/`` so draft runs never clobber
the final cards.

``nikke-viewer`` writes its result next to the input file, so each card is
rendered inside a throw-away working directory which is deleted as soon as
the card is done: the intermediate renders are high-resolution lossless
PNGs and must not accumulate on disk.

Cards are independent of each other, so they are processed by a pool of
worker processes (see ``--jobs``); within an animated card, the frames are
composited in parallel threads, and the cores are split between that stage
and the ffmpeg encode so the parallel work stays within the core count.

By default every ``*.json`` under ``cards/`` is generated; one or more card
definition paths may be passed on the command line to generate only those.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterator

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CARDS_DIR = REPO_ROOT / "cards"
IMAGES_DIR = REPO_ROOT / "images"
OUTPUT_DIR = REPO_ROOT / "output"
DRAFT_DIR = REPO_ROOT / "draft"

VIEWER = "nikke-viewer"
ENCODER = "ffmpeg"

DEFAULT_FRAMERATE = 60

#: ``nikke-viewer`` writes its frames from multiple threads and can
#: occasionally leave a truncated file behind while still exiting with
#: status 0; a card whose render cannot be processed is re-run up to this
#: many times before giving up.
RENDER_ATTEMPTS = 3

#: The logo sits this many times the card ``padding`` away from the corner.
LOGO_PADDING_FACTOR = 1.5

#: Reference card width (pixels): the nominal sizes below are expressed at
#: this width and scale proportionally for other viewport widths.
CARD_REFERENCE_WIDTH = 1640

#: Nominal logo width (pixels) at the reference card width: the logo is
#: scaled proportionally, preserving its aspect ratio (200 px wide on the
#: 1640 px cards we have).
LOGO_NOMINAL_WIDTH = 200

#: Nominal copyright text size (pixels) at the reference card width.
COPYRIGHT_NOMINAL_SIZE = 20

#: Copyright line rendered at the bottom left of the card.
COPYRIGHT_TEXT = "©SHIFT UP CORP."

#: Sans-serif face for the copyright line (vendored, SIL Open Font License).
FONT = IMAGES_DIR / "fonts" / "NotoSans-Regular.ttf"

#: Orbitron face for the card name (vendored variable font, SIL OFL).
FONT_NAME = IMAGES_DIR / "fonts" / "Orbitron.ttf"

#: Card name placement, in units of the card padding: the ink starts at
#: (padding * NAME_POSITION_FACTOR, padding * NAME_POSITION_FACTOR) with
#: font size padding * NAME_SIZE_FACTOR and Orbitron weight NAME_WEIGHT
#: (700 = bold).
NAME_POSITION_FACTOR = 2.0
NAME_SIZE_FACTOR = 1.5
NAME_WEIGHT = 700

#: H.264 quality settings for the MP4 output: visually lossless CRF,
#: yuv420p for compatibility and fast-start for streaming. The x264 preset
#: and the resolution scale are chosen per run: ``slow`` at full
#: resolution by default, ``ultrafast`` at half resolution for drafts
#: (``--draft``).
FFMPEG_QUALITY_ARGS = (
    "-crf", "16",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
)

DEFAULT_PRESET = "slow"
DRAFT_PRESET = "ultrafast"
DEFAULT_SCALE = 1.0
DRAFT_SCALE = 0.5

#: ffmpeg encodes and frame compositing get at most this many threads
#: each, even when a single card uses all the cores.
MAX_STAGE_THREADS = 16

LOGO_PATHS = {
    False: IMAGES_DIR / "logo-white.png",
    True: IMAGES_DIR / "logo-black.png",
}


class GenerationError(RuntimeError):
    """A card definition could not be rendered or composed."""


def generate() -> None:
    """Render and composite the selected (or all) card definitions."""
    args = _parse_args()
    draft = args.draft
    try:
        _generate(
            args.paths,
            args.jobs,
            DRAFT_PRESET if draft else DEFAULT_PRESET,
            DRAFT_SCALE if draft else DEFAULT_SCALE,
            DRAFT_DIR if draft else OUTPUT_DIR,
        )
    except GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


def _require_executable(name: str) -> None:
    if shutil.which(name) is None:
        raise GenerationError(f"required executable not found in PATH: {name!r}")


def _find_card_configs(paths: list[Path] | None = None) -> list[Path]:
    """Return the card definition files to generate.

    With no explicit *paths*, every ``*.json`` under :data:`CARDS_DIR`
    (sorted for deterministic output). Explicit paths are resolved against
    the repo root, must be files that live under :data:`CARDS_DIR`, are
    de-duplicated and returned in the given order.
    """
    if not paths:
        return sorted(CARDS_DIR.rglob("*.json"))
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


def _load_card(json_path: Path) -> dict:
    try:
        import json

        return json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GenerationError(f"cannot read card definition {json_path.name}: {exc}") from exc


def _background_path(card: dict, json_path: Path) -> Path:
    if "background" not in card:
        raise GenerationError(f"{json_path.name}: missing 'background'")
    background = (json_path.parent / card["background"]).resolve()
    if not background.is_file():
        raise GenerationError(f"{json_path.name}: background not found: {background}")
    return background


def _render_card(json_path: Path, workdir: Path) -> Path:
    """Render one card into *workdir* and return the produced artifact.

    The result is either a single ``<stem>.png`` (static card) or a
    ``<stem>/`` directory of numbered frames (animated card).
    """
    config = workdir / json_path.name
    shutil.copyfile(json_path, config)
    command = [VIEWER, config.name]
    try:
        result = subprocess.run(
            command,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GenerationError(f"could not run {VIEWER!r}: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise GenerationError(f"{VIEWER} failed for {json_path.name} (exit {result.returncode}){': ' + detail if detail else ''}")

    # Static cards produce <stem>.png next to the input; animated cards
    # produce a <stem>/ directory of numbered frames.
    png_artifact = workdir / f"{json_path.stem}.png"
    if png_artifact.is_file():
        return png_artifact
    render_dir = workdir / json_path.stem
    if render_dir.is_dir():
        return render_dir
    detail = (result.stderr or result.stdout).strip()
    detail = f" ({detail[-500:]})" if detail else ""
    raise GenerationError(f"{VIEWER} produced no output for {json_path.name}{detail}")


def _frame_paths(render_dir: Path) -> list[Path]:
    """Numbered frames of an animated render, in presentation order.

    ``nikke-viewer`` writes frames out of order (the zero-padded width of
    the names depends on the frame count), so the names must be sorted
    numerically.
    """
    frames = sorted((p for p in render_dir.iterdir() if p.is_file()),
                    key=lambda p: int(p.stem))
    if not frames:
        raise GenerationError(f"animated render has no frames: {render_dir.name}")
    return frames


def _open_frame(path: Path) -> Image.Image:
    """Open and fully decode a render frame.

    Frames are written by ``nikke-viewer`` from several threads and can
    occasionally be left truncated; a full decode catches that (and closes
    the file), so callers may use the returned image directly.
    """
    try:
        image = Image.open(path)
        image.load()
    except Exception as exc:
        raise GenerationError(f"unreadable render output {path.name}: {exc}") from exc
    return image


def _check_frame_size(
    frame: Image.Image, name: str, expected: tuple[int, int] | None
) -> None:
    if expected is not None and frame.size != expected:
        raise GenerationError(
            f"{name} is {frame.size[0]}x{frame.size[1]}, "
            f"expected {expected[0]}x{expected[1]}"
        )


def _fit_background(background: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Fit *background* to *size* (cover) and center-crop it."""
    width, height = size
    scale = max(width / background.width, height / background.height)
    if scale != 1.0:
        background = background.resize(
            (round(background.width * scale), round(background.height * scale)),
            Image.Resampling.LANCZOS,
        )
    left = (background.width - width) // 2
    top = (background.height - height) // 2
    return background.crop((left, top, left + width, top + height)).convert("RGBA")


def _scale_logo(logo: Image.Image, card_width: int) -> Image.Image:
    """Scale *logo* to the nominal width for a *card_width* px-wide card.

    The nominal width is :data:`LOGO_NOMINAL_WIDTH` px at the
    :data:`CARD_REFERENCE_WIDTH` reference width, scaled proportionally for
    other viewport widths; the aspect ratio is preserved.
    """
    target = round(LOGO_NOMINAL_WIDTH * card_width / CARD_REFERENCE_WIDTH)
    if target == logo.width:
        return logo
    height = round(logo.height * target / logo.width)
    return logo.resize((target, height), Image.Resampling.LANCZOS)


def _with_logo(base: Image.Image, logo: Image.Image, margin: int) -> Image.Image:
    """Return a copy of *base* with *logo* stamped at the bottom right."""
    canvas = base.copy()
    canvas.alpha_composite(
        logo, (base.width - logo.width - margin, base.height - logo.height - margin)
    )
    return canvas


def _text_ink_offsets(text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int, int]:
    """Ink offsets (left, top, bottom) of *text* from its draw origin.

    Measured on a probe render, because the rasterized ink can differ from
    the font metrics by a pixel.
    """
    origin = 8
    probe = Image.new(
        "L",
        (
            round(font.getlength(text)) + 2 * origin,
            font.getmetrics()[0] + font.getmetrics()[1] + 2 * origin,
        ),
        0,
    )
    ImageDraw.Draw(probe).text((origin, origin), text, font=font, fill=255)
    left, top, right, bottom = probe.getbbox()
    return left - origin, top - origin, bottom - origin


def _with_name(base: Image.Image, padding: int, name: str) -> Image.Image:
    """Return a copy of *base* with the card *name* at the top left.

    The ink starts at ``(padding * NAME_POSITION_FACTOR,
    padding * NAME_POSITION_FACTOR)``, the font size is
    ``padding * NAME_SIZE_FACTOR``; the text is white.
    """
    canvas = base.copy()
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(FONT_NAME), round(padding * NAME_SIZE_FACTOR))
    font.set_variation_by_axes([NAME_WEIGHT])
    left, top, bottom = _text_ink_offsets(name, font)
    position = round(padding * NAME_POSITION_FACTOR)
    draw.text(
        (position - left, position - top),
        name,
        font=font,
        fill=(255, 255, 255, 255),
    )
    return canvas


def _with_copyright(
    base: Image.Image, padding: int, color: tuple[int, int, int, int]
) -> Image.Image:
    """Return a copy of *base* with the copyright line at the bottom left.

    The ink of the text starts ``padding`` pixels from the left edge and
    is vertically centered inside the box of height ``padding`` at the
    bottom of the card; its size scales with the card width like the logo.
    """
    canvas = base.copy()
    draw = ImageDraw.Draw(canvas)
    font_size = round(COPYRIGHT_NOMINAL_SIZE * base.width / CARD_REFERENCE_WIDTH)
    font = ImageFont.truetype(str(FONT), font_size)
    left, top, bottom = _text_ink_offsets(COPYRIGHT_TEXT, font)
    x = padding - left
    y = base.height - padding // 2 - round((top + bottom) / 2)
    draw.text((x, y), COPYRIGHT_TEXT, font=font, fill=color)
    return canvas


def _composite_frame(frame: Image.Image, base: Image.Image) -> Image.Image:
    """Composite *frame* over the pre-stamped *base*; the result is RGBA."""
    canvas = base.copy()
    if frame.mode != "RGBA":
        frame = frame.convert("RGBA")
    canvas.alpha_composite(frame)
    return canvas


def _encode_mp4(
    frames: Iterator[Image.Image],
    size: tuple[int, int],
    framerate: int,
    out_path: Path,
    threads: int,
    preset: str,
    scale: float,
) -> None:
    """Encode an RGBA frame stream into an MP4 using ffmpeg."""
    width, height = size
    command = [
        ENCODER,
        "-y",
        "-loglevel", "error",
        "-f", "rawvideo",
        "-pix_fmt", "rgba",
        "-s", f"{width}x{height}",
        "-framerate", str(framerate),
        "-i", "-",
    ]
    if scale != 1.0:
        # Downscale inside ffmpeg (fast, SIMD-optimized swscale) rather
        # than resizing every frame in Python first.
        target = (round(width * scale) & ~1, round(height * scale) & ~1)  # yuv420p needs even dims
        command += ["-vf", f"scale={target[0]}:{target[1]}"]
    command += [
        "-c:v", "libx264",
        "-preset", preset,
        *FFMPEG_QUALITY_ARGS,
        "-threads", str(max(1, threads)),
        "-f", "mp4",  # explicit format: the output name may carry a suffix (e.g. .part)
        str(out_path),
    ]
    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise GenerationError(f"could not run {ENCODER!r}: {exc}") from exc

    try:
        assert proc.stdin is not None
        for frame in frames:
            proc.stdin.write(frame.tobytes())
    except Exception as exc:  # includes a bad frame surfacing mid-stream
        proc.kill()
        proc.wait()
        detail = proc.stderr.read().decode(errors="replace").strip() if proc.stderr else ""
        detail = f" ({detail[-500:]})" if detail else ""
        raise GenerationError(f"frame stream failed: {exc}{detail}") from exc
    finally:
        if proc.stdin:
            proc.stdin.close()

    stderr = proc.communicate()[1]
    if proc.returncode != 0:
        raise GenerationError(
            f"{ENCODER} failed (exit {proc.returncode}): {stderr.decode(errors='replace').strip()}"
        )


def _save_atomic(image: Image.Image, out_path: Path) -> Path:
    """Save *image* to a ``.part`` file and atomically move it into place.

    A finished card therefore only ever exists in its complete form.
    """
    tmp_path = out_path.with_name(out_path.name + ".part")
    try:
        image.save(tmp_path, format="PNG")
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    tmp_path.replace(out_path)
    return out_path


def _finish_card(
    json_path: Path,
    artifact: Path,
    background: Image.Image,
    logo: Image.Image,
    margin: int,
    padding: int,
    copyright_color: tuple[int, int, int, int],
    name: str,
    framerate: int,
    ffmpeg_threads: int,
    composite_workers: int,
    preset: str,
    scale: float,
    expected_size: tuple[int, int] | None,
    out_dir: Path,
) -> Path:
    """Composite a render and write the final PNG or MP4 (atomically).

    Every frame is decoded exactly once, in the streaming pass: a corrupt
    or truncated frame surfaces there and re-triggers the render.
    """
    if artifact.is_file():
        frame = _open_frame(artifact)
        _check_frame_size(frame, artifact.name, expected_size)
        base = _fit_background(background, frame.size)
        base = _with_logo(base, _scale_logo(logo, frame.width), margin)
        base = _with_name(base, padding, name)
        base = _with_copyright(base, padding, copyright_color)
        final = _composite_frame(frame, base).convert("RGB")
        return _save_atomic(final, out_dir / f"{json_path.stem}.png")

    frame_paths = _frame_paths(artifact)
    first = _open_frame(frame_paths[0])
    _check_frame_size(first, frame_paths[0].name, expected_size)
    size = first.size
    base = _fit_background(background, size)
    base = _with_logo(base, _scale_logo(logo, size[0]), margin)
    base = _with_name(base, padding, name)
    base = _with_copyright(base, padding, copyright_color)

    def frames() -> Iterator[Image.Image]:
        def composite(index: int, path: Path) -> Image.Image:
            frame = first if index == 0 else _open_frame(path)
            if frame.size != size:
                raise GenerationError(
                    f"frame size {frame.size[0]}x{frame.size[1]} does not match "
                    f"the first frame's {size[0]}x{size[1]}"
                )
            return _composite_frame(frame, base)

        # Frames are independent of each other, so they are composited out
        # of order in a thread pool (Pillow releases the GIL while
        # decoding); only the hand-off to ffmpeg follows presentation
        # order. A sliding window of `workers` pending composites keeps the
        # pool fed without materializing the whole clip: at most ~2x the
        # worker count of frames are in memory at any moment.
        workers = max(1, min(composite_workers, len(frame_paths)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures: list[Future[Image.Image] | None] = [None] * len(frame_paths)
            for i in range(workers):
                futures[i] = pool.submit(composite, i, frame_paths[i])
            for index in range(len(frame_paths)):
                try:
                    yield futures[index].result()
                except Exception:
                    for pending in futures[index + 1 :]:
                        if pending is not None:
                            pending.cancel()
                    raise
                next_index = index + workers
                if next_index < len(frame_paths):
                    futures[next_index] = pool.submit(composite, next_index, frame_paths[next_index])

    out_path = out_dir / f"{json_path.stem}.mp4"
    tmp_path = out_path.with_name(out_path.name + ".part")
    try:
        _encode_mp4(frames(), size, framerate, tmp_path, ffmpeg_threads, preset, scale)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
    tmp_path.replace(out_path)
    return out_path


def _process_card(
    json_path: Path,
    ffmpeg_threads: int = 1,
    composite_workers: int = 4,
    preset: str = DEFAULT_PRESET,
    scale: float = DEFAULT_SCALE,
    out_base: Path = OUTPUT_DIR,
) -> Path:
    """Render, composite and encode a single card definition."""
    json_path = json_path.resolve()
    card = _load_card(json_path)
    background = Image.open(_background_path(card, json_path)).convert("RGBA")

    logo_path = LOGO_PATHS[bool(card.get("invert_logo", False))]
    if not logo_path.is_file():
        raise GenerationError(f"logo not found: {logo_path}")
    logo = Image.open(logo_path).convert("RGBA")
    if not FONT.is_file():
        raise GenerationError(f"font not found: {FONT}")
    if not FONT_NAME.is_file():
        raise GenerationError(f"font not found: {FONT_NAME}")
    if "name" not in card:
        raise GenerationError(f"{json_path.name}: missing 'name'")
    name = str(card["name"])
    padding = card["padding"]
    margin = round(LOGO_PADDING_FACTOR * padding)
    copyright_color = (
        (0, 0, 0, 255) if card.get("invert_copyright", False) else (255, 255, 255, 255)
    )
    framerate = card["framerate"] or DEFAULT_FRAMERATE

    viewport = card.get("viewport")
    expected_size = tuple(viewport) if viewport else None

    out_dir = out_base / json_path.parent.relative_to(CARDS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Each render lives in a throw-away working directory; it is removed
    # (together with all intermediate PNGs) when the block exits. The GPU
    # is shared with other tenants, so failures here can be transient
    # (render missing, truncated frame, encode error); the card is re-run
    # from scratch up to RENDER_ATTEMPTS times before giving up.
    for attempt in range(1, RENDER_ATTEMPTS + 1):
        with tempfile.TemporaryDirectory(prefix="nikke-reborn-") as workdir:
            try:
                artifact = _render_card(json_path, Path(workdir))
                return _finish_card(
                    json_path,
                    artifact,
                    background,
                    logo,
                    margin,
                    padding,
                    copyright_color,
                    name,
                    framerate,
                    ffmpeg_threads,
                    composite_workers,
                    preset,
                    scale,
                    expected_size,
                    out_dir,
                )
            except Exception as exc:
                if attempt >= RENDER_ATTEMPTS:
                    raise GenerationError(
                        f"render of {json_path.name} still failing after "
                        f"{RENDER_ATTEMPTS} attempts: {exc}"
                    ) from exc
                print(
                    f"    ! {json_path.name}: {exc}; re-rendering "
                    f"(attempt {attempt}/{RENDER_ATTEMPTS})",
                    flush=True,
                )
    raise AssertionError("unreachable")  # pragma: no cover


def _default_jobs() -> int:
    """A sensible default pool size: up to 8 cards at once, 1 per 4 cores."""
    return min(8, max(1, (os.cpu_count() or 4) // 4))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render and composite Nikke trading cards from cards/"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        metavar="CARD_JSON",
        help="card definition(s) to generate; default: all under cards/",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=_default_jobs(),
        help="number of cards to process in parallel (default: %(default)s)",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help=(
            "draft mode for quick iteration: ultrafast x264 preset, "
            "half-resolution MP4s, results written to draft/ instead of output/"
        ),
    )
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")
    return args


def _generate(
    paths: list[Path],
    jobs: int,
    preset: str,
    scale: float,
    out_base: Path,
) -> None:
    """Process the selected cards in a pool of worker processes."""
    _require_executable(VIEWER)
    _require_executable(ENCODER)
    card_configs = _find_card_configs(paths)
    total = len(card_configs)
    # Split the cores available to each card between the stages that run
    # in parallel: the frame compositing and the ffmpeg encode.
    per_card = (os.cpu_count() or 1) // max(1, min(jobs, total))
    ffmpeg_threads = max(2, min(MAX_STAGE_THREADS, per_card // 2))
    composite_workers = max(2, min(MAX_STAGE_THREADS, per_card - ffmpeg_threads))
    start = time.monotonic()
    notes = []
    if preset != DEFAULT_PRESET:
        notes.append(f"x264 preset '{preset}'")
    if scale != 1.0:
        notes.append(f"{scale:g}x resolution")
    notes_text = f", {', '.join(notes)} (draft)" if notes else ""
    if paths:
        print(f"Rendering {total} selected card(s) with {jobs} worker(s){notes_text} ...")
        for path in card_configs:
            print(f"  - {path.relative_to(REPO_ROOT)}")
    else:
        print(
            f"Rendering {total} card(s) from {CARDS_DIR.relative_to(REPO_ROOT)}/ "
            f"with {jobs} worker(s){notes_text} ..."
        )

    failures: list[tuple[Path, Exception]] = []
    done = 0
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        futures = {
            pool.submit(
                _process_card, path, ffmpeg_threads, composite_workers, preset, scale, out_base
            ): path
            for path in card_configs
        }
        for future in as_completed(futures):
            done += 1
            label = futures[future].relative_to(CARDS_DIR)
            try:
                out_path = future.result()
                print(f"[{done}/{total}] {label} -> {out_path.relative_to(REPO_ROOT)}", flush=True)
            except Exception as exc:
                # Let the other cards finish; failures are reported (and the
                # run exits non-zero) once everything has had its retries.
                failures.append((label, exc))
                print(f"[{done}/{total}] {label} FAILED: {exc}", file=sys.stderr, flush=True)
    if failures:
        for label, exc in failures:
            print(f"error: {label}: {exc}", file=sys.stderr)
        sys.exit(1)
    word = "drafts" if out_base == DRAFT_DIR else "final cards"
    print(
        f"Done. {total} card(s) in {time.monotonic() - start:.1f}s, "
        f"{word} written to {out_base.relative_to(REPO_ROOT)}/"
    )
