# Scheduler Persistence v1 Read Contract Planning

## 1. Purpose

- Define the docs-only read contract planning for Scheduler Persistence v1.
- Establish a shared read contract direction for future Work Hub, Calendar, Notification, Analytics, and Mobile consumers.
- Keep this slice limited to read-contract design with no runtime, schema, API implementation, workflow, or write-path change.

## 2. Data Sources

The planned Scheduler Persistence read surface should be composed from:

- Scheduling Entries (planned persistence source)
- Vendor Work Entry
- Scheduling Engine Decision
- Business Date
- Scheduled Date
- Scheduled Time

Each source has a distinct role:

- Scheduling Entries
  - preserve the fact that a formal schedule exists
- Vendor Work Entry
  - preserve the original entry context and vendor-submitted details
- Scheduling Engine Decision
  - remains the decision boundary used before scheduling is committed
- Business Date
  - supports operational “today” views
- Scheduled Date / Scheduled Time
  - support display and downstream schedule-oriented grouping

## 3. Read Contract Proposal

Recommended high-level contract:

```json
{
  "summary": {},
  "scheduled_entries": [],
  "today_schedule": [],
  "future_schedule": []
}
```

Recommended semantic meaning:

- `summary`
  - aggregate counts for scheduling-oriented views
- `scheduled_entries`
  - the primary persisted scheduling dataset in the requested scope
- `today_schedule`
  - scheduled entries that belong to the current operational day
- `future_schedule`
  - scheduled entries that are already committed but fall after today

## 4. Summary

The first baseline summary should include at least:

- `scheduled_count`
- `today_schedule_count`
- `future_schedule_count`

This keeps the contract small while supporting Work Hub, Calendar, and other consumer summaries.

## 5. Consumer

The planned read contract should support:

- Work Hub
- Calendar
- Notification
- Analytics
- Mobile

Expected usage direction:

- Work Hub
  - surfaces committed schedules as operational work context
- Calendar
  - uses persisted schedule facts as display input
- Notification
  - uses persisted schedule facts as trigger input
- Analytics
  - uses persisted schedule facts as reporting input
- Mobile
  - consumes a compact schedule-oriented read contract without recomputing scheduling state client-side

## 6. Design Principles

- Scheduler Persistence preserves scheduling facts.
- It must not re-judge whether an entry is schedulable.
- It must not recompute readiness.
- It must not recompute formal approval.
- It must not recompute scheduling decision.

The read contract should read persisted scheduling outcome and enrich it with already-established context, rather than recreating upstream product logic.

## 7. Out-of-Scope

- Runtime
- UI
- Calendar implementation
- Notification implementation
- Analytics implementation
- Attendance
- Audit
- Override

## 8. Proposed Next Slices

- SP-005 Runtime Schema Baseline
- SP-006 Runtime Write
- SP-007 Work Hub Integration
- SP-008 Guardrail Freeze
- SP-009 Production Baseline
- SP-010 Release Baseline
