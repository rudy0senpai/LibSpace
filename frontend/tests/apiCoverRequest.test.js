import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { build } from 'esbuild';
import { resolve } from 'node:path';

const require = createRequire(import.meta.url);
const { outputFiles } = await build({
  entryPoints: [resolve('src/services/api.js')],
  bundle: true,
  write: false,
  format: 'cjs',
  platform: 'node',
  define: { 'import.meta.env.VITE_API_URL': '"http://localhost:5001"' },
});
const moduleValue = { exports: {} };
new Function('require', 'module', 'exports', outputFiles[0].text)(require, moduleValue, moduleValue.exports);
const { lookupBookCover } = moduleValue.exports;

test('cover URL load failures are reported to the authenticated backend route', async () => {
  const originalFetch = globalThis.fetch;
  const originalStorage = globalThis.localStorage;
  const requests = [];
  globalThis.localStorage = { getItem: key => key === 'access_token' ? 'test-token' : null };
  globalThis.fetch = async (url, options) => {
    requests.push({ url, options });
    return { ok: true, status: 200, json: async () => ({ status: 'success', data: {} }) };
  };
  try {
    await lookupBookCover('book/1', { failed: true });
    assert.equal(requests[0].url, 'http://localhost:5001/api/books/book%2F1/cover?failed=1');
    assert.equal(requests[0].options.headers.Authorization, 'Bearer test-token');
  } finally {
    globalThis.fetch = originalFetch;
    if (originalStorage === undefined) delete globalThis.localStorage;
    else globalThis.localStorage = originalStorage;
  }
});
