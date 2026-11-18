"""Text in, RSVP video out."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from redline.render import FrameRenderer
from redline.style import FORMATS, THEMES, Layout
from redline.timing import DEFAULT_WPM_STEP, estimate_seconds, frame_counts, wpm_schedule
from redline.tokens import Token, tokenize
from redline.video import ProgressFn, encode

DEFAULT_MAX_WORDS = 6000
WPM_FLOOR, WPM_CEILING = 30, 2000  # hard limits, whatever the caller sends
RENDER_SHARE = 0.5  # share of the progress bar spent drawing frames
PROGRESS_EVERY = 50  # report drawing progress every N words
PNG_COMPRESS_LEVEL = 3  # measured: 3x smaller than level 1 and no slower


@dataclass(frozen=True)
class RenderOptions:
    start_wpm: int = 300
    end_wpm: int = 300
    fmt: str = "16:9"
    theme: str = "Dark"
    show_wpm: bool = True
    fps: int = 30
    wpm_step: int = DEFAULT_WPM_STEP
    max_words: int = DEFAULT_MAX_WORDS
    max_seconds: float | None = None  # cap on video length; None means no cap

    def __post_init__(self) -> None:
        for name, value in (("start", self.start_wpm), ("end", self.end_wpm)):
            if not WPM_FLOOR <= value <= WPM_CEILING:
                raise ValueError(f"{name} speed must be {WPM_FLOOR}-{WPM_CEILING} wpm, got {value}")
        if self.fmt not in FORMATS:
            raise ValueError(f"unknown format {self.fmt!r}; pick one of {list(FORMATS)}")
        if self.theme not in THEMES:
            raise ValueError(f"unknown theme {self.theme!r}; pick one of {list(THEMES)}")
        if self.fps <= 0:
            raise ValueError("fps must be positive")


@dataclass(frozen=True)
class RenderPlan:
    tokens: tuple[Token, ...]
    wpms: tuple[int, ...]
    seconds: float

    @property
    def word_count(self) -> int:
        return len(self.tokens)


def plan_render(text: str, options: RenderOptions) -> RenderPlan:
    tokens = tokenize(text)
    if not tokens:
        raise ValueError("There is no text to read.")
    wpms = wpm_schedule(len(tokens), options.start_wpm, options.end_wpm, options.wpm_step)
    return RenderPlan(tuple(tokens), tuple(wpms), estimate_seconds(tokens, wpms))


def _report(on_progress: ProgressFn | None, value: float) -> None:
    if on_progress:
        on_progress(value)


def _draw_frames(
    plan: RenderPlan,
    options: RenderOptions,
    frames_dir: Path,
    on_progress: ProgressFn | None,
) -> list[tuple[Path, int]]:
    """Draw each distinct (word, label) frame once; return (frame, count) clips."""
    renderer = FrameRenderer(Layout.for_format(FORMATS[options.fmt]), THEMES[options.theme])
    counts = frame_counts(plan.tokens, plan.wpms, options.fps)
    cache: dict[tuple[str, str | None], Path] = {}
    clips: list[tuple[Path, int]] = []
    for i, (token, wpm, n) in enumerate(zip(plan.tokens, plan.wpms, counts)):
        key = (token.text, f"{wpm} wpm" if options.show_wpm else None)
        if key not in cache:
            path = frames_dir / f"{len(cache):06d}.png"
            renderer.render(*key).save(path, compress_level=PNG_COMPRESS_LEVEL)
            cache[key] = path
        clips.append((cache[key], n))
        if i % PROGRESS_EVERY == 0:
            _report(on_progress, RENDER_SHARE * i / plan.word_count)
    return clips


def render_video(
    text: str,
    options: RenderOptions,
    out_dir: Path,
    on_progress: ProgressFn | None = None,
) -> Path:
    """Render ``text`` to an MP4 inside ``out_dir`` and return its path."""
    plan = plan_render(text, options)
    if plan.word_count > options.max_words:
        raise ValueError(
            f"That's {plan.word_count:,} words; the limit is {options.max_words:,}. "
            "Pick fewer pages or trim the text."
        )
    if options.max_seconds is not None and plan.seconds > options.max_seconds:
        raise ValueError(
            f"That would be a {plan.seconds / 60:.0f}-minute video; the limit is "
            f"{options.max_seconds / 60:.0f} minutes. Raise the speed or trim the text."
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = Path(tempfile.mkdtemp(prefix="frames-", dir=out_dir))
    out_path = out_dir / f"redline-{frames_dir.name.removeprefix('frames-')}.mp4"
    try:
        clips = _draw_frames(plan, options, frames_dir, on_progress)
        encode(
            clips,
            options.fps,
            out_path,
            on_progress=lambda f: _report(on_progress, RENDER_SHARE + (1 - RENDER_SHARE) * f),
        )
    except BaseException:
        out_path.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(frames_dir, ignore_errors=True)
    _report(on_progress, 1.0)
    return out_path
