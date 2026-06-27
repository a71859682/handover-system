# CI

## What CI Checks

The GitHub Actions workflow runs the following checks on every push and pull request:

- `python tools/check_progress_orm.py`
- `python tools/check_sheets_orm.py`
- `python tools/check_users_orm.py`
- `python tools/check_settings_orm.py`
- `python tools/check_model_schema.py`
- `python tests/smoke_test.py`

## Branch Flow

- `main`: production-ready branch
- `develop`: integration branch for staged work
- `feature/*` or task branches: isolated implementation branches for focused changes

Recommended flow:

1. Start work in a feature branch
2. Open a pull request into `develop` or `main` depending on the release plan
3. Wait for CI to pass
4. Merge only after checks are green

## Merge Rule

CI should pass before merging into shared branches.
