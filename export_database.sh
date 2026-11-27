#!/usr/bin/env bash
set -euo pipefail
# PostgreSQL pg_dump must be installed; the database must be seeded first.
# For local docker-compose: docker compose exec -T db pg_dump -U conference -d conference_db --no-owner --no-privileges --inserts --clean --if-exists > schema_and_seed.sql
: "${DATABASE_URL:?Set DATABASE_URL to a PostgreSQL URL in the environment}"
pg_dump "$DATABASE_URL" --no-owner --no-privileges --inserts --clean --if-exists > schema_and_seed.sql
echo 'Created schema_and_seed.sql'
