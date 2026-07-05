# Product OS v1.0 (M1) Capability Inventory

## 1. Baseline Source

- Source baseline:
  - `06b747f`
  - `Merge architecture foundation v1 baseline`
- Planning branch:
  - `product-os-v1-m1-planning`

This document is the first Product OS v1.0 capability inventory. It translates the completed Architecture Foundation into a product-capability view and defines the initial M1 planning boundary.

This is a docs-only planning artifact. It does not change runtime behavior, tests, schema, migrations, routes, or business logic.

## 2. Product OS v1.0 Context

Architecture Foundation v1.0 is now treated as complete and ready. Product OS v1.0 (M1) begins from that frozen platform baseline.

Product OS v1.0 is responsible for turning the already-frozen foundation into a controlled product capability program:

- product-facing capability mapping
- bounded implementation sequencing
- alignment between route families and operator workflows
- controlled evolution from frozen platform guarantees into product-level behavior

Product OS v1.0 must not redefine foundation rules that have already been frozen.

## 3. Core Product OS v1.0 Capability Already Available

The following product-relevant capabilities already exist because they were established by earlier stages and now inherit the Architecture Foundation v1.0 baseline.

### Site-aware operational context

Current product capability:

- current-site awareness exists as a real session and authorization boundary
- route behavior already distinguishes valid site context from missing or stale site context
- both read and write surfaces already respect current-site-aware behavior in the covered paths

Product value:

- product workflows can safely depend on site-scoped state
- site selection is not only UI state; it is an enforced application boundary

### Deterministic read surfaces

Current product capability:

- key read APIs already provide deterministic success and error contracts
- empty-result behavior is already stabilized on covered routes
- response shape and error messages are already guardrailed on covered read surfaces

Product value:

- product-level dashboards and operational read flows can rely on stable contracts
- future product modules can reuse covered read patterns with lower uncertainty

### Site-aware write isolation

Current product capability:

- write-path strategy is already bounded by explicit site/sheet isolation rules
- write isolation is already demonstrated on frozen single-path families
- current write runtime boundary is explicit and stable

Product value:

- future product implementation can extend write behavior incrementally without prematurely changing the write foundation

### Vendor bounded operating surface

Current product capability:

- vendor read routes are already bounded
- vendor write route family is already baseline-backed
- vendor preflight, scope, and profile surfaces are already inventoried and partially guardrailed
- vendor and internal identities are already separated in covered paths

Product value:

- vendor-facing operations already have a stable minimum platform
- vendor capability can be expanded as product work without first reopening foundation concerns

### Admin current-site aware content mutation

Current product capability:

- admin content actions are no longer assumed to be global
- admin mutation depends on current-site-aware boundaries in covered paths
- representative smoke guardrails already prove missing-site non-mutation behavior

Product value:

- admin operational features can be extended from a bounded site-aware baseline

## 4. Capability Mapping To Completed Stages

### Stage 1 to Stage 2

Contribution to Product OS:

- early system stabilization
- initial bounded iteration model
- pre-foundation hardening that enabled later freeze-driven work

### Stage 3B

Contribution to Product OS:

- deterministic read contract baseline
- read-path route confidence for crew and vendor-facing read surfaces

Primary capability outcome:

- read-side product trust layer

### Stage 4

Contribution to Product OS:

- explicit write-isolation operating boundary
- frozen-path rollout model for write-path evolution

Primary capability outcome:

- safe product-write expansion strategy

### Stage 4 User Site Permissions path

Contribution to Product OS:

- frozen access-control write path under `/admin/users`

Primary capability outcome:

- stable site-permission management foundation

### Stage 4A and Stage 4B

Contribution to Product OS:

- vendor work entry write smoke baseline
- vendor work entry read smoke baseline

Primary capability outcome:

- bounded vendor operations family

### Stage 5

Contribution to Product OS:

- vendor work entry API-family inventory

Primary capability outcome:

- unified capability map for vendor work entry APIs

### Stage 6

Contribution to Product OS:

- admin current-site aware content-action planning and smoke baseline

Primary capability outcome:

- bounded admin site-aware content mutation baseline

### Stage 7

Contribution to Product OS:

- Architecture Foundation v1.0 completion
- final foundation inventory and gap review

Primary capability outcome:

- Product OS can now plan from a confirmed platform baseline instead of from provisional route-level work

## 5. Existing Smoke Baseline, API Baseline, And Foundation Mapping

### Smoke Baselines

Current Product OS inherits these smoke-backed families:

- Stage 3B read-contract smoke family
- user site permissions smoke guardrail family
- vendor work entry Stage 4A write smoke family
- vendor work entry Stage 4B read smoke family
- admin current-site smoke family

### API Baselines

Current Product OS inherits:

- vendor work entry Stage 5 API baseline

### Architecture Foundation Mapping

Product OS v1.0 M1 depends on:

- deterministic contracts
- current-site awareness
- authorization correctness
- site isolation correctness
- bounded vendor/internal surface separation
- stable SQLite-primary write boundary

These are not optional product features. They are the platform assumptions Product OS is allowed to build upon.

## 6. Product OS v1.0 Capability Boundary

Product OS v1.0 should include:

- product-level sequencing of capabilities already backed by the frozen foundation
- bounded implementation slices that preserve current-site, authorization, and isolation guarantees
- selective extension of admin, vendor, and operational APIs where the platform contract is already trusted
- roadmap-driven implementation from a stable baseline rather than exploratory foundation work

Product OS v1.0 should not include:

- schema redesign
- migration rollout
- broad write-runtime migration
- governance redesign
- redefinition of frozen foundation boundaries
- uncontrolled broad feature expansion

## 7. Controlled M1 Implementation Scope

M1 should be limited to product work that can be safely built on the current foundation without reopening platform assumptions.

Examples of acceptable M1 implementation scope:

- bounded feature increments built on current-site aware flows
- product slices that reuse deterministic read contracts
- bounded admin operational improvements under existing site-aware rules
- bounded vendor workflow improvements inside already-inventoried route families

Examples of unacceptable M1 scope:

- schema-affecting redesign
- cross-cutting auth redesign
- enabling new write runtime backends
- broad replacement of route helpers or database foundation
- reopening frozen baselines without explicit review

## 8. Deferred Capability After M1

The following capability areas are explicitly deferred beyond M1 and are not part of this planning slice:

### Post-M1.x platform evolution

- PostgreSQL-primary write migration
- `USE_SQLALCHEMY_WRITES=true`
- broader dual-write rollout
- database foundation replacement

### Post-M1.x product expansion

- new major workflow domains not yet inventoried
- broad UI/system redesign
- governance redesign
- large cross-module operating model changes

### Post-M1.x coverage deepening

- route families not yet selected into the M1 roadmap
- broader admin mutation coverage beyond bounded representative slices
- capability expansion that would require reopening Architecture Foundation assumptions

## 9. M1 Planning Principles

All Product OS v1.0 work should continue to follow the same operating rules that made Stage 3B through Stage 7 successful:

- evolution before revolution
- docs-only planning before implementation
- bounded slice selection
- smoke or contract guardrail first when appropriate
- merge/readiness/production verification discipline
- no hidden schema or runtime migration scope creep

## 10. Immediate Next-Step Boundary

After this capability inventory, the next safe step should be one of:

- Product OS v1.0 capability planning review
- a bounded M1 gap review
- selection of the first controlled M1 implementation family

Do not use this document to:

- start broad Product OS implementation immediately
- reopen Architecture Foundation v1.0
- start schema or migration work
- introduce new runtime behavior without a bounded M1 planning step
