/* Frame geometry and colours: port of redline/style.py (proportions measured from the reference
   1280x720 RSVP video). */
import { pyRound } from './pystr.js';

const TOP_RULE = 0.231;
const BOTTOM_RULE = 0.784;
const TICK_LENGTH = 0.094;
const FIXATION_X = 0.376;
const BASELINE = 0.551;
const FONT_SIZE = 0.152;
const LABEL_RIGHT = 0.916;
const LABEL_BASELINE = 0.857;
const LABEL_SIZE = 0.058;
const LINE_WIDTH = 0.0045;
const MARGIN_X = 0.04;

export const FORMATS = Object.freeze({
  '16:9': Object.freeze({ label: 'Landscape 16:9', size: [1280, 720], stageScale: 1.0 }),
  '1:1': Object.freeze({ label: 'Square 1:1', size: [1080, 1080], stageScale: 1.35 }),
  '9:16': Object.freeze({ label: 'Vertical 9:16', size: [1080, 1920], stageScale: 1.5 }),
});

const rgb = (r, g, b) => `rgb(${r}, ${g}, ${b})`;

export const THEMES = Object.freeze({
  Dark: Object.freeze({
    background: rgb(0, 0, 0), text: rgb(242, 242, 242), highlight: rgb(222, 68, 76),
    rule: rgb(40, 40, 40), label: rgb(72, 72, 72),
  }),
  Light: Object.freeze({
    background: rgb(250, 248, 243), text: rgb(24, 24, 24), highlight: rgb(214, 52, 60),
    rule: rgb(214, 210, 202), label: rgb(150, 146, 140),
  }),
});

/** Pixel geometry for one format: a 16:9 stage across the width (scaled per format), centred. */
export function layoutFor(formatKey) {
  const fmt = FORMATS[formatKey];
  if (!fmt) throw new RangeError(`unknown format ${formatKey}`);
  const [width, height] = fmt.size;
  const stageH = Math.min(height, ((width * 9) / 16) * fmt.stageScale);
  const stageTop = (height - stageH) / 2;
  const sy = (fraction) => pyRound(stageTop + stageH * fraction);

  return Object.freeze({
    width,
    height,
    topRuleY: sy(TOP_RULE),
    bottomRuleY: sy(BOTTOM_RULE),
    tickLength: pyRound(stageH * TICK_LENGTH),
    fixationX: pyRound(width * FIXATION_X),
    baselineY: sy(BASELINE),
    fontSize: pyRound(stageH * FONT_SIZE),
    labelRight: pyRound(width * LABEL_RIGHT),
    labelBaseline: sy(LABEL_BASELINE),
    labelSize: pyRound(stageH * LABEL_SIZE),
    lineWidth: Math.max(2, pyRound(stageH * LINE_WIDTH)),
    marginX: pyRound(width * MARGIN_X),
  });
}
