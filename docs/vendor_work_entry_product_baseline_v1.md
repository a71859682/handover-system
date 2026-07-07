# Vendor Work Entry Product Baseline v1

## 1. Purpose

This document defines the first integrated product baseline for Vendor Work Entry v1.

Its purpose is to consolidate the completed `VWE-PROD-004` through `VWE-PROD-009` slices into a single stable product reference before future VWE v2 lines begin.

This baseline is documentation-only and does not modify application code, templates, tests, schema, API behavior, permission behavior, workflow behavior, or write behavior.

## 2. Product Capability Inventory

The current Vendor Work Entry product baseline includes:

- `004` Vendor Pre-entry Requirement
- `005` Requirement Confirmation
- `006` Entry Readiness
- `007` Entry Readiness Production Baseline
- `008` Scheduling Gate
- `009` Scheduling Gate Production / Release Baseline

In practical terms, the integrated baseline already supports:

- vendor-authored entry-level requirement input
- site-side per-entry requirement confirmation
- read-side readiness projection
- crew-side readiness display
- read-side scheduling-gate projection
- crew-side scheduling-gate warning display
- frozen regression guardrails for the above product line

## 3. End-to-End Product Flow

The current end-to-end Vendor Work Entry flow is:

1. Vendor creates or updates a Vendor Work Entry.
2. Vendor fills `pre_entry_requirement` at the single-entry level.
3. Site/Crew confirms the requirement per entry when needed.
4. The crew-side read surface derives `readiness_state` and `readiness_reason`.
5. The crew-side read surface derives `scheduling_gate_state` and `scheduling_gate_reason`.
6. Crew UI displays readiness and scheduling-gate signals on the entry list.

Current product semantics:

- entry identity = one Vendor Work Entry
- requirement identity = one Vendor Work Entry
- confirmation identity = one Vendor Work Entry
- readiness identity = one Vendor Work Entry
- scheduling-gate identity = one Vendor Work Entry

The current baseline does not aggregate these decisions:

- per vendor
- per work-content grouping
- per same-day vendor batch

## 4. Actor Boundary

### Vendor

- create entry
- update entry
- fill `pre_entry_requirement`
- submit through existing vendor flow
- cannot confirm requirement
- is not blocked by scheduling-gate warning in v1

### Site/Crew

- view entry requirement data
- confirm requirement per entry
- view `readiness_state` and `readiness_reason`
- view `scheduling_gate_state` and `scheduling_gate_reason`
- view readiness and scheduling-gate indicators in crew-side UI

### Admin

- retains existing site-side operational boundary
- does not receive a new scheduling override surface in v1
- does not receive a new workflow authority surface in v1

## 5. API Boundary

The current API boundary is intentionally narrow and separated:

- `/api/vendor-work-entry`
  - vendor-facing create / update path for Vendor Work Entry data
  - includes requirement write-through behavior already frozen in v1

- `/api/crew-work-entry-requirement-confirm`
  - crew/site-side confirmation path
  - responsible only for requirement confirmation

- `/api/crew-forms`
  - crew-side read surface
  - exposes requirement-related read data
  - exposes readiness projection
  - exposes scheduling-gate projection

These responsibilities should remain separate unless a future redesign slice explicitly changes the contract.

## 6. Data Contract

The integrated v1 data contract includes:

- persisted entry requirement field
  - `pre_entry_requirement`

- persisted confirmation fields
  - `requirement_status`
  - `requirement_confirmed_by`
  - `requirement_confirmed_at`

- crew-side read projection fields
  - `readiness_state`
  - `readiness_reason`
  - `scheduling_gate_state`
  - `scheduling_gate_reason`

Contract boundary notes:

- requirement and confirmation fields are entry-level persisted data
- readiness fields are read-side projection fields
- scheduling-gate fields are read-side projection fields
- scheduling-gate fields are derived from readiness semantics in v1
- no separate scheduling-gate persistence model exists in v1

Frozen rule set:

- pending requirement
  - `readiness_state=not_ready`
  - `readiness_reason=requirement_pending`
  - `scheduling_gate_state=warning`
  - `scheduling_gate_reason=requirement_pending`

- confirmed requirement
  - `readiness_state=ready`
  - `readiness_reason=requirement_confirmed`
  - `scheduling_gate_state=allowed`
  - `scheduling_gate_reason=requirement_confirmed`

- no requirement
  - `readiness_state=ready`
  - `readiness_reason=no_requirement`
  - `scheduling_gate_state=allowed`
  - `scheduling_gate_reason=no_requirement`

## 7. Freeze Scope

The following capabilities are completed and frozen:

- vendor pre-entry requirement authoring
- requirement validation baseline
- requirement confirmation contract
- entry readiness read contract
- entry readiness UI indicator
- scheduling-gate read contract
- scheduling-gate warning UI
- regression guardrails for requirement, confirmation, readiness, scheduling-gate, submit pipeline, and write isolation

The following capabilities are completed and Production Live:

- Vendor Work Entry v1 requirement flow
- Requirement Confirmation flow
- Entry Readiness flow
- Scheduling Gate warning flow
- Crew UI render flow
- Vendor submit regression baseline
- Confirmation regression baseline
- Write isolation regression baseline

Current production status:

- `Vendor Work Entry Product Baseline Production Live`

## 8. Explicit Out-of-Scope

The following remain outside Vendor Work Entry Product Baseline v1:

- Hard Block
- Override
- Scheduling Engine
- Notification
- Audit Log
- Rejected / Returned Flow
- Workflow Redesign

Also intentionally excluded from v1:

- permission rewrite
- broader vendor workflow redesign
- batch scheduling orchestration
- scheduling-driven submit enforcement

## 9. Future Product Lines

The next product lines should be introduced as explicit follow-up slices:

- `VWE-PROD-010B` Hard Block Design Baseline
- `VWE-PROD-011` Override Policy
- `VWE-PROD-012` Scheduling Engine
- `VWE-PROD-013` Notification
- `VWE-PROD-014` Audit Log

These should be layered on top of this v1 baseline rather than folded back into `004` through `009`.
