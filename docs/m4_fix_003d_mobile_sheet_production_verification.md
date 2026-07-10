# M4-FIX-003D — Mobile Sheet Production Verification Baseline

## 1. Purpose

- Formalize the production release evidence for the complete `M4-FIX-003` mobile sheet fix chain.
- Record the deployed production baseline at `ae13b61c7c4c90461d818c4839e2f915c4f25074`.
- Preserve the distinction between completed automated/runtime verification and pending authenticated production device verification.

This slice is docs-only.

It does not modify application code, templates, static assets, tests, API behavior, schema, permissions, workflow behavior, or write behavior.

## 2. Release Baseline

- Production commit:
  - `ae13b61c7c4c90461d818c4839e2f915c4f25074`
  - `Fix Android landscape footer unfreeze`
- Branch alignment after release:
  - `main` / `origin/main`: `ae13b61`
  - `develop` / `origin/develop`: `ae13b61`
- Production integration:
  - `main` fast-forwarded from `develop`
  - fast-forward PASS
  - no merge commit created
- Production commit chain:
  - `f9c1b7b` — `Document mobile Work Hub top access production verification baseline`
  - `2167cae` — `Fix mobile sheet frozen regions`
  - `6b99cf8` — `Improve mobile sheet viewport fit`
  - `ae13b61` — `Fix Android landscape footer unfreeze`
- Reviewed production diff scope:
  - `docs/m4_imp_002b_mobile_work_hub_top_access_production_verification.md`
  - `templates/sheet.html`
  - `static/styles.css`
  - `tests/smoke_test.py`
- Render production service:
  - `handover-system`

## 3. Production Deploy Evidence

The Render production deployment for `ae13b61` completed successfully:

- Render live commit: `ae13b61`
- build successful
- service live
- Gunicorn started normally
- one worker boot observed
- `0` Traceback occurrences
- `0` ERROR occurrences
- `0` timeout occurrences
- `0` worker exit occurrences
- no restart loop observed
- production `styles.css` `Last-Modified`:
  - `Fri, 10 Jul 2026 14:48:15 GMT`

## 4. Runtime Evidence

Public unauthenticated production verification completed with the expected results:

- `GET /` -> `302 /login`
- `GET /login` -> `200`
- `GET /sheet` -> `302 /login`

Stability verification:

- `/login` returned `200` for 20 consecutive checks
- stability result: `20/20 = 200`
- intermittent non-`200` responses observed: `0`

## 5. Released Mobile Behavior

### Portrait

- the second `戶數` column is hidden across the table header, body, and footer
- the hidden count cells have zero width, minimum width, maximum width, padding, and border
- the remaining unit sticky offset is `92px`
- the three footer rows use explicit `meta -> count -> unit -> tasks -> extra fields` logical-cell ordering
- footer summary alignment no longer depends on a spanning or collapsed column
- the footer remains sticky in portrait
- the matrix uses dynamic viewport fitting with a `100vh` fallback and `100dvh` override
- the portrait viewport offset is `clamp(8rem, 24dvh, 12rem)`

### Landscape

- the original iPhone boundary remains `max-width: 900px` with `orientation: landscape`
- the Android-compatible boundary uses:
  - `orientation: landscape`
  - `max-height: 600px`
  - `hover: none`
  - `pointer: coarse`
- footer cells use `position: static`, `top: auto`, and `bottom: auto`
- all three footer rows remain present and reachable through internal vertical scrolling
- the matrix uses dynamic viewport fitting with a `100vh` fallback and `100dvh` override
- the landscape viewport offset is `clamp(3rem, 16dvh, 6rem)`
- viewport-relative minimum and maximum heights remain enabled
- `overflow-x: auto` and `overflow-y: auto` remain enabled

### Desktop

- the `戶數` column remains visible
- the sticky footer remains enabled
- the matrix height remains `calc(100vh - 170px)`

## 6. Technical Safety Boundary

- no `app.py` change
- no `static/app.js` change
- no API contract change
- no schema or migration change
- no permission change
- no workflow or write contract change
- no Work Hub or Management Insight data-source change
- no Vendor Work Entry change
- no Unit Report or Floor Report change
- no JavaScript user-agent or device detection
- `visibility: collapse` is absent
- no partial `colgroup` or footer `colspan="3"` dependency remains
- explicit logical footer cells replace the rejected spanning/collapsed-column approach

## 7. Verification Status

### Dev Device Verification — PASS

- Android portrait: PASS
- Android landscape: PASS
- small iPhone portrait: PASS
- small iPhone landscape: PASS
- large iPhone portrait: PASS
- large iPhone landscape: PASS
- Desktop: PASS

### Production Automated and Runtime Verification — PASS

- production fast-forward and push: PASS
- Render deploy and logs: PASS
- public runtime health: PASS
- `/login` stability: PASS
- production CSS release markers: PASS
- `python -m compileall app.py tests`: PASS
- `python tests/smoke_test.py`: PASS
- `node --check static/app.js`: PASS
- `git diff --check`: PASS

### Production Authenticated Device Verification — PENDING

The production environment was not tested with an authenticated production session on physical mobile devices in this verification environment. No production credentials were used, requested, or inferred.

Pending production checks:

- Android landscape
- iPhone portrait and landscape
- Desktop
- floor rows before and after expansion
- footer summary alignment
- footer reachability through internal scrolling
- absence of unexpected body/matrix double scrolling

## 8. Freeze Gate

The `M4-FIX-003` series is deployed and recorded as a production baseline, but it must not be marked as fully frozen until all pending authenticated production device checks pass.

Freeze requires confirmation of:

- Android landscape behavior
- iPhone portrait and landscape behavior
- Desktop behavior
- floor expansion behavior
- footer summary alignment
- footer scroll reachability
- no double-scroll regression

If any production device check fails, the series remains unfrozen and requires a controlled follow-up fix before freeze classification.

## 9. Final Classification

- Production baseline deployed: YES
- Automated/runtime production verification: PASS
- Authenticated production device verification: PENDING
- `M4-FIX-003` freeze status: NOT YET FROZEN
- This document records verification evidence only and introduces no runtime or contract change.
