/* Draw one RSVP frame on a 2D canvas: port of redline/render.py. The fixation letter's centre lands
   on the tick; widths come from measureText, which includes kerning, as Pillow's getlength does. */
import { splitAtOrp } from './engine/orp.js';
import { pyRound } from './engine/pystr.js';

export const FONT_FAMILY = 'Redline STIX';
const FONT_STACK = `"${FONT_FAMILY}", "STIX Two Text", "Times New Roman", serif`;
const MIN_FONT_SCALE = 0.35; // never shrink a word below this share of the base size
const SHRINK_STEP = 0.92;
const FONT_FILES = Object.freeze([
  ['fonts/STIXTwoText.ttf', 'normal'],
  ['fonts/STIXTwoText-Italic.ttf', 'italic'],
]);

/** Load the video font (STIX Two Text, OFL) before the first frame is drawn. */
export async function loadFonts(baseUrl = document.baseURI) {
  const faces = FONT_FILES.map(([file, style]) => new FontFace(
    FONT_FAMILY, `url("${new URL(file, baseUrl).href}")`, { style, weight: '400' },
  ));
  await Promise.all(faces.map((face) => face.load()));
  faces.forEach((face) => document.fonts.add(face));
}

export class FrameRenderer {
  constructor(ctx, layout, style) {
    this.ctx = ctx;
    this.layout = layout;
    this.style = style;
    this.widths = new Map(); // `${size}|${text}` -> width; words repeat a lot in papers
  }

  measure(text, size) {
    const key = `${size}|${text}`;
    let width = this.widths.get(key);
    if (width === undefined) {
      this.ctx.font = `${size}px ${FONT_STACK}`;
      width = this.ctx.measureText(text).width;
      this.widths.set(key, width);
    }
    return width;
  }

  /** The largest font size that keeps the word inside the margins, and the word's left edge. */
  fit(before, pivot, after) {
    const lay = this.layout;
    const minSize = Math.max(8, pyRound(lay.fontSize * MIN_FONT_SCALE));
    let size = lay.fontSize;
    for (;;) {
      const lead = this.measure(before + pivot, size) - this.measure(pivot, size) / 2;
      const x0 = lay.fixationX - lead;
      const x1 = x0 + this.measure(before + pivot + after, size);
      if ((x0 >= lay.marginX && x1 <= lay.width - lay.marginX) || size <= minSize) return { size, x0 };
      size = Math.max(minSize, Math.trunc(size * SHRINK_STEP));
    }
  }

  drawBase() {
    const { ctx, layout: lay, style } = this;
    ctx.fillStyle = style.background;
    ctx.fillRect(0, 0, lay.width, lay.height);
    ctx.fillStyle = style.rule;
    const half = lay.lineWidth / 2;
    for (const y of [lay.topRuleY, lay.bottomRuleY]) {
      ctx.fillRect(0, Math.round(y - half), lay.width, lay.lineWidth);
    }
    const x = Math.round(lay.fixationX - half);
    ctx.fillRect(x, lay.topRuleY, lay.lineWidth, lay.tickLength);
    ctx.fillRect(x, lay.bottomRuleY - lay.tickLength, lay.lineWidth, lay.tickLength);
  }

  render(word, wpmLabel = null) {
    const { ctx, layout: lay, style } = this;
    this.drawBase();
    const [before, pivot, after] = splitAtOrp(word);
    ctx.textBaseline = 'alphabetic';
    if (pivot) {
      const { size, x0 } = this.fit(before, pivot, after);
      const y = lay.baselineY;
      const pivotX = x0 + this.measure(before + pivot, size) - this.measure(pivot, size);
      const afterX = x0 + this.measure(before + pivot + after, size) - this.measure(after, size);
      ctx.font = `${size}px ${FONT_STACK}`;
      ctx.textAlign = 'left';
      ctx.fillStyle = style.text;
      ctx.fillText(before, x0, y);
      ctx.fillText(after, afterX, y);
      ctx.fillStyle = style.highlight;
      ctx.fillText(pivot, pivotX, y);
    }
    if (wpmLabel) {
      ctx.font = `italic ${lay.labelSize}px ${FONT_STACK}`;
      ctx.textAlign = 'right';
      ctx.fillStyle = style.label;
      ctx.fillText(wpmLabel, lay.labelRight, lay.labelBaseline);
    }
  }
}
