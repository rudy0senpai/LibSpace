"""Assign a one-time shared password to isolated local demo accounts."""
from __future__ import annotations

import os
from pathlib import Path

os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///libsphere_demo_full.db"

from sqlalchemy import text  # noqa: E402
from app import app, db  # noqa: E402
from models import RoleType, User  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402


PASSWORDS = {
    RoleType.STUDENT: "1234",
    RoleType.FACULTY: "1234",
    RoleType.DEPARTMENT: "1234",
    RoleType.LIBRARIAN: "1234",
}
VERSION = "shared-password-1234-v2"
EXPECTED_DB = (Path(__file__).resolve().parent / "instance" / "libsphere_demo_full.db").resolve()


with app.app_context():
    if db.engine.dialect.name != "sqlite":
        raise SystemExit("Local demo passwords can only be configured in SQLite.")
    actual_db = Path(db.engine.url.database or "").resolve()
    if actual_db != EXPECTED_DB or not EXPECTED_DB.is_file():
        raise SystemExit(f"Refusing to modify a database other than {EXPECTED_DB}.")

    db.session.execute(text(
        "CREATE TABLE IF NOT EXISTS local_demo_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT NOT NULL)"
    ))
    current_version = db.session.execute(text(
        "SELECT setting_value FROM local_demo_settings WHERE setting_key = 'demo_password_version'"
    )).scalar_one_or_none()
    if current_version == VERSION:
        db.session.commit()
        print("Local demo passwords are already configured; leaving them unchanged.")
    else:
        users = db.session.query(User).filter(User.email.like("%@libsphere.test")).all()
        for user in users:
            password = PASSWORDS.get(user.role)
            if password:
                user.password_hash = generate_password_hash(password, method="scrypt")
        db.session.execute(text(
            "INSERT INTO local_demo_settings (setting_key, setting_value) "
            "VALUES ('demo_password_version', :version) "
            "ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value"
        ), {"version": VERSION})
        db.session.commit()
        print(f"Configured hashed local demo passwords for {len(users)} testing accounts.")
