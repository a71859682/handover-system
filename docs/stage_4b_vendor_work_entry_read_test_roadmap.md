# Stage 4B Vendor Work Entry Read Test Roadmap

## 1. Baseline Source

- Source baseline: `USER SITE PERMISSIONS FREEZE BASELINE @ 73c2e4d`
- Stage 4B planning branch family:
  - `stage-4b-vendor-work-entry-read-planning`

This document consolidates the current Stage 4B Vendor Work Entry read-side docs-only audits into a tests-only roadmap. It does not change runtime behavior, tests, schema, or business logic.

## 2. Completed Stage 4B Docs-Only Audit Inputs

Current Stage 4B planning is based on these completed docs-only commits and files:

- `d03dbca` — `docs/stage_4b_vendor_work_entry_read_path_inventory.md`
- `4137b7d` — `docs/stage_4b_vendor_work_entry_read_authorization_audit.md`
- `4df05c4` — `docs/stage_4b_vendor_work_entry_read_response_contract_inventory.md`

Together, these documents already inventory:

- read route list
- vendor-only authorization flow
- role/access matrix
- site/vendor isolation status
- success response contract
- error response contract
- deterministic preflight error behavior
- currently unfrozen response/auth boundary areas

## 3. Stage 4B Goal

The Stage 4B goal is not runtime redesign. The goal is:

- freeze Vendor Work Entry read-path contracts through the smallest possible tests-only guardrails
- keep vendor read-path work independent from write-path migration
- preserve the existing vendor session / vendor identity boundary
- avoid mixing read planning with schema, migration, or broad auth redesign

## 4. Read Path Tests-Only Slice Candidates

The current read-side route family is small enough that future implementation should stay narrow and route-specific.

Candidate test-only slices:

1. `/vendor/profile` top-level response shape guardrail
2. `/vendor/scope` top-level and nested `scope` shape guardrail
3. `/vendor/business-read-preview` dedicated route-level redirect/auth-boundary guardrail extraction
4. `/api/vendor/work-entry/preflight` one-single-error deterministic contract refinement, but only if a true gap remains after review
5. `/vendor/home` minimal authenticated page-boundary guardrail refinement

These are candidate slices only. This roadmap does not authorize implementation in this document.

## 5. Minimal Scope Definition Per Slice

### Slice 1: `/vendor/profile` response shape guardrail

- smallest scope:
  - verify only exact top-level JSON keys for authenticated success
- do not:
  - redesign payload
  - expand into auth-flow changes
  - add write-path checks

### Slice 2: `/vendor/scope` response shape guardrail

- smallest scope:
  - verify exact top-level keys and exact `scope` keys
- do not:
  - broaden into vendor/session runtime changes
  - add site-scope redesign work

### Slice 3: `/vendor/business-read-preview` redirect/auth-boundary guardrail

- smallest scope:
  - isolate one route-specific boundary check
  - choose either unauthenticated redirect or internal-session redirect, not both in one slice unless already unavoidable in same harness block
- do not:
  - reopen top-level shape, item shape, or ordering work already strongly covered

### Slice 4: `/api/vendor/work-entry/preflight` deterministic error guardrail

- smallest scope:
  - add exactly one isolated deterministic error contract only if a gap is still confirmed
- do not:
  - expand into write-route runtime validation
  - mix multiple preflight error paths into one slice

### Slice 5: `/vendor/home` page-boundary refinement

- smallest scope:
  - lock a single minimal authenticated page contract beyond current representative fragment checks
- do not:
  - turn this into template/UI redesign work

## 6. Recommended Smoke Guardrail Order

Recommended order, from lowest risk to higher risk:

1. `/vendor/profile` top-level response shape guardrail
   - low risk because it is a small JSON surface with already-evidenced fields

2. `/vendor/scope` exact shape guardrail
   - still low risk, but includes nested object shape

3. `/vendor/business-read-preview` dedicated redirect/auth-boundary extraction
   - moderate risk because it overlaps with existing broad vendor auth smoke and should avoid duplication

4. `/vendor/home` page-boundary refinement
   - moderate risk because HTML assertions can become brittle if over-scoped

5. `/api/vendor/work-entry/preflight` extra deterministic error guardrail
   - only if a concrete uncovered gap remains after the earlier slices
   - keep late because preflight sits on the read/write boundary and is easiest to accidentally over-expand

## 7. Recommended Response Contract Guardrail Order

Recommended contract-freeze order:

1. `/vendor/profile`
   - exact top-level keys

2. `/vendor/scope`
   - exact top-level keys
   - exact `scope` nested keys

3. `/vendor/business-read-preview`
   - no immediate response-shape expansion needed unless a real gap is discovered later
   - current success shape, item shape, ordering, and empty-result coverage are already strong

4. `/api/vendor/work-entry/preflight`
   - only one route-specific deterministic error lock at a time if needed

5. `/vendor/home`
   - keep as last because it is not a JSON contract surface

## 8. Freeze Conditions

Stage 4B can be considered ready for freeze review when all of the following are true:

- no runtime files were changed
- no schema or migration work was introduced
- any added tests are strictly route-specific and tests-only
- `/vendor/profile` and `/vendor/scope` have explicit shape freezes if still deemed necessary
- `/vendor/business-read-preview` has no remaining meaningful auth-boundary or response-contract gap
- `/api/vendor/work-entry/preflight` has no remaining meaningful deterministic error gap worth a separate slice
- no slice broadened into write runtime, session redesign, or cross-domain auth redesign

## 9. Future Implementation Boundaries

The following belong to future implementation and are explicitly out of scope for this roadmap document:

- changing `app.py`
- changing route behavior
- changing vendor session design
- changing site scoping model
- changing preflight semantics
- changing write runtime
- changing schema, migration, models, or database foundation
- broad template/UI work

## 10. Roadmap Discipline

Future Stage 4B implementation should follow these rules:

- only one tests-only guardrail slice at a time
- one route per slice whenever possible
- one contract class per slice whenever possible:
  - auth boundary
  - response shape
  - deterministic error
  - page boundary
- do not mix read-path freeze work with write-path migration work
- do not introduce broad vendor runtime redesign under the label of a smoke guardrail

## 11. Next-Step Boundary

The next safe move after this roadmap should be exactly one of:

- a Stage 4B read-path gap review confirming whether any guardrail is still truly missing
- or one single tests-only read guardrail implementation chosen from this roadmap

Do not:

- begin runtime implementation from this document
- merge multiple guardrails into one slice
- expand into unrelated route families
