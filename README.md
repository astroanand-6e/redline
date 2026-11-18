---
title: Redline
emoji: 🔴
colorFrom: red
colorTo: gray
sdk: gradio
sdk_version: 6.32.0
python_version: "3.12"
app_file: app.py
pinned: false
license: mit
short_description: Turn any PDF into an RSVP speed-reading video
---

# Redline

**Turn any PDF into a speed-reading video.** Words flash one at a time with the fixation
letter in red, pinned to the same spot, so your eyes never move. Upload a paper, pick a speed
ramp (say 300 → 900 wpm), and download an MP4 in landscape, square or vertical format.

![Redline preview](demo/preview.gif)

## Why

Most reading time goes into moving your eyes: saccades between words and jumps back to reread.
RSVP (rapid serial visual presentation) removes those movements by showing each word in a fixed
spot. Redline does this for PDFs. It cleans up the extracted text first, so you get the paper's
prose instead of its page furniture, and then renders a shareable video.

## How it works

```
PDF ──► extract (pypdf) ──► clean ──► tokenize ──► schedule ──► draw frames ──► encode
                            │          │            │            │               │
          headers/footers,  │   pause multipliers   wpm ramp,    Pillow, ORP     ffmpeg concat,
          page numbers,     │   for . , ¶ and long  rounded on   letter centred   one PNG per
          hyphen rejoin,    │   words / numbers     running sum  on the tick      unique word
          refs + citations  ┘                       (no drift)
```

- **Optimal recognition point.** The red letter sits slightly left of centre (2nd letter of a
  5-letter word, 3rd of a 9-letter word, and so on). Every word is shifted so that letter lands
  on the tick marks.
- **Natural pacing.** Sentence ends get 2× time, commas 1.5×, paragraph breaks 2.5×. Long words
  and numbers get a little extra.
- **Text cleanup for papers.** Running headers and footers are removed (lines repeated on most
  pages), page numbers dropped, words split across lines rejoined, headings and paragraphs
  detected, and the references section, citations (`[12]`, `(Vaswani et al., 2017)`), links,
  emails and arXiv stamps stripped on request.
- **Fast encoding.** Each distinct (word, speed) frame is drawn once and reused, then ffmpeg's
  concat demuxer holds it for the right number of frames. Frame counts are rounded on the
  running total, so a 10-minute video stays in sync to within one frame. The 15-page
  *Attention Is All You Need* paper (4.7k words, a 12.5-minute video) renders in about 20 s on
  a laptop.

## Run it locally

```bash
uv venv && uv pip install -r requirements-dev.txt
.venv/bin/python app.py            # Gradio UI on http://127.0.0.1:7860
```

Or use the command line:

```bash
python -m redline paper.pdf -o paper.mp4 --start 300 --end 900 --format 1:1
python -m redline notes.txt -o notes.mp4 --start 450 --theme Light
python -m redline book.pdf -o ch1.mp4 --pages 12-30 --keep-references
```

## Project layout

| File | Role |
| --- | --- |
| `redline/extract.py` | PDF text extraction and cleanup heuristics |
| `redline/tokens.py` | Word tokens and pause multipliers |
| `redline/orp.py` | Fixation-letter (ORP) index |
| `redline/timing.py` | WPM ramps and drift-free frame counts |
| `redline/style.py`, `render.py` | Frame geometry and Pillow drawing |
| `redline/video.py` | ffmpeg encoding with progress |
| `redline/pipeline.py` | Text in, MP4 out |
| `app.py` | Gradio app (Hugging Face Spaces entry point) |

## Tests

```bash
.venv/bin/python -m pytest --cov
```

The 105 tests cover ORP placement (measured from red pixels in rendered frames), cleanup
heuristics, timing drift, every output format, the CLI, the Gradio handlers and the server-side limits (speed range, text size, video length, PDF parse timeout). Coverage is 96%.

## Limits

- Scanned PDFs have no text layer, so run OCR first.
- Math, tables and figure captions come through as plain text.
- Comprehension drops at very high speeds. RSVP works best for skimming, review and practice.

## Credits

The frame style follows the classic RSVP speed-reading look: black background, serif word,
red fixation letter, guide ticks. Font: [STIX Two Text](https://github.com/stipub/stixfonts)
(SIL OFL 1.1). Sample PDF: the Gettysburg Address (public domain).
