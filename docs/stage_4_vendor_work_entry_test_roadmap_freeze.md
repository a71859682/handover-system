# Stage 4 Vendor Work Entry Test Roadmap Freeze

## 1. Baseline

- Roadmap freeze baseline: `USER SITE PERMISSIONS FREEZE BASELINE @ 73c2e4d`

This document freezes the documentation roadmap for future `/api/vendor-work-entry` test and smoke work. It is planning only and does not change runtime behavior, tests, tools, schema, or write-path implementation.

## 2. Completed Docs-Only Audit And Planning Items

The following docs-only items are already complete:

- `STAGE4-AUDIT-003 — Vendor Work Entry Write Readiness Document`
  - recorded in `docs/stage_4_vendor_work_entry_write_readiness.md`
- `STAGE4-AUDIT-004 — Vendor Work Entry Test-only Gap Review`
  - recorded in `docs/stage_4_vendor_work_entry_test_only_gap_review.md`
- `STAGE4-AUDIT-005 — Vendor Work Entry Smoke Guardrail Planning`
  - recorded in `docs/stage_4_vendor_work_entry_smoke_guardrail_planning.md`

These documents together define the current planning baseline for this write path.

## 3. Frozen Implementation Order

Future implementation order should remain test-first and low-risk-first:

1. deterministic `vendor_not_in_sheet` error contract guardrail
2. deterministic `sheet_mismatch` error contract guardrail
3. deterministic missing current site error contract guardrail
4. deterministic permission removed error contract guardrail
5. internal-route auth-boundary smoke guardrail for vendor session access to `/api/vendor-work-entry`
6. minimal success response contract guardrail, if still needed after the error-path freezes
7. only after test-only slices are stabilized should a dedicated freeze baseline be considered for this path

This ordering is the roadmap baseline and should not be casually reordered without a new planning review.

## 4. Slice Goals And Protection Scope

### Slice 1: `vendor_not_in_sheet` deterministic error contract

- goal:
  - freeze the rejection contract when vendor identity does not belong to the target sheet
- protects:
  - vendor-to-sheet ownership boundary
  - stable caller-facing failure semantics

### Slice 2: `sheet_mismatch` deterministic error contract

- goal:
  - freeze the conflict contract when entry id and target sheet diverge
- protects:
  - row-to-sheet consistency signaling
  - stable conflict reporting

### Slice 3: missing current site deterministic error contract

- goal:
  - freeze failure semantics when internal current-site context is absent
- protects:
  - site-context authorization boundary

### Slice 4: permission removed deterministic error contract

- goal:
  - freeze failure semantics after site permission is revoked
- protects:
  - stale authorization boundary
  - non-mutation expectations after permission loss

### Slice 5: internal-route auth-boundary smoke guardrail

- goal:
  - freeze that vendor session cannot pass the internal protected route
- protects:
  - separation between vendor session flow and internal route boundary

### Slice 6: minimal success response contract guardrail

- goal:
  - freeze only the smallest stable success-side response contract if still necessary
- protects:
  - caller expectations after accepted writes

## 5. Guardrail Classification

### Smoke

- internal-route auth-boundary smoke guardrail
- minimal success response contract guardrail

### Regression

- deterministic `vendor_not_in_sheet` error contract
- deterministic `sheet_mismatch` error contract
- deterministic missing current site error contract
- deterministic permission removed error contract

### Authorization

- missing current site contract
- permission removed contract
- internal-route vendor-session boundary

### Isolation

- `vendor_not_in_sheet` contract
- `sheet_mismatch` contract
- all non-mutation failure-path checks already present in smoke

## 6. Items That Must Stay Frozen

The following must remain frozen to avoid scope expansion:

- no runtime implementation in `app.py`
- no schema change
- no migration
- no `USE_SQLALCHEMY_WRITES=true`
- no dual-write rollout
- no broader vendor auth redesign
- no expansion into `/admin/table`
- no expansion into unrelated write paths
- no broad success-payload freeze before narrower failure-path contracts are settled

## 7. Sole Planning Baseline Rule

This document is the sole roadmap baseline for future `/api/vendor-work-entry` test-first implementation planning unless a later planning review explicitly supersedes it.

Any later implementation proposal for this path should align with:

- `docs/stage_4_vendor_work_entry_write_readiness.md`
- `docs/stage_4_vendor_work_entry_test_only_gap_review.md`
- `docs/stage_4_vendor_work_entry_smoke_guardrail_planning.md`
- this roadmap freeze document

## 8. Next Step Boundary

The next step after this roadmap freeze is constrained to:

- review of this roadmap freeze
- or one single low-risk test-only implementation slice from the frozen order above

Do not:

- start runtime implementation directly from this roadmap
- skip to a higher-risk slice without fresh review
- broaden this roadmap into general Stage 4 migration work
