# M1-IMP-005 — Work Hub Product Freeze Baseline

## 1. Purpose

- Consolidate the current Work Hub implementation into an M1 Product Freeze decision.
- Confirm that Work Hub has reached a stable read-only product boundary for Product OS v1.x.
- Record the final freeze checklist, production baseline, and post-freeze backlog split.

This slice is docs-only.

It does not modify runtime code, static assets, templates, schema, migration behavior, API behavior, permission behavior, workflow behavior, or write behavior.

## 2. Current Production Baseline

- Production live commit:
  - `ad828de`
  - `Add work hub accessibility freeze baseline`
- Current production status:
  - Deploy PASS
  - Logs PASS
  - Runtime Health PASS

## 3. Runtime Freeze

The following runtime capabilities are complete and verified:

### Work Hub Runtime Helper

- `build_work_hub_runtime_payload(...)` exists and is smoke-covered.
- It preserves the expected top-level contract:
  - `sheet_id`
  - `business_date`
  - `dashboard`
  - `scheduling`
  - `work_hub`
- It reuses dashboard and scheduling payloads rather than inventing a new contract.

### Work Hub Runtime API

- `/api/work-hub-runtime` exists and is smoke-covered.
- It matches helper output without contract drift.
- It preserves authorization boundaries:
  - unauthenticated -> `403`
  - vendor forbidden -> `403`
  - missing current site -> `403`
  - cross-site read forbidden -> `403`
- It remains read-only and must not modify DB state.

### Single API Consumption

- Work Hub UI consumes `/api/work-hub-runtime` as the primary read path.
- Frontend uses the unified payload instead of recomputing separate cross-domain facts.

### Runtime Fallback

- If `/api/work-hub-runtime` is unavailable, the frontend falls back to:
  - `/api/dashboard`
  - `/api/scheduling`
- This preserves the earlier baseline and avoids a hard dependency regression.

### Freeze Decision

Runtime Freeze status:

- complete
- no contract drift observed
- no runtime change required for M1 freeze

## 4. UI Freeze

The following UI capabilities are complete and verified:

### Cards

- Work Hub cards show top-level counts for:
  - blocked
  - schedulable
  - scheduled
  - pending approval
  - pending requirement
  - today entries
- Cards preserve quick-action scroll targets.

### Focus Sections

- Five focus sections are complete:
  - Blocked 項目
  - 可排程
  - 已正式排程
  - 今日排程
  - 今日進場總覽
- Each section includes:
  - count
  - short description
  - up to 4 entries
  - empty state

### Focus Item Navigation

- Focus item click locates:
  - `.crew-entry-row[data-entry-id="<entry_id>"]`
- Existing behavior is preserved:
  - row scroll
  - row highlight
  - safe fallback / no-op

### Focus Item Affordance

- Section-level hint is present.
- Hover / active / arrow affordance is present.
- Mobile tap target has been hardened.

### Summary Density

- Focus item summary now uses:
  - 1 primary timeline summary
  - 1 short summary line
  - up to 2 short badges
- No long metadata is introduced.
- No headcount information is pulled into the focus item surface.

### Accessibility

- Focus items are keyboard reachable.
- Focus items now expose:
  - `tabindex="0"`
  - `role="button"`
  - `aria-label`
- `Enter` / `Space` activate the existing navigation path.
- `:focus-visible` style is present.

### Freeze Decision

UI Freeze status:

- complete
- no required M1 UI blocker remains

## 5. Product Freeze Checklist

The following checklist defines Work Hub Product Freeze for Product OS v1.x.

### Runtime

- unified runtime helper exists
- runtime API exists
- single API consumption exists
- runtime fallback exists
- no contract drift

### API

- top-level response shape frozen
- internal `work_hub` shape frozen
- summary shape frozen
- protected auth behavior frozen

### UI

- cards complete
- focus sections complete
- focus item summary density complete
- focus item affordance complete

### Navigation

- cards quick action preserved
- focus item row navigation preserved
- row-missing fallback preserved

### Accessibility

- keyboard reachable
- keyboard activation
- focus-visible state
- aria semantics

### Mobile-first

- first-screen scan is practical
- density is readable
- tap target is acceptable
- no long metadata overload

### Read-only Boundary

- no new fetch path beyond existing read contracts
- no POST / mutation added in Work Hub focus interaction
- no write action introduced by freeze slices

### Business Rule Boundary

- Work Hub does not re-judge:
  - blocked
  - schedulable
  - scheduled
  - formal approval
  - gate state
  - readiness

### Smoke Coverage

- runtime helper smoke
- runtime API smoke
- runtime consumption smoke
- quick action smoke
- scheduling smoke
- scheduled smoke
- scheduled guardrail smoke
- focus item summary density guardrails
- focus item accessibility guardrails

### Production Verification

- GitHub main updated
- Render deploy PASS
- Render logs clean
- public runtime health PASS

## 6. Outstanding Items

### M1 Freeze Completed

- runtime helper
- runtime API
- single API consumption
- runtime fallback
- cards
- focus sections
- focus item navigation
- focus item affordance
- summary density
- accessibility freeze
- smoke guardrails
- production verification

### M2 Backlog

- richer operational action entry
- deeper keyboard / screen-reader polish
- filtering / sorting refinement
- analytics
- notification
- calendar integration
- attendance
- broader mobile-native experience

These items are future product growth, not M1 freeze blockers.

## 7. Freeze Decision

### M1 Product Freeze

Decision:

- Work Hub has reached M1 Product Freeze.

Rationale:

- runtime path is complete
- UI surface is complete
- read-only boundary is preserved
- business-rule boundary is preserved
- smoke guardrails are comprehensive
- production baseline is verified live

### Frozen Module Recommendation

Recommendation:

- Work Hub should be marked as a Product OS v1 Frozen Module.

This means future change after this point should default to:

- planning first
- explicit scope boundary
- freeze-safe implementation slices
- no casual contract drift

## 8. Verification

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `run_work_hub_runtime_helper_smoke(...)` - PASS
- `run_work_hub_runtime_api_smoke(...)` - PASS
- `run_work_hub_runtime_consumption_smoke(...)` - PASS
- `run_work_hub_quick_action_smoke(...)` - PASS
- `run_work_hub_scheduling_smoke(...)` - PASS
- `run_work_hub_scheduled_smoke(...)` - PASS
- `run_work_hub_scheduled_guardrail_smoke(...)` - PASS

## 9. Next Slice

Recommended next slice:

- `M1-IMP-006 — Work Hub Release Baseline`

Its role should be:

- release-level documentation
- Product OS v1.x baseline alignment
- no new runtime or UI feature scope
