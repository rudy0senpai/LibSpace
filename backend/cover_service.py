"""ISBN-first, conservative book-cover lookup with SQLite-backed caching."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
import urllib.error
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


def title_matches(source, remote, threshold=0.92):
    left_words = normalize_text(source).split()
    right_words = normalize_text(remote).split()
    if not left_words or not right_words:
        return False
    if left_words == right_words:
        return True
    if len(left_words) == 1 and len(left_words[0]) >= 4 and right_words[0] == left_words[0]:
        return True
    if len(left_words) > 1 and right_words[:len(left_words)] == left_words:
        return True
    return title_score(source, remote) >= threshold


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


def error_reason(exc):
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return f"network error ({type(exc.reason).__name__})"
    if isinstance(exc, TimeoutError):
        return "timeout"
    return type(exc).__name__


def image_is_usable(content_type, data):
    """Reject HTML/error bodies and tiny provider placeholder images."""
    if not data or not content_type.startswith("image/"):
        return False
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        return width > 1 and height > 1 and b"IDAT" in data[33:] and len(data) > 41
    if data.startswith((b"GIF87a", b"GIF89a")) and len(data) >= 14:
        return (int.from_bytes(data[6:8], "little") > 1
                and int.from_bytes(data[8:10], "little") > 1 and b"," in data[10:])
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        if data[12:16] == b"VP8X" and len(data) >= 30:
            width = 1 + int.from_bytes(data[24:27], "little")
            height = 1 + int.from_bytes(data[27:30], "little")
            return width > 1 and height > 1
        if data[12:16] == b"VP8 " and len(data) >= 30 and data[23:26] == b"\x9d\x01\x2a":
            width = int.from_bytes(data[26:28], "little") & 0x3fff
            height = int.from_bytes(data[28:30], "little") & 0x3fff
            return width > 1 and height > 1
        if data[12:16] == b"VP8L" and len(data) >= 25 and data[20] == 0x2f:
            width = 1 + data[21] + ((data[22] & 0x3f) << 8)
            height = 1 + ((data[22] >> 6) & 0x03) + (data[23] << 2) + ((data[24] & 0x0f) << 10)
            return width > 1 and height > 1
        return False
    if not data.startswith(b"\xff\xd8"):
        return False
    # Parse JPEG frame dimensions from the bounded response prefix.
    pos = 2
    dimensions = None
    while pos + 4 <= len(data):
        while pos < len(data) and data[pos] != 0xFF:
            pos += 1
        while pos < len(data) and data[pos] == 0xFF:
            pos += 1
        if pos >= len(data):
            break
        marker = data[pos]
        pos += 1
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if pos + 2 > len(data):
            break
        segment_length = int.from_bytes(data[pos:pos + 2], "big")
        if segment_length < 2 or pos + segment_length > len(data):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if segment_length < 7:
                return False
            height = int.from_bytes(data[pos + 3:pos + 5], "big")
            width = int.from_bytes(data[pos + 5:pos + 7], "big")
            dimensions = (width, height)
        if marker == 0xDA:
            scan_start = pos + segment_length
            scan_prefix = data[scan_start:scan_start + 4]
            return bool(dimensions and dimensions[0] > 1 and dimensions[1] > 1
                        and len(scan_prefix) >= 3 and not scan_prefix.startswith(b"\xff\xd9"))
        pos += segment_length
    return False


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
            except urllib.error.HTTPError as exc:
                if exc.code < 500 and exc.code != 429:
                    exc.close()
                    raise
                if attempt >= self.retries:
                    exc.close()
                    raise
                logging.getLogger(__name__).warning("Cover provider retry %d/%d after HTTP %d", attempt + 1, self.retries, exc.code)
                exc.close()
                self.sleep(delay)
                delay *= 2
            except Exception as exc:
                if attempt >= self.retries:
                    raise
                logging.getLogger(__name__).warning("Cover provider retry %d/%d after %s", attempt + 1, self.retries, error_reason(exc))
                self.sleep(delay)
                delay *= 2

    def _json(self, url):
        request = urllib.request.Request(url, headers={"User-Agent": "LibSphere/1.0 book-cover service"})
        with self._open(request) as response:
            return json.load(response)

    def _image_exists(self, url):
        request = urllib.request.Request(url, headers={
            "User-Agent": "LibSphere/1.0 book-cover service",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            "Range": "bytes=0-65536",
        })
        with self._open(request) as response:
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            status = getattr(response, "status", 200)
            if not 200 <= status < 300:
                return False
            body = response.read(65537)
            return image_is_usable(content_type, body)

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
        if not title_matches(book.title, remote_title, threshold=0.84) or not authors_match("; ".join(a.name for a in book.authors), remote_authors):
            return None
        cover_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
        if self._image_exists(cover_url):
            return {"cover_url": cover_url, "source": "openlibrary_isbn", "edition_title": remote_title}
        return None

    def _google_items(self, query):
        url = "https://www.googleapis.com/books/v1/volumes?q=" + urllib.parse.quote(query) + "&maxResults=10"
        data = self._json(url)
        return data.get("items", []) if isinstance(data, dict) else []

    def _trusted_google(self, book, volume, isbn=None, excluded_urls=None):
        info = volume.get("volumeInfo", {}) if isinstance(volume, dict) else {}
        if not info:
            return None
        identifiers = {normalize_isbn(x.get("identifier")) for x in info.get("industryIdentifiers", []) if isinstance(x, dict)}
        if isbn and isbn not in identifiers:
            return None
        if not title_matches(book.title, info.get("title", ""), threshold=(0.84 if isbn else 0.92)):
            return None
        if not authors_match("; ".join(a.name for a in book.authors), info.get("authors", [])):
            return None
        source_publisher = normalize_text(book.publisher.name if book.publisher else "")
        result_publisher = normalize_text(info.get("publisher", ""))
        if source_publisher and result_publisher and source_publisher not in result_publisher and result_publisher not in source_publisher:
            return None
        source_year = book.publication_year
        year_match = re.search(r"(?:1[4-9]\d{2}|20\d{2}|2100)", str(info.get("publishedDate", "")))
        if source_year and year_match and source_year != int(year_match.group(0)):
            return None
        source_edition = normalize_text(book.edition or "")
        result_edition = normalize_text(info.get("edition", ""))
        if source_edition and result_edition and source_edition != result_edition:
            return None
        image_links = info.get("imageLinks") or {}
        image = next((image_links.get(size) for size in ("extraLarge", "large", "medium", "small", "thumbnail", "smallThumbnail") if image_links.get(size)), None)
        if not image:
            return None
        image = image.replace("http://", "https://", 1)
        parsed_image = urllib.parse.urlsplit(image)
        if parsed_image.scheme != "https" or not parsed_image.netloc:
            return None
        if image in (excluded_urls or set()) or not self._image_exists(image):
            return None
        return {"cover_url": image, "source": "google_books_isbn" if isbn else "google_books_title_author", "edition_title": info.get("title", "")}

    def _title_author_fallback(self, book, excluded_urls=None):
        authors = "; ".join(author.name for author in book.authors)
        if not book.title or not authors:
            return None
        query = f'intitle:"{book.title}" inauthor:"{authors.split(";")[0].strip()}"'
        for volume in self._google_items(query):
            result = self._trusted_google(book, volume, excluded_urls=excluded_urls)
            if result:
                return result
        extras = []
        if book.category:
            extras.append(book.category.name)
        if book.description:
            extras.extend(re.findall(r"[A-Za-z]{4,}", book.description)[:4])
        if extras:
            refined = query + " " + " ".join(extras[:5])
            for volume in self._google_items(refined):
                result = self._trusted_google(book, volume, excluded_urls=excluded_urls)
                if result:
                    result["source"] = "google_books_title_author_subject"
                    return result
        return None

    def _openlibrary_title_author_fallback(self, book, excluded_urls=None):
        authors = "; ".join(author.name for author in book.authors)
        if not book.title or not authors:
            return None
        params = urllib.parse.urlencode({
            "title": book.title,
            "author": authors.split(";")[0].strip(),
            "fields": "title,author_name,publisher,first_publish_year,cover_i,isbn,edition_name",
            "limit": 10,
        })
        data = self._json("https://openlibrary.org/search.json?" + params)
        docs = data.get("docs", []) if isinstance(data, dict) else []
        for doc in docs:
            if not isinstance(doc, dict) or not title_matches(book.title, doc.get("title", ""), threshold=0.92):
                continue
            if not authors_match(authors, doc.get("author_name", [])):
                continue
            source_publisher = normalize_text(book.publisher.name if book.publisher else "")
            remote_publishers = [normalize_text(value) for value in doc.get("publisher", []) if normalize_text(value)]
            if source_publisher and remote_publishers and not any(source_publisher in value or value in source_publisher for value in remote_publishers):
                continue
            source_year = book.publication_year
            remote_year = doc.get("first_publish_year")
            if source_year and remote_year and int(source_year) != int(remote_year):
                continue
            source_edition = normalize_text(book.edition or "")
            remote_edition = normalize_text(doc.get("edition_name", ""))
            if source_edition and remote_edition and source_edition != remote_edition:
                continue
            remote_isbns = {normalize_isbn(value) for value in doc.get("isbn", []) if value}
            isbn = normalize_isbn(book.isbn)
            if valid_isbn(isbn) and remote_isbns and isbn not in remote_isbns:
                continue
            try:
                cover_id = int(doc.get("cover_i"))
            except (TypeError, ValueError):
                continue
            if cover_id <= 0:
                continue
            url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg?default=false"
            if url in (excluded_urls or set()) or not self._image_exists(url):
                continue
            return {"cover_url": url, "source": "openlibrary_title_author", "edition_title": doc.get("title", "")}
        return None

    def _find(self, book, isbn, excluded_urls=None):
        provider_failed = False
        excluded_urls = excluded_urls or set()
        if valid_isbn(isbn):
            try:
                result = self._isbn_lookup(book, isbn)
                if result and result["cover_url"] not in excluded_urls:
                    return result, False
            except Exception as exc:
                provider_failed = True
                logging.getLogger(__name__).warning("Open Library ISBN lookup failed for %s (%s)", isbn, error_reason(exc))
            try:
                for volume in self._google_items("isbn:" + isbn):
                    result = self._trusted_google(book, volume, isbn=isbn, excluded_urls=excluded_urls)
                    if result:
                        return result, provider_failed
            except Exception as exc:
                provider_failed = True
                logging.getLogger(__name__).warning("Google Books ISBN lookup failed for %s (%s)", isbn, error_reason(exc))
        try:
            result = self._title_author_fallback(book, excluded_urls=excluded_urls)
            if result:
                return result, provider_failed
        except Exception as exc:
            provider_failed = True
            logging.getLogger(__name__).warning("Google Books title/author lookup failed for %s (%s)", isbn or "unknown", error_reason(exc))
        try:
            result = self._openlibrary_title_author_fallback(book, excluded_urls=excluded_urls)
            if result:
                return result, provider_failed
        except Exception as exc:
            provider_failed = True
            logging.getLogger(__name__).warning("Open Library title/author lookup failed for %s (%s)", isbn or "unknown", error_reason(exc))
        return None, provider_failed

    def lookup(self, book, db_session, cache_model, refresh=False, reported_failure=False, validate_existing=False):
        isbn = normalize_isbn(book.isbn)
        key = cover_cache_key(book)
        now = self.clock()

        cached = db_session.get(cache_model, key)
        cached_expiry = as_utc(cached.expires_at) if cached else None
        cache_is_fresh = bool(cached_expiry and cached_expiry > as_utc(now))
        existing_cover = book.cover_image_ref
        browser_failure_cached = bool(cached and cached.error and cached.error.startswith("Browser reported failed cover"))

        if cache_is_fresh and not refresh and (
            browser_failure_cached
            or (reported_failure and cached.status in {"FAILED", "NO_MATCH"})
        ):
            return {"matched": False, "cover_url": None, "source": None, "cached": True,
                    "failed": cached.status == "FAILED", "error": cached.error}

        if existing_cover and not refresh and not reported_failure and not validate_existing:
            if cached and cached.status == "MATCHED" and cached.cover_url == existing_cover:
                return {"matched": True, "cover_url": existing_cover, "source": cached.source, "cached": True, "failed": False}
            cache = cached or cache_model(cache_key=key, isbn=isbn or None)
            cache.status = "MATCHED"
            cache.cover_url = existing_cover
            cache.source = "existing_catalogue_cover"
            cache.error = None
            cache.attempted_at = now
            cache.expires_at = now + timedelta(days=30)
            db_session.add(cache)
            db_session.commit()
            return {"matched": True, "cover_url": existing_cover, "source": cache.source, "cached": True, "failed": False}

        if cache_is_fresh and not refresh and not validate_existing and not reported_failure:
            return {"matched": cached.status == "MATCHED", "cover_url": cached.cover_url, "source": cached.source,
                    "cached": True, "failed": cached.status == "FAILED", "error": cached.error}

        excluded_urls = set()
        if reported_failure and existing_cover:
            excluded_urls.add(existing_cover)
        elif validate_existing and existing_cover and not refresh:
            try:
                if self._image_exists(existing_cover):
                    cache = cached or cache_model(cache_key=key, isbn=isbn or None)
                    cache.status = "MATCHED"
                    cache.cover_url = existing_cover
                    cache.source = cached.source if cached and cached.source else "existing_catalogue_cover"
                    cache.error = None
                    cache.attempted_at = now
                    cache.expires_at = now + timedelta(days=30)
                    db_session.add(cache)
                    db_session.commit()
                    return {"matched": True, "cover_url": existing_cover, "source": cache.source, "cached": False, "failed": False}
            except Exception as exc:
                logging.getLogger(__name__).warning("Existing cover validation failed for %s (%s)", isbn or "unknown", type(exc).__name__)
            excluded_urls.add(existing_cover)

        rejected_existing = bool(existing_cover and existing_cover in excluded_urls)
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
                if reported_failure and existing_cover and cached.cover_url == existing_cover:
                    return {"matched": False, "cover_url": None, "source": None, "cached": True, "failed": cached.status == "FAILED", "error": cached.error}
                return {"matched": cached.status == "MATCHED", "cover_url": cached.cover_url, "source": cached.source, "cached": True, "failed": cached.status == "FAILED", "error": cached.error}
            return {"matched": False, "cover_url": None, "source": None, "cached": False, "error": "Concurrent lookup did not produce a cache record"}
        try:
            match, provider_failed = self._find(book, isbn, excluded_urls=excluded_urls)
            preserved_existing = bool(existing_cover and not rejected_existing)
            status = "MATCHED" if match or preserved_existing else "FAILED" if provider_failed else "NO_MATCH"
            expiry = now + timedelta(days=30) if status == "MATCHED" else now + timedelta(seconds=max(60, self.failed_ttl))
            cache = cached or cache_model(cache_key=key, isbn=isbn or None)
            cache.status = status
            cache.cover_url = match["cover_url"] if match else (existing_cover if preserved_existing else None)
            cache.source = match["source"] if match else ("existing_catalogue_cover" if preserved_existing else None)
            if status == "MATCHED":
                cache.error = None
            elif rejected_existing:
                cache.error = "Browser reported failed cover; " + ("provider unavailable" if provider_failed else "no reliable alternate match")
            else:
                cache.error = "Provider unavailable" if provider_failed else "No reliable provider match"
            cache.attempted_at = now
            cache.expires_at = expiry
            if match and (not existing_cover or refresh or rejected_existing):
                book.cover_image_ref = match["cover_url"]
            db_session.add(cache)
            db_session.commit()
            if match:
                logging.getLogger(__name__).info("Book cover matched isbn=%s source=%s", isbn or "unknown", match["source"])
            elif status != "MATCHED":
                logging.getLogger(__name__).warning("Book cover unresolved isbn=%s reason=%s retry_after=%s", isbn or "unknown", cache.error, cache.expires_at.isoformat() if cache.expires_at else "none")
            return {"matched": status == "MATCHED", "cover_url": cache.cover_url, "source": cache.source, "cached": False, "failed": status == "FAILED", "error": cache.error}
        except Exception as exc:
            db_session.rollback()
            failed = cached or cache_model(cache_key=key, isbn=isbn or None)
            failed.status = "FAILED"
            failed.cover_url = None if rejected_existing else existing_cover
            failed.source = None if rejected_existing else ("existing_catalogue_cover" if existing_cover else None)
            failed.error = type(exc).__name__
            failed.attempted_at = now
            failed.expires_at = now + timedelta(seconds=max(60, self.failed_ttl))
            db_session.add(failed)
            db_session.commit()
            logging.getLogger(__name__).warning("Book cover lookup failed isbn=%s reason=%s retry_after=%s", isbn or "unknown", failed.error, failed.expires_at.isoformat())
            return {"matched": not rejected_existing and bool(existing_cover), "cover_url": failed.cover_url, "source": failed.source, "cached": False, "failed": True, "error": failed.error}
        finally:
            with self._lock:
                self._inflight.pop(key, None)
                event.set()


cover_service = CoverService()
