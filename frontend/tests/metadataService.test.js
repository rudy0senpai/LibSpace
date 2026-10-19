import test from 'node:test';
import assert from 'node:assert/strict';
import { clearMetadataCache, lookupBookMetadata } from '../src/services/metadataService.js';

const response = (body, ok = true) => ({ ok, status: ok ? 200 : 503, json: async () => body });

test('normalizes ISBN and caches successful Google Books metadata', async () => {
  clearMetadataCache();
  let calls = 0;
  const fetchImpl = async () => { calls += 1; return response({ items: [{ volumeInfo: { title: 'Example', authors: ['A'], description: 'Text', imageLinks: { thumbnail: 'http://cover' } } }] }); };
  const first = await lookupBookMetadata('978-0-306-40615-7', { fetchImpl });
  const second = await lookupBookMetadata('9780306406157', { fetchImpl });
  assert.equal(first.title, 'Example');
  assert.equal(first.cover_url, undefined);
  assert.equal(first.attribution, 'Book metadata from Google Books.');
  assert.deepEqual(second, first);
  assert.equal(calls, 1);
});

test('returns no metadata when Google Books has no metadata; covers are handled by the Flask API', async () => {
  clearMetadataCache();
  const urls = [];
  const fetchImpl = async (url, options) => { urls.push([url, options.method || 'GET']); return response({}); };
  const result = await lookupBookMetadata('9780306406157', { fetchImpl });
  assert.equal(result, null);
  assert.equal(urls.length, 1);
});

test('rejects malformed ISBN without making a request and avoids retrying cached misses', async () => {
  clearMetadataCache();
  let calls = 0;
  const fetchImpl = async (_url, options) => { calls += 1; return options.method === 'HEAD' ? { ok: false } : response({ items: [] }); };
  assert.equal(await lookupBookMetadata('not-isbn', { fetchImpl }), null);
  assert.equal(await lookupBookMetadata('9780306406157', { fetchImpl }), null);
  assert.equal(await lookupBookMetadata('9780306406157', { fetchImpl }), null);
  assert.equal(calls, 1); // Google metadata lookup; the miss is cached.
});

test('provider timeout is handled and cached without retrying', async () => {
  clearMetadataCache();
  let calls = 0;
  const fetchImpl = (_url, { signal }) => new Promise((_, reject) => {
    calls += 1;
    signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true });
  });
  assert.equal(await lookupBookMetadata('9780306406157', { fetchImpl, timeout: 5 }), null);
  assert.equal(await lookupBookMetadata('9780306406157', { fetchImpl, timeout: 5 }), null);
  assert.equal(calls, 1);
});

test('handles provider HTTP failures with a cached no-result', async () => {
  clearMetadataCache();
  let calls = 0;
  const fetchImpl = async () => { calls += 1; return response({}, false); };
  assert.equal(await lookupBookMetadata('9780306406157', { fetchImpl }), null);
  assert.equal(await lookupBookMetadata('9780306406157', { fetchImpl }), null);
  assert.equal(calls, 1);
});
