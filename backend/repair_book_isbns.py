"""Research, report, and conservatively repair missing LibSphere ISBNs.

Research defaults to dry-run. Only source-correlated, checksum-valid ISBNs are
eligible for transactional application. Provider errors and incomplete searches
remain REVIEW_REQUIRED; they are never treated as evidence for deletion.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_URL = "sqlite:///libsphere_test.db"
DEFAULT_OUTPUT = Path.home() / "T450" / "DataSets" / "LibSphere_isbn_repair"
USER_AGENT = "LibSphereISBNRepair/1.0 (catalogue reconciliation)"
ACTIVE_LOAN_STATES = "'REQUESTED','APPROVED','BORROWED','OVERDUE'"
ACTIVE_RESERVATION_STATES = "'WAITING','ACTIVE'"


def norm(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def norm_person(value: str | None) -> str:
    return re.sub(r"[^\w]+", "", norm(value), flags=re.UNICODE)


def normalize_isbn(value: str | None) -> str | None:
    raw = (value or "").strip().upper()
    if not raw:
        return None
    compact = re.sub(r"[\s-]", "", raw)
    if not re.fullmatch(r"(?:\d{9}[\dX]|\d{13})", compact):
        return None
    if len(compact) == 10:
        return compact if sum((10 - i) * (10 if ch == "X" else int(ch)) for i, ch in enumerate(compact)) % 11 == 0 else None
    return compact if sum(int(ch) * (1 if i % 2 == 0 else 3) for i, ch in enumerate(compact)) % 10 == 0 else None


def database_file(database_url: str) -> Path:
    if not database_url.startswith("sqlite:") or database_url in {"sqlite://", "sqlite:///:memory:"}:
        raise ValueError("ISBN repair accepts only a file-backed SQLite DATABASE_URL.")
    path = database_url.removeprefix("sqlite:///")
    if database_url.startswith("sqlite:////"):
        path = "/" + path
    result = Path(path)
    if not result.is_absolute():
        result = ROOT / "backend" / "instance" / result
    return result.resolve()


def readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def backup_database(database: Path, backup_path: Path) -> dict:
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    src = readonly(database)
    dst = sqlite3.connect(backup_path)
    try:
        src.backup(dst)
        integrity = dst.execute("PRAGMA integrity_check").fetchone()[0]
        fk_errors = dst.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        dst.close()
        src.close()
    if integrity != "ok" or fk_errors:
        raise RuntimeError(f"Backup failed verification: integrity={integrity}, FK errors={len(fk_errors)}")
    digest = hashlib.sha256(backup_path.read_bytes()).hexdigest()
    return {"path": str(backup_path.resolve()), "bytes": backup_path.stat().st_size,
            "sha256": digest, "integrity_check": integrity, "foreign_key_errors": len(fk_errors)}


def load_books(conn: sqlite3.Connection) -> list[dict]:
    sql = """SELECT b.id,b.title,b.subtitle,b.isbn,b.publication_year,b.edition,b.language,
        b.description,b.cover_image_ref,p.name publisher,c.name category,
        (SELECT group_concat(a.name, char(31)) FROM book_authors ba JOIN authors a ON a.id=ba.author_id WHERE ba.book_id=b.id) authors,
        (SELECT count(*) FROM book_copies cp WHERE cp.book_id=b.id) copy_count,
        (SELECT count(*) FROM reservations r WHERE r.book_id=b.id) reservation_count,
        (SELECT count(*) FROM loans l JOIN book_copies cp ON cp.id=l.book_copy_id WHERE cp.book_id=b.id) loan_history_count
        FROM books b LEFT JOIN publishers p ON p.id=b.publisher_id LEFT JOIN categories c ON c.id=b.category_id
        ORDER BY b.title,b.id"""
    cur = conn.execute(sql)
    columns = [d[0] for d in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    for row in rows:
        row["author_list"] = sorted(filter(None, (row.get("authors") or "").split(chr(31))), key=str.casefold)
    return rows


def seed_map(seed_path: Path, books: list[dict]) -> dict[str, dict]:
    if not seed_path.is_file():
        return {}
    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    result = {}
    for source in seed.get("books", []):
        title_key = norm(source.get("title"))
        authors_key = {norm_person(a) for a in source.get("authors", []) if norm_person(a)}
        year = str(source.get("year") or "")
        candidates = [b for b in books if norm(b["title"]) == title_key
                      and {norm_person(a) for a in b["author_list"]} == authors_key
                      and str(b.get("publication_year") or "") == year]
        if len(candidates) == 1 and source.get("openlibrary_work"):
            result[candidates[0]["id"]] = source
    return result


def fetch_json(url: str, cache_dir: Path, min_gap: float, state: dict, timeout: float = 25.0) -> dict:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / (hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json")
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("http_status") == 200:
                return cached
            # Retry cached errors on resume; successful provider results are immutable cache hits.
        except (OSError, json.JSONDecodeError):
            pass
    elapsed = time.time() - state.get("last_request", 0.0)
    if elapsed < min_gap:
        time.sleep(min_gap - elapsed)
    state["last_request"] = time.time()
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            result = {"http_status": response.status, "url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(), "data": payload}
    except HTTPError as exc:
        result = {"http_status": exc.code, "url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                  "error": str(exc), "retry_after": exc.headers.get("Retry-After") if exc.headers else None}
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        result = {"http_status": None, "url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(), "error": f"{type(exc).__name__}: {exc}"}
    cache_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def check_cover(url: str, cache_dir: Path, min_gap: float, state: dict, timeout: float = 25.0) -> dict:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / (hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json")
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("http_status") == 200 and cached.get("content_type", "").startswith("image/"):
                return cached
        except (OSError, json.JSONDecodeError):
            pass
    elapsed = time.time() - state.get("last_request", 0.0)
    if elapsed < min_gap:
        time.sleep(min_gap - elapsed)
    state["last_request"] = time.time()
    request = Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
    try:
        with urlopen(request, timeout=timeout) as response:
            result = {"http_status": response.status, "content_type": response.headers.get("Content-Type", ""),
                      "url": response.geturl(), "checked_at": datetime.now(timezone.utc).isoformat()}
    except HTTPError as exc:
        result = {"http_status": exc.code, "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
                  "url": url, "error": str(exc), "checked_at": datetime.now(timezone.utc).isoformat()}
    except (URLError, TimeoutError, OSError) as exc:
        result = {"http_status": None, "content_type": "", "url": url, "error": f"{type(exc).__name__}: {exc}",
                  "checked_at": datetime.now(timezone.utc).isoformat()}
    cache_path.write_text(json.dumps(result), encoding="utf-8")
    return result


def isbn_from_edition(edition: dict) -> list[str]:
    primary = []
    for value in edition.get("isbn_13", []) or []:
        isbn = normalize_isbn(value)
        if isbn and len(isbn) == 13:
            primary.append(isbn)
    if primary:
        return sorted(set(primary))
    return sorted({isbn for value in (edition.get("isbn_10", []) or []) if (isbn := normalize_isbn(value)) and len(isbn) == 10})


def year_from_date(value: str | None) -> int | None:
    match = re.search(r"\b(1[4-9]\d{2}|20\d{2}|2100)\b", value or "")
    return int(match.group(1)) if match else None


def publisher_compatible(expected: str | None, candidate_publishers: list[str]) -> bool:
    if not expected:
        return True
    left = norm(expected)
    for name in candidate_publishers:
        right = norm(name)
        if left == right or left in right or right in left:
            return True
    return False  # a stored publisher could not be checked against the edition record


def field_compatible(expected: str | None, observed: str | None) -> bool:
    wanted, actual = norm(expected), norm(observed)
    return not wanted or bool(actual and (wanted == actual or wanted in actual or actual in wanted))


def title_compatible(expected: str, edition: dict) -> bool:
    wanted = norm(expected)
    variants = [edition.get("title", ""), edition.get("full_title", ""), edition.get("subtitle", "")]
    for text in variants:
        candidate = norm(text)
        if candidate == wanted or candidate.startswith(wanted + ":") or candidate.startswith(wanted + " "):
            return True
    return False


def classify_work_editions(book: dict, source: dict, result: dict) -> dict:
    base = {"status": "REVIEW_REQUIRED", "resolved_isbn": "", "candidate_isbns": [],
            "edition_evidence": "", "publisher_evidence": "", "publication_year_evidence": "",
            "source_urls": [], "confidence": "LOW", "cover_candidate_url": "", "reason": "No verified edition candidate."}
    work = source.get("openlibrary_work", "")
    editions_url = f"https://openlibrary.org{work}/editions.json?limit=100"
    base["source_urls"] = [f"{ROOT / 'database' / 'seed' / 'books_catalog.json'} (Open Library work key: {work})", editions_url]
    if result.get("http_status") != 200:
        base["reason"] = f"Open Library edition lookup failed ({result.get('http_status') or result.get('error')}); retained, not classified NOT_FOUND."
        return base
    editions = result.get("data", {}).get("entries", [])
    expected_year = int(book["publication_year"]) if book.get("publication_year") else None
    matched = []
    for ed in editions:
        edition_work_keys = [ref.get("key") for ref in (ed.get("works") or [])]
        if work not in edition_work_keys:
            continue
        if not title_compatible(book["title"], ed):
            continue
        pub_year = year_from_date(ed.get("publish_date"))
        if expected_year and pub_year != expected_year:
            continue
        publishers = ed.get("publishers") or []
        if not publisher_compatible(book.get("publisher"), publishers):
            continue
        # Seed work key is tied to the exact title/author/year tuple in the local source catalog.
        isbns = isbn_from_edition(ed)
        for isbn in isbns:
            matched.append((isbn, ed, pub_year, publishers))
    by_isbn = {}
    for isbn, ed, pub_year, publishers in matched:
        by_isbn.setdefault(isbn, []).append((ed, pub_year, publishers))
    candidates = sorted(by_isbn)
    base["candidate_isbns"] = candidates
    if len(candidates) == 1:
        isbn = candidates[0]
        editions_for_isbn = by_isbn[isbn]
        # Multiple editions sharing one ISBN are a single identifier, but report all edition evidence.
        ed, pub_year, publishers = editions_for_isbn[0]
        cover_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
        base.update({"status": "VERIFIED", "resolved_isbn": isbn, "confidence": "HIGH", "cover_candidate_url": cover_url,
                     "edition_evidence": f"Open Library edition {ed.get('key','')} title={ed.get('title','')!r}; work={work}; year={pub_year}; ISBN checksum valid.",
                     "publisher_evidence": "; ".join(publishers),
                     "publication_year_evidence": str(pub_year or ""),
                     "reason": "Unique checksum-valid ISBN on an exact local Open Library work/title/author/year mapping."})
    elif len(candidates) > 1:
        base["reason"] = "Multiple distinct ISBN candidates match the mapped work/year; edition/format cannot be distinguished from the local record."
        base["edition_evidence"] = "; ".join(f"{isbn}: {items[0][0].get('key','')} {items[0][0].get('title','')} ({items[0][1]})" for isbn, items in by_isbn.items())
    else:
        base["reason"] = "No checksum-valid ISBN matched this Open Library work and exact recorded year; absence is not proof of no-ISBN edition."
    return base


def research_generated_query(book: dict) -> str:
    query = f'intitle:"{book["title"]}"'
    authors = book.get("author_list") or []
    if authors:
        query += " inauthor:" + " ".join(f'"{author}"' for author in authors)
    params = urlencode({"q": query, "maxResults": 10, "printType": "books"})
    return "https://www.googleapis.com/books/v1/volumes?" + params


def openlibrary_search_query(book: dict, alternative: bool = False) -> str:
    params = {"title": book["title"], "limit": 10,
              "fields": "title,author_name,publisher,first_publish_year,edition_key,isbn,subtitle,edition_count"}
    if book.get("author_list") and not alternative:
        params["author"] = " ".join(book["author_list"])
    return "https://openlibrary.org/search.json?" + urlencode(params)


def classify_search_candidates(book: dict, openlibrary: dict, google: dict | None = None) -> dict:
    ol_url = openlibrary.get("url", "")
    google_url = (google or {}).get("url", "")
    decision = {"status": "REVIEW_REQUIRED", "resolved_isbn": "", "candidate_isbns": [], "confidence": "LOW",
                "edition_evidence": "", "publisher_evidence": "", "publication_year_evidence": "",
                "source_urls": [u for u in (ol_url, google_url) if u], "cover_candidate_url": "",
                "reason": "Title/author search candidates need exact-edition corroboration; retained."}
    ol_candidates = {}
    if openlibrary.get("http_status") == 200:
        docs = openlibrary.get("data", {}).get("docs", [])
        expected_authors = {norm_person(a) for a in book.get("author_list", [])}
        for doc in docs:
            doc_authors = {norm_person(a) for a in doc.get("author_name", [])}
            year = doc.get("first_publish_year")
            if (norm(doc.get("title")) != norm(book["title"])
                    or (expected_authors and not expected_authors.issubset(doc_authors))
                    or (book.get("publication_year") and year != int(book["publication_year"]))
                    or not publisher_compatible(book.get("publisher"), doc.get("publisher", []))
                    or not field_compatible(book.get("subtitle"), doc.get("subtitle"))
                    or not field_compatible(book.get("edition"), doc.get("edition"))):
                continue
            for value in doc.get("isbn", []) or []:
                isbn = normalize_isbn(value)
                if isbn:
                    ol_candidates.setdefault(isbn, []).append(doc)
    google_candidates = {}
    if google and google.get("http_status") == 200:
        for item in google.get("data", {}).get("items", []) or []:
            volume = item.get("volumeInfo", {})
            authors = {norm_person(a) for a in volume.get("authors", [])}
            expected_authors = {norm_person(a) for a in book.get("author_list", [])}
            year = year_from_date(volume.get("publishedDate"))
            if (norm(volume.get("title")) != norm(book["title"])
                    or (expected_authors and not expected_authors.issubset(authors))
                    or (book.get("publication_year") and year != int(book["publication_year"]))
                    or not publisher_compatible(book.get("publisher"), [volume.get("publisher", "")] if volume.get("publisher") else [])):
                continue
            for entry in volume.get("industryIdentifiers", []) or []:
                isbn = normalize_isbn(entry.get("identifier"))
                if isbn:
                    google_candidates.setdefault(isbn, []).append(volume)
    common = set(ol_candidates) & set(google_candidates)
    decision["candidate_isbns"] = sorted(set(ol_candidates) | set(google_candidates))
    if len(common) == 1:
        isbn = next(iter(common))
        decision.update({"status": "VERIFIED", "resolved_isbn": isbn, "confidence": "HIGH",
                         "edition_evidence": "Exact title/author/year/publisher candidate and ISBN corroborated by Google Books and Open Library.",
                         "publisher_evidence": book.get("publisher") or "Provider publisher metadata matched catalogue.",
                         "publication_year_evidence": str(book.get("publication_year") or ""),
                         "cover_candidate_url": f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false",
                         "reason": "One checksum-valid ISBN was independently corroborated by both providers."})
    elif decision["candidate_isbns"]:
        if openlibrary.get("http_status") != 200 or google is None or google.get("http_status") != 200:
            decision["reason"] = "Provider candidate(s) exist, but a required source failed or was skipped; cross-provider verification is incomplete. Retained for review."
        else:
            decision["reason"] = "One or more provider candidates exist, but exact ISBN/edition corroboration is not unique; manual review required."
    elif openlibrary.get("http_status") != 200 or google is None or google.get("http_status") != 200:
        decision["reason"] = "At least one provider search failed or was skipped; API errors/skips are not treated as NOT_FOUND. Retained for review."
    else:
        decision["reason"] = "No exact provider candidate in this query; alternate spellings/subtitles and publisher search remain uncompleted. Retained for review."
    return decision


def report_fields() -> list[str]:
    return ["book_id", "title", "authors", "catalogue_publication_year", "catalogue_publisher", "catalogue_edition",
            "catalogue_subtitle", "original_isbn", "cover_original_ref", "resolved_isbn", "candidate_isbns", "status", "confidence",
            "edition_evidence", "publisher_evidence", "publication_year_evidence", "source_urls", "cover_candidate_url",
            "cover_status", "cover_content_type", "action_taken", "action_timestamp", "reason", "copy_count", "loan_history_count", "reservation_count"]


def atomic_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp, path)


def safe_to_delete(conn: sqlite3.Connection, book_id: str) -> tuple[bool, str]:
    copies = conn.execute("SELECT count(*) FROM book_copies WHERE book_id=?", (book_id,)).fetchone()[0]
    reservations = conn.execute("SELECT count(*) FROM reservations WHERE book_id=?", (book_id,)).fetchone()[0]
    loans = conn.execute("SELECT count(*) FROM loans l JOIN book_copies c ON c.id=l.book_copy_id WHERE c.book_id=?", (book_id,)).fetchone()[0]
    if copies or loans or reservations:
        return False, f"Retained: {copies} physical copies, {loans} loan-history rows, {reservations} reservations depend on book."
    # Only association rows explicitly configured with CASCADE are allowed to be removed by FK enforcement.
    for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        for fk in conn.execute(f'PRAGMA foreign_key_list("{table}")'):
            if fk[2] == "books" and fk[3] == "id" and fk[6].upper() != "CASCADE":
                n = conn.execute(f'SELECT count(*) FROM "{table}" WHERE "{fk[3]}"=?', (book_id,)).fetchone()[0]
                if n:
                    return False, f"Retained: {n} references in {table} block deletion."
    return True, "No copy, loan, reservation, or non-cascade book references; safe under current schema retention rules."


def verify_cached_candidate(row: dict, book: dict, out_dir: Path) -> dict | None:
    if row.get("confidence") != "HIGH":
        return None
    current_authors = {norm_person(author) for author in book.get("author_list", [])}
    report_authors = {norm_person(author) for author in (row.get("authors") or "").split(";")}
    if (norm(row.get("title")) != norm(book.get("title"))
            or current_authors != report_authors
            or str(row.get("catalogue_publication_year") or "") != str(book.get("publication_year") or "")
            or norm(row.get("catalogue_publisher")) != norm(book.get("publisher"))
            or norm(row.get("catalogue_edition")) != norm(book.get("edition"))
            or norm(row.get("catalogue_subtitle")) != norm(book.get("subtitle"))):
        return None
    urls = [part.strip() for part in (row.get("source_urls") or "").split("|")]
    edition_url = next((u for u in urls if u.startswith("https://openlibrary.org/works/") and "/editions.json?limit=100" in u), None)
    if not edition_url:
        return None
    cache_path = out_dir / "cache" / "openlibrary" / (hashlib.sha256(edition_url.encode("utf-8")).hexdigest() + ".json")
    if not cache_path.is_file():
        return None
    try:
        source_response = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    mapping = seed_map(ROOT / "database" / "seed" / "books_catalog.json", [book])
    seed_source = mapping.get(book["id"])
    if not seed_source:
        return None
    checked = classify_work_editions(book, seed_source, source_response)
    if (checked.get("status") != "VERIFIED"
            or checked.get("resolved_isbn") != normalize_isbn(row.get("resolved_isbn"))
            or checked.get("edition_evidence") != row.get("edition_evidence")
            or checked.get("publisher_evidence") != row.get("publisher_evidence")
            or checked.get("publication_year_evidence") != row.get("publication_year_evidence")):
        return None
    cover_path = out_dir / "cache" / "covers" / (hashlib.sha256(checked["cover_candidate_url"].encode("utf-8")).hexdigest() + ".json")
    if cover_path.is_file():
        try:
            checked["cover_check"] = json.loads(cover_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            checked["cover_check"] = {}
    else:
        checked["cover_check"] = {}
    return checked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", help="File-backed SQLite URL; defaults to DATABASE_URL/test DB")
    parser.add_argument("--seed-catalog", type=Path, default=ROOT / "database" / "seed" / "books_catalog.json")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=0, help="Limit total book records searched (0=all eligible records).")
    parser.add_argument("--research-unmapped", action="store_true", help="Search unmapped books by title/author in Open Library and Google Books; incomplete or ambiguous results remain review-only.")
    parser.add_argument("--request-gap", type=float, default=1.2, help="Minimum seconds between Open Library requests (default 1.2).")
    parser.add_argument("--check-covers", action="store_true", help="HEAD-check verified ISBN cover URLs; preserves failures as missing covers.")
    parser.add_argument("--apply-report", type=Path, help="Apply VERIFIED ISBNs from a previous dry-run CSV after creating a fresh backup.")
    parser.add_argument("--delete-not-found", action="store_true", help="Also remove NOT_FOUND entries, only when no retained relationships exist.")
    args = parser.parse_args(argv)
    if args.request_gap < 1.0:
        parser.error("--request-gap must be at least 1.0 seconds for Open Library API etiquette.")
    database = database_file(args.database_url or os.getenv("DATABASE_URL") or DEFAULT_DB_URL)
    if not database.is_file():
        print(f"Database not found; refusing implicit creation: {database}", file=sys.stderr)
        return 2
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = args.out_dir / "cache" / "openlibrary"
    report_path = args.out_dir / "reports" / f"isbn_repair_dry_run_{stamp}.csv"
    audit_path = args.out_dir / "reports" / f"isbn_repair_audit_{stamp}.csv"

    if args.apply_report:
        return apply_report(database, args.apply_report, args.out_dir, args.delete_not_found, audit_path)

    with readonly(database) as conn:
        books = load_books(conn)
        counts = baseline_counts(conn)
        isbn_owner = {}
        for book in books:
            normalized = normalize_isbn(book.get("isbn"))
            if normalized:
                isbn_owner.setdefault(normalized, []).append(book["id"])
        seed_records = seed_map(args.seed_catalog, books)
        targets = [b for b in books if not normalize_isbn(b.get("isbn"))]
        researched = seed_researched = unmapped_researched = 0
        open_library_blocked = google_blocked = False
        open_library_state = {"last_request": 0.0}
        google_state = {"last_request": 0.0}
        cover_state = {"last_request": 0.0}
        cover_cache_dir = args.out_dir / "cache" / "covers"
        google_cache_dir = args.out_dir / "cache" / "googlebooks"
        rows = []
        provider_health = {"google_books": "one initial title/author probe returned HTTP 429; run stops retrying after a per-item 429", "open_library": "available subject to per-request API rate limit"}
        for book in targets:
            budget_available = args.limit == 0 or researched < args.limit
            if book["id"] in seed_records and budget_available:
                work = seed_records[book["id"]]["openlibrary_work"]
                url = f"https://openlibrary.org{work}/editions.json?limit=100"
                researched += 1
                seed_researched += 1
                if open_library_blocked:
                    response = {"http_status": 429, "url": url, "error": "Skipped after prior Open Library rate-limit response"}
                else:
                    response = fetch_json(url, cache_dir, args.request_gap, open_library_state)
                decision = classify_work_editions(book, seed_records[book["id"]], response)
                if response.get("http_status") == 429:
                    open_library_blocked = True
                    provider_health["open_library"] = "HTTP 429 rate limited; remaining records retained for review without additional requests"
            elif args.research_unmapped and budget_available:
                researched += 1
                unmapped_researched += 1
                ol_url = openlibrary_search_query(book)
                if open_library_blocked:
                    ol_response = {"http_status": 429, "url": ol_url, "error": "Skipped after prior Open Library rate-limit response"}
                else:
                    ol_response = fetch_json(ol_url, cache_dir, args.request_gap, open_library_state)
                if ol_response.get("http_status") == 429:
                    open_library_blocked = True
                    provider_health["open_library"] = "HTTP 429 rate limited; remaining records retained for review without additional requests"
                google_response = None
                if not google_blocked:
                    google_url = research_generated_query(book)
                    google_response = fetch_json(google_url, google_cache_dir, 2.0, google_state)
                    if google_response.get("http_status") == 429:
                        google_blocked = True
                        provider_health["google_books"] = "HTTP 429 on title/author lookup; further Google Books requests stopped"
                    elif google_response.get("http_status") == 200:
                        provider_health["google_books"] = "Title/author API lookup available; ambiguous results remain review-only"
                decision = classify_search_candidates(book, ol_response, google_response)
            else:
                decision = {"status": "REVIEW_REQUIRED", "resolved_isbn": "", "candidate_isbns": [], "confidence": "LOW",
                            "edition_evidence": "", "publisher_evidence": "", "publication_year_evidence": "",
                            "source_urls": [], "cover_candidate_url": "",
                            "reason": ("Title/author search not run for this record in the selected batch; Google Books previously returned HTTP 429. "
                            "The record is retained and is not classified NOT_FOUND."), "action_taken": "RETAINED"}
            candidate = decision.get("resolved_isbn")
            if candidate and len(isbn_owner.get(candidate, [])):
                decision.update({"status": "REVIEW_REQUIRED", "resolved_isbn": "", "confidence": "LOW",
                                 "reason": f"Candidate ISBN already belongs to book(s) {','.join(isbn_owner[candidate])}; conflict prevented."})
            cover = {}
            if args.check_covers and decision["status"] == "VERIFIED" and decision.get("cover_candidate_url"):
                if cover_state.get("blocked"):
                    cover = {"http_status": 429, "content_type": "", "url": decision["cover_candidate_url"], "error": "Skipped after prior cover API rate limit"}
                else:
                    cover = check_cover(decision["cover_candidate_url"], cover_cache_dir, args.request_gap, cover_state)
                    if cover.get("http_status") == 429:
                        cover_state["blocked"] = True
                if cover.get("http_status") == 200 and cover.get("content_type", "").startswith("image/"):
                    decision["cover_candidate_url"] = cover.get("url", decision["cover_candidate_url"])
            rows.append({"book_id": book["id"], "title": book["title"], "authors": "; ".join(book["author_list"]),
                         "catalogue_publication_year": book.get("publication_year") or "",
                         "catalogue_publisher": book.get("publisher") or "", "catalogue_edition": book.get("edition") or "",
                         "catalogue_subtitle": book.get("subtitle") or "", "original_isbn": book.get("isbn") or "",
                         "cover_original_ref": book.get("cover_image_ref") or "", "status": decision["status"],
                         "resolved_isbn": decision.get("resolved_isbn", ""),
                         "candidate_isbns": "; ".join(decision.get("candidate_isbns", [])),
                         "confidence": decision.get("confidence", "LOW"),
                         "edition_evidence": decision.get("edition_evidence", ""), "publisher_evidence": decision.get("publisher_evidence", ""),
                         "publication_year_evidence": decision.get("publication_year_evidence", ""),
                         "source_urls": " | ".join(decision.get("source_urls", [])),
                         "cover_candidate_url": decision.get("cover_candidate_url", ""),
                         "cover_status": str(cover.get("http_status", "NOT_CHECKED")),
                         "cover_content_type": cover.get("content_type", ""),
                         "action_taken": decision.get("action_taken", "DRY_RUN_ONLY"),
                         "reason": decision.get("reason", ""), "copy_count": book["copy_count"],
                         "loan_history_count": book["loan_history_count"], "reservation_count": book["reservation_count"]})
    atomic_csv(report_path, report_fields(), rows)
    counts_by_status = {}
    for row in rows:
        counts_by_status[row["status"]] = counts_by_status.get(row["status"], 0) + 1
    summary = {"generated_at": datetime.now().astimezone().isoformat(), "database": str(database), "dry_run": True,
               "baseline_counts": counts, "books_with_missing_or_invalid_isbn": len(targets),
               "seed_work_records_researched": seed_researched, "unmapped_title_author_records_researched": unmapped_researched,
               "provider_health": provider_health,
               "statuses": counts_by_status, "covers_successfully_resolved": sum(r["cover_status"] == "200" and r["cover_content_type"].startswith("image/") for r in rows),
               "cover_checks_performed": sum(r["cover_status"] != "NOT_CHECKED" for r in rows),
               "report_csv": str(report_path.resolve()),
               "database_modified": False, "deletions_proposed": 0,
               "caution": "Provider failure or an incomplete search is REVIEW_REQUIRED, never NOT_FOUND. No rows are deleted by a dry run."}
    summary_path = args.out_dir / "reports" / f"isbn_repair_dry_run_{stamp}.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({**summary, "summary_json": str(summary_path.resolve())}, indent=2))
    return 0


def baseline_counts(conn: sqlite3.Connection) -> dict:
    return {
        "books": conn.execute("SELECT count(*) FROM books").fetchone()[0],
        "copies": conn.execute("SELECT count(*) FROM book_copies").fetchone()[0],
        "loans_all_history": conn.execute("SELECT count(*) FROM loans").fetchone()[0],
        "loans_active": conn.execute(f"SELECT count(*) FROM loans WHERE status IN ({ACTIVE_LOAN_STATES})").fetchone()[0],
        "reservations": conn.execute("SELECT count(*) FROM reservations").fetchone()[0],
        "reservations_active": conn.execute(f"SELECT count(*) FROM reservations WHERE status IN ({ACTIVE_RESERVATION_STATES})").fetchone()[0],
        "suggestions": conn.execute("SELECT count(*) FROM suggestions").fetchone()[0],
        "suggestion_votes": conn.execute("SELECT count(*) FROM suggestion_votes").fetchone()[0],
        "notifications": conn.execute("SELECT count(*) FROM notifications").fetchone()[0],
        "users": conn.execute("SELECT count(*) FROM users").fetchone()[0],
    }


def apply_report(database: Path, report_path: Path, out_dir: Path, delete_not_found: bool, audit_path: Path) -> int:
    if not report_path.is_file():
        print(f"Report not found: {report_path}", file=sys.stderr)
        return 2
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = backup_database(database, out_dir / "backups" / f"{database.stem}_before_isbn_apply_{stamp}.db")
    with report_path.open("r", encoding="utf-8-sig", newline="") as stream:
        proposed = list(csv.DictReader(stream))
    audit=[]
    applied=deleted=conflicts=covers_added=0
    conn=sqlite3.connect(database, timeout=30)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN IMMEDIATE")
        current_books = {book["id"]: book for book in load_books(conn)}
        current_ids=set(current_books)
        current_norm={}
        for book_id,isbn in conn.execute("SELECT id,isbn FROM books WHERE isbn IS NOT NULL AND trim(isbn)<>''"):
            normalized=normalize_isbn(isbn)
            if normalized: current_norm.setdefault(normalized,set()).add(book_id)
        for row in proposed:
            bid=row.get("book_id", "")
            if bid not in current_ids:
                audit.append({**row,"action_taken":"SKIPPED_MISSING_BOOK","reason":"Book ID no longer exists."}); continue
            status=row.get("status","")
            if status=="VERIFIED":
                isbn=normalize_isbn(row.get("resolved_isbn"))
                if not isbn:
                    audit.append({**row,"action_taken":"SKIPPED_INVALID_CANDIDATE","reason":"Report candidate failed checksum revalidation."}); continue
                book=current_books[bid]
                reverified=verify_cached_candidate(row,book,out_dir)
                if not reverified:
                    audit.append({**row,"action_taken":"SKIPPED_STALE_OR_UNSUPPORTED_EVIDENCE","reason":"Current catalogue fields or cached source evidence no longer support this candidate."}); continue
                existing=book.get("isbn")
                if (existing or "") != (row.get("original_isbn") or ""):
                    audit.append({**row,"action_taken":"SKIPPED_STALE_ISBN","reason":"Stored ISBN changed since the dry run; no overwrite performed."}); continue
                existing_norm=normalize_isbn(existing)
                if existing_norm:
                    audit.append({**row,"action_taken":"SKIPPED_ALREADY_VALID","original_isbn":existing,"reason":"Existing checksum-valid ISBN was not overwritten."}); continue
                owners=current_norm.get(isbn,set())-{bid}
                if owners:
                    conflicts+=1; audit.append({**row,"action_taken":"SKIPPED_DUPLICATE_ISBN","reason":"Candidate conflicts with another book."}); continue
                cover_check=reverified.get("cover_check",{})
                add_cover=(not book.get("cover_image_ref") and row.get("cover_status")=="200"
                           and (row.get("cover_content_type") or "").startswith("image/")
                           and cover_check.get("http_status")==200
                           and (cover_check.get("content_type") or "").startswith("image/")
                           and row.get("cover_candidate_url")==cover_check.get("url"))
                cover_ref=row.get("cover_candidate_url") if add_cover else None
                conn.execute("UPDATE books SET isbn=?,cover_image_ref=CASE WHEN (cover_image_ref IS NULL OR trim(cover_image_ref)='') AND ? IS NOT NULL THEN ? ELSE cover_image_ref END,updated_at=CURRENT_TIMESTAMP WHERE id=? AND COALESCE(isbn,'')=?",(isbn,cover_ref,cover_ref,bid,existing or ''))
                if conn.execute("SELECT changes()").fetchone()[0]:
                    current_norm.setdefault(isbn,set()).add(bid); applied+=1
                    if add_cover: covers_added+=1
                    action="UPDATED_VERIFIED_ISBN_AND_COVER" if add_cover else "UPDATED_VERIFIED_ISBN"
                    reason="Applied unique verified ISBN; other curated metadata and circulation fields were left untouched."
                    if not add_cover and row.get("cover_candidate_url"):
                        reason += " No verified available cover was persisted; frontend fallback/placeholder remains active."
                    audit.append({**row,"original_isbn":existing or "","resolved_isbn":isbn,"action_taken":action,"reason":reason})
                continue
            if status=="NOT_FOUND" and delete_not_found:
                safe,reason=safe_to_delete(conn,bid)
                if safe:
                    conn.execute("DELETE FROM books WHERE id=?",(bid,)); deleted+=1
                    audit.append({**row,"action_taken":"DELETED_NOT_FOUND","reason":reason})
                else:
                    audit.append({**row,"action_taken":"RETAINED_DEPENDENCIES","reason":reason})
            else:
                audit.append({**row,"action_taken":"RETAINED_REVIEW_REQUIRED","reason":row.get("reason", "Not verified; retained.")})
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()
    audit_at = datetime.now().astimezone().isoformat()
    for entry in audit:
        entry["action_timestamp"] = audit_at
    atomic_csv(audit_path, report_fields(), audit)
    print(json.dumps({"applied_at":audit_at,"database":str(database),"backup":backup,"report":str(report_path.resolve()),
                      "audit_csv":str(audit_path.resolve()),"verified_isbns_applied":applied,"verified_covers_added":covers_added,
                      "books_removed":deleted,"duplicate_conflicts_skipped":conflicts},indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
