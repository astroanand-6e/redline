/* Text in, reading plan out: tokens, the wpm of each, and the frame each one starts on. The live
   player and the MP4 exporter both read this, so what you watch is what you download. */
import { pyRound } from './pystr.js';
import { frameCounts, wpmSchedule } from './timing.js';
import { tokenize } from './tokens.js';

export const FPS = 30;

export function planReading(text, options) {
  return planFromTokens(tokenize(text), options);
}

/** Same as planReading, for callers that cache tokens (a speed change needs no re-tokenizing). */
export function planFromTokens(tokens, { startWpm, endWpm, fps = FPS }) {
  const wpms = wpmSchedule(tokens.length, startWpm, endWpm);
  const counts = tokens.length ? frameCounts(tokens, wpms, fps) : [];
  const starts = [];
  let totalFrames = 0;
  for (const count of counts) {
    starts.push(totalFrames);
    totalFrames += count;
  }
  return Object.freeze({ tokens, wpms, counts, starts, fps, totalFrames, seconds: totalFrames / fps });
}

/** Index of the token on screen at `frame`: the last start that is <= frame. */
export function indexAtFrame(starts, frame) {
  let lo = 0;
  let hi = starts.length - 1;
  if (hi < 0) return 0;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (starts[mid] <= frame) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

/** "12 min 05 s" or "22 s", as the Python app prints it. */
export function formatDuration(seconds) {
  const total = pyRound(seconds);
  const minutes = Math.floor(total / 60);
  const secs = total % 60;
  return minutes ? `${minutes} min ${String(secs).padStart(2, '0')} s` : `${secs} s`;
}

/** "1:05" for the transport clock. */
export function formatClock(seconds) {
  const total = Math.max(0, Math.floor(seconds));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`;
}
