# P-3 Implementation Preflight

## 1. Current State

- Stable baseline: `ef934eb`
- Planning branch: `p-2-permission-planning`
- Planning PR: `#1`
  - status: `APPROVED`
  - merge state: `NOT MERGED`

Current state summary:

- production remains on the stable baseline family established during release closure
- planning work has been completed as docs-only changes
- no P-3 runtime implementation has started

## 2. Planning Artifacts

P-3 implementation should begin only with the following planning artifacts as the active reference set:

- [p-2-planning-summary.md](C:\Users\耀祥\Documents\handover-system-formal\docs\p-2-planning-summary.md)
- [p-2a-permission-contract-freeze.md](C:\Users\耀祥\Documents\handover-system-formal\docs\p-2a-permission-contract-freeze.md)
- [p-2b-vendor-identity-planning.md](C:\Users\耀祥\Documents\handover-system-formal\docs\p-2b-vendor-identity-planning.md)
- [p-2c-login-flow-planning.md](C:\Users\耀祥\Documents\handover-system-formal\docs\p-2c-login-flow-planning.md)
- [p-2d-implementation-roadmap.md](C:\Users\耀祥\Documents\handover-system-formal\docs\p-2d-implementation-roadmap.md)

These documents together define:

- the frozen permission and session contracts
- the vendor identity gap
- the recommended login architecture direction
- the staged implementation roadmap

## 3. Implementation Entry Criteria

P-3 implementation should not begin until all of the following are true:

- PR `#1` is merged
- `main` is updated to include the approved planning docs
- the working implementation branch is created from the updated `main`
- staging is synchronized from the merged baseline when needed
- production remains unchanged during planning-to-implementation transition
- the stable baseline is reconfirmed before the first code change
- the implementation branch starts from a clean working tree
- local validation still passes at the chosen implementation starting point

Recommended pre-flight verification before the first code change:

- confirm `git status` is clean
- confirm target branch point is correct
- rerun:
  - `python -m compileall tools tests`
  - `python tests/smoke_test.py`

## 4. First Implementation Target

### P-3 Stage 1

**Vendor Authentication Foundation**

### Goal

- introduce the minimal code foundation needed for vendor authentication
- keep internal login stable
- avoid session-key collision with internal users
- establish a safe base for later vendor session and authorization work

### Expected touch points

High-level touch points may include:

- authentication entry routing
- vendor account lookup path
- vendor session namespace foundation
- auth decorator preparation or identity discrimination path
- smoke/readiness tooling updates

This stage should stay as small as possible and avoid expanding into downstream vendor workflow behavior.

### Expected risks

- accidental regression to internal login
- ambiguous session identity handling
- coupling vendor auth too early to current-site behavior
- introducing incomplete vendor auth that appears valid but lacks clear scope boundaries

### Validation plan

- local compile validation
- local smoke validation
- focused authenticated vendor-path checks in isolated test coverage
- regression checks for internal login and logout
- staging validation before any production-facing rollout

## 5. Out of Scope

P-3 Stage 1 should not do the following:

- vendor UI rollout
- vendor authorization completion
- vendor read/write workflow completion
- schema migration
- production rollout
- production data changes
- broad login UX redesign
- current-site lifecycle redesign

The goal is foundation only, not full vendor enablement.

## 6. Success Criteria

P-3 Stage 1 should be considered complete only if all high-level conditions are met:

- vendor authentication foundation exists in code
- internal login behavior remains stable
- internal session behavior remains stable
- no unintended production-facing contract drift is introduced
- validation passes locally
- the stage remains small enough to review and roll back cleanly
- follow-on stages can build on the result without redefining the identity model
