# P-2 Planning Summary

## 1. Overview

### P-2 Planning objective

P-2 Planning was completed to:

- inventory the existing auth, site permission, and vendor-related structures
- freeze the current permission and login contracts before implementation
- separate near-term implementation from architecture drift
- produce a staged roadmap for future execution

### Stable baseline

- stable baseline: `ef934eb`

### Planning branch

- planning branch: `p-2-permission-planning`

## 2. Completed Documents

### P-2A Permission Contract Freeze

Core decisions:

- freezes the current internal auth/session/site-permission contracts from baseline `ef934eb`
- confirms `users.role` is the global role contract
- confirms `user_site_permissions.role` is the site-scoped role contract
- confirms admin remains globally authorized across active sites
- confirms P-2A must not change login flow, session schema, DB schema, or runtime behavior

### P-2B Vendor Identity Planning

Core decisions:

- documents that `vendor_accounts` already exists but is not wired into active auth runtime
- confirms vendor data APIs exist independently from vendor login/session
- defines `Global Admin`, `Internal User`, and `Vendor User` as distinct identities
- compares shared-login vs split-login options for vendor identity
- recommends separate vendor login/session direction as the safer planning path

### P-2C Login Flow Planning

Core decisions:

- documents the current internal login sequence and current-site normalization lifecycle
- confirms existing decorators are internal-session specific
- compares three login architecture options:
  - shared `/login`
  - split `/login` and `/vendor/login`
  - identity gateway
- recommends split login surfaces as the long-term direction
- freezes P-2C as planning-only with no runtime login/session changes

### P-2D Implementation Roadmap

Core decisions:

- converts P-2A / P-2B / P-2C into an executable implementation roadmap
- defines Stage 1 through Stage 5 for future implementation
- records expected files, risk level, runtime impact, rollback complexity, and validation plan for each stage
- establishes dependency order between vendor auth, session, authorization, UI, and integration
- recommends staged rollout with staging verification and small rollback-safe slices

## 3. Key Decisions

The following design decisions are now frozen at planning level:

- `users.role` and `user_site_permissions.role` have separate responsibilities and must not be mixed casually
- internal identity and vendor identity should remain explicitly separated
- vendor identity should not be silently injected into the current internal login/session path
- the recommended long-term direction is a separate vendor login route (`Option B`)
- P-2 planning does not modify runtime behavior
- P-2 planning does not modify schema
- P-2 planning does not modify active session behavior
- current internal login, current-site lifecycle, and stable site isolation behavior remain protected during planning

## 4. Open Questions

The following items remain for future implementation stages and should not be treated as resolved by planning alone:

- exact vendor login UX and entrypoint exposure
- exact vendor session field set beyond the baseline recommended namespace
- whether vendor flow needs explicit site switching or can remain vendor-plus-sheet scoped
- exact vendor read surface
- exact vendor write surface and workflow boundaries
- whether any feature flag is required for rollout
- final production validation sequence for vendor-enabled releases

## 5. Next Phase

The next phase is:

- **P-3 Implementation**

Recommended execution order from the P-2D roadmap:

### Stage 1

- Vendor authentication foundation

### Stage 2

- Vendor session implementation

### Stage 3

- Vendor authorization

### Stage 4

- Vendor UI / login

### Stage 5

- Integration / migration

### Execution note

- stages should remain small and rollback-safe
- staging verification is expected between risky stages
- implementation should not combine login, session, and authorization into one large change set
