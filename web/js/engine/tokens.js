/* Split text into display tokens with timing multipliers: port of redline/tokens.py. */
import { PARAGRAPH_BREAK, WS, codePoints, cpLength, isAlpha, isDigit, splitWords, strip } from './pystr.js';

export const SENTENCE_PAUSE = 2.0;
export const COMMA_PAUSE = 1.5;
export const PARAGRAPH_PAUSE = 2.5;
export const NUMBER_PAUSE = 1.3;
const LONG_WORD_START = 8; // letters; longer words get extra time
const LONG_WORD_STEP = 0.05; // extra multiplier per letter beyond LONG_WORD_START
const LONG_WORD_MAX = 1.5;
const SPLIT_HYPHENATED_OVER = 14; // characters; longer hyphenated words are split
const HYPHEN_CHUNK = 10; // target characters per chunk when splitting

const CLOSERS = `"'”’)\\]}»`;
const SENTENCE_END = new RegExp(`[.!?…][${CLOSERS}]*$`, 'u');
const CLAUSE_END = new RegExp(`[,;:—–][${CLOSERS}]*$`, 'u');
const DASH_SPLIT = new RegExp(`(?<=[—–])(?=[^${WS}])`, 'u');

function stripHyphens(word) {
  return word.replace(/^-+|-+$/g, '');
}

/** Break long hyphenated words into chunks no longer than the limit. */
function splitHyphenated(word) {
  if (cpLength(word) <= SPLIT_HYPHENATED_OVER || !stripHyphens(word).includes('-')) return [word];
  const pieces = word.split('-');
  const parts = [...pieces.slice(0, -1).map((p) => `${p}-`), pieces[pieces.length - 1]];
  const chunks = [];
  let current = '';
  for (const part of parts) {
    if (current && cpLength(current) + cpLength(part) > HYPHEN_CHUNK) {
      chunks.push(current);
      current = part;
    } else {
      current += part;
    }
  }
  return current ? [...chunks, current] : chunks;
}

function pieces(word) {
  return word.split(DASH_SPLIT).filter(Boolean).flatMap(splitHyphenated);
}

function pauseFor(text, endsParagraph) {
  let punctuation = 1.0;
  if (endsParagraph) punctuation = PARAGRAPH_PAUSE;
  else if (SENTENCE_END.test(text)) punctuation = SENTENCE_PAUSE;
  else if (CLAUSE_END.test(text)) punctuation = COMMA_PAUSE;

  const chars = codePoints(text);
  const letters = chars.filter(isAlpha).length;
  const length = 1.0 + Math.max(0, letters - LONG_WORD_START) * LONG_WORD_STEP;
  const number = chars.some(isDigit) ? NUMBER_PAUSE : 1.0;
  return punctuation * Math.min(length, LONG_WORD_MAX) * number;
}

/** Turn text into frozen {text, pause} tokens. Blank lines mark paragraph breaks. */
export function tokenize(text) {
  const paragraphs = text.split(PARAGRAPH_BREAK).filter((p) => strip(p));
  return paragraphs.flatMap((paragraph) => {
    const parts = splitWords(paragraph).flatMap(pieces);
    return parts.map((piece, i) => Object.freeze({ text: piece, pause: pauseFor(piece, i === parts.length - 1) }));
  });
}
