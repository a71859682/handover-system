# Scheduling Engine v1 State & Rules Baseline

## 1. Purpose

This document defines the state and rules baseline for Scheduling Engine v1.

Its purpose is to establish the minimal scheduling state model and the first set of scheduling rules before any schema, API, UI, or runtime implementation is introduced.

This slice is docs-only.

It does not modify application code, schema, migration behavior, API behavior, permission behavior, workflow behavior, or write behavior.

## 2. Current Baseline

Scheduling Engine v1 state and rules are expected to build on the following existing product capabilities:

- Vendor Work Entry
- Requirement
- Readiness
- Hard Block
- Formal Approval
- Work Hub
- SE-001 Product Design Baseline

This means the scheduling model should be derived from already-established entry-level product signals, rather than inventing a separate workflow foundation.

## 3. Scheduling State Model

The minimal scheduling state model should be:

- `unscheduled`
- `schedulable`
- `blocked`
- `scheduled`

## 4. State Semantics

### `unscheduled`

The entry has not yet entered formal scheduling.

It may still be waiting for prerequisite signals, or it may already be eligible but not yet assigned to a real schedule.

### `schedulable`

The entry satisfies the minimum conditions required to be treated as eligible for scheduling.

This means the system can regard it as available for future formal scheduling action.

### `blocked`

The entry does not currently satisfy the minimum conditions required for scheduling.

The blocking reason should come from already-existing prerequisite product signals rather than a separate parallel rule system.

### `scheduled`

The entry has already been formally placed into a real work schedule.

This state is part of the model baseline now, even though the first implementation slice may not persist it yet.

## 5. Rule Inputs

The minimal scheduling decision should depend on the following inputs:

- `pre_entry_requirement`
- `requirement_status`
- `readiness_state`
- `scheduling_gate_state`
- `formal_approval_state`
- `business_date`
- `planned_at`

These inputs are sufficient for the first baseline to determine whether an entry is still blocked, merely unscheduled, or eligible to become schedulable.

## 6. Minimal Rules

The first minimal rules should be:

- `formal_approval_state = approved` and `scheduling_gate_state = allowed` => `schedulable`
- `formal_approval_state != approved` => `blocked`
- `scheduling_gate_state = warning` => `blocked`
- before an entry is formally placed into a real schedule, it should default to `unscheduled`
- the first version should not implement time conflict logic

These rules imply that schedulability is only reached after both prerequisite readiness/gate conditions and formal approval conditions are satisfied.

## 7. Transition Table

| Current State | Condition | Next State | Reason |
| --- | --- | --- | --- |
| `unscheduled` | `formal_approval_state != approved` | `blocked` | formal approval is not complete |
| `unscheduled` | `scheduling_gate_state = warning` | `blocked` | entry still fails scheduling gate |
| `unscheduled` | `formal_approval_state = approved` and `scheduling_gate_state = allowed` | `schedulable` | entry satisfies minimal scheduling prerequisites |
| `blocked` | blocking prerequisite remains unresolved | `blocked` | entry is still not eligible for scheduling |
| `blocked` | `formal_approval_state = approved` and `scheduling_gate_state = allowed` | `schedulable` | previously blocked entry becomes eligible |
| `schedulable` | no formal schedule placement yet | `schedulable` | entry remains eligible but not yet scheduled |
| `schedulable` | formally placed into a real schedule | `scheduled` | entry becomes part of scheduled work |
| `scheduled` | schedule remains valid | `scheduled` | no change in formal schedule placement |

## 8. Out-of-Scope

The following are explicitly out of scope for this baseline:

- schema implementation
- API implementation
- UI implementation
- time conflict
- calendar integration
- notification
- audit log
- override
- permission redesign

## 9. Proposed Next Slices

Recommended next slices:

- `SE-003` Scheduling Read Contract Planning
- `SE-004` Scheduling Runtime Baseline
- `SE-005` Work Hub Integration
- `SE-006` Guardrail Freeze
- `SE-007` Production Baseline
- `SE-008` Release Baseline

Suggested sequencing:

1. define scheduling read contract semantics
2. establish the first runtime scheduling baseline
3. integrate scheduling signals into Work Hub
4. freeze scheduling guardrails
5. consolidate production and release baselines
