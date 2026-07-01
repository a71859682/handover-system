# P-2A Permission Contract Freeze

## 1. Stable Baseline

- Baseline commit: `ef934eb`
- Release status: `CLOSED`

This planning note freezes the current permission and auth contracts as the starting point for the next development cycle. P-2A is planning only and does not change runtime behavior.

## 2. Current Auth Contract

### Internal user session keys

Current internal user session state uses these keys:

- `user_id`
- `username`
- `display_name`
- `role`
- `current_site_id`
- `current_site_name`
- `site_selection_required`
- `sheet_id`

### `login_required` contract

- `login_required` only checks whether `session["user_id"]` exists.
- If the key is missing, the request redirects to `/login`.
- It does not revalidate the current user against the database on every request.

### `admin_required` contract

- `admin_required` requires an authenticated session.
- It then checks `session["role"] == "admin"`.
- If the session is authenticated but not admin, the request flashes an error and redirects to `/sheet`.

### Logout contract

- Logout is handled by `POST /logout`.
- The route calls `session.clear()`.
- This clears auth state, current site state, and any sheet selection state together.

### Current site / session contract

- Login success immediately runs current-site normalization for internal users.
- Current site is stored in session via:
  - `current_site_id`
  - `current_site_name`
  - `site_selection_required`
- Admin users may fall back to the default site for session resolution.
- Non-admin users must resolve to an accessible site or be forced into site selection.
- Zero-site users are denied an authenticated session after login verification succeeds.

## 3. Role Boundary

- `users.role` is the global role contract.
- `user_site_permissions.role` is the site-scoped role contract.
- These two fields must not be mixed during P-2A.
- Global admin remains defined by `users.role == "admin"`.

### Admin site access rule

- Admin is globally authorized across active sites.
- Admin site access does not depend on rows in `user_site_permissions`.
- Admin may still carry a current site in session for site-aware read/write behavior.

## 4. Site Permission Contract

### Site access decision source

- Non-admin site access is derived from `user_site_permissions`.
- A site must also remain active in `sites`.
- Admin access is derived from `users.role == "admin"` plus active site existence.

### Read isolation contract

- Non-admin reads are constrained by:
  - a valid `current_site_id`
  - active site membership
  - `user_site_permissions`
  - target sheet belonging to the current site
- Admin reads remain globally allowed.

### Write isolation contract

- High-risk non-admin writes are already enforced against current site and permission checks.
- Admin site-scoped content writes use current-site-aware authorization for the implemented admin actions.
- Session current site is part of authorization context, but it is not the standalone source of permission.

### `sheets.site_id` contract

- `sheets.site_id` is the canonical site binding for sheet-scoped content.
- Read isolation depends on it.
- Write isolation depends on it.
- Admin current-site-aware content writes depend on it.
- P-2A does not redefine or migrate this contract.

## 5. Vendor Identity Gap

- `vendor_accounts` already exists in schema.
- Vendor data APIs already exist:
  - vendor contacts
  - vendor work entries
- Vendor-facing identity and login/session flow are not yet wired into runtime auth.
- P-2A does not implement vendor authentication.

## 6. P-2A Frozen Decisions

- Do not change the login flow.
- Do not change session schema.
- Do not change database schema.
- Do not change `app.py` runtime behavior.
- Do not change production deploy behavior or production runtime.
- Do not merge global role and site-scoped role semantics in this stage.

## 7. Next Candidates

### P-2B Vendor Identity Planning

Candidate scope:

- vendor account contract review
- vendor identity model
- vendor login/session planning
- vendor authorization boundary planning

### P-2C Login Flow Planning

Candidate scope:

- internal vs vendor login surface planning
- session namespace planning
- logout contract review
- auth boundary and route entry planning
