# M4-IMP-002B — Mobile Work Hub Top Access Production Verification Baseline

## 1. Purpose

- Formalize the production release evidence for `22c8360e43c82913c23c281277f64f853bfac6a2`.
- Record the stable production baseline for Mobile Work Hub top access.
- Preserve the release evidence without changing runtime behavior or expanding product scope.

This slice is docs-only.

It does not modify application code, templates, static assets, tests, API behavior, schema, permissions, workflow behavior, or write behavior.

## 2. Production Baseline

- Production baseline commit:
  - `22c8360e43c82913c23c281277f64f853bfac6a2`
  - `Add mobile Work Hub top access`
- Baseline slice:
  - `M4-IMP-002A — Mobile Work Hub Top Access Baseline`
- Branch alignment after release:
  - `main` / `origin/main`: `22c8360`
  - `develop` / `origin/develop`: `22c8360`
- Production merge:
  - fast-forward PASS
  - no merge commit created
- Reviewed implementation diff was limited to three approved files:
  - `templates/sheet.html`
  - `static/styles.css`
  - `tests/smoke_test.py`
- Render production service:
  - `handover-system`

## 3. Deploy Evidence

The Render production deployment for `22c8360` completed successfully:

- Render live commit: `22c8360`
- build successful
- service live
- Gunicorn started normally
- one worker boot observed
- `0` Traceback occurrences
- `0` ERROR occurrences
- `0` worker exit occurrences
- `0` worker timeout occurrences
- no restart loop observed

## 4. Runtime Health

Public unauthenticated runtime verification completed with the expected results:

- `GET /` -> `302 /login`
- `GET /login` -> `200`
- `GET /sheet` -> `302 /login`

Stability verification:

- `/login` returned `200` for 20 consecutive checks
- stability result: `20/20 = 200`
- `502` responses observed: `0`

## 5. Production Release Markers

Production release verification confirmed the expected top-access markers:

- anchor destination: `href="#sheet-work-hub-overview"`
- one unique `sheet-work-hub-overview` target ID
- one existing Work Hub shell
- one existing Management Insight container
- one existing Work Hub cards container
- one existing Work Hub focus sections container
- mobile breakpoint marker: `@media (max-width: 760px)`
- mobile touch target minimum: `44px`
- target `scroll-margin`
- target `:target` landing marker
- target `:focus-visible` marker
- production `styles.css` `Last-Modified`:
  - `Fri, 10 Jul 2026 12:14:11 GMT`

The top-access anchor and target reuse the existing Work Hub and Management Insight shell. No shell, summary, cards, or focus container was duplicated or moved.

## 6. Regression Evidence

Regression verification completed successfully:

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `node --check static/app.js` - PASS
- Vendor Work Entry mobile quick-entry regression PASS
- M3 Unit Report regression PASS
- M3 Floor Report regression PASS
- `static/app.js` remained unchanged from the parent baseline
- Work Hub and Management Insight API dependency sets remained unchanged
- existing readonly drilldown mappings and row/focus guardrails remained unchanged
- no API, schema, permission, workflow, or write contract change
- no new fetch, storage, URL routing, history manipulation, or mutation helper

The smoke suite also confirmed:

- anchor and target values match exactly
- target ID remains unique
- Work Hub shell, Management Insight, cards, and focus containers remain unique
- mobile CSS remains scoped to `.sheet-page`
- the top-access control remains hidden by default on desktop
- the top-access navigation has no JavaScript dependency
- existing click, Enter, and Space drilldown behavior remains preserved
- Vendor Quick-Entry and M3 report styles remain unaffected

## 7. Verification Boundary

- Public production checks verified deployment state, unauthenticated route behavior, runtime stability, production CSS markers, and the stylesheet modification timestamp.
- The protected `/sheet` page was not rendered with production credentials in this verification environment.
- Protected template markers, container counts, API boundaries, and drilldown behavior were verified through the Render live commit source baseline and the complete smoke regression suite.
- No production credentials were used, requested, or inferred.

## 8. Product Classification

- This slice is a readonly mobile navigation improvement only.
- It adds no new business workflow or business-state derivation.
- It does not duplicate the existing Work Hub or Management Insight shell.
- It does not change API, schema, permission, workflow, or write behavior.
- Desktop layout and spacing remain preserved.
- Existing grid, sticky column, write control, overflow, data source, and drilldown behavior remain preserved.

## 9. Final Decision

- `M4-IMP-002A` is production-verified at commit `22c8360e43c82913c23c281277f64f853bfac6a2`.
- `22c8360` is the stable production baseline for Mobile Work Hub top access.
- This document records release evidence only and introduces no runtime or contract change.
