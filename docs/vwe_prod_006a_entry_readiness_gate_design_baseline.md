# VWE-PROD-006A — Entry Readiness Gate Design Baseline

## 1. Purpose

This document defines the product design baseline for the Vendor Work Entry entry readiness gate.

The goal of this slice is to clarify when a single Vendor Work Entry should be considered ready or not ready for entry based on its pre-entry requirement confirmation state.

This slice is docs-only. It does not modify schema, API, UI, or runtime behavior.

## 2. Current Baseline

Current Vendor Work Entry capability already supports the following:

- Vendor can create and update `pre_entry_requirement` as an entry-level field.
- Site/Crew can confirm a requirement per entry.
- Confirmation is defined at the single Vendor Work Entry level.
- The current confirmation state does not yet affect entry readiness or any "allowed to enter" product decision.

## 3. Readiness Gate Semantics

The readiness gate unit is a single Vendor Work Entry.

The gate is not evaluated:

- at the whole-vendor level
- by `work_content` grouping
- by same-day vendor aggregate status

If the same vendor has multiple entries on the same business date, each entry must be evaluated independently for readiness.

This keeps the readiness model aligned with the current product baseline:

- planned entry identity = entry
- confirmation identity = entry
- future readiness identity = entry

## 4. Proposed Minimal Rule

The first minimal rule is:

- If an entry has `pre_entry_requirement` and `requirement_status != confirmed`, the entry is treated as `not ready`.
- If an entry has no `pre_entry_requirement`, the entry is treated as `no requirement / ready`.
- If an entry has `pre_entry_requirement` and the requirement is already confirmed, the entry is treated as `ready`.

This rule intentionally avoids broader workflow branching.

In short:

- requirement exists + not confirmed = not ready
- no requirement = ready
- confirmed requirement = ready

## 5. UI Direction

Future UI should present readiness in a simple, entry-level way:

- pending requirement: `尚未具備進場條件`
- confirmed requirement: `需求已確認`
- no requirement: `無進場前需求`

This slice does not implement UI.

It only defines the wording direction and the expected product meaning behind each state.

## 6. Override Policy

Version one does not include override behavior.

That means:

- no manual bypass
- no exception release
- no special "allow anyway" control

If override is needed in the future, it should be introduced in a separate design slice with explicit actor boundary, audit expectations, and permission rules.

No exception path is introduced in this slice.

## 7. Out-of-Scope

This slice does not include:

- schema / migration
- API implementation
- UI implementation
- notification
- audit log
- rejected / returned flow
- override workflow
- scheduling engine
- permission redesign
- bulk readiness

## 8. Proposed Next Slices

Potential next slices:

- `VWE-PROD-006B` — Readiness Gate Schema/API Baseline, if a dedicated persisted or computed contract becomes necessary
- `VWE-PROD-006C` — Readiness Indicator UI Wiring
- `VWE-PROD-006D` — Readiness Guardrail / Regression Freeze

The intended progression is:

1. freeze the readiness rule
2. expose the readiness indicator
3. lock the behavior with targeted regression coverage
