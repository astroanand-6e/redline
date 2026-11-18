"""Encode still frames with per-frame durations into an MP4 using ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path

ProgressFn = Callable[[float], None]


class EncodingError(RuntimeError):
    """Raised when ffmpeg fails."""


def ffmpeg_exe() -> str:
    """Prefer a system ffmpeg; fall back to the static binary from imageio-ffmpeg."""
    system = shutil.which("ffmpeg")
    if system:
        return system
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _quote(path: Path) -> str:
    """Quote a path for the concat demuxer (single quotes escaped as '\\'')."""
    return "'" + path.as_posix().replace("'", "'\\''") + "'"


def _concat_file(clips: Sequence[tuple[Path, int]], fps: int, list_path: Path) -> None:
    lines = []
    for frame_path, n_frames in clips:
        lines.append(f"file {_quote(frame_path)}")
        lines.append(f"duration {n_frames / fps:.6f}")
    # The concat demuxer ignores the last duration unless the file is repeated.
    lines.append(f"file {_quote(clips[-1][0])}")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_with_progress(cmd: list[str], total_us: float, on_progress: ProgressFn | None) -> None:
    # stderr goes to a temp file so a chatty ffmpeg can never block on a full pipe.
    with tempfile.TemporaryFile(mode="w+") as err:
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err, text=True) as proc:
            assert proc.stdout is not None
            for line in proc.stdout:
                if on_progress and line.startswith("out_time_us="):
                    value = line.split("=", 1)[1].strip()
                    if value.isdigit():
                        on_progress(min(int(value) / total_us, 1.0))
            code = proc.wait()
        if code != 0:
            err.seek(0)
            raise EncodingError(f"ffmpeg failed ({code}): {err.read().strip()[-500:]}")


def encode(
    clips: Sequence[tuple[Path, int]],
    fps: int,
    out_path: Path,
    on_progress: ProgressFn | None = None,
) -> Path:
    """Write ``clips`` (frame image, frame count) as a constant-frame-rate MP4."""
    if not clips:
        raise ValueError("nothing to encode")
    total_frames = sum(n for _, n in clips)
    total_us = total_frames / fps * 1_000_000
    list_path = out_path.with_suffix(".txt")
    cmd = [
        ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-fps_mode", "cfr", "-r", str(fps), "-frames:v", str(total_frames),
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats",
        str(out_path),
    ]  # fmt: skip
    try:
        _concat_file(clips, fps, list_path)
        _run_with_progress(cmd, total_us, on_progress)
    finally:
        list_path.unlink(missing_ok=True)
    return out_path
