# Seeding

`site.db` is a local runtime database and should not be committed to Git.

`seeds/default_seed.json` is the version-controlled snapshot used to rebuild the default SQLite database when a fresh `site.db` is needed.

## Export a new seed

Run:

```powershell
python tools/export_seed.py
```

This reads the current `site.db` and writes `seeds/default_seed.json`.

## Rebuild a database from seed

If `site.db` is missing, the app bootstrap flow will:

1. create the schema
2. import `seeds/default_seed.json` if it exists
3. fall back to `source.xlsx` only when the seed file does not exist

To import manually into an empty database:

```powershell
python tools/import_seed.py
```

The import tool refuses to run if the target database already contains data.
