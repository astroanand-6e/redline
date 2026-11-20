---
title: Redline
emoji: 🔴
colorFrom: red
colorTo: gray
sdk: static
app_file: index.html
pinned: false
license: mit
short_description: Turn any PDF into an RSVP speed-reading video
---

# Redline

Turn any PDF into a speed-reading video, in your browser. Words flash one at a time with the
fixation letter in red, pinned to the same spot, so your eyes never move (RSVP). Read it on the
page or download an MP4 in landscape, square or vertical format.

Everything runs client-side: pdf.js reads the PDF, a canvas draws each frame and the browser's
H.264 encoder (WebCodecs) writes the MP4. Your PDF is never uploaded.

Source, tests and the Python command-line version: https://github.com/astroanand-6e/redline
