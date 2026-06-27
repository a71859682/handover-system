# Dual Write Preparation

This document inventories the current write paths before any PostgreSQL write enablement.

Current boundary:

- Do not enable `USE_SQLALCHEMY_WRITES=true`
- Do not switch PostgreSQL to primary
- Do not remove SQLite
- Do not change production write behavior yet

## Current State

- Runtime reads can be switched by `USE_SQLALCHEMY_READS`
- Runtime writes still use SQLite only
- No production write path is currently controlled by `USE_SQLALCHEMY_WRITES`
- `DUAL_WRITE_DRY_RUN=true` only emits dry-run logs for future dual-write entry points
- ORM write flow is not enabled

## Dry-Run Mode

- Purpose:
  capture future dual-write payloads without changing the real write target
- Enable:
  set `DUAL_WRITE_DRY_RUN=true`
- Validation:
  run `python tools/check_dual_write_dry_run.py`
- Behavior:
  production writes still go to SQLite only
- Safety boundary:
  dry-run does not perform any PostgreSQL `INSERT`, `UPDATE`, or `DELETE`
- Logged fields:
  `operation`, `table`, `key`, `fields`, `timestamp`, `dry_run=true`
- Log visibility:
  dry-run logs should appear in Render Logs, gunicorn logs, local console output, or local `server.err.log`
- Expected prefix:
  `DUAL_WRITE_DRY_RUN operation=... table=... key=... fields=... timestamp=... dry_run=true`

## Observing Dry-Run Logs

- Render:
  open the service logs and search for `DUAL_WRITE_DRY_RUN`
- gunicorn / platform logs:
  search stderr/stdout for `DUAL_WRITE_DRY_RUN`
- Local Flask server:
  run with `DUAL_WRITE_DRY_RUN=true` and inspect console output or redirected `server.err.log`
- Verification flow:
  modify a setting, update progress, create a sheet, or create a user, then confirm a matching `DUAL_WRITE_DRY_RUN` line appears

## Write Entry Inventory

### Runtime write entry points

1. `routes/admin.py` → `/admin/users` `POST`
   - Behavior:
     create user, update user
   - Tables:
     `users`
   - Current write path:
     SQLite via `app.db()` and `conn.execute(...)`
   - Runtime flag control:
     No
   - Notes:
     password hashing happens here and must stay identical across any future dual-write path

2. `routes/admin.py` → `/admin/table` `POST`
   - Behavior:
     create/delete sheets, create/delete tasks, create/delete floors, create/delete units, create/delete extra fields, save sheet metadata and naming updates
   - Tables:
     `sheets`
     `tasks`
     `floors`
     `units`
     `progress`
     `unit_extra`
     `extra_fields`
     `unit_extra_values`
     `meta`
   - Current write path:
     SQLite via `app.db()` and `conn.execute(...)`
   - Runtime flag control:
     No
   - Notes:
     this is the broadest write surface and contains multi-table cascading behavior

3. `routes/api.py` → `/api/progress` `POST`
   - Delegates to:
     `services/progress_service.py:update_progress`
   - Tables:
     `progress`
   - Current write path:
     SQLite via `app.db()` and `conn.execute(...)`
   - Runtime flag control:
     No
   - Notes:
     single upsert-style write with `updated_by` / `updated_at`

4. `routes/api.py` → `/api/unit-extra` `POST`
   - Delegates to:
     `services/progress_service.py:update_unit_extra`
   - Tables:
     `unit_extra`
     `unit_extra_values`
   - Current write path:
     SQLite via `app.db()` and `conn.execute(...)`
   - Runtime flag control:
     No
   - Notes:
     includes built-in field updates and custom extra-field upserts

5. `routes/api.py` → `/api/reset-sheet` `POST`
   - Delegates to:
     `services/progress_service.py:reset_sheet`
   - Tables:
     `progress`
     `unit_extra`
     `unit_extra_values`
   - Current write path:
     SQLite via `app.db()` and `conn.execute(...)`
   - Runtime flag control:
     No
   - Notes:
     bulk reset path; high impact because it touches many rows in one request

### Bootstrap / setup / maintenance write entry points

6. `app.py` → `seed_admin(conn)`
   - Tables:
     `users`
   - Current write path:
     SQLite
   - Runtime flag control:
     No

7. `app.py` → `set_setting(conn)` and `seed_settings(conn)`
   - Tables:
     `meta`
   - Current write path:
     SQLite
   - Runtime flag control:
     No

8. `app.py` → `seed_from_excel(conn)`
   - Tables:
     `sheets`
     `tasks`
     `floors`
     `units`
     `progress`
     `unit_extra`
     `meta`
   - Current write path:
     SQLite
   - Runtime flag control:
     No

9. `app.py` → `migrate_schema(conn)`
   - Tables / schema:
     `users`
     `sheets`
     `tasks`
     `floors`
     `unit_extra`
   - Current write path:
     SQLite schema migration / data backfill
   - Runtime flag control:
     No

10. `app.py` → `normalize_progress_values(conn)`
    - Tables:
      `progress`
    - Current write path:
      SQLite
    - Runtime flag control:
      No

11. `app.py` → `migrate_unit_layout(conn)`
    - Tables:
      `progress`
      `unit_extra`
      `units`
      `floors`
      `meta`
    - Current write path:
      SQLite
    - Runtime flag control:
      No
    - Notes:
      destructive/rebuild-style maintenance path with deletes and reinserts

12. `app.py` → `ensure_unit_extra_rows(conn)`
    - Tables:
      `unit_extra`
    - Current write path:
      SQLite
    - Runtime flag control:
      No

13. `app.py` → `ensure_extra_fields(conn)`
    - Tables:
      `extra_fields`
    - Current write path:
      SQLite
    - Runtime flag control:
      No

14. `app.py` → `bootstrap()`
    - Calls:
      `init_schema`
      `import_seed_into_conn`
      `seed_admin`
      `seed_settings`
      `seed_from_excel`
      `migrate_schema`
      `normalize_progress_values`
      `ensure_unit_extra_rows`
      `ensure_extra_fields`
      `migrate_unit_layout`
    - Current write path:
      SQLite
    - Runtime flag control:
      No
    - Notes:
      this is setup/maintenance logic, not a production request write path

## Table Coverage Summary

- `users`
  runtime writes in `/admin/users`
  setup writes in `seed_admin`
- `meta`
  runtime writes in `/admin/table` settings save
  setup writes in `set_setting`, `seed_settings`, `seed_from_excel`, `migrate_unit_layout`
- `sheets`
  runtime writes in `/admin/table`
  setup writes in `seed_from_excel`, `migrate_schema`
- `tasks`
  runtime writes in `/admin/table`
  setup writes in `seed_from_excel`, `migrate_schema`
- `floors`
  runtime writes in `/admin/table`
  setup writes in `seed_from_excel`, `migrate_schema`, `migrate_unit_layout`
- `units`
  runtime writes in `/admin/table`
  setup writes in `seed_from_excel`, `migrate_unit_layout`
- `progress`
  runtime writes in `/api/progress`, `/api/reset-sheet`, `/admin/table`
  setup writes in `seed_from_excel`, `normalize_progress_values`, `migrate_unit_layout`
- `unit_extra`
  runtime writes in `/api/unit-extra`, `/api/reset-sheet`, `/admin/table`
  setup writes in `seed_from_excel`, `migrate_schema`, `migrate_unit_layout`, `ensure_unit_extra_rows`
- `extra_fields`
  runtime writes in `/admin/table`
  setup writes in `ensure_extra_fields`
- `unit_extra_values`
  runtime writes in `/api/unit-extra`, `/api/reset-sheet`, `/admin/table`

## Dual Write Risk Points

1. Multi-table request writes must stay atomic across two backends.
   The current SQLite flow relies on one connection context; dual write introduces cross-database partial-failure risk.

2. Bulk destructive operations are high risk.
   `/admin/table` delete flows and `reset_sheet()` perform broad deletes/updates and are the most sensitive to divergence.

3. Generated IDs and foreign-key relationships must remain aligned.
   Sheet/task/floor/unit creation currently depends on SQLite `lastrowid` behavior.

4. Upsert semantics must match exactly.
   `progress`, `unit_extra`, and `unit_extra_values` use SQLite conflict handling that will need PostgreSQL-equivalent behavior.

5. Setup logic should not automatically become dual write.
   `bootstrap()` and maintenance helpers should stay isolated from production runtime dual-write rollout.

6. Session-visible writes must remain immediately readable.
   In mixed-mode operation, write-after-read consistency problems will appear if PostgreSQL lags while reads are already switched.

7. Password and audit fields must not drift.
   `password_hash`, `updated_by`, `updated_at`, and `created_at` need exact parity.

## Recommended Refactor Order

1. Introduce write helper/service boundaries without changing behavior.
   Wrap each runtime write path in explicit helper functions first.

2. Start with the smallest isolated runtime write:
   `/api/progress`
   Single table, deterministic upsert, easiest to compare.

3. Then move to `/api/unit-extra`.
   Slightly more complex because it branches between `unit_extra` and `unit_extra_values`.

4. Then move to `/api/reset-sheet`.
   Bulk write path, but still operationally narrower than admin table editing.

5. Then move to `/admin/users`.
   Limited table scope but must preserve password-hash behavior exactly.

6. Last, refactor `/admin/table`.
   This is the highest-risk write surface because it spans many tables and create/delete cascades.

7. Keep bootstrap and maintenance logic out of the first dual-write rollout.
   Treat `bootstrap()`-related writes as a separate track after runtime writes are proven stable.

## Suggested Next Validation Before Any Write Enablement

- Add per-write-path dry-run logging or mirrored comparison hooks
- Add request-level dual-write diff tooling for affected tables
- Validate ID generation strategy for create flows before enabling any PostgreSQL write path
- Enable `USE_SQLALCHEMY_WRITES` only after each runtime write path has isolated helpers and backend parity checks
