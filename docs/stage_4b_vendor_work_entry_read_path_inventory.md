# Stage 4B Vendor Work Entry Read Path Inventory

## 1. Baseline Source

- Source baseline: `USER SITE PERMISSIONS FREEZE BASELINE @ 73c2e4d`
- Working branch intent: `stage-4b-vendor-work-entry-read-planning`

This document is a docs-only inventory for Vendor Work Entry read paths. It does not change runtime behavior, tests, schema, or business logic.

## 2. Inventory Scope

This inventory is limited to the current Vendor Work Entry read-side surfaces and adjacent vendor identity read surfaces:

- `/vendor/business-read-preview`
- `/api/vendor/work-entry/preflight`
- `/vendor/profile`
- `/vendor/scope`
- `/vendor/home`

The inventory does not include:

- `/api/vendor-work-entry` write runtime behavior
- schema or migration work
- broad internal sheet/grid read surfaces unrelated to Vendor Work Entry

## 3. Current Read Path List

### `GET /vendor/business-read-preview`

- Primary purpose:
  - vendor-facing read preview of the authenticated vendor's business entries
- Primary user:
  - authenticated vendor session only
- Current auth boundary:
  - guarded by `@vendor_login_required`
  - business identity resolved by `authorize_vendor_business_read()`
  - internal session is redirected to `/vendor/login`
  - unauthenticated session is redirected to `/vendor/login`
- Current data boundary:
  - query uses authenticated `vendor_name`
  - rows are filtered by `WHERE vendor_name = ?`
  - no internal site/session scope is injected into vendor session
- Current response contract:
  - top-level keys:
    - `ok`
    - `vendor_account_id`
    - `vendor_username`
    - `vendor_name`
    - `entry_count`
    - `business_dates`
    - `entries`
  - `entries[]` keys:
    - `vendor_name`
    - `business_date`
    - `planned_at`
    - `planned_headcount`
    - `actual_headcount`
    - `work_content`
    - `work_headcount`
    - `entry_order`
  - ordering:
    - `business_date DESC`
    - then `entry_order ASC`
    - then `rowid ASC` as stable tiebreaker in SQL
  - empty-result behavior:
    - `ok=true`
    - `entry_count=0`
    - `business_dates=[]`
    - `entries=[]`
- Current known smoke coverage:
  - unauthenticated redirect to `/vendor/login`
  - internal session blocked from vendor-only preview
  - happy-path top-level shape
  - item-level shape
  - stable ordering
  - empty-result payload
  - exclusion of forbidden internal/system fields

### `POST /api/vendor/work-entry/preflight`

- Primary purpose:
  - read-only trusted preflight context for vendor write preparation
- Primary user:
  - authenticated vendor session only
- Current auth boundary:
  - requires vendor identity
  - unauthenticated request returns `403`
  - internal session returns `403`
- Current data boundary:
  - trusted vendor identity is sourced from session, not payload
  - validates target `sheet_id`, `business_date`, optional `id`, and vendor ownership constraints before write
  - does not create internal `current_site_id` session state
- Current response contract:
  - success payload has `ok=true`
  - success `preflight` keys:
    - `vendor_account_id`
    - `vendor_username`
    - `vendor_name`
    - `sheet_id`
    - `business_date`
    - `entry_id`
    - `write_mode`
  - covered deterministic error codes in smoke:
    - `vendor_auth_required`
    - `vendor_name_mismatch`
    - `vendor_cross_vendor_write_forbidden`
    - `vendor_business_date_mismatch`
- Current known smoke coverage:
  - unauthenticated `vendor_auth_required`
  - internal session `vendor_auth_required`
  - happy-path preflight top-level and nested shape
  - vendor identity mismatch reject
  - cross-vendor preflight reject
  - update-mode trusted context
  - business-date mismatch reject

### `GET /vendor/profile`

- Primary purpose:
  - vendor identity readback for authenticated vendor session
- Primary user:
  - authenticated vendor session only
- Current auth boundary:
  - guarded by `@vendor_login_required`
  - unauthenticated/internal sessions redirect to `/vendor/login`
- Current response contract:
  - `ok=true`
  - includes `vendor_account_id`, `vendor_username`, `vendor_name`
  - excludes `password_hash`
- Current known smoke coverage:
  - unauthenticated redirect
  - internal session blocked
  - happy-path authenticated payload

### `GET /vendor/scope`

- Primary purpose:
  - vendor identity scope readback
- Primary user:
  - authenticated vendor session only
- Current auth boundary:
  - guarded by `@vendor_login_required`
  - unauthenticated/internal sessions redirect to `/vendor/login`
- Current response contract:
  - `ok=true`
  - `scope` keys include:
    - `identity_type`
    - `vendor_account_id`
    - `vendor_username`
    - `vendor_name`
    - `scope_type`
    - `scope_version`
  - excludes internal site/sheet scope fields
- Current known smoke coverage:
  - unauthenticated redirect
  - internal session blocked
  - happy-path authenticated payload
  - forbidden internal scope keys absent

### `GET /vendor/home`

- Primary purpose:
  - vendor-only landing page for authenticated vendor session
- Primary user:
  - authenticated vendor session only
- Current auth boundary:
  - guarded by `@vendor_login_required`
  - unauthenticated/internal sessions redirect to `/vendor/login`
- Current response contract:
  - HTML page contract only
  - smoke confirms representative identity fragments are rendered
- Current known smoke coverage:
  - authenticated page `200`
  - representative vendor identity fragments present

## 4. Existing Authorization And Isolation Protections

Current Vendor Work Entry read-side protections already visible in code and smoke include:

- vendor session isolation via `vendor_login_required`
- hard separation between vendor session and internal session
- vendor session does not carry internal `user_id`, `role`, `current_site_id`, or `current_site_name`
- vendor read preview is constrained to authenticated `vendor_name`
- preflight uses trusted vendor identity rather than caller-supplied identity
- cross-vendor preflight access is rejected
- business-date mismatch for update preflight is rejected deterministically
- internal protected routes such as `/sheet` remain blocked from vendor session

## 5. Existing Response Contract Baseline

Current response-contract baseline already frozen or evidenced by smoke/docs:

- `docs/stage_3b_cross_domain_deterministic_contracts_freeze.md`
  - `/vendor/business-read-preview` top-level shape
  - `entries[]` shape
  - empty-result payload
  - stable ordering
  - forbidden-field exclusion
- `tests/smoke_test.py`
  - vendor preflight nested contract shape
  - vendor identity/session boundary
  - deterministic auth and selected preflight error contracts

At current baseline, the strongest contract freeze already exists on:

- vendor business read preview success-side payload
- vendor preflight trusted-context payload
- vendor session/auth boundary

## 6. Known Gaps And Risks

This section is inventory only. It does not recommend implementation in this slice.

Current known read-path gaps or review risks include:

- no dedicated Stage 4B freeze baseline yet for Vendor Work Entry read surfaces
- no single consolidated document had previously mapped write-side and read-side vendor surfaces together
- `/vendor/business-read-preview` currently filters by `vendor_name` identity and not by an explicit site-bound vendor read scope object
- preflight is a POST-based read-like surface, so its contract belongs partly to read preparation and partly to write readiness
- route inventory is strong on vendor-only surfaces, but there is not yet a dedicated Stage 4B follow-up review deciding whether any additional test-only guardrail is still justified

These are planning and freeze gaps, not evidence of a current runtime defect.

## 7. Suggested Future Minimal Implementation Slices

The next slices should stay read-path-specific and remain independent from runtime migration.

Potential minimal slices:

1. `STAGE4B-AUDIT-002 — Vendor Work Entry Read Contract Gap Review`
   - docs-only review of remaining read-path test-only gaps
   - purpose:
     - decide whether `/vendor/business-read-preview` or preflight still lacks any deterministic contract guardrail

2. `STAGE4B-AUDIT-003 — Vendor Work Entry Read Smoke Guardrail Planning`
   - docs-only freeze of candidate read-side smoke additions
   - purpose:
     - separate route-level, authorization, response-shape, and identity-boundary guardrails before any new test work

3. `STAGE4B-AUDIT-004 — Vendor Business Read Preview Focused Test-Only Slice`
   - test-only, only if a real gap is confirmed later
   - purpose:
     - add exactly one missing deterministic read-contract guardrail without touching write runtime

4. `STAGE4B-AUDIT-005 — Vendor Work Entry Preflight Read-Contract Focused Test-Only Slice`
   - test-only, only if a real gap is confirmed later
   - purpose:
     - treat preflight as a read-preparation contract and freeze one missing deterministic contract at a time

## 8. Boundary For The Next Step

The next safe move after this inventory should remain one of:

- read-path gap review
- read-path smoke planning
- one single test-only read-contract guardrail, but only after a dedicated gap review

Do not:

- expand into broad vendor write runtime changes
- mix Stage 4B read work with schema or migration work
- broaden into unrelated `/admin/table` or other write-path migration work
