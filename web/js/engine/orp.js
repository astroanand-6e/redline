/* Optimal recognition point: port of redline/orp.py. Indices are code-point indices. */
import { codePoints, isAlnum } from './pystr.js';

// (max letter count, 0-based letter position) pairs, checked in order.
const ORP_TABLE = Object.freeze([[1, 0], [5, 1], [9, 2], [13, 3]]);
const ORP_LONG_WORD = 4;

/** Code-point index of the character to highlight in `word`. */
export function orpIndex(word) {
  const chars = codePoints(word);
  const letters = chars.flatMap((ch, i) => (isAlnum(ch) ? [i] : []));
  if (!letters.length) return Math.floor(chars.length / 2);
  const n = letters.length;
  const row = ORP_TABLE.find(([limit]) => n <= limit);
  return letters[row ? row[1] : ORP_LONG_WORD];
}

/** Split `word` into [before, fixation character, after]. */
export function splitAtOrp(word) {
  if (!word) return ['', '', ''];
  const chars = codePoints(word);
  const i = orpIndex(word);
  return [chars.slice(0, i).join(''), chars[i], chars.slice(i + 1).join('')];
}
