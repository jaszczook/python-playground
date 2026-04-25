#!/usr/bin/env bash
# Creates all application databases. phoenix sits unused unless the eval profile is active.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE my_app;
    CREATE DATABASE phoenix;
    GRANT ALL PRIVILEGES ON DATABASE my_app TO "$POSTGRES_USER";
    GRANT ALL PRIVILEGES ON DATABASE phoenix TO "$POSTGRES_USER";
EOSQL
