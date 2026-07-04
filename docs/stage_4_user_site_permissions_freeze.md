# Stage 4 User Site Permissions Freeze

## 1. Stable Baseline

- Stable baseline: `USER SITE PERMISSIONS SMOKE GUARDRAIL BASELINE @ affdfe5`
- Freeze status: `User Site Permissions = Stage 4 Freeze Candidate`

This document records the freeze baseline for the `user_site_permissions` write path. This freeze record is documentation only and does not change runtime behavior.

## 2. Freeze Scope

This freeze is limited to `user_site_permissions` writes under `/admin/users`:

- `add_site_permission`
- `update_site_permission`
- `delete_site_permission`

This freeze does not expand to the broader `/admin/users` management surface.

## 3. Covered Contract Summary

Current covered contract scope includes:

- `add_site_permission` successful persistence
- duplicate prevention
- `update_site_permission` role update
- `delete_site_permission` row removal
- inactive site reject
- invalid role reject
- non-admin blocked
- permission persistence
- route/auth boundary summary for the covered write path

## 4. Coverage Sources

Current freeze evidence is derived from:

- `docs/stage_4_user_site_permissions_write_readiness.md`
- `tests/smoke_test.py`
- `tools/check_site_permission_readiness.py`

Together these sources cover:

- docs-only readiness framing
- route-specific smoke guardrail coverage
- readiness tool verification of the same write path and related structural assumptions

## 5. Runtime Boundary

Current runtime boundary remains:

- SQLite remains the primary write runtime
- `USE_SQLALCHEMY_WRITES=false`
- no schema change
- no migration
- no database foundation change
- no runtime implementation started for Stage 4 write migration

This freeze does not enable any new write backend behavior.

## 6. Explicit Out Of Scope

This freeze does not include:

- broader `/admin/users` flow
- `delete_user` cleanup freeze
- other write paths
- Stage 4 runtime implementation

This freeze also does not introduce:

- new runtime capability
- new write-path behavior
- new auth scope

## 7. Next Step Boundary

The next step after this freeze is constrained to:

- freeze review
- freeze baseline validation
- or switching to another single write-path audit

Do not:

- start runtime write migration directly from this freeze
- enable `USE_SQLALCHEMY_WRITES`
- expand into broader Stage 4 implementation from this document alone
