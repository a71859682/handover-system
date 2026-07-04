# Stage 4 Write Isolation Baseline

## 1. Baseline Source

- Source baseline: `STAGE 3B FREEZE BASELINE @ 66c2f97`

This document records the Stage 4 write isolation baseline as a documentation-only planning artifact. It does not change runtime behavior.

## 2. Stage 4 Goal

Stage 4 is intended to:

- systematically freeze site-scoped and sheet-scoped write isolation behavior
- keep SQLite as the current primary write runtime boundary
- define the next safe write-isolation review path before any broader runtime write migration

Stage 4 does not begin write runtime migration in this document.

## 3. Stage 4 Out Of Scope

Stage 4 does not include:

- governance redesign
- PostgreSQL primary write
- `USE_SQLALCHEMY_WRITES=true`
- dual-write strict rollout
- schema change
- migration
- backfill
- new feature development

## 4. Write Path Inventory

Current write surfaces include:

- `/admin/table`
- `/api/progress`
- `/api/unit-extra`
- `/api/reset-sheet`
- `/admin/users`
- `/api/vendor-contact`
- `/api/vendor-work-entry`
- `user_site_permissions` related flows under `/admin/users`

## 5. Current Runtime Boundary

Current runtime boundary remains:

- SQLite remains the primary write runtime
- `USE_SQLALCHEMY_WRITES=false`
- dual-write remains controlled and scoped
- no broad PostgreSQL-primary write migration is active

## 6. Known Coverage Summary

Current known Stage 4-adjacent coverage includes:

- admin table readiness inventory and current-site enforcement review
- `progress` write isolation smoke
- `unit-extra` write isolation smoke
- `reset-sheet` write isolation smoke
- vendor write isolation smoke for:
  - `/api/vendor-contact`
  - `/api/vendor-work-entry`
- `users create` controlled dual-write status tracking
- `user_site_permissions` and related site-permission write flows still require a future focused review

## 7. Next Step Boundary

The next step after this baseline is constrained to:

- Stage 4 baseline review
- or a single write-path contract/readiness audit

Do not:

- start broad write runtime implementation directly from this baseline
- enable `USE_SQLALCHEMY_WRITES`
- expand into governance redesign

