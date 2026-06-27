# Dual Database Runtime

This document describes the runtime flags introduced for the dual-database transition work.

## Flags

- `USE_SQLALCHEMY_READS`
  Default: `false`
- `USE_SQLALCHEMY_WRITES`
  Default: `false`
- `DATABASE_URL`
  Optional PostgreSQL connection string
- `APP_DB_PATH`
  Optional SQLite file path override

## Current Behavior

The runtime currently supports these rollout stages:

- `SQLite only`
  `USE_SQLALCHEMY_READS=false`
  `USE_SQLALCHEMY_WRITES=false`
  Reads and writes both use SQLite.

- `Read from PostgreSQL / ORM`
  `USE_SQLALCHEMY_READS=true`
  `USE_SQLALCHEMY_WRITES=false`
  Read paths can use SQLAlchemy ORM backed by PostgreSQL while writes still use SQLite.

- `Future: Dual Write`
  `USE_SQLALCHEMY_READS=true`
  `USE_SQLALCHEMY_WRITES=true`
  Reads use PostgreSQL / ORM, and writes are expected to write to both SQLite and PostgreSQL.

- `Future: PostgreSQL primary`
  PostgreSQL becomes the primary runtime database after dual-write validation is complete.

At the current stage:

- Existing route URLs are unchanged.
- Existing write flows still use sqlite3.
- `settings`, `users`, `sheets`, `progress`, `unit_extra`, `extra_fields`, and `unit_extra_values` read paths can switch through `USE_SQLALCHEMY_READS`.
- Without `DATABASE_URL`, the app still falls back to SQLite.
- With `DATABASE_URL`, SQLAlchemy is configured with `postgresql+psycopg://`.

## Intended Use

These flags are meant to support a gradual rollout of dual-database runtime behavior in later steps.

- Keep `USE_SQLALCHEMY_READS=false`
- Keep `USE_SQLALCHEMY_WRITES=false`

Do not enable production behavior changes until the related runtime work is implemented and verified.
