# Dashboard v1 Read Contract Planning

## 1. Purpose

This document defines the planning baseline for the Dashboard v1 read contract.

Its role is to establish a shared data contract direction for both the future Dashboard API and the future Dashboard UI.

This planning slice is docs-only.

It does not implement an API, UI, schema, permission change, workflow change, or write behavior.

The intent is to align product semantics first so later implementation can stay consistent across backend aggregation and frontend presentation.

## 2. Dashboard Sections

Dashboard v1 is expected to organize information into the following sections.

### Blocked Items

Entries that currently cannot proceed to the next crew-side formal action because readiness or scheduling gate conditions are not satisfied.

### Pending Formal Approval

Entries that are ready for the next formal crew-side action but do not yet have a completed formal approval.

### Pending Requirement Confirmation

Entries whose pre-entry requirement exists but has not yet been confirmed by site or crew users.

### Today's Entries

A daily operational list of today's relevant work entries so users can understand the full workload context.

### Completed Today

Entries that have already completed formal approval today or otherwise represent completed crew-side action for the current operational window.

### Summary Statistics

A compact summary of key counts so the team can quickly assess workload shape, bottlenecks, and completion status.

### Quick Actions

A lightweight action-oriented section that links users into the most common operational surfaces without forcing them to navigate through multiple intermediate pages.

## 3. Data Sources

Each dashboard section should build on already-existing product capabilities wherever possible.

### `/api/crew-forms`

Primary source for crew-side work entry read data.

Expected to provide:

- work entry identity
- site-scoped visibility
- readiness state and reason
- scheduling gate state and reason
- formal approval state and metadata
- requirement-related read information already surfaced in the crew experience

### Vendor Work Entry

Provides the core operational entry object used throughout the platform.

Relevant dashboard uses include:

- planned date and time context
- work content identity
- vendor-linked operational context
- daily entry listing

### Formal Approval

Provides persisted formal approval information for completed approval state and approval metadata.

Relevant dashboard uses include:

- completed formal approval state
- approved_by
- approved_at

### Readiness

Provides the core distinction between entries that are operationally ready and entries that are still waiting on prerequisite completion.

Relevant dashboard uses include:

- blocked detection
- pending readiness interpretation
- ready-for-approval filtering

### Scheduling Gate

Provides the higher-level crew-side decision signal for whether the next formal action should proceed.

Relevant dashboard uses include:

- blocked item surfacing
- warning versus allowed interpretation
- crew-side prioritization

## 4. Read Contract Proposal

Dashboard v1 should return a high-level aggregated structure.

This document defines semantics only and does not lock the exact API endpoint or transport format.

### `summary`

A compact object containing top-level counts for the dashboard.

Expected semantics:

- total entries in scope for today
- blocked count
- pending requirement confirmation count
- pending formal approval count
- completed approval count

### `blocked_items`

A list of entries currently blocked from the next crew-side formal action.

Expected semantics:

- entry identity
- relevant vendor or work context
- readiness state
- scheduling gate state
- primary blocking reason

### `pending_approvals`

A list of entries that are ready but not yet formally approved.

Expected semantics:

- entry identity
- ready state
- formal approval pending state
- enough context for quick review and approval routing

### `pending_requirements`

A list of entries whose requirement confirmation is still pending.

Expected semantics:

- entry identity
- requirement presence
- confirmation pending state
- enough context to route users toward confirmation work

### `today_entries`

A broader list of entries relevant to today's operational queue.

Expected semantics:

- entry identity
- planned time context
- readiness signal
- scheduling gate signal
- formal approval signal

### `quick_actions`

A lightweight list of action entry points the dashboard can surface to reduce navigation friction.

Expected semantics:

- action label
- target surface or route
- associated count or urgency when relevant

## 5. Mobile First Considerations

Dashboard v1 should be planned with mobile-first operational use in mind.

Key considerations:

- the most important information should appear first
- the main daily work should be understandable within a single screen flow
- interaction patterns should remain suitable for one-handed phone usage
- the dashboard should reduce unnecessary page switching

This means the read contract should support concise, high-signal sections rather than assuming large desktop tables as the default consumption model.

## 6. Explicit Out-of-Scope

The following are explicitly out of scope for this planning slice:

- Dashboard API implementation
- Dashboard UI implementation
- Analytics
- Notification
- Scheduling Engine
- Audit Log

Also out of scope:

- schema changes
- permission redesign
- workflow redesign
- dashboard write behavior

## 7. Proposed Next Slices

Recommended next slices:

- `DASH-003` Dashboard API Baseline
- `DASH-004` Dashboard UI Baseline
- `DASH-005` Dashboard Guardrail Freeze
- `DASH-006` Dashboard Production Baseline

Suggested implementation order:

1. define the Dashboard API around the agreed read contract semantics
2. build the Dashboard UI on top of that contract
3. freeze API and UI guardrails
4. consolidate the production baseline
