# VENDOR-ID-001 — Vendor Organization and Owner/Member Design

Status: design baseline
Scope: docs-only
Implementation status: not started

## 1. Purpose and governing boundary

This document freezes the conceptual model and ownership boundary for a future canonical vendor organization identity.

It defines:

- the distinction between a vendor organization, a vendor account, a vendor backend principal, and a vendor display name;
- the stable identity semantics of future `vendor_id`;
- the minimum owner/member model;
- organization and membership lifecycle boundaries;
- vendor-site assignment and sheet-vendor binding semantics;
- the boundary between the future model and current `vendor_name`-scoped operational workflows;
- privacy, provenance, audit, migration, and authority-switch requirements; and
- the exact owner of each deferred implementation decision.

This document does not:

- create a runtime vendor organization source of truth;
- define physical keys, column types, tables, indexes, constraints, or DDL;
- read, classify, normalize, rewrite, backfill, merge, or delete existing vendor data;
- change vendor authentication, session, authorization, routing, API, UI, or response behavior;
- grant repair, reconciliation, linking, lifecycle mutation, or authority-switch permission; or
- authorize any later VENDOR-ID slice merely by naming it.

The governing rule is:

- a stable business identity may be designed here;
- no runtime authority may move to that identity until separately approved schema, discovery, backfill, compatibility, and authority-switch gates have passed.

## 2. Current-state evidence

### 2.1 Current persisted representations

Current repository evidence contains several vendor-related representations, but no canonical vendor organization runtime source of truth:

- `tasks.vendor` stores a free-text vendor business label associated with a sheet task;
- `vendor_accounts.id` identifies a backend-local credential principal;
- `vendor_accounts.vendor_name` stores a business/display label on that credential principal;
- `vendor_contacts.vendor_name` stores a sheet-scoped vendor label;
- `vendor_work_entries.vendor_name` stores a sheet-scoped operational vendor label; and
- downstream approvals, scheduling, crew reads, and reports obtain vendor context through work-entry or task relationships.

Current constraints do not establish `vendor_name` as a stable organization key:

- `vendor_accounts.username` is unique, but `vendor_name` is not;
- vendor contact and work-entry data can repeat the same `vendor_name`;
- one label can appear on tasks in more than one sheet or site;
- the normalizer trims and length-checks vendor names but does not create canonical identity; and
- no current foreign key binds these records to a vendor organization.

### 2.2 Current runtime authority

Current runtime behavior remains based on the existing account and free-text model:

- vendor login authenticates against `vendor_accounts`;
- the vendor session carries `vendor_account_id`, `vendor_username`, and `vendor_name`;
- vendor mutation paths re-canonicalize the vendor credential principal before writing;
- trusted-target resolution currently compares canonical session/account `vendor_name` with `tasks.vendor`;
- exactly one active candidate sheet is required for the current vendor mutation target;
- zero candidates fail unavailable;
- multiple candidates fail ambiguous;
- vendor business read preview is currently filtered by authenticated `vendor_name`; and
- internal contact and work-entry writers retain their existing site and sheet checks.

These are current-state compatibility facts, not the future canonical organization model.

### 2.3 Current operational capability

The repository already implements and freezes Vendor Work Entry operational behavior, including:

- vendor login and logout;
- vendor home, profile, scope, business preview, and work-entry pages;
- vendor work-entry preflight;
- vendor and internal work-entry creation and update;
- internal vendor-contact creation and update;
- crew requirement confirmation and formal approval;
- scheduling-related projections and actions;
- current response shapes and error codes; and
- rejection-before-write guardrails.

VENDOR-ID-001 does not reopen or replace those contracts.

### 2.4 Evidence limitation

Repository source and frozen documents establish the current model and its boundaries. They do not establish:

- the contents, quality, uniqueness, or topology of any DEV or Production vendor rows;
- a safe name-to-organization mapping;
- a safe organization merge;
- a complete vendor-site assignment;
- a complete sheet-vendor binding; or
- readiness to switch runtime authority.

Deployment health is not evidence of vendor row contents, relationships, anomalies, or migration safety.

## 3. Canonical terminology

The canonical repository term is `vendor`, not `vender`.

The canonical Chinese UI label is `廠商`.

The following terminology is frozen:

| Term | Frozen meaning |
|---|---|
| vendor | Repository-wide English business term for the vendor domain |
| vendor organization | A future canonical business entity representing one vendor organization |
| `vendor_id` | The future stable opaque identity of a vendor organization |
| vendor account | An account used by a vendor-side human or system actor to authenticate |
| vendor backend principal | The backend-local credential principal identified today by `vendor_accounts.id` |
| vendor membership | An explicit relationship between one vendor account and one vendor organization |
| owner | A membership role with future organization-administration responsibility, not automatic runtime business authority |
| member | A membership role without owner responsibility, not automatic runtime business authority |
| vendor display name | A mutable human-facing or business-facing label, represented today by `vendor_name` or `tasks.vendor` |
| vendor-site assignment | An explicit relationship between a vendor organization and a site |
| sheet-vendor binding | An explicit, site-consistent relationship between a vendor organization and a sheet |

The following exact semantic distinction is frozen:

| Value | Current meaning | Must not become |
|---|---|---|
| `vendor_accounts.id` | Backend-local credential principal ID | Vendor organization ID |
| `vendor_name` / `tasks.vendor` | Mutable legacy business/display label | Stable identity or authorization proof |
| `vendor_id` | Future opaque vendor organization identity | Encoded name/site/backend/authority |

No implementation may use any one of these values as if it were another.

## 4. Vendor organization identity

### 4.1 Entity definition

A vendor organization is a business entity, not a login account, username, credential, session, site, sheet, task label, or backend principal.

Each future vendor organization has exactly one stable opaque `vendor_id`.

`vendor_id` must:

- remain stable across display-name changes;
- remain stable across account membership changes;
- remain stable across site-assignment and sheet-binding changes;
- remain stable when an organization is disabled or retired;
- contain no business meaning that a caller can use to infer name, site, sheet, account, lifecycle, or authority; and
- be generated only by a separately approved server-controlled implementation.

`vendor_id` must not be derived from:

- `vendor_name`;
- normalized display name;
- username;
- `vendor_accounts.id`;
- a global identity;
- site ID or site code;
- sheet ID;
- task text;
- credentials;
- imported free text; or
- any caller-supplied authority claim.

### 4.2 Identity is not proof

Possession, knowledge, or submission of a `vendor_id` is not:

- authentication proof;
- membership proof;
- owner proof;
- site-access proof;
- sheet-access proof;
- read authorization;
- write authorization; or
- evidence that a relationship is active.

Every future protected read or write must independently re-canonicalize the authenticated backend principal and resolve active canonical relationships under the separately approved runtime authority contract.

### 4.3 Deferred physical representation

The following belong exclusively to `VENDOR-ID-002`:

- physical key type;
- generation format;
- storage representation;
- table and column names;
- indexes and constraints;
- referential actions;
- migration mechanics; and
- schema compatibility behavior.

VENDOR-ID-001 does not select or imply any of those physical decisions.

### 4.4 Current implementation status

No vendor organization currently exists as a runtime source of truth.

The existence of `vendor_accounts`, vendor contacts, vendor work entries, bootstrap definitions, or schema-manifest entries must not be described as implementation of this conceptual entity.

## 5. Vendor account and backend-principal boundary

### 5.1 Current principal

`vendor_accounts.id` remains the current backend-local credential principal ID.

It identifies the account whose credential is verified. It does not identify the organization represented by that account.

The vendor backend continues to own:

- username;
- password hash;
- credential-active status;
- credential verification;
- backend-principal lookup; and
- current vendor session establishment.

### 5.2 Account-to-organization relationship

A future vendor account relates to a vendor organization only through an explicit vendor membership.

The relationship must not be inferred from:

- matching `vendor_name`;
- matching username;
- a shared domain or contact value;
- a task label;
- a prior session value;
- a site or sheet association;
- a global-identity mapping; or
- historical operational records.

One vendor organization may have multiple vendor-account memberships.

For the first implementation, one vendor account may belong to at most one active vendor organization.

A vendor account may retain historical revoked memberships to other organizations, but those historical relationships must not be active or authority-bearing.

### 5.3 Credential status separation

Current `vendor_accounts.is_active` remains credential status.

Credential status must not be treated as:

- vendor organization lifecycle;
- membership lifecycle;
- vendor-site assignment status;
- sheet-vendor binding status; or
- proof that the organization is authorized for a workflow.

Disabling an account must not silently disable, retire, merge, rename, or move its organization.

Disabling or retiring an organization must not silently rewrite credential state.

### 5.4 Public and session boundary

No future API or UI may accept `vendor_accounts.id`, username, `vendor_name`, or `vendor_id` as self-authenticating authority.

VENDOR-ID-001 does not change current session keys. Future session migration, if any, requires a separately approved owner and must preserve backend-principal re-canonicalization.

## 6. Owner and member model

### 6.1 Membership entity

Vendor membership is an explicit relationship between:

- exactly one vendor backend principal; and
- exactly one vendor organization.

A membership has a conceptual role and status. It is not a credential and does not replace the backend principal.

The frozen membership roles are:

- `owner`;
- `member`.

The frozen conceptual membership statuses are:

- `pending`;
- `active`;
- `revoked`.

These names freeze semantics only. Their physical representation belongs to `VENDOR-ID-002`.

### 6.2 Status semantics

`pending` means:

- the relationship has not become active;
- it grants no runtime authority;
- it cannot satisfy the minimum-owner invariant; and
- it cannot be used for site, sheet, read, or write authorization.

`active` means:

- the relationship is the current canonical account-to-organization relationship;
- it may be considered by a future separately approved authority layer; and
- it still grants no runtime authority merely by existing.

`revoked` means:

- the relationship is historical and inactive;
- it grants no runtime authority;
- it cannot satisfy the minimum-owner invariant; and
- it must not be silently reactivated, moved, or reassigned.

Re-establishing a relationship after revocation requires an explicit later mutation contract and new provenance. It must not silently overwrite history.

### 6.3 Membership status transition contract

The exact conceptual membership status transitions are:

- initial creation to `pending`;
- `pending` to `active`;
- `pending` to `revoked`; and
- `active` to `revoked`.

The following transitions and behaviors are forbidden:

- `active` to `pending`;
- in-place `revoked` to `pending`;
- in-place `revoked` to `active`;
- silent reactivation;
- silent replacement;
- silent organization movement; and
- automatic revocation of another active membership.

Re-establishing a revoked relationship must create a separately evidenced new relationship under a later mutation contract. The revoked historical relationship and its role, status, actor, reason, and provenance must not be rewritten.

Activation from `pending` to `active` must:

- verify that the current membership status is `pending`;
- verify that the account has no other active organization membership;
- verify that the target organization is eligible under its lifecycle;
- verify the actor, authorized role, reason, and provenance;
- reject stale, duplicate, or conflicting state;
- avoid automatically revoking, moving, replacing, or rewriting another membership; and
- leave every existing relationship unchanged on rejection.

Status transition does not itself grant runtime authority. A newly active membership may be considered only by a separately approved authority-wiring contract.

### 6.4 Membership role transition contract

Role transition is separate from membership status transition.

The exact conceptual role transitions for an active membership are:

- active `member` to active `owner`; and
- active `owner` to active `member`.

Both role transitions require explicit later mutation authority.

Role-transition rules are:

- a pending or revoked membership grants no role authority;
- the last active owner cannot be demoted or revoked;
- an owner transfer may atomically promote the active target membership and demote the active source membership;
- no member is promoted automatically;
- a revoked membership's role and history are not rewritten;
- a role update must not change the organization;
- a role update must not change the vendor account;
- a role update must not create, move, activate, or deactivate a vendor-site assignment; and
- a role update must not create, move, activate, or deactivate a sheet-vendor binding.

Any stale, duplicate, conflicting, cross-organization, non-active, or minimum-owner-violating role transition fails closed and leaves existing state unchanged.

### 6.5 Cardinality and uniqueness

The following cardinality is frozen:

- one vendor organization may have multiple memberships;
- one vendor organization may have multiple active vendor accounts;
- one vendor account may have at most one active membership across all vendor organizations in the first implementation;
- one account/organization pair may have at most one pending or active membership at a time; and
- duplicate active or pending membership attempts fail closed.

Duplicate membership detection must not merge, replace, move, revoke, or promote an existing relationship automatically.

### 6.6 Minimum-owner invariant

Once membership management exists and an organization is eligible for organization-managed operations:

- the organization must have at least one active owner;
- a pending or revoked owner does not satisfy the invariant;
- removal, revocation, or demotion of the last active owner is forbidden;
- owner transfer must be explicit and atomic with respect to the minimum-owner invariant; and
- failure at any point must leave the previous valid owner set unchanged.

Bootstrap or migration of an owner requires a separately approved evidence gate. This document does not infer an owner from existing usernames, names, contacts, or usage history.

### 6.7 Owner transfer

A future owner transfer requires:

- an authenticated and authorized actor under the later mutation contract;
- a target membership that is already canonical and active;
- explicit source owner, target owner, reason, and correlation evidence;
- validation that both memberships belong to the same vendor organization;
- no cross-organization movement;
- no automatic role promotion; and
- no intermediate or final state with zero active owners.

Owner transfer does not:

- move vendor-site assignments;
- move sheet-vendor bindings;
- merge organizations;
- change `vendor_id`;
- change credentials;
- perform AUTH-ID linking; or
- grant unrelated business authority.

### 6.8 Authority boundary

Owner or member status does not itself grant runtime authority until a later approved authority-wiring slice.

No membership may automatically authorize:

- login;
- organization administration;
- site access;
- sheet access;
- vendor work-entry reads or writes;
- contact reads or writes;
- scheduling;
- approval;
- report access; or
- any cross-site operation.

## 7. Vendor display name, normalization, and duplicate policy

### 7.1 Display-name semantics

`vendor_name` becomes a mutable display/business label only in the future target model.

A display-name change must:

- preserve `vendor_id`;
- preserve historical organization identity;
- avoid changing credential identity;
- avoid silently changing memberships;
- avoid silently changing site assignments or sheet bindings; and
- avoid becoming an authority-switch mechanism.

Current runtime use of `vendor_name` for grouping and trusted-target derivation remains preserved legacy behavior until a later approved authority switch.

### 7.2 Normalized lookup

A future normalized lookup key may support candidate discovery or duplicate review.

It must not:

- become the vendor organization primary identity;
- become authorization proof;
- silently rewrite the submitted or stored display name;
- silently merge organizations;
- guarantee that two equal normalized values are the same organization; or
- guarantee that two unequal normalized values are different organizations.

The exact normalization algorithm is deferred to `VENDOR-ID-TBD — Display-name normalization and duplicate-review contract`.

That later owner must freeze:

- Unicode handling;
- case handling;
- whitespace handling;
- punctuation handling;
- locale behavior;
- empty and invalid input behavior;
- bounded candidate presentation;
- ambiguity behavior; and
- compatibility with existing free-text values.

### 7.3 Duplicate and ambiguity policy

Name equality alone is never sufficient to:

- create a vendor organization;
- assign `vendor_id`;
- merge organizations;
- create or move a membership;
- create or move a site assignment;
- create or move a sheet binding; or
- authorize a runtime action.

Zero candidates, exactly one candidate, and multiple candidates must remain distinguishable outcomes.

Multiple or conflicting candidates fail closed.

Duplicate review may collect evidence, but merge, alias reconciliation, and repair require separate approval and must preserve source records and provenance.

### 7.4 Automatic creation prohibited

No vendor organization may be created automatically from:

- `tasks.vendor`;
- `vendor_accounts.vendor_name`;
- `vendor_contacts.vendor_name`;
- `vendor_work_entries.vendor_name`;
- an imported file;
- a form field;
- a username;
- a site/sheet relationship; or
- a normalized lookup result.

## 8. Vendor organization lifecycle

### 8.1 Conceptual states

The frozen vendor organization lifecycle states are:

- `active`;
- `disabled`;
- `retired`.

These names define conceptual behavior only. Their physical representation belongs to `VENDOR-ID-002`.

### 8.2 State semantics

`active` means:

- the organization is eligible to participate in separately authorized active relationships;
- active status alone grants no authentication, membership, site, sheet, read, or write authority.

`disabled` means:

- new authority use must fail closed under the future authority contract;
- identity and historical records remain preserved;
- existing relationships are not silently moved, deleted, or reassigned; and
- reactivation requires a future explicit mutation gate.

`retired` means:

- the organization remains a durable historical identity;
- it is not eligible for new active business relationships;
- historical memberships, assignments, bindings, and operational records remain attributable;
- retirement is not deletion or merge; and
- restoration requires an independently approved future owner and gate.

### 8.3 Allowed conceptual transitions

The conceptual transition set is:

- `active` to `disabled`;
- `disabled` to `active`, only through explicit reactivation;
- `active` to `retired`;
- `disabled` to `retired`; and
- `retired` to another state only through a separately approved restoration contract.

No transition is implemented or authorized by this document.

Every future transition must:

- be explicit;
- verify current state;
- verify actor and role;
- include reason and provenance;
- preserve `vendor_id`;
- preserve historical references;
- reject stale or conflicting state;
- produce no partial relationship movement; and
- produce no write on rejection.

### 8.4 Deletion and restoration

Hard deletion is forbidden when an organization is referenced by historical or current records.

Disabled or retired organizations retain:

- identity;
- lifecycle history;
- relationship history;
- operational attribution; and
- audit/provenance evidence.

Status changes must not silently:

- move memberships;
- promote owners;
- alter credentials;
- move site assignments;
- move sheet bindings;
- rename the organization;
- merge organizations; or
- backfill legacy records.

## 9. Vendor-site assignment

### 9.1 Relationship definition

Vendor-site assignment is an explicit relationship between:

- one vendor organization identified by `vendor_id`; and
- one canonical site.

The relationship is not inferred from matching names, tasks, contacts, work entries, account activity, current sessions, or prior access.

One vendor organization may be assigned to multiple sites only through separate explicit relationships.

### 9.2 Assignment lifecycle

Every future assignment must have an explicit conceptual status:

- `active`;
- `inactive`.

The exact conceptual assignment transitions are:

- initial creation to `active`;
- `active` to `inactive`; and
- `inactive` to `active` only through explicit reactivation.

The following cardinality is frozen:

- one organization/site pair may have at most one current assignment;
- multiple active assignments for the same organization/site pair are invalid; and
- one organization may have active assignments to multiple distinct sites only through distinct explicit relationships.

An inactive assignment:

- grants no site-derived eligibility;
- must not be selected as a trusted target;
- remains available for history and audit; and
- must not be silently reactivated.

Historical inactive evidence must remain preserved even when the current assignment is later explicitly reactivated.

Assignment creation, deactivation, or reactivation must:

- verify the current relationship state;
- verify organization and site identity;
- reject duplicate create or duplicate reactivate requests;
- reject stale, conflicting, or ambiguous state;
- avoid silent replacement or reactivation;
- leave existing state unchanged on rejection; and
- avoid automatically changing any membership, sheet-vendor binding, credential, or organization lifecycle.

The exact physical lifecycle and constraints belong to `VENDOR-ID-002`. Assignment mutation belongs to `VENDOR-ID-TBD — Vendor relationship mutation`.

### 9.3 Assignment authority boundary

Site assignment alone does not:

- authenticate an actor;
- establish membership;
- choose a sheet;
- authorize a read;
- authorize a write;
- grant an internal site role;
- grant portfolio access; or
- establish a current-site session.

Future runtime authorization must combine a re-canonicalized backend principal with separately approved active organization and relationship checks.

Missing, inactive, duplicate, conflicting, or ambiguous site assignments fail closed.

### 9.4 Provenance

Every future site assignment must preserve:

- organization identity;
- site identity;
- status;
- actor;
- authorized role;
- reason;
- source/provenance;
- created and updated timestamps; and
- correlation or idempotency evidence where mutation is introduced.

## 10. Sheet-vendor binding

### 10.1 Relationship definition

Sheet-vendor binding is an explicit relationship between:

- one vendor organization identified by `vendor_id`; and
- one canonical sheet.

The sheet must belong to a site for which the same vendor organization has an active vendor-site assignment.

A binding must reference `vendor_id`, not only a display label, username, vendor account ID, task value, or session value.

### 10.2 Binding lifecycle and cardinality

Every future sheet-vendor binding must have an explicit conceptual status:

- `active`;
- `inactive`.

The exact conceptual binding transitions are:

- initial creation to `active`;
- `active` to `inactive`; and
- `inactive` to `active` only through explicit reactivation.

The following cardinality is frozen:

- one vendor organization may bind to multiple distinct sheets through distinct explicit relationships;
- one sheet may bind to multiple distinct vendor organizations through distinct explicit relationships;
- one organization/sheet pair may have at most one current binding; and
- multiple active bindings for the same organization/sheet pair are invalid.

Every active binding requires an active vendor-site assignment for the site that owns the bound sheet.

An inactive binding:

- is historical;
- grants no sheet-derived eligibility;
- must not be selected as a trusted target;
- remains available for provenance and audit; and
- must not be silently reactivated, replaced, or rewritten.

Binding creation, deactivation, or reactivation must:

- verify the current binding state;
- verify organization, sheet, and site identity;
- verify the active same-site vendor-site assignment;
- reject duplicate, stale, conflicting, ambiguous, or cross-site state;
- avoid first-result, name-derived, remembered, or caller-selected resolution;
- leave existing state unchanged on rejection; and
- avoid automatically changing any site assignment, membership, credential, or organization lifecycle.

The exact physical lifecycle and constraints belong to `VENDOR-ID-002`. Binding mutation belongs to `VENDOR-ID-TBD — Vendor relationship mutation`.

### 10.3 Site consistency

Before any future binding is created or used, the server-controlled implementation must confirm:

- the sheet exists;
- the sheet belongs to exactly one canonical site under the applicable site contract;
- the vendor organization exists;
- the organization is eligible under its lifecycle;
- an active vendor-site assignment exists for that same site; and
- the binding itself is active and unambiguous.

Caller-supplied site or sheet values are requests, not authority.

### 10.4 Trusted-target behavior

Trusted-target selection remains fail closed:

- no candidate means unavailable;
- one fully canonical and active candidate may be considered by a later authority contract;
- multiple active candidates are ambiguous;
- conflicting site or sheet relationships are invalid; and
- no remembered, browser-supplied, name-derived, or first-sorted candidate may resolve ambiguity.

Site assignment alone does not choose a sheet.

One implicit vendor per sheet is not assumed.

### 10.5 Provenance

Every future sheet-vendor binding must preserve:

- organization identity;
- sheet identity;
- site identity;
- status;
- actor;
- authorized role;
- reason;
- source/provenance;
- created and updated timestamps; and
- correlation or idempotency evidence where mutation is introduced.

### 10.6 Current runtime preservation

Live runtime continues using the existing frozen `vendor_name`-based trusted-target behavior until a separately approved authority-switch slice.

VENDOR-ID-001 does not:

- add a binding store;
- alter target resolution;
- alter multi-target behavior;
- change current error codes;
- change current request or response fields; or
- authorize dual-write or shadow authority.

## 11. Operational workflow and trusted-target boundary

### 11.1 Preserved runtime surfaces

The following current surfaces and workflows remain unchanged:

- vendor login and logout;
- current vendor session behavior;
- `/vendor/home`;
- `/vendor/profile`;
- `/vendor/scope`;
- `/vendor/business-read-preview`;
- `/vendor/work-entry`;
- `/api/vendor/work-entry/preflight`;
- `/api/vendor-work-entry`;
- `/api/vendor-contact`;
- crew requirement confirmation;
- formal approval and cancellation;
- scheduling behavior;
- current-site and cross-site guards;
- current response shapes and error codes;
- current free-text fixtures; and
- existing Production data.

### 11.2 Current legacy authority

Current runtime use of canonical account/session `vendor_name` plus `tasks.vendor` for business scope and trusted-target derivation is classified as:

- preserved legacy authority;
- not the future canonical organization authority;
- not evidence that free-text labels are clean or unique; and
- not safe precedent for new vendor expansion.

No new consumer may adopt this legacy join as its future authority model merely because current operational workflows remain frozen.

### 11.3 Caller input

Current caller-submitted vendor name, sheet, entry, and business-date fields retain their existing validation behavior.

Future `vendor_id`, site, sheet, organization status, membership, and relationship values supplied by a caller must remain untrusted requests.

Future protected operations must derive authority from:

- the authenticated and re-canonicalized backend principal;
- the canonical active membership under the approved authority model;
- canonical organization lifecycle;
- canonical active vendor-site assignment;
- canonical active sheet-vendor binding; and
- the operation-specific permission contract.

### 11.4 No implied CRUD

This document creates no vendor organization:

- list;
- search;
- autocomplete;
- select;
- create;
- edit;
- rename;
- disable;
- retire;
- reactivate;
- delete;
- owner-transfer;
- membership;
- site-assignment;
- sheet-binding;
- import;
- export; or
- batch-mutation workflow.

## 12. Authentication, authorization, and AUTH-ID boundary

### 12.1 Authentication separation

Vendor organization identity is not global human identity.

`vendor_id` is not:

- a login identifier;
- a username;
- a password subject;
- a credential principal;
- a session secret;
- a global identity; or
- proof of account ownership.

`vendor_accounts.id` remains a backend principal.

Membership does not authenticate a principal and does not perform account recognition.

### 12.2 Authorization separation

Vendor organization, membership, site assignment, and sheet binding are business relationships.

None grants runtime authority automatically.

No future authorization decision may use:

- raw `vendor_id`;
- raw `vendor_name`;
- normalized vendor name;
- raw vendor account ID;
- username;
- caller-selected site;
- caller-selected sheet; or
- a remembered target

as sufficient proof.

### 12.3 AUTH-ID E2/F/G/H exclusions

VENDOR-ID cannot acquire or exercise:

- E2 identity-registry ID generation/validation and future creation-consumer collision, retry, caller-supplied-ID, and transaction-acceptance authority;
- F global-identity lifecycle, merge, movement, or remapping authority;
- G account-linking, unlinking, or identity-proof authority;
- H repair, reconciliation, plan, apply, mutation, or winner-selection authority.

VENDOR-ID cannot:

- create or reconcile global identities;
- infer global identity from vendor organization or membership;
- link internal and vendor principals;
- move a backend principal between global identities;
- choose a reconciliation winner;
- repair identity-registry anomalies; or
- reuse discovery evidence as mutation authorization.

### 12.4 Credential and session exclusions

Credential, password, password-hash, account-recognition, login-failure, session-key, session-migration, and global-identity-session work remain outside this slice.

No VENDOR-ID owner may change those boundaries without the independently approved AUTH owner.

## 13. Privacy, provenance, and audit requirements

### 13.1 Required future evidence

Where future writes are separately authorized, they must preserve:

- canonical actor identity;
- authenticated backend principal;
- authorized role;
- operation;
- reason;
- source/provenance;
- created and updated timestamps;
- correlation identifier;
- idempotency evidence where retries are possible;
- before/after evidence for lifecycle or relationship changes; and
- success, rejection, conflict, and rollback outcome.

### 13.2 Sensitive data boundary

Future reports, discovery artifacts, logs, errors, and audit evidence must not contain:

- passwords;
- password hashes;
- session cookies or session state;
- credential material;
- backend secrets;
- database URLs;
- environment secrets;
- raw authentication proofs; or
- unnecessary personal contact data.

Vendor ID or vendor name must not be recorded or displayed as proof that an actor was authorized.

### 13.3 Bounded discovery and reporting

Where raw values are unnecessary, future discovery and readiness evidence must use:

- aggregate counts;
- bounded classifications;
- redacted or non-reversible identifiers;
- deterministic ordering; and
- explicit incomplete or indeterminate states.

Discovery output is evidence only. It is not repair, merge, backfill, lifecycle, or authority-switch permission.

### 13.4 No audit implementation here

This document does not add:

- an audit table;
- an event schema;
- an event stream;
- a logging API;
- a report format;
- a database trigger; or
- any audit write path.

Those physical and runtime decisions require their named later owners.

## 14. Legacy free-text data and reconciliation boundary

### 14.1 Legacy evidence classification

Existing values in:

- `tasks.vendor`;
- `vendor_accounts.vendor_name`;
- `vendor_contacts.vendor_name`;
- `vendor_work_entries.vendor_name`; and
- related fixtures, imports, exports, projections, or reports

are legacy free-text evidence.

They are not assumed:

- clean;
- normalized;
- unique;
- complete;
- current;
- mutually consistent;
- site-consistent;
- organization-consistent; or
- safe to map automatically.

### 14.2 No data access or mutation

This docs-only slice does not:

- open a database;
- count vendor rows;
- inspect vendor values;
- compare environments;
- normalize names;
- classify candidates;
- create mappings;
- rewrite labels;
- delete records;
- backfill `vendor_id`;
- merge organizations; or
- reconcile conflicts.

Production or DEV deployment health does not establish the contents or topology of this data.

### 14.3 Matching boundary

Name equality alone cannot establish a mapping.

Future mapping readiness must support at least:

- zero candidates;
- one candidate requiring evidence;
- multiple candidates;
- conflicting candidates;
- missing relationships;
- stale relationships;
- unmapped legacy values; and
- indeterminate results.

Ambiguous or conflicting results fail closed.

No automatic organization creation, merge, reassignment, owner selection, membership creation, site assignment, or sheet binding may result from discovery.

### 14.4 Reconciliation separation

The sequence is:

- conceptual design;
- physical schema;
- read-only discovery and dry-run;
- independently approved controlled backfill;
- separately approved runtime authority switch; and
- separately approved lifecycle or relationship mutation.

Repair, merge, alias handling, conflict resolution, reconciliation, and authority movement remain separate approvals.

## 15. Migration and authority-switch sequencing

The required sequence is:

```text
VENDOR-ID-001
Conceptual organization / owner-member design

VENDOR-ID-002
Physical schema and migration design/implementation

VENDOR-ID-003
Read-only readiness, discovery, and dry-run mapping

VENDOR-ID-004
Controlled backfill under independently approved evidence gates

VENDOR-ID-TBD
Runtime authority switch and consumer wiring

VENDOR-ID-TBD
Lifecycle, rename, membership, assignment, or relationship mutation
```

Only `VENDOR-ID-001` through `VENDOR-ID-004` are existing assigned permanent IDs.

Each `VENDOR-ID-TBD` label is descriptive and requires Product Owner naming before implementation.

### 15.1 Slice isolation

The following must not share one implementation slice:

- conceptual design and physical schema;
- physical schema and live backfill;
- discovery and live mutation;
- backfill and runtime authority switch;
- authority switch and relationship/lifecycle mutation;
- vendor organization migration and credential/session migration; or
- vendor relationships and AUTH-ID linking/reconciliation.

### 15.2 Schema-stage boundary

`VENDOR-ID-002` may define and implement separately approved physical storage and compatibility behavior.

It must not:

- scan live vendor content;
- create name-based mappings;
- backfill organizations;
- switch read or write authority;
- alter current vendor responses;
- migrate credentials or sessions; or
- implement organization CRUD.

### 15.3 Discovery-stage boundary

`VENDOR-ID-003` must be:

- read-only;
- evidence-first;
- bounded;
- deterministic;
- fail closed;
- aggregate/redacted where raw values are unnecessary; and
- incapable of performing backfill or authority switch.

### 15.4 Backfill-stage boundary

`VENDOR-ID-004` requires independently approved:

- discovery evidence;
- conflict classification;
- mapping review;
- maintenance/write-freeze plan;
- idempotency;
- rollback;
- no-write rejection evidence;
- post-operation reconciliation; and
- environment-specific authorization.

Backfill must not itself switch runtime authority.

### 15.5 Authority-switch boundary

Runtime authority may switch only in a separately approved `VENDOR-ID-TBD` slice after schema, discovery, backfill, compatibility, and rollback evidence are complete.

The switch must explicitly cover every consumer that currently uses `vendor_name`, `tasks.vendor`, vendor-account data, site context, sheet context, or work-entry ownership.

No consumer is pre-authorized by this document.

## 16. Rejected alternatives

### 16.1 `vendor_name` as primary key

Rejected because names are mutable, non-unique, free text, and currently reused across records and scopes.

### 16.2 Normalized name as identity

Rejected because normalization is lossy, policy-dependent, and incapable of proving that two labels represent one organization.

### 16.3 `vendor_accounts.id` as organization ID

Rejected because it is a backend-local credential principal. One organization may have multiple accounts, and credentials have an independent lifecycle.

### 16.4 Username as organization ID

Rejected because username identifies a credential account, is not a business entity, and may change under a separate authentication policy.

### 16.5 Site or sheet encoded in `vendor_id`

Rejected because organization identity must remain stable across relationship changes and may relate explicitly to multiple sites or sheets.

### 16.6 Automatic organization creation from free text

Rejected because current free-text values are not proven clean, unique, canonical, current, or organization-consistent.

### 16.7 Automatic name-based merge

Rejected because equal names are not identity proof and merge requires dedicated authority, conflict handling, provenance, rollback, and reconciliation.

### 16.8 One implicit vendor per sheet

Rejected because a sheet may contain multiple vendor labels and a vendor may relate to multiple sheets. Neither direction can be guessed.

### 16.9 Site assignment as authorization

Rejected because an organization-to-site relationship does not authenticate an actor, establish membership, choose a sheet, or grant operation-specific permission.

### 16.10 Runtime authority replacement in schema slice

Rejected because physical capability, migrated data, reconciled data, and authorized runtime behavior are different gates.

### 16.11 Hard deletion of referenced vendors

Rejected because historical work, contacts, approvals, scheduling, provenance, and audit attribution must remain stable.

### 16.12 CRUD or UI before ownership and migration contracts

Rejected because an interface would prematurely freeze unsafe identity, duplicate, lifecycle, assignment, and authority semantics.

### 16.13 Membership inferred from usage

Rejected because login history, work-entry creation, contact data, task names, or existing sessions do not prove organization membership or owner role.

### 16.14 Global identity reused as vendor organization

Rejected because a global identity represents an actor identity, while a vendor organization is a business entity with separate membership and relationship semantics.

## 17. Owner matrix and deferred slices

No deferred item is authorized merely by appearing in this table.

`VENDOR-ID-TBD` entries require Product Owner naming and a separate gate before work begins.

| Decision | Current owner | Frozen decision | Deferred implementation owner | Forbidden inference |
|---|---|---|---|---|
| Exact `vendor_id` physical format | `VENDOR-ID-001` conceptual boundary | Stable, opaque, non-semantic, server-controlled | `VENDOR-ID-002` | Do not derive from name, account, site, sheet, or global identity |
| Organization DDL | `VENDOR-ID-001` conceptual entity | One durable organization identity with lifecycle | `VENDOR-ID-002` | Current vendor tables do not imply the physical design |
| Membership DDL | `VENDOR-ID-001` cardinality and lifecycle | Explicit account-to-organization relationship with exact pending/active/revoked transitions and at most one active organization per account | `VENDOR-ID-002` | Do not infer membership from account `vendor_name` or auto-revoke another membership |
| Membership status mutation | `VENDOR-ID-001` transition contract | Creation to pending; pending to active/revoked; active to revoked; revoked history immutable | `VENDOR-ID-TBD — Vendor membership mutation` | Do not reactivate in place, replace, move, or rewrite a revoked relationship |
| Membership role mutation | `VENDOR-ID-001` role and minimum-owner contract | Explicit active member/owner transition; last owner protected; role and status remain separate | `VENDOR-ID-TBD — Vendor membership mutation` | Do not auto-promote or change organization, account, assignment, or binding |
| Vendor-site assignment storage | `VENDOR-ID-001` relationship semantics | Explicit `vendor_id`-to-site relation with active/inactive status, one current pair, and preserved history/provenance | `VENDOR-ID-002` | Do not infer assignment from matching task or entry labels |
| Vendor-site assignment mutation | `VENDOR-ID-001` transition contract | Creation active; active to inactive; explicit inactive-to-active reactivation | `VENDOR-ID-TBD — Vendor relationship mutation` | Do not duplicate, silently replace/reactivate, or change membership/binding/credential/lifecycle |
| Sheet-vendor binding storage | `VENDOR-ID-001` relationship semantics | Explicit, site-consistent `vendor_id`-to-sheet relation with active/inactive status and one current pair | `VENDOR-ID-002` | Do not infer one vendor per sheet or one sheet per vendor |
| Sheet-vendor binding mutation | `VENDOR-ID-001` transition contract | Creation active; active to inactive; explicit inactive-to-active reactivation with active same-site assignment | `VENDOR-ID-TBD — Vendor relationship mutation` | Do not duplicate, cross sites, silently replace/reactivate, or change assignment/membership/credential/lifecycle |
| Display-name normalization | `VENDOR-ID-001` authority boundary | Lookup aid only; never identity or authority | `VENDOR-ID-TBD — Display-name normalization and duplicate-review contract` | Equal normalized text does not prove same organization |
| Duplicate detection | `VENDOR-ID-001` fail-closed policy | Ambiguous candidates remain distinct and non-mutating | `VENDOR-ID-003` for discovery; mutation remains `VENDOR-ID-TBD` | Discovery must not merge or choose a winner |
| Rename | `VENDOR-ID-001` identity invariant | Rename preserves `vendor_id` and relationships | `VENDOR-ID-TBD — Vendor relationship mutation` | Rename must not become merge, reassignment, or authority switch |
| Disable/retire/reactivate | `VENDOR-ID-001` conceptual lifecycle | Explicit states; history retained; no hard delete | `VENDOR-ID-TBD — Vendor lifecycle mutation` | Credential status is not organization lifecycle |
| Owner transfer | `VENDOR-ID-001` minimum-owner and role-transition invariant | Explicit atomic target promotion/source demotion; no automatic promotion; zero-owner state forbidden | `VENDOR-ID-TBD — Vendor membership mutation` | Usage, username, or contact data does not prove ownership |
| Membership revoke | `VENDOR-ID-001` status-transition boundary | Pending or active may become revoked; revoked relationship and role history remain immutable | `VENDOR-ID-TBD — Vendor membership mutation` | Revocation must not move or disable the organization or be reversed in place |
| Read-only discovery/dry-run | `VENDOR-ID-001` evidence boundary | Bounded, non-mutating, ambiguity-preserving | `VENDOR-ID-003` | Name equality is not a mapping decision |
| Controlled backfill | `VENDOR-ID-001` sequencing boundary | Evidence-gated, reversible, separate from authority switch | `VENDOR-ID-004` | Schema or discovery does not authorize mutation |
| Runtime authority switch | `VENDOR-ID-001` separation boundary | Separate after schema, discovery, backfill, and compatibility proof | `VENDOR-ID-TBD — Runtime authority switch and consumer wiring` | Existing `vendor_name` routing is not the target authority |
| Merge/reconciliation | `VENDOR-ID-001` prohibition | No automatic merge, winner, movement, or repair | `VENDOR-ID-TBD`, with applicable AUTH-ID owner where principals are involved | Duplicate labels do not authorize merge |
| Credential/session migration | AUTH owners | Outside vendor organization scope | Applicable `AUTH-SESSION` / vendor-auth Product Owner-named slice | `vendor_id` must not replace backend credential principal automatically |
| Organization CRUD/API/UI | `VENDOR-ID-001` sequencing boundary | Not implemented before schema, ownership, migration, and authority contracts | `VENDOR-ID-TBD — Vendor organization management` | UI availability must not define authority |
| Site/sheet relationship mutation | `VENDOR-ID-001` lifecycle, cardinality, and site-consistency invariants | Exact active/inactive transitions, one current relationship per pair, audited, no silent movement | `VENDOR-ID-TBD — Vendor relationship mutation` | Caller-selected target is not authority and duplicate current relationships are invalid |
| Audit/event physical model | `VENDOR-ID-001` evidence requirements | Actor, reason, provenance, correlation, before/after required | `VENDOR-ID-TBD — Vendor audit implementation` | Logs or names are not authorization proof |

## 18. Future implementation acceptance matrix

Each future slice must define its own exact commands, fixtures, hashes, environment boundary, and approved mutation scope. The following evidence is a minimum contract, not execution authorization.

| Future gate | Required acceptance evidence | Mandatory rejection/no-write evidence |
|---|---|---|
| Physical organization identity | Stable opaque organization identity; deterministic schema manifest; no business data encoded in key | Reject caller-controlled or name/site/account-derived identity |
| Account/member separation | Backend principal, organization, membership, role, and status remain distinct; exact cardinality and uniqueness enforced | Reject duplicate pending/active membership and multi-active-organization account |
| Membership status transitions | Prove creation-to-pending, pending-to-active/revoked, active-to-revoked, activation eligibility, and immutable revoked history | Reject active-to-pending, in-place revoked reactivation, other-membership auto-revoke, stale/duplicate/conflicting activation, and any rejected-path write |
| Membership role transitions | Prove explicit active member-to-owner and owner-to-member transitions independently of status | Reject pending/revoked role authority, last-owner demotion/revocation, automatic promotion, and relationship movement |
| Minimum-owner invariant | At least one active owner once management is enabled; atomic target-promotion/source-demotion transfer proof | Reject last-owner removal, stale transfer, cross-organization target, automatic promotion, and partial transfer |
| Organization lifecycle | Exact active/disabled/retired behavior; `vendor_id` and history preserved | Reject hard delete, silent relationship movement, stale state, and implicit restoration |
| Display-name rename | Rename preserves `vendor_id`, history, memberships, assignments, and bindings | Reject rename-as-merge, rename-as-authority-switch, and ambiguous target |
| Duplicate/ambiguity handling | Zero/one/multiple/conflicting outcomes are explicit and bounded | Reject winner guessing, automatic merge, and normalized-name authority |
| Vendor-site assignment | Prove active/inactive lifecycle, exact transitions, one current organization/site pair, multi-distinct-site cardinality, provenance, and preserved inactive history | Reject duplicate create/reactivate, multiple active same-pair assignments, silent replacement/reactivation, stale/conflicting state, and relationship side effects |
| Sheet-vendor binding | Prove active/inactive lifecycle, exact transitions, one current organization/sheet pair, many-to-many distinct-pair cardinality, active same-site assignment, and complete provenance | Reject duplicate create/reactivate, multiple active same-pair bindings, cross-site/stale/conflicting state, caller-selected or first-result authority, and relationship side effects |
| Protected read/write authorization | Re-canonicalized backend principal plus approved active canonical relationships and operation-specific authorization | Reject raw ID/name authority, cross-site leakage/write, stale session/relationship, and ambiguous target |
| Rejected path behavior | Deterministic errors and complete before/after no-write proof | Any rejected, forbidden, stale, duplicate, or ambiguous path that mutates data fails the gate |
| Current workflow compatibility | Current routes, response shapes, error codes, and behavior remain unchanged until separately authorized | Reject accidental consumer wiring, dual authority, or changed current runtime behavior |
| Read-only discovery | Bounded deterministic output, aggregate/redacted evidence, explicit incomplete/indeterminate states | Reject writes, credentials in output, name-based mapping, or repair authority |
| Controlled backfill | Reviewed dry-run mapping, conflict handling, idempotency, rollback, write freeze, post-checks | Reject unresolved ambiguity, unreviewed mapping, authority switch, or partial mutation |
| Runtime authority switch | Exact consumer inventory, compatibility plan, rollback, cross-site/no-write tests, independently approved deployment gate | Reject switching any consumer before schema, discovery, backfill, and reconciliation evidence passes |
| Validation environment | Disposable SQLite fixtures only where a later implementation gate authorizes database validation; source and sidecars controlled | Reject DEV or Production DB access during implementation gates and reject persistent fixture reuse |
| Privacy and audit | Actor/role/reason/provenance/correlation/before-after evidence without secrets | Reject passwords, hashes, sessions, credentials, backend secrets, or raw authority proofs in output |
| AUTH-ID separation | No global-identity creation, linking, movement, lifecycle, or reconciliation side effect; no E2 identity-registry ID generation/validation or future creation-consumer acceptance role | Reject any vendor operation that acquires E2 collision/retry/caller-supplied-ID/transaction-acceptance, F lifecycle/movement, G linking, or H reconciliation authority |

Global future-gate rules:

- no Production or DEV database access during implementation gates;
- no caller-selected identity, organization, role, site, sheet, membership, or relationship may become authority;
- no rejected path may write;
- no schema presence may be reported as feature completion;
- no dry-run may become backfill;
- no backfill may become runtime authority switch;
- no runtime authority switch may be combined with lifecycle or relationship mutation;
- no current response or workflow contract may change until its dedicated consumer gate is approved; and
- every later slice must stop when its exact evidence is incomplete or contradictory.

VENDOR-ID-001 completion means only that the conceptual organization and owner/member contract is frozen.

It does not mean:

- physical schema started;
- vendor rows were discovered;
- existing labels were classified;
- mappings were approved;
- backfill was authorized;
- runtime authority changed;
- CRUD or UI was authorized;
- lifecycle or relationship mutation was authorized; or
- AUTH-ID work was reopened.
