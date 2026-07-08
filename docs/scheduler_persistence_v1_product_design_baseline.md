# Scheduler Persistence v1 Product Design Baseline

## 1. Purpose

- Define the product positioning for Scheduler Persistence v1.
- Keep this slice docs-only with no code, schema, API, permission, workflow, or write-path change.
- Establish Scheduler Persistence as a distinct product line from Scheduling Engine v1.

## 2. Current Baseline

- Vendor Work Entry v1
- Hard Block v1
- Persistent Formal Approval v1
- Work Hub v1
- Scheduling Engine v1

These baselines already provide the current readiness, hard-block, formal-approval, and scheduling-decision surfaces needed to support a future persisted scheduling layer.

## 3. Product Goal

- Persist the result of a formal scheduling action.
- Keep persistence separate from Scheduling Engine decision logic.
- Provide a stable shared source for future Calendar, Notification, and Analytics product lines.

Scheduler Persistence v1 is not responsible for deciding whether an entry is schedulable. Its role is to preserve the outcome after a crew/site-side scheduling action is completed.

## 4. Core Semantics

- Scheduling Engine answers which Vendor Work Entries can be scheduled.
- Scheduler Persistence records which Vendor Work Entries have already been formally scheduled.
- In the first baseline, one Vendor Work Entry maps to one formal scheduling record.

This separation keeps the system model clear:

- Decision Layer
  - dynamic
  - read-only
  - derived from existing readiness, scheduling-gate, and formal-approval state

- Persistence Layer
  - explicit
  - write-backed
  - represents a committed scheduling result

## 5. Candidate Persistence Models

### Option A. Extend `vendor_work_entries`

Possible direction:

- add scheduling-related persisted columns directly on the existing entry row

Advantages:

- simple lookup path
- fewer joins for read flows
- easier to surface basic scheduled state in existing read contracts

Tradeoffs:

- mixes raw vendor entry data with crew/site scheduling outcome
- reduces clarity between source entry and persisted scheduling action
- makes future audit / reschedule / multi-stage scheduling expansion harder

### Option B. Add `scheduling_entries`

Possible direction:

- create a separate persistence table dedicated to formal scheduling results

Advantages:

- preserves clean separation between vendor-submitted entry data and scheduling result
- easier to extend for future scheduling metadata
- better fit for future calendar, notification, analytics, and history-oriented features

Tradeoffs:

- requires join-based read integration
- adds schema and migration complexity
- requires more deliberate contract planning for write and read paths

This baseline compares the options but does not choose the implementation yet.

## 6. Relationship

### Scheduling Engine

- Scheduling Engine remains the Decision Layer.
- It determines whether a Vendor Work Entry is schedulable.
- Scheduler Persistence must not re-implement scheduling decision rules.

### Work Hub

- Work Hub can later surface scheduled items from persisted scheduling state.
- Work Hub should not itself become the source of truth for persisted scheduling outcome.

### Future Calendar

- Calendar should read from persisted scheduling records rather than recomputing schedule commitment from decision state alone.

### Future Notification

- Notification should trigger from persisted scheduling events, not only from schedulable status.

## 7. Out-of-Scope

- schema implementation
- runtime API
- UI
- calendar
- notification
- audit
- override
- permission redesign

## 8. Proposed Next Slices

- SP-002 Persistence Schema Evaluation
- SP-003 Runtime Write Contract
- SP-004 Read Contract
- SP-005 Work Hub Integration
- SP-006 Guardrail Freeze
- SP-007 Production Baseline
- SP-008 Release Baseline
