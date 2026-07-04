# Stage 4 User Site Permissions Write Readiness

## 1. Baseline Source

- Source baseline: `STAGE 4 WRITE ISOLATION BASELINE @ bb3d470`

This document records a docs-only readiness audit target for `user_site_permissions` writes. It does not change runtime behavior.

## 2. Audit Target

This audit is focused on:

- `user_site_permissions` write readiness
- `/admin/users` related site permission flows

The goal is to freeze the current write boundary before any broader Stage 4 runtime work begins.

## 3. Current Runtime Boundary

Current runtime boundary remains:

- SQLite remains the primary write runtime
- `USE_SQLALCHEMY_WRITES=false`
- no schema change
- no migration
- no database foundation change

This audit does not enable dual-write runtime behavior and does not start broad write migration.

## 4. Write Flow Inventory

Current `user_site_permissions`-adjacent write flows include:

- `add_site_permission`
  - creates a site-scoped permission row for a non-admin user through `/admin/users`
- `update_site_permission`
  - updates the site-scoped role on an existing permission row through `/admin/users`
- `delete_site_permission`
  - removes an existing site permission row through `/admin/users`
- user create / update / delete relation to site permissions
  - `create_user` is adjacent because new users may later receive site permission rows
  - `update_user` is adjacent because global user management remains on the same admin surface
  - `delete_user` is adjacent because deleting a user also affects related `user_site_permissions` rows

For this audit, the primary target is the site-permission CRUD subset, not the broader `/admin/users` runtime surface.

## 5. Known Coverage

Current known coverage includes:

- `tools/check_site_permission_readiness.py`
  - validates `user_site_permissions` table presence
  - validates the unique `(user_id, site_id)` constraint
  - exercises `/admin/users` site permission create / update / delete flows
  - checks duplicate prevention
  - checks invalid user rejection
  - checks inactive site rejection
  - checks invalid role rejection
  - checks admin compatibility behavior
  - checks non-admin permission CRUD is blocked
- `tests/smoke_test.py`
  - includes `/admin/users` flow coverage
  - includes site permission add / update / delete coverage through the admin users surface
  - includes surrounding admin users smoke and compatibility checks
- `docs/stage_4_write_isolation_baseline.md`
  - already records that `user_site_permissions` flows still require a focused future review

## 6. Known Gaps

The current gaps are readiness and freeze gaps rather than runtime implementation gaps:

- missing focused Stage 4 readiness freeze for `user_site_permissions`
- `/admin/users` site permission writes are still grouped inside broader admin user management coverage
- current site-permission write boundary is documented only indirectly across tools, smoke, and baseline notes
- the next smallest follow-up is still a single test-only or review-only slice, not a runtime change

Potential future test-only audit candidates include:

- a narrower route-specific smoke check that isolates site-permission create / update / delete expectations from the broader `/admin/users` flow
- a focused audit of user delete interaction with `user_site_permissions` cleanup, if later needed as a separate bounded review

## 7. Next Step Boundary

The next step after this audit is constrained to:

- review of this readiness audit
- or one single test-only readiness check for `user_site_permissions`

Do not:

- change the runtime write path directly
- enable `USE_SQLALCHEMY_WRITES`
- start broad Stage 4 write implementation
- expand into governance redesign
