# M3-IMP-001B — Single Unit Report Production Verification Baseline

## 1. Purpose

- Formalize the production release evidence for `5ff8cd4`.
- Record the verified production baseline for the single-unit read-only print report.
- Preserve the release evidence without changing runtime behavior or expanding product scope.

This slice is docs-only.

It does not modify application code, templates, static assets, tests, API behavior, schema, permissions, workflow behavior, or write behavior.

## 2. Production Baseline

- Production baseline commit:
  - `5ff8cd4`
  - `Add single unit read-only print report`
- Baseline slice:
  - `M3-IMP-001A — Single Unit Read-only Print Report Baseline`
- Main branch merge:
  - `eac60c8` -> `5ff8cd4`
  - fast-forward PASS
- Remote update:
  - `origin/main` updated to `5ff8cd4`
  - push PASS
- Render production service:
  - `handover-system`
- Render live commit:
  - `5ff8cd4`

## 3. Deploy Evidence

The Render deployment for `5ff8cd4` completed successfully:

- build successful
- service live
- `0` Traceback occurrences
- `0` ERROR occurrences
- one worker boot observed
- no worker exit observed
- no worker restart loop observed

## 4. Runtime Health

Public unauthenticated runtime verification completed with the expected results:

- `GET /` -> `302 /login`
- `GET /login` -> `200`
- `GET /reports/unit/1` -> `302 /login`
- `GET /api/grid?sheet_id=1` -> `302 /login`

Stability verification:

- `/login` returned `200` for 20 consecutive checks
- stability result: `20/20 = 200`
- no intermittent `502` was observed

Assessment:

- the internal report route preserves its unauthenticated login boundary
- the existing `/api/grid` unauthenticated contract remains unchanged
- the public service remained stable after the deployment completed

## 5. Report Release Evidence

Production release verification confirmed:

- report-scoped `.unit-report-*` CSS is present in production
- the read-only unit report link marker is present
- production `styles.css` `Last-Modified`:
  - `Fri, 10 Jul 2026 08:38:31 GMT`
- authenticated report content markers were verified through the Render live commit and smoke regression suite

The verified report content markers include:

- the single-unit report title
- the current-state disclaimer
- the `未填寫` missing-value presentation
- the no-tasks empty state
- the no-active-extra-fields empty state
- the `window.print()` print action
- the read-only report entry from the existing unit context on `/sheet`

## 6. Permission And Regression Evidence

The complete smoke regression suite verified:

- same-site member access PASS
- same-site admin access PASS
- vendor access forbidden PASS
- cross-site member access returns `403` PASS
- cross-site admin access returns `403` PASS
- cross-site responses do not disclose site, sheet, floor, block, or unit identity PASS
- missing current site behavior PASS
- missing unit returns `404` PASS
- report `GET` leaves the database unchanged PASS
- existing `/sheet` behavior and contract preserved
- existing `/api/grid` behavior and contract preserved
- no POST or mutation behavior added
- no schema, migration, dependency, or PDF library added

Local regression verification:

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `node --check static/app.js` - PASS

## 7. Known Limitation

- The authenticated production report HTML was not directly rendered because no production application login session was available in the verification environment.
- No production credentials were used, requested, or inferred for this verification.
- Therefore the protected report body was verified through:
  - the Render live commit
  - the complete smoke regression suite
  - the production unauthenticated route behavior
  - production report-scoped CSS markers
  - the read-only unit report link marker

This limitation does not change the verified public runtime health or the regression evidence, but it distinguishes production public checks from authenticated role-matrix checks performed by the smoke suite.

## 8. Report Classification

- The report reflects the current system read model at generation time.
- The report is not an immutable historical certificate.
- Browser Print and Save as PDF are the supported first-version output paths.
- No historical snapshot, electronic signature, attachment bundle, batch export, or server-generated PDF is included in this baseline.

## 9. Final Decision

- `M3-IMP-001A` is production-verified at commit `5ff8cd4`.
- `5ff8cd4` is suitable as the stable production baseline for the single-unit read-only print report.
- This document records release evidence only and introduces no runtime or contract change.
