"""Optimal recognition point (ORP): the letter the eye should fixate on.

Uses the classic Spritz-style table: the fixation letter sits slightly left
of the word's centre, shifting right as words get longer.
"""

from __future__ import annotations

# (max letter count, 0-based letter position) pairs, checked in order.
_ORP_TABLE = ((1, 0), (5, 1), (9, 2), (13, 3))
_ORP_LONG_WORD = 4


def _letter_positions(word: str) -> list[int]:
    return [i for i, ch in enumerate(word) if ch.isalnum()]


def orp_index(word: str) -> int:
    """Return the string index of the character to highlight in ``word``."""
    letters = _letter_positions(word)
    if not letters:
        return len(word) // 2
    n = len(letters)
    k = next((pos for limit, pos in _ORP_TABLE if n <= limit), _ORP_LONG_WORD)
    return letters[k]


def split_at_orp(word: str) -> tuple[str, str, str]:
    """Split ``word`` into (before, fixation character, after)."""
    if not word:
        return ("", "", "")
    i = orp_index(word)
    return (word[:i], word[i], word[i + 1 :])
