# Deployment

## Render Deployment Flow

1. Keep production-ready code on `main`.
2. Use `develop` for v2.2 refactor preparation and ongoing development.
3. Open a pull request from `develop` to `main` after smoke tests pass.
4. Render deploys with:

```text
web: gunicorn app:app
```

5. Render installs dependencies from `requirements.txt`.
6. On startup, `gunicorn app:app` imports `app.py`, which runs `bootstrap()`.

## Branch Usage

- `main`: production branch for stable Render deploys.
- `develop`: integration branch for refactor work before merging to production.

Do not commit experimental changes directly to `main`.

## Environment

- Without `DATABASE_URL`, the app uses SQLite at the project root: `site.db`.
- With `DATABASE_URL`, the app can use the configured PostgreSQL database.
- Keep secrets such as `APP_SECRET_KEY` in Render environment variables.

## Rollback

1. Find the last known good commit on `main`.
2. Revert the bad deployment commit or redeploy the previous commit from Render.
3. If database changes were involved, restore from the most recent backup before redeploying.
4. Confirm `/login` and `/` respond after rollback.
