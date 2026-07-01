# P-2C Login Flow Planning

## 1. Current Login Flow

### Internal login sequence

The active runtime login flow is internal-user oriented.

Current sequence:

1. Request enters `POST /login`
2. Username/password are read from the form
3. User lookup is performed against `users`
4. Password hash is verified
5. `session.clear()` runs before a new session is written
6. Internal session keys are populated
7. Current site is normalized through current-site resolution
8. User is redirected either to:
   - `/sheet`
   - `/site-selector`
   - `/login` for zero-site denial

### Session lifecycle

Current internal session state includes:

- `user_id`
- `username`
- `display_name`
- `role`
- `current_site_id`
- `current_site_name`
- `site_selection_required`
- `sheet_id`

This session contract is already active and stable in production.

### Current site resolution

Current site resolution is part of login success handling for internal users.

- Global admin resolves globally but may carry a current site in session
- Single-site internal users auto-resolve
- Multi-site internal users may require selector flow
- Zero-site users are denied an authenticated session

This means current-site normalization is not an optional post-login concern. It is already embedded in internal login lifecycle.

### Logout flow

- Active route: `POST /logout`
- Behavior: `session.clear()`
- Effect:
  - clears internal auth state
  - clears current-site state
  - clears current sheet selection state

### `login_required` / `admin_required` contract

#### `login_required`

- checks for authenticated internal session through `session["user_id"]`
- redirects to `/login` when missing

#### `admin_required`

- requires authenticated session first
- then checks `session["role"] == "admin"`
- redirects non-admin authenticated users away from admin-only views

These decorators are currently internal-session specific and do not account for vendor identity.

## 2. Future Identity Architecture

P-2C planning assumes three long-lived identity types:

### Global Admin

- Authentication entry:
  - internal login
- Session namespace:
  - internal session
- Authorization model:
  - global admin authorization
- Logout behavior:
  - standard internal logout clears full internal session

### Internal User

- Authentication entry:
  - internal login
- Session namespace:
  - internal session
- Authorization model:
  - `users` + `user_site_permissions` + current-site resolution
- Logout behavior:
  - standard internal logout clears full internal session

### Vendor User

- Authentication entry:
  - future vendor login surface
- Session namespace:
  - vendor session, separate from internal session
- Authorization model:
  - vendor account identity + vendor authorization boundary + sheet/site scoped access
- Logout behavior:
  - vendor logout should clear vendor-specific session state without assuming internal session fields

## 3. Login Route Options

### Option A

- Shared `/login`
- Identity type inferred automatically

#### Advantages

- single visible login entrypoint
- minimal route growth

#### Disadvantages

- mixes internal and vendor auth logic in one route
- complicates session branching
- increases ambiguity in post-login redirect rules
- increases regression risk to stable internal login

#### Runtime risk

- high

#### Migration cost

- medium to high

#### User experience

- simple on the surface
- potentially confusing when errors or routing diverge by identity

#### Maintenance cost

- high

### Option B

- `/login` for internal identities
- `/vendor/login` for vendor identities

#### Advantages

- clean identity separation
- low regression risk for current internal flow
- simpler session reasoning
- simpler decorator evolution

#### Disadvantages

- more than one login entrypoint
- future UX must clearly expose vendor login

#### Runtime risk

- low to medium

#### Migration cost

- lower than shared-route design

#### User experience

- explicit and understandable
- slightly more navigational surface

#### Maintenance cost

- lower long-term

### Option C

- Unified identity gateway
- gateway resolves identity type
- downstream identity-specific flow continues separately

#### Advantages

- allows centralized identity discovery
- can support future expansion beyond two identity types
- can preserve separation after the gateway stage

#### Disadvantages

- introduces extra architectural layer
- more moving parts than a simple split-route model
- overdesigned for near-term needs if introduced too early

#### Runtime risk

- medium

#### Migration cost

- medium

#### User experience

- can be polished later
- likely more complex than needed initially

#### Maintenance cost

- medium

## 4. Session Namespace Planning

This section is planning-only and does not change runtime.

### Internal session

Recommended to preserve current internal session namespace as-is:

- `user_id`
- `username`
- `display_name`
- `role`
- `current_site_id`
- `current_site_name`
- `site_selection_required`
- `sheet_id`
- `identity_type = internal`

### Vendor session

Recommended future vendor session fields:

- `identity_type = vendor`
- `vendor_account_id`
- `vendor_username`
- `vendor_name`
- optional future fields:
  - `vendor_site_id`
  - `vendor_sheet_id`
  - `vendor_scope_version`

### Current site

- internal current-site contract should remain internal-user specific unless a future stage explicitly extends it
- vendor identity should not automatically inherit internal `current_site_id`

### Vendor context

- vendor context should be explicit, not inferred from internal user keys
- vendor session should not reuse `user_id` or `role`

### Logout contract

Recommended long-term direction:

- internal logout clears internal namespace
- vendor logout clears vendor namespace
- if unified logout UI ever exists, it must clear the active identity namespace safely

## 5. Authorization Pipeline

Recommended future conceptual pipeline:

Authentication  
→ Identity  
→ Site Resolution  
→ Authorization  
→ Read Scope  
→ Write Scope

### Authentication

- verify credentials against the correct identity store
- internal users authenticate via `users`
- vendor users authenticate via `vendor_accounts`

### Identity

- determine whether the session is:
  - global admin
  - internal user
  - vendor user
- assign correct session namespace

### Site Resolution

- internal users resolve current site through current-site lifecycle
- vendor users may use explicit vendor scope without adopting the same current-site model immediately

### Authorization

- determine whether the authenticated identity may access the requested functional surface
- identity must not be treated as equivalent to authorization

### Read Scope

- constrain data visibility based on identity type and authorized scope
- internal users already use site read isolation
- vendor read scope requires future explicit definition

### Write Scope

- constrain mutations based on identity type and authorized scope
- current high-risk write isolation remains the reference model for internal auth
- vendor write scope must layer on top of existing isolation constraints, not bypass them

## 6. Risks

### Login regression risk

- current internal login is stable and production-proven
- changing it directly is high-risk

### Current-site coupling

- current-site lifecycle is already tightly coupled to internal login
- extending it blindly to vendor identity would create unnecessary coupling

### Session compatibility

- current decorators and downstream flows assume internal session keys
- mixing namespaces too early risks silent authorization bugs

### Vendor auth introduction risk

- vendor data tables already exist
- vendor write APIs already exist
- vendor auth does not yet exist
- introducing vendor auth without clear identity separation risks breaking both internal and vendor flows

### What must not be implemented in P-2C

- no login route change
- no new runtime session schema
- no decorator changes
- no DB schema changes
- no production auth changes
- no vendor auth implementation

## 7. Recommendation

Recommended long-term direction: **Option B**, separate internal and vendor login routes with separate session namespaces.

### Why this is recommended

- protects current stable internal login flow
- keeps session contracts explicit
- reduces migration risk
- allows vendor identity to evolve independently
- aligns better with future authorization layering

### Longer-term note

If the system later grows beyond internal + vendor identities, a gateway-style architecture may become useful. However, P-2C should not start there. The simpler and safer path is explicit split login surfaces with explicit session namespaces.

P-2C remains planning-only. No runtime behavior should change in this stage.
