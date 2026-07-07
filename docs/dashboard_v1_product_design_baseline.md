# Dashboard v1 Product Design Baseline

## 1. Purpose

This document defines the product design baseline for Dashboard v1.

Dashboard v1 is positioned as the first daily work homepage for internal site members after login.

Its purpose is to consolidate already-completed operational product lines into a single first-stop surface so site and crew users can quickly see what requires attention today.

This baseline is docs-only.

It does not modify application code, static assets, templates, tests, schema, migration behavior, API behavior, permission behavior, workflow behavior, or write behavior.

## 2. Current Product Baselines

Dashboard v1 is intended to build on the following completed product baselines:

- Vendor Work Entry v1 - Production Live
- Hard Block v1 - Production Live
- Persistent Formal Approval v1 - Production Live

This means Dashboard v1 does not need to invent a new workflow from scratch.

Instead, it should aggregate and prioritize information that already exists across the current crew-side product surfaces.

## 3. Primary Users

### Site / Crew

Site and crew users are the primary target for Dashboard v1.

They need a fast operational view of:

- which entries still need requirement confirmation
- which entries are blocked
- which entries are ready but still awaiting formal approval
- which entries have already completed formal approval

### Vendor

Vendor is not the primary user for Dashboard v1 in the first version.

A vendor-facing dashboard can remain a future extension, but it is not required for the first baseline.

### Admin

Admin should be able to use the same overall operational dashboard direction as internal site users.

The first version should not redesign admin permissions or create an admin-only dashboard model.

## 4. Dashboard Modules

The following modules are recommended for Dashboard v1.

### Today’s Pending Requirement Confirmations

Purpose:

- show entries whose pre-entry requirement exists but is not yet confirmed

Operational value:

- surfaces items that block readiness and later formal approval

### Today’s Pending Formal Approvals

Purpose:

- show entries that are ready for action but not yet formally approved

Operational value:

- highlights the next operational queue after requirement confirmation is complete

### Today’s Completed Formal Approvals

Purpose:

- show entries that already have persisted formal approval

Operational value:

- gives a trustworthy completed-action view for the current day

### Ready / Blocked Summary

Purpose:

- provide a compact summary of ready vs blocked workload

Operational value:

- helps the team understand whether the current bottleneck is confirmation, approval, or downstream scheduling readiness

### Today’s Entry List

Purpose:

- provide a broad list view of today’s entries across vendors

Operational value:

- keeps the dashboard anchored to the actual day’s operational queue

### Quick Action Entry Points

Purpose:

- give users a fast route into the existing crew-side surfaces that already support confirmation and formal approval

Operational value:

- keeps the dashboard actionable instead of purely informational

## 5. Information Priority

Dashboard v1 should prioritize information in the following order:

1. Blocked Items
2. Pending Formal Approval
3. Today’s Entries
4. Completed Approvals
5. Summary Statistics

Rationale:

- blocked items represent the highest operational risk because they prevent downstream crew action
- pending formal approvals represent the next most urgent crew-side queue
- today’s entries provide the full operational context
- completed approvals are useful, but are less urgent than blocked or pending items
- summary statistics should support decision-making, not dominate the screen

## 6. Data Sources

Dashboard v1 should prefer existing read contracts rather than introducing new workflow semantics in the first design baseline.

Expected primary data sources:

- `/api/crew-forms`
  - current crew-side entry read surface
  - already includes readiness state
  - already includes scheduling gate state
  - already includes formal approval read contract

- Vendor Work Entry
  - source of today’s entry identity, work content, planned timing, requirement state, and readiness inputs

- Formal Approval
  - source of persisted formal approval state and approval metadata

The first dashboard direction should therefore be read-driven and aggregation-oriented.

It should reuse current operational contracts wherever possible.

## 7. Out-of-Scope

The following are explicitly out of scope for this design baseline:

- Dashboard API implementation
- Dashboard UI implementation
- Notification
- Scheduling Engine
- Analytics
- Audit Log
- Permission redesign

Also out of scope:

- dashboard-specific write behavior
- workflow redesign
- vendor-facing dashboard rollout

## 8. Proposed Next Slices

Recommended next slices:

- `DASH-002` Dashboard Read Contract
- `DASH-003` Dashboard API
- `DASH-004` Dashboard UI
- `DASH-005` Dashboard Guardrail Freeze
- `DASH-006` Dashboard Production Baseline

Suggested sequence:

1. define the dashboard read contract and aggregation shape
2. implement the dashboard API surface
3. build the first crew-facing dashboard UI
4. freeze dashboard guardrails
5. consolidate the production baseline
