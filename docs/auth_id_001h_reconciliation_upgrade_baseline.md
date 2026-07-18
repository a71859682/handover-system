Status: design baseline

Scope: docs-only

Implementation status: not started

# AUTH-ID-001H — Registry Reconciliation and Upgrade Design Baseline

Canonical path: `docs/auth_id_001h_reconciliation_upgrade_baseline.md`.

This exact path, filename, title, and slice ID are the canonical name for
this owner. Descriptive phrases such as "reconciliation / upgrade" are aliases
only and must not create a different owner ID, document, or authority.

## 1. Purpose and current baseline

This document freezes the design boundary for future registry reconciliation
and upgrade work. It does not authorize or implement discovery, reporting,
planning, repair, relationship correction, or any persistent write.

The starting Production-frozen commit is
`1d49f2db7bf98c67c964e1cccf9b9448aa6d9d21`. The recorded Production deploy
is `dep-d9dgui7aqgkc73cnldt0`.

At this baseline, `AUTH-ID-001H` has no implementation, scanner, consumer,
authority, plan format, or write path. Production registry objects, rows,
topology, anomalies, and actual repair demand are unknown because this slice
does not query a persistent database. Deployment health is not database-content
evidence.

## 2. Canonical terminology

The following terms have the specified meaning and must not be silently
substituted for one another.

| Term | Frozen meaning |
|---|---|
| observation | A source-derived fact with bounded evidence; it is not a conclusion or mutation instruction. |
| anomaly | An observed state that violates, or cannot be shown to satisfy, a frozen contract. |
| conflict | A state with incompatible candidate interpretations that must fail closed. |
| collision | A specific uniqueness, cardinality, or identifier conflict; it is not a winner-selection signal. |
| drift | A difference between bounded snapshots, source contracts, or declared versions. |
| reconciliation | Evidence-preserving classification and separately approved correction planning; it is not merge. |
| upgrade | A compatibility assessment or later approved change between declared versions; it does not automatically mean DDL or data rewrite. |
| discovery | Read-only collection and classification of bounded evidence. |
| report | Deterministic, redacted presentation of discovery results. |
| quarantine recommendation | A non-mutating recommendation to isolate a case for controlled review. |
| plan | A non-executable, snapshot-bound proposal. A plan has no write authority. |
| dry run | A zero-persistent-write evaluation that produces no authoritative mutation. |
| apply | A future, separately authorized mutation phase. This slice does not create it. |
| repair | A mutation intended to correct a confirmed anomaly; repair requires independent approval. |
| relationship correction | Any proposed change to alias, mapping, or identity relationships; it must not imply movement, merge, or reassignment authority. |
| stale plan | A plan whose bound snapshot, schema fingerprint, tool version, or preconditions no longer match. |
| immutable evidence | Evidence whose integrity, source binding, and before/after meaning can be independently verified. |
| hot maintenance | Production mutation performed ad hoc, in place, or without a separately designed maintenance workflow. |

Discovery and reporting do not equal repair. A dry run must perform zero
persistent writes. A plan must not confer write authority. Reconciliation must
not mean merge, and upgrade must not automatically mean DDL or data rewrite.

## 3. Frozen ownership boundary

`AUTH-ID-001H` owns only the future, independently approved design of:

- existing-state anomaly handling;
- principals mapped to different identities;
- evidence-preserving reconciliation planning;
- upgrade compatibility assessment; and
- future separately approved relationship correction.

This ownership is a design allocation, not an implementation authorization.
`AUTH-ID-001H` must not reverse-acquire any of the following:

- `AUTH-ID-001E1` physical schema or migration ownership;
- `AUTH-ID-001E2` ID generation or creation-consumer collision and
  transaction acceptance;
- `AUTH-ID-001F` lifecycle, unlink, disable/reactivate, tombstone,
  merge/split/restore, or relationship-movement authority;
- `AUTH-ID-001G` linking authority, proof, consumer, or new-topology
  creation; or
- authentication, credential, session, role, permission, site, vendor, or
  workflow authority.

Every cross-owner capability requires its corresponding owner's independent
gate. This document must not self-authorize a cross-owner capability.

## 4. Current facts, inferences, and unknowns

### 4.1 Proven source and deployment facts

- The frozen source contains the physical registry schema and static policy
  guardrails.
- The recorded Production baseline is the commit and deploy named in
  Section 1.
- Existing source guardrails prohibit unauthorized lifecycle and linking
  consumers and registry DML outside their tightly bounded fixtures.
- This document creates no runtime source behavior.

### 4.2 Reasonable inferences

- A deployed process may import the existing application bootstrap during
  startup; deployment health must not be described as proof of zero SQLite
  contact.
- Future reconciliation requires source, schema, transaction, and authority
  evidence beyond the current static design documents.

### 4.3 Unknown because no persistent database query occurred

The following remain unknown and must not be inferred from deployment health:

- registry objects and row counts;
- noncanonical IDs;
- alias conflicts;
- mapping topology;
- orphan or otherwise invalid rows;
- source-backend principal state;
- historical mutations;
- first creation time; and
- actual repair demand.

## 5. Frozen anomaly taxonomy

Stable anomaly codes must be lowercase ASCII snake_case. Unknown codes must
not be coerced into a known class. The following taxonomy is frozen for future
design review only.

| Stable code | Required evidence | Severity | Fail-closed disposition | H role now | Future mutation requires |
|---|---|---|---|---|---|
| `schema_object_drift` | Bounded schema manifest and expected contract | high | `owner_gate_required` | report only | E1 and H approval |
| `noncanonical_registry_id` | Raw stored value, lexical validation result, and source binding | high | `fail_closed` | report only | E2 and H approval |
| `invalid_registry_status` | Row evidence and closed status contract | high | `fail_closed` | report only | F and H approval |
| `invalid_provenance` | Complete provenance tuple and frozen profile | high | `quarantine_recommended` | report only | E1 and H approval |
| `invalid_backend_principal_key` | Typed key evidence and range validation | high | `fail_closed` | report only | E1 and H approval |
| `orphan_fk_relationship` | Parent and child snapshot evidence | critical | `quarantine_recommended` | report only | E1, F, and H approval |
| `normalized_alias_ambiguity` | Deterministic candidate set and normalization provenance | high | `fail_closed` | report only | F and H approval; no automatic link |
| `active_exact_alias_collision` | Exact alias/index evidence and source snapshot | high | `fail_closed` | report only | F and H approval |
| `backend_principal_inconsistent_mapping` | Backend kind/key and mapping evidence | critical | `fail_closed` | report only | F, G, and H approval |
| `incompatible_backend_cardinality` | Identity and backend-kind mapping set | critical | `fail_closed` | report only | E1, F, and H approval |
| `conflicting_principals_different_identities` | Both principal mappings and identity IDs | critical | `manual_review_required` | classify/report only | F, G, and H approval; no winner selection |
| `disabled_superseded_relationship_inconsistency` | Statuses, provenance, and bounded relationship evidence | high | `fail_closed` | report only | F and H approval |
| `source_principal_missing_inactive_stale` | Re-canonicalized backend evidence | high | `fail_closed` | report only | F and H approval; no fallback |
| `snapshot_concurrency_drift` | Two snapshot identities or changed preconditions | critical | `owner_gate_required` | report only | H plan and mutation approval |
| `unknown_unclassified_anomaly` | Bounded evidence plus failure reason | high | `fail_closed` | report only | no mutation; future owner gate required |

No class may select a winner, perform an automatic repair, or convert severity,
count, or confidence into mutation authority.

## 6. Classification and disposition contract

The disposition vocabulary is closed to the following values:

- `report_only`
- `fail_closed`
- `quarantine_recommended`
- `manual_review_required`
- `owner_gate_required`
- `unsupported`

An unknown classification must be `fail_closed`. Implementations must not use
best-effort repair, silent ignore, fuzzy matching, or automatic
canonicalization. They must not select a winner from username, alias, display
name, `vendor_name`, timestamp, apparent recency, count, severity, or
confidence. A collision delta must not become a repair plan or write authority.

## 7. Read-only discovery boundary

Any discovery implementation requires a separate approval. If approved, it
must be read-only by construction and must satisfy all of the following:

- no `INSERT`, `UPDATE`, `DELETE`, `REPLACE`, or UPSERT;
- no DDL;
- no temporary table, trigger, or persistent marker in the canonical database;
- no claim that WAL, SHM, or journal side effects are absent unless that claim
  is independently proven for the exact tool and environment;
- no application bootstrap as the discovery mechanism;
- no Production scan in this docs-only slice;
- verifiable source database identity and snapshot binding; and
- output that must not become authentication or authorization proof.

## 8. Evidence bundle and provenance contract

A future evidence bundle must contain at least:

- format and schema version;
- run or correlation ID;
- tool version and commit;
- source snapshot identity or fingerprint;
- capture time and timezone;
- schema-manifest fingerprint;
- classification code;
- aggregate counts;
- deterministic ordering;
- redaction policy;
- completeness and integrity marker;
- errors and unsupported classifications; and
- evidence hash.

Evidence must not record or leak credential material, password, password hash,
session, cookie, token, raw proof material, environment or database secrets,
unrestricted raw alias, unrestricted normalized lookup key, backend principal
key, or role/site/permission authority. A controlled audit may cite an opaque
registry ID, but that ID must not become identity proof or authority proof.

## 9. Collision-delta and comparison contract

Future comparison must keep baseline and candidate snapshots separate. It must
classify bounded evidence as added, removed, changed, or unchanged; group
anomaly counts by stable code; and render deterministic output. It must not use
fuzzy matching, silently canonicalize values, or mutate while comparing.

Collision delta must not automatically form a repair plan. A partial or
incomplete capture must not be marked `PASS` or complete.

## 10. Dry-run and plan artifact contract

Dry run and apply must remain completely separate. A dry run must perform zero
persistent writes. A plan artifact has no execution authority and must bind to
the exact source snapshot, schema fingerprint, and tool version.

A future plan design requires explicit expiry and staleness rules and must not
contain secrets. It must not imply that a winner, merge, movement, repair, or
approval has already been granted. A stale, partial, tampered, or
version-mismatched plan must be rejected. This slice does not create a plan
format or an implementation of one.

## 11. Approval and authority model

There is currently no H repair authority, and no role or account is assigned
H authority. Production access, Render access, database access, an admin role,
or operator identity must not be treated as repair authority.

A discovery operator must not equal an approver. A plan author must not equal
an approver. An approver must not automatically gain apply authority. Future
authority, separation of duties, expiry, scope, revocation, and controlled
audit access require an independent slice. This document must not create a new
role or permission.

## 12. Concurrency and stale-state contract

Before any future approved apply operation, an implementation must:

- revalidate the exact snapshot identity;
- revalidate the schema fingerprint;
- revalidate affected rows and backend principals;
- detect concurrent change;
- reject a stale plan;
- never continue a partially matched plan;
- never recalculate a winner during apply; and
- never mutate unrelated rows.

This document does not claim that SQLite or Production currently provides
these capabilities.

## 13. Transaction and rollback boundary

If mutation is independently approved later, it must provide a caller-owned
transaction boundary, all-or-nothing logical operation, no partial rows, no
partial audit or event evidence, and rollback on every failure. It must
distinguish a target constraint collision from an unrelated `IntegrityError`
without fuzzy error-string classification. It requires idempotency/correlation
rules, explicit concurrency tests, and disposable SQLite evidence.

`AUTH-ID-001E2` acceptance must not be replaced by H. This baseline implements
no transaction, savepoint, ledger, DML, or rollback capability.

## 14. Audit, privacy, and error boundary

External errors must be generic. Detailed evidence may enter only a separately
authorized controlled audit. Implementations must not create an
account-existence, topology, conflict, or candidate-winner oracle, and must
not leak secrets or authority information.

Evidence access requires independent authorization. Audit failure must not
allow repair to continue. Deployment logs must not emit sensitive row evidence.

## 15. Operational and maintenance boundary

The following are explicitly forbidden by this baseline:

- hot repair;
- in-place Production experimentation;
- ad hoc SQL;
- Render Shell mutation;
- live winner selection;
- partial backfill;
- manual row movement;
- best-effort repair;
- emergency bypass;
- direct canonical database replacement; and
- treating backup availability as mutation approval.

A future maintenance workflow requires independent design, review, and
rehearsal. It must not be inferred from this document.

## 16. Threat model

| Threat | Current guard | Remaining gap | Required future gate |
|---|---|---|---|
| automatic winner selection | F/G policies require fail-closed handling | No H taxonomy implementation | H docs then read-only discovery review |
| overwrite in place | No registry repair consumer exists | No immutable-event enforcement | H mutation plus audit gate |
| merge, remap, or reassignment | F forbids movement; G cannot repair | No controlled reconciliation design | F/G/H companion approval |
| alias-based guessing | E/F/G reject alias as authority | No redacted discovery implementation | H discovery gate |
| stale snapshot | No H plan exists | No snapshot revalidation mechanism | H plan and mutation gates |
| concurrent mutation | Live movement is unsupported | No concurrency protocol | H mutation/maintenance gate |
| partial repair | No H DML exists | No rollback/event ledger | E2/F/H companion approval |
| provenance loss | Schema has limited provenance columns | No immutable before/after ledger | Audit/event capability gate |
| audit omission | F requires audit for future lifecycle writes | No audit capability exists | Audit/event capability gate |
| evidence tampering | No H evidence artifact exists | No integrity format exists | H evidence-format gate |
| replay | No plan/apply flow exists | No correlation/idempotency design | H plan and mutation gates |
| caller-selected IDs | E2 rejects normal caller selection | Import/reconciliation exception is undefined | E2 companion gate |
| authority inheritance | F/G forbid inherited authority | No H authority model implementation | H authority gate |
| linking or lifecycle owner bypass | Static readiness checkers protect boundaries | No cross-owner orchestration contract | E2/F/G companion approvals |
| Production operator overreach | No H authority is assigned | No separation-of-duties workflow | H authority/maintenance gate |
| hot-maintenance assumption | F rejects hot maintenance | No rehearsed maintenance workflow | Operational maintenance gate |
| data or existence oracle | G/F policies require generic handling | No H report redaction implementation | H discovery/evidence gate |
| incomplete scan marked clean | No H scanner exists | No completeness enforcement | H discovery gate |

## 17. Owner handoffs and future slices

| Area | Owner | H must not self-complete | Required progression |
|---|---|---|---|
| physical schema and migration | E1 | DDL, migration, or schema repair | E1 companion review |
| ID and creation collision behavior | E2 | retry, caller-ID exception, or creation transaction acceptance | E2 consumer gate |
| lifecycle and legacy alias import | F | lifecycle DML, unlink, disable/reactivate, merge/split/restore, movement | F gate |
| explicit linking | G | authority, proof, consumer, or new topology creation | G gate |
| H discovery | H | scan or report implementation before approval | docs freeze then static readiness guard |
| H plan format | H | executable plan or apply authority | evidence review then plan-format gate |
| H authority | H | role, permission, or apply assignment | separate authority gate |
| H mutation | H with companion owners | repair, correction, or DML | separately approved consumer/mutation gate |
| operational maintenance | separate operational owner | hot maintenance or Production experimentation | designed, reviewed, rehearsed maintenance gate |
| audit/event capability | separate schema/audit owner | immutable ledger claim | separate audit/event gate |

Future work must follow this sequence without skipping a step:

`docs freeze → static readiness guard → read-only disposable discovery → evidence review → separately approved consumer/mutation gate`

## 18. Future acceptance matrix and explicit exclusions

Any future implementation proposal must demonstrate all applicable items:

- anomaly-taxonomy negative controls;
- deterministic report output;
- secret-safe output;
- read-only enforcement;
- unchanged source database and sidecars;
- incomplete-capture failure;
- stale-plan rejection;
- tampered-plan rejection;
- concurrency rejection;
- no automatic winner;
- no merge or relationship movement;
- no owner bypass;
- zero PostgreSQL attempts;
- disposable fixtures only;
- no DEV or Production persistent-database access during implementation
  validation;
- no rewrite of existing rows; and
- no authentication or authorization change.

This slice explicitly excludes code, tests, a checker, scanner, report
artifact, plan-format implementation, route, API, form, UI, CLI, role,
permission, DDL, DML, backfill, repair, merge, split, restore, relationship
movement, import, hot maintenance, and Production database inspection.

## 19. Frozen conclusion

```text
AUTH-ID-001H DOCS-ONLY RECONCILIATION / UPGRADE DESIGN BASELINE
DESIGN STATUS: FROZEN FOR REVIEW
IMPLEMENTATION STATUS: NOT STARTED
DISCOVERY / SCANNER: NOT IMPLEMENTED
REPORT / PLAN FORMAT: NOT IMPLEMENTED
REPAIR AUTHORITY: NOT IMPLEMENTED OR ASSIGNED
RECONCILIATION MUTATION: NOT IMPLEMENTED
NO DATABASE OR ENVIRONMENT ACCESSED
AUTH-ID-001H OVERALL: OPEN — NOT CLOSED
```
