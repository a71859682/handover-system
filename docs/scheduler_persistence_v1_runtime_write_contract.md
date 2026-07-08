# Scheduler Persistence v1 Runtime Write Contract

## 1. Purpose

- Define the docs-only runtime write contract for Scheduler Persistence v1.
- Clarify the minimum scheduling write behavior expected in a future implementation slice.
- Keep this slice limited to contract design with no code, schema, API implementation, permission, workflow, or write-path change.

## 2. Current Baseline

- Scheduling Engine v1 already provides a read-only scheduling decision surface.
- SP-001 Product Design Baseline is complete.
- SP-002 Schema Evaluation is complete.
- The current product direction leans toward a dedicated `scheduling_entries` model.

The system can already determine whether an entry is schedulable. It does not yet persist the fact that an entry has been formally scheduled.

## 3. Write Contract

The future formal scheduling write path should define a minimum contract across five layers:

- request
- validation
- authorization
- decision check
- persistence
- response

The scheduling write path should not re-implement Scheduling Engine semantics independently. It should consume the scheduling decision boundary already established by Scheduling Engine v1.

## 4. Minimal Request Shape

Recommended minimum request fields:

- `entry_id`
- `sheet_id`
- `action = schedule_entry`
- `scheduled_date`
- `scheduled_time`

Expected request meaning:

- `entry_id`
  - identifies the Vendor Work Entry to be formally scheduled
- `sheet_id`
  - confirms the current scheduling context and sheet isolation boundary
- `action`
  - preserves an explicit contract marker for the scheduling write intent
- `scheduled_date`
  - records the planned formal schedule date
- `scheduled_time`
  - records the planned formal schedule time

## 5. Minimal Success Response

Recommended minimum success response:

- `ok`
- `action`
- `schedule`
  - `id`
  - `entry_id`
  - `sheet_id`
  - `scheduled_date`
  - `scheduled_time`

This success response should confirm that a persisted formal schedule was created without expanding into calendar, notification, attendance, or analytics responsibilities.

## 6. Failure Contract

The minimum failure contract should define deterministic error outcomes for:

- `entry_not_schedulable`
- `duplicate_schedule`
- `sheet_mismatch`
- `entry_not_found`
- `vendor_auth_forbidden`
- `site_context_invalid`

Recommended meanings:

- `entry_not_schedulable`
  - the target entry fails the Scheduling Engine decision boundary
- `duplicate_schedule`
  - the target entry already has an active schedule in the first baseline
- `sheet_mismatch`
  - the request sheet context does not match the resolved target
- `entry_not_found`
  - the target entry does not exist
- `vendor_auth_forbidden`
  - vendor authentication cannot access the scheduling persistence write path
- `site_context_invalid`
  - the current site context is missing or invalid

## 7. Persistence Rules

- Only entries that Scheduling Engine classifies as schedulable may create a schedule.
- Blocked entries must not create a persisted schedule.
- Duplicate schedule attempts must not create a second active schedule.
- In the first baseline, one Vendor Work Entry maps to one active schedule.

Scheduler Persistence records only the formal scheduling outcome.

It does not own:

- calendar projection
- notification fan-out
- analytics projection
- attendance state

## 8. Transaction Boundary

The following steps should execute in one transaction or under an equivalent consistent rollback rule:

- target resolve
- authorization
- decision check
- duplicate check
- insert

Expected consistency principle:

- if any step fails, no persisted schedule should be created
- the duplicate and insert boundary should be protected against race-condition drift
- the final committed state should always match the returned response

## 9. Explicit Out-of-Scope

- schema implementation
- runtime implementation
- UI
- calendar
- notification
- analytics
- audit log
- attendance
- override
- permission redesign

## 10. Proposed Next Slices

- SP-004 Persistence Schema Baseline
- SP-005 Runtime Write Implementation
- SP-006 Read Contract
- SP-007 Work Hub Integration
- SP-008 Guardrail Freeze
- SP-009 Production Baseline
- SP-010 Release Baseline
