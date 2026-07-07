# VWE-PROD-011A - Persistent Formal Approval Design Baseline

## 1. Purpose

This document defines the docs-only design baseline for Persistent Formal Approval.

Its purpose is to establish the first product-design baseline for evolving Hard Block v1 from a no-op formal-approve contract into a persistent formal-approval model.

This slice does not modify application code, static assets, templates, tests, schema, migration behavior, API behavior, permission behavior, workflow behavior, or write behavior.

## 2. Current Baseline

The current baseline is:

- `Vendor Work Entry Product Baseline v1` is Production Live.
- `Hard Block v1` is Production Live.
- crew-side formal approve currently exists as a no-op API contract.
- crew-side formal approve already has a blocking runtime guardrail through `entry_not_ready`.
- crew-side UI already provides formal approve success / blocked feedback.
- there is not yet any persisted formal approval state.

This means the current product can:

- evaluate whether a crew-side formal action is allowed
- reject not-ready entries deterministically
- provide crew-side feedback for allowed vs blocked attempts

What it cannot yet do is:

- remember that a formal approval has happened
- expose a persisted formal approval state on the read side
- drive downstream product behavior from a durable formal approval record

## 3. Problem Statement

Persistent Formal Approval is needed because the current no-op model only proves contract shape and hard-block semantics.

The current no-op model is intentionally limited:

- a successful formal approve call does not persist any state
- a later read cannot distinguish between never-approved and previously-approved entries
- there is no durable product boundary that downstream features can depend on

This creates three product limitations:

- crew cannot rely on a stored formal approval outcome across sessions
- future read surfaces cannot truthfully show approved vs not-approved operational state
- future Scheduling Engine work has no durable approval signal to consume

In other words, Hard Block v1 proved the blocking boundary, but not the lifecycle state beyond that boundary.

## 4. Product Semantics

### What is Formal Approval

Formal Approval is the first durable crew-side operational approval for a single `Vendor Work Entry`.

It represents that the entry has crossed the formal action boundary that requires Entry Ready.

It is not:

- a vendor-authored state
- a whole-vendor approval
- a same-day aggregate approval
- a scheduling engine implementation by itself

### Who can create it

The creator should remain a crew/site-side actor operating through the formal approve boundary.

Vendor cannot create formal approval.

### Whether it can be revoked

The first persistent version should not support revocation.

Revocation introduces separate policy questions:

- who can revoke
- whether revocation is audited
- whether downstream scheduling effects must be rolled back

Those questions should be deferred to a future slice.

### Entry-to-approval relationship

The first persistent version should keep a one-entry-to-one-formal-approval model.

That means:

- one `Vendor Work Entry`
- one corresponding formal approval record or persisted approval state

This keeps the persistent model aligned with the existing entry-level identity model already established by requirement, readiness, scheduling gate, and hard-block behavior.

## 5. Candidate Persistence Models

Two minimal persistence directions are candidates.

### A. Extend `vendor_work_entries`

Example direction:

- add formal-approval fields directly to `vendor_work_entries`
- possible future fields could include:
  - formal approval state
  - approved by
  - approved at

Advantages:

- keeps all entry lifecycle state on the existing primary entry row
- crew read contract can remain row-local and straightforward
- simpler for single-entry read paths
- avoids a new join table in the first persistence phase

Risks / disadvantages:

- keeps expanding `vendor_work_entries` into a broad lifecycle container
- may become harder to separate authoring state from operational approval state
- can become less flexible if future approval history or multi-event approval semantics are needed

### B. Add a separate `formal_approvals`

Example direction:

- create a dedicated formal-approval persistence model
- tie each record to one `Vendor Work Entry`

Advantages:

- keeps formal approval as an explicit operational domain object
- separates entry authoring from crew operational approval
- leaves more room for future lifecycle growth such as history, policy, or event-oriented evolution

Risks / disadvantages:

- introduces another persistence surface and read-path join requirement
- may add more implementation complexity for the first persistent phase
- requires clearer uniqueness rules to preserve the intended one-entry-to-one-approval model

This slice intentionally compares the models without deciding implementation.

The persistence decision should be made in a dedicated schema-baseline slice.

## 6. State Model Evolution

The current conceptual state model already includes:

- `draft`
- `submitted`
- `requirement_pending`
- `ready`
- `blocked`
- `formally_approved` as a product concept

Today, `formally_approved` is only conceptual.

It is not yet a persisted runtime state.

The intended evolution is:

1. keep the existing concept-level state model
2. introduce a persistent representation for formal approval
3. extend read surfaces so `formally_approved` can be observed durably
4. allow future downstream products to depend on that durable approval state

This evolution should preserve two principles:

- entry identity remains entry-level
- formal approval remains a crew-side operational state, not a vendor authoring state

## 7. API Impact

Persistent Formal Approval will likely affect at least two surfaces in a future implementation phase.

### `POST /api/crew-work-entry/formal-approve`

Future likely impact:

- success path would no longer be pure no-op
- success path would need to persist formal approval
- repeated approval behavior would need a deterministic contract

### `/api/crew-forms`

Future likely impact:

- crew read payload may need to expose durable formal approval state
- crew read payload may need to distinguish:
  - ready but not formally approved
  - formally approved

This slice does not modify API behavior.

It only records that these future API surfaces will need explicit planning.

## 8. Out-of-Scope

The following are explicitly out of scope for this slice:

- schema implementation
- migration
- runtime API changes
- UI implementation
- override
- rejected / returned
- notification
- audit log
- scheduling engine
- permission redesign

Also out of scope:

- persistence model selection
- downstream deployment planning
- production rollout mechanics

## 9. Proposed Next Slices

Recommended next slices:

- `011B` Persistence Schema Baseline
- `011C` Formal Approval Write Contract
- `011D` Crew Read Contract Extension
- `011E` UI Integration
- `011F` Guardrail Freeze
- `011G` Production Baseline

Suggested sequence:

1. decide the persistence schema direction
2. define the formal approval write contract
3. extend crew read surfaces for durable approval state
4. connect the UI to the persisted state
5. freeze guardrails
6. consolidate the production baseline
