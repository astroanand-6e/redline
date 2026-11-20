"""Write tests/web/fixtures.json: the Python engine's answers for the JS parity tests.

Run with the repo's venv after changing redline/*.py, then run `node --test tests/web/`.
tests/test_web_fixtures.py fails if this file is stale.
"""

from __future__ import annotations

import json
import sys
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from redline.extract import clean_pages, clean_text, extract_pages
from redline.orp import orp_index
from redline.style import FORMATS, Layout
from redline.timing import frame_counts, wpm_schedule
from redline.tokens import tokenize

FIXTURES = Path(__file__).with_name("fixtures.json")
ABSTRACT = (ROOT / "demo" / "attention-abstract.txt").read_text(encoding="utf-8")
SAMPLE_PDF = ROOT / "examples" / "gettysburg.pdf"

ORP_WORDS = [
    "", "a", "I.", "it", "the", "read", "words", "reading", "understand", "comprehension",
    "internationalization", "—", "“Hello,”", "(1997)", "3.14", "naïve", "🙂abc", "x²", "--",
]

TOKEN_TEXTS = [
    ABSTRACT,
    "state-of-the-art-transformer-based models are well-known.",
    "e.g., 3.14% of runs (n=12) failed; others: fine.",
    "word—another–third — spaced",
    "“Quoted.” 'single,' (paren). [bracket]! {brace}? »guillemet«…",
    "naïve café ünïcödé façade, x² and H₂O at 10:30.",
    "emoji 🙂 test\tTabs and nbsp thin",
    "Paragraph one.\n\n\nParagraph two\n \nthree   \n\n",
    "extraordinarily incomprehensibilities antidisestablishmentarianism",
    "--leading-hyphen- trailing- -both-",
]

SCHEDULES = [
    (0, 300, 600, 30), (1, 300, 900, 30), (10, 300, 900, 30), (7, 900, 300, 30),
    (100, 120, 1200, 30), (5, 300, 360, 30), (9, 300, 330, 30), (13, 450, 450, 30),
    (40, 600, 300, 60),
]

RAW_PAGES = [
    (
        "Journal of Tests 2024\nAttention Is All\nYou Need\n\nAbstract\n"
        "The dominant sequence trans-\nduction models are based on com-\n"
        "plex recurrent networks [1, 2] that are slow to train on long inputs.\n1"
    ),
    (
        "Journal of Tests 2024\nWe build on (Vaswani et al., 2017; Bahdanau and Cho, 2014) and\n"
        "email me at someone@example.com or see https://example.com/x for the code.\n"
        "Results‡ are -- as expected -- good, see arXiv:1706.03762v7 for more detail.\n2"
    ),
    (
        "Journal of Tests 2024\nConclusion\nShort line.\n"
        "Another paragraph starts here and keeps going for a while longer than most.\n"
        "We thank everyone who reviewed the many drafts of this paper over the years.\n"
        "References\n[1] A. Author. A paper about attention in deep networks. 2017.\n3"
    ),
    "Journal of Tests 2024\n[2] B. Author. Another paper about recurrence. 2018.\nPage 4 of 4",
]


def _clean_cases(pages: list[str]) -> list[dict]:
    return [
        {
            "pages": pages,
            "skipReferences": skip,
            "removeCitations": strip,
            "expected": clean_pages(pages, skip_references=skip, strip_citations=strip),
        }
        for skip, strip in product((False, True), repeat=2)
    ]


def build() -> dict:
    abstract_tokens = tokenize(ABSTRACT)
    return {
        "orp": [[w, orp_index(w)] for w in ORP_WORDS],
        "tokens": [
            {"text": t, "tokens": [[tok.text, tok.pause] for tok in tokenize(t)]} for t in TOKEN_TEXTS
        ],
        "schedules": [
            {"args": list(args), "expected": wpm_schedule(*args)} for args in SCHEDULES
        ],
        "frameCounts": [
            {
                "start": start,
                "end": end,
                "fps": fps,
                "expected": frame_counts(
                    abstract_tokens, wpm_schedule(len(abstract_tokens), start, end), fps
                ),
            }
            for start, end, fps in ((300, 600, 30), (300, 900, 30), (450, 450, 24))
        ],
        "layouts": {key: vars(Layout.for_format(fmt)) for key, fmt in FORMATS.items()},
        "clean": _clean_cases(RAW_PAGES) + _clean_cases(extract_pages(SAMPLE_PDF)),
        "cleanText": [
            {"text": t, "expected": clean_text(t)}
            for t in (
                "a--b and c -- d\r\nnext\rline",
                "ﬁne ligature ﬀ, full-width ＡＢＣ, ½",
                "  para one  \n\n\n  para two \n \n",
            )
        ],
    }


def render() -> str:
    return json.dumps(build(), ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    FIXTURES.write_text(render(), encoding="utf-8")
    print(f"wrote {FIXTURES.relative_to(ROOT)}")
