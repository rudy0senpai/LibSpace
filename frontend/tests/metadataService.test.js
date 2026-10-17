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
  assert.equal(first.cover_url, 'https://cover');
  assert.deepEqual(second, first);
  assert.equal(calls, 1);
});

test('falls back to Open Library when Google has no metadata', async () => {
  clearMetadataCache();
  const urls = [];
  const fetchImpl = async (url, options) => { urls.push([url, options.method || 'GET']); return options.method === 'HEAD' ? { ok: true } : response({}); };
  const result = await lookupBookMetadata('9780306406157', { fetchImpl });
  assert.match(result.cover_url, /covers\.openlibrary\.org\/b\/isbn\/9780306406157-L\.jpg/);
  assert.equal(urls.length, 2);
});

test('rejects malformed ISBN without making a request and avoids retrying cached misses', async () => {
  clearMetadataCache();
  let calls = 0;
  const fetchImpl = async (_url, options) => { calls += 1; return options.method === 'HEAD' ? { ok: false } : response({ items: [] }); };
  assert.equal(await lookupBookMetadata('not-isbn', { fetchImpl }), null);
  assert.equal(await lookupBookMetadata('9780306406157', { fetchImpl }), null);
  assert.equal(await lookupBookMetadata('9780306406157', { fetchImpl }), null);
  assert.equal(calls, 2); // Google lookup and one Open Library cover check; the miss is cached.
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
  assert.equal(calls, 2);
});

test('handles provider HTTP failures with a cached no-result', async () => {
  clearMetadataCache();
  let calls = 0;
  const fetchImpl = async () => { calls += 1; return response({}, false); };
  assert.equal(await lookupBookMetadata('9780306406157', { fetchImpl }), null);
  assert.equal(await lookupBookMetadata('9780306406157', { fetchImpl }), null);
  assert.equal(calls, 2);
});
