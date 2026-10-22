#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
unset PYTHONPATH

PYTHON="$ROOT_DIR/backend/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$ROOT_DIR/backend/.venv"
fi
"$PYTHON" -m pip install -r "$ROOT_DIR/backend/requirements.txt"

# Keep local testing data isolated from the existing application catalog. The
# initializer creates one fully populated demo DB and preserves it on later runs.
export APP_ENV=testing
export DATABASE_URL=sqlite:///libsphere_demo_full.db
"$PYTHON" "$ROOT_DIR/backend/init_local_demo_db.py"
"$PYTHON" "$ROOT_DIR/backend/configure_local_demo_passwords.py"

export BACKEND_HOST=127.0.0.1
export BACKEND_PORT=5001
export CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
export JWT_SECRET_KEY="$(openssl rand -hex 32)"

cd "$ROOT_DIR/backend"
exec "$PYTHON" app.py
