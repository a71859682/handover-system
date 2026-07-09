# M2-IMP-002C — Management Read Model API Boundary Docs Baseline

## 1. Purpose

This slice defines the docs-only baseline for the future Management Read Model API boundary.

Its purpose is to clarify:

- future API strategy
- public contract boundary
- source mapping
- guardrails
- non-goals
- implementation sequence before any API baseline is implemented

This slice is docs-only.

It does not modify runtime code, frontend code, templates, tests, schema, migration behavior, API behavior, permission behavior, workflow behavior, or write behavior.

## 2. Current Context

Current production baseline:

- commit:
  - `6f59c67`
  - `Add management read model helper prototype baseline`
- current slice:
  - `M2-IMP-002B — Management Read Model Helper Prototype Baseline`
- current status:
  - Production Live
  - Deploy PASS
  - Logs PASS
  - Runtime Health PASS

Current state of Management Read Model:

- docs-only design baseline exists
- helper-only prototype exists
- no API has been added
- no UI consumes Management Read Model directly
- existing API contracts remain unchanged

This means the product now has enough design context and helper groundwork to define the API boundary safely before exposing any public contract.

## 3. API Strategy

### Recommended Direction

Future Management Read Model should prefer a dedicated independent API:

- `GET /api/management-read-model`

This is the recommended public API direction because it gives the management projection layer an independent read boundary.

### Why A Dedicated API Is Preferred

- avoids existing contract drift
- avoids Work Hub frozen surface pollution
- avoids Dashboard surface overload
- keeps management-oriented projection separate from operational presentation
- makes helper evolution easier before public API freeze
- improves testability by isolating contract verification to one API surface

### Why Existing APIs Should Not Be Expanded

The following surfaces should not be used as the public Management Read Model contract:

- `/api/dashboard`
- `/api/work-hub-runtime`

Reasons:

- `/api/dashboard` should remain a dashboard-oriented operational surface
- `/api/work-hub-runtime` is part of a frozen Work Hub read boundary
- expanding either surface would increase contract drift risk
- management projection would become coupled to unrelated frozen consumers
- future analytics evolution would be harder to isolate

### Why Helper-only Internal State Is Not The End Goal

The current helper-only prototype is a correct intermediate step, but it is not the desired final boundary.

Keeping the helper permanently internal-only would:

- delay contract clarification
- leave future consumers without a stable read surface
- encourage ad hoc reuse through unrelated APIs

Therefore:

- helper-only is correct for now
- dedicated API is the recommended next public boundary

## 4. Public Contract Boundary

If a future Management Read Model API is introduced, the following top-level shape is appropriate to expose publicly:

- `management_summary`
- `scheduling_overview`
- `approval_overview`
- `requirement_overview`
- `operational_risk_overview`
- `drilldown_refs`

These sections are appropriate because they express management-facing read concerns without exposing internal implementation details.

### Public Sections

#### `management_summary`

Should contain:

- compact top-line management counts
- read-only summary values derived from existing frozen read sources

Should not contain:

- presentation wording
- ranking semantics
- future KPI scoring

#### `scheduling_overview`

Should contain:

- scheduling-related read-side counts
- scheduling-related read-side references

Should not contain:

- scheduling decision logic
- scheduling action semantics
- scheduling write capability

#### `approval_overview`

Should contain:

- approval-related read-side counts
- approval-related read-side references

Should not contain:

- approval decision semantics
- approval action semantics
- approval write capability

#### `requirement_overview`

Should contain:

- requirement-related read-side counts
- requirement-related read-side references

Should not contain:

- requirement workflow action semantics
- requirement confirmation write capability

#### `operational_risk_overview`

Should contain:

- existing risk-related read-side counts
- existing risk-related read-side references

Should not contain:

- ranking
- scoring
- prediction
- bottleneck winner logic

#### `drilldown_refs`

Should contain:

- static read-side drilldown references
- safe target references for future consumer navigation

Should not contain:

- write action metadata
- workflow mutation intent
- frontend-only affordance metadata

### What Must Not Be Publicly Exposed

The future API should not expose:

- internal helper implementation details
- frontend copy wording
- future-only fields
- incomplete KPI / ranking / prediction fields
- workflow/action fields
- write-intent fields
- UI-only affordance metadata
- prototype debug fields

Interpretation:

- public contract should expose stable read meaning
- internal helper structure should remain refactorable
- incomplete management analytics semantics should stay private until intentionally frozen

## 5. Source Mapping

Each public section must only be projected from existing frozen read sources.

### Allowed Reuse Sources

- `build_dashboard_payload(...)`
- `build_scheduling_payload(...)`
- `/api/dashboard`
- `/api/scheduling`
- scheduling facts
- formal approval state
- requirement status
- vendor work entries

### Mapping Guidance

#### `management_summary`

Should be sourced from:

- existing dashboard summary counts
- existing scheduling summary counts

#### `scheduling_overview`

Should be sourced from:

- existing dashboard scheduled / today-schedule read-side results
- existing scheduling summary counts
- existing scheduling read-side entry refs

#### `approval_overview`

Should be sourced from:

- existing dashboard approval-related counts
- existing approval-related read-side refs

#### `requirement_overview`

Should be sourced from:

- existing dashboard requirement-related counts
- existing requirement-related read-side refs

#### `operational_risk_overview`

Should be sourced from:

- existing blocked-related counts
- existing pending approval counts
- existing pending requirement counts
- existing read-side refs only

#### `drilldown_refs`

Should be sourced from:

- static read-side drilldown target references
- existing operational navigation targets where appropriate

### Rule Ownership Must Stay Upstream

Management Read Model must not re-derive:

- blocked
- schedulable
- scheduled
- formal approval
- requirement workflow
- readiness
- scheduling gate
- priority
- ranking

Management Read Model may project existing truth.

It must not become a second rule engine.

## 6. Guardrails

The following guardrails are mandatory for any future API baseline.

### Same-site Only

- Management Read Model API must remain same-site only in M2.
- It must not introduce cross-site aggregation.

### Read-only Only

- Management Read Model API must be read-only only.
- It must not introduce mutation, workflow action, or write action.

### No Schema Change In API Boundary Baseline

- the API boundary baseline does not require schema change
- future schema pressure may exist, but it is not part of this baseline

### No Permission Change

- existing authorization boundary should be reused
- no permission expansion should be introduced in the API boundary baseline

### No Workflow Or Write Behavior Change

- vendor write behavior remains unchanged
- requirement workflow remains unchanged
- formal approval write behavior remains unchanged
- scheduling write behavior remains unchanged

### No Existing API Contract Drift

- `/api/dashboard` contract must remain unchanged
- `/api/work-hub-runtime` contract must remain unchanged
- `/api/scheduling` contract must remain unchanged

### No Work Hub Runtime Contract Pollution

- Work Hub runtime must not become the transport for management projection
- frozen Work Hub surface must remain operationally scoped

### No Frontend-only Analytics Truth

- analytics semantics must not depend on frontend-only recomposition
- frontend copy must not become the source of management truth

### No AI / Prediction / Ranking Semantics

- no AI summary layer
- no prediction layer
- no ranking layer
- no scoring semantics

### No Mutation / Write Action

- no POST baseline
- no action route
- no workflow mutation path

## 7. Non-goals

This baseline explicitly excludes:

- AI assistant
- prediction
- KPI scoring
- ranking
- automation
- notification
- workflow action
- owner / 工區管理部 permission expansion
- cross-site analytics

These may become future product topics, but they are not part of the Management Read Model API boundary baseline.

## 8. Future Implementation Sequence

Recommended sequence:

1. API boundary docs-only baseline
2. helper refinement before API
3. API implementation baseline
4. UI consumption planning
5. UI consumption baseline

### Why This Sequence Is Preferred

#### 1. API Boundary Docs-only Baseline

First clarify the public contract boundary before exposing any API surface.

This reduces accidental freeze of helper internals.

#### 2. Helper Refinement Before API

Next refine helper naming, section ownership, and field stability if needed.

This should happen before public API freeze.

#### 3. API Implementation Baseline

Only after boundary and helper readiness are clear should the API be added.

#### 4. UI Consumption Planning

After API shape exists, consumer planning can be grounded in a real read boundary.

#### 5. UI Consumption Baseline

UI should come last so that it consumes a stable API rather than driving contract shape prematurely.

## 9. Freeze Criteria Before API Implementation

Before future API implementation begins, the following conditions should be confirmed:

- helper shape stable enough
- no duplicate business rules
- authorization boundary reused
- no existing contract drift
- smoke strategy defined
- fallback / rollback plan clear

### Additional Interpretation

#### Helper Shape Stable Enough

The helper should no longer look like a temporary debug projection.

It should be stable enough to expose meaningful public sections.

#### No Duplicate Business Rules

Public API must not introduce duplicated decision semantics outside upstream read truth.

#### Authorization Boundary Reused

The API should reuse existing same-site authorization expectations.

It should not become a hidden permission redesign.

#### No Existing Contract Drift

The new API must be additive.

Existing operational contracts must remain untouched.

#### Smoke Strategy Defined

API baseline should have explicit smoke coverage for:

- route existence
- same-site authorization boundary
- read-only behavior
- top-level contract shape
- no write side effects
- no existing API regression

#### Fallback / Rollback Plan Clear

If the API baseline needs rollback:

- existing dashboard and Work Hub consumers must remain unaffected
- the new API should be removable without contract damage to frozen surfaces

## 10. Summary

Management Read Model should move toward a dedicated public API boundary.

That public API should:

- be independent
- be read-only
- remain same-site only
- project existing frozen read truth
- avoid contract drift
- avoid Work Hub runtime pollution

The next safe step is not immediate UI work.

The next safe step is:

- preserve this docs baseline
- refine helper shape if needed
- then implement a dedicated API baseline intentionally
