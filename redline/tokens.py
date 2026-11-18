"""Split text into display tokens, each with a timing multiplier."""

from __future__ import annotations

import re
from dataclasses import dataclass

SENTENCE_PAUSE = 2.0
COMMA_PAUSE = 1.5
PARAGRAPH_PAUSE = 2.5
NUMBER_PAUSE = 1.3
LONG_WORD_START = 8  # letters; longer words get extra time
LONG_WORD_STEP = 0.05  # extra multiplier per letter beyond LONG_WORD_START
LONG_WORD_MAX = 1.5
SPLIT_HYPHENATED_OVER = 14  # characters; longer hyphenated words are split
HYPHEN_CHUNK = 10  # target characters per chunk when splitting

_CLOSERS = "\"'”’)]}»"
_SENTENCE_END = re.compile(r"[.!?…][" + re.escape(_CLOSERS) + r"]*$")
_CLAUSE_END = re.compile(r"[,;:—–][" + re.escape(_CLOSERS) + r"]*$")
_DASH_SPLIT = re.compile(r"(?<=[—–])(?=\S)")


@dataclass(frozen=True)
class Token:
    text: str
    pause: float


def _split_hyphenated(word: str) -> list[str]:
    """Break long hyphenated words into chunks no longer than the limit."""
    if len(word) <= SPLIT_HYPHENATED_OVER or "-" not in word.strip("-"):
        return [word]
    pieces = word.split("-")
    parts = [p + "-" for p in pieces[:-1]] + [pieces[-1]]
    chunks: list[str] = []
    current = ""
    for part in parts:
        if current and len(current) + len(part) > HYPHEN_CHUNK:
            chunks.append(current)
            current = part
        else:
            current += part
    return chunks + ([current] if current else [])


def _pieces(word: str) -> list[str]:
    pieces = [p for p in _DASH_SPLIT.split(word) if p]
    return [chunk for p in pieces for chunk in _split_hyphenated(p)]


def _pause_for(text: str, ends_paragraph: bool) -> float:
    if ends_paragraph:
        punctuation = PARAGRAPH_PAUSE
    elif _SENTENCE_END.search(text):
        punctuation = SENTENCE_PAUSE
    elif _CLAUSE_END.search(text):
        punctuation = COMMA_PAUSE
    else:
        punctuation = 1.0

    letters = sum(ch.isalpha() for ch in text)
    length = 1.0 + max(0, letters - LONG_WORD_START) * LONG_WORD_STEP
    number = NUMBER_PAUSE if any(ch.isdigit() for ch in text) else 1.0
    return punctuation * min(length, LONG_WORD_MAX) * number


def tokenize(text: str) -> list[Token]:
    """Turn text into tokens. Blank lines mark paragraph breaks."""
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    tokens: list[Token] = []
    for paragraph in paragraphs:
        pieces = [piece for word in paragraph.split() for piece in _pieces(word)]
        for i, piece in enumerate(pieces):
            tokens.append(Token(piece, _pause_for(piece, i == len(pieces) - 1)))
    return tokens
