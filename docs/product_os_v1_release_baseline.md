# Product OS v1.0 Release Baseline

## 1. Purpose

- Define Product OS v1.0 (M1) as the first official product milestone.
- Consolidate the currently completed core product lines into one milestone-level release baseline.
- Keep this slice docs-only with no runtime, schema, API, permission, workflow, or write-path change.

## 2. Product Vision

Product OS v1.0 is built on two aligned product principles:

- Task-Driven Construction Operations Platform
- Role-Oriented Work Hub

Together, these principles define a system that helps each role understand what work exists, what is blocked, what is ready, and what action should happen next.

## 3. Capability Inventory

Product OS v1.0 (M1) consolidates the following completed product lines:

- Vendor Work Entry v1
- Hard Block v1
- Persistent Formal Approval v1
- Work Hub v1
- Scheduling Engine v1
- Scheduler Persistence v1

These capabilities together establish the first milestone-level operational baseline for vendor entry submission, crew-side review, decision gating, formal approval, scheduling decision, schedule persistence, and role-oriented work presentation.

## 4. Architecture Summary

### Product Vision

- Task-Driven Construction Operations Platform
- Role-Oriented Work Hub

### Business Layer

- Vendor Work Entry
- Requirement Confirmation
- Formal Approval

This layer represents the core business actions and business state transitions used by vendor and crew/site operations.

### Decision Layer

- Entry Readiness
- Scheduling Gate
- Hard Block
- Scheduling Engine

This layer evaluates whether work is ready, blocked, schedulable, or not yet allowed for downstream actions.

### Persistence Layer

- Persistent Formal Approval
- Scheduler Persistence

This layer stores durable operational facts after business and decision checks succeed.

### Presentation Layer

- Crew-side readonly entry rendering
- Work Hub
- Work Hub Cards
- Work Hub Quick Actions

This layer presents the current operational state to users without redefining business or decision rules.

## 5. Production Baselines

The following product lines already have completed Production / Release Baselines:

- Vendor Work Entry Product Baseline v1
- Hard Block v1 Production / Release Baseline
- Persistent Formal Approval v1 Production / Release Baseline
- Work Hub v1 Production / Release Baseline
- Scheduling Engine v1 Production / Release Baseline
- Scheduler Persistence v1 Production / Release Baseline

These baselines together define the current Product OS v1.0 operating surface.

## 6. Verification

The shared milestone validation baseline is:

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- core smoke suites across Vendor Work Entry, Hard Block, Persistent Formal Approval, Work Hub, Scheduling Engine, and Scheduler Persistence - PASS

This release baseline assumes the current full smoke suite remains the canonical integrated verification surface for Product OS v1.0.

## 7. Out-of-Scope

- Calendar
- Notification
- Analytics
- Attendance
- Mobile implementation
- 工區管理部角色
- New runtime feature expansion in this milestone document

## 8. Next Product Evolution

Product OS v1.x is expected to evolve through controlled, baseline-driven expansion, including:

- Calendar Integration
- Notification
- Analytics
- Mobile Experience
- Work Hub Scheduled Integration

Future work should continue to follow the same pattern used in M1:

- design baseline
- schema / contract planning
- runtime implementation
- guardrail freeze
- production baseline
- release baseline
