"""One card's frame output and its presentations' renders: the shared
pipeline that turns a presentation into a stream of frames
(:func:`_render_and_finish`, :func:`_write_final_card`), the profile's
face offset and photo-reel compositing (:func:`_face_offset`,
:func:`_photo_reel`, :func:`_render_profile`), the standard's render
(:func:`_render_standard`), and the three tiers' per-presentation
workers (:func:`_process_full_art`, :func:`_process_standard_card`,
:func:`_process_profile_card`).
"""

from __future__ import annotations

import io
import subprocess
import threading
import time
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import cast

from PIL import Image, ImageOps, ImageStat

from nikke_reborn import card, expansion
from nikke_reborn.card import LOGO_PATHS, _manufacturer_logo
from nikke_reborn.config import FONT, VIEWER
from nikke_reborn.error import GenerationError
from nikke_reborn.file import _save_atomic, _stored_hash
from nikke_reborn.image import (
    LOGO_PADDING_FACTOR,
    _fade_to_dominant,
    _fit_background,
    _profile_layers,
    _standard_layers,
)
from nikke_reborn.lettering import (
    FONT_NAME,
    MANUFACTURER_LOGO_WIDTH,
    NAME_RECT_COLOR,
    _name_layers,
    _overlay_for,
    _rect_tint,
    _tint_layer,
)
from nikke_reborn.preset import Preset
from nikke_reborn.video import (
    PIPE_BUFSIZE,
    _encode_mp4,
    _PipeDrain,
    _read_exact,
    _reap_viewer,
    _stream_composited,
    _stream_dual_composited,
)

#: The ``--face`` zoom for the profile card's face framing.
PROFILE_FACE_ZOOM = 2
#: The face framing's vertical centre (a fraction of the frame height):
#: :func:`_face_offset` measures the body's occlusion of a square face
#: footprint centred there.
PROFILE_FACE_CENTER_Y = 0.1
#: The horizontal shifts (px, at the native viewport) that move the face
#: framing aside from the centered body, either side of it:
#: :func:`_face_offset` picks whichever leaves its footprint least
#: occluded.
PROFILE_FACE_OFFSET_LEFT = 500
PROFILE_FACE_OFFSET_RIGHT = 420
#: The profile card's "photo reel": face stills stacked down the card's
#: right edge — the first PROFILE_REEL_COUNT of PROFILE_REEL_ANIMATIONS
#: the character has (per the viewer's ``--list-animations``), one at
#: time 0 per animation (the viewer's ``--portrait`` framing in a square
#: viewport), taken once per card and reused for every frame, framed by
#: a border of the background's dominant tint. Fewer stills — or none —
#: when fewer of the list match.
PROFILE_REEL_SIDE = 1 / 7
#: The first photo-reel square's top edge (a fraction of the frame
#: height).
PROFILE_REEL_TOP = 3 / 7
#: The photo reel's inset from the card's right edge (a multiple of the
#: card's padding).
PROFILE_REEL_MARGIN = 1.5
#: The photo-reel border's width (a fraction of the photo's side).
PROFILE_REEL_BORDER = 0.005
#: The photo-reel border's opacity (the tint frame is semi-transparent,
#: so the card art behind it shows through).
PROFILE_REEL_BORDER_ALPHA = 0.8

#: A card whose render cannot be processed is re-run up to this many
#: times before giving up: the GPU is shared, so a render error, a
#: truncated frame stream or an encode error can be transient
#: (``nikke-viewer`` writes its frames from multiple threads and can
#: occasionally leave a truncated stream behind while still exiting
#: with status 0).
RENDER_ATTEMPTS = 3


def _presentation_flags(presentation: expansion.Presentation) -> list[str]:
    """The presentation's viewer flags (the character's variant, the
    render's animation, the time 0 stills): the viewer's defaults when
    the presentation names none of them."""
    flags: list[str] = []
    if presentation.variant is not None:
        flags += ["--variant", presentation.variant]
    if presentation.animation is not None:
        flags += ["--animation", presentation.animation]
    if presentation.time is not None:
        flags += ["--time", str(presentation.time)]
    if presentation.half_body:
        flags += ["--half-body"]
    return flags


def _framing_overrides(presentation: expansion.Presentation) -> list[str]:
    """The presentation's viewer framing overrides (its *x*/*y* world-space
    translation and *zoom* multiplier, when the TOML names them for the
    presentation) as the viewer's ``--x``/``--y``/``--zoom`` flags."""
    flags: list[str] = []
    if presentation.x is not None:
        flags += ["--x", str(presentation.x)]
    if presentation.y is not None:
        flags += ["--y", str(presentation.y)]
    if presentation.zoom is not None:
        flags += ["--zoom", str(presentation.zoom)]
    return flags


def _framerate_flags(presentation: expansion.Presentation, framerate: int) -> list[str]:
    """The viewer's export-framerate flag (animation streams only — the
    viewer ignores it for a ``--time`` still). It must equal the run's
    mux framerate: the viewer samples the animation at that rate and
    ffmpeg labels the MP4 with it, so a mismatch would play the card
    back at the wrong speed."""
    return ["--framerate", str(framerate)] if presentation.animated else []


def _viewer_args(size: tuple[int, int], char_id: str, *flags: str) -> list[str]:
    """The viewer's command for one stream: the *flags* (the framing and
    the presentation's terms), the run's size and the character's id —
    the viewer's ``--stdout`` emits raw RGBA frames at that size."""
    return [
        VIEWER,
        *flags,
        "--width",
        str(size[0]),
        "--height",
        str(size[1]),
        "--stdout",
        char_id,
    ]


def _logo_faces() -> tuple[Image.Image, Image.Image]:
    """The NIKKE logo's two faces (black, white), both required: the
    first frame's luma picks the one a card stamps (see
    :func:`nikke_reborn.lettering._overlay_for`)."""
    faces: list[Image.Image] = []
    for path in (LOGO_PATHS[True], LOGO_PATHS[False]):
        if not path.is_file():
            raise GenerationError(f"logo not found: {path}")
        faces.append(Image.open(path).convert("RGBA"))
    return faces[0], faces[1]


def _render_and_finish(
    presentation: expansion.Presentation,
    size: tuple[int, int],
    animated: bool,
    base: Image.Image,
    faces: tuple[Image.Image, Image.Image],
    margin: int,
    padding: int,
    framerate: int,
    ffmpeg_threads: int,
    composite_workers: int,
    preset: Preset,
    source_hash: str,
) -> tuple[Path, dict[str, float | None]]:
    """Render the presentation via the viewer's ``--stdout`` raw stream
    and write the final PNG, or the MP4 alongside its first frame as a
    PNG.

    The framing is the presentation's (the ``--half-body`` flag when
    *half_body* — the upper body, head to waist — or the viewer's
    default framing). Nothing intermediate touches the disk: the viewer's
    raw RGBA frames are piped straight into the in-memory compositing and
    (for animations) the ffmpeg encode; only the finished card is written
    (atomically). A failure at any stage surfaces as a
    :class:`GenerationError` so the caller can re-render the card from
    scratch.

    Returns the finished card's path and the stage timings in seconds
    (see :func:`_write_final_card`). A raw frame is far larger than the
    pipe buffer, so the viewer blocks on write until the reader drains:
    under load ``render`` therefore reflects the slowest downstream stage
    as much as the viewer itself."""

    # The logo and copyright line sit on top of the art: the first
    # frame's luma under each picks its face, and the overlay is applied
    # to each frame after the art is composited.
    def make_overlay(
        art: Image.Image,
    ) -> tuple[Image.Image, tuple[int, int]]:
        return _overlay_for(art, size, faces[0], faces[1], margin, padding)

    composite_time: list[float] = [0.0]
    stream_end: list[float] = [0.0]

    render_started = time.perf_counter()
    viewer_args = _viewer_args(
        size,
        presentation.card.id,
        *_presentation_flags(presentation),
        *_framing_overrides(presentation),
        *_framerate_flags(presentation, framerate),
    )
    try:
        viewer = subprocess.Popen(
            viewer_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=PIPE_BUFSIZE,
        )
    except OSError as exc:
        raise GenerationError(f"could not run {VIEWER!r}: {exc}") from exc
    assert viewer.stderr is not None
    # A Popen pipe is a buffered reader (needed for read1).
    drain = _PipeDrain(cast(io.BufferedReader, viewer.stderr))
    first_frame: list[Image.Image] = []
    composited = _stream_composited(
        viewer,
        drain,
        presentation.label,
        size,
        base,
        make_overlay,
        composite_workers,
        first_frame,
        composite_time,
        stream_end,
    )
    return _write_final_card(
        composited,
        presentation,
        animated,
        size,
        framerate,
        ffmpeg_threads,
        preset,
        source_hash,
        first_frame,
        composite_time,
        stream_end,
        render_started,
    )


class _FirstFrameWriter:
    """The animation's first-frame PNG sidecar, written in a background
    thread: started with the first consumed frame (mid-encode, see
    :func:`_write_final_card`), so the PNG's save overlaps the encode
    instead of following it. *join* waits for the write and re-raises
    its failure — a finished card only exists in its complete form (both
    the mp4 and the sidecar), and a failed write surfaces as the card's
    failure so the caller re-renders it from scratch."""

    def __init__(self, out_path: Path, source_hash: str) -> None:
        self._out_path = out_path
        self._source_hash = source_hash
        self._thread: threading.Thread | None = None
        self._exc: BaseException | None = None
        self._done = False

    @property
    def started(self) -> bool:
        return self._thread is not None

    def start(self, image: Image.Image) -> None:
        if self._thread is not None:
            return
        self._image = image
        self._thread = threading.Thread(
            target=self._run, name="first-frame-png", daemon=True
        )
        self._thread.start()

    def _run(self) -> None:
        try:
            _save_atomic(self._image.convert("RGB"), self._out_path, self._source_hash)
            self._done = True
        except BaseException as exc:  # noqa: BLE001 — re-raised by join
            self._exc = exc

    def join(self, *, fail: bool = True) -> None:
        """Wait for the write; when *fail*, re-raise its failure (or the
        write not completing at all). A no-op when never started."""
        if self._thread is None:
            return
        self._thread.join()
        self._thread = None
        if fail and (self._exc is not None or not self._done):
            raise self._exc or GenerationError("first-frame PNG write did not complete")


def _write_final_card(
    composited: Generator[Image.Image],
    presentation: expansion.Presentation,
    animated: bool,
    size: tuple[int, int],
    framerate: int,
    ffmpeg_threads: int,
    preset: Preset,
    source_hash: str,
    first_frame: list[Image.Image],
    composite_time: list[float],
    stream_end: list[float],
    render_started: float,
) -> tuple[Path, dict[str, float | None]]:
    """Write a composited frame stream to the final card.

    An animation is encoded to an MP4 alongside its first frame (the
    same composited frame, so it matches the mp4's opening frame
    exactly); a fixed-time card is written as a single PNG. For
    animations the first-frame PNG is written in a background thread
    that starts with the first consumed frame, so the sidecar's save
    overlaps the encode. *composited* is closed (so the viewer
    stream(s) are reaped). Returns the stage timings (in seconds):
    ``render`` (spawn until the frame stream is fully delivered),
    ``composite`` (the per-frame Pillow work, summed across the worker
    threads) and ``encode`` (the ffmpeg wall time for animations, the
    PNG write for static cards) — the stages overlap, so the numbers are
    per-stage costs, not a sequential partition."""
    out_path = card.output_path(
        presentation.expansion.name,
        presentation.card.stem,
        presentation.name,
        presentation.rarity_index,
        "mp4" if animated else "png",
        preset,
    )
    encode_time: float | None = None
    try:
        if animated:
            tmp_path = out_path.with_name(out_path.name + ".part")
            png_writer = _FirstFrameWriter(
                card.output_path(
                    presentation.expansion.name,
                    presentation.card.stem,
                    presentation.name,
                    presentation.rarity_index,
                    "png",
                    preset,
                ),
                source_hash,
            )

            def feed(frames: Iterator[Image.Image]) -> Iterator[Image.Image]:
                # Fire the sidecar's write at the first frame, so it runs
                # under the encode instead of after it.
                for frame in frames:
                    if not png_writer.started and first_frame:
                        png_writer.start(first_frame[0])
                    yield frame

            try:
                encode_started = time.perf_counter()
                _encode_mp4(
                    feed(composited),
                    size,
                    card.run_video_size(preset),
                    framerate,
                    tmp_path,
                    ffmpeg_threads,
                    preset.x264_preset,
                    source_hash,
                )
                encode_time = time.perf_counter() - encode_started
                if not first_frame:
                    raise GenerationError(
                        f"{VIEWER} produced no frames for {presentation.label}"
                    )
            except Exception:
                tmp_path.unlink(missing_ok=True)
                # Let the sidecar's write settle before the retry starts
                # (both write the same .part); its error does not shadow
                # the encode's.
                png_writer.join(fail=False)
                raise
            tmp_path.replace(out_path)
            png_writer.join()
        else:
            # A single frame: consume the stream (its image landed in
            # first_frame while it was composited) and write it.
            next(composited, None)
            if not first_frame:
                raise GenerationError(
                    f"{VIEWER} produced no frame for {presentation.label}"
                )
            encode_started = time.perf_counter()
            _save_atomic(first_frame[0].convert("RGB"), out_path, source_hash)
            encode_time = time.perf_counter() - encode_started
    finally:
        # Stop consuming; the compositor's finally reaps the viewer(s)
        # and checks their exit.
        composited.close()
    # Measured to stream EOF (not the reap, which happens after the
    # encode and the save), so ``render`` covers the frame delivery only.
    render_seconds = (stream_end[0] or time.perf_counter()) - render_started
    return out_path, {
        "render": render_seconds,
        "composite": composite_time[0],
        "encode": encode_time,
    }


def _first_frame(
    size: tuple[int, int], char_id: str, *viewer_flags: str
) -> Image.Image:
    """The first frame of the character's render by the viewer with
    *viewer_flags* — one raw RGBA frame read from the ``--stdout``
    stream, at exactly *size* (the flags are passed here so the stream
    always matches the read). The viewer is reaped: for an animation
    only the opening frame is needed."""
    width, height = size
    viewer = subprocess.Popen(
        _viewer_args(size, char_id, *viewer_flags),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=PIPE_BUFSIZE,
    )
    assert viewer.stdout is not None
    assert viewer.stderr is not None
    # A Popen pipe is a buffered reader (needed for read1).
    drain = _PipeDrain(cast(io.BufferedReader, viewer.stderr))
    try:
        data = _read_exact(viewer.stdout, width * height * 4)
    finally:
        # One frame is all we need; reap the viewer, which may still be
        # mid-stream.
        _reap_viewer(viewer, drain, clean_exit_expected=False)
    frame_bytes = width * height * 4
    if len(data) != frame_bytes:
        raise GenerationError(
            f"{VIEWER} stream for {char_id!r} truncated: "
            f"{len(data)} of {frame_bytes} bytes"
        )
    return Image.frombytes("RGBA", (width, height), data)


def _face_offset(
    presentation: expansion.Presentation, size: tuple[int, int], preset: Preset
) -> int:
    """The face framing's ``--offset-x``: the left or right shift (scaled
    to the run's final size, since the viewer's ``--offset-x`` is screen
    px), whichever leaves the face's footprint least occluded by the
    body. The body is measured in the presentation's own framing (its
    default framing — the body stream's — with its variant and
    animation)."""
    width, height = size
    body = _first_frame(
        size,
        presentation.card.id,
        *_presentation_flags(presentation),
        *_framing_overrides(presentation),
    )
    alpha = body.getchannel("A").point(lambda v: 255 if v > 32 else 0)
    centre_y = int(height * PROFILE_FACE_CENTER_Y)
    half = int(height * PROFILE_FACE_CENTER_Y * PROFILE_FACE_ZOOM) // 2

    def occlusion(cx: int) -> int:
        x0, y0, x1, y1 = cx - half, centre_y - half, cx + half, centre_y + half
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(width, x1), min(height, y1)
        if x0 >= x1 or y0 >= y1:
            return 0
        return ImageStat.Stat(alpha.crop((x0, y0, x1, y1))).sum[0]

    if not ImageStat.Stat(alpha).sum[0]:
        return 0  # no body at all; keep the face centered
    left_offset = round(PROFILE_FACE_OFFSET_LEFT * preset.scale)
    right_offset = round(PROFILE_FACE_OFFSET_RIGHT * preset.scale)
    left = occlusion(width // 2 - left_offset)
    right = occlusion(width // 2 + right_offset)
    # A tie (the body sits between the two footprints) still shifts;
    # never leave the face on top of the body.
    return -left_offset if left < right else right_offset


def _reel_animations(char_id: str) -> list[str]:
    """The photo reel's animations (see
    :func:`nikke_reborn.expansion.reel_animations`), asked of the viewer
    once per process: the render's profile passes reuse the selection's
    lists."""
    return expansion.reel_animations(char_id)


def _photo_reel(
    presentation: expansion.Presentation,
    size: tuple[int, int],
    padding: int,
    tint_rgb: tuple[int, int, int],
) -> list[tuple[Image.Image, tuple[int, int]]]:
    """The profile card's photo reel (see :data:`PROFILE_REEL_COUNT`):
    one face still per animation of :func:`_reel_animations`, as
    (still, position) pairs for the compositor.

    Each still is the time 0 frame of its animation, rendered in the
    viewer's ``--portrait`` framing in a square viewport and flattened
    onto a white background (the viewer's frames are transparent where
    the character does not cover), framed by a border of the
    background's dominant tint. The stills are taken once per card and
    reused for every frame; the blocks run down the right edge (see the
    ``PROFILE_REEL_*`` constants)."""
    animations = _reel_animations(presentation.card.id)
    if not animations:
        return []
    side = round(size[0] * PROFILE_REEL_SIDE)
    border = round(side * PROFILE_REEL_BORDER)
    block = side + 2 * border
    left = size[0] - round(padding * PROFILE_REEL_MARGIN) - block
    top = round(size[1] * PROFILE_REEL_TOP)
    step = block + padding
    reel: list[tuple[Image.Image, tuple[int, int]]] = []
    for index, animation in enumerate(animations):
        still = _first_frame(
            (side, side),
            presentation.card.id,
            "--portrait",
            "--time",
            "0",
            "--animation",
            animation,
        )
        white = Image.new("RGBA", still.size, (255, 255, 255, 255))
        white.paste(still, (0, 0), still)
        still = white
        framed = Image.new(
            "RGBA", (block, block), (*tint_rgb, round(255 * PROFILE_REEL_BORDER_ALPHA))
        )
        framed.paste(still, (border, border))
        reel.append((framed, (left, top + index * step)))
    return reel


def _render_profile(
    presentation: expansion.Presentation,
    size: tuple[int, int],
    animated: bool,
    background: Image.Image,
    tint: Image.Image,
    mask: Image.Image,
    tint_rgb: tuple[int, int, int],
    faces: tuple[Image.Image, Image.Image],
    margin: int,
    padding: int,
    name: str,
    subtitle: str,
    manufacturer_logo: Image.Image | None,
    framerate: int,
    ffmpeg_threads: int,
    composite_workers: int,
    preset: Preset,
    source_hash: str,
    face_zoom: float,
) -> tuple[Path, dict[str, float | None]]:
    """Render the profile card (a presentation, written out as
    ``<card>_<presentation>.<suffix>``): the ``--face`` framing animates
    (as a monochrome of the tint's hue, shifted aside from the body)
    over the background, under the tint wash, and the body over the
    mask, both streamed in lockstep (the presentation's framing overrides,
    if any, apply to the body stream; the face close-up keeps its own
    zoom and offset). The name and subtitle overlays are
    applied as usual (with the character's manufacturer's logo above the
    name's bar, *manufacturer_logo*). The logo and copyright line sit
    on top of the art, the logo at the top right instead of the bottom
    right, each stamp's face chosen from the first frame's luma under it.
    The card's photo reel (:func:`_photo_reel`) is composited onto every
    frame as well.

    Like :func:`_render_and_finish`, nothing intermediate touches the
    disk; only the finished card is written (atomically). Returns the
    finished card's path and the stage timings (see
    :func:`_write_final_card`)."""

    # The logo and copyright line sit on top of the art; the profile
    # card's logo sits at the top right instead of the bottom right, and
    # the first frame's luma under each picks its face.
    def make_overlay(
        art: Image.Image,
    ) -> tuple[Image.Image, tuple[int, int]]:
        return _overlay_for(
            art, size, faces[0], faces[1], margin, padding, logo_top=True
        )

    parts = (
        _name_layers(
            size,
            name,
            subtitle,
            padding,
            NAME_RECT_COLOR,
            _rect_tint(background),
            manufacturer_logo,
        )
        if (name or subtitle)
        else None
    )
    composite_time: list[float] = [0.0]
    stream_end: list[float] = [0.0]

    face_offset = _face_offset(presentation, size, preset)

    reel = _photo_reel(presentation, size, padding, tint_rgb)

    render_started = time.perf_counter()
    face_args = _viewer_args(
        size,
        presentation.card.id,
        "--face",
        "--zoom",
        str(face_zoom),
        "--offset-x",
        str(face_offset),
        *_presentation_flags(presentation),
        *_framerate_flags(presentation, framerate),
    )
    body_args = _viewer_args(
        size,
        presentation.card.id,
        *_presentation_flags(presentation),
        *_framing_overrides(presentation),
        *_framerate_flags(presentation, framerate),
    )
    try:
        face_viewer = subprocess.Popen(
            face_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=PIPE_BUFSIZE,
        )
    except OSError as exc:
        raise GenerationError(f"could not run {VIEWER!r} (face): {exc}") from exc
    try:
        body_viewer = subprocess.Popen(
            body_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=PIPE_BUFSIZE,
        )
    except OSError as exc:
        face_viewer.kill()
        face_viewer.wait()
        raise GenerationError(f"could not run {VIEWER!r} (body): {exc}") from exc
    assert face_viewer.stderr is not None
    assert body_viewer.stderr is not None
    # A Popen pipe is a buffered reader (needed for read1).
    face_drain = _PipeDrain(cast(io.BufferedReader, face_viewer.stderr))
    body_drain = _PipeDrain(cast(io.BufferedReader, body_viewer.stderr))
    first_frame: list[Image.Image] = []
    composited = _stream_dual_composited(
        face_viewer,
        face_drain,
        body_viewer,
        body_drain,
        presentation.label,
        size,
        background,
        tint,
        mask,
        make_overlay,
        parts,
        reel,
        composite_workers,
        first_frame,
        composite_time,
        stream_end,
    )
    return _write_final_card(
        composited,
        presentation,
        animated,
        size,
        framerate,
        ffmpeg_threads,
        preset,
        source_hash,
        first_frame,
        composite_time,
        stream_end,
        render_started,
    )


def _render_standard(
    presentation: expansion.Presentation,
    size: tuple[int, int],
    animated: bool,
    base: Image.Image,
    sub_rect_color: tuple[int, int, int],
    name: str,
    subtitle: str,
    manufacturer_logo: Image.Image | None,
    faces: tuple[Image.Image, Image.Image],
    margin: int,
    padding: int,
    framerate: int,
    ffmpeg_threads: int,
    composite_workers: int,
    preset: Preset,
    source_hash: str,
) -> tuple[Path, dict[str, float | None]]:
    """Render the standard card (a presentation, written out as
    ``<card>_<presentation>.<suffix>``): the presentation's background
    (faded toward its dominant color, no monochrome) carries the
    standard card mask (already composited into *base*), and the
    character's upper body (the viewer's ``--half-body`` flag, the
    presentation's animation) animates over it. The name and subtitle
    overlays are applied as usual; the manufacturer's logo
    (*manufacturer_logo*) sits at the top right, its corner inset and
    drawn in black; the NIKKE logo sits at the bottom right and the
    copyright at the bottom left, each stamp's face chosen from the
    first frame's luma under it.

    Like :func:`_render_and_finish`, nothing intermediate touches the
    disk; only the finished card is written (atomically). Returns the
    finished card's path and the stage timings (see
    :func:`_write_final_card`)."""

    # The overlay's faces are picked from the first frame's luma; the
    # manufacturer's logo joins it: top right, drawn in black.
    def make_overlay(
        art: Image.Image,
    ) -> tuple[Image.Image, tuple[int, int]]:
        overlay, overlay_pos = _overlay_for(
            art, size, faces[0], faces[1], margin, padding
        )
        if manufacturer_logo is not None:
            inset = round(padding * 1.5)
            mark_w = round(size[0] * MANUFACTURER_LOGO_WIDTH)
            mark_h = round(mark_w * manufacturer_logo.height / manufacturer_logo.width)
            mark = manufacturer_logo.resize((mark_w, mark_h), Image.Resampling.LANCZOS)
            mark = _tint_layer(mark.getchannel("A"), (0, 0, 0), 1.0)
            # Rebuild on a full frame so the (already cropped) overlay
            # and the new mark land at their card positions, then crop
            # back to the combined ink.
            full = Image.new("RGBA", size, (0, 0, 0, 0))
            full.alpha_composite(overlay, overlay_pos)
            full.alpha_composite(mark, (size[0] - inset - mark_w, inset))
            box = full.getbbox()
            assert box is not None, "the standard card's overlay is empty"
            return full.crop(box), (box[0], box[1])
        return overlay, overlay_pos

    parts = (
        _name_layers(
            size,
            name,
            subtitle,
            padding,
            NAME_RECT_COLOR,
            sub_rect_color,
        )
        if (name or subtitle)
        else None
    )
    composite_time: list[float] = [0.0]
    stream_end: list[float] = [0.0]

    render_started = time.perf_counter()
    viewer_args = _viewer_args(
        size,
        presentation.card.id,
        *_presentation_flags(presentation),
        *_framing_overrides(presentation),
        *_framerate_flags(presentation, framerate),
    )
    try:
        viewer = subprocess.Popen(
            viewer_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=PIPE_BUFSIZE,
        )
    except OSError as exc:
        raise GenerationError(f"could not run {VIEWER!r} (half body): {exc}") from exc
    assert viewer.stderr is not None
    # A Popen pipe is a buffered reader (needed for read1).
    drain = _PipeDrain(cast(io.BufferedReader, viewer.stderr))
    first_frame: list[Image.Image] = []
    composited = _stream_composited(
        viewer,
        drain,
        presentation.label,
        size,
        base,
        make_overlay,
        composite_workers,
        first_frame,
        composite_time,
        stream_end,
        parts,
    )
    return _write_final_card(
        composited,
        presentation,
        animated,
        size,
        framerate,
        ffmpeg_threads,
        preset,
        source_hash,
        first_frame,
        composite_time,
        stream_end,
        render_started,
    )


def _process_full_art(
    presentation: expansion.Presentation,
    ffmpeg_threads: int = 1,
    composite_workers: int = 4,
    preset: Preset = Preset.DEFAULT,
    force: bool = False,
    no_video: bool = False,
) -> tuple[Path, bool, dict[str, float | None] | None]:
    """Render, composite and encode one presentation of the full-art
    tier (no mask): the presentation's background (fitted to the frame
    and left as-is — no auto-contrast, no fade, the standard tier's
    treatments — a solid black for the goddess presentation) carries
    the white NIKKE logo and the copyright line (white); the card name
    is not drawn on the full-art cards. The framing is the
    presentation's (the ``--half-body`` flag for some presentations,
    the viewer's default framing for the rest).

    With *no_video* an animated presentation renders its first frame
    alone — its MP4 is skipped and the viewer reaped right after that
    frame — so the output, and the up-to-date check, cover the
    first-frame PNG.

    Returns ``(out_path, skipped, timings)``; *skipped* is True when the
    output already exists and the presentation hash it embeds matches
    the current one (nothing was re-rendered), in which case *timings*
    is None; otherwise it is the stage-timing dict from
    :func:`_render_and_finish` plus ``total``, the card's overall
    wall-clock seconds."""
    total_started = time.perf_counter()
    exp = presentation.expansion
    entry = presentation.card

    faces = _logo_faces()
    if not FONT.is_file():
        raise GenerationError(f"font not found: {FONT}")
    # The effective padding at the run's final size (the card's padding
    # is native-px): it drives the lettering, the logo placement and the
    # like.
    padding = card.padding(preset)
    margin = round(LOGO_PADDING_FACTOR * padding)
    framerate = preset.framerate

    # The run's card size: the card's viewport at the run's scale (even
    # dims for the yuv420p encode). The whole pipeline — the viewer, the
    # compositing and the finished card — runs at this size; the video
    # is the only output that can leave it resampled (the low preset's
    # lower-resolution video, scaled at the encode).
    size = card.run_size(preset)

    # A presentation without a `time` renders an animation (mp4) plus its
    # first frame (png); one with a `time` renders a single frame (png).
    animated = presentation.animated and not no_video
    out_path = card.output_path(
        exp.name,
        entry.stem,
        presentation.name,
        presentation.rarity_index,
        "mp4" if animated else "png",
        preset,
    )
    source_hash = card.presentation_source_hash(presentation, preset)
    if not force:
        up_to_date = out_path.is_file() and _stored_hash(out_path) == source_hash
        if up_to_date and animated:
            # The animation's first frame is kept alongside it; a missing or
            # stale copy forces the card to be re-rendered.
            first_frame_path = card.output_path(
                exp.name,
                entry.stem,
                presentation.name,
                presentation.rarity_index,
                "png",
                preset,
            )
            up_to_date = (
                first_frame_path.is_file()
                and _stored_hash(first_frame_path) == source_hash
            )
        if up_to_date:
            return out_path, True, None
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # The full-art base: the background as-is (or solid black for the
    # goddess presentation, which composites on no background).
    if presentation.background == "black":
        base = Image.new("RGBA", size, (0, 0, 0, 255))
    else:
        background = expansion.load_background(exp, presentation.background)

        background = ImageOps.autocontrast(
            background.convert("RGB"),
            cutoff=(5, 0),
            preserve_tone=True,
        ).convert("RGBA")

        base = _fit_background(background, size)

    # The GPU is shared, so a render error, a truncated frame stream or an
    # encode error can be transient; the card is re-rendered from scratch
    # up to RENDER_ATTEMPTS times before giving up. Nothing intermediate is
    # written to disk in between.
    for attempt in range(1, RENDER_ATTEMPTS + 1):
        try:
            finished, timings = _render_and_finish(
                presentation,
                size,
                animated,
                base,
                faces,
                margin,
                padding,
                framerate,
                ffmpeg_threads,
                composite_workers,
                preset,
                source_hash,
            )
            timings["total"] = time.perf_counter() - total_started
            return finished, False, timings
        except Exception as exc:
            if attempt >= RENDER_ATTEMPTS:
                raise GenerationError(
                    f"render of {presentation.label} still failing after "
                    f"{RENDER_ATTEMPTS} attempts: {exc}"
                ) from exc
            print(
                f"    ! {presentation.label}: {exc}; re-rendering "
                f"(attempt {attempt}/{RENDER_ATTEMPTS})",
                flush=True,
            )
    raise AssertionError("unreachable")  # pragma: no cover


def _process_profile_card(
    presentation: expansion.Presentation,
    ffmpeg_threads: int = 1,
    composite_workers: int = 4,
    preset: Preset = Preset.DEFAULT,
    force: bool = False,
    no_video: bool = False,
) -> tuple[Path, bool, dict[str, float | None] | None]:
    """Render the profile card for the presentation (on the profile's
    mask): the ``--face`` framing animates (as a monochrome of the
    tint's hue) over the background, under its dominant tint wash, and
    the body over the card mask (both streamed in lockstep). The name
    and subtitle overlays are applied as usual; the logo sits at the top
    right. The card's photo reel (:func:`_photo_reel`) is composited onto
    every frame.

    With *no_video* an animated profile card renders its first frame
    alone — its MP4 is skipped and the viewers reaped right after that
    frame — so the output, and the up-to-date check, cover the
    first-frame PNG.

    Everything is composited in memory (only the finished card is
    written). Returns ``(out_path, skipped, timings)`` like
    :func:`_process_full_art`."""
    total_started = time.perf_counter()
    exp = presentation.expansion
    entry = presentation.card

    faces = _logo_faces()
    if not FONT.is_file():
        raise GenerationError(f"font not found: {FONT}")
    if not FONT_NAME.is_file():
        raise GenerationError(f"font not found: {FONT_NAME}")
    name = entry.title
    subtitle = entry.subtitle
    # The character's manufacturer's logo (None when unknown): it sits
    # above the name's bar.
    manufacturer_logo = _manufacturer_logo(entry.id)
    padding = card.padding(preset)
    margin = round(LOGO_PADDING_FACTOR * padding)
    framerate = preset.framerate

    size = card.run_size(preset)

    animated = presentation.animated and not no_video
    out_path = card.output_path(
        exp.name,
        entry.stem,
        presentation.name,
        presentation.rarity_index,
        "mp4" if animated else "png",
        preset,
    )
    source_hash = card.presentation_source_hash(presentation, preset)
    if not force:
        up_to_date = out_path.is_file() and _stored_hash(out_path) == source_hash
        if up_to_date and animated:
            first_frame_path = card.output_path(
                exp.name,
                entry.stem,
                presentation.name,
                presentation.rarity_index,
                "png",
                preset,
            )
            up_to_date = (
                first_frame_path.is_file()
                and _stored_hash(first_frame_path) == source_hash
            )
        if up_to_date:
            return out_path, True, None
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # The static layers (the fitted background, the dominant tint, the
    # mask), prepared once ahead of the render (a failure re-renders from
    # scratch).
    background = expansion.load_background(exp, presentation.background)

    background = ImageOps.autocontrast(
        background.convert("RGB"),
        cutoff=(5, 0),
        preserve_tone=True,
    ).convert("RGBA")

    base, tint, mask, tint_rgb = _profile_layers(background, size)

    for attempt in range(1, RENDER_ATTEMPTS + 1):
        try:
            finished, timings = _render_profile(
                presentation,
                size,
                animated,
                base,
                tint,
                mask,
                tint_rgb,
                faces,
                margin,
                padding,
                name,
                subtitle,
                manufacturer_logo,
                framerate,
                ffmpeg_threads,
                composite_workers,
                preset,
                source_hash,
                PROFILE_FACE_ZOOM,
            )
            timings["total"] = time.perf_counter() - total_started
            return finished, False, timings
        except Exception as exc:
            if attempt >= RENDER_ATTEMPTS:
                raise GenerationError(
                    f"render of {presentation.label} still failing after "
                    f"{RENDER_ATTEMPTS} attempts: {exc}"
                ) from exc
            print(
                f"    ! {presentation.label}: {exc}; re-rendering "
                f"(attempt {attempt}/{RENDER_ATTEMPTS})",
                flush=True,
            )
    raise AssertionError("unreachable")  # pragma: no cover


def _process_standard_card(
    presentation: expansion.Presentation,
    ffmpeg_threads: int = 1,
    composite_workers: int = 4,
    preset: Preset = Preset.DEFAULT,
    force: bool = False,
    no_video: bool = False,
) -> tuple[Path, bool, dict[str, float | None] | None]:
    """Render the standard card for the presentation (on the standard's
    mask): the presentation's background (faded toward its dominant
    color, no monochrome) carries the standard card mask, and the
    ``--half-body`` framing animates over it (the presentation's
    animation). The name and subtitle overlays are applied as usual; the
    manufacturer's logo sits at the top right, drawn in black (the white
    face would hide the white version); the NIKKE logo sits at the bottom
    right and the copyright at the bottom left, both in black.

    With *no_video* an animated standard card renders its first frame
    alone — its MP4 is skipped and the viewer reaped right after that
    frame — so the output, and the up-to-date check, cover the
    first-frame PNG.

    Everything is composited in memory (only the finished card is
    written). Returns ``(out_path, skipped, timings)`` like
    :func:`_process_full_art`."""
    total_started = time.perf_counter()
    exp = presentation.expansion
    entry = presentation.card

    faces = _logo_faces()
    if not FONT.is_file():
        raise GenerationError(f"font not found: {FONT}")
    if not FONT_NAME.is_file():
        raise GenerationError(f"font not found: {FONT_NAME}")
    name = entry.title
    subtitle = entry.subtitle
    # The character's manufacturer's logo (None when unknown): top
    # right, drawn in black.
    manufacturer_logo = _manufacturer_logo(entry.id)
    padding = card.padding(preset)
    margin = round(LOGO_PADDING_FACTOR * padding)
    framerate = preset.framerate

    size = card.run_size(preset)

    animated = presentation.animated and not no_video
    out_path = card.output_path(
        exp.name,
        entry.stem,
        presentation.name,
        presentation.rarity_index,
        "mp4" if animated else "png",
        preset,
    )
    source_hash = card.presentation_source_hash(presentation, preset)
    if not force:
        up_to_date = out_path.is_file() and _stored_hash(out_path) == source_hash
        if up_to_date and animated:
            first_frame_path = card.output_path(
                exp.name,
                entry.stem,
                presentation.name,
                presentation.rarity_index,
                "png",
                preset,
            )
            up_to_date = (
                first_frame_path.is_file()
                and _stored_hash(first_frame_path) == source_hash
            )
        if up_to_date:
            return out_path, True, None
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # The subtitle rectangle's tint is sampled from the unmasked fitted
    # background, so the mask's white does not wash the scene's color out.
    background = expansion.load_background(exp, presentation.background)
    background = _fit_background(background, size)
    sub_rect_color = _rect_tint(background)

    background = ImageOps.autocontrast(
        background.convert("RGB"),
        cutoff=(20, 0),
        preserve_tone=True,
    ).convert("RGBA")
    brightness = ImageStat.Stat(background).mean[0]

    background = _fade_to_dominant(
        background,
        factor=min(4.0 * max(brightness - 80, 0) / 255, 1.0),
    )

    base = _standard_layers(background)

    for attempt in range(1, RENDER_ATTEMPTS + 1):
        try:
            finished, timings = _render_standard(
                presentation,
                size,
                animated,
                base,
                sub_rect_color,
                name,
                subtitle,
                manufacturer_logo,
                faces,
                margin,
                padding,
                framerate,
                ffmpeg_threads,
                composite_workers,
                preset,
                source_hash,
            )
            timings["total"] = time.perf_counter() - total_started
            return finished, False, timings
        except Exception as exc:
            if attempt >= RENDER_ATTEMPTS:
                raise GenerationError(
                    f"render of {presentation.label} still failing after "
                    f"{RENDER_ATTEMPTS} attempts: {exc}"
                ) from exc
            print(
                f"    ! {presentation.label}: {exc}; re-rendering "
                f"(attempt {attempt}/{RENDER_ATTEMPTS})",
                flush=True,
            )
    raise AssertionError("unreachable")  # pragma: no cover
