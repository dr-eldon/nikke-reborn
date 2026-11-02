"""One card's frame output and its presentations' renders.

The shared pipeline that turns a presentation into a stream of frames
(:func:`_render_and_finish`) and the frame-output primitives it builds on
(:func:`_write_final_card`, :func:`_first_frame`, the face and photo-reel
compositing), plus the standard's and profile's presentations' renders
(:func:`_render_standard`, :func:`_render_profile`) and the three tiers'
per-presentation workers (:func:`_process_full_art`,
:func:`_process_standard_card`, :func:`_process_profile_card`).
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
    _logo_copyright_overlay,
    _name_layers,
    _rect_tint,
    _tint_layer,
)
from nikke_reborn.preset import Preset
from nikke_reborn.video import (
    DEFAULT_FRAMERATE,
    PIPE_BUFSIZE,
    _encode_mp4,
    _PipeDrain,
    _read_exact,
    _reap_viewer,
    _stream_composited,
    _stream_dual_composited,
)

# --- the profile presentation -------------------------------------------
# The profile cards render the character in two: the face framing (the
# viewer's ``--face`` at :data:`PROFILE_FACE_ZOOM`, shifted aside from the
# body so it is not occluded) animates over the background (a monochrome of
# its own dominant tint), under the dominant tint wash, as a monochrome of
# the same hue, and the body (the viewer's default framing) animates over
# the card mask (tinted at each pixel's own lightness, the white staying
# white) — the two framings are streamed in lockstep for the character
# (the same variant and animation). The name and subtitle overlays are
# applied as usual, and the logo sits at the top right instead of the
# bottom right. The card also carries a photo reel down its right edge: the
# first PROFILE_REEL_COUNT of PROFILE_REEL_ANIMATIONS the character has (per
# the viewer's ``--list-animations``, the ``fb`` variant's) become face
# stills — one at time 0 per animation (the viewer's ``--portrait 1``
# framing in a square viewport), taken once per card and reused for every
# frame — fewer squares, or none, when fewer animations match. Each still
# sits on a white background and is framed by a border of the background's
# dominant tint (PROFILE_REEL_BORDER of the side). Everything is composited
# in memory — no intermediate frame touches the disk; only the finished
# card is written (atomically).
# --- the standard presentation -------------------------------------------
# The ``Standard`` tier renders through its own pipeline: the presentation's
# background (in color, no monochrome, but faded a bit toward its dominant
# color) carries the standard card mask (``STANDARD_MASK_PATH``) and the
# character's upper body (the viewer's ``--half-body`` flag) animates over
# it. The name and subtitle overlays are applied as usual; the
# manufacturer's logo sits at the top right (its corner inset by
# ``padding * 1.5``, in black), the NIKKE logo at the bottom right and the
# copyright at the bottom left, both in black.
#: The ``--face`` zoom that renders the face framing composited over the
#: profile card's background, under its tint wash (ahead of the body).
PROFILE_FACE_ZOOM = 2
#: The face framing's vertical centre, as a fraction of the frame height
#: (0.1). :func:`_face_offset` treats the face as a square of side
#: ``height * PROFILE_FACE_CENTER_Y * :data:`PROFILE_FACE_ZOOM`` centred at that height
#: when deciding which side leaves its footprint least occluded by the body.
PROFILE_FACE_CENTER_Y = 0.1
#: Horizontal shifts (px) that move the face framing aside from the centered
#: body so it is not occluded by the body: the face is rendered
#: :data:`PROFILE_FACE_OFFSET_LEFT` px to the left or
#: :data:`PROFILE_FACE_OFFSET_RIGHT` px to the right (whichever leaves its
#: footprint least occluded by the body, see :func:`_face_offset`).
PROFILE_FACE_OFFSET_LEFT = 500
PROFILE_FACE_OFFSET_RIGHT = 420
#: The profile card's "photo reel": the face stills stacked down the card's
#: right edge. The reel holds the first PROFILE_REEL_COUNT of
#: PROFILE_REEL_ANIMATIONS the character has (per the viewer's
#: ``--list-animations``); fewer stills — or none at all — when fewer of
#: the list match. Each still is the time 0 frame of its animation (the
#: viewer's ``--portrait 1`` framing in a square viewport of side
#: ``frame_width * PROFILE_REEL_SIDE``, see :func:`_photo_reel`), taken
#: once per card and reused for every frame, framed by a border of
#: ``side * PROFILE_REEL_BORDER`` filled with the background's dominant
#: tint: the framed squares run down the right edge, inset by
#: ``padding * PROFILE_REEL_MARGIN``, the first square's top edge at
#: ``frame_height * PROFILE_REEL_TOP`` and the card's padding of gap
#: between the squares.
PROFILE_REEL_SIDE = 1 / 7
#: The first photo-reel square's top edge, as a fraction of the frame
PROFILE_REEL_TOP = 3 / 7
#: The photo reel's inset from the card's right edge, as a multiple of
#: the card's padding (padding * 1.5).
PROFILE_REEL_MARGIN = 1.5
#: The photo-reel border's width, as a fraction of the photo's side
#: (side * 0.005): a frame of the background's dominant tint
#: (PROFILE_REEL_BORDER_ALPHA) around each still, so the positioned block
#: is the framed still (side + 2 * the border across).
PROFILE_REEL_BORDER = 0.005
#: The photo-reel border's opacity (0.5): the tint frame is
#: semi-transparent, so the card art behind it shows through.
PROFILE_REEL_BORDER_ALPHA = 0.8

#: ``nikke-viewer`` writes its frames from multiple threads and can
#: occasionally leave a truncated file behind while still exiting with
#: status 0; a card whose render cannot be processed is re-run up to this
#: many times before giving up.
RENDER_ATTEMPTS = 3


def _presentation_flags(presentation: expansion.Presentation) -> list[str]:
    """The presentation's viewer flags (the character's ``--variant`` —
    ``aim``, ``cover`` or ``sc``; the ``--animation`` — the render's
    animation; the ``--time`` — 0 stills the render): the viewer's
    defaults when the presentation names none of them (the ``fb`` variant
    is the viewer's default variant)."""
    flags: list[str] = []
    if presentation.variant is not None:
        flags += ["--variant", presentation.variant]
    if presentation.animation is not None:
        flags += ["--animation", presentation.animation]
    if presentation.time is not None:
        flags += ["--time", str(presentation.time)]
    return flags


def _viewer_args(
    size: tuple[int, int], char_id: str, *flags: str
) -> list[str]:
    """The viewer's command for one stream: the *flags* (the framing and
    the presentation's terms), the run's size (the ``--width``/
    ``--height``) and the character's id — the viewer's ``--stdout`` emits
    raw RGBA frames at that size."""
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


def _render_and_finish(
    presentation: expansion.Presentation,
    size: tuple[int, int],
    animated: bool,
    base: Image.Image,
    logo: Image.Image,
    margin: int,
    padding: int,
    copyright_color: tuple[int, int, int, int],
    framerate: int,
    ffmpeg_threads: int,
    composite_workers: int,
    preset: Preset,
    source_hash: str,
    half_body: bool = False,
) -> tuple[Path, dict[str, float | None]]:
    """Render the presentation via the viewer's ``--stdout`` raw stream and
    write the final PNG, or the MP4 alongside its first frame as a PNG.

    The single framing is the presentation's (the ``--half-body`` flag
    when *half_body* — the upper body, head to waist — or the viewer's
    default framing, the character's variant and animation). Nothing
    intermediate touches the disk: the viewer's raw RGBA frames are piped
    straight into the in-memory compositing and (for animations) the
    ffmpeg encode. Only the finished card is written (atomically). A
    failure at any stage surfaces as a :class:`GenerationError` so the
    caller can re-render the card from scratch.

    Returns the finished card's path and the stage timings in seconds (see
    :func:`_write_final_card`, which performs the write and the reap). A raw
    frame is far larger than the pipe buffer, so the viewer blocks on
    write until the reader drains: under load ``render`` therefore
    reflects the slowest downstream stage (usually the encode) as much as
    the viewer itself.
    """
    # The logo and copyright line sit on top of the art, not under it:
    # pre-stamp them onto a transparent layer and let _stream_composited
    # apply it to each frame after the art is composited over the
    # background.
    overlay, overlay_pos = _logo_copyright_overlay(
        size, logo, margin, padding, copyright_color
    )
    composite_time: list[float] = [0.0]
    stream_end: list[float] = [0.0]

    # Spawn the viewer streaming raw RGBA frames to stdout (no intermediate
    # files). --half-body, when set, frames the upper body (head to waist)
    # instead of the viewer's default framing. The viewer renders at the
    # run's final size (*size*); the save's viewport stays the native
    # reference. stderr is drained in a thread so it never blocks the
    # viewer.
    render_started = time.perf_counter()
    viewer_args = _viewer_args(
        size,
        presentation.card.id,
        *([ "--half-body"] if half_body else []),
        *_presentation_flags(presentation),
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
        overlay,
        overlay_pos,
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
    thread.

    Started with the first consumed frame (mid-encode, see
    :func:`_write_final_card`), so the PNG's save overlaps the encode
    instead of following it. *join* waits for the write and re-raises its
    failure — a finished card only exists in its complete form (both the
    mp4 and the sidecar), and a failed write still surfaces as the card's
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
    """Write a composited frame stream (raw RGBA bytes) to the final card.

    An animation is encoded to an MP4 alongside its first frame (the same
    composited frame, so it matches the mp4's opening frame exactly); a
    fixed-time card is written as a single PNG. For animations the
    first-frame PNG is written in a background thread that starts with the
    first consumed frame, so the sidecar's save overlaps the encode instead
    of following it. *composited* is closed (so the viewer stream(s) are
    reaped) and the stage timings (in seconds) are returned: ``render``
    (spawn until the frame stream is fully delivered), ``composite`` (the
    per-frame Pillow work — decode, blend, stamps — summed across the worker
    threads) and ``encode`` (the ffmpeg wall time for animations, the PNG
    write for static cards). The stages overlap — the encode consumes frames
    while the viewer still renders, the compositing runs in its own threads,
    and the first-frame sidecar runs in its own thread — so the numbers are
    per-stage costs, not a sequential partition.
    """
    out_path = card.output_path(
        presentation.expansion.name,
        presentation.card.stem,
        presentation.name,
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
            # A single frame: consume the stream (the frame's image landed
            # in first_frame while it was composited) and write it.
            next(composited, None)
            if not first_frame:
                raise GenerationError(
                    f"{VIEWER} produced no frame for {presentation.label}"
                )
            encode_started = time.perf_counter()
            _save_atomic(
                first_frame[0].convert("RGB"), out_path, source_hash
            )
            encode_time = time.perf_counter() - encode_started
    finally:
        # Stop consuming and make sure the viewer stream is reaped (the
        # compositor's ``finally`` runs, reaping the viewer(s) and checking
        # their exit).
        composited.close()
    # Measured to stream EOF (not to the reap, which happens after the
    # encode and the save), so the number covers the frame delivery only.
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
    *viewer_flags* — one raw RGBA frame read from the ``--stdout`` stream.
    The viewer is asked for exactly *size* (the run's final size, which
    may differ from the save's viewport — the flags are passed here so the
    stream always matches the read below); it is reaped, and for an
    animation only the opening frame is needed."""
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
        # One frame is all we need; stop consuming and reap the viewer, which
        # may still be mid-stream for animations.
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
    """The face framing's ``--offset-x``: :data:`PROFILE_FACE_OFFSET_LEFT` px to
    the left or :data:`PROFILE_FACE_OFFSET_RIGHT` px to the right (both
    native-px — the card's viewport — scaled by the output preset's
    scale to the run's final size, since the viewer's ``--offset-x`` is
    screen px), whichever
    leaves the face's footprint least occluded by the body, so the face
    sits clear rather than behind it.

    The face's centre always sits at :data:`PROFILE_FACE_CENTER_Y` of the frame
    height, so the face is treated as a square of side
    ``height * PROFILE_FACE_CENTER_Y * :data:`PROFILE_FACE_ZOOM``. Each candidate
    footprint — the left at the card centre minus the left offset, the right at
    the card centre plus the right offset — is measured against the body's
    opaque pixels and the face is sent to the emptier one (fewer body pixels
    behind it). A bodyless frame leaves the face centered (0). The body is
    measured in the presentation's own framing (its default framing — the
    body stream's — with the presentation's variant and animation).
    """
    width, height = size
    body = _first_frame(
        size, presentation.card.id, *_presentation_flags(presentation)
    )
    # The face's footprint: a square centred at the face's fixed vertical
    # centre, one for each candidate horizontal position (left / right).
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
    # Both footprints empty means the body sits *between* them, so the face
    # still shifts (a tie defaults to the left); never leave it centered on
    # top of the body.
    return -left_offset if left < right else right_offset


def _reel_animations(char_id: str) -> list[str]:
    """The photo reel's animations (see
    :func:`nikke_reborn.expansion.reel_animations`): the first
    PROFILE_REEL_COUNT of PROFILE_REEL_ANIMATIONS the character has, asked
    of the viewer once per process (the render's profile passes reuse the
    selection's lists)."""
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
    viewer's ``--portrait 1`` framing (the face exactly inside the
    viewport bounds) in a square viewport of side
    ``frame_width * PROFILE_REEL_SIDE`` (``--time 0`` and
    ``--animation``; :func:`_first_frame` passes the square size to the
    viewer) and flattened onto a white
    background (the viewer's frames are transparent where the character
    does not cover): the stills are taken once per card and reused for
    every frame. Each is framed by a border of
    ``side * PROFILE_REEL_BORDER`` filled with *tint_rgb* (the
    background's dominant tint, at PROFILE_REEL_BORDER_ALPHA) — the
    positioned block is the framed still. The blocks run down the right
    edge, inset by ``*padding* * PROFILE_REEL_MARGIN``, the first block's
    top edge at ``frame_height * PROFILE_REEL_TOP`` and a gap of *padding*
    between them. Empty (no reel) when the character has none of
    PROFILE_REEL_ANIMATIONS.
    """
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
            "1",
            "--time",
            "0",
            "--animation",
            animation,
        )
        # The still's background: the viewer's frames are transparent where
        # the character does not cover, so flatten them to white.
        white = Image.new("RGBA", still.size, (255, 255, 255, 255))
        white.paste(still, (0, 0), still)
        still = white
        # The border (PROFILE_REEL_BORDER of the photo's side, the
        # background's dominant tint at PROFILE_REEL_BORDER_ALPHA) frames
        # the still.
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
    logo: Image.Image,
    margin: int,
    padding: int,
    copyright_color: tuple[int, int, int, int],
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
    ``<card>_<presentation>.<suffix>``): the ``--face <face_zoom>``
    framing animates (as a monochrome of the tint's hue, shifted aside from
    the body) over the background, under the tint wash, and the body (the
    viewer's default framing, the presentation's variant and animation)
    animates over the mask, both streamed for the character so the two stay
    in lockstep. The name and subtitle overlays are applied as usual (with
    the character's manufacturer's logo above the name's bar,
    *manufacturer_logo*); the logo sits at the top right. The card's photo
    reel (the face stills down the right edge, :func:`_photo_reel`) is
    composited onto every frame as well.

    Like :func:`_render_and_finish`, nothing intermediate touches the disk —
    the two raw RGBA streams are piped straight into the in-memory
    compositing and (for animations) the ffmpeg encode; only the finished
    card is written (atomically, as ``<card>_<stem>.<suffix>``). Returns the
    finished card's path and the stage timings (see
    :func:`_write_final_card`).
    """
    # The logo and copyright line sit on top of the art: pre-stamp them onto
    # a transparent layer and let the compositor apply it to each frame.
    # The profile card's logo sits at the top right instead of the bottom
    # right.
    overlay, overlay_pos = _logo_copyright_overlay(
        size, logo, margin, padding, copyright_color, logo_top=True
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

    # The face is shifted to the side the body leaves most room on (measured
    # from the body's first frame), so it is not occluded by the centered
    # body.
    face_offset = _face_offset(presentation, size, preset)

    # The photo reel (the face stills down the right edge): the stills are
    # taken once — one frame at time 0 per animation — and reused for
    # every frame of the card.
    reel = _photo_reel(presentation, size, padding, tint_rgb)

    # Spawn the two viewers streaming raw RGBA frames to stdout (no
    # intermediate files): the face framing (over the background, under the
    # tint wash, shifted aside from the body) and the body (the viewer's
    # default framing). stderr is drained in a thread so it never blocks a
    # viewer.
    render_started = time.perf_counter()
    face_args = _viewer_args(
        size,
        presentation.card.id,
        "--face",
        str(face_zoom),
        "--offset-x",
        str(face_offset),
        *_presentation_flags(presentation),
    )
    body_args = _viewer_args(
        size,
        presentation.card.id,
        *_presentation_flags(presentation),
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
        overlay,
        overlay_pos,
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
    logo: Image.Image,
    margin: int,
    padding: int,
    copyright_color: tuple[int, int, int, int],
    framerate: int,
    ffmpeg_threads: int,
    composite_workers: int,
    preset: Preset,
    source_hash: str,
) -> tuple[Path, dict[str, float | None]]:
    """Render the standard card (a presentation, written out as
    ``<card>_<presentation>.<suffix>``): the presentation's
    *background* (faded toward its dominant color, no monochrome) carries
    the standard card mask
    (:data:`STANDARD_MASK_PATH`, already composited into *base*), and the
    character's upper body (the viewer's ``--half-body`` flag, the
    presentation's animation) animates over it. The name and subtitle
    overlays are applied as usual, like the profile cards; the
    manufacturer's logo (*manufacturer_logo*) sits at the top right, its
    corner inset by ``padding * 1.5`` and drawn in black (the white face
    would hide the white version); the NIKKE logo sits at the bottom right
    and the copyright at the bottom left, both in black.

    Like :func:`_render_and_finish` and :func:`_render_profile`, nothing
    intermediate touches the disk — the raw RGBA stream is piped straight
    into the in-memory compositing and (for animations) the ffmpeg encode;
    only the finished card is written (atomically, as
    ``<card>_<stem>.<suffix>``). Returns the finished card's path and the
    stage timings (see :func:`_write_final_card`).
    """
    # The logo, the copyright line and the manufacturer's logo sit on top of
    # the art: pre-stamp them onto a transparent layer and let the
    # compositor apply them to each frame. The NIKKE logo sits at the bottom
    # right (the copyright at the bottom left), both in black; the
    # manufacturer's logo sits at the top right, its corner inset by
    # padding * 1.5, in black (the standard card's white face would hide the
    # white version).
    overlay, overlay_pos = _logo_copyright_overlay(
        size, logo, margin, padding, copyright_color
    )
    if manufacturer_logo is not None:
        inset = round(padding * 1.5)
        mark_w = round(size[0] * MANUFACTURER_LOGO_WIDTH)
        mark_h = round(mark_w * manufacturer_logo.height / manufacturer_logo.width)
        mark = manufacturer_logo.resize((mark_w, mark_h), Image.Resampling.LANCZOS)
        mark = _tint_layer(mark.getchannel("A"), (0, 0, 0), 1.0)
        # Rebuild on a full frame so both the (already cropped) logo/copyright
        # overlay and the new top-right mark land at their card positions,
        # then crop back to the combined ink.
        full = Image.new("RGBA", size, (0, 0, 0, 0))
        full.alpha_composite(overlay, overlay_pos)
        full.alpha_composite(mark, (size[0] - inset - mark_w, inset))
        box = full.getbbox()
        assert box is not None, "the standard card's overlay is empty"
        overlay, overlay_pos = full.crop(box), (box[0], box[1])
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

    # Spawn the viewer streaming raw RGBA frames to stdout (no intermediate
    # files): the half body over the mask. --half-body frames the upper body
    # (head to waist). stderr is drained in a thread so it never blocks the
    # viewer.
    render_started = time.perf_counter()
    viewer_args = _viewer_args(
        size,
        presentation.card.id,
        "--half-body",
        *_presentation_flags(presentation),
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
        overlay,
        overlay_pos,
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
    """Render, composite and encode one presentation of the full-art tier
    (the ``Classic``, ``Special``, ``Exotic`` and ``Goddess`` presentations,
    no mask): the presentation's background (fitted to the frame,
    autocontrasted and dark-faded toward its dominant color — the solid
    black for the goddess presentation) carries the white NIKKE logo and
    the copyright line (white); the card name is not drawn on the full-art
    cards. The framing is the presentation's (the ``--half-body`` flag for
    the classic, special and exotic; the viewer's default framing for the
    goddess's ``sc`` variant).

    With *no_video* (``--no-video``) an animated presentation renders its
    first frame alone — its MP4 is skipped and the viewer reaped right
    after that frame — so the output, and the up-to-date check, cover the
    first-frame PNG.

    Returns ``(out_path, skipped, timings)``; *skipped* is True when the
    output already exists and the presentation hash it embeds matches the
    current one (nothing was re-rendered), in which case *timings* is None;
    otherwise it is the stage-timing dict from :func:`_render_and_finish`
    plus ``total``, the card's overall wall-clock seconds.
    """
    total_started = time.perf_counter()
    exp = presentation.expansion
    entry = presentation.card

    logo_path = LOGO_PATHS[False]
    if not logo_path.is_file():
        raise GenerationError(f"logo not found: {logo_path}")
    logo = Image.open(logo_path).convert("RGBA")
    if not FONT.is_file():
        raise GenerationError(f"font not found: {FONT}")
    # The full-art cards never carry the card name (the profile and
    # standard cards render the title and subtitle).
    # The card's padding is native-px (its viewport); the effective
    # padding at the run's final size drives the lettering, the logo
    # placement, the reel insets and the like.
    padding = card.padding(preset)
    margin = round(LOGO_PADDING_FACTOR * padding)
    copyright_color = (255, 255, 255, 255)
    framerate = DEFAULT_FRAMERATE

    # The run's final size: the card's viewport at the run's scale (even
    # dims for the yuv420p encode). The whole pipeline — the viewer, the
    # compositing and the finished card — runs at this size, so no frame is
    # ever resampled on the way out.
    size = card.run_size(preset)

    # A presentation without a `time` renders an animation (mp4) plus its
    # first frame (png); one with a `time` renders a single frame (png).
    # With --no-video an animation renders its first frame (png) alone:
    # the mp4 is skipped and the viewer reaped right after that frame.
    animated = presentation.animated and not no_video
    out_path = card.output_path(
        exp.name, entry.stem, presentation.name, "mp4" if animated else "png", preset
    )
    source_hash = card.presentation_source_hash(presentation, preset)
    if not force:
        up_to_date = out_path.is_file() and _stored_hash(out_path) == source_hash
        if up_to_date and animated:
            # The animation's first frame is kept alongside it; a missing or
            # stale copy forces the card to be re-rendered.
            first_frame_path = card.output_path(
                exp.name, entry.stem, presentation.name, "png", preset
            )
            up_to_date = (
                first_frame_path.is_file()
                and _stored_hash(first_frame_path) == source_hash
            )
        if up_to_date:
            # The presentation is unchanged since the card was written: skip
            # the render
            return out_path, True, None
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # The full-art base: the presentation's background fitted to the frame,
    # autocontrasted and dark-faded toward its dominant color (the
    # standard's treatment minus the mask) — or the solid black for the
    # goddess presentation (which composites on no background).
    if presentation.background == "black":
        base = Image.new("RGBA", size, (0, 0, 0, 255))
    else:
        background = expansion.load_background(exp, presentation.background)
        background = _fit_background(background, size)
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
        base = background

    # The GPU is shared with other tenants, so failures here can be
    # transient (render error, truncated frame stream, encode error); the
    # card is re-rendered from scratch up to RENDER_ATTEMPTS times before
    # giving up. Nothing intermediate is written to disk in between.
    for attempt in range(1, RENDER_ATTEMPTS + 1):
        try:
            finished, timings = _render_and_finish(
                presentation,
                size,
                animated,
                base,
                logo,
                margin,
                padding,
                copyright_color,
                framerate,
                ffmpeg_threads,
                composite_workers,
                preset,
                source_hash,
                half_body=presentation.half_body,
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
    """Render the profile card for the presentation (one of the ``Classic``,
    ``Idle``, ``Cover`` and ``Aim`` presentations, on the profile's mask):
    the ``--face`` framing animates (as a monochrome of the tint's hue) over
    the background, under its dominant tint wash, and the body (the viewer's
    default framing, the presentation's variant and animation) animates over
    the card mask (both streamed in lockstep for the character). The name
    and subtitle overlays are applied as usual, like the other rarities; the
    logo sits at the top right. The card's photo reel (the face stills down
    the right edge, :func:`_photo_reel`) is composited onto every frame.

    With *no_video* (``--no-video``) an animated profile card renders its
    first frame alone — its MP4 is skipped and the viewers reaped right
    after that frame — so the output, and the up-to-date check, cover the
    first-frame PNG.

    Everything is composited in memory — the viewer's raw frames stream
    straight into the pipeline and nothing intermediate touches the disk
    (only the finished card is written). Returns ``(out_path, skipped,
    timings)`` like :func:`_process_full_art` (written out as
    ``<card>_<presentation>.<suffix>``).
    """
    total_started = time.perf_counter()
    exp = presentation.expansion
    entry = presentation.card

    # The profile presentation always carries the black logo and black
    # copyright — the profile card's white mask would wash out the white
    # versions — while the name stays white, as the other rarities.
    logo_path = LOGO_PATHS[True]
    if not logo_path.is_file():
        raise GenerationError(f"logo not found: {logo_path}")
    logo = Image.open(logo_path).convert("RGBA")
    if not FONT.is_file():
        raise GenerationError(f"font not found: {FONT}")
    if not FONT_NAME.is_file():
        raise GenerationError(f"font not found: {FONT_NAME}")
    # The profile presentation carries the card name, as the other
    # presentations do.
    name = entry.title
    subtitle = entry.subtitle
    # The character's manufacturer's logo (tinted to the title's
    # background; None when the character or its manufacturer is
    # unknown): it sits above the name's bar.
    manufacturer_logo = _manufacturer_logo(entry.id)
    # The card's padding is native-px (its viewport); the effective
    # padding at the run's final size drives the lettering, the logo
    # placement, the reel insets and the like.
    padding = card.padding(preset)
    margin = round(LOGO_PADDING_FACTOR * padding)
    copyright_color = (0, 0, 0, 255)
    framerate = DEFAULT_FRAMERATE

    # The run's final size: the card's viewport at the run's scale (even
    # dims for the yuv420p encode). The whole pipeline — the viewer, the
    # compositing and the finished card — runs at this size, so no frame is
    # ever resampled on the way out.
    size = card.run_size(preset)

    # A presentation without a `time` renders an animation (mp4) plus its
    # first frame (png); one with a `time` renders a single frame (png).
    # With --no-video an animation renders its first frame (png) alone:
    # the mp4 is skipped and the viewer reaped right after that frame.
    animated = presentation.animated and not no_video
    out_path = card.output_path(
        exp.name, entry.stem, presentation.name, "mp4" if animated else "png", preset
    )
    source_hash = card.presentation_source_hash(presentation, preset)
    if not force:
        up_to_date = out_path.is_file() and _stored_hash(out_path) == source_hash
        if up_to_date and animated:
            # The animation's first frame is kept alongside it; a missing or
            # stale copy forces the card to be re-rendered.
            first_frame_path = card.output_path(
                exp.name, entry.stem, presentation.name, "png", preset
            )
            up_to_date = (
                first_frame_path.is_file()
                and _stored_hash(first_frame_path) == source_hash
            )
        if up_to_date:
            # The presentation and the mask are unchanged since the card was
            # written: skip the render.
            return out_path, True, None
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # The static layers (the fitted background, the dominant tint, the mask)
    # are prepared once, ahead of the render (a failure at any stage
    # re-renders from scratch, up to RENDER_ATTEMPTS times; the two viewer
    # framings stream directly, so nothing intermediate is written to disk in
    # between).
    background = expansion.load_background(exp, presentation.background)
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
                logo,
                margin,
                padding,
                copyright_color,
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
    """Render the standard card for the presentation (one of the
    ``Classic``, ``Special`` and ``Exotic`` presentations, on the
    standard's mask): the presentation's ``background`` (faded toward its
    dominant color, no monochrome) carries the standard card mask
    (:data:`STANDARD_MASK_PATH`), and the ``--half-body`` framing animates
    over it (the presentation's animation — the reel's pick for the special,
    ``action`` for the exotic, the viewer's default for the classic). The
    name and subtitle overlays are applied as usual, like the profile cards;
    the manufacturer's logo sits at the top right, its corner inset by
    ``padding * 1.5`` and drawn in black (the white face would hide the
    white version); the NIKKE logo sits at the bottom right and the
    copyright at the bottom left, both in black.

    With *no_video* (``--no-video``) an animated standard card renders its
    first frame alone — its MP4 is skipped and the viewer reaped right
    after that frame — so the output, and the up-to-date check, cover the
    first-frame PNG.

    Everything is composited in memory — the viewer's raw frames stream
    straight into the pipeline and nothing intermediate touches the disk
    (only the finished card is written). Returns ``(out_path, skipped,
    timings)`` like :func:`_process_full_art` (written out as
    ``<card>_<presentation>.<suffix>``).
    """
    total_started = time.perf_counter()
    exp = presentation.expansion
    entry = presentation.card

    # The standard presentation always carries the black logo and black
    # copyright — the standard card's white face would wash out the white
    # versions — while the name stays white, as the profile cards.
    logo_path = LOGO_PATHS[True]
    if not logo_path.is_file():
        raise GenerationError(f"logo not found: {logo_path}")
    logo = Image.open(logo_path).convert("RGBA")
    if not FONT.is_file():
        raise GenerationError(f"font not found: {FONT}")
    if not FONT_NAME.is_file():
        raise GenerationError(f"font not found: {FONT_NAME}")
    # The standard presentation carries the card name, as the profile cards
    # do.
    name = entry.title
    subtitle = entry.subtitle
    # The character's manufacturer's logo (None when the character or its
    # manufacturer is unknown): it sits at the top right, its corner inset
    # by padding * 1.5, drawn in black.
    manufacturer_logo = _manufacturer_logo(entry.id)
    # The card's padding is native-px (its viewport); the effective
    # padding at the run's final size drives the lettering, the logo
    # placement, the reel insets and the like.
    padding = card.padding(preset)
    margin = round(LOGO_PADDING_FACTOR * padding)
    copyright_color = (0, 0, 0, 255)
    framerate = DEFAULT_FRAMERATE

    # The run's final size: the card's viewport at the run's scale (even
    # dims for the yuv420p encode). The whole pipeline — the viewer, the
    # compositing and the finished card — runs at this size, so no frame is
    # ever resampled on the way out.
    size = card.run_size(preset)

    # A presentation without a `time` renders an animation (mp4) plus its
    # first frame (png); one with a `time` renders a single frame (png).
    # With --no-video an animation renders its first frame (png) alone:
    # the mp4 is skipped and the viewer reaped right after that frame.
    animated = presentation.animated and not no_video
    out_path = card.output_path(
        exp.name, entry.stem, presentation.name, "mp4" if animated else "png", preset
    )
    source_hash = card.presentation_source_hash(presentation, preset)
    if not force:
        up_to_date = out_path.is_file() and _stored_hash(out_path) == source_hash
        if up_to_date and animated:
            # The animation's first frame is kept alongside it; a missing or
            # stale copy forces the card to be re-rendered.
            first_frame_path = card.output_path(
                exp.name, entry.stem, presentation.name, "png", preset
            )
            up_to_date = (
                first_frame_path.is_file()
                and _stored_hash(first_frame_path) == source_hash
            )
        if up_to_date:
            # The presentation and the mask are unchanged since the card was
            # written: skip the render.
            return out_path, True, None
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # The static base (the fitted background, faded toward its dominant
    # color, carrying the standard card mask) is prepared once, ahead of the
    # render (a failure at any stage re-renders from scratch, up to
    # RENDER_ATTEMPTS times; the viewer framing streams directly, so nothing
    # intermediate is written to disk in between). The subtitle rectangle's
    # tint is sampled from the unmasked fitted background, so the mask's
    # white does not wash the scene's color out.
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
                logo,
                margin,
                padding,
                copyright_color,
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
