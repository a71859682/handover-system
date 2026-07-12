# CORE-USE-003C — Formal Approval Cancellation Design Baseline

## Status and scope

This document freezes the product and delivery boundaries for **Formal Entry Approval Cancellation** (Type 1; 中文：**取消今日進場核准**). CORE-USE-003C is documentation-only: it introduces no schema, API, UI, permission, workflow, runtime, or data change.

The cancellation workflow is domain-specific. It must not be generalized into a shared governance, audit, or workflow framework in this slice family.

CORE-USE-003* is Type 1 only: it cancels the `formal_approvals` fact whose action is `crew_formal_approve_entry`. It does not cancel, reset, or otherwise alter pre-entry requirement confirmation. **Pre-entry Requirement Confirmation Cancellation** (Type 2; 中文：**取消進場前需求確認**) is a separate domain frozen in [CORE-USE-004A](core_use_004a_requirement_confirmation_cancellation_design_baseline.md). The two domains must not share an endpoint, action code, button, status, metadata, event table, read projection, or runtime-verification slice.

## Frozen product decisions

1. Cancellation uses an independent **Cancel formal entry approval** / **取消今日進場核准** action. The existing approval button must never act as a toggle.
2. A cancellation never deletes the `formal_approvals` row.
3. `formal_approvals` remains the canonical current-state record. A new append-only `formal_approval_events` table records lifecycle evidence for this domain.
4. Cancellation metadata is `cancelled_by`, `cancelled_at`, and `cancellation_reason`.
5. The cancellation reason is trimmed, required, must contain a non-whitespace character, and is limited to 500 characters.
6. The original `approved_by` and `approved_at` values are immutable after approval.
7. Reapproval is not supported before CORE-USE-003H.
8. A member may cancel only an approval that the same member originally created.
9. A global admin may cancel any approval in the valid current-site scope.
10. Admin cancellation uses the same two-step confirmation and required-reason interaction as member cancellation.
11. Vendor and unauthenticated actors are forbidden.
12. If any `scheduling_entries` row exists for the entry, cancellation fails closed with HTTP 409 and `approval_has_schedule`.
13. Cancellation never automatically deletes, cancels, or mutates scheduling data.
14. Requirement confirmation fields and vendor-entry business content remain unchanged.
15. A cancelled approval is not schedulable.
16. Read models expose a distinct `cancelled` formal-approval state, cancellation metadata, and a canonical reason such as `formal_approval_cancelled`.
17. Management projections distinguish cancelled approvals from requirement-pending and never-approved entries.
18. The previously planned approved-state renderer guard and post-success duplicate-window guard move into CORE-USE-003F.

## Canonical current state

The existing `formal_approvals` row remains the authoritative current state for an entry and action. Its lifecycle is:

```text
approved -> cancelled
```

There is no cancelled-to-approved transition before CORE-USE-003H. The row is retained and its approval identity and time remain immutable. Cancellation updates only the approved row's current status and cancellation metadata, subject to the later schema and API slices.

At most one canonical row continues to exist for the existing `(entry_id, action)` uniqueness boundary. Cancellation must not create a second canonical approval row.

## Append-only lifecycle evidence

`formal_approval_events` is an append-only, domain-specific event ledger. It records at least the approval identity, entry, sheet, action, lifecycle event, actor, event time, sequence, and cancellation reason when applicable. Exact column definitions and constraints belong to CORE-USE-003D.

Events are immutable after insertion. Application flows must not update or delete event rows. Event sequence is monotonic within the approval lifecycle and must be protected by a database uniqueness boundary defined in CORE-USE-003D.

### No automatic backfill

CORE-USE-003D must not auto-backfill events for existing approvals during bootstrap, application startup, migration, or deploy. Existing `approved` rows remain valid canonical facts even when no corresponding event exists.

After event integration:

- A new approval writes the canonical approval row and its `approved` event in the same transaction.
- On the first cancellation of a legacy approval with no `approved` event, the transaction first appends sequence 1 `approved`, derived from the immutable canonical `approved_by` and `approved_at`, and then appends sequence 2 `cancelled`.
- If the `approved` event already exists, it is not duplicated; cancellation appends only the next `cancelled` event.
- The canonical state update and all required event inserts succeed or roll back together.

This is on-demand lifecycle completion for the single approval being acted upon, not a full-database backfill.

## Authorization and scope boundaries

Cancellation authorization must re-read the internal actor, current site, sheet, entry, approval, and schedule facts from canonical storage within the request flow.

- The current-site context must be valid.
- The sheet must belong to the current site.
- The entry and approval must belong to the trusted sheet.
- A member's canonical identity must equal the immutable original approver identity.
- A global admin is exempt only from the same-approver rule, not from current-site isolation.
- Mixed, vendor, stale, forged, and unauthenticated actor states remain rejected under their existing contracts.

Client-supplied actor, site, vendor, approver, status, or timestamp values are never trusted.

## Scheduling fail-closed boundary

Before any cancellation write, the API must test for any scheduling row associated with the target entry. Existence of one or more rows produces:

```text
HTTP 409
error.code = approval_has_schedule
```

That rejected path performs no application-table write. Cancellation must not attempt to infer whether a scheduling row is active, historical, or reversible; row existence is the frozen fail-closed boundary.

## Transaction and conflict semantics

The cancellation API slice must use one SQLite transaction that:

1. revalidates actor, current site, ownership, approval state, and absence of scheduling rows;
2. conditionally updates the exact canonical approval from `approved` to `cancelled`;
3. verifies the affected row count is exactly one;
4. appends the required lifecycle event or events; and
5. commits only after every operation succeeds.

Any authorization failure, stale state, duplicate cancellation, schedule race, update conflict, event conflict, constraint failure, or exception rolls back the entire transaction. Rejected paths require full application-table logical-manifest no-write evidence.

## Read projection semantics

Canonical projection rules are:

| Canonical approval row | Formal approval projection |
| --- | --- |
| No row | `pending` |
| `approval_status=approved` | `approved` |
| `approval_status=cancelled` | `cancelled` |

For a cancelled approval:

- Requirement readiness may remain `ready` because requirement confirmation is unchanged.
- The requirement-derived scheduling gate may remain `allowed`.
- The formal-approval gate fails with the canonical reason `formal_approval_cancelled`.
- The entry is not schedulable and cannot be scheduled.
- Management and Work Hub expose independent cancelled facts, counts, and classification.
- The entry must not be folded back into requirement-pending or ordinary never-approved classifications.

If the required Management response expansion makes CORE-USE-003E2 too broad, its Management-specific part must be split into a separately reviewed E2 follow-up rather than expanding write or UI scope.

## UI contract reserved for CORE-USE-003F

The UI must ultimately render these distinct action states:

| State | Approval action | Cancellation action | Read-only state |
| --- | --- | --- | --- |
| Pending and eligible | One approval button | None | Pending metadata |
| Approved and cancellable | None | Independent **取消今日進場核准** button | Original approval metadata |
| Approved with any schedule row | None | No actionable cancellation | Approval and schedule-blocked cancellation state |
| Cancelled | None | None | Original approval plus cancellation metadata and reason |

Cancellation requires a two-step confirmation and a valid reason. Approval success must immediately close the duplicate-action window before canonical refresh; a refresh failure must never re-enable the successfully used approval button. Rejected or network-failed approval attempts retain the existing retry behavior and must not be presented as approved.

## Delivery slices

### CORE-USE-003C — Design freeze

- Documentation only.
- No runtime or data change.

### CORE-USE-003D — Schema only

- Add nullable cancellation columns to `formal_approvals`.
- Add `formal_approval_events` with lifecycle constraints, uniqueness boundaries, and indexes.
- Add idempotent ensure/migration behavior and temporary-database schema smoke coverage.
- Do not backfill event rows for existing approvals.
- No API, UI, read-projection, or live cancellation behavior.

### CORE-USE-003E1 — Cancellation write API

- Implement internal actor, permission, current-site, sheet, entry, and approval ownership checks.
- Enforce schedule-existence fail-closed behavior.
- Implement conditional current-state update, exact row-count handling, legacy on-demand event completion, and append-only cancelled event in one transaction.
- Prove rejected-path full-manifest no-write behavior.
- No UI and no read-projection expansion.

### CORE-USE-003E2 — Read projections

- Project pending, approved, and cancelled states and cancellation metadata.
- Update Management, Work Hub, and scheduling classification without writes.
- Split Management response expansion into a separately reviewed follow-up if this slice cannot remain minimal.

### CORE-USE-003F — UI action state and cancellation UX

- Render pending approval, approved cancellation, and cancelled history states from canonical facts.
- Add the independent cancellation action, two-step confirmation, and required reason.
- Include the CORE-USE-003B approved-state renderer guard and immediate post-success duplicate-window guard.
- Use behavioral Node coverage for render and handler state, including refresh failure.
- No DEV data mutation in implementation verification.

### CORE-USE-003G — Single DEV runtime verification

- Perform one authorized, permanent `approved -> cancelled` mutation on the designated DEV synthetic entry.
- Capture pre/post full manifests, events, projections, cross-site non-leakage, and absence of scheduling side effects.
- Do not retry, reverse, delete, or recreate the approval.

### CORE-USE-003H — Future reapproval design

- Reapproval remains unsupported until a separate design, event, authorization, and UI contract is reviewed and approved.

## Must-not-change boundaries

Until its dedicated slice is approved, this design does not authorize:

- direct SQL mutation or manual cleanup;
- approval-row deletion;
- automatic schedule mutation;
- requirement, vendor-entry, permission, or current-site model changes;
- schema, API, read model, or UI work outside the listed slice;
- generalized workflow/audit infrastructure;
- Production data mutation or authenticated Production runtime testing;
- event backfill during deploy or startup; or
- reapproval.

This baseline does not authorize Type 2 requirement-confirmation cancellation. Until CORE-USE-004* is implemented, a confirmed requirement cannot be cancelled through the product.

## Acceptance baseline

Each implementation slice must preserve current-site isolation, structured errors, transaction rollback, full rejected-path no-write evidence, disposable SQLite testing, repository database non-change, sensitive-output safety, and existing authenticated vendor and internal-member contracts. No slice may silently broaden the next slice's authorized files or runtime mutation scope.
