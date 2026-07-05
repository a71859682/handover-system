# Stage 5 Vendor Work Entry API Inventory

## 1. Baseline Source

- Source baseline: `8a4fe85`
  - `Merge vendor work entry stage 4B read smoke baseline`

This document is a docs-only Stage 5 planning inventory for the Vendor Work Entry API family. It does not change runtime behavior, tests, schema, or business logic.

## 2. Inventory Scope

This inventory covers the current Vendor Work Entry API family across write, read, and preflight surfaces:

- `POST /api/vendor-work-entry`
- `POST /api/vendor/work-entry/preflight`
- `GET /vendor/business-read-preview`
- `GET /vendor/profile`
- `GET /vendor/scope`
- `GET /vendor/home`

This inventory does not cover:

- unrelated admin table flows
- unrelated progress / unit-extra runtime
- schema or migration work
- broader vendor UI redesign

## 3. Vendor Work Entry API / Route List

### `POST /api/vendor-work-entry`

- Route:
  - `app.py:4120`
- Category:
  - write API
- Primary purpose:
  - create or update vendor work-entry rows
- Primary caller:
  - internal authenticated user flow
- Current permission boundary:
  - not vendor-only
  - vendor session must not pass this internal route
  - current-site enforcement, site permission enforcement, and sheet/vendor ownership validation are expected before write

### `POST /api/vendor/work-entry/preflight`

- Route:
  - `app.py:4224`
- Category:
  - preflight / trusted-context API
- Primary purpose:
  - return trusted vendor write context before a write attempt
- Primary caller:
  - authenticated vendor session
- Current permission boundary:
  - vendor authentication required
  - internal session rejected
  - caller-supplied vendor identity cannot override authenticated vendor identity

### `GET /vendor/business-read-preview`

- Route:
  - `app.py:3747`
- Category:
  - read route
- Primary purpose:
  - vendor-facing preview of current vendor business entries
- Primary caller:
  - authenticated vendor session
- Current permission boundary:
  - vendor-only
  - unauthenticated/internal sessions redirect to `/vendor/login`

### `GET /vendor/profile`

- Route:
  - `app.py:3724`
- Category:
  - read route
- Primary purpose:
  - vendor identity readback
- Primary caller:
  - authenticated vendor session
- Current permission boundary:
  - vendor-only
  - unauthenticated/internal sessions redirect to `/vendor/login`

### `GET /vendor/scope`

- Route:
  - `app.py:3738`
- Category:
  - read route
- Primary purpose:
  - vendor identity scope readback
- Primary caller:
  - authenticated vendor session
- Current permission boundary:
  - vendor-only
  - unauthenticated/internal sessions redirect to `/vendor/login`

### `GET /vendor/home`

- Route:
  - `app.py:3713`
- Category:
  - vendor-only landing/read page
- Primary purpose:
  - authenticated vendor home surface
- Primary caller:
  - authenticated vendor session
- Current permission boundary:
  - vendor-only
  - unauthenticated/internal sessions redirect to `/vendor/login`

## 4. Per-API Purpose, Caller, And Permission Boundary

### Write surface summary

- `/api/vendor-work-entry`
  - caller:
    - internal authenticated site-scoped flow
  - boundary:
    - vendor session blocked
    - write isolation enforced through current-site, site permission, sheet ownership, and vendor ownership checks
  - risk class:
    - high-risk write path

### Preflight surface summary

- `/api/vendor/work-entry/preflight`
  - caller:
    - authenticated vendor
  - boundary:
    - vendor auth required
    - trusted vendor identity taken from session
    - cross-vendor and mismatch paths rejected
  - risk class:
    - read/write boundary surface

### Read surface summary

- `/vendor/business-read-preview`
  - caller:
    - authenticated vendor
  - boundary:
    - vendor-only route
    - data filtered to current vendor identity

- `/vendor/profile`
  - caller:
    - authenticated vendor
  - boundary:
    - vendor-only route

- `/vendor/scope`
  - caller:
    - authenticated vendor
  - boundary:
    - vendor-only route

- `/vendor/home`
  - caller:
    - authenticated vendor
  - boundary:
    - vendor-only route

## 5. Stage 4A / 4B Coverage Mapping

### Stage 4A completed coverage

Stage 4A established the Vendor Work Entry write smoke baseline:

- docs-only planning/readiness/gap-review/roadmap freeze completed
- tests-only guardrails completed for:
  - `vendor_not_in_sheet`
  - missing current site
  - happy-path success response top-level contract
  - `sheet_mismatch`
  - permission removed / `site_permission_missing`
- write baseline merged to `main`

This means Stage 4A already covers the primary deterministic write-path contract family without runtime migration.

### Stage 4B completed coverage

Stage 4B established the Vendor Work Entry read smoke baseline:

- docs-only planning completed for:
  - read path inventory
  - authorization audit
  - response contract inventory
  - read test roadmap
- tests-only guardrails completed for:
  - `/vendor/profile` success response top-level shape
  - `/vendor/scope` success response top-level shape
  - `/vendor/business-read-preview` unauthenticated boundary and no-session-pollution guardrail

This means Stage 4B already covers the first minimal read-path freeze layer.

## 6. Current Capability Status

### Already completed capabilities

- internal write isolation baseline for `/api/vendor-work-entry`
- vendor preflight trusted-context contract baseline
- vendor-only read route baseline
- vendor profile top-level response guardrail
- vendor scope top-level response guardrail
- vendor business read preview auth-boundary baseline

### Tests-only candidates

Potential remaining tests-only candidates, if later review still justifies them:

- `/vendor/home` minimal page-boundary refinement
- `/api/vendor/work-entry/preflight` one-single-error contract extraction, only if a real uncovered deterministic gap is later identified
- additional route-level extraction for read-side boundary behavior, only if future freeze review finds current coverage too broad or implicit

These are candidates only and not authorized by this document.

### Future production implementation candidates

Potential future implementation candidates, beyond current Stage 4A/4B freeze work:

- runtime consolidation across vendor write/read/preflight contract boundaries
- stronger explicit vendor/site read scoping model
- broader vendor API unification work
- any runtime change to session or authorization helpers

These are later production implementation candidates and are not part of this Stage 5 inventory slice.

## 7. Uncovered Or Deferred API Contract Areas

Known deferred or not-yet-promoted areas include:

- `/vendor/home` still relies on representative-fragment HTML checks rather than a stronger dedicated contract freeze
- preflight sits on the read/write boundary, so future work must be careful not to over-expand a small contract slice into runtime migration
- no Stage 5 runtime implementation has started

These are planning/deferment notes, not evidence of a current defect.

## 8. Suggested Stage 5 Minimal Implementation Slices

Stage 5 should remain incremental and evolutionary. Suggested minimal slices:

1. `STAGE5-AUDIT-002 — Vendor Work Entry API Contract Freeze Review`
   - docs-only or review-only
   - purpose:
     - confirm whether the combined Stage 4A + 4B baseline is already sufficient for freeze at API-family level

2. `STAGE5-AUDIT-003 — Vendor Home Boundary Guardrail`
   - tests-only
   - purpose:
     - add one minimal page-boundary guardrail if review confirms it is still worth doing

3. `STAGE5-AUDIT-004 — Vendor Preflight Residual Contract Review`
   - review-first
   - purpose:
     - verify whether any single preflight deterministic error still deserves isolation as a standalone guardrail

4. `STAGE5-AUDIT-005 — Vendor Work Entry API Freeze Baseline`
   - docs-only
   - purpose:
     - record the combined write/read/preflight frozen baseline if no meaningful blocker remains

## 9. Scope Discipline For Stage 5

Stage 5 should keep these boundaries:

- do not modify `app.py` in this inventory slice
- do not mix schema or migration work into API planning
- do not broaden into unrelated route families
- do not introduce runtime redesign under a planning label
- keep tests-only slices single-purpose and single-route whenever possible

## 10. Classification Summary

### Completed abilities

- write smoke baseline
- read smoke baseline
- merge to `main`
- no runtime/schema/migration expansion

### Tests-only candidates

- vendor-home boundary refinement
- isolated preflight error review and only then one single guardrail if truly needed

### Future production implementation candidates

- API-family runtime consolidation
- stronger explicit read/write scoping model
- later production-side contract hardening beyond smoke freeze

## 11. Next-Step Boundary

The next safe move after this Stage 5 inventory should be one of:

- a review deciding whether Vendor Work Entry API can already be treated as a broader freeze candidate
- or one single tests-only candidate slice if a real narrow gap is still confirmed

Do not:

- start runtime implementation from this document
- mix in schema or migration work
- expand into unrelated write/read domains
