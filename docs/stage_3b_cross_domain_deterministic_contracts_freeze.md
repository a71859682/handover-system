# Stage 3B Cross-Domain Deterministic Contracts Freeze

## 1. Stable Baseline

- Stable baseline commit: `8fb5eee`
- Freeze status: `Stage 3B Freeze Candidate`
- Production baseline: `BASELINE GREEN @ 8fb5eee`

This document records the Stage 3B freeze baseline for cross-domain deterministic contracts. Stage 3B freeze is documentation only and does not change runtime behavior.

## 2. Completed Items

- `IW-001`
- `XD-READ-001`
- `XD-READ-002`
- `SMOKE-HARNESS-WIN-001`
- `XD-READ-003`
- `XD-READ-004`
- `XD-READ-005`
- `XD-READ-006`
- `XD-READ-007`
- `XD-READ-008`
- `XD-READ-009`
- `XD-READ-010`
- `XD-READ-011`
- `XD-READ-012`
- `XD-READ-013`
- `XD-READ-014`
- `XD-READ-015`

## 3. `/api/crew-missing` Freeze Scope

The following contracts are frozen for `/api/crew-missing`:

- success-side top-level response shape
- success-side `items[]` item-level response shape
- representative happy-path payload checks
- deterministic empty-result payload
- invalid `sheet_id` error contract
- invalid `business_date` error contract
- missing `current_site_id` auth-boundary contract
- `sheet_not_in_current_site` auth-boundary contract
- `site_permission_missing` auth-boundary contract
- deterministic error messages for covered error paths

## 4. `/api/crew-daily-summary` Freeze Scope

The following contracts are frozen for `/api/crew-daily-summary`:

- success-side top-level response shape
- success-side `items[]` item-level response shape
- success-side `totals` shape
- representative happy-path payload checks
- deterministic empty-result payload
- invalid `sheet_id` error contract
- invalid `business_date` error contract
- missing `current_site_id` auth-boundary contract
- deterministic error messages for covered error paths

## 5. `/vendor/business-read-preview` Coverage Summary

Current Stage 3B coverage confirms:

- authenticated success payload top-level response shape
- authenticated `entries[]` item-level response shape
- deterministic empty-result payload
- stable entry ordering contract
- vendor identity boundary behavior
- exclusion of forbidden internal/system fields from response payload

Stage 3B freeze does not redefine vendor runtime behavior beyond the currently covered read contracts.

## 6. Site Read Isolation And Smoke Coverage Summary

Current Stage 3B coverage confirms:

- `tests/smoke_test.py` includes route-level deterministic contract guardrails for the covered read APIs
- `tools/check_site_read_isolation.py` verifies cross-site denial behavior
- `tools/check_site_read_isolation.py` verifies stale selected-sheet denial behavior
- `tools/check_site_read_isolation.py` verifies missing-site-context denial behavior
- `tools/check_site_read_isolation.py` verifies permission-removed denial behavior
- site read isolation coverage includes both grid and crew read surfaces

## 7. Explicit Out Of Scope

Stage 3B does not include:

- schema change
- migration
- governance redesign
- Stage 4 write isolation runtime work

Stage 3B freeze also does not introduce:

- new runtime capability
- new auth scope
- new production write-path behavior

## 8. Next Step Boundary

- next step must begin with Stage 3B Freeze Baseline review
- do not start Stage 4 runtime work directly from this document
- any post-freeze work should begin from the frozen baseline family established at `8fb5eee`

