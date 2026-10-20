"""Add the catalogue provenance and availability tables without resetting the database.

Run from backend/ with a file-backed SQLite DATABASE_URL and an explicit backup path.
"""
import argparse
import json
import sqlite3
from pathlib import Path

from app import app, db
from models import Book, BookAvailabilityHold, BookSourceMetadata

PREFIX = "[Academic CSV provenance: "


def make_backup(database_path: Path, backup_path: Path) -> None:
    if not database_path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {database_path}")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if backup_path.exists():
        raise FileExistsError(f"Backup path already exists: {backup_path}")
    if backup_path.resolve() == database_path.resolve():
        raise ValueError("Backup path must differ from the active database path.")
    with sqlite3.connect(database_path) as source, sqlite3.connect(backup_path) as target:
        source.backup(target)
    with sqlite3.connect(backup_path) as check:
        result = check.execute("PRAGMA integrity_check").fetchone()[0]
        fk_errors = check.execute("PRAGMA foreign_key_check").fetchall()
    if result != "ok" or fk_errors:
        backup_path.unlink(missing_ok=True)
        raise RuntimeError(f"Backup validation failed: integrity={result}, fk_errors={len(fk_errors)}")


def run_migration(backup_path: Path) -> dict:
    with app.app_context():
        return _run_migration(backup_path)


def _run_migration(backup_path: Path) -> dict:
    if db.engine.dialect.name != "sqlite":
        raise RuntimeError("This additive migration currently supports SQLite only.")
    database_path = Path(db.engine.url.database).resolve()
    make_backup(database_path, backup_path)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[BookSourceMetadata.__table__, BookAvailabilityHold.__table__])
        migrated = 0
        rows = db.session.query(Book).filter(Book.description.like("[Academic CSV provenance:%")).all()
        for book in rows:
            raw = book.description[len(PREFIX):].rstrip("]")
            try:
                metadata = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                metadata = {"legacy_provenance": raw}
            if not book.source_metadata:
                book.source_metadata = BookSourceMetadata(
                    source_name="Academic CSV provenance",
                    metadata_json=json.dumps(metadata, ensure_ascii=False, separators=(",", ":")),
                )
            book.description = None
            migrated += 1
        db.session.commit()
        db.session.remove()
    with sqlite3.connect(database_path) as check:
        integrity = check.execute("PRAGMA integrity_check").fetchone()[0]
        fk_errors = check.execute("PRAGMA foreign_key_check").fetchall()
        table_names = {row[0] for row in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    expected = {"book_source_metadata", "book_availability_holds"}
    if integrity != "ok" or fk_errors or not expected.issubset(table_names):
        raise RuntimeError(f"Migration verification failed: integrity={integrity}, fk_errors={len(fk_errors)}, missing_tables={sorted(expected-table_names)}")
    return {"database": str(database_path), "backup": str(backup_path.resolve()), "legacy_rows_migrated": migrated, "integrity": integrity, "foreign_key_errors": len(fk_errors)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-path", type=Path, required=True, help="New verified SQLite backup file created before migration")
    args = parser.parse_args()
    result = run_migration(args.backup_path)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
