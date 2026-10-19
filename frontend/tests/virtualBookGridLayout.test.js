import test from 'node:test';
import assert from 'node:assert/strict';
import { getVirtualBookGridLayout } from '../src/pages/student/virtualBookGridLayout.js';

test('portrait layout adapts columns and preserves 2:3 covers at available grid widths', () => {
  for (const [width, expectedColumns] of [[390, 1], [768, 2], [1024, 3], [1440, 4]]) {
    const layout = getVirtualBookGridLayout(width, 12);
    assert.equal(layout.columns, expectedColumns, `${width}px container`);
    assert.equal(layout.coverHeight / layout.coverWidth, 1.5, `${width}px cover ratio`);
    assert.equal(layout.rowHeights.length, Math.ceil(12 / expectedColumns));
    assert.equal(layout.spacerHeight, layout.rowHeights.reduce((sum, height) => sum + height, 0));
  }
});

test('expanding a card reserves its details row without overlapping later virtual rows', () => {
  const collapsed = getVirtualBookGridLayout(390, 4);
  const expanded = getVirtualBookGridLayout(390, 4, { 0: true });
  assert.ok(expanded.rowHeights[0] > collapsed.rowHeights[0]);
  assert.equal(expanded.rowTops[1], expanded.rowHeights[0]);
  assert.equal(expanded.spacerHeight, expanded.rowHeights.reduce((sum, height) => sum + height, 0));
});

test('empty results produce no virtual rows', () => {
  const layout = getVirtualBookGridLayout(390, 0);
  assert.equal(layout.rowHeights.length, 0);
  assert.equal(layout.spacerHeight, 0);
});
