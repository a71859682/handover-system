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

At this stage, these flags are configuration-only.

- Existing route and service flows are unchanged.
- Existing reads are not switched to ORM.
- Existing writes are not switched to ORM.
- The default runtime behavior stays the same as before:
  without `DATABASE_URL`, the app uses SQLite;
  with `DATABASE_URL`, SQLAlchemy is configured with that PostgreSQL URL.

## Intended Use

These flags are meant to support a gradual rollout of dual-database runtime behavior in later steps.

- Keep `USE_SQLALCHEMY_READS=false`
- Keep `USE_SQLALCHEMY_WRITES=false`

Do not enable production behavior changes until the related runtime work is implemented and verified.
