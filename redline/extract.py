"""PDF text extraction and cleanup for reading."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_PAGES = 400
HEADER_MIN_PAGES = 3  # need this many pages before guessing running headers
HEADER_PAGE_FRACTION = 0.5  # a line on at least this share of pages is a header
REFERENCES_MIN_POSITION = 0.3  # references heading must come after this share of text
SHORT_LINE_RATIO = 0.6  # a line under 60% of the median length ends a paragraph
MIN_MEDIAN_FOR_SHORT_LINES = 30  # characters; skip the heuristic for tiny inputs

_PAGE_NUMBER = re.compile(r"^(page\s*)?\d{1,4}(\s*(of|/)\s*\d{1,4})?$", re.IGNORECASE)
_REFERENCES = re.compile(
    r"^\s*(\d+\.?\s*)?(references|bibliography|works cited|literature cited)\s*$",
    re.IGNORECASE,
)
_NUMERIC_CITATION = re.compile(r"\s*\[\d+(?:\s*[,–-]\s*\d+)*\]")
_AUTHOR_YEAR_CITATION = re.compile(
    r"\s*\((?:[A-Z][\w'-]+(?: et al\.)?(?:,? (?:and|&) [A-Z][\w'-]+)?,? \d{4}[a-z]?(?:;\s*)?)+\)"
)
_NOISE = re.compile(
    # Bounded quantifiers keep this linear on huge unbroken tokens.
    r"\s*(?:[^\s@]{1,64}@[^\s@]{1,255}\.[A-Za-z]{2,}"  # emails
    r"|https?://\S{1,2000}"  # links
    r"|arXiv:\d{4}\.\d{4,5}(?:v\d+)?)"  # arXiv stamps
)
_FOOTNOTE_MARKS = re.compile(r"[∗†‡§¶]")
_DOUBLE_HYPHEN = re.compile(r"[ \t]*--+[ \t]*")
_PARAGRAPH_END = (".", "!", "?", ":", '"', "”")


class ExtractionError(ValueError):
    """Raised when a PDF cannot be read or the page range is invalid."""


def extract_pages(
    pdf_path: str | Path, first_page: int | None = None, last_page: int | None = None
) -> list[str]:
    """Return raw text for each page in the inclusive 1-based range."""
    try:
        reader = PdfReader(str(pdf_path))
        total = len(reader.pages)
    except (PdfReadError, OSError, ValueError) as exc:
        raise ExtractionError("Could not read this PDF. It may be damaged or encrypted.") from exc

    first = first_page or 1
    last = min(last_page or total, total)
    if first < 1 or first > last:
        raise ExtractionError(f"Invalid page range {first}-{last} for a {total}-page PDF")
    if last - first + 1 > MAX_PAGES:
        raise ExtractionError(f"Please pick at most {MAX_PAGES} pages at a time")

    try:
        return [reader.pages[i].extract_text() or "" for i in range(first - 1, last)]
    except Exception as exc:  # pypdf raises many types on malformed content
        raise ExtractionError("Could not extract text from this PDF.") from exc


def _normalise_line(line: str) -> str:
    return re.sub(r"\d+", "#", line.strip().lower())


def _running_lines(pages: list[list[str]]) -> set[str]:
    """Lines that repeat across many pages, like running headers and footers."""
    if len(pages) < HEADER_MIN_PAGES:
        return set()
    counts = Counter(
        key for page in pages for key in {_normalise_line(line) for line in page if line.strip()}
    )
    threshold = max(HEADER_MIN_PAGES, len(pages) * HEADER_PAGE_FRACTION)
    return {line for line, n in counts.items() if n >= threshold}


def _drop_noise(pages: list[list[str]]) -> list[str]:
    running = _running_lines(pages)
    kept: list[str] = []
    for page in pages:
        for line in page:
            stripped = line.strip()
            if _PAGE_NUMBER.match(stripped) or _normalise_line(stripped) in running:
                continue
            kept.append(stripped)
        kept.append("")  # page boundary behaves like a soft break
    return kept


def _cut_references(lines: list[str]) -> list[str]:
    total = sum(len(line) for line in lines) or 1
    seen = 0
    for i, line in enumerate(lines):
        if _REFERENCES.match(line) and seen / total >= REFERENCES_MIN_POSITION:
            return lines[:i]
        seen += len(line)
    return lines


def _short_line_limit(lines: list[str]) -> float:
    """Lines shorter than this probably end a paragraph or are headings."""
    lengths = sorted(len(line) for line in lines if line)
    if not lengths:
        return 0.0
    median = lengths[len(lengths) // 2]
    return median * SHORT_LINE_RATIO if median >= MIN_MEDIAN_FOR_SHORT_LINES else 0.0


def _join_lines(lines: list[str]) -> str:
    """Rejoin wrapped lines into paragraphs, undoing end-of-line hyphenation."""
    short_limit = _short_line_limit(lines)
    paragraphs: list[str] = []
    current = ""
    previous_len = 0
    for line in lines:
        if not line:
            if current.endswith(_PARAGRAPH_END):
                paragraphs.append(current)
                current = ""
            continue
        starts_block = line[:1].isupper() or line[:1].isdigit()
        if current and previous_len < short_limit and starts_block and not current.endswith("-"):
            paragraphs.append(current)
            current = ""
        previous_len = len(line)
        if not current:
            current = line
        elif current.endswith("-") and line[:1].islower():
            current = current[:-1] + line
        elif current.endswith("-"):
            current += line
        else:
            current += " " + line
    if current:
        paragraphs.append(current)
    return "\n\n".join(paragraphs)


def _strip_citations(text: str) -> str:
    """Remove citations plus links, emails, arXiv stamps and footnote marks."""
    for pattern in (_NUMERIC_CITATION, _AUTHOR_YEAR_CITATION, _NOISE, _FOOTNOTE_MARKS):
        text = pattern.sub("", text)
    return text


def clean_text(text: str) -> str:
    """Normalise unicode and whitespace, keeping paragraph breaks."""
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = _DOUBLE_HYPHEN.sub("— ", text)
    paragraphs = re.split(r"\n\s*\n", text)
    squashed = (" ".join(p.split()) for p in paragraphs)
    return "\n\n".join(p for p in squashed if p)


def clean_pages(
    pages: list[str], *, skip_references: bool = False, strip_citations: bool = False
) -> str:
    """Turn raw page texts into clean, readable paragraphs."""
    normalised = [unicodedata.normalize("NFKC", p).replace("\r", "") for p in pages]
    lines = _drop_noise([page.split("\n") for page in normalised])
    if skip_references:
        lines = _cut_references(lines)
    text = _join_lines(lines)
    if strip_citations:
        text = _strip_citations(text)
    return clean_text(text)
