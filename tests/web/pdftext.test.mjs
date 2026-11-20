// PDF reading: line rebuilding from pdf.js items, and the real pdf.js on the sample PDF.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { cleanPages } from '../../web/js/engine/clean.js';
import { ExtractionError, extractPages, pageText } from '../../web/js/pdftext.js';

const fixtures = JSON.parse(readFileSync(new URL('./fixtures.json', import.meta.url), 'utf8'));
const samplePdf = () => new Uint8Array(readFileSync(new URL('../../examples/gettysburg.pdf', import.meta.url)));
const item = (str, x, y, { size = 10, width = str.length * 5, eol = false } = {}) => ({
  str, transform: [size, 0, 0, size, x, y], width, height: size, hasEOL: eol,
});

test('pageText joins items on a line and breaks between lines', () => {
  const text = pageText([
    item('Hello', 0, 100), item('world', 30, 100),
    { type: 'beginMarkedContent' },
    item('Next', 0, 86), item('line', 25, 86, { eol: true }),
    item('', 0, 0, { eol: true }),
  ]);
  assert.equal(text, 'Hello world\nNext line\n\n');
});

test('pageText does not add a space inside a word split across items', () => {
  assert.equal(pageText([item('trans', 0, 50), item('former', 25, 50)]), 'transformer');
  assert.equal(pageText([item('a ', 0, 50), item(' b', 30, 50)]), 'a  b');
});

test('pageText keeps a small superscript on its line', () => {
  const text = pageText([item('10', 0, 100), item('9', 10, 104, { size: 6 }), item('steps', 20, 100)]);
  assert.equal(text, '109 steps');
});

test('pdf.js reads the sample PDF word for word like pypdf', async () => {
  const { pages, total } = await extractPages(samplePdf());
  assert.equal(total, 1);
  const python = fixtures.clean.find((c) => c.skipReferences && c.removeCitations && c.pages.length === 1);
  const js = cleanPages(pages, { skipReferences: true, removeCitations: true });
  assert.deepEqual(js.split(/\s+/), python.expected.split(/\s+/));
});

test('bad PDFs and page ranges give friendly errors', async () => {
  await assert.rejects(extractPages(new Uint8Array([37, 80, 68, 70, 1, 2, 3])), ExtractionError);
  await assert.rejects(extractPages(samplePdf(), { first: 3 }), /Invalid page range 3-1 for a 1-page PDF/);
});
