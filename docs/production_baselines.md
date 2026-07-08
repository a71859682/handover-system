# Production Baselines

## Entry Readiness v1 Production Live

### 1. Baseline Name

- Entry Readiness v1 Production Live

### 2. Branch / Commit

- Branch: `main`
- Commit: `2251bf8 Merge entry readiness v1`

### 3. Deploy Status

- Render production live commit: `2251bf8`
- Deploy: `PASS`
- Runtime health: `PASS`

### 4. Completed Capability

- Vendor can write entry-level `pre_entry_requirement`
- Vendor create/update path supports requirement write-through
- Site/Crew can confirm requirement per entry
- Confirmation is entry-level
- Crew read payload exposes `readiness_state` and `readiness_reason`
- Crew UI shows a per-entry readiness indicator
- Entry Readiness v1 guardrails are frozen

### 5. Verified Health

- `GET /` -> `302 /login`
- `GET /login` -> `200`
- `GET /vendor/work-entry` unauthenticated -> `302 /vendor/login`
- `GET /sheet` unauthenticated -> `302 /login`
- `GET /api/crew-forms?sheet_id=1` unauthenticated -> `302 /login`
- Render logs clean:
  - no `Traceback`
  - no `ERROR`
  - no restart loop

### 6. Known Limitation

- This production validation did not include authenticated payload-level manual verification after deploy.
- Authenticated payload-level verification can remain part of a future staging / production checklist.

## Scheduling Gate v1 Production Baseline

### 1. Purpose

- Define the first production baseline for Scheduling Gate v1.
- Consolidate the completed Scheduling Gate read contract, warning UI, and guardrail freeze into a stable reference baseline.
- Keep this baseline docs-only, with no application, schema, API, permission, workflow, or write-path change.

### 2. Completed Capability Inventory

- Scheduling Gate Read Contract
- Scheduling Gate Warning UI
- Scheduling Gate Guardrail Freeze

### 3. Actor Boundary

- Vendor
  - continues vendor submit flow without scheduling-gate blocking
  - does not control scheduling-gate projection

- Site/Crew
  - views scheduling-gate state and reason from crew-side read payload
  - sees warning / allowed indicator on the crew-side entry list
  - continues requirement confirmation without scheduling-gate blocking

- Admin
  - retains existing site-side operational boundary
  - does not receive new scheduling-gate override or control surface in this baseline

### 4. API / Read Boundary

- Crew-side read surface exposes:
  - `scheduling_gate_state`
  - `scheduling_gate_reason`

- These fields are read-contract projection fields only.

- Relationship to readiness:
  - `readiness_state=not_ready` and `readiness_reason=requirement_pending`
    - projects to `scheduling_gate_state=warning`
    - projects to `scheduling_gate_reason=requirement_pending`
  - `readiness_state=ready` and `readiness_reason=requirement_confirmed`
    - projects to `scheduling_gate_state=allowed`
    - projects to `scheduling_gate_reason=requirement_confirmed`
  - `readiness_state=ready` and `readiness_reason=no_requirement`
    - projects to `scheduling_gate_state=allowed`
    - projects to `scheduling_gate_reason=no_requirement`

- No new persisted scheduling-gate field is introduced in this baseline.

### 5. UI Boundary

- Crew-side UI shows a scheduling-gate indicator per `.crew-entry-row`.
- Indicator states in this baseline are:
  - warning indicator
  - allowed indicator
- This UI is non-blocking.
- It does not affect vendor submit.
- It does not affect requirement confirmation.
- It does not introduce hard block, override, or write behavior.

### 6. Freeze Criteria

- Read Contract
  - `/api/crew-forms` work entries must include `scheduling_gate_state` and `scheduling_gate_reason`
  - pending requirement must remain `warning / requirement_pending`
  - confirmed requirement must remain `allowed / requirement_confirmed`
  - no requirement must remain `allowed / no_requirement`

- UI Warning
  - crew readonly render guardrail must cover scheduling-gate indicator wiring
  - crew readonly render guardrail must cover the three scheduling-gate labels

- Regression Guardrails
  - readiness regression remains green
  - confirmation API smoke remains green
  - vendor submit pipeline regression remains green
  - vendor write isolation remains green

### 7. Explicit Out-of-Scope

- Hard Block
- Override
- Notification
- Audit Log
- Scheduling Engine
- Permission Rewrite
- Workflow Redesign

### 8. Future Product Lines

- Scheduling Gate Hard Block
- Override Policy
- Rejected / Returned Flow
- Notification
- Audit Log

## Scheduling Gate v1 Release Baseline

### 1. Release Name

- Scheduling Gate v1

### 2. Capability Inventory

- Scheduling Gate Read Contract
- Scheduling Gate Warning UI
- Scheduling Gate Guardrail Freeze

### 3. Baseline Commit

- Read Contract commit
  - `bb96f9f` - `Add scheduling gate read contract`
- Warning UI commit
  - `2349639` - `Add scheduling gate warning UI`
- Guardrail Freeze commit
  - `08180ec` - `Freeze scheduling gate guardrails`
- Production Baseline commit
  - `6cb9823` - `Document scheduling gate production baseline`

### 4. Verification

- `python -m compileall app.py tests` - PASS
- `run_crew_api_smoke(...)` - PASS
- `run_crew_readonly_render_smoke(...)` - PASS
- `run_vendor_work_entry_requirement_confirmation_smoke(...)` - PASS
- `run_vendor_work_entry_submit_pipeline_regression_smoke(...)` - PASS
- `run_vendor_work_entry_write_isolation_smoke(...)` - PASS

### 5. Production Scope

- warning only
- non-blocking
- no override
- no scheduling engine
- no workflow change

### 6. Future Product Lines

- Scheduling Gate Hard Block
- Override Policy
- Scheduling Engine
- Notification
- Audit Log

## Hard Block v1 Production Baseline

### 1. Baseline Name

- Hard Block v1 Production Baseline

### 2. Completed Capability

- Formal approve no-op API contract
- Hard block `entry_not_ready` guardrail
- Crew-side formal approve UI baseline
- Success / blocked feedback
- Guardrail freeze

### 3. Scope

- no-op success
- no persistence
- blocked reject
- DB unchanged
- crew-side only

### 4. Explicit Out-of-Scope

- override
- rejected / returned
- notification
- audit log
- scheduling engine
- persistent formal approval state
- permission redesign

### 5. Verification

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `run_vendor_work_entry_formal_approve_smoke(...)` - PASS
- `run_crew_readonly_render_smoke(...)` - PASS
- `run_crew_api_smoke(...)` - PASS
- `run_vendor_work_entry_submit_pipeline_regression_smoke(...)` - PASS
- `run_vendor_work_entry_requirement_confirmation_smoke(...)` - PASS
- `run_vendor_work_entry_write_isolation_smoke(...)` - PASS

### 6. Dependencies

- Vendor Work Entry Product Baseline v1
- Scheduling Gate v1 Production Baseline
- 010B
- 010C
- 010D-0
- 010D
- 010E
- 010F
- 010G

## Hard Block v1 Release Baseline

### 1. Release Name

- Hard Block v1

### 2. Capability Inventory

- Hard Block Design
- Contract Planning
- Formal Action Inventory
- State Machine
- No-op API Contract
- UI Baseline
- Guardrail Freeze
- Production Baseline

### 3. Baseline Commits

- 010B Design Baseline
  - `3ae0b8f` - `Document scheduling hard block design baseline`
- 010C Contract Planning
  - `fca03b9` - `Document hard block contract planning`
- 010D-0 Formal Action Inventory
  - `947cddd` - `Document crew formal action inventory`
- 010D State Machine
  - `f905774` - `Document formal action state machine baseline`
- 010E No-op API Contract
  - `216125f` - `Add hard block formal approve API baseline`
- 010F UI Baseline
  - `2ba355b` - `Add hard block formal approve UI baseline`
- 010G Guardrail Freeze
  - `562adba` - `Freeze hard block guardrails`
- 010H Production Baseline
  - `6a7888d` - `Document hard block production baseline`

### 4. Verification

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `run_vendor_work_entry_formal_approve_smoke(...)` - PASS
- `run_crew_readonly_render_smoke(...)` - PASS
- `run_crew_api_smoke(...)` - PASS
- `run_vendor_work_entry_submit_pipeline_regression_smoke(...)` - PASS
- `run_vendor_work_entry_requirement_confirmation_smoke(...)` - PASS
- `run_vendor_work_entry_write_isolation_smoke(...)` - PASS

### 5. Production Scope

- no persistence
- no schema
- no workflow change
- no override
- no scheduling engine
- no audit log

### 6. Future Product Lines

- Persistent Formal Approval State
- Override Policy
- Scheduling Engine
- Notification
- Audit Log

## Persistent Formal Approval v1 Production Baseline

### 1. Baseline Name

- Persistent Formal Approval v1 Production Baseline

### 2. Completed Capability

- Formal Approval Schema
- Formal Approval Runtime Write
- Formal Approval Crew Read Contract
- Formal Approval Crew UI
- Formal Approval Guardrail Freeze

### 3. Scope

- persisted approval
- approved metadata
- no override
- no rejected / returned
- no scheduling engine
- no audit log

### 4. Verification

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `run_vendor_work_entry_formal_approve_smoke(...)` - PASS
- `run_crew_api_smoke(...)` - PASS
- `run_crew_readonly_render_smoke(...)` - PASS
- `run_vendor_work_entry_write_isolation_smoke(...)` - PASS

### 5. Explicit Out-of-Scope

- override
- notification
- audit log
- scheduling engine
- rejected / returned

## Persistent Formal Approval v1 Release Baseline

### 1. Release Name

- Persistent Formal Approval v1

### 2. Capability Inventory

- Design Baseline
- Schema Evaluation
- Persistence Schema
- Write Contract
- Runtime Write
- Crew Read Contract
- Crew UI
- Guardrail Freeze
- Production Baseline

### 3. Baseline Commits

- 011A Design Baseline
  - `ef7ade6` - `Document persistent formal approval design baseline`
- 011B Schema Evaluation
  - `a026f0b` - `Document formal approval schema evaluation`
- 011C Persistence Schema
  - `1497c03` - `Add formal approval persistence schema baseline`
- 011D Write Contract
  - `5a2052f` - `Document formal approval write contract`
- 011E Runtime Write
  - `ac50826` - `Persist vendor formal approval`
- 011F Crew Read Contract
  - `31fa5e4` - `Add formal approval crew read contract`
- 011G Crew UI
  - `6667cf0` - `Add formal approval crew UI`
- 011H Guardrail Freeze
  - Freeze verified by full smoke and targeted formal approval / crew render / crew API smoke coverage
- 011I Production Baseline
  - `2a51556` - `Document persistent formal approval production baseline`

### 4. Verification

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `run_vendor_work_entry_formal_approve_smoke(...)` - PASS
- `run_crew_api_smoke(...)` - PASS
- `run_crew_readonly_render_smoke(...)` - PASS
- `run_vendor_work_entry_write_isolation_smoke(...)` - PASS

### 5. Production Scope

- persisted approval
- read contract
- UI indicator
- no override
- no audit log
- no scheduling engine
- no rejected / returned

### 6. Future Product Lines

- Override Policy
- Approval Revocation
- Approval History / Audit
- Scheduling Engine Integration
- Notification

## Product Capability Freeze Scope

### Included

- Vendor pre-entry requirement
- Requirement confirmation
- Entry readiness read contract
- Entry readiness indicator UI
- Entry readiness guardrails
- Scheduling gate read contract
- Scheduling gate warning UI
- Scheduling gate guardrails

### Explicitly Not Included

- Override
- Rejected / Returned flow
- Notification
- Audit log
- Checklist
- Scheduling gate hard block
- Scheduling gate override
- Scheduling engine
- Permission model redesign
- Bulk confirmation

## Work Hub v1 Production Baseline

### 1. Baseline Name

- Work Hub v1 Production Baseline

### 2. Completed Capability

- Product Vision: Task-Driven / Role-Oriented
- Dashboard v1 Design Baseline
- Dashboard Read Contract Planning
- Dashboard Aggregation API
- Work Hub Cards
- Work Hub Quick Actions

### 3. Scope

- read-only aggregation
- mobile-first work cards
- role-oriented work hub
- quick action scroll targets
- no write behavior
- no new schema

### 4. Verification

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `run_dashboard_api_smoke(...)` - PASS
- `run_work_hub_quick_action_smoke(...)` - PASS
- `run_crew_readonly_render_smoke(...)` - PASS

### 5. Explicit Out-of-Scope

- full Dashboard UI
- analytics
- notification
- scheduling engine
- audit log
- permission redesign
- new persistence

## Work Hub v1 Release Baseline

### 1. Release Name

- Work Hub v1

### 2. Capability Inventory

- Product Vision: Task-Driven Construction Operations Platform
- Role-Oriented Work Hub
- Dashboard v1 Product Design Baseline
- Dashboard Read Contract Planning
- Dashboard Aggregation API
- Work Hub Cards
- Work Hub Quick Actions
- Work Hub Production Baseline

### 3. Baseline Commits

- VISION-001
  - `b523748` - `Document product vision`
- VISION-002
  - `fb9bd98` - `Document dashboard read contract and role-oriented work hub`
- DASH-001
  - `df2547a` - `Document dashboard v1 product design baseline`
- DASH-002
  - `fb9bd98` - `Document dashboard read contract and role-oriented work hub`
- DASH-003
  - `35d6fc1` - `Add dashboard aggregation API baseline`
- DASH-004
  - `60c0ed5` - `Add work hub dashboard cards`
- DASH-005
  - `70b6fa1` - `Add work hub quick actions`
- DASH-006
  - `236db4c` - `Document work hub v1 production baseline`

### 4. Verification

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `run_dashboard_api_smoke(...)` - PASS
- `run_work_hub_quick_action_smoke(...)` - PASS
- `run_crew_readonly_render_smoke(...)` - PASS

### 5. Production Scope

- read-only aggregation
- mobile-first cards
- role-oriented work hub
- quick action scroll targets
- no write behavior
- no new schema

### 6. Future Product Lines

- Scheduling Engine
- Notification
- Analytics
- Mobile Experience

## Scheduling Engine v1 Production Baseline

### 1. Baseline Name

- Scheduling Engine v1 Production Baseline

### 2. Completed Capability

- Product Design Baseline
- State & Rules Baseline
- Read Contract Planning
- Runtime Aggregation API
- Work Hub Integration
- Guardrail Freeze

### 3. Scope

- Read-only Decision Layer
- Scheduling Decision API
- Work Hub Integration
- No persistence
- No scheduler write
- No calendar
- No time conflict engine

### 4. Verification

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `run_scheduling_api_smoke(...)` - PASS
- `run_work_hub_scheduling_smoke(...)` - PASS
- `run_scheduling_guardrail_smoke(...)` - PASS

### 5. Explicit Out-of-Scope

- Scheduler persistence
- Calendar integration
- Time conflict resolution
- Notification
- Audit log
- Override
- Permission redesign

## Scheduling Engine v1 Release Baseline

### 1. Release Name

- Scheduling Engine v1

### 2. Capability Inventory

- Product Design Baseline
- State & Rules Baseline
- Read Contract Planning
- Runtime Aggregation API
- Work Hub Integration
- Guardrail Freeze
- Production Baseline

### 3. Baseline Commits

- SE-001
  - `9c53a09` - `Document scheduling engine v1 product design baseline`
- SE-002
  - `60468cf` - `Document scheduling engine state rules baseline`
- SE-003
  - `18b78ba` - `Document scheduling engine read contract planning`
- SE-004
  - `b032efe` - `Add scheduling runtime aggregation baseline`
- SE-005
  - `dfdd145` - `Integrate scheduling into work hub`
- SE-006
  - `f033a00` - `Freeze scheduling engine guardrails`
- SE-007
  - `d3e7a36` - `Document scheduling engine production baseline`

### 4. Verification

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `run_scheduling_api_smoke(...)` - PASS
- `run_work_hub_scheduling_smoke(...)` - PASS
- `run_scheduling_guardrail_smoke(...)` - PASS

### 5. Production Scope

- Read-only Decision Layer
- Scheduling Decision API
- Work Hub Integration
- No persistence
- No scheduler write
- No calendar
- No time conflict engine

### 6. Future Product Lines

- Scheduler Persistence
- Calendar Integration
- Time Conflict Resolution
- Notification
- Analytics
- Mobile Experience

## Scheduler Persistence v1 Production Baseline

### 1. Baseline Name

- Scheduler Persistence v1 Production Baseline

### 2. Completed Capability

- Product Design Baseline
- Schema Evaluation
- Runtime Write Contract
- Read Contract Planning
- Schema Baseline
- Runtime Write
- Guardrail Freeze

### 3. Scope

- Scheduler Persistence
- Runtime Write
- Read Contract
- No calendar
- No notification
- No analytics
- No attendance
- No override

### 4. Verification

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `run_scheduler_schema_smoke(...)` - PASS
- `run_scheduler_persistence_smoke(...)` - PASS
- `run_scheduler_persistence_guardrail_smoke(...)` - PASS

### 5. Explicit Out-of-Scope

- Calendar
- Notification
- Analytics
- Attendance
- Override
- Audit Log
- Permission redesign

## Scheduler Persistence v1 Release Baseline

### 1. Release Name

- Scheduler Persistence v1

### 2. Capability Inventory

- Product Design Baseline
- Schema Evaluation
- Runtime Write Contract
- Read Contract Planning
- Schema Baseline
- Runtime Write
- Guardrail Freeze
- Production Baseline

### 3. Baseline Commits

- SP-001
  - `3aa11f6` - `Document scheduler persistence product design baseline`
- SP-002
  - `dd083c0` - `Document scheduler persistence schema evaluation`
- SP-003
  - `f6ff7b1` - `Document scheduler persistence write contract`
- SP-004
  - `cb45cfa` - `Document scheduler persistence read contract planning`
- SP-005
  - `49dc2d1` - `Add scheduler persistence schema baseline`
- SP-006
  - `9339c71` - `Add scheduler persistence runtime write`
- SP-007
  - `d88c9f8` - `Freeze scheduler persistence guardrails`
- SP-008
  - `eae362c` - `Document scheduler persistence production baseline`

### 4. Verification

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `run_scheduler_schema_smoke(...)` - PASS
- `run_scheduler_persistence_smoke(...)` - PASS
- `run_scheduler_persistence_guardrail_smoke(...)` - PASS

### 5. Production Scope

- Scheduler Persistence
- Runtime Write
- Read Contract
- No calendar
- No notification
- No analytics
- No attendance
- No override

### 6. Future Product Lines

- Calendar Integration
- Notification Integration
- Analytics
- Attendance
- Mobile Experience

## Work Hub Scheduled Integration Production Baseline

### 1. Baseline Name

- Work Hub Scheduled Integration Production Baseline

### 2. Completed Capability

- Planning
- Scheduled Aggregation Runtime
- Scheduled Work Hub Card
- Scheduled Quick Action
- Scheduled Guardrail Freeze

### 3. Scope

- Dashboard scheduled aggregation
- Scheduled Work Hub card
- Scheduled quick action
- Read-only integration
- No write behavior
- No schema change

### 4. Verification

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `run_dashboard_api_smoke(...)` - PASS
- `run_work_hub_scheduled_smoke(...)` - PASS
- `run_work_hub_scheduled_guardrail_smoke(...)` - PASS

### 5. Explicit Out-of-Scope

- Calendar
- Notification
- Analytics
- Attendance
- Scheduler write
- Permission redesign
