# VWE-PROD-010C - Hard Block Contract Planning

## 1. Purpose

This document defines the docs-only contract planning baseline for the first Scheduling Hard Block implementation slice.

Its purpose is to decide which crew-side formal write boundary should receive the first hard-block enforcement and to define the minimal contract for that future write path.

This slice does not modify application code, static assets, templates, tests, schema, API behavior, permission behavior, workflow behavior, or write behavior.

## 2. Current Baseline

The current baseline is:

- `Vendor Work Entry Product Baseline v1` is complete, released, and production live.
- Scheduling Gate v1 is warning-only.
- `readiness_state` / `readiness_reason` are already exposed on the crew-side read surface.
- `scheduling_gate_state` / `scheduling_gate_reason` are already exposed on the crew-side read surface.
- Crew-side UI can already display readiness and scheduling-gate signals.
- Vendor submit is not blocked.
- Requirement confirmation is not blocked.
- No current crew-side formal action is yet enforced by hard-block semantics.

This means v1 already provides the read-side signal required for future enforcement, but it does not yet define the enforcement write boundary.

## 3. Candidate Write Paths

The current relevant write-path landscape is:

### Existing VWE-related write paths

- `/api/vendor-work-entry`
  - vendor-side create / update path
  - not suitable for first hard block
  - reason: hard block must not stop vendor authoring, vendor submit, or requirement entry

- `/api/crew-work-entry-requirement-confirm`
  - crew/site-side requirement confirmation path
  - not suitable for first hard block
  - reason: requirement confirmation is the action needed to resolve not-ready state, so blocking it would trap the workflow

- `POST /api/vendor/work-entry/preflight`
  - vendor-side read-adjacent preflight surface
  - not suitable for first hard block
  - reason: it is not the crew-side formal action boundary and should remain write-adjacent context preparation

### Existing non-VWE site/admin write paths

- `/api/progress`
- `/api/unit-extra`
- `/api/reset-sheet`
- `/admin/table` `POST`

These are not suitable first hard-block targets because:

- they are broader site/admin content-management paths
- they are not entry-level Vendor Work Entry formal-action boundaries
- they would couple hard block to unrelated write domains

### Suitable target shape

The suitable first target is:

- a dedicated crew/site-side formal write path
- scoped to one `Vendor Work Entry`
- invoked only when the operator tries to complete an action that requires Entry Ready

This target does not exist as a stable public contract in v1 and should be introduced explicitly rather than inferred from unrelated write paths.

## 4. Recommended First Hard Block Target

The recommended first hard-block target is:

- a new dedicated crew-side formal-action write path for entry-level scheduling completion or entry approval semantics

Why this is the best first target:

- it matches the v2 design direction from `VWE-PROD-010B`
- it preserves vendor authoring flow
- it preserves requirement confirmation flow
- it keeps enforcement aligned with the entry-level identity boundary
- it avoids overloading unrelated existing endpoints
- it provides a clean contract for future guardrails, UI, and eventual override policy

Recommended target characteristics:

- one request acts on one `Vendor Work Entry`
- the action is crew-side only
- the action represents a formal operational decision that requires Entry Ready
- the action rejects `scheduling_gate_state = warning`
- the action allows `scheduling_gate_state = allowed`

## 5. Request / Response Contract

The first hard-block contract should stay minimal.

### Request

Recommended minimal request shape:

- `entry_id`
- `sheet_id`
- `action`

Recommended semantics:

- `entry_id`
  - identifies the single `Vendor Work Entry` being acted on

- `sheet_id`
  - preserves sheet-scoped validation context

- `action`
  - identifies the crew-side formal action being attempted
  - should remain narrow and deterministic in the first phase

Example shape:

```json
{
  "entry_id": 123,
  "sheet_id": 1,
  "action": "schedule_confirm"
}
```

This example is illustrative only.

The final action name should be locked when the actual write path is introduced.

### Success Response

Recommended success shape:

- `ok: true`
- `entry`
- `action`

Recommended semantics:

- keep the success contract narrow
- return the acted-on entry identity
- return resulting action status only as needed by the write path

Example shape:

```json
{
  "ok": true,
  "action": "schedule_confirm",
  "entry": {
    "id": 123
  }
}
```

## 6. Error Contract

The first hard-block phase should use a deterministic error contract.

Recommended error code:

- `entry_not_ready`

Recommended error message:

- `Entry is not ready for this action.`

Recommended failure shape:

```json
{
  "ok": false,
  "error": {
    "code": "entry_not_ready",
    "message": "Entry is not ready for this action."
  }
}
```

Recommended error semantics:

- return the same error contract whenever the targeted formal action requires Entry Ready and the entry resolves to blocked state
- keep the first phase minimal
- do not add override metadata in this phase
- do not add rejected / returned semantics in this phase

## 7. Out-of-Scope

The following remain out of scope for this contract-planning slice:

- override
- rejected / returned flow
- notification
- audit log
- full scheduling engine

Also out of scope:

- schema / migration
- runtime API implementation
- UI implementation
- permission rewrite
- workflow redesign

## 8. Proposed Next Slice

The next slice should be:

- `VWE-PROD-010D - Hard Block API / Write Guardrail`

Its purpose should be:

- lock the chosen write boundary
- implement deterministic `entry_not_ready` guardrail behavior
- ensure vendor submit and requirement confirmation remain outside hard-block enforcement
