# Stage 4B Vendor Work Entry Read Authorization Audit

## 1. Baseline Source

- Source baseline: `USER SITE PERMISSIONS FREEZE BASELINE @ 73c2e4d`
- Inventory prerequisite:
  - `docs/stage_4b_vendor_work_entry_read_path_inventory.md`

This document is a docs-only authorization and isolation audit for Vendor Work Entry read paths. It does not change runtime behavior, tests, schema, or route logic.

## 2. Audit Scope

This audit covers current authorization and isolation behavior for:

- `GET /vendor/home`
- `GET /vendor/profile`
- `GET /vendor/scope`
- `GET /vendor/business-read-preview`
- `POST /api/vendor/work-entry/preflight`

This audit does not cover:

- `/api/vendor-work-entry` write runtime
- internal `/sheet` or grid read runtime except where vendor-session blocking is relevant
- schema or migration work
- new role design or governance redesign

## 3. Current Authorization Flow

### Vendor-only session gate

Current vendor read paths rely on a shared vendor-only session boundary:

- `vendor_login_required`
  - allows request only when `current_vendor_account()` resolves successfully
  - otherwise clears vendor session and redirects to `/vendor/login`

This gate is applied directly to:

- `/vendor/home`
- `/vendor/profile`
- `/vendor/scope`
- `/vendor/business-read-preview`

### Vendor business identity resolution

Current vendor business identity is resolved through:

- `require_current_vendor_business_identity()`
  - trusted source:
    - `vendor_account_id`
    - `vendor_username`
    - `vendor_name`
- `authorize_vendor_business_read()`
  - currently returns `require_current_vendor_business_identity()` directly

This means current read authorization is vendor-identity-scoped rather than internal site/session-scoped.

### Preflight authorization path

`POST /api/vendor/work-entry/preflight` follows a slightly different flow:

- requires vendor authentication
- builds trusted write-preflight context from authenticated vendor identity
- rejects caller-supplied identity mismatch
- rejects cross-vendor update access
- rejects business-date mismatch for update mode

Although preflight is POST-based, its current role in this audit is still read-adjacent because it returns trusted context before write.

## 4. Role And Access Matrix

### Vendor Work Entry Read Path Access Matrix

| Role / Session Type | `/vendor/home` | `/vendor/profile` | `/vendor/scope` | `/vendor/business-read-preview` | `/api/vendor/work-entry/preflight` |
| --- | --- | --- | --- | --- | --- |
| Unauthenticated | Redirect `/vendor/login` | Redirect `/vendor/login` | Redirect `/vendor/login` | Redirect `/vendor/login` | `403 vendor_auth_required` |
| Internal site member session | Redirect `/vendor/login` | Redirect `/vendor/login` | Redirect `/vendor/login` | Redirect `/vendor/login` | `403 vendor_auth_required` |
| Internal admin session | Redirect `/vendor/login` | Redirect `/vendor/login` | Redirect `/vendor/login` | Redirect `/vendor/login` | `403 vendor_auth_required` |
| Authenticated vendor session | Allowed | Allowed | Allowed | Allowed | Allowed, subject to vendor ownership and payload validation |

### Current interpretation

- vendor-only read surfaces are not available to internal users, including admin
- internal role does not grant fallback access to vendor-only routes
- vendor routes use vendor identity only, not internal current-site context
- vendor read access is narrower than site-member/admin access because it is identity-specific

## 5. Site Isolation And Vendor Isolation Status

### Vendor isolation

Current vendor isolation is explicit and strong:

- vendor session identity is separate from internal session identity
- vendor session does not carry:
  - `user_id`
  - `role`
  - `current_site_id`
  - `current_site_name`
- `/vendor/business-read-preview` returns only rows matching authenticated `vendor_name`
- preflight rejects payload vendor identity mismatch
- preflight rejects cross-vendor update attempts

### Site isolation

Current site isolation for these read paths is indirect:

- vendor-only routes do not use internal `current_site_id`
- preflight validates target sheet/vendor ownership before returning trusted context
- `/vendor/business-read-preview` is vendor-filtered rather than explicitly site-filtered

That means current protection model is:

- primary isolation by vendor identity
- secondary protection by sheet/vendor ownership checks in preflight
- explicit internal site-session isolation only for internal routes, not for vendor read routes

### Internal/vendor boundary

Current internal/vendor boundary is also covered:

- internal session is redirected away from vendor-only pages
- vendor session is blocked from internal protected `/sheet`
- vendor session is blocked from internal `/api/vendor-work-entry`

## 6. Existing Protections

Current protections already evidenced by runtime structure and smoke include:

- vendor-only route gate via `vendor_login_required`
- deterministic unauthenticated/vendor-auth-required behavior on preflight
- deterministic redirect behavior for vendor-only pages
- trusted vendor identity sourced from session, not caller payload
- cross-vendor update protection
- vendor-name mismatch protection
- vendor business-date mismatch protection
- response payload exclusion of internal/system fields on vendor read preview and vendor scope
- stable vendor read preview ordering and empty-result behavior

## 7. Known Risks

This section is inventory only and does not propose runtime changes in this slice.

Current authorization/isolation review risks include:

- `/vendor/business-read-preview` depends on `vendor_name` identity filtering and does not expose an explicit site-bound scope contract
- preflight sits across the read/write boundary, so later slices must keep scope disciplined to avoid mixing read audit with write migration
- admin and site-member denial behavior for vendor-only pages is stable in smoke, but no dedicated Stage 4B freeze document exists yet for these read-side auth contracts
- there is not yet a dedicated Stage 4B decision on whether any additional auth-boundary guardrail is still missing or whether current coverage is already sufficient

These are planning risks, not confirmed runtime defects.

## 8. Candidate Future Test-Only Guardrails

The following are reasonable future test-only candidates if a later gap review confirms they are still needed:

### Route-level / authorization candidates

- dedicated `/vendor/business-read-preview` internal-admin deny guardrail
- dedicated `/vendor/business-read-preview` unauthenticated redirect guardrail, if later extraction into route-specific isolated smoke is useful
- dedicated preflight auth-boundary guardrail review separating unauthenticated and internal-session behavior

### Vendor isolation candidates

- focused guardrail reaffirming read preview never leaks another vendor's row even when multiple vendors share nearby sheet/runtime context
- focused guardrail reaffirming top-level vendor identity in response always matches authenticated vendor session

### Response-contract candidates

- focused deterministic contract lock for any currently uncovered preflight error path
- focused read-preview contract lock if a later review finds an uncovered auth/error case rather than only success-shape coverage

These are candidates only. This slice does not select one for implementation.

## 9. Future Implementation Work That Is Explicitly Out Of Scope Here

The following belong to future implementation or later planning, and must not be done in this audit slice:

- changing `app.py`
- introducing site-scoped vendor read runtime redesign
- modifying vendor session model
- changing route behavior for `/vendor/business-read-preview`
- changing preflight semantics
- mixing Stage 4B read planning with Stage 4 write runtime migration
- expanding into `/admin/table`, `/api/progress`, `/api/unit-extra`, or other write paths

## 10. Next-Step Boundary

The next safe move after this audit should remain one of:

- a docs-only read contract gap review
- a docs-only read smoke planning note
- one single test-only read guardrail, but only after a narrow gap is explicitly confirmed

Do not:

- start runtime implementation from this document
- broaden into cross-domain redesign
- mix vendor read-path audit with unrelated write-path changes
