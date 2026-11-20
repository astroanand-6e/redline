import assert from 'node:assert/strict';
import { test } from 'node:test';

import { formatClock, formatDuration, indexAtFrame, planReading } from '../../web/js/engine/plan.js';
import { pyRound } from '../../web/js/engine/pystr.js';

test('plan starts are a running sum of frame counts', () => {
  const plan = planReading('One two, three. Four five six.', { startWpm: 300, endWpm: 600 });
  assert.equal(plan.tokens.length, 6);
  assert.equal(plan.starts[0], 0);
  plan.counts.forEach((n, i) => {
    if (i) assert.equal(plan.starts[i], plan.starts[i - 1] + plan.counts[i - 1]);
  });
  assert.equal(plan.totalFrames, plan.counts.reduce((a, b) => a + b, 0));
  assert.equal(plan.seconds, plan.totalFrames / 30);
  assert.ok(Object.isFrozen(plan));
});

test('empty text gives an empty plan', () => {
  const plan = planReading('   \n\n ', { startWpm: 300, endWpm: 300 });
  assert.equal(plan.tokens.length, 0);
  assert.equal(plan.totalFrames, 0);
});

test('indexAtFrame finds the word on screen', () => {
  const starts = [0, 6, 10, 18];
  const cases = [[0, 0], [5, 0], [6, 1], [9, 1], [10, 2], [17, 2], [18, 3], [999, 3]];
  for (const [frame, index] of cases) assert.equal(indexAtFrame(starts, frame), index, `frame ${frame}`);
  assert.equal(indexAtFrame([], 5), 0);
});

test('durations and clock read like the Python app', () => {
  assert.equal(formatDuration(21.7), '22 s');
  assert.equal(formatDuration(750.4), '12 min 30 s');
  assert.equal(formatDuration(62.5), '1 min 02 s');
  assert.equal(formatClock(65.9), '1:05');
  assert.equal(formatClock(-1), '0:00');
});

test('pyRound rounds halves to even like Python', () => {
  assert.deepEqual([0.5, 1.5, 2.5, -1.5, 2.4, 2.6].map(pyRound), [0, 2, 2, -2, 2, 3]);
});
