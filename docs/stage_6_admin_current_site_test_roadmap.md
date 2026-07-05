# Stage 6 Admin Current-Site Test Roadmap

## 1. Baseline Source

- Source baseline: `591755d`
  - `Merge vendor work entry stage 5 API baseline`
- Stage 6 planning branch family:
  - `stage-6-admin-current-site-planning`

This document consolidates the current Stage 6 docs-only audits into a tests-only roadmap for admin current-site aware content actions. It does not change runtime behavior, tests, schema, or business logic.

## 2. Completed Stage 6 Docs-Only Audit

Current Stage 6 planning already includes:

- `1ce1578` — `docs/stage_6_admin_current_site_content_actions_inventory.md`
- `9aaea7f` — `docs/stage_6_admin_current_site_authorization_audit.md`

Together, these documents already inventory:

- admin content-action route family under `/admin/table`
- current-site-aware actions already present
- admin-only and current-site-aware authorization flow
- current-site validation chain
- current site / target sheet / target entity isolation pattern
- existing smoke coverage for sheet and task actions
- remaining narrower review targets

## 3. Stage 6 Goal

Stage 6 is not runtime redesign work. The goal is:

- freeze the admin current-site aware content-action contract through the smallest possible tests-only guardrails
- verify that current-site session state remains a real write boundary for admin content mutations
- extend coverage incrementally without broadening into unrelated admin or write-path redesign

## 4. Recommended Tests-Only Implementation Slices

Current candidate slices, ordered by boundedness and likely signal:

1. extra-field current-site guardrail
2. floor current-site guardrail
3. unit current-site guardrail
4. default save-path current-site guardrail
5. optional relationship review for `/api/reset-sheet`, only if still needed after the above

These are candidate slices only. This roadmap does not authorize implementation by itself.

## 5. Minimal Scope Per Slice

### Slice 1: Extra-field current-site guardrail

- minimal scope:
  - add or delete one extra-field under same-site admin session
  - verify same-site success
  - verify cross-site block or missing-current-site block
- do not:
  - redesign extra-field behavior
  - mix in floor/unit coverage
  - touch runtime helper logic

### Slice 2: Floor current-site guardrail

- minimal scope:
  - add or delete one floor under same-site admin session
  - verify cross-site block
- do not:
  - mix in unit behavior
  - reopen task/sheet coverage

### Slice 3: Unit current-site guardrail

- minimal scope:
  - add or delete one unit under same-site admin session
  - verify cross-site block
- do not:
  - mix in floor coverage if avoidable
  - expand into broader save behavior

### Slice 4: Default save-path current-site guardrail

- minimal scope:
  - verify broad save path is blocked when `current_site_id` is missing
  - or blocked when selected target sheet is outside current site
- do not:
  - freeze all settings/content payload behavior
  - expand into template or UI concerns

### Slice 5: `/api/reset-sheet` relationship review

- minimal scope:
  - review-only unless a concrete gap remains
- do not:
  - pull `/api/reset-sheet` into Stage 6 implementation automatically

## 6. Recommended Smoke Guardrail Order

Recommended order from lowest risk to higher coupling:

1. extra-field current-site guardrail
   - smallest bounded content object after task/sheet

2. floor current-site guardrail
   - similar target-resolution pattern, limited blast radius

3. unit current-site guardrail
   - slightly more coupled because unit actions touch related rows

4. default save-path current-site guardrail
   - highest coupling within `/admin/table`
   - should wait until simpler object-specific actions are frozen

5. `/api/reset-sheet` follow-up review
   - only if still necessary after the core `/admin/table` family is frozen

## 7. Coverage Goals

Stage 6 tests-only work should aim to make the following explicit:

### Authorization coverage goals

- admin-only access remains required
- content mutation never relies on admin role alone
- current-site-aware helper gate remains active for admin actions

### Current-site coverage goals

- missing `current_site_id` blocks content mutation
- current-site session must be valid and active
- same-site action succeeds only when target belongs to current site

### Site-isolation coverage goals

- cross-site target mutation is blocked
- target resolution must remain tied to persisted sheet/site lineage
- delete/mutate flows must not trust only submitted action intent

## 8. Freeze Conditions

Stage 6 can be considered ready for freeze review when all of the following are true:

- no runtime files were changed
- no schema or migration work was introduced
- added tests remain route-specific and tests-only
- object-specific current-site guardrails cover the remaining meaningful `/admin/table` content actions
- the default save path either has a dedicated guardrail or is explicitly judged safe to inherit existing guarantees
- no slice broadens into unrelated admin domains such as `/admin/users`

## 9. Future Implementation Boundaries

The following are future implementation topics and are explicitly out of scope for this roadmap:

- changing `app.py`
- changing templates
- changing schema or migration
- changing admin helper semantics
- broad admin UX redesign
- unrelated write/runtime consolidation work

## 10. Roadmap Discipline

Future Stage 6 implementation should follow these rules:

- one tests-only slice at a time
- one content-action family per slice whenever possible
- keep each slice scoped to one contract class:
  - current-site boundary
  - cross-site block
  - same-site success
- do not reopen already covered sheet/task actions unless a real regression gap appears
- do not mix Stage 6 with broader product redesign

## 11. Next-Step Boundary

The next safe move after this roadmap should be exactly one of:

- a Stage 6 planning review confirming whether the roadmap is sufficient
- or one single tests-only guardrail implementation chosen from this roadmap

Do not:

- start runtime implementation from this document
- merge multiple content-action families into one slice
- expand into unrelated admin or write domains
