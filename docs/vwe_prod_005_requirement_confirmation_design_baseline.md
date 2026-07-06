## Purpose

This document defines the docs-only baseline for Vendor Work Entry requirement confirmation.

The goal of `VWE-PROD-005A` is to establish the minimum product semantics for site-side confirmation of `pre_entry_requirement` without changing schema, API, UI, or runtime behavior in this slice.

## Current Baseline

The current Vendor Work Entry baseline already supports `pre_entry_requirement` as an entry-level field on `vendor_work_entries`.

Current frozen behavior:

- `pre_entry_requirement` belongs to a single Vendor Work Entry.
- A vendor can create and update `pre_entry_requirement`.
- Validation is frozen:
  - input is trimmed
  - missing input becomes `""`
  - whitespace-only input becomes `""`
  - max length is 500 characters
- There is no confirmation state yet.
- There is no site-side confirmation UI, API, or permission workflow yet.

## Confirmation Semantics

Requirement confirmation should be modeled per `Vendor Work Entry`.

The confirmation unit is:

- one entry

The confirmation unit is not:

- the whole vendor
- a `work_content` grouping
- a same-day vendor batch

This means that the same vendor can have multiple entries on the same `business_date`, and each entry should be confirmed independently.

Example semantics:

- Vendor A, Entry 1, Requirement A -> confirmed independently
- Vendor A, Entry 2, Requirement B -> confirmed independently
- Vendor A, Entry 3, no requirement or a different requirement -> handled independently

## Proposed Minimal Fields

The minimal future confirmation model should introduce the following fields:

- `requirement_status`
- `requirement_confirmed_by`
- `requirement_confirmed_at`

Suggested minimal status values:

- `pending`
- `confirmed`

These are intentionally excluded from the first confirmation baseline:

- `rejected`
- `returned`
- confirmation comments

The purpose of the first phase is only to support a clear confirmed/not-yet-confirmed boundary.

## Role Boundary

The role boundary should remain minimal and explicit.

- Vendor can fill in and update `pre_entry_requirement`.
- Vendor should not confirm its own requirement.
- Site member or a higher-trust site-side role should perform confirmation.
- This phase should not redesign the broader permission model.

The confirmation feature should plug into the existing role model as narrowly as possible instead of reopening vendor/admin/site authorization globally.

## UI Direction

The first confirmation phase should not place confirmation controls inside the vendor edit form.

Recommended direction:

- Vendor page continues to focus on vendor-authored entry data.
- A future site/admin-facing view may expose confirmation controls.
- Confirmation should be performed per entry, not through vendor-level batch actions.

This keeps the vendor workflow and the site-side verification workflow clearly separated.

## Out-of-Scope

The following items are explicitly out of scope for `VWE-PROD-005A`:

- schema / migration
- API implementation
- UI implementation
- audit log
- notification
- checklist workflow
- rejected flow
- returned flow
- permission redesign
- bulk confirmation
- history redesign

## Proposed Next Slices

Recommended next slices:

- `VWE-PROD-005B` — Schema Baseline
- `VWE-PROD-005C` — Site/Admin Confirmation UI/API Wiring
- `VWE-PROD-005D` — Confirmation Validation / Permission Guardrail

Suggested sequence:

1. Add the minimal schema baseline for confirmation state.
2. Wire a narrow site/admin confirmation path without broad workflow expansion.
3. Freeze validation, authorization, and regression guardrails.

