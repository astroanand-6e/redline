// The browser engine must give exactly the Python engine's answers (tests/web/fixtures.json).
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { cleanPages, cleanText } from '../../web/js/engine/clean.js';
import { orpIndex, splitAtOrp } from '../../web/js/engine/orp.js';
import { layoutFor } from '../../web/js/engine/style.js';
import { frameCounts, wpmSchedule } from '../../web/js/engine/timing.js';
import { tokenize } from '../../web/js/engine/tokens.js';

const fixtures = JSON.parse(readFileSync(new URL('./fixtures.json', import.meta.url), 'utf8'));
const camel = (key) => key.replace(/_([a-z])/g, (_, c) => c.toUpperCase());

test('fixation letter matches Python for every sample word', () => {
  for (const [word, expected] of fixtures.orp) {
    assert.equal(orpIndex(word), expected, `orp_index(${JSON.stringify(word)})`);
  }
});

test('splitAtOrp works in code points, so emoji stay whole', () => {
  assert.deepEqual(splitAtOrp('🙂abc'), ['🙂a', 'b', 'c']);
  assert.deepEqual(splitAtOrp(''), ['', '', '']);
});

test('tokens and pause multipliers match Python exactly', () => {
  for (const { text, tokens } of fixtures.tokens) {
    const actual = tokenize(text).map((t) => [t.text, t.pause]);
    assert.deepEqual(actual, tokens, `tokenize(${JSON.stringify(text.slice(0, 40))})`);
  }
});

test('wpm schedules match Python, including round-half-to-even plateaus', () => {
  for (const { args, expected } of fixtures.schedules) {
    assert.deepEqual(wpmSchedule(...args), expected, `wpm_schedule(${args})`);
  }
});

test('frame counts match Python frame for frame', () => {
  const tokens = tokenize(fixtures.tokens[0].text);
  for (const { start, end, fps, expected } of fixtures.frameCounts) {
    const wpms = wpmSchedule(tokens.length, start, end);
    assert.deepEqual(frameCounts(tokens, wpms, fps), expected, `${start}->${end} @ ${fps}`);
  }
});

test('frame layouts match Python for every format', () => {
  for (const [key, layout] of Object.entries(fixtures.layouts)) {
    const expected = Object.fromEntries(Object.entries(layout).map(([k, v]) => [camel(k), v]));
    assert.deepEqual({ ...layoutFor(key) }, expected, key);
  }
});

test('page cleanup matches Python for every flag combination', () => {
  for (const { pages, skipReferences, removeCitations, expected } of fixtures.clean) {
    assert.equal(cleanPages(pages, { skipReferences, removeCitations }), expected,
      `skipReferences=${skipReferences} removeCitations=${removeCitations}`);
  }
});

test('cleanText matches Python', () => {
  for (const { text, expected } of fixtures.cleanText) {
    assert.equal(cleanText(text), expected);
  }
});

test('bad input is rejected', () => {
  assert.throws(() => wpmSchedule(3, 0, 300), RangeError);
  assert.throws(() => frameCounts(tokenize('a b'), [300], 30), RangeError);
  assert.throws(() => layoutFor('4:3'), RangeError);
});
