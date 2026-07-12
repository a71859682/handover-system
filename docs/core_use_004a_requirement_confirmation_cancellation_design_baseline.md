# CORE-USE-004A — Requirement Confirmation Cancellation Design Baseline

## Status and Production baseline

This document freezes the product and delivery boundaries for **Pre-entry Requirement Confirmation Cancellation** (Type 2; 中文：**取消進場前需求確認**). CORE-USE-004A is documentation-only and introduces no schema, API, UI, permission, runtime, or data change.

The baseline at this freeze is:

```text
Production/main: d9fa1f16865476c7b94da44456262218d1427809
```

Production already contains the Type 1 cancellation schema (`formal_approvals` cancellation metadata and `formal_approval_events`) with no event backfill. It also contains the extra-field startup no-op guardrail. Controlled Production deployment preserved canonical application manifests and existing sequences. Type 1 cancellation API, projection, and UI remain unimplemented. Every Type 2 capability remains unimplemented.

## Independent cancellation domains

| Type | Chinese | Canonical English | Roadmap | Cancelled fact |
| --- | --- | --- | --- | --- |
| 1 | 取消今日進場核准 | Formal Entry Approval Cancellation | CORE-USE-003* | `formal_approvals.action=crew_formal_approve_entry` |
| 2 | 取消進場前需求確認 | Pre-entry Requirement Confirmation Cancellation | CORE-USE-004* | `vendor_work_entries` requirement-confirmation state |

The domains must not share an endpoint, action code, button, status, metadata, event table, read projection, or runtime-verification slice. Type 2 must never write `formal_approval_events`, and Type 1 must never alter requirement-confirmation state.

## Frozen current-state lifecycle

The Type 2 lifecycle is:

```text
pending -> confirmed -> cancelled
```

Cancellation persists the literal value:

```text
requirement_status=cancelled
```

It must not collapse a cancelled confirmation into ordinary `pending`. The current-state row gains nullable metadata:

```text
requirement_cancelled_by TEXT
requirement_cancelled_at TEXT
requirement_cancellation_reason TEXT
```

The immutable original confirmation evidence remains populated:

```text
requirement_confirmed_by
requirement_confirmed_at
```

Cancellation must never clear or overwrite those fields. The cancellation reason is trimmed, required, must contain a non-whitespace character, and is limited to 500 characters.

Timestamps use SQLite `CURRENT_TIMESTAMP`: UTC `YYYY-MM-DD HH:MM:SS` without a timezone suffix. The current-state update and lifecycle events use one transaction-time semantic.

CORE-USE-004A through CORE-USE-004F do not support re-confirmation. A cancelled requirement remains cancelled. Re-confirmation, if approved later, belongs to CORE-USE-004G and must not use a toggle button.

## Authorization

Every cancellation re-reads the internal actor, current site, site permission, sheet, entry, confirmation, formal approval, and scheduling facts from canonical SQLite storage.

- Vendor and unauthenticated actors are forbidden.
- An internal member may cancel only a requirement confirmation originally completed by that same member.
- A global admin may cancel a confirmation completed by another member only inside a valid current-site scope.
- Admin remains subject to current-site isolation and site permission.
- Admin must provide a reason and complete the same two-step confirmation interaction.
- Client-supplied actor, confirmer, site, status, or timestamp values are never trusted.

## Dependency and reverse-order rules

The only safe reverse order is:

```text
cancel scheduling
-> cancel formal entry approval
-> cancel pre-entry requirement confirmation
```

There is no automatic cascade.

1. If any matching `scheduling_entries` row exists, Type 2 cancellation fails closed with HTTP 409 and `requirement_has_schedule`. Version 1 does not distinguish active from historical scheduling rows and never deletes or updates scheduling data.
2. If the current formal approval remains `approved`, Type 2 cancellation fails closed with HTTP 409 and `requirement_has_formal_approval`.
3. Requirement cancellation is eligible only when there is no matching scheduling row and the formal entry approval is not approved.
4. Cancelling a formal entry approval leaves the requirement confirmed.
5. Cancelling a requirement makes readiness not ready, the scheduling gate not allowed, and the entry not schedulable.

All dependency rejections are no-write paths.

## Append-only lifecycle evidence

Type 2 uses its own append-only table:

```sql
CREATE TABLE requirement_confirmation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL,
    sheet_id INTEGER NOT NULL,
    event_sequence INTEGER NOT NULL CHECK (event_sequence > 0),
    event_type TEXT NOT NULL,
    actor_username TEXT,
    reason TEXT,
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (entry_id) REFERENCES vendor_work_entries(id),
    FOREIGN KEY (sheet_id) REFERENCES sheets(id),
    UNIQUE (entry_id, event_sequence)
);
```

The only separately planned index is:

```sql
CREATE INDEX ... ON requirement_confirmation_events (sheet_id, occurred_at);
```

The unique `(entry_id, event_sequence)` boundary already supplies an entry-leading index. The design does not add an event-type check, reason-length check, cascade behavior, PostgreSQL mirror, or dual-write path.

Events are immutable. Application flows do not update or delete event rows.

### No automatic backfill

CORE-USE-004B must not add events, rewrite status, or alter existing sequences during bootstrap, startup, migration, or deployment.

On the first valid cancellation of a legacy confirmed entry with no confirmed event, one transaction:

1. appends sequence 1 `confirmed`, derived from the preserved `requirement_confirmed_by` and `requirement_confirmed_at`;
2. appends sequence 2 `cancelled` with the cancelling actor, reason, and transaction timestamp;
3. updates the canonical requirement state and cancellation metadata; and
4. commits only if every operation succeeds.

If the confirmed event already exists, it is not duplicated. This is **on-demand lifecycle completion** for one target entry, not full-database backfill.

## Candidate write API contract

Reserved endpoint:

```http
POST /api/crew-work-entry/requirement-confirmation-cancel
Content-Type: application/json
```

Request:

```json
{
  "entry_id": 1,
  "sheet_id": 3,
  "action": "crew_cancel_requirement_confirmation",
  "reason": "需求尚未完成，先取消確認"
}
```

The success response exposes only non-sensitive canonical cancellation facts. The write slice must use a conditional update, require an affected row count of exactly one, append lifecycle evidence in the same transaction, and roll back on any error.

Frozen error taxonomy:

```text
400 invalid_request
400 invalid_cancellation_reason
403 auth_required
403 vendor_auth_forbidden
403 site_context_invalid
403 site_permission_missing
403 write_target_not_in_current_site
403 requirement_cancel_forbidden
404 sheet_not_found
404 entry_not_found
409 sheet_mismatch
409 requirement_not_confirmed
409 requirement_already_cancelled
409 requirement_has_formal_approval
409 requirement_has_schedule
409 write_conflict
```

Rejected paths return structured JSON, disclose no cross-site entry facts, and require full application-table logical-manifest no-write evidence.

## Race and idempotency semantics

The transaction must revalidate current-site authorization, original confirmer ownership, requirement state, formal approval state, scheduling-row absence, and event sequence immediately before writing.

- A conditional update succeeds only from effective `confirmed` and uncancelled state.
- An affected row count other than one returns `409 write_conflict`.
- A duplicate request after successful cancellation returns `409 requirement_already_cancelled`; it is not treated as success and appends no event.
- A schedule or formal approval created after an earlier read causes the transaction-time guard to reject and roll back.
- Snapshot update and required event inserts commit or roll back together.

## Read projection contract reserved for CORE-USE-004D

| Current state | Readiness | Scheduling gate | Schedulable |
| --- | --- | --- | --- |
| `pending` | Not ready | Not allowed | No |
| `confirmed` | Derived by existing rules | Derived by existing rules | Requires separate formal approval |
| `cancelled` | Not ready | Not allowed | No |

Cancelled is an independent lifecycle fact. It must not project as ordinary pending. Read models expose original confirmation metadata, cancellation metadata and reason, and a canonical cancellation reason without leaking those facts cross-site.

## UI contract reserved for CORE-USE-004E

| Requirement | Formal approval | Schedule | Requirement action |
| --- | --- | --- | --- |
| Pending | None | None | No cancellation action |
| Confirmed | None or cancelled | None | Independent **取消需求確認** button |
| Confirmed | Approved | None | Read-only: **請先取消今日進場核准** |
| Confirmed | Any | Exists | Read-only: **請先取消排程** |
| Cancelled | Not approved | None | Show **需求確認已取消** and complete lifecycle metadata |
| Cancelled | Approved or scheduled | Any | Invalid combination; no action |

The cancellation button uses a danger style, a two-step confirmation, and a required reason. Only HTTP success with `ok=true` closes the action permanently. Success immediately removes or permanently disables the old action and then reloads canonical data. Refresh failure must not re-enable a successfully used action. Rejected and network-failed requests retain retry behavior and must not be rendered as cancelled.

## Delivery slices

### CORE-USE-004A — Design Freeze

- Documentation only.
- No runtime or data change.

### CORE-USE-004B — Schema Baseline

- Add nullable requirement cancellation metadata.
- Add `requirement_confirmation_events` and its approved constraints and index.
- No event backfill, API, projection, UI, or runtime cancellation.

### CORE-USE-004C — Write API

- Implement authorization, dependency checks, conditional current-state update, on-demand lifecycle completion, event append, rollback, and rejected-path no-write evidence.
- No projection or UI expansion.

### CORE-USE-004D — Read Projection

- Project cancelled lifecycle, readiness, scheduling gate, and management/work-hub facts without writes.

### CORE-USE-004E — UI Wiring

- Add the independent cancellation action, reason dialog, immediate post-success guard, canonical reload, and read-only dependency messages.

### CORE-USE-004F — DEV Runtime Verification

- Perform at most one separately approved, permanent DEV cancellation after all earlier slices pass.
- Do not retry, reverse, delete, or recreate the entry.

### CORE-USE-004G — Future Re-confirmation Design

- Re-confirmation remains unsupported until its state, event, authorization, dependency, and UI contracts are separately reviewed.

## Must-not-change boundaries

This design does not authorize:

- schema, migration, API, read-model, UI, test, or runtime implementation;
- direct SQL mutation or manual cleanup;
- clearing original confirmation evidence;
- automatic cancellation or deletion of formal approval or scheduling facts;
- PostgreSQL schema, mirror, or dual-write work;
- generalized workflow or audit infrastructure;
- Production authenticated testing or application-data mutation;
- deployment-time event backfill or status normalization; or
- re-confirmation.

Every implementation slice must preserve current-site isolation, structured errors, transaction rollback, full rejected-path no-write evidence, disposable SQLite testing, repository database non-change, and sensitive-output safety.
