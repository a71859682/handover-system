# Work Hub Scheduled Integration Planning

## 1. Purpose

- Define the product positioning for Work Hub Scheduled Integration.
- Clarify how Work Hub should evolve from showing only schedulable decision state toward also showing persisted scheduled fact state.
- Keep this slice docs-only with no runtime, schema, API, permission, workflow, or write-path change.

## 2. Current Baseline

- Product OS v1.0 (M1)
- Work Hub v1
- Scheduling Engine v1
- Scheduler Persistence v1

These baselines already provide:

- a role-oriented work surface
- a schedulable decision layer
- a persisted formal schedule write surface

What is still missing is a unified Work Hub view that lets users immediately distinguish between work that can be scheduled and work that has already been formally scheduled.

## 3. Product Goal

Work Hub should eventually present both:

- Decision
  - what is schedulable now
- Fact
  - what is already formally scheduled

The first-screen product questions should become:

- 今天可以開始哪些工作？
- 今天已安排哪些工作？

This keeps Work Hub aligned with its role as the first operational screen after login.

## 4. Information Model

The Work Hub information model should distinguish at least four categories:

- Pending Work
  - work that exists in the system but is not yet ready for formal scheduling action

- Schedulable Work
  - work that the Scheduling Engine decision layer says can now be scheduled

- Scheduled Work
  - work that Scheduler Persistence says has already been formally scheduled

- Blocked Work
  - work that is currently blocked by business or decision constraints

This separation helps users understand the progression from possible work, to ready-to-schedule work, to already-scheduled work.

## 5. Data Sources

The planned integrated Work Hub should combine:

- Dashboard Aggregation
- Scheduling Engine
- Scheduler Persistence

Boundary principles:

- Dashboard Aggregation
  - provides general work information and role-oriented summary context

- Scheduling Engine
  - provides decision state such as schedulable and blocked

- Scheduler Persistence
  - provides fact state such as formally scheduled items

Work Hub must not re-judge business rules on its own.

Decision and fact must remain separate:

- Decision answers what can be scheduled
- Fact answers what has been scheduled

## 6. Mobile First

The integrated Work Hub should remain mobile-first:

- formally scheduled information should be high-priority on the first screen
- a user should be able to complete the primary daily scan on one page
- page switching should be minimized

This is especially important once Work Hub needs to present both decision state and scheduled fact state without becoming cluttered.

## 7. Out-of-Scope

- Runtime implementation
- UI implementation
- Calendar
- Notification
- Analytics
- Attendance
- Permission redesign

## 8. Proposed Next Slices

- M1-IMP-002 Runtime Aggregation
- M1-IMP-003 Work Hub UI
- M1-IMP-004 Guardrail
- M1-IMP-005 Production Baseline
- M1-IMP-006 Release Baseline
