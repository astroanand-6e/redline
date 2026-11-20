/* Read text out of a PDF with pdf.js, page by page, in the visitor's browser. pdf.js is loaded on
   first use so the page itself stays light. Raw page text then goes through engine/clean.js. */
import { MAX_PAGES } from './engine/clean.js';

const PDFJS_URL = new URL('../vendor/pdfjs/pdf.min.mjs', import.meta.url).href;
const WORKER_URL = new URL('../vendor/pdfjs/pdf.worker.min.mjs', import.meta.url).href;
// Glyph data for the 14 standard PDF fonts (Helvetica, Times...), which PDFs may use unembedded.
const STANDARD_FONTS_URL = new URL('../vendor/pdfjs/standard_fonts/', import.meta.url).href;
const LINE_JUMP = 0.5; // a vertical move over half the font height starts a new line
const WORD_GAP = 0.12; // a horizontal gap over this share of the font height is a space
const ENDS_WITH_SPACE = /\s$/u;
const STARTS_WITH_SPACE = /^\s/u;

export class ExtractionError extends Error {}

let pdfjs = null;

async function loadPdfjs() {
  if (!pdfjs) {
    pdfjs = await import(PDFJS_URL);
    pdfjs.GlobalWorkerOptions.workerSrc = WORKER_URL;
  }
  return pdfjs;
}

/** Rebuild one page's text, with newlines, from pdf.js text items. */
export function pageText(items) {
  let out = '';
  let lastY = null;
  let lastEnd = null;
  let lastHeight = 0;
  for (const item of items) {
    if (typeof item.str !== 'string') continue; // marked-content markers carry no text
    const [, , c, d, x, y] = item.transform;
    const own = Math.hypot(c, d) || item.height || 1;
    // Measure jumps against the larger of the two fonts, so a small superscript stays on its line.
    const height = Math.max(own, lastHeight);
    const atLineStart = out === '' || out.endsWith('\n');
    if (!atLineStart && lastY !== null && Math.abs(y - lastY) > height * LINE_JUMP) {
      out += '\n';
    } else if (!atLineStart && lastEnd !== null && x - lastEnd > height * WORD_GAP
      && !ENDS_WITH_SPACE.test(out) && !STARTS_WITH_SPACE.test(item.str)) {
      out += ' ';
    }
    out += item.str;
    if (item.hasEOL) out += '\n';
    if (item.str) {
      lastY = y;
      lastEnd = x + item.width;
      lastHeight = own;
    }
  }
  return out;
}

function readError(error) {
  if (error?.name === 'PasswordException') {
    return new ExtractionError('This PDF is password-protected. Remove the password and try again.');
  }
  return new ExtractionError('Could not read this PDF. It may be damaged or encrypted.');
}

function pageRange(total, first, last) {
  const from = first || 1;
  const to = Math.min(last || total, total);
  if (!Number.isInteger(from) || from < 1 || from > to) {
    throw new ExtractionError(`Invalid page range ${from}-${to} for a ${total}-page PDF.`);
  }
  if (to - from + 1 > MAX_PAGES) throw new ExtractionError(`Please pick at most ${MAX_PAGES} pages at a time.`);
  return [from, to];
}

/**
 * Raw text of each page in the inclusive 1-based range.
 * `data` is a Uint8Array; pdf.js takes ownership of its buffer, so pass a fresh copy each call.
 */
export async function extractPages(data, { first = 1, last = 0, onProgress } = {}) {
  const lib = await loadPdfjs();
  const task = lib.getDocument({
    data, isEvalSupported: false, disableFontFace: true, standardFontDataUrl: STANDARD_FONTS_URL,
  });
  let doc;
  try {
    doc = await task.promise;
  } catch (error) {
    await task.destroy();
    throw readError(error);
  }
  try {
    const [from, to] = pageRange(doc.numPages, first, last);
    const pages = [];
    for (let n = from; n <= to; n += 1) {
      const page = await doc.getPage(n);
      pages.push(pageText((await page.getTextContent()).items));
      page.cleanup();
      onProgress?.(n - from + 1, to - from + 1);
    }
    return { pages, total: doc.numPages };
  } catch (error) {
    if (error instanceof ExtractionError) throw error;
    throw new ExtractionError('Could not extract text from this PDF.');
  } finally {
    await task.destroy();
  }
}
