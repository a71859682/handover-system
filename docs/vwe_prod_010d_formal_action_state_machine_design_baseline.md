# VWE-PROD-010D - Formal Action State Machine Design Baseline

## 1. Purpose

This document defines the docs-only design baseline for the Vendor Work Entry v2 Formal Action State Machine.

Its purpose is to establish the minimal product state model that future Hard Block API, UI, and guardrail slices will follow.

This slice does not modify application code, static assets, templates, tests, schema, API behavior, permission behavior, workflow behavior, or write behavior.

## 2. Current Baseline

The current baseline is:

- `Vendor Work Entry Product Baseline v1` is complete.
- Scheduling Gate v1 is warning-only.
- `VWE-PROD-010B` has already defined the Hard Block product direction.
- `VWE-PROD-010C` has already defined the first hard-block contract-planning direction.
- `VWE-PROD-010D-0` has already confirmed that Hard Block should not attach to existing endpoints and should instead target a new crew-side formal action.

This means the current product already provides:

- vendor entry authoring
- requirement confirmation
- readiness projection
- scheduling-gate projection
- warning-only crew-side visibility

What it does not yet provide is:

- a formal-action state machine
- a crew-side hard-block write boundary
- a deterministic blocked-state runtime contract

## 3. Core State Model

The recommended minimal v2 state model is:

- `draft`
- `submitted`
- `requirement_pending`
- `ready`
- `blocked`
- `formally_approved`

These states are product-level semantic states.

They are not yet a schema implementation plan in this slice.

## 4. State Semantics

### `draft`

- vendor is still creating or editing the entry
- entry is not yet treated as a completed crew-consumable formal candidate

### `submitted`

- entry exists in a form that crew can view
- the entry is visible on the read side
- requirement evaluation can now matter operationally

### `requirement_pending`

- the entry has a requirement
- the requirement has not yet been confirmed
- the entry is not yet ready for formal crew-side actions that require Entry Ready

### `ready`

- the entry has no requirement, or
- the requirement has been confirmed
- the entry is eligible for formal crew-side actions that require Entry Ready

### `blocked`

- a crew-side formal action requiring Entry Ready was attempted
- the entry was not ready for that action
- the action must fail deterministically

### `formally_approved`

- the crew-side formal action has completed successfully
- the entry has crossed the first formal operational approval boundary

## 5. Formal Actions

The minimal formal-action set should include:

- `vendor_create_entry`
- `vendor_update_entry`
- `crew_confirm_requirement`
- `crew_formal_approve_entry`

Action intent:

- `vendor_create_entry`
  - creates a new entry in vendor workflow

- `vendor_update_entry`
  - updates entry content in vendor workflow

- `crew_confirm_requirement`
  - resolves requirement-pending state

- `crew_formal_approve_entry`
  - represents the first crew-side formal action that requires Entry Ready

Only `crew_formal_approve_entry` is the first intended Hard Block target.

## 6. Hard Block Rules

The first minimal Hard Block rule set is:

- `vendor_create_entry`
  - must not be blocked by hard block

- `vendor_update_entry`
  - must not be blocked by hard block

- `crew_confirm_requirement`
  - must not be blocked by hard block

- `crew_formal_approve_entry`
  - requires `ready`

- if the entry is not ready when `crew_formal_approve_entry` is attempted
  - result should be `blocked`
  - error should be `entry_not_ready`

This keeps the workflow resolvable:

- vendor can still author the entry
- crew can still confirm the requirement
- only the formal approval boundary is blocked

## 7. Transition Table

| Current State | Action | Allowed? | Next State | Reason |
| --- | --- | --- | --- | --- |
| `draft` | `vendor_create_entry` | Yes | `submitted` | entry is created and becomes crew-readable |
| `draft` | `vendor_update_entry` | Yes | `draft` | vendor can continue editing before operational use |
| `submitted` | `vendor_update_entry` | Yes | `submitted` | vendor can still update authoring content |
| `submitted` | `crew_confirm_requirement` | Yes | `ready` or `submitted` | if requirement exists and is confirmed, the entry becomes operationally ready; if no requirement is relevant, submitted visibility remains unchanged |
| `submitted` | readiness evaluation detects pending requirement | Yes | `requirement_pending` | entry has requirement but is not yet confirmed |
| `submitted` | readiness evaluation detects no requirement | Yes | `ready` | no requirement means entry is already ready |
| `requirement_pending` | `crew_confirm_requirement` | Yes | `ready` | confirmation resolves pending requirement |
| `requirement_pending` | `crew_formal_approve_entry` | No | `blocked` | formal action requires Entry Ready |
| `ready` | `crew_formal_approve_entry` | Yes | `formally_approved` | ready entry may complete formal approval |
| `blocked` | `crew_confirm_requirement` | Yes | `ready` | the blocked cause can still be resolved through confirmation |
| `blocked` | `crew_formal_approve_entry` | No | `blocked` | repeated formal approval attempt remains blocked until ready |
| `formally_approved` | `vendor_update_entry` | Future decision | `formally_approved` or separate future state | post-approval mutation policy is intentionally not fixed in this baseline |

Transition notes:

- `blocked` is primarily an action-result state, not a vendor-authoring restriction state
- `ready` is the minimum gate required for `crew_formal_approve_entry`
- the first state machine intentionally avoids override and rejected/returned complexity

## 8. Out-of-Scope

The following are outside this design baseline:

- override
- rejected / returned flow
- notification
- audit log
- scheduling engine
- permission model redesign
- UI implementation
- API implementation

Also outside this slice:

- schema / migration
- runtime state persistence strategy
- bulk formal-action approval
- downstream workflow redesign after formal approval

## 9. Proposed Next Slices

The next slices should be:

- `010E` Hard Block API / Write Guardrail
- `010F` Hard Block UI
- `010G` Hard Block Guardrail Freeze
- `010H` Hard Block Production Baseline

Suggested sequence:

1. lock the API/write guardrail for `crew_formal_approve_entry`
2. define the blocking UI surface and message
3. freeze the hard-block guardrail behavior
4. consolidate the first production baseline for Hard Block
