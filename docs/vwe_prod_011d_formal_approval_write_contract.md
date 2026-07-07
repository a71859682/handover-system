# VWE-PROD-011D - Formal Approval Write Contract Planning

## 1. Purpose

This document defines the docs-only write-contract planning baseline for Persistent Formal Approval.

Its purpose is to describe how crew-side formal approval should evolve from the current no-op contract into a persistent write contract, without changing runtime code in this slice.

This slice does not modify application code, static assets, templates, tests, `docs/production_baselines.md`, schema implementation, migration behavior, API implementation, permission behavior, workflow behavior, or write behavior.

## 2. Current Baseline

The current baseline is:

- the `formal_approvals` schema baseline already exists
- `POST /api/crew-work-entry/formal-approve` already exists as a no-op API contract
- the current hard-block guardrail already rejects not-ready entries with `entry_not_ready`
- a successful formal approve response does not yet persist any approval record

This means the system can already:

- validate the formal approve action shape
- enforce readiness through the existing scheduling gate contract
- provide deterministic success vs blocked API behavior

What it does not yet do is:

- create a durable `formal_approvals` row
- detect and classify duplicate persisted approvals
- expose durable formal approval state on read surfaces

## 3. Write Contract

The future persistent write contract should be defined in six stages.

### Request

The request should remain minimal and continue to identify:

- `entry_id`
- `sheet_id`
- `action`

The action should remain fixed to:

- `crew_formal_approve_entry`

The request should not accept client-controlled approval status, actor identity, or timestamps.

Those values should remain server-derived.

### Validation

Validation should confirm:

- `entry_id` is present and resolves to an existing `Vendor Work Entry`
- `sheet_id` is present
- `action` is present
- `action` exactly matches `crew_formal_approve_entry`
- the target entry actually belongs to the requested `sheet_id`

Validation should remain deterministic and should reject malformed or mismatched requests before persistence.

### Authorization

Authorization should continue to follow the existing crew/site-side internal authorization pattern.

The contract should preserve these boundaries:

- vendor cannot formal approve
- missing current site cannot formal approve
- cross-site formal approve is rejected
- sheet mismatch is rejected

This slice does not redesign permission behavior.

It only records that the persistent write contract must continue to honor the existing boundary.

### Gate Check

The gate check should continue to use the existing readiness and scheduling gate derivation.

The decision rule should remain:

- `scheduling_gate_state = allowed` -> eligible for persistence
- `scheduling_gate_state = warning` -> blocked

This keeps the formal approval write contract aligned with the already-frozen Hard Block v1 behavior.

### Persistence

When the request is authorized and the gate check passes, the runtime should create one `formal_approvals` record for the target entry.

The write should be server-owned and should populate:

- `entry_id`
- `sheet_id`
- `action`
- `approval_status`
- `approved_by`
- `approved_at`
- `created_at`
- `updated_at`

The first persistent version should continue to treat one entry as one approval record for the single action `crew_formal_approve_entry`.

### Response

The response should remain compact and deterministic.

Success should confirm:

- the action that was completed
- the entry identity that was approved
- enough approval metadata to support future read and UI integration, if needed

This document does not freeze the full success payload shape yet.

It only records that the persistent version should return a stable success contract after the write commits successfully.

## 4. Persistence Rules

### Allowed path

If the target entry is allowed for formal approval:

- create exactly one `formal_approvals` row
- do not create multiple rows for the same `entry_id` and `action`
- treat approval as an entry-level crew-side operational record

### Blocked path

If the target entry is not ready:

- do not create any `formal_approvals` row
- do not partially write any approval metadata
- preserve current blocked semantics

### Duplicate approve behavior

The product should treat repeated approval attempts against the same `entry_id` and `action` as a duplicate approval condition, not as a second successful approval event.

That means the first persistent version should not:

- create multiple approvals for the same action
- silently overwrite an existing approval record
- reinterpret duplicate approval as an override flow

### UNIQUE conflict strategy

The existing `UNIQUE(entry_id, action)` constraint should be treated as a product guardrail, not only as a database detail.

Recommended strategy:

- pre-check whether the approval already exists
- if it already exists, return a deterministic duplicate-approval failure contract
- still treat the database unique constraint as the final protection against race conditions

If a race still reaches the database constraint, the runtime should map that uniqueness violation to the same deterministic duplicate-approval contract.

## 5. Failure Contract

The persistent write contract should preserve deterministic failure categories.

### `entry_not_ready`

Use when:

- the target entry fails the readiness / scheduling gate check

Meaning:

- the formal action requires Entry Ready
- persistence must not occur

### `duplicate_approval`

Use when:

- a `formal_approvals` row already exists for the same `entry_id` and `action`

Meaning:

- the first persistent approval already happened
- the new request is not allowed to create another record

### `forbidden`

Use when:

- the actor is not allowed to perform crew-side formal approval

This includes vendor-authenticated requests and other non-authorized identities.

### `sheet_mismatch`

Use when:

- the requested `sheet_id` does not match the entry's actual `sheet_id`

### `entry_not_found`

Use when:

- the requested `entry_id` does not resolve to a target record in scope

This failure should remain deterministic and should not leak unrelated state.

## 6. Transaction Boundary

The future persistent implementation should treat the following steps as one transaction:

1. resolve the target entry
2. validate sheet ownership and authorization boundary
3. perform the gate check
4. confirm duplicate-approval absence
5. insert the `formal_approvals` row
6. build the final success outcome from the committed write result

The transaction should commit only after the persistence step succeeds.

Rollback principle:

- if any validation, authorization, gate, duplicate, or insert step fails, the transaction should roll back
- blocked and failed requests must not leave partial approval rows
- duplicate detection and insert should be transactionally aligned so the product stays deterministic under concurrent attempts

The first persistent version should keep the transaction boundary narrow and local to the formal approve write path.

## 7. Out-of-Scope

The following are explicitly out of scope for this slice:

- UI
- override
- notification
- audit log
- scheduling engine

Also out of scope:

- runtime implementation details
- final read-contract shape
- production rollout steps
- approval revocation
- returned / rejected lifecycle design

## 8. Proposed Next Slices

Recommended next slices:

- `011E` Runtime Write Implementation
- `011F` Crew Read Contract Extension
- `011G` UI Integration
- `011H` Guardrail Freeze
- `011I` Production Baseline

Suggested sequence:

1. implement the persistent formal approval write path
2. extend crew read surfaces to expose durable approval state
3. connect the UI to the persisted approval result
4. freeze guardrails for duplicate, blocked, and success behavior
5. consolidate the resulting production baseline
