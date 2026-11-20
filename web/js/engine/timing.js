/* Words-per-minute ramps and per-word frame durations: port of redline/timing.py. */
import { pyRound } from './pystr.js';

export const DEFAULT_WPM_STEP = 30;
const SECONDS_PER_MINUTE = 60.0;

function checkWpm(...values) {
  for (const value of values) {
    if (!(value > 0)) throw new RangeError(`words per minute must be positive, got ${value}`);
  }
}

/** Linear ramp from start to end wpm, quantised to `step` plateaus. */
export function wpmSchedule(nTokens, startWpm, endWpm, step = DEFAULT_WPM_STEP) {
  checkWpm(startWpm, endWpm, step);
  if (nTokens <= 0) return [];
  if (nTokens === 1 || startWpm === endWpm) return new Array(nTokens).fill(startWpm);

  const low = Math.min(startWpm, endWpm);
  const high = Math.max(startWpm, endWpm);
  const span = endWpm - startWpm;
  const schedule = Array.from({ length: nTokens }, (_, i) => {
    const raw = startWpm + (span * i) / (nTokens - 1);
    const snapped = startWpm + pyRound((raw - startWpm) / step) * step;
    return Math.trunc(Math.min(Math.max(snapped, low), high));
  });
  schedule[nTokens - 1] = endWpm;
  return schedule;
}

function durations(tokens, wpms) {
  if (tokens.length !== wpms.length) throw new RangeError(`${tokens.length} tokens but ${wpms.length} wpm values`);
  checkWpm(...wpms);
  return tokens.map((t, i) => (t.pause * SECONDS_PER_MINUTE) / wpms[i]);
}

export function estimateSeconds(tokens, wpms) {
  return durations(tokens, wpms).reduce((a, b) => a + b, 0);
}

/** Frames per token, rounding on the running total so time never drifts. */
export function frameCounts(tokens, wpms, fps) {
  const counts = [];
  let elapsed = 0.0;
  let framesSoFar = 0;
  for (const seconds of durations(tokens, wpms)) {
    elapsed += seconds;
    const target = Math.max(pyRound(elapsed * fps), framesSoFar + 1);
    counts.push(target - framesSoFar);
    framesSoFar = target;
  }
  return counts;
}
