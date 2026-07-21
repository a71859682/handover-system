# VENDOR-ID-003 Read-only vendor discovery design baseline

| Metadata key | Frozen value |
|---|---|
| Slice ID | `VENDOR-ID-003` |
| Canonical title | `VENDOR-ID-003 Read-only vendor discovery design baseline` |
| Canonical path | `docs/vendor_id_003_read_only_vendor_discovery_baseline.md` |
| Status | `DOCS-ONLY CONTRACT PRODUCTION-FROZEN / IMPLEMENTATION NOT STARTED` |
| Governing baselines | `VENDOR-ID-001`; `VENDOR-ID-002` |
| Baseline commit | `66522e95e263edbc2e485a7e602106437ef3dd07` |
| Owner boundary | Read-only source projection, bounded anomaly classification, deterministic aggregate evidence, ambiguity preservation, and privacy-safe transient output only |
| Deferred-owner boundary | Mapping/backfill, relationship mutation, runtime consumers, authority switching, credential/session work, identity reconciliation, and Production operation remain separately owned and unauthorized |

## 1. Purpose, governing documents and non-authority boundary

### 1.1 Purpose

This document freezes one independently reviewable design for a future local,
disposable, read-only vendor discovery tool.

The future tool may:

- inspect a caller-prepared disposable SQLite database;
- read only the exact frozen source projection;
- classify only the closed anomaly taxonomy in Section 6;
- retain ambiguity rather than choose a candidate;
- emit deterministic aggregate evidence to standard output; and
- prove its behavior only against fresh disposable fixtures.

This document creates no executable capability. No source module, checker,
fixture, route, CLI, report, artifact, mapping, backfill, consumer, authority
switch, database operation, or deployment is implemented by this document.

### 1.2 Governing order

The governing order is:

1. the organization, membership, assignment, binding, lifecycle, and
   non-authority semantics frozen by the first governing baseline;
2. the exact four-table SQLite schema, indexes, constraints, migration helper,
   classifier, and schema-manifest ownership frozen by the second governing
   baseline; and
3. the narrower discovery-only rules in this document.

If a future implementation encounters a conflict, it must fail closed and
return to a docs-only reconciliation gate. It must not reinterpret either
governing baseline.

### 1.3 Capability separation

The following are distinct:

```text
physical schema
!= legacy operational truth
!= discovery evidence
!= candidate mapping
!= approved mapping
!= backfill plan
!= backfill execution
!= runtime consumer
!= authority switch
```

Presence of an organization row does not make that row authoritative.
Normalized label equality does not establish organization identity.
Discovery evidence does not approve a mapping. A reviewed mapping does not
authorize data movement. Data movement does not change runtime authority.

### 1.4 Positive authority

The only future capability authorized for implementation review is:

- bounded read-only discovery;
- deterministic anomaly classification;
- ambiguity-preserving evidence;
- aggregate and redacted output;
- no-touch source verification; and
- disposable validation.

### 1.5 Explicitly absent authority

The future tool must not:

- choose a canonical vendor or winner;
- create an organization;
- create, reactivate, revoke, or move a membership;
- create, reactivate, deactivate, or move a site assignment;
- create, reactivate, deactivate, or move a sheet binding;
- update, delete, merge, deduplicate, or repair a row;
- generate an executable mapping or backfill plan;
- execute or authorize backfill;
- change login, session, routing, authorization, or trusted-target behavior;
- associate credentials with an organization as an authority decision;
- become a route, API, UI, scheduled job, deployment hook, or runtime oracle;
- access DEV or Production data; or
- acquire operator, identity, repair, or reconciliation authority.

## 2. Owner and deferred-work matrix

### 2.1 Frozen owner matrix

| Capability or decision | Owner | State in this slice | Boundary |
|---|---|---|---|
| Organization semantics and lifecycle | `VENDOR-ID-001` | Governing and unchanged | Discovery cannot create, rename, disable, retire, reactivate, merge, or select an organization |
| Membership roles, statuses, lifecycle, owner/member cardinality, last-owner rule, and atomic owner transfer | `VENDOR-ID-001` | Governing and unchanged | Discovery can count mismatches but cannot create or transition a membership |
| Vendor-site assignment semantics and lifecycle | `VENDOR-ID-001` | Governing and unchanged | Discovery cannot establish or mutate an assignment |
| Sheet-vendor binding semantics and lifecycle | `VENDOR-ID-001` | Governing and unchanged | Discovery cannot establish or mutate a binding |
| Exact four-table SQLite projection, indexes, constraints, migration helper, classifier, and schema-manifest representation | `VENDOR-ID-002` | Implemented upstream and unchanged | Discovery performs only its minimum source-availability projection and never reports physical-schema conformance |
| Read-only source projection and closed anomaly taxonomy | This slice | Design frozen; implementation not started | Aggregate evidence only |
| Discovery-only normalization for evidence grouping | This slice | Design frozen; implementation not started | Not a business-name, identity, mapping, or authority normalizer |
| Mapping approval and controlled backfill design/execution | `VENDOR-ID-004` | Not authorized | No plan or mutation output |
| Credential, login, password, hash, and session behavior | Authentication owner | Not authorized | Credential secrets and usernames are excluded |
| Site and sheet operational authorization | Existing site/sheet owners | Not authorized | Read-only site isolation does not grant operational access |
| Runtime vendor routing and trusted-target behavior | Future runtime-consumer owner | Not authorized | Existing legacy routing remains unchanged |
| Production database access and execution | Product Owner-named operator/access gate | Not authorized | Source deployment or service health is not live discovery authority |
| Identity generation, lifecycle, linking, reconciliation, winner selection, and repair | Applicable `AUTH-ID` E2/F/G/H owners | Not authorized | Vendor evidence cannot become global-identity authority |
| Relationship mutation and lifecycle consumers | Future Product Owner-named slice | Not authorized | No creation or transition API is implied |
| Persistent reports, publication, transport, retention, and download | Future privacy/report owner | Not authorized | First implementation is transient stdout only |

### 2.2 No reverse acquisition

Reading an identifier does not transfer ownership of that identifier.
Counting a relationship does not grant relationship authority.
Detecting a conflict does not grant repair authority.
Producing a candidate count does not grant mapping authority.
Observing an existing row does not grant lifecycle authority.

The future implementation must not expose an output field, helper, callback,
exception, CLI option, or hidden mode that can be used as any of those
authorities.

## 3. Platform, database and input-path boundary

### 3.1 Supported platform

The first implementation supports exactly:

```text
operating system: Windows 11
architecture: AMD64
Python implementation: CPython
Python version boundary: 3.14.x
SQLite runtime version: 3.50.4
Unicode database version: 16.0.0
```

Any other OS, architecture, Python implementation, Python major/minor,
SQLite runtime version, or Unicode database version is an input rejection
before a SQLite connection attempt.

This platform decision is independently frozen here. It does not inherit the
platform contract of an AUTH-ID tool.

### 3.2 Public input identity

The future callable accepts one `pathlib.Path` object as `db_path`. It rejects:

- strings, path-like wrappers, bytes, file descriptors, URLs, and SQLite URIs;
- relative paths;
- nonexistent paths;
- directories and non-regular files;
- paths with an alternate data stream;
- paths containing a NUL;
- paths with a trailing space or trailing dot component; and
- paths that change identity between validation checkpoints.

The caller value is never parsed as a URI or query string.

### 3.3 System-temp containment

The only accepted database is a caller-prepared disposable file strictly below
the directory returned by the Windows `GetTempPath2W` API.

The future tool:

- obtains that root from the Windows API, not an environment variable;
- resolves the root and candidate to normalized absolute paths;
- requires the candidate to be a strict descendant, not the root itself;
- rejects every reparse-point component from the root through the file;
- rejects symbolic links, junctions, mount points, and other reparse points;
- requires the database file link count to be exactly one;
- rejects a hard link and any file identity shared with another path;
- opens no repository path to decide acceptance; and
- accepts no environment or configuration fallback.

Containment plus the single-link rule prevents a disposable path from
redirecting to the repository or canonical database.

### 3.4 Canonical and repository database rejection

Any path outside the system-temp root is rejected. Therefore the repository
database, a canonical `site.db`, a mounted persistent disk, a network share,
and a DEV or Production database are rejected regardless of filename.

A disposable fixture may be named `site.db`; the filename alone has no
authority. It remains acceptable only when all containment, identity, header,
sidecar, and topology checks pass.

### 3.5 Pre-open raw header gate

Before `sqlite3.connect`, the future tool reads exactly the first 100 raw bytes
without parsing SQL.

It requires:

- file length at least 100 bytes;
- bytes `0..15` exactly equal to `SQLite format 3\0`;
- header byte offset `18` exactly integer `1`; and
- header byte offset `19` exactly integer `1`.

Only rollback-journal format `1 / 1` is accepted. WAL format `2 / 2`, mixed
values, zero values, unknown values, short input, and malformed magic are
input rejections before any SQLite connection attempt.

The tool does not run `PRAGMA journal_mode`, convert a database, checkpoint a
WAL, or repair a header.

### 3.6 Sidecar policy

Before connection, each exact sibling must be absent:

```text
<db>-wal
<db>-shm
<db>-journal
```

An existing sidecar is an input rejection. The tool does not read, create,
delete, move, truncate, or clean a sidecar.

After connection close, all three must still be absent. A newly observed
sidecar is an internal no-touch invariant failure.

### 3.7 URI and connection contract

The connection URI is exactly:

```text
resolved_path.as_uri() + "?mode=ro"
```

The tool appends the fixed query itself. The caller cannot supply a URI,
query, VFS, cache, immutable, nolock, or mode parameter.

The connection arguments are exactly:

```text
uri = true
timeout = 0.0
isolation_level = null
check_same_thread = true
cached_statements = 0
```

`immutable=1` is prohibited. `mode=ro` preserves SQLite locking and external
change detection. No extension loading, callback injection, custom function,
custom collation, row factory supplied by a caller, or connection factory is
allowed.

### 3.8 Topology

The fixed `database_list` query must return exactly one row:

```text
seq = 0
name = "main"
file = the accepted resolved path
```

No attached database is allowed. The `temp` schema must contain no object.
The tool never runs `ATTACH` or `DETACH`.

An unexpected database row, temp object, or path mismatch is an input
rejection before business-row queries.

### 3.9 Source-object identity

The ten approved source names are:

```text
sites
sheets
tasks
vendor_accounts
vendor_contacts
vendor_work_entries
vendor_organizations
vendor_organization_memberships
vendor_site_assignments
sheet_vendor_bindings
```

An available source must have exactly:

- one `pragma_table_list` row with schema `main`, exact lowercase name, type
  `table`, exact positive integer `ncol`, and the exact `wr`/`strict` values
  below;
- one `main.sqlite_schema` row with type `table`, exact lowercase `name`,
  exact lowercase `tbl_name` equal to `name`, and an exact string SQL value;
- zero source-name case aliases;
- zero same-name view, virtual table, shadow table, index, or trigger;
- zero same-name object in `temp`; and
- zero attached schema.

The required table-list values are:

| Source group | `wr` | `strict` |
|---|---:|---:|
| Six legacy/isolation tables | `0` | `0` |
| Four new organization tables | `0` | `1` |

For an available source, `ncol` must equal the number of successful xinfo rows
for that table, including every extra/generated/hidden column. Extra columns
therefore change the observed `ncol` and fingerprint but do not make the
ordinary table unavailable and do not expand read authority.

`ncol` zero, negative, boolean, or different from the successful xinfo row
count is `source_metadata_incompatible`.

Name comparison for conflict detection uses ASCII lowercase only. A row named
`Sites`, `SITES`, or any other case variant conflicts with `sites`; it does not
satisfy the required identity.

An unrelated ordinary `main` table may be ignored. An unrelated index or
trigger whose `tbl_name` references a source table does not by itself conflict.
An object whose own `name` is an exact or case-alias source name always
conflicts unless it is the one approved ordinary table.

The stronger topology rule takes precedence: any `temp` object or attached
schema is `topology_unsupported`, input rejection, exit `2`, and no envelope.
It is not downgraded to an operational source-object anomaly.

### 3.10 Input rejection mapping

Malformed path, containment failure, reparse/hardlink evidence, malformed
header, unsupported runtime, existing sidecar, unsupported topology, and
failure to establish that the opened file is the accepted `main` database are
classified as private `input` failures.

The public callable raises the fixed public exception. The CLI mapping is
frozen in Section 11. No SQLite connection is attempted for a pre-open
rejection.

Missing or incompatible source tables/columns discovered through the accepted
read-only connection are operational incompleteness, not input rejection.
They produce the bounded envelope defined in Sections 6, 9, and 11.

## 4. Exact legacy and new-schema source inventory

### 4.1 Inventory rules

The future tool reads only the columns below. It must not use `SELECT *`.
It must not read a column merely because it exists.

Every row value is internal transient evidence. Raw labels and row identifiers
are never emitted.

### 4.2 Legacy and isolation sources

| Table | Allowed columns | Purpose | Internal grouping key | Count unit | Output rule | Missing column/table |
|---|---|---|---|---|---|---|
| `sites` | `id` | Validate a referenced site and count distinct isolated scopes | Exact positive integer site ID | Distinct sites or violating relationships, category-dependent | ID prohibited; aggregate count only | Operational incomplete |
| `sheets` | `id`, `site_id` | Establish the sole sheet-to-site isolation map | Exact positive integer sheet ID | Distinct sheets or violating relationships | IDs prohibited; aggregate count only | Operational incomplete |
| `tasks` | `sheet_id`, `vendor` | Observe legacy task labels in a sheet/site scope | Discovery-normalized label plus sheet/site | Rows or violating label groups | Raw/normalized label prohibited | Operational incomplete |
| `vendor_accounts` | `id`, `vendor_name` | Observe account-to-label evidence without credential data | Positive account ID and discovery-normalized label | Account rows, accounts, or label groups | Account ID and label prohibited | Operational incomplete |
| `vendor_contacts` | `sheet_id`, `vendor_name` | Observe only the label associated with a sheet | Discovery-normalized label plus sheet/site | Rows or label groups | Contact/person columns categorically unread; label prohibited | Operational incomplete |
| `vendor_work_entries` | `sheet_id`, `vendor_name` | Observe only the operational label associated with a sheet | Discovery-normalized label plus sheet/site | Rows or label groups | Business payload and label prohibited | Operational incomplete |

`sites.id`, `sheets.id`, every permitted `sheet_id`, and
`vendor_accounts.id` must be exact Python integers greater than zero; booleans
are invalid. A bad non-null isolation identifier is
`result_contract_failed` under Section 4.6.

### 4.3 New organization sources

| Table | Allowed columns | Purpose | Internal grouping key | Count unit | Output rule | Missing column/table |
|---|---|---|---|---|---|---|
| `vendor_organizations` | `vendor_id`, `display_name`, `organization_status` | Compare discovery-only label evidence with existing organization candidates | UUID plus discovery-normalized display name | Organization rows or label groups | UUID and display name prohibited | New-schema-dependent categories indeterminate |
| `vendor_organization_memberships` | `vendor_membership_id`, `vendor_id`, `vendor_account_id`, `membership_role`, `membership_status` | Classify account/organization relationship evidence | Membership UUID internally | Violating membership rows | All IDs prohibited | New-schema-dependent categories indeterminate |
| `vendor_site_assignments` | `vendor_site_assignment_id`, `vendor_id`, `site_id`, `assignment_status` | Classify organization/site relationship evidence | Assignment UUID internally | Violating assignment rows | All IDs prohibited | New-schema-dependent categories indeterminate |
| `sheet_vendor_bindings` | `sheet_vendor_binding_id`, `vendor_id`, `sheet_id`, `site_id`, `vendor_site_assignment_id`, `binding_status` | Classify organization/sheet/site relationship evidence | Binding UUID internally | Violating binding rows | All IDs prohibited | New-schema-dependent categories indeterminate |

The four new tables are treated as one availability group:

- all four present with the minimum exact column projection: available;
- all four absent: unavailable without claiming drift;
- any partial group or wrong required column: incomplete.

This source-availability decision is not the physical-schema classifier and
does not replace the `VENDOR-ID-002` checker or manifest.

### 4.4 Minimum column metadata

The required metadata is:

| Table | Column | Declared type | `notnull` | `pk` | `hidden` |
|---|---|---:|---:|---:|---:|
| `sites` | `id` | `INTEGER` | `0` | `1` | `0` |
| `sheets` | `id` | `INTEGER` | `0` | `1` | `0` |
| `sheets` | `site_id` | `INTEGER` | `0` | `0` | `0` |
| `tasks` | `sheet_id` | `INTEGER` | `0` | `0` | `0` |
| `tasks` | `vendor` | `TEXT` | `0` | `0` | `0` |
| `vendor_accounts` | `id` | `INTEGER` | `0` | `1` | `0` |
| `vendor_accounts` | `vendor_name` | `TEXT` | `1` | `0` | `0` |
| `vendor_contacts` | `sheet_id` | `INTEGER` | `1` | `0` | `0` |
| `vendor_contacts` | `vendor_name` | `TEXT` | `1` | `0` | `0` |
| `vendor_work_entries` | `sheet_id` | `INTEGER` | `1` | `0` | `0` |
| `vendor_work_entries` | `vendor_name` | `TEXT` | `1` | `0` | `0` |
| `vendor_organizations` | `vendor_id` | `TEXT` | `1` | `1` | `0` |
| `vendor_organizations` | `display_name` | `TEXT` | `1` | `0` | `0` |
| `vendor_organizations` | `organization_status` | `TEXT` | `1` | `0` | `0` |
| `vendor_organization_memberships` | `vendor_membership_id` | `TEXT` | `1` | `1` | `0` |
| `vendor_organization_memberships` | `vendor_id` | `TEXT` | `1` | `0` | `0` |
| `vendor_organization_memberships` | `vendor_account_id` | `INTEGER` | `1` | `0` | `0` |
| `vendor_organization_memberships` | `membership_role` | `TEXT` | `1` | `0` | `0` |
| `vendor_organization_memberships` | `membership_status` | `TEXT` | `1` | `0` | `0` |
| `vendor_site_assignments` | `vendor_site_assignment_id` | `TEXT` | `1` | `1` | `0` |
| `vendor_site_assignments` | `vendor_id` | `TEXT` | `1` | `0` | `0` |
| `vendor_site_assignments` | `site_id` | `INTEGER` | `1` | `0` | `0` |
| `vendor_site_assignments` | `assignment_status` | `TEXT` | `1` | `0` | `0` |
| `sheet_vendor_bindings` | `sheet_vendor_binding_id` | `TEXT` | `1` | `1` | `0` |
| `sheet_vendor_bindings` | `vendor_id` | `TEXT` | `1` | `0` | `0` |
| `sheet_vendor_bindings` | `sheet_id` | `INTEGER` | `1` | `0` | `0` |
| `sheet_vendor_bindings` | `site_id` | `INTEGER` | `1` | `0` | `0` |
| `sheet_vendor_bindings` | `vendor_site_assignment_id` | `TEXT` | `1` | `0` | `0` |
| `sheet_vendor_bindings` | `binding_status` | `TEXT` | `1` | `0` | `0` |

Declared types are compared after trimming surrounding ASCII whitespace and
converting ASCII letters to uppercase. The resulting value must equal the
table above. `notnull`, `pk`, and `hidden` are exact integers, not booleans.

The metadata fingerprint retains every observed column and `dflt_value`, but
source availability depends only on the required rows above. Extra legacy
columns do not expand read authority. For the four new tables, this minimum
projection permits discovery input but does not claim the full physical
schema is exact.

### 4.5 Object and metadata decision table

The terms used below are:

```text
object absent:
  no exact or case-alias source row in table_list or main.sqlite_schema

object exact:
  the exact ordinary-main-table identity in Section 3.9

object conflicting:
  any source-name row exists but object exact is false, or more than one
  identity row exists
```

The fingerprint object state is exactly `available`, `unavailable`, or
`incomplete`.

| Case | Source availability | `schema.availability` | New-schema group | Row query | Capture / code / exit | Anomaly dependency | Fingerprint representation |
|---|---|---|---|---|---|---|---|
| Source object absent and xinfo returns zero rows; source is legacy | `unavailable` | `incomplete` | Derived independently | No legacy row query executes | `incomplete`; `source_projection_unavailable`; exit `3` | Source-unavailable observed; all other categories indeterminate | Object state `unavailable`; both identity-row arrays and column array empty |
| Source object absent and xinfo returns zero rows; source is one new table | `unavailable` | `unavailable` only when all four are absent, otherwise `incomplete` | `unavailable` when all four absent; otherwise `incomplete` | No new-schema row query executes | `incomplete`; `source_projection_unavailable` for all absent, otherwise `new_schema_projection_incomplete`; exit `3` | Legacy dependencies may survive; new dependencies follow Section 6.6 | Object state `unavailable`; arrays empty |
| Source object present but xinfo returns zero rows | `incomplete` | `incomplete` | `incomplete` when new source | No affected row query | `incomplete`; `source_metadata_incompatible`; exit `3` | Source-unavailable observed; affected dependencies indeterminate | Exact observed identity rows retained; column state `incomplete` with empty column array |
| Exact object with a missing required column | `incomplete` | `incomplete` | `incomplete` when new source | No affected row query | `incomplete`; `source_metadata_incompatible`; exit `3` | Same as preceding case | Full observed columns retained; object/column state `incomplete` |
| Exact object with wrong required type, `notnull`, `pk`, or `hidden` | `incomplete` | `incomplete` | `incomplete` when new source | No affected row query | `incomplete`; `source_metadata_incompatible`; exit `3` | Same as preceding case | Full observed columns retained; object/column state `incomplete` |
| Duplicate `cid` in one xinfo result | `incomplete` | `incomplete` | `incomplete` when new source | No affected row query | `incomplete`; `source_metadata_ambiguous`; exit `3` | Same as preceding case | All tuples retained in returned order; state `incomplete` |
| Duplicate exact column name in one xinfo result | `incomplete` | `incomplete` | `incomplete` when new source | No affected row query | `incomplete`; `source_metadata_ambiguous`; exit `3` | Same as preceding case | All tuples retained in returned order; state `incomplete` |
| Exact object and required metadata plus extra columns | `available` | Derived from all sources | Derived from all new sources | Yes, but only frozen columns | No error from extra columns | Normal classification | Extra columns retained in fingerprint; no read authority added |
| All four new objects absent with zero xinfo rows | Each new source `unavailable` | `unavailable` | `unavailable` | Six legacy queries only | `incomplete`; `source_projection_unavailable`; exit `3` | Legacy categories conclusive; new dependencies unavailable | Four explicit unavailable object entries |
| Some but not all new objects absent, or any new object conflicting/incompatible | Per source `available`, `unavailable`, or `incomplete` | `incomplete` | `incomplete` | No new-schema row query | `incomplete`; `new_schema_projection_incomplete`; exit `3` | Legacy categories conclusive; new dependencies unavailable | Exact observed identity/column rows retained per source |
| Legacy object conflicting, absent, or incompatible | `incomplete` for conflict/incompatibility; `unavailable` for confirmed absence | `incomplete` | Derived independently but not queried | No row query executes | `incomplete`; exact object/metadata code; exit `3` | Source-unavailable observed; all other categories indeterminate | Exact observed conflict/absence representation retained |
| Wrong-case, wrong-type, virtual/shadow, same-name main view/index/trigger, or duplicate main identity | `incomplete` | `incomplete` | `incomplete` when new source | No affected row query | `incomplete`; `source_object_identity_failed`; exit `3` | Same dependency rule as incompatible source | Every matching table-list/schema identity tuple retained; state `incomplete` |

An exact object with zero xinfo rows is never absent. A confirmed absent object
requires zero exact/case-alias identity rows and zero xinfo rows. A source
identity conflict takes precedence over xinfo absence.

After the four topology/schema/object queries succeed, all ten xinfo queries
execute in frozen order even when an identity is absent or conflicting. The
xinfo result is metadata evidence only. No source row query executes until all
ten metadata results have been classified.

### 4.6 Row-value domain contract

Row validation completes before anomaly aggregation. A row-domain failure
stops the current phase, prevents later queries, discards every earlier
conclusive category result, and returns an incomplete envelope with:

```text
errors = ["result_contract_failed"]
schema_or_source_unavailable = observed
every other category = indeterminate
CLI exit = 3
```

No invalid value is silently filtered from an eligible set.

#### Opaque legacy-label values

The selected label slot in each legacy account, task, contact, and work-entry
tuple is an opaque source value at the tuple/result-contract layer. Exact tuple
arity, field order, and every non-label field domain remain mandatory, but the
Python type of the label slot alone never causes `result_contract_failed`.

The closed label classification is:

- only a value for which `type(value) is str` enters the frozen discovery
  normalization and the subsequent blank, length, and prohibited-Unicode
  checks;
- `value is None` is an invalid legacy label; and
- every value for which `type(value) is not str` is an invalid legacy label,
  including an integer, float, bytes/blob value, boolean, or injected custom
  object.

The label value's classification contributes only to
`legacy_vendor_label_blank_or_invalid`. It is never normalized, coerced or
stringified; never becomes an `LG`; never enters any of the other thirteen
categories' valid-label populations; and never exposes its value, bytes,
numeric representation, type name, `repr`, or exception text in output,
hashing, errors, or logs. An independent non-label fact on the same row, such
as an unresolved sheet/site, remains eligible for its own non-label predicate;
that predicate receives the `LR` but never the opaque label payload.

Every selected legacy row receives its own `LR` token before this label
classification. Each invalid-label row occurrence therefore counts exactly
once under its existing `(source kind, source row occurrence)` key, and
identical duplicate source rows continue to count as distinct occurrences.

Row-level `result_contract_failed` remains reserved for tuple arity/order
failure, a non-label field outside its exact domain, duplicate primary identity
or another already frozen closed row-domain failure that is independent of the
legacy label value's Python type.

#### UUID domains

The four distinct UUID domains are:

```text
vendor organization ID
vendor membership ID
vendor site-assignment ID
sheet-vendor-binding ID
```

Every primary or foreign value in one of those domains must be an exact
lowercase RFC 9562 UUID version 4 lexical string:

- exact Python string;
- exactly 36 ASCII characters;
- hyphens exactly at zero-based offsets `8`, `13`, `18`, and `23`;
- character at offset `14` exactly `4`;
- character at offset `19` one of `8`, `9`, `a`, `b`;
- every other character one of `0..9` or `a..f`; and
- not `00000000-0000-0000-0000-000000000000`.

No Unicode lookalike, uppercase, braces, URN, compact form, leading/trailing
text, whitespace, coercion, `uuid.UUID` normalization, or AUTH-ID semantic
validator is accepted.

This is lexical validation only. It does not generate an ID, establish
identity, or acquire AUTH-ID authority.

#### Exact vocabularies

```text
organization_status:
active
disabled
retired

membership_role:
owner
member

membership_status:
pending
active
revoked

assignment_status:
active
inactive

binding_status:
active
inactive
```

Values are exact case-sensitive strings. Null, non-string, leading/trailing
whitespace, case variant, unknown value, and coercion are
`result_contract_failed`.

Only a valid organization status of `active` or `disabled` participates in
candidate evidence. A valid `retired` row is intentionally ineligible but
remains part of observed organization population/fingerprint counts.

#### Organization display name

`display_name` must:

- be an exact string;
- have original length from 1 through 100 Unicode code points;
- contain at least one character outside the exact 29-code-point whitespace
  set in Section 7;
- successfully complete discovery normalization;
- produce a nonblank normalized result of at most 100 code points; and
- contain no prohibited post-normalization Unicode category.

Null, non-string, blank, overlength, or normalization failure is
`result_contract_failed`; it is never treated as an ineligible organization
or an orphan label.

#### Integer identifiers

Every observed site, sheet, account, or integer foreign identifier must have
exact Python type `int`, must not be `bool`, and must be greater than zero.

The sole exception is `sheets.site_id` and `tasks.sheet_id`, whose physical
columns permit null. A null value is valid row shape but is classified as a
cross-site relationship conflict. A non-null value must be a positive exact
integer.

Any other null, non-integer, boolean, zero, or negative integer in an allowed
identifier column is `result_contract_failed`.

#### Duplicate identities and references

The following must be unique within their own source:

```text
sites.id
sheets.id
vendor_accounts.id
vendor_organizations.vendor_id
vendor_organization_memberships.vendor_membership_id
vendor_site_assignments.vendor_site_assignment_id
sheet_vendor_bindings.sheet_vendor_binding_id
```

A duplicate is `result_contract_failed`, even when duplicate rows are byte
identical. UUID values from different UUID domains do not collide because the
domains are tagged.

A lexically valid foreign reference with no corresponding row is not a
row-domain failure. It is counted by the exact membership, assignment,
binding, or cross-site anomaly predicate.

Duplicate active relationship pairs with distinct valid relationship IDs are
not result-contract failures; they are counted by the applicable relationship
anomaly.

Legacy task/contact/work-entry rows have no selected primary key. Identical
tuples remain separate row occurrences and follow the category duplicate
rules.

### 4.7 Categorically prohibited reads

The future tool must not read:

- `vendor_accounts.username`;
- `vendor_accounts.password_hash`;
- credential secrets or authentication proof;
- session tokens, cookies, or session storage;
- contact name, title, phone, or other person data;
- work content, dates, headcounts, approvals, confirmation actors, or other
  unrelated business payload;
- site names or sheet names;
- provenance actor IDs, reasons, sources, or correlation IDs;
- arbitrary caller-selected tables, columns, expressions, or SQL;
- environment values; or
- PostgreSQL or any non-SQLite backend.

## 5. Fixed read-only SQL and site-isolation contract

### 5.1 Fixed-query family

The first implementation contains exactly the following fixed query family.
Every statement is a module constant. There is no runtime construction,
formatting, concatenation, identifier quoting helper, wildcard projection, or
caller SQL.

Every bind-parameter list is exactly empty. This slice accepts no business
filter, site selector, sheet selector, label selector, row limit, offset, or
caller predicate.

### 5.2 Topology and schema queries

```sql
SELECT seq, name, file
FROM pragma_database_list
ORDER BY seq;
```

Expected tuple shape:

```text
(exact int, exact str, exact str)
```

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

Expected tuple shape:

```text
(exact str, exact str, exact str, exact int, exact int, exact int)
```

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

Each schema tuple is:

```text
(exact str, exact str, exact str, exact str or null)
```

The direct SQL source name is `sqlite_schema`. The historical authorizer
callback names are `sqlite_master` for `main` and `sqlite_temp_master` for
`temp`; those aliases are callback-only and are never direct SQL sources.

### 5.3 Column metadata queries

The tool contains these ten independent literal statements:

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

The checker must prove the ten independent literals. A loop may execute the
predeclared constants in frozen order, but no executable source may substitute
a table name into SQL.

Expected tuple shape:

```text
(exact int, exact str, exact str, exact int, exact str or null, exact int, exact int)
```

Zero rows mean `unavailable` only when the source-object proof independently
confirmed absence. Zero rows for a present/conflicting object are incompatible
metadata. Duplicate `cid` or exact column-name values are ambiguous metadata.

### 5.4 Isolation and legacy data queries

```sql
SELECT id
FROM main.sites
ORDER BY id;
```

Tuple:

```text
(exact positive int)
```

```sql
SELECT id, site_id
FROM main.sheets
ORDER BY id;
```

Tuple:

```text
(exact positive int, exact positive int or null)
```

```sql
SELECT sheet_id, vendor
FROM main.tasks
ORDER BY
    sheet_id,
    vendor IS NOT NULL,
    vendor COLLATE BINARY;
```

Tuple:

```text
(exact positive int or null, opaque legacy-label source value)
```

```sql
SELECT id, vendor_name
FROM main.vendor_accounts
ORDER BY id;
```

Tuple:

```text
(exact positive int, opaque legacy-label source value)
```

```sql
SELECT sheet_id, vendor_name
FROM main.vendor_contacts
ORDER BY
    sheet_id,
    vendor_name IS NOT NULL,
    vendor_name COLLATE BINARY;
```

```sql
SELECT sheet_id, vendor_name
FROM main.vendor_work_entries
ORDER BY
    sheet_id,
    vendor_name IS NOT NULL,
    vendor_name COLLATE BINARY;
```

The last two tuple shapes are:

```text
(exact positive int, opaque legacy-label source value)
```

In these four legacy query tuple declarations, `opaque legacy-label source
value` means any Python value occupying that exact label position. It does not
weaken tuple arity, tuple order, `sheet_id`, or account-ID validation. Section
4.6 and Section 6.4 alone classify the opaque label value after those exact
non-label checks succeed.

### 5.5 New-schema data queries

These queries execute only when all four new tables have the required minimum
projection.

```sql
SELECT vendor_id, display_name, organization_status
FROM main.vendor_organizations
ORDER BY vendor_id COLLATE BINARY;
```

```sql
SELECT
    vendor_membership_id,
    vendor_id,
    vendor_account_id,
    membership_role,
    membership_status
FROM main.vendor_organization_memberships
ORDER BY vendor_membership_id COLLATE BINARY;
```

```sql
SELECT
    vendor_site_assignment_id,
    vendor_id,
    site_id,
    assignment_status
FROM main.vendor_site_assignments
ORDER BY vendor_site_assignment_id COLLATE BINARY;
```

```sql
SELECT
    sheet_vendor_binding_id,
    vendor_id,
    sheet_id,
    site_id,
    vendor_site_assignment_id,
    binding_status
FROM main.sheet_vendor_bindings
ORDER BY sheet_vendor_binding_id COLLATE BINARY;
```

Every textual identifier/status value is an exact string. Every site, sheet,
or account ID is an exact positive integer. A tuple shape or type mismatch
makes all new-schema-dependent categories indeterminate.

### 5.6 Site-isolation join semantics

Site isolation is established only by these in-memory maps:

```text
valid_site_ids = sites.id
sheet_to_site = sheets.id -> sheets.site_id
```

For each task, contact, or work-entry row:

1. its `sheet_id` must identify exactly one sheet;
2. that sheet must have exactly one non-null positive `site_id`;
3. that site must exist in `valid_site_ids`; and
4. the row receives that site only for discovery grouping.

For each binding:

1. `sheet_id` must resolve through the same map;
2. the resolved site must equal the binding `site_id`;
3. the referenced assignment must carry the same `vendor_id` and `site_id`;
4. active binding evidence requires an active assignment; and
5. all referenced rows must exist exactly once.

Missing, duplicate, null, or mismatched isolation evidence is counted under
`cross_site_relationship_conflict`. It is never silently ignored or repaired.

### 5.7 Query failure

The query order is:

1. topology;
2. table list;
3. main schema;
4. temp schema;
5. source-object proof;
6. ten column projections;
7. sites;
8. sheets;
9. tasks;
10. accounts;
11. contacts;
12. work entries;
13. organizations, memberships, assignments, and bindings when available.

Source-object proof is a pure in-memory comparison of the already captured
table-list and main/temp schema tuples and executes no additional SQL.

The fixed family contains exactly 24 statements: four topology/schema/object
queries, ten column-metadata queries, six legacy/isolation row queries, and
four new-schema row queries. A complete new-schema run executes all 24. A run
with the entire new-schema group absent executes the first 20 and marks the
four dependent query phases unavailable without preparing or executing them.

After the ten metadata queries:

- if any required legacy table/column is unavailable or incompatible, no row
  query executes;
- if the legacy projection is available, all six legacy/isolation queries
  execute;
- if the new-schema group is available, all four new-schema queries then
  execute; and
- if that group is absent, partial, or incompatible, none of those four is
  prepared or executed.

On the first SQLite/query-result-shape/tuple-arity/non-label-domain failure:

- no later query executes;
- capture status is `incomplete`;
- `schema_or_source_unavailable` is `observed`;
- every other anomaly is `indeterminate`;
- no partial observed/not-observed claim survives; and
- the operational incomplete result maps to exit `3`.

The Python type of a legacy label slot is not a query-shape or row-domain
failure. Null and non-string legacy labels continue through aggregate
classification exactly as specified in Sections 4.6 and 6.4; they do not take
this incomplete-result path.

## 6. Anomaly taxonomy, predicates and count units

### 6.1 Closed order and vocabulary

The anomaly array contains exactly these identifiers in this order:

1. `legacy_vendor_label_blank_or_invalid`
2. `legacy_label_cross_scope_reuse`
3. `multiple_vendor_accounts_ambiguous_label`
4. `vendor_account_conflicting_operational_scope`
5. `orphan_legacy_label_without_organization_evidence`
6. `organization_without_legacy_evidence`
7. `ambiguous_legacy_to_organization_candidate`
8. `conflicting_existing_organization_candidates`
9. `membership_evidence_mismatch`
10. `vendor_site_assignment_evidence_mismatch`
11. `sheet_vendor_binding_evidence_mismatch`
12. `cross_site_relationship_conflict`
13. `schema_or_source_unavailable`
14. `unknown_unclassified_anomaly`

The state vocabulary is exactly:

```text
observed
not_observed
indeterminate
```

For `observed` and `not_observed`, `count` is an exact nonnegative integer.
For `indeterminate`, `count` is null.

Duplicate source rows contribute according to each category's explicit count
unit. No implicit SQL `DISTINCT` or deduplication is allowed.

### 6.2 Fixed evidence object

Each anomaly has the same evidence object:

```text
legacy_row_count: exact nonnegative int or null
organization_row_count: exact nonnegative int or null
relationship_row_count: exact nonnegative int or null
distinct_site_count: exact nonnegative int or null
distinct_sheet_count: exact nonnegative int or null
```

The fields contain only aggregate counts relevant to the category. An
irrelevant but successfully evaluated field is zero. Every field is null when
the category is indeterminate.

No grouping key, raw label, normalized label, account ID, vendor UUID, site
ID, sheet ID, relationship ID, or source row is output or hashed.

### 6.3 Typed aggregation and exact evidence formulas

The implementation uses disjoint tagged internal namespaces:

```text
LR = ("legacy_row", source_kind, zero_based_query_row_ordinal)
LG = ("label_group", discovery_normalized_label)
AC = ("account", positive_account_id)
OR = ("organization", vendor_uuid)
MR = ("membership", membership_uuid)
AR = ("assignment", assignment_uuid)
BR = ("binding", binding_uuid)
SI = ("site", positive_site_id)
SH = ("sheet", positive_sheet_id)
EC = ("error", private_error_code)
```

Tags are part of equality. The same textual or integer payload in two
namespaces never collides.

For category `c`, the classifier constructs violation set `V_c` and these
participant sets:

```text
L_c = participating LR tokens
O_c = participating OR tokens
R_c = participating MR, AR, and BR tokens
S_c = participating SI tokens
H_c = participating SH tokens
```

Evidence formulas are exactly:

```text
legacy_row_count = cardinality(L_c)
organization_row_count = cardinality(O_c)
relationship_row_count = cardinality(R_c)
distinct_site_count = cardinality(S_c)
distinct_sheet_count = cardinality(H_c)
```

Set construction deduplicates only identical tagged tokens. It never
deduplicates by raw string across different source rows. Group-count categories
deduplicate through `LG`; row-count categories retain every `LR`.

For an observed category, evidence fields use those cardinalities. For a
not-observed category, `V_c` and all five participant sets are empty, `count`
is zero, and all five evidence fields are zero even when the relevant source
population is nonempty. For an indeterminate category, `count` and all five
evidence fields are null; no partial cardinality survives.

The exact category formulas are:

| Category | Exact `count_unit` | Relevant population | `V_c` and `count` | Exact participant sets | Exact disposition |
|---|---|---|---|---|---|
| `legacy_vendor_label_blank_or_invalid` | `legacy_source_rows` | Every selected account/task/contact/work-entry row | `V_c` is every `LR` whose selected label satisfies Section 6.4 predicate; `count = cardinality(V_c)` | `L_c = V_c`; `O_c = R_c = empty`; `S_c`/`H_c` contain the valid resolved site/sheet of participating scoped rows, excluding account rows and unresolved scopes | `review legacy label quality; do not rewrite` |
| `legacy_label_cross_scope_reuse` | `normalized_label_groups` | Valid site-resolved task/contact/work-entry labels | `V_c` is each `LG` with at least two sites; `count = cardinality(V_c)` | `L_c` is all scoped legacy rows in violating groups; `O_c = R_c = empty`; `S_c`/`H_c` are all valid sites/sheets of those rows | `retain distinct scopes; mapping is ambiguous` |
| `multiple_vendor_accounts_ambiguous_label` | `normalized_label_groups` | Valid account labels | `V_c` is each `LG` with at least two distinct `AC`; `count = cardinality(V_c)` | `L_c` is all account rows in violating groups; every other participant set is empty | `do not select an account or organization` |
| `vendor_account_conflicting_operational_scope` | `vendor_accounts` | Every valid `AC`, legacy operational scopes sharing its label, non-revoked memberships, and active assignments for linked organizations | `V_c` is each violating `AC`; `count = cardinality(V_c)` | `L_c` is the account row plus all valid legacy rows sharing its normalized label; `O_c` is every organization referenced by a `pending` or `active` membership for `V_c`; `R_c` is every such membership plus every active assignment for those organizations; `S_c` is the union of valid legacy sites and those active-assignment sites; `H_c` is every valid legacy sheet in `L_c` | `preserve conflict; no account-to-organization decision` |
| `orphan_legacy_label_without_organization_evidence` | `normalized_label_groups` | All valid legacy label groups and eligible organizations | `V_c` is each legacy `LG` with zero eligible candidate `OR`; `count = cardinality(V_c)` | `L_c` is all legacy rows in violating groups; `O_c = R_c = empty`; `S_c`/`H_c` are valid scoped sites/sheets of those rows | `evidence absent; do not create an organization` |
| `organization_without_legacy_evidence` | `vendor_organization_rows` | Every eligible organization and all valid legacy groups | `V_c` is each eligible `OR` with zero equal legacy `LG`; `count = cardinality(V_c)` | `O_c = V_c`; all other participant sets are empty | `do not retire, delete, or treat as authoritative` |
| `ambiguous_legacy_to_organization_candidate` | `normalized_label_groups` | All valid legacy groups and eligible organizations | `V_c` is each legacy `LG` with at least two eligible candidate `OR`; `count = cardinality(V_c)` | `L_c` is all legacy rows in violating groups; `O_c` is all eligible candidates for those groups; `R_c = empty`; `S_c`/`H_c` are valid scoped sites/sheets of participating legacy rows | `preserve candidate multiplicity; no winner` |
| `conflicting_existing_organization_candidates` | `normalized_label_groups` | Every eligible organization | `V_c` is each organization-name `LG` containing at least two `OR`; `count = cardinality(V_c)` | `O_c` is every organization in violating groups; all other participant sets are empty | `duplicate review only; no merge or canonical selection` |
| `membership_evidence_mismatch` | `membership_rows` | Every valid membership plus referenced account/organization evidence | `V_c` is each violating `MR`; `count = cardinality(V_c)` | `R_c = V_c`; `L_c` contains each existing referenced account row; `O_c` contains each existing referenced organization; `S_c = H_c = empty` | `relationship evidence conflict; no membership mutation` |
| `vendor_site_assignment_evidence_mismatch` | `assignment_rows` | Every valid assignment plus referenced organization/site evidence | `V_c` is every violating `AR`, including every row participating in a duplicate active pair; `count = cardinality(V_c)` | `R_c = V_c`; `O_c` contains existing referenced organizations; `S_c` contains valid mentioned sites; `L_c = H_c = empty` | `relationship evidence conflict; no assignment mutation` |
| `sheet_vendor_binding_evidence_mismatch` | `binding_rows` | Every valid binding plus referenced organization/assignment/sheet/site evidence | `V_c` is every violating `BR`, including every row participating in a duplicate active pair; `count = cardinality(V_c)` | `R_c` is `V_c` plus every existing referenced `AR`; `O_c` contains existing referenced organizations; `S_c`/`H_c` contain valid mentioned/resolved sites/sheets; `L_c = empty` | `relationship evidence conflict; no binding mutation` |
| `cross_site_relationship_conflict` | `typed_conflict_groups` | Legacy isolation rows, normalized multi-site label groups, and binding/assignment site evidence | `V_c` is the tagged union of `("legacy_scope", LR)` for unresolved legacy scopes, `("multi_site_label", LG)` for multi-site labels, and `("binding_site_conflict", BR)` for cross-site bindings; `count = cardinality(V_c)` | `L_c` is every participating legacy row; `O_c` is every existing organization referenced by participating bindings; `R_c` is participating `BR` plus existing referenced `AR`; `S_c`/`H_c` contain every valid site/sheet participating in a conflict | `fail closed by site; do not expose or map across sites` |
| `schema_or_source_unavailable` | `private_error_codes` | Deduplicated closed operational error codes for the run | `V_c` is the sorted set of distinct `EC`; `count = cardinality(V_c)` | All five participant sets are empty, so all evidence fields are zero | `capture incomplete; no partial conclusion` |
| `unknown_unclassified_anomaly` | `classification_boundary` | No first-slice observation population | Complete capture: `V_c = empty`, count `0`; incomplete capture: count null | Complete capture: all participant sets empty and all evidence fields zero; incomplete capture: all fields null | `extend only through a new frozen taxonomy review` |

Participant-set construction order is:

1. validate exact tuple arity/order, every non-label field domain, and every
   already frozen new-schema row domain;
2. build one `LR` for every selected legacy row occurrence and build the valid
   `AC`, `OR`, `MR`, `AR`, `BR`, `SI`, and `SH` tokens;
3. classify each opaque legacy label, sending null/non-string values directly
   to the invalid-label predicate without normalization or stringification;
4. build normalized `LG` groups only from exact-string labels that pass every
   frozen normalization validity check;
5. evaluate predicates in the closed category order;
6. build each `V_c`;
7. derive participant sets from the table above;
8. compute cardinalities; and
9. discard every token payload before envelope construction.

This sequence excludes every null/non-string label from every other
label-based population. It does not suppress a distinct non-label source,
reference, sheet, or site defect carried by the same row; such a defect may
contribute the row's `LR` to its independently defined category without
normalizing, grouping, or otherwise consuming the opaque label.

No raw grouping key enters output, canonical JSON, evidence hashing, error
text, or logging.

### 6.4 Category contracts

#### `legacy_vendor_label_blank_or_invalid`

- Sources: the label columns in accounts, tasks, contacts, and work entries.
- Predicate: value is null, is not an exact string, becomes blank under
  discovery normalization, exceeds 100 Unicode code points after
  normalization, or contains a prohibited Unicode category after frozen
  whitespace mapping.
- Aggregation key: `(source kind, source row occurrence)`.
- Count unit: source rows.
- Duplicate handling: every duplicate row counts.
- Null and every non-string value produce one violating `LR` without calling
  normalization. Non-string includes integer, float, bytes/blob, boolean, and
  injected custom-object values.
- A non-string value produces no `LG`, is excluded from all other thirteen
  valid-label populations, and cannot cause `result_contract_failed` solely
  because of its type.
- Raw value, bytes, numeric representation, type name, `repr`, and exception
  text are never output, hashed, included in errors, or logged.
- New schema required: no.
- Disposition: `review legacy label quality; do not rewrite`.

#### `legacy_label_cross_scope_reuse`

- Sources: valid task, contact, and work-entry labels with resolved sites.
- Predicate: one normalized label occurs in two or more distinct site scopes.
- Aggregation key: normalized label.
- Count unit: violating label groups.
- Duplicate handling: repeated rows inside one site do not add a group; they
  remain reflected in aggregate evidence.
- New schema required: no.
- Disposition: `retain distinct scopes; mapping is ambiguous`.

#### `multiple_vendor_accounts_ambiguous_label`

- Sources: valid account labels.
- Predicate: one normalized label belongs to two or more distinct account IDs.
- Aggregation key: normalized label.
- Count unit: violating label groups.
- Duplicate handling: duplicate account rows with the same positive ID are a
  source integrity failure, not a second account.
- New schema required: no.
- Disposition: `do not select an account or organization`.

#### `vendor_account_conflicting_operational_scope`

- Sources: each account label and site-resolved task/contact/work-entry labels.
- Predicate: the normalized account label occurs in two or more operational
  sites, or the account participates in two or more non-revoked memberships
  whose organizations have distinct active site-assignment sets.
- Aggregation key: account ID.
- Count unit: violating accounts.
- Duplicate handling: each account counts at most once.
- New schema required: only the membership/assignment branch; the legacy
  multi-site branch remains observable without new schema.
- Disposition: `preserve conflict; no account-to-organization decision`.

#### `orphan_legacy_label_without_organization_evidence`

- Sources: every valid normalized legacy label group and eligible organization
  display-name group.
- Eligible organization: status exactly `active` or `disabled`; `retired` is
  excluded from candidate evidence.
- Predicate: a legacy label group has zero eligible organization candidates
  with the same discovery-normalized display name.
- Aggregation key: normalized legacy label.
- Count unit: orphan legacy label groups.
- Duplicate handling: rows across all legacy sources form one group.
- New schema required: yes.
- Disposition: `evidence absent; do not create an organization`.

#### `organization_without_legacy_evidence`

- Sources: eligible organizations and all valid legacy labels.
- Predicate: an eligible organization has no discovery-normalized legacy
  label equal to its normalized display name.
- Aggregation key: organization UUID.
- Count unit: organization rows.
- Duplicate handling: every eligible organization row counts independently.
- New schema required: yes.
- Disposition: `do not retire, delete, or treat as authoritative`.

#### `ambiguous_legacy_to_organization_candidate`

- Sources: valid legacy groups and eligible organizations.
- Predicate: one normalized legacy label has two or more eligible organization
  candidates with the same normalized display name.
- Aggregation key: normalized legacy label.
- Count unit: ambiguous legacy label groups.
- Duplicate handling: all legacy occurrences form one group.
- New schema required: yes.
- Disposition: `preserve candidate multiplicity; no winner`.

#### `conflicting_existing_organization_candidates`

- Sources: eligible organizations.
- Predicate: two or more eligible organization UUIDs share one
  discovery-normalized display name.
- Aggregation key: normalized display name.
- Count unit: conflicting organization-name groups.
- Duplicate handling: each UUID is a distinct candidate; creation order,
  status preference, and row order do not resolve the conflict.
- New schema required: yes.
- Disposition: `duplicate review only; no merge or canonical selection`.

#### `membership_evidence_mismatch`

- Sources: memberships, accounts, and organizations.
- Precondition: every selected membership value passed Section 4.6.
- Predicate: a membership references a missing account or organization; or,
  when both references exist, its legacy account label is an exact string that
  passes every frozen label-validity check and its valid organization display
  name has an unequal discovery-normalized value. A null/non-string/otherwise
  invalid account label is classified only by the invalid-label category and
  does not itself make the membership mismatched.
- Aggregation key: membership UUID.
- Count unit: violating membership rows.
- Duplicate handling: every relationship row counts once.
- New schema required: yes.
- Disposition: `relationship evidence conflict; no membership mutation`.

#### `vendor_site_assignment_evidence_mismatch`

- Sources: assignments, organizations, and sites.
- Precondition: every selected assignment value passed Section 4.6.
- Predicate: an assignment references a missing organization/site; is active
  for a retired organization; or duplicates an active
  `(vendor UUID, site ID)` pair.
- Aggregation key: assignment UUID, except duplicate active pairs are first
  grouped by `(vendor UUID, site ID)` and all participating rows count.
- Count unit: violating assignment rows.
- Duplicate handling: a row satisfying multiple clauses counts once.
- New schema required: yes.
- Disposition: `relationship evidence conflict; no assignment mutation`.

#### `sheet_vendor_binding_evidence_mismatch`

- Sources: bindings, organizations, assignments, sheets, and sites.
- Precondition: every selected binding value passed Section 4.6.
- Predicate: a binding references a missing row; carries a vendor/site
  different from its assignment; carries a site different from its sheet; is
  active without an active same-vendor/same-site assignment; or duplicates an
  active `(vendor UUID, sheet ID)` pair.
- Aggregation key: binding UUID, except duplicate active pairs are grouped and
  all participating rows count.
- Count unit: violating binding rows.
- Duplicate handling: a row satisfying multiple clauses counts once.
- New schema required: yes.
- Disposition: `relationship evidence conflict; no binding mutation`.

#### `cross_site_relationship_conflict`

- Sources: all site-resolved legacy labels, sheets, sites, assignments, and
  bindings.
- Predicate: a legacy row cannot resolve to exactly one valid sheet/site; one
  normalized legacy label spans multiple sites; or a binding/assignment
  relationship crosses the sheet's canonical site.
- Label boundary: the unresolved-sheet/site clause is an independent
  non-label predicate and may include the `LR` of a row whose label is null or
  non-string. That row's opaque label value is neither consumed nor grouped;
  the label itself contributes only to the invalid-label category. The
  multi-site-label clause accepts only valid normalized `LG` values.
- Aggregation key: violating legacy row occurrence or relationship UUID;
  multi-site label groups count as one group.
- Count unit: violating evidence groups.
- Duplicate handling: one row/relationship/group counts once even if several
  cross-site clauses apply.
- New schema required: no for legacy isolation; yes for relationship clauses.
- Disposition: `fail closed by site; do not expose or map across sites`.

#### `schema_or_source_unavailable`

- Sources: platform, path, header, topology, metadata, source availability,
  fixed queries, result shapes, checkpoints, and required new-schema group.
- Predicate: an accepted run cannot complete every category because a required
  source/query/checkpoint is unavailable or operationally fails.
- Aggregation key: fixed private error code.
- Count unit: unavailable source/query/checkpoint codes.
- Duplicate handling: each distinct code counts once in sorted order.
- Disposition: `capture incomplete; no partial conclusion`.

Pre-open input rejections and internal invariant failures do not return an
anomaly envelope; they raise/map through Section 11.

#### `unknown_unclassified_anomaly`

- First-slice predicate: none.
- Aggregation key: none.
- Count unit: fixed classification boundary.
- Complete capture: state `not_observed`, count `0`.
- Incomplete capture: state `indeterminate`, count null.
- State `observed` is impossible in the first implementation.
- Disposition: `extend only through a new frozen taxonomy review`.

### 6.5 Reasons

Each category uses exactly one of:

```text
predicate_satisfied
predicate_not_satisfied
source_incomplete
```

`observed` pairs with `predicate_satisfied`; `not_observed` pairs with
`predicate_not_satisfied`; `indeterminate` pairs with `source_incomplete`.

### 6.6 Dependency and capture decision table

| Condition | `capture_status` | `errors` | Category result |
|---|---|---|---|
| Legacy and new-schema projections available; all 24 queries and checkpoints succeed | `complete` | Empty | Every category is conclusively observed/not observed; unknown is not observed |
| Required legacy object confirmed absent | `incomplete` | `["source_projection_unavailable"]` | Source-unavailable observed; all other categories indeterminate |
| Required source identity conflicts | `incomplete` | Sorted distinct `source_object_identity_failed` plus any other metadata code observed before row queries | Source-unavailable observed; all affected categories indeterminate |
| Present source has zero xinfo rows or missing/wrong required metadata | `incomplete` | Sorted distinct `source_metadata_incompatible` plus other observed metadata codes | Source-unavailable observed; all affected categories indeterminate |
| Source has duplicate xinfo `cid` or column name | `incomplete` | Sorted distinct `source_metadata_ambiguous` plus other observed metadata codes | Source-unavailable observed; all affected categories indeterminate |
| All four new tables absent | `incomplete` | `["source_projection_unavailable"]` | Legacy-only categories remain conclusive; every new-schema-dependent branch is unavailable |
| New-schema group partial or incompatible | `incomplete` | `["new_schema_projection_incomplete"]` | Same dependency treatment as absent, without a physical-schema drift claim |
| Connection-open, BEGIN, topology-query, or topology-tuple operational failure before topology proof | `incomplete` | Exact one of `connection_open_failed`, `begin_failed`, `topology_query_failed`, or `result_contract_failed`, plus `concurrent_source_change` only under the exact Section 12.1 composition rule; ASCII-sorted | Exact pre-topology projection in Section 9.2: all three topology fields null, every schema availability field incomplete, fingerprint null, source-unavailable observed, other 13 categories indeterminate, summary `1 / 0 / 13` |
| First schema/metadata/row SQLite operational failure after successful topology proof | `incomplete` | Exact phase code from Section 11.5, plus `concurrent_source_change` only under the exact Section 12.1 composition rule; ASCII-sorted | Proven non-null topology survives; source-unavailable observed; all other categories indeterminate; schema fingerprint/availability survival follows the exact phase-specific Section 11.5 row, and no row/anomaly conclusion survives unless Section 4.5 or the new-schema dependency rule explicitly preserves it |
| First tuple arity/order, non-label value, or other frozen result-contract failure after successful topology proof | `incomplete` | `["result_contract_failed"]`, with `concurrent_source_change` added and ASCII-sorted only under Section 12.1 | Proven non-null topology survives; source-unavailable observed; all other categories indeterminate; no earlier row/anomaly result survives, while a fully completed schema projection survives only as frozen in Section 11.5 |
| Concurrent size/mtime/hash change with successful rollback and no tool mutation and no earlier operational error | `incomplete` | `["concurrent_source_change"]` | Proven topology survives when topology proof completed; otherwise the exact pre-topology projection applies |
| Programming/RuntimeError, authorizer invariant, cleanup, aggregation, post-close identity/no-touch, fingerprint, canonicalization, hash, or final self-validation failure | No envelope | Not emitted | Public exception; CLI exit 4 |

Legacy-only categories are:

```text
legacy_vendor_label_blank_or_invalid
legacy_label_cross_scope_reuse
multiple_vendor_accounts_ambiguous_label
```

New-schema-dependent categories are:

```text
orphan_legacy_label_without_organization_evidence
organization_without_legacy_evidence
ambiguous_legacy_to_organization_candidate
conflicting_existing_organization_candidates
membership_evidence_mismatch
vendor_site_assignment_evidence_mismatch
sheet_vendor_binding_evidence_mismatch
```

These two categories have one legacy branch and one new-schema branch:

```text
vendor_account_conflicting_operational_scope
cross_site_relationship_conflict
```

For a mixed category:

1. if any available branch satisfies its predicate, state is `observed`;
2. otherwise, if any required branch is unavailable, state is
   `indeterminate`;
3. otherwise state is `not_observed`.

`schema_or_source_unavailable` is observed for every incomplete envelope.
`unknown_unclassified_anomaly` is not observed only for a complete envelope
and is indeterminate for every incomplete envelope.

## 7. Normalization, ambiguity and mapping-evidence boundary

### 7.1 Scope

The algorithm here is named:

```text
VENDOR_DISCOVERY_EVIDENCE_NORMALIZATION_V1
```

It exists only to form internal evidence groups. It does not freeze a business
display-name policy and does not replace the separately deferred display-name
normalization owner.

### 7.2 Exact algorithm

For an exact Python string:

1. apply Unicode NFKC normalization;
2. apply Unicode default `casefold`;
3. apply Unicode NFKC normalization again;
4. replace each of the following 29 code points with ASCII U+0020:

```text
U+0009 U+000A U+000B U+000C U+000D
U+001C U+001D U+001E U+001F U+0020
U+0085 U+00A0 U+1680
U+2000 U+2001 U+2002 U+2003 U+2004 U+2005 U+2006
U+2007 U+2008 U+2009 U+200A
U+2028 U+2029 U+202F U+205F U+3000
```

5. collapse each maximal run of ASCII U+0020 to one U+0020;
6. remove leading and trailing ASCII U+0020;
7. reject a blank result;
8. reject a result longer than 100 Unicode code points; and
9. reject a remaining code point whose Unicode general category begins with
   `C` (`Cc`, `Cf`, `Cs`, `Co`, or `Cn`).

Punctuation is preserved except for compatibility changes performed by NFKC.
No punctuation is deleted. No transliteration, diacritic removal, width rule
outside NFKC, locale collation, locale case rule, phonetic match, token
reordering, synonym, abbreviation, or fuzzy match is allowed.

The algorithm is locale independent. Applying it to its own successful result
must return exactly the same code-point sequence.

### 7.3 Ambiguity

```text
normalized equality
!= identity proof
!= organization membership proof
!= mapping approval
!= backfill authorization
```

Zero candidates, one candidate, multiple candidates, conflicting scopes, and
insufficient evidence remain distinct internal outcomes.

Even exactly one normalized candidate is only discovery evidence. It is not
output as a row-level mapping and cannot authorize a later write.

No candidate list, candidate identifier, confidence score, similarity score,
winner score, ranking, recommendation, or canonical-vendor selection appears
in output.

### 7.4 Winner prohibitions

The future tool must not choose by:

- lowest or highest identifier;
- first or last sort position;
- earliest or latest timestamp;
- active/disabled status preference;
- existing-row preference;
- most accounts, sites, sheets, contacts, tasks, or work entries;
- lexical similarity;
- caller preference; or
- any hidden fallback.

## 8. Privacy, credential exclusion and redaction

### 8.1 Aggregate-only output

The output contains counts and fixed vocabulary only. It contains no
per-label, per-account, per-site, per-sheet, per-organization, or
per-relationship evidence object.

Raw and normalized labels are internal transient values. They are discarded
before envelope construction and never enter the evidence hash.

### 8.2 Excluded values

Output, error text, logs, exception attributes, hashes, and debug paths must
not contain:

- password or password hash;
- username;
- account, vendor, membership, assignment, binding, site, sheet, task,
  contact, or work-entry identifier;
- session value, cookie, token, credential proof, or authentication result;
- contact name, phone, title, or personal data;
- raw or normalized vendor label;
- site or sheet name;
- database path or filename;
- environment value;
- SQL row representation; or
- a mutation-ready candidate pair.

### 8.3 No reversible or dictionary identifier

The first implementation does not emit a raw hash, unsalted hash, keyed hash,
token, truncated label, prefix, suffix, or encoded representation of a label
or row identifier.

The only SHA-256 values are source-file integrity, schema-projection integrity,
tool source integrity, and envelope integrity. None is a label pseudonym.

### 8.4 Aggregate sensitivity

Exact nonnegative counts are permitted only in the disposable local contract.
The independent Production operator gate must reconsider minimum-cell
suppression and audience rules before any live-data use. This document does
not pre-approve live aggregate disclosure.

## 9. Deterministic output JSON and evidence hashing

### 9.1 Canonical envelope

The callable returns exactly:

```text
{
  "schema_version": str,
  "capture_status": str,
  "run": {
    "run_id": str,
    "captured_at": str,
    "tool_commit": str,
    "tool_source_sha256": str,
    "platform": str,
    "python_version": str,
    "sqlite_version": str,
    "unicode_version": str
  },
  "source": {
    "file_size_before": int,
    "file_size_after": int,
    "mtime_ns_before": int,
    "mtime_ns_after": int,
    "source_sha256_before": str,
    "source_sha256_after": str,
    "sidecars_before": {
      "journal": bool,
      "shm": bool,
      "wal": bool
    },
    "sidecars_after": {
      "journal": bool,
      "shm": bool,
      "wal": bool
    },
    "topology": {
      "attached_count": int or null,
      "main_only": bool or null,
      "temp_object_count": int or null
    }
  },
  "schema": {
    "projection_version": str,
    "availability": str,
    "fingerprint_sha256": str or null,
    "legacy_sources": {
      "sheets": str,
      "sites": str,
      "tasks": str,
      "vendor_accounts": str,
      "vendor_contacts": str,
      "vendor_work_entries": str
    },
    "new_schema_group": str
  },
  "anomalies": [
    {
      "id": str,
      "state": str,
      "count": int or null,
      "count_unit": str,
      "reason": str,
      "disposition": str,
      "evidence": {
        "legacy_row_count": int or null,
        "organization_row_count": int or null,
        "relationship_row_count": int or null,
        "distinct_site_count": int or null,
        "distinct_sheet_count": int or null
      }
    }
  ],
  "summary": {
    "indeterminate_category_count": int,
    "not_observed_category_count": int,
    "observed_category_count": int
  },
  "errors": [str],
  "evidence_sha256": str
}
```

There are no optional keys. JSON null appears only where explicitly shown.
No additional property is allowed.

An opaque legacy-label value never enters this envelope or the preimage of
`evidence_sha256`. Its label classification retains only the aggregate
invalid-label count and the already frozen participant cardinalities. An
independent non-label defect on the same row may also affect its own aggregate
category, but receives no label payload. The raw value, string conversion,
bytes, numeric representation, type name, `repr`, and exception text are
prohibited from every property, error, hash input, and log.

### 9.2 Fixed values

```text
schema_version = "VENDOR_ID_003_DISCOVERY_V1"
schema.projection_version = "VENDOR_ID_003_SOURCE_SCHEMA_V1"
capture_status = "complete" or "incomplete"
platform = "windows-11-amd64"
python_version = exact runtime major.minor.patch
sqlite_version = "3.50.4"
unicode_version = "16.0.0"
```

Every source availability value is exactly:

```text
available
unavailable
incomplete
```

The new-schema group uses the same vocabulary.

`schema.availability` is:

```text
available:
  all six legacy sources and all four new sources are available

unavailable:
  all six legacy sources are available and all four new sources are
  confirmed unavailable

incomplete:
  every other combination, including legacy absence/incompatibility,
  partial new schema, identity conflict, metadata query failure, and
  result-contract failure
```

Topology nullability is all-or-none:

1. after the topology query and its tuple/value validation succeed,
   `attached_count` is an exact nonnegative integer, `main_only` is an exact
   boolean, and `temp_object_count` is an exact nonnegative integer;
2. if connection open, `BEGIN`, topology query, or topology tuple validation
   fails operationally before topology proof completes, all three fields are
   JSON null;
3. no envelope may contain one or two null topology fields;
4. a complete capture may not contain any null topology field;
5. schema, metadata, row, or later operational failure after topology proof
   retains all three proved non-null values; and
6. unsupported topology is input rejection with exit `2` and no envelope. It
   is never represented by a null-topology envelope.

The exact pre-topology operational incomplete projection is:

```text
capture_status = "incomplete"

source.topology = {
  "attached_count": null,
  "main_only": null,
  "temp_object_count": null
}

schema.availability = "incomplete"
schema.legacy_sources = {
  "sheets": "incomplete",
  "sites": "incomplete",
  "tasks": "incomplete",
  "vendor_accounts": "incomplete",
  "vendor_contacts": "incomplete",
  "vendor_work_entries": "incomplete"
}
schema.new_schema_group = "incomplete"
schema.fingerprint_sha256 = null
```

The anomaly projection for that envelope is exactly:

```text
schema_or_source_unavailable:
  state = "observed"
  count = cardinality(errors)
  count_unit = "private_error_codes"
  reason = "predicate_satisfied"
  legacy_row_count = 0
  organization_row_count = 0
  relationship_row_count = 0
  distinct_site_count = 0
  distinct_sheet_count = 0

every other 13 categories:
  state = "indeterminate"
  count = null
  reason = "source_incomplete"
  legacy_row_count = null
  organization_row_count = null
  relationship_row_count = null
  distinct_site_count = null
  distinct_sheet_count = null

summary.observed_category_count = 1
summary.not_observed_category_count = 0
summary.indeterminate_category_count = 13
```

Its `errors` array is respectively:

```text
connect operational failure:
["connection_open_failed"]

BEGIN operational failure:
["begin_failed"]

topology query operational failure:
["topology_query_failed"]

topology tuple/result-contract failure:
["result_contract_failed"]
```

If the required post-attempt/post-close checkpoint also proves a same-identity
size, mtime, or hash change, retain the original operational code, add
`concurrent_source_change`, deduplicate, and sort the two codes by ASCII. The
result is not implementation-selectable. Identity replacement, a sidecar,
cleanup failure, or inability to prove no-touch suppresses the envelope and
uses the internal mapping in Sections 11.5 and 12.1.

For every pre-topology envelope, `file_size_before`, `mtime_ns_before`, and
`source_sha256_before` are the exact pre-open measurements.
`file_size_after`, `mtime_ns_after`, and `source_sha256_after` are the exact
post-attempt or post-close measurements. The three `sidecars_before` values
and three `sidecars_after` values are exact observed booleans. No zero, false,
repeated, or copied value is a sentinel. With no concurrent change, the before
and after size, mtime, and hash values are equal. With the permitted
same-identity concurrent change they retain their observed differences and
the errors array follows the composition rule above.

`tool_source_sha256`, both source hashes, the schema fingerprint, and the
evidence hash are uppercase strings of exactly 64 hexadecimal characters.
`tool_source_sha256` is calculated over the discovery module's raw bytes.

### 9.3 Schema fingerprint

The observed source schema projection is:

```text
{
  "source_objects": [
    [
      expected_table_name,
      object_state,
      [[schema, name, type, ncol, wr, strict], ...],
      [[type, name, tbl_name, sql_or_null], ...]
    ],
    ...
  ],
  "legacy_columns": [
    [table_name, availability, [[cid, name, type, notnull, default, pk, hidden], ...]],
    ...
  ],
  "new_schema_columns": [
    [table_name, availability, [[cid, name, type, notnull, default, pk, hidden], ...]],
    ...
  ],
  "vendor_objects": [
    [type, name, tbl_name, sql_or_null],
    ...
  ]
}
```

`source_objects` contains exactly ten entries in Section 3.9 order. Its
table-list rows are those whose ASCII-lowercased `name` equals the expected
name. Its schema rows are those whose ASCII-lowercased own `name` equals the
expected name. Both nested arrays retain their fixed-query order.

Legacy and new-schema column entries are ordered exactly as Section 4 lists
them. Successful xinfo tuples are retained in `cid` query order, including
duplicates and extra columns.

`vendor_objects` contains only rows whose exact `name` or `tbl_name` is one of
the four new tables or fifteen explicit indexes, ordered by the main schema
query. It is evidence for fingerprinting only and does not report physical
schema conformance.

Missing tables use `availability = "unavailable"` and an empty column array.
An exact/conflicting object with a successfully returned but invalid column
projection uses `availability = "incomplete"` and retains every observed
column tuple. A metadata query/tuple failure that prevents construction of the
complete observed projection makes the fingerprint null.

The schema fingerprint is uppercase SHA-256 of canonical JSON bytes for this
projection. It is null only when metadata capture itself is incomplete.
It is an observed source fingerprint, not a physical-schema PASS result.

Connection-open, BEGIN, topology-query, and topology-tuple operational
failures occur before an observed schema projection and always use a null
fingerprint. Once topology is proved, a later failure still uses a null
fingerprint unless every fixed schema/object/xinfo query required for the
complete projection has succeeded and the projection can be canonically
reconstructed. A completed observed projection remains available across a
later row-query/result operational failure.

### 9.4 Canonical JSON

Canonical JSON bytes are:

```text
UTF-8
ensure_ascii = false
sort_keys = true
separators = (",", ":")
allow_nan = false
no BOM
no trailing whitespace
```

Arrays retain their frozen semantic order. Object keys are serialized by
Unicode code-point order through `sort_keys`.

### 9.5 Evidence hash

To compute `evidence_sha256`:

1. construct the complete envelope without the `evidence_sha256` property;
2. canonicalize it using Section 9.4;
3. compute SHA-256 over those exact bytes;
4. uppercase the 64 hexadecimal characters; and
5. insert the result as `evidence_sha256`.

Verification removes only that property, repeats the recipe, and requires an
exact match.

The hash is envelope-integrity evidence only. It is not a signature, approval,
identity proof, authorization proof, execution token, idempotency token,
mapping identifier, or permission to persist or act.

### 9.6 Ordering

- anomaly entries use the Section 6 order;
- error codes use ascending ASCII order with duplicates removed;
- schema tables use Section 4 order;
- schema columns use `cid`;
- source count fields are fixed object keys; and
- summary counts are derived from exactly 14 anomaly entries.

The summary formulas are exactly:

```text
summary.observed_category_count =
  number of anomaly entries whose state is "observed"

summary.not_observed_category_count =
  number of anomaly entries whose state is "not_observed"

summary.indeterminate_category_count =
  number of anomaly entries whose state is "indeterminate"
```

The three values count category entries only. They do not add anomaly
`count`, evidence fields, source rows, groups, relationships, sites, sheets,
or error codes. Their sum must equal exactly `14`.

## 10. Public callable, CLI and export surface

### 10.1 Module and exports

The future module path is exactly:

```text
tools/discover_vendor_organization_readiness.py
```

Its `__all__` is exactly:

```text
VendorOrganizationDiscoveryError
discover_vendor_organization_readiness
```

No connection factory, query factory, callback, serializer, writer, scanner
registry, plugin, repository abstraction, ORM model, route, job, or other
public symbol is allowed.

The future module's two private type aliases use these exact imports:

```python
from pathlib import Path as _Path
from typing import Sequence as _Sequence
```

`Path`, `Sequence`, `_Path`, `_Sequence`, and `_main` are not exports. The
module does not use `from __future__ import annotations`: the annotation source
below uses explicit string literals, so each raw `__annotations__` entry has
exactly one string layer and remains resolvable through the private aliases.

### 10.2 Public callable

The exact callable contract is:

```python
discover_vendor_organization_readiness(
    *,
    db_path: "_Path",
    run_id: "str",
    captured_at: "str",
    tool_commit: "str",
) -> "dict[str, object]"
```

All four parameters are mandatory keyword-only. There are no positional
parameters, defaults, variadic arguments, dependency injection parameters, or
environment fallbacks.

`run_id` is an exact lowercase RFC 9562 UUID version 4 string.
`captured_at` is exact UTC-seconds form `YYYY-MM-DDTHH:MM:SSZ`, passes strict
Gregorian calendar parsing, and round-trips exactly without trimming or
normalization. `tool_commit` is exactly 40 lowercase hexadecimal characters.

The callable returns a complete or operationally incomplete canonical
envelope. It raises the fixed public exception for input rejection or internal
invariant failure.

The raw annotations are exactly the five quoted strings shown above. Runtime
`typing.get_type_hints()` must resolve them exactly as follows:

```text
db_path = pathlib.Path
run_id = str
captured_at = str
tool_commit = str
return = dict[str, object]
```

### 10.3 Public exception

The only public exception is:

```text
VendorOrganizationDiscoveryError
```

Its message is always:

```text
VENDOR-ID-003 vendor discovery failed
```

It has no public classification/detail attributes. It suppresses exception
context and cause. Its representation contains no path, SQL, source value,
identifier, or secret.

Private non-sensitive classifications may distinguish `input` from `internal`
solely for CLI exit mapping.

### 10.4 CLI

The only private CLI dispatcher has the exact signature:

```python
_main(argv: "_Sequence[str] | None" = None) -> "int"
```

Its raw annotations are exactly `"_Sequence[str] | None"` and `"int"`.
Runtime `typing.get_type_hints()` resolves them to
`typing.Sequence[str] | None` and `int`. When `argv is None`, `_main` uses
exactly `sys.argv[1:]`. A non-null `argv` is accepted only when
`type(argv) is list` or `type(argv) is tuple` and `type(item) is str` for every
item. A string, bytes object, mapping, set, generator, custom `Sequence`, list
or tuple subclass, or container containing any non-exact-string item is an
internal contract failure: `_main` returns `4`, writes zero stdout bytes and
the fixed internal marker, makes zero database connection attempts, and
reveals no value, type, `repr`, or exception.

`_main` is the sole CLI dispatcher. There is no second dispatcher, public CLI
function, plugin entry point, or console-script abstraction. Module execution
is limited to:

```python
if __name__ == "__main__":
    raise SystemExit(_main())
```

The executable surface is only:

```text
python -B tools/discover_vendor_organization_readiness.py
  --db-path <absolute-path>
  --run-id <uuidv4>
  --captured-at <utc-seconds>
  --tool-commit <40-lowercase-hex>
```

All four long options occur exactly once and require a value.
No short option, positional input, abbreviation, combined option, duplicate
option, unknown option, response file, config file, stdin input, environment
input, `--output`, `--format`, `--limit`, `--site`, `--sheet`, `--label`,
`--apply`, or `--production` mode is accepted.

The parser uses `prog="discover_vendor_organization_readiness.py"`,
`add_help=False`, and `allow_abbrev=False`. It explicitly registers only the
long help token `--help`; `-h` is never registered and is always rejected. The
four value metavars, in option-registration order, are exactly `DB_PATH`,
`RUN_ID`, `CAPTURED_AT`, and `TOOL_COMMIT`.

Help succeeds only when the argument vector is the single exact token
`--help`. That path returns `0`, writes the frozen help bytes below to stdout,
writes zero stderr bytes, and makes zero database connection attempts. These
all map to input rejection and exit `2`: `--help` with any other token,
duplicate `--help`, `--help=value`, `-h`, an abbreviated canonical option, a
duplicate canonical option, an unknown option, a positional token, a combined
option, a response-file token, or a missing mandatory option. Help does not
take precedence over an otherwise invalid vector.

The exact help byte payload is the UTF-8 strict encoding of the following
ASCII block, including its displayed spaces and line breaks and exactly one
terminal LF after the last line:

```text
usage: discover_vendor_organization_readiness.py --help
       discover_vendor_organization_readiness.py --db-path DB_PATH --run-id RUN_ID
       --captured-at CAPTURED_AT --tool-commit TOOL_COMMIT

Read aggregate-only VENDOR-ID-003 evidence from one disposable SQLite database.

options:
  --help                    show this exact help and exit
  --db-path DB_PATH         absolute disposable SQLite database path
  --run-id RUN_ID           lowercase RFC 9562 UUID version 4
  --captured-at CAPTURED_AT UTC seconds in YYYY-MM-DDTHH:MM:SSZ form
  --tool-commit TOOL_COMMIT 40 lowercase hexadecimal characters
```

The code fence is not part of the payload. There is no BOM or CR byte. Parser
rejection writes only the fixed input marker; raw parser diagnostics,
usage-on-error, value-bearing errors, and tracebacks are prohibited.

### 10.5 No export

The first implementation is transient output only. It exposes no:

- output path;
- artifact directory;
- report or evidence-bundle writer;
- download, export, upload, network, clipboard, or publication path;
- persistent cache;
- logging of source values; or
- environment-derived destination.

Shell redirection is outside the tool and is not authorized by this document.
A future persistent report requires a separate privacy/access/retention gate.

## 11. Errors, exits, stdout and stderr

### 11.1 CLI mapping

Every nonempty CLI payload is encoded with UTF-8 strict and emitted in exactly
one call to `sys.stdout.buffer.write` or `sys.stderr.buffer.write`. An exact
private binary wrapper is allowed only when its final sink remains the
applicable `.buffer.write` method and it preserves the payload byte-for-byte.
No payload has a BOM or CR byte; every nonempty payload has exactly one
terminal byte `0x0A`; and the CLI performs no second content write or explicit
flush.

`print`, `sys.stdout.write`, `sys.stderr.write`, text-mode newline translation,
locale encoding, console code-page encoding, and environment-derived encoding
are prohibited.

| Condition | Callable | Exit | stdout | stderr |
|---|---|---:|---|---|
| Complete capture | Return canonical dict | `0` | canonical JSON UTF-8 bytes + `b"\n"` | 0 bytes |
| Operational incomplete capture | Return canonical dict with `capture_status = "incomplete"` | `3` | canonical JSON UTF-8 bytes + `b"\n"` | 0 bytes |
| Input rejection | Raise fixed public exception | `2` | 0 bytes | `b"VENDOR-ID-003 DISCOVERY INPUT REJECTED\n"` |
| Internal invariant failure | Raise fixed public exception | `4` | 0 bytes | `b"VENDOR-ID-003 DISCOVERY INTERNAL FAILURE\n"` |
| Help | Callable not invoked | `0` | exact Section 10.4 help bytes | 0 bytes |

No traceback, parser diagnostic, error usage, value-bearing error, or other
byte is emitted by the CLI.

### 11.2 Private error codes

The closed private error vocabulary is:

```text
aggregation_invariant_failed
authorizer_install_failed
authorizer_reset_failed
begin_failed
canonical_json_failed
concurrent_source_change
connection_close_failed
connection_open_failed
evidence_hash_failed
header_invalid
input_not_regular_file
input_path_invalid
input_path_not_contained
internal_authorizer_invariant
internal_no_touch_violation
internal_runtime_invariant
metadata_query_failed
new_schema_projection_incomplete
platform_unsupported
result_contract_failed
rollback_failed
row_query_failed
schema_fingerprint_failed
schema_query_failed
sidecar_present
source_identity_changed
source_metadata_ambiguous
source_metadata_incompatible
source_object_identity_failed
source_projection_unavailable
topology_query_failed
topology_unsupported
```

Only codes relevant to an operational incomplete envelope appear in
`errors`. Pre-open input and internal codes are not emitted because those
paths have no JSON output.

### 11.3 Operational versus internal

An operational failure is a source/query/checkpoint condition that the
contract anticipates without evidence that the tool wrote or violated its own
invariants.

An internal failure includes:

- an unexpected authorizer callback accepted or attempted;
- source or sidecar mutation attributable to the tool;
- output that fails its own schema/hash checks;
- an unexpected public value;
- failure to roll back/reset safely; or
- a code path outside the frozen decision table.

### 11.4 Exception classes

Expected source-operational SQLite exceptions are
`sqlite3.OperationalError` and other `sqlite3.DatabaseError` values except
`sqlite3.ProgrammingError`, `sqlite3.InterfaceError`, and
`sqlite3.NotSupportedError`.

The three excluded SQLite classes, `RuntimeError`, `AssertionError`,
`MemoryError`, and every other unexpected `Exception` are internal programming
or invariant failures.

`OSError` is input rejection during pre-open path/stat/header/sidecar checks.
After a connection is returned, `OSError` during identity/hash/sidecar checks
is internal unless the exact concurrent-change case in Section 11.5 applies.

The CLI catches `KeyboardInterrupt` after parsing and maps it to internal exit
`4` after attempting the required cleanup. Sole-token help is consumed only by
the Section 10.4 pre-scan and never reaches the parser. Parser-owned
`SystemExit` therefore maps only an invalid token vector to input exit `2`; it
can never produce help exit `0`. A malformed parser namespace, an unexpected
parser exception, a parser-returned help state, or any parser invariant drift
is `internal_runtime_invariant`, emits the fixed internal bytes, and exits `4`.
No parser path leaks a traceback or diagnostic. No other `BaseException` is
converted into a trusted envelope.

### 11.5 Complete phase and failure decision table

Cleanup protocols are:

```text
C0 = no connection exists; no cleanup
C1 = install deny-all authorizer if possible, then close
C2 = ROLLBACK active transaction, install deny-all authorizer, then close
```

For `C1` and `C2`, every later cleanup step is attempted even when an earlier
step fails. Cleanup-code precedence is:

```text
rollback_failed
authorizer_reset_failed
connection_close_failed
original failure code
```

The first applicable code in that list becomes the final private code. Any
cleanup failure is internal, suppresses every envelope, and maps to exit `4`.

| Phase | Handled condition or exception | Private code / class | Envelope and earlier results | Required cleanup | CLI |
|---|---|---|---|---|---|
| Private `_main` argv container/item validation | Non-null object is not exact list/tuple, or any item is not exact string | `internal_runtime_invariant` / internal | No envelope; callable and parser not invoked | C0 | Exit `4`; zero stdout; fixed internal stderr; zero database attempts |
| CLI token pre-scan | Exact sole `--help` | Help / control path | No envelope; callable and parser validation not invoked | C0 | Exit `0`; exact frozen help bytes; zero stderr; zero database attempts |
| CLI token pre-scan/parser rejection | Mixed or duplicate help, `-h`, abbreviation, duplicate canonical option, unknown/positional/combined/response token, missing option, or any parser-owned `SystemExit` after pre-scan | Private non-sensitive `input` classification; no envelope error code | No envelope; callable not invoked | C0 | Exit `2`; zero stdout; fixed input stderr; zero database attempts |
| Parser result/invariant | Malformed namespace, unexpected parser exception, parser-returned help namespace/state, second non-`SystemExit` help path, or any parser invariant drift | `internal_runtime_invariant` / internal | No envelope; callable not invoked | C0 | Exit `4`; zero stdout; fixed internal stderr; zero database attempts |
| Public scalar input validation | Invalid UUID, calendar timestamp, commit, or callable argument type before path inspection | Private non-sensitive `input` classification; no envelope error code | No envelope | C0 | Exit `2`; zero stdout; fixed input stderr; zero database attempts |
| Platform/architecture/Python/SQLite/Unicode check | Expected value differs; sqlite module import unavailable | `platform_unsupported` / input | No envelope | C0 | Exit `2`; fixed input stderr |
| Platform check | Unexpected `Exception` or runtime object shape | `internal_runtime_invariant` / internal | No envelope | C0 | Exit `4`; fixed internal stderr |
| Raw `db_path` type, absolute-path syntax, ADS/trailing component validation | `TypeError`, `ValueError`, rejected lexical rule | `input_path_invalid` / input | No envelope | C0 | Exit `2` |
| Windows root/containment/reparse/hardlink/file-identity stat | Expected rejection or `OSError` | `input_path_not_contained`, `input_not_regular_file`, or `input_path_invalid` / input, using the first failed frozen check | No envelope | C0 | Exit `2` |
| Header length/magic/version raw read | Rejected bytes, short read, or `OSError` | `header_invalid` / input | No envelope | C0 | Exit `2` |
| Sidecar precheck | Any sidecar exists or stat is not safely absent | `sidecar_present` / input | No envelope | C0 | Exit `2` |
| `sqlite3.connect` | Expected source-operational SQLite exception | `connection_open_failed` / operational | Exact pre-topology incomplete projection in Section 9.2; topology is all-null, schema fields incomplete, fingerprint null, source-unavailable observed, other 13 categories indeterminate, summary `1 / 0 / 13` | C0 because no connection was returned; required post-attempt checkpoint still runs | Exit `3`; canonical JSON only after safe postcheck/hash/self-validation |
| `sqlite3.connect` | Programming/interface/not-supported or unexpected exception | `internal_runtime_invariant` / internal | No envelope | C0 | Exit `4` |
| Authorizer installation | Any SQLite error, `RuntimeError`, or callback-registration mismatch | `authorizer_install_failed` / internal | No envelope | C1 | Exit `4` |
| `BEGIN` | Expected source-operational SQLite exception and transaction remains inactive | `begin_failed` / operational | Exact pre-topology incomplete projection in Section 9.2; no fabricated topology or schema fact | C1 | Exit `3` only after safe close/postcheck/hash/self-validation |
| `BEGIN` | Transaction active state differs, authorizer evidence differs, or unexpected exception | `internal_authorizer_invariant` or `internal_runtime_invariant` / internal | No envelope | C2 if active, otherwise C1 | Exit `4` |
| Topology query | Expected source-operational SQLite exception | `topology_query_failed` / operational | Exact pre-topology incomplete projection in Section 9.2 | C2 | Exit `3` only after safe cleanup/postcheck/hash/self-validation |
| Topology tuple shape/type | Contract mismatch | `result_contract_failed` / operational | Exact pre-topology incomplete projection in Section 9.2 | C2 | Exit `3` only after safe cleanup/postcheck/hash/self-validation |
| Topology values | Attached/temp/path topology is unsupported | `topology_unsupported` / input | No envelope | C2 | Exit `2`, unless cleanup fails then `4` |
| Table-list, main-schema, or temp-schema query | Expected source-operational SQLite exception | `schema_query_failed` / operational | Proven non-null topology survives; schema availability, legacy sources, and new group are incomplete; fingerprint null; source-unavailable observed; other 13 categories indeterminate | C2 | Exit `3` |
| Schema tuple shape/type/order | Contract mismatch | `result_contract_failed` / operational | Proven non-null topology survives; schema availability, legacy sources, and new group are incomplete; fingerprint null; source-unavailable observed; other 13 categories indeterminate | C2 | Exit `3` |
| Source-object proof | Absent legacy object | `source_projection_unavailable` / operational | Proven non-null topology survives; Section 4.5 unavailable/incomplete schema values apply; no category except source-unavailable is conclusive | C2 | Exit `3` |
| Source-object proof | Wrong case/type/schema, virtual/shadow, duplicate/conflicting identity | `source_object_identity_failed` / operational | Incomplete envelope under Section 4.5 | C2 | Exit `3` |
| Any table-xinfo query | Expected source-operational SQLite exception | `metadata_query_failed` / operational | Proven non-null topology survives; schema availability, all six legacy sources, and new group are incomplete; fingerprint null; no earlier schema/category conclusion survives | C2 | Exit `3` |
| Table-xinfo tuple shape/type/order | Contract mismatch | `result_contract_failed` / operational | Proven non-null topology survives; schema availability, all six legacy sources, and new group are incomplete; fingerprint null; no earlier schema/category conclusion survives | C2 | Exit `3` |
| Table-xinfo semantic proof | Present with zero rows, missing/wrong required metadata | `source_metadata_incompatible` / operational | Incomplete envelope under Section 4.5 | C2 | Exit `3` |
| Table-xinfo semantic proof | Duplicate `cid` or column name | `source_metadata_ambiguous` / operational | Incomplete envelope under Section 4.5 | C2 | Exit `3` |
| New-schema group proof | All four absent | `source_projection_unavailable` / operational | Legacy conclusions survive; new dependencies unavailable | C2 after legacy queries | Exit `3` |
| New-schema group proof | Partial/conflicting/incompatible | `new_schema_projection_incomplete` / operational | Legacy conclusions survive; new dependencies unavailable | C2 after legacy queries | Exit `3` |
| Each legacy or new row query | Expected source-operational SQLite exception | `row_query_failed` / operational | Proven non-null topology and completed schema fingerprint survive; every earlier conclusive category is discarded | C2 | Exit `3` |
| Row tuple arity/order, non-label field domain, new-schema text vocabulary/UUID/integer, or duplicate primary identity | Contract mismatch | `result_contract_failed` / operational | Proven non-null topology and completed schema fingerprint survive; every earlier conclusive category is discarded | C2 | Exit `3` |
| Result grouping/category/evidence/summary aggregation | Any unexpected exception, impossible state, or formula mismatch | `aggregation_invariant_failed` / internal | No envelope | C2 | Exit `4` |
| Authorizer callback during any SQL phase | Denial, missing required callback, extra action/pair/function, or wrong phase | `internal_authorizer_invariant` / internal | No envelope, even if SQLite also reports an operational error | C2 | Exit `4` |
| `ROLLBACK` | Any SQLite error, active-state mismatch, or unexpected exception | `rollback_failed` / internal | No envelope | Continue reset and close | Exit `4` |
| Deny-all authorizer reset | Any registration error or verification mismatch | `authorizer_reset_failed` / internal | No envelope | Continue close | Exit `4` |
| Connection close | Any exception or retained usable connection | `connection_close_failed` / internal | No envelope | No further SQLite action | Exit `4` |
| Source postcheck | Same file identity and absent sidecars, but size/mtime/hash changed | `concurrent_source_change` / operational | Retain any earlier operational code, add this code, deduplicate, and ASCII-sort; if no earlier code this is the sole code. Proven topology survives, or the exact all-null pre-topology projection applies if proof never completed; source-unavailable observed and every other category indeterminate | Connection already safely closed | Exit `3` |
| Source postcheck | File missing, replaced, or Windows file identity differs | `source_identity_changed` / internal | No envelope | Connection already safely closed | Exit `4` |
| Source/sidecar postcheck | A sidecar appears, source becomes unreadable without identity proof, or any other no-touch property cannot be proven | `internal_no_touch_violation` / internal | No envelope | Connection already safely closed | Exit `4` |
| Schema projection/fingerprint | Canonical projection cannot be built/serialized/hashed or reconstructed | `schema_fingerprint_failed` / internal | No envelope | Connection already safely closed | Exit `4` |
| Canonical envelope construction | Key/type/nullability/order/count/canonical JSON failure | `canonical_json_failed` / internal | No envelope | Connection already safely closed | Exit `4` |
| Evidence-hash construction/reconstruction | Hash cannot be computed or exact reconstruction differs | `evidence_hash_failed` / internal | No envelope | Connection already safely closed | Exit `4` |
| Final self-validation | Envelope schema, 14-entry order, summary, errors, or privacy invariant differs | `internal_runtime_invariant` / internal | No envelope | Connection already safely closed | Exit `4` |

An operational envelope is constructed only after required cleanup,
connection close, source/sidecar postcheck, schema fingerprint, canonical JSON,
evidence hash, privacy scan, and final self-validation all succeed.

No `ROLLBACK`, authorizer reset, close, internal invariant, canonicalization,
fingerprint, hash, or no-touch failure may emit partial JSON or preserve a
success/incomplete marker.

Null or non-string values in a legacy label slot are deliberately excluded
from the `result_contract_failed` row. Their label values are classified only
by `legacy_vendor_label_blank_or_invalid` after exact tuple arity/order and
non-label fields have passed. The row may independently participate in a
Section 6 non-label predicate, such as an unresolved sheet/site conflict,
without that predicate consuming the opaque label payload.

## 12. Snapshot, concurrency and no-touch checkpoints

The exact private-argv check, sole-help recognition, parser token validation,
public scalar validation, and pre-open path/header/sidecar gates all precede
`sqlite3.connect`. Every help, parser rejection, public input rejection, and
invalid-private-argv path therefore performs exactly zero database connection
attempts. Help and parser rejection do not invoke the public callable; an
invalid private `argv` does not invoke either the parser or callable.

### 12.1 Checkpoints

Before connect and after close, the future tool captures:

- Windows file identity;
- exact file size;
- exact `mtime_ns`;
- uppercase SHA-256 of all source bytes;
- existence of the three exact sidecars; and
- the resolved absolute path.

The source path itself is never output.

Before and after values must match exactly for a complete capture.
Identity change is an input/internal safety failure depending on whether it
occurs before or during the connection. Size, mtime, or hash change while the
read transaction is active is `concurrent_source_change` and returns an
incomplete envelope after safe rollback/close.

Every operational exit-3 path performs the applicable post-attempt or
post-close checkpoint before envelope construction. If the same Windows file
identity and absent sidecars are proved but size, `mtime_ns`, or SHA-256
changed, the errors array retains the original operational code when one
exists, adds `concurrent_source_change`, deduplicates, and sorts by ASCII.
There is no replacement alternative. If no earlier operational code exists,
the array is exactly `["concurrent_source_change"]`.

For a pre-topology failure, that concurrent-change composition does not
authorize topology inference: all three topology fields remain null and the
exact Section 9.2 projection applies. For a post-topology failure, the three
proved non-null topology values remain in the envelope. A Windows file
identity change, any sidecar appearance, any cleanup failure, or inability to
prove the source/no-touch checkpoints is internal exit `4` with zero JSON.

### 12.2 Transaction

After connection and authorizer installation, the tool executes exactly one:

```text
BEGIN
```

It executes every fixed metadata and row query inside that read transaction.
The success and operational-failure path end with exactly:

```text
ROLLBACK
```

No `COMMIT`, savepoint, release, retry, reopen, or second transaction is
allowed.

If `BEGIN` does not establish a transaction, the run is internal failure.
If `ROLLBACK` fails, no output is returned and the run is internal failure.

### 12.3 Authorizer

The authorizer is phase-controlled and fail closed.

It may return `SQLITE_OK` only for:

- `SQLITE_SELECT` for the current fixed query;
- `SQLITE_READ` for the exact database/table/column triples selected by that
  query;
- `SQLITE_FUNCTION` only for `pragma_database_list`, `pragma_table_list`, and
  `pragma_table_xinfo` in their exact metadata phases; and
- `SQLITE_TRANSACTION` only for the one `BEGIN` and one `ROLLBACK`.

For the main schema query, the SQL source remains `main.sqlite_schema` while
the accepted callback table is the historical `sqlite_master` in database
`main`. For the temp schema query, the SQL source remains
`temp.sqlite_schema` while the callback table is `sqlite_temp_master` in
database `temp`.

Every other action is `SQLITE_DENY`, including:

- INSERT, UPDATE, DELETE;
- CREATE, ALTER, DROP, REINDEX, ANALYZE;
- PRAGMA action;
- ATTACH and DETACH;
- VACUUM;
- transaction COMMIT;
- arbitrary function/collation;
- reads of any non-frozen table or column; and
- reads in the wrong query phase.

The phase-specific READ matrix is:

| Query phase | Callback database | Callback table | Allowed columns |
|---|---|---|---|
| Database list | `main` | `pragma_database_list` | `seq`, `name`, `file` |
| Table list | `main` | `pragma_table_list` | `schema`, `name`, `type`, `ncol`, `wr`, `strict` |
| Main schema | `main` | `sqlite_master` | `type`, `name`, `tbl_name`, `sql` |
| Temp schema | `temp` | `sqlite_temp_master` | `type`, `name`, `tbl_name`, `sql` |
| Any one table-xinfo phase | `main` | `pragma_table_xinfo` | `cid`, `name`, `type`, `notnull`, `dflt_value`, `pk`, `hidden` |
| Sites | `main` | `sites` | `id` |
| Sheets | `main` | `sheets` | `id`, `site_id` |
| Tasks | `main` | `tasks` | `sheet_id`, `vendor` |
| Accounts | `main` | `vendor_accounts` | `id`, `vendor_name` |
| Contacts | `main` | `vendor_contacts` | `sheet_id`, `vendor_name` |
| Work entries | `main` | `vendor_work_entries` | `sheet_id`, `vendor_name` |
| Organizations | `main` | `vendor_organizations` | `vendor_id`, `display_name`, `organization_status` |
| Memberships | `main` | `vendor_organization_memberships` | `vendor_membership_id`, `vendor_id`, `vendor_account_id`, `membership_role`, `membership_status` |
| Assignments | `main` | `vendor_site_assignments` | `vendor_site_assignment_id`, `vendor_id`, `site_id`, `assignment_status` |
| Bindings | `main` | `sheet_vendor_bindings` | `sheet_vendor_binding_id`, `vendor_id`, `sheet_id`, `site_id`, `vendor_site_assignment_id`, `binding_status` |

Repeated callbacks for an allowed pair are permitted only within the same
phase because ordering expressions may read a selected column again.
An empty-string or null column callback is not a wildcard and is denied.

If the frozen SQLite runtime reports a different callback table, database,
column, function, or action for a canonical query, implementation stops for a
docs-only reconciliation. The checker or tool must not broaden the matrix to
make the query pass.

Each phase must observe at least one `SQLITE_SELECT` and every required
selected-column READ pair. Missing or additional callback evidence is an
internal authorizer invariant failure.

After rollback, the tool installs a deny-all authorizer before close. It
executes no further SQL.

### 12.4 Query-only behavior

The tool relies on `mode=ro`, the authorizer, a read transaction, and
before/after checkpoints. It does not execute or mutate `PRAGMA query_only`.
It does not infer safety from a connection flag alone.

### 12.5 Prohibited operations

The implementation contains no:

- DDL or DML;
- PRAGMA mutation;
- WAL checkpoint;
- VACUUM;
- attach/detach;
- sidecar cleanup;
- application bootstrap or project-module import;
- migration-helper invocation;
- backfill;
- commit; or
- network/backend attempt.

## 13. Artifact persistence, retention and download policy

### 13.1 First-slice policy

The first slice creates no persistent discovery artifact.

The only result is the return value or one canonical JSON line on stdout.
The tool writes zero files, directories, logs, caches, manifests, reports,
plans, temp outputs, downloads, or cleanup ledgers.

### 13.2 Retention

No retention period is defined because persistence is prohibited.
The tool does not promise secure deletion of caller redirection or terminal
history and therefore does not authorize either.

### 13.3 Transport and publication

The tool has no upload, HTTP, Render, email, Drive, clipboard, archive,
compression, transport bundle, QR code, or other export capability.

Publication, audience selection, access controls, suppression thresholds,
transport integrity, retention, cleanup, and audit ownership require a new
Product Owner-approved gate.

### 13.4 Report and plan boundary

Canonical stdout is discovery evidence, not:

- a report product;
- a published evidence bundle;
- an approved mapping;
- an executable plan;
- a backfill input;
- a repair instruction; or
- an authority token.

## 14. Static checker allowance and negative-source cases

### 14.1 Checker shape

Before discovery implementation, a separate static readiness guard must be
reviewed and frozen.

Its positive allowance is limited to:

- the exact canonical discovery module path;
- the exact two exports;
- the exact private `_Path`/`_Sequence` imports, absence of future-annotation
  double stringification, raw annotations, resolved type hints, public callable,
  sole `_main` dispatcher, and two-export surface;
- exact private-argv list/tuple/item validation and its internal exit-4,
  zero-connect behavior;
- exact `argv is None` ownership: `_main` reads the current `sys.argv[1:]` at
  entry, excluding `argv[0]`, with no empty/cached/alternate argument source;
- the exact non-default help parser, token precedence, `prog`, metavars, frozen
  help bytes, and parser-rejection behavior;
- exact UTF-8 strict binary-buffer output sinks, payload bytes, and one-LF/no-CR
  rules;
- all 24 fixed query constants in Section 5;
- exact ordinary-main-table identity proof from table-list, main/temp schema,
  and xinfo;
- the exact source columns;
- the exact UUID, status/role, display-name, integer, and duplicate-identity
  row domains;
- opaque legacy-label handling: exact strings alone enter normalization, while
  null/non-string values produce only the invalid-label label-classification
  result without coercion, grouping, leakage, or result-contract failure;
  independent non-label defects remain separately classifiable without label
  consumption;
- the exact platform/path/header/sidecar/topology gates;
- the exact authorizer and transaction state machine;
- every typed aggregation namespace, category count/evidence formula,
  disposition, dependency, and summary formula;
- the complete phase/exception/private-code/cleanup/exit decision table;
- the canonical output/hash contract;
- aggregate-only evidence and redaction rules; and
- zero artifact, network, environment, backend, mutation, and authority
  capability.

### 14.2 Prohibited checker mechanisms

The checker must not use:

- a whole-file or whole-function exemption;
- a generic scanner/discovery/schema/migration allowlist;
- a wildcard path;
- substring-only suppression;
- a caller-derived SQL allowance;
- generic `execute`/cursor/connection permission;
- dynamic table or column selection;
- ORM, Alembic, or PostgreSQL projection;
- route/API/UI/scheduled-job allowance;
- report/plan/backfill/apply capability;
- Production access;
- raw-data oracle allowance; or
- winner-selection allowance.

### 14.3 Required negative-source mutations

At minimum, self-test source mutations must cover:

- third export or public factory;
- optional/positional/variadic callable input;
- missing/wrong/double-quoted raw annotation, unresolved type hint, public
  `Path`/`Sequence` alias, exported private alias/dispatcher, second dispatcher,
  non-exact `_main` signature, or module execution other than the one frozen
  `raise SystemExit(_main())` guard;
- private `argv` accepting string/bytes/mapping/set/generator/custom Sequence,
  list/tuple subclass, or non-exact-string item, or mapping that rejection to
  input instead of internal exit `4`;
- `argv is None` replaced by an empty vector, full `sys.argv` including
  `argv[0]`, a cached vector, environment/config input, or any source other than
  the current `sys.argv[1:]` read at `_main` entry;
- parser-owned `SystemExit` accepted as help instead of normalized to input
  exit `2`, accepted `-h`, option abbreviation, mixed/duplicate or valued
  help, noncanonical `prog`/metavar/order/text/wrapping/spacing, raw parser
  diagnostic, or help/parser/input path that attempts a connection;
- parser-returned help namespace/state or a second non-`SystemExit` help route
  accepted instead of internal exit `4`;
- malformed parser namespace, unexpected parser exception, or parser invariant
  drift accepted as user input instead of internal exit `4`;
- `print`, text-stream write, locale/code-page/environment encoding, BOM, CRLF,
  missing/duplicate terminal LF, split output writes, explicit output flush, or
  noncanonical JSON/help/error bytes;
- public exception detail leakage;
- output path, file write, log, upload, or environment destination;
- dynamic SQL, f-string SQL, concatenated SQL, caller table/column, or
  wildcard projection;
- removal, construction, reordering, duplication, or count drift of any of the
  24 fixed SQL statements;
- direct `sqlite_master` SQL source;
- removal/broadening of table-list ordinary-main-table proof;
- wrong-case table accepted as exact, view/virtual/shadow accepted, same-name
  index/trigger accepted, duplicate identity accepted, or temp/attached object
  satisfying a source;
- absent object treated as present, present object with zero xinfo rows treated
  as absent, missing/wrong metadata accepted, duplicate `cid`/name accepted,
  or extra columns expanding read authority;
- unapproved table or column read;
- username, password hash, contact person field, site name, sheet name, or
  work payload read;
- removal or broadening of system-temp containment;
- symlink/reparse/hardlink acceptance;
- repository/canonical DB access;
- header gate removal or `2 / 2` acceptance;
- `immutable=1`, VFS, shared-cache, nolock, or query injection;
- sidecar cleanup or WAL checkpoint;
- ATTACH/DETACH, DDL, DML, PRAGMA mutation, VACUUM, or COMMIT;
- second connection, transaction, or retry;
- authorizer removal, broad READ, broad function, or wrong-phase allowance;
- raw label, normalized label, username, ID, path, SQL row, or mutation target
  in output/error/hash/log;
- legacy non-string label normalization, stringification, grouping, entry into
  another valid-label category, type/`repr`/value leakage, silent omission,
  deduplication, or classification as `result_contract_failed`;
- invalid UUID/status/role/display name/integer silently filtered or treated as
  ineligible; duplicate primary/relationship identity silently deduplicated;
- AUTH-ID UUID validator reused as vendor semantic authority;
- wrong `count_unit`, count cardinality, participant-set formula, namespace
  tag, evidence zero/null rule, disposition, or summary category formula;
- candidate/winner selection;
- organization, membership, assignment, or binding mutation;
- report, mapping plan, backfill, runtime fallback, or authority switch;
- route, API, template, UI, scheduled job, deployment hook, or app import;
- PostgreSQL/backend/environment/Render access;
- unknown anomaly marked observed;
- noncanonical anomaly order or count unit;
- hash recipe or canonical JSON weakening;
- incomplete capture retaining a partial conclusive anomaly;
- SQLite operational failure mapped as internal without the frozen reason, or
  RuntimeError/programming/authorizer invariant mapped as operational;
- rollback/reset/close/fingerprint/hash/no-touch failure emitting JSON;
- cleanup precedence, earlier-result survival, private code, exit, or
  stdout/stderr drift;
- null topology accepted in a complete capture;
- one or two null topology fields accepted instead of the frozen all-or-none
  rule;
- zero/false topology values fabricated before topology proof;
- proved topology values discarded after a later schema, metadata, or row
  operational failure;
- a pre-topology envelope whose schema availability, six legacy source
  availability values, or new-schema group is not uniformly `incomplete`;
- a pre-topology summary other than exactly observed `1`, not-observed `0`,
  and indeterminate `13`;
- a non-null pre-topology schema fingerprint;
- replacement, omission, non-ASCII ordering, or other drift in the frozen
  original-error plus `concurrent_source_change` composition;
- source checkpoint or sidecar post-check removal; and
- transient output converted into an artifact.

The checker must also test bounded forwarding, aliases, imports, inheritance,
starred arguments, recursion, and depth exhaustion so target evidence cannot
silently escape analysis.

No exact self-test scenario count is frozen before the checker exists.

### 14.4 Positive false-positive controls

Positive controls must show that the checker does not reject:

- ordinary unrelated business reads that do not reference the frozen sources;
- documentation containing prohibited examples;
- disposable fixture construction inside the exact test scope;
- canonical fixed SQL and its exact authorizer matrix;
- aggregate count arithmetic with no raw output;
- standard-library hashing/canonical JSON operations;
- fixed parser help behavior;
- exact private aliases/annotations and binary-buffer output behavior;
- opaque non-string label values counted only through aggregate invalid-label
  classification, while an independent non-label row defect remains separately
  testable without consuming that value; and
- explicit fixed unsupported-operation error text with no capability.

## 15. Disposable fixtures and acceptance matrix

### 15.1 Fixture boundary

Every fixture lives in a new, uniquely named directory strictly below the
Windows system-temp root.

Fixtures:

- are created by the test harness, not by the discovery tool;
- use rollback-journal header format;
- have no sidecars before invocation;
- are never reused between scenarios;
- contain no real credential, person, DEV, or Production data;
- are removed only by the harness after the tool is closed; and
- never use the repository database.

### 15.2 Acceptance matrix

| Scenario | Expected result |
|---|---|
| Exact required sources, all rows empty | Complete; all categories not observed; unknown count zero |
| Representative legacy-only data, all new tables absent | Legacy-only categories deterministic; new-schema categories indeterminate; source-unavailable observed |
| Exact new schema, empty, with clean legacy labels | Complete deterministic output |
| Exact null label | One invalid-label row occurrence observed; no normalization and no result-contract failure |
| Exact blank string | Invalid-label row occurrence observed after frozen normalization |
| Overlength or prohibited-Unicode exact string | Invalid-label row occurrence observed after frozen validity checks |
| Integer, float, bytes/blob, boolean, or injected custom-object label | Each occurrence observed once as invalid-label; duplicate rows each count; no result-contract failure |
| Non-string label alone with otherwise healthy references/scope | Excluded from every other label-based category, every valid-label population, and every `LG` |
| Non-string account label plus pending/active membership with existing references | Invalid-label observed; label invalidity alone does not produce membership mismatch |
| Non-string scoped-row label plus unresolved sheet/site | Invalid-label and independent cross-site row conflict may both be observed; no label normalization or `LG` occurs |
| Non-string sensitive canary value, type, and `repr` | None appears in stdout, stderr, exception, hash input, or captured logs |
| Two accounts with one normalized label | Ambiguous-account label group observed |
| One normalized label across two sites | Cross-scope reuse and cross-site conflict observed without raw label |
| One account label across incompatible sites | Conflicting operational scope observed |
| Legacy label with zero eligible organization candidates | Orphan legacy group observed |
| Eligible organization with zero legacy evidence | Organization-without-legacy-evidence observed |
| One legacy group with two eligible organizations | Ambiguous candidate and conflicting organization groups observed; no winner |
| Membership label mismatch or missing reference | Membership mismatch row count exact |
| Active assignment with missing/retired organization or invalid site | Assignment mismatch row count exact |
| Active binding whose sheet/site/assignment disagree | Binding and cross-site conflict counts exact |
| Simultaneous categories | Every row/group follows its own count unit; summary totals categories, not rows |
| Duplicate identical source rows | Row-count categories count rows; group-count categories remain one group |
| Missing legacy table/column | Exit 3 incomplete envelope; no business-row query executes |
| All four new tables absent | Legacy analysis bounded; new-schema-dependent categories indeterminate |
| Partial or wrong-column new schema | Incomplete result; no partial conclusive mapping category |
| Exact source ordinary `main` table | Table-list/schema/xinfo identity available |
| Source-named main view, virtual table, shadow table, index, trigger, or wrong-case alias | `source_object_identity_failed`; never satisfies required source |
| Any temp object or attached object | `topology_unsupported` input rejection; no envelope |
| Source object absent with zero xinfo rows | Explicit unavailable representation |
| Source object present with zero xinfo rows | Incompatible metadata, not absent |
| Missing/wrong required xinfo metadata | Incomplete with `source_metadata_incompatible` |
| Duplicate xinfo `cid` or column name | Incomplete with `source_metadata_ambiguous` |
| Extra source columns | Retained in fingerprint; frozen read projection unchanged |
| Extra unrelated main object | Ignored by discovery projection; no physical-schema PASS claim |
| Any temp object | Input rejection |
| Attached database | Input rejection |
| Fixed query operational failure | Exit 3 canonical incomplete envelope |
| Tuple arity/order or non-label type failure | Exit 3 canonical incomplete envelope |
| Connection-open operational failure before topology proof | Exit 3 exact all-null topology projection with sole error `connection_open_failed`; all schema fields incomplete; fingerprint null; source-unavailable observed; other 13 categories indeterminate; summary `1 / 0 / 13`; canonical reconstruction/hash passes |
| BEGIN operational failure before topology proof | Same exact pre-topology projection with sole error `begin_failed`; canonical reconstruction/hash passes |
| Topology-query operational failure | Same exact pre-topology projection with sole error `topology_query_failed`; canonical reconstruction/hash passes |
| Topology tuple/result-contract failure | Same exact pre-topology projection with sole error `result_contract_failed`; canonical reconstruction/hash passes |
| Schema-query operational failure after successful topology proof | Three proved non-null topology values survive; schema fields are incomplete; fingerprint null; exit 3 reconstruction/hash passes |
| Pre-topology operational failure plus same-identity concurrent content change | Original operational code retained, `concurrent_source_change` added, deduplicated and ASCII-sorted; exact pre-topology projection and reconstruction/hash pass |
| Complete envelope with any null topology field, partially null topology, fabricated zero/false pre-proof topology, discarded proved topology, wrong pre-topology schema fields/summary, or non-null pre-topology fingerprint | Final self-validation or checker fails closed |
| Cleanup, identity replacement, sidecar, or no-touch injection on any pre-topology path | Internal exit 4; zero stdout; no incomplete envelope |
| Invalid organization/membership/assignment/binding UUID | Exit 3 `result_contract_failed`; no row silently omitted |
| Invalid organization, membership, assignment, or binding vocabulary | Exit 3 `result_contract_failed`; no ineligible-set filtering |
| Null/blank/overlength/normalization-failing organization display name | Exit 3 `result_contract_failed` |
| Invalid/nonpositive/boolean integer identifier | Exit 3 `result_contract_failed` |
| Duplicate site/sheet/account/organization/relationship primary identity | Exit 3 `result_contract_failed` |
| Valid foreign identifier with missing target | Applicable relationship anomaly, not silent filtering |
| Every category formula with known participant sets | Exact `count_unit`, count, five evidence cardinalities, and disposition |
| Not-observed category with nonempty healthy population | Count and all five evidence fields zero |
| Indeterminate category after incomplete dependency | Count and all five evidence fields null |
| Mixed account/cross-site typed namespaces | No row/group/relationship/error token collision |
| Summary reconstruction | Three state counts count entries only and sum to 14 |
| Unexpected authorizer callback | Exit 4, no stdout |
| DDL/DML/PRAGMA/ATTACH/COMMIT injection | Authorizer denial and internal fail-closed test |
| Source modified concurrently | Exit 3 incomplete; before/after evidence differs; exact original-code retention/addition/ASCII-sort rule applies |
| Source/sidecar mutation attributable to tool | Exit 4; no success marker |
| Connection-open operational SQLite failure | Exact Section 9.2 all-null-topology exit-3 envelope after safe postcheck |
| Programming error or injected RuntimeError in every phase | Exit 4; no envelope |
| Operational SQLite error in topology/schema/xinfo/row query | Exact phase code and exit 3; proved topology and any completed schema projection survive exactly according to the phase-specific Section 11.5 row |
| `ROLLBACK`, deny-all reset, or close injection | Cleanup precedence exact; exit 4; zero stdout |
| Schema-fingerprint/canonical-JSON/evidence-hash injection | Exact internal code; exit 4; zero stdout |
| WAL `2 / 2`, mixed header, short file, bad magic | Exit 2; zero connection attempts and no sidecars |
| Space, Unicode, `#`, `?`, and `%` in filename | Correct `Path.as_uri` encoding; no query injection |
| Reparse, symlink, junction, hardlink, outside-temp path | Exit 2 before connection |
| Same fixture/input A/A | Byte-identical canonical JSON and evidence hash |
| Meaningfully changed fixture A/B | Deterministic changed envelope/hash |
| Evidence-hash reconstruction | Exact uppercase match after removing hash property |
| Public callable and `_main` raw annotations/signatures | Exact single-layer strings; `typing.get_type_hints()` resolves the Section 10 types; four mandatory keyword-only public inputs; one optional private `argv` |
| Public `Path`/`Sequence`, third export, second dispatcher, or future-annotation double stringification | Static checker and focused smoke fail closed |
| Private `argv` is string, bytes, mapping, set, generator, custom Sequence, subclass, or contains non-string | Internal exit 4, exact internal bytes, zero stdout and zero database attempts |
| `_main(argv=None)` with controlled process arguments | Consumes exactly the current `sys.argv[1:]`, excludes `argv[0]`, and uses no empty, cached, environment, config, or alternate source |
| Sole exact `--help` | Exit 0; exact frozen help bytes; zero stderr and zero database attempts |
| `-h`, help plus valid option, duplicate help, or `--help=value` | Exit 2 fixed input bytes; no help bytes, parser diagnostic, or database attempt |
| CLI duplicate canonical option, abbreviated option, positional, unknown, response-file, combined, or missing option | Exit 2 fixed input bytes; no database attempt |
| Parser-owned `SystemExit`, including status zero, after pre-scan | Input exit 2, fixed input bytes, no help bytes and zero database attempts |
| Parser-returned help namespace/state or second non-`SystemExit` help route | Internal exit 4; no second help route and zero database attempts |
| Malformed parser namespace or unexpected parser exception | Internal exit 4, exact internal bytes, zero stdout and zero database attempts |
| Invalid calendar, UUID, commit, path, or containment | Exit 2 fixed input bytes; zero database attempts |
| Complete/incomplete JSON, help, input error, and internal error binary capture | Exact UTF-8 payload; no BOM/CR; exactly one terminal LF; one applicable buffer write and no extra bytes |
| Text-stream/`print`, CRLF translation, parser diagnostic, usage-on-error, or value-bearing error injection | Static checker and focused smoke fail closed |
| Callable invalid input | Fixed public exception with no leaked context |
| Sensitive canary values in prohibited columns | Canary absent from stdout, stderr, exception, and captured logs |
| Raw label/ID canaries in allowed read columns | Canaries used only internally and absent from output/hash |
| PostgreSQL/backend/environment/network attempt counters | Exactly zero |
| Canonical repository DB and sidecars | Byte/size/mtime/existence unchanged and never opened |
| Temp-root/pycache/bytecode cleanup | Harness removes fresh roots; repository receives no cache or bytecode |

### 15.3 Regression validation

A future implementation gate must include:

- static checker normal and self-test;
- discovery focused smoke;
- callable and CLI annotation/signature inspection;
- deterministic/hashing reconstruction;
- all fixture matrix scenarios;
- existing vendor schema checker normal/self-test;
- manifest serializer self-test only when separately authorized;
- isolated full smoke only when separately authorized; and
- canonical database and sidecar before/after evidence.

This document executes none of those validations.

## 16. Production access and operator gate

### 16.1 No live access

This design and its future local disposable implementation do not authorize:

- DEV database access;
- Production database access;
- Render Shell, SSH, API, CLI, MCP, or one-off job use;
- persistent-disk inspection;
- snapshot download;
- live database copy;
- environment/DB-path discovery; or
- scheduled or runtime discovery.

### 16.2 Deployment is not execution evidence

Source deployment, build success, service health, `gunicorn` startup, HTTP
health, Shell availability, physical schema presence, or an attached disk does
not prove that discovery executed and does not grant permission to execute it.

### 16.3 Required independent live gate

Any future live discovery request requires an independent Product
Owner-approved operator/access/privacy gate that freezes:

- authorized human or service actor;
- exact service and environment;
- source snapshot and recovery evidence;
- database path acquisition and secret-handling boundary;
- whether the operation uses a disposable copy rather than the persistent
  source;
- output audience;
- aggregate suppression;
- retention;
- redaction;
- transport;
- review/approval;
- cleanup; and
- incident/abort behavior.

That gate must separately authorize each environment. DEV authority does not
imply Production authority.

### 16.4 No inferred authority

Permission must not be inferred from:

- Render deployment;
- branch or commit synchronization;
- Shell selector availability;
- database physical presence;
- an existing snapshot;
- service ownership;
- schema migration success; or
- a previous unrelated discovery gate.

## 17. Deferred backfill, consumer and authority owners

### 17.1 Controlled mapping and backfill

Any future controlled mapping/backfill owner must independently freeze:

- reviewed row-level mapping inputs;
- approval and separation of duties;
- ambiguity resolution;
- idempotency;
- write freeze;
- rollback and recovery;
- provenance;
- post-checks; and
- abort behavior.

Discovery output does not satisfy those requirements and is not directly
consumable as a plan.

### 17.2 Runtime consumers

No vendor route, login flow, session, trusted-target resolver, contact API,
work-entry API, report, scheduler, template, or service reads the new schema
under this design.

Runtime consumer inventory, compatibility, fallback, dual-read, rollback, and
authority switching require a separate owner and deployment gate.

### 17.3 Relationship and lifecycle mutation

Organization lifecycle, owner transfer, membership transition, site
assignment, and sheet binding remain governed by the conceptual owner and
future mutation slices.

An anomaly count cannot create a mutation precondition.

### 17.4 Credential and identity owners

The future tool does not:

- verify credentials;
- read password hashes or usernames;
- migrate sessions;
- associate a credential with an organization as an authority decision;
- generate a global identity;
- link/move/reconcile identity records;
- select an identity winner; or
- grant repair authority.

### 17.5 Production operator

The Production operator/access owner remains unset until an independent gate
names the actor and exact operation. This design creates no implied operator.

## 18. Frozen status and next-gate criteria

### 18.1 Frozen decisions

This document freezes:

- Windows-only disposable platform/input safety;
- the exact legacy/new-schema read projection;
- fixed literal query family and site-isolation semantics;
- discovery-only normalization;
- the closed ordered anomaly taxonomy and count units;
- aggregate-only privacy;
- deterministic canonical JSON and evidence hashing;
- opaque legacy-label classification, including non-string aggregate-only
  handling without coercion or result-contract failure;
- exact private aliases, raw/resolved callable annotations, sole `_main`
  dispatcher, and private-argv validation;
- sole-long-help token precedence and exact deterministic help bytes;
- exact UTF-8 binary-buffer callable, CLI, exception, exit, stdout, and stderr
  behavior;
- transient-output-only policy;
- read transaction, authorizer, checkpoints, and no-touch behavior;
- future narrow static-checker responsibilities;
- disposable acceptance requirements; and
- the independent Production access boundary.

### 18.2 Next-gate prerequisites

Implementation remains blocked until a final diff review confirms that this
document:

- preserves both governing baselines;
- leaves no predicate, count, privacy, path, platform, error, or authority
  decision to the implementer;
- contains no live access authority;
- does not create a report or mapping plan; and
- can be protected by a narrow static checker.

After final diff approval, the next independently authorized slice should be a
docs-aligned static readiness checker gate before discovery implementation.

### 18.3 Final status

This subsection records the pre-deployment design-freeze status. Section 19.5
supersedes it for Production deployment-evidence status without changing any
discovery implementation or authority boundary.

```text
VENDOR-ID-003 DOCS-ONLY READ-ONLY VENDOR DISCOVERY DESIGN BASELINE COMPLETE
DISCOVERY CONTRACT：FROZEN
DISCOVERY IMPLEMENTATION：NOT STARTED
REPORT / ARTIFACT：NOT IMPLEMENTED OR AUTHORIZED
MAPPING / BACKFILL：NOT IMPLEMENTED OR AUTHORIZED
RUNTIME CONSUMER / AUTHORITY SWITCH：NOT IMPLEMENTED OR AUTHORIZED
DEV / PRODUCTION DATABASE ACCESS：NOT AUTHORIZED
VENDOR-ID-003 OVERALL：OPEN — NOT CLOSED
READY FOR FINAL DIFF REVIEW
```

## 19. Production baseline freeze evidence

### 19.1 Production target and deployment identity

The Production baseline evidence recorded on 2026-07-21 is:

- service: `handover-system`;
- commit: `12b8458a68ce0e194820c5b4573d3d6eb876baad`;
- commit message: `Reconcile vendor discovery CLI and legacy label contract`;
- deploy: `dep-d9fg4ad7vvec73e98bog`;
- trigger: `new_commit`;
- final status: `Live`; and
- latest effective deploy: yes, with no newer deploy superseding it.

### 19.2 Build and bootstrap evidence

The complete target build and startup log window was obtained with
`hasMore=false`. It showed:

- checkout of exact commit
  `12b8458a68ce0e194820c5b4573d3d6eb876baad` on `main`;
- `Build successful`;
- `Running 'gunicorn app:app'`;
- Gunicorn 23.0.0 starting and listening at `0.0.0.0:10000`;
- worker boot;
- healthcheck `HEAD /` returning `302`; and
- `Your service is live`.

The same complete window contained no Traceback, unhandled exception, `ERROR`,
schema or migration failure, worker crash, restart loop, port-binding failure,
missing required configuration, OOM, build failure, or deploy failure. One old
instance received `TERM`, its worker exited, and its master shut down before the
new instance became healthy. That single sequence is a graceful deployment
replacement, not a crash or restart loop.

### 19.3 Public runtime evidence and dashboard contract adjudication

The following requests were directly observed without cookies or credentials
and without following redirects:

| Request | Direct result |
|---|---|
| `GET /` | `302`, `Location: /login` |
| `GET /login` | `200` |
| `GET /sheet` | `302`, `Location: /login` |
| Bare `GET /api/dashboard` | `400`, missing required `sheet_id` / `invalid_sheet_id` request-validation contract |

The bare dashboard result is not an authentication response. The route parses
and validates `sheet_id` before opening a database connection, resolving an
actor or current site, or invoking authorization. A missing or invalid
`sheet_id` therefore returns the established `400 invalid_sheet_id` contract.

For a valid-input unauthenticated request,
`GET /api/dashboard?sheet_id=<valid>`, the route proceeds to authorization and
returns `403 auth_required`. That result is established by frozen tests, the
existing Production baseline, and runtime source that is unchanged between the
target and its parent. It was not re-executed during this Production gate and is
not recorded as a direct observation here.

The earlier checklist expectation that bare `GET /api/dashboard` return `403`
omitted the required `sheet_id` and was incorrect. Re-adjudication therefore
records:

- application regression: no evidence;
- authentication-order defect: not confirmed;
- fix implementation: not required;
- Production deployment verification: PASS after re-adjudication; and
- public read-only runtime check: PASS after re-adjudication.

### 19.4 Repository integrity and frozen boundary

The deployed target is a single-parent, non-merge commit whose direct parent is
`28cec03db2b1f488064b4022522f52cae01c34cf`. Its original committed scope was
only this VENDOR-ID-003 document, with 311 insertions and 43 deletions. The
committed document evidence was:

- Git blob: `c195116e1ebc9d189d0e706aef41438ece9aa623`; and
- raw SHA-256:
  `8E839C2DB53616786285A4C6CB09797DAECF8DC818D5B345AE19595F93A9F51E`.

This Production freeze records only the docs-only discovery CLI and
legacy-label contract and its deployment evidence. It preserves these strict
boundaries:

- Windows-only discovery tool: NOT EXECUTED;
- canonical discovery implementation: NOT STARTED;
- mapping, report, artifact, backfill, runtime consumer, and authority: not
  created or authorized;
- database, persistent disk, snapshot, secret, and environment value: not
  accessed; and
- runtime, schema, permission, and workflow behavior: unchanged.

Production-frozen source and deployment evidence do not mean that discovery
implementation or execution is complete. Any implementation requires a new,
independently authorized implementation slice and gate.

### 19.5 Production-frozen status

```text
VENDOR-ID-003 DOCS-ONLY DISCOVERY CLI / LEGACY-LABEL CONTRACT：PRODUCTION-FROZEN
PRODUCTION LIVE COMMIT：12b8458a68ce0e194820c5b4573d3d6eb876baad
PRODUCTION DEPLOY：dep-d9fg4ad7vvec73e98bog
PRODUCTION DEPLOYMENT VERIFICATION：PASS
APP BOOTSTRAP HEALTH：PASS
PUBLIC READ-ONLY RUNTIME CHECK：PASS AFTER RE-ADJUDICATION
BARE DASHBOARD CONTRACT：400 invalid_sheet_id
VALID-INPUT UNAUTHENTICATED CONTRACT：403 auth_required — FROZEN EVIDENCE, NOT RE-EXECUTED
APPLICATION REGRESSION：NO EVIDENCE
DISCOVERY IMPLEMENTATION：NOT STARTED
WINDOWS-ONLY DISCOVERY TOOL：NOT EXECUTED
REPORT / ARTIFACT / MAPPING / BACKFILL：NOT IMPLEMENTED OR AUTHORIZED
RUNTIME CONSUMER / AUTHORITY SWITCH：NOT IMPLEMENTED OR AUTHORIZED
RUNTIME / SCHEMA / PERMISSION / WORKFLOW：UNCHANGED
NO DATABASE OR ENVIRONMENT ACCESSED
VENDOR-ID-003 OVERALL：OPEN — NOT CLOSED
```
