Status: schema baseline

Scope: docs-only

Implementation status: not started

# AUTH-ID-001E — Registry Schema Baseline

## 1. Baseline and scope

### 1.1 Frozen baseline

- Canonical repository baseline:
  - `main` = `develop` = `origin/main` = `origin/develop` =
    `2b69ce05736b45f83c8f0d6b7df23dc69295ac5d`
- Production deploy:
  - `dep-d9c1i2km0tmc739c9p5g`
- Production status at baseline check:
  - live / healthy
- Active normalization profile:
  - `NFKC_CASEFOLD_V1_UCD16_0_0`
- Upstream frozen documents:
  - `docs/auth_ux_001a_unified_login_design_freeze.md`
  - `docs/auth_id_001c_global_account_identity_registry_design_baseline.md`
  - `docs/auth_id_001d_identifier_normalization_policy.md`
- Required runtime evidence status:
  - `AUTH-ID-001D1` = `RUNTIME EVIDENCE COMPLETE`

### 1.2 Slice purpose

This document converts the architecture selected by `AUTH-ID-001C` into a precise physical-schema baseline for later implementation review.

Chosen exact architecture:

- Separate Global Identity Registry
- Explicit Backend Principal Mappings
- Versioned Login Identifier Alias records

This slice is docs-only. It does not create schema, execute DDL, run migration, perform backfill, change authority, change credential verification, or modify runtime behavior.

### 1.3 Reading rule

This document distinguishes four statement classes:

- Observed fact:
  directly evidenced by frozen documents or accepted runtime aggregates
- Design inference:
  conclusion drawn from observed fact and frozen security requirements
- Frozen schema decision:
  physical-schema baseline approved for later implementation slices
- Deferred decision:
  intentionally postponed item with an owner slice and invariant

## 2. Evidence integration from AUTH-ID-001D1

### 2.1 Observed fact

Accepted aggregate-only runtime evidence:

- DEV:
  - internal accounts = `3`
  - vendor accounts = `5`
- Production:
  - internal accounts = `2`
  - vendor accounts = `0`
- Exact D profile collision:
  - DEV = `0`
  - Production = `0`
- C → D newly-colliding groups:
  - DEV = `0`
  - Production = `0`
- C → D newly-distinct groups:
  - DEV = `0`
  - Production = `0`
- invalid / control / format evidence:
  - DEV = `0`
  - Production = `0`
- UCD `16.0.0` and all `26` normative vectors:
  - DEV = PASS
  - Production = PASS
- no-write proof:
  - DEV = PASS
  - Production = PASS
- Runtime Python:
  - DEV = `3.14.3`
  - Production = `3.14.3`

No username, vendor label, identifier sample, credential, secret, hash, or URL is recorded here.

### 2.2 Design inference

- Python patch version is evidence metadata, not profile identity.
- Profile compatibility is determined by:
  - UCD `16.0.0`
  - pinned boundary-trim conformance
  - normative vector conformance
- Current zero-collision evidence does not justify assuming:
  - global normalized uniqueness
  - automatic cross-backend linking
  - future absence of ambiguity

### 2.3 Frozen schema decision

- The registry schema must preserve ambiguous candidate possibility even when current evidence shows zero collisions.
- Normalized lookup data must carry explicit provenance rather than relying on implicit runtime assumptions.
- No schema decision in this slice may convert a recognition key into identity primary key, credential authority, or authorization authority.

## 3. Registry schema inventory

### 3.1 Inventory boundary

This baseline defines exactly three registry-owned core structures:

- `global_identities`
- `login_identifier_aliases`
- `backend_principal_mappings`

No vendor organization schema is defined here.

### 3.2 Additional registry-owned metadata

Only metadata necessary to satisfy frozen provenance, lifecycle, constraint, and reconciliation boundaries is included. No extra vendor-organization, permission, session, routing, or workflow structure is introduced.

## 4. Global identity contract

### 4.1 Observed fact

- `AUTH-ID-001C` froze `GlobalIdentity` as an opaque key distinct from alias and backend principal.
- Current credential authority remains backend-local:
  - internal principal = `users.id`
  - vendor principal = `vendor_accounts.id` / session `vendor_account_id`

### 4.2 Frozen schema decision

- `global_identity_id` is a stable opaque key.
- Username or normalized alias must not be the global identity primary key.
- Global identity records must not store:
  - password hash
  - password material
  - credential secret
  - role authority
  - site authority
  - sheet authority
  - vendor authority
- Global identity lifecycle is intentionally minimal in this baseline.

Minimum frozen lifecycle set:

- `active`
- `disabled`

Meaning:

- `active`:
  eligible to remain a recognition candidate if backed by valid alias and valid backend mapping
- `disabled`:
  must not become an authority-bearing session outcome through registry recognition alone

Frozen creation default:

- `registry_status` default must be `disabled`
- future creation flow must not rely on default `active`

Frozen effect of disable / deactivate:

- disable prevents registry identity from being treated as a successful recognition-to-authentication handoff target by itself
- disable does not replace backend re-canonicalization requirements
- disable does not grant or remove business authorization directly
- disabled global identity does not participate in candidate lookup
- an active global identity is only candidate-eligible when it also has:
  - at least one active alias
  - at least one active backend mapping

Required provenance fields:

- created-at metadata
- updated-at metadata
- created-by / source provenance marker
- updated-by / source provenance marker

### 4.3 Forbidden usage

Global identity must not be used as:

- a password-verification source
- a browser-session authority shortcut
- a role subject
- a site-permission subject
- a vendor organization identity
- a trusted-target authority key

### 4.4 Deferred decision

Merge, tombstone, split, and hot-maintenance reconciliation states are not safely defined here and are explicitly deferred.

## 5. Login identifier alias contract

### 5.1 Observed fact

- `AUTH-ID-001D` froze raw alias and normalized key as separate concepts.
- `AUTH-ID-001D` froze the active profile:
  - `NFKC_CASEFOLD_V1_UCD16_0_0`
- `AUTH-ID-001D1` proved exact-profile compatibility and no-write evidence in DEV and Production.

### 5.2 Frozen schema decision

Each alias record must separate:

- raw alias
- normalized lookup key
- normalization provenance

Raw alias:

- preserved for display, audit, and compatibility
- not an identity primary key
- not authorization authority
- not a credential source

Normalized lookup key:

- used only for recognition candidate lookup
- not a credential
- not a global identity primary key
- not authorization authority
- not proof that two candidates are the same actor

Each normalized key record must preserve provenance that can distinguish at least:

- logical algorithm family
- active profile / version
- Unicode data version
- boundary-trim / conformance profile

Frozen provenance fields:

- `normalization_algorithm_family`
- `normalization_profile`
- `unicode_data_version`
- `trim_conformance_profile`

### 5.3 Exact candidate eligibility predicate

Frozen candidate identity collection must require all of the following:

- `login_identifier_aliases.alias_status = active`
- alias normalization provenance exactly matches the requested active profile, including trim token `PY3146_UCD16_0_0_STRIP_V1`
- `normalized_lookup_key` exactly matches the requested lookup key
- `global_identities.registry_status = active`
- at least one related backend mapping exists with `mapping_status = active`
- results are deduplicated by `global_identity_id`

Frozen exclusions:

- `disabled` alias does not participate in candidate lookup
- `superseded` alias does not participate in candidate lookup
- `disabled` global identity does not participate in candidate lookup
- `disabled` mapping does not make an identity candidate-eligible

Frozen runtime boundary:

- registry lookup is only candidate discovery
- stale, deleted, or inactive backend principal must still be re-canonicalized against the backend source of truth before password verification, session creation, or any authority-bearing outcome
- mapping existence alone does not prove backend principal still exists
- mapping existence alone does not prove backend principal is still active
- registry lookup must not replace backend re-canonicalization
- no fallback or guessing to another backend is allowed

### 5.4 Ambiguity representation decision

Ambiguity is a derived candidate-set state, not a persisted authoritative flag.

Reason:

- persistent ambiguity flags become stale when aliases are added, disabled, retired, or remapped
- derived ambiguity keeps candidate state aligned with current alias + mapping records
- derived ambiguity avoids turning a mutable convenience flag into an authority shortcut

Frozen candidate lookup rule:

- lookup by exact normalization provenance + normalized key
- collect only candidate rows that satisfy the full predicate above
- deduplicate by `global_identity_id`
- outcome is:
  - zero candidates
  - one candidate
  - multiple candidates

Multiple-candidate state must remain representable and must fail closed.

### 5.5 Duplicate policy

Frozen duplicate-prevention rule:

- active alias duplicate prevention must cover:
  - `global_identity_id`
  - `raw_alias`
  - `normalized_lookup_key`
  - full normalization provenance tuple

Full normalization provenance tuple means:

- `normalization_algorithm_family`
- `normalization_profile`
- `unicode_data_version`
- `trim_conformance_profile`

Frozen non-unique rule:

- multiple identities may share the same normalized key under the same profile
- therefore normalized key must not be globally unique
- disabled or superseded historical alias rows may remain duplicated for audit / lifecycle history

### 5.6 Provenance tuple integrity

`AUTH-ID-001D` froze trim/conformance semantics but did not assign a physical stored token name. Therefore `AUTH-ID-001E` defines an exact ASCII storage token for schema use while keeping the already approved semantics unchanged.

Exact stored trim/conformance token for this baseline:

- `PY3146_UCD16_0_0_STRIP_V1`

Allowed active-profile tuple for this frozen baseline:

- algorithm family:
  - `NFKC_CASEFOLD_V1`
- normalization profile:
  - `NFKC_CASEFOLD_V1_UCD16_0_0`
- Unicode data version:
  - `16.0.0`
- trim / conformance profile:
  - `PY3146_UCD16_0_0_STRIP_V1`

Frozen token meaning:

- `PY3146_UCD16_0_0_STRIP_V1` means exactly the approved Python `3.14.6` / Unicode `16.0.0` boundary-trim conformance baseline frozen by `AUTH-ID-001D`

Frozen consistency rules:

- the four provenance fields must not be arbitrarily mixed
- `normalization_profile` and its UCD / trim / conformance metadata must remain mutually consistent
- unsupported tuple must not be written
- inconsistent tuple must not be written
- unsupported or inconsistent tuple must not participate in candidate lookup
- profile upgrade must create new profile records and must not rewrite existing alias provenance in place
- `AUTH-ID-001E1` must enforce tuple consistency through schema constraint, closed validation, or equivalent fail-closed mechanism

### 5.7 Alias lifecycle

Minimal alias lifecycle frozen here:

- `active`
- `disabled`
- `superseded`

Meaning:

- `active`:
  participates in candidate lookup
- `disabled`:
  excluded from candidate lookup
- `superseded`:
  retained for audit / history and excluded from candidate lookup

Invalid normalization rule:

- invalid-after-trim or unsupported-profile results must not be written as alias records
- schema must not imply fallback to exact, legacy guess, another profile, or another backend

### 5.8 Forbidden usage

Alias records must not be used for:

- password verification
- automatic account linking
- backend selection by guess after ambiguity
- role / site / sheet / vendor authority
- cross-backend fallback guessing

## 6. Backend principal mapping contract

### 6.1 Observed fact

- `AUTH-ID-001C` froze explicit backend mappings as part of the chosen architecture.
- Current canonical principals remain:
  - internal principal = `users.id`
  - vendor principal = `vendor_accounts.id` / `vendor_account_id`
- Current code/schema definition confirms:
  - `users.id` = `INTEGER PRIMARY KEY AUTOINCREMENT`
  - `vendor_accounts.id` = `INTEGER PRIMARY KEY AUTOINCREMENT`

### 6.2 Frozen schema decision

Each backend mapping record must encode:

- backend kind
- canonical backend principal key
- referenced `global_identity_id`
- provenance metadata

Frozen backend kinds in baseline:

- `internal`
- `vendor`

Canonical principals:

- internal principal = `users.id`
- vendor principal = `vendor_accounts.id`

Frozen backend principal key representation:

- `backend_principal_key` logical type = positive canonical backend integer primary-key value
- future SQLite storage intent = `INTEGER`
- no string coercion
- no zero-padding
- no float conversion
- no backend-independent reinterpretation
- `backend_kind` remains the required namespace discriminator
- `internal + 1` and `vendor + 1` are different principals
- invalid, non-integer, or out-of-domain key must not create a mapping
- exact physical `CHECK` and DDL remain deferred to `AUTH-ID-001E1`

Cardinality decisions:

- each canonical backend principal maps to at most one `global_identity_id`
- one `global_identity_id` may map to:
  - one internal principal
  - one vendor principal
  - both internal and vendor principals only after explicit linking policy is separately approved

Schema capability preserved:

- the schema may represent both internal and vendor mappings for the same global identity

Runtime meaning not approved here:

- this slice does not approve automatic or inferred multi-backend linking
- same alias text must not auto-create multi-backend mapping

### 6.3 Mapping lifecycle

Minimal mapping lifecycle frozen here:

- `active`
- `disabled`

Meaning:

- `active`:
  counts toward candidate eligibility when all other candidate predicates also hold
- `disabled`:
  retained for audit / provenance but does not count toward candidate eligibility

Frozen rules:

- mapping existence by itself does not prove backend principal still exists
- mapping existence by itself does not prove backend principal is active
- disabled mapping does not participate in candidate lookup
- no fallback or guessing to another backend is allowed

### 6.4 Stale / deleted / inactive backend handling

Frozen baseline behavior:

- a mapping record may exist even if later runtime re-canonicalization finds the backend principal deleted, inactive, or stale
- protected requests must still re-canonicalize the backend principal against the backend source of truth
- mapping existence alone must not establish authority

### 6.5 Forbidden usage

Backend mapping must not:

- duplicate password hash
- change canonical credential backend
- grant role / site / sheet / vendor authority
- bypass protected-request re-canonicalization
- infer vendor organization identity from `vendor_name`

## 7. Table and field matrices

### 7.1 `global_identities`

| Proposed canonical name | Field name | Logical type | Nullable / required | Default | PK | FK target | Unique / non-unique rule | Indexed lookup intent | Immutable / mutable | Authoritative owner | Lifecycle responsibility | Can carry authorization | Forbidden usage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `global_identities` | `global_identity_id` | opaque registry identity key | required | generated later | yes | none | unique | direct identity resolution | immutable | identity registry | identity lifecycle slice | no | must not be alias text or username |
| `global_identities` | `registry_status` | closed lifecycle enum (`active`, `disabled`) | required | `disabled` | no | none | non-unique | status filtering and candidate eligibility | mutable by future lifecycle slice | identity registry | identity lifecycle slice | no | must not grant authority |
| `global_identities` | `created_at` | timestamp metadata | required | set on create | no | none | non-unique | audit | immutable | identity registry | creation slice | no | not business authority |
| `global_identities` | `updated_at` | timestamp metadata | required | set on update | no | none | non-unique | audit | mutable | identity registry | lifecycle / reconciliation slice | no | not business authority |
| `global_identities` | `created_provenance` | source marker | required | none | no | none | non-unique | audit | immutable | identity registry | creation slice | no | not runtime authority |
| `global_identities` | `updated_provenance` | source marker | required | none | no | none | non-unique | audit | mutable | identity registry | lifecycle / reconciliation slice | no | not runtime authority |

### 7.2 `login_identifier_aliases`

| Proposed canonical name | Field name | Logical type | Nullable / required | Default | PK | FK target | Unique / non-unique rule | Indexed lookup intent | Immutable / mutable | Authoritative owner | Lifecycle responsibility | Can carry authorization | Forbidden usage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `login_identifier_aliases` | `login_identifier_alias_id` | opaque alias record key | required | generated later | yes | none | unique | direct alias record addressing | immutable | identity registry | alias lifecycle slice | no | must not be identity key |
| `login_identifier_aliases` | `global_identity_id` | opaque registry identity reference | required | none | no | `global_identities.global_identity_id` | non-unique | candidate resolution | immutable after creation except controlled reassignment slice | identity registry | linking / reconciliation slice | no | not authority by itself |
| `login_identifier_aliases` | `raw_alias` | preserved source alias text | required | none | no | none | intentionally non-unique | audit / compatibility | immutable in baseline | identity registry | alias lifecycle slice | no | must not be credential or auth key |
| `login_identifier_aliases` | `normalized_lookup_key` | normalized recognition key | required | none | no | none | intentionally non-unique across identities; duplicate-restricted within one identity when alias is active | candidate lookup | immutable for a given profile record | identity registry | normalization-aware alias slice | no | must not be global unique authority |
| `login_identifier_aliases` | `normalization_algorithm_family` | provenance token | required | none | no | none | non-unique | provenance filtering | immutable | identity registry | alias creation slice | no | must not be implied from runtime only |
| `login_identifier_aliases` | `normalization_profile` | profile token | required | none | no | none | non-unique | provenance filtering | immutable | identity registry | alias creation slice | no | must not drift silently |
| `login_identifier_aliases` | `unicode_data_version` | version token | required | none | no | none | non-unique | provenance filtering | immutable | identity registry | alias creation slice | no | must not be omitted |
| `login_identifier_aliases` | `trim_conformance_profile` | trim/conformance token | required | none | no | none | non-unique but cross-field constrained | provenance filtering | immutable | identity registry | alias creation slice | no | must use exact stored token `PY3146_UCD16_0_0_STRIP_V1` for the frozen active profile |
| `login_identifier_aliases` | `alias_status` | alias lifecycle enum (`active`, `disabled`, `superseded`) | required | `active` | no | none | non-unique | active candidate filtering | mutable | identity registry | alias lifecycle slice | no | must not establish authority |
| `login_identifier_aliases` | `created_at` | timestamp metadata | required | set on create | no | none | non-unique | audit | immutable | identity registry | alias creation slice | no | not business authority |
| `login_identifier_aliases` | `updated_at` | timestamp metadata | required | set on update | no | none | non-unique | audit | mutable | identity registry | alias lifecycle / reconciliation slice | no | not business authority |
| `login_identifier_aliases` | `created_provenance` | source marker | required | none | no | none | non-unique | audit | immutable | identity registry | alias creation slice | no | not runtime authority |
| `login_identifier_aliases` | `updated_provenance` | source marker | required | none | no | none | non-unique | audit | mutable | identity registry | alias lifecycle / reconciliation slice | no | not runtime authority |

### 7.3 `backend_principal_mappings`

| Proposed canonical name | Field name | Logical type | Nullable / required | Default | PK | FK target | Unique / non-unique rule | Indexed lookup intent | Immutable / mutable | Authoritative owner | Lifecycle responsibility | Can carry authorization | Forbidden usage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `backend_principal_mappings` | `backend_principal_mapping_id` | opaque mapping record key | required | generated later | yes | none | unique | direct mapping addressing | immutable | identity registry | mapping lifecycle slice | no | must not be authority |
| `backend_principal_mappings` | `global_identity_id` | opaque registry identity reference | required | none | no | `global_identities.global_identity_id` | non-unique overall; cardinality-constrained by backend kind | identity-to-principal traversal | mutable only in explicit linking / reconciliation slice | identity registry | mapping lifecycle slice | no | not authority by itself |
| `backend_principal_mappings` | `backend_kind` | backend namespace token | required | none | no | none | unique only with principal key | backend resolution | immutable | identity registry | mapping creation slice | no | must not guess backend |
| `backend_principal_mappings` | `backend_principal_key` | positive canonical backend integer principal key as logical external reference | required | none | no | none; logical reference interpreted by `backend_kind` | unique within backend kind | backend principal lookup | immutable in baseline | identity registry | mapping creation slice | no | must not copy credential secret, must not use string/float reinterpretation, and must not be treated as SQLite-enforced backend FK |
| `backend_principal_mappings` | `mapping_status` | mapping lifecycle enum (`active`, `disabled`) | required | `active` | no | none | non-unique | active mapping filtering and candidate eligibility | mutable | identity registry | mapping lifecycle slice | no | must not establish authority without backend re-check |
| `backend_principal_mappings` | `created_at` | timestamp metadata | required | set on create | no | none | non-unique | audit | immutable | identity registry | mapping creation slice | no | not business authority |
| `backend_principal_mappings` | `updated_at` | timestamp metadata | required | set on update | no | none | non-unique | audit | mutable | identity registry | mapping lifecycle / reconciliation slice | no | not business authority |
| `backend_principal_mappings` | `created_provenance` | source marker | required | none | no | none | non-unique | audit | immutable | identity registry | mapping creation slice | no | not runtime authority |
| `backend_principal_mappings` | `updated_provenance` | source marker | required | none | no | none | non-unique | audit | mutable | identity registry | mapping lifecycle / reconciliation slice | no | not runtime authority |

## 8. Constraint and cardinality matrix

| Area | Frozen baseline |
|---|---|
| Global identity PK | `global_identity_id` unique opaque key |
| Alias PK | `login_identifier_alias_id` unique opaque key |
| Mapping PK | `backend_principal_mapping_id` unique opaque key |
| Alias FK | alias → `global_identities.global_identity_id` required |
| Mapping FK | mapping → `global_identities.global_identity_id` required |
| Backend principal uniqueness | unique on `backend_kind + backend_principal_key` |
| Per-identity backend-kind cardinality | unique on `global_identity_id + backend_kind` |
| Same-identity duplicate prevention | forbid two active alias rows under one identity with the same raw alias + normalized key + provenance |
| Normalized lookup key uniqueness | intentionally non-unique |
| Candidate lookup index | index on normalization provenance + normalized lookup key + active alias state |
| Provenance index | index on profile / Unicode / trim provenance for audit and controlled upgrade workflows |
| Backend principal key representation | positive canonical backend integer primary-key value stored as `INTEGER`; interpreted only together with `backend_kind` |
| Registry delete behavior | lifecycle-first handling; physical delete blocked while alias or mapping rows remain |
| Registry update behavior | `global_identity_id` and alias / mapping identity FK keys are not ordinary-update fields |
| Registry orphan prevention | alias and mapping rows require valid referenced global identity |
| Backend stale-reference handling | runtime re-canonicalization and reconciliation, not SQLite backend FK |
| Collision preservation | schema must allow many alias rows with the same normalized key under the same profile |
| Active identity minimum cardinality | active identity must have at least one active alias and one active mapping |

### 8.1 Why normalized key cannot be global unique

- Current zero-collision evidence is not a guarantee of future zero-collision state.
- `AUTH-ID-001D` froze many-candidate ambiguity as a valid fail-closed outcome.
- A global unique normalized key would erase the ability to represent:
  - future collisions
  - controlled ambiguous candidate state
  - dry-run upgrade comparison outcomes

### 8.2 How one backend principal is prevented from mapping to two identities

- uniqueness on `backend_kind + backend_principal_key`
- mapping row is the sole registry representation of that backend principal
- reassignment, if ever allowed, belongs to explicit later reconciliation / linking policy rather than ordinary writes

### 8.3 How one identity is prevented from holding two mappings of the same backend kind

- uniqueness on `global_identity_id + backend_kind`
- therefore one identity may hold:
  - at most one internal mapping
  - at most one vendor mapping
- same identity may structurally hold both one internal mapping and one vendor mapping, but runtime linking semantics remain deferred

### 8.4 How multiple-candidate state is represented

- multiple alias rows may share the same:
  - normalization provenance
  - normalized lookup key
- those rows may point to different global identities
- candidate multiplicity is derived from the alias lookup result set

### 8.5 How alias or mapping is prevented from becoming an authorization shortcut

- alias has no role / site / sheet / vendor authority fields
- mapping has no permission / trusted-target / workflow authority fields
- protected requests must still re-canonicalize backend principal and downstream authority relations

## 9. Write ownership and transaction boundary

### 9.1 Frozen design boundary

This slice freezes write ownership only as future design allocation. It implements nothing.

### 9.2 Future slice ownership

- identity creation:
  future registry schema implementation + creation workflow slice
- alias creation:
  future alias import / shadow-write slice
- backend mapping creation:
  future mapping creation / backfill slice

### 9.3 Stage isolation rules

Frozen rules:

- schema creation must be separate from backfill
- backfill must be separate from runtime recognition authority switch
- schema creation must be separate from session / routing authority migration
- normalization upgrade must be separate from authority switch

### 9.4 Transaction boundary

Future implementation must guarantee:

- failed partial write must not leave orphan global identity
- failed partial write must not leave orphan alias
- failed partial write must not leave orphan mapping
- failed partial write must not leave an identity marked `active` without:
  - one active alias
  - one active mapping
- dual-write success must not be assumed forever during transition
- rollback must not depend on hot-merging registry data back into continuously mutating legacy authority tables

Frozen creation / activation sequence:

1. create `global_identity` as `disabled`
2. create required active alias
3. create required active mapping
4. validate minimum cardinality and provenance consistency
5. switch identity to `active`
6. commit

If any step fails:

- rollback the entire transaction

Explicitly forbidden:

- relying on default `active` at identity creation time
- committing an `active` identity that lacks an active alias
- committing an `active` identity that lacks an active mapping
- treating reconciliation as a substitute for normal creation-transaction atomicity

Frozen invariants:

- `global_identity_id` and alias / mapping identity FK keys are not ordinary-update fields
- a global identity with existing alias or mapping rows must not be physically deleted in ordinary operation
- FK delete / update intent is `RESTRICT` / `NO ACTION`; exact DDL remains deferred to `AUTH-ID-001E1`
- lifecycle change is preferred over physical delete
- disabled identity may retain historical alias and mapping rows
- the active-identity minimum-cardinality rule is cross-table and cannot be guaranteed by a single-table `CHECK`
- future creation / activation transaction and reconciliation must jointly enforce that invariant
- reconciliation is for anomaly detection / repair, not a license for partial normal commits

## 10. `vendor_id` boundary

### 10.1 Observed fact

- `vendor_account_id` is the current authenticated vendor login principal.
- Future vendor organization authorization identity is `vendor_id`.
- `vendor_name` is only display / business label and must not become future authority.

### 10.2 Frozen schema decision

This registry baseline may describe the boundary to future vendor organization identity, but it must not define vendor organization schema.

Frozen rules:

- `vendor_account_id` remains the login principal concept
- `vendor_id` remains the future vendor organization authorization identity
- `vendor_name` must not appear as an authorization join key in registry schema
- no registry-owned field may imply `vendor_name`-based authority

Deferred outside this slice:

- `vendor_id` physical schema
- vendor membership schema
- vendor-site assignment schema
- sheet-vendor binding schema
- trusted-target migration
- vendor backfill and reconciliation

## 11. Rollout dependency freeze

Frozen order:

1. `AUTH-ID-001E` docs/schema design freeze
2. separate schema implementation slice
3. schema-only deployment verification
4. read-only shadow registry
5. backfill readiness / dry-run
6. controlled backfill
7. reconciliation
8. recognition API
9. UI consumption
10. session / routing authority migration

Non-negotiable boundaries:

- schema and backfill must not share one slice
- backfill and runtime authority switch must not share one slice
- normalization upgrade and authority switch must not share one slice
- no rollout plan may assume hot-maintenance merge capability

## 12. Deferred-decision ownership matrix

| Decision | Owner slice | Why deferred | Frozen invariant |
|---|---|---|---|
| physical SQLite DDL and migration | `AUTH-ID-001E1` | This slice freezes logical schema shape first; physical DDL, naming, migration ordering, provenance enforcement, and deployment verification need their own implementation review. | DDL must preserve opaque global identity, preserve raw alias separately from normalized key, enforce closed or fail-closed provenance consistency, and must not perform backfill. |
| exact ID generation format | `AUTH-ID-001E2` | Opaque-key format affects storage, audit ergonomics, and future interoperability, but does not block the logical schema boundary. | Identity keys must remain opaque stable keys and must not encode username, backend type, or authority. |
| lifecycle / tombstone / merge policy | `AUTH-ID-001F` | Safe lifecycle states require separate operational and authority review beyond initial schema shape. | No tombstone, merge, or lifecycle field may imply hot-merge support or authority by itself. |
| explicit cross-backend account linking | `AUTH-ID-001G` | Linking is a high-risk identity decision and must be isolated from initial schema introduction. | Shared alias text must never auto-link internal and vendor principals. |
| legacy alias import | `AUTH-ID-001F` | Import, retirement, compatibility, and history handling depend on lifecycle semantics after schema shape is frozen. | Existing backend usernames remain canonical credential lookup data until a controlled later migration. |
| control / format rejection policy | `AUTH-ID-001D2` | Category-specific reject and legacy exception handling belongs to a dedicated normalization-adjacent evidence slice. | No silent deletion, repair, authentication, or authorization from control / format risk state. |
| collision resolution UX | `AUTH-UX-001B` | Candidate ambiguity UI depends on frozen schema and normalization semantics but should remain separate from storage design. | Ambiguous candidate state must fail closed and must not leak backend type or target existence. |
| recognition API | `AUTH-READ-001` | API shape depends on schema and ambiguity semantics and should be designed after storage baseline is frozen. | Recognition remains read-only, non-authoritative, and session-free. |
| session migration | `AUTH-SESSION-001` | Session semantics must follow schema, recognition, and linking design rather than being implied by storage. | Protected requests must continue backend re-canonicalization; registry data must not become a session authority shortcut. |
| vendor_id conceptual organization model | `VENDOR-ID-001` | Vendor business-identity semantics must be frozen before any physical vendor authority schema. | `vendor_id` must not be auto-derived from `vendor_name`; membership must not become login authority. |
| vendor_id physical schema | `VENDOR-ID-002` | Vendor organization records require a separate schema slice after conceptual vendor design. | Schema must not execute backfill and must not switch runtime authority. |
| vendor_id backfill readiness / dry-run | `VENDOR-ID-003` | Read-only backfill preparation must be independently reviewable before any live data change. | This slice must remain read-only and must not auto-merge by `vendor_name`. |
| controlled vendor identity backfill | `VENDOR-ID-004` | Live backfill requires dedicated maintenance, rollback, conflict, and reconciliation gates. | Controlled backfill must not share a slice with schema or authority switch. |
| registry upgrade / reconciliation workflow | `AUTH-ID-001H` | Upgrade and reconciliation operations depend on implemented schema plus runtime evidence and must be reviewed separately from baseline design. | Upgrade must preserve provenance, report collision deltas, and must not overwrite or merge in place without isolated gates. |

No unresolved decision in this baseline is left without an owner slice.

## 13. Out of scope

Explicitly out of scope:

- `app.py` changes
- `tests` changes
- DDL
- SQL
- migration execution
- schema execution
- backfill
- live-data repair
- API / route / session / UI changes
- password movement or rehash
- authorization / permission / workflow changes
- `vendor_name` cleanup
- `vendor_id` implementation
- account linking implementation
- identity merge implementation
- DB / DEV / Production operations
- `AUTH-ID-001F` or any later implementation slice

## 14. Review checklist

- The registry remains separate from canonical credential backends.
- Global identity is opaque and non-authoritative.
- Raw alias and normalized key are separate.
- Version provenance is explicit and queryable.
- Normalized key is intentionally non-unique.
- Candidate predicate requires active alias, exact profile match, active global identity, and at least one active mapping.
- Candidate ambiguity is represented by derived candidate set, not by authority shortcut.
- Mapping lifecycle is exactly `active` / `disabled`.
- One backend principal cannot map to two global identities.
- One identity cannot hold two mappings of the same backend kind.
- Backend principal reference is a logical external reference, not a dynamic SQLite backend FK.
- Backend principal reference uses positive canonical backend integer primary-key values stored as `INTEGER`.
- `registry_status` defaults to `disabled`, not `active`.
- Normal creation activates identity only after alias, mapping, and provenance checks pass in one transaction.
- `trim_conformance_profile` uses the exact stored token `PY3146_UCD16_0_0_STRIP_V1`.
- Registry orphan prevention and backend stale-reference detection are explicitly separate.
- Active identity minimum cardinality is one active alias plus one active mapping.
- Mapping does not copy or move password authority.
- Alias and mapping cannot grant site / sheet / vendor / role authority.
- `vendor_account_id` and future `vendor_id` remain distinct.
- This document does not define vendor organization schema.
- Schema, backfill, and authority switch remain isolated slices.
