# P-2D Implementation Roadmap

## 1. Objective

This document converts the completed planning work from:

- P-2A Permission Contract Freeze
- P-2B Vendor Identity Planning
- P-2C Login Flow Planning

into an executable implementation roadmap.

P-2D is still planning-only.

- no code change
- no runtime change
- no schema change
- no production change

The purpose is to define a staged path from planning artifacts to safe implementation slices.

## 2. Milestones

### Stage 1: Vendor Authentication Foundation

#### Goal

- establish the minimal runtime foundation for vendor identity
- introduce a vendor-specific authentication entry without destabilizing internal login
- preserve current internal auth/session behavior

#### Expected files

- `app.py`
- `templates/login.html` or a new vendor login template if later approved
- `tests/smoke_test.py`
- new readiness / inventory tooling under `tools/`

#### Risk level

- Medium

#### Runtime impact

- introduces new auth surface
- should not alter internal login behavior

#### Rollback complexity

- Low to Medium
- expected to be code-only if introduced cleanly

#### Validation plan

- local smoke coverage
- staging authenticated vendor login test
- internal login regression verification
- production unauthenticated health checks before any rollout

### Stage 2: Vendor Session Implementation

#### Goal

- implement vendor-specific session namespace
- avoid reusing internal user session keys
- formalize `identity_type` behavior

#### Expected files

- `app.py`
- `tests/smoke_test.py`
- vendor session readiness checker in `tools/`

#### Risk level

- High

#### Runtime impact

- affects request identity interpretation
- interacts with login/logout and session lifecycle

#### Rollback complexity

- Medium
- code rollback should be sufficient if no schema changes are introduced

#### Validation plan

- staging authenticated session tests
- logout/session-clearing verification
- mixed internal/vendor login regression checks

### Stage 3: Vendor Authorization

#### Goal

- bind vendor session identity to explicit authorization rules
- define what vendor identities can read and write
- align vendor scope with existing site/sheet isolation

#### Expected files

- `app.py`
- `tests/smoke_test.py`
- readiness checker(s) in `tools/`

#### Risk level

- High

#### Runtime impact

- touches authorization pipeline
- directly affects vendor data visibility and mutation behavior

#### Rollback complexity

- Medium

#### Validation plan

- staging vendor same-scope allow checks
- staging cross-scope reject checks
- regression checks for internal read/write isolation

### Stage 4: Vendor UI / Login

#### Goal

- expose vendor-facing login UX and any vendor-facing landing flow
- keep internal UI stable

#### Expected files

- `app.py`
- `templates/*`
- `tests/smoke_test.py`

#### Risk level

- Medium

#### Runtime impact

- visible auth-entry change
- potential user-facing confusion if not clearly separated

#### Rollback complexity

- Low to Medium

#### Validation plan

- staging manual verification
- template/render regression checks
- production post-deploy health and page-render checks

### Stage 5: Integration / Migration

#### Goal

- consolidate vendor auth, vendor session, and vendor authorization into a stable integrated release path
- decide whether any follow-up cleanup, routing cleanup, or contract cleanup is required

#### Expected files

- `app.py`
- `templates/*`
- `tests/smoke_test.py`
- `tools/*`

#### Risk level

- High

#### Runtime impact

- integration-stage regressions are more likely than isolated earlier stages

#### Rollback complexity

- Medium

#### Validation plan

- full local validation
- staging release checklist
- authenticated manual verification
- production post-deploy verification

## 3. Dependency Graph

### Must happen first

- Stage 1 before all other implementation stages
- Stage 2 after Stage 1
- Stage 3 after Stage 2

### Usually follows later

- Stage 4 should follow Stage 1 and Stage 2 at minimum
- Stage 5 should follow Stages 1 through 4

### Parallel candidates

- parts of Stage 4 planning can proceed while Stage 3 implementation is underway
- readiness tooling and validation tooling may be prepared in parallel with each stage

### Sequentially required path

Recommended strict dependency chain:

Stage 1  
→ Stage 2  
→ Stage 3  
→ Stage 4  
→ Stage 5

## 4. Risk Matrix

### Low

- docs and readiness-only tooling
- isolated template copy or vendor-facing UI polish after auth is stable

### Medium

- login route expansion
- logout branching
- vendor UI entry design
- non-destructive routing additions

### High

- session namespace changes
- authorization model introduction
- current-site interaction decisions
- vendor API scope enforcement
- any change that mixes internal and vendor auth in the same request path

### Topic-specific notes

#### Login

- Risk: High if internal and vendor login are combined
- Risk: Medium if vendor route is separate

#### Session

- Risk: High
- session ambiguity can create silent authorization bugs

#### Authorization

- Risk: High
- mistakes affect both visibility and mutation safety

#### Current site

- Risk: Medium to High
- vendor identity should not be coupled to internal current-site logic without explicit design

#### Vendor APIs

- Risk: High
- they already write business data and must not bypass existing isolation guarantees

## 5. Rollout Strategy

### Feature flag

- recommended if vendor auth is introduced incrementally
- especially useful for hiding vendor login entrypoints before full authorization is ready

### Staging verification

- required before any production-facing rollout
- staging should use safe vendor test accounts and seeded vendor data
- authenticated vendor manual verification is mandatory before release closure

### Production verification

- deploy health checks
- deploy log checks
- authenticated vendor verification when safe credentials are available
- regression checks for internal login, selector, admin, read isolation, and write isolation

### Rollback strategy

- prefer small, single-purpose commits per implementation slice
- rollback should remain code-only whenever possible
- avoid schema dependence in early slices

## 6. Recommended Execution Order

### Recommended order

1. Vendor authentication foundation
2. Vendor session implementation
3. Vendor authorization
4. Vendor UI / login
5. Integration / migration

### Why this order is recommended

- authentication foundation creates the smallest explicit entrypoint first
- session implementation must be stable before authorization can be trusted
- authorization should be defined before broad vendor-facing UI is exposed
- UI should come after the core identity and scope contracts are stable
- integration should be the final consolidation step, not the starting point

### Additional execution guidance

- keep each stage as small as possible
- prefer code-only slices
- require staging verification between risky stages
- do not combine login, session, and authorization changes in one large release
