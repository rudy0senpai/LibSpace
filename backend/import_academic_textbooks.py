"""Preflight and import the supplied academic-textbook CSV safely.

The importer keeps Book and BookCopy separate; it never creates physical copies.
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
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from html import unescape
from pathlib import Path

REQUIRED = {
    "book_id", "title", "authors", "isbn", "isbn_type", "programme",
    "subject_area", "subjects", "publisher", "publication_year", "edition",
    "language", "cover_url", "source_name", "source_record_url",
}


def normalize(value: str | None) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", unescape(value or "").casefold()).split())


def normalize_isbn(value: str | None) -> str:
    return re.sub(r"[^0-9Xx]", "", value or "").upper()


def valid_isbn(value: str | None) -> bool:
    isbn = normalize_isbn(value)
    if len(isbn) == 10 and isbn[:9].isdigit() and (isbn[-1].isdigit() or isbn[-1] == "X"):
        return sum((10 - index) * (10 if char == "X" else int(char)) for index, char in enumerate(isbn)) % 11 == 0
    if len(isbn) == 13 and isbn.isdigit():
        return sum(int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(isbn)) % 10 == 0
    return False


def split_authors(value: str | None) -> list[str]:
    result, seen = [], set()
    for name in (value or "").split(";"):
        name = unescape(name).strip()
        key = normalize(name)
        if name and key and key not in seen:
            result.append(name)
            seen.add(key)
    return result


def author_match(source_authors: str, remote_authors: list[dict]) -> bool:
    local = split_authors(source_authors)
    remote = [str(item.get("name", "")).strip() for item in remote_authors if isinstance(item, dict) and item.get("name")]
    for source in local:
        source_norm = normalize(source)
        source_tokens = source_norm.split()
        for target in remote:
            target_norm = normalize(target)
            target_tokens = target_norm.split()
            if source_norm == target_norm or SequenceMatcher(None, source_norm, target_norm).ratio() >= 0.82:
                return True
            if source_tokens and target_tokens and source_tokens[-1] == target_tokens[-1] and source_tokens[0][0] == target_tokens[0][0]:
                return True
            if len(target_tokens) > 1 and source_norm in target_norm:
                return True
    return False


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = set(reader.fieldnames or [])
        missing = REQUIRED - fields
        if missing:
            raise ValueError("CSV missing required columns: " + ", ".join(sorted(missing)))
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


def isbn_batches(rows: list[dict], batch_size: int = 100):
    for start in range(0, len(rows), batch_size):
        yield rows[start:start + batch_size]


def fetch_openlibrary_batch(rows: list[dict], opener=urllib.request.urlopen, sleep=time.sleep) -> dict:
    isbns = [normalize_isbn(row["isbn"]) for row in rows]
    bibkeys = ",".join("ISBN:" + value for value in isbns)
    url = "https://openlibrary.org/api/books?bibkeys=" + urllib.parse.quote(bibkeys, safe=":,") + "&format=json&jscmd=data"
    request = urllib.request.Request(url, headers={"User-Agent": "LibSphere academic catalogue validation"})
    delay = 1.0
    for attempt in range(3):
        try:
            with opener(request, timeout=30) as response:
                data = json.load(response)
            return data if isinstance(data, dict) else {}
        except Exception:
            if attempt == 2:
                raise
            sleep(delay)
            delay *= 2
    return {}


def verify_rows(rows: list[dict], opener=urllib.request.urlopen, sleep=time.sleep) -> tuple[list[dict], dict]:
    duplicate_counts = Counter(normalize_isbn(row.get("isbn")) for row in rows)
    unique_valid = [row for row in rows if valid_isbn(row.get("isbn")) and duplicate_counts[normalize_isbn(row.get("isbn"))] == 1]
    evidence_by_isbn = {}
    for index, batch in enumerate(isbn_batches(unique_valid)):
        response = fetch_openlibrary_batch(batch, opener=opener, sleep=sleep)
        for row in batch:
            isbn = normalize_isbn(row["isbn"])
            remote = response.get("ISBN:" + isbn)
            if not isinstance(remote, dict):
                evidence_by_isbn[isbn] = {"matched": False, "reason": "No edition record returned for ISBN"}
                continue
            remote_title = str(remote.get("title", ""))
            source_title = str(row.get("title", ""))
            title_score = SequenceMatcher(None, normalize(source_title), normalize(remote_title)).ratio()
            title_match = bool(title_score >= 0.92)
            remote_authors = remote.get("authors", [])
            authors_match = author_match(row.get("authors", ""), remote_authors if isinstance(remote_authors, list) else [])
            matched = title_match and authors_match
            evidence_by_isbn[isbn] = {
                "matched": matched,
                "reason": "" if matched else ("Title mismatch" if not title_match else "Author mismatch"),
                "edition_title": remote_title,
                "edition_authors": [str(a.get("name", "")) for a in remote_authors if isinstance(a, dict)],
                "edition_publishers": [str(p.get("name", "")) for p in remote.get("publishers", []) if isinstance(p, dict)],
                "edition_publish_date": str(remote.get("publish_date", "")),
                "title_similarity": round(title_score, 4),
                "title_match": title_match,
                "author_match": authors_match,
                "edition_record_url": "https://openlibrary.org/isbn/" + isbn,
            }
        if index < (len(unique_valid) - 1) // 100:
            sleep(1.0)

    report_rows = []
    seen_book_ids = set()
    for row in rows:
        isbn = normalize_isbn(row.get("isbn"))
        reasons = []
        if not row.get("book_id") or row["book_id"] in seen_book_ids:
            reasons.append("Missing or duplicate book_id")
        seen_book_ids.add(row.get("book_id", ""))
        if not row.get("title") or len(row["title"]) > 300:
            reasons.append("Missing title or title exceeds 300 characters")
        if not split_authors(row.get("authors")):
            reasons.append("Missing authors")
        if not valid_isbn(row.get("isbn")):
            reasons.append("Invalid or missing ISBN checksum")
        elif duplicate_counts[isbn] > 1:
            reasons.append("Duplicate ISBN in source")
        year = row.get("publication_year", "")
        if year and (not year.isdigit() or not 1400 <= int(year) <= 2100):
            reasons.append("Invalid publication_year")
        evidence = evidence_by_isbn.get(isbn, {})
        if not reasons and not evidence.get("matched"):
            reasons.append(evidence.get("reason") or "ISBN/title/author association not verified")
        report_rows.append({"row": row, "evidence": evidence, "rejected": bool(reasons), "reasons": reasons})

    duplicate_isbns = {key for key, count in duplicate_counts.items() if key and count > 1}
    summary = {
        "source_rows": len(rows),
        "checksum_valid_isbn_rows": sum(valid_isbn(row.get("isbn")) for row in rows),
        "unique_checksum_valid_isbns": len({normalize_isbn(row.get("isbn")) for row in rows if valid_isbn(row.get("isbn"))}),
        "duplicate_isbn_values": len(duplicate_isbns),
        "duplicate_rows_beyond_first": sum(duplicate_counts[value] - 1 for value in duplicate_isbns),
        "provider_checked": len(evidence_by_isbn),
        "title_author_verified": sum(bool(item["evidence"].get("matched")) and not item["rejected"] for item in report_rows),
        "rejected_records": sum(item["rejected"] for item in report_rows),
        "publisher_discrepancies": sum(bool(item["evidence"].get("matched")) and bool(row.get("publisher")) and bool(item["evidence"].get("edition_publishers")) and not any(normalize(row["publisher"]) in normalize(p) or normalize(p) in normalize(row["publisher"]) for p in item["evidence"]["edition_publishers"]) for item in report_rows for row in [item["row"]]),
        "publication_year_discrepancies": sum(bool(item["evidence"].get("matched")) and bool(item["row"].get("publication_year")) and bool(re.search(r"(?:1[4-9]\d{2}|20\d{2}|2100)", item["evidence"].get("edition_publish_date", ""))) and item["row"]["publication_year"] != re.search(r"(?:1[4-9]\d{2}|20\d{2}|2100)", item["evidence"]["edition_publish_date"]).group(0) for item in report_rows),
    }
    return report_rows, summary


def database_file(uri: str) -> Path:
    if not uri.startswith("sqlite:") or uri in {"sqlite://", "sqlite:///:memory:"}:
        raise ValueError("Academic import requires a file-backed SQLite database")
    name = uri.removeprefix("sqlite:///")
    if uri.startswith("sqlite:////"):
        name = "/" + name
    path = Path(name)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / "instance" / path
    return path.resolve()


def backup_database(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect("file:" + source.as_posix() + "?mode=ro", uri=True)
    dst = sqlite3.connect(destination)
    try:
        src.backup(dst)
        if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite backup integrity check failed")
        if dst.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("SQLite backup has foreign-key violations")
    finally:
        dst.close()
        src.close()
    return destination


def source_notes(row: dict, evidence: dict) -> str:
    data = {
        "dataset": "LibSphere_Academic_Textbooks_1000.csv",
        "source_book_id": row.get("book_id"),
        "source_authors": row.get("authors"),
        "source_isbn_type": row.get("isbn_type"),
        "programme": row.get("programme"),
        "subject_area": row.get("subject_area"),
        "subjects": row.get("subjects"),
        "source_name": row.get("source_name"),
        "source_record_url": row.get("source_record_url"),
        "source_cover_url_unverified": row.get("cover_url"),
        "source_publisher": row.get("publisher"),
        "source_publication_year": row.get("publication_year"),
        "source_edition": row.get("edition"),
        "source_language": row.get("language"),
        "edition_evidence_url": evidence.get("edition_record_url"),
    }
    return "[Academic CSV provenance: " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "]"


def import_verified(app, db, models, records: list[dict]) -> dict:
    Book, BookCopy, Author, Publisher, Category, Department = models
    stats = Counter({"created_books": 0, "matched_existing": 0, "updated_missing_metadata": 0, "copies_created": 0, "rejected_conflicts": 0})
    with app.app_context():
        try:
            books_by_isbn = {normalize_isbn(book.isbn): book for book in db.session.query(Book).all() if valid_isbn(book.isbn)}
            authors = {normalize(a.name): a for a in db.session.query(Author).all()}
            publishers = {normalize(p.name): p for p in db.session.query(Publisher).all()}
            categories = {normalize(c.name): c for c in db.session.query(Category).all()}
            departments = {normalize(d.code): d for d in db.session.query(Department).all()}
            departments.update({normalize(d.name): d for d in db.session.query(Department).all()})
            for item in records:
                if item["rejected"]:
                    continue
                row, evidence = item["row"], item["evidence"]
                isbn = normalize_isbn(row["isbn"])
                book = books_by_isbn.get(isbn)
                if book:
                    if normalize(book.title) != normalize(row["title"]):
                        stats["rejected_conflicts"] += 1
                        continue
                    stats["matched_existing"] += 1
                    changed = False
                    if not book.publication_year:
                        date_match = re.search(r"(?:1[4-9]\d{2}|20\d{2}|2100)", evidence.get("edition_publish_date", ""))
                        if date_match:
                            book.publication_year = int(date_match.group(0)); changed = True
                    if not book.edition and row.get("edition"):
                        book.edition = row["edition"]; changed = True
                    if not book.language and row.get("language"):
                        book.language = row["language"]; changed = True
                    if changed:
                        stats["updated_missing_metadata"] += 1
                    continue

                date_match = re.search(r"(?:1[4-9]\d{2}|20\d{2}|2100)", evidence.get("edition_publish_date", ""))
                year = int(date_match.group(0)) if date_match else (int(row["publication_year"]) if row.get("publication_year") else None)
                if year is not None and not 1400 <= year <= 2100:
                    stats["rejected_conflicts"] += 1
                    continue
                title = row["title"]
                book = Book(isbn=isbn, title=title, publication_year=year, edition=row.get("edition") or None, language=row.get("language") or "English", description=source_notes(row, evidence))
                publishers_in_record = evidence.get("edition_publishers") or []
                publisher_name = publishers_in_record[0] if publishers_in_record else row.get("publisher", "")
                if publisher_name:
                    publisher = publishers.get(normalize(publisher_name))
                    if publisher is None:
                        publisher = Publisher(name=publisher_name[:200]); publishers[normalize(publisher_name)] = publisher
                    book.publisher = publisher
                category_name = row.get("subject_area", "")
                if category_name:
                    category = categories.get(normalize(category_name))
                    if category is None:
                        category = Category(name=category_name[:120]); categories[normalize(category_name)] = category
                    book.category = category
                for author_name in split_authors(row.get("authors")):
                    author = authors.get(normalize(author_name))
                    if author is None:
                        author = Author(name=author_name[:180]); authors[normalize(author_name)] = author
                    if author not in book.authors:
                        book.authors.append(author)
                programme = normalize(row.get("programme"))
                department = departments.get(programme)
                if department is None and "aids" in programme:
                    department = departments.get("aids") or departments.get("b.tech - ai&ds")
                if department is None and "aiml" in programme:
                    department = departments.get("aiml") or departments.get("b.tech - ai&ml")
                if department is not None and department not in book.departments:
                    book.departments.append(department)
                db.session.add(book)
                books_by_isbn[isbn] = book
                stats["created_books"] += 1
            db.session.flush()
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    return dict(stats)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=Path(__file__).resolve().parents[1] / "database" / "LibSphere_Academic_Textbooks_1000.csv")
    parser.add_argument("--database-url", help="File-backed SQLite URL (defaults to DATABASE_URL or sqlite:///libsphere_test.db)")
    parser.add_argument("--report", type=Path, help="Preflight report JSON path")
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--use-preflight", type=Path, help="Reuse a report generated for this exact CSV hash instead of querying Open Library again")
    parser.add_argument("--apply", action="store_true", help="Apply verified rows after preflight; default is dry-run")
    args = parser.parse_args(argv)
    if not args.csv.is_file():
        print(f"CSV not found: {args.csv}", file=sys.stderr); return 2
    source_hash = hashlib.sha256(args.csv.read_bytes()).hexdigest()
    try:
        if args.use_preflight:
            saved = json.loads(args.use_preflight.read_text(encoding="utf-8"))
            if Path(saved.get("source_csv", "")).resolve() != args.csv.resolve() or saved.get("source_sha256") != source_hash:
                raise ValueError("Preflight report does not match this CSV path and SHA-256")
            report = saved
            records, summary = report["records"], report["summary"]
        else:
            rows = read_csv(args.csv)
            records, summary = verify_rows(rows)
            report = {
                "source_csv": str(args.csv.resolve()),
                "source_sha256": source_hash,
                "preflight_at": datetime.now().astimezone().isoformat(),
                "provider": "Open Library Books API by ISBN",
                "summary": summary,
                "records": records,
            }
    except Exception as exc:
        print(f"Preflight failed: {exc}", file=sys.stderr); return 2
    report_path = args.report or args.csv.with_name("LibSphere_Academic_Textbooks_1000_preflight.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"preflight": summary, "report": str(report_path.resolve()), "mode": "apply" if args.apply else "dry-run"}, ensure_ascii=False, indent=2))
    if not args.apply:
        return 0

    uri = args.database_url or os.getenv("DATABASE_URL") or "sqlite:///libsphere_test.db"
    os.environ["DATABASE_URL"] = uri
    os.environ.setdefault("APP_ENV", "testing")
    target = database_file(uri)
    if not target.is_file():
        print(f"Target database does not exist: {target}; refusing implicit creation.", file=sys.stderr); return 2
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = args.backup_dir or target.parent / "academic_import_backups"
    backup = backup_database(target, backup_dir / f"{target.stem}_before_academic_import_{stamp}.db")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from app import app, db
        from models import Book, BookCopy, Author, Publisher, Category, Department
        applied = import_verified(app, db, (Book, BookCopy, Author, Publisher, Category, Department), records)
        with app.app_context():
            final_counts = {name: db.session.execute(db.text(f"SELECT COUNT(*) FROM {table}")).scalar_one() for name, table in (("books", "books"), ("copies", "book_copies"), ("users", "users"), ("loans", "loans"), ("reservations", "reservations"), ("suggestions", "suggestions"), ("suggestion_votes", "suggestion_votes"), ("notifications", "notifications"))}
        report.update({"backup": str(backup), "applied": applied, "final_counts": final_counts})
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"applied": applied, "final_counts": final_counts, "backup": str(backup.resolve()), "report": str(report_path.resolve())}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"Import rolled back; backup at {backup}: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
