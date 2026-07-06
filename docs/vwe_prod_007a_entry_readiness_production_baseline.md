# VWE-PROD-007A — Entry Readiness Production Baseline

## 1. Purpose

This document defines the first production baseline for the Entry Readiness product line.

Its purpose is to consolidate the completed VWE-PROD-004 through VWE-PROD-006 capability set into a stable reference baseline before future extension work begins.

This slice is docs-only and does not modify application code, schema, API behavior, or runtime product behavior.

## 2. Completed Capability Inventory

The following capabilities are completed in the current baseline:

- Vendor can write entry-level `pre_entry_requirement`.
- Vendor create and update paths support requirement write-through.
- Site/Crew can confirm requirement per entry.
- Confirmation is defined at the single Vendor Work Entry level.
- Crew read payload includes `readiness_state` and `readiness_reason`.
- Crew UI displays a readiness indicator per entry.
- Regression guardrails for requirement, confirmation, readiness read contract, and readiness UI are frozen.

In practical product terms, the current baseline already supports:

- requirement authoring by vendor
- requirement confirmation by site-side actor
- readiness evaluation on the read side
- readiness display on the crew-side UI

## 3. Actor Boundary

Current actor responsibilities are:

- Vendor
  - fill `pre_entry_requirement`
  - update `pre_entry_requirement`
  - cannot confirm requirement

- Site/Crew
  - view requirement
  - confirm requirement
  - view readiness state and readiness reason

- Admin
  - retains site-side management capability
  - participates in site-side operational control boundary

Vendor is intentionally not allowed to confirm its own requirement.

## 4. API Boundary

The current API boundary is:

- Vendor write path
  - `/api/vendor-work-entry`
  - responsible for vendor-facing create/update of Vendor Work Entry data, including requirement text

- Crew confirmation path
  - `/api/crew-work-entry-requirement-confirm`
  - responsible only for requirement confirmation

- Crew read path
  - `/api/crew-forms`
  - responsible for crew-side read surface, including readiness projection

These three responsibilities must remain separate and should not be mixed into a shared endpoint contract without an explicit redesign slice.

## 5. Data / Contract Boundary

Current data and contract surface includes:

- persisted requirement field
  - `pre_entry_requirement`

- persisted confirmation fields
  - `requirement_status`
  - `requirement_confirmed_by`
  - `requirement_confirmed_at`

- crew-side read projection fields
  - `readiness_state`
  - `readiness_reason`

Boundary note:

- requirement fields are persisted entry data
- readiness fields are currently read-contract projection fields
- readiness fields are not a separate schema baseline at this stage

## 6. Readiness Rules

The frozen readiness rule set is:

- pending requirement
  - `not_ready / requirement_pending`

- confirmed requirement
  - `ready / requirement_confirmed`

- no requirement
  - `ready / no_requirement`

This rule is evaluated per entry.

It is not evaluated:

- per vendor
- per work-content group
- per same-day vendor aggregate

## 7. Freeze Criteria

This production baseline is considered complete because the following slices are already in place:

- schema baseline completed
- vendor write contract completed
- crew confirmation API completed
- crew readiness read contract completed
- crew readiness indicator UI completed
- regression guardrail completed

Together, these provide a coherent first production baseline for the Entry Readiness line.

## 8. Explicit Out-of-Scope

The following remain outside this production baseline:

- rejected / returned flow
- override
- notification
- audit log
- checklist
- bulk confirmation
- scheduling engine
- permission model rewrite
- broader vendor page redesign

These are intentionally deferred so the current baseline stays minimal, explicit, and stable.

## 9. Future Extension Candidates

Potential future expansion slices include:

- override design
- rejected / returned flow
- audit log
- notification
- checklist integration
- scheduling gate
- role-based refinement

Each of these should be introduced as an isolated product slice rather than folded into the current baseline implicitly.
