import unittest
import threading
import time
import urllib.request
from datetime import datetime, timezone
from flask import Flask

from backend.models import db, Book, Author, Category, Publisher, CoverLookupCache
from backend.cover_service import CoverService, valid_isbn, cover_cache_key


class StubCoverService(CoverService):
    def __init__(self, isbn_result=None, google_results=None, provider_error=False, **kwargs):
        super().__init__(sleep=lambda _seconds: None, min_interval=0, **kwargs)
        self.isbn_result = isbn_result
        self.google_results = google_results or {}
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


if __name__ == '__main__':
    unittest.main()
