import pytest

from redline.orp import orp_index, split_at_orp


@pytest.mark.parametrize(
    ("word", "expected_char"),
    [
        ("a", "a"),
        ("up", "p"),
        ("the", "h"),
        ("like", "i"),
        ("feels", "e"),
        ("reading", "a"),
        ("understand", "e"),
        ("comprehension", "p"),
        ("internationalization", "r"),
    ],
)
def test_orp_matches_reference_video_letters(word, expected_char):
    assert word[orp_index(word)] == expected_char


def test_orp_skips_leading_punctuation():
    assert "(the"[orp_index("(the")] == "h"
    assert '"like'[orp_index('"like')] == "i"


def test_orp_ignores_trailing_punctuation_when_counting_letters():
    # "word." has 4 letters, so the ORP is the 2nd letter.
    assert "word."[orp_index("word.")] == "o"


def test_orp_handles_words_without_letters():
    assert orp_index("") == 0
    assert orp_index("—") == 0
    assert orp_index("...") == 1


def test_split_at_orp_returns_three_parts():
    assert split_at_orp("like") == ("l", "i", "ke")
    assert split_at_orp("a") == ("", "a", "")
    assert split_at_orp("") == ("", "", "")
