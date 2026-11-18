"""Redline: Gradio app (Hugging Face Spaces entry point)."""

from __future__ import annotations

import logging
import multiprocessing
import os
import shutil
import tempfile
import time
from pathlib import Path

import gradio as gr

from redline.extract import ExtractionError, clean_pages, extract_pages
from redline.pipeline import RENDER_SHARE, RenderOptions, plan_render, render_video
from redline.style import FORMATS, THEMES
from redline.video import EncodingError

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
SAMPLE_PDF = ROOT / "examples" / "gettysburg.pdf"
OUTPUT_DIR = Path(tempfile.mkdtemp(prefix="redline-out-"))
MAX_WORDS = int(os.environ.get("REDLINE_MAX_WORDS", "6000"))
MAX_CHARS = MAX_WORDS * 15  # generous for long words; stops megabyte pastes
MAX_VIDEO_SECONDS = 60 * int(os.environ.get("REDLINE_MAX_MINUTES", "40"))
EXTRACT_TIMEOUT_SECONDS = float(os.environ.get("REDLINE_EXTRACT_TIMEOUT", "60"))
OUTPUT_TTL_SECONDS = 3600
WPM_MIN, WPM_MAX, WPM_STEP = 120, 1200, 30
REPO_URL = "https://github.com/astroanand-6e/redline"

HEAD = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link href="https://fonts.googleapis.com/css2?family=STIX+Two+Text:ital@0;1'
    '&display=swap" rel="stylesheet">'
)
FORCE_DARK_JS = "() => { document.body.classList.add('dark'); }"

HOW_IT_WORKS = """
**RSVP (rapid serial visual presentation)** shows one word at a time in a fixed spot, so
your eyes skip the saccades they normally make between words.

- **Red fixation letter.** Each word's *optimal recognition point*, slightly left of centre,
  is drawn in red and pinned to the tick marks, so your eye never moves.
- **Natural pacing.** Sentence ends get 2× time, commas 1.5×, paragraph breaks 2.5×.
  Long words and numbers get a little extra.
- **PDF cleanup.** Repeated headers and footers and page numbers are removed, words split
  across lines are rejoined, and you can drop the references section, citations like `[12]`,
  links and emails.
- **Speed ramp.** Start slow and finish fast (for example 300 → 900 wpm); the counter
  in the corner shows the current speed.

Comprehension drops at very high speeds, so this works best for skimming, review, and practice.
"""

log = logging.getLogger("redline")


def _extract_with_timeout(pdf_path: str, first: int | None, last: int | None) -> list[str]:
    """Parse the PDF in a child process so a hostile file can't stall a worker."""
    ctx = multiprocessing.get_context("spawn")
    with ctx.Pool(1) as pool:
        job = pool.apply_async(extract_pages, (pdf_path, first, last))
        try:
            return job.get(timeout=EXTRACT_TIMEOUT_SECONDS)
        except multiprocessing.TimeoutError:
            raise ExtractionError(
                "This PDF took too long to read. Try a smaller page range."
            ) from None


def extract_text(pdf_path, first_page, last_page, skip_references, strip_citations):
    if not pdf_path:
        return gr.update()
    first = int(first_page) if first_page else None
    last = int(last_page) if last_page else None
    try:
        pages = _extract_with_timeout(str(pdf_path), first, last)
    except ExtractionError as exc:
        log.warning("extraction failed: %s", exc.__cause__ or exc)
        raise gr.Error(str(exc)) from exc
    text = clean_pages(
        pages, skip_references=bool(skip_references), strip_citations=bool(strip_citations)
    )
    if not text:
        raise gr.Error("No selectable text found. This PDF may be a scan; run OCR on it first.")
    return text


def _format_duration(seconds: float) -> str:
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes} min {secs:02d} s" if minutes else f"{secs} s"


def _too_long(text: str) -> str | None:
    if len(text) > MAX_CHARS:
        return f"That's {len(text):,} characters; the limit is {MAX_CHARS:,}. Trim the text."
    return None


def describe(text, start_wpm, end_wpm) -> str:
    if not text or not text.strip():
        return "Upload a PDF or paste text to begin."
    if problem := _too_long(text):
        return f"⚠️ {problem}"
    start, end = int(start_wpm), int(end_wpm)
    plan = plan_render(text, RenderOptions(start_wpm=start, end_wpm=end))
    speed = f"{start} wpm" if start == end else f"{start}→{end} wpm"
    summary = f"**{plan.word_count:,} words** · about {_format_duration(plan.seconds)} at {speed}"
    if plan.word_count > MAX_WORDS:
        summary += f"  \n⚠️ Over the {MAX_WORDS:,}-word limit. Choose fewer pages or trim the text."
    elif plan.seconds > MAX_VIDEO_SECONDS:
        summary += f"  \n⚠️ Over the {MAX_VIDEO_SECONDS // 60}-minute limit. Raise the speed."
    return summary


def _prune_old_outputs() -> None:
    """Delete stale videos, concat lists and frame dirs (e.g. from a killed render)."""
    if not OUTPUT_DIR.exists():
        return
    cutoff = time.time() - OUTPUT_TTL_SECONDS
    for pattern in ("redline-*.mp4", "redline-*.txt", "frames-*"):
        for path in OUTPUT_DIR.glob(pattern):
            try:
                if path.stat().st_mtime >= cutoff:
                    continue
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)
            except FileNotFoundError:
                continue  # a concurrent render already removed it


def _check_inputs(text, start_wpm, end_wpm) -> None:
    """Server-side limits: the sliders only constrain the browser, not the API."""
    if not text or not text.strip():
        raise gr.Error("Add some text first: upload a PDF or paste text.")
    if problem := _too_long(text):
        raise gr.Error(problem)
    for label, value in (("Start", start_wpm), ("End", end_wpm)):
        if not WPM_MIN <= float(value) <= WPM_MAX:
            raise gr.Error(f"{label} speed must be between {WPM_MIN} and {WPM_MAX} wpm.")


def render(text, start_wpm, end_wpm, fmt, theme, show_wpm, progress=gr.Progress()):  # noqa: B008
    _check_inputs(text, start_wpm, end_wpm)
    _prune_old_outputs()

    def report(fraction: float) -> None:
        progress(fraction, desc="Drawing frames" if fraction < RENDER_SHARE else "Encoding MP4")

    try:
        options = RenderOptions(
            start_wpm=int(start_wpm),
            end_wpm=int(end_wpm),
            fmt=fmt,
            theme=theme,
            show_wpm=bool(show_wpm),
            max_words=MAX_WORDS,
            max_seconds=MAX_VIDEO_SECONDS,
        )
        return str(render_video(text, options, OUTPUT_DIR, on_progress=report))
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc
    except EncodingError as exc:
        log.exception("encoding failed")
        raise gr.Error("Video encoding failed. Try again with less text.") from exc


def _source_column():
    gr.Markdown("1 · Source", elem_classes="rl-step")
    pdf = gr.File(label="PDF", file_types=[".pdf"], type="filepath")
    with gr.Row():
        first = gr.Number(label="From page", value=1, precision=0, minimum=1)
        last = gr.Number(label="To page (0 = last page)", value=0, precision=0, minimum=0)
    with gr.Row():
        skip_refs = gr.Checkbox(label="Skip references section", value=True)
        strip_cites = gr.Checkbox(label="Remove citations, links and emails", value=True)
    extract_btn = gr.Button("Re-extract with these settings", size="sm")
    gr.Examples([[str(SAMPLE_PDF)]], inputs=[pdf], label="Try a sample PDF")
    text = gr.Textbox(
        label="Text to read (edit it, or paste your own)",
        lines=12,
        max_lines=20,
        max_length=MAX_CHARS,
    )
    stats = gr.Markdown("Upload a PDF or paste text to begin.", elem_classes="rl-stats")
    return pdf, [pdf, first, last, skip_refs, strip_cites], extract_btn, text, stats


def _output_column():
    gr.Markdown("2 · Speed and look", elem_classes="rl-step")
    start = gr.Slider(WPM_MIN, WPM_MAX, value=300, step=WPM_STEP, label="Start speed (wpm)")
    end = gr.Slider(WPM_MIN, WPM_MAX, value=600, step=WPM_STEP, label="End speed (wpm)")
    fmt = gr.Radio([(f.label, key) for key, f in FORMATS.items()], value="16:9", label="Format")
    theme = gr.Radio(list(THEMES), value="Dark", label="Theme")
    show_wpm = gr.Checkbox(value=True, label="Show the wpm counter")
    render_btn = gr.Button("Render video", variant="primary", size="lg")
    video = gr.Video(label="Your video", interactive=False, autoplay=True)
    return start, end, fmt, theme, show_wpm, render_btn, video


def build_demo() -> gr.Blocks:
    with gr.Blocks(
        title="Redline · PDF to speed-reading video",
        delete_cache=(3600, 3600),
        analytics_enabled=False,
    ) as demo:
        gr.HTML((ASSETS / "hero.html").read_text(), js_on_load=(ASSETS / "hero.js").read_text())
        with gr.Row(equal_height=False):
            with gr.Column(scale=5):
                pdf, extract_inputs, extract_btn, text, stats = _source_column()
            with gr.Column(scale=4):
                start, end, fmt, theme, show_wpm, render_btn, video = _output_column()
        with gr.Accordion("How it works", open=False):
            gr.Markdown(HOW_IT_WORKS)
        gr.HTML(
            f'<div class="rl-footer">Built by Anand Thakkar · <a href="{REPO_URL}" '
            'target="_blank" rel="noopener">Source on GitHub</a></div>'
        )

        pdf.change(extract_text, extract_inputs, text)
        extract_btn.click(extract_text, extract_inputs, text)
        for trigger in (text.change, start.change, end.change):
            trigger(
                describe,
                [text, start, end],
                stats,
                show_progress="hidden",
                trigger_mode="always_last",
            )
        render_btn.click(render, [text, start, end, fmt, theme, show_wpm], video)
    return demo


def _theme() -> gr.themes.Base:
    coral = gr.themes.Color(
        c50="#fdf2f2", c100="#fbe1e2", c200="#f6c4c6", c300="#ef9a9e", c400="#e6676e",
        c500="#de444c", c600="#c8323a", c700="#a7272e", c800="#8a2329", c900="#732226",
        c950="#3e0d10", name="coral",
    )  # fmt: skip
    return gr.themes.Base(
        primary_hue=coral,
        neutral_hue="zinc",
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_demo().queue(default_concurrency_limit=2, max_size=16).launch(
        theme=_theme(),
        css_paths=[ASSETS / "style.css"],
        head=HEAD,
        js=FORCE_DARK_JS,
        max_file_size="50mb",
    )
