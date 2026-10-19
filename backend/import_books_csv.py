"""Idempotently import CSV book metadata into the configured LibSphere SQLite DB.

CSV inventory columns are treated as unverified summary values; this importer
never creates physical copies or changes the catalogue's circulation inventory.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import joinedload, selectinload

REQUIRED = {"title"}
FIELDS = ("book_id", "title", "author", "department", "category", "publisher", "publication_year", "edition", "isbn", "language", "total_copies", "available_copies", "shelf_location", "description", "record_type")


def norm(value: str | None) -> str:
    return " ".join((value or "").strip().casefold().split())


def norm_isbn(value: str | None) -> str | None:
    digits = re.sub(r"[^0-9Xx]", "", value or "").upper()
    if len(digits) == 10 and digits[:9].isdigit() and (digits[9].isdigit() or digits[9] == "X"):
        check = sum((10 - i) * (10 if ch == "X" else int(ch)) for i, ch in enumerate(digits)) % 11
        return digits if check == 0 else None
    if len(digits) == 13 and digits.isdigit():
        check = sum(int(ch) * (1 if i % 2 == 0 else 3) for i, ch in enumerate(digits)) % 10
        return digits if check == 0 else None
    return None


def identity(row: dict) -> tuple[str, ...]:
    """Stable fallback key avoids merging same-title editions/authors."""
    return tuple(norm(row.get(k)) for k in ("title", "author", "edition", "publication_year", "publisher"))


def source_note(row: dict) -> str:
    fields = ("book_id", "department", "total_copies", "available_copies", "shelf_location", "record_type")
    values = [f"{key}={row[key]}" for key in fields if row.get(key)]
    return "[CSV source metadata: " + "; ".join(values) + ". Inventory counts/location are source-reported summaries, not imported physical copies.]"


def read_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or ())
        missing = REQUIRED - headers
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")
        if not headers.issuperset(FIELDS):
            raise ValueError(f"CSV missing expected columns: {', '.join(sorted(set(FIELDS) - headers))}")
        for row_number, raw in enumerate(reader, start=2):
            yield row_number, {key: (value or "").strip() for key, value in raw.items()}


def database_file(uri: str) -> Path:
    if not uri.startswith("sqlite:"):
        raise ValueError("CSV import is limited to SQLite databases.")
    if uri in ("sqlite://", "sqlite:///:memory:"):
        raise ValueError("Refusing to import into an in-memory SQLite database.")
    path = uri.removeprefix("sqlite:///")
    if uri.startswith("sqlite:////"):
        path = "/" + path
    result = Path(path)
    if not result.is_absolute():
        result = Path(__file__).resolve().parent / "instance" / result
    return result.resolve()


def backup_database(source: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(destination)
    try:
        src.backup(dst)
        result = dst.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"Backup integrity check failed: {result}")
    finally:
        dst.close()
        src.close()
    return destination


def import_rows(app, db, Book, Author, Publisher, Category, Department, book_departments, rows, report_path: Path):
    stats = Counter({key: 0 for key in ("rows", "new_books", "matched_existing", "updated", "duplicate_rows_skipped", "duplicate_isbn_rows_skipped", "rejected", "missing_isbn", "invalid_isbn", "unmapped_departments")})
    rejected = []
    with app.app_context():
        try:
            books = db.session.query(Book).options(selectinload(Book.authors), joinedload(Book.publisher)).all()
            by_isbn = {norm_isbn(book.isbn): book for book in books if norm_isbn(book.isbn)}
            by_identity = {identity({"title": b.title, "author": ";".join(sorted(a.name for a in b.authors)), "edition": b.edition or "", "publication_year": str(b.publication_year or ""), "publisher": b.publisher.name if b.publisher else ""}): b for b in books}
            authors = {norm(a.name): a for a in db.session.query(Author).all()}
            publishers = {norm(p.name): p for p in db.session.query(Publisher).all()}
            categories = {norm(c.name): c for c in db.session.query(Category).all()}
            departments = {norm(d.name): d for d in db.session.query(Department).all()}
            department_aliases = {
                norm("Computer Science & Engineering"): "B.Tech - CSE",
                norm("AI & Data Science"): "B.Tech - AI&DS",
                norm("Electrical Engineering"): "B.Tech - Electrical",
                norm("Mechanical Engineering"): "B.Tech - Mechanical",
                norm("Civil Engineering"): "B.Tech - Civil",
            }
            seen_isbn, seen_identity = set(), set()
            pending = []
            for row_number, row in rows:
                stats["rows"] += 1
                title = row.get("title", "")
                if not title or len(title) > 300:
                    stats["rejected"] += 1
                    rejected.append({"row_number": row_number, "reason": "missing title or title exceeds 300 characters", **row})
                    continue
                limits = {"author": 180, "publisher": 200, "category": 120, "edition": 80, "language": 80, "isbn": 20}
                too_long = [field for field, maximum in limits.items() if len(row.get(field, "")) > maximum]
                if too_long:
                    stats["rejected"] += 1
                    rejected.append({"row_number": row_number, "reason": "field exceeds schema length: " + ", ".join(too_long), **row})
                    continue
                year_text = row.get("publication_year", "")
                try:
                    year = int(year_text) if year_text else None
                    if year is not None and not 1400 <= year <= 2100:
                        raise ValueError
                except ValueError:
                    stats["rejected"] += 1
                    rejected.append({"row_number": row_number, "reason": "invalid publication_year", **row})
                    continue
                isbn_input = row.get("isbn", "")
                isbn = norm_isbn(isbn_input) if isbn_input else None
                if not isbn_input:
                    stats["missing_isbn"] += 1
                    stats["rejected"] += 1
                    rejected.append({"row_number": row_number, "reason": "missing ISBN; legacy blank-ISBN imports are disabled", **row})
                    continue
                if not isbn:
                    stats["invalid_isbn"] += 1
                    stats["rejected"] += 1
                    rejected.append({"row_number": row_number, "reason": "invalid ISBN checksum", **row})
                    continue
                key = identity({**row, "publication_year": str(year or "")})
                if isbn and isbn in seen_isbn or not isbn and key in seen_identity:
                    stats["duplicate_rows_skipped"] += 1
                    if isbn:
                        stats["duplicate_isbn_rows_skipped"] += 1
                    continue
                if isbn: seen_isbn.add(isbn)
                else: seen_identity.add(key)
                found = by_isbn.get(isbn) if isbn else by_identity.get(key)
                if found:
                    stats["matched_existing"] += 1
                    changed = False
                    if not found.description and row.get("description"):
                        found.description = row["description"]
                        changed = True
                    if not found.subtitle and row.get("edition"):
                        found.subtitle = row["edition"]
                        changed = True
                    if not found.publication_year and year:
                        found.publication_year = year
                        changed = True
                    if found.description and "UNVERIFIED GENERATED DATASET" in found.description and "[CSV source metadata:" not in found.description:
                        found.description = f"{found.description}\n\n{source_note(row)}"
                        changed = True
                    if changed:
                        stats["updated"] += 1
                    continue
                author_names = [name.strip() for name in row.get("author", "").split(";") if name.strip()]
                if not author_names and row.get("author"):
                    author_names = [row["author"]]
                book = Book(title=title, isbn=isbn, description=row.get("description") or None,
                            publication_year=year, edition=row.get("edition") or None,
                            subtitle=row.get("edition") or None, language=row.get("language") or "English")
                publisher_name = row.get("publisher", "")
                if publisher_name:
                    pub = publishers.get(norm(publisher_name))
                    if not pub:
                        pub = Publisher(name=publisher_name[:200]); publishers[norm(publisher_name)] = pub
                    book.publisher = pub
                category_name = row.get("category", "")
                if category_name:
                    cat = categories.get(norm(category_name))
                    if not cat:
                        cat = Category(name=category_name[:120]); categories[norm(category_name)] = cat
                    book.category = cat
                for name in author_names:
                    author = authors.get(norm(name))
                    if not author:
                        author = Author(name=name[:180]); authors[norm(name)] = author
                    book.authors.append(author)
                department_key = norm(row.get("department"))
                department = departments.get(department_key) or departments.get(norm(department_aliases.get(department_key)))
                if department:
                    book.departments.append(department)
                elif row.get("department"):
                    stats["unmapped_departments"] += 1
                description = row.get("description") or ""
                record_type = row.get("record_type") or ""
                if "generated" in record_type.casefold() and "verify" in record_type.casefold():
                    warning = "[UNVERIFIED GENERATED DATASET: bibliographic details require verification before operational use.]"
                    description = f"{description}\n\n{warning}" if description else warning
                description = f"{description}\n\n{source_note(row)}" if description else source_note(row)
                book.description = description or None
                pending.append(book)
                if isbn: by_isbn[isbn] = book
                by_identity[key] = book
                stats["new_books"] += 1
                if len(pending) >= 500:
                    db.session.add_all(pending); db.session.flush(); pending.clear()
            if pending:
                db.session.add_all(pending)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["row_number", "reason", *FIELDS], extrasaction="ignore")
        writer.writeheader(); writer.writerows(rejected)
    return stats


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path, help="Input CSV path")
    parser.add_argument("--database-url", help="SQLite URL; defaults to DATABASE_URL or testing DB")
    parser.add_argument("--backup-dir", type=Path, help="Backup destination directory; defaults beside CSV")
    parser.add_argument("--report", type=Path, help="Rejected-row report path; defaults beside CSV")
    args = parser.parse_args(argv)
    uri = args.database_url or os.getenv("DATABASE_URL") or "sqlite:///libsphere_test.db"
    os.environ["DATABASE_URL"] = uri
    os.environ.setdefault("APP_ENV", "testing")
    target = database_file(uri)
    if not target.is_file():
        print(f"Database file does not exist: {target}; refusing implicit database creation.", file=sys.stderr)
        return 2
    if not args.csv.is_file():
        print(f"CSV file not found: {args.csv}", file=sys.stderr); return 2
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = args.backup_dir or args.csv.resolve().parent / "libsphere_import_backups"
    backup = backup_database(target, backup_dir / f"{target.stem}_before_import_{stamp}.db")
    report_path = args.report or args.csv.resolve().with_name(f"{args.csv.stem}_import_rejected_{stamp}.csv")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from app import app, db
    from models import Book, Author, Publisher, Category, Department, book_departments
    try:
        stats = import_rows(app, db, Book, Author, Publisher, Category, Department, book_departments, read_rows(args.csv), report_path)
        with app.app_context():
            counts = {"books": db.session.query(Book).count(), "authors": db.session.query(Author).count(),
                      "publishers": db.session.query(Publisher).count(), "categories": db.session.query(Category).count()}
        final_report = {"database": str(target), "csv": str(args.csv.resolve()), "backup": str(backup),
                        "rejected_csv": str(report_path), "counts": dict(stats), "final_counts": counts}
        report_json = report_path.with_suffix(".json")
        report_json.write_text(json.dumps(final_report, indent=2), encoding="utf-8")
        print(json.dumps(final_report, indent=2))
        return 0
    except Exception as exc:
        print(f"FATAL: import rolled back: {exc}; backup: {backup}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
