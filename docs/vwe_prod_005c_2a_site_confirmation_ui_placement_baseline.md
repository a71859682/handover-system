## Purpose

This document defines the docs-only baseline for Site/Crew-side requirement confirmation UI placement.

The purpose of `VWE-PROD-005C-2A` is to decide where confirmation should appear in the Site/Crew experience before any template, API, or workflow implementation is added.

This slice does not modify code.

## Current Baseline

The current baseline is:

- `VWE-PROD-004A` established the pre-entry requirement design baseline.
- `VWE-PROD-004B` established the schema baseline for requirement text.
- `VWE-PROD-004C-1` wired vendor draft create/update support for `pre_entry_requirement`.
- `VWE-PROD-004C-2` froze the validation contract and regression guardrails.
- `VWE-PROD-005A` established requirement confirmation semantics.
- `VWE-PROD-005B` established the confirmation schema baseline.
- `VWE-PROD-005C-1` established confirmation API and permission wiring.

At this point:

- vendor can fill in `pre_entry_requirement`
- site/admin can confirm a requirement through API wiring
- there is still no formal Site/Crew confirmation UI

## UI Placement Decision

The confirmation UI should not be placed on the vendor page.

The confirmation UI should also avoid introducing a large new page in the first UI slice.

Recommended direction:

- attach confirmation UI to an existing Site/Crew read surface
- prefer the existing crew/site-side entry list or vendor-related crew read surface
- keep confirmation close to where site-side users already review vendor planned entry data

This means the UI should be layered onto the existing Site/Crew-facing read context rather than building a separate workflow hub.

## Entry-level Display

The display unit must remain one `Vendor Work Entry`.

Even when the same vendor has multiple entries on the same day, the Site/Crew UI should show them separately.

Each displayed entry should include:

- `vendor_name`
- `work_content`
- `planned_at`
- `pre_entry_requirement`
- `requirement_status`
- `requirement_confirmed_by` and `requirement_confirmed_at` when confirmed

This preserves the existing entry-level product model and avoids drifting into vendor-level batch semantics.

## Confirm Action Placement

The confirm action should be placed next to each entry, not at the vendor group level.

Recommended behavior:

- pending entry: show a `Confirm` action
- confirmed entry: show confirmed status and confirmation metadata
- confirmed entry: do not show a repeated primary action in the first UI slice

This keeps the interaction model simple:

- one entry
- one visible confirmation state
- one action when confirmation is still pending

## Actor Boundary

The actor boundary must remain explicit.

- vendor page must not show confirmation actions
- Site/Crew/Admin users may see confirmation UI
- the first UI slice must reuse the existing permission model

This means UI visibility should follow the already established site-side permission boundary instead of introducing a new role system.

## Out-of-Scope

The following items are explicitly out of scope for `VWE-PROD-005C-2A`:

- template implementation
- API change
- schema change
- permission rewrite
- audit log
- rejected / returned flow
- notification
- checklist
- bulk confirmation
- broader page redesign

## Proposed Next Slice

Recommended next slice:

- `VWE-PROD-005C-2B` — Site Confirmation UI Wiring

That slice should implement:

- entry-level pending / confirmed display
- per-entry confirm action
- site-side visibility only
- minimal regression guardrails

