# PostgreSQL Staging Verification

## Current Status

- The staging or dev Render Web Service has `DATABASE_URL` configured
- The production service does not set `DATABASE_URL`
- Production currently remains on SQLite

## Scope Of This Stage

- Validate PostgreSQL connectivity only
- Validate `SELECT 1`
- Do not run `flask db upgrade`
- Do not perform data migration
- Do not switch the production data flow

## Safety Notes

- Do not print the full `DATABASE_URL`
- `tools/check_database_url.py` masks the password when it prints the URL
- `tools/postgres_staging_check.py` does not print the URL

## How To Run In Render Staging

Open the staging service shell in Render and run:

```bash
python tools/postgres_staging_check.py
python tools/check_database_url.py
```

## Expected Result

- `python tools/postgres_staging_check.py` should print `PASS`
- `python tools/check_database_url.py` should print the masked URL and `PASS`

## If Validation Fails

- Confirm the service has `DATABASE_URL` set
- Confirm the URL is the Render Internal Database URL
- Confirm the staging service can reach the PostgreSQL instance
- Do not run schema migration during this stage
