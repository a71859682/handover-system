# AUTH-UX-001A — Unified Login Design Freeze

Status: design freeze

Scope: docs-only

Implementation status: not started

## 1. Baseline

- Repository: `C:\Users\耀祥\Documents\handover-system-formal`
- Design worktree base: `origin/develop`
- Frozen main: `f76866613d9340359cd792422d6bbf88df61c32c`
- Frozen develop: `f76866613d9340359cd792422d6bbf88df61c32c`
- Frozen Production: `f76866613d9340359cd792422d6bbf88df61c32c`
- AUTH-ORDER: CLOSED / FROZEN

This document defines the product and security baseline for a future unified login entrypoint. It does not implement UI, API, schema, routing, or session changes.

## 2. Current-state inventory

### 2.1 Current login entrypoints

- Internal login: `POST /login` (`app.py:6622-6654`)
- Vendor login: `POST /vendor/login` (`app.py:6657-6668`)
- Internal logout: `POST /logout` (`app.py:6676-6680`)
- Vendor logout: `GET /vendor/logout` (`app.py:6683-6686`)

### 2.2 Current canonical account sources

Current internal and vendor authentication still use separate account backends.

- Internal account source:
  - `get_user_by_username()` → `_sqlite_get_user_by_username()` (`app.py:1182-1186`, `app.py:186-194`)
- Vendor account source:
  - `get_vendor_account_by_username()` → `_sqlite_get_vendor_account_by_username()` (`app.py:1196-1197`, `app.py:210-218`)

This means the current system does not have a unified global account registry yet.

### 2.3 Current internal session markers

Successful internal login writes these session markers (`app.py:6631-6635`):

- `user_id`
- `username`
- `display_name`
- `role`

Current-site routing may then add or normalize:

- `current_site_id`
- `current_site_name`
- `site_selection_required`
- `sheet_id` may later be set by page navigation, not by login itself

Important current-state note:

- Internal login currently does **not** set `identity_type = "internal"`.
- Internal-vs-vendor distinction is inferred from `user_id` presence versus vendor markers (`app.py:4188-4198`).

### 2.4 Current vendor session markers

Successful vendor login clears the session, then writes (`app.py:6660-6666`, `app.py:4341-4346`):

- `identity_type = "vendor"`
- `vendor_account_id`
- `vendor_username`
- `vendor_name`

Vendor protected pages use:

- `vendor_login_required()` (`app.py:4360-4368`)
- `current_vendor_account()` (`app.py:4178-4185`)

### 2.5 Mixed-session rejection convention

Current mixed-session rejection is explicit:

- `resolve_vendor_work_entry_actor_session_type()` checks:
  - internal present = `session["user_id"] is not None`
  - vendor present = `identity_type == "vendor"` or vendor markers present
- If both are present, it raises `LookupError("ambiguous_actor_session")` (`app.py:4188-4198`)

Current API behavior on mixed session:

- vendor work-entry actor lookup returns `409 ambiguous_actor_session` (`app.py:4289-4305`)

Current write authority rule:

- Internal-only mutation resolvers reject vendor sessions as `vendor_auth_forbidden` (`app.py:2435-2449`)

### 2.6 Stale / deleted / inactive account handling

#### Internal

- `_current_internal_user()` reloads the current user by `user_id` on demand (`app.py:5502-5506`)
- `_resolve_canonical_internal_actor_snapshot()` re-canonicalizes every protected mutation request by reading `session["user_id"]` and then calling `_current_internal_user()` (`app.py:2418-2432`)
- If the user is missing, invalid, or stale, the internal canonical resolver fails with `auth_required`

#### Vendor

- `is_vendor_session()` requires all vendor markers to be present (`app.py:4169-4175`)
- `_resolve_canonical_vendor_work_entry_actor_snapshot()` re-reads `vendor_accounts` by `vendor_account_id` every protected vendor mutation request (`app.py:4201-4229`)
- If the account is deleted, inactive, or the stored markers no longer match canonical data, the code:
  - clears vendor session markers
  - raises `vendor_session_inactive`

#### Vendor credential verification

- `verify_vendor_account()` rejects:
  - unknown vendor username
  - inactive vendor account
  - password mismatch
  (`app.py:4349-4356`)

### 2.7 Internal post-login site-selector flow

After successful internal password verification, the current flow is:

1. `session.clear()`
2. write internal session markers
3. call `normalize_current_site_for_user(user)` (`app.py:6631-6636`)
4. route by resolution status

Current internal routing outcomes:

- zero accessible sites:
  - `access_denied_no_site_permission`
  - session is cleared
  - flash error
  - redirect back to `/login`
  (`app.py:6638-6642`, `app.py:5622-5631`)

- one accessible site:
  - status `resolved`
  - current site auto-selected
  - redirect to `/sheet`
  (`app.py:5633-5646`, `app.py:5496-5499`)

- multiple accessible sites with valid remembered current site:
  - status `resolved`
  - redirect to `/sheet`
  (`app.py:5648-5658`)

- multiple accessible sites without valid remembered site:
  - status `site_selection_required`
  - clear current-site state
  - set `site_selection_required = True`
  - redirect to `/site-selector`
  (`app.py:5660-5667`, `app.py:5678-5681`, `app.py:5496-5499`)

Current admin behavior:

- Admins are treated specially and fall back to the default active site when the remembered current site is absent or inactive (`app.py:5596-5620`)

### 2.8 Vendor trusted site / sheet scope

Current vendor business scope is still resolved from canonical vendor session plus vendor-task relationships.

For vendor write authority:

- canonical session authority is derived from `vendor_account_id`
- then current vendor business identity exposes:
  - `vendor_account_id`
  - `vendor_username`
  - `vendor_name`

Trusted write target resolution is currently sheet-based:

- `resolve_vendor_work_entry_trusted_target(conn, vendor_name=...)`
- query finds active sheets with tasks whose `vendor` matches canonical `vendor_name`
- zero candidates → `vendor_scope_unavailable`
- multiple candidates → `vendor_scope_ambiguous`
  (`app.py:4265-4286`)

Current vendor mutation contract for `/api/vendor-work-entry`:

- actor is resolved first (`app.py:7304-7307`)
- vendor branch enforces:
  - payload `sheet_id` must match trusted target sheet
  - payload `vendor_name` must match canonical vendor session `vendor_name`
  - payload `business_date` must match canonical crew business date
  (`app.py:7335-7369`)

Current vendor preflight contract for `/api/vendor/work-entry/preflight`:

- uses current vendor business identity
- can reject `vendor_name_mismatch`
- can reject cross-vendor entry updates
  (`app.py:4387-4453`, `app.py:8103-8134`)

### 2.9 Existing logout / session-clear behavior

- Internal logout:
  - `POST /logout`
  - `session.clear()`
  - redirect `/login`
  (`app.py:6676-6680`)

- Vendor logout:
  - `GET /vendor/logout`
  - `session.clear()`
  - redirect `/vendor/login`
  (`app.py:6683-6686`)

- Vendor stale-session cleanup:
  - `clear_vendor_session()` clears vendor-only markers
  - vendor-protected page decorator also clears vendor markers before redirecting when vendor session is invalid
  (`app.py:4158-4163`, `app.py:4360-4365`)

### 2.10 Existing unauthorized response conventions

Current unauthorized behavior is not globally uniform; it depends on route family.

#### Internal page routes

- `@login_required` → redirect `/login` (`app.py:4122-4129`)
- missing or invalid current site on read:
  - redirect `/site_selector` or `/sheet` with flash, depending on cause
  (`app.py:1321-1338`)

#### Internal JSON read APIs

- grid/site read failures return JSON with `error.code` and 403/404 (`app.py:1341-1353`)

#### Internal-only business APIs hit by vendor or unauthenticated session

- return JSON `auth_required` or `vendor_auth_forbidden`
- generally 403
  (`app.py:1356-1389`, `app.py:2435-2462`)

#### Vendor protected pages

- `@vendor_login_required` redirects `/vendor/login` when vendor session is absent/invalid (`app.py:4360-4368`)

#### Vendor mutation APIs

- unauthenticated vendor actor lookup → 401 `auth_required`
- ambiguous mixed session → 409
- inactive/stale vendor session → 401 `vendor_session_inactive`
  (`app.py:4289-4305`)

### 2.11 Current vendor identity authority

Current code evidence already distinguishes vendor login principal from vendor display naming, but it does **not** yet have a separately modeled canonical vendor organization identity.

Current-state facts:

- Canonical vendor login principal is keyed by `vendor_account_id` and re-canonicalized from `vendor_accounts` (`app.py:4206-4229`)
- `vendor_account_id` currently identifies the authenticated vendor account principal
- `vendor_account_id` does **not** by itself prove that the system already has a separately modeled vendor organization authorization identity such as future `vendor_id`
- `vendor_name` is still used downstream for trusted target and business grouping (`app.py:4265-4286`, `app.py:4476-4510`, `app.py:7303-7448`)

Therefore, the accurate current-state statement is:

- current authentication authority is anchored by `vendor_account_id`
- current trusted-target and business scoping still depends in part on canonical `vendor_name`
- current code should be described as using vendor-account principal authority plus `vendor_name`-based business scoping, not as already having completed `vendor_id`-based authorization modeling

Future target-state freeze implied by this document:

- future unified login must preserve `vendor_account_id` only as the authenticated vendor account principal
- future vendor organization authorization and ownership must be anchored by canonical `vendor_id`
- `vendor_name` must be treated as display alias / business label only, not future authorization identity
- AUTH-UX-001A does **not** claim that current schema, current write paths, or current trusted-target resolution have already been migrated to `vendor_id`

## 3. Target design freeze

### 3.1 Unified entry meaning

Unified login means:

- one user-facing login entrypoint
- one interaction model
- one product-level recognition/authentication flow

Unified login does **not** mean, in this slice:

- immediate merge of `users` and `vendor_accounts`
- immediate schema unification
- immediate session schema replacement

Frozen decision:

- until dedicated migration slices land, internal and vendor canonical authentication backends remain separate
- UI must not infer actor type from sheet content, vendor display name, remembered route, or guessed business scope

### 3.2 Account recognition

Future unified login must use a two-stage model.

Stage 1: account recognition

- user enters a single login identifier
- recognition returns one of:
  - internal candidate
  - vendor candidate
  - unknown
  - ambiguous / collision state
  - inactive / unavailable state

Frozen decisions:

- recognition result is not authentication authority
- recognition must not create an authorized session
- recognition must not trigger backend fallback login attempts
- username collision across internal and vendor namespaces must be handled as an explicit ambiguous state, not guessed
- unknown / inactive / ambiguous outward responses must not become an account-existence oracle

External response rule:

- before password authentication succeeds, user-visible failure language must remain generic enough not to disclose:
  - account type
  - site membership
  - vendor organization
  - trusted target existence

### 3.3 Authentication

Frozen decisions:

- password verification must be performed only against the backend selected by account recognition
- internal candidate → internal canonical backend only
- vendor candidate → vendor canonical backend only
- no cross-backend fallback retries
- no “try internal, then vendor” or “try vendor, then internal” password checks for the same submission
- no authority-bearing session may be created before successful password verification

Failure contract:

- login failure must not disclose:
  - whether a matching account exists
  - whether it is internal or vendor
  - whether the vendor has a trusted target
  - whether the internal user has site access

### 3.4 Session authority

Frozen decisions:

- internal and vendor sessions must never be simultaneously valid
- establishing a new canonical session must clear all prior actor markers first
- every protected request must continue to re-canonicalize against the source of truth
- preview / recognition state must never become write authority
- browser-supplied values for:
  - role
  - vendor name
  - site
  - sheet
  may not serve as authorization authority

Future direction frozen here:

- internal authority remains user-account based
- vendor login principal remains vendor-account based
- vendor organization authorization identity must be future canonical `vendor_id`, not `vendor_name`
- future vendor account principal or future global account principal must bind to `vendor_id` through canonical relations
- business routing may depend on canonical relationships, but authority must not depend on UI-provided aliases
- future vendor-site assignment authority must bind by `vendor_id`
- future sheet-vendor binding authority must bind by `vendor_id`
- future vendor work-entry ownership must bind by `vendor_id`
- future trusted-target resolution must be derived from canonical `vendor_id` relationships, not from `vendor_name`
- current `vendor_name`-based scoping is a frozen current-state fact only; migration, backfill, compatibility, rollback, and no-write verification must be completed in later dedicated slices

### 3.5 Post-login routing contract

This slice freezes routing semantics only.

#### Internal

Zero-site:

- authenticate successfully
- do not establish a usable business session
- route to generic blocked state with no target leakage

One-site:

- authenticate successfully
- auto-resolve current site
- continue to the normal internal post-login destination

Multi-site:

- authenticate successfully
- require explicit site selection unless a remembered site is still authorized and valid

Stale current-site:

- if remembered site no longer exists, is inactive, or is no longer authorized, it must not be reused as authority

Unauthorized remembered site:

- remembered site must be ignored or cleared
- system must route via valid selection / fallback logic only

#### Vendor

Inactive account:

- authentication may not yield a usable session
- outward response must remain non-disclosing

Zero trusted target:

- authenticated vendor without current valid business target must not receive write authority

One trusted target:

- authenticated vendor may route directly to the canonical vendor destination bound to that target

Multiple trusted targets:

- system must not guess
- route to explicit selection / disambiguation state defined in a later slice

Stale / revoked vendor-site or sheet binding:

- remembered or preview target must be revalidated before use
- stale bindings must not produce write authority

### 3.6 UI flow

Future unified login will use a two-stage interaction design.

Stage 1: account recognition

- accept one login identifier
- show neutral recognition outcome
- never disclose hidden business data

Stage 2: credential authentication

- authenticate only against the recognized canonical backend
- create one canonical session if successful
- clear previous actor markers before session establishment

Success routing:

- internal and vendor route according to their frozen contracts above

Generic failure / ambiguous state:

- UI must support:
  - generic login failure
  - ambiguous account recognition
  - unavailable / blocked state

Back / cancel / switch-account:

- user must be able to return from credential step to recognition step
- switching account path must clear transient recognition state

Desktop / mobile:

- semantic behavior must match across form factors
- only presentation may differ in later UI slices

This slice does not define templates, CSS, JavaScript, or endpoint payloads.

### 3.7 Security boundaries to preserve

Frozen non-regression boundaries:

- AUTH-ORDER Frozen contracts remain mandatory
- current-site isolation remains mandatory
- cross-site non-disclosure remains mandatory
- vendor trusted-target isolation remains mandatory
- admin / member role boundaries remain mandatory
- existing write-path rejection-before-write behavior remains mandatory
- rejected path must remain no-write
- future vendor authorization, ownership, vendor-site assignment, sheet-vendor binding, and trusted-target derivation must not use `vendor_name` as authority
- future vendor authorization, ownership, vendor-site assignment, sheet-vendor binding, and trusted-target derivation must converge on canonical `vendor_id` relationships
- credentials, password hashes, and secrets must not appear in:
  - responses
  - logs
  - URLs
- unified login design must not assume hot maintenance data merge capability
- current `vendor_name` scoping must not be changed inside AUTH-UX-001A; migration, backfill, compatibility, rollback, and no-write verification remain separate follow-up work

## 4. Roadmap dependency freeze

Ordered dependency sequence:

1. AUTH-UX-001A — Unified Login Design Freeze
2. AUTH-ID-001 — Global Account Identity Registry
3. VENDOR-ID-001 — Vendor Organization and Owner/Member Design
4. VENDOR-AUTH-001 — Vendor Account Activation Schema
5. VENDOR-AUTH-002 — Invitation and Activation API
6. AUTH-SEC-001 — Login Failure Lockout
7. AUTH-READ-001 — Explicit Account Recognition API
8. AUTH-UX-001B — Two-stage Unified Login UI
9. AUTH-ROUTE-001 — Post-login Site/Sheet Routing

Frozen dependency rules:

- this slice completes item 1 only
- no later item is implemented here
- schema changes, migrations, and credential migration each require independent slices

## 5. Unresolved decisions

These decisions are intentionally left open for later slices because AUTH-UX-001A freezes security semantics and product boundaries, not final schema, API, or UI delivery details.

| Deferred decision | Owner slice | Why deferral does not block 001A | Frozen invariant |
|---|---|---|---|
| Unified identifier format | `AUTH-ID-001` | 001A only needs one unified entry concept plus non-disclosing recognition/authentication boundaries; it does not need final identifier syntax. | The identifier must not directly become authorization authority; it must not create an existence oracle; it must not trigger cross-backend password fallback. |
| Internal/vendor username collision | `AUTH-ID-001` with downstream UI consumer `AUTH-UX-001B` | 001A already freezes that actor type may not be guessed from collision; later identity work can define the canonical collision model. | Collision must not guess actor type; unresolved collision must not establish an authority-bearing session. |
| Explicit recognition API shape | `AUTH-READ-001` | 001A freezes recognition as a stage and a security boundary without needing endpoint shape, payload format, or transport contract. | Recognition must remain read-only and non-authoritative; it must not create session or write state; it must not disclose account type, site, vendor, or trusted target. |
| Vendor multi-target routing UX | `AUTH-ROUTE-001` with downstream presentation consumer `AUTH-UX-001B` | 001A already freezes that multiple targets cannot be guessed and that target choice is routing, not authentication. | Multiple targets must not be auto-selected; remembered or preview target must be re-canonicalized; no write authority may exist before selection is complete and re-authorized. |
| Unified post-auth landing behavior | `AUTH-ROUTE-001` | 001A freezes the routing inputs and authority boundaries without deciding final landing layout or navigation hierarchy. | Routing may use only canonical actor identity and canonical site/vendor relationships; browser-supplied role, vendor name, site, or sheet must not determine routing authority. |
| Vendor read-preview and write-target scope separation | `VENDOR-ID-001` | 001A can freeze the distinction between preview and authority without deciding final vendor organization/read-model structure. | Preview/read result is never write authority; write target must be independently re-canonicalized and authorized; final business ownership authority must converge on `vendor_id`. |

Additional 001A freeze note for all deferred vendor-identity work:

- future target-state uses `vendor_id` as the canonical vendor organization authorization identity
- current-state `vendor_account_id` remains the authenticated login principal until later identity and migration slices land
- current `vendor_name` scoping may be described as current-state evidence, but may not be carried forward as future authorization authority

## 6. Out of scope

Explicitly out of scope for AUTH-UX-001A:

- `app.py` changes
- template or static asset changes
- schema or migration work
- account merge or data movement
- password rehash or credential rotation
- new APIs
- route changes
- session key changes
- login lockout implementation
- email / phone / SSO
- invitation flow
- site / sheet permission model changes
- DEV / Production operations

## 7. Review checklist

Docs review for this slice should verify:

- current-state claims are grounded in existing code
- target design does not silently assume data migration already exists
- unified login does not break AUTH-ORDER frozen guarantees
- session authority rules remain explicit and mutually exclusive
- vendor login principal (`vendor_account_id`) and future vendor organization authorization identity (`vendor_id`) are explicitly distinguished
- future vendor authorization, ownership, vendor-site assignment, sheet-vendor binding, and trusted-target derivation are frozen toward `vendor_id`, not `vendor_name`
- unresolved decisions each have an owner slice and an invariant that later slices may not violate
- roadmap boundaries remain intact
