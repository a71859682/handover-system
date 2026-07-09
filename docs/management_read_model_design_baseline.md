# M2-IMP-002A — Management Read Model Design Baseline

## 1. Purpose

This slice defines the first design baseline for a future Management Read Model.

Management Read Model should be understood as:

`same-site, read-only, management-oriented projection layer built from frozen operational read sources, without re-deriving workflow or decision semantics`

Its purpose is to:

- clarify why the current Management Insight layer is useful but still limited
- define the future management read boundary before helper, API, or UI expansion begins
- reduce the risk of contract drift, duplicated rule logic, and Work Hub surface pollution

This slice is docs-only.

It does not modify runtime code, static assets, templates, tests, schema, migration behavior, API behavior, permission behavior, workflow behavior, or write behavior.

## 2. Current Context

Current production baseline:

- commit:
  - `9b39483`
  - `Refine management insight summary copy`
- current management capability:
  - Management Insight Summary baseline
  - Management Insight metric drilldown baseline
  - Management Insight summary copy refinement baseline
- current status:
  - Production Live
  - Deploy PASS
  - Logs PASS
  - Runtime Health PASS

The current Management Insight layer already proves that read-only management presentation can be added safely on top of frozen operational surfaces.

However, it still depends on lightweight summary counts and should not be mistaken for a complete management read boundary.

## 3. Why Management Read Model Is Needed

The current Management Insight layer is intentionally small:

- it summarizes existing counts
- it supports drilldown into existing Work Hub operational detail
- it preserves read-only boundaries

That is the right M2 starting point.

But it also has clear limits:

- it is optimized for first-screen summary, not deeper management analysis
- it is tied to existing dashboard / work hub runtime surfaces
- it does not yet define a stable management-facing projection contract
- it should not force Work Hub to grow into a general management surface

Future product directions such as:

- analytics
- KPI-style management summaries
- Owner View
- 工區管理部 View
- broader management drilldown

will need a more stable read boundary so that:

- management surfaces do not recompute semantics independently
- multiple UIs do not each invent their own aggregation logic
- Work Hub remains a frozen operational presentation surface
- future management products can evolve without polluting frozen contracts

## 4. Role And Responsibility

Management Read Model should eventually be responsible for:

- management summary
- scheduling overview
- approval overview
- requirement overview
- operational risk overview
- drilldown refs

These responsibilities are read-oriented only.

They describe how existing operational truth can be projected for management consumption.

Management Read Model must not be responsible for:

- write behavior
- workflow action
- scheduling decision
- approval decision
- requirement confirmation
- permission expansion
- replacing Work Hub runtime
- redefining dashboard ownership

Interpretation:

- Scheduling Engine remains the decision owner
- Approval / Requirement workflows remain the workflow owners
- Work Hub remains the frozen operational presentation layer
- Management Read Model should project, not decide

## 5. Source Mapping

The following existing sources are valid reuse candidates.

### API Surfaces

- `/api/dashboard`
- `/api/work-hub-runtime`
- `/api/scheduling`

### Helper Surfaces

- `build_dashboard_payload(...)`
- `build_work_hub_runtime_payload(...)`

### Operational Fact Sources

- scheduling facts
- formal approval state
- requirement status
- vendor work entries

### Interpretation

These sources already expose the minimum read facts needed to support a future management projection layer.

They should be treated as upstream operational read sources rather than rewritten or replaced.

Management Read Model should prefer reuse before introducing any new contract.

## 6. Boundary And Guardrails

The following boundaries are mandatory for the design baseline.

### Read-only

- Management Read Model must be read-only.
- It must not introduce write paths, mutations, or action semantics.

### Same-site Only

- The first baseline must remain same-site only.
- It must not introduce cross-site aggregation or cross-site read expansion.

### No Schema Change In Design Baseline

- This design slice does not require schema change.
- Future schema pressure may exist, but it is explicitly out of scope here.

### No Permission Change In Design Baseline

- This design slice does not redesign authorization or visibility policy.
- Existing dashboard / runtime boundaries remain in force.

### No Workflow Or Write Behavior Change

- vendor write behavior remains unchanged
- requirement confirmation remains unchanged
- formal approval write behavior remains unchanged
- scheduling write behavior remains unchanged

### No Scheduling Engine Decision Re-derivation

- Management Read Model must not re-judge:
  - blocked
  - schedulable
  - scheduled

Decision semantics remain upstream.

### No Approval Or Requirement Workflow Re-derivation

- Management Read Model must not redefine:
  - approval decision semantics
  - requirement workflow semantics
  - readiness workflow semantics

### No Work Hub Runtime Contract Pollution

- Work Hub runtime should not become the accidental management source of truth.
- Future management-specific projection should not casually expand frozen Work Hub runtime responsibilities.

### No Frontend-only Analytics Truth

- frontend summary logic must not become the owner of analytics semantics
- management truth should not depend on repeated frontend-only recomposition

## 7. High-level Shape Draft

This section is intentionally high-level.

It does not freeze a final contract.

The likely shape should include:

- `management_summary`
- `scheduling_overview`
- `approval_overview`
- `requirement_overview`
- `operational_risk_overview`
- `drilldown_refs`

### `management_summary`

Purpose:

- provide management-level top-line counts
- act as the first compact read surface for high-level status

### `scheduling_overview`

Purpose:

- project scheduling fact and scheduling decision context for management reading
- separate committed schedule facts from eligibility-oriented context

### `approval_overview`

Purpose:

- summarize approval-oriented management status
- expose read refs without redefining approval workflow semantics

### `requirement_overview`

Purpose:

- summarize requirement confirmation state
- expose requirement-oriented read refs without redefining the workflow

### `operational_risk_overview`

Purpose:

- summarize blocked or warning-oriented management concerns
- expose read refs for management visibility

### `drilldown_refs`

Purpose:

- provide safe references into existing operational surfaces
- support future management drilldown without inventing new workflow actions

## 8. Risk Register

The following risks should be treated as primary design concerns.

### New API Contract Risk

- a dedicated management read surface may eventually require a new API
- new API introduction should happen only after the design boundary is explicit

### Existing API Drift Risk

- reusing existing API surfaces is good
- over-expanding `/api/dashboard` or `/api/work-hub-runtime` could create contract drift

### Business Rule Duplication

- the largest design risk is duplicating blocked / schedulable / approval / requirement semantics
- management projection must consume upstream truth rather than recreate it

### Permission Boundary Expansion

- Owner View or management-specific audiences may later pressure permission redesign
- that pressure should not be silently absorbed into this baseline

### Work Hub Frozen Surface Pollution

- Work Hub is already a frozen operational module
- management evolution must not casually turn Work Hub runtime into a general analytics contract

### Future Schema Pressure

- richer KPI and history-oriented management products may later expose schema limits
- this design baseline acknowledges that pressure without solving it here

## 9. Relationship To Existing Surfaces

### Dashboard

Dashboard remains the current aggregation-oriented source.

Management Read Model should be compatible with dashboard read responsibilities, not casually replace them.

### Work Hub Runtime

Work Hub runtime remains the frozen operational aggregation surface for Work Hub UI.

Management Read Model should not be treated as a rename of Work Hub runtime.

### Scheduling

Scheduling remains split into:

- Scheduling Engine
  - decision layer
- Scheduler Persistence
  - fact layer

Management Read Model may project both layers, but must not collapse or redefine them.

## 10. Future Implementation Sequence

Recommended sequence:

1. docs-only design baseline
2. helper-only prototype
3. API baseline
4. UI consumption

### 1. docs-only design baseline

Reason:

- define role, boundary, and non-goals before code exists

### 2. helper-only prototype

Reason:

- validate shape and source reuse without immediately freezing a public contract

### 3. API baseline

Reason:

- expose the read model only after helper shape and duplication risk are understood

### 4. UI consumption

Reason:

- consume the management read model only after contract boundaries are explicit

## 11. M2 And M3 Boundary

### M2

M2 should focus on:

- read-only management projection
- analytics foundation
- management-oriented summary and drilldown support
- safe reuse of frozen operational read sources

### M3 Or Later

The following belong to a later boundary:

- AI
- prediction
- agent behavior
- automation

These future directions should not be smuggled into M2 under the label of management summary or analytics.

## 12. Design Decision

Current recommendation:

- do not jump directly into runtime implementation
- do not introduce a management API before helper shape is understood
- keep the next concrete step design-first and boundary-first

Recommended immediate next slice:

- helper-only prototype planning or design follow-up

This preserves the current Product OS v2 pattern:

- small slices
- read-only first
- no contract drift
- no accidental duplication of frozen workflow or decision semantics
