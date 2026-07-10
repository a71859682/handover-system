# M4-IMP-001B — Vendor Mobile Quick-Entry Production Verification Baseline

## 1. Purpose

- Formalize the production release evidence for `ce97b6e995b0e57b7bdba485fe25b47086e1a74b`.
- Record the stable production baseline for Vendor Work Entry mobile quick-entry navigation.
- Preserve the release evidence without changing runtime behavior or expanding product scope.

This slice is docs-only.

It does not modify application code, templates, static assets, tests, API behavior, schema, permissions, workflow behavior, or write behavior.

## 2. Production Baseline

- Production baseline commit:
  - `ce97b6e995b0e57b7bdba485fe25b47086e1a74b`
  - `Add vendor mobile quick-entry navigation`
- Baseline slice:
  - `M4-IMP-001A — Vendor Work Entry Mobile Quick-Entry Navigation Baseline`
- Branch alignment after release:
  - `main` / `origin/main`: `ce97b6e`
  - `develop` / `origin/develop`: `ce97b6e`
- Production merge:
  - fast-forward PASS
  - no merge commit created
- Reviewed implementation diff was limited to three approved files:
  - `templates/vendor_work_entry.html`
  - `static/styles.css`
  - `tests/smoke_test.py`
- Render production service:
  - `handover-system`

## 3. Deploy Evidence

The Render production deployment for `ce97b6e` completed successfully:

- Render live commit: `ce97b6e`
- build successful
- service live
- Gunicorn started normally
- one worker boot observed
- `0` Traceback occurrences
- `0` ERROR occurrences
- no restart loop observed

## 4. Runtime Health

Public unauthenticated runtime verification completed with the expected results:

- `GET /` -> `302 /login`
- `GET /login` -> `200`
- `GET /vendor/work-entry` -> `302 /vendor/login`

Stability verification:

- `/login` returned `200` for 20 consecutive checks
- stability result: `20/20 = 200`
- no intermittent non-`200` response was observed during the stability check

## 5. Production Release Markers

Production release verification confirmed the expected quick-entry markers:

- mobile quick-entry block
- create-mode action copy: `開始填報`
- selected/edit-mode action copy: `繼續填報`
- anchor destination: `#vendor-work-entry-draft-form-target`
- one unique draft target
- mobile touch target minimum: `44px`
- draft target `scroll-margin`
- draft target `:target` landing marker
- one existing draft form
- one existing submit button
- submit URL remains `/api/vendor-work-entry`
- submit method remains `POST`
- production `styles.css` `Last-Modified`:
  - `Fri, 10 Jul 2026 11:05:49 GMT`

## 6. Regression Evidence

Regression verification completed successfully:

- `python -m compileall app.py tests` - PASS
- `python tests/smoke_test.py` - PASS
- `node --check static/app.js` - PASS
- M3 Unit Report regression PASS
- M3 Floor Report regression PASS
- no API, schema, permission, workflow, or write behavior change
- no new fetch, storage, URL routing, or history manipulation was added to quick-entry navigation

The smoke suite also confirmed:

- create and selected/edit copy remain mutually exclusive
- quick-entry context reuses the existing business date and vendor context
- anchor and target values match exactly
- target, form, and submit remain unique
- existing field names remain unchanged
- hidden trusted context markers remain unchanged
- validation markers and existing `data-testid` values remain preserved
- mobile CSS remains scoped to `.vendor-work-entry-page`
- desktop and M3 report styles remain unaffected

## 7. Verification Boundary

- Public production checks verified deployment state, unauthenticated route behavior, runtime stability, production CSS markers, and the stylesheet modification timestamp.
- The protected Vendor Work Entry page was not rendered with production credentials in this verification environment.
- Create/edit rendered states, template markers, form counts, and POST metadata were verified through the Render live commit source baseline and the complete smoke regression suite.
- No production credentials were used, requested, or inferred.

## 8. Product Classification

- This slice is a mobile navigation improvement only.
- It adds no new business workflow or business-state derivation.
- It does not duplicate the existing form or submit path.
- It does not change create/update semantics, trusted context, validation, or persistence behavior.
- Desktop layout and spacing remain preserved.
- Existing summary, readiness, history, and M3 report content remain preserved.

## 9. Final Decision

- `M4-IMP-001A` is production-verified at commit `ce97b6e995b0e57b7bdba485fe25b47086e1a74b`.
- `ce97b6e` is the stable production baseline for Vendor Work Entry mobile quick-entry navigation.
- This document records release evidence only and introduces no runtime or contract change.
