# Stage 4 Vendor Work Entry Smoke Guardrail Planning

## 1. Baseline

- Planning baseline: `USER SITE PERMISSIONS FREEZE BASELINE @ 73c2e4d`

This document records a docs-only planning note for future `/api/vendor-work-entry` smoke guardrails. It does not change runtime behavior, tests, schema, or write-path implementation.

## 2. Existing Smoke Protection

Current smoke and readiness protection already includes:

- `tests/smoke_test.py`
  - `run_vendor_work_entry_write_isolation_smoke(...)`
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
- vendor session boundary smoke in `tests/smoke_test.py`
  - vendor login page and vendor-only endpoint checks
  - internal session blocked from vendor-only flow
  - vendor preflight contract checks
  - vendor identity mismatch / cross-vendor preflight reject
  - vendor session blocked from internal `/api/vendor-work-entry`
- `tools/check_site_write_isolation_readiness.py`
  - `/api/vendor-work-entry` marked `ENFORCED`
  - current-site enforcement expectation
  - site-permission enforcement expectation
  - sheet/vendor ownership validation expectation

## 3. Proposed Future Smoke Guardrail List

The following guardrails are the most reasonable future candidates:

- deterministic `vendor_not_in_sheet` error contract guardrail
- deterministic `sheet_mismatch` error contract guardrail
- deterministic missing current site error contract guardrail
- deterministic permission removed error contract guardrail
- internal-route auth-boundary smoke guardrail for vendor session access to `/api/vendor-work-entry`
- stable success response contract guardrail for same-site create / update

## 4. Guardrail Purpose And Protection Target

### Route-Level

- internal-route auth-boundary smoke guardrail
  - purpose: freeze that vendor session cannot use the internal protected route
  - protects: separation between internal user route and vendor session flow

### Authorization

- missing current site deterministic error guardrail
  - purpose: freeze auth rejection behavior when site context is absent
  - protects: site-context boundary
- permission removed deterministic error guardrail
  - purpose: freeze behavior after site permission revocation
  - protects: permission boundary after session state becomes stale
- `vendor_not_in_sheet` deterministic error guardrail
  - purpose: freeze rejection when vendor identity does not belong to the target sheet
  - protects: vendor-to-sheet ownership boundary

### Response Contract

- same-site create / update success response contract guardrail
  - purpose: freeze the minimal success payload shape or key contract if later chosen
  - protects: stable caller expectations after accepted writes
- `sheet_mismatch` deterministic error contract guardrail
  - purpose: freeze error payload contract when entry id and target sheet diverge
  - protects: conflict signaling contract

### Data Isolation

- cross-site create / update non-mutation guardrail
  - purpose: keep DB unchanged on cross-site reject
  - protects: site isolation
- permission removed non-mutation guardrail
  - purpose: keep DB unchanged after permission revocation
  - protects: stale permission isolation
- invalid input non-mutation guardrail
  - purpose: keep DB unchanged on invalid `business_date` or invalid headcount
  - protects: input validation boundary

## 5. Guardrails That Should Remain Future Implementation

The following should not be implemented in this planning slice:

- any runtime behavior change in `app.py`
- any schema or migration work
- broad success payload freeze across all fields at once
- broad preflight/runtime unification work
- dual-write enablement
- `USE_SQLALCHEMY_WRITES=true`
- vendor auth redesign
- broader vendor write migration across other endpoints

This slice remains planning only.

## 6. Recommended Minimal Smoke Implementation Order

Recommended order from lower risk to higher risk:

1. `vendor_not_in_sheet` deterministic error contract guardrail
   - low risk because rejection path already exists and is already observed
2. `sheet_mismatch` deterministic error contract guardrail
   - low-to-medium risk because the path is already exercised and conflict semantics are narrow
3. missing current site deterministic error contract guardrail
   - medium risk because it depends on session-state details
4. permission removed deterministic error contract guardrail
   - medium risk because it depends on stale authorization state
5. internal-route auth-boundary smoke guardrail for vendor session
   - medium risk because it overlaps with broader vendor session coverage
6. success response contract guardrail
   - highest risk in this group because it can over-freeze response shape too early

## 7. Recommended Next Slice

If the next slice must remain minimal and test-only, the safest first implementation candidate is:

- `STAGE4-AUDIT-005A — Vendor Work Entry Vendor-Not-In-Sheet Error Contract Guardrail`

Why this first:

- already exercised in existing smoke
- narrow rejection path
- low blast radius
- no need to widen auth or session setup

## 8. Next Step Boundary

The next step after this planning note is constrained to:

- document review
- or one single vendor work entry test-only guardrail implementation

Do not:

- start runtime implementation directly from this plan
- expand to unrelated write paths
- broaden this planning note into general write migration work
