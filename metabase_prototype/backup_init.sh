#!/usr/bin/env bash

echo "LOADING DUMP FILE"

psql -U metabase -d postgres -c "DROP DATABASE metabase;"
psql -U metabase -d postgres -c "CREATE DATABASE metabase;"

pg_restore -c -U metabase -d metabase /docker-entrypoint-initdb.d/def.dump
