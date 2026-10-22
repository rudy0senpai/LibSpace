"""Create the isolated, fully populated SQLite database for local demo use."""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BACKEND_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
DEMO_DB = INSTANCE_DIR / "libsphere_demo_full.db"

if DEMO_DB.exists():
    try:
        with sqlite3.connect(f"file:{DEMO_DB}?mode=ro", uri=True) as existing:
            if existing.execute("SELECT COUNT(*) FROM books").fetchone()[0] >= 100:
                print(f"Local demo database already exists; leaving it unchanged: {DEMO_DB}")
                raise SystemExit(0)
    except sqlite3.Error:
        raise SystemExit(f"Existing demo database is unreadable; preserving it: {DEMO_DB}")
    raise SystemExit(f"Existing demo database has fewer than 100 books; preserving it: {DEMO_DB}")

# Build the fixture in memory first. The legacy 119-book fixture is allowed in
# isolated tests; it is never written into the user's normal libsphere.db.
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("JWT_SECRET_KEY", secrets.token_urlsafe(32))
sys.path.insert(0, str(BACKEND_DIR))

import seed_test_db  # noqa: E402

summary = seed_test_db.seed_all()
if summary["books"] < 100 or summary["books"] > 200:
    raise RuntimeError(f"Expected 100–200 demo books, got {summary['books']}.")

with seed_test_db.app.app_context():
    raw_connection = seed_test_db.db.engine.raw_connection()
    try:
        with sqlite3.connect(DEMO_DB) as destination:
            raw_connection.driver_connection.backup(destination)
    finally:
        raw_connection.close()

print(json.dumps({**summary, "database": str(DEMO_DB.resolve())}, indent=2))
