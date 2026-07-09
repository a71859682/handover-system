# M2-IMP-002H — Management Read Model Runtime Verification / Release Note Baseline

## 1. Purpose

- Formalize the production verification evidence for `5d74e7a`.
- Record the release-note baseline for the Management Read Model dashboard consumption slice.
- Preserve the current runtime baseline without expanding API scope or changing behavior.

This slice is docs-only.

It does not modify runtime code, static assets, templates, schema, migration behavior, API behavior, permission behavior, fallback behavior, workflow behavior, or write behavior.

## 2. Production Baseline

- Production baseline commit:
  - `5d74e7a`
  - `Add management read model dashboard consumption`
- Baseline slice:
  - `M2-IMP-002G — Management Read Model Dashboard Consumption Baseline`
- Production service:
  - `handover-system`
- Production verification status:
  - public runtime verification completed

## 3. Release Evidence

Production verification confirmed that `/static/app.js` includes the expected Management Read Model dashboard-consumption markers:

- `/api/management-read-model?sheet_id=`
- `優先使用 management read model API`
- `drilldown_refs: managementReadModelData.drilldown_refs`
- `resolveTargetAction("today_entries", "today-entries")`

Interpretation:

- Management Insight Summary now primarily consumes `GET /api/management-read-model`.
- The frontend keeps read-only drilldown wiring through `drilldown_refs`.
- The deployed asset matches the intended `5d74e7a` release shape.

## 4. Runtime Health

Public runtime verification completed successfully with the following unauthenticated route checks:

- `GET /` -> `302 /login`
- `GET /login` -> `200`
- `GET /api/management-read-model?sheet_id=1` -> `403`
- `GET /api/work-hub-runtime?sheet_id=1` -> `403`

Assessment:

- page-route redirect behavior remains healthy
- protected JSON API guardrails remain healthy
- no public runtime evidence of contract or auth regression was observed

## 5. Preserved Contracts

The following contracts and behavior remain unchanged in this baseline:

- `/api/dashboard` unchanged
- `/api/scheduling` unchanged
- `/api/work-hub-runtime` unchanged
- `/api/management-read-model` public shape unchanged
- Work Hub runtime consumer preserved
- fallback path preserved
- read-only drilldown preserved
- no write behavior added
- no mutation behavior added
- no workflow action added

## 6. Verification Evidence

Local verification:

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS

Merge / deploy verification:

- `main` fast-forward to `5d74e7a` - PASS
- `origin/main` updated to `5d74e7a` - PASS
- production public runtime verification - PASS

## 7. Known Limitation

- Render dashboard logs were not directly readable in this verification environment.
- Public runtime checks showed stable service after deploy.
- Production verification observed a brief transient `502` during rollout, followed by stable healthy responses after the new asset became live.

## 8. Release Note Baseline

This slice should be understood as a release-note and runtime-verification consolidation step, not as new feature expansion.

It records that:

- dashboard Management Insight Summary primarily reads from `GET /api/management-read-model`
- existing dashboard, scheduling, and work-hub contracts remain preserved
- no runtime write-path, permission, schema, or workflow expansion was introduced

## 9. Final Decision

- `M2-IMP-002G` is production-verified at commit `5d74e7a`
- the Management Read Model dashboard-consumption baseline is now formally documented
- the next slice should continue with verification / guardrail strengthening before any new API expansion
