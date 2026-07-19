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

## 20. Static reconciliation readiness guardrail evidence

### 20.1 Guardrail status

The static source and policy guardrail is implemented and Production-frozen.
It does not change the H runtime baseline: H runtime implementation remains not
started; discovery/scanner is not implemented; report/plan format is not
implemented; repair authority is not implemented or assigned; and
reconciliation mutation is not implemented. The top-level `Implementation
status: not started` continues to describe H runtime capability, not the static
checker. `AUTH-ID-001H` remains OPEN / NOT CLOSED.

### 20.2 Implementation evidence

The guardrail was introduced by commit
`63341c22df50029b43a6df5f7fd07502b42a2e87`, with direct parent
`1ba5084b9205ed09604b5ab46033b82d5300694a` and message
`Add identity registry reconciliation readiness checker`.

Its exact changed files were:

- `tools/check_identity_registry_reconciliation_readiness.py`; and
- `tests/smoke_test.py`.

The checker blob is `b55b61e532afdde4ff2831dde7128f919371c935`; the
smoke blob is `7402c8f92d120b65fa2b4c2c5e0ed1686287246e`; and the
checker raw SHA-256 is
`F34EF75ED60B07FE33A1B5365F44B53E585B5642E22C98C2C3491EF50EC0A0F1`.

### 20.3 Completed static acceptance

Completed acceptance evidence covers AST/static source analysis only; normal
checker PASS with `issues_count: 0`; self-test PASS with 100 scenarios;
focused H readiness smoke PASS; lifecycle checker normal/self-test PASS;
linking checker normal/self-test PASS; serializer self-test PASS; identity
schema checker self-test and disposable normal PASS; app-compatible disposable
bootstrap PASS; and isolated full smoke PASS. PostgreSQL attempts were zero;
the canonical repository database and sidecars were unchanged; and temporary
fixtures, logs, and pycache were cleaned.

The checker detects forbidden route/API/form, CLI, scanner/discovery,
reporter/evidence-generator, plan/apply-plan, repair-authority, Production
reconciliation-access, automatic-winner-selection, hot-maintenance,
relationship-correction, registry-repair, caller-selected-ID, public-oracle,
unredacted-evidence, dynamic-unresolved-capability, and
policy/owner/upstream-checker drift. It creates no runtime capability.

### 20.4 DEV deployment evidence

DEV service `handover-system-dev` deployed
`dep-d9dnfie8bjmc73avkjpg` with live commit
`63341c22df50029b43a6df5f7fd07502b42a2e87`. Deployment, logs, and HTTP
health passed. Shell instance `wxnvr` had a disabled selector, and no Shell
command was executed.

### 20.5 Production deployment evidence

Production evidence was observed browser-only for service `handover-system`.
Deploy `dep-d9dp523bc2fs73fij00g`, triggered by `New commit via Auto-Deploy`,
is Live for commit `63341c22df50029b43a6df5f7fd07502b42a2e87` with message
`Add identity registry reconciliation readiness checker`. No newer deploy was
observed. Build, logs, startup, and HTTP health passed. Shell instance `pphhj`
had a disabled selector, and no Shell command was executed. No Render MCP,
CLI, API, SSH, or job was used.

### 20.6 Live-tool evidence limitation

DEV and Production live checker commands were not executed. No deployed
checker stdout/self-test output or deployed checker SHA-256 was obtained. A
selector-disabled state is not a checker failure; live-tool verification must
not be claimed PASS. The evidence substitution relies on exact live commits,
immutable committed blobs, independent final-diff review, completed disposable
validation, healthy DEV/Production deploys, and absence of runtime consumer or
DB capability. Live Shell verification remains a named supplementary
follow-up. Deployment health is not direct evidence of database contents,
anomalies, topology, or repair needs.

### 20.7 Preserved boundaries

No DEV/Production persistent database query, capture, or modification occurred;
there was no DDL, DML, or backfill; and no scanner/discovery, report/plan
artifact, repair authority, winner selection, relationship correction, hot
maintenance, reconciliation mutation, authentication/authorization change,
E1/E2/F/G owner change, or Production database-content claim was introduced.

```text
AUTH-ID-001H STATIC RECONCILIATION READINESS GUARDRAIL
SOURCE/POLICY GUARDRAIL: IMPLEMENTED AND PRODUCTION-FROZEN
DEV LIVE TOOL VERIFICATION: NOT EXECUTED — RENDER SHELL SELECTOR DISABLED
PRODUCTION LIVE TOOL VERIFICATION: NOT EXECUTED — RENDER SHELL SELECTOR DISABLED
DISCOVERY / SCANNER: NOT IMPLEMENTED
REPORT / PLAN FORMAT: NOT IMPLEMENTED
REPAIR AUTHORITY: NOT IMPLEMENTED OR ASSIGNED
RECONCILIATION MUTATION: NOT IMPLEMENTED
AUTH-ID-001H OVERALL: OPEN — NOT CLOSED
```

## 21. Disposable read-only discovery format and authorization

This section freezes the format and authorization boundary for one future,
separately approved implementation slice. It creates no scanner or runtime
capability. Sections 1–20 remain authoritative and unchanged.

### 21.1 Slice identity and non-authority

The canonical future tool path is:

`tools/discover_identity_registry_anomalies.py`

The first implementation slice is limited to an explicitly supplied disposable
SQLite fixture located under the resolved system temporary directory. This
location restriction is a hard boundary for the first slice; it does not grant
present or future authority to inspect any persistent database.

The slice does not authorize:

- DEV, Production, or canonical `site.db` discovery;
- repair, plan generation, winner selection, authority, or mutation;
- a consumer, route, API, form, UI, or maintenance entrypoint;
- authentication, authorization, identity proof, or mutation instructions; or
- any claim that discovery or scanner implementation already exists.

Discovery output is bounded evidence only. It is not authentication proof,
authorization proof, identity proof, reconciliation approval, or a mutation
instruction.

### 21.2 Exact callable and CLI surface

The only future public module symbols are:

- `IdentityRegistryDiscoveryError`; and
- `discover_identity_registry_anomalies`.

The exact public export tuple is:

```python
__all__ = (
    "IdentityRegistryDiscoveryError",
    "discover_identity_registry_anomalies",
)
```

`IdentityRegistryDiscoveryError` is the single public fail-closed exception
type. Its exact public message and sole public `args` value are:

```text
identity registry discovery failed
```

It has no public detail attributes. Its cause and context are both `None`, and
external raising suppresses implicit chaining. The implementation can retain
only one private non-sensitive classification with the closed values `input`
and `internal`; it cannot retain an input value, path, SQL, exception,
traceback, row, environment value, or database detail.

The exact public callable contract is:

```python
def discover_identity_registry_anomalies(
    *,
    db_path: Path,
    run_id: str,
    captured_at: str,
    tool_commit: str,
) -> dict[str, object]:
    ...
```

All four arguments are mandatory keyword-only arguments. The callable must apply
the same validation, path, read-only, redaction, output-object, and no-touch
contracts as the CLI. It must not accept a connection, URL, file object,
environment-derived default, query override, output sink, callback, authority,
or capability object.

The callable behavior is exact:

- valid inputs plus a complete bounded capture return the exact
  `capture_status = complete` dictionary and do not print or write;
- valid inputs plus schema, query, source, or no-touch incompleteness return the
  exact `capture_status = incomplete` dictionary and do not print or write;
- CLI-value, lexical, path, file-type, sidecar-presence, or SQLite-format
  rejection raises `IdentityRegistryDiscoveryError` with private
  classification `input`; and
- an unexpected implementation, serialization, redaction, or invariant failure
  raises `IdentityRegistryDiscoveryError` with private classification
  `internal`.

The callable never returns `capture_status = error`, never returns a partial
dictionary, and never converts an input rejection or internal failure into an
incomplete dictionary.

The sole private CLI entrypoint is:

```python
def _main(argv: Sequence[str] | None = None) -> int:
    ...
```

`_main` must not be exported. No other public factory, candidate resolver, path
bypass, connection helper, or entrypoint is authorized.

The canonical CLI is:

```text
python -B tools/discover_identity_registry_anomalies.py \
  --db <absolute-disposable-sqlite-path> \
  --run-id <canonical-lowercase-uuidv4> \
  --captured-at <RFC3339-UTC-seconds> \
  --tool-commit <40-lowercase-hex>
```

The parser must accept exactly those four mandatory named options. Option
abbreviation, positional arguments, repeated options, unknown options, and
values beginning with an implicit option expansion must fail closed. The CLI
must provide no default database, positional database, environment fallback,
URL, backend connection, output path, apply, repair, plan, force, or Production
option.

`run_id` must satisfy the E2 canonical lowercase UUIDv4 lexical contract. It is
evidence correlation only. It is not a registry ID, identity proof,
reconciliation authority, approval, or idempotent mutation key.

`captured_at` must be supplied as exact RFC 3339 UTC seconds:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Lexical validation first requires the exact ASCII shape
`[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z`. A strict
Gregorian-calendar datetime parser must then accept the year, month, day, hour,
minute, and second, assign UTC, and format the value back with
`%Y-%m-%dT%H:%M:%SZ`. The formatted value must equal the original input byte
for byte. This rejects year zero, an invalid month or day, February 30, hour
24, minute 60, second 60, fractional seconds, offsets other than `Z`, and leap
second text. Validation does not trim, repair, normalize, or read the current
clock. `tool_commit` must match `[0-9a-f]{40}` exactly.

### 21.3 Disposable path acceptance

`db_path` and `--db` must satisfy every condition below before SQLite is
imported or a connection is attempted:

- the supplied lexical path is absolute;
- the resolved path is strictly below, and is not equal to, the resolved system
  temporary root returned by the standard-library system-temp facility;
- the path already exists and is a regular file;
- the path is not in the repository and is not named `site.db`,
  `site.db-wal`, `site.db-shm`, or `site.db-journal`;
- no supplied or resolved path component is a symbolic link, junction, mount
  substitution, or platform reparse point;
- the file has exactly one hard link;
- the path is not a directory, FIFO, socket, device, URL, URI supplied by the
  caller, or non-SQLite input; and
- the resolved identity remains unchanged between validation, open, capture,
  and final no-touch verification.

Containment must be checked by resolved path components, not string prefix.
Both the lexical path and resolved path must be checked against the repository,
canonical database names, substitutions, and link metadata. A successful
initial check must not suppress final identity and no-touch revalidation.

The tool must not read `APP_DB_PATH`, `DATABASE_URL`, or any other
database-selection environment value. It must not search for, infer, probe, or
guess a database path. Database paths, filenames, path hashes that permit path
guessing, and environment contents must never appear in stdout or external
stderr.

System-temp containment is an input restriction only. It is not evidence that
a file is disposable, trusted, or authorized; every other check remains
mandatory.

### 21.4 SQLite read-only construction

The tool constructs the SQLite URI from the resolved absolute `Path` by the
exact expression:

```python
resolved_path.as_uri() + "?mode=ro&immutable=1"
```

`Path.as_uri()` is the sole path-to-URI conversion. Its standard-library
percent encoding is used exactly once. The tool performs no pre-decoding,
post-decoding, manual quoting, manual unquoting, or second encoding pass. The
caller supplies a filesystem path, never a URI. A literal space, Unicode
character, `#`, `?`, or `%` in a filename remains path data after the one
`Path.as_uri()` conversion and cannot become a fragment or query parameter.

The query suffix is exactly `?mode=ro&immutable=1`, in that order, with no
extra parameter. The caller cannot influence the URI, query string, VFS, cache
mode, or connection options. The connection call passes the constructed URI
and `uri=True`; it passes no caller-controlled keyword arguments. Query
injection, fragment injection, VFS selection, cache selection, parameter
smuggling, and double decoding are forbidden.

Before open, the tool must reject the source if any sibling `-wal`, `-shm`, or
`-journal` file exists.

Immediately after open and before schema or row inspection, the connection must
set and verify connection-local:

```sql
PRAGMA query_only=ON
```

An SQLite authorizer must then fail closed for every operation outside the
fixed read-only query contract. The only authorized SQL sources are immutable
module constants reviewed with the tool. Runtime string interpolation,
identifier interpolation, caller-supplied SQL, query fragments, dynamic SQL,
and extension-defined SQL are forbidden.

The fixed query set is limited to:

- read `sqlite_schema` and the read-only schema metadata that validates the
  three registry tables and their indexes, constraints, columns, and foreign
  keys;
- read connection-local `query_only`, `schema_version`, table, column,
  foreign-key, and index metadata;
- compute fixed aggregate counts and fixed equality, type, range, cardinality,
  parent/child, status, and normalization-provenance predicates over
  `global_identities`, `login_identifier_aliases`, and
  `backend_principal_mappings`; and
- use explicit deterministic `ORDER BY` clauses for every query whose order
  contributes to canonical evidence.

The query set must not read credential tables, usernames, roles, sites,
permissions, sessions, proof material, application business tables, or
external backends.

The authorizer must deny DML, DDL, transaction writes, savepoints, temporary
objects, writable PRAGMAs, `ATTACH`, `DETACH`, extension loading, `VACUUM`,
`REINDEX`, `ANALYZE`, user-defined functions, virtual-table module loading, and
any unresolved operation. SQLite extension loading must remain disabled.

The tool must not:

- import `app`;
- invoke bootstrap, migration, schema ensure, or application initialization;
- import or use PostgreSQL, HTTP, network, or backend connectors;
- create a database, sidecar, temporary SQLite object, output file, cache, log,
  or persistent artifact; or
- modify source bytes or metadata.

Before open and after close, the tool must compare source file identity, raw
byte SHA-256, bytes, size, and mtime, and must verify continued absence of all
three sidecars. Any difference makes the capture `incomplete`; it must not be
reported as `complete`.

### 21.5 Exact output envelope

For a completed or safely bounded incomplete capture, stdout is exactly one
RFC 8259 JSON object encoded as UTF-8 without BOM, followed by one final LF.
There is no other stdout text.

The top-level object contains exactly these keys and types:

| Key | Type | Exact meaning |
|---|---|---|
| `format` | string | Fixed format identifier |
| `schema_version` | integer | Output schema version |
| `run_id` | string | Caller-supplied canonical UUIDv4 correlation value |
| `captured_at` | string | Caller-supplied RFC 3339 UTC-seconds value |
| `tool` | object | Declared source and immutable tool identity |
| `source` | object | Redacted disposable-source evidence |
| `scope` | object | Fixed bounded-observation declaration |
| `capture_status` | string | `complete`, `incomplete`, or reserved `error` |
| `anomalies` | array | The 15 frozen anomaly observations |
| `errors` | array of strings | Sorted unique generic capture reason codes |
| `redaction` | object | Fixed aggregate-only redaction declaration |
| `integrity` | object | Canonical evidence hash |

The fixed values are:

```text
format = "auth-id-001h-disposable-registry-discovery"
schema_version = 1
```

The `tool` object contains exactly:

| Key | Type | Contract |
|---|---|---|
| `commit` | string | Caller-declared 40-lowercase-hex commit |
| `module_sha256` | string | Lowercase SHA-256 of exact module bytes |
| `version` | string | `AUTH_ID_001H_DISPOSABLE_DISCOVERY_V1` |

The `source` object contains exactly:

| Key | Type | Contract |
|---|---|---|
| `classification` | string | `system-temp-disposable-sqlite-fixture` |
| `schema_manifest_sha256` | string or null | Lowercase SHA-256 of the exact projection below; null only when schema metadata capture was incomplete |
| `sha256` | string | Lowercase SHA-256 of source bytes before SQLite open |
| `size_bytes` | nonnegative integer | Source size before SQLite open |

The schema-manifest projection is an in-memory object with exactly this shape:

```text
{
  "format": "auth-id-001h-registry-schema-projection",
  "objects": [schema_object, ...],
  "schema_version": 1,
  "sqlite_schema_version": nonnegative integer,
  "tables": [table_projection, ...]
}
```

Each `schema_object` has exactly:

| Key | Type | Source |
|---|---|---|
| `name` | string | `sqlite_schema.name` |
| `normalized_sql` | string or null | Exact normalization below |
| `sql` | string or null | Exact `sqlite_schema.sql` text |
| `tbl_name` | string | `sqlite_schema.tbl_name` |
| `type` | string | `sqlite_schema.type` |

`objects` contains every `sqlite_schema` row whose `name` does not begin with
`sqlite_`. It includes unrelated tables, indexes, views, and triggers so that
the fingerprint binds the complete non-internal schema. Its sort key is the
five-tuple `(type, name, tbl_name, sql_is_not_null, sql_or_empty)`, ascending
by Unicode code point for strings and with `false` before `true`.

`tables` contains exactly three entries in this fixed order:

1. `global_identities`;
2. `login_identifier_aliases`; and
3. `backend_principal_mappings`.

Each `table_projection` has exactly:

| Key | Type |
|---|---|
| `columns` | array of `column_projection` |
| `foreign_keys` | array of `foreign_key_projection` |
| `indexes` | array of `index_projection` |
| `name` | string |
| `present` | boolean |
| `strict` | boolean or null |
| `without_rowid` | boolean or null |

For a missing expected table, `present` is `false`, `strict` and
`without_rowid` are JSON `null`, and `columns`, `foreign_keys`, and `indexes`
are empty arrays. For a present table, `present` is `true`; `strict` and
`without_rowid` are the boolean projections of the exact `PRAGMA table_list`
values.

Each `column_projection` has exactly:

| Key | Type | Source |
|---|---|---|
| `cid` | nonnegative integer | `PRAGMA table_xinfo.cid` |
| `default_sql` | string or null | `PRAGMA table_xinfo.dflt_value` |
| `hidden` | nonnegative integer | `PRAGMA table_xinfo.hidden` |
| `name` | string | `PRAGMA table_xinfo.name` |
| `not_null` | boolean | Boolean projection of `PRAGMA table_xinfo.notnull` |
| `pk_position` | nonnegative integer | `PRAGMA table_xinfo.pk` |
| `type` | string | `PRAGMA table_xinfo.type` |

`columns` is sorted by `(cid, name)`.

Each `foreign_key_projection` has exactly:

| Key | Type | Source |
|---|---|---|
| `from` | string | `PRAGMA foreign_key_list.from` |
| `id` | nonnegative integer | `PRAGMA foreign_key_list.id` |
| `match` | string | `PRAGMA foreign_key_list.match` |
| `on_delete` | string | `PRAGMA foreign_key_list.on_delete` |
| `on_update` | string | `PRAGMA foreign_key_list.on_update` |
| `seq` | nonnegative integer | `PRAGMA foreign_key_list.seq` |
| `table` | string | `PRAGMA foreign_key_list.table` |
| `to` | string | `PRAGMA foreign_key_list.to` |

`foreign_keys` is sorted by
`(id, seq, table, from, to, on_update, on_delete, match)`.

Each `index_projection` has exactly:

| Key | Type | Source |
|---|---|---|
| `columns` | array of `index_column_projection` | Exact index column metadata |
| `name` | string | `PRAGMA index_list.name` |
| `normalized_sql` | string or null | Exact normalization below |
| `origin` | string | `PRAGMA index_list.origin` |
| `partial` | boolean | Boolean projection of `PRAGMA index_list.partial` |
| `sql` | string or null | Matching `sqlite_schema.sql` |
| `unique` | boolean | Boolean projection of `PRAGMA index_list.unique` |

`indexes` contains every index returned for the expected table, including
SQLite autoindexes, and is sorted by `name`.

Each `index_column_projection` has exactly:

| Key | Type | Source |
|---|---|---|
| `cid` | integer | `PRAGMA index_xinfo.cid` |
| `collation` | string | `PRAGMA index_xinfo.coll` |
| `descending` | boolean | Boolean projection of `PRAGMA index_xinfo.desc` |
| `key` | boolean | Boolean projection of `PRAGMA index_xinfo.key` |
| `name` | string or null | `PRAGMA index_xinfo.name` |
| `seqno` | nonnegative integer | `PRAGMA index_xinfo.seqno` |

`index_projection.columns` is sorted by `seqno`.

For every SQL field, null remains JSON `null`. A non-null SQL value participates
twice: `sql` is the exact SQLite text, and `normalized_sql` is exactly
`" ".join(sql.strip().lower().split())`. No other SQL parsing, quoting,
rewriting, comment removal, or normalization occurs.

Object keys use Section 21.8 lexicographic serialization. Every array uses the
fixed or tuple sort above. The projection fingerprint is the lowercase SHA-256
of the Section 21.8 canonical UTF-8 JSON bytes without a final LF.

Missing expected objects use the explicit missing-table representation above.
Missing indexes are represented by absence from the owning table's `indexes`
array. Extra non-internal objects remain in `objects`; extra indexes on an
expected table also remain in that table's `indexes`. Type, column, foreign-key,
constraint, index, SQL, strictness, and `WITHOUT ROWID` drift are represented
by the observed values without substitution.

If every projection query completes, the hash is populated even when schema
drift exists. If any projection query fails or returns a structurally invalid
metadata row, the hash is JSON `null`, `capture_status` is `incomplete`, and
the schema decision table in Section 21.7 applies.

This contract does not import, call, or reuse
`tools/capture_schema_manifest.py`, its CLI, output directories, or
artifact-writing paths. It reuses only the general RFC 8259 canonicalization
recipe already restated exactly in Section 21.8 and performs the projection
entirely in memory. Raw schema SQL and the projection object do not appear in
discovery stdout.

The `scope` object contains exactly:

```json
{"backend_revalidation":false,"fixture":"system-temp-disposable-sqlite","historical_ledger":false,"production":false,"snapshot_count":1}
```

The `redaction` object contains exactly:

```json
{"policy":"auth-id-001h-aggregate-only-v1"}
```

The `integrity` object contains exactly:

```text
evidence_sha256: string
```

`capture_status` is limited to `complete`, `incomplete`, and `error`.
`unsupported` and `indeterminate` are per-anomaly observation states, not H
dispositions and not top-level success values. The first implementation must
not emit `capture_status = error`; an internal fail-closed error uses exit `4`
without an evidence bundle. The value is reserved to prevent an incompatible
future schema change and requires a later authorization before use.

The output must never contain `PASS`.

### 21.6 Per-anomaly schema

`anomalies` contains every frozen Section 5 anomaly code exactly once and in
the exact Section 5 taxonomy order. No code is permitted to be added, removed, renamed,
coerced, duplicated, or sorted into a different order.

Each array item contains exactly:

| Key | Type |
|---|---|
| `code` | string |
| `state` | string |
| `disposition` | string |
| `count` | nonnegative integer or null |
| `reason_code` | string |

`state` is limited to:

- `observed`;
- `not_observed`;
- `unsupported`; and
- `indeterminate`.

For `observed` and `not_observed`, `count` is a nonnegative integer.
`not_observed` requires `count = 0`; `observed` requires `count > 0`. For
`unsupported` and `indeterminate`, `count` is JSON `null`.

`disposition` is the exact Section 5 disposition for that anomaly and must be
one of the closed Section 6 values. Observation state does not alter or replace
disposition.

The generic `reason_code` vocabulary is closed to:

- `bounded_violation_observed`;
- `bounded_violation_not_observed`;
- `backend_revalidation_required`;
- `cross_backend_subject_evidence_required`;
- `historical_ledger_unavailable`;
- `single_snapshot_cannot_exclude_concurrency_drift`;
- `schema_contract_unavailable`;
- `bounded_query_incomplete`.

The first two reason codes correspond only to `observed` and `not_observed`.
The next two correspond only to `unsupported`. The remaining four correspond
only to `indeterminate`.

No anomaly item is permitted to contain a row, raw value, sample, username, alias,
normalized lookup key, backend principal key, opaque registry ID, confidence,
candidate, winner, repair suggestion, priority score, or free-form reason.

### 21.7 First-slice discoverability boundary

The first slice uses only the predicates and count units in this section.
Every count is computed in memory or by a fixed aggregate query and is emitted
only as an integer. Internal grouping keys, individual values, and per-group
hashes are never emitted and never added separately to the evidence hash. The
whole-source byte hash remains the file-integrity value defined in Section
21.5; it is not a grouping-key hash.

#### 21.7.1 Exact schema-drift unit

`schema_object_drift.count` is the size of a deduplicated set of atomic schema
drift facts. Each fact is the exact six-element canonical JSON array:

```text
[object_kind, owner_name, subject_name, attribute, expected_value, observed_value]
```

The first four elements are strings. `expected_value` and `observed_value` are
the exact JSON scalar, object, or tuple-array values from the frozen contract
and observed projection; JSON `null` is the absence sentinel. Facts are
deduplicated by their Section 21.8 canonical JSON bytes. The fact array is used
for deduplication only and is not emitted or separately hashed.

Atomic facts are generated exactly as follows:

- a missing expected table contributes
  `["table",table_name,table_name,"present",true,false]` and contributes no
  child column, foreign-key, or index facts;
- a present table with incorrect `strict` or `without_rowid` contributes one
  fact for each incorrect attribute, using the expected and observed booleans;
- a missing expected column contributes one fact with the expected complete
  `column_projection` and observed JSON `null`;
- an extra column contributes one fact with expected JSON `null` and the
  observed complete `column_projection`;
- a present expected column contributes one fact for each mismatch in
  `type`, `not_null`, `default_sql`, `pk_position`, or `hidden`, using the
  exact expected and observed scalar;
- the symmetric difference between expected and observed foreign-key tuples
  contributes one fact per tuple, placing the tuple on its present side and
  JSON `null` on its absent side;
- a missing approved index contributes one fact with the expected complete
  `index_projection` and observed JSON `null`, and contributes no child index
  facts;
- an extra index owned by an expected table contributes one fact with expected
  JSON `null` and the observed complete `index_projection`;
- a present approved index contributes one fact for each mismatch in `unique`,
  `origin`, `partial`, or `normalized_sql`, using the exact expected and
  observed scalar;
- the symmetric difference between expected and observed index-column tuples
  contributes one fact per tuple, placing the tuple on its present side and
  JSON `null` on its absent side; and
- a present expected table whose `normalized_sql` differs from the frozen E1
  table SQL contributes one fact with the exact expected and observed
  normalized strings, covering CHECK and table-constraint text not represented
  by the other tuples.

Fact labels are exact:

| Fact | `object_kind` | `owner_name` | `subject_name` | `attribute` |
|---|---|---|---|---|
| Table presence or table attribute | `table` | table name | table name | `present`, `strict`, or `without_rowid` |
| Column presence | `column` | table name | column name | `present` |
| Column attribute | `column` | table name | column name | Exact mismatching field name |
| Foreign-key tuple difference | `foreign_key` | table name | `foreign_key` | `tuple` |
| Index presence | `index` | owning table name | index name | `present` |
| Index attribute | `index` | owning table name | index name | Exact mismatching field name |
| Index-column tuple difference | `index_column` | index name | `index_column` | `tuple` |
| Table SQL difference | `table_sql` | table name | table name | `normalized_sql` |
| Extra owned view or trigger | `owned_object` | expected table name | object name | `present` |

A renamed column contributes two facts: one missing expected column and one
extra observed column. An unrelated schema object whose `name` and `tbl_name`
are both outside the three expected table names and approved index names
contributes zero drift facts. It remains in the schema projection and therefore
changes the schema-manifest fingerprint. A view, trigger, or unapproved index
whose `tbl_name` is an expected table contributes one fact with expected JSON
`null` and the observed complete `schema_object`; an unapproved index already
counted by the index rule is not counted again.

The expected values are exactly the `VALID_SCHEMA_SQL`, `EXPECTED_TABLES`,
`ALIAS_ALLOWED_EXPLICIT_INDEXES`, `ALIAS_ALLOWED_PARTIAL_UNIQUE_COLUMNS`,
`ALIAS_ALLOWED_PARTIAL_UNIQUE_WHERE`, and `MAPPING_ALLOWED_UNIQUE_SETS`
constants in approved schema-checker blob
`d322d051a7b3060f4d53598a5dbfb6e65f784965`. The future module transcribes
those immutable values and the checker verifies exact equality; it does not
import or call `app`, the schema checker, or the serializer. SQL expected values
use the exact Section 21.5 normalization recipe. A zero-size fact set yields
`not_observed`, count `0`, and `bounded_violation_not_observed`. A nonzero fact
set yields `observed`, its set size, and `bounded_violation_observed`. Metadata
capture failure yields `indeterminate`, count `null`, and
`schema_contract_unavailable`.

#### 21.7.2 Exact registry-row predicates and units

The following nine contracts are closed:

| Anomaly code | Exact predicate | Aggregation key and count unit | Duplicate, null, and type rule |
|---|---|---|---|
| `schema_object_drift` | Atomic fact set in Section 21.7.1 is nonempty | One deduplicated atomic schema fact; count is fact-set size | Missing parents suppress their child facts; identical facts count once |
| `noncanonical_registry_id` | The stored value fails the exact E2 validator for any of `global_identities.global_identity_id`, `login_identifier_aliases.login_identifier_alias_id`, `login_identifier_aliases.global_identity_id`, `backend_principal_mappings.backend_principal_mapping_id`, or `backend_principal_mappings.global_identity_id` | One stored field occurrence; count is the sum of failing occurrences across the five fixed columns | Repeated equal values in different rows or columns count separately; null and every non-text SQLite storage type fail |
| `invalid_registry_status` | A value is outside its exact closed set: identity `{active,disabled}`, alias `{active,disabled,superseded}`, mapping `{active,disabled}` | One stored status field occurrence; count is the sum across the three status columns | Repeated values count per row; null and every non-text storage type fail |
| `invalid_backend_principal_key` | A mapping row has `backend_kind` outside `{internal,vendor}`, non-text/null `backend_kind`, non-integer/null `backend_principal_key`, or integer key `<= 0` | One mapping row; count is the number of rows satisfying any predicate branch | A row failing multiple branches counts once; equal invalid keys in different rows count separately |
| `orphan_fk_relationship` | An alias or mapping row has a null/non-text `global_identity_id`, or no identity row has an exactly equal text `global_identity_id` | One child row; count is the sum of violating alias rows and mapping rows | A child row counts once; duplicate child references count per row; no fallback normalization occurs |
| `normalized_alias_ambiguity` | An eligible alias set has at least two distinct `global_identity_id` values for one exact tuple `(normalization_algorithm_family, normalization_profile, unicode_data_version, trim_conformance_profile, normalized_lookup_key)`; eligibility requires active alias, algorithm `NFKC_CASEFOLD_V1`, profile `NFKC_CASEFOLD_V1_UCD16_0_0`, Unicode version `16.0.0`, trim profile `PY3146_UCD16_0_0_STRIP_V1`, active identity, and at least one active registry mapping for that identity | One violating five-field tuple; count is the number of violating groups | Multiple aliases for the same identity are deduplicated by identity before cardinality; a null/non-text grouping field or identity ID makes this category `indeterminate` rather than forming a group |
| `active_exact_alias_collision` | At least two active alias rows share the exact tuple `(global_identity_id, raw_alias, normalized_lookup_key, normalization_algorithm_family, normalization_profile, unicode_data_version, trim_conformance_profile)` | One violating seven-field tuple; count is the number of violating groups | Every row participates once in its group; a null/non-text grouping field makes this category `indeterminate` |
| `backend_principal_inconsistent_mapping` | At least one exact `(backend_kind, backend_principal_key)` group contains two or more distinct `global_identity_id` values | One violating backend-principal tuple; count is the number of violating groups | Duplicate rows mapping the same principal to the same identity do not increase group cardinality; an invalid/null kind, key, or identity field makes this category `indeterminate` and is still counted by its separately applicable anomaly |
| `incompatible_backend_cardinality` | At least one exact `(global_identity_id, backend_kind)` group contains two or more distinct positive-integer `backend_principal_key` values | One violating identity/backend-kind tuple; count is the number of violating groups | Duplicate rows for the same principal do not increase cardinality; an invalid/null identity, kind, or key field makes this category `indeterminate` |

For every predicate, exact equality is SQLite binary value equality after the
explicit storage-type checks above. There is no trimming, case folding,
coercion, numeric text conversion, fuzzy comparison, or fallback. Group order
does not affect counts. No grouping key, member value, row identifier, sample,
or per-key digest appears in output.

If the schema decision table forbids the relevant row query, the category is
`indeterminate`, count `null`, and reason
`schema_contract_unavailable`. If an authorized fixed query for a category
fails, that category is `indeterminate`, count `null`, and reason
`bounded_query_incomplete`.

`invalid_provenance` is always `indeterminate`, count `null`, and
`historical_ledger_unavailable` in the first slice. The current columns do not
provide the complete frozen historical/event tuple.

`conflicting_principals_different_identities` is always `unsupported`, count
`null`, and `cross_backend_subject_evidence_required`. The tool cannot infer a
subject pair from alias, normalized key, username, display text, `vendor_name`,
or arbitrary internal/vendor topology.

`disabled_superseded_relationship_inconsistency` is always `indeterminate`,
count `null`, and `historical_ledger_unavailable`.

`source_principal_missing_inactive_stale` is always `unsupported`, count
`null`, and `backend_revalidation_required`.

`snapshot_concurrency_drift` is always `indeterminate`, count `null`, and
`single_snapshot_cannot_exclude_concurrency_drift`.

`unknown_unclassified_anomaly` is never `observed` in the first slice. It is
`not_observed`, count `0`, and `bounded_violation_not_observed` when schema
projection and every authorized fixed row query finish. It is `indeterminate`,
count `null`, and `schema_contract_unavailable` after schema metadata failure
or a row-query prohibition. It is `indeterminate`, count `null`, and
`bounded_query_incomplete` after any fixed row-query failure. It never absorbs
schema drift, unsupported states, malformed input, source mutation, or another
category's count.

#### 21.7.3 Schema and query decision table

This table is the sole schema/query continuation policy:

| Condition | Exit / status | Exact `errors` | `schema_object_drift` | Remaining states | Row-query rule |
|---|---|---|---|---|---|
| Exact registry schema match | `0` / `complete` | `[]` | `not_observed`, `0`, `bounded_violation_not_observed` | Apply every fixed category rule | Execute every fixed row query |
| Extra unrelated object only | `0` / `complete` | `[]` | `not_observed`, `0`, `bounded_violation_not_observed` | Apply every fixed category rule; fingerprint reflects the object | Execute every fixed row query |
| Missing approved index, extra owned index/object, or approved-index attribute/column/SQL drift | `3` / `incomplete` | `["schema_drift"]` | `observed`, exact fact count, `bounded_violation_observed` | Apply every fixed category rule | Execute every fixed row query; no row predicate depends on index presence |
| Missing expected table | `3` / `incomplete` | `["schema_drift"]` | `observed`, exact fact count, `bounded_violation_observed` | All table-bounded categories are `indeterminate`/`null`/`schema_contract_unavailable`; fixed backend, ledger, concurrency, and unknown rules remain | Execute no row query |
| Missing, extra, renamed, type-drifted, nullable-drifted, default-drifted, PK-drifted, or hidden-drifted column | `3` / `incomplete` | `["schema_drift"]` | `observed`, exact fact count, `bounded_violation_observed` | All table-bounded categories are `indeterminate`/`null`/`schema_contract_unavailable`; fixed backend, ledger, concurrency, and unknown rules remain | Execute no row query |
| FK, CHECK, UNIQUE, strictness, `WITHOUT ROWID`, or table normalized-SQL drift with all expected tables and columns otherwise exact | `3` / `incomplete` | `["schema_drift"]` | `observed`, exact fact count, `bounded_violation_observed` | Apply every fixed category rule | Execute every fixed row query |
| Schema metadata query failure or structurally invalid metadata row | `3` / `incomplete` | `["schema_capture_incomplete"]` | `indeterminate`, `null`, `schema_contract_unavailable` | All table-bounded categories and unknown are `indeterminate`/`null`/`schema_contract_unavailable`; fixed backend, ledger, and concurrency rules remain | Execute no row query |
| One fixed row query fails after an exact or query-compatible drifted schema | `3` / `incomplete` | `["bounded_query_incomplete"]`, plus `schema_drift` exactly when drift facts exist | Preserve the schema result already determined | The failed category and unknown are `indeterminate`/`null`/`bounded_query_incomplete`; every other category preserves its fixed result | Continue independent fixed queries; do not retry, rewrite, substitute, or broaden the failed query |

If more than one table row in the decision table applies, the most restrictive
row-query rule wins: `execute no row query` overrides continuation. The
`errors` array is the sorted union of the exact listed codes. Source identity,
bytes, size, mtime, or sidecar change is governed by Section 21.9 and cannot be
downgraded by a schema result.

Backend-dependent categories are never `not_observed` in this slice.
Ledger/history-dependent categories never infer historical legality from
current rows. A single snapshot never claims that concurrency drift was
excluded.

No observation is permitted to select a winner, recommend repair, infer
authority, or propose merge, remap, reassignment, lifecycle transition, or
relationship correction.

### 21.8 Canonical serialization and evidence hash

Serialization is RFC 8259 JSON with:

- UTF-8 encoding;
- no BOM;
- lexicographic object-key ordering at every depth;
- arrays in their frozen order, or lexicographic complete-tuple order for
  explicitly set-like schema metadata;
- integers preserved as integers and never converted to floating point;
- `,` and `:` separators;
- no whitespace outside JSON string content; and
- exactly one final LF after the top-level object.

Serialization uses these exact arguments:

```python
json.dumps(
    value,
    ensure_ascii=False,
    allow_nan=False,
    sort_keys=True,
    separators=(",", ":"),
)
```

The evidence hash is calculated by:

1. constructing the complete output object;
2. removing only the `integrity.evidence_sha256` member while retaining an
   empty `integrity` object;
3. serializing that object canonically without the external final LF;
4. hashing those UTF-8 bytes with SHA-256;
5. encoding the digest as lowercase 64-hex; and
6. inserting it as `integrity.evidence_sha256` before final canonical
   serialization.

Given identical source bytes and identical values for all four CLI inputs, the
complete stdout bytes must be identical. `captured_at` is caller-supplied; the
tool must not read the current clock. Output must not depend on locale, local
timezone, filesystem enumeration order, dictionary insertion order, SQLite
incidental row order, randomized hashing, process ID, hostname, or temporary
path text.

### 21.9 Exit and error semantics

The exact exit codes are:

- `0`: the bounded capture completed; observed, unsupported, and indeterminate
  categories are permitted;
- `2`: CLI, path, lexical format, file-type, sidecar-presence, or SQLite-format
  input rejection;
- `3`: source, schema, query, or final no-touch evidence is incomplete; and
- `4`: internal fail-closed error.

`_main` performs no discovery logic outside the public callable. It parses the
four CLI values without automatic usage, help, or exception output, invokes
`discover_identity_registry_anomalies` once, and applies this exact mapping:

| Callable outcome | `_main` behavior |
|---|---|
| Returns a dictionary with `capture_status = complete` | Canonically serialize once, write it to stdout, write zero stderr bytes, return `0` |
| Returns a dictionary with `capture_status = incomplete` | Canonically serialize once, write it to stdout, write the fixed incomplete marker to stderr, return `3` |
| Raises `IdentityRegistryDiscoveryError` classified privately as `input` | Write zero stdout bytes, write the fixed input-rejected marker to stderr, return `2` |
| Raises `IdentityRegistryDiscoveryError` classified privately as `internal` | Write zero stdout bytes, write the fixed internal-error marker to stderr, return `4` |
| Returns any other type/status, raises another exception, or fails serialization/output invariants | Discard any un-emitted bundle, write zero stdout bytes, write the fixed internal-error marker to stderr, return `4` |

Parser rejection, including `-h` or `--help`, occurs before callable invocation
and maps directly to zero stdout bytes, the fixed input-rejected marker, and
exit `2`.

The result is fully serialized and redaction-validated in memory before either
stdout or stderr is written. `_main` performs at most one stdout write and one
stderr write. A serialization or validation failure writes no partial JSON.
The private `input`/`internal` classification is not exported, serialized,
logged, or included in the public exception message or public attributes.

Exit `0` emits one `capture_status = complete` JSON object and zero stderr
bytes. Exit `3` emits one fully constructed `capture_status = incomplete`
JSON object and the exact stderr marker:

```text
AUTH-ID-001H DISCOVERY INCOMPLETE
```

Exit `2` emits zero stdout bytes and the exact stderr marker:

```text
AUTH-ID-001H DISCOVERY INPUT REJECTED
```

Exit `4` emits zero stdout bytes and the exact stderr marker:

```text
AUTH-ID-001H DISCOVERY INTERNAL ERROR
```

Each stderr marker has one final LF and no other bytes. No error path is permitted to emit a
candidate, path, filename, SQL, exception type, exception representation,
cause, context, traceback, environment value, database detail, or raw input.
Exception chaining and implicit context must be suppressed at the external
boundary.

The top-level `errors` vocabulary for exit `3` is closed to:

- `bounded_query_incomplete`;
- `schema_capture_incomplete`;
- `schema_drift`;
- `sidecar_state_changed`;
- `source_identity_changed`; and
- `source_read_incomplete`.

The array is sorted lexicographically and contains no duplicates. Exit `0`
requires `errors = []`. Malformed, non-SQLite, unreadable, or rejected input
must never produce an evidence bundle that appears complete.

Final source/no-touch failures use this exact rule:

- source byte-read failure before SQLite open is an input rejection and exit
  `2`;
- source identity, bytes, SHA-256, size, or mtime change after initial
  validation produces exit `3`, `capture_status = incomplete`, and
  `errors = ["source_identity_changed"]`, combined with any earlier error code;
- appearance or change of `-wal`, `-shm`, or `-journal` produces exit `3`,
  `capture_status = incomplete`, and `errors = ["sidecar_state_changed"]`,
  combined with any earlier error code; and
- inability to perform final source/no-touch reads produces exit `3`,
  `capture_status = incomplete`, and `errors = ["source_read_incomplete"]`,
  combined with any earlier error code.

After any final no-touch failure, `schema_object_drift`, every table-bounded
category, and `unknown_unclassified_anomaly` are `indeterminate`, count `null`,
and `bounded_query_incomplete`; fixed backend, ledger, and concurrency states
remain as frozen in Section 21.7. No pre-failure row count survives as an
observed or not-observed result.

### 21.10 Empty, incomplete and unsupported semantics

Empty valid registry tables do not prove that all H anomalies, external
backends, history, concurrency, DEV, or Production state are clean.

For an empty structurally valid fixture:

- table/schema-bounded categories whose fixed queries complete are
  `not_observed` when their exact count is zero;
- backend-dependent categories remain `unsupported`;
- ledger/history-dependent categories remain `indeterminate`;
- `snapshot_concurrency_drift` remains `indeterminate`; and
- top-level `complete` means only that every observation authorized by this
  first-slice scope completed.

Top-level `complete` is not a health, policy approval, deployment, authority,
backend, or Production assertion. Observed anomalies do not change exit `0`;
discovery is not a policy approval gate.

Schema drift, partial reads, fixed-query failure, changed source identity or
bytes, changed size or mtime, or any sidecar appearance or change must not be
reported as complete. Unsupported and indeterminate observations are explicit
bounded results and must not be silently converted to zero,
`not_observed`, clean, or `PASS`.

### 21.11 Redaction contract

Stdout, stderr, exception text, logging, and any externally visible object must
not contain:

- a database path, filename, directory, environment name/value, or connection
  string;
- username, raw alias, normalized lookup key, or backend principal key;
- credential, password, password hash, session, cookie, or token;
- role, site, permission, authority, or proof material;
- raw SQL row values, raw schema SQL, or candidate IDs;
- an opaque registry ID; or
- a candidate, winner, repair target, topology subject, or account-existence
  signal.

The first slice permits only aggregate counts, closed generic reason codes,
fixed scope declarations, tool/source hashes, source size, and the redacted
schema-manifest fingerprint. A future independently authorized controlled
audit is the only scope that can use opaque registry IDs; this first slice
forbids them.

The tool must not create logs, reports, plans, bundles, output files, temporary
artifacts, or exception dumps. Redaction failure is an internal fail-closed
error and cannot be downgraded to an incomplete or successful capture.

### 21.12 Narrow static-checker authorization contract

This section authorizes only the shape of a future checker change. It does not
modify the checker and does not activate an allowance.

A future checker allowance can accept the discovery implementation only when
all of these independently verified conditions hold:

- exact canonical path
  `tools/discover_identity_registry_anomalies.py`;
- exact public `__all__`, public class, public callable, private `_main`, and no
  extra entrypoint or capability export;
- exact four-option mandatory CLI with the validators in Section 21.2;
- exact path rejection and no-environment invariants in Section 21.3;
- exact read-only URI construction, fixed SQL constants, authorizer, and
  no-touch invariants in Section 21.4;
- exact JSON schema, version, reason vocabularies, state matrix, serializer,
  evidence hash, and exit behavior in Sections 21.5–21.11; and
- no output file, app import, bootstrap, migration, network, PostgreSQL,
  backend connector, authority, plan, winner, repair, or mutation capability.

The checker must prove those positive structural invariants. It must not use:

- a whole-file or whole-function exemption;
- token suppression;
- a generic scanner, reporter, CLI, or evidence-generator allowlist;
- a path-prefix wildcard;
- an unresolved dynamic-dispatch exception;
- a capability-name-only exemption; or
- an exemption based only on `if __name__ == "__main__"`.

Any extra entrypoint, symbol, option, path source, write operation, writable
PRAGMA, dynamic SQL, artifact output, environment fallback, raw evidence,
report/plan expansion, winner selection, repair, relationship correction,
authority, consumer, or Production meaning must re-trigger the applicable
original issue code. The allowance must not weaken lifecycle, linking, E2,
Production-access, oracle, redaction, dynamic-capability, or mutation guards.

### 21.13 Mandatory future acceptance matrix

A future implementation and checker proposal must demonstrate at least:

- exact canonical path acceptance and wrong-path rejection;
- exact symbol/export acceptance and wrong or extra symbol rejection;
- exact four-option CLI acceptance and omitted, repeated, positional, unknown,
  abbreviated, extra, default, and environment-fallback rejection;
- canonical/repository database, `site.db`, sidecar, URL, and non-temp
  rejection;
- symlink, junction, reparse-point, hardlink, mount, and path-substitution
  rejection;
- exact one-pass `Path.as_uri()` behavior for filenames containing spaces,
  Unicode, `#`, `?`, and `%`, with query/fragment/VFS/cache injection
  rejection;
- strict `captured_at` Gregorian validity and exact UTC-seconds round-trip,
  including February 30, year zero, invalid month/day, hour 24, minute 60,
  second 60, fractional seconds, offset, whitespace, and repair rejection;
- direct callable complete return, incomplete return, fixed-message input
  exception, fixed-message internal exception, absent cause/context, private
  classification, and exact `_main` exit mapping;
- regular disposable SQLite acceptance with immutable read-only open;
- writable connection, DML, DDL, transaction write, temporary object, writable
  PRAGMA, `ATTACH`, `DETACH`, extension load, `VACUUM`, `REINDEX`, `ANALYZE`,
  user-defined-function, and dynamic-SQL rejection;
- artifact/file/log output rejection;
- `app`, bootstrap, migration, and schema-ensure import/call rejection;
- zero PostgreSQL, HTTP, network, and backend-connector attempts;
- raw evidence, path, environment, row, alias, normalized key, backend key,
  opaque ID, credential, authority, candidate, and oracle leakage rejection;
- report, plan, winner, repair, relationship-correction, authority, consumer,
  maintenance, and mutation expansion rejection;
- clean empty and structurally valid populated fixtures;
- one isolated fixture for every table/schema-bounded observable anomaly;
- simultaneous anomalies with exact taxonomy ordering and aggregate counts;
- exact unsupported and indeterminate behavior for backend, subject-pair,
  ledger, and concurrency-dependent categories;
- missing, extra, and drifted schema; malformed/non-SQLite input; unreadable
  source; fixed-query failure; and source/sidecar mutation;
- source bytes, identity, size, mtime, and sidecars unchanged after every
  accepted capture;
- deterministic A/A byte equality, controlled A/B difference, evidence-hash
  reconstruction, and module-hash verification;
- generic stderr exact-byte tests and zero stderr on exit `0`;
- upstream lifecycle, linking, and reconciliation guard regression;
- isolated full smoke; and
- canonical repository database and sidecars unchanged before and after all
  validation.

All fixtures, sentinels, pycache, and validation artifacts must remain in a
controlled system-temp root and be removed after validation. Implementation
validation must not access DEV, Production, Render, `DATABASE_URL`,
`APP_DB_PATH`, or any persistent database.

### 21.14 Preserved status

This Section 21 freezes a future discovery format and a future narrow
authorization contract only. It does not implement the tool, change the static
checker, create an evidence artifact, or authorize a database scan.

```text
DISCOVERY FORMAT / AUTHORIZATION CONTRACT：FROZEN
DISCOVERY / SCANNER IMPLEMENTATION：NOT STARTED
REPORT / PLAN IMPLEMENTATION：NOT STARTED
REPAIR AUTHORITY：NOT IMPLEMENTED OR ASSIGNED
RECONCILIATION MUTATION：NOT IMPLEMENTED
AUTH-ID-001H OVERALL：OPEN — NOT CLOSED
```
