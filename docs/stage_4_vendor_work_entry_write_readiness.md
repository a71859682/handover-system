# Stage 4 Vendor Work Entry Write Readiness

## 1. Baseline Source

- Source baseline: `USER SITE PERMISSIONS FREEZE BASELINE @ 73c2e4d`

This document records a docs-only readiness audit target for `/api/vendor-work-entry`. It does not change runtime behavior.

## 2. Audit Target

This audit is focused on:

- `/api/vendor-work-entry` write readiness
- vendor work entry write isolation
- vendor identity / sheet / site boundary

The goal is to freeze the current write boundary for vendor work entry before any broader Stage 4 runtime migration begins.

## 3. Current Runtime Boundary

Current runtime boundary remains:

- SQLite remains the primary write runtime
- `USE_SQLALCHEMY_WRITES=false`
- no schema change
- no migration
- no database foundation change
- no runtime implementation started

This audit does not enable dual-write runtime behavior and does not begin write migration.

## 4. Known Coverage

Current known coverage includes:

- `run_vendor_work_entry_write_isolation_smoke(...)`
- same-site create / update success
- cross-site create / update reject
- missing current site reject
- permission removed reject
- vendor-not-in-sheet reject
- sheet mismatch reject
- invalid `business_date` reject
- invalid headcount reject
- DB state unchanged checks

These checks already confirm both success-path persistence and failure-path non-mutation behavior for the current write path.

## 5. Vendor Session / Identity Boundary

Current session and identity boundary coverage includes:

- vendor login page / vendor-only endpoints
- internal session blocked from vendor-only flow
- vendor preflight contract
- vendor identity mismatch / cross-vendor preflight reject
- vendor session cannot pass internal `/api/vendor-work-entry`

This keeps vendor identity and internal identity separated while preserving the current write-path boundary.

## 6. Readiness Tool Summary

Current readiness-tool evidence includes:

- `tools/check_site_write_isolation_readiness.py` marks `/api/vendor-work-entry` as `ENFORCED`
- current-site enforcement is expected before write
- site permission enforcement is expected before write
- sheet/vendor ownership validation is expected before write

The readiness inventory treats `/api/vendor-work-entry` as a high-risk non-admin site-scoped write path with enforced validation.

## 7. Known Gaps

The current gaps are readiness and freeze gaps rather than runtime implementation gaps:

- no dedicated freeze baseline yet
- future test-only gap review may still be needed
- no broad runtime implementation started

At this stage, the next safest move is still documentation or test-only review, not runtime migration.

## 8. Next Step Boundary

The next step after this readiness audit is constrained to:

- document review
- or vendor work entry test-only gap review

Do not:

- start runtime write implementation directly from this document
- expand into other write paths
- broaden into governance redesign
