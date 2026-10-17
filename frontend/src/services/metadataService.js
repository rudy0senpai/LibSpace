const cache = new Map();
const timeoutMs = 5000;
const digitsOnly = value => String(value || '').replace(/[^0-9Xx]/g, '').toUpperCase();

async function getJson(url, fetchImpl, timeout) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetchImpl(url, { signal: controller.signal });
    if (!response.ok) throw new Error(`Metadata provider returned HTTP ${response.status}`);
    return await response.json();
  } finally { clearTimeout(timer); }
}

export async function lookupBookMetadata(isbn, { fetchImpl = fetch, timeout = timeoutMs } = {}) {
  const normalized = digitsOnly(isbn);
  if (![10, 13].includes(normalized.length)) return null;
  if (cache.has(normalized)) return cache.get(normalized);
  const task = (async () => {
    let google = null;
    try {
      const data = await getJson(`https://www.googleapis.com/books/v1/volumes?q=isbn:${encodeURIComponent(normalized)}`, fetchImpl, timeout);
      const volume = data.items?.[0]?.volumeInfo;
      if (volume) google = {
        title: volume.title || null, subtitle: volume.subtitle || null,
        authors: Array.isArray(volume.authors) ? volume.authors : [], publisher: volume.publisher || null,
        published_date: volume.publishedDate || null, description: volume.description || null,
        categories: Array.isArray(volume.categories) ? volume.categories : [],
        page_count: Number.isInteger(volume.pageCount) ? volume.pageCount : null,
        isbn: normalized, cover_url: volume.imageLinks?.thumbnail?.replace(/^http:/, 'https:') || null,
        attribution: 'Metadata and cover information from Google Books.'
      };
    } catch { /* continue with Open Library cover fallback */ }
    if (!google?.cover_url) {
      const url = `https://covers.openlibrary.org/b/isbn/${encodeURIComponent(normalized)}-L.jpg?default=false`;
      try {
        const response = await fetchImpl(url, { method: 'HEAD', signal: AbortSignal.timeout(timeout) });
        if (response.ok) google = { ...(google || { isbn: normalized }), cover_url: url, attribution: 'Cover from Open Library.' };
      } catch { /* no cover available */ }
    }
    return google;
  })();
  cache.set(normalized, task);
  try { return await task; }
  catch { return null; }
}

export function clearMetadataCache() { cache.clear(); }
export function normalizeISBN(value) { return digitsOnly(value); }
