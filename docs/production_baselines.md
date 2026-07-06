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

## Product Capability Freeze Scope

### Included

- Vendor pre-entry requirement
- Requirement confirmation
- Entry readiness read contract
- Entry readiness indicator UI
- Entry readiness guardrails

### Explicitly Not Included

- Override
- Rejected / Returned flow
- Notification
- Audit log
- Checklist
- Scheduling gate
- Permission model redesign
- Bulk confirmation
