# Stage 4B Vendor Work Entry Read Response Contract Inventory

## 1. Baseline Source

- Source baseline: `USER SITE PERMISSIONS FREEZE BASELINE @ 73c2e4d`
- Related Stage 4B docs:
  - `docs/stage_4b_vendor_work_entry_read_path_inventory.md`
  - `docs/stage_4b_vendor_work_entry_read_authorization_audit.md`

This document is a docs-only response-contract inventory for Vendor Work Entry read paths. It does not change runtime behavior, tests, schema, or business logic.

## 2. Inventory Scope

This response-contract inventory covers:

- `GET /vendor/home`
- `GET /vendor/profile`
- `GET /vendor/scope`
- `GET /vendor/business-read-preview`
- `POST /api/vendor/work-entry/preflight`

It does not cover:

- `/api/vendor-work-entry` write response contract
- non-vendor internal read APIs
- schema, migration, or runtime implementation work

## 3. Success Response Contract Inventory

### `GET /vendor/home`

- success status:
  - `200`
- response type:
  - HTML page
- currently evidenced contract:
  - authenticated vendor page renders vendor identity fragments
  - not a JSON API contract
- currently frozen level:
  - minimal HTML presence only

### `GET /vendor/profile`

- success status:
  - `200`
- response type:
  - JSON
- success shape:
  - top-level keys currently evidenced:
    - `ok`
    - `vendor_account_id`
    - `vendor_username`
    - `vendor_name`
- currently evidenced value constraints:
  - `ok == true`
  - `vendor_account_id` exists
  - `vendor_username` matches authenticated vendor
  - `vendor_name` matches authenticated vendor
- currently evidenced exclusions:
  - no `password_hash`

### `GET /vendor/scope`

- success status:
  - `200`
- response type:
  - JSON
- success shape:
  - top-level keys:
    - `ok`
    - `scope`
  - `scope` keys currently evidenced:
    - `identity_type`
    - `vendor_account_id`
    - `vendor_username`
    - `vendor_name`
    - `scope_type`
    - `scope_version`
- currently evidenced value constraints:
  - `ok == true`
  - `scope.identity_type == "vendor"`
  - `scope.scope_type == "vendor_identity_only"`
  - `scope.scope_version == 1`
- currently evidenced exclusions:
  - no `password_hash`
  - no `site_id`
  - no `sheet_id`
  - no `allowed_site_ids`
  - no `allowed_sheet_ids`

### `GET /vendor/business-read-preview`

- success status:
  - `200`
- response type:
  - JSON
- success top-level keys:
  - `ok`
  - `vendor_account_id`
  - `vendor_username`
  - `vendor_name`
  - `entry_count`
  - `business_dates`
  - `entries`
- `entries[]` item keys:
  - `vendor_name`
  - `business_date`
  - `planned_at`
  - `planned_headcount`
  - `actual_headcount`
  - `work_content`
  - `work_headcount`
  - `entry_order`
- currently evidenced value constraints:
  - `ok == true`
  - top-level vendor identity matches authenticated vendor
  - `entries` is a list
  - all entries belong to current vendor
  - numeric fields are serialized as integers
  - empty `planned_at` is serialized as `""`
  - `entry_count` matches result count
  - `business_dates` is de-duplicated and stable-sorted
- ordering contract currently evidenced:
  - `business_date DESC`
  - then `entry_order ASC`
- empty-result success shape currently evidenced:
  - same top-level keys as happy path
  - `ok == true`
  - `entry_count == 0`
  - `business_dates == []`
  - `entries == []`
- currently evidenced exclusions:
  - no `password_hash`
  - no `site_id`
  - no `sheet_id`
  - no `allowed_site_ids`
  - no `allowed_sheet_ids`

### `POST /api/vendor/work-entry/preflight`

- success status:
  - `200`
- response type:
  - JSON
- success top-level keys:
  - `ok`
  - `preflight`
- `preflight` keys:
  - `vendor_account_id`
  - `vendor_username`
  - `vendor_name`
  - `sheet_id`
  - `business_date`
  - `entry_id`
  - `write_mode`
- currently evidenced value constraints:
  - `ok == true`
  - preflight vendor identity matches authenticated vendor
  - preflight `sheet_id` and `business_date` reflect trusted write context
  - create mode returns:
    - `entry_id == null`
    - `write_mode == "create"`
  - update mode returns:
    - trusted existing `entry_id`
    - `write_mode == "update"`
- currently evidenced session boundary:
  - success preflight must not create internal `current_site_id` / `current_site_name` session state

## 4. Error Response Contract Inventory

### Redirect-based vendor-only read routes

These are not JSON error APIs. Their current error/deny contract is redirect-based:

- `GET /vendor/home`
- `GET /vendor/profile`
- `GET /vendor/scope`
- `GET /vendor/business-read-preview`

Current deny behavior:

- unauthenticated request:
  - `302` redirect to `/vendor/login`
- internal session request:
  - `302` redirect to `/vendor/login`

This redirect contract is already evidenced in smoke, but it is page-boundary behavior rather than JSON error payload behavior.

### `POST /api/vendor/work-entry/preflight`

This route currently uses deterministic JSON error payloads shaped as:

- `status_code`
- payload:
  - `ok == false`
  - `error.code`
  - `error.message`

Currently evidenced deterministic preflight error contracts:

- unauthenticated / internal non-vendor access
  - status:
    - `403`
  - code:
    - `vendor_auth_required`
  - message:
    - `vendor authentication is required.`

- vendor identity mismatch
  - status:
    - `403`
  - code:
    - `vendor_name_mismatch`
  - message:
    - `payload vendor_name does not match authenticated vendor identity.`

- cross-vendor update attempt
  - status:
    - `403`
  - code:
    - `vendor_cross_vendor_write_forbidden`
  - message:
    - `authenticated vendor cannot write another vendor's entry.`

- update business-date mismatch
  - status:
    - `409`
  - code:
    - `vendor_business_date_mismatch`
  - message:
    - `payload business_date must match the existing vendor work entry business_date.`

## 5. Deterministic Error Contracts Already Frozen Or Strongly Evidenced

The currently strongest deterministic error contracts on Vendor Work Entry read paths are:

- `/api/vendor/work-entry/preflight`
  - `vendor_auth_required`
  - `vendor_name_mismatch`
  - `vendor_cross_vendor_write_forbidden`
  - `vendor_business_date_mismatch`

The currently strongest deterministic page-boundary deny contracts are:

- `/vendor/home` unauthenticated redirect
- `/vendor/profile` unauthenticated redirect
- `/vendor/scope` unauthenticated redirect
- `/vendor/business-read-preview` unauthenticated redirect
- internal session redirect away from all vendor-only read pages

## 6. Response Contracts Not Yet Explicitly Frozen

The following response-contract areas are evidenced by smoke but not yet separately frozen by a dedicated Stage 4B document family:

- `/vendor/profile` full top-level key freeze
- `/vendor/scope` exact top-level key freeze
- `/vendor/home` HTML response contract beyond representative identity fragments
- redirect contract freeze for vendor-only read pages as a dedicated Stage 4B read-side boundary note
- explicit Stage 4B decision on whether preflight error coverage is already sufficient or still needs one isolated route-specific guardrail extraction

These are contract-freeze gaps, not proven runtime bugs.

## 7. Candidate Future Tests-Only Response Guardrails

If a later Stage 4B gap review confirms a real need, the safest future tests-only candidates are:

1. `/vendor/profile` exact top-level response shape guardrail
   - protect stable vendor profile JSON contract

2. `/vendor/scope` exact top-level and `scope`-object shape guardrail
   - protect vendor identity-only scope contract

3. `/vendor/business-read-preview` redirect-boundary guardrail extraction
   - isolate unauthenticated/internal redirect behavior into a dedicated read-side contract note/test if needed

4. `/api/vendor/work-entry/preflight` one-single-error isolated guardrail
   - only if later review shows one deterministic preflight error still needs a more explicit route-specific lock

5. `/vendor/home` minimal page-boundary guardrail refinement
   - only if a future review decides representative fragment checks are too loose

These are candidate slices only. This document does not authorize implementation.

## 8. Items That Should Wait For Later Implementation

The following should remain deferred beyond this slice:

- any runtime change in `app.py`
- any route behavior change
- any vendor session model redesign
- any schema or migration work
- any broad unification of read and write vendor contracts
- any expansion into non-vendor internal read/write surfaces

## 9. Next-Step Boundary

The next safe move after this inventory should remain one of:

- docs-only Stage 4B gap review
- docs-only Stage 4B smoke guardrail planning for read paths
- one single test-only response-contract guardrail, but only after a narrow gap is explicitly chosen

Do not:

- start runtime implementation from this document
- mix this inventory with write-path migration work
- expand into unrelated route families
