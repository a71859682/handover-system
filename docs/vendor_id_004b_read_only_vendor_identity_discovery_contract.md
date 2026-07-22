# VENDOR-ID-004B Read-only Vendor Identity Discovery Contract

| Field | Frozen value |
|---|---|
| Slice | `VENDOR-ID-004B` |
| Canonical title | `Read-only Vendor Identity Discovery Implementation` |
| Contract status | `DOCS-ONLY CONTRACT / IMPLEMENTATION NOT STARTED` |
| Baseline commit | `f9a974ec1ec3364242db3858969ba012195b57f7` |
| Canonical implementation path | `tools/discover_vendor_identity_evidence.py` |
| Safe-reference profile | `HMAC_SHA256_SAFE_REFERENCE_V1` |
| Supported backend/environment in V1 | Windows system-temp disposable synthetic SQLite / `synthetic_local` |
| Output surface | Canonical JSON on stdout only |
| Controlled backfill | `NOT AUTHORIZED` |
| Mapping approval | `NOT AUTHORIZED` |
| Runtime authority switch | `NOT AUTHORIZED` |

## 1. Status and adopted product decisions

This document records the product decisions accepted for VENDOR-ID-004B and
freezes the contract that a later, separately authorized implementation must
satisfy. It creates no executable capability and performs no discovery.

The adopted decisions are exactly:

1. `DECISION 1-B`: retain the Production-frozen VENDOR-ID-003 aggregate
   readiness contract unchanged and create a separate VENDOR-ID-004B
   candidate-evidence contract and canonical path;
2. `DECISION 2-A`: use keyed HMAC safe references and never emit raw source
   keys, raw vendor identities, raw labels, usernames, credentials, password
   hashes, or the HMAC key;
3. `DECISION 3-A`: retain the VENDOR-ID-004A closed eleven-class taxonomy and
   express narrower conditions through the closed reason-code vocabulary in
   this document; and
4. `DECISION 4-A`: support only Windows system-temp disposable synthetic
   SQLite in V1, emit canonical JSON to stdout only, and defer live execution,
   PostgreSQL, and artifact persistence to later independent gates.

The targeted contract-gap decisions adopted after the first complete docs
review are exactly:

1. `CG-1 A`: reviewed items are legacy-root rows addressed by physical stable
   primary keys; query ordinals are prohibited as VENDOR-ID-004B identities;
2. `CG-2 A`: use the exact candidate graph, status, structural/label evidence,
   scope, cardinality, and precedence rules in Section 4;
3. `HG-1 A`: use the target-side, scope-bound, physical-PK-based HMAC recipes
   and closed query IDs in Section 5;
4. `IG-1 A`: enforce the cross-field invariants, closed reason-code extension,
   recomputable counts, empty V1 exclusions, and all-items-unresolved rules in
   Sections 7 and 8; and
5. `LG-1 A`: use exactly one SQLite `mode=ro` connection and perform only
   filesystem no-touch checks after close.

These decisions supplement and do not reopen `1-B`, `2-A`, `3-A`, or `4-A`.

The final residual contract-gap decisions are exactly:

1. `R1-A`: every reviewed source kind uses the exact atomic source-scope
   derivation in Section 4.6; a vendor account never acquires intrinsic site or
   sheet scope from relationship evidence;
2. `R2-A`: every exact existing vendor mapping uses the single relation
   projection in Section 4.7, including exact relation counts, statuses,
   evidence codes, and missing/disabled-target behavior;
3. `R3-A`: every distinct required table proved missing or malformed produces
   exactly one coalesced `source_contract` item under Sections 7.3 and 8.4;
4. `R4-A`: metadata and business rows are read only through the exact literal
   statements, canonical schema projection, row-count bounds, and failure
   rules in Sections 4.8 and 4.9; and
5. `R5-A`: deterministic A/A identity is the complete controlled-input and
   acceptance-runtime contract in Section 7.5, not merely equal fixture/key
   bytes and timestamps.

These decisions supplement and do not reopen `CG-1 A`, `CG-2 A`, `HG-1 A`,
`IG-1 A`, or `LG-1 A`.

The final canonical-consistency decisions are exactly:

1. `C1-A`: accumulate every applicable organization-conflict code by
   `candidate_ref` before constructing exactly one relation for that target;
2. `C2-A`: distinguish fatal metadata capture/projection failures from fully
   observed schema-content conflicts under the exact xinfo conformance matrix;
3. `C3-A`: distinguish SQL-byte, query-ID, and fixed-query-family effects
   without changing the frozen provenance-reference HMAC preimage;
4. `C4-A`: make every before/after no-touch mismatch fatal with zero stdout and
   retain stale vocabulary as unreachable in V1; and
5. `C5-A`: keep valid non-vendor mappings outside candidate relations and
   vendor-item classification while retaining them in bounded snapshot
   evidence.

These decisions supplement and do not reopen `R1-A`, `R2-A`, `R3-A`, `R4-A`,
or `R5-A`.

The final residual canonical decisions are exactly:

1. `D1-A`: a retired organization is excluded from normalized-label/general
   lookup but is retained once as ineligible when current exact structural
   evidence directly references its existing row;
2. `D2-A`: a disabled global identity is excluded from general lookup but is
   retained once as ineligible by the exact R2-A existing-mapping projection;
3. `D3-A`: a type-valid topology-content failure produces the exact twelve-item
   incomplete projection, performs no data query, and creates no thirteenth
   topology item;
4. `D4-A`: metadata content conflicts are the closed eight-category vocabulary
   in Section 4.8, with all other frozen fields fingerprint-only; and
5. `D5-A`: `conflicting_backend_principal` is unreachable in V1, while
   `registry_target_conflict` remains exclusive to the R2-A missing-target
   projection.

These decisions supplement and do not reopen `C1-A`, `C2-A`, `C3-A`, `C4-A`,
or `C5-A`.

No later step becomes authorized merely because this contract is frozen.

## 2. Governing contracts, ownership, and precedence

### 2.1 VENDOR-ID-003 remains unchanged

`docs/vendor_id_003_read_only_vendor_discovery_baseline.md` continues to own
the aggregate-only readiness surface. Its canonical path, CLI, public callable,
canonical envelope, evidence hash, static-checker fail-closed semantics, fixed
queries, anomaly taxonomy, transient-output rules, and privacy rules remain
unchanged. Only the exact checker-composition plumbing frozen in Section 15
may change under the separately authorized 004B0S gate; that change cannot
alter a VENDOR-ID-003 product or aggregate semantic.

VENDOR-ID-003 does not produce candidate mapping evidence and cannot substitute
for the VENDOR-ID-004B surface. VENDOR-ID-004B does not implement, replace,
extend, wrap, or relax the VENDOR-ID-003 aggregate tool.

### 2.2 VENDOR-ID-004A remains unchanged

`docs/vendor_id_004_controlled_vendor_identity_backfill_operational_gate_baseline.md`
continues to own:

- controlled-backfill sequencing;
- separation of evidence production, mapping review, authorization, apply,
  reconciliation, and runtime authority;
- the exact eleven-class conflict taxonomy;
- environment independence; and
- all later no-write, write-freeze, recovery, audit, and authorization gates.

This document does not change or reinterpret those frozen requirements.

### 2.3 VENDOR-ID-004B ownership

This document owns only:

- the candidate-evidence implementation identity;
- synthetic-only invocation and lifecycle;
- the safe-reference profile and byte recipe;
- the exact candidate item and evidence-envelope shapes;
- the closed reason-code vocabulary and its classification mapping;
- the V1 read-only/no-touch controls; and
- the disposable acceptance matrix.

If this contract cannot be reconciled with either governing frozen contract,
the implementation must fail closed. Runtime code must never resolve a
contract conflict by silently overriding VENDOR-ID-003 or VENDOR-ID-004A.

## 3. Authority and non-equivalence boundary

The VENDOR-ID-004B result is discovery evidence for a future VENDOR-ID-004C
human review. It is not an approved mapping, vendor identity, authorization,
operation package, write instruction, reconciliation result, or authority
switch.

```text
candidate evidence
!= approved mapping
!= approved vendor_id
!= identity merge
!= ID persistence
!= controlled apply
!= backfill
!= reconciliation
!= runtime authority
```

`vendor_name`, a normalized vendor label, an account ID, a backend principal,
or a browser-provided identity, role, vendor, site, or sheet value cannot by
itself establish canonical identity. VENDOR-ID-004B has no browser, API, route,
session, or runtime-consumer surface.

## 4. Exact V1 source boundary

### 4.1 General source rules

The implementation may read only the columns in this section through fixed
module-level SQL constants. `SELECT *`, runtime SQL construction, caller SQL,
caller predicates, caller-selected columns, table-name interpolation, and
environment-derived queries are prohibited.

All values remain transient internal evidence. Every raw identifier and label
is prohibited from stdout, stderr, exceptions, logs, evidence hashes other than
the keyed safe-reference construction, and test failure messages.

### 4.2 Legacy and isolation sources

| Source table | Allowed columns | Purpose |
|---|---|---|
| `sites` | `id` | Validate site scope. |
| `sheets` | `id`, `site_id` | Establish the sheet-to-site map. |
| `tasks` | `id`, `sheet_id`, `vendor` | Observe task vendor-label evidence and bind it to a physical stable primary key. |
| `vendor_accounts` | `id`, `vendor_name` | Observe vendor-account and label evidence without credentials. |
| `vendor_contacts` | `id`, `sheet_id`, `vendor_name` | Observe sheet-scoped label evidence through a physical stable primary key; contact/person columns are prohibited. |
| `vendor_work_entries` | `id`, `sheet_id`, `vendor_name` | Observe sheet-scoped label evidence through a physical stable primary key; business payload columns are prohibited. |

`vendor_accounts.username`, `vendor_accounts.password_hash`, contact/person
fields, phone fields, and work-entry payload fields are categorically outside
the V1 read authority.

The twelve exact VENDOR-ID-004B data statements, including these four reviewed
legacy roots, are frozen in Section 4.9. They do not modify or replace the
separately frozen VENDOR-ID-003 statements. No row-order position enters any
source identity. Ordering exists only for deterministic fixed-query/result
validation.

### 4.3 Vendor-organization candidate sources

| Source table | Allowed columns |
|---|---|
| `vendor_organizations` | `vendor_id`, `display_name`, `organization_status` |
| `vendor_organization_memberships` | `vendor_membership_id`, `vendor_id`, `vendor_account_id`, `membership_role`, `membership_status` |
| `vendor_site_assignments` | `vendor_site_assignment_id`, `vendor_id`, `site_id`, `assignment_status` |
| `sheet_vendor_bindings` | `sheet_vendor_binding_id`, `vendor_id`, `sheet_id`, `site_id`, `vendor_site_assignment_id`, `binding_status` |

These tables are a non-authoritative shadow projection. Reading a row does not
grant lifecycle, relationship, mapping, apply, or runtime-consumer authority.

### 4.4 Identity-registry conflict sources

| Source table | Allowed columns | Purpose |
|---|---|---|
| `global_identities` | `global_identity_id`, `registry_status` | Detect unavailable or conflicting registry targets. |
| `backend_principal_mappings` | `backend_principal_mapping_id`, `global_identity_id`, `backend_kind`, `backend_principal_key`, `mapping_status` | Detect consistent/conflicting existing vendor backend-principal state. |

`login_identifier_aliases` is not a V1 data source. Alias, username, credential,
or authentication correlation is outside this slice.

For `backend_principal_mappings`, only `backend_kind = 'vendor'` participates in
candidate classification or relation construction. A valid row whose
`backend_kind != 'vendor'` creates no mapping relation, creates no identity
relation, does not change a vendor item's classification, does not increase
`candidate_relation_count`, and never contributes
`conflicting_backend_principal`. It remains transaction-observed only through
the bounded source row count, source snapshot, schema fingerprint, and evidence
digest. Equal numeric principal keys or equal global-identity keys in different
backend namespaces are not vendor conflicts.

A non-vendor row can affect the run only when its fully observed content proves
a duplicate mapping primary identity, a same-backend-kind uniqueness violation,
an invalid tuple/status/key, a required physical-uniqueness violation, or a
result-cardinality violation. That condition is
`backend_principal_mappings` source-contract incompleteness under Section 8.4;
it still creates no mapping or identity relation, changes no individual vendor
item to `target_state_conflict`, and selects or aggregates no target. These
rules do not expand identity or authentication authority.

### 4.5 Exact reviewed-item and non-item boundary

The complete V1 source-role matrix is:

| Source table or condition | Candidate-item `source_kind` | Exact unit | V1 role |
|---|---|---|---|
| `vendor_accounts` | `vendor_account` | One selected row addressed by its exact positive physical `id` | Reviewed legacy-root item |
| `tasks` | `task_vendor_label` | One selected row addressed by its exact positive physical `id` | Reviewed legacy-root item |
| `vendor_contacts` | `vendor_contact_label` | One selected row addressed by its exact positive physical `id` | Reviewed legacy-root item |
| `vendor_work_entries` | `vendor_work_entry_label` | One selected row addressed by its exact positive physical `id` | Reviewed legacy-root item |
| Missing or malformed required source | `source_contract` | One exact required table name | Reviewed operational-incompleteness item |
| `sites` | none | One exact positive site ID | Scope evidence only |
| `sheets` | none | One exact positive sheet/site pair | Scope evidence only |
| `vendor_organizations` | none | One exact organization row | Candidate-target evidence only |
| `vendor_organization_memberships` | none | One exact membership row | Structural evidence only |
| `vendor_site_assignments` | none | One exact assignment row | Scope-consistency evidence only |
| `sheet_vendor_bindings` | none | One exact binding row | Scope-consistency evidence only |
| `global_identities` | none | One exact registry identity row | Existing-state target evidence only |
| `backend_principal_mappings` | none | One exact mapping row | Existing-state evidence only |

No target, relationship, scope, identity-registry, or mapping row becomes a
reviewed item merely because it participates in evidence. A selected physical
primary key is mandatory for every legacy-root item. VENDOR-ID-003's
zero-based query-row ordinal is not a VENDOR-ID-004B source identity and must
not enter a `source_record_ref` preimage.

`id` in each of `tasks`, `vendor_contacts`, and `vendor_work_entries` must have
exact Python type `int`, must not be `bool`, and must be greater than zero. It
is read only to construct the keyed source reference and is never emitted.
Duplicate physical primary identities are a result-contract failure; they are
not disambiguated by row order.

### 4.6 Exact structural graph and status behavior

The only structural relationships usable by V1 are:

```text
sheets.id -> sheets.site_id -> sites.id

vendor_accounts.id
  <- vendor_organization_memberships.vendor_account_id
  -> vendor_organization_memberships.vendor_id
  -> vendor_organizations.vendor_id

vendor_organizations.vendor_id
  -> vendor_site_assignments.vendor_id
  -> vendor_site_assignments.site_id
  -> sites.id

sheet_vendor_bindings
  -> vendor_organizations
  -> sheets
  -> sites
  -> vendor_site_assignments

backend_principal_mappings.global_identity_id
  -> global_identities.global_identity_id
```

For `backend_kind = 'vendor'`, a positive exact-integer
`backend_principal_key` is a logical external reference to
`vendor_accounts.id`. It is not a SQLite foreign key, must not be guessed or
coerced, and does not acquire authentication or authorization meaning.

The exact case-sensitive status behavior is:

| Domain | Closed values | Candidate/structural behavior |
|---|---|---|
| `organization_status` | `active`, `disabled`, `retired` | `active` and `disabled` may enter normalized-label organization-candidate evidence; `retired` never enters normalized-label or general lookup, but D1-A retains one ineligible relation when current exact structural evidence directly references its existing row |
| `membership_role` | `owner`, `member` | Required structural metadata; neither value establishes identity |
| `membership_status` | `pending`, `active`, `revoked` | `pending` and `active` form a current structural organization edge; `revoked` does not |
| `assignment_status` | `active`, `inactive` | Only `active` forms current site-scope evidence; `inactive` remains observed state |
| `binding_status` | `active`, `inactive` | Only `active` forms current sheet/site evidence; `inactive` remains observed state |
| `registry_status` | `active`, `disabled` | `disabled` never becomes a general registry-lookup candidate; D2-A permits only the exact R2-A existing vendor-mapping projection to retain its existing row as one ineligible identity relation; an `active` row is still not a general lookup candidate unless the governing registry predicate is independently proved |
| `mapping_status` | `active`, `disabled` | Only `active` contributes to current mapping eligibility; `disabled` remains historical/ineligible existing-state evidence |

An invalid type, null, whitespace variant, case variant, or unknown status is a
result-contract failure. It is never silently treated as an ineligible row.

V1 does not read `login_identifier_aliases`; therefore it cannot claim that it
performed the governing alias-based registry lookup. A global-identity or
mapping relation may arise only from an exact existing vendor backend mapping
structure observed through the two approved registry sources. D2-A is not a
general registry lookup: it is only the exact existing-mapping projection of an
identity row already named by that mapping.

#### Exact source-kind scope derivation

The source scope is part of item identity and is never selected by a caller,
candidate, mapping, assignment, or output-order position. The exact derivation
table is:

| `source_kind` | `typed_site_scope_or_null` (`S_i`) | `typed_sheet_scope_or_null` (`H_i`) | Exact source |
|---|---|---|---|
| `vendor_account` | `null` | `null` | No intrinsic scope exists. Zero, one, or multiple membership/assignment edges never alter item identity. |
| `task_vendor_label` | `I(sheets.site_id)` | `I(tasks.sheet_id)` | `tasks.sheet_id -> sheets.id -> sheets.site_id -> sites.id` |
| `vendor_contact_label` | `I(sheets.site_id)` | `I(vendor_contacts.sheet_id)` | `vendor_contacts.sheet_id -> sheets.id -> sheets.site_id -> sites.id` |
| `vendor_work_entry_label` | `I(sheets.site_id)` | `I(vendor_work_entries.sheet_id)` | `vendor_work_entries.sheet_id -> sheets.id -> sheets.site_id -> sites.id` |
| `source_contract` | `null` | `null` | No business scope is parsed. |

For each task, contact, or work-entry item, scope is atomic all-or-null:

1. the selected row's `sheet_id` must have exact Python type `int`, must not be
   `bool`, and must be greater than zero;
2. exactly one selected `sheets` row must carry that `id`;
3. its `site_id` must have exact Python type `int`, must not be `bool`, and
   must be greater than zero; and
4. exactly one selected `sites` row must carry that `id`.

Only when all four conditions succeed are both `S_i` and `H_i` non-null and
both scope references constructed. A null row `sheet_id` or null resolved
`site_id` sets both to null and produces
`invalid_or_incomplete_source_identity` plus `missing_required_scope`. A
non-integer, boolean, non-positive, unresolvable, duplicate, or ambiguous
identifier/relationship sets both to null and produces the same classification
plus `malformed_source_identity`. A partial site-only or sheet-only scope or
scope reference is prohibited.

When the complete source chain resolves but independent current structural
evidence points to a different known site, the source-derived `S_i` and `H_i`
remain unchanged. The item becomes `target_state_conflict` and includes
`cross_site_evidence` in the C1-A ordered union; every otherwise discovered
affected relation follows the exact ineligible rule below. Missing or
unresolvable evidence never becomes cross-site evidence.

For a vendor account, zero assignments, one assignment, multiple assignments
to one site, and multiple assignments to different sites all leave
`S_i = null` and `H_i = null`. Current assignment contradictions contribute
only `assignment_evidence_conflict` relation/item evidence. They never create
an account-level intrinsic site or sheet scope.

A `source_contract` item has null `S_i`/`H_i`, null `site_scope_ref` and
`sheet_scope_ref`, `label_evidence.validity = "missing"`, a null
`safe_label_ref`, and an empty `candidate_relations` array.

The item's exact `S_i` and `H_i` from this table are reused without
reinterpretation in its `source_record_ref`, non-null `safe_label_ref`, every
target-side `candidate_ref`, and `provenance_ref`. A candidate reference still
uses the candidate target's kind, table, and key; source-side identity is never
substituted.

### 4.7 Frozen normalization and candidate construction

The exact normalization profile name is:

```text
VENDOR_DISCOVERY_EVIDENCE_NORMALIZATION_V1
```

For an exact string, the algorithm is exactly:

1. apply Unicode NFKC;
2. apply Unicode default `casefold`;
3. apply Unicode NFKC again;
4. replace exactly these 29 code points with ASCII U+0020:

```text
U+0009 U+000A U+000B U+000C U+000D
U+001C U+001D U+001E U+001F U+0020
U+0085 U+00A0 U+1680
U+2000 U+2001 U+2002 U+2003 U+2004 U+2005 U+2006
U+2007 U+2008 U+2009 U+200A
U+2028 U+2029 U+202F U+205F U+3000
```

5. collapse each maximal ASCII-space run to one U+0020;
6. remove leading and trailing ASCII spaces;
7. reject a blank result;
8. reject a result longer than 100 Unicode code points; and
9. reject any remaining code point whose Unicode general category begins with
   `C` (`Cc`, `Cf`, `Cs`, `Co`, or `Cn`).

Punctuation is preserved except for NFKC compatibility changes. Fuzzy
matching, transliteration, diacritic removal, punctuation deletion, locale
collation/casing, phonetic matching, token reordering, synonyms, and
abbreviations are prohibited. The algorithm is locale-independent and
idempotent on every successful result.

A valid normalized legacy label can produce only unapproved
`vendor_organization` candidates whose valid display names have exactly the
same normalized value and whose statuses are `active` or `disabled`. Every
such target is retained under the cardinality rules below. A `retired` row is
never included in this normalized-label target set, never contributes to
`N_t`, and cannot become eligible or ambiguous through label equality or any
general lookup. Label equality:

```text
does not produce a global identity
does not produce a backend mapping
does not approve a candidate
does not prove canonical identity
```

A `pending` or `active` membership may independently add the exact referenced
eligible organization as structural candidate evidence for its account. When
that current edge directly names an existing `retired` organization row, D1-A
instead retains that exact target once as `ineligible_unapproved`; the target
is not admitted to normalized-label lookup. A label mismatch must not delete
that structural edge; it produces `membership_evidence_conflict`. A `revoked`
membership produces no current edge. A missing referenced organization row is
never fabricated.

Missing assignment or binding evidence must not silently delete a label
candidate. Any assignment or binding evidence that exists must satisfy every
frozen structural and site relationship. Exact registry relations arise only
from existing mapping rows and never from label equality.

Required scope has these exact classifications:

| Condition | Classification | Required reason |
|---|---|---|
| Required site/sheet scope is missing | `invalid_or_incomplete_source_identity` | `missing_required_scope` |
| Required site/sheet identifier or relationship is malformed or cannot resolve | `invalid_or_incomplete_source_identity` | `malformed_source_identity` |
| Site and sheet scopes are both known and their exact evidence contradicts | `target_state_conflict` | `cross_site_evidence` |

Missing or unresolved scope is never reclassified as cross-site evidence.
An item with missing, malformed, or unresolvable required scope has no
candidate relation because candidate construction cannot safely complete. When
both scopes are known and contradictory, every otherwise discovered target is
retained through the C1-A conflict accumulation rule as one
`ineligible_unapproved` relation whose ordered evidence union includes
`cross_site_evidence`; the conflict is never hidden by deleting the relation.

Relationship evidence affects a reviewed legacy-root item through these exact
rules:

| Evidence conflict | Item classification | Required item reason | Relation behavior |
|---|---|---|---|
| Current membership references a missing/ineligible organization, directly references an existing retired organization, or has disagreeing valid account/organization labels | `target_state_conflict` | `membership_evidence_conflict` | Preserve the exact referenced organization once as `ineligible_unapproved` when its row exists; fabricate no target when it does not |
| Existing active assignment is missing its organization/site, directly references an existing retired organization, or duplicates/conflicts on active scope | `target_state_conflict` | `assignment_evidence_conflict` | Preserve the exact affected existing organization once as `ineligible_unapproved` for every related reviewed item; fabricate no missing target |
| Existing active binding has a missing/mismatched/retired organization, mismatched assignment/sheet/site, lacks active same-vendor/same-site assignment, or duplicates active sheet scope | `target_state_conflict` | `binding_evidence_conflict` | Preserve the exact affected existing organization once as `ineligible_unapproved` for every related reviewed item; fabricate no missing target |

A `vendor_organization` `candidate_ref` has exactly one relation and exactly one
`relation_status` within an item. Before any relation object is constructed,
the implementation accumulates, by `candidate_ref`, the distinct applicable
organization-conflict evidence from this exact Section 8.2-ordered list:

```text
cross_site_evidence
membership_evidence_conflict
assignment_evidence_conflict
binding_evidence_conflict
```

If the accumulated set is nonempty, the one relation is
`ineligible_unapproved` and its `evidence_codes` is exactly that ordered union,
with minimum/maximum cardinality `1 / 4`. This one relation replaces the
otherwise eligible or ambiguous relation; an eligible/ambiguous and an
ineligible version must not coexist. First-wins, last-wins, repeated relations,
and loss of a later conflict are prohibited. Accumulation occurs before
relation construction and is not post-construction silent deduplication.

For an item classified `target_state_conflict`, the subset of item
`reason_codes` drawn from those four organization-conflict codes is exactly the
same distinct ordered union of every applicable item conflict. When no other
permitted target-state reason applies, the item reason array is exactly that
union. Multiple conflict causes for one `candidate_ref` increase
`candidate_relation_count` by exactly one, never by the number of causes.

D1-A applies only after a reviewed legacy-root item and its required source and
scope validity have been established. A current `pending`/`active` membership,
active assignment, or active binding must directly name the exact `vendor_id`
of an actually observed retired organization row. That target then has exactly
one `vendor_organization` relation, status `ineligible_unapproved`, and the
complete applicable C1-A evidence union. It must not coexist with an eligible
or ambiguous version. A relationship/target row never fabricates an item, a
missing organization never fabricates a relation, and D1-A never bypasses
missing/malformed-scope fail-closed behavior or classification precedence.

A target or relationship row with no corresponding reviewed legacy-root item
does not fabricate an item. It remains transaction-observed target-state
evidence covered by the source snapshot and evidence digest.

For every valid normalized-label evidence group:

```text
N_s = number of distinct reviewed source_record_ref values in the group
N_t = number of distinct active/disabled eligible organization targets in the group;
      retired organizations are excluded even when directly retained elsewhere
      by D1-A structural evidence
```

The exact base classification is:

| Cardinality | Relation status | Item classification | Required item reason | Required relation evidence |
|---|---|---|---|---|
| `N_t = 0`, account item | no relation | `no_match` | `orphan_vendor_account` | none |
| `N_t = 0`, task/contact/work-entry item | no relation | `no_match` | `orphan_business_label` | none |
| `N_s = 1`, `N_t = 1` | `eligible_unapproved` | `unique_eligible_match` | `exact_evidence_unapproved` | `exact_evidence_unapproved` |
| `N_s > 1`, `N_t = 1` | `eligible_unapproved` | `many_legacy_rows_to_one_canonical_identity` | `many_to_one_candidate_set` | `exact_evidence_unapproved` |
| `N_s = 1`, `N_t > 1` | every relation `ambiguous_unapproved` | `one_legacy_row_to_multiple_canonical_candidates` | `one_to_many_candidate_set` | `ambiguous_candidate` |
| `N_s > 1`, `N_t > 1` | every relation `ambiguous_unapproved` | `multiple_candidate_match` | `ambiguous_candidate` | `ambiguous_candidate` |

All participating items receive the applicable group cardinality
classification. A candidate is never selected by creation time, status
preference, UUID order, source order, or row order.

Existing mapping evidence is projected only onto the reviewed `vendor_account`
item whose physical positive integer `id` exactly equals a row's
`backend_principal_key` with `backend_kind = 'vendor'`. A mapping with no such
reviewed account fabricates neither an item nor a relation. A disabled identity
row is never searched or discovered generally; when an exact mapping names its
existing row, D2-A permits only the R2-A ineligible identity relation displayed
below. The exact projection is:

| Exact observed state | Mapping relation | Identity relation | Item classification and ordered reasons | Relation-count increment |
|---|---|---|---|---:|
| No vendor mapping for the account | none | none | Preserve the independently derived base/cardinality result | `0` |
| `active` mapping to exactly one existing `active` identity | `backend_principal_mapping` / `existing_consistent_unapproved` / `[existing_mapping_consistent]` | `global_identity` / `existing_consistent_unapproved` / `[existing_mapping_consistent]` | `already_mapped_consistent` / `[existing_mapping_consistent]` | `2` |
| `active` mapping whose identity target is missing | `backend_principal_mapping` / `existing_conflicting_unapproved` / `[registry_target_conflict, existing_mapping_conflicting]` | none; a target is never fabricated | `already_mapped_conflicting` / `[registry_target_conflict, existing_mapping_conflicting]` | `1` |
| `active` mapping to an existing `disabled` identity | `backend_principal_mapping` / `ineligible_unapproved` / `[ineligible_registry_state]` | `global_identity` / `ineligible_unapproved` / `[ineligible_registry_state]` | `target_state_conflict` / `[ineligible_registry_state]` | `2` |
| `disabled` mapping to an existing `active` or `disabled` identity | `backend_principal_mapping` / `ineligible_unapproved` / `[ineligible_registry_state]` | `global_identity` / `ineligible_unapproved` / `[ineligible_registry_state]` | `target_state_conflict` / `[ineligible_registry_state]` | `2` |
| `disabled` mapping whose identity target is missing | `backend_principal_mapping` / `existing_conflicting_unapproved` / `[registry_target_conflict, existing_mapping_conflicting]` | none; a target is never fabricated | `already_mapped_conflicting` / `[registry_target_conflict, existing_mapping_conflicting]` | `1` |

The relation triples in this table are respectively `candidate_kind`,
`relation_status`, and ordered `evidence_codes`. Item reasons use the same
displayed order, which is the Section 8.2 order. The item-level mapping
classification follows the frozen precedence: a missing identity target is an
existing-mapping conflict even when the mapping row is disabled; otherwise a
disabled mapping or identity is the lower target-state conflict.

For D2-A, the direct disabled-identity exception itself adds exactly one
`global_identity / ineligible_unapproved / [ineligible_registry_state]`
relation. The same R2-A row also retains its one mapping relation, so the full
row's existing relation-count increment remains exactly `2`; no prior R2-A
count changes. A missing identity row follows the displayed missing-target row
and never fabricates an identity relation.

All independently valid organization relations remain in the item when a
mapping classification wins precedence. If `O_i` is their count, the item's
exact relation count is `O_i` plus the increment in the table. Organization
IDs and global-identity IDs are different domains and must not be compared,
joined, or inferred equal.

Non-vendor mappings follow the complete C5-A boundary in Section 4.4 and never
produce candidate relations or vendor-item classification changes. Disabled
state is never treated as absent. Under a source that satisfies the required
physical constraints, one vendor account has at most one vendor mapping, one
vendor mapping names exactly one identity, and one global identity has at most
one mapping for backend kind `vendor`. Any observed duplicate/multiple
violation, one mapping purportedly resolving to multiple targets, or multiple
vendor mappings targeting one identity is malformed source/result-contract
evidence. It is never aggregated, deduplicated, sorted to select a winner, or
converted into variable relation arrays; Section 8.4 applies and no
mapping/identity relation is emitted for that incomplete run.

Classification precedence is exact and applies before the base cardinality
result:

```text
invalid or incomplete source
> existing mapping conflict
> target-state, structural, or cross-site conflict
> cardinality conflict
> existing mapping consistent
> no-match or unique eligible match
```

`stale_evidence_or_source_changed` remains in the frozen eleven-class
vocabulary but is unreachable in V1 under C4-A and therefore does not
participate in V1 precedence.

### 4.8 Source metadata

Every metadata statement is a module-level literal with an empty bind list.
Runtime PRAGMA construction, table-name interpolation, identifier quoting
helpers, caller-selected columns, and incidental SQLite row order are
prohibited. The metadata limits are exactly:

```text
MAX_METADATA_ROWS_PER_QUERY = 10000
MAX_XINFO_ROWS_PER_TABLE = 256
```

Reading one additional row is permitted only to prove overflow. The metadata
failure boundary has exactly two layers.

Fatal metadata capture/projection failures are:

- a metadata-statement exception;
- a result-row arity error;
- a Python value-type error, including `bool` in an integer position;
- metadata-result overflow;
- inability to reconstruct the complete canonical projection reliably;
- projection-serialization failure; or
- schema-fingerprint reconstruction failure.

Each is exit `4`, zero stdout, and the fixed internal marker after applicable
cleanup and no-touch handling. A tuple that fails arity or Python type
validation must never be converted to exit `3`.

After every required tuple has passed arity and Python type validation, the
closed D4-A metadata-content conflict vocabulary has exactly these eight
categories and no others:

1. missing source;
2. wrong owner;
3. wrong object type;
4. case alias;
5. duplicate source identity;
6. duplicate `cid` or duplicate column name, as two exact predicates within
   this one category;
7. missing required column; and
8. required xinfo conformance mismatch against the exact matrix below.

Each is source malformation or absence under Section 8.4, exit `3`, and an
incomplete envelope after successful cleanup and no-touch proof. An
implementation must not invent, infer, or configure another exit-`3` metadata
content category. D3-A topology-content failure is separately closed below and
is not a ninth schema-conflict category. Fatal capture/projection failures stay
under C2-A exit `4` and zero stdout.

#### Topology statement

```sql
SELECT seq, name, file
FROM pragma_database_list
ORDER BY seq;
```

The returned positions are exactly `(seq, name, file)`. Each row is exactly
`(int, str, str)`; `bool` is never an integer. Arity or Python-type failure is a
fatal C2-A capture failure. After type validation, `seq` must be nonnegative
and unique, `name` must be nonempty and unique, and there must be exactly one
`main` row. A content violation is completely observed topology/source
malformation and follows exit `3`; it is not a tuple-capture failure.
`attached_count` is the number of rows whose name is neither `main` nor `temp`;
`main_only` is true exactly when the single `main` row exists and
`attached_count = 0`. Complete evidence requires `main_only = true`. The
explicit `ORDER BY seq` is the canonical row order; no secondary runtime sort
is permitted.

D3-A applies exactly when statement execution, row arity, Python value types,
the integer/bool distinction, metadata row bound, and canonical projection
capability all succeed, but any of these content predicates fails:

- `seq` values are not unique nonnegative integers;
- a `name` is empty;
- `name` values are not unique;
- the number of exact `main` rows is not one; or
- `main_only` is not true.

The implementation then completes only the remaining frozen metadata
statements needed for the canonical schema projection, non-null schema
fingerprint, three canonical topology fields, and evidence binding. Their
type-valid values are retained for fingerprinting only; the D3-A projection
dominates per-table content classification for this run, so it gains no
additional table-specific reason. No data statement is executed. If any
remaining metadata statement instead has an exception, arity/type/bool error,
overflow, projection/serialization failure, or fingerprint-reconstruction
failure, C2-A replaces D3-A with exit `4`, zero stdout, and the fixed internal
marker.

After successful cleanup and no-touch proof, the D3-A result is exactly exit
`3` with one canonical incomplete envelope and all of these invariants:

```text
target_schema_identity.availability = "incomplete"
target_schema_identity.schema_fingerprint_sha256 = non-null uppercase SHA-256
candidate_item_count = 12
candidate_relation_count = 0
classified_item_count = 12
unresolved_item_count = 12
excluded_item_count = 0
fixed_query_count = 0
all twelve source_row_counts.row_count values = null
invalid_or_incomplete_source_identity classification count = 12
every other classification count = 0
operational_reason_codes =
  [malformed_source_identity, insufficient_evidence]
```

There is exactly one `source_contract` item for each required Section 4.9
table, using that table's existing source-reference/provenance recipes. Every
item has classification `invalid_or_incomplete_source_identity`, reasons
exactly `[malformed_source_identity]`, empty `candidate_relations`, null scopes,
and missing label evidence. No business-row item and no thirteenth
topology/global item exists. The three serialized topology fields are the
canonical observed values; `main_only` can remain true when another listed
topology predicate caused D3-A, but availability and the twelve-item projection
remain incomplete.

#### Table-list and schema statements

```sql
SELECT schema, name, type, ncol, wr, strict
FROM pragma_table_list
ORDER BY
    schema COLLATE BINARY,
    name COLLATE BINARY,
    type COLLATE BINARY,
    ncol,
    wr,
    strict;
```

Each row is exactly `(str, str, str, int, int, int)` in those positions;
booleans are rejected in integer positions. Every returned row is retained up
to the metadata bound in the exact SQL order. Duplicate complete tuples remain
observable, but duplicate source-object identities make that source malformed.

```sql
SELECT type, name, tbl_name, sql
FROM main.sqlite_schema
ORDER BY
    type COLLATE BINARY,
    name COLLATE BINARY,
    tbl_name COLLATE BINARY,
    sql IS NOT NULL,
    sql COLLATE BINARY;
```

```sql
SELECT type, name, tbl_name, sql
FROM temp.sqlite_schema
ORDER BY
    type COLLATE BINARY,
    name COLLATE BINARY,
    tbl_name COLLATE BINARY,
    sql IS NOT NULL,
    sql COLLATE BINARY;
```

Each schema row is exactly `(str, str, str, str-or-null)` in the selected
positions. Both complete result sets use their displayed SQL order.
`temp_object_count` is exactly the number of validated rows returned by the
temp statement. No implementation-selected schema column or secondary sort is
accepted.

The source-row selection predicate used by the schema fingerprint is exact.
`ASCII_LOWER` changes only ASCII `A` through `Z` to `a` through `z` and leaves
every other code point unchanged. For each expected lowercase ASCII source
table name `t`:

```text
source_table_list_rows =
  every pragma_table_list row for which ASCII_LOWER(name) == t

source_main_schema_rows =
  every main.sqlite_schema row for which
  ASCII_LOWER(name) == t or ASCII_LOWER(tbl_name) == t

source_temp_schema_rows =
  every temp.sqlite_schema row for which
  ASCII_LOWER(name) == t or ASCII_LOWER(tbl_name) == t
```

Each selected array retains the displayed SQL order. An unrelated row is not
selected and never expands read authority. An available source requires one
case-exact `main` table identity, its case-exact `main.sqlite_schema` table row,
no case-insensitive competing table/view in any schema, no temp source/shadow,
and a valid xinfo projection. Zero source rows across table-list/main/temp plus
zero xinfo rows means missing. Failure to produce the required single table
identity and its single schema table row is `missing source`. A wrong-case
match is `case alias`; a non-`main` match is `wrong owner`; a non-table match is
`wrong object type`; and more than one competing match is `duplicate source
identity`. No other type-valid table-list/schema content predicate is an
exit-`3` conflict. Index rows whose `tbl_name` is exactly the source table are
retained in the fingerprint but do not expand the approved data columns. Extra
unrelated objects are permitted and ignored by this per-source projection.

#### Exact table-xinfo statements

The implementation contains all twelve independent literals below. It may
iterate over the predeclared constants in the displayed order but must not
substitute a table name into SQL.

```sql
SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('sites', 'main')
ORDER BY cid;
```

```sql
SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('sheets', 'main')
ORDER BY cid;
```

```sql
SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('tasks', 'main')
ORDER BY cid;
```

```sql
SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('vendor_accounts', 'main')
ORDER BY cid;
```

```sql
SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('vendor_contacts', 'main')
ORDER BY cid;
```

```sql
SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('vendor_work_entries', 'main')
ORDER BY cid;
```

```sql
SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('vendor_organizations', 'main')
ORDER BY cid;
```

```sql
SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('vendor_organization_memberships', 'main')
ORDER BY cid;
```

```sql
SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('vendor_site_assignments', 'main')
ORDER BY cid;
```

```sql
SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('sheet_vendor_bindings', 'main')
ORDER BY cid;
```

```sql
SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('global_identities', 'main')
ORDER BY cid;
```

```sql
SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('backend_principal_mappings', 'main')
ORDER BY cid;
```

Every xinfo row is exactly
`(int, str, str, int, str-or-null, int, int)` in the selected positions;
booleans are rejected in integer positions. An arity or Python-type failure is
fatal under C2-A. Rows retain `ORDER BY cid` order. After tuple validation,
duplicate `cid`, duplicate exact or case-aliased required `name`, a negative
`cid`, missing required columns, or required metadata outside the exact matrix
below exhaust the xinfo conflicts. A missing required column contributes
`missing_required_source`. Duplicate `cid`, duplicate column name, and exact
required-xinfo conformance mismatch contribute `malformed_source_identity`.
Zero xinfo rows are valid only when the independent object proof says the source
is missing; otherwise they prove a missing required column. No other type-valid
xinfo content predicate is an exit-`3` conflict.

The required xinfo conformance notation is exactly
`column TYPE/notnull/pk/hidden`. Required declared types are compared only
after trimming ASCII surrounding whitespace and applying ASCII uppercase.
Each required column name is case-exact and occurs exactly once. Every required
`cid` is an exact nonnegative Python integer, not `bool`, and every observed
`cid` is unique; its actual positional value is fingerprint evidence only and
is not compared to a frozen position. The exact matrix is:

| Required table | Exact required xinfo conformance |
|---|---|
| `sites` | `id INTEGER/0/1/0` |
| `sheets` | `id INTEGER/0/1/0`; `site_id INTEGER/0/0/0` |
| `tasks` | `id INTEGER/0/1/0`; `sheet_id INTEGER/0/0/0`; `vendor TEXT/0/0/0` |
| `vendor_accounts` | `id INTEGER/0/1/0`; `vendor_name TEXT/1/0/0` |
| `vendor_contacts` | `id INTEGER/0/1/0`; `sheet_id INTEGER/1/0/0`; `vendor_name TEXT/1/0/0` |
| `vendor_work_entries` | `id INTEGER/0/1/0`; `sheet_id INTEGER/1/0/0`; `vendor_name TEXT/1/0/0` |
| `vendor_organizations` | `vendor_id TEXT/1/1/0`; `display_name TEXT/1/0/0`; `organization_status TEXT/1/0/0` |
| `vendor_organization_memberships` | `vendor_membership_id TEXT/1/1/0`; `vendor_id TEXT/1/0/0`; `vendor_account_id INTEGER/1/0/0`; `membership_role TEXT/1/0/0`; `membership_status TEXT/1/0/0` |
| `vendor_site_assignments` | `vendor_site_assignment_id TEXT/1/1/0`; `vendor_id TEXT/1/0/0`; `site_id INTEGER/1/0/0`; `assignment_status TEXT/1/0/0` |
| `sheet_vendor_bindings` | `sheet_vendor_binding_id TEXT/1/1/0`; `vendor_id TEXT/1/0/0`; `sheet_id INTEGER/1/0/0`; `site_id INTEGER/1/0/0`; `vendor_site_assignment_id TEXT/1/0/0`; `binding_status TEXT/1/0/0` |
| `global_identities` | `global_identity_id TEXT/1/1/0`; `registry_status TEXT/1/0/0` |
| `backend_principal_mappings` | `backend_principal_mapping_id TEXT/1/1/0`; `global_identity_id TEXT/1/0/0`; `backend_kind TEXT/1/0/0`; `backend_principal_key ANY/1/0/0`; `mapping_status TEXT/1/0/0` |

`dflt_value` is fingerprint evidence only and does not decide V1 source
availability. Extra columns are allowed, are retained completely in the
fingerprint, and never expand an approved data statement. Likewise,
`pragma_table_list.ncol`, `wr`, and `strict`, and raw schema SQL are fingerprint
evidence only. Their values must never be promoted to an availability conflict
or implementation-defined exit-`3` category. They do not replace or relax the
VENDOR-ID-002 physical-schema checker or the identity-registry physical-schema
checker. Data-level duplicate mapping or cardinality violations can still make
`backend_principal_mappings` source-contract evidence incomplete.

#### Exact schema-fingerprint projection

The canonical projection input is this exact JSON-array shape:

```text
[
  "VENDOR_ID_004B_SOURCE_SCHEMA_V1",
  [
    [
      fixed_query_id,
      exact_source_table_name,
      [[schema, name, type, ncol, wr, strict], ...],
      [[type, name, tbl_name, sql_or_null], ...],
      [[type, name, tbl_name, sql_or_null], ...],
      [[cid, name, type, notnull, dflt_value_or_null, pk, hidden], ...]
    ],
    ... exactly twelve entries ...
  ]
]
```

Within each entry the four row arrays are, in order,
`source_table_list_rows`, `source_main_schema_rows`,
`source_temp_schema_rows`, and the complete xinfo result. Their contents are
defined only by the exact predicates and statements above. Entries use the
Section 5.5 fixed-query-ID order. A genuinely missing source therefore has
empty table-list, main-schema, temp-schema, and xinfo arrays. A malformed
source retains every successfully validated observed row; no row is repaired,
deduplicated, or synthesized.

Canonical JSON uses UTF-8 strict, `ensure_ascii=false`, `allow_nan=false`,
`separators=(',', ':')`, no BOM, no CR, no trailing whitespace, and no terminal
LF. `schema_fingerprint_sha256` is uppercase SHA-256 of those exact bytes. It is
non-null in every emitted complete or incomplete V1 envelope because all
required metadata statements, tuple validation, canonical projection,
serialization, and hash reconstruction completed. A projection can contain a
missing or malformed source and still have a non-null observed fingerprint.
If complete projection reconstruction, serialization, or fingerprinting is
impossible, C2-A requires exit `4` and zero stdout, so no envelope containing a
null fingerprint is emitted. The field's syntactic nullable alternative is
reserved but unreachable in V1. The fingerprint is an observed-schema
identity, not a schema-conformance PASS.

### 4.9 Exact fixed data-query family and bounded row counts

The exact query-ID-to-SQL mapping is:

```sql
-- V004B_QUERY_SITES_V1
SELECT id FROM main.sites ORDER BY id;

-- V004B_QUERY_SHEETS_V1
SELECT id, site_id FROM main.sheets ORDER BY id;

-- V004B_QUERY_TASKS_V1
SELECT id, sheet_id, vendor FROM main.tasks ORDER BY id;

-- V004B_QUERY_VENDOR_ACCOUNTS_V1
SELECT id, vendor_name FROM main.vendor_accounts ORDER BY id;

-- V004B_QUERY_VENDOR_CONTACTS_V1
SELECT id, sheet_id, vendor_name FROM main.vendor_contacts ORDER BY id;

-- V004B_QUERY_VENDOR_WORK_ENTRIES_V1
SELECT id, sheet_id, vendor_name FROM main.vendor_work_entries ORDER BY id;

-- V004B_QUERY_VENDOR_ORGANIZATIONS_V1
SELECT vendor_id, display_name, organization_status
FROM main.vendor_organizations
ORDER BY vendor_id COLLATE BINARY;

-- V004B_QUERY_VENDOR_ORGANIZATION_MEMBERSHIPS_V1
SELECT vendor_membership_id, vendor_id, vendor_account_id,
       membership_role, membership_status
FROM main.vendor_organization_memberships
ORDER BY vendor_membership_id COLLATE BINARY;

-- V004B_QUERY_VENDOR_SITE_ASSIGNMENTS_V1
SELECT vendor_site_assignment_id, vendor_id, site_id, assignment_status
FROM main.vendor_site_assignments
ORDER BY vendor_site_assignment_id COLLATE BINARY;

-- V004B_QUERY_SHEET_VENDOR_BINDINGS_V1
SELECT sheet_vendor_binding_id, vendor_id, sheet_id, site_id,
       vendor_site_assignment_id, binding_status
FROM main.sheet_vendor_bindings
ORDER BY sheet_vendor_binding_id COLLATE BINARY;

-- V004B_QUERY_GLOBAL_IDENTITIES_V1
SELECT global_identity_id, registry_status
FROM main.global_identities
ORDER BY global_identity_id COLLATE BINARY;

-- V004B_QUERY_BACKEND_PRINCIPAL_MAPPINGS_V1
SELECT backend_principal_mapping_id, global_identity_id, backend_kind,
       backend_principal_key, mapping_status
FROM main.backend_principal_mappings
ORDER BY backend_principal_mapping_id COLLATE BINARY;
```

Every statement is one independent module-level literal with an exactly empty
bind list. Runtime `WHERE`, filter, `LIMIT`, `OFFSET`, table-name interpolation,
identifier construction, caller SQL, and caller-selected order or columns are
prohibited.

The expected tuple positions and canonical value types are:

| Query ID | Exact returned tuple |
|---|---|
| `V004B_QUERY_SITES_V1` | `(positive-int id)` |
| `V004B_QUERY_SHEETS_V1` | `(positive-int id, positive-int-or-null site_id)` |
| `V004B_QUERY_TASKS_V1` | `(positive-int id, positive-int-or-null sheet_id, opaque-label-value vendor)` |
| `V004B_QUERY_VENDOR_ACCOUNTS_V1` | `(positive-int id, opaque-label-value vendor_name)` |
| `V004B_QUERY_VENDOR_CONTACTS_V1` | `(positive-int id, positive-int-or-null sheet_id, opaque-label-value vendor_name)` |
| `V004B_QUERY_VENDOR_WORK_ENTRIES_V1` | `(positive-int id, positive-int-or-null sheet_id, opaque-label-value vendor_name)` |
| `V004B_QUERY_VENDOR_ORGANIZATIONS_V1` | `(str vendor_id, str display_name, str organization_status)` |
| `V004B_QUERY_VENDOR_ORGANIZATION_MEMBERSHIPS_V1` | `(str membership_id, str vendor_id, positive-int account_id, str role, str status)` |
| `V004B_QUERY_VENDOR_SITE_ASSIGNMENTS_V1` | `(str assignment_id, str vendor_id, positive-int site_id, str status)` |
| `V004B_QUERY_SHEET_VENDOR_BINDINGS_V1` | `(str binding_id, str vendor_id, positive-int sheet_id, positive-int site_id, str assignment_id, str status)` |
| `V004B_QUERY_GLOBAL_IDENTITIES_V1` | `(str global_identity_id, str registry_status)` |
| `V004B_QUERY_BACKEND_PRINCIPAL_MAPPINGS_V1` | `(str mapping_id, str global_identity_id, str backend_kind, positive-int backend_principal_key, str mapping_status)` |

`positive-int` always means exact Python `int`, not `bool`, greater than zero.
An opaque label position accepts any Python value only for later label-validity
classification; it does not weaken tuple arity/order or other position checks.
Text identifiers and statuses must be exact strings and must then satisfy their
frozen canonical/status contracts.

The exact row bounds are:

```text
MAX_ROWS_PER_QUERY = 10000
MAX_ROWS_ALL_QUERIES = 50000
```

The implementation may read row 10001 only to prove per-query overflow. Empty
successful results count as zero. A query's row count becomes a nonnegative
integer only after complete consumption, tuple validation, duplicate physical
identity validation, and both bounds pass. A metadata-skipped, failed, or
overflowed query has null row count. The query that would make the aggregate
exceed 50000 fails and has null row count.

After complete metadata capture, data statements are considered in fixed
query-ID order. A source proved missing or malformed by metadata is skipped;
later metadata-compatible statements remain eligible. The first statement
that is actually executed and encounters an execution, result-contract, or
bound failure stops every later data statement. Later unattempted row counts
are null. Non-attempt alone never fabricates a `source_contract` item; only
successful metadata proof or an actually attempted failing query can do so.

`fixed_query_count` is exactly the number of twelve `source_row_counts`
entries whose `row_count` is non-null. It is `12` for complete evidence and
`0` through `11` for incomplete evidence. A proved source/query failure emits
exit `3` only after successful cleanup and verified no-touch evidence. Fatal
metadata capture, canonical serialization/hash/count reconstruction,
authorizer, rollback, or no-touch failure emits exit `4` and zero stdout.

## 5. Safe-reference profile

### 5.1 Profile and output

The exact profile name is:

```text
HMAC_SHA256_SAFE_REFERENCE_V1
```

The algorithm is HMAC-SHA-256. Every safe reference is exactly:

```text
hmac-sha256-v1:<64 lowercase hexadecimal characters>
```

Safe references are opaque evidence locators. They are not `vendor_id`,
`global_identity_id`, `approved_mapping_id`, an authorization token, or proof
that two records have the same identity.

### 5.2 Key-file input

The key is exactly 32 bytes represented by exactly 64 lowercase hexadecimal
ASCII characters. The mandatory key file:

- is supplied only by the explicit `--reference-key-file` option;
- is an absolute path strictly below the resolved Windows OS system-temp root;
- is a regular file with exactly one link;
- is not a symlink, junction, reparse point, hardlink, repository path, or
  repository descendant;
- contains exactly 64 lowercase hexadecimal bytes and optionally one final LF;
- contains no CR, BOM, prefix, suffix, whitespace, or second line; and
- is opened only after containment, identity, and file-attribute validation.

The tool must not obtain the key from a CLI value, environment variable,
browser, database, stdin, repository default, network source, config file, or
fallback path. It must not create, rotate, persist, copy, emit, log, delete, or
overwrite the key file. A synthetic test harness owns key-fixture creation and
cleanup and must not claim secure memory erasure.

DEV or Production key custody, rotation, retention, acquisition, and use are
not authorized by this contract.

### 5.3 Reference domains

The closed reference-domain vocabulary is, in this exact order:

```text
source_record
candidate_relation
site_scope
sheet_scope
label_evidence
provenance
source_snapshot
```

An unknown domain is an internal invariant failure.

### 5.4 Canonical HMAC preimage

The HMAC preimage is the UTF-8 encoding of one JSON array with this exact
positional order:

```text
[
  profile,
  reference_domain,
  environment,
  source_kind,
  source_table,
  typed_source_key,
  typed_site_scope_or_null,
  typed_sheet_scope_or_null,
  typed_domain_payload_or_null
]
```

Canonical JSON bytes use:

```text
UTF-8 strict
ensure_ascii = false
allow_nan = false
separators = (",", ":")
no BOM
no trailing whitespace
no terminal LF
```

The array fixes field order; object-key ordering is not part of this recipe.
Each typed value is exactly one of:

```text
["integer", "<base-10 canonical positive integer>"]
["text", "<exact validated text>"]
null
```

Integer text has no sign, leading zero, decimal point, exponent, whitespace,
or locale formatting. Boolean is never an integer. Text is not trimmed or
normalized unless the applicable source contract explicitly defines the
domain payload as a normalized label. A missing scope is represented by JSON
`null`; it is never omitted, replaced by an empty string, or represented by
zero.

The domain payload is:

| Domain | Exact payload |
|---|---|
| `source_record` | `null` |
| `candidate_relation` | typed candidate target key |
| `site_scope` | typed site key |
| `sheet_scope` | typed sheet key |
| `label_evidence` | `['text', '<discovery-normalized-label>']` or `null` when invalid/missing |
| `provenance` | `['text', '<fixed-query-id>']` |
| `source_snapshot` | `['text', '<uppercase-source-sha256>']` |

`generated_at`, `expires_at`, execution ID, process ID, path text, output order,
and system time are excluded from every stable source/candidate reference
preimage. Raw preimage values exist only transiently in memory for HMAC
calculation and are never returned or logged.

### 5.5 Exact field-to-HMAC recipes

The following notation is exact:

```text
E = "synthetic_local"
I(n) = ["integer", "<canonical positive base-10 n>"]
T(s) = ["text", "<exact validated text s>"]
K_i = the reviewed item's typed physical primary key
S_i = the exact atomic typed site scope or null from Section 4.6
H_i = the exact atomic typed sheet scope or null from Section 4.6
Q_i = the exact fixed-query ID that produced the item
```

For `vendor_account`, `task_vendor_label`, `vendor_contact_label`, and
`vendor_work_entry_label`, `K_i` is `I(id)`. For `source_contract`, `K_i` is
`T(exact-required-table-name)`. A query ordinal, row offset, result position,
path, label, username, or incidental ordering value is never `K_i`.

For every scoped legacy item, `S_i` and `H_i` are either both non-null under
the successful Section 4.6 chain or both null. For `vendor_account` and
`source_contract`, both are always null. No reference recipe may recompute,
override, partially retain, or derive scope from candidate-side evidence.

The closed HMAC-only kind tags are:

```text
source_database
site_scope
sheet_scope
vendor_organization
global_identity
backend_principal_mapping
```

They are preimage namespace tags, not additional candidate-item source kinds.

The exact recipes are:

| Output field | `reference_domain` | `environment` | `source_kind` | `source_table` | `typed_source_key` | `typed_site_scope_or_null` | `typed_sheet_scope_or_null` | `typed_domain_payload_or_null` |
|---|---|---|---|---|---|---|---|---|
| `source_snapshot_identity.source_database_ref` | `source_snapshot` | `E` | `source_database` | `main` | `T("main")` | `null` | `null` | `T(source_sha256_before-uppercase)` |
| Candidate item `source_record_ref` | `source_record` | `E` | exact item source kind | exact item source table | `K_i` | `S_i` | `H_i` | `null` |
| Candidate item `site_scope_ref` | `site_scope` | `E` | `site_scope` | `sites` | `I(site_id)` | `I(site_id)` | `null` | `I(site_id)` |
| Candidate item `sheet_scope_ref` | `sheet_scope` | `E` | `sheet_scope` | `sheets` | `I(sheet_id)` | `I(site_id)` | `I(sheet_id)` | `I(sheet_id)` |
| `label_evidence.safe_label_ref` | `label_evidence` | `E` | exact item source kind | exact item source table | `K_i` | `S_i` | `H_i` | `T(discovery-normalized-label)` |
| Organization `candidate_ref` | `candidate_relation` | `E` | `vendor_organization` | `vendor_organizations` | `T(vendor_id)` | `S_i` | `H_i` | `T(vendor_id)` |
| Identity `candidate_ref` | `candidate_relation` | `E` | `global_identity` | `global_identities` | `T(global_identity_id)` | `S_i` | `H_i` | `T(global_identity_id)` |
| Mapping `candidate_ref` | `candidate_relation` | `E` | `backend_principal_mapping` | `backend_principal_mappings` | `T(backend_principal_mapping_id)` | `S_i` | `H_i` | `T(backend_principal_mapping_id)` |
| Candidate item `provenance_ref` | `provenance` | `E` | exact item source kind | exact item source table | `K_i` | `S_i` | `H_i` | `T(Q_i)` |
| `unresolved_refs[]` member | no new HMAC | n/a | n/a | n/a | exact copy of an item's `source_record_ref` | n/a | n/a | n/a |
| `excluded_refs[]` member | no new HMAC | n/a | n/a | n/a | exact copy of an item's `source_record_ref` | n/a | n/a | n/a |

Candidate references always use the target kind, target table, and target key.
They never reuse the source item's kind/table/key tuple. The source item's
site/sheet scope remains in the target reference so an equal target examined
under different scopes cannot collide.

The database reference depends on the exact `main` database bytes and never on
path text. Two byte-identical accepted synthetic fixtures under different
allowed paths produce the same `source_database_ref` for the same key and
environment. A changed byte hash changes the reference.

The closed fixed-query ID vocabulary is, in this exact order:

```text
V004B_QUERY_SITES_V1
V004B_QUERY_SHEETS_V1
V004B_QUERY_TASKS_V1
V004B_QUERY_VENDOR_ACCOUNTS_V1
V004B_QUERY_VENDOR_CONTACTS_V1
V004B_QUERY_VENDOR_WORK_ENTRIES_V1
V004B_QUERY_VENDOR_ORGANIZATIONS_V1
V004B_QUERY_VENDOR_ORGANIZATION_MEMBERSHIPS_V1
V004B_QUERY_VENDOR_SITE_ASSIGNMENTS_V1
V004B_QUERY_SHEET_VENDOR_BINDINGS_V1
V004B_QUERY_GLOBAL_IDENTITIES_V1
V004B_QUERY_BACKEND_PRINCIPAL_MAPPINGS_V1
```

Each query ID is bound to the same-named exact source table; no caller-selected
or runtime-generated query ID is accepted. A `source_contract` item's
`provenance_ref` uses the fixed query ID for the exact required source that was
proved missing or malformed.

Because domain, environment, kind, table, typed key, and both scopes are all
positional preimage members, equal raw values in different domains, tables, or
scopes do not collide. `generated_at`, `expires_at`, execution ID, process ID,
system time, path text, and output order never enter a stable reference. Raw
IDs and labels never enter stdout, stderr, logs, exception text, or a
field-level unkeyed digest. The full-file SHA-256 used for filesystem no-touch
proof is not a per-field identity digest.

## 6. Invocation and lifecycle contract

### 6.1 Canonical path and CLI

The future canonical implementation path is exactly:

```text
tools/discover_vendor_identity_evidence.py
```

At the separately authorized `004B1` stage this exact path may exist only as a
non-executable pure-core source: it has no `__main__`, CLI parser, stdout,
SQLite, filesystem, environment, or runtime capability. The CLI obligations
below become mandatory only when the separately authorized `004B2` stage adds
the first executable integration at this same path. This staged source rule
does not create an alternate implementation path or relax the final CLI.

Its V1 CLI accepts only these mandatory options, exactly once each:

```text
--db-path <absolute-system-temp-sqlite-path>
--environment synthetic_local
--execution-id <lowercase-rfc9562-uuidv4>
--repository-commit <40-lowercase-hex>
--generated-at <YYYY-MM-DDTHH:MM:SSZ>
--expires-at <YYYY-MM-DDTHH:MM:SSZ>
--reference-key-file <absolute-system-temp-key-path>
```

`expires_at` must be strictly later than `generated_at`. Both values are
caller-supplied exact UTC-seconds strings and round-trip through strict
Gregorian parsing. The tool never reads the system clock.

There are no defaults, positional inputs, short options, abbreviations,
duplicate options, response files, config files, stdin inputs, environment
fallbacks, backend overrides, Production flags, output paths, filters, limits,
site selectors, sheet selectors, vendor selectors, apply modes, or repair
modes.

### 6.2 Supported environment and backend

The only accepted environment value is exact lowercase:

```text
synthetic_local
```

The only accepted backend is SQLite inferred from the validated disposable DB
file. There is no backend option. Repository databases, `site.db`, DEV,
Staging, Production, PostgreSQL, remote paths, network paths, and live copies
are rejected before connection.

### 6.3 Output and exits

The first executable implementation at `004B2` emits only canonical JSON to
stdout. It creates no
artifact, report, cache, temporary output, clipboard data, upload, network
request, database table, log file, or sidecar.

Exit codes are exactly:

| Exit | Meaning | stdout | stderr |
|---:|---|---|---|
| `0` | Complete evidence | Canonical JSON plus one LF | Empty |
| `2` | Input rejection | Empty | Fixed non-sensitive input marker plus one LF |
| `3` | Operationally incomplete evidence | Canonical incomplete JSON plus one LF | Empty |
| `4` | Internal invariant or no-touch proof failure | Empty | Fixed non-sensitive internal marker plus one LF |

The exact stderr markers are:

```text
VENDOR-ID-004B DISCOVERY INPUT REJECTED
VENDOR-ID-004B DISCOVERY INTERNAL FAILURE
```

Each displayed marker is UTF-8 strict ASCII with exactly one terminal LF.
The input marker is used only for exit `2`; the internal marker is used only
for exit `4`.

No traceback, raw path, source value, key material, SQL text, exception text,
credential, or parser diagnostic may be emitted.

## 7. Exact canonical evidence envelope

### 7.1 Top-level shape

The result has exactly these fifteen top-level keys and no others:

```text
{
  "environment": "synthetic_local",
  "source_repository_commit": str,
  "discovery_implementation_identity": object,
  "discovery_execution_id": str,
  "generated_at": str,
  "source_snapshot_identity": object,
  "target_schema_identity": object,
  "candidate_set": array,
  "conflict_classification": array,
  "counts_and_safe_digests": object,
  "unresolved_and_excluded": object,
  "database_access_evidence": object,
  "provenance": object,
  "expires_at": str,
  "staleness_conditions": array
}
```

Object keys are serialized using Unicode code-point order with
`sort_keys=true`. Arrays retain the semantic order frozen below. Canonical JSON
uses UTF-8, `ensure_ascii=false`, `allow_nan=false`, separators `(',', ':')`,
no BOM, no CR, no trailing spaces, and exactly one terminal LF only at the CLI
stdout boundary.

### 7.2 Implementation and snapshot identity

`discovery_implementation_identity` is exactly:

```text
{
  "contract_version": "VENDOR_ID_004B_CANDIDATE_EVIDENCE_V1",
  "path": "tools/discover_vendor_identity_evidence.py",
  "source_sha256": "<64 uppercase hex>"
}
```

`source_sha256` is uppercase SHA-256 of the raw bytes of exactly the canonical
tool file named by `path`. It does not hash, attest, or stand in for Python,
SQLite, Unicode data, standard-library, operating-system, or other dependency
bytes. Runtime equivalence is a separate acceptance-environment precondition
under Section 7.5; no unlisted dependency digest field exists in V1.

`source_snapshot_identity` is exactly:

```text
{
  "source_database_ref": safe-reference,
  "file_size_before": nonnegative-int,
  "file_size_after": nonnegative-int,
  "mtime_ns_before": nonnegative-int,
  "mtime_ns_after": nonnegative-int,
  "source_sha256_before": "<64 uppercase hex>",
  "source_sha256_after": "<64 uppercase hex>",
  "sidecars_before": {"journal": bool, "shm": bool, "wal": bool},
  "sidecars_after": {"journal": bool, "shm": bool, "wal": bool},
  "topology": {
    "attached_count": nonnegative-int | null,
    "main_only": bool | null,
    "temp_object_count": nonnegative-int | null
  }
}
```

Topology nullability is all-or-none. A pre-topology operational failure uses
three nulls. Once the topology statement yields a type-valid, bounded,
canonically projectable row set, all three values remain non-null in the
envelope, including a D3-A topology-content failure and any later fixed-query
failure. A complete envelope cannot contain a null topology value.

`target_schema_identity` is exactly:

```text
{
  "projection_version": "VENDOR_ID_004B_SOURCE_SCHEMA_V1",
  "availability": "available" | "incomplete",
  "schema_fingerprint_sha256": "<64 uppercase hex>" | null,
  "source_table_count": 12,
  "source_row_counts": [
    {"query_id": "V004B_QUERY_SITES_V1", "row_count": nonnegative-int | null},
    {"query_id": "V004B_QUERY_SHEETS_V1", "row_count": nonnegative-int | null},
    {"query_id": "V004B_QUERY_TASKS_V1", "row_count": nonnegative-int | null},
    {"query_id": "V004B_QUERY_VENDOR_ACCOUNTS_V1", "row_count": nonnegative-int | null},
    {"query_id": "V004B_QUERY_VENDOR_CONTACTS_V1", "row_count": nonnegative-int | null},
    {"query_id": "V004B_QUERY_VENDOR_WORK_ENTRIES_V1", "row_count": nonnegative-int | null},
    {"query_id": "V004B_QUERY_VENDOR_ORGANIZATIONS_V1", "row_count": nonnegative-int | null},
    {"query_id": "V004B_QUERY_VENDOR_ORGANIZATION_MEMBERSHIPS_V1", "row_count": nonnegative-int | null},
    {"query_id": "V004B_QUERY_VENDOR_SITE_ASSIGNMENTS_V1", "row_count": nonnegative-int | null},
    {"query_id": "V004B_QUERY_SHEET_VENDOR_BINDINGS_V1", "row_count": nonnegative-int | null},
    {"query_id": "V004B_QUERY_GLOBAL_IDENTITIES_V1", "row_count": nonnegative-int | null},
    {"query_id": "V004B_QUERY_BACKEND_PRINCIPAL_MAPPINGS_V1", "row_count": nonnegative-int | null}
  ]
}
```

The array always contains exactly those twelve objects in that order. Its
counts, null behavior, bounds, and relationship to `fixed_query_count` are
exactly Section 4.9. This changes only the nested
`target_schema_identity` shape; the top-level envelope remains exactly the
fifteen keys in Section 7.1.

### 7.3 Candidate item

Every `candidate_set` member has exactly these keys:

```text
{
  "source_kind": str,
  "source_table": str,
  "source_record_ref": safe-reference,
  "source_environment": "synthetic_local",
  "site_scope_ref": safe-reference | null,
  "sheet_scope_ref": safe-reference | null,
  "label_evidence": {
    "safe_label_ref": safe-reference | null,
    "normalization_profile": "VENDOR_DISCOVERY_EVIDENCE_NORMALIZATION_V1",
    "validity": "valid" | "invalid" | "missing"
  },
  "candidate_relations": [candidate-relation, ...],
  "classification": classification,
  "reason_codes": [reason-code, ...],
  "provenance_ref": safe-reference
}
```

The closed `source_kind` vocabulary is:

```text
vendor_account
task_vendor_label
vendor_contact_label
vendor_work_entry_label
source_contract
```

The exact source-table mapping is:

| `source_kind` | `source_table` | Typed source key |
|---|---|---|
| `vendor_account` | `vendor_accounts` | Physical positive integer `id` |
| `task_vendor_label` | `tasks` | Physical positive integer `id` |
| `vendor_contact_label` | `vendor_contacts` | Physical positive integer `id` |
| `vendor_work_entry_label` | `vendor_work_entries` | Physical positive integer `id` |
| `source_contract` | Exact required table name | Same exact table name as typed text |

No other source-kind/table pair is valid. Organization, membership,
assignment, binding, global-identity, and backend-mapping rows contribute only
the non-item evidence frozen in Section 4.5.

Exactly one `source_contract` item exists for each distinct required table
proved missing, malformed, or failed under Section 8.4, whether or not another
source's safely queried business-row items can still exist. Multiple failures
for the same table are coalesced into that one item. Its `source_table` is the
exact required table name, its typed source key is that same name as exact
text, both scopes and scope references are null, label evidence is missing
with a null safe-label reference, candidate relations are empty, and its
classification is `invalid_or_incomplete_source_identity`. It never
fabricates a business row or a failure for an unattempted table.

The `label_evidence` cross-field contract is exact:

| `validity` | `safe_label_ref` | Meaning and required item behavior |
|---|---|---|
| `valid` | Non-null | An exact string successfully completed the complete Section 4.7 algorithm |
| `invalid` | Null | A legacy label was `None`, non-string, blank, overlength, or contained prohibited post-normalization Unicode; classification is `invalid_or_incomplete_source_identity` with `invalid_label_evidence` |
| `missing` | Null | The source kind has no applicable label, as for `source_contract`; missing alone adds no label reason code |

For every legacy-root source kind, `None`, every non-string, blank, overlength,
and prohibited-Unicode label is `invalid`, never `missing`. A valid label must
have exactly one non-null safe label reference. An invalid or missing label
must have a null safe label reference. Every other combination is an internal
invariant failure.

`candidate_relations` members have exactly:

```text
{
  "candidate_kind": "vendor_organization" | "global_identity" | "backend_principal_mapping",
  "candidate_ref": safe-reference,
  "relation_status": "eligible_unapproved" | "ambiguous_unapproved" | "existing_consistent_unapproved" | "existing_conflicting_unapproved" | "ineligible_unapproved",
  "evidence_codes": [reason-code, ...]
}
```

No property may be named `vendor_id`, `global_identity_id`,
`approved_mapping_id`, `selected_candidate`, `winner`, or `authorized_target`.
All relation statuses explicitly remain unapproved.

`evidence_codes` is always nonempty, duplicate-free, and ordered by Section
8.2. The exact relation rules are:

| `relation_status` | Exact required `evidence_codes` |
|---|---|
| `eligible_unapproved` | Exactly `exact_evidence_unapproved` |
| `ambiguous_unapproved` | Exactly `ambiguous_candidate` |
| `existing_consistent_unapproved` | Exactly `existing_mapping_consistent` |
| `existing_conflicting_unapproved` | Exactly `[registry_target_conflict, existing_mapping_conflicting]`; used only for the R2-A missing-identity-target rows |
| `ineligible_unapproved` on `vendor_organization` | Distinct ordered union of every applicable `cross_site_evidence`, `membership_evidence_conflict`, `assignment_evidence_conflict`, and `binding_evidence_conflict`; minimum/maximum `1 / 4` |
| `ineligible_unapproved` on `global_identity` or `backend_principal_mapping` | Exactly `[ineligible_registry_state]`; minimum/maximum `1 / 1` |

Relation evidence codes and item reason codes are independently validated.
They need not be identical or subsets of one another: for example, each
relation in a one-to-many item carries `ambiguous_candidate`, while the item
carries `one_to_many_candidate_set`.

Applicable organization-conflict evidence must first be accumulated by
`candidate_ref` exactly as Section 4.7 requires; constructing one relation from
that pre-construction union is required behavior and is not silent
deduplication. After relation construction, a duplicate `candidate_ref` within
one item is an internal invariant failure, exit `4`, and zero stdout. The same
`candidate_ref` under two different relation statuses has the identical
failure behavior. Runtime code must not silently deduplicate, select, prefer,
or retain either duplicate relation.

### 7.4 Ordering

Candidate items sort by the ASCII tuple:

```text
(source_kind, source_table, source_record_ref, site_scope_ref-or-empty,
 sheet_scope_ref-or-empty, provenance_ref)
```

Candidate relations sort by:

```text
(candidate_kind, candidate_ref, relation_status)
```

Reason codes use the exact vocabulary order in Section 8.2, not incidental
discovery order. Duplicate safe references, relations, or reason codes are an
internal invariant failure; they are not silently deduplicated.

### 7.5 Classification summary and digests

`conflict_classification` contains exactly eleven entries in Section 8.1 order:

```text
{"classification": classification, "count": nonnegative-int}
```

`counts_and_safe_digests` is exactly:

```text
{
  "candidate_item_count": nonnegative-int,
  "candidate_relation_count": nonnegative-int,
  "classified_item_count": nonnegative-int,
  "unresolved_item_count": nonnegative-int,
  "excluded_item_count": nonnegative-int,
  "candidate_set_sha256": "<64 uppercase hex>",
  "evidence_sha256": "<64 uppercase hex>"
}
```

`candidate_set_sha256` hashes canonical JSON bytes of `candidate_set` only.
`evidence_sha256` hashes the complete envelope with only its own value replaced
by JSON null. The HMAC key is never included.

#### Deterministic A/A identity

Byte-identical A/A output is required only when every controlled identity input
and acceptance-environment precondition below is identical:

1. the SQLite database's complete raw bytes;
2. accepted topology and the before/after file size, mtime, identity, and
   sidecar evidence needed to reproduce the serialized snapshot fields;
3. the exact 32-byte HMAC key;
4. the caller-supplied execution ID;
5. the caller-supplied repository commit;
6. the caller-supplied `generated_at`;
7. the caller-supplied `expires_at`;
8. the raw bytes of exactly the canonical tool file whose hash is serialized
   as `discovery_implementation_identity.source_sha256`;
9. `VENDOR_ID_004B_CANDIDATE_EVIDENCE_V1`;
10. `VENDOR_ID_004B_SOURCE_SCHEMA_V1`;
11. `VENDOR_ID_004B_FIXED_QUERY_V1` and all twelve exact query IDs and SQL
    statement bytes;
12. `HMAC_SHA256_SAFE_REFERENCE_V1`;
13. `VENDOR_DISCOVERY_EVIDENCE_NORMALIZATION_V1` and all behavior prescribed
    by that profile; and
14. the acceptance runtime behavior that can affect results, including the
    Python implementation/version, SQLite library/version, Unicode data and
    normalization behavior, JSON/HMAC/SHA implementations, and filesystem
    observation semantics.

Item 8 is only the canonical tool file. Item 14 is an external controlled-test
precondition and is not claimed to be covered by `source_sha256`. V1 adds no
dependency-digest field. Database or key path text, process ID, system clock,
incidental iterator order, and unrelated host state never enter identity.

The exact single-input effect matrix is:

| Exactly one changed input | Fields/digests that must change | Fields allowed to remain equal |
|---|---|---|
| Database raw bytes | Both serialized source SHA fields, `source_database_ref`, and `evidence_sha256`; file size also changes when byte length changes | Schema fingerprint, row counts, candidate set, candidate digest, classifications, and counts change only when the observed logical projection changes |
| HMAC key | `source_database_ref`, every safe reference that exists, and `evidence_sha256` | Semantic classifications/counts; an empty `candidate_set_sha256` remains equal because it contains no safe reference |
| Execution ID | `discovery_execution_id` and `evidence_sha256` | Safe references and `candidate_set_sha256` |
| Repository commit | `source_repository_commit` and `evidence_sha256` | Safe references and `candidate_set_sha256` |
| `generated_at` | `generated_at` and `evidence_sha256` | Safe references and `candidate_set_sha256` |
| `expires_at` | `expires_at` and `evidence_sha256` | Safe references and `candidate_set_sha256` |
| Canonical tool bytes | `discovery_implementation_identity.source_sha256` and `evidence_sha256` | Other semantic output remains equal only when behavior remains equal |
| Contract version | `contract_version` and `evidence_sha256` | Safe references and candidate digest when every other contract behavior is unchanged |
| Schema-projection version | `projection_version`, `schema_fingerprint_sha256` because the version is in its canonical input, and `evidence_sha256` | Candidate output remains equal only when projection behavior remains equal |
| SQL bytes only, with every query ID unchanged | Canonical tool `source_sha256` and `evidence_sha256` | Every `provenance_ref`; when logical rows are identical, the candidate set and `candidate_set_sha256` |
| Query ID | Every affected item's `provenance_ref`, `evidence_sha256`, and `candidate_set_sha256` when the affected candidate set is nonempty; `source_sha256` also changes when the actual tool bytes change | Every unaffected source's `provenance_ref`; semantic rows/counts/classifications may remain equal when query behavior remains equal |
| Fixed-query family only, with every query ID unchanged | `provenance.fixed_query_family` and `evidence_sha256` | Every `provenance_ref`, the candidate set, and `candidate_set_sha256` |
| Normalization profile or prescribed behavior | Every affected `label_evidence.normalization_profile`, safe label reference, candidate item/relation result, `candidate_set_sha256`, and `evidence_sha256` | An input with no affected label item may retain the same candidate digest |
| Safe-reference profile | `provenance.safe_reference_profile`, every safe reference, and `evidence_sha256`; a nonempty candidate set changes its digest | Semantic classifications/counts |
| Only accepted file mtime | Serialized before/after mtime fields and `evidence_sha256` | Source database reference, schema fingerprint, row counts, and candidate digest |

Each `must change` statement is a contract invariant for accepted test vectors;
a cryptographic collision is an internal failure, not an alternative accepted
result. If changed input invalidates the CLI, topology, time ordering, runtime,
or no-touch preconditions, the mandated exit behavior replaces envelope
comparison.

The C3-A matrix does not modify the Section 5.4/5.5 `provenance_ref` HMAC
recipe. SQL bytes and fixed-query-family text never enter that preimage; only
the exact query ID enters its domain payload. Therefore SQL-only change with
the same query ID and logical rows changes `source_sha256` and
`evidence_sha256`, while `provenance_ref`, `candidate_set`, and
`candidate_set_sha256` remain unchanged.

All count equations are exact and recomputable:

```text
candidate_item_count = len(candidate_set)

candidate_relation_count =
  sum(len(item.candidate_relations) for item in candidate_set)

classified_item_count = candidate_item_count

conflict_classification[classification].count =
  number of candidate_set items with that exact classification

sum(all eleven conflict_classification counts) = candidate_item_count
```

Every candidate item has exactly one classification. Counts must not be
accepted from a caller, persisted cache, prior run, incidental loop counter, or
runtime interpretation. A mismatch between recomputed and envelope values is
an internal invariant failure, exit `4`, and zero stdout.

### 7.6 Unresolved, database evidence, provenance, and staleness

`unresolved_and_excluded` is exactly:

```text
{
  "unresolved_refs": [safe-reference, ...],
  "excluded_refs": [safe-reference, ...],
  "operational_reason_codes": [reason-code, ...]
}
```

The reference arrays use ascending ASCII safe-reference order. Operational
reason codes use Section 8.2 order. Complete evidence has an empty
`operational_reason_codes` array.

The reference and V1 exclusion invariants are exact:

```text
every candidate_set.source_record_ref is globally unique
unresolved_refs contains no duplicates
excluded_refs contains no duplicates
intersection(unresolved_refs, excluded_refs) is empty
unresolved_item_count = len(unresolved_refs)
excluded_item_count = len(excluded_refs)
```

V1 accepts no exclusion input and freezes:

```text
excluded_refs = []
excluded_item_count = 0
explicitly_excluded_record classification count = 0
unresolved_refs = sorted candidate_set.source_record_ref values
unresolved_item_count = candidate_item_count
```

Therefore every V1 candidate item remains unresolved. This includes
`unique_eligible_match` and `already_mapped_consistent`; neither is an approved
mapping. Any nonempty excluded reference array, missing unresolved item,
duplicate reference, overlap, or inconsistent count is an internal invariant
failure, exit `4`, and zero stdout.

`database_access_evidence` is exactly:

```text
{
  "backend": "sqlite",
  "open_mode": "mode=ro",
  "fixed_query_count": nonnegative-int,
  "write_attempt_count": 0,
  "write_count": 0,
  "authorizer_denial_count": 0,
  "transaction_started": bool,
  "rollback_completed": bool,
  "no_touch_proof": "verified"
}
```

`rollback_completed` is true exactly when a transaction was started and its
cleanup rollback completed. Both values are false when an operational failure
occurred before `BEGIN`. Every emitted complete or incomplete envelope still
requires `no_touch_proof = "verified"`.

An authorizer denial, rollback failure, or no-touch failure cannot produce a
trusted envelope; it maps to exit `4` with zero stdout.

`provenance` is exactly:

```text
{
  "producer_kind": "synthetic_test_harness",
  "invocation_boundary": "local_disposable_read_only",
  "fixed_query_family": "VENDOR_ID_004B_FIXED_QUERY_V1",
  "safe_reference_profile": "HMAC_SHA256_SAFE_REFERENCE_V1"
}
```

`staleness_conditions` is the following exact ordered array:

```text
[
  "source_snapshot_changed",
  "target_schema_changed",
  "implementation_identity_changed",
  "repository_commit_changed",
  "candidate_set_changed",
  "classification_changed",
  "evidence_expired"
]
```

This array lists conditions under which a later consumer must invalidate
previously emitted evidence. It does not mean V1 can emit a stale candidate
item or stale/incomplete envelope. Under C4-A, any before/after file identity,
size, mtime, full-file SHA-256, journal-sidecar, WAL-sidecar, or SHM-sidecar
invariant failure returns exit `4`, zero stdout, and the fixed internal marker,
regardless of whether the change was caused by this tool or a concurrent
external actor. Consequently V1 freezes:

```text
stale_evidence_or_source_changed classification count = 0
source_snapshot_changed item-reason occurrence count = 0
target_schema_changed item-reason occurrence count = 0
```

The classification and both reason codes remain in the frozen vocabularies but
are unreachable in V1.

D5-A likewise freezes:

```text
conflicting_backend_principal item-reason occurrence count = 0
```

The reason code remains in the closed vocabulary but is unreachable in V1 and
must not appear on an item or relation. `registry_target_conflict` remains
reachable only in the exact R2-A `already_mapped_conflicting` missing-target
projection together with `existing_mapping_conflicting`; it is not a
`target_state_conflict` reason.

## 8. Closed classification and reason-code vocabularies

### 8.1 Exact eleven-class taxonomy

The closed classification vocabulary is, in this exact order:

```text
unique_eligible_match
no_match
multiple_candidate_match
many_legacy_rows_to_one_canonical_identity
one_legacy_row_to_multiple_canonical_candidates
already_mapped_consistent
already_mapped_conflicting
invalid_or_incomplete_source_identity
stale_evidence_or_source_changed
target_state_conflict
explicitly_excluded_record
```

Every reviewed item has exactly one classification. Unknown, missing, or
multiple classifications fail closed.

### 8.2 Exact reason-code vocabulary

The closed reason-code vocabulary is, in this exact order:

```text
exact_evidence_unapproved
ambiguous_candidate
one_to_many_candidate_set
many_to_one_candidate_set
orphan_vendor_account
orphan_business_label
missing_required_source
missing_required_scope
malformed_source_identity
insufficient_evidence
invalid_label_evidence
cross_site_evidence
membership_evidence_conflict
assignment_evidence_conflict
binding_evidence_conflict
ineligible_registry_state
conflicting_backend_principal
registry_target_conflict
existing_mapping_consistent
existing_mapping_conflicting
source_snapshot_changed
target_schema_changed
excluded_by_frozen_scope
```

Runtime code may not construct or accept an unlisted reason code. A new reason
code requires a later docs-only contract revision.

### 8.3 Exact mapping

Reason-code arrays are duplicate-free and use Section 8.2 order. Their exact
cardinality and combinations are:

| Classification | Minimum / maximum reasons | Exact required or permitted reasons |
|---|---:|---|
| `unique_eligible_match` | `1 / 1` | Exactly `exact_evidence_unapproved` |
| `no_match` | `1 / 1` | Exactly `orphan_vendor_account` for an account item or `orphan_business_label` for a task/contact/work-entry item |
| `multiple_candidate_match` | `1 / 1` | Exactly `ambiguous_candidate` |
| `many_legacy_rows_to_one_canonical_identity` | `1 / 1` | Exactly `many_to_one_candidate_set` |
| `one_legacy_row_to_multiple_canonical_candidates` | `1 / 1` | Exactly `one_to_many_candidate_set` |
| `already_mapped_consistent` | `1 / 1` | Exactly `existing_mapping_consistent` |
| `already_mapped_conflicting` | `2 / 2` | Exactly `[registry_target_conflict, existing_mapping_conflicting]` under R2-A missing-target behavior |
| `invalid_or_incomplete_source_identity` | `1 / 5` | One or more of `missing_required_source`, `missing_required_scope`, `malformed_source_identity`, `insufficient_evidence`, `invalid_label_evidence` |
| `stale_evidence_or_source_changed` | `0 / 0` in V1 | Unreachable in V1; classification count is fixed zero and neither `source_snapshot_changed` nor `target_schema_changed` may occur on an item |
| `target_state_conflict` | `1 / 5` | One or more of `cross_site_evidence`, `membership_evidence_conflict`, `assignment_evidence_conflict`, `binding_evidence_conflict`, `ineligible_registry_state` |
| `explicitly_excluded_record` | `1 / 1` | Exactly `excluded_by_frozen_scope`; impossible in V1 because exclusions are fixed empty |

A reason code never replaces classification. `cross_site_evidence` always maps
to `target_state_conflict`, and only applies when both scopes are known and
contradict. Missing scope maps to `invalid_or_incomplete_source_identity` plus
`missing_required_scope`; malformed or unresolvable scope maps to the same
classification plus `malformed_source_identity`. Invalid legacy labels map to
that classification plus `invalid_label_evidence`. Relationship and registry
state conflicts map to `target_state_conflict`. Orphan account/label evidence
maps to `no_match`. `ineligible_registry_state` is the only registry/mapping
reason permitted on `target_state_conflict`. The only use of
`registry_target_conflict` is the exact R2-A
mapping-with-missing-identity-target `already_mapped_conflicting` projection.
`conflicting_backend_principal` is unreachable. Every vendor or non-vendor
mapping primary-identity, uniqueness, physical-uniqueness, or result-cardinality
violation is `backend_principal_mappings` source-contract incompleteness, not a
runtime candidate classification or relation.

When one vendor-organization candidate has multiple applicable organization
conflicts, the `target_state_conflict` item-reason subset and its single
relation's evidence array are the complete distinct Section-8.2-ordered union
required by C1-A. Valid non-vendor mapping rows never contribute
`conflicting_backend_principal`, `registry_target_conflict`, or any other item
reason.

An unknown classification, unknown reason code, absent classification,
multiple classification, empty reason array, duplicate reason, disallowed
combination, or reason-count violation is an internal invariant failure, exit
`4`, and zero stdout.

No classification may automatically approve a candidate. Even
`unique_eligible_match` remains `exact_evidence_unapproved` pending VENDOR-ID-004C.

### 8.4 Operationally incomplete envelope

An operationally incomplete envelope retains all fifteen top-level keys. The
required-source set is exactly the twelve Section 4.9 tables. For every
distinct required table actually proved missing, malformed, or failed, the
envelope contains exactly one coalesced `source_contract` item. The exact
failure mapping is:

| Proven condition for one required table | Exact `source_contract.reason_codes` contribution | Business-row behavior |
|---|---|---|
| Missing legacy-root table | `missing_required_source` | No item is fabricated for that root; other successfully completed legacy-root queries remain usable as incomplete items |
| Missing `sites` or `sheets` | `missing_required_source` | Successfully read scoped legacy rows remain, with atomic null scopes and `missing_required_scope`; account rows remain unscoped |
| Missing organization or relationship table | `missing_required_source` | Safely read legacy items remain; no relation is produced |
| Missing registry or mapping table | `missing_required_source` | Safely read legacy items remain; no identity/mapping relation is produced |
| Missing required column | `missing_required_source` | That table's data statement is skipped and no row is fabricated |
| Wrong owner, wrong object type, case alias, or duplicate source identity | `malformed_source_identity` | That table's data statement is skipped |
| Duplicate `cid`, duplicate column name, or required xinfo conformance mismatch | `malformed_source_identity` | That table's data statement is skipped |
| D3-A type-valid topology-content failure | Exactly `malformed_source_identity` for each of all twelve required tables | All twelve data statements are skipped; the exact D3-A twelve-item projection applies |
| Executed data statement raises an expected source/query failure | `insufficient_evidence` | Discard that statement's partial rows and stop every later data statement |
| Executed data result has invalid tuple/type/order/physical identity or exceeds either row bound | `malformed_source_identity`, `insufficient_evidence` | Discard that statement's rows and stop every later data statement |
| Multiple proven failures for the same table | Distinct union of the applicable codes in Section 8.2 order | Still exactly one `source_contract` item |

Therefore:

```text
source_contract_item_count =
  number of distinct required table names with at least one proven failure
```

Each such item's `source_record_ref` uses the exact required table name as its
typed source identity, null `S_i`/`H_i`, and that table's fixed query ID. This
makes source-contract references unique per table. A failed or metadata-skipped
source contributes no business row. A fully completed safe legacy-root query
retains every validated row item even when another source is incomplete.

D3-A is the exact closed exception to per-table source discovery: one
type-valid topology-content failure proves the owner/topology boundary invalid
for all twelve required tables at once. It therefore creates all and only the
twelve `source_contract` items fixed in Section 4.8, with no additional reason
from later fingerprint-only metadata, no business-row item, no data-query
attempt, and no thirteenth item. Its fixed counts, row-count nulls, operational
reasons, non-null fingerprint, and topology fields override the generic partial
execution equations only as explicitly stated there.

Once any required source is incomplete, candidate construction is globally
incomplete. Every retained business-row item and every `source_contract` item
has classification `invalid_or_incomplete_source_identity`, every
`candidate_relations` array is empty, and safely retained business items
include `insufficient_evidence` plus any independently applicable
`missing_required_scope`, `malformed_source_identity`, or
`invalid_label_evidence`, in Section 8.2 order. No partial organization,
mapping, or identity relation survives.

The exact incomplete-run equations are:

```text
candidate_item_count =
  source_contract_item_count + safely reconstructed legacy item count

candidate_relation_count = 0

invalid_or_incomplete_source_identity classification count =
  candidate_item_count

every other classification count = 0

operational_reason_codes =
  Section-8.2-ordered distinct union of all source_contract reason codes,
  plus insufficient_evidence when any required data query row_count is null
```

A table skipped solely because it occurs after the first executed data-query
failure has null `source_row_counts.row_count`, but non-attempt alone does not
prove a table failure and does not fabricate a `source_contract` item. The
first executed data-query execution/result/bound failure stops all later data
queries exactly as Section 4.9 requires.

`target_schema_identity.availability` is `incomplete`. Its schema fingerprint
is non-null because an emitted incomplete envelope requires complete metadata
capture, validated tuple types, canonical projection, serialization, and hash
reconstruction. Proved missing/malformed objects remain represented in that
non-null observed fingerprint. An inability to reconstruct the complete
projection is fatal under C2-A and emits no envelope. Row counts and
`fixed_query_count` use the exact null/count rules in Sections 4.9 and 7.6.

A successful, type-valid metadata projection that proves source
absence/malformation, or an executed bounded data-query failure, may emit exit
`3` only after successful rollback/close and verified before/after no-touch
evidence. Connection-open, `BEGIN`, metadata-statement exception,
metadata-tuple arity/type failure, metadata bound overflow, canonical
projection/serialization/hash/count failure, authorizer, rollback, or no-touch
failure cannot construct trusted incomplete evidence; it returns exit `4`,
zero stdout, and the fixed internal marker. Fully captured and type-valid
schema-content conflicts remain exit `3` under C2-A. No failure is converted
into complete evidence or invented source state.

## 9. Read-only and no-touch enforcement

The implementation must establish this exact single-connection lifecycle:

1. validate an explicit absolute DB path strictly below Windows system temp;
2. reject repository, canonical, outside-temp, network, symlink, junction,
   reparse, hardlink, non-regular, ambiguous, WAL, and unsupported files;
3. reject any existing `-wal`, `-shm`, or `-journal` sidecar;
4. before opening SQLite, capture file identity, size, mtime, full-file byte
   hash, sidecars, and header;
5. create exactly one SQLite connection using only
   `Path.as_uri() + '?mode=ro'`, URI mode, and no writable fallback;
6. install a strict phase-aware authorizer before business-row reads;
7. permit only frozen SELECT/READ/schema metadata operations plus explicit
   `BEGIN` and cleanup `ROLLBACK`;
8. deny DDL, DML, ATTACH, DETACH, COMMIT, VACUUM, writable PRAGMA, extension
   loading, user functions, triggers, and dynamic SQL;
9. begin exactly one explicit read transaction;
10. within that same transaction, capture topology, the schema fingerprint,
    bounded source-row counts, every fixed-query result, and all discovery
    evidence as one transaction-observed snapshot;
11. attempt cleanup `ROLLBACK` and close that same connection on every path;
12. treat rollback only as cleanup, never as the read-only guarantee;
13. after close, capture only file identity, size, mtime, full-file byte hash,
    and sidecars;
14. never reopen SQLite to obtain a post-close schema fingerprint, row count,
    topology result, or business-row result; and
15. emit trusted evidence only when every no-touch invariant is verified.

The schema fingerprint and bounded source-row counts describe only the snapshot
observed inside the one explicit read transaction. They are not post-close
queries and must not be labelled, serialized, or interpreted as such.

Byte-identical full-file hashes, identical file identity/size/mtime, and absent
journal, WAL, and SHM sidecars before and after are the post-close filesystem
evidence that the database was not touched. Every individual invariant is
mandatory. Failure of any one is exit `4`, zero stdout, and the fixed internal
marker, whether the change came from this tool or a concurrent external actor;
V1 emits no stale or incomplete envelope. These checks do not authorize a
second connection. Connection-factory instrumentation in future tests must
prove exactly one accepted SQLite open and zero post-close opens.

There is no `app` import, application bootstrap, schema initializer, migration,
repair, ORM, network library, PostgreSQL driver, environment lookup, or
connection fallback.

An expected source/query failure may return the bounded incomplete envelope and
exit `3` only after no-touch proof succeeds. Any possible mutation, authorizer
invariant failure, cleanup failure, file-identity replacement, file-size or
mtime mismatch, full-file-hash mismatch, journal/WAL/SHM sidecar appearance, or
inability to prove unchanged state returns exit `4`, zero stdout, and the fixed
internal marker. No actor distinction and no stale-candidate fallback exists.

## 10. Acceptance matrix

Every fixture is newly created by the test harness under a unique Windows
system-temp directory, contains only synthetic values, starts without
sidecars, is never reused, and is removed only by the harness after the tool is
closed.

| Scenario | Required result |
|---|---|
| All twelve exact required tables present and empty | Complete deterministic envelope; twelve zero row counts, `fixed_query_count=12`, zero candidates, and all eleven classification counts zero. |
| Physical source identity | Every account/task/contact/work-entry item uses its selected positive physical `id`; query ordinal use is an internal failure. |
| Canonical normalization profile | Exact name `VENDOR_DISCOVERY_EVIDENCE_NORMALIZATION_V1`; every algorithm step and prohibited transformation is enforced. |
| Single unambiguous evidence | `unique_eligible_match` plus `exact_evidence_unapproved`; never approved or selected. |
| Duplicate equal label | No automatic merge; ambiguity/cardinality classification is deterministic. |
| One source to many candidates | `one_legacy_row_to_multiple_canonical_candidates`. |
| Many sources to one candidate | `many_legacy_rows_to_one_canonical_identity`. |
| Many sources to many candidates | `multiple_candidate_match`; every target remains ambiguous and unselected. |
| Missing required scope | `invalid_or_incomplete_source_identity` plus `missing_required_scope`; never cross-site. |
| Malformed or unresolvable required scope | `invalid_or_incomplete_source_identity` plus `malformed_source_identity`; never cross-site. |
| Known contradictory site/sheet scope | `target_state_conflict` plus `cross_site_evidence`. |
| Current membership structural edge | `pending`/`active` edge retained; label mismatch becomes `membership_evidence_conflict`; `revoked` creates no current edge. |
| Assignment/binding status behavior | Only active rows form current scope evidence; missing rows do not silently delete a label candidate. |
| Retired organization from label/general lookup only | No candidate relation and no contribution to `N_t`. |
| Current exact structural reference to existing retired organization | Exactly one `vendor_organization / ineligible_unapproved` relation with the complete applicable C1-A ordered conflict union; relation count increases by one. |
| Current structural reference to missing organization row | No fabricated organization relation. |
| Four simultaneous organization conflicts | One `vendor_organization` relation only; `ineligible_unapproved`; evidence exactly `[cross_site_evidence, membership_evidence_conflict, assignment_evidence_conflict, binding_evidence_conflict]`; `candidate_relation_count` increases by one. |
| Disabled global identity without exact existing vendor mapping | No general-lookup identity relation. |
| Exact existing vendor mapping to disabled global identity | Exactly one additional `global_identity / ineligible_unapproved / [ineligible_registry_state]` relation; together with the R2-A mapping relation, the displayed row increment remains two; never active or absent. |
| Valid non-vendor mapping | Transaction-observed snapshot/row-count evidence only; no mapping or identity relation, no vendor-item classification change, no relation-count increment, and no backend-principal conflict. |
| Invalid or uniqueness-violating non-vendor mapping | `backend_principal_mappings` source-contract incompleteness; no target relation, target selection, aggregation, or individual vendor-item target-state conflict. |
| Orphan vendor account | `no_match` plus `orphan_vendor_account`. |
| Orphan business label | `no_match` plus `orphan_business_label`. |
| Missing required table/column | Operational incomplete, `invalid_or_incomplete_source_identity`, no later unsafe query. |
| Malformed source identity/type | `invalid_or_incomplete_source_identity` plus `malformed_source_identity`. |
| Invalid legacy label | Null safe label reference plus `invalid_label_evidence`; legacy `None`/non-string/blank/overlength/prohibited Unicode is never `missing`. |
| Existing mapping consistent | `already_mapped_consistent`; still unapproved for later action. |
| Existing mapping conflicting | `already_mapped_conflicting`; blocking evidence preserved. |
| Vendor or non-vendor mapping identity/uniqueness/cardinality violation | `backend_principal_mappings` source-contract incompleteness; no mapping/identity relation, no `conflicting_backend_principal`, no target selection, and no individual vendor-item target-state change. |
| Metadata statement exception, row arity/type error, bool in integer position, overflow, projection serialization, or fingerprint reconstruction failure | Exit `4`, zero stdout, fixed internal marker. |
| Fully typed metadata proves one of the closed D4-A source/owner/type/case/duplicate/cid/name/required-column/xinfo-conformance conflicts | Exit `3` incomplete envelope with one coalesced source-contract item for the affected table; fingerprint-only fields never become conflicts. |
| Type-valid topology-content failure | Exact D3-A exit-`3` envelope: twelve source-contract items, zero relations, zero fixed data queries, twelve null row counts, exact operational reasons, non-null fingerprint/topology fields, and no thirteenth item. |
| SQL bytes only change, query ID and logical rows unchanged | Tool `source_sha256` and `evidence_sha256` change; `provenance_ref` and `candidate_set_sha256` remain unchanged. |
| Any before/after identity/size/mtime/full-hash/sidecar mismatch | Exit `4`, zero stdout, fixed internal marker, and no stale candidate classification. |
| Unsupported environment | Exit `2`, no connection attempt. |
| Unsupported backend/PostgreSQL | Exit `2`, no connection attempt. |
| Repository or writable-path misuse | Read-only open after full validation or fail closed before connection; never writable fallback. |
| HMAC key outside temp | Exit `2`; key not read. |
| HMAC key symlink/reparse/hardlink/repository path | Exit `2`; key not emitted. |
| HMAC key malformed, uppercase, prefixed, short, long, CRLF, or multi-line | Exit `2`; no database attempt. |
| Same complete controlled fixture/key/CLI identity inputs/runtime A/A | Every Section 7.5 identity input and runtime precondition is equal; canonical stdout and both digests are byte-identical. |
| Changed fixture bytes A/B | Source SHA/reference and evidence digest change; schema, row-count, candidate, classification, and candidate-digest fields change exactly when their observed logical inputs change. |
| Changed key with identical source | Source-database and every existing safe reference plus evidence digest change; a nonempty candidate set changes its digest; classifications and counts remain semantically equal. |
| Exact field-to-HMAC fixtures | Every output reference matches the Section 5.5 recipe for domain, environment, kind, table, key, scopes, and payload. |
| Cross-domain/table/scope equal canaries | Safe references differ; candidate references use target-side kind/table/key and never source-side identity. |
| Database path relocation with identical accepted bytes | `source_database_ref` remains identical; path text never enters its preimage. |
| Duplicate candidate relation | After required pre-construction C1-A evidence accumulation, a duplicate `candidate_ref`, conflicting status for one ref, or duplicate evidence code produces exit `4` and zero stdout. |
| Recomputed counts | Every count equals the exact Section 7 equations; all eleven classification counts sum to `candidate_item_count`. |
| V1 exclusions | `excluded_refs=[]`, excluded count and explicit-exclusion classification count are zero. |
| V1 unresolved set | Every candidate item source reference appears exactly once in `unresolved_refs`, including unique and existing-consistent items. |
| Raw ID/label/username/password/hash/token/contact canaries | Zero occurrences in stdout, stderr, exceptions, hashes other than opaque HMAC results, and captured logs. |
| DDL/DML/ATTACH/COMMIT/mutating-PRAGMA injection | Authorizer denial and internal fail-closed result. |
| Query/result-contract failure | Bounded exit `3` only after verified no-touch proof. |
| Rollback/close/authorizer-reset failure | Exit `4`, zero stdout. |
| Single connection lifecycle | Exactly one accepted `mode=ro` open and one explicit read transaction; every path rolls back/ closes as applicable. |
| Post-close lifecycle | Filesystem identity/size/mtime/full hash/sidecars only; zero SQLite reopen and zero logical post-close query. |
| Schema and bounded rows | Captured only inside the explicit read transaction; `source_row_counts` contains exactly twelve entries, bounds are `10000` per query and `50000` total, and `fixed_query_count` equals its non-null count. |
| DB bytes, size, mtime, schema, and bounded rows | Full-file bytes, identity, size, mtime, and sidecars unchanged; transaction-observed schema/row evidence remains internally consistent. |
| WAL/SHM/journal before and after | Absent; none created. |
| Repository DB and sidecars | Never opened and unchanged. |
| Existing VENDOR-ID-003 aggregate contract | Unchanged and independently passing. |
| Existing VENDOR-ID-002 schema guard | Unchanged and independently passing. |
| Full smoke regression | PASS using separately authorized disposable isolation. |

## 11. Future validation contract

A separately authorized implementation gate must define an exact changed-file
scope and execute, at minimum:

```text
git diff --check
python -m compileall -q app.py services tools tests
VENDOR-ID-004B static checker normal mode
VENDOR-ID-004B static checker self-test
VENDOR-ID-004B focused synthetic test matrix
existing VENDOR-ID-003 readiness checker normal mode and self-test
existing VENDOR-ID-002 schema checker normal mode and self-test
existing identity-registry ID validation tests
python tests/smoke_test.py under separately approved disposable isolation
repository DB/sidecar and artifact-cleanup verification
```

This document runs none of those commands and does not authorize them.

## 12. Explicit exclusions

VENDOR-ID-004B V1 does not include or authorize:

- modification or implementation of the VENDOR-ID-003 product, canonical
  implementation, query family, envelope, taxonomy, runtime behavior, or
  authority; only the exact Section 15 checker-composition plumbing may change
  under a separately authorized 004B0S gate;
- schema, migration, schema initialization, or physical projection changes;
- API, UI, route, scheduler, job, webhook, or runtime consumer;
- login, credential, session, role, permission, workflow, site isolation, or
  vendor routing changes;
- raw identity, raw key, raw label, contact/person, credential, or secret
  disclosure;
- approved mappings, mapping-package approval, ranking/suppressing/choosing an
  approved, canonical, or winning candidate, deduplication, merge, or identity
  repair;
- vendor/global ID generation or persistence;
- report, artifact, audit-record, cache, or evidence-package persistence;
- controlled apply, backfill, reconciliation, recovery, or authority switch;
- PostgreSQL or any non-SQLite backend;
- DEV, Staging, or Production discovery execution;
- authenticated verification; or
- deployment.

## 13. Independent future sequence

The sequence remains:

```text
004B0D exact guard-composition contract
-> 004B0S static guard and upstream composition
-> 004B1 pure candidate/safe-reference/envelope core
-> 004B2 exact CLI and synthetic read-only SQLite discovery
-> 004B3 disposable acceptance matrix and freeze
-> 004C mapping review package
-> 004D controlled apply contract and implementation
-> later environment-specific discovery, review, authorization, apply,
   reconciliation, and authority gates
```

No arrow grants authority to execute the next step. Each step requires its own
baseline, exact scope, review, validation, and explicit authorization.

## 14. Frozen markers

```text
VENDOR-ID-004B PRODUCT DECISIONS: 1-B / 2-A / 3-A / 4-A
VENDOR-ID-004B CONTRACT-GAP DECISIONS: CG-1 A / CG-2 A / HG-1 A / IG-1 A / LG-1 A
VENDOR-ID-004B FINAL RESIDUAL DECISIONS: R1-A / R2-A / R3-A / R4-A / R5-A
VENDOR-ID-004B FINAL CANONICAL CONSISTENCY DECISIONS: C1-A / C2-A / C3-A / C4-A / C5-A
VENDOR-ID-004B FINAL RESIDUAL CANONICAL DECISIONS: D1-A / D2-A / D3-A / D4-A / D5-A
VENDOR-ID-003 AGGREGATE READINESS CONTRACT: UNCHANGED
VENDOR-ID-004A CONTROLLED-BACKFILL CONTRACT: UNCHANGED
VENDOR-ID-004B CANDIDATE-EVIDENCE CONTRACT: DOCS-ONLY / FROZEN
SAFE REFERENCE PROFILE: HMAC_SHA256_SAFE_REFERENCE_V1
CLASSIFICATION TAXONOMY: CLOSED ELEVEN-CLASS
REASON-CODE VOCABULARY: CLOSED
REVIEWED SOURCE IDENTITY: PHYSICAL PRIMARY KEY ONLY
V1 EXCLUSIONS: EMPTY
ALL V1 CANDIDATE ITEMS: UNRESOLVED
SQLITE LIFECYCLE: SINGLE MODE=RO CONNECTION / POST-CLOSE FILESYSTEM ONLY
BACKEND / ENVIRONMENT: SYNTHETIC WINDOWS TEMP SQLITE ONLY
OUTPUT: CANONICAL JSON STDOUT ONLY
CANONICAL DISCOVERY IMPLEMENTATION: NOT STARTED
MAPPING APPROVAL: NOT STARTED
CONTROLLED BACKFILL: NOT AUTHORIZED
RECONCILIATION: NOT AUTHORIZED
RUNTIME AUTHORITY SWITCH: NOT AUTHORIZED
DEV / STAGING / PRODUCTION DISCOVERY: NOT AUTHORIZED
```

## 15. VENDOR-ID-004B0D exact static-guard composition decision

### 15.1 Ownership and non-equivalence

This section resolves only the static-guard ownership conflict between
VENDOR-ID-003 and the future VENDOR-ID-004B implementation. It changes no
runtime, schema, data, product, or authority behavior.

VENDOR-ID-003 continues to own only its aggregate-only vendor-organization
readiness discovery, canonical implementation, fixed query family, aggregate
envelope, anomaly taxonomy, classifications, projections, and forbidden
capabilities.

VENDOR-ID-004B continues to own only candidate evidence, safe references,
closed reason-code and classification validation, the canonical
candidate-evidence envelope, synthetic-only read-only SQLite discovery, and
no-touch evidence. Its evidence is not a mapping approval, canonical identity,
backfill authorization, reconciliation result, runtime authority, runtime
consumer, or VENDOR-ID-003 aggregate discovery result.

### 15.2 Exact canonical path and closed routing inventory

The sole implementation path covered by this composition decision is exactly:

```text
tools/discover_vendor_identity_evidence.py
```

The sole VENDOR-ID-004B static-guard path permitted to adjudicate routed
findings is exactly:

```text
tools/check_vendor_identity_evidence.py
```

An alternate checker, alias, wrapper, re-export, renamed copy, or dynamically
selected checker cannot satisfy the composition. The generic VENDOR-ID-004B
static-checker references in Section 11 mean this exact path.

The exact guard file itself remains fully parsed and enumerated by the
VENDOR-ID-003 and VENDOR-ID-002 guards. They may structurally accept only the
exact top-level node inventory, callable signatures, immutable policy/issue
vocabulary, deterministic output nodes, self-audit AST bundle, and exact
negative-fixture node hashes frozen by 004B0S. VENDOR-ID-004B markers or SQL
bytes may occur there only in exact pinned policy constants or negative
fixture nodes, never in executable SQL, database, environment, mutation,
runtime, or discovery capability. Its only filesystem authority is exact
read-only repository-source inspection required for static analysis; writes
and non-source reads are forbidden. Every extra, missing, reordered, unparsed,
or hash-drifted node, and every marker moved outside its exact pinned node,
fails closed. A whole-guard-file, whole-function, or subtree exemption is
forbidden.

No directory wildcard, filename prefix or suffix, generic allowlist, renamed
substitute, hidden path, alias, symlink, generated path, dynamically
constructed identifier, or whole-`tools/` exemption is permitted.

At that path, the only findings eligible for bounded VENDOR-ID-004B routing
are individual AST nodes whose literal, identifier, query identity, field set,
and use are exact members of this closed inventory:

| VENDOR-ID-004B-owned family | Exact definition in this document | Sole permitted use |
|---|---|---|
| Normalization | `VENDOR_DISCOVERY_EVIDENCE_NORMALIZATION_V1`; Sections 4.7 and 7.3 | Candidate-evidence label normalization only |
| Safe references | `HMAC_SHA256_SAFE_REFERENCE_V1`, `hmac-sha256-v1:`, closed domains, and exact byte recipes; Section 5 | Non-reversible evidence references only |
| Sources and candidates | The five source kinds and exact candidate-item and relation keys, values, cardinalities, and ordering; Sections 4 and 7.3-7.4 | Unresolved candidate evidence only |
| Envelope | The exact fifteen top-level keys and nested closed shapes; Section 7 | Canonical evidence output only |
| Classification and reasons | The ordered eleven classes, closed reason vocabulary, and exact mapping; Section 8 | Validation and unresolved evidence classification only |
| CLI and failures | The exact CLI options, fixed stderr markers, exits, stdout rules, and synthetic-only lifecycle; Section 6 | The VENDOR-ID-004B CLI only |
| Queries and no-touch proof | Exact query IDs, SQL bytes, result contracts, bounds, mode-`ro` lifecycle, authorizer, transaction, and post-close proof; Sections 4.8-4.9 and 9 | Synthetic VENDOR-ID-004B evidence capture only |

The routing unit is one specifically identified finding at one exact AST node,
not a file, function, class, module, or broad vocabulary family. Mere use of
`vendor`, `discovery`, `candidate`, `identity`, `mapping`, `classification`, or
`evidence` is never sufficient.

VENDOR-ID-003 canonical queries, aggregate categories, output and projection
semantics, and canonical symbols are never delegated. For a SQL statement
common to both frozen inventories, the exact VENDOR-ID-004B query ID, result
contract, bounded data flow, and VENDOR-ID-004B-only use must all pass the
VENDOR-ID-004B guard. Literal equality alone does not establish ownership;
aggregate or mixed flow fails closed.

### 15.3 No whole-file exemption and exact fail-closed predicates

The VENDOR-ID-003 checker must scan the complete canonical VENDOR-ID-004B file
and must independently reject:

- aggregate vendor discovery or a VENDOR-ID-003 canonical query/result family;
- VENDOR-ID-003-owned anomaly, classification, projection, envelope, or output
  semantics;
- mapping approval; ranking, suppressing, or choosing an approved, canonical,
  or winning candidate; merge, reconciliation, or identity authority;
- schema creation, mutation, migration, repair, conformance-PASS, or
  schema-authority capability;
- write, apply, repair, backfill, or persistence capability;
- runtime route, API, UI, job, consumer, or authority behavior; and
- every other VENDOR-ID-003 frozen forbidden behavior.

Complete deterministic construction and retention of the unresolved
VENDOR-ID-004B candidate set is candidate-evidence projection, not candidate
selection under this prohibition. Exact read-only table-list, xinfo, and
schema-fingerprint evidence frozen by this document is evidence capture, not
schema capability or conformance authority.

An individual finding may be routed only when all of these predicates hold:

1. its path is byte-for-byte the exact canonical path in Section 15.2;
2. its marker and AST use are exact members of the closed VENDOR-ID-004B
   inventory;
3. its use is solely evidence-only VENDOR-ID-004B behavior;
4. the exact frozen VENDOR-ID-004B guard exists, completes successfully, emits
   deterministic PASS, and validates that node;
5. the VENDOR-ID-003 checker independently finds no VENDOR-ID-003-owned or
   otherwise forbidden behavior; and
6. the VENDOR-ID-002 schema guard accepts the frozen composition structure.

Unknown paths or markers, unrecognized AST shapes, mixed ownership, ambiguous
query flow, missing or renamed guard, invocation failure, nonzero exit, empty
or malformed guard output, guard FAIL, or inability to classify must fail the
combined result. None may be suppressed or treated as PASS.

### 15.3.1 Source-bound composition proof

004B0S freezes one composition protocol only. VENDOR-ID-003 invokes exactly
one isolated child process with `subprocess.run`, `shell=False`, no dynamic
command construction, repository root as `cwd`, a 30-second timeout, and this
exact argument vector:

```text
[sys.executable, "-I", "-B",
 <absolute-repository-path-to-tools/check_vendor_identity_evidence.py>,
 "--composition-proof",
 "tools/discover_vendor_identity_evidence.py",
 <UPPERCASE-SOURCE-SHA256-or-ABSENT>]
```

No other subprocess, direct/dynamic import, alternate callable, module cache,
file-based or cached proof, shell, retry, or caller-supplied PASS value may
replace it. The guard source path, raw-byte SHA-256, parsed AST identity, and
absence of repository bytecode/cache artifacts are checked immediately before
and after the sole invocation. `-I -B` is mandatory; stdin, stdout, and stderr
are binary pipes and no repository file is created.

For a present implementation, VENDOR-ID-003 reads and parses the exact source
bytes, computes their uppercase 64-hex SHA-256, supplies that digest as the
final argument, and supplies only those bytes on stdin. The VENDOR-ID-004B
guard recomputes the stdin digest and parses stdin; it never opens, imports, or
substitutes the implementation source.

For the 004B0S absence state, VENDOR-ID-003 proves the canonical path absent
before invocation, supplies exact `ABSENT` and zero stdin bytes, and proves the
path remains absent after return. The proof is exactly:

```json
{"canonical_path":"tools/discover_vendor_identity_evidence.py","covered_node_keys":[],"implementation_stage":"not_started","issue_codes":[],"result":"PASS","source_sha256":null}
```

For a present source, canonical JSON contains exactly the same six keys:

- `canonical_path`;
- `source_sha256`;
- `implementation_stage`;
- `covered_node_keys`;
- `issue_codes`; and
- `result`.

The proof uses UTF-8, sorted keys, compact separators, `ensure_ascii=False`,
`allow_nan=False`, and exactly one terminal LF. Child exit is `0` and stderr
is empty. The path is exact, source digest is the expected uppercase value,
stage is derived, `issue_codes` is an empty list, and `result` is exact `PASS`.

Each covered-node key is the exact seven-member tuple
`(lineno, col_offset, end_lineno, end_col_offset, node_type, marker_family,
node_ast_sha256)`. `node_ast_sha256` is uppercase SHA-256 over UTF-8 bytes of
the node's canonical `ast.dump(..., annotate_fields=True,
include_attributes=False)` text. Keys are unique and ordered by source
position, node type, marker family, and digest.

VENDOR-ID-003 independently computes every routeable node key. Its ordered set
must equal `covered_node_keys` exactly, with no missing, duplicate, overlapping,
extra, or unbound node. It then re-reads the source and requires unchanged path
state and digest before emitting its normal PASS marker.

The structural stage is exact `not_started` when the implementation path is
absent. When present, it is derived only from the sole literal module constant
`_VENDOR_ID_004B_IMPLEMENTATION_STAGE`, whose value is exactly `004B1`,
`004B2`, or `004B3`. Environment, CLI, branch, config, or dynamically composed
stage input is forbidden. Missing, duplicate, nonliteral, contradictory,
stale, or capability-incompatible stage evidence fails closed. Recognition is
structural evidence only, never authorization.

Any guard identity, command, invocation, timeout, exit, exception, proof-shape,
path, digest, stage, coverage, issue, result, stdout/stderr, cache/artifact, or
post-call source mismatch must add
the exact VENDOR-ID-003 issue code
`downstream_vendor_identity_evidence_guard_drift`, return nonzero, and suppress
the VENDOR-ID-003 normal PASS marker.

### 15.4 Future checker-composition slice

The separately authorized `004B0S` slice must:

- create a dedicated VENDOR-ID-004B static guard;
- create it only at `tools/check_vendor_identity_evidence.py`;
- validate exact-path positive and negative source cases;
- change the VENDOR-ID-003 checker only enough to implement individual-node,
  exact-path, exact-marker bounded routing while retaining its full
  forbidden-behavior scan;
- change the VENDOR-ID-002 schema checker only enough to freeze and validate
  the explicit cross-guard structure and identities;
- preserve all existing VENDOR-ID-003 aggregate and VENDOR-ID-002 schema
  semantics and negative guarantees;
- require every participating guard to pass; and
- fail closed if any guard is absent, renamed, incomplete, failing, silent, or
  unclassifiable.

Its exact code scope is:

```text
A tools/check_vendor_identity_evidence.py
M tools/check_vendor_organization_discovery_readiness.py
M tools/check_vendor_organization_schema.py
M tests/smoke_test.py
```

The canonical implementation file is absent from that scope. Any additional
file requires a new docs decision and explicit authorization.

Execution and downstream delegation are one-way from the VENDOR-ID-003 guard
to the exact VENDOR-ID-004B composition-proof process. The VENDOR-ID-004B guard must
never invoke either upstream guard. VENDOR-ID-002 independently validates the
VENDOR-ID-003 composition nodes; the pre-existing reciprocal VENDOR-ID-002 /
VENDOR-ID-003 static AST-integrity attestations remain unchanged and are not
downstream invocation. A VENDOR-ID-004B-to-upstream call, recursive execution,
or delegated-result cycle fails closed.

The Section 12 exclusion on modification or implementation of VENDOR-ID-003
continues to prohibit changes to its product, aggregate tool, query family,
output, and authority. The narrowly authorized checker-composition enforcement
above is not VENDOR-ID-003 product implementation and may occur only in the
separate 004B0S gate.

### 15.5 Staged implementation states

| Stage | Sole legal state |
|---|---|
| `004B0D` | Docs only; every checker and implementation remains unchanged. Because the existing VENDOR-ID-003 guard pins the pre-004B0D policy bytes, this transitional feature state makes no normal checker-PASS claim and may fail closed with `vendor_discovery_policy_drift` if run. It must not be merged or deployed without 004B0S atomically refreshing the exact checker pins. |
| `004B0S` | The exact four-file guard scope in Section 15.4 implements composition and self-tests first; the canonical implementation path remains absent. Normal mode emits exact `implementation_state: not_started` and PASS only for that absence state, rejecting partial, wrong-path, hidden, or uncontrolled implementation. |
| `004B1` | After 004B0S passes and a separate gate authorizes it, the canonical path may be created only as non-executable pure candidate/safe-reference/envelope source with sole literal stage marker `_VENDOR_ID_004B_IMPLEMENTATION_STAGE = "004B1"` and zero CLI, I/O, SQL, filesystem, environment, or runtime capability. |
| `004B2` | After 004B1 passes and a separate gate authorizes it, the marker becomes exact `"004B2"` and the exact CLI plus synthetic-only read-only SQLite discovery lifecycle may be added at the same canonical path. |
| `004B3` | After 004B2 passes and a separate gate authorizes it, the marker becomes exact `"004B3"` and the disposable acceptance matrix and freeze may be completed. |

Guard recognition never grants stage authorization. Each stage requires its
own exact changed-file scope, review, and explicit authorization.

### 15.6 Preserved VENDOR-ID-003 and VENDOR-ID-004B contracts

The composition leaves all of the following VENDOR-ID-003 properties
unchanged:

- aggregate-only ownership and scope;
- canonical implementation absence until independently authorized;
- canonical query family;
- output, anomaly, count, classification, and projection semantics;
- prohibitions on schema creation/mutation/authority, mapping approval,
  ranking/suppressing/choosing a canonical or winning candidate, write,
  VENDOR-ID-003 aggregate-projection drift, runtime consumer, and runtime
  authority behavior;
- fail-closed checking; and
- existing VENDOR-ID-003 and VENDOR-ID-002 negative guarantees.

Apart from resolving this static-guard ownership conflict, it also leaves all
of the following VENDOR-ID-004B properties unchanged:

- exact CLI surface;
- exact source kinds and source contracts;
- candidate-item and candidate-relation shapes;
- the fifteen-key canonical envelope;
- the safe-reference HMAC profile and exact byte recipe;
- the eleven-class taxonomy and closed reason vocabulary;
- V1 unresolved items and empty exclusions;
- the synthetic-only lifecycle;
- exactly one SQLite `mode=ro` connection and explicit read transaction;
- bounded evidence and post-close filesystem-only no-touch verification;
- canonical JSON, exit-code, and zero-stdout failure rules;
- the unchanged VENDOR-ID-003 aggregate contract; and
- the prohibition on canonical identity, mapping approval, apply, backfill,
  reconciliation, and runtime authority.

### 15.7 Required 004B0S positive and negative matrix

The 004B0S self-test contract must include at least:

| Case | Required result | Exact issue code when failing |
|---|---|---|
| Same filename in a different directory | FAIL | `vendor_identity_evidence_path_drift` |
| Canonical directory with a different filename | FAIL | `vendor_identity_evidence_path_drift` |
| Extra, missing, early, duplicate, case-aliased, wrapped, re-exported, or otherwise invalid stage path combination | FAIL | `vendor_identity_evidence_stage_drift` |
| Unauthorized vendor/discovery marker outside the exact canonical path or closed inventory | FAIL | `vendor_identity_evidence_unresolved_target` |
| VENDOR-ID-003 aggregate query, canonical symbol, category, or aggregate result flow added to the VENDOR-ID-004B file | FAIL | `vendor_identity_evidence_ownership_conflict` |
| Mapping approval; ranking, suppressing, or choosing an approved/canonical/winning candidate; merge, write, apply, repair, backfill, consumer, or authority behavior | FAIL | `vendor_identity_evidence_forbidden_capability` |
| Whole-file, whole-function, subtree, directory, wildcard, prefix, suffix, generic allowlist, or generic issue-suppression exemption | FAIL | `vendor_identity_evidence_checker_exemption` |
| Canonical path added to a runtime-path exclusion, non-vendor-output suppression set, ignore list, or exact-path early `continue` | FAIL | `vendor_identity_evidence_checker_exemption` |
| Guard file skipped wholesale or permitted without its exact inventory, signatures, AST bundle, self-audit, and fixture-node hashes | FAIL | `vendor_identity_evidence_checker_exemption` |
| Guard top-level inventory, callable signature, AST bundle, self-audit, fixture-node hash, or deterministic-output contract drifts | FAIL | `vendor_identity_evidence_guard_contract_drift` |
| A guarded marker or SQL value moves outside its exact pinned policy or fixture node | FAIL | `vendor_identity_evidence_guard_contract_drift` |
| VENDOR-ID-004B checker missing, renamed, failing, silent, malformed, forged, multi-PASS, or emitting unexpected stdout/stderr | FAIL | `downstream_vendor_identity_evidence_guard_drift` |
| Any subprocess, argument, shell, cwd, timeout, input, output, retry, or invocation count other than the exact Section 15.3.1 protocol | FAIL | `downstream_vendor_identity_evidence_guard_drift` |
| Wrong, stale, duplicate, or changed source digest; source changes between parse, delegated result, and post-call check | FAIL | `downstream_vendor_identity_evidence_guard_drift` |
| Missing, duplicate, overlapping, extra, or unbound routed-node coverage | FAIL | `downstream_vendor_identity_evidence_guard_drift` |
| VENDOR-ID-004B checker invokes an upstream guard, recursively executes composition, or creates a delegated-result cycle | FAIL | `downstream_vendor_identity_evidence_guard_drift` |
| Mixed VENDOR-ID-003/VENDOR-ID-004B ownership or ambiguous common-query flow | FAIL | `vendor_identity_evidence_ownership_conflict` |
| Dynamic string, identifier, import, path, SQL, `eval`, `exec`, generated code, or reflective construction used to evade detection | FAIL | `vendor_identity_evidence_unresolved_target` |
| Imported, module-qualified, or relative constant; inherited attribute; default/return propagation; cross-file or bound-method forwarding; or starred positional/keyword forwarding reaches a guarded sink unresolved | FAIL | `vendor_identity_evidence_unresolved_target` |
| Recursion, cycle, fifth-level forwarding, or depth exhaustion reaches guarded evidence unresolved | FAIL | `vendor_identity_evidence_unresolved_target` |
| Missing, duplicate, nonliteral, stale, contradictory, or capability-incompatible stage marker | FAIL | `vendor_identity_evidence_stage_drift` |
| Partial implementation or capability appears before its separately authorized stage | FAIL | `vendor_identity_evidence_stage_drift` |
| `004B0S` contains the canonical implementation or any DB, environment, mutation, discovery CLI/output, artifact, or runtime capability beyond exact read-only source inspection and deterministic guard output | FAIL | `vendor_identity_evidence_forbidden_capability` |
| `004B1` contains CLI, SQL/SQLite, filesystem/path access, environment, clock/random input, stdout, artifact, app/project bootstrap, DB, or write capability | FAIL | `vendor_identity_evidence_forbidden_capability` |
| `004B2` contains nonliteral/dynamic SQL, wildcard or sensitive reads, mutation, ATTACH/DETACH, writable PRAGMA, multiple connections, or post-close SQLite access | FAIL | `vendor_identity_evidence_forbidden_capability` |
| VENDOR-ID-003 checker changes outside exact composition nodes or VENDOR-ID-002 no longer pins the revised VENDOR-ID-003 composition | FAIL | `vendor_schema_discovery_checker_contract_drift` |
| VENDOR-ID-002 guard identity required by VENDOR-ID-003 drifts | FAIL | `upstream_vendor_schema_guard_drift` |
| Exact VENDOR-ID-003 canonical implementation path appears | FAIL | `forbidden_vendor_discovery_module_path` |
| Exact frozen guard and self-test corpus at the 004B0S absence state | PASS | none |
| Exact-path, exact-shape, VENDOR-ID-004B-only marker routing with every guard and proof invariant passing in a disposable fixture | PASS | none |
| Existing VENDOR-ID-003 and VENDOR-ID-002 regression suites remain unchanged and pass | PASS | none |

The PASS cases do not authorize creation of an implementation during 004B0S.
Every FAIL row must return nonzero, emit its listed exact issue code, and emit
no normal PASS marker. Positive routing exists only in disposable self-test
source; it is not an implementation in 004B0S.

### 15.8 Frozen composition markers

```text
VENDOR-ID-004B0D STATIC GUARD COMPOSITION: FROZEN
COMPOSITION: EXACT-PATH / INDIVIDUAL-NODE / BOUNDED / FAIL-CLOSED
CANONICAL VENDOR-ID-004B PATH: tools/discover_vendor_identity_evidence.py
CANONICAL VENDOR-ID-004B GUARD: tools/check_vendor_identity_evidence.py
WHOLE-FILE EXEMPTION: FORBIDDEN
VENDOR-ID-003 AGGREGATE CONTRACT: UNCHANGED
VENDOR-ID-004B PRODUCT CONTRACT: UNCHANGED
VENDOR-ID-004B0S: REQUIRED BEFORE IMPLEMENTATION
CURRENT COMPOSITION STAGE: 004B0D
VENDOR-ID-004B STATIC GUARD: NOT IMPLEMENTED
VENDOR-ID-004B IMPLEMENTATION: NOT STARTED
```
