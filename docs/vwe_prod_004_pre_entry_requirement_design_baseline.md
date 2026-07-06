# VWE-PROD-004A — Pre-entry Requirement Design Baseline

## 1. Purpose

This document defines the design baseline for `VWE-PROD-004A`.

The goal of this slice is to establish the minimum product direction for a future pre-entry requirement capability in Vendor Work Entry.

This slice does not implement:

- schema or migration changes
- UI or template changes
- API contract changes
- confirmation workflow
- audit logging

## 2. Current Baseline

The current `vendor_work_entries` baseline already supports the following:

- the same vendor can have multiple entries on the same `business_date`
- `entry_order` provides same-day ordering
- the today entries list can render multiple entries
- create mode can add additional entries for the same day
- update mode can edit a single selected entry
- selected-entry mode, create mode, and submit-result landing are already stabilized

In practical terms, the current product already supports a multi-entry planned-entry baseline for the same vendor on the same day.

More concretely, each planned entry is an independent Vendor Work Entry row with its own work content, planned time, headcount, and future requirement context. The vendor page then groups and presents these rows primarily by vendor, while still allowing multiple entries for the same vendor and business date.

## 3. Planned Entry Semantics

The identity unit of planned-entry behavior is the entry itself, not `work_content`.

The current baseline already supports multiple planned entries for the same vendor on the same business date. Each entry can describe different work content, a different planned arrival time, and different headcount details. Because of that, the current product does not need a grouping model centered on `work_content`.

What exists today:

- multiple entry rows for the same vendor and business date
- explicit ordering through `entry_order`
- selected-entry viewing and update flow
- create-mode flow for adding another planned entry

What does not yet exist:

- task linkage for each entry
- requirement grouping across multiple entries
- a formal concept of grouped work items beyond the entry itself

Short-term direction:

- do not add task linkage in this slice
- do not add requirement grouping in this slice
- keep the current model centered on entry-level planning data

## 4. Pre-entry Requirement Minimal Design

Recommended future minimal field:

- `pre_entry_requirement TEXT`

Recommended design principles:

- attach the field to `vendor_work_entries`
- treat the requirement as entry-level data
- let the vendor provide the requirement text
- start with plain text only
- do not model checklist items yet
- do not create a separate multi-row requirement table yet
- do not add status flow in the first implementation step

Rationale:

- the requirement is most naturally tied to a specific planned entry
- the requirement should remain entry-level, not vendor-level
- even when the same vendor has multiple planned entries, each entry may need a different pre-entry requirement
- this keeps the first implementation aligned with the existing selected-entry and create-mode flow
- a single text field keeps the initial scope small and avoids prematurely locking in a more complex requirement structure

## 5. Future Confirmation Phase

This section records future design direction only. It is not part of `VWE-PROD-004A` implementation.

Possible future fields:

- `requirement_status`
- `requirement_confirmed_by`
- `requirement_confirmed_at`

Suggested initial statuses:

- `pending`
- `confirmed`

Statuses to consider only in a later phase:

- `rejected`
- `needs_update`

Design notes:

- a vendor should not confirm its own requirement
- confirmation should happen per entry, not once for the whole vendor
- confirmation should be handled by a site-side role
- confirmation should remain outside this slice
- audit logging is a future phase and not included here

## 6. Explicit Out-of-Scope

The following items are explicitly out of scope for `VWE-PROD-004A`:

- schema changes
- migrations
- API contract changes
- template or UI changes
- confirmation implementation
- audit log implementation
- permission model rewrite
- delete / reorder / bulk edit
- multi-entry redesign
- broader vendor page redesign

## 7. Proposed Next Slice Options

Possible next slices after this design baseline:

- schema-only baseline: add `pre_entry_requirement`
- page-only placeholder: show a future requirement area without persistence
- implementation slice: let vendors fill requirement text
- confirmation design slice: define site member confirmation separately

Recommended sequencing:

1. freeze this design baseline
2. choose whether to do schema-only groundwork or a page-only placeholder
3. implement vendor-entered requirement text before confirmation
4. defer site-side confirmation to a separate design and implementation phase

## 8. Freeze Criteria

`VWE-PROD-004A` can be considered complete when:

- the current baseline is clearly documented
- the minimal field direction is clearly documented
- the future confirmation boundary is clearly documented
- out-of-scope items are clearly documented
- no application code has been modified
