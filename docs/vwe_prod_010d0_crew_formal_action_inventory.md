# VWE-PROD-010D-0 - Crew Formal Action Inventory

## 1. Purpose

This document records a docs-only inventory of current crew/site-side write actions and identifies which actions should count as true formal actions for future Scheduling Hard Block enforcement.

Its purpose is to separate ordinary write activity from crew-side formal actions that actually require `Entry Ready`.

This slice does not modify application code, static assets, templates, tests, schema, API behavior, or write behavior.

## 2. Current Crew Write Inventory

The current system contains several crew/site-side or site-admin-side write surfaces.

They do not all belong to the same product category.

### Metadata

- `/api/vendor-contact`

Inventory classification:

- metadata write
- vendor contact maintenance
- not an Entry Ready decision boundary

Why it matters:

- this write path supports vendor-contact data hygiene
- it does not represent entry execution approval, scheduling approval, or readiness enforcement

### Progress

- `/api/progress`
- `/api/unit-extra`

Inventory classification:

- progress / operational worksheet write
- unit/task execution tracking
- not Vendor Work Entry formal-action approval

Why it matters:

- these writes track work progress or extra unit state
- they may happen after work is already operationally underway
- they do not define whether a single Vendor Work Entry is ready for scheduling approval

### Requirement Confirmation

- `/api/crew-work-entry-requirement-confirm`

Inventory classification:

- requirement confirmation write
- readiness-enabling write
- not a hard-block target

Why it matters:

- this is the exact write used to resolve pending readiness
- if hard block were applied here, blocked entries would become impossible to clear through the normal confirmation flow

### Admin

- `/api/reset-sheet`
- `/admin/table` `POST`
- `/admin/users` `POST`

Inventory classification:

- admin content-management or admin control writes
- broader system-management boundary
- not entry-level Vendor Work Entry formal action

Why it matters:

- these paths manage broader site data, sheet state, or user/admin behavior
- they are not single-entry scheduling approval or entry-ready enforcement boundaries

### Future Scheduling

Current state:

- there is no existing dedicated crew/site-side scheduling-confirmation write path in v1

Inventory classification:

- future formal-action domain
- expected hard-block target domain

Why it matters:

- hard block must eventually attach to an actual crew-side formal action that operationally depends on `Entry Ready`
- that action is not yet implemented as a distinct write path in v1

## 3. Candidate Formal Actions

Not every crew/site-side write should be treated as a formal action.

The real candidate formal actions are only those that do all of the following:

- act on a single `Vendor Work Entry`
- represent a crew/site-side formal operational decision
- require `Entry Ready`
- should reject blocked entries deterministically

Based on that standard:

### Not formal actions

- metadata writes
- progress writes
- requirement confirmation
- broad admin content-management writes

These may be important writes, but they are not the formal operational boundary that Hard Block is supposed to protect.

### True formal-action candidate

The true candidate is:

- a future dedicated crew/site-side entry-level scheduling or entry-approval write action

This is the first write domain that naturally requires:

- `readiness_state`
- `scheduling_gate_state`
- a deterministic allow/block decision

## 4. Recommendation

The recommended first Hard Block target is:

- a new dedicated crew-side formal-action write path for single-entry scheduling completion or entry approval

This recommendation is the cleanest product direction because:

- it keeps vendor authoring outside hard-block enforcement
- it keeps requirement confirmation outside hard-block enforcement
- it keeps enforcement attached to a true operational decision
- it preserves the entry-level identity model already established in VWE v1
- it avoids coupling hard block to unrelated worksheet, metadata, or admin writes

In short:

- first hard block should target a future formal-action write path
- first hard block should not be retrofitted into an existing non-formal endpoint

## 5. Why Existing Endpoints Should NOT Be Used

### Vendor submit

Endpoint:

- `/api/vendor-work-entry`

Why it should not be used:

- vendor submit is authoring, not formal crew-side approval
- vendors must still be able to create and update entries
- vendors must still be able to fill `pre_entry_requirement`
- blocking vendor submit would prevent the workflow from reaching a resolvable ready state

### Requirement confirmation

Endpoint:

- `/api/crew-work-entry-requirement-confirm`

Why it should not be used:

- this is the write path that resolves pending readiness
- blocking it would trap the system in `warning`
- confirmation is not the formal action that requires Entry Ready; it is the action that creates Entry Ready

### Progress

Endpoints:

- `/api/progress`
- `/api/unit-extra`

Why they should not be used:

- these are broader worksheet/progress writes
- they are not single-entry scheduling decisions
- they belong to downstream operational tracking, not the entry-ready approval boundary

### Admin table

Endpoint:

- `/admin/table` `POST`

Why it should not be used:

- it is a broad admin content-management surface
- it is not scoped to one `Vendor Work Entry`
- it is not a true crew-side formal action for entry-level scheduling or entry approval
- using it would incorrectly blend hard-block semantics into unrelated admin editing

## 6. Future API Shape

The future API direction should be:

- one dedicated crew-side formal-action write path
- one request acts on one `Vendor Work Entry`
- the action explicitly represents a formal decision requiring `Entry Ready`
- the action returns deterministic success or deterministic hard-block error

The future shape should likely include:

- `entry_id`
- `sheet_id`
- `action`

The future shape should not:

- reuse vendor submit contract
- reuse requirement confirmation contract
- piggyback on progress writes
- overload broad admin content-management writes

This document describes product direction only.

It does not implement or lock the final runtime API.

## 7. Out-of-Scope

The following are out of scope for this inventory slice:

- runtime API implementation
- hard-block write implementation
- schema / migration
- UI implementation
- override
- notification
- audit log
- scheduling engine implementation
- permission redesign
- workflow redesign

## 8. Proposed Next Slice

The next slice should be:

- `VWE-PROD-010D - Hard Block API Guardrail`

Its purpose should be:

- choose the actual first hard-block write boundary
- lock deterministic allow/block behavior
- preserve the rule that vendor submit, requirement confirmation, progress, and admin table are not Hard Block targets
