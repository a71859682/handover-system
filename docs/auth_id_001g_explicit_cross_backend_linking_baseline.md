Status: design baseline

Scope: docs-only

Implementation status: not started

# AUTH-ID-001G — Explicit Cross-Backend Account Linking

## 1. Purpose and baseline

This document freezes the design boundary for explicit cross-backend account
linking. It does not implement linking, create link authority, or authorize a
runtime consumer.

Starting Production-frozen baseline:

- commit: `571e03a6b2ea4800c602c720ce560a2d3c229f71`
- commit message: `Record identity lifecycle guardrail evidence`

Current repository facts at this baseline:

- the registry physical schema exists
- the identity registry ID generator and validator exist
- the lifecycle source/policy readiness guardrail exists
- there is no runtime registry creation consumer
- there is no runtime linking consumer
- there is no dedicated link authority
- there is no link-proof challenge implementation
- there is no registry-specific immutable event ledger

Production registry rows, existing mapping topology, and current link state were
not queried during this docs-only slice. They remain unknown. Deployment health
and deployed source identity are not evidence of database objects, rows, or
link relationships.

## 2. Frozen ownership

The upstream owner matrix remains unchanged:

| Decision | Owner / gate | Frozen boundary |
|---|---|---|
| explicit cross-backend account linking | `AUTH-ID-001G` | Shared alias text must never auto-link internal and vendor principals. |
| lifecycle, mapping disable/reactivation, and unlink | `AUTH-ID-001F` | Linking must not bypass lifecycle policy or create relationship-movement authority. |
| existing-state anomaly repair, upgrade, and reconciliation | `AUTH-ID-001H` | Conflicting existing identities must not be merged, moved, or repaired in place by linking. |
| creation-consumer ID collision and transaction acceptance | `AUTH-ID-001E2` | A real creation consumer must complete target-PK collision, retry, rollback, and caller-supplied-ID acceptance. |

This document creates no new owner ID and does not reassign any existing owner.
It does not close `AUTH-ID-001E2`, `AUTH-ID-001F`, `AUTH-ID-001G`, or
`AUTH-ID-001H`.

## 3. Exact definition of linking

Explicit cross-backend account linking means only:

> After explicit approval, one canonical internal backend principal and one
> canonical vendor backend principal are associated with the same
> `GlobalIdentity`.

The backend principals remain separate credential and authority records:

- internal principal: `backend_kind = internal` plus canonical `users.id`
- vendor principal: `backend_kind = vendor` plus canonical
  `vendor_accounts.id`

Linking does not mean:

- credential merge
- password copy, transfer, sharing, or replacement
- authentication proof
- authorization proof
- role inheritance
- site or sheet permission inheritance
- vendor organization authority
- session authority switching
- alias ownership reassignment
- mapping reassignment
- `GlobalIdentity` merge
- account recovery
- unlink
- relink
- split
- restore
- legacy alias import
- reconciliation
- hot maintenance

A registry ID, mapping row, or linked topology is not login authority, identity
proof, or authorization proof. Protected requests must continue to resolve and
revalidate the canonical backend principal and its downstream role, site,
sheet, vendor, and workflow authority.

## 4. Topology classification

Every future link request must classify the complete current mapping topology
before it can reach a write path. Alias text, normalized keys, usernames,
display text, and `vendor_name` must not determine the classification.

### 4.1 Both principals unmapped

Disposition:

- may become a future link-request candidate
- must not be written merely because both principals are unmapped
- requires one new `GlobalIdentity` and two immutable backend mappings if a
  future creation consumer is independently approved
- any generated registry ID triggers the pending real-consumer acceptance in
  `AUTH-ID-001E2`
- alias creation is a separate explicit decision
- same username or other shared text must not automatically create an alias
- every approved alias must independently satisfy normalization, collision,
  ambiguity, provenance, and lifecycle requirements
- the new identity must not acquire authentication or business authority from
  the link transaction

### 4.2 One principal mapped and one principal unmapped

Disposition:

- may become a future add-second-backend-mapping candidate
- the existing identity, existing mapping, both backend principals, identity
  state, and all uniqueness/cardinality constraints must be freshly
  revalidated
- the existing mapping must remain immutable
- no alias, username, display text, or `vendor_name` similarity can approve the
  request
- no existing alias or mapping may be moved

### 4.3 Both principals mapped to the same `GlobalIdentity`

Disposition:

- classify as already linked
- return an idempotent no-write result
- freshly revalidate both backend principals and the two immutable mappings
- do not create duplicate rows
- do not rewrite timestamps or provenance
- do not consume new link authority merely to rewrite an already-complete
  topology
- do not expose the linked identity or topology through an ordinary public
  response

### 4.4 Principals mapped to different `GlobalIdentity` records

Disposition:

- classify as a conflict
- fail closed
- perform no link, merge, move, unlink, reassignment, or repair
- do not let an alias, credential, administrator, or operator select a winning
  identity
- preserve the observed state for a separately approved `AUTH-ID-001H`
  reconciliation gate
- do not expose either identity through the public response

### 4.5 Missing, inactive, stale, or mismatched principal

Disposition:

- fail closed
- create or modify no registry row
- consume no proof as a successful link
- do not fall back to another backend, username, alias, principal, or
  candidate
- expose no account-existence or principal-state oracle

## 5. Authority model

No current actor automatically has link authority:

- ordinary internal user
- vendor user
- administrator
- site administrator
- Production operator
- database operator
- browser, form, API, session, or CLI caller

Existing role, site permission, vendor scope, deployment access, or Production
access must not be inferred as link authority.

Frozen future authority requirements:

- final approval requires an independently reviewed dedicated link-approval
  capability
- that capability is not currently implemented
- that capability is not currently assigned to any role or account
- this document creates no role or permission
- a browser, form, API caller, session, or CLI must never choose a
  `global_identity_id`, `backend_principal_mapping_id`, or
  `login_identifier_alias_id`
- a single credential is insufficient for cross-backend linking
- simultaneous control of both credentials is evidence of control over two
  backend accounts, but is not by itself proof that the accounts represent the
  same subject
- password verification is not linking proof
- no linking consumer may exist before dedicated authority is implemented and
  independently verified

Dedicated link approval is a distinct decision from authentication,
account-control verification, identity equivalence, and runtime authorization.

## 6. Proof contract

A future proof bundle must contain at least:

- exact internal backend kind
- canonical internal backend principal key
- exact vendor backend kind
- canonical vendor backend principal key
- fresh canonical revalidation of both backend principals
- vendor active-state verification
- internal existence and then-current eligible-state verification
- two independent, recent, single-use account-control evidence references
- explicit subject linking intent
- dedicated link approver evidence
- proof issuance time
- proof freshness and expiry state
- proof single-use state
- correlation/idempotency key
- mapping conflict and cardinality result
- reason code
- transaction outcome

The following concepts remain separate:

| Concept | Meaning |
|---|---|
| credential verification | Evidence of control of one backend credential only. |
| account control | Evidence that a subject currently controls a particular backend account. |
| identity equivalence | A separately approved conclusion that the two controlled accounts may share one `GlobalIdentity`. |
| link approval | A decision made by the future dedicated link authority. |
| runtime authorization | Authority resolved from each canonical backend and its current downstream relations. |

The following must never serve as identity-equivalence proof or link authority:

- raw alias
- normalized alias
- same username
- `vendor_name`
- display name
- role
- site
- permission
- browser continuity
- existing session alone
- IP or device similarity
- Production operator access

Alias and normalized-key data may only support candidate discovery under their
separately frozen collision and ambiguity rules. Candidate discovery must not
be promoted to link approval.

## 7. Session and challenge boundary

Frozen rules:

- an internal-plus-vendor mixed authenticated session must not be created to
  prove a link
- the existing login-time `session.clear()` behavior must remain unchanged
- existing mixed-session fail-closed behavior must not be weakened
- a future link challenge may use only server-controlled, short-lived,
  single-use, purpose-bound proof references
- a proof reference must not become a login session, identity proof,
  authorization token, credential substitute, or recovery artifact
- completion, failure, cancellation, or expiry must invalidate the proof
  reference
- proof and credential material must not appear in a browser response, URL,
  ordinary log, analytics event, or generic error

The exact proof-token format, storage, cryptography, expiry duration, revocation
mechanism, and cleanup implementation are deferred to a separately reviewed
implementation gate. They are not implemented or approved by this document.

## 8. Canonical revalidation order

A future implementation must perform all necessary canonical revalidation at
least once before the transaction begins and again for conflict-sensitive state
before commit.

Minimum sequence:

1. Resolve the canonical requesting actor.
2. Validate the dedicated link authority.
3. Resolve the internal principal by exact backend key.
4. Resolve the vendor principal by exact backend key.
5. Revalidate vendor active state.
6. Revalidate proof freshness and single-use state.
7. Re-read existing mappings for both principals.
8. Classify the topology as unmapped, same identity, different identity, or a
   missing/inactive/stale conflict.
9. Validate uniqueness and cardinality.
10. Begin or continue the caller-owned transaction.
11. Re-read and recheck all conflict-sensitive state before any write.
12. Perform the complete approved row set.
13. Record immutable audit evidence.
14. Commit every effect atomically.
15. Return a generic result that exposes no account-existence or linkage
    oracle.

Alias, normalized-key, and username lookup must never replace exact
backend-key canonical resolution.

If any canonical state changes between validation points, the operation must
fail closed and roll back.

## 9. Transaction and `AUTH-ID-001E2` contract

Linking is one logical transaction.

Atomic effects include, when separately approved:

- `GlobalIdentity` creation
- internal backend mapping creation
- vendor backend mapping creation
- any independently approved alias creation
- proof consumption
- immutable audit outcome

Frozen requirements:

- every effect is all-or-nothing
- no partial global identity may remain
- no partial alias may remain
- no partial mapping may remain
- no proof may be recorded as successfully consumed without a committed link
- no audit success may be recorded for a rolled-back link
- caller-owned transaction boundaries must be preserved
- retry is allowed only for a classified target-primary-key UUID collision
- each logical creation allows at most three ID-generation attempts
- a non-target-PK or noncollision `IntegrityError` fails immediately
- collision classification must not depend on fuzzy exception-message matching
- retry exhaustion produces a generic internal failure
- replay with the same idempotency key returns the same completed result or a
  safe no-write state
- concurrent conflicting requests permit only one legal commit
- a losing concurrent request must fail closed or return the same idempotent
  result

A real linking creation consumer formally triggers the pending
`AUTH-ID-001E2` acceptance for:

- target-PK collision classification
- first-collision retry success
- second-collision retry success
- third-attempt exhaustion
- immediate noncollision failure
- complete multi-row rollback
- savepoint and caller-owned transaction behavior
- caller-supplied ID rejection

Exact savepoint ownership, ledger schema, and consumer implementation remain
deferred. This document does not satisfy those acceptance items.

## 10. Audit and privacy contract

A future immutable audit record must contain at least:

- canonical requesting actor ID
- dedicated approver ID
- request ID
- correlation/idempotency ID
- reason code
- timestamp
- before topology
- after topology
- immutable `GlobalIdentity` ID
- immutable mapping IDs
- backend kinds
- controlled backend principal references
- backend revalidation result
- proof-state result without proof material
- conflict classification
- transaction outcome

Audit and ordinary output must never contain:

- password
- password hash
- credential secret
- session value
- proof token
- raw alias
- normalized alias
- full sensitive backend evidence
- environment secret
- database secret

An ordinary error response must not reveal:

- whether either account exists
- whether the other backend account exists
- whether the principals are already linked
- the owning `GlobalIdentity`
- the conflicting identity
- proof failure details
- approver identity
- internal topology classification

Controlled audit access, retention, redaction, export, incident access, and
cleanup require independent approval before implementation.

The current registry timestamps and provenance text fields are not a complete
immutable link event ledger.

## 11. Failure and conflict matrix

Public responses must remain generic and non-oracular. Detailed internal
classification may appear only in an independently approved, access-controlled,
secret-safe audit channel.

| Condition | Frozen internal disposition | Write result |
|---|---|---|
| malformed request | reject before proof or topology disclosure | no write |
| missing dedicated authority | fail closed | no write |
| stale or invalid requesting actor | fail closed | no write |
| missing internal principal | generic rejection | no write |
| missing vendor principal | generic rejection | no write |
| inactive vendor principal | generic rejection | no write |
| expired proof | reject and invalidate as required | no registry write |
| replayed proof | return safe idempotent result or reject | no duplicate write |
| one-sided account control | reject | no write |
| missing dedicated approval | reject | no write |
| either principal mapped elsewhere | conflict | no write |
| both principals mapped to different identities | hand off to H without repair | no write |
| duplicate same-identity request | idempotent already-linked classification | no write |
| uniqueness conflict | classify exact constraint; fail closed unless it proves the same idempotent result | no partial write |
| target-PK UUID collision | retry within the three-attempt limit | no partial write |
| noncollision `IntegrityError` | fail immediately; do not retry | rollback |
| concurrent request | one legal commit; loser fails closed or returns same idempotent result | no duplicate or partial write |
| audit failure | fail the logical transaction | rollback |
| transaction failure | fail closed | rollback |
| post-validation mismatch | fail closed | rollback |

No public error code may distinguish these conditions in a way that becomes an
account-existence, identity-membership, proof-state, or link-topology oracle.

## 12. Threat model

| Threat | Frozen mitigation | Capability still not implemented |
|---|---|---|
| alias or username collision takeover | Alias and username similarity never proves equivalence or approval. | Link-specific proof and authority enforcement |
| compromised single credential | One credential is insufficient; two independent account-control references are required. | Challenge issuance, verification, and consumption |
| compromised administrator | Existing administrator status grants no link authority. | Dedicated authority, separation of duties, and approval audit |
| confused deputy | Canonical requesting actor and dedicated approver are separate, explicit inputs. | End-to-end actor/approver enforcement |
| cross-site privilege escalation | Link state confers no role, site, sheet, or permission. | Consumer negative tests and authorization isolation proof |
| `vendor_name` impersonation | `vendor_name` is forbidden as identity or link authority. | Link consumer enforcement |
| mixed-session abuse | Mixed session is not proof and existing fail-closed behavior must remain. | Purpose-bound challenge implementation |
| proof replay | Single-use proof plus idempotency is required. | Proof ledger and atomic consumption |
| stale mapping | Both mappings and backend principals are re-read before transaction and commit. | Transactional consumer |
| concurrent double link | Exact topology recheck and uniqueness/cardinality enforcement; only one legal commit. | Concurrency acceptance |
| partial write | Identity, mappings, alias, proof, and audit effects are one logical transaction. | Real-consumer rollback acceptance |
| linking used as authentication proof | Registry ID and link state are explicitly non-authoritative. | Runtime negative tests |
| audit leakage | Audit excludes credentials, proof material, aliases, sessions, and secrets. | Access-controlled audit implementation |
| operator overreach | Production access is not link authority. | Dedicated approval capability |
| automatic merge or reassignment | Different-identity topology fails closed and moves to H. | H reconciliation design |
| hot-maintenance repair assumption | Linking performs no merge, movement, repair, or live reconciliation. | Independently reviewed maintenance and reconciliation capabilities |

No threat may be resolved through fallback guessing, password probing across
backends, alias repair, automatic remapping, best-effort linking, or silent
reconciliation.

## 13. Owner handoffs

### 13.1 `AUTH-ID-001E2`

Triggered only when a formally approved real creation consumer exists:

- ID target-PK collision classification
- maximum three-attempt retry
- immediate noncollision failure
- all-or-nothing creation
- savepoint/caller-owned transaction acceptance
- caller-selected ID rejection

`AUTH-ID-001E2` remains open and parked until that trigger exists.

### 13.2 `AUTH-ID-001F`

Owns:

- unlink policy and implementation
- mapping disable/reactivation
- identity, alias, and mapping lifecycle
- legacy alias import

This document implements none of those capabilities.

### 13.3 `AUTH-ID-001H`

Owns:

- principals mapped to different identities
- existing-state anomalies
- repair
- upgrade
- reconciliation
- any future independently approved relationship correction

`AUTH-ID-001G` must not repair, merge, overwrite, move, or select a winning
identity.

### 13.4 Preserved G boundary

`AUTH-ID-001G` must not implement:

- merge
- unlink
- relink
- reassignment
- repair
- relationship movement
- upgrade
- reconciliation

No G implementation may bypass the F, H, or E2 gates.

## 14. Future implementation acceptance matrix

A future implementation must demonstrate at least:

- no automatic linking
- no alias-, username-, display-name-, or `vendor_name`-derived approval
- no caller-selected registry IDs
- no role, site, sheet, permission, credential, session, or vendor-authority
  inheritance
- both-backend canonical revalidation
- vendor active-state revalidation
- dedicated link authority required
- one credential is insufficient
- two account-control evidence references do not alone prove identity
  equivalence
- mixed session is not proof
- both-unmapped topology classification
- one-mapped/one-unmapped topology classification
- same-identity topology classification
- different-identity topology classification
- same-identity idempotent no-write
- different-identity fail closed
- missing/inactive/stale principal fail closed
- target-PK first-collision retry success
- target-PK second-collision retry success
- third-attempt exhaustion
- noncollision `IntegrityError` does not retry
- replay/idempotency behavior
- concurrent conflict behavior
- complete rollback with no partial rows
- proof consumption rollback
- audit failure rollback
- no account-existence or link-topology oracle
- secret-safe logs and errors
- disposable SQLite fixtures only
- PostgreSQL attempts equal zero
- no DEV or Production persistent database access
- no scan or rewrite of existing persistent data
- `AUTH-ID-001F` and `AUTH-ID-001H` boundaries preserved
- `AUTH-ID-001E2` not closed before real-consumer acceptance passes

Passing this docs-only review does not satisfy any implementation acceptance
item.

## 15. Explicit exclusions

This slice does not create or modify:

- application code
- tests
- tools
- schema
- indexes
- API
- route
- form
- UI
- CLI
- role
- permission
- session behavior
- proof token
- proof store
- event ledger
- DDL
- DML
- backfill
- import
- link
- unlink
- relink
- merge
- split
- restore
- relationship movement
- reconciliation
- Production database inspection
- hot-maintenance capability

It also does not scan usernames, credentials, sessions, registry rows, mapping
topology, or account-link state.

## 16. Production facts, inferences, and unknowns

Known from source and deployment evidence:

- Production has deployed source containing the physical registry schema.
- The deployed application has started successfully at the recorded baseline.
- The repository contains no approved runtime linking consumer.

Reasonable source-level inference:

- the schema can structurally represent one internal and one vendor mapping
  under the same identity
- that representational capacity does not prove a link exists

Unknown because no Production database query occurred:

- whether registry tables currently contain rows
- whether any backend mappings exist
- whether any principals share one `GlobalIdentity`
- whether any existing topology is conflicting, stale, or anomalous
- when any registry object or row was first created

Deployment health must not be described as database-content or linking-state
evidence.

## 17. Docs-only validation and preserved status

This design baseline is valid only if repository review confirms:

- this document is the only newly changed repository file
- the index remains clean
- upstream `AUTH-ID-001E` and `AUTH-ID-001F` documents are unchanged
- application, service, test, tool, schema, route, template, and dependency
  files are unchanged
- `.codex/` remains untouched
- the top metadata remains the exact design-baseline, docs-only, and
  not-started contract
- Production registry rows and link state remain explicitly unknown
- `AUTH-ID-001E2` remains consumer acceptance pending
- `AUTH-ID-001F` lifecycle mutation remains not started
- `AUTH-ID-001H` remains the reconciliation owner
- no dedicated link authority is claimed to exist
- no linking consumer is claimed to exist

## 18. Frozen conclusion

```text
AUTH-ID-001G DOCS-ONLY LINKING DESIGN FREEZE
LINKING IMPLEMENTATION: NOT STARTED
DEDICATED LINK AUTHORITY: NOT IMPLEMENTED OR ASSIGNED
NO LINKING CONSUMER CREATED
```

No implementation work may begin until this docs-only baseline receives
independent final-diff review and a subsequent implementation gate explicitly
defines the allowed scope.
