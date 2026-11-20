/* Python string semantics the engine relies on, so the browser port matches redline/*.py exactly:
   lengths and indices in code points, Unicode character classes, Python's whitespace set and
   round-half-to-even. */

// Characters Python's str.isspace() / str.split() / re's \s treat as whitespace.
export const WS = '\\t\\n\\v\\f\\r\\x1c-\\x1f \\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000';

// re.split(r"\n\s*\n", text): a blank line separates paragraphs.
export const PARAGRAPH_BREAK = new RegExp(`\\n[${WS}]*\\n`, 'u');

const WS_RUN = new RegExp(`[${WS}]+`, 'u');
const WS_EDGE = new RegExp(`^[${WS}]+|[${WS}]+$`, 'gu');
const ALPHA = /\p{L}/u;
const ALNUM = /[\p{L}\p{N}]/u;
const DIGIT = /[\p{Nd}²³¹⁰⁴-⁹₀-₉]/u;
const UPPER = /\p{Uppercase}/u;
const LOWER = /\p{Lowercase}/u;

export const codePoints = (s) => Array.from(s);
export const cpLength = (s) => codePoints(s).length;
export const firstChar = (s) => codePoints(s)[0] ?? '';

export const isAlpha = (ch) => ALPHA.test(ch);
export const isAlnum = (ch) => ALNUM.test(ch);
export const isDigit = (ch) => DIGIT.test(ch);
export const isUpper = (ch) => UPPER.test(ch);
export const isLower = (ch) => LOWER.test(ch);

/** str.strip() with no arguments. */
export const strip = (s) => s.replace(WS_EDGE, '');

/** str.split() with no arguments: split on whitespace runs, drop empty strings. */
export const splitWords = (s) => s.split(WS_RUN).filter(Boolean);

/** Python's round(): halves go to the even neighbour. */
export function pyRound(x) {
  const floor = Math.floor(x);
  const frac = x - floor;
  if (frac < 0.5) return floor;
  if (frac > 0.5) return floor + 1;
  return floor % 2 === 0 ? floor : floor + 1;
}
