# PostgreSQL Schema Upgrade

## Scope

This procedure is allowed only for `handover-system-dev` or another staging service.

## Before You Run Upgrade

1. Confirm the target service is a staging or dev service
2. Confirm `DATABASE_URL` is set to a PostgreSQL URL
3. Run:

```bash
python tools/postgres_staging_check.py
```

Only continue if the command prints `PASS`.

## Schema Upgrade Command

Run the schema upgrade in the staging or dev environment only:

```bash
python -m flask db upgrade
```

## Post-Upgrade Verification

After the upgrade finishes, run:

```bash
python tools/check_database_url.py
```

## Warnings

- Do not run this on the production `handover-system` service
- Do not run this against the production SQLite database
- Do not change the production service `DATABASE_URL`
