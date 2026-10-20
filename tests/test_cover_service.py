import unittest
import threading
import time
import struct
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.error
import urllib.request
from datetime import datetime, timezone
from flask import Flask

from backend.models import db, Book, Author, Category, Publisher, CoverLookupCache
from backend.cover_service import CoverService, valid_isbn, cover_cache_key


def png_bytes(width=4, height=6):
    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)
    header = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    pixels = b''.join(b'\x00' + bytes((210, 180, 140)) * width for _ in range(height))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')


class StubCoverService(CoverService):
    def __init__(self, isbn_result=None, google_results=None, openlibrary_result=None, provider_error=False, **kwargs):
        super().__init__(sleep=lambda _seconds: None, min_interval=0, **kwargs)
        self.isbn_result = isbn_result
        self.google_results = google_results or {}
        self.openlibrary_result = openlibrary_result
        self.provider_error = provider_error
        self.calls = []

    def _isbn_lookup(self, book, isbn):
        self.calls.append(('isbn', isbn))
        if self.provider_error:
            raise TimeoutError('provider timeout')
        return self.isbn_result

    def _google_items(self, query):
        self.calls.append(('google', query))
        if self.provider_error:
            raise TimeoutError('provider timeout')
        return self.google_results.get(query, [])

    def _openlibrary_title_author_fallback(self, book, excluded_urls=None):
        self.calls.append(('openlibrary', book.isbn))
        if self.provider_error:
            raise TimeoutError('provider timeout')
        return self.openlibrary_result

    def _image_exists(self, _url):
        return True


class CoverServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask('cover-service-tests')
        cls.app.config.update(SQLALCHEMY_DATABASE_URI='sqlite://', SQLALCHEMY_TRACK_MODIFICATIONS=False)
        db.init_app(cls.app)

    def setUp(self):
        self.ctx = self.app.app_context(); self.ctx.push()
        db.create_all()
        author = Author(name='A. Writer')
        book = Book(isbn='9780131103627', title='The C Programming Language', language='eng')
        book.authors.append(author)
        db.session.add(book); db.session.commit()
        self.book = book

    def tearDown(self):
        db.session.remove(); db.drop_all(); self.ctx.pop()

    def test_checksum_valid_and_cache_key_stable(self):
        self.assertTrue(valid_isbn('9780131103627'))
        self.assertFalse(valid_isbn('9780131103628'))
        self.assertEqual(cover_cache_key(self.book), cover_cache_key(self.book))

    def test_isbn_is_primary_and_source_is_persisted(self):
        service = StubCoverService(isbn_result={'cover_url':'https://covers.openlibrary.org/b/isbn/9780131103627-L.jpg','source':'openlibrary_isbn'})
        result = service.lookup(self.book, db.session, CoverLookupCache)
        self.assertTrue(result['matched'])
        self.assertEqual(service.calls[0][0], 'isbn')
        self.assertEqual(self.book.cover_image_ref, result['cover_url'])
        cached = db.session.get(CoverLookupCache, cover_cache_key(self.book))
        self.assertEqual(cached.source, 'openlibrary_isbn')
        again = service.lookup(self.book, db.session, CoverLookupCache)
        self.assertEqual(again['source'], 'openlibrary_isbn')
        self.assertTrue(again['cached'])

    def test_title_author_fallback_rejects_unrelated_result(self):
        mismatched = {'volumeInfo': {'title':'A different title', 'authors':['Other Person'], 'imageLinks': {'thumbnail':'https://books.example/cover.jpg'}}}
        matching = {'volumeInfo': {'title':'The C Programming Language', 'authors':['A. Writer'], 'imageLinks': {'thumbnail':'http://books.example/match.jpg'}}}
        isbn_query = 'isbn:9780131103627'
        title_query = 'intitle:"The C Programming Language" inauthor:"A. Writer"'
        service = StubCoverService(google_results={isbn_query:[], title_query:[mismatched, matching]})
        result = service.lookup(self.book, db.session, CoverLookupCache)
        self.assertTrue(result['matched'])
        self.assertEqual(result['source'], 'google_books_title_author')
        self.assertEqual(result['cover_url'], 'https://books.example/match.jpg')

    def test_title_author_fallback_also_rejects_publisher_or_year_disagreement(self):
        self.book.publisher = Publisher(name='Original Publisher')
        self.book.publication_year = 2000
        db.session.commit()
        mismatched = {'volumeInfo': {
            'title':'The C Programming Language', 'authors':['A. Writer'],
            'publisher':'Different Publisher', 'publishedDate':'2021',
            'imageLinks': {'thumbnail':'https://books.example/wrong-edition.jpg'},
        }}
        isbn_query = 'isbn:9780131103627'
        title_query = 'intitle:"The C Programming Language" inauthor:"A. Writer"'
        service = StubCoverService(google_results={isbn_query:[], title_query:[mismatched]})
        result = service.lookup(self.book, db.session, CoverLookupCache)
        self.assertFalse(result['matched'])
        self.assertFalse(result['failed'])

    def test_description_and_subject_terms_refine_search_but_identity_is_still_required(self):
        category = Category(name='Computing')
        self.book.category = category
        self.book.description = 'Systems programming and compiler architecture.'
        db.session.commit()
        refined = 'intitle:"The C Programming Language" inauthor:"A. Writer" Computing Systems programming compiler architecture'
        matching = {'volumeInfo': {'title':'The C Programming Language', 'authors':['A. Writer'], 'imageLinks': {'thumbnail':'https://books.example/cover.jpg'}}}
        service = StubCoverService(google_results={'isbn:9780131103627':[], 'intitle:"The C Programming Language" inauthor:"A. Writer"':[], refined:[matching]})
        result = service.lookup(self.book, db.session, CoverLookupCache)
        self.assertTrue(result['matched'])
        self.assertEqual(result['source'], 'google_books_title_author_subject')

    def test_retry_uses_exponential_backoff(self):
        calls, delays = [], []
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *_args): pass
        def opener(_request, timeout):
            calls.append(timeout)
            if len(calls) < 3: raise TimeoutError('temporary provider timeout')
            return Response()
        service = CoverService(opener=opener, sleep=delays.append, min_interval=0, timeout=4, retries=2)
        response = service._open(urllib.request.Request('https://provider.example/test'))
        self.assertEqual(response.status, 200)
        self.assertEqual(calls, [4, 4, 4])
        self.assertEqual(delays, [0.5, 1.0])

    def test_concurrent_lookups_for_same_isbn_are_deduplicated(self):
        started, release = threading.Event(), threading.Event()
        calls = []
        match = {'cover_url':'https://covers.example/shared.jpg','source':'openlibrary_isbn'}
        class SlowService(StubCoverService):
            def _isbn_lookup(self, book, isbn):
                calls.append(isbn); started.set(); release.wait(2); return match
        class CacheRow:
            def __init__(self, cache_key, isbn=None):
                self.cache_key=cache_key; self.isbn=isbn; self.status=None; self.cover_url=None; self.source=None; self.error=None; self.attempted_at=None; self.expires_at=None
        class Session:
            def __init__(self): self.rows={}; self.lock=threading.Lock()
            def get(self, _model, key):
                with self.lock: return self.rows.get(key)
            def add(self, item):
                with self.lock: self.rows[item.cache_key]=item
            def commit(self): pass
            def expire_all(self): pass
        book = type('BookValue', (), {'isbn':'9780131103627','title':'The C Programming Language','authors':[type('AuthorValue', (), {'name':'A. Writer'})()],'cover_image_ref':None})()
        session=Session(); service=SlowService(isbn_result=match)
        results=[]
        first=threading.Thread(target=lambda: results.append(service.lookup(book, session, CacheRow)))
        second=threading.Thread(target=lambda: results.append(service.lookup(book, session, CacheRow)))
        first.start(); self.assertTrue(started.wait(1)); second.start(); time.sleep(0.05); release.set()
        first.join(2); second.join(2)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(result['matched'] for result in results))

    def test_no_reliable_match_is_cached_and_provider_failure_is_distinguished(self):
        service = StubCoverService(google_results={'isbn:9780131103627':[], 'intitle:"The C Programming Language" inauthor:"A. Writer"':[]})
        first = service.lookup(self.book, db.session, CoverLookupCache)
        second = service.lookup(self.book, db.session, CoverLookupCache)
        self.assertFalse(first['matched'])
        self.assertFalse(first['failed'])
        self.assertTrue(second['cached'])
        self.assertEqual(db.session.get(CoverLookupCache, cover_cache_key(self.book)).status, 'NO_MATCH')

        db.session.query(CoverLookupCache).delete(); db.session.commit()
        failing = StubCoverService(provider_error=True)
        failed = failing.lookup(self.book, db.session, CoverLookupCache)
        self.assertFalse(failed['matched'])
        self.assertTrue(failed['failed'])
        self.assertEqual(db.session.get(CoverLookupCache, cover_cache_key(self.book)).status, 'FAILED')

    def test_curated_cover_is_not_overwritten_without_explicit_refresh(self):
        self.book.cover_image_ref = 'https://curated.example/cover.jpg'
        db.session.commit()
        service = StubCoverService(isbn_result={'cover_url':'https://provider.example/new.jpg','source':'openlibrary_isbn'})
        reused = service.lookup(self.book, db.session, CoverLookupCache)
        self.assertEqual(reused['cover_url'], 'https://curated.example/cover.jpg')
        self.assertEqual(service.calls, [])
        refreshed = service.lookup(self.book, db.session, CoverLookupCache, refresh=True)
        self.assertEqual(refreshed['cover_url'], 'https://provider.example/new.jpg')
        self.assertEqual(self.book.cover_image_ref, 'https://provider.example/new.jpg')


    def test_openlibrary_isbn_response_is_verified_and_uses_isbn_cover(self):
        service = CoverService(sleep=lambda _seconds: None, min_interval=0, retries=0)
        service._json = lambda _url: {
            'ISBN:9780131103627': {
                'identifiers': {'isbn_13': ['9780131103627']},
                'title': 'The C Programming Language',
                'authors': [{'name': 'A. Writer'}],
            }
        }
        service._image_exists = lambda _url: True
        result = service._isbn_lookup(self.book, '9780131103627')
        self.assertEqual(result['source'], 'openlibrary_isbn')
        self.assertEqual(result['cover_url'], 'https://covers.openlibrary.org/b/isbn/9780131103627-L.jpg?default=false')

    def test_openlibrary_miss_falls_through_to_google_isbn(self):
        volume = {'volumeInfo': {
            'title': self.book.title, 'authors': ['A. Writer'],
            'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': self.book.isbn}],
            'imageLinks': {'thumbnail': 'https://books.example/cover.jpg'},
        }}
        service = StubCoverService(google_results={'isbn:9780131103627': [volume]})
        result = service.lookup(self.book, db.session, CoverLookupCache)
        self.assertTrue(result['matched'])
        self.assertEqual(result['source'], 'google_books_isbn')
        self.assertEqual(service.calls[:2], [('isbn', self.book.isbn), ('google', 'isbn:' + self.book.isbn)])

    def test_google_uses_best_available_cover_variant_and_https(self):
        volume = {'volumeInfo': {
            'title': self.book.title, 'authors': ['A. Writer'],
            'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': self.book.isbn}],
            'imageLinks': {
                'thumbnail': 'https://books.example/small.jpg',
                'extraLarge': 'http://books.example/large.jpg',
            },
        }}
        result = StubCoverService(google_results={'isbn:9780131103627': [volume]}).lookup(self.book, db.session, CoverLookupCache)
        self.assertEqual(result['cover_url'], 'https://books.example/large.jpg')

    def test_invalid_isbn_uses_verified_title_author_fallback(self):
        self.book.isbn = '9780131103628'
        db.session.commit()
        query = 'intitle:"The C Programming Language" inauthor:"A. Writer"'
        volume = {'volumeInfo': {
            'title': self.book.title, 'authors': ['A. Writer'],
            'imageLinks': {'thumbnail': 'https://books.example/match.jpg'},
        }}
        service = StubCoverService(google_results={query: [volume]})
        result = service.lookup(self.book, db.session, CoverLookupCache)
        self.assertTrue(result['matched'])
        self.assertEqual(result['source'], 'google_books_title_author')
        self.assertEqual(service.calls, [('google', query)])

    def test_reported_broken_cover_is_excluded_and_failure_is_cached(self):
        old_url = 'https://covers.example/broken.jpg'
        self.book.cover_image_ref = old_url
        db.session.commit()
        service = StubCoverService()
        result = service.lookup(self.book, db.session, CoverLookupCache, reported_failure=True)
        self.assertFalse(result['matched'])
        self.assertIsNone(result['cover_url'])
        self.assertEqual(self.book.cover_image_ref, old_url)
        cached = db.session.get(CoverLookupCache, cover_cache_key(self.book))
        self.assertIn(cached.status, {'NO_MATCH', 'FAILED'})
        before = list(service.calls)
        again = service.lookup(self.book, db.session, CoverLookupCache, reported_failure=True)
        self.assertTrue(again['cached'])
        self.assertIsNone(again['cover_url'])
        self.assertEqual(service.calls, before)

    def test_broken_cover_can_be_replaced_only_by_a_different_verified_match(self):
        old_url = 'https://covers.example/broken.jpg'
        new_url = 'https://books.example/new.jpg'
        self.book.cover_image_ref = old_url
        db.session.commit()
        volume = {'volumeInfo': {
            'title': self.book.title, 'authors': ['A. Writer'],
            'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': self.book.isbn}],
            'imageLinks': {'thumbnail': new_url},
        }}
        service = StubCoverService(
            isbn_result={'cover_url': old_url, 'source': 'openlibrary_isbn'},
            google_results={'isbn:9780131103627': [volume]},
        )
        result = service.lookup(self.book, db.session, CoverLookupCache, reported_failure=True)
        self.assertEqual(result['cover_url'], new_url)
        self.assertEqual(self.book.cover_image_ref, new_url)

    def test_existing_cover_is_validated_when_batch_requests_it(self):
        old_url = 'https://covers.example/broken.jpg'
        new_url = 'https://books.example/new.jpg'
        self.book.cover_image_ref = old_url
        db.session.commit()
        volume = {'volumeInfo': {
            'title': self.book.title, 'authors': ['A. Writer'],
            'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': self.book.isbn}],
            'imageLinks': {'thumbnail': new_url},
        }}
        class BatchService(StubCoverService):
            def _image_exists(self, url):
                return url != old_url
        service = BatchService(google_results={'isbn:9780131103627': [volume]})
        result = service.lookup(self.book, db.session, CoverLookupCache, validate_existing=True)
        self.assertEqual(result['cover_url'], new_url)
        self.assertEqual(self.book.cover_image_ref, new_url)

    def test_expired_failure_cache_is_retried(self):
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        cache = CoverLookupCache(
            cache_key=cover_cache_key(self.book), isbn=self.book.isbn, status='FAILED',
            error='TimeoutError', attempted_at=now - timedelta(days=2), expires_at=now - timedelta(days=1),
        )
        db.session.add(cache); db.session.commit()
        match = {'cover_url': 'https://covers.example/retried.jpg', 'source': 'openlibrary_isbn'}
        service = StubCoverService(isbn_result=match)
        result = service.lookup(self.book, db.session, CoverLookupCache)
        self.assertTrue(result['matched'])
        self.assertIn(('isbn', self.book.isbn), service.calls)

    def test_failed_refresh_never_overwrites_existing_cover(self):
        existing = 'https://curated.example/usable.jpg'
        self.book.cover_image_ref = existing
        db.session.commit()
        result = StubCoverService(provider_error=True).lookup(self.book, db.session, CoverLookupCache, refresh=True)
        self.assertEqual(self.book.cover_image_ref, existing)
        self.assertEqual(result['cover_url'], existing)
        self.assertTrue(result['matched'])

    def test_openlibrary_title_author_fallback_requires_identity_and_uses_cover_id(self):
        service = CoverService(sleep=lambda _seconds: None, min_interval=0, retries=0)
        service._json = lambda _url: {'docs': [{
            'title': self.book.title, 'author_name': ['A. Writer'], 'cover_i': 987654,
            'isbn': [self.book.isbn],
        }]}
        service._image_exists = lambda _url: True
        result = service._openlibrary_title_author_fallback(self.book)
        self.assertEqual(result['source'], 'openlibrary_title_author')
        self.assertEqual(result['cover_url'], 'https://covers.openlibrary.org/b/id/987654-L.jpg?default=false')

    def test_cover_image_validation_follows_redirect_and_rejects_bad_or_missing_images(self):
        image = png_bytes()
        tiny = png_bytes(1, 1)

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/redirect':
                    self.send_response(302); self.send_header('Location', '/cover.png'); self.end_headers(); return
                if self.path == '/cover.png':
                    body, content_type, status = image, 'image/png', 200
                elif self.path == '/bad.jpg':
                    body, content_type, status = b'<html>not an image</html>', 'image/jpeg', 200
                elif self.path == '/tiny.png':
                    body, content_type, status = tiny, 'image/png', 200
                else:
                    body, content_type, status = b'not found', 'text/plain', 404
                self.send_response(status); self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)

            def log_message(self, *_args):
                return

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        service = CoverService(sleep=lambda _seconds: None, min_interval=0, timeout=2, retries=0)
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            self.assertTrue(service._image_exists(base + '/redirect'))
            self.assertFalse(service._image_exists(base + '/bad.jpg'))
            self.assertFalse(service._image_exists(base + '/tiny.png'))
            with self.assertRaises(urllib.error.HTTPError):
                service._image_exists(base + '/missing')
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_cover_image_timeout_is_retried_and_bounded(self):
        calls, delays = [], []

        def opener(request, timeout):
            calls.append((request.get_method(), timeout))
            raise TimeoutError('provider timeout')

        service = CoverService(opener=opener, sleep=delays.append, min_interval=0, timeout=0.25, retries=1)
        with self.assertRaises(TimeoutError):
            service._image_exists('https://covers.example/slow.jpg')
        self.assertEqual(calls, [('GET', 0.25), ('GET', 0.25)])
        self.assertEqual(delays, [0.5])

if __name__ == '__main__':
    unittest.main()
