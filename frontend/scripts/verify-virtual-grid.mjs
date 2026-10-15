import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { build } from 'esbuild';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const require = createRequire(import.meta.url);
const entry = resolve('src/pages/student/VirtualBookGrid.jsx');
const { outputFiles } = await build({
  entryPoints: [entry],
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  external: ['react', 'react/jsx-runtime'],
});
const componentModule = { exports: {} };
new Function('require', 'module', 'exports', 'React', outputFiles[0].text)(
  require,
  componentModule,
  componentModule.exports,
  React,
);
const VirtualBookGrid = componentModule.exports.default;

const total = 1000;
const items = Array.from({ length: total }, (_, id) => ({ id: `book-${id}` }));
const markup = renderToStaticMarkup(
  React.createElement(VirtualBookGrid, {
    items,
    renderItem: (item) => React.createElement(
      'article',
      { key: item.id, 'data-book': item.id, role: 'listitem' },
      item.id,
    ),
  }),
);
const mounted = (markup.match(/data-book=/g) || []).length;
assert.ok(mounted > 0, 'the initial viewport should render some book cards');
assert.ok(mounted <= 20, `expected the initial virtual window to stay under 20 cards; got ${mounted}`);
assert.ok(mounted < total, `expected fewer than all ${total} cards to be rendered`);
const percent = ((mounted / total) * 100).toFixed(1);
console.log(`Initial virtual window: ${mounted}/${total} items (${percent}%) in server-rendered markup.`);
console.log('Scope: deterministic initial-render smoke measurement; it does not profile browser scrolling or runtime performance.');
