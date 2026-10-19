"""Progressively retrieve missing catalogue covers; never runs at app startup."""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", help="Existing SQLite URL; defaults to DATABASE_URL or app config")
    parser.add_argument("--limit", type=int, default=50, help="Maximum records in this batch")
    parser.add_argument("--batch-size", type=int, default=10, help="Print progress after each group")
    parser.add_argument("--retry-failed", action="store_true", help="Retry provider failures from the cache")
    parser.add_argument("--refresh-book-id", help="Force-refresh one book; only a staff-triggered match can replace an existing cover")
    args = parser.parse_args(argv)
    if args.limit < 1 or args.batch_size < 1:
        parser.error("--limit and --batch-size must be positive")
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    os.environ.setdefault("APP_ENV", "testing")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from app import app, db
    from models import Book, CoverLookupCache
    from cover_service import cover_service, cover_cache_key
    from import_academic_textbooks import database_file
    try:
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        target = database_file(uri)
        if not target.is_file():
            raise ValueError(f"Database file does not exist: {target}; refusing implicit creation")
        # Creating the new cache table is additive; there is no catalogue reset or seeding.
        with app.app_context():
            db.create_all()
            if args.refresh_book_id:
                records = [db.session.get(Book, args.refresh_book_id)]
                if not records[0]:
                    raise ValueError("Book id was not found")
            else:
                records = (db.session.query(Book)
                    .filter((Book.cover_image_ref.is_(None)) | (Book.cover_image_ref == ""))
                    .order_by(Book.title.asc(), Book.id.asc())
                    .limit(args.limit).all())
            report = Counter({"records_processed": 0, "covers_matched": 0, "no_reliable_match": 0, "failed_requests": 0, "skipped_records": 0, "cached_results_reused": 0})
            for index, book in enumerate(records, start=1):
                report["records_processed"] += 1
                cached = db.session.get(CoverLookupCache, cover_cache_key(book))
                force = bool(args.refresh_book_id) or bool(args.retry_failed and cached and cached.status == "FAILED")
                if book.cover_image_ref and not args.refresh_book_id:
                    report["skipped_records"] += 1
                    continue
                if cached and cached.status == "FAILED" and not args.retry_failed and not args.refresh_book_id and cached.expires_at:
                    from datetime import datetime, timezone
                    expiry = cached.expires_at
                    if expiry.tzinfo is None:
                        expiry = expiry.replace(tzinfo=timezone.utc)
                    if expiry > datetime.now(timezone.utc):
                        report["skipped_records"] += 1
                        report["cached_results_reused"] += 1
                        continue
                result = cover_service.lookup(book, db.session, CoverLookupCache, refresh=force)
                if result.get("cached"):
                    report["cached_results_reused"] += 1
                if result.get("matched"):
                    report["covers_matched"] += 1
                elif result.get("failed"):
                    report["failed_requests"] += 1
                elif not result.get("failed"):
                    report["no_reliable_match"] += 1
                if index % args.batch_size == 0 or index == len(records):
                    print(json.dumps({"progress": index, "batch_size": args.batch_size, "current_title": book.title}, ensure_ascii=False))
            print(json.dumps({"summary": dict(report), "database_url": uri, "refresh_book_id": args.refresh_book_id}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"Cover batch failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
