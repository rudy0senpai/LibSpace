"""ISBN-first, conservative book-cover lookup with SQLite-backed caching."""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher


def normalize_isbn(value):
    return re.sub(r"[^0-9Xx]", "", value or "").upper()


def valid_isbn(value):
    isbn = normalize_isbn(value)
    if len(isbn) == 10 and isbn[:9].isdigit() and (isbn[-1].isdigit() or isbn[-1] == "X"):
        return sum((10-i)*(10 if char == "X" else int(char)) for i, char in enumerate(isbn)) % 11 == 0
    if len(isbn) == 13 and isbn.isdigit():
        return sum(int(char)*(1 if i % 2 == 0 else 3) for i, char in enumerate(isbn)) % 10 == 0
    return False


def normalize_text(value):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).split())


def title_score(source, remote):
    left, right = normalize_text(source), normalize_text(remote)
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def authors_match(source_authors, remote_authors):
    sources = [normalize_text(x) for x in re.split(r"[;,]", source_authors or "") if normalize_text(x)]
    remotes = [normalize_text(x) for x in (remote_authors or []) if normalize_text(x)]
    for source in sources:
        source_tokens = source.split()
        for remote in remotes:
            remote_tokens = remote.split()
            if source == remote or SequenceMatcher(None, source, remote).ratio() >= 0.82:
                return True
            if source_tokens and remote_tokens and source_tokens[-1] == remote_tokens[-1] and source_tokens[0][0] == remote_tokens[0][0]:
                return True
    return False


def isbn_values(data):
    values = data.get("isbn_13", []) + data.get("isbn_10", [])
    return {normalize_isbn(value) for value in values if value}


def cover_cache_key(book):
    isbn = normalize_isbn(book.isbn)
    identity = isbn if valid_isbn(isbn) else normalize_text(book.title) + "|" + normalize_text(";".join(author.name for author in book.authors))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def as_utc(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


class CoverService:
    def __init__(self, opener=None, sleep=time.sleep, clock=None, min_interval=None, timeout=None, retries=None, failed_ttl=None):
        self.opener = opener or urllib.request.urlopen
        self.sleep = sleep
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.min_interval = float(min_interval if min_interval is not None else os.getenv("COVERS_MIN_REQUEST_INTERVAL", "1"))
        self.timeout = float(timeout if timeout is not None else os.getenv("COVERS_TIMEOUT_SECONDS", "5"))
        self.retries = int(retries if retries is not None else os.getenv("COVERS_RETRIES", "2"))
        self.failed_ttl = int(failed_ttl if failed_ttl is not None else os.getenv("COVERS_FAILED_CACHE_TTL_SECONDS", "86400"))
        self._lock = threading.RLock()
        self._last_request = 0.0
        self._inflight = {}

    def _open(self, request):
        with self._lock:
            wait = self.min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                self.sleep(wait)
            self._last_request = time.monotonic()
        delay = 0.5
        for attempt in range(self.retries + 1):
            try:
                return self.opener(request, timeout=self.timeout)
            except Exception:
                if attempt >= self.retries:
                    raise
                self.sleep(delay)
                delay *= 2

    def _json(self, url):
        request = urllib.request.Request(url, headers={"User-Agent": "LibSphere/1.0 book-cover service"})
        with self._open(request) as response:
            return json.load(response)

    def _image_exists(self, url):
        request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "LibSphere/1.0 book-cover service"})
        with self._open(request) as response:
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            return 200 <= getattr(response, "status", 200) < 300 and content_type.startswith("image/")

    def _isbn_lookup(self, book, isbn):
        query = urllib.parse.quote("ISBN:" + isbn, safe=":")
        data = self._json(f"https://openlibrary.org/api/books?bibkeys={query}&format=json&jscmd=data")
        edition = data.get("ISBN:" + isbn) if isinstance(data, dict) else None
        if not isinstance(edition, dict):
            return None
        identifiers = edition.get("identifiers", {})
        editions_isbns = set()
        for key in ("isbn_13", "isbn_10"):
            editions_isbns.update(normalize_isbn(value) for value in identifiers.get(key, []) if value)
        if isbn not in editions_isbns:
            return None
        remote_title = edition.get("title", "")
        remote_authors = [str(author.get("name", "")) for author in edition.get("authors", []) if isinstance(author, dict)]
        if title_score(book.title, remote_title) < 0.84 or not authors_match("; ".join(a.name for a in book.authors), remote_authors):
            return None
        cover_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
        if self._image_exists(cover_url):
            return {"cover_url": cover_url, "source": "openlibrary_isbn", "edition_title": remote_title}
        return None

    def _google_items(self, query):
        url = "https://www.googleapis.com/books/v1/volumes?q=" + urllib.parse.quote(query) + "&maxResults=10"
        data = self._json(url)
        return data.get("items", []) if isinstance(data, dict) else []

    def _trusted_google(self, book, volume, isbn=None):
        info = volume.get("volumeInfo", {}) if isinstance(volume, dict) else {}
        if not info:
            return None
        identifiers = {normalize_isbn(x.get("identifier")) for x in info.get("industryIdentifiers", []) if isinstance(x, dict)}
        if isbn and isbn not in identifiers:
            return None
        if title_score(book.title, info.get("title", "")) < (0.84 if isbn else 0.92):
            return None
        if not authors_match("; ".join(a.name for a in book.authors), info.get("authors", [])):
            return None
        if not isbn:
            source_publisher = normalize_text(book.publisher.name if book.publisher else "")
            result_publisher = normalize_text(info.get("publisher", ""))
            if source_publisher and result_publisher and source_publisher not in result_publisher and result_publisher not in source_publisher:
                return None
            source_year = book.publication_year
            year_match = re.search(r"(?:1[4-9]\d{2}|20\d{2}|2100)", str(info.get("publishedDate", "")))
            if source_year and year_match and source_year != int(year_match.group(0)):
                return None
        image = (info.get("imageLinks") or {}).get("thumbnail") or (info.get("imageLinks") or {}).get("smallThumbnail")
        if not image:
            return None
        image = image.replace("http://", "https://", 1)
        if self._image_exists(image):
            return {"cover_url": image, "source": "google_books_isbn" if isbn else "google_books_title_author", "edition_title": info.get("title", "")}
        return None

    def _title_author_fallback(self, book):
        authors = "; ".join(author.name for author in book.authors)
        if not book.title or not authors:
            return None
        query = f'intitle:"{book.title}" inauthor:"{authors.split(";")[0].strip()}"'
        for volume in self._google_items(query):
            result = self._trusted_google(book, volume)
            if result:
                return result
        # Subjects/description are supplementary query terms; a match still requires title + author.
        extras = []
        if book.category:
            extras.append(book.category.name)
        if book.description:
            extras.extend(re.findall(r"[A-Za-z]{4,}", book.description)[:4])
        if extras:
            refined = query + " " + " ".join(extras[:5])
            for volume in self._google_items(refined):
                result = self._trusted_google(book, volume)
                if result:
                    result["source"] = "google_books_title_author_subject"
                    return result
        return None

    def _find(self, book, isbn):
        provider_failed = False
        if valid_isbn(isbn):
            try:
                result = self._isbn_lookup(book, isbn)
                if result:
                    return result, False
            except Exception:
                provider_failed = True
            try:
                for volume in self._google_items("isbn:" + isbn):
                    result = self._trusted_google(book, volume, isbn=isbn)
                    if result:
                        return result, provider_failed
            except Exception:
                provider_failed = True
        try:
            result = self._title_author_fallback(book)
            if result:
                return result, provider_failed
        except Exception:
            provider_failed = True
        return None, provider_failed

    def lookup(self, book, db_session, cache_model, refresh=False):
        isbn = normalize_isbn(book.isbn)
        key = cover_cache_key(book)
        now = self.clock()

        cached = db_session.get(cache_model, key)
        if book.cover_image_ref and not refresh:
            if cached and cached.status == "MATCHED" and cached.cover_url == book.cover_image_ref:
                return {"matched": True, "cover_url": book.cover_image_ref, "source": cached.source, "cached": True, "failed": False}
            cache = cached or cache_model(cache_key=key, isbn=isbn or None)
            cache.status = "MATCHED"
            cache.cover_url = book.cover_image_ref
            cache.source = "existing_catalogue_cover"
            cache.error = None
            cache.attempted_at = now
            cache.expires_at = now + timedelta(days=30)
            db_session.add(cache)
            db_session.commit()
            return {"matched": True, "cover_url": book.cover_image_ref, "source": cache.source, "cached": True, "failed": False}
        existing_cover = book.cover_image_ref
        if cached and not refresh and as_utc(cached.expires_at) and as_utc(cached.expires_at) > as_utc(now):
            return {"matched": cached.status == "MATCHED", "cover_url": cached.cover_url, "source": cached.source, "cached": True, "failed": cached.status == "FAILED", "error": cached.error}

        with self._lock:
            event = self._inflight.get(key)
            is_leader = event is None
            if is_leader:
                event = threading.Event()
                self._inflight[key] = event
        if not is_leader:
            event.wait(timeout=self.timeout * (self.retries + 2) * 3)
            db_session.expire_all()
            cached = db_session.get(cache_model, key)
            if cached:
                return {"matched": cached.status == "MATCHED", "cover_url": cached.cover_url, "source": cached.source, "cached": True, "failed": cached.status == "FAILED", "error": cached.error}
            return {"matched": False, "cover_url": None, "source": None, "cached": False, "error": "Concurrent lookup did not produce a cache record"}
        try:
            match, provider_failed = self._find(book, isbn)
            status = "MATCHED" if match or existing_cover else "FAILED" if provider_failed else "NO_MATCH"
            expiry = now + timedelta(days=30) if status == "MATCHED" else now + timedelta(seconds=max(60, self.failed_ttl))
            cache = cached or cache_model(cache_key=key, isbn=isbn or None)
            cache.status = status
            cache.cover_url = match["cover_url"] if match else existing_cover
            cache.source = match["source"] if match else ("existing_catalogue_cover" if existing_cover else None)
            cache.error = None if status == "MATCHED" else ("Provider unavailable" if provider_failed else "No reliable provider match")
            cache.attempted_at = now
            cache.expires_at = expiry
            if match and not book.cover_image_ref:
                book.cover_image_ref = match["cover_url"]
            elif match and refresh:
                book.cover_image_ref = match["cover_url"]
            db_session.add(cache)
            db_session.commit()
            return {"matched": status == "MATCHED", "cover_url": cache.cover_url, "source": cache.source, "cached": False, "failed": status == "FAILED", "error": cache.error}
        except Exception as exc:
            db_session.rollback()
            failed = cached or cache_model(cache_key=key, isbn=isbn or None)
            failed.status = "FAILED"
            failed.cover_url = None
            failed.source = None
            failed.error = type(exc).__name__
            failed.attempted_at = now
            failed.expires_at = now + timedelta(seconds=max(60, self.failed_ttl))
            db_session.add(failed)
            db_session.commit()
            return {"matched": False, "cover_url": None, "source": None, "cached": False, "error": failed.error}
        finally:
            with self._lock:
                self._inflight.pop(key, None)
                event.set()


cover_service = CoverService()
