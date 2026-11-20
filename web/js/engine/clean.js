/* Turn raw PDF page text into readable paragraphs: port of the cleanup half of redline/extract.py.
   Same heuristics, same thresholds, same regexes (with Python's Unicode \s, \d and \w spelled out). */
import {
  PARAGRAPH_BREAK, WS, cpLength, firstChar, isDigit, isLower, isUpper, splitWords, strip,
} from './pystr.js';

export const MAX_PAGES = 400;
const HEADER_MIN_PAGES = 3; // need this many pages before guessing running headers
const HEADER_PAGE_FRACTION = 0.5; // a line on at least this share of pages is a header
const REFERENCES_MIN_POSITION = 0.3; // references heading must come after this share of text
const SHORT_LINE_RATIO = 0.6; // a line under 60% of the median length ends a paragraph
const MIN_MEDIAN_FOR_SHORT_LINES = 30; // characters; skip the heuristic for tiny inputs

const S = `[${WS}]`;
const NOT_S = `[^${WS}]`;
const D = '\\p{Nd}';
const WORD = "[\\p{L}\\p{N}_'-]";

const PAGE_NUMBER = new RegExp(`^(page${S}*)?${D}{1,4}(${S}*(of|/)${S}*${D}{1,4})?$`, 'iu');
const REFERENCES = new RegExp(
  `^${S}*(${D}+\\.?${S}*)?(references|bibliography|works cited|literature cited)${S}*$`, 'iu',
);
const NUMERIC_CITATION = new RegExp(`${S}*\\[${D}+(?:${S}*[,–-]${S}*${D}+)*\\]`, 'gu');
const AUTHOR_YEAR_CITATION = new RegExp(
  `${S}*\\((?:[A-Z]${WORD}+(?: et al\\.)?(?:,? (?:and|&) [A-Z]${WORD}+)?,? ${D}{4}[a-z]?(?:;${S}*)?)+\\)`, 'gu',
);
const NOISE = new RegExp(
  // Bounded quantifiers keep this linear on huge unbroken tokens.
  `${S}*(?:[^${WS}@]{1,64}@[^${WS}@]{1,255}\\.[A-Za-z]{2,}` // emails
  + `|https?://${NOT_S}{1,2000}` // links
  + `|arXiv:${D}{4}\\.${D}{4,5}(?:v${D}+)?)`, // arXiv stamps
  'gu',
);
const FOOTNOTE_MARKS = /[∗†‡§¶]/gu;
const DOUBLE_HYPHEN = /[ \t]*--+[ \t]*/g;
const PARAGRAPH_END = Object.freeze(['.', '!', '?', ':', '"', '”']);
const DIGIT_RUN = new RegExp(`${D}+`, 'gu');

const normaliseLine = (line) => strip(line).toLowerCase().replace(DIGIT_RUN, '#');
const endsParagraph = (text) => PARAGRAPH_END.some((mark) => text.endsWith(mark));

/** Lines that repeat across many pages, like running headers and footers. */
function runningLines(pages) {
  if (pages.length < HEADER_MIN_PAGES) return new Set();
  const counts = new Map();
  for (const page of pages) {
    for (const key of new Set(page.filter((line) => strip(line)).map(normaliseLine))) {
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
  }
  const threshold = Math.max(HEADER_MIN_PAGES, pages.length * HEADER_PAGE_FRACTION);
  return new Set([...counts].filter(([, n]) => n >= threshold).map(([line]) => line));
}

function dropNoise(pages) {
  const running = runningLines(pages);
  return pages.flatMap((page) => [
    ...page.map(strip).filter((line) => !PAGE_NUMBER.test(line) && !running.has(normaliseLine(line))),
    '', // page boundary behaves like a soft break
  ]);
}

function cutReferences(lines) {
  const total = lines.reduce((n, line) => n + cpLength(line), 0) || 1;
  let seen = 0;
  for (let i = 0; i < lines.length; i += 1) {
    if (REFERENCES.test(lines[i]) && seen / total >= REFERENCES_MIN_POSITION) return lines.slice(0, i);
    seen += cpLength(lines[i]);
  }
  return lines;
}

/** Lines shorter than this probably end a paragraph or are headings. */
function shortLineLimit(lines) {
  const lengths = lines.filter(Boolean).map(cpLength).sort((a, b) => a - b);
  if (!lengths.length) return 0;
  const median = lengths[Math.floor(lengths.length / 2)];
  return median >= MIN_MEDIAN_FOR_SHORT_LINES ? median * SHORT_LINE_RATIO : 0;
}

/** Rejoin wrapped lines into paragraphs, undoing end-of-line hyphenation. */
function joinLines(lines) {
  const shortLimit = shortLineLimit(lines);
  const paragraphs = [];
  let current = '';
  let previousLen = 0;
  for (const line of lines) {
    if (!line) {
      if (endsParagraph(current)) {
        paragraphs.push(current);
        current = '';
      }
      continue;
    }
    const first = firstChar(line);
    const startsBlock = isUpper(first) || isDigit(first);
    if (current && previousLen < shortLimit && startsBlock && !current.endsWith('-')) {
      paragraphs.push(current);
      current = '';
    }
    previousLen = cpLength(line);
    if (!current) current = line;
    else if (current.endsWith('-') && isLower(first)) current = current.slice(0, -1) + line;
    else if (current.endsWith('-')) current += line;
    else current += ` ${line}`;
  }
  if (current) paragraphs.push(current);
  return paragraphs.join('\n\n');
}

/** Remove citations plus links, emails, arXiv stamps and footnote marks. */
function stripCitations(text) {
  return [NUMERIC_CITATION, AUTHOR_YEAR_CITATION, NOISE, FOOTNOTE_MARKS]
    .reduce((acc, pattern) => acc.replace(pattern, ''), text);
}

/** Normalise unicode and whitespace, keeping paragraph breaks. */
export function cleanText(text) {
  const normalised = text.normalize('NFKC').replace(/\r\n/g, '\n').replace(/\r/g, '\n')
    .replace(DOUBLE_HYPHEN, '— ');
  return normalised.split(PARAGRAPH_BREAK).map((p) => splitWords(p).join(' ')).filter(Boolean).join('\n\n');
}

/** Turn raw page texts into clean, readable paragraphs. */
export function cleanPages(pages, { skipReferences = false, removeCitations = false } = {}) {
  const lines = dropNoise(pages.map((p) => p.normalize('NFKC').replace(/\r/g, '').split('\n')));
  const kept = skipReferences ? cutReferences(lines) : lines;
  const joined = joinLines(kept);
  return cleanText(removeCitations ? stripCitations(joined) : joined);
}
