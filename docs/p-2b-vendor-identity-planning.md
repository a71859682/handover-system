# P-2B Vendor Identity Planning

## 1. Current State

### `vendor_accounts` schema

Current schema defines:

- `id`
- `username` (unique)
- `password_hash`
- `vendor_name`
- `is_active`
- `created_at`
- `updated_at`

This establishes that a vendor account model already exists in storage, but it is not yet wired into the active login/session runtime.

### `vendor_contacts` schema

Current schema defines:

- `id`
- `sheet_id`
- `vendor_name`
- `contact_name`
- `contact_title`
- `contact_phone`
- `is_primary`
- `contact_order`
- `created_at`
- `updated_at`

This is sheet-scoped vendor contact data, not an identity/session table.

### `vendor_work_entries` schema

Current schema defines:

- `id`
- `sheet_id`
- `vendor_name`
- `business_date`
- `planned_at`
- `planned_headcount`
- `actual_headcount`
- `work_content`
- `work_headcount`
- `entry_order`
- `created_at`
- `updated_at`

This is also sheet-scoped operational data, not an auth table.

### Existing vendor APIs

Current runtime already contains vendor-related APIs:

- `POST /api/vendor-contact`
- `POST /api/vendor-work-entry`

These APIs already participate in site-aware write isolation, but they currently execute under the active authenticated internal-user model. They are not yet attached to a vendor-specific identity flow.

### Existing internal login/session

Current login runtime is internal-user oriented:

- active route: `/login`
- session keys include:
  - `user_id`
  - `username`
  - `display_name`
  - `role`
  - `current_site_id`
  - `current_site_name`
  - `site_selection_required`
  - `sheet_id`
- decorators:
  - `login_required`
  - `admin_required`

There is no active vendor-specific login route, vendor session namespace, or vendor-specific auth decorator.

## 2. Identity Model

P-2B planning defines three identities:

### Global Admin

- Authentication source:
  - `users`
- Authorization scope:
  - global across active sites
- Session identity:
  - internal user session
- Site relationship:
  - may carry `current_site_id` for site-aware reads/writes, but authorization is globally admin-scoped

### Internal User

- Authentication source:
  - `users`
- Authorization scope:
  - limited by `user_site_permissions`
- Session identity:
  - internal user session
- Site relationship:
  - current site is part of normal session lifecycle

### Vendor User

- Authentication source:
  - `vendor_accounts`
- Authorization scope:
  - vendor-specific operational surface only
- Session identity:
  - vendor session, not internal user session
- Site relationship:
  - not yet defined in runtime; requires explicit planning because vendor identity currently binds most naturally to `vendor_name`, while read/write data is sheet-scoped

## 3. Vendor Login Options

### Option A

- Share `/login` with internal users
- Detect identity type automatically

#### Advantages

- one visible login entrypoint
- less initial route surface
- minimal URL expansion

#### Disadvantages

- mixes internal and vendor authentication in the same route
- increases coupling with current internal login/session code
- raises risk of session-key collision
- makes error handling and post-login routing more ambiguous

#### Migration impact

- higher
- requires branching logic inside the active login path

#### Runtime risk

- higher
- touches stable internal login flow directly

#### Maintenance cost

- higher over time
- one route must carry multiple identity models

### Option B

- Separate vendor login route
- Separate internal and vendor session contracts

#### Advantages

- clean identity boundary
- lower regression risk to internal login
- clearer session ownership
- easier to reason about decorators and authorization

#### Disadvantages

- adds one more login surface
- requires explicit vendor navigation entry design later

#### Migration impact

- lower
- existing internal login flow can remain unchanged

#### Runtime risk

- lower
- vendor auth can be introduced incrementally without destabilizing internal auth

#### Maintenance cost

- lower long-term
- each identity model remains explicit

### P-2B planning recommendation

Option B is the recommended planning direction.

The key reason is isolation of concerns: internal auth is already tightly coupled to current-site normalization, role-based decorators, and existing session keys. A separate vendor login surface reduces risk and keeps the future migration path simpler.

## 4. Session Contract

Vendor session design is planning-only at this stage.

Recommended vendor session fields:

- `identity_type`
  - expected value: `vendor`
- `vendor_account_id`
- `vendor_name`
- `vendor_username`
- `vendor_is_active`

Optional fields requiring future-stage confirmation:

- `site_id`
- `sheet_id`
- `vendor_scope_version`

### Session design notes

- Vendor session should not reuse `user_id` as its primary identity key.
- Vendor session should not reuse `role` from internal users.
- Vendor session should not silently depend on internal `current_site_id` unless later stages formally adopt that contract.

## 5. Authorization Contract

### Vendor can read

Planning assumption:

- vendor may read vendor-scoped operational data relevant to its own `vendor_name`
- vendor read access should remain constrained by sheet/site scope, not by global visibility

### Vendor can write

Planning assumption:

- vendor may write only vendor-scoped operational data allowed by future workflow design
- likely targets:
  - vendor contacts
  - vendor work entries
- any write must be constrained to allowed vendor identity and allowed sheet/site scope

### Vendor cannot access

Vendor should not access:

- `/admin/users`
- `/admin/table`
- internal member management
- global settings
- internal site permission management
- unrelated vendors' data
- global cross-site views

### Does vendor need `current_site`?

Not necessarily as a first principle.

Recommended planning direction:

- vendor authorization should first bind to `vendor_name`
- then to target sheet/site scope
- only introduce vendor `current_site` if later UX requires multi-site vendor switching

### Does vendor need sheet scope?

Yes.

Current vendor operational tables are already sheet-scoped. A future vendor auth model should therefore explicitly include sheet-aware authorization behavior, even if the final UX uses site or vendor-centric wording.

## 6. Risks

### Coupling with existing login flow

- current `/login` is tightly coupled to internal users
- mixing vendor auth into that path too early increases regression risk

### Coupling with current site

- internal current-site behavior is already established and stable
- forcing vendor auth into that same lifecycle too early may create artificial coupling

### Relationship to read/write isolation

- high-risk internal write isolation is already enforced
- vendor identity planning must not weaken that enforcement
- vendor auth should layer on top of existing sheet/site constraints, not bypass them

### What must not be implemented in P-2B

- no vendor login runtime
- no new vendor session behavior
- no route changes
- no DB schema changes
- no decorator changes
- no production auth changes

## 7. Recommendation

Recommended direction: **Option B, separate vendor login route and separate vendor session contract**.

### Reasons

- preserves stable internal login behavior
- avoids mixing internal and vendor identity keys
- keeps authorization reasoning explicit
- reduces migration risk
- supports later staged rollout:
  - vendor identity planning
  - vendor auth contract
  - vendor read/write boundary
  - vendor-facing workflow

P-2B remains planning-only. No runtime behavior should change in this stage.
