import csv
import hashlib
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from backend.repair_book_isbns import (
    apply_report, atomic_csv, check_cover, classify_search_candidates, classify_work_editions, fetch_json, normalize_isbn,
    openlibrary_search_query, report_fields, safe_to_delete, seed_map,
)

ROOT = Path(__file__).resolve().parents[1]
WORK = "/works/OL17618370W"
VALID_ISBN = "9780136083252"
BOOK = {
    "id": "book-1", "title": "Clean Code", "subtitle": None, "isbn": None,
    "publication_year": 2008, "edition": None, "language": "English",
    "description": None, "cover_image_ref": None, "publisher": "Pearson Education Canada",
    "category": "Programming", "author_list": ["Robert C. Martin"],
}
SOURCE = {"title": "Clean Code", "authors": ["Robert C. Martin"], "year": 2008,
          "openlibrary_work": WORK}
EDITION = {
    "key": "/books/OL34878707M", "title": "Clean Code", "subtitle": "A Handbook of Agile Software Craftsmanship",
    "publish_date": "2008", "publishers": ["Pearson Education Canada"],
    "isbn_13": [VALID_ISBN], "works": [{"key": WORK}], "covers": [14415969],
}


def make_report_row(book=BOOK, isbn=VALID_ISBN, cover_url=None):
    url = f"https://openlibrary.org{WORK}/editions.json?limit=100"
    cover_url = cover_url or f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
    return {
        "book_id": book["id"], "title": book["title"], "authors": "; ".join(book["author_list"]),
        "catalogue_publication_year": str(book["publication_year"] or ""),
        "catalogue_publisher": book["publisher"] or "", "catalogue_edition": book["edition"] or "",
        "catalogue_subtitle": book["subtitle"] or "", "original_isbn": book["isbn"] or "",
        "cover_original_ref": book["cover_image_ref"] or "", "resolved_isbn": isbn,
        "status": "VERIFIED", "confidence": "HIGH",
        "edition_evidence": f"Open Library edition {EDITION['key']} title='Clean Code'; work={WORK}; year=2008; ISBN checksum valid.",
        "publisher_evidence": "Pearson Education Canada", "publication_year_evidence": "2008",
        "source_urls": f"{ROOT / 'database' / 'seed' / 'books_catalog.json'} (Open Library work key: {WORK}) | {url}",
        "cover_candidate_url": cover_url, "cover_status": "200", "cover_content_type": "image/jpeg",
        "action_taken": "DRY_RUN_ONLY", "reason": "Unique ISBN candidate.",
        "copy_count": "2", "loan_history_count": "0", "reservation_count": "0",
    }


def create_db(path, book=BOOK, existing_cover=None, existing_isbn=None):
    conn = sqlite3.connect(path)
    conn.executescript("""
      PRAGMA foreign_keys=ON;
      CREATE TABLE publishers(id TEXT PRIMARY KEY,name TEXT UNIQUE NOT NULL);
      CREATE TABLE categories(id TEXT PRIMARY KEY,name TEXT UNIQUE NOT NULL);
      CREATE TABLE authors(id TEXT PRIMARY KEY,name TEXT NOT NULL);
      CREATE TABLE books(id TEXT PRIMARY KEY,isbn TEXT UNIQUE,title TEXT NOT NULL,subtitle TEXT,description TEXT,
        publication_year INTEGER,edition TEXT,language TEXT NOT NULL,cover_image_ref TEXT,publisher_id TEXT,category_id TEXT,updated_at TEXT);
      CREATE TABLE book_authors(book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
        author_id TEXT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,PRIMARY KEY(book_id,author_id));
      CREATE TABLE book_copies(id TEXT PRIMARY KEY,book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE);
      CREATE TABLE reservations(id TEXT PRIMARY KEY,book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,status TEXT NOT NULL);
      CREATE TABLE loans(id TEXT PRIMARY KEY,book_copy_id TEXT NOT NULL REFERENCES book_copies(id) ON DELETE RESTRICT,status TEXT NOT NULL);
      CREATE TABLE book_departments(book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,department_id TEXT NOT NULL);
    """)
    conn.execute("INSERT INTO publishers VALUES('pub-1',?)", (book["publisher"],))
    conn.execute("INSERT INTO categories VALUES('cat-1','Programming')")
    conn.execute("INSERT INTO authors VALUES('author-1','Robert C. Martin')")
    conn.execute("INSERT INTO books VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (
        book["id"], existing_isbn, book["title"], book["subtitle"], book["description"],
        book["publication_year"], book["edition"], book["language"], existing_cover,
        "pub-1", "cat-1", None))
    conn.execute("INSERT INTO book_authors VALUES(?, 'author-1')", (book["id"],))
    conn.execute("INSERT INTO book_copies VALUES('copy-1',?)", (book["id"],))
    conn.commit(); conn.close()


class RepairBookIsbnTests(unittest.TestCase):
    def test_fetch_json_and_cover_head_use_mocked_responses_and_cache_successes(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory)
            url = "https://openlibrary.org/search.json?title=Clean+Code"
            response = MagicMock()
            response.status = 200
            response.read.return_value = b'{"numFound":0,"docs":[]}'
            response.__enter__.return_value = response
            state = {"last_request": 0.0}
            with patch("backend.repair_book_isbns.urlopen", return_value=response) as mocked:
                first = fetch_json(url, cache / "json", 0, state)
                second = fetch_json(url, cache / "json", 0, state)
            self.assertEqual(first["data"]["numFound"], 0)
            self.assertEqual(second, first)
            self.assertEqual(mocked.call_count, 1)

            cover_url = "https://covers.openlibrary.org/b/isbn/9780136083252-L.jpg?default=false"
            cover_response = MagicMock()
            cover_response.status = 200
            cover_response.headers = {"Content-Type": "image/jpeg"}
            cover_response.geturl.return_value = cover_url
            cover_response.__enter__.return_value = cover_response
            with patch("backend.repair_book_isbns.urlopen", return_value=cover_response) as mocked:
                first_cover = check_cover(cover_url, cache / "covers", 0, state)
                second_cover = check_cover(cover_url, cache / "covers", 0, state)
            self.assertEqual(first_cover["content_type"], "image/jpeg")
            self.assertEqual(second_cover, first_cover)
            self.assertEqual(mocked.call_count, 1)
            self.assertEqual(mocked.call_args.args[0].get_method(), "HEAD")

    def test_unmapped_search_requires_cross_provider_isbn_corroboration(self):
        book = {**BOOK, "publisher": "Pearson Education Canada"}
        ol_url = openlibrary_search_query(book)
        self.assertIn("author=Robert", ol_url)
        ol = {"http_status": 200, "url": ol_url, "data": {"docs": [{
            "title": "Clean Code", "author_name": ["Robert C. Martin"], "publisher": ["Pearson Education Canada"],
            "first_publish_year": 2008, "isbn": [VALID_ISBN]}]}}
        one_source = classify_search_candidates(book, ol)
        self.assertEqual(one_source["status"], "REVIEW_REQUIRED")
        self.assertIn("skipped", one_source["reason"])
        google = {"http_status": 200, "url": "https://www.googleapis.com/books/v1/volumes?q=clean+code",
                  "data": {"items": [{"volumeInfo": {"title": "Clean Code", "authors": ["Robert C. Martin"],
                  "publisher": "Pearson Education Canada", "publishedDate": "2008",
                  "industryIdentifiers": [{"type": "ISBN_13", "identifier": VALID_ISBN}]}}]}}
        corroborated = classify_search_candidates(book, ol, google)
        self.assertEqual(corroborated["status"], "VERIFIED")
        self.assertEqual(corroborated["resolved_isbn"], VALID_ISBN)
        self.assertEqual(len(corroborated["source_urls"]), 2)

        edition_book = {**book, "subtitle": "A Handbook of Agile Software Craftsmanship", "edition": "Second edition"}
        edition_ol = {**ol, "data": {"docs": [{**ol["data"]["docs"][0], "subtitle": edition_book["subtitle"]}]}}
        edition_google = {**google, "data": {"items": [{"volumeInfo": {**google["data"]["items"][0]["volumeInfo"],
                          "subtitle": edition_book["subtitle"]}}]}}
        edition_result = classify_search_candidates(edition_book, edition_ol, edition_google)
        self.assertEqual(edition_result["status"], "REVIEW_REQUIRED")

        subtitle_book = {**book, "subtitle": "A Faithful Subtitle"}
        subtitle_ol = {**ol, "data": {"docs": [{**ol["data"]["docs"][0], "subtitle": "An Unrelated Subtitle"}]}}
        subtitle_google = {**google, "data": {"items": [{"volumeInfo": {**google["data"]["items"][0]["volumeInfo"],
                             "subtitle": "An Unrelated Subtitle"}}]}}
        subtitle_result = classify_search_candidates(subtitle_book, subtitle_ol, subtitle_google)
        self.assertEqual(subtitle_result["status"], "REVIEW_REQUIRED")

        failed = classify_search_candidates(book, {"http_status": 429, "url": ol_url, "error": "rate limit"}, None)
        self.assertEqual(failed["status"], "REVIEW_REQUIRED")
        self.assertEqual(failed["resolved_isbn"], "")

    def test_normalize_isbn_enforces_checksums_and_x(self):
        self.assertEqual(normalize_isbn("978-0-306-40615-7"), "9780306406157")
        self.assertEqual(normalize_isbn("0-306-40615-2"), "0306406152")
        self.assertEqual(normalize_isbn("0-8044-2957-X"), "080442957X")
        self.assertIsNone(normalize_isbn("9780306406158"))
        self.assertIsNone(normalize_isbn("978x306406157"))

    def test_seed_map_requires_exact_title_author_and_year(self):
        books = [BOOK, {**BOOK, "id": "wrong-year", "publication_year": 2009}]
        mapping = seed_map(ROOT / "database" / "seed" / "books_catalog.json", books)
        self.assertEqual(mapping.get("book-1", {}).get("openlibrary_work"), WORK)
        self.assertNotIn("wrong-year", mapping)

    def test_unique_openlibrary_edition_candidate_is_verified(self):
        result = {"http_status": 200, "data": {"entries": [EDITION]}}
        decision = classify_work_editions(BOOK, SOURCE, result)
        self.assertEqual(decision["status"], "VERIFIED")
        self.assertEqual(decision["resolved_isbn"], VALID_ISBN)
        self.assertIn(WORK, decision["edition_evidence"])
        self.assertTrue(decision["cover_candidate_url"].endswith("?default=false"))

    def test_ambiguous_multiple_editions_are_review_required(self):
        second = {**EDITION, "key": "/books/OL999M", "isbn_13": ["9780136083221"]}
        decision = classify_work_editions(BOOK, SOURCE, {"http_status": 200, "data": {"entries": [EDITION, second]}})
        self.assertEqual(decision["status"], "REVIEW_REQUIRED")
        self.assertEqual(set(decision["candidate_isbns"]), {VALID_ISBN, "9780136083221"})

    def test_wrong_work_invalid_isbn_and_provider_error_are_not_not_found(self):
        wrong_work = {**EDITION, "works": [{"key": "/works/OL000W"}]}
        bad_isbn = {**EDITION, "isbn_13": ["9780136083253"]}
        for result in (
            {"http_status": 200, "data": {"entries": [wrong_work]}},
            {"http_status": 200, "data": {"entries": [bad_isbn]}},
            {"http_status": 429, "error": "rate limit"},
            {"http_status": None, "error": "timeout"},
        ):
            decision = classify_work_editions(BOOK, SOURCE, result)
            self.assertEqual(decision["status"], "REVIEW_REQUIRED")
            self.assertNotEqual(decision["status"], "NOT_FOUND")

    def test_safe_delete_rejects_books_with_copies_reservations_or_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.db"
            create_db(path)
            conn = sqlite3.connect(path); conn.execute("PRAGMA foreign_keys=ON")
            ok, _ = safe_to_delete(conn, "book-1")
            self.assertFalse(ok)  # a copy exists, so circulation history must be retained
            conn.execute("DELETE FROM book_copies"); conn.commit()
            conn.execute("INSERT INTO reservations VALUES('res-1','book-1','WAITING')"); conn.commit()
            ok, _ = safe_to_delete(conn, "book-1")
            self.assertFalse(ok)
            conn.execute("DELETE FROM reservations"); conn.commit()
            ok, reason = safe_to_delete(conn, "book-1")
            self.assertTrue(ok, reason)
            conn.close()

    def test_apply_revalidates_source_and_updates_only_isbn_and_verified_cover(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); db_path = base / "test.db"; out_dir = base / "research"
            create_db(db_path)
            url = f"https://openlibrary.org{WORK}/editions.json?limit=100"
            cache_path = out_dir / "cache" / "openlibrary" / (hashlib.sha256(url.encode()).hexdigest()+".json")
            cache_path.parent.mkdir(parents=True)
            cache_path.write_text(json.dumps({"http_status":200,"url":url,"data":{"entries":[EDITION]}}),encoding="utf-8")
            cover_url=f"https://covers.openlibrary.org/b/isbn/{VALID_ISBN}-L.jpg?default=false"
            cover_cache=out_dir / "cache" / "covers" / (hashlib.sha256(cover_url.encode()).hexdigest()+".json")
            cover_cache.parent.mkdir(parents=True)
            cover_cache.write_text(json.dumps({"http_status":200,"content_type":"image/jpeg","url":cover_url}),encoding="utf-8")
            report=base/"dry-run.csv"; row=make_report_row(cover_url=cover_url)
            atomic_csv(report, report_fields(), [row])
            result=apply_report(db_path, report, out_dir, False, base/"audit.csv")
            self.assertEqual(result, 0)
            with (base/"audit.csv").open(encoding="utf-8-sig", newline="") as stream:
                audit_row = next(csv.DictReader(stream))
            self.assertTrue(audit_row["action_timestamp"])
            self.assertEqual(audit_row["resolved_isbn"], VALID_ISBN)
            conn=sqlite3.connect(db_path)
            found=conn.execute("SELECT isbn,cover_image_ref,publication_year FROM books WHERE id='book-1'").fetchone()
            self.assertEqual(found, (VALID_ISBN, cover_url, 2008))
            self.assertEqual(conn.execute("SELECT count(*) FROM book_copies").fetchone()[0], 1)
            conn.close()

    def test_apply_preserves_existing_valid_isbn_and_curated_cover(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); db_path=base/"test.db"; out=base/"research"
            curated="https://catalog.example/curated-cover.jpg"
            create_db(db_path,existing_isbn=VALID_ISBN,existing_cover=curated)
            report=base/"report.csv"; atomic_csv(report,report_fields(),[make_report_row()])
            apply_report(db_path,report,out,False,base/"audit.csv")
            conn=sqlite3.connect(db_path)
            self.assertEqual(conn.execute("SELECT isbn,cover_image_ref FROM books").fetchone(),(VALID_ISBN,curated))
            conn.close()


if __name__ == "__main__":
    unittest.main()
