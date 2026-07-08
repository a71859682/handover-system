# Scheduling Engine v1 Product Design Baseline

## 1. Purpose

This document defines the product design baseline for Scheduling Engine v1.

Scheduling Engine v1 is positioned as the product capability that determines which Vendor Work Entry items can be started, and when they can be treated as ready for real crew-side scheduling execution.

This slice is docs-only.

It does not modify application code, schema, migration behavior, API behavior, permission behavior, workflow behavior, or write behavior.

## 2. Current Baseline

Scheduling Engine v1 is expected to build on the following completed product baselines:

- Vendor Work Entry v1
- Hard Block v1
- Persistent Formal Approval v1
- Work Hub v1

The following operational signals already exist and form the prerequisite foundation:

- `readiness_state` / `readiness_reason`
- `scheduling_gate_state` / `scheduling_gate_reason`
- formal approval state and metadata

This means Scheduling Engine v1 does not need to invent prerequisite readiness logic from scratch.

Instead, it should build on already-established product contracts and guardrails.

## 3. Product Goal

Scheduling Engine v1 should help determine which Vendor Work Entry items can be arranged for entry.

It should help Site and Crew users understand which work items can actually start today.

It should also become the future source that allows Work Hub to display real daily schedulable work instead of only upstream readiness and approval indicators.

## 4. Core Semantics

The scheduling unit is a single Vendor Work Entry.

It is not the whole vendor.

It is not a `work_content` grouping.

If the same vendor has multiple entries, each entry must be evaluated independently for schedulability.

This keeps the scheduling model consistent with the existing entry-level requirement, readiness, hard block, and formal approval model.

## 5. Minimal Scheduling Rule

The first minimal schedulability rule should be:

- requirement confirmed, or no requirement exists
- formal approval completed
- hard block passed
- only then can the entry be treated as schedulable

The first version should not attempt time-conflict scheduling.

It should decide schedulable versus not schedulable first, before introducing richer time allocation logic.

## 6. Actor Boundary

### Vendor

Vendor proposes planned entries.

Vendor does not directly create formal schedule execution state.

### Site / Crew

Site and Crew users review, understand, and execute scheduling decisions based on schedulable entries.

### Supervisor / Admin

Supervisor and Admin can remain the likely future owners of higher-level scheduling rules and controls.

That future responsibility is acknowledged here, but not implemented in this baseline.

## 7. Work Hub Relationship

Scheduling Engine should become one of the future data sources for Work Hub.

Work Hub should be able to display:

- work that can truly start today
- work that is actually scheduled for today

Work Hub itself should not decide scheduling rules.

Instead, Work Hub should remain the presentation and operational entry surface, while Scheduling Engine owns the scheduling semantics.

## 8. Out-of-Scope

The following are explicitly out of scope for this design baseline:

- schema / migration
- API implementation
- UI implementation
- time conflict engine
- calendar integration
- notification
- audit log
- override
- permission redesign

## 9. Proposed Next Slices

Recommended next slices:

- `SE-002` Scheduling State & Rules
- `SE-003` Scheduling Read Contract Planning
- `SE-004` Scheduling Runtime Baseline
- `SE-005` Work Hub Integration
- `SE-006` Guardrail Freeze
- `SE-007` Production Baseline
- `SE-008` Release Baseline

Suggested sequencing:

1. define scheduling state and rules
2. define the scheduling read contract
3. establish runtime baseline
4. integrate with Work Hub
5. freeze guardrails
6. consolidate production and release baselines
