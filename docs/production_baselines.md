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
