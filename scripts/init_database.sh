#!/usr/bin/env bash
set -euo pipefail
DB_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/mitrc_libsphere}"
echo "Creating LibSphere schema..."
psql "$DB_URL" -f database/schema/schema.sql
echo "Loading realistic demo data..."
psql "$DB_URL" -f database/seed/seed.sql
echo "Database initialized."
