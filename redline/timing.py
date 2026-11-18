"""Words-per-minute ramps and per-word frame durations."""

from __future__ import annotations

from collections.abc import Sequence

from redline.tokens import Token

DEFAULT_WPM_STEP = 30
SECONDS_PER_MINUTE = 60.0


def _check_wpm(*values: int) -> None:
    for value in values:
        if value <= 0:
            raise ValueError(f"words per minute must be positive, got {value}")


def wpm_schedule(
    n_tokens: int, start_wpm: int, end_wpm: int, step: int = DEFAULT_WPM_STEP
) -> list[int]:
    """Linear ramp from start to end WPM, quantised to ``step`` plateaus."""
    _check_wpm(start_wpm, end_wpm, step)
    if n_tokens <= 0:
        return []
    if n_tokens == 1 or start_wpm == end_wpm:
        return [start_wpm] * n_tokens

    low, high = sorted((start_wpm, end_wpm))
    span = end_wpm - start_wpm
    schedule = []
    for i in range(n_tokens):
        raw = start_wpm + span * i / (n_tokens - 1)
        snapped = start_wpm + round((raw - start_wpm) / step) * step
        schedule.append(int(min(max(snapped, low), high)))
    schedule[-1] = end_wpm
    return schedule


def _durations(tokens: Sequence[Token], wpms: Sequence[int]) -> list[float]:
    if len(tokens) != len(wpms):
        raise ValueError(f"{len(tokens)} tokens but {len(wpms)} wpm values")
    _check_wpm(*wpms)
    return [t.pause * SECONDS_PER_MINUTE / w for t, w in zip(tokens, wpms)]


def estimate_seconds(tokens: Sequence[Token], wpms: Sequence[int]) -> float:
    return sum(_durations(tokens, wpms))


def frame_counts(tokens: Sequence[Token], wpms: Sequence[int], fps: int) -> list[int]:
    """Frames per token, rounding on the running total so time never drifts."""
    counts: list[int] = []
    elapsed = 0.0
    frames_so_far = 0
    for seconds in _durations(tokens, wpms):
        elapsed += seconds
        target = max(round(elapsed * fps), frames_so_far + 1)
        counts.append(target - frames_so_far)
        frames_so_far = target
    return counts
