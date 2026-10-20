"""Repair missing or expired catalogue covers in bounded batches."""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", help="Existing SQLite URL; defaults to DATABASE_URL or app config")
    parser.add_argument("--limit", type=int, default=50, help="Maximum attempted records (1-200)")
    parser.add_argument("--batch-size", type=int, default=10, help="Print progress after each group")
    parser.add_argument("--retry-failed", action="store_true", help="Retry temporary negative-cache entries now")
    parser.add_argument("--refresh-book-id", help="Force-refresh one book; only a verified provider match may replace its cover")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 200 or not 1 <= args.batch_size <= args.limit:
        parser.error("--limit must be 1-200 and --batch-size must be between 1 and --limit")
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    os.environ.setdefault("APP_ENV", "testing")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from app import app, db
    from models import Book, CoverLookupCache
    from cover_service import as_utc, cover_service, cover_cache_key, valid_isbn
    from import_academic_textbooks import database_file
    try:
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        target = database_file(uri)
        if not target.is_file():
            raise ValueError(f"Database file does not exist: {target}; refusing implicit creation")
        # Additive table creation only; this command never resets, imports, or seeds.
        with app.app_context():
            db.create_all()
            if args.refresh_book_id:
                book = db.session.get(Book, args.refresh_book_id)
                if not book:
                    raise ValueError("Book id was not found")
                candidates = [book]
                skipped = 0
            else:
                now = datetime.now(timezone.utc)
                books = db.session.query(Book).order_by(Book.title.asc(), Book.id.asc()).all()
                candidates = []
                skipped = 0
                for book in books:
                    if not valid_isbn(book.isbn):
                        skipped += 1
                        continue
                    cached = db.session.get(CoverLookupCache, cover_cache_key(book))
                    expiry = as_utc(cached.expires_at) if cached else None
                    fresh = bool(expiry and expiry > now)
                    if fresh and cached.status == "MATCHED" and cached.cover_url == book.cover_image_ref and book.cover_image_ref:
                        skipped += 1
                        continue
                    if fresh and cached.status in {"FAILED", "NO_MATCH"} and not args.retry_failed:
                        skipped += 1
                        continue
                    candidates.append(book)

            records = candidates[:args.limit]
            report = Counter({"processed": 0, "matched": 0, "unresolved": 0, "failed": 0, "skipped": skipped})
            unresolved_isbns = []
            for index, book in enumerate(records, start=1):
                report["processed"] += 1
                cached = db.session.get(CoverLookupCache, cover_cache_key(book))
                retry_now = bool(args.retry_failed and cached and cached.status in {"FAILED", "NO_MATCH"})
                reported_failure = bool(cached and cached.error and cached.error.startswith("Browser reported failed cover"))
                result = cover_service.lookup(
                    book,
                    db.session,
                    CoverLookupCache,
                    refresh=bool(args.refresh_book_id) or retry_now,
                    reported_failure=reported_failure,
                    validate_existing=not bool(args.refresh_book_id),
                )
                if result.get("matched"):
                    report["matched"] += 1
                else:
                    report["unresolved"] += 1
                    if result.get("failed"):
                        report["failed"] += 1
                    unresolved_isbns.append({"isbn": book.isbn, "title": book.title,
                                             "reason": result.get("error") or "No reliable matching cover found"})
                if index % args.batch_size == 0 or index == len(records):
                    print(json.dumps({"progress": index, "batch_size": args.batch_size, "current_title": book.title}, ensure_ascii=False))
            summary = dict(report)
            summary.update({
                "eligible_candidates": len(candidates),
                "deferred_candidates": max(0, len(candidates) - len(records)),
                "unresolved_isbns": unresolved_isbns,
                "database_file": target.name,
                "refresh_book_id": args.refresh_book_id,
            })
            print(json.dumps({"summary": summary}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"Cover batch failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
