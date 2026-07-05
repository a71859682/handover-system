# Product OS v1.0 (M1) Implementation Roadmap

## 1. Baseline Source

- Source baseline:
  - `215e7e1`
  - `Record product os v1 m1 capability inventory`
- Planning branch:
  - `product-os-v1-m1-planning`

This document defines a docs-only controlled implementation roadmap for Product OS v1.0 (M1). It does not change runtime behavior, tests, schema, migrations, routes, or business logic.

## 2. Roadmap Goal

The goal of this roadmap is to convert the completed Architecture Foundation v1.0 into a safe product implementation sequence.

This roadmap is designed to:

- keep implementation slices small and reversible
- preserve the frozen current-site, authorization, site-isolation, and deterministic-contract guarantees
- sequence product work from the lowest-risk modules to the highest-risk modules
- make smoke and regression strategy explicit before product implementation begins

## 3. Core Product OS v1.0 Modules

The current Product OS v1.0 (M1) capability set can be organized into the following product modules:

### Module A: Site-aware operational reads

This module includes:

- crew read surfaces
- daily summary read surfaces
- vendor-facing business preview and related readback
- deterministic read contract behavior used by operational consumers

Foundation dependency:

- Stage 3B read-contract freeze

### Module B: Site-aware admin content actions

This module includes:

- admin current-site aware content mutation
- current-site-aware `/admin/table` content actions
- representative add/delete content flows that must respect current-site boundaries

Foundation dependency:

- Stage 6 admin current-site smoke baseline

### Module C: Vendor bounded operating surface

This module includes:

- vendor profile
- vendor scope
- vendor business read preview
- vendor work entry preflight/read/write family as a bounded product subsystem

Foundation dependency:

- Stage 4A
- Stage 4B
- Stage 5

### Module D: Site permission management

This module includes:

- `user_site_permissions` write path under `/admin/users`
- site-permission lifecycle under the existing admin surface

Foundation dependency:

- Stage 4 user site permissions frozen path

### Module E: Write-path operating model

This module includes:

- the bounded write-isolation expansion strategy
- the current SQLite-primary write runtime constraint
- future write evolution sequencing, but not runtime migration itself

Foundation dependency:

- Stage 4 write isolation baseline

## 4. Recommended Implementation Order

Recommended order from lowest risk to highest risk:

1. Site permission management refinement
2. Site-aware admin content actions expansion
3. Site-aware operational reads expansion
4. Vendor bounded operating surface enhancement
5. Write-path operating model expansion

The order is intentionally conservative. It prefers modules with already-frozen boundaries, smaller blast radius, and lower runtime coupling.

## 5. Minimal Scope Per Implementation Slice

### Slice 1: Site permission management refinement

Category:

- M1 must-do candidate

Minimal scope:

- extend or harden product behavior only inside the already-frozen `user_site_permissions` path
- do not broaden into the entire `/admin/users` family
- do not mix user lifecycle redesign into site-permission work

Why low risk:

- already frozen as a single write path
- clear authorization and persistence boundary
- existing smoke and readiness evidence already exists

### Slice 2: Admin current-site content-action extension

Category:

- M1 must-do candidate

Minimal scope:

- pick one additional bounded `/admin/table` content-action family
- preserve current-site redirect/block behavior
- verify non-mutation on invalid site context

Why moderate risk:

- still bounded under a known admin route family
- reuses the same current-site boundary already proven in Stage 6

### Slice 3: Operational read enhancement on covered APIs

Category:

- M1 must-do candidate

Minimal scope:

- build product behavior only on top of already-frozen read surfaces
- do not redefine response contracts
- do not reopen Stage 3B route families

Why moderate risk:

- read-side blast radius is lower than write-side mutation
- deterministic contracts are already frozen

### Slice 4: Vendor bounded operating surface enhancement

Category:

- M1 optional candidate

Minimal scope:

- select one bounded vendor capability within the already inventoried API family
- preserve vendor/internal boundary and current contract assumptions
- avoid broadening to new vendor domains

Why higher risk:

- vendor flows touch both identity and workflow-specific behavior
- multiple route families are involved even when the slice is bounded

### Slice 5: Write-path operating model expansion

Category:

- defer to M1.x or later unless a very narrow bounded slice is justified

Minimal scope:

- route-family specific write-path improvement only
- no runtime backend migration
- no schema change
- no broad write helper redesign

Why highest risk:

- highest coupling to persistence behavior
- easiest place for hidden scope expansion

## 6. Smoke And Regression Verification Strategy

### Slice 1 Verification Strategy

Smoke strategy:

- route-specific smoke on `user_site_permissions`
- persistence verification
- duplicate prevention verification
- non-admin rejection verification

Regression strategy:

- existing smoke suite
- targeted readiness tool checks if the route family already has them

### Slice 2 Verification Strategy

Smoke strategy:

- current-site missing boundary check
- cross-site or invalid-target non-mutation check
- route-level redirect or deterministic rejection check

Regression strategy:

- `python tests/smoke_test.py`
- no unrelated admin route mutation changes

### Slice 3 Verification Strategy

Smoke strategy:

- preserve deterministic read contract
- preserve response shape where already frozen
- preserve auth-boundary behavior

Regression strategy:

- smoke suite plus covered read-path checks
- avoid changing frozen route contracts

### Slice 4 Verification Strategy

Smoke strategy:

- vendor session boundary verification
- internal session rejection verification where relevant
- success-side minimal response contract validation

Regression strategy:

- smoke suite plus vendor-specific bounded checks
- no reopening of already-frozen Stage 4A/4B guardrails

### Slice 5 Verification Strategy

Smoke strategy:

- single-path bounded verification only
- explicit non-mutation or unchanged-state checks on rejected writes

Regression strategy:

- smoke suite
- existing readiness tools if applicable
- extra review before merge because this is the highest-risk category

## 7. M1 Must-Do, Optional, And Deferred Scope

### M1 Must-Do

The following are appropriate M1 implementation categories:

- bounded site permission management refinement
- bounded admin current-site content-action expansion
- product behavior built on already-frozen operational read surfaces

These are the best fit for M1 because they extend proven foundations without requiring foundation rework.

### M1 Optional

The following can be included only if earlier M1 slices remain clean and bounded:

- one additional bounded vendor operating-surface enhancement
- one narrowly scoped read-side workflow improvement that does not reopen frozen contracts

Optional means:

- not required for M1 success
- should be skipped if it introduces broader coupling or ambiguity

### Deferred To M1.x Or Later

The following should be explicitly deferred:

- broad write runtime evolution
- schema change
- migration
- governance redesign
- broad vendor domain expansion
- broad admin workflow redesign
- multi-module orchestration expansion
- any capability requiring Architecture Foundation to be reopened

## 8. Freeze Conditions For M1

Product OS v1.0 (M1) should be considered ready for freeze when:

- every included slice has a bounded documented scope
- each included slice has an explicit smoke/regression validation strategy
- no included slice requires schema or migration work
- no included slice redefines a frozen foundation contract
- no included slice forces broad runtime redesign
- merged slices keep `main` production-ready at each step
- any optional slice is excluded if it weakens boundedness or review clarity

## 9. Definition Of Done For M1

M1 should be considered complete only when:

- selected must-do slices are implemented and verified
- smoke and regression validation pass for each merged slice
- no hidden foundation reopening has occurred
- product capability growth remains inside the documented M1 boundary
- remaining work is clearly reclassified into M1.x or later

M1 completion is not defined by quantity of features. It is defined by safe, bounded, production-ready product progression from the frozen foundation.

## 10. Next-Step Boundary

The next step after this roadmap should be one of:

- M1 planning review
- selection of the first bounded M1 implementation slice
- merge readiness review for the docs-only M1 planning baseline

Do not use this document to:

- start multiple implementation families at once
- reopen Architecture Foundation v1.0
- introduce schema or migration work
- begin broad runtime redesign
