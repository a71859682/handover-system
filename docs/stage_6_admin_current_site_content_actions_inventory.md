# Stage 6 Admin Current-Site Content Actions Inventory

## 1. Baseline Source

- Source baseline: `591755d`
  - `Merge vendor work entry stage 5 API baseline`

This document is a docs-only inventory for Admin current-site aware content actions. It does not change runtime behavior, tests, schema, or business logic.

## 2. Inventory Scope

This inventory is focused on admin-managed content actions that operate on site-bound or sheet-bound data, especially under `/admin/table`.

Included scope:

- `/admin/table` content actions
- admin current-site session dependency
- sheet/site-scoped content mutation helpers
- relevant smoke coverage

Excluded scope:

- `/admin/users` and user/site-permission management
- vendor-specific runtime paths
- schema or migration work
- route redesign

## 3. Current Admin Content Actions

### `/admin/table` content actions

Current content actions under `/admin/table` include:

- `create_sheet`
- `delete_sheet`
- `add_task`
- `delete_task:<id>`
- `add_extra_field`
- `delete_extra_field:<id>`
- `add_floor`
- `delete_floor:<id>`
- `add_unit:<floor_id>`
- `delete_unit:<id>`
- default `save`
  - persists admin global settings
  - persists admin site content for the selected sheet

These actions affect content tables such as:

- `sheets`
- `tasks`
- `progress`
- `extra_fields`
- `floors`
- `units`
- `unit_extra`
- `unit_extra_values`

### Related admin content mutation surface

- `/api/reset-sheet`
  - admin-only reset behavior
  - content-adjacent, but not part of `/admin/table`
- `/api/progress`
- `/api/unit-extra`
- `/api/vendor-contact`
- `/api/vendor-work-entry`

These are already part of Stage 4 write isolation work, but this Stage 6 inventory is centered on admin current-site-aware content actions rather than the API-family work already frozen elsewhere.

## 4. Which Actions Already Have Current-Site Awareness

Current code shows explicit current-site awareness for the following admin content actions:

- `create_sheet`
  - uses `authorize_admin_create_sheet_site(conn)`
  - sheet is created under the admin's current site

- `delete_sheet`
  - uses `authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)`
  - prevents deleting sheets outside the admin's current site

- `add_task`
  - uses `authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)`

- `delete_task:<id>`
  - resolves task sheet
  - verifies task belongs to selected sheet
  - verifies selected sheet belongs to current site

- `add_extra_field`
  - uses `authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)`

- `delete_extra_field:<id>`
  - resolves field sheet
  - checks selected/current-site alignment

- `add_floor`
  - uses `authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)`

- `delete_floor:<id>`
  - resolves floor sheet
  - checks selected/current-site alignment

- `add_unit:<floor_id>`
  - resolves floor sheet
  - checks selected/current-site alignment

- `delete_unit:<id>`
  - resolves unit sheet
  - checks selected/current-site alignment

- default `save`
  - uses `authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)` before persistence

## 5. Which Actions Still Need Review Or Are Less Explicit

Current inventory suggests the following should still be treated as review targets rather than declared fully frozen by this document:

- whether all `/admin/table` content actions have route-specific smoke coverage at the same depth
- whether `save_admin_global_settings(...)` and `save_admin_site_content(...)` are always kept under the same current-site-aware guardrail in every future refactor
- whether `/api/reset-sheet` should eventually be reviewed alongside `/admin/table` as part of the broader admin current-site content-action family

These are review gaps, not confirmed defects.

## 6. Authorization And Site Isolation Status

Current authorization boundary for `/admin/table` content actions:

- route is guarded by `@admin_required`
- content writes additionally depend on current-site session state through:
  - `resolve_admin_current_site_id(conn)`
  - `authorize_admin_site_scoped_write(conn, sheet_id=...)`
  - `authorize_admin_create_sheet_site(conn)`

Current site isolation pattern:

- selected write target is resolved back to its sheet/site
- current admin site is resolved from session
- cross-site writes are rejected with `write_target_not_in_current_site`
- missing current-site session redirects admin to `/site-selector`

Current helper coverage shows target-specific resolution helpers for:

- tasks
- floors
- units
- extra_fields
- sheets

This is a strong sign that current-site awareness has been threaded into the admin content-action path rather than only added at the route edge.

## 7. Existing Smoke Coverage

Current known smoke coverage already includes:

- admin current-site sheet write smoke
  - create-sheet uses current site
  - missing current site blocks create
  - current-site delete works for same-site sheet
  - cross-site delete is blocked
  - missing current site blocks delete

- admin current-site task write smoke
  - same-site add task succeeds
  - cross-site add task is blocked
  - same-site delete task succeeds
  - cross-site delete task is blocked
  - missing current site blocks task actions

Current Stage 4 baseline documents also indicate adjacent write-isolation coverage for:

- `/api/progress`
- `/api/unit-extra`
- `/api/reset-sheet`

But this inventory does not claim full Stage 6 freeze for those paths yet.

## 8. Current Assessment

What is already strong:

- admin content actions are not relying on admin role alone
- current-site session is explicitly required for site-scoped content mutation
- cross-site write prevention exists in both helper structure and smoke coverage
- task and sheet actions already have concrete current-site-aware smoke evidence

What remains planning-only:

- a consolidated Stage 6 roadmap for the broader admin content-action family
- a decision on whether the next safest slice should stay inside `/admin/table` or move to another adjacent admin content surface

## 9. Suggested Future Minimal Implementation Slices

This section is inventory only. It does not authorize implementation.

Suggested next minimal slices:

1. `STAGE6-AUDIT-002 — Admin Current-Site Extra Field Actions Review`
   - review whether add/delete extra-field flows need isolated smoke guardrails

2. `STAGE6-AUDIT-003 — Admin Current-Site Floor And Unit Actions Review`
   - review whether floor/unit actions need isolated current-site smoke guardrails

3. `STAGE6-AUDIT-004 — Admin Current-Site Save Action Contract Review`
   - review the combined save path that calls `save_admin_global_settings(...)` and `save_admin_site_content(...)`

4. `STAGE6-AUDIT-005 — Admin Current-Site Action Roadmap`
   - docs-only roadmap that chooses the smallest bounded tests-only slice

## 10. Classification Summary

### Already current-site aware

- create/delete sheet
- add/delete task
- add/delete extra field
- add/delete floor
- add/delete unit
- default save path under `/admin/table`

### Needs narrower Stage 6 review

- extra-field actions
- floor/unit actions
- combined save path
- relationship to `/api/reset-sheet`

### Not part of this slice

- runtime implementation
- template redesign
- schema or migration work
- unrelated admin/user management flows

## 11. Next-Step Boundary

The next safe move after this inventory should be one of:

- a Stage 6 planning review
- or one single docs-only follow-up review choosing the smallest admin current-site content-action slice

Do not:

- start runtime implementation from this inventory
- mix in schema or migration work
- expand into unrelated modules under the label of Stage 6
