# Scheduling Engine v1 Read Contract Planning

## 1. Purpose

This document defines the planning baseline for the Scheduling Engine v1 read contract.

Its purpose is to establish how Scheduling Engine should expose scheduling-oriented decision outputs as a read contract before any runtime API, schema, or UI implementation is introduced.

This slice is docs-only.

It does not modify application code, schema, migration behavior, API implementation, permission behavior, workflow behavior, or write behavior.

## 2. Data Sources

The Scheduling Engine read contract should be built on existing product signals and operational context.

Expected data sources:

- Vendor Work Entry
- Readiness
- Scheduling Gate
- Formal Approval
- Business Date
- Planned Time

These inputs already describe the entry-level operational state needed for a first-pass scheduling decision layer.

## 3. Read Contract Proposal

Scheduling Engine v1 should expose a high-level read contract that is decision-oriented rather than CRUD-oriented.

Suggested structure:

```json
{
  "summary": {},
  "schedulable_entries": [],
  "blocked_entries": [],
  "scheduled_entries": [],
  "unscheduled_entries": []
}
```

### `summary`

A compact aggregation object that helps downstream surfaces understand the current scheduling picture at a glance.

Expected semantics may include:

- schedulable count
- blocked count
- scheduled count
- unscheduled count

### `schedulable_entries`

Entries that satisfy the minimal scheduling rules and can be treated as ready for scheduling action.

### `blocked_entries`

Entries that remain ineligible for scheduling because prerequisite decision signals are not yet satisfied.

### `scheduled_entries`

Entries that have already entered a future real scheduling state.

This category is part of the contract planning now, even if the first runtime slice may not fully populate it yet.

### `unscheduled_entries`

Entries that are still outside a real schedule and have not yet transitioned into a formally scheduled state.

This category helps the contract remain explicit about entries that are still pending scheduling progression.

## 4. Decision Principles

Scheduling Engine must follow these principles:

- do not recompute readiness
- do not recompute formal approval
- only aggregate and interpret existing states
- Scheduling Engine is a Decision Layer

This means the read contract should be derived from already-established product signals rather than introducing parallel rule systems that drift from the existing baseline.

## 5. Work Hub Relationship

Work Hub should consume the Scheduling Engine read contract rather than inventing its own scheduling interpretation.

This keeps the responsibilities clear:

- Scheduling Engine decides which entries are schedulable, blocked, unscheduled, or scheduled
- Work Hub presents those results as operational work surfaces

Work Hub should therefore not decide schedulable state on its own.

## 6. Mobile First

The Scheduling Engine read contract should support mobile-first consumption.

That means:

- prioritize information that can be acted on immediately
- reduce the amount of client-side assembly required
- keep contract sections easy to map into compact work surfaces

The goal is to make downstream mobile UI simpler and more reliable, not to push scheduling interpretation into the frontend.

## 7. Out-of-Scope

The following are explicitly out of scope for this planning slice:

- Runtime API
- UI
- Schema
- Write
- Time Conflict
- Calendar
- Notification
- Audit

## 8. Proposed Next Slices

Recommended next slices:

- `SE-004` Runtime Baseline
- `SE-005` Work Hub Integration
- `SE-006` Guardrail Freeze
- `SE-007` Production Baseline
- `SE-008` Release Baseline

Suggested sequencing:

1. define the first runtime scheduling baseline
2. integrate the scheduling contract into Work Hub
3. freeze contract and regression guardrails
4. consolidate production and release baselines
