import pytest

from redline.timing import estimate_seconds, frame_counts, wpm_schedule
from redline.tokens import Token


def test_constant_schedule_when_start_equals_end():
    assert wpm_schedule(5, 300, 300) == [300] * 5


def test_ramp_hits_both_endpoints_and_is_monotonic():
    schedule = wpm_schedule(100, 300, 900, step=60)
    assert schedule[0] == 300
    assert schedule[-1] == 900
    assert schedule == sorted(schedule)
    assert set(schedule) <= set(range(300, 901, 60))


def test_ramp_can_slow_down():
    schedule = wpm_schedule(10, 600, 300, step=30)
    assert schedule[0] == 600
    assert schedule[-1] == 300
    assert schedule == sorted(schedule, reverse=True)


def test_single_token_schedule_uses_start():
    assert wpm_schedule(1, 300, 900) == [300]


def test_empty_schedule():
    assert wpm_schedule(0, 300, 900) == []


@pytest.mark.parametrize("bad", [0, -10])
def test_schedule_rejects_non_positive_wpm(bad):
    with pytest.raises(ValueError):
        wpm_schedule(3, bad, 300)
    with pytest.raises(ValueError):
        wpm_schedule(3, 300, bad)


def test_frame_counts_total_matches_duration_without_drift():
    tokens = [Token("w", 1.0)] * 300
    counts = frame_counts(tokens, [300] * 300, fps=30)
    # 300 words at 300 wpm = 60 s = 1800 frames, despite 0.2 s = 6 frames each.
    assert sum(counts) == 1800


def test_frame_counts_give_every_word_at_least_one_frame():
    tokens = [Token("w", 1.0)] * 10
    counts = frame_counts(tokens, [10_000] * 10, fps=24)
    assert all(c >= 1 for c in counts)


def test_frame_counts_respect_pause_multiplier():
    tokens = [Token("a", 1.0), Token("b.", 2.0)]
    counts = frame_counts(tokens, [300, 300], fps=30)
    assert counts == [6, 12]


def test_frame_counts_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        frame_counts([Token("a", 1.0)], [300, 300], fps=30)


def test_estimate_seconds():
    tokens = [Token("a", 1.0), Token("b", 2.0)]
    assert estimate_seconds(tokens, [600, 600]) == pytest.approx(0.3)
