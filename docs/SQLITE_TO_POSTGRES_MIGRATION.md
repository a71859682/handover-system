# SQLite to PostgreSQL Migration

This tooling is for staging use only.

Do not run this against production PostgreSQL.
Back up both the SQLite source and the staging PostgreSQL target before running anything.

## Source and Target

- SQLite source path priority:
  `APP_SQLITE_SOURCE_PATH`
  fallback: `site.db` in the project root
- PostgreSQL target:
  `DATABASE_URL`

The migration script refuses to run unless `DATABASE_URL` points to PostgreSQL.
The scripts redact the database password in console output.

## Safe Usage

1. Back up the staging PostgreSQL database.
2. Confirm `DATABASE_URL` points to staging, not production.
3. Run the migration:

```bash
python tools/migrate_sqlite_to_postgres.py
```

If the target PostgreSQL already contains data, the script stops without modifying it.

To intentionally clear the staging tables and re-import from SQLite, use:

```bash
python tools/migrate_sqlite_to_postgres.py --force
```

`--force` deletes data in reverse foreign-key order before importing.

4. Run the count check:

```bash
python tools/check_sqlite_postgres_counts.py
```

The check script prints `PASS` or `FAIL` for each migrated table and returns a failing exit code when counts do not match.

## Migrated Tables

The import order is:

1. `meta`
2. `users`
3. `sheets`
4. `tasks`
5. `floors`
6. `units`
7. `progress`
8. `unit_extra`
9. `extra_fields`
10. `unit_extra_values`
