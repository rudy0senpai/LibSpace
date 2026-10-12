#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example; edit it if your PostgreSQL settings differ."
fi

python -m venv backend/.venv
if [[ -f backend/.venv/Scripts/activate ]]; then
  # Git Bash on Windows
  source backend/.venv/Scripts/activate
else
  source backend/.venv/bin/activate
fi
python -m pip install -r backend/requirements.txt
python backend/app.py
