import test from 'node:test';
import assert from 'node:assert/strict';
import {
  coverLookupKey,
  getCoverCandidates,
  nextCoverIndex,
  visibleBookDescription,
} from '../src/components/catalogue/coverCardData.js';

test('cover candidates prefer the local record and deduplicate fallback URLs', () => {
  assert.deepEqual(getCoverCandidates(
    { cover_image_ref: 'https://covers.example/local.jpg' },
    { cover_url: 'https://covers.example/fallback.jpg' },
  ), ['https://covers.example/local.jpg', 'https://covers.example/fallback.jpg']);
  assert.deepEqual(getCoverCandidates(
    { cover_image_ref: 'https://covers.example/same.jpg' },
    { cover_url: 'https://covers.example/same.jpg' },
  ), ['https://covers.example/same.jpg']);
});

test('failed image advances once to fallback then stops at the placeholder', () => {
  assert.equal(nextCoverIndex(0, 2), 1);
  assert.equal(nextCoverIndex(1, 2), 2);
  assert.equal(nextCoverIndex(2, 2), 2);
  assert.equal(nextCoverIndex(0, 0), 0);
});

test('a failed provider image gets one backend fallback request after the initial lookup', () => {
  assert.notEqual(coverLookupKey('9780131103627', 'book-1', 0), coverLookupKey('9780131103627', 'book-1', 1));
  assert.equal(coverLookupKey('9780131103627', 'book-1', 1), coverLookupKey('9780131103627', 'book-1', 2));
});

test('legacy provenance JSON is never rendered as a description', () => {
  assert.equal(visibleBookDescription('[Academic CSV provenance: {"dataset":"catalog.csv"}]'), '');
  assert.equal(visibleBookDescription('Academic CSV provenance: {"source":"import"}'), '');
  assert.equal(visibleBookDescription('A real description of the book.'), 'A real description of the book.');
  assert.equal(visibleBookDescription(null), '');
});
