"""Stream the viewer's frames and encode the MP4.

``nikke-viewer --stdout`` streams its frames as raw RGBA on stdout (no
intermediate files); the streaming side reads them in order (or in
lockstep, for the profile card's two streams) and reaps the viewer once
the stream ends or is abandoned — its stderr is drained in the
background so it can never block on a full pipe. The encoding side feeds
the composited frames to ffmpeg through a pipe and embeds the source
hash as a container tag."""

from __future__ import annotations

import io
import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable, Generator, Iterator
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import IO

from PIL import Image

from nikke_reborn.config import SOURCE_HASH_KEY, VIEWER
from nikke_reborn.error import GenerationError
from nikke_reborn.image import _composite_frame, _monochrome
from nikke_reborn.lettering import _apply_name, _NameLayers

ENCODER = "ffmpeg"

#: Wide pipe buffer for the frame streams (the default would mean a
#: syscall per kernel quantum).
PIPE_BUFSIZE = 1 << 20

DEFAULT_FRAMERATE = 60

#: Brightness scale for the monochrome face: below 1.0 it sits quieter
#: against the tinted background.
PROFILE_FACE_BRIGHTNESS = 0.7

#: The H.264 quality settings for the MP4 output. The x264 preset is
#: chosen per run (:mod:`nikke_reborn.preset`); the frames arrive at the
#: run's output size, so the encoder never rescales.
FFMPEG_QUALITY_ARGS = (
    "-crf",
    "16",
    "-pix_fmt",
    "yuv420p",
    "-movflags",
    "+faststart",
)


def _read_exact(stream: IO[bytes], n: int) -> bytes:
    """Read exactly *n* bytes from *stream* (fewer only at
    end-of-stream): a buffered read may return partial chunks, so read
    to completion."""
    chunks: list[bytes] = []
    remaining = n
    while remaining > 0:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    if len(chunks) == 1:
        return chunks[0]  # a buffered read gathers the whole frame at once;
    return b"".join(chunks)  # joining would just copy it for no reason


class _PipeDrain:
    """Drain a pipe into a bounded in-memory buffer from a daemon
    thread: keeps the writer (the viewer's stderr) from blocking on a
    full pipe; only the tail is kept, for error reporting."""

    def __init__(self, stream: io.BufferedReader, cap: int = 1 << 20) -> None:
        self._stream = stream
        self._cap = cap
        self._buf = bytearray()
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            while True:
                chunk = self._stream.read1(65536)
                if not chunk:
                    break
                with self._lock:
                    self._buf.extend(chunk)
                    if len(self._buf) > self._cap:
                        del self._buf[: len(self._buf) - self._cap]
        except OSError, ValueError:
            pass

    def text(self) -> str:
        with self._lock:
            return bytes(self._buf).decode(errors="replace").strip()

    def join(self, timeout: float | None = None) -> None:
        self._thread.join(timeout)


def _reap_viewer(
    viewer: subprocess.Popen,
    drain: _PipeDrain,
    *,
    clean_exit_expected: bool,
) -> None:
    """Wait for *viewer* to exit, draining its stderr, and raise on
    failure.

    When the frame stream was fully read (*clean_exit_expected*) a grace
    period is given before killing a hung process, and a non-zero exit
    is a :class:`GenerationError`; when the stream was abandoned early
    the viewer may be blocked writing to a full pipe and is killed — its
    exit code is not consulted (the caller already has the real
    exception)."""
    if clean_exit_expected:
        try:
            viewer.wait(timeout=60)
        except subprocess.TimeoutExpired:
            viewer.kill()
            viewer.wait()
    else:
        if viewer.poll() is None:
            viewer.kill()
        viewer.wait()
    drain.join(timeout=5)
    if clean_exit_expected and viewer.returncode != 0:
        detail = drain.text()
        detail = f" ({detail[-500:]})" if detail else ""
        raise GenerationError(f"{VIEWER} failed (exit {viewer.returncode}){detail}")


def _stream_composited(
    viewer: subprocess.Popen,
    drain: _PipeDrain,
    label: str,
    size: tuple[int, int],
    base: Image.Image,
    make_overlay: Callable[[Image.Image], tuple[Image.Image, tuple[int, int]]],
    composite_workers: int,
    first_frame: list[Image.Image],
    composite_time: list[float],
    stream_end: list[float],
    parts: _NameLayers | None = None,
) -> Generator[Image.Image]:
    """Composite the viewer's raw RGBA stdout frames and yield them in
    order: each frame is decoded and composited over *base*, the overlay
    — the caller's *make_overlay* applied to the first frame's art (the
    stamps' faces are chosen from that frame's luma) — stamped on top of
    every frame, and the name stack (*parts*, when any) applied, in a
    sliding window of *composite_workers* threads (Pillow releases the
    GIL in its raster ops, so the reader stays ahead of the encode).
    Frame 0 is read and composited on the calling thread (the overlay
    is derived from it, so it cannot race the window's workers); at most
    ~2x the worker count of further frames are in memory at once. The
    first composited frame is appended to *first_frame*; when the stream
    ends (or the consumer stops) the viewer is reaped and a non-zero
    exit surfaced. *composite_time* and *stream_end* accumulate the
    composite wall seconds and the moment the stream reaches
    end-of-file."""
    width, height = size
    frame_bytes = width * height * 4
    assert viewer.stdout is not None
    stdout = viewer.stdout
    # A fully opaque base takes the GIL-releasing Image.composite path
    # (see _composite_frame); the base's alpha is restored onto the
    # result so the downstream stamps see the same alpha either way.
    # Computed once per card (None when the base is not fully opaque).
    base_alpha = base.getchannel("A")
    if base_alpha.getextrema() != (255, 255):
        base_alpha = None

    def to_art(data: bytes) -> Image.Image:
        frame = Image.frombytes("RGBA", (width, height), data)
        return _composite_frame(frame, base, base_alpha)

    def stamp(
        art: Image.Image, overlay: Image.Image, overlay_pos: tuple[int, int]
    ) -> Image.Image:
        art.alpha_composite(overlay, overlay_pos)
        return _apply_name(art, parts) if parts is not None else art

    time_lock = threading.Lock()
    workers = max(1, composite_workers)
    eof = False
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            pending: deque[Future[Image.Image]] = deque()

            # Frame 0, on the calling thread: make_overlay picks the
            # overlay's faces from its luma, and the window's workers
            # stamp the overlay, so it must not race them.
            data = _read_exact(stdout, frame_bytes)
            if not data:
                eof = True
                stream_end[0] = time.perf_counter()
                raise GenerationError(f"{VIEWER} produced no frames for {label}")
            if len(data) != frame_bytes:
                raise GenerationError(
                    f"{VIEWER} stream for {label} truncated: "
                    f"{len(data)} of {frame_bytes} bytes"
                )
            art = to_art(data)
            overlay, overlay_pos = make_overlay(art)
            started = time.perf_counter()
            first = stamp(art, overlay, overlay_pos)
            with time_lock:
                composite_time[0] += time.perf_counter() - started
            # Keep the first composited frame: for animations it is
            # written alongside the mp4, for a static card it is the
            # card itself.
            first_frame.append(first)

            def composite(data: bytes) -> Image.Image:
                started = time.perf_counter()
                result = stamp(to_art(data), overlay, overlay_pos)
                with time_lock:
                    composite_time[0] += time.perf_counter() - started
                return result

            def submit_next() -> None:
                nonlocal eof
                data = _read_exact(stdout, frame_bytes)
                if not data:
                    eof = True  # end of stream
                    stream_end[0] = time.perf_counter()
                    return
                if len(data) != frame_bytes:
                    raise GenerationError(
                        f"{VIEWER} stream for {label} truncated: "
                        f"{len(data)} of {frame_bytes} bytes"
                    )
                pending.append(pool.submit(composite, data))

            yield first

            # Prime the window.
            for _ in range(workers):
                submit_next()

            while pending:
                future = pending.popleft()
                try:
                    frame = future.result()
                except Exception:
                    for pending_future in pending:
                        pending_future.cancel()
                    raise
                # Keep the window full (read ahead) before handing off.
                submit_next()
                yield frame
    finally:
        _reap_viewer(viewer, drain, clean_exit_expected=eof)


def _stream_dual_composited(
    face_viewer: subprocess.Popen,
    face_drain: _PipeDrain,
    body_viewer: subprocess.Popen,
    body_drain: _PipeDrain,
    label: str,
    size: tuple[int, int],
    background: Image.Image,
    tint: Image.Image,
    mask: Image.Image,
    make_overlay: Callable[[Image.Image], tuple[Image.Image, tuple[int, int]]],
    parts: _NameLayers | None,
    reel: list[tuple[Image.Image, tuple[int, int]]],
    composite_workers: int,
    first_frame: list[Image.Image],
    composite_time: list[float],
    stream_end: list[float],
) -> Generator[Image.Image]:
    """Composite the two synchronized viewer streams and yield the
    frames in presentation order — the profile card, where the face
    stream animates (as a monochrome of the tint's hue) over the
    background, under the tint wash, and the body stream over the mask.

    Both streams come from the same definition at the same framerate,
    so frame *i* of the face stream pairs with frame *i* of the body
    stream and they are read in lockstep. Per frame the face — collapsed
    to a monochrome of the background's dominant tint — is composited
    over *background*, the *tint* wash laid over both, then the *mask*
    and the body frame, then the *reel* (the photo reel's face stills,
    if any), the overlay — the caller's *make_overlay* applied to the
    first frame's art (the stamps' faces are chosen from that frame's
    luma, the reel already in place under the stamps) — and the name
    stack, in a sliding window of *composite_workers* threads — as in
    :func:`_stream_composited`, frame 0 on the calling thread — and
    yielded in order. The first composited frame is appended to
    *first_frame*; when both streams reach end-of-file (or the consumer
    stops) the two viewers are reaped and a non-zero exit surfaced."""
    width, height = size
    frame_bytes = width * height * 4
    assert face_viewer.stdout is not None
    assert body_viewer.stdout is not None
    face_stdout = face_viewer.stdout
    body_stdout = body_viewer.stdout
    # The tint layer's top row is the background's dominant tint: reuse it
    # to key the face's monochrome recolor (so the face blends into the
    # card's palette).
    tint_pixel = tint.getpixel((0, 0))
    assert isinstance(tint_pixel, tuple)
    tint_rgb = (tint_pixel[0], tint_pixel[1], tint_pixel[2])
    # The background is a fully opaque card: the per-frame blends take the
    # GIL-releasing Image.composite path (see _composite_frame), with the
    # background's alpha restored before the stamps — the finished card is
    # byte-identical to the alpha_composite chain. The constant layers'
    # alpha channels are the blend masks, computed once.
    background_alpha = background.getchannel("A")
    base_opaque = background_alpha.getextrema() == (255, 255)
    tint_alpha = tint.getchannel("A")
    mask_alpha = mask.getchannel("A")

    def to_art(face_data: bytes, body_data: bytes) -> Image.Image:
        face = Image.frombytes("RGBA", (width, height), face_data)
        face = _monochrome(face, tint_rgb, PROFILE_FACE_BRIGHTNESS)
        body = Image.frombytes("RGBA", (width, height), body_data)
        if base_opaque:
            art = Image.composite(face, background, face.getchannel("A"))
            art = Image.composite(tint, art, tint_alpha)
            art = Image.composite(mask, art, mask_alpha)
            art = Image.composite(body, art, body.getchannel("A"))
            art.putalpha(background_alpha)
        else:
            art = background.copy()
            art.alpha_composite(face)
            art.alpha_composite(tint)
            art.alpha_composite(mask)
            art.alpha_composite(body)
        return art

    def apply_reel(art: Image.Image) -> Image.Image:
        for still, position in reel:
            art.alpha_composite(still, position)
        return art

    def stamp(
        art: Image.Image, overlay: Image.Image, overlay_pos: tuple[int, int]
    ) -> Image.Image:
        art.alpha_composite(overlay, overlay_pos)
        return _apply_name(art, parts) if parts is not None else art

    time_lock = threading.Lock()
    workers = max(1, composite_workers)
    face_eof = False
    body_eof = False
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            pending: deque[Future[Image.Image]] = deque()

            # Frame 0, on the calling thread: make_overlay picks the
            # overlay's faces from its luma, and the window's workers
            # stamp the overlay, so it must not race them.
            face_data = _read_exact(face_stdout, frame_bytes)
            if not face_data:
                face_eof = True
                stream_end[0] = time.perf_counter()
                raise GenerationError(f"{VIEWER} produced no frames for {label}")
            if len(face_data) != frame_bytes:
                raise GenerationError(
                    f"{VIEWER} face stream for {label} truncated: "
                    f"{len(face_data)} of {frame_bytes} bytes"
                )
            body_data = _read_exact(body_stdout, frame_bytes)
            if not body_data:
                body_eof = True
                stream_end[0] = time.perf_counter()
                raise GenerationError(f"{VIEWER} produced no frames for {label}")
            if len(body_data) != frame_bytes:
                raise GenerationError(
                    f"{VIEWER} body stream for {label} truncated: "
                    f"{len(body_data)} of {frame_bytes} bytes"
                )
            art = apply_reel(to_art(face_data, body_data))
            overlay, overlay_pos = make_overlay(art)
            started = time.perf_counter()
            first = stamp(art, overlay, overlay_pos)
            with time_lock:
                composite_time[0] += time.perf_counter() - started
            # Keep the first composited frame: for animations it is
            # written alongside the mp4, for a static card it is the
            # card itself.
            first_frame.append(first)

            def composite(face_data: bytes, body_data: bytes) -> Image.Image:
                started = time.perf_counter()
                result = stamp(
                    apply_reel(to_art(face_data, body_data)), overlay, overlay_pos
                )
                with time_lock:
                    composite_time[0] += time.perf_counter() - started
                return result

            def submit_next() -> None:
                nonlocal face_eof, body_eof
                if face_eof or body_eof:
                    return
                face_data = _read_exact(face_stdout, frame_bytes)
                if not face_data:
                    face_eof = True  # end of the face stream
                    stream_end[0] = time.perf_counter()
                    return
                if len(face_data) != frame_bytes:
                    raise GenerationError(
                        f"{VIEWER} face stream for {label} truncated: "
                        f"{len(face_data)} of {frame_bytes} bytes"
                    )
                body_data = _read_exact(body_stdout, frame_bytes)
                if not body_data:
                    body_eof = True  # end of the body stream
                    stream_end[0] = time.perf_counter()
                    return
                if len(body_data) != frame_bytes:
                    raise GenerationError(
                        f"{VIEWER} body stream for {label} truncated: "
                        f"{len(body_data)} of {frame_bytes} bytes"
                    )
                pending.append(pool.submit(composite, face_data, body_data))

            yield first

            # Prime the window.
            for _ in range(workers):
                submit_next()

            while pending:
                future = pending.popleft()
                try:
                    frame = future.result()
                except Exception:
                    for pending_future in pending:
                        pending_future.cancel()
                    raise
                # Keep the window full (read ahead) before handing off.
                submit_next()
                yield frame
    finally:
        # A stream is "clean" only if read to end-of-file; one abandoned
        # early may be blocked on a full pipe and is killed instead.
        _reap_viewer(face_viewer, face_drain, clean_exit_expected=face_eof)
        _reap_viewer(body_viewer, body_drain, clean_exit_expected=body_eof)


def _encode_mp4(
    frames: Iterator[Image.Image],
    size: tuple[int, int],
    framerate: int,
    out_path: Path,
    threads: int,
    x264_preset: str,
    source_hash: str | None = None,
) -> None:
    """Encode an RGBA frame stream into an MP4 with ffmpeg: the frames
    are already at the run's final size, so no rescaling filter is
    applied."""
    width, height = size
    command = [
        ENCODER,
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgba",
        "-s",
        f"{width}x{height}",
        "-framerate",
        str(framerate),
        "-i",
        "-",
    ]
    command += [
        "-c:v",
        "libx264",
        "-preset",
        x264_preset,
        *FFMPEG_QUALITY_ARGS,
        "-threads",
        str(max(1, threads)),
    ]
    if source_hash is not None:
        # use_metadata_tags lands the custom key in the container (read
        # back via ffprobe's format tags).
        command += [
            "-movflags",
            "use_metadata_tags",
            "-metadata",
            f"{SOURCE_HASH_KEY}={source_hash}",
        ]
    command += [
        "-f",
        "mp4",  # explicit format: the output name may carry a suffix
        str(out_path),
    ]
    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=PIPE_BUFSIZE,
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
        detail = (
            proc.stderr.read().decode(errors="replace").strip() if proc.stderr else ""
        )
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
