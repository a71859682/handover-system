# Stage 7 Architecture Foundation Inventory

## 1. Baseline Source

- Source baseline: `3b43aaf`
  - `Merge admin current-site smoke baseline`
- Planning branch:
  - `stage-7-architecture-foundation-planning`

This document records the Stage 7 planning inventory for Architecture Foundation completion. It is documentation only and does not change runtime behavior, tests, schema, migrations, or business logic.

## 2. Stage 7 Goal

Stage 7 exists to consolidate the engineering foundation built across Stage 1 through Stage 6 into a final Architecture Foundation v1.0 planning baseline.

The intent is to:

- inventory foundation capabilities that are already frozen or baseline-backed
- map current-site, authorization, site isolation, vendor, and admin behavior into one foundation view
- identify which capabilities are already backed by smoke baselines or API baselines
- identify the remaining capabilities that are not yet part of Architecture Foundation v1.0
- define freeze criteria for the Architecture Foundation family before Product OS v1.0 (M1) expands further

## 3. Completed Foundation Capability Inventory

### Stage 1 to Stage 2 Foundation

The earlier foundation stages established the initial operating base for the Engineering Management System:

- baseline project hardening and incremental stabilization
- early read/write isolation direction
- initial smoke-driven development pattern
- groundwork for deterministic route behavior and bounded rollout

These stages form the pre-freeze base that later stages refined into route-specific and path-specific frozen contracts.

### Stage 3B: Cross-Domain Deterministic Contracts

Stage 3B is the read-contract foundation family.

Frozen or baseline-backed capability includes:

- deterministic read error contracts
- deterministic empty-result contracts
- happy-path top-level response shape contracts
- representative item-level response shape contracts
- route-specific auth-boundary guardrails
- read-path site isolation checks

Key covered route families:

- `/api/crew-missing`
- `/api/crew-daily-summary`
- `/vendor/business-read-preview`

Key supporting foundation:

- `tests/smoke_test.py`
- `tools/check_site_read_isolation.py`

Reference baseline:

- `docs/stage_3b_cross_domain_deterministic_contracts_freeze.md`

### Stage 4: Write Isolation Baseline Family

Stage 4 established the write-isolation planning boundary without starting runtime migration.

Foundation state established:

- SQLite remains the primary write runtime
- `USE_SQLALCHEMY_WRITES=false`
- no schema or migration changes are required for the baseline
- write-path work must proceed through single-path readiness, smoke, freeze, and production verification

Reference baseline:

- `docs/stage_4_write_isolation_baseline.md`

### Stage 4 Frozen Path: User Site Permissions

This is the first fully frozen single write path under Stage 4.

Covered capability:

- `add_site_permission` success persistence
- duplicate prevention
- `update_site_permission` role update
- `delete_site_permission` row removal
- inactive site rejection
- invalid role rejection
- non-admin blocked
- persistence and auth-boundary verification

Reference freeze:

- `docs/stage_4_user_site_permissions_freeze.md`

### Stage 4A and Stage 4B: Vendor Work Entry Smoke Baselines

Vendor Work Entry was completed as a dual-path frozen family:

- Stage 4A:
  - write smoke baseline
- Stage 4B:
  - read smoke baseline

Covered write-side capability includes:

- same-site write success
- cross-site rejection
- missing current-site rejection
- permission-removed rejection
- vendor-not-in-sheet rejection
- sheet mismatch rejection
- deterministic write-side error contracts
- happy-path success response guardrails
- DB unchanged checks for rejected paths

Covered read-side capability includes:

- `/vendor/profile` authenticated response shape
- `/vendor/scope` authenticated response shape
- `/vendor/business-read-preview` vendor-only route boundary

### Stage 5: Vendor Work Entry API Baseline

Stage 5 completed the API-family level inventory for Vendor Work Entry.

Covered foundation view includes:

- write API
- read API
- preflight API
- caller and permission boundary per route
- Stage 4A and Stage 4B coverage mapping
- distinction between completed capability, tests-only candidates, and future production implementation candidates

Reference baseline:

- `docs/stage_5_vendor_work_entry_api_inventory.md`

### Stage 6: Admin Current-Site Aware Content Actions

Stage 6 completed planning plus an initial smoke baseline for admin current-site aware content actions.

Planning coverage includes:

- admin content-action inventory
- current-site authorization audit
- tests-only roadmap

Smoke baseline currently freezes:

- `/admin/table` add-extra-field missing-current-site boundary
- `/admin/table` delete-extra-field missing-current-site boundary
- redirect to `/site-selector` when current-site context is missing
- non-mutation guarantee for covered missing-site paths

Reference planning family:

- `docs/stage_6_admin_current_site_content_actions_inventory.md`
- `docs/stage_6_admin_current_site_authorization_audit.md`
- `docs/stage_6_admin_current_site_test_roadmap.md`

## 4. Core Capability Mapping

### Current-Site

Current-site awareness is now a first-class architectural concept across both read and write baselines.

Foundation evidence includes:

- read-path missing-site rejection on crew read APIs
- write-path missing-site rejection on vendor write and admin content actions
- route-level redirect or deterministic error behavior when current-site context is absent

### Authorization

Authorization is no longer treated as a generic login check alone. The foundation now distinguishes:

- internal authenticated access
- vendor authenticated access
- admin-only mutation access
- site-scoped permission validation
- selected-site and selected-sheet validation before protected actions

### Site Isolation

Site isolation is one of the strongest frozen themes in the current foundation.

Foundation evidence includes:

- cross-site read denial
- cross-site write denial
- stale site-context denial
- sheet ownership validation
- vendor ownership validation
- user-site permission enforcement

### Vendor

Vendor capability is now split into clear bounded surfaces:

- vendor-only read surfaces
- internal-only write surfaces
- vendor preflight trusted-context surface
- vendor identity and scope readback

This separation is now baseline-backed by Stage 4A, Stage 4B, and Stage 5.

### Admin

Admin capability is no longer assumed to bypass site context.

The current foundation confirms:

- admin-only access is necessary but not sufficient
- current-site session state remains part of the mutation boundary
- admin content actions must remain site-aware

## 5. Smoke Baseline And API Baseline Mapping

### Established Smoke Baselines

- Stage 3B deterministic read contract smoke baseline
- User Site Permissions smoke guardrail baseline
- Vendor Work Entry Stage 4A write smoke baseline
- Vendor Work Entry Stage 4B read smoke baseline
- Admin Current-Site smoke baseline

### Established API Baselines

- Vendor Work Entry Stage 5 API baseline

### Supporting Tool Baselines

- `tools/check_site_read_isolation.py`
- `tools/check_site_permission_readiness.py`
- `tools/check_site_write_isolation_readiness.py`

These tools strengthen the architectural foundation by validating isolation assumptions beyond route-specific smoke alone.

## 6. Capabilities Not Yet Included In Architecture Foundation v1.0

The following areas are not yet treated as completed Architecture Foundation v1.0 capability:

- broader Product OS workflow orchestration beyond currently frozen route families
- broad runtime write migration away from SQLite-primary behavior
- PostgreSQL-primary write runtime
- `USE_SQLALCHEMY_WRITES=true` rollout
- governance redesign
- broad admin content-action freeze beyond the currently covered extra-field missing-site paths
- additional non-vendor domain API families not yet baseline-inventoried or frozen

These items may become future roadmap candidates, but they are intentionally outside this Stage 7 planning inventory.

## 7. Stage 7 Freeze Criteria

Architecture Foundation v1.0 should be considered ready for freeze review when all of the following are true:

- Stage 3B read-contract family remains frozen and production-verified
- Stage 4 write-isolation baseline remains explicit and unchanged
- at least one single write path is fully frozen end-to-end
- Vendor Work Entry write, read, and API-family baselines remain merged and stable
- Admin current-site aware content actions have at least a bounded smoke baseline
- no pending schema or migration dependency exists for the covered foundation family
- no foundation-critical route family depends on undefined auth or site-isolation behavior
- remaining future work is clearly outside the Architecture Foundation v1.0 boundary rather than hidden inside it

## 8. Architecture Foundation v1.0 Boundary

Architecture Foundation v1.0 should include:

- deterministic read contract foundation
- current-site aware authorization foundation
- site and sheet isolation foundation
- vendor read/write boundary foundation
- admin current-site mutation boundary foundation
- smoke baseline and API baseline evidence for the covered route families
- SQLite-primary write runtime as the explicitly frozen current boundary

Architecture Foundation v1.0 should not include:

- schema redesign
- migration rollout
- database foundation replacement
- governance redesign
- Product OS feature expansion
- broad write-runtime migration
- new business capability development

## 9. Boundary With Product OS v1.0 (M1)

Architecture Foundation v1.0 is the platform safety layer. Product OS v1.0 (M1) is the future product-capability layer built on top of that safety layer.

Architecture Foundation v1.0 is responsible for:

- trusted route boundaries
- deterministic contracts
- current-site awareness
- authorization correctness
- site isolation correctness
- stable smoke and API baselines for the covered families

Product OS v1.0 (M1) should own:

- future workflow expansion
- new product modules
- new operating surfaces
- capability growth that depends on the frozen foundation but is not itself part of the foundation

## 10. Next Step Boundary

The next step after this inventory should be one of the following:

- Stage 7 planning review
- Architecture Foundation v1.0 freeze review
- a roadmap decision about which capability family belongs to Product OS v1.0 (M1) rather than the foundation

Do not use this document as authorization to:

- start schema work
- start migration work
- start broad runtime write migration
- expand Vendor Work Entry beyond its frozen scope
- reopen Stage 3B through Stage 6 frozen families without a new explicit review
