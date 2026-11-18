"""Command line: python -m redline paper.pdf -o paper.mp4 --start 300 --end 900"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from redline.extract import ExtractionError, clean_pages, clean_text, extract_pages
from redline.pipeline import RenderOptions, plan_render, render_video
from redline.style import FORMATS, THEMES


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="redline", description="Turn a PDF or text file into an RSVP video."
    )
    p.add_argument("source", type=Path, help="a .pdf, or a .txt with the text to read")
    p.add_argument("-o", "--output", type=Path, required=True, help="output .mp4 path")
    p.add_argument("--start", type=int, default=300, help="starting words per minute")
    p.add_argument("--end", type=int, default=None, help="final wpm (default: same as start)")
    p.add_argument("--format", choices=list(FORMATS), default="16:9")
    p.add_argument("--theme", choices=list(THEMES), default="Dark")
    p.add_argument("--pages", default=None, help="page range like 1-5 (PDF only)")
    p.add_argument("--keep-references", action="store_true", help="keep the references section")
    p.add_argument("--keep-citations", action="store_true", help="keep citations and links")
    p.add_argument("--no-wpm", action="store_true", help="hide the wpm counter")
    p.add_argument("--max-words", type=int, default=50_000)
    return p


def _page_range(spec: str | None) -> tuple[int | None, int | None]:
    """Parse "3" (one page), "2-5" (inclusive) or "3-" (to the end)."""
    if not spec:
        return None, None
    first_s, dash, last_s = spec.partition("-")
    try:
        first = int(first_s)
        last = int(last_s) if last_s else (None if dash else first)
    except ValueError:
        raise ValueError(f"bad page range {spec!r}; use 3, 2-5 or 3-") from None
    if first < 1 or (last is not None and last < first):
        raise ValueError(f"bad page range {spec!r}; pages start at 1")
    return first, last


def read_source(args: argparse.Namespace) -> str:
    if args.source.suffix.lower() != ".pdf":
        return clean_text(args.source.read_text(encoding="utf-8"))
    first, last = _page_range(args.pages)
    pages = extract_pages(args.source, first, last)
    return clean_pages(
        pages,
        skip_references=not args.keep_references,
        strip_citations=not args.keep_citations,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.start <= 0 or (args.end is not None and args.end <= 0):
            raise ValueError("--start and --end must be positive words per minute")
        text = read_source(args)
        options = RenderOptions(
            start_wpm=args.start,
            end_wpm=args.start if args.end is None else args.end,
            fmt=args.format,
            theme=args.theme,
            show_wpm=not args.no_wpm,
            max_words=args.max_words,
        )
        plan = plan_render(text, options)
        print(f"{plan.word_count:,} words, {plan.seconds / 60:.1f} min of video", file=sys.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            video = render_video(text, options, Path(tmp))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(video, args.output)
    except (ExtractionError, ValueError, OSError) as exc:
        print(f"redline: {exc}", file=sys.stderr)
        return 1
    print(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
