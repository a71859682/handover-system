# VWE-PROD-008A — Scheduling Gate Design Baseline

## 1. Purpose

This document defines the docs-only design baseline for the Scheduling Gate product line.

The goal is to clarify whether Entry Readiness should affect actual entry execution or scheduling decisions, while keeping this slice strictly non-implementation.

This slice does not modify application code, schema, API behavior, UI behavior, or runtime product behavior.

## 2. Current Baseline

Current Entry Readiness baseline already supports:

- Vendor can write `pre_entry_requirement`
- Site/Crew can confirm requirement per entry
- The system can derive `readiness_state` and `readiness_reason`
- Crew UI already displays a readiness indicator

However, current readiness does not yet block, warn, or otherwise alter actual entry execution or scheduling behavior.

At this stage, readiness is visible but not yet operationally enforced.

## 3. Scheduling Gate Semantics

The scheduling gate unit is a single Vendor Work Entry.

The gate is not evaluated:

- at the whole-vendor level
- by `work_content` grouping
- by same-day vendor aggregate state

If the same vendor has multiple entries on the same business date, each entry must be evaluated independently.

This keeps the scheduling gate aligned with the existing product identity:

- entry identity = entry
- readiness identity = entry
- future scheduling signal = entry

## 4. Proposed Minimal Rule

The first minimal scheduling rule is:

- `readiness_state = ready`
  - allow entry / scheduling

- `readiness_state = not_ready`
  - mark as not recommended for entry / scheduling

Version one should be a warning gate, not a hard block.

This means the product direction is:

- readiness can influence operational awareness
- readiness does not yet hard-stop workflow execution

## 5. UI Direction

Future UI direction should be:

- `not_ready`
  - display a clear warning

- `ready`
  - display that the entry is ready for entry

- vendor page
  - do not block submit directly on the vendor page in this phase

- crew/site-side surface
  - prioritize scheduling gate visibility on crew/site-side read surfaces first

This slice does not implement UI.

It only establishes the intended display direction and warning-based semantics.

## 6. Out-of-Scope

This slice does not include:

- schema / migration
- API implementation
- UI implementation
- hard block
- override
- rejected / returned flow
- notification
- audit log
- scheduling engine
- permission redesign

## 7. Proposed Next Slices

Potential next slices:

- `VWE-PROD-008B` — Scheduling Gate Read Contract
- `VWE-PROD-008C` — Scheduling Gate UI Warning
- `VWE-PROD-008D` — Guardrail Freeze

Suggested progression:

1. expose scheduling-gate read semantics
2. display warning on crew/site-side surfaces
3. freeze with regression guardrails before any stronger operational enforcement is considered
