#!/usr/bin/env bash
# Creates the phoenix database. my_app is created via POSTGRES_DB env var.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE phoenix;
    GRANT ALL PRIVILEGES ON DATABASE phoenix TO "$POSTGRES_USER";
EOSQL
