# VWE-PROD-011B - Persistence Schema Evaluation

## 1. Purpose

This document defines the docs-only schema evaluation baseline for Persistent Formal Approval.

Its purpose is to compare the two primary persistence-model directions for formal approval state and produce a product recommendation before any schema implementation begins.

This slice does not modify schema, migration behavior, application code, static assets, templates, tests, API behavior, permission behavior, workflow behavior, or write behavior.

## 2. Candidate A

### Extend `vendor_work_entries`

The first candidate is to extend `vendor_work_entries` directly with formal-approval fields.

Possible future examples:

- formal approval state
- formal approval actor
- formal approval timestamp

### Advantages

- keeps approval state on the same row as the existing entry identity
- simplifies single-row lookup for crew read surfaces
- avoids introducing a second persistence object in the first implementation phase
- can reduce join complexity for simple read contracts

### Disadvantages

- continues growing `vendor_work_entries` into a large mixed-responsibility lifecycle table
- mixes vendor-authored state and crew operational approval state on the same record
- can become harder to evolve if future approval history or event-level audit semantics are needed
- can push future override / scheduling / approval policy concerns into the entry table even when those concerns are conceptually separate

### Best-fit situations

Candidate A fits best when:

- the approval model is expected to stay simple and mostly single-state
- there is low expectation of future approval history or multiple approval events
- product priority favors minimum relational complexity over long-term domain separation

## 3. Candidate B

### Separate `formal_approvals` table

The second candidate is to introduce a separate `formal_approvals` persistence model that references one `Vendor Work Entry`.

The first product version would still preserve a one-entry-to-one-approval rule, but the persistence model would treat approval as its own domain object.

### Advantages

- keeps formal approval separate from vendor entry authoring
- models approval as a first-class operational object rather than an extra flag on the entry row
- scales better toward future policy features such as override, audit, scheduling dependency, and richer approval lifecycle
- creates a cleaner foundation for future multiple approval events or approval history if product scope expands later

### Disadvantages

- adds schema and relational complexity earlier
- requires join logic or read-side projection logic for crew read contracts
- increases implementation overhead for the first persistent release
- requires explicit uniqueness and lifecycle rules so that one-entry-to-one-approval behavior remains deterministic

### Best-fit situations

Candidate B fits best when:

- approval is expected to become a long-lived product concept
- future scheduling and operational products will depend on durable approval state
- policy, audit, or override evolution is likely
- long-term domain clarity is more important than minimizing the first persistence step

## 4. Product Comparison

### Data consistency

- Candidate A
  - row-local consistency is simpler because the approval state sits on the entry row
  - fewer moving parts for a simple write path

- Candidate B
  - consistency remains strong if one-entry-to-one-approval uniqueness is enforced
  - requires clearer cross-table integrity rules

Assessment:

- Candidate A is simpler for first-write consistency
- Candidate B is still acceptable if uniqueness is explicitly designed

### Extensibility

- Candidate A
  - less flexible as approval semantics expand
  - future history or multi-event approval can become awkward

- Candidate B
  - more extensible for future product evolution
  - cleaner path toward richer approval semantics

Assessment:

- Candidate B is stronger

### Audit capability

- Candidate A
  - limited unless the entry row accumulates more audit-style fields
  - tends to compress the current state but not the approval lifecycle

- Candidate B
  - aligns more naturally with future approval records and audit-oriented growth

Assessment:

- Candidate B is stronger

### Override capability

- Candidate A
  - override policy would likely create more entry-row fields and conditional semantics

- Candidate B
  - override can remain adjacent to, or layered on top of, the approval domain more cleanly

Assessment:

- Candidate B is stronger

### Scheduling Engine compatibility

- Candidate A
  - can expose a simple approved/not-approved state quickly
  - but downstream scheduling logic may become tightly coupled to entry-row lifecycle fields

- Candidate B
  - provides a clearer durable operational boundary for future scheduling dependencies

Assessment:

- Candidate B is stronger

### Future repeated approval flows

- Candidate A
  - weak fit for multiple approval events or approval history

- Candidate B
  - adaptable if the product later needs repeated approval, versioning, or approval-event history

Assessment:

- Candidate B is much stronger

### Maintenance cost

- Candidate A
  - lower initial maintenance cost
  - higher long-term risk of table overloading

- Candidate B
  - higher initial maintenance cost
  - lower long-term conceptual drift if approval becomes an important product line

Assessment:

- Candidate A is cheaper initially
- Candidate B is cleaner long term

### Migration complexity

- Candidate A
  - typically simpler for a first persistence rollout
  - fewer objects to create and backfill

- Candidate B
  - more migration design work up front
  - requires separate-table rollout planning

Assessment:

- Candidate A is simpler for migration

## 5. Recommendation

The recommended first-direction baseline is:

- Candidate B: separate `formal_approvals`

### Recommendation rationale

The primary reasons are:

- formal approval is already emerging as a distinct operational product concept
- future Scheduling Engine work is more likely to depend on a durable approval object than on an overloaded entry-row flag set
- future override, audit, and richer approval semantics are easier to accommodate when approval is modeled separately
- the long-term product direction appears more operational and policy-driven than purely authoring-driven

Candidate A is still viable if product strategy changes toward a deliberately minimal and short-lived approval state.

However, based on the current roadmap, Candidate B provides the better long-term product foundation.

This document makes a product recommendation only.

It does not implement schema and does not freeze field-level design yet.

## 6. Out-of-Scope

The following are explicitly out of scope for this slice:

- schema implementation
- migration
- API
- UI
- write behavior

Also out of scope:

- permission redesign
- workflow redesign
- runtime rollout strategy
- detailed field list for the chosen schema

## 7. Proposed Next Slices

Recommended next slices:

- `011C` Persistence Schema Baseline
- `011D` Formal Approval Write Contract
- `011E` Crew Read Contract Extension
- `011F` UI Integration
- `011G` Guardrail Freeze

Suggested sequence:

1. freeze the persistence-schema direction around the recommended model
2. define the formal approval write contract
3. extend the crew read contract
4. integrate persisted approval state into crew-side UI
5. freeze the resulting guardrails before production-baseline consolidation
