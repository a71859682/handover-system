# AUTH-ID-001C — Global Account Identity Registry Design Baseline

Status: design baseline

Scope: docs-only

Implementation status: not started

## 1. Baseline

- Canonical repository: `C:\Users\耀祥\Documents\handover-system-formal`
- Design worktree base: `origin/develop`
- Frozen main: `145b7c5387049766f267f35592825e9513cb51c8`
- Frozen develop: `145b7c5387049766f267f35592825e9513cb51c8`
- Frozen Production: `145b7c5387049766f267f35592825e9513cb51c8`
- AUTH-UX-001A: Production Frozen
- AUTH-ID-001A: Inventory Complete
- AUTH-ID-001B: Runtime Evidence Complete

This document establishes the docs-only design baseline for a future Global Account Identity Registry. It defines the boundary between global identity, login identifier alias, credential backend principal, vendor organization identity, and session authority. It does not create schema, migration, API, UI, runtime adapter, or backfill behavior.

## 2. Repository baseline

- Local `main`: `145b7c5387049766f267f35592825e9513cb51c8`
- Origin `main`: `145b7c5387049766f267f35592825e9513cb51c8`
- Local `develop`: `145b7c5387049766f267f35592825e9513cb51c8`
- Origin `develop`: `145b7c5387049766f267f35592825e9513cb51c8`
- `main` and `develop` are in sync at this baseline
- Canonical repository tracked working tree and index must remain clean
- Known canonical-repository untracked file:
  - `.codex/environments/environment.toml`
- Production baseline remains live on `145b7c5`

## 3. Terminology freeze

### 3.1 Global identity

Frozen definition:

- A global identity is a stable, opaque identity key for a human or system actor record in the unified identity layer.
- It must not depend on current username text.
- It must not equal role, site, sheet, vendor organization, or credential principal.
- It must not change when display name or login alias changes.
- A registry record by itself does not grant business authorization.

Boundary:

- Global identity is identity coordination, not direct authorization.
- Authorization must still be derived from canonical backend relationships and later canonical business relationships.

### 3.2 Login identifier alias

Frozen definition:

- A login identifier alias is the user-supplied identifier used during recognition.
- Current raw usernames may be preserved as initial compatibility aliases.
- Alias is not the global identity primary key.
- Alias is not authorization authority.

Recognition outcomes:

- zero candidates
- exactly one candidate
- multiple / ambiguous candidates

Frozen boundary:

- Multiple candidates must enter an ambiguous state.
- The system must not guess actor type, target, or authority from alias collisions.

### 3.3 Credential backend principal

Current canonical backend principals remain separate.

- Internal current principal: `users.id`
- Vendor current principal: `vendor_accounts.id`
- Current vendor session principal marker: `vendor_account_id`

Frozen boundary:

- Password hash remains owned by the canonical credential backend.
- The registry must not copy or store password hash.
- Recognition must not try password verification against multiple backends.
- Password verification is executed only against the single backend selected by recognition.

### 3.4 Vendor organization identity

Frozen future definition:

- Future canonical vendor business identity is `vendor_id`.
- `vendor_id` is distinct from vendor login account principal.
- Vendor authorization, ownership, vendor-site assignment, sheet-vendor binding, work-entry ownership, and trusted-target derivation must ultimately flow from canonical `vendor_id` relationships.
- `vendor_name` is only display / business label, not future authority.

Frozen non-assumption:

- This document does not claim that current schema, current write paths, or current business scoping have already migrated to `vendor_id`.

## 4. Chosen architecture

### 4.1 Selected target architecture

Selected target architecture:

- Separate Global Identity Registry + Explicit Backend Mappings

This is the chosen target architecture for AUTH-ID.

### 4.2 Why Option A is chosen

Frozen decision:

- Option A is the target architecture.
- A staged compatibility adapter may be used later as rollout technique only.
- A staged adapter must not become:
  - a third credential source
  - a third authorization authority
  - a hidden identity-merge mechanism

### 4.3 Option B not chosen

Not chosen:

- Direct merge of `users` and `vendor_accounts`
- Auto-merge of internal and vendor principals that happen to share the same username

Reason:

- Username equality is not identity proof.
- Separate credential backends and separate business authorities remain frozen facts.
- Current evidence does not justify collapsing internal principal and vendor principal into one authority record.

### 4.4 Mapping invariants

Frozen invariants:

- Each existing backend principal maps to at most one global identity.
- Initial migration must create one distinct global identity per existing backend principal.
- Matching username must not auto-merge identities.
- Future many-principal-to-one-identity linking, if allowed at all, requires separate explicit linking policy.
- Linking policy must be auditable.
- This slice does not design or implement linking workflow.

## 5. Identifier and collision contract

### 5.1 Frozen decisions from 001B evidence

Observed fact:

- Current DEV and Production evidence shows:
  - exact collision = 0
  - NFC(strip).casefold collision = 0
  - NFKC(strip).casefold collision = 0

Frozen decisions:

- Existing raw username may be retained as an initial compatibility alias.
- Raw username must not become the global identity primary key.
- The system must not drop ambiguous state just because current collision count is 0.
- This slice does not freeze a global unique username constraint.
- This slice does not rewrite existing usernames by case-folding or Unicode normalization.
- Normalization policy remains unresolved and must be decided independently.

### 5.2 Recognition contract

Recognition lookup must support:

- zero candidate
- exactly one candidate
- multiple / ambiguous candidates

Frozen boundary:

- Ambiguous candidate must not establish authority-bearing session.
- Outward response must not become an account-existence oracle.

### 5.3 Normalization evidence recorded but not selected

The following analyses are recorded as evidence only:

- `NFC(strip(username)).casefold()`
- `NFKC(strip(username)).casefold()`

Frozen boundary:

- Evidence is not policy.
- No canonical normalization policy is selected in this slice.

## 6. Authentication and session boundary

Frozen decisions:

- Registry recognition is not authentication.
- Password verification runs only in the single backend selected by recognition.
- Internal-then-vendor fallback is forbidden.
- Vendor-then-internal fallback is forbidden.
- No authority-bearing session may exist before successful authentication.
- Current internal `user_id` and current vendor `vendor_account_id` remain canonical principal authority before migration.
- Future `global_identity_id` may exist first only as server-derived linkage / recognition context.
- `global_identity_id` must not initially replace write authorization.
- Protected requests must continue to re-canonicalize backend principal from canonical source of truth.
- Internal and vendor sessions must never both be valid.
- Browser-supplied identity, role, vendor name, site, and sheet must never be authority.

## 7. Vendor identity sequencing

Observed fact:

- DEV vendor trusted-target evidence shows:
  - exactly one sheet = 4 accounts
  - more than one sheet = 1 account
  - maximum = 2
- Production vendor accounts = 0
- Task unmapped-label evidence exists:
  - DEV = 18
  - Production = 14

Frozen decisions:

- `vendor_id` must not be auto-derived from `vendor_name`.
- Task unmapped-label evidence must not be treated as safe auto-merge input.
- DEV multi-target evidence proves that routing must not guess a single sheet.
- Production `vendor_accounts = 0` is an evidence gap, not rollout proof.
- `VENDOR-ID-001` must complete before any AUTH-READ or AUTH-ROUTE feature relies on vendor authority, ownership, or trusted-target derivation.
- Pure non-authoritative recognition design may be specified before `VENDOR-ID-001`, but it must not cross vendor authority boundary.

## 8. Conceptual model

This section defines logical entities and cardinality only. It does not define DDL, SQL, migration scripts, or physical schema.

| Entity | Stable identity key | Logical ownership | Cardinality | Unique / non-unique concept | Authoritative source | Forbidden joins | Lifecycle responsibility |
|---|---|---|---|---|---|---|---|
| GlobalIdentity | `global_identity_id` | identity registry | One per initial backend principal; future linking unresolved | unique opaque key | future registry | must not join directly to browser-supplied role/site/vendor/sheet as authority | identity layer |
| LoginIdentifierAlias | alias record key or alias text under registry control | identity registry | many aliases may point to one global identity; one alias may later become ambiguous across candidates | alias text is not guaranteed globally unique | recognition layer / later registry schema | must not be treated as authorization authority | identity layer |
| BackendPrincipalMapping | mapping key from backend principal to global identity | identity registry | each backend principal maps to at most one global identity | backend principal must be unique within its backend namespace | canonical backend principal + registry mapping | must not auto-merge on matching username text | identity layer |
| InternalCredentialPrincipal | `users.id` | internal auth backend | one internal credential principal per internal account | backend-local unique | `users` backend | must not be merged with vendor principal by shared username | internal backend |
| VendorCredentialPrincipal | `vendor_accounts.id` / session `vendor_account_id` | vendor auth backend | one vendor credential principal per vendor login account | backend-local unique | `vendor_accounts` backend | must not be treated as vendor organization identity | vendor backend |
| VendorOrganization (`vendor_id`) | `vendor_id` | vendor business authority layer | one vendor organization may later relate to multiple vendor credential principals or members | unique opaque business identity | future vendor-identity layer | must not be derived from `vendor_name` text alone | vendor identity layer |
| VendorOrganizationMembership | membership key | vendor identity / authorization layer | one vendor organization to many members; membership policy deferred | uniqueness must be explicit by policy | future vendor membership layer | must not be inferred from current username, `vendor_name`, or display-text match; must not act as login identifier or credential principal | vendor identity layer |
| SitePermission | permission record key | internal authorization layer | one canonical internal principal may map to many sites; future global identity may only derive internal subject through canonical internal backend mapping | uniqueness by internal-subject / site pair | existing internal permission model; future unified mapping later | must not use VendorOrganization, alias, `vendor_name`, or browser-supplied role/site as permission subject | authorization layer |
| VendorSiteAssignment | assignment key | vendor authorization layer | one vendor organization may map to many sites | uniqueness by vendor-site relationship | future `vendor_id` mapping | authoritative vendor subject key must not be `vendor_account_id`, username, or `vendor_name` | vendor authorization layer |
| SheetVendorBinding | binding key | vendor authorization / routing layer | one vendor organization may bind to many sheets; sheet may have multiple vendor relationships if model allows | uniqueness by vendor-sheet binding policy | future `vendor_id` mapping | authoritative vendor subject key must not be task label, `vendor_name`, username, or `vendor_account_id` | vendor authorization / routing layer |

## 9. Rollout and rollback boundary

### 9.1 Staged rollout sequence

Frozen staged sequence:

1. docs/design freeze
2. normalization decision
3. schema baseline
4. read-only shadow registry
5. backfill readiness / dry-run
6. controlled backfill
7. comparison / reconciliation
8. recognition API
9. UI consumption
10. routing migration

### 9.2 Stage isolation rules

Frozen rules:

- Each stage must be its own slice.
- Schema and backfill must not share one slice.
- Backfill and runtime authority switch must not share one slice.
- This roadmap must not assume hot-maintenance merge capability.
- Live identity merge must not occur before:
  - maintenance mode planning
  - write freeze planning
  - conflict handling
  - rollback design
  - post-deploy reconciliation
  are independently validated
- Rollback must not depend on directly merging newly written identity data back into continuously written legacy authority records.

## 10. Evidence integration

This document records only aggregate evidence. It must not contain username, vendor_name, password hash, credential, or row sample.

### 10.1 Observed fact

- DEV account totals:
  - users = 3
  - vendor_accounts = 5
  - active vendor_accounts = 5
  - inactive vendor_accounts = 0
  - distinct non-empty vendor account business-label count = 5
  - groups with count > 1 = 0
  - maximum accounts per non-empty vendor_name = 1
- Production account totals:
  - users = 2
  - vendor_accounts = 0
  - active vendor_accounts = 0
  - inactive vendor_accounts = 0
- DEV exact / normalized collision count = 0
- Production exact / normalized collision count = 0
- Stored-value hygiene counts are all 0 in both environments
- DEV trusted-target distribution:
  - exactly one = 4
  - more than one = 1
  - maximum = 2
- Production vendor trusted-target distribution is empty because vendor_accounts = 0
- Unmapped-label evidence:
  - DEV tasks = 18
  - Production tasks = 14
- Logical relation integrity missing-target counts are all 0 in both environments
- Read-only no-write proof succeeded in both environments

### 10.2 Design inference

- Current absence of collision supports preserving raw username as initial alias.
- Current absence of collision does not justify removing ambiguous state from the design.
- Current DEV maximum of 1 account per observed non-empty vendor label does not promote `vendor_name` to identity or future authority.
- DEV vendor multi-target evidence proves that future routing and vendor authority cannot safely guess one target.
- Production vendor-account absence leaves a vendor rollout evidence gap.
- Unmapped-label evidence means current label text cannot be treated as trustworthy organization identity.

### 10.3 Frozen decision

- Global identity is opaque and separate from alias and principal.
- Alias is not authority.
- Backend principal remains canonical credential authority until later migration.
- `vendor_id` is future canonical vendor organization authority.
- No cross-backend password fallback.
- No auto-merge on matching username.

### 10.4 Unresolved decision

- normalization policy
- exact registry schema
- mapping schema
- linking workflow
- recognition API shape
- session migration design
- `vendor_id` schema and backfill
- post-login routing migration

## 11. Deferred decisions and owners

| Decision | Owner slice | Why deferred | Frozen invariant |
|---|---|---|---|
| normalization policy | `AUTH-ID-001D` | Current evidence proves only that observed collisions are absent, not that one normalization rule is safe to canonicalize into authority or storage semantics. | Normalization must not silently rewrite existing username authority; ambiguous state must remain possible even if current evidence is collision-free. |
| exact registry schema | `AUTH-ID-001E` | This slice freezes architecture and identity boundary first; physical registry shape must follow after terminology, rollout sequencing, and authority boundaries are fixed. | DDL must preserve opaque global identity and must not make alias text the identity primary key. |
| backend mapping schema | `AUTH-ID-001E` | Mapping storage depends on registry schema decisions, but initial architecture can be frozen before physical mapping records are designed. | Each existing backend principal maps to at most one global identity during initial rollout. |
| global identity lifecycle status | `AUTH-ID-001F` | Lifecycle states need a dedicated pass because activation, disabled, retired, and blocked semantics must not be conflated with business authorization. | Registry lifecycle state must not itself grant business authorization. |
| explicit account linking policy | `AUTH-ID-001G` | Linking is a high-risk identity merge decision and must be separated from initial registry baseline and initial backfill planning. | Linking must never be automatic from shared username, shared display text, or inferred vendor label. |
| collision resolution UX | `AUTH-UX-001B` | Interaction design for ambiguous recognition can wait until the underlying identity and recognition boundaries are frozen. | Ambiguous candidates must not establish authority-bearing session and must not reveal hidden account type. |
| recognition API | `AUTH-READ-001` | API shape depends on frozen identity semantics, but docs-only baseline can define those semantics first without choosing endpoint contract. | Recognition is read-only, non-authoritative, and must not disclose site, vendor, or trusted-target existence. |
| session migration | `AUTH-SESSION-001` | Session transition rules should follow registry and recognition design, because runtime authority must not move until backend re-canonicalization boundaries are preserved. | Future `global_identity_id` must not replace backend principal write authority before protected-request re-canonicalization is preserved. |
| vendor organization / owner-member conceptual design | `VENDOR-ID-001` | Vendor organization semantics must be frozen before any physical vendor identity schema, because membership and business ownership must not be guessed from labels. | `vendor_id` must not be auto-derived from `vendor_name`, and membership must not become login authority. |
| vendor identity physical schema | `VENDOR-ID-002` | Physical vendor identity records require their own schema slice after conceptual vendor-organization design is frozen. | Schema must not execute backfill; `vendor_id` must remain an opaque stable key; runtime authority must not switch in this slice. |
| vendor identity backfill readiness / dry-run | `VENDOR-ID-003` | Read-only preparation should happen only after schema exists, and must be isolated so reconciliation logic can be audited before any live mutation. | This slice must remain read-only / dry-run, must not perform live authority switch, and must not auto-merge by `vendor_name`. |
| controlled vendor identity backfill | `VENDOR-ID-004` | Live backfill requires dedicated operational gating after readiness, conflict handling, rollback, and reconciliation are separately validated. | Controlled backfill must not share a slice with schema or authority switch; it requires maintenance, write-freeze, conflict, rollback, and reconciliation gates first. |
| post-login routing | `AUTH-ROUTE-001` | Routing depends on later recognition output and later canonical relationships, so authority-safe routing can be specified after identity and vendor sequencing are frozen. | Routing may only use canonical actor and canonical relationships; browser-supplied site, sheet, role, or vendor label must not decide authority. |

All unresolved decisions in this baseline have an owner slice and a non-negotiable invariant.

## 12. Out of scope

Explicitly out of scope:

- `app.py` changes
- `tests` changes
- schema or migration work
- DDL or SQL
- backfill
- credential movement
- password rehash
- API or route changes
- session-key changes
- UI
- vendor_name data cleanup
- identity merge
- DB / DEV / Production operations

## 13. Review checklist

Docs review for this slice should verify:

- Option A is clearly selected as target architecture
- global identity, alias, backend principal, and `vendor_id` are explicitly distinct
- raw username is preserved only as compatibility alias, not primary identity key
- current collision-free evidence is not misused to remove ambiguous state
- no cross-backend password fallback is permitted
- current backend principals remain canonical authority before migration
- `vendor_id` is frozen as future vendor authority
- task unmapped-label evidence and DEV multi-target evidence are integrated as design constraints
- conceptual model stays logical and avoids DDL
- rollout and rollback remain independently sliced
- every unresolved decision has owner and invariant
