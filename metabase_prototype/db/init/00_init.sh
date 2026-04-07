#!/usr/bin/env bash
set -euo pipefail

echo "Creating MVP results database and loading schema..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
SELECT 'CREATE DATABASE ' || quote_ident('${MVP_RESULTS_DB}')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${MVP_RESULTS_DB}')\gexec
SQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname="$MVP_RESULTS_DB" -f /docker-entrypoint-initdb.d/01_schema.sql
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname="$MVP_RESULTS_DB" -f /docker-entrypoint-initdb.d/02_data.sql

echo "MVP results database initialized."
