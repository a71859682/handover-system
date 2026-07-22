# VENDOR-ID-004A Controlled vendor identity backfill operational gate design baseline

| Metadata key | Frozen value |
|---|---|
| Slice ID | `VENDOR-ID-004A` |
| Canonical title | `Controlled vendor identity backfill operational gate design baseline` |
| Canonical path | `docs/vendor_id_004_controlled_vendor_identity_backfill_operational_gate_baseline.md` |
| Status | `DOCS-ONLY OPERATIONAL GATE DESIGN / BACKFILL NOT AUTHORIZED` |
| Governing baselines | `VENDOR-ID-001`; `VENDOR-ID-002`; `VENDOR-ID-003` |
| Baseline commit | `1e2d013018ebe2dde1f70423d960cacb30c475bc` |
| Runtime authority | Legacy `vendor_name` / `vendor_accounts` behavior remains authoritative |
| Deferred-owner boundary | Discovery implementation, evidence production, mapping approval, apply capability, reconciliation, runtime consumers, and authority switching remain separate future slices |

## 1. Status and decision

### 1.1 Baseline decision

The VENDOR-ID-004 readiness inventory is accepted as `PASS` for the purpose of
defining this design slice. That result means only that the repository state is
understood well enough to freeze operational gates. It is not an authorization
to discover, classify live data, create mappings, or write data.

The frozen current status is:

| Capability | Current status | Consequence |
|---|---|---|
| Physical SQLite DDL projection | `IMPLEMENTED / FROZEN` | The exact four-table and fifteen-explicit-index source projection exists. |
| Static schema policy guard | `IMPLEMENTED / FROZEN` | Static source readiness is guarded; persistent contents are not thereby proven. |
| Static discovery policy guard | `IMPLEMENTED / FROZEN` | Absence-first and fail-closed source boundaries are guarded. |
| Canonical vendor discovery | `NOT IMPLEMENTED` | No discovery evidence can yet be produced. |
| Reviewed vendor mappings | `MISSING` | No candidate or mapping is approved. |
| Controlled apply capability | `NOT IMPLEMENTED` | No backfill command or write path is authorized. |
| Runtime authority switch | `NOT IMPLEMENTED / NOT AUTHORIZED` | Legacy authority remains unchanged. |

### 1.2 Non-equivalence decision

The following capabilities are permanently distinct:

```text
physical DDL readiness
!= static policy readiness
!= discovery implementation
!= reviewed discovery evidence
!= approved mapping package
!= apply capability
!= reconciled operation
!= runtime authority switch
```

Physical schema readiness does not establish data readiness. A healthy DEV or
Production deployment does not establish persistent row contents, candidate
mappings, approved mappings, or backfill need. Successful future backfill would
not itself authorize or perform a runtime authority switch.

### 1.3 This slice's decision

VENDOR-ID-004A is a docs-only operational gate design. It freezes the evidence,
authorization, separation-of-duties, write-freeze, idempotency, abort, recovery,
audit, and reconciliation conditions that later slices must satisfy.

It creates no executable capability and authorizes no backfill.

## 2. Scope and non-goals

### 2.1 In scope

This document defines only:

- logical roles and separation of duties;
- the minimum discovery-evidence envelope accepted for later review;
- a deterministic conflict taxonomy;
- the reviewed mapping package contract;
- environment-specific, one-operation authorization;
- maintenance and write-freeze prerequisites;
- deterministic operation-manifest and idempotency requirements;
- pre-write rejection, atomicity, abort, and recovery requirements;
- provenance and audit boundaries;
- post-operation reconciliation gates;
- a capability-neutral state model; and
- the required separation of DEV and Production.

### 2.2 Explicit non-goals

This slice does not create or authorize:

- a discovery query, implementation, CLI, or tool;
- inspection of real vendor data;
- candidate generation or mapping selection;
- SQL, DDL, DML, migration, or schema change;
- apply, repair, merge, deduplication, or reconciliation execution;
- a report, JSON artifact, operation package, or audit record;
- an API, UI, route, scheduler, background task, or runtime consumer;
- a DEV or Production operation;
- credential, session, role, or permission behavior;
- runtime authority switching; or
- lifecycle mutation for organizations, memberships, assignments, or bindings.

### 2.3 No implied implementation

Normative language in this document is a requirement for future independently
approved slices. Words such as `must`, `requires`, and `rejects` describe that
future contract. They do not assert that a tool, reviewer system, maintenance
control, recovery process, or authorization service currently exists.

## 3. Canonical terminology and authority boundary

### 3.1 Frozen schema names

This design uses, without redefining, the exact physical projection frozen by
VENDOR-ID-002:

- `vendor_organizations`;
- `vendor_organization_memberships`;
- `vendor_site_assignments`; and
- `sheet_vendor_bindings`.

No table, column, index, constraint, lifecycle value, or relationship is added
or changed by this document. A future slice must return to docs-only
reconciliation if its needs conflict with that frozen schema.

### 3.2 Legacy identity terms

`vendor_name` remains a legacy display and business label. Text equality,
normalized text equality, or reuse of a label cannot prove canonical identity.

`vendor_accounts.id` identifies a legacy vendor account. It is not the future
canonical vendor organization identifier and must not be copied or treated as
one merely because both values identify vendor-related records.

Legacy operational consumers, including behavior based on `vendor_accounts`,
`vendor_name`, or `tasks.vendor`, remain authoritative until a later independent
runtime-authority slice explicitly changes every affected consumer.

### 3.3 Shadow projection boundary

The vendor organization projection is shadow and non-authoritative. Its
physical existence, future population, or future reconciliation must not:

- change login identity;
- alter session contents;
- change trusted-target resolution;
- change task, site, sheet, contact, or work-entry ownership;
- enable a new route or consumer; or
- disable legacy compatibility behavior.

Backfill completion is therefore not an authority-switch event. Runtime
authority switching belongs to a later, independently designed, tested,
authorized, and reversible program or slice.

## 4. Required roles and segregation of duties

### 4.1 Logical roles

Roles are logical responsibilities. This document does not invent actual human
names, accounts, teams, or an approval system.

| Role | Required responsibility | Must not do under this role |
|---|---|---|
| Discovery evidence producer | Run an approved read-only discovery implementation and bind its deterministic evidence to a source snapshot. | Approve mappings, authorize apply, or convert candidates into writes. |
| Mapping reviewer | Review candidate evidence, conflicts, exclusions, and exact ordered mappings. | Change evidence, execute apply, or infer identity from label equality alone. |
| Operation authorizer | Grant one environment-specific, time-bounded authorization for one exact operation package. | Authorize a different digest, silently broaden scope, or inherit DEV authorization into Production. |
| Operation executor | Execute only the exact approved package and retain machine-readable outcome evidence. | Reclassify conflicts, repair inputs, expand scope, switch authority, or improvise recovery. |
| Reconciliation reviewer | Independently compare expected and actual outcomes and accept or reject reconciliation evidence. | Treat apply completion as reconciliation or authorize runtime authority. |

### 4.2 Separation rules

- An evidence producer cannot elevate an unreviewed candidate into an approved
  mapping.
- A mapping reviewer cannot modify the immutable discovery evidence being
  reviewed.
- An executor may execute only an operation package whose digest exactly
  matches the authorization.
- A reconciliation reviewer must assess immutable post-operation evidence, not
  an executor's unsupported assertion.
- CODEX cannot authorize a Production apply. User authorization must be
  explicit, independent, environment-specific, and granted for each operation.
- One person or system may fulfill multiple logical roles only if a later gate
  explicitly accepts that reduced separation and records the risk. No such
  reduction is authorized by this baseline.

### 4.3 Authority precedence

Evidence production, review, authorization, execution, and reconciliation are
separate decisions. A later decision cannot retroactively change the bytes,
scope, or identity of an earlier evidence package.

## 5. Discovery-evidence input envelope

### 5.1 Required envelope

A future mapping review may accept discovery evidence only when the immutable
envelope binds all of the following:

| Field | Requirement |
|---|---|
| `environment` | Exact logical environment; DEV and Production are distinct. |
| `source_repository_commit` | Exact source commit used by the discovery implementation. |
| `discovery_implementation_identity` | Canonical path and immutable version or blob identity. |
| `discovery_execution_id` | Unique, non-reused execution identifier. |
| `generated_at` | Unambiguous UTC timestamp. |
| `source_snapshot_identity` | Snapshot, transaction, backup, or equivalent consistency identity sufficient to detect later source change. |
| `target_schema_identity` | Exact frozen projection and schema/version evidence. |
| `candidate_set` | Deterministically ordered candidate records represented by stable safe identifiers and digests. |
| `conflict_classification` | Exactly one frozen taxonomy result for each reviewed unit. |
| `counts_and_safe_digests` | Deterministic aggregate counts and non-sensitive cryptographic digests. |
| `unresolved_and_excluded` | Explicit sets, reason codes, and safe references. |
| `database_access_evidence` | Proof that discovery was read-only and its write count was zero. |
| `provenance` | Tool, actor reference, invocation boundary, and evidence lineage. |
| `expires_at` | Explicit staleness deadline. |
| `staleness_conditions` | Conditions that invalidate evidence before normal expiry. |

### 5.2 Determinism and privacy

Equivalent source snapshots and tool versions must produce byte-equivalent
normalized evidence. Ordering, identifiers, timestamps included in digests,
and serialization must be frozen by the discovery implementation slice.

Evidence and examples must not contain real vendor values, credentials,
secrets, tokens, password hashes, unnecessary personal data, or full raw row
dumps. Stable safe references and digests must be used wherever review does not
require a raw value.

### 5.3 Evidence invalidation

Evidence becomes stale immediately if any bound source snapshot, target schema,
implementation identity, repository commit, deterministic candidate set, safe
digest, or classification changes. Stale evidence cannot enter mapping review
or apply and must produce a no-write rejection.

## 6. Conflict taxonomy

### 6.1 Closed taxonomy

Each discovery unit must receive exactly one classification from this table.
Unknown or overlapping conditions fail closed as a blocking conflict.

| Classification | Automatic entry to review | Human decision required | Blocks apply | Exclusion permitted | Required exclusion evidence |
|---|---:|---:|---:|---:|---|
| `unique_eligible_match` | Yes | Yes | Until approved | Yes | Reviewer reason, source reference, and package digest coverage |
| `no_match` | Yes | Yes | Yes unless excluded | Yes | Evidence that exclusion creates no implicit organization or relationship |
| `multiple_candidate_match` | Yes | Yes | Yes | Yes | Candidate set, ambiguity reason, reviewer decision, and no-selection proof |
| `many_legacy_rows_to_one_canonical_identity` | Yes | Yes | Yes until cardinality is approved | Yes | Complete source set, target reference, and collision analysis |
| `one_legacy_row_to_multiple_canonical_candidates` | Yes | Yes | Yes | Yes | Full safe candidate set and explicit unresolved classification |
| `already_mapped_consistent` | Yes | Yes | Until pre-state is verified | Yes | Existing mapping digest and no-write/no-op decision |
| `already_mapped_conflicting` | Yes | Yes | Yes | Yes | Existing and proposed mapping digests plus conflict reason |
| `invalid_or_incomplete_source_identity` | Yes | Yes | Yes | Yes | Validation reason code and proof that the record remains untouched |
| `stale_evidence_or_source_changed` | No | No; evidence must be regenerated | Yes | No | Not applicable; stale evidence is rejected, not excluded |
| `target_state_conflict` | Yes | Yes | Yes | Yes | Expected/actual target digest and conflict analysis |
| `explicitly_excluded_record` | Yes | Already decided | No for unrelated approved records | Already excluded | Original classification, reviewer, reason, timestamp, and immutable source reference |

### 6.2 Identity decision boundary

No classification may use `vendor_name` equality as sufficient evidence that
two rows represent the same canonical identity. A unique eligible match is a
candidate for human review, not an automatically approved mapping.

### 6.3 Blocking-set calculation

The operation manifest must contain zero unresolved blocking conflicts. An
excluded record leaves the blocking set only when its exclusion evidence is
complete, review-approved, included in the package digest, and guaranteed to
receive no write.

## 7. Reviewed mapping approval contract

### 7.1 Approved mapping package

An approved mapping package must be immutable and contain:

| Field | Frozen requirement |
|---|---|
| `mapping_package_id` | Globally unique package identifier. |
| `environment` | Exact environment; no wildcard or shared DEV/Production value. |
| `discovery_evidence_id` | Exact evidence execution identifier. |
| `discovery_evidence_digest` | Digest of the complete normalized evidence envelope. |
| `ordered_mapping_set` | Deterministic, complete, ordered set of approved mapping actions. |
| `conflict_decisions` | Decision and rationale for every classified conflict. |
| `exclusions` | Complete excluded set and reason codes. |
| `reviewer_reference` | Safe reviewer identity reference. |
| `approved_at` | UTC approval timestamp. |
| `approval_scope` | Exact records and allowed mapping semantics. |
| `expires_at` | Mandatory expiry timestamp. |
| `supersession_status` | `active`, `superseded`, `revoked`, or `expired`. |
| `package_digest` | Digest covering every field and ordered member. |

### 7.2 Approval invalidation

Approval is invalid if:

- any candidate, mapping, exclusion, conflict decision, order, source state, or
  target pre-state changes;
- the discovery evidence or mapping package expires;
- the evidence, package, or operation digest differs;
- the package is revoked or superseded; or
- its environment, repository commit, schema identity, or tool version differs
  from the proposed operation.

Invalid approval must return a stable no-write rejection. It cannot be repaired
or broadened by the executor.

## 8. Environment-specific authorization

### 8.1 Authorization envelope

Every future authorization must bind:

| Authorization field | Requirement |
|---|---|
| `environment` | Exact `DEV` or `Production` identity. |
| `service_database_reference` | Safe, non-secret reference to the exact target service/database. |
| `repository_commit` | Exact approved source commit. |
| `tool_identity` | Exact canonical tool path and immutable version/blob identity. |
| `mapping_package_digest` | Exact approved package digest. |
| `operation_manifest_digest` | Exact operation manifest digest. |
| `operation_mode` | One explicitly permitted mode; no implicit fallback. |
| `valid_from` / `expires_at` | Narrow permitted execution window. |
| `maximum_write_scope` | Maximum rows/actions by exact target class. |
| `authorizer_reference` | Safe reference to the independent authorizer. |
| `one_use_token` | Single-operation, non-replayable authorization identity. |
| `revocation_conditions` | Events that invalidate authorization before expiry. |

### 8.2 DEV and Production independence

DEV authorization cannot authorize, imply, or be inherited by Production.
Production authorization requires a new envelope bound to Production evidence,
Production mapping review, the exact Production operation package, and a new
one-use authorization.

### 8.3 Authorization is not execution

Authorization only makes an exact operation eligible for a later executor
gate. It does not trigger execution, create a credential, open a database,
enable maintenance mode, or approve runtime authority switching.

## 9. Maintenance and write-freeze protocol

### 9.1 Required hard gate

Before a future apply can become eligible, an environment-specific plan must
identify and prove:

- the maintenance-mode plan and its owner;
- every relevant vendor identity write entry point;
- the exact mechanism that enables the write freeze;
- the freeze start timestamp and responsible role;
- handling of in-flight requests and transactions;
- handling of background, scheduled, queued, and administrative writers;
- evidence that the freeze is effective;
- the operations forbidden while frozen;
- timeout, abort, and freeze-release conditions; and
- the reconciliation state required before release.

### 9.2 No assumed hot maintenance

The engineering management system must not be assumed to support hot
maintenance followed by safe data merging. No later slice may infer that
concurrent writes can be reconciled merely because the operation is additive.

If all relevant writers cannot be identified and proven stopped, preflight must
abort with `write_count = 0`.

### 9.3 Freeze release

Write freeze cannot be released merely because the apply process exited zero.
Release requires either:

- independently accepted reconciliation; or
- an approved abort/recovery result demonstrating a known safe state.

## 10. Operation manifest and idempotency contract

### 10.1 Immutable operation manifest

The future operation package must bind:

| Field | Requirement |
|---|---|
| `operation_id` | Unique immutable operation identifier. |
| `environment` | Exact target environment. |
| `source_snapshot_identity` | Same immutable source identity used by approved evidence. |
| `mapping_package_digest` | Exact approved mapping digest. |
| `target_schema_identity` | Exact target schema/version evidence. |
| `repository_commit` / `tool_identity` | Exact executable source identities. |
| `ordered_actions` | Deterministic complete action set and ordering. |
| `expected_pre_state` | Per-action and aggregate safe digests/counts. |
| `expected_post_state` | Per-action and aggregate safe digests/counts. |
| `maximum_write_counts` | Exact ceiling by action and target class. |
| `idempotency_key` | Stable key derived from the immutable operation identity. |
| `created_at` / `approved_at` / `expires_at` | UTC lifecycle timestamps. |
| `manifest_digest` | Digest of every normalized field and action. |

### 10.2 Idempotency rules

- An exact replay of a successfully applied operation may only return a safe
  no-op or `already_applied` result after verifying the same manifest digest and
  post-state.
- Reuse of an idempotency key with different bytes or a different digest must
  be rejected before write.
- A partial, indeterminate, disconnected, or unknown prior outcome must not be
  retried blindly. It enters reconciliation or recovery.
- A different source snapshot or target pre-state requires a new evidence,
  mapping, manifest, review, and authorization chain.
- VENDOR-ID-002 DDL idempotence is not evidence of data-backfill idempotence.

## 11. Preflight and no-write rejection contract

### 11.1 Checks before the first write

All checks in this table must pass before a write transaction or write-capable
statement begins.

| Preflight check | Required proof | Rejection code |
|---|---|---|
| Environment match | Authorization, evidence, mapping, manifest, and target agree exactly. | `environment_mismatch` |
| Schema identity | Target projection matches the approved frozen identity. | `schema_identity_mismatch` |
| Evidence freshness | Evidence is unexpired and no staleness condition is true. | `discovery_evidence_stale` |
| Source snapshot stability | Current source identity equals the reviewed snapshot. | `source_snapshot_changed` |
| Mapping digest | Approved package digest equals the manifest reference. | `mapping_digest_mismatch` |
| Blocking conflicts | Unresolved blocking count is exactly zero. | `blocking_conflicts_present` |
| Authorization validity | Exact one-use authorization is active, unexpired, and unrevoked. | `authorization_invalid` |
| Write freeze | All identified writers are proven stopped. | `write_freeze_unverified` |
| Target pre-state | Actual safe digest/counts equal the manifest pre-state. | `target_prestate_mismatch` |
| Recovery prerequisite | Exact approved recovery plan and restore point are available and verifiable. | `recovery_prerequisite_missing` |
| Prior operation state | Operation is not applied, in progress, unknown, or recovery-required. | `operation_state_ineligible` |
| Maximum scope | Planned writes do not exceed every authorized ceiling. | `maximum_scope_exceeded` |

### 11.2 Universal rejection behavior

Any preflight failure must:

- produce `write_count = 0`;
- avoid starting a write transaction or fully roll back any pre-write setup;
- return the stable machine-readable rejection code;
- emit privacy-safe evidence containing the expected and observed safe
  identities, not raw vendor data;
- leave the authorization unused only when the later authorization contract
  explicitly permits safe retry after correction; and
- never repair, reclassify, select a different candidate, or broaden scope.

## 12. Apply atomicity and abort behavior

### 12.1 Future apply contract

Transaction and batch strategy must be frozen by the later apply slice. This
document does not select or implement a transaction mechanism.

Regardless of mechanism:

- partial success cannot be reported as success;
- each write must be attributable to exactly one approved action;
- actual counts must be checked against per-action and aggregate limits;
- an unexpected row count, digest drift, constraint failure, connection loss,
  authorization expiry, or write-freeze loss must abort;
- no error path may switch runtime authority; and
- an executor must not continue with a reduced or altered action set unless
  that exact behavior was independently reviewed and represented in the
  manifest before authorization.

### 12.2 Abort outcome

Abort must leave a durable, privacy-safe operation record capable of
distinguishing:

- no write attempted;
- transaction fully rolled back;
- known partial state requiring compensating recovery;
- unknown result requiring investigation; and
- recovery completed and reconciled.

Unknown state must enter `RECOVERY_REQUIRED`. It must not be retried directly.

## 13. Rollback and recovery contract

### 13.1 Distinct recovery layers

The following are separate and cannot substitute for one another:

| Layer | Purpose | Limitation |
|---|---|---|
| Database transaction rollback | Revert writes within a still-valid transaction boundary. | Does not cover committed batches, external interruption, or unknown connection outcome. |
| Operation-level compensating recovery | Restore approved business state after known committed changes. | Requires a pre-approved inverse plan and complete provenance. |
| Backup or snapshot restore | Restore an environment-specific database recovery point. | May affect unrelated data and requires separate operational authority. |
| Application/runtime rollback | Restore deployed source or behavior. | Does not automatically remove or reverse persisted data changes. |

### 13.2 Mandatory recovery plan

Before apply, the environment-specific authorization must reference an approved
recovery plan and a verifiable restore point. The plan must freeze:

- exact recovery scope;
- responsible owner;
- triggering conditions;
- maximum tolerated data loss and downtime assumptions, if applicable;
- commands or mechanism to be approved in the later operation gate;
- evidence required before recovery;
- validation after recovery; and
- the state transition back to reconciliation or safe abort.

VENDOR-ID-002 DDL savepoints are not a data-operation recovery plan. Migration
rollback is not equivalent to backfill rollback. Production recovery cannot be
designed and immediately executed by CODEX after an incident; it requires its
own explicit authority and the previously approved plan.

## 14. Provenance and audit boundary

### 14.1 Required safe audit fields

A future audit record must include at least:

- operation ID and environment;
- repository commit and tool version/blob identity;
- discovery evidence, mapping package, and manifest digests;
- authorization reference and one-use status;
- safe actor references for producer, reviewer, authorizer, executor, and
  reconciliation reviewer;
- created, approved, started, completed, aborted, and reconciled timestamps as
  applicable;
- attempted, written, skipped, excluded, and conflict counts;
- terminal result or stable abort reason; and
- reconciliation evidence reference.

### 14.2 Prohibited audit content

Audit output must not include:

- password hashes, credentials, secrets, or tokens;
- raw session or authentication material;
- unnecessary vendor-sensitive values;
- a complete row dump not specifically approved for review; or
- environment-variable or connection-string values.

### 14.3 Immutability

Audit evidence must be append-only or otherwise tamper-evident under a mechanism
frozen by a later slice. Correction must supersede prior evidence rather than
silently overwrite it.

## 15. Post-operation reconciliation contract

### 15.1 Required reconciliation

Successful apply completion enters `APPLIED_PENDING_RECONCILIATION`. A separate
read-only reconciliation must verify:

- exact equality of the expected action set and actual result set;
- inserted, updated, skipped, excluded, and rejected counts;
- missing, extra, conflicting, and duplicate mappings;
- referential integrity of the canonical shadow projection;
- absence of unintended change to legacy authority data;
- equality of the shadow projection and the approved mapping package;
- no writes to rejected or excluded records;
- actual write scope within every manifest ceiling;
- complete audit and provenance linkage; and
- no database change outside the authorized target scope.

### 15.2 Independent acceptance

The reconciliation reviewer must independently accept immutable evidence. The
executor's success exit code is insufficient.

Before acceptance:

```text
operation_state = APPLIED_PENDING_RECONCILIATION
production_frozen = false
runtime_authority_switched = false
```

Only reconciliation acceptance may enter `RECONCILED`. Even then, the canonical
projection remains shadow/non-authoritative until a later authority-switch
slice is separately approved and completed.

## 16. Gate state model

### 16.1 Frozen states

| State | Entry prerequisites | Permitted actions | Forbidden actions | Required evidence | Exit condition |
|---|---|---|---|---|---|
| `NOT_AUTHORIZED` | Baseline only, or any required prerequisite absent | Docs-only review; read-only readiness inventory | Discovery execution, mapping approval, apply, authority switch | Baseline refs and frozen contracts | Approved read-only discovery slice exists |
| `DISCOVERY_EVIDENCE_READY` | Valid read-only evidence envelope; zero writes | Mapping review | Apply, mutation, authority switch | Evidence ID/digest, snapshot, counts, taxonomy | Complete mapping review |
| `MAPPING_REVIEWED` | Immutable approved mapping package; blocking conflicts resolved or excluded | Environment preflight and authorization review | Apply without authorization; package change | Mapping package and reviewer evidence | Exact environment authorization issued |
| `ENVIRONMENT_AUTHORIZED` | Valid one-use authorization bound to exact manifest | Write-freeze preparation and preflight | Apply before freeze proof; reuse in another environment | Authorization envelope and manifest digest | Write freeze verified |
| `WRITE_FREEZE_VERIFIED` | All writers inventoried and proven stopped | Final no-write preflight | Scope expansion, candidate change, unauthorized write | Freeze evidence and owner/timestamps | Every apply-eligibility check passes |
| `APPLY_ELIGIBLE` | All Section 11 checks pass | Begin exact authorized apply once | Reclassification, repair, different manifest, authority switch | Complete preflight result with zero failures | Apply begins or eligibility expires |
| `APPLY_IN_PROGRESS` | Exact authorized executor begins within window | Execute deterministic action set; abort safely | New actions, manual repair, runtime switch | Operation ID, live authorization, audit stream | Applied pending reconciliation, aborted, or recovery required |
| `APPLIED_PENDING_RECONCILIATION` | Apply reports known complete result | Read-only reconciliation; retain freeze | Production freeze declaration, authority switch, unreviewed release | Apply result, counts, digests, audit evidence | Independent reconciliation accepts or rejects |
| `RECONCILED` | Independent reconciliation accepted all checks | Close operation evidence; controlled freeze release | Automatic runtime authority switch | Reconciliation reference and reviewer acceptance | Separate program may propose later authority work |
| `ABORTED` | Known no-write or known fully rolled-back result | Review abort evidence; safely release freeze if approved | Blind retry, claim success, authority switch | Stable abort code, write count, rollback proof | Close or create a newly reviewed operation chain |
| `RECOVERY_REQUIRED` | Known partial or unknown outcome | Execute separately approved recovery/investigation gate | Retry apply, release freeze, claim success, authority switch | Incident state, audit trail, approved recovery authority | Recovery reconciliation establishes a known state |

### 16.2 Universal state rule

No state implies, enables, or authorizes runtime authority switching. State
transitions are environment-specific and cannot be copied from DEV to
Production.

## 17. DEV and Production separation

### 17.1 Permanent sequence

The required order is:

1. read-only discovery implementation;
2. disposable/local validation;
3. DEV discovery evidence;
4. reviewed DEV mappings;
5. DEV-specific authorization;
6. DEV controlled apply;
7. DEV reconciliation;
8. independent Production discovery and preflight;
9. Production mapping review;
10. Production-specific authorization;
11. Production controlled operation; and
12. Production reconciliation.

### 17.2 Non-transfer rules

- DEV data, candidates, decisions, mappings, snapshots, digests, and exclusions
  are not Production evidence.
- DEV success is technical evidence only; it is not Production authorization.
- Production discovery must bind a Production-consistent snapshot.
- Every Production mutation requires a new explicit operation gate and one-use
  authorization.
- No Production operation may be inferred from repository ownership, service
  ownership, deployment health, a previous authorization, or DEV acceptance.

## 18. Acceptance evidence for future implementation

### 18.1 Required evidence classes

Later slices must provide, without combining independent approvals:

| Evidence class | Minimum proof |
|---|---|
| Static guard | Exact allowed paths/callables and fail-closed rejection of mapping, mutation, dynamic SQL, broad exemptions, environment access, and authority switching outside the owned slice. |
| Disposable no-write fixtures | Every rejected preflight returns stable code and `write_count = 0`. |
| Disposable apply fixtures | Exact approved actions produce exact expected post-state and bounded counts. |
| Repeat fixtures | Exact replay safely no-ops or reports `already_applied`; conflicting key/digest rejects without write. |
| Conflict fixtures | Every Section 6 class, exclusion path, ambiguity path, and unknown classification is covered. |
| Before/after digests | Deterministic safe digests prove authorized scope and unchanged protected state. |
| Forced-failure atomicity | Constraint, row-count, connection, expiry, and injected-failure cases prove rollback or recovery-required classification. |
| Recovery rehearsal | Environment-appropriate restore or compensating process is rehearsed against disposable or explicitly authorized non-Production state. |
| DEV operation chain | DEV discovery, mapping review, authorization, freeze, apply, and reconciliation each have distinct evidence. |
| Production preflight | Fresh Production evidence and mapping review with zero mutation. |
| Production execution | Separately authorized exact operation with bounded writes and immutable audit evidence. |
| Final reconciliation | Independent result-set, scope, integrity, provenance, and protected-state verification. |

### 18.2 Evidence cannot be substituted

Static checker success cannot replace runtime disposable tests. Deployment
health cannot replace database evidence. DEV evidence cannot replace Production
evidence. Apply exit zero cannot replace reconciliation. Source rollback cannot
replace data recovery. None of these can replace runtime authority-switch
review.

## 19. Explicit blockers and current readiness

### 19.1 Current blockers

The current repository state has all of these blocking conditions:

| Blocker | Current state | Required future owner |
|---|---|---|
| Canonical discovery implementation | `NOT IMPLEMENTED` | VENDOR-ID-004B |
| Environment discovery evidence | `MISSING` | Future discovery execution gates |
| Reviewed candidate mappings | `MISSING` | VENDOR-ID-004C and environment-specific review |
| Write-freeze implementation and evidence | `MISSING` | Environment operation owner |
| Controlled apply capability | `NOT IMPLEMENTED` | VENDOR-ID-004D |
| Data recovery plan and verified restore point | `MISSING` | Environment authorization/recovery owner |
| Post-operation reconciliation implementation | `NOT IMPLEMENTED` | Reconciliation slice owner |
| DEV authorization | `MISSING` | Explicit future user authorization |
| Production authorization | `MISSING` | Separate explicit future user authorization |

### 19.2 Readiness decision

VENDOR-ID-004A freezes design gates only. It does not authorize discovery,
mapping, backfill, reconciliation, or runtime authority switching.

The next slice may only define and implement the read-only discovery capability.
It must not begin mapping approval or mutation.

```text
VENDOR-ID-004 BASELINE: PASS
VENDOR-ID-004A DESIGN BASELINE: DOCS-ONLY
CONTROLLED BACKFILL: NOT AUTHORIZED
CANONICAL DISCOVERY: NOT IMPLEMENTED
REVIEWED MAPPINGS: MISSING
WRITE FREEZE: MISSING
APPLY CAPABILITY: NOT IMPLEMENTED
RECOVERY PLAN: MISSING
RECONCILIATION CAPABILITY: NOT IMPLEMENTED
RUNTIME AUTHORITY: LEGACY / UNCHANGED
```

## 20. Future slice sequence

### 20.1 Independently gated slices

The candidate sequence is:

1. `VENDOR-ID-004B` — Read-only vendor identity discovery implementation.
2. `VENDOR-ID-004C` — Discovery evidence and conflict classification review.
3. `VENDOR-ID-004D` — Controlled apply tool contract and implementation.
4. `VENDOR-ID-004E` — Disposable local backfill verification.
5. `VENDOR-ID-004F` — DEV discovery, authorization, and controlled apply.
6. `VENDOR-ID-004G` — DEV reconciliation.
7. `VENDOR-ID-004H` — Production preflight and independent authorization.
8. `VENDOR-ID-004I` — Production controlled operation.
9. `VENDOR-ID-004J` — Production reconciliation and freeze.

Each slice requires its own baseline review, exact changed-file scope, static
and/or disposable evidence appropriate to its capability, commit and deployment
gates where applicable, and explicit environment authority before mutation.

### 20.2 Permanent ownership separation

The following must not be merged into one authorization merely for convenience:

- physical schema;
- discovery implementation;
- discovery execution and evidence;
- conflict classification and mapping approval;
- apply implementation;
- environment-specific apply;
- reconciliation; and
- runtime authority switching.

Runtime authority switching remains a later independent program or slice after
Production reconciliation. No slice listed above pre-authorizes it.

### 20.3 Final frozen marker

```text
VENDOR-ID-004A CONTROLLED VENDOR IDENTITY BACKFILL OPERATIONAL GATE DESIGN BASELINE
DOCS-ONLY DESIGN: COMPLETE
CONTROLLED BACKFILL: NOT AUTHORIZED
CANONICAL DISCOVERY: NOT IMPLEMENTED
NO MAPPING, APPLY, RECONCILIATION, CONSUMER, OR AUTHORITY CREATED
READY FOR FINAL DIFF REVIEW
```
