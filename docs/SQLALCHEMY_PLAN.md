# SQLAlchemy Plan

## Goal

Prepare a gradual transition from direct `sqlite3` usage to SQLAlchemy without changing the current production behavior in v2.3.

## Scope For This Step

- Add SQLAlchemy-related dependencies
- Add shared database extension bootstrap in `database.py`
- Add draft ORM models in `models.py`
- Reserve `migrations/` for future Alembic revisions

## Non-Goals

- Do not replace the current `sqlite3` data access
- Do not modify existing routes
- Do not change the current deployment flow
- Do not run schema migration against production data yet

## Planned Next Steps

1. Wire `database.py` into app startup behind a non-invasive initialization step
2. Validate model definitions against the live SQLite schema
3. Introduce Flask-Migrate commands and first baseline migration
4. Migrate one read-only workflow at a time to SQLAlchemy
5. Evaluate PostgreSQL readiness after ORM and migrations are stable

## Notes

- Current models intentionally mirror the existing tables only as a draft
- Composite primary keys remain in `progress` and `unit_extra_values`
- Timestamp fields stay text-based for now to avoid changing live behavior
