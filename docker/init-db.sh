#!/usr/bin/env bash
# Creates the phoenix database. my_app is created via POSTGRES_DB env var.
# Connects explicitly to 'postgres' to avoid depending on POSTGRES_DB being available.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-EOSQL
    SELECT 'CREATE DATABASE phoenix' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'phoenix')\gexec
    GRANT ALL PRIVILEGES ON DATABASE phoenix TO "$POSTGRES_USER";
EOSQL
