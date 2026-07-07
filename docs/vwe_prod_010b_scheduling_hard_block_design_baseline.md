# VWE-PROD-010B - Scheduling Hard Block Design Baseline

## 1. Purpose

This document defines the docs-only design baseline for Scheduling Hard Block.

Its purpose is to open the first Vendor Work Entry v2 product slice for evolving Scheduling Gate from warning-only semantics into hard-block semantics.

This slice does not modify application code, templates, tests, schema, API behavior, permission behavior, workflow behavior, or write behavior.

## 2. Current Baseline

The current baseline is:

- `Vendor Work Entry Product Baseline v1` is complete and released.
- Scheduling Gate v1 is currently warning-only.
- `readiness_state` and `readiness_reason` are already available on the crew-side read surface.
- `scheduling_gate_state` and `scheduling_gate_reason` are already available on the crew-side read surface.
- Crew-side UI already displays readiness and scheduling-gate status.
- The current product does not block vendor submit.
- The current product does not block requirement confirmation.
- The current product does not block any scheduling action yet.

This means the current baseline already provides visibility, but not enforcement.

## 3. Hard Block Semantics

The hard-block unit is one `Vendor Work Entry`.

It is not evaluated at:

- whole-vendor level
- `work_content` grouping level
- same-day vendor aggregate level

If the same vendor has multiple entries on the same business date, each entry must be evaluated independently.

This keeps the hard-block model aligned with the existing v1 identity model:

- entry identity = entry
- readiness identity = entry
- scheduling-gate identity = entry
- future hard-block identity = entry

## 4. Proposed Minimal Rule

The proposed minimal hard-block rule is:

- `scheduling_gate_state = allowed`
  - allow crew-side formal actions that require Entry Ready

- `scheduling_gate_state = warning`
  - first hard-block phase should block any crew-side formal action that requires Entry Ready

This first hard-block phase should not block:

- vendor create entry
- vendor update entry
- vendor fill `pre_entry_requirement`
- site/crew requirement confirmation

The enforcement target is a crew-side formal-action boundary that depends on Entry Ready, not vendor authoring.

## 5. Actor Boundary

### Vendor

- can still create entry
- can still update entry
- can still fill `pre_entry_requirement`
- is not blocked from requirement authoring by hard-block semantics

### Site/Crew

- can see block reason
- can see whether the entry is allowed or blocked for formal scheduling completion
- cannot complete a blocked scheduling confirmation when `scheduling_gate_state = warning`
- can still confirm requirement

### Admin

- follows the same hard-block rule in the first phase
- does not receive override power in this slice

Override is intentionally deferred to `VWE-PROD-011`.

## 6. UI Direction

The future direction is to upgrade warning-only messaging into blocking-warning messaging on the site/crew-side scheduling surface.

Required blocking message direction:

- `無法完成排程：進場前需求尚未確認`

Allowed state direction remains:

- ready / allowed entries remain schedulable

This slice does not implement UI.

It only defines the intended direction for a future blocking indicator.

## 7. API / Write Boundary

This slice is design-only and does not implement any write-path enforcement.

The intended future boundary is:

- hard block should be enforced only on crew-side formal actions that require Entry Ready
- the first actual write path is not fixed in this document
- the concrete application point should be decided in `VWE-PROD-010C` Hard Block Contract Planning
- hard block should not be enforced in the vendor submit path
- hard block should not change the requirement confirmation API

In particular:

- do not add enforcement to vendor-side entry authoring flows

## 8. Out-of-Scope

The following are explicitly out of scope for this slice:

- schema / migration
- API implementation
- UI implementation
- override
- rejected / returned flow
- notification
- audit log
- checklist
- scheduling engine full implementation
- permission model redesign

## 9. Proposed Next Slices

Recommended next slices:

- `010C` Hard Block Contract Planning
- `010D` Hard Block API / Write Guardrail
- `010E` Hard Block UI Indicator
- `010F` Hard Block Guardrail Freeze

Suggested progression:

1. define the hard-block contract boundary
2. define and freeze write-path guardrails
3. introduce a blocking UI indicator on the site/crew-side scheduling surface
4. freeze hard-block behavior before any override or scheduling-engine expansion
