# Stage 6 Admin Current-Site Authorization Audit

## 1. Baseline Source

- Source baseline: `591755d`
  - `Merge vendor work entry stage 5 API baseline`
- Related inventory:
  - `docs/stage_6_admin_current_site_content_actions_inventory.md`

This document is a docs-only authorization and site-isolation audit for admin current-site content actions. It does not change runtime behavior, tests, schema, or business logic.

## 2. Audit Scope

This audit covers:

- `/admin/table` content actions
- current-site session dependency for admin content mutations
- sheet/site target resolution for content actions
- current-site-aware rejection behavior

This audit does not cover:

- `/admin/users`
- vendor-only routes
- schema or migration work
- runtime redesign

## 3. Current Authorization Flow

### Route gate

`/admin/table` is currently protected by:

- `@admin_required`

This means:

- unauthenticated users must not reach the route
- authenticated non-admin users must not perform these content actions
- only admin sessions can enter the content-action flow

### Action-level authorization

Admin role alone is not the final authorization boundary.

After the admin route gate, content actions additionally rely on current-site-aware authorization helpers:

- `resolve_admin_current_site_id(conn)`
- `authorize_admin_site_scoped_write(conn, sheet_id=...)`
- `authorize_admin_create_sheet_site(conn)`

Target-specific resolution helpers are then used before certain delete/mutate actions:

- `resolve_sheet_site_for_admin_write(...)`
- `resolve_task_sheet_for_admin_write(...)`
- `resolve_floor_sheet_for_admin_write(...)`
- `resolve_unit_sheet_for_admin_write(...)`
- `resolve_extra_field_sheet_for_admin_write(...)`

This creates a two-layer boundary:

1. admin-only route access
2. current-site-aware target validation before write

## 4. Authorization Flow Per Content Action

### `create_sheet`

- route access:
  - admin only
- current-site flow:
  - `authorize_admin_create_sheet_site(conn)`
  - internally uses `resolve_admin_current_site_id(conn)`
- expected result:
  - new sheet is created under the admin's current site

### `delete_sheet`

- route access:
  - admin only
- current-site flow:
  - `authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)`
  - validates target sheet site against admin current site
- expected result:
  - same-site delete allowed
  - cross-site delete blocked

### `add_task`

- route access:
  - admin only
- current-site flow:
  - `authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)`
- expected result:
  - same-site add allowed
  - cross-site add blocked

### `delete_task:<id>`

- route access:
  - admin only
- current-site flow:
  - `resolve_task_sheet_for_admin_write(conn, task_id=task_id)`
  - explicit check that resolved task sheet matches selected sheet
  - `authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)`
- expected result:
  - only same-site/same-sheet delete allowed

### `add_extra_field`

- route access:
  - admin only
- current-site flow:
  - `authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)`

### `delete_extra_field:<id>`

- route access:
  - admin only
- current-site flow:
  - `resolve_extra_field_sheet_for_admin_write(...)`
  - selected-sheet consistency check
  - `authorize_admin_site_scoped_write(...)`

### `add_floor`

- route access:
  - admin only
- current-site flow:
  - `authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)`

### `delete_floor:<id>`

- route access:
  - admin only
- current-site flow:
  - `resolve_floor_sheet_for_admin_write(...)`
  - selected-sheet consistency check
  - `authorize_admin_site_scoped_write(...)`

### `add_unit:<floor_id>`

- route access:
  - admin only
- current-site flow:
  - `resolve_floor_sheet_for_admin_write(...)`
  - selected-sheet consistency check
  - `authorize_admin_site_scoped_write(...)`

### `delete_unit:<id>`

- route access:
  - admin only
- current-site flow:
  - `resolve_unit_sheet_for_admin_write(...)`
  - selected-sheet consistency check
  - `authorize_admin_site_scoped_write(...)`

### default `save`

- route access:
  - admin only
- current-site flow:
  - `authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)`
  - then:
    - `save_admin_global_settings(...)`
    - `save_admin_site_content(...)`

This means even the broad save path is intended to remain behind the same current-site-aware gate.

## 5. Current-Site Validation Flow

The current-site validation chain is currently:

1. resolve current admin user
2. read `current_site_id` from session
3. verify site exists and remains active
4. resolve target object back to its owning sheet/site when needed
5. compare target site to current admin site
6. reject cross-site write with `write_target_not_in_current_site`

Key helper behavior:

- `resolve_admin_current_site_id(conn)`
  - requires authenticated admin session
  - requires `current_site_id`
  - requires target site row to exist and be active

- `authorize_admin_site_scoped_write(conn, sheet_id=...)`
  - resolves target sheet site
  - compares target site to current admin site
  - raises `write_target_not_in_current_site` on mismatch

- target-specific resolvers
  - ensure task/floor/unit/extra-field operations cannot bypass sheet/site lineage checks

## 6. Site Isolation Status

Current site isolation appears strong for the already reviewed admin content actions:

- write target is not trusted from form intent alone
- target entities are re-resolved from storage before destructive actions
- cross-site content writes are blocked
- missing current-site state blocks or redirects the action flow
- helper structure is consistent across multiple content object types

Current isolation model is:

- admin may be globally privileged
- but content mutation is still constrained by current selected site
- current-site context acts as a required operational boundary, not just a UI hint

## 7. Existing Protections

Current protections already evidenced by code and smoke include:

- admin-only route guard
- missing current site redirects to `/site-selector`
- cross-site sheet delete blocked
- cross-site task add/delete blocked
- same-site sheet and task actions succeed
- target-specific resolution before delete/mutate actions
- broad save path remains behind `authorize_admin_site_scoped_write(...)`

## 8. Known Gaps

This section is audit-only and does not propose runtime change.

Current known authorization/isolation gaps are mostly coverage-depth gaps:

- extra-field actions do not yet appear to have the same clearly isolated smoke coverage level as sheet/task actions
- floor/unit actions appear to have dedicated smoke scaffolding, but this Stage 6 family has not yet frozen their contract at the same explicit level
- the combined default `save` path is guarded, but deserves a narrower review because it touches both settings and site content in one flow
- relationship between `/admin/table` content actions and `/api/reset-sheet` has not yet been unified under one Stage 6 freeze decision

These are review gaps, not confirmed authorization bugs.

## 9. Future Tests-Only Guardrail Candidates

If a later Stage 6 review confirms a real need, the safest tests-only candidates are:

1. extra-field current-site guardrail
   - add/delete extra-field same-site vs cross-site behavior

2. floor current-site guardrail
   - add/delete floor same-site vs cross-site behavior

3. unit current-site guardrail
   - add/delete unit same-site vs cross-site behavior

4. default save-path current-site guardrail
   - verify the broad save action is blocked when current site is missing or cross-site mismatch exists

These are candidates only. This document does not authorize implementation.

## 10. Future Implementation Work Out Of Scope Here

The following belong to future implementation and must not be done in this audit slice:

- changing `app.py`
- changing helper semantics
- redesigning admin/site permission model
- changing templates
- changing schema or migration
- broad admin UX refactor

## 11. Next-Step Boundary

The next safe move after this audit should be one of:

- a Stage 6 planning review
- or one single docs-only follow-up review choosing the smallest current-site content-action guardrail family

Do not:

- start runtime implementation from this document
- mix in schema or migration work
- broaden into unrelated modules
