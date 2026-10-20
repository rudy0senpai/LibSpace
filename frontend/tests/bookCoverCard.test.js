import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { build } from 'esbuild';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const require = createRequire(import.meta.url);
const entry = resolve('src/components/catalogue/BookCoverCard.jsx');
const { outputFiles } = await build({
  entryPoints: [entry], bundle: true, write: false, format: 'cjs', platform: 'node',
  external: ['react', 'react/jsx-runtime'],
  define: { 'import.meta.env.VITE_API_URL': '"http://localhost:5001"' },
});
const moduleValue = { exports: {} };
new Function('require', 'module', 'exports', 'React', outputFiles[0].text)(require, moduleValue, moduleValue.exports, React);
const BookCoverCard = moduleValue.exports.default;
const getCoverCandidates = moduleValue.exports.getCoverCandidates;

test('cover candidates prefer a curated cover and then use the Flask-validated cover response', () => {
  assert.deepEqual(getCoverCandidates(
    { cover_image_ref: '/covers/curated.jpg' },
    { cover_url: 'https://books.google.test/cover.jpg', fallback_cover_url: 'https://covers.openlibrary.test/isbn.jpg' },
  ), ['/covers/curated.jpg', 'https://books.google.test/cover.jpg']);
  assert.deepEqual(getCoverCandidates({}, null), []);
});

test('collapsed book card exposes an accessible toggle and a consistent local cover placeholder', () => {
  const markup = renderToStaticMarkup(React.createElement(BookCoverCard, {
    book: { id: 'book-1', title: 'Accessible Example', author: 'A. Writer', category: 'Computing', available: 2, total: 4 },
    actions: React.createElement('button', { type: 'button' }, 'Request Book'),
  }));
  assert.match(markup, /aria-expanded="false"/);
  assert.match(markup, /aria-hidden="true" inert=""/);
  assert.match(markup, /aria-label="Expand details for Accessible Example"/);
  assert.match(markup, /aria-label="No cover available for Accessible Example"/);
  assert.match(markup, /Computing/);
  assert.match(markup, /Request Book/);
});

test('controlled expansion renders accessible details for the virtual grid', () => {
  const markup = renderToStaticMarkup(React.createElement(BookCoverCard, {
    expanded: true,
    book: { id: 'book-2', title: 'Portrait Example', author: 'B. Writer', category: 'History', available: 1, total: 2 },
  }));
  assert.match(markup, /aria-expanded="true"/);
  assert.match(markup, /aria-hidden="false"/);
  assert.match(markup, /class="book-cover-card is-expanded"/);
  assert.match(markup, /Portrait Example/);
  assert.match(markup, /B\. Writer/);
});

test('cover images remain lazy-loaded and asynchronously decoded', () => {
  const markup = renderToStaticMarkup(React.createElement(BookCoverCard, {
    book: { id: 'book-3', title: 'Cover Example', cover_image_ref: 'https://covers.example/cover.jpg' },
  }));
  assert.match(markup, /src="https:\/\/covers\.example\/cover\.jpg"/);
  assert.match(markup, /loading="lazy"/);
  assert.match(markup, /decoding="async"/);
});

test('expanded card does not expose legacy provenance JSON as a user description', () => {
  const markup = renderToStaticMarkup(React.createElement(BookCoverCard, {
    expanded: true,
    book: {
      id: 'book-provenance', title: 'Provenance Example',
      description: '[Academic CSV provenance: {"dataset":"catalogue.csv"}]',
    },
  }));
  assert.doesNotMatch(markup, /Academic CSV provenance|catalogue\.csv/);
  assert.match(markup, /No description available\./);
});

test('cover and placeholder CSS reserve a 2:3 portrait frame without cropping', () => {
  const css = readFileSync(resolve('src/styles/dashboard-glass.css'), 'utf8');
  assert.match(css, /\.book-cover-card__image-frame\s*\{[^}]*aspect-ratio:\s*2\s*\/\s*3/s);
  assert.match(css, /\.book-cover-card__image-frame img\s*\{[^}]*object-fit:\s*contain/s);
  assert.match(css, /\.book-cover-card__placeholder\s*\{[^}]*width:\s*100%[^}]*height:\s*100%/s);
  assert.match(css, /\.book-cover-card__subject\s*\{[^}]*flex:\s*0 0 34px/s);
});

test('tablet-width catalogue filters wrap instead of forcing page overflow', () => {
  const css = readFileSync(resolve('src/styles/dashboard-glass.css'), 'utf8');
  const tabletRules = css.match(/@media\s*\(max-width:\s*850px\)\s*\{([\s\S]*?)\n\}/);
  assert.ok(tabletRules, 'an 850px responsive ruleset exists');
  assert.match(tabletRules[1], /\.dashboard-app \.prototype-search\s*\{[^}]*flex-wrap:\s*wrap/s);
});
