#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
cd "$FRONTEND_DIR"

export VITE_API_URL=http://127.0.0.1:5001
export VITE_AUTH_MODE=testing

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  npm install
fi

exec npm run dev -- --host 127.0.0.1 --port 5173
