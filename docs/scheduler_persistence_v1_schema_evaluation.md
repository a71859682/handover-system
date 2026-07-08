# Scheduler Persistence v1 Schema Evaluation

## 1. Purpose

- Define the docs-only schema evaluation for Scheduler Persistence v1.
- Compare the candidate persistence models needed for future runtime implementation.
- Keep this slice limited to product and data-model evaluation with no schema, API, UI, workflow, or write-path implementation.

## 2. Candidate A

### Extend `vendor_work_entries`

Possible direction:

- add persisted scheduling fields directly onto `vendor_work_entries`

Example categories of fields:

- scheduled state
- scheduled by
- scheduled at
- scheduling metadata

Strengths:

- simple read path for existing entry-centric views
- lower join complexity for first-pass crew read surfaces
- easier to expose scheduled status in already-existing entry payloads

Weaknesses:

- mixes vendor-submitted entry data with crew/site scheduling result
- makes the entry row carry both source data and downstream operational state
- reduces flexibility if scheduling later needs history, reschedule tracking, or multi-step state

## 3. Candidate B

### Add `scheduling_entries`

Possible direction:

- add a dedicated persistence table that records formal scheduling outcomes separately from the source entry

Example categories of fields:

- `entry_id`
- scheduling status
- scheduled by
- scheduled at
- future calendar-oriented metadata

Strengths:

- clean separation between source entry and scheduling outcome
- better fit for future scheduling history and richer scheduling lifecycle
- easier to extend for calendar, notification, analytics, and downstream integrations

Weaknesses:

- requires join-based read composition
- adds more schema and migration surface
- increases implementation complexity for first runtime slice

## 4. Product Comparison

### Data Consistency

- Candidate A is simpler for single-row consistency because source entry and scheduled state live together.
- Candidate B is stronger for boundary consistency because it preserves the distinction between submitted entry data and persisted scheduling outcome.

### Extensibility

- Candidate A works for a minimal single-state baseline.
- Candidate B is more extensible for future scheduling lifecycle growth.

### Audit Capability

- Candidate A is weaker because row mutation tends to overwrite the latest state.
- Candidate B is more compatible with audit-oriented evolution and future scheduling history.

### Notification Compatibility

- Candidate A can support basic notification triggers.
- Candidate B is a cleaner fit because persisted scheduling events can be treated as distinct notification sources.

### Calendar Compatibility

- Candidate A can expose scheduled state but is less expressive for future calendar metadata.
- Candidate B is better aligned with a future calendar-oriented scheduling model.

### Analytics Compatibility

- Candidate A supports simple reporting.
- Candidate B better supports long-term analytics because the scheduling record is modeled as its own operational artifact.

### Multi-Schedule Capability

- Candidate A is a weak fit if one entry later needs reschedule history or multiple scheduling attempts.
- Candidate B is a stronger fit for future multi-schedule or scheduling-history requirements.

### Maintenance Cost

- Candidate A is cheaper in the short term.
- Candidate B is cleaner in the long term but costs more to implement and maintain initially.

### Migration Complexity

- Candidate A is lower complexity for an initial rollout.
- Candidate B is higher complexity because it introduces a new table and new read/write integration points.

## 5. Recommendation

The first product recommendation is to lean toward a dedicated `scheduling_entries` model.

Reasoning:

- it keeps Scheduling Engine and Scheduler Persistence clearly separated
- it preserves the distinction between vendor input data and crew/site scheduling outcome
- it better supports future Calendar, Notification, Analytics, and scheduling-history product lines

This is a product recommendation only.

This evaluation does not make the implementation decision final and does not introduce schema changes in this slice.

## 6. Out-of-Scope

- schema implementation
- runtime
- API
- UI
- write
- permission
- workflow

## 7. Proposed Next Slices

- SP-003 Runtime Write Contract
- SP-004 Read Contract
- SP-005 Work Hub Integration
- SP-006 Guardrail Freeze
- SP-007 Production Baseline
- SP-008 Release Baseline
