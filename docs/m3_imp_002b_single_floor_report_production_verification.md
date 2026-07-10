# M3-IMP-002B — Single Floor Report Production Verification Baseline

## 1. Purpose

- Formalize the production release evidence for `4e06c6324d2ae750b00214324e00bc5b3252f262`.
- Record the stable production baseline for the single-floor read-only print report.
- Preserve the release evidence without changing runtime behavior or expanding product scope.

This slice is docs-only.

It does not modify application code, templates, static assets, tests, API behavior, schema, permissions, workflow behavior, or write behavior.

## 2. Production Baseline

- Production baseline commit:
  - `4e06c6324d2ae750b00214324e00bc5b3252f262`
  - `Add single floor read-only print report`
- Baseline slice:
  - `M3-IMP-002A — Single Floor Read-only Print Report Baseline`
- Branch baselines after release:
  - `main` / `origin/main`: `4e06c63`
  - `develop` / `origin/develop`: `4e06c63`
- Preserved develop backup:
  - `backup/develop-a852093`: `a852093`
- Render production service:
  - `handover-system`

## 3. Integration Evidence

The Floor Report integration followed a repaired and verified develop baseline:

- the develop baseline repair was completed before Floor Report integration
- the Floor Report commit was cherry-picked onto the repaired develop baseline without conflict
- the develop-to-main production review contained exactly one commit:
  - `4e06c63 Add single floor read-only print report`
- the production merge used fast-forward only
- no merge commit was created
- the reviewed diff was limited to five approved files:
  - `app.py`
  - `static/styles.css`
  - `templates/floor_handover_report.html`
  - `templates/sheet.html`
  - `tests/smoke_test.py`
- reviewed diff stat:
  - `838 insertions(+), 1 deletion(-)`

## 4. Deploy Evidence

The Render production deployment for `4e06c63` completed successfully:

- Render live commit: `4e06c63`
- build successful
- service live
- Gunicorn started normally
- one worker boot observed
- `0` Traceback occurrences
- `0` ERROR occurrences
- no restart loop observed

## 5. Runtime Health

Public unauthenticated runtime verification completed with the expected results:

- `GET /` -> `302 /login`
- `GET /login` -> `200`
- `GET /reports/floor/1` -> `302 /login`
- `GET /api/grid?sheet_id=1` -> `302 /login`

Stability verification:

- `/login` returned `200` for 20 consecutive checks
- stability result: `20/20 = 200`
- no intermittent non-`200` response was observed during the stability check

## 6. Production Release Markers

Production release verification confirmed the expected Floor Report markers:

- `GET /reports/floor/<int:floor_id>` route
- `templates/floor_handover_report.html`
- read-only `樓層報表` entry on `/sheet`
- current-state disclaimer:
  - `本報表反映產出當下系統狀態，並非不可變歷史證明。`
- `window.print()` print action
- `.floor-report-link` CSS marker
- `.floor-report-page` CSS marker
- `48` scoped `.floor-report-*` markers in the production stylesheet
- production `styles.css` `Last-Modified`:
  - `Fri, 10 Jul 2026 09:56:30 GMT`

## 7. Permission And Regression Evidence

The complete smoke regression suite verified:

- same-site member access PASS
- same-site admin access PASS
- vendor access forbidden PASS
- cross-site member and admin access returns `403` PASS
- cross-site responses do not disclose site, sheet, floor, or block identity PASS
- missing current site behavior PASS
- missing floor returns `404` PASS
- report `GET` leaves the database unchanged PASS
- Unit Report regression PASS
- existing `/sheet` behavior and contract preserved
- existing `/api/grid` behavior and contract preserved

Regression commands:

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `node --check static/app.js` - PASS

## 8. Verification Boundary

- Public production checks verified deployment state, unauthenticated route behavior, runtime stability, and production static markers.
- Authenticated role and permission cases were verified by the complete smoke regression suite against the live commit source baseline.
- No production credentials were used or inferred for this verification.

## 9. Product Classification

- The Floor Report reflects the current system read model at generation time.
- It is not an immutable historical certificate.
- Browser Print and Save as PDF are the supported output paths.
- No schema or migration was added.
- No dependency or PDF library was added.
- No POST, mutation, workflow action, or write behavior was added.
- No completion scoring was added.
- No business-rule re-derivation was introduced.

## 10. Final Decision

- `M3-IMP-002A` is production-verified at commit `4e06c6324d2ae750b00214324e00bc5b3252f262`.
- `4e06c63` is the stable production baseline for the single-floor read-only print report.
- This document records release evidence only and introduces no runtime or contract change.
