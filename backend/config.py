import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
    if APP_ENV == "testing":
        SQLALCHEMY_DATABASE_URI = os.getenv(
            "DATABASE_URL",
            os.getenv("TEST_DATABASE_URL", "sqlite:///libsphere_test.db"),
        )
        if not SQLALCHEMY_DATABASE_URI.startswith("sqlite:"):
            raise RuntimeError("APP_ENV=testing requires a SQLite DATABASE_URL; refusing to connect to another database.")
    else:
        configured_database_url = os.getenv("DATABASE_URL", "")
        if APP_ENV == "production":
            SQLALCHEMY_DATABASE_URI = configured_database_url or None
        else:
            # Local development stays on persistent SQLite even if a stale
            # PostgreSQL URL exists in a developer's environment.
            SQLALCHEMY_DATABASE_URI = (
                configured_database_url
                if configured_database_url.startswith("sqlite:")
                else "sqlite:///libsphere.db"
            )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_ACCESS_TOKEN_HOURS", "8")))
    BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", "5001"))
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    CORS_ORIGINS = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            f"{FRONTEND_URL},http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    )
