# Stage 4 Vendor Work Entry Test-Only Gap Review

## 1. Baseline

- Review baseline: `USER SITE PERMISSIONS FREEZE BASELINE @ 73c2e4d`

This document records a docs-only gap review for `/api/vendor-work-entry`. It does not change runtime behavior, tests, schema, or write-path implementation.

## 2. Existing Test And Check Foundation

Current `/api/vendor-work-entry` protection already rests on these sources:

- `tests/smoke_test.py`
  - `run_vendor_work_entry_write_isolation_smoke(...)`
  - vendor login and vendor-only endpoint boundary checks
  - vendor write preflight contract checks
  - vendor identity mismatch and cross-vendor preflight rejection checks
  - internal-session rejection from vendor-only flows
- `tools/check_site_write_isolation_readiness.py`
  - marks `/api/vendor-work-entry` as `ENFORCED`
  - records current-site enforcement expectation
  - records site-permission enforcement expectation
  - records sheet/vendor ownership validation expectation
- `docs/stage_4_vendor_work_entry_write_readiness.md`
  - captures current runtime boundary
  - captures known write isolation coverage
  - captures vendor session and identity boundary summary

## 3. Covered Boundary Summary

Current coverage already includes:

- same-site create success
- same-site update success
- cross-site create reject
- cross-site update reject
- missing current site reject
- permission removed reject
- vendor-not-in-sheet reject
- entry-to-sheet mismatch reject
- invalid `business_date` reject
- invalid headcount reject
- DB state unchanged checks after rejected writes
- vendor login page and vendor-only endpoint availability checks
- internal session blocked from vendor-only flow
- vendor preflight contract shape checks
- vendor identity mismatch reject in preflight
- cross-vendor preflight reject
- vendor session blocked from internal `/api/vendor-work-entry`

## 4. Remaining Test-Only Gaps

The remaining gaps are relatively small and should stay test-only:

- deterministic error contract locking for selected vendor-work-entry write failures
  - for example, status + `error.code` + `error.message` on key rejection paths
- explicit route-specific smoke isolation for the internal `/api/vendor-work-entry` auth boundary
  - today this is covered as part of broader vendor session smoke
- explicit freeze-level documentation of which failure paths are already considered stable versus still observational

These are refinement gaps, not missing foundational coverage gaps.

## 5. Gaps That Should Not Be Implemented In This Slice

The following should not be expanded in this review slice:

- runtime behavior changes in `app.py`
- schema or migration changes
- new vendor write capabilities
- broader `/admin/table` or unrelated write-path work
- dual-write enablement
- `USE_SQLALCHEMY_WRITES=true`
- governance redesign
- broad refactoring of vendor auth or vendor session helpers

This slice should remain a documentation-only gap review.

## 6. Recommended Next Minimal Safe Test-Only Slice

Recommended next slice:

- `STAGE4-AUDIT-005 — Vendor Work Entry Deterministic Error Contract Guardrail`

Why this is the next safest slice:

- it stays test-only
- it does not widen the write surface
- it builds on already-existing rejection coverage
- it helps convert observational failure behavior into explicit frozen contract behavior

Suggested first focus within that slice:

- lock one deterministic failure path first, not all of them at once
- best candidate: `vendor_not_in_sheet` or `sheet_mismatch`
- verify status code, `ok=false`, `error.code`, and deterministic `error.message`

## 7. Next Step Boundary

The next step after this review is constrained to:

- document review
- or one single vendor work entry test-only guardrail slice

Do not:

- start runtime implementation directly from this review
- expand to other write paths
- broaden this into a general vendor write migration plan
