#!/usr/bin/env bash
set -euo pipefail
cd backend
python -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -r requirements.txt
cp -n .env.example .env || true
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
