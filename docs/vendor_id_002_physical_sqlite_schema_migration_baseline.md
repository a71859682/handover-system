# VENDOR-ID-002 — Physical SQLite DDL and Migration

Status: design baseline
Scope: docs-only
Implementation status: not started

## 1. Purpose and governing boundary

This document freezes the exact SQLite projection and migration contract for the vendor-organization model approved by VENDOR-ID-001.

It defines:

- exactly four new SQLite tables;
- the exact opaque-ID lexical checks;
- exact column order, type, nullability, defaults, checks, keys, and foreign-key metadata;
- exact index names, columns, uniqueness, and partial predicates;
- the historical episode model for memberships, assignments, and bindings;
- schema-state classification;
- caller-owned transaction and helper-owned savepoint behavior;
- future checker, manifest, bootstrap, migration, and disposable-test ownership; and
- the boundary that prevents schema presence from becoming row creation, migration, runtime authority, or reconciliation mutation.

This document authorizes no implementation.

It does not authorize:

- creating any vendor organization, membership, assignment, or binding row;
- scanning or changing an existing database;
- modifying a legacy vendor table;
- generating an ID;
- backfill, reconciliation, merge, repair, or authority switching;
- a runtime reader or writer;
- an API, session, template, UI, import, or export change;
- a global `PRAGMA foreign_keys` change;
- PostgreSQL DDL or parity claims; or
- an audit/event subsystem.

The VENDOR-ID-001 conceptual contract remains upstream and controlling. If this document and VENDOR-ID-001 appear to conflict, implementation stops for a new review; it does not choose an interpretation.

## 2. Upstream VENDOR-ID-001 invariants

The following VENDOR-ID-001 invariants remain frozen:

- a vendor organization is distinct from a vendor account, backend principal, username, display name, global identity, site, sheet, task label, and session;
- `vendor_id` is stable, opaque, non-semantic, and never proof of authentication or authority;
- `vendor_accounts.id` remains a backend-local credential-principal ID;
- vendor membership is an explicit account-to-organization relationship;
- the only membership roles are `owner` and `member`;
- the only membership states are `pending`, `active`, and `revoked`;
- one vendor account has at most one active organization membership;
- one account/organization pair has at most one pending-or-active relationship;
- a revoked membership remains historical and is never reactivated in place;
- assignment and binding relationships preserve inactive history;
- one organization/site pair has at most one active assignment;
- one organization/sheet pair has at most one active binding;
- an active binding must resolve through an active same-organization, same-site assignment before use;
- display-name equality or normalization is not identity evidence;
- relationship presence is not authorization;
- current `vendor_name` behavior remains the runtime authority until a separately approved authority-switch slice;
- no hard deletion of referenced vendor history is authorized; and
- no schema slice may perform discovery, backfill, repair, merge, or authority switching.

The physical schema can represent some of these invariants, but representation is not implementation of a lifecycle or authority consumer.

## 3. SQLite platform and enforcement boundary

VENDOR-ID-002 is SQLite-only.

The future implementation must use SQLite features already implied by this repository's `STRICT` tables. The minimum SQLite capability is:

- `STRICT` table support;
- partial indexes;
- table and index introspection through SQLite metadata; and
- savepoints.

No PostgreSQL connection, ORM model, Alembic migration, or PostgreSQL DDL is part of this contract.

All four tables are `STRICT`.

`STRICT` affinity does not replace the explicit lexical and positive-integer checks frozen below.

SQLite applies column affinity before a row CHECK observes `typeof(...)`.

Therefore:

- `typeof(site_id) = 'integer'` and equivalent checks observe the post-affinity stored value;
- a value such as text `"1"` can be losslessly coerced by a `STRICT` `INTEGER` column and then satisfy the physical CHECK;
- the DDL cannot distinguish an originally bound integer `1` from every representation that SQLite losslessly converts to stored integer `1`; and
- this document does not claim impossible pre-affinity type rejection by DDL.

The frozen physical boundary is:

```text
After SQLite affinity conversion, vendor_account_id, site_id, and sheet_id
must have storage class INTEGER and value greater than zero.
```

Losslessly coercible input is physically accepted when SQLite stores it as a positive integer.

Every future runtime consumer must validate before SQL binding that an externally derived parent ID has the exact application-level integer type and is positive. In Python, `type(value) is int` is required; `bool`, `str`, `float`, `Decimal`, and caller-defined numeric objects are rejected before SQL even when SQLite could coerce them.

This runtime type boundary is not implemented or authorized by the DDL slice.

VENDOR-ID-002 implementation acceptance must not add a synthetic runtime validator or claim that the future `type(value) is int` rule has been executed or proven. It proves only post-affinity stored `INTEGER`, value greater than zero, documented lossless coercion, and absence of a runtime consumer.

Foreign-key declarations are required metadata, but current normal application connections do not globally execute:

```sql
PRAGMA foreign_keys = ON;
```

VENDOR-ID-002 must not change that application behavior.

Consequences:

- exact foreign-key metadata is required;
- disposable tests with foreign-key enforcement explicitly enabled are required later;
- Production enforcement must not be inferred from declarations alone;
- every future writer must revalidate parents and cross-row relationships inside its authorized transaction;
- deletion and key mutation remain forbidden by runtime contract even when a connection has foreign-key enforcement disabled; and
- no global or connection-factory PRAGMA change is authorized.

The canonical DDL contains no:

- trigger;
- view;
- generated column;
- virtual table;
- hidden normalization;
- `WITHOUT ROWID`;
- `AUTOINCREMENT`;
- `CREATE ... IF NOT EXISTS`;
- automatic ID generation; or
- automatic update timestamp behavior.

`CURRENT_TIMESTAMP` is only an insert-time default on the two timestamp columns of each row. It does not update `updated_at` automatically and does not authorize any update.

## 4. Exact opaque ID lexical contract

The following are four independent ID domains:

```text
vendor_id
vendor_membership_id
vendor_site_assignment_id
sheet_vendor_binding_id
```

Every value is an RFC 9562 UUID version 4 in canonical lowercase text form:

```text
xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
```

where every `x` is one lowercase ASCII hexadecimal character and `y` is one of `8`, `9`, `a`, or `b`.

The frozen lexical properties are:

- SQLite storage class is `text`;
- exact length is 36 characters;
- hyphens occur only at positions 9, 14, 19, and 24, using one-based positions;
- the version nibble at position 15 is `4`;
- the variant nibble at position 20 is `8`, `9`, `a`, or `b`;
- all other non-hyphen positions are lowercase ASCII hexadecimal;
- no leading or trailing content is allowed;
- no prefix, suffix, braces, URN, compact form, uppercase form, or non-hexadecimal character is accepted;
- a nil UUID is rejected;
- a numeric or otherwise coerced noncanonical value is rejected;
- no business, account, site, sheet, role, status, authority, or lifecycle meaning is encoded; and
- caller-selected values are not authority.

The exact deterministic SQLite expression for `vendor_id` is:

```sql
CHECK (
    typeof(vendor_id) = 'text'
    AND length(vendor_id) = 36
    AND vendor_id GLOB
        '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
    AND vendor_id <> '00000000-0000-0000-0000-000000000000'
)
```

The exact expression for `vendor_membership_id` is:

```sql
CHECK (
    typeof(vendor_membership_id) = 'text'
    AND length(vendor_membership_id) = 36
    AND vendor_membership_id GLOB
        '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
    AND vendor_membership_id <> '00000000-0000-0000-0000-000000000000'
)
```

The exact expression for `vendor_site_assignment_id` is:

```sql
CHECK (
    typeof(vendor_site_assignment_id) = 'text'
    AND length(vendor_site_assignment_id) = 36
    AND vendor_site_assignment_id GLOB
        '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
    AND vendor_site_assignment_id <> '00000000-0000-0000-0000-000000000000'
)
```

The exact expression for `sheet_vendor_binding_id` is:

```sql
CHECK (
    typeof(sheet_vendor_binding_id) = 'text'
    AND length(sheet_vendor_binding_id) = 36
    AND sheet_vendor_binding_id GLOB
        '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
    AND sheet_vendor_binding_id <> '00000000-0000-0000-0000-000000000000'
)
```

Nullable predecessor IDs use the same domain check under an `IS NULL OR (...)` guard.

`REGEXP` is not used.

The lexical shape may match an AUTH-ID UUIDv4 shape, but vendor IDs have separate semantic ownership.

The future implementation must not use `services.identity_registry_ids` as the vendor-domain generator or validator API.

DDL creates no IDs and no rows. A future creation or controlled-backfill consumer must use a separately reviewed vendor-specific generator and validator. This document does not pre-authorize that module, public API, caller, or mutation.

## 5. Exact table inventory and creation order

The exact new table inventory is:

```text
vendor_organizations
vendor_organization_memberships
vendor_site_assignments
sheet_vendor_bindings
```

No fifth vendor table, mapping table, alias table, event table, normalized-name table, compatibility view, or trigger is authorized.

The exact creation order is:

```text
1. vendor_organizations
2. vendor_organization_memberships
3. vendor_site_assignments
4. sheet_vendor_bindings
5. indexes in the order frozen by Section 10
```

The future source constant is exactly:

```text
VENDOR_ORGANIZATION_SCHEMA_STATEMENTS
```

It is an immutable ordered tuple containing the four complete `CREATE TABLE` statements followed by the complete index statements.

No statement uses runtime identifier construction, caller input, `executescript()`, or `IF NOT EXISTS`.

## 6. `vendor_organizations` exact projection

The exact column order is:

```text
1. vendor_id
2. display_name
3. organization_status
4. created_at
5. updated_at
6. created_actor_kind
7. created_actor_id
8. created_reason
9. created_source
10. created_correlation_id
11. updated_actor_kind
12. updated_actor_id
13. updated_reason
14. updated_source
15. updated_correlation_id
```

The exact canonical statement is:

```sql
CREATE TABLE vendor_organizations (
    vendor_id TEXT NOT NULL PRIMARY KEY,
    display_name TEXT NOT NULL,
    organization_status TEXT NOT NULL DEFAULT 'disabled',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_actor_kind TEXT NOT NULL,
    created_actor_id TEXT NOT NULL,
    created_reason TEXT NOT NULL,
    created_source TEXT NOT NULL,
    created_correlation_id TEXT NOT NULL,
    updated_actor_kind TEXT NOT NULL,
    updated_actor_id TEXT NOT NULL,
    updated_reason TEXT NOT NULL,
    updated_source TEXT NOT NULL,
    updated_correlation_id TEXT NOT NULL,
    CHECK (
        typeof(vendor_id) = 'text'
        AND length(vendor_id) = 36
        AND vendor_id GLOB
            '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
        AND vendor_id <> '00000000-0000-0000-0000-000000000000'
    ),
    CHECK (
        length(display_name) BETWEEN 1 AND 100
        AND length(
            trim(
                display_name,
                CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT)
            )
        ) > 0
    ),
    CHECK (organization_status IN ('active', 'disabled', 'retired')),
    CHECK (created_actor_kind IN ('system', 'internal_user', 'vendor_account', 'migration')),
    CHECK (updated_actor_kind IN ('system', 'internal_user', 'vendor_account', 'migration')),
    CHECK (length(created_actor_id) BETWEEN 1 AND 128 AND length(trim(created_actor_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_actor_id) BETWEEN 1 AND 128 AND length(trim(updated_actor_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(created_reason) BETWEEN 1 AND 500 AND length(trim(created_reason, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_reason) BETWEEN 1 AND 500 AND length(trim(updated_reason, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(created_source) BETWEEN 1 AND 100 AND length(trim(created_source, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_source) BETWEEN 1 AND 100 AND length(trim(updated_source, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(created_correlation_id) BETWEEN 1 AND 128 AND length(trim(created_correlation_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_correlation_id) BETWEEN 1 AND 128 AND length(trim(updated_correlation_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0)
) STRICT;
```

`display_name` is:

- a mutable human-facing label;
- between 1 and 100 SQLite characters;
- required to contain at least one character outside the exact Python-compatible whitespace set enumerated in the DDL;
- not unique;
- not normalized by this schema;
- not an identity, match, merge, grouping, or authority key.

The status default is deliberately fail-closed: omission produces `disabled`, not `active`.

The DDL represents the closed values `active`, `disabled`, and `retired`; it does not implement allowed transitions.

## 7. `vendor_organization_memberships` exact projection

The exact column order is:

```text
1. vendor_membership_id
2. vendor_id
3. vendor_account_id
4. membership_role
5. membership_status
6. predecessor_membership_id
7. created_at
8. updated_at
9. created_actor_kind
10. created_actor_id
11. created_reason
12. created_source
13. created_correlation_id
14. updated_actor_kind
15. updated_actor_id
16. updated_reason
17. updated_source
18. updated_correlation_id
```

The exact canonical statement is:

```sql
CREATE TABLE vendor_organization_memberships (
    vendor_membership_id TEXT NOT NULL PRIMARY KEY,
    vendor_id TEXT NOT NULL,
    vendor_account_id INTEGER NOT NULL,
    membership_role TEXT NOT NULL DEFAULT 'member',
    membership_status TEXT NOT NULL DEFAULT 'pending',
    predecessor_membership_id TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_actor_kind TEXT NOT NULL,
    created_actor_id TEXT NOT NULL,
    created_reason TEXT NOT NULL,
    created_source TEXT NOT NULL,
    created_correlation_id TEXT NOT NULL,
    updated_actor_kind TEXT NOT NULL,
    updated_actor_id TEXT NOT NULL,
    updated_reason TEXT NOT NULL,
    updated_source TEXT NOT NULL,
    updated_correlation_id TEXT NOT NULL,
    FOREIGN KEY (vendor_id)
        REFERENCES vendor_organizations(vendor_id)
        ON DELETE RESTRICT
        ON UPDATE NO ACTION,
    FOREIGN KEY (vendor_account_id)
        REFERENCES vendor_accounts(id)
        ON DELETE RESTRICT
        ON UPDATE NO ACTION,
    FOREIGN KEY (predecessor_membership_id)
        REFERENCES vendor_organization_memberships(vendor_membership_id)
        ON DELETE RESTRICT
        ON UPDATE NO ACTION,
    CHECK (
        typeof(vendor_membership_id) = 'text'
        AND length(vendor_membership_id) = 36
        AND vendor_membership_id GLOB
            '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
        AND vendor_membership_id <> '00000000-0000-0000-0000-000000000000'
    ),
    CHECK (
        typeof(vendor_id) = 'text'
        AND length(vendor_id) = 36
        AND vendor_id GLOB
            '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
        AND vendor_id <> '00000000-0000-0000-0000-000000000000'
    ),
    CHECK (
        predecessor_membership_id IS NULL
        OR (
            typeof(predecessor_membership_id) = 'text'
            AND length(predecessor_membership_id) = 36
            AND predecessor_membership_id GLOB
                '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
            AND predecessor_membership_id <> '00000000-0000-0000-0000-000000000000'
            AND predecessor_membership_id <> vendor_membership_id
        )
    ),
    CHECK (typeof(vendor_account_id) = 'integer' AND vendor_account_id > 0),
    CHECK (membership_role IN ('owner', 'member')),
    CHECK (membership_status IN ('pending', 'active', 'revoked')),
    CHECK (created_actor_kind IN ('system', 'internal_user', 'vendor_account', 'migration')),
    CHECK (updated_actor_kind IN ('system', 'internal_user', 'vendor_account', 'migration')),
    CHECK (length(created_actor_id) BETWEEN 1 AND 128 AND length(trim(created_actor_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_actor_id) BETWEEN 1 AND 128 AND length(trim(updated_actor_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(created_reason) BETWEEN 1 AND 500 AND length(trim(created_reason, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_reason) BETWEEN 1 AND 500 AND length(trim(updated_reason, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(created_source) BETWEEN 1 AND 100 AND length(trim(created_source, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_source) BETWEEN 1 AND 100 AND length(trim(updated_source, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(created_correlation_id) BETWEEN 1 AND 128 AND length(trim(created_correlation_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_correlation_id) BETWEEN 1 AND 128 AND length(trim(updated_correlation_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0)
) STRICT;
```

The default role is `member`; omission never creates an owner.

The default status is `pending`; omission never creates an active membership.

The predecessor is nullable for the first episode. A non-null predecessor:

- points to one earlier membership episode;
- cannot equal the current row ID;
- is constrained by a unique index to at most one direct successor;
- records lineage only;
- does not prove same account, same organization, compatible role, compatible status, or an authorized transition.

Those cross-row conditions remain runtime-owned.

## 8. `vendor_site_assignments` exact projection

The exact column order is:

```text
1. vendor_site_assignment_id
2. vendor_id
3. site_id
4. assignment_status
5. predecessor_assignment_id
6. created_at
7. updated_at
8. created_actor_kind
9. created_actor_id
10. created_reason
11. created_source
12. created_correlation_id
13. updated_actor_kind
14. updated_actor_id
15. updated_reason
16. updated_source
17. updated_correlation_id
```

The exact canonical statement is:

```sql
CREATE TABLE vendor_site_assignments (
    vendor_site_assignment_id TEXT NOT NULL PRIMARY KEY,
    vendor_id TEXT NOT NULL,
    site_id INTEGER NOT NULL,
    assignment_status TEXT NOT NULL DEFAULT 'inactive',
    predecessor_assignment_id TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_actor_kind TEXT NOT NULL,
    created_actor_id TEXT NOT NULL,
    created_reason TEXT NOT NULL,
    created_source TEXT NOT NULL,
    created_correlation_id TEXT NOT NULL,
    updated_actor_kind TEXT NOT NULL,
    updated_actor_id TEXT NOT NULL,
    updated_reason TEXT NOT NULL,
    updated_source TEXT NOT NULL,
    updated_correlation_id TEXT NOT NULL,
    FOREIGN KEY (vendor_id)
        REFERENCES vendor_organizations(vendor_id)
        ON DELETE RESTRICT
        ON UPDATE NO ACTION,
    FOREIGN KEY (site_id)
        REFERENCES sites(id)
        ON DELETE RESTRICT
        ON UPDATE NO ACTION,
    FOREIGN KEY (predecessor_assignment_id)
        REFERENCES vendor_site_assignments(vendor_site_assignment_id)
        ON DELETE RESTRICT
        ON UPDATE NO ACTION,
    CHECK (
        typeof(vendor_site_assignment_id) = 'text'
        AND length(vendor_site_assignment_id) = 36
        AND vendor_site_assignment_id GLOB
            '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
        AND vendor_site_assignment_id <> '00000000-0000-0000-0000-000000000000'
    ),
    CHECK (
        typeof(vendor_id) = 'text'
        AND length(vendor_id) = 36
        AND vendor_id GLOB
            '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
        AND vendor_id <> '00000000-0000-0000-0000-000000000000'
    ),
    CHECK (
        predecessor_assignment_id IS NULL
        OR (
            typeof(predecessor_assignment_id) = 'text'
            AND length(predecessor_assignment_id) = 36
            AND predecessor_assignment_id GLOB
                '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
            AND predecessor_assignment_id <> '00000000-0000-0000-0000-000000000000'
            AND predecessor_assignment_id <> vendor_site_assignment_id
        )
    ),
    CHECK (typeof(site_id) = 'integer' AND site_id > 0),
    CHECK (assignment_status IN ('active', 'inactive')),
    CHECK (created_actor_kind IN ('system', 'internal_user', 'vendor_account', 'migration')),
    CHECK (updated_actor_kind IN ('system', 'internal_user', 'vendor_account', 'migration')),
    CHECK (length(created_actor_id) BETWEEN 1 AND 128 AND length(trim(created_actor_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_actor_id) BETWEEN 1 AND 128 AND length(trim(updated_actor_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(created_reason) BETWEEN 1 AND 500 AND length(trim(created_reason, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_reason) BETWEEN 1 AND 500 AND length(trim(updated_reason, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(created_source) BETWEEN 1 AND 100 AND length(trim(created_source, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_source) BETWEEN 1 AND 100 AND length(trim(updated_source, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(created_correlation_id) BETWEEN 1 AND 128 AND length(trim(created_correlation_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_correlation_id) BETWEEN 1 AND 128 AND length(trim(updated_correlation_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0)
) STRICT;
```

The default status is `inactive`; omission never creates a current relationship.

An authorized future initial-relationship mutation must explicitly request `active`.

The predecessor lineage has the same linear, one-direct-successor rule as membership lineage.

## 9. `sheet_vendor_bindings` exact projection

The exact column order is:

```text
1. sheet_vendor_binding_id
2. vendor_id
3. sheet_id
4. site_id
5. vendor_site_assignment_id
6. binding_status
7. predecessor_binding_id
8. created_at
9. updated_at
10. created_actor_kind
11. created_actor_id
12. created_reason
13. created_source
14. created_correlation_id
15. updated_actor_kind
16. updated_actor_id
17. updated_reason
18. updated_source
19. updated_correlation_id
```

The exact canonical statement is:

```sql
CREATE TABLE sheet_vendor_bindings (
    sheet_vendor_binding_id TEXT NOT NULL PRIMARY KEY,
    vendor_id TEXT NOT NULL,
    sheet_id INTEGER NOT NULL,
    site_id INTEGER NOT NULL,
    vendor_site_assignment_id TEXT NOT NULL,
    binding_status TEXT NOT NULL DEFAULT 'inactive',
    predecessor_binding_id TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_actor_kind TEXT NOT NULL,
    created_actor_id TEXT NOT NULL,
    created_reason TEXT NOT NULL,
    created_source TEXT NOT NULL,
    created_correlation_id TEXT NOT NULL,
    updated_actor_kind TEXT NOT NULL,
    updated_actor_id TEXT NOT NULL,
    updated_reason TEXT NOT NULL,
    updated_source TEXT NOT NULL,
    updated_correlation_id TEXT NOT NULL,
    FOREIGN KEY (vendor_id)
        REFERENCES vendor_organizations(vendor_id)
        ON DELETE RESTRICT
        ON UPDATE NO ACTION,
    FOREIGN KEY (sheet_id)
        REFERENCES sheets(id)
        ON DELETE RESTRICT
        ON UPDATE NO ACTION,
    FOREIGN KEY (site_id)
        REFERENCES sites(id)
        ON DELETE RESTRICT
        ON UPDATE NO ACTION,
    FOREIGN KEY (vendor_site_assignment_id)
        REFERENCES vendor_site_assignments(vendor_site_assignment_id)
        ON DELETE RESTRICT
        ON UPDATE NO ACTION,
    FOREIGN KEY (predecessor_binding_id)
        REFERENCES sheet_vendor_bindings(sheet_vendor_binding_id)
        ON DELETE RESTRICT
        ON UPDATE NO ACTION,
    CHECK (
        typeof(sheet_vendor_binding_id) = 'text'
        AND length(sheet_vendor_binding_id) = 36
        AND sheet_vendor_binding_id GLOB
            '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
        AND sheet_vendor_binding_id <> '00000000-0000-0000-0000-000000000000'
    ),
    CHECK (
        typeof(vendor_id) = 'text'
        AND length(vendor_id) = 36
        AND vendor_id GLOB
            '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
        AND vendor_id <> '00000000-0000-0000-0000-000000000000'
    ),
    CHECK (
        typeof(vendor_site_assignment_id) = 'text'
        AND length(vendor_site_assignment_id) = 36
        AND vendor_site_assignment_id GLOB
            '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
        AND vendor_site_assignment_id <> '00000000-0000-0000-0000-000000000000'
    ),
    CHECK (
        predecessor_binding_id IS NULL
        OR (
            typeof(predecessor_binding_id) = 'text'
            AND length(predecessor_binding_id) = 36
            AND predecessor_binding_id GLOB
                '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f]-4[0-9a-f][0-9a-f][0-9a-f]-[89ab][0-9a-f][0-9a-f][0-9a-f]-[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'
            AND predecessor_binding_id <> '00000000-0000-0000-0000-000000000000'
            AND predecessor_binding_id <> sheet_vendor_binding_id
        )
    ),
    CHECK (typeof(sheet_id) = 'integer' AND sheet_id > 0),
    CHECK (typeof(site_id) = 'integer' AND site_id > 0),
    CHECK (binding_status IN ('active', 'inactive')),
    CHECK (created_actor_kind IN ('system', 'internal_user', 'vendor_account', 'migration')),
    CHECK (updated_actor_kind IN ('system', 'internal_user', 'vendor_account', 'migration')),
    CHECK (length(created_actor_id) BETWEEN 1 AND 128 AND length(trim(created_actor_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_actor_id) BETWEEN 1 AND 128 AND length(trim(updated_actor_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(created_reason) BETWEEN 1 AND 500 AND length(trim(created_reason, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_reason) BETWEEN 1 AND 500 AND length(trim(updated_reason, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(created_source) BETWEEN 1 AND 100 AND length(trim(created_source, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_source) BETWEEN 1 AND 100 AND length(trim(updated_source, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(created_correlation_id) BETWEEN 1 AND 128 AND length(trim(created_correlation_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0),
    CHECK (length(updated_correlation_id) BETWEEN 1 AND 128 AND length(trim(updated_correlation_id, CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT))) > 0)
) STRICT;
```

The default status is `inactive`; omission never creates a current binding.

An active binding is valid for runtime use only when a future authorized runtime transaction proves all of the following:

- the binding organization equals the referenced assignment organization;
- the binding site equals the referenced assignment site;
- the referenced assignment is active;
- the sheet currently belongs to the same canonical site;
- the organization is eligible;
- the binding itself is active; and
- the caller has operation-specific authority.

The DDL proves only the existence of each referenced row when foreign-key enforcement is enabled.

No legacy table or index is changed to create a composite foreign key. Same-organization, same-site, active-state, and sheet-site consistency remain runtime/checker responsibilities.

The predecessor lineage has the same linear, one-direct-successor rule as the other episode tables.

## 10. Exact index inventory and predicates

The exact index order follows the four table statements.

There are exactly 15 explicit vendor-owned indexes.

### Organization index

```sql
CREATE INDEX idx_vendor_organizations_status
ON vendor_organizations (organization_status);
```

There is no display-name index, normalized-name index, or unique display-name constraint. A later evidence-backed lookup owner may request a non-unique display-name index, but it is not frozen here.

### Membership indexes

```sql
CREATE UNIQUE INDEX uq_vendor_organization_memberships_active_account
ON vendor_organization_memberships (vendor_account_id)
WHERE membership_status = 'active';
```

```sql
CREATE UNIQUE INDEX uq_vendor_organization_memberships_current_pair
ON vendor_organization_memberships (vendor_id, vendor_account_id)
WHERE membership_status IN ('pending', 'active');
```

```sql
CREATE INDEX idx_vendor_organization_memberships_vendor_status
ON vendor_organization_memberships (vendor_id, membership_status);
```

```sql
CREATE INDEX idx_vendor_organization_memberships_account_status
ON vendor_organization_memberships (vendor_account_id, membership_status);
```

```sql
CREATE UNIQUE INDEX uq_vendor_organization_memberships_predecessor
ON vendor_organization_memberships (predecessor_membership_id)
WHERE predecessor_membership_id IS NOT NULL;
```

The predecessor unique index is also the predecessor lookup index. No redundant non-unique predecessor index is authorized.

### Assignment indexes

```sql
CREATE UNIQUE INDEX uq_vendor_site_assignments_active_pair
ON vendor_site_assignments (vendor_id, site_id)
WHERE assignment_status = 'active';
```

```sql
CREATE INDEX idx_vendor_site_assignments_vendor_status
ON vendor_site_assignments (vendor_id, assignment_status);
```

```sql
CREATE INDEX idx_vendor_site_assignments_site_status
ON vendor_site_assignments (site_id, assignment_status);
```

```sql
CREATE UNIQUE INDEX uq_vendor_site_assignments_predecessor
ON vendor_site_assignments (predecessor_assignment_id)
WHERE predecessor_assignment_id IS NOT NULL;
```

### Binding indexes

```sql
CREATE UNIQUE INDEX uq_sheet_vendor_bindings_active_pair
ON sheet_vendor_bindings (vendor_id, sheet_id)
WHERE binding_status = 'active';
```

```sql
CREATE INDEX idx_sheet_vendor_bindings_vendor_status
ON sheet_vendor_bindings (vendor_id, binding_status);
```

```sql
CREATE INDEX idx_sheet_vendor_bindings_sheet_status
ON sheet_vendor_bindings (sheet_id, binding_status);
```

```sql
CREATE INDEX idx_sheet_vendor_bindings_assignment
ON sheet_vendor_bindings (vendor_site_assignment_id);
```

```sql
CREATE UNIQUE INDEX uq_sheet_vendor_bindings_predecessor
ON sheet_vendor_bindings (predecessor_binding_id)
WHERE predecessor_binding_id IS NOT NULL;
```

The partial predicates are exact SQL contracts. The future checker may normalize insignificant SQLite whitespace and identifier quoting for comparison, but it must not broaden, reorder, or reinterpret a predicate.

No broad uniqueness may prevent multiple revoked membership episodes or multiple inactive assignment/binding episodes.

## 11. Historical episode and reactivation model

Membership, assignment, and binding IDs identify relationship episodes, not reusable pair identities.

The exact membership episode model is:

1. the first relationship episode is created as `pending`;
2. that same episode may transition `pending` to `active`;
3. that same episode may transition `pending` or `active` to `revoked`;
4. a revoked episode is immutable historical relationship state except that no later write is authorized by this document;
5. re-establishment creates a new `pending` row;
6. the new row sets `predecessor_membership_id` to the immediately preceding episode;
7. the predecessor unique index permits at most one direct successor; and
8. no in-place revoked-to-pending or revoked-to-active rewrite is permitted.

The exact assignment episode model is:

1. an authorized initial relationship creates a new `active` row;
2. deactivation updates that row from `active` to `inactive`;
3. the inactive row remains historical;
4. reactivation creates a new `active` row;
5. the new row points to the immediately preceding episode through `predecessor_assignment_id`;
6. the predecessor unique index permits at most one direct successor; and
7. no in-place inactive-to-active rewrite is permitted.

The exact binding episode model is identical:

1. an authorized initial relationship creates a new `active` row;
2. deactivation updates that row to `inactive`;
3. the inactive row remains historical;
4. reactivation creates a new `active` row;
5. the new row points to the immediately preceding episode through `predecessor_binding_id`;
6. the predecessor unique index permits at most one direct successor; and
7. no in-place inactive-to-active rewrite is permitted.

The linear predecessor indexes prevent branching from one predecessor.

They do not prevent:

- a cycle longer than one row;
- a link across account, organization, site, sheet, or relationship pair;
- skipping an intermediate episode;
- a status-incompatible predecessor; or
- an unauthorized or stale transition.

Every future mutation must reject those cases transactionally. A future checker must be able to report them without repairing them.

## 12. Provenance capability and deferred audit boundary

Every table has the same current-row provenance column set:

```text
created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
created_actor_kind TEXT NOT NULL
created_actor_id TEXT NOT NULL
created_reason TEXT NOT NULL
created_source TEXT NOT NULL
created_correlation_id TEXT NOT NULL
updated_actor_kind TEXT NOT NULL
updated_actor_id TEXT NOT NULL
updated_reason TEXT NOT NULL
updated_source TEXT NOT NULL
updated_correlation_id TEXT NOT NULL
```

The closed actor-kind vocabulary is:

```text
system
internal_user
vendor_account
migration
```

The meanings are:

| Value | Stored meaning | Must not be inferred |
|---|---|---|
| `system` | A separately approved server-controlled operation | That any system component is authorized |
| `internal_user` | An internal backend-principal identifier is recorded | Authentication, role, permission, or global identity |
| `vendor_account` | A vendor backend-principal identifier is recorded | Membership, owner role, organization, or permission |
| `migration` | A later separately approved migration actor is recorded | Backfill authority from this schema document |

Actor identifiers are opaque, non-authoritative text of 1–128 characters after the exact DDL checks.

Reason values are opaque text of 1–500 characters.

Source values are opaque text of 1–100 characters.

Correlation IDs are opaque text of 1–128 characters. They are not vendor entity IDs and do not receive the vendor UUID semantic contract.

The exact blank-string character set for `display_name` and every actor ID, reason, source, and correlation value is:

```text
U+0009 CHARACTER TABULATION
U+000A LINE FEED
U+000B LINE TABULATION
U+000C FORM FEED
U+000D CARRIAGE RETURN
U+001C FILE SEPARATOR
U+001D GROUP SEPARATOR
U+001E RECORD SEPARATOR
U+001F UNIT SEPARATOR
U+0020 SPACE
U+0085 NEXT LINE
U+00A0 NO-BREAK SPACE
U+1680 OGHAM SPACE MARK
U+2000 EN QUAD
U+2001 EM QUAD
U+2002 EN SPACE
U+2003 EM SPACE
U+2004 THREE-PER-EM SPACE
U+2005 FOUR-PER-EM SPACE
U+2006 SIX-PER-EM SPACE
U+2007 FIGURE SPACE
U+2008 PUNCTUATION SPACE
U+2009 THIN SPACE
U+200A HAIR SPACE
U+2028 LINE SEPARATOR
U+2029 PARAGRAPH SEPARATOR
U+202F NARROW NO-BREAK SPACE
U+205F MEDIUM MATHEMATICAL SPACE
U+3000 IDEOGRAPHIC SPACE
```

The exact UTF-8 bytes for the set, in the order above, are:

```text
090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080
```

Every relevant DDL CHECK passes that byte string through:

```sql
CAST(X'090A0B0C0D1C1D1E1F20C285C2A0E19A80E28080E28081E28082E28083E28084E28085E28086E28087E28088E28089E2808AE280A8E280A9E280AFE2819FE38080' AS TEXT)
```

and uses it as the second argument to SQLite `trim`.

A value is blank exactly when removing characters from that set at both ends leaves length zero.

Consequences:

- ASCII-space-only input is rejected;
- tab-only input is rejected;
- LF/newline-only input is rejected;
- NBSP-only input is rejected;
- any mixture made only from the 29 frozen characters is rejected;
- ordinary nonblank text is accepted within its column's length bound;
- surrounding frozen whitespace is not removed from stored nonblank text; and
- no Unicode normalization or value mutation occurs.

No other code point is classified as whitespace by this DDL contract.

Creation provenance is immutable by contract. Ordinary DDL cannot fully enforce that immutability without triggers, and triggers are forbidden.

Update provenance describes only the latest separately authorized row change.

The timestamp defaults:

- populate insert-time UTC text according to SQLite's `CURRENT_TIMESTAMP`;
- do not validate actor or authority;
- do not update automatically;
- do not prove chronology across systems; and
- do not create an event history.

Before/after history, append-only audit events, idempotency records, and mutation receipts require a later audit/event owner.

No password, password hash, credential, session value, token, secret, database URL, or raw authorization proof may be stored in provenance.

Provenance capability does not make any lifecycle or relationship mutation safe or authorized.

## 13. Foreign-key and cross-row enforcement boundary

The exact foreign-key metadata is:

| Child table | Child column | Parent table | Parent column | On update | On delete |
|---|---|---|---|---|---|
| `vendor_organization_memberships` | `vendor_id` | `vendor_organizations` | `vendor_id` | `NO ACTION` | `RESTRICT` |
| `vendor_organization_memberships` | `vendor_account_id` | `vendor_accounts` | `id` | `NO ACTION` | `RESTRICT` |
| `vendor_organization_memberships` | `predecessor_membership_id` | `vendor_organization_memberships` | `vendor_membership_id` | `NO ACTION` | `RESTRICT` |
| `vendor_site_assignments` | `vendor_id` | `vendor_organizations` | `vendor_id` | `NO ACTION` | `RESTRICT` |
| `vendor_site_assignments` | `site_id` | `sites` | `id` | `NO ACTION` | `RESTRICT` |
| `vendor_site_assignments` | `predecessor_assignment_id` | `vendor_site_assignments` | `vendor_site_assignment_id` | `NO ACTION` | `RESTRICT` |
| `sheet_vendor_bindings` | `vendor_id` | `vendor_organizations` | `vendor_id` | `NO ACTION` | `RESTRICT` |
| `sheet_vendor_bindings` | `sheet_id` | `sheets` | `id` | `NO ACTION` | `RESTRICT` |
| `sheet_vendor_bindings` | `site_id` | `sites` | `id` | `NO ACTION` | `RESTRICT` |
| `sheet_vendor_bindings` | `vendor_site_assignment_id` | `vendor_site_assignments` | `vendor_site_assignment_id` | `NO ACTION` | `RESTRICT` |
| `sheet_vendor_bindings` | `predecessor_binding_id` | `sheet_vendor_bindings` | `sheet_vendor_binding_id` | `NO ACTION` | `RESTRICT` |

The DDL and indexes enforce or represent the following:

| VENDOR-ID-001 invariant | Frozen physical classification |
|---|---|
| Stable opaque row identities | primary key plus DDL CHECK |
| Closed organization states | DDL CHECK |
| Closed membership roles and states | DDL CHECK |
| Closed assignment/binding states | DDL CHECK |
| Positive stored-integer parent-key shape after SQLite affinity | DDL CHECK plus foreign-key metadata |
| Original caller value has exact application integer type | runtime transaction only before SQL binding |
| At most one active organization membership per account | partial unique index |
| At most one pending-or-active account/organization relationship | partial unique index |
| At most one active organization/site assignment | partial unique index |
| At most one active organization/sheet binding | partial unique index |
| At most one direct successor per predecessor episode | partial unique index |
| Parent-row existence | foreign-key metadata plus future runtime validation |
| Predecessor same relationship/account/organization | runtime transaction only and future checker |
| Predecessor status and chronological compatibility | runtime transaction only and future checker |
| Allowed lifecycle transitions | runtime transaction only |
| Last active owner protection | runtime transaction only |
| Atomic owner transfer | runtime transaction only |
| Organization eligibility | runtime transaction only |
| Same-organization, same-site active assignment for binding | runtime transaction only and future checker |
| Sheet-site consistency | runtime transaction only and future checker |
| Stale-state rejection | runtime transaction only |
| Caller authority | runtime transaction only under a later owner |
| Creation provenance immutability | runtime transaction only and future checker |
| Cross-row provenance validity | runtime transaction only and future checker |
| Before/after history | deferred audit owner |

DDL cannot guarantee:

- the last-active-owner invariant;
- an allowed state or role transition;
- atomic owner transfer;
- organization eligibility;
- same-site active assignment;
- binding/assignment active-state agreement;
- sheet-site consistency;
- stale-state rejection;
- caller authority;
- predecessor pair compatibility;
- creation-provenance immutability;
- cross-row provenance validity; or
- before/after history.

No delete or key-update consumer is authorized.

A future writer must reject deletions and relationship-key mutation at runtime even if foreign-key enforcement is disabled.

## 14. Exact schema-state decision table

The required object set is:

- the four tables frozen by Sections 5–9;
- the 15 explicit indexes frozen by Section 10; and
- exactly four SQLite-generated primary-key autoindexes.

The exact permitted internal autoindexes are:

```text
sqlite_autoindex_vendor_organizations_1
sqlite_autoindex_vendor_organization_memberships_1
sqlite_autoindex_vendor_site_assignments_1
sqlite_autoindex_sheet_vendor_bindings_1
```

Each permitted autoindex:

- belongs to the table named in the autoindex;
- has `sqlite_schema.type = 'index'`;
- has `sqlite_schema.sql IS NULL`;
- has `pragma_index_list.origin = 'pk'`;
- is unique;
- is not partial;
- has exactly one key column, the table's text primary-key column, using `BINARY` collation and ascending order; and
- has only SQLite's expected non-key rowid auxiliary entry after that key column.

No other `sqlite_autoindex_*` object on a required table is permitted.

The vendor-owned object namespace is exact:

- the four exact table names;
- every table, view, or trigger name beginning with `vendor_organization_`;
- every table, view, or trigger name beginning with `vendor_organizations_`;
- every table, view, or trigger name beginning with `vendor_site_assignment_`;
- every table, view, or trigger name beginning with `vendor_site_assignments_`;
- every table, view, or trigger name beginning with `sheet_vendor_binding_`;
- every table, view, or trigger name beginning with `sheet_vendor_bindings_`;
- every index name beginning with `idx_vendor_organizations_`;
- every index name beginning with `uq_vendor_organizations_`;
- every index name beginning with `idx_vendor_organization_memberships_`;
- every index name beginning with `uq_vendor_organization_memberships_`;
- every index name beginning with `idx_vendor_site_assignments_`;
- every index name beginning with `uq_vendor_site_assignments_`;
- every index name beginning with `idx_sheet_vendor_bindings_`; and
- every index name beginning with `uq_sheet_vendor_bindings_`.

Ownership is also relationship-based, not only name-based:

- every index whose `main.sqlite_schema.tbl_name` is one of the four exact vendor tables is vendor-owned regardless of index name;
- every trigger whose `main.sqlite_schema.tbl_name` is one of the four exact vendor tables is vendor-owned regardless of trigger name; and
- every required table's SQLite-generated PK autoindex is vendor-owned.

Therefore an index named `rogue_unique`, an index named `anything`, or a trigger named `after_write` is an extra owned object when it is attached to a required vendor table.

Only the 15 exact explicit indexes and four exact PK autoindexes are allowed on the four tables.

No trigger is allowed on any of the four tables.

The exact table names are owned even where a prefix rule would not otherwise match.

Legacy objects such as `vendor_accounts`, `vendor_contacts`, `vendor_work_entries`, `idx_vendor_accounts_vendor_name`, and their existing indexes are not VENDOR-ID-002-owned objects.

An object is unrelated only when:

- its name is outside every reserved name rule;
- its `tbl_name` is not one of the four required tables; and
- it is not one of the four expected internal autoindexes.

Unrelated legacy objects do not cause fuzzy-match failure and are not altered.

### 14.1 Legacy parent-key prerequisites

Creation eligibility requires a metadata-only compatibility projection for these exact parents:

```text
main.vendor_accounts(id)
main.sites(id)
main.sheets(id)
```

Each parent must satisfy all of the following before the helper creates its savepoint:

- it exists in schema `main`;
- its SQLite object type is `table`;
- it is a rowid table, with `pragma_table_list.wr = 0`;
- it has exactly one visible column named `id`;
- that column has `cid = 0`;
- its declared type, after trimming surrounding ASCII whitespace and converting ASCII letters to uppercase, is exactly `INTEGER`;
- its default is `NULL`;
- its primary-key position is exactly `1`;
- its hidden flag is exactly `0`;
- its `notnull` metadata is exactly `0`, matching the current repository's implicit `INTEGER PRIMARY KEY` declaration;
- the top-level `id` column declaration token sequence is exactly `id INTEGER PRIMARY KEY` or `id INTEGER PRIMARY KEY AUTOINCREMENT`;
- the `id` declaration contains no `COLLATE` clause; and
- no second column has a nonzero primary-key position.

An exact `INTEGER PRIMARY KEY` is the SQLite rowid alias and is the required unique parent key. A separate unique index is neither required nor accepted as a substitute for a missing or incompatible integer primary key.

The absence of `COLLATE` freezes the parent-key comparison as SQLite's default `BINARY` collation. A custom parent-key collation is incompatible.

The parent table's other columns, indexes, rows, and business constraints are outside this projection and are not interpreted.

The helper must not:

- read a parent row;
- count parent rows;
- create or alter a parent object;
- add a parent index;
- infer compatibility from DML success; or
- accept a view, virtual table, temp table, or attached-database table as a parent.

A compatible parent found only in `temp` or an attached schema does not satisfy the prerequisite.

Missing table, wrong object type, missing/wrong `id`, non-integer key, non-primary key, composite primary key, non-BINARY collation, hidden/generated key, or a unique non-PK substitute classifies as `parent_incompatible`.

An explicit `NOT NULL` on the parent `id` is also `parent_incompatible` in this frozen baseline, even though it may be SQLite-compatible in isolation. The metadata and accepted lexical declarations intentionally describe the same two current-repository forms only.

### 14.2 Fixed metadata queries

The schema comparator uses only the fixed SQL below.

The complete `main.sqlite_schema` projection is:

```sql
SELECT type, name, tbl_name, sql
FROM main.sqlite_schema
ORDER BY
    type COLLATE BINARY,
    name COLLATE BINARY,
    tbl_name COLLATE BINARY;
```

Its exact row shape is:

```text
(type: str, name: str, tbl_name: str, sql: str | None)
```

The complete `temp.sqlite_schema` projection is:

```sql
SELECT type, name, tbl_name, sql
FROM temp.sqlite_schema
ORDER BY
    type COLLATE BINARY,
    name COLLATE BINARY,
    tbl_name COLLATE BINARY;
```

Its exact row shape is:

```text
(type: str, name: str, tbl_name: str, sql: str | None)
```

Every TEMP index or trigger whose `tbl_name` is one of the four exact main vendor tables is vendor-owned regardless of its own name.

Any arbitrary-name TEMP trigger attached to a main vendor table classifies as `extra_owned_object`.

Any TEMP object using a reserved vendor-owned name classifies under the existing `wrong_object_type`/`extra_owned_object` precedence.

The complete table-list projection is:

```sql
SELECT schema, name, type, ncol, wr, strict
FROM pragma_table_list
ORDER BY
    schema COLLATE BINARY,
    name COLLATE BINARY,
    type COLLATE BINARY;
```

Its exact row shape is:

```text
(schema: str, name: str, type: str, ncol: int, wr: int, strict: int)
```

The exact table-column projection, executed once for each internally frozen required or legacy-parent table name, is:

```sql
SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo(?1, 'main')
ORDER BY cid;
```

Its only bound value is an internally frozen table name. Its exact row shape is:

```text
(cid: int, name: str, type: str, notnull: int, dflt_value: str | None, pk: int, hidden: int)
```

The exact foreign-key projection, executed once for each internally frozen required table name, is:

```sql
SELECT "from", "table", "to", on_update, on_delete, match, seq
FROM pragma_foreign_key_list(?1, 'main')
ORDER BY
    "from" COLLATE BINARY,
    "table" COLLATE BINARY,
    "to" COLLATE BINARY,
    seq;
```

Its only bound value is an internally frozen required table name. Its exact row shape is:

```text
(from: str, table: str, to: str, on_update: str, on_delete: str, match: str, seq: int)
```

The exact index-list projection, executed once for each internally frozen required table name, is:

```sql
SELECT name, "unique", origin, partial
FROM pragma_index_list(?1, 'main')
ORDER BY name COLLATE BINARY;
```

Its only bound value is an internally frozen required table name. Its exact row shape is:

```text
(name: str, unique: int, origin: str, partial: int)
```

The exact index-column projection, executed once for each expected explicit or internal index name, is:

```sql
SELECT seqno, cid, name, "desc", coll, key
FROM pragma_index_xinfo(?1, 'main')
ORDER BY seqno;
```

Its only bound value is an internally frozen index name. Its exact row shape is:

```text
(seqno: int, cid: int, name: str | None, desc: int, coll: str | None, key: int)
```

The database-topology projection is:

```sql
SELECT seq, name, file
FROM pragma_database_list
ORDER BY seq;
```

Its exact row shape is:

```text
(seq: int, name: str, file: str)
```

The metadata-query inventory is exactly eight fixed SQL constants:

```text
1. main.sqlite_schema
2. temp.sqlite_schema
3. pragma_table_list
4. pragma_table_xinfo
5. pragma_foreign_key_list
6. pragma_index_list
7. pragma_index_xinfo
8. pragma_database_list
```

`main` is mandatory. `temp` may be present. Any other schema name classifies as `unsupported_database_topology` before parent validation, savepoint creation, or DDL.

The `temp.sqlite_schema` and `pragma_table_list` results must not contain a required or reserved vendor-owned object name in `temp`. Such a shadow classifies as `wrong_object_type` or `extra_owned_object`, as applicable.

The fixed `temp.sqlite_schema` projection also detects arbitrary-name TEMP triggers whose `tbl_name` is one of the four main vendor tables.

All authoritative schema queries are explicitly `main`-qualified or pass the literal schema argument `'main'`.

Objects in `temp` or an attached schema:

- never satisfy a required object;
- never satisfy a legacy parent;
- never replace a `main` result; and
- never authorize creation.

No dynamic `PRAGMA` statement is allowed.

No schema name, table name, index name, identifier, or SQL fragment is interpolated.

Bound parameter values come only from immutable internal tuples frozen by this document. The helper accepts no caller-supplied SQL, schema, table, index, predicate, or identifier.

### 14.3 Exact tuple comparison and ordering

The comparator first validates every returned Python value against the exact tuple shape above.

Unexpected result-column count, result-value type, forbidden `NULL`, duplicate metadata row, out-of-order key, or impossible metadata value classifies as `metadata_unreadable`.

A cleanly projected absence is not a malformed result: an absent legacy parent maps to `parent_incompatible`, while absent required vendor objects participate in `all_absent` or `partial` classification.

The ordered required-table tuple is:

```text
vendor_organizations
vendor_organization_memberships
vendor_site_assignments
sheet_vendor_bindings
```

The ordered legacy-parent tuple is:

```text
vendor_accounts
sites
sheets
```

The ordered explicit-index tuple is the exact creation order in Section 10.

The ordered internal-index tuple is the four autoindex names listed at the start of Section 14.

Table columns are compared by `cid`.

Foreign keys are compared by `(from, table, to, seq)` after projecting the complete result.

Every frozen FK is single-column and therefore has `seq = 0`. SQLite's internal FK `id` is deliberately not projected because full canonical SQL already freezes declaration order and the internal numeric identifier is not part of the semantic FK contract.

Indexes are compared by `name COLLATE BINARY`.

Index columns and auxiliary rows are compared by `seqno`.

For every explicit index:

- `origin` is exactly `c`;
- `unique` is exactly `0` or `1` as frozen by its statement;
- `partial` is exactly `0` or `1` as frozen by its statement;
- each declared key column has `key = 1`, `desc = 0`, and `coll = 'BINARY'`;
- the final SQLite rowid auxiliary entry has `cid = -1`, `name IS NULL`, `key = 0`, `desc = 0`, and `coll = 'BINARY'`; and
- no expression column (`cid = -2`) is allowed.

For every expected PK autoindex, the exact `pragma_index_list` tuple is:

```text
(expected_autoindex_name, 1, "pk", 0)
```

The exact `pragma_index_xinfo` rows are:

```text
(0, 0, exact_primary_key_column_name, 0, "BINARY", 1)
(1, -1, None, 0, "BINARY", 0)
```

The primary-key column name is respectively:

```text
vendor_id
vendor_membership_id
vendor_site_assignment_id
sheet_vendor_binding_id
```

An internal autoindex has `main.sqlite_schema.sql IS NULL`.

`NULL` internal SQL is never converted to an empty string and never passed to SQL normalization.

An explicit table or index must have non-null SQL.

### 14.4 Exact SQL normalization

The normalizer accepts only a Python `str` for explicit table/index SQL.

It applies these operations in this exact order:

1. Reject a string containing U+0000.
2. Reject an unpaired Unicode surrogate.
3. Replace each CRLF pair with LF.
4. Replace each remaining CR with LF.
5. Remove leading and trailing characters only from this ASCII set: space, tab, LF, vertical tab, and form feed.
6. If the resulting final character is one semicolon, remove exactly that semicolon.
7. Again remove trailing characters only from the same ASCII set.
8. Require a non-empty result.

The normalizer does not:

- case-fold;
- Unicode-normalize;
- collapse internal whitespace;
- rewrite quoting;
- remove comments;
- reorder clauses;
- tokenize or reserialize the canonical DDL; or
- accept an extra semicolon.

Each expected table/index SQL value is the corresponding canonical Section 6–10 statement after the same normalization.

Observed explicit SQL must compare code-point-for-code-point equal to that expected value.

SQLite's own limited schema-table normalization is not treated as a flexible equivalence rule. Because the future implementation executes the exact canonical statement, any additional case, quoting, comment, or internal-whitespace difference is drift.

For a partial index, the full normalized `CREATE UNIQUE INDEX` statement is compared first.

The predicate projection is then the exact suffix following the statement's only uppercase delimiter: one LF (U+000A), the five ASCII characters `WHERE`, and one SPACE (U+0020).

The suffix, excluding the final normalized semicolon, must be exactly one of:

```text
membership_status = 'active'
membership_status IN ('pending', 'active')
predecessor_membership_id IS NOT NULL
assignment_status = 'active'
predecessor_assignment_id IS NOT NULL
binding_status = 'active'
predecessor_binding_id IS NOT NULL
```

No alternate capitalization, quoting, operand order, redundant parentheses, comment, collation, or logically equivalent predicate is accepted.

### 14.5 Exact parent-declaration parser

The legacy-parent compatibility parser is separate from full vendor-object SQL comparison.

It uses a fixed lexical scanner over the normalized `main.sqlite_schema.sql` for the three exact parent tables.

The scanner:

- recognizes SQLite single-quoted string literals, double-quoted identifiers, backtick-quoted identifiers, and bracket-quoted identifiers;
- tracks parentheses depth;
- splits table elements only on commas at depth one;
- rejects malformed quoting, comments, embedded U+0000, or unbalanced parentheses;
- selects the element whose first unquoted identifier is exactly `id` under ASCII case-insensitive comparison;
- requires that element to be the first column element; and
- converts only its unquoted ASCII keyword tokens to uppercase.

After removing insignificant ASCII whitespace between tokens, the accepted token sequences are exactly:

```text
id INTEGER PRIMARY KEY
id INTEGER PRIMARY KEY AUTOINCREMENT
```

Quoted `id`, a constraint name, sort direction, conflict clause, default, generated clause, reference, or `COLLATE` clause is not in the accepted sequence.

The lexical result and `pragma_table_xinfo` result must both pass. Neither can substitute for the other.

The exact decision table is:

| Observed state | Required classification | Required behavior |
|---|---|---|
| All four tables, all 15 explicit indexes, and all four PK autoindexes absent; no other owned object exists; all three legacy parents compatible | `all_absent` | Eligible to create the exact empty schema inside the helper savepoint |
| All four tables, all 15 explicit indexes, and all four PK autoindexes exact; no other owned object exists; all three legacy parents compatible | `all_exact` | Exact no-op; execute no DDL and create no savepoint |
| Any non-empty proper subset of required objects exists | `partial` | Fail closed before savepoint; no DDL |
| A required object exists with wrong type, SQL, columns, order, type, nullability, default, PK, STRICT flag, CHECK, FK, index metadata, uniqueness, columns, or predicate | `drifted` | Fail closed before savepoint; no repair |
| An extra table, index, view, or trigger exists in the owned namespace | `extra_owned_object` | Fail closed before savepoint |
| An arbitrary-name unique or non-unique index has a required table as `tbl_name` | `extra_owned_object` | Fail closed before savepoint |
| An arbitrary-name trigger has a required table as `tbl_name` | `extra_owned_object` | Fail closed before savepoint |
| An arbitrary-name TEMP trigger has a required main vendor table as `tbl_name` | `extra_owned_object` | Fail closed before savepoint |
| A reserved-name TEMP table, view, index, or trigger exists | `wrong_object_type` or `extra_owned_object` | Apply frozen precedence and fail before savepoint |
| An internal autoindex is missing, extra, attached to the wrong table, has non-null SQL, or has wrong index metadata | `drifted` | Fail closed before savepoint |
| A required name exists with the wrong SQLite object type | `wrong_object_type` | Fail closed before savepoint |
| Any required legacy parent is missing or incompatible in `main` | `parent_incompatible` | Fail closed before savepoint; do not inspect parent rows or repair parent schema |
| A compatible parent exists only in `temp` or an attached schema | `parent_incompatible` | Fail closed before savepoint |
| A non-`main`/non-`temp` database is attached | `unsupported_database_topology` | Fail closed before parent validation, savepoint, or DDL |
| A required/reserved vendor name is shadowed in `temp` | `wrong_object_type` or `extra_owned_object` | Fail closed before savepoint |
| Only compatible legacy vendor tables/indexes exist and every required object is absent | `all_absent` | Preserve legacy objects; eligible to create exact empty schema |
| Required objects are exact and one or more required tables contain rows | `all_exact` | Exact no-op; checker/manifest may report row counts, but the migration helper neither fails nor reads, creates, updates, or deletes a row |
| Schema metadata cannot be read or deterministically resolved | `metadata_unreadable` | Fail closed; no DDL |
| An unrelated main-schema object is outside the owned namespace, has no required table as `tbl_name`, and does not affect a legacy parent key | no vendor-state effect | Preserve it; classify only the required and owned objects |

The implementation-acceptance and initial rollout gate requires all four tables to be empty immediately after creation. That one-time evidence requirement is not a permanent bootstrap precondition. After a separately authorized later slice creates rows, an exact populated schema remains `all_exact` and bootstrap remains a no-op.

Schema exactness never adopts, validates, authorizes, or repairs the rows. Row-content validation belongs to later consumers and checkers.

No state authorizes:

- automatic `DROP`;
- `ALTER`;
- rename;
- repair;
- reconstruction;
- `CREATE IF NOT EXISTS`;
- partial completion;
- data copying; or
- object adoption by fuzzy name.

## 15. Migration transaction and savepoint contract

The future exception and helper signatures are exactly:

```python
class VendorOrganizationSchemaMigrationError(RuntimeError):
    code: str

    def __init__(self, code: str, /) -> None:
        ...


def ensure_vendor_organization_schema(
    conn: sqlite3.Connection,
    /,
) -> str:
    ...
```

The helper has:

- exactly one positional-only parameter named `conn`;
- no default;
- no `*args`;
- no `**kwargs`;
- no caller-supplied schema, statement, identifier, option, or policy parameter;
- the annotation `sqlite3.Connection`; and
- the return annotation `str`.

The exception initializer has exactly one positional-only `code: str` parameter after `self`, no default, no variadic parameters, and return annotation `None`.

It rejects construction with any code outside the frozen set.

Its connection parameter is caller-owned.

The exact success returns are:

```text
"created"
"all_exact"
```

`"created"` means that all four tables, 15 explicit indexes, and four expected PK autoindexes were proven exact after execution inside the still-active caller transaction.

`"all_exact"` means the pre-existing required schema was proven exact and the helper executed no savepoint or DDL.

Neither return value:

- commits;
- proves row contents;
- proves runtime authority; or
- authorizes a writer.

No other success value, boolean, `None`, object, count, or detail dictionary is permitted.

The exact stable error codes are:

```text
invalid_connection
inactive_transaction
metadata_unreadable
unsupported_database_topology
parent_incompatible
schema_partial
schema_drifted
extra_owned_object
wrong_object_type
savepoint_create_failed
ddl_or_postcheck_failed
rollback_to_failed
cleanup_release_failed
success_release_failed
```

For code `<code>`, the exception contract is:

```text
type:
VendorOrganizationSchemaMigrationError

args:
("VENDOR-ID-002 schema migration failed [<code>]",)

code:
<code>
```

The exception exposes no other public detail attribute.

Raw SQLite messages, SQL text, paths, connection representations, database filenames, parent rows, schema contents, and injected fault strings are not part of the stable message or attributes.

The public exception must have:

```text
__cause__ is None
__context__ is None
```

Implementation must finish handling and discard a caught internal exception before it raises the bounded public exception. Raising the public exception while an internal exception is active is forbidden because `raise ... from None` alone would still retain `__context__`.

Private logs are not authorized by this docs-only contract.

The exact classification-to-code map is:

| Condition | Stable code |
|---|---|
| `isinstance(conn, sqlite3.Connection)` is false | `invalid_connection` |
| `conn.in_transaction` is not exactly true | `inactive_transaction` |
| Fixed metadata query, tuple validation, SQL normalization, or parser fails | `metadata_unreadable` |
| Attached database topology is outside the frozen boundary | `unsupported_database_topology` |
| Any legacy parent prerequisite fails | `parent_incompatible` |
| Required schema is a non-empty proper subset | `schema_partial` |
| Required object or autoindex metadata differs | `schema_drifted` |
| Any additional owned object exists | `extra_owned_object` |
| Required/reserved name has wrong object type or temp shadow | `wrong_object_type` |
| Helper savepoint cannot be created | `savepoint_create_failed` |
| Canonical DDL or post-create exactness/emptiness proof fails and cleanup succeeds | `ddl_or_postcheck_failed` |
| Rollback-to fails | `rollback_to_failed` |
| Rollback-to succeeds but cleanup release fails | `cleanup_release_failed` |
| Success-path release fails | `success_release_failed` |

When more than one schema-state defect is observed in the same complete metadata projection, precedence is:

```text
unsupported_database_topology
metadata_unreadable
parent_incompatible
wrong_object_type
extra_owned_object
schema_partial
schema_drifted
```

The helper reports only the highest-precedence stable code. It does not expose an object name or defect inventory.

The frozen transaction choice is:

```text
A. The helper requires an already-active caller transaction before entering its savepoint.
```

The reserved helper savepoint name is:

```text
vendor_id_002_schema_v1
```

The helper must not:

- call `commit()`;
- call connection-wide `rollback()`;
- execute `BEGIN`, `BEGIN IMMEDIATE`, or `BEGIN EXCLUSIVE`;
- use `executescript()`;
- close the connection;
- alter transaction isolation;
- change a PRAGMA;
- interpolate an identifier;
- accept a statement list from a caller; or
- catch a failure and continue creating later objects.

The exact post-create emptiness constants are:

```text
VENDOR_ORGANIZATIONS_ROW_COUNT_SQL
VENDOR_ORGANIZATION_MEMBERSHIPS_ROW_COUNT_SQL
VENDOR_SITE_ASSIGNMENTS_ROW_COUNT_SQL
SHEET_VENDOR_BINDINGS_ROW_COUNT_SQL
```

Their literal SQL values are respectively:

```sql
SELECT COUNT(*) AS row_count
FROM main.vendor_organizations;
```

```sql
SELECT COUNT(*) AS row_count
FROM main.vendor_organization_memberships;
```

```sql
SELECT COUNT(*) AS row_count
FROM main.vendor_site_assignments;
```

```sql
SELECT COUNT(*) AS row_count
FROM main.sheet_vendor_bindings;
```

Each query:

- is a separate immutable literal constant;
- is main-qualified;
- contains no placeholder;
- accepts no parameter;
- uses no identifier or table-name interpolation;
- executes only after the create-path schema recheck succeeds;
- executes before the success-path `RELEASE SAVEPOINT vendor_id_002_schema_v1`;
- must return exactly one result row;
- must return exactly one column named `row_count`;
- must return an exact Python `int`, not `bool` or a coercible value;
- must return a nonnegative value; and
- must return exactly zero for creation success.

The `all_exact` no-op path never executes any of these four queries.

A query exception, zero rows, multiple rows, wrong column count/name, wrong value type, negative value, or nonzero value is a post-check failure. It executes the frozen rollback-to and cleanup-release sequence and, when cleanup succeeds, raises `ddl_or_postcheck_failed`.

The exact algorithm is:

1. Evaluate exactly `isinstance(conn, sqlite3.Connection)`; if false, raise the bounded `invalid_connection` failure.
2. Read `connection.in_transaction`.
3. If it is not exactly true, raise `inactive_transaction` before schema metadata inspection, savepoint creation, or DDL.
4. Project database topology, parent metadata, and vendor schema state inside the caller-owned transaction using only the fixed Section 14 queries.
5. If metadata inspection or tuple comparison fails, map it to the exact bounded code and execute no DDL.
6. If state is `all_exact`, return exactly `"all_exact"` without reading row content. Do not create a savepoint.
7. If state is anything other than eligible `all_absent` with compatible parents, raise its exact bounded failure before savepoint.
8. Execute exactly `SAVEPOINT vendor_id_002_schema_v1` using one `execute()` call.
9. Execute each of the four canonical table statements and 15 canonical index statements in frozen order using one `execute()` call per statement.
10. Reproject and reclassify the resulting schema and prove it is exact, including exact attached indexes/triggers and PK autoindexes.
11. Execute the four literal emptiness constants in the frozen order and prove each exact result is integer zero.
12. Execute exactly `RELEASE SAVEPOINT vendor_id_002_schema_v1`.
13. Return exactly `"created"` while leaving the caller transaction active.

The helper's success does not commit the schema.

An explicit caller rollback after helper success removes every new object.

An explicit caller commit after helper success preserves the exact objects.

`init_schema()` and `migrate_schema()` must satisfy the precondition as follows:

- all legacy `executescript()` work, if still present, finishes before the VENDOR-ID-002 caller-owned transaction begins;
- the caller checks `connection.in_transaction`;
- if false, the caller executes `BEGIN IMMEDIATE` before calling the helper;
- if true, the caller does not issue another `BEGIN`;
- the caller invokes the helper on the same connection;
- the caller, not the helper, owns the eventual commit or connection-wide rollback;
- no legacy `executescript()` executes between the caller's `BEGIN IMMEDIATE`, helper invocation, and caller resolution; and
- the enclosing `init_schema()` or `migrate_schema()` failure path rolls back its caller-owned transaction.

The `BEGIN IMMEDIATE` rule applies only when these entry points do not already have an active caller transaction. It is not executed by the helper.

An existing caller transaction may include earlier caller-owned work. Helper failure must not commit or connection-wide rollback that work.

Failure behavior is exact:

| Failure point | Helper behavior | Caller obligation | Result after required resolution |
|---|---|---|---|
| Invalid connection | Raise `invalid_connection` before inspection/savepoint/DDL | Caller retains ownership | No vendor object created |
| Inactive transaction | Raise `inactive_transaction` before inspection/savepoint/DDL | Caller retains ownership | No vendor object created |
| Metadata read/shape/normalization failure | Raise `metadata_unreadable` before savepoint/DDL | Caller decides rollback | No vendor object created |
| Parent incompatibility | Raise `parent_incompatible` before savepoint/DDL | Caller decides rollback | No vendor object created |
| Partial, drifted, extra, wrong-type, or unsupported topology | Raise the exact mapped stable code before savepoint/DDL | Caller decides rollback | No vendor object created |
| `SAVEPOINT` creation | Raise `savepoint_create_failed`; execute no DDL | Caller rolls back its transaction if connection state is uncertain | No vendor object after caller rollback |
| Any table or index statement | Stop immediately; execute `ROLLBACK TO SAVEPOINT vendor_id_002_schema_v1`, then `RELEASE SAVEPOINT vendor_id_002_schema_v1`; if both succeed, raise `ddl_or_postcheck_failed` | Caller transaction remains active after successful cleanup; otherwise caller immediately rolls back the whole transaction | No partial vendor objects after cleanup or caller rollback |
| Post-create exactness or emptiness proof | Apply the same cleanup and `ddl_or_postcheck_failed` mapping as DDL failure | Same as DDL failure | No partial vendor objects after cleanup or caller rollback |
| `ROLLBACK TO SAVEPOINT` | Raise `rollback_to_failed`; do not attempt further DDL or same-name release; do not call connection-wide rollback | Caller immediately rolls back the whole transaction | No vendor objects after caller rollback |
| Cleanup `RELEASE SAVEPOINT` after successful rollback-to | Raise `cleanup_release_failed`; do not report clean recovery or call connection-wide rollback | Caller immediately rolls back the whole transaction | No vendor objects after caller rollback |
| Success-path `RELEASE SAVEPOINT` | Raise `success_release_failed`; do not report success or retry inside the same transaction | Caller immediately rolls back the whole transaction | No vendor objects after caller rollback |

When rollback-to fails, the helper does not execute a same-name `RELEASE`, because release could collapse an uncertain boundary. The caller resolves the connection with a whole-transaction rollback.

The reserved savepoint name can already exist in a caller's outer savepoint stack. SQLite creates a nested same-name savepoint, and `ROLLBACK TO`/`RELEASE` resolve to the innermost matching savepoint. The helper therefore owns only its innermost frame; a pre-existing same-name outer frame remains caller-owned.

Future tests must prove that same-name nesting preserves the outer frame.

Retry is permitted only after:

- a DDL/post-check failure completed both rollback-to and cleanup release successfully; or
- the caller completed a whole-transaction rollback after an uncertain savepoint failure.

Every retry starts a new state classification. It never resumes at a later statement.

Schema drift discovered after the caller transaction starts is classified inside that transaction and fails closed before helper DDL.

The helper may not claim caller-owned transaction preservation by opening and releasing an outermost savepoint. Its active-transaction precondition is mandatory.

## 16. Init, migrate, checker, and manifest ownership

Only these future implementation files are pre-authorized for a separately approved VENDOR-ID-002 implementation gate:

```text
app.py
tools/check_vendor_organization_schema.py
tools/capture_schema_manifest.py
tests/smoke_test.py
```

No other implementation file is pre-authorized.

`app.py` owns:

- `VENDOR_ORGANIZATION_SCHEMA_STATEMENTS`;
- `VendorOrganizationSchemaMigrationError`;
- `ensure_vendor_organization_schema`;
- the exact signature, two success returns, 14 stable error codes, message, and no-chaining contract;
- the fixed Section 14 metadata SQL and immutable parameter inventories;
- the four literal Section 15 post-create emptiness SQL constants;
- the exact SQL normalizer and legacy-parent declaration parser;
- exact integration into `init_schema()` and `migrate_schema()`;
- caller-owned transaction setup and resolution; and
- no runtime row consumer.

`tools/check_vendor_organization_schema.py` owns read-only schema validation and self-test.

Its future checker must validate:

- static source tuple exactness;
- statement count and exact order;
- no dynamic SQL or `executescript()`;
- exact fixed metadata query strings, tuple shapes, parameter sources, and result ordering;
- exact eight-query metadata inventory, including the literal `temp.sqlite_schema` projection;
- no identifier, schema, table, index, predicate, or SQL interpolation;
- exact `main`/`temp`/attached topology behavior;
- exact SQL normalization and partial-predicate extraction;
- exact legacy-parent declaration parser and compatible `INTEGER PRIMARY KEY` projection;
- exact helper active-transaction precondition;
- exact helper callable signature and return annotation;
- exact `"created"` and `"all_exact"` returns;
- exact exception type, bounded code set, stable message, attributes, precedence, and no cause/context;
- exact savepoint name and failure cleanup;
- absence of helper commit and connection-wide rollback;
- exact table inventory;
- exact column names, order, declared types, nullability, defaults, and primary keys;
- exact `STRICT` flags;
- exact CHECK expressions, including full UUID position patterns;
- exact foreign-key parents, columns, and actions;
- exact explicit index inventory;
- exact four internal PK autoindexes and `NULL` internal SQL handling;
- arbitrary-name and reserved-name TEMP triggers attached to every required main table;
- exact index columns, uniqueness, and partial predicates;
- the absence of triggers, views, generated columns, arbitrary-name indexes/triggers attached to required tables, and every other extra vendor-owned object;
- `all_absent`, `all_exact`, partial, drifted, extra, wrong-type, parent-incompatible, unsupported-topology, and unreadable classifications;
- no table rows in implementation acceptance;
- exact no-op behavior for a later populated `all_exact` schema without row-content inspection;
- post-affinity stored-positive-integer semantics without impossible pre-affinity DDL claims;
- absence of any runtime pre-bind integer validator or synthetic consumer proof;
- exact four literal post-create emptiness SQL constants, execution order, result shape/type/value, and exclusion from `all_exact`;
- exact 29-code-point blank set on display name and every provenance text field;
- no legacy table or row mutation;
- no global foreign-key PRAGMA change;
- no ID generator or runtime authority consumer; and
- fail-closed negative source variants for every allowance.

`tools/capture_schema_manifest.py` owns:

- including the exact four tables;
- including the exact 15 indexes and their canonical metadata;
- adding row-count inventory for only the four new tables;
- preserving every existing manifest field and serializer contract;
- no artifact write during normal app runtime; and
- no discovery, mapping, or authority inference.

`tests/smoke_test.py` owns disposable validation only.

It must not use DEV or Production persistent data.

No existing AUTH-ID checker, serializer, vendor runtime service, PostgreSQL bootstrap, dependency file, or migration framework is pre-authorized.

## 17. Existing-data and runtime-authority boundary

The physical-schema implementation must create empty tables only.

It must create:

```text
vendor organization rows: 0
vendor membership rows: 0
vendor-site assignment rows: 0
sheet-vendor binding rows: 0
```

It must not:

- add `vendor_id` to `vendor_accounts`;
- add `vendor_id` to `vendor_contacts`;
- add `vendor_id` to `vendor_work_entries`;
- add `vendor_id` to `tasks`;
- add `vendor_id` to `sheets`;
- add any relationship key to a legacy table;
- scan vendor labels or accounts;
- normalize names;
- infer duplicates;
- create a mapping;
- create a row;
- rewrite a row;
- backfill;
- reconcile;
- merge;
- create an owner;
- assign a site;
- bind a sheet;
- change login or session behavior;
- add CRUD;
- add an API, template, UI, import, export, or report;
- add dual-read, dual-write, shadow-read, or shadow-authority behavior;
- switch authority;
- connect to PostgreSQL; or
- access DEV or Production databases during implementation validation.

Current `vendor_name`, `vendor_accounts`, task, sheet, contact, work-entry, authentication, trusted-target, and workflow behavior remains unchanged.

Schema presence does not mean the vendor organization feature is active.

## 18. Rejected alternatives

The following are rejected:

- integer vendor-domain IDs;
- generic unconstrained `TEXT` IDs;
- prefixed, name-derived, account-derived, site-derived, sheet-derived, or authority-derived IDs;
- caller-supplied ID authority;
- reuse of the AUTH-ID semantic generator API;
- composite primary keys for historical relationships;
- a unique display name;
- a normalized-name column or unique normalized-name index;
- in-place revoked membership reactivation;
- in-place inactive assignment or binding reactivation;
- broad uniqueness across historical rows;
- branching predecessor chains;
- triggers for transition, owner, timestamp, or audit behavior;
- generated columns for normalization or cross-row authority;
- modifying a legacy table solely to support a composite foreign key;
- treating foreign-key metadata as proof of Production enforcement;
- a global `PRAGMA foreign_keys` change;
- `executescript()` inside the vendor schema helper;
- helper-level `commit()` or connection-wide `rollback()`;
- an outermost helper savepoint that is released as an implicit commit;
- `CREATE IF NOT EXISTS` used to hide drift;
- automatic repair, drop, recreate, alter, rename, or reconstruction;
- partial schema completion;
- existing-row migration or backfill in the schema slice;
- authority switching in the schema slice;
- an audit/event subsystem in this slice;
- a fifth vendor table, alias table, mapping table, compatibility view, or trigger;
- fuzzy vendor-object ownership based only on the word `vendor`; and
- PostgreSQL parity or implementation claims.

## 19. Future implementation acceptance matrix

The separately approved implementation gate must prove every row below.

| Area | Required positive evidence | Required rejection/no-change evidence |
|---|---|---|
| Compile | Full approved `compileall` succeeds in an isolated temporary bytecode root | No repository bytecode or temp residue |
| Dedicated checker | Normal mode and reviewed self-test pass | Negative source/schema variants fail closed |
| Manifest | Existing serializer self-test plus exact new tables/indexes/row counts pass | No existing manifest field or ordering regression |
| Fresh bootstrap | Exact four tables, 15 explicit indexes, and four PK autoindexes created/proven in order | No fifth table, sixteenth explicit index, extra internal index, trigger, view, or row |
| Existing legacy fixture | Migration adds only exact empty objects | Legacy schema and rows remain byte- or row-equivalent |
| Exact rerun | `all_exact` is a no-op | No statement, savepoint, timestamp, or row change |
| State classification | `all_absent` and empty or populated `all_exact` resolve exactly | Every partial, drifted, extra, wrong-type, parent-incompatible, unsupported-topology, and unreadable state fails closed |
| Owned attachment by table | Exact 15 explicit and four PK indexes are accepted | For each of the four tables, add separately an arbitrary-name UNIQUE index, non-unique index, and trigger; all 12 fixtures classify `extra_owned_object` |
| TEMP trigger coverage | Empty/harmless TEMP schema passes and never satisfies a requirement | For each main vendor table, arbitrary-name and reserved-name TEMP trigger fixtures classify `extra_owned_object` or the higher-precedence frozen reserved-name failure |
| Internal autoindexes | Four exact PK autoindexes have null SQL and exact index metadata | Missing, renamed, extra, non-null-SQL, wrong-origin, wrong-column, expression, collation, direction, or partial internal index fails |
| Legacy parent projection | Exact current `main.vendor_accounts(id)`, `main.sites(id)`, and `main.sheets(id)` with `notnull = 0` pass without row reads | For each parent, missing table, view/wrong type, missing/wrong `id`, non-`INTEGER`, explicit `NOT NULL`, non-PK, composite PK, unique-index substitute, custom collation, hidden key, temp-only, and attached-only variants fail before savepoint |
| Database topology | `main` plus optional harmless `temp` passes | Attached database and temp required/reserved shadow fail before savepoint |
| Fixed metadata SQL | All eight frozen queries, including both schema projections, return exact tuple shapes/order from immutable internal parameters | Missing TEMP projection, dynamic PRAGMA, unqualified schema read, identifier interpolation, caller SQL/identifier, missing/extra/ill-typed tuple element, duplicate, or unstable ordering fails |
| SQL normalization | Canonical stored table/index SQL and exact partial suffixes pass | Case, internal whitespace, quoting, comment, second semicolon, predicate order, redundant parentheses, or logically equivalent but noncanonical SQL fails |
| Table statement injection | Each of four table statements can fail under controlled injection | Savepoint cleanup leaves no partial object |
| Index statement injection | Each of 15 index statements can fail under controlled injection | Savepoint cleanup leaves no partial object |
| Post-create emptiness SQL | Four exact main-qualified literal queries each return one `row_count` integer equal to zero after schema recheck and before release | For each query, exception, no/multiple rows, wrong column shape/name, bool/non-int, negative, and nonzero controlled results map through cleanup to `ddl_or_postcheck_failed`; `all_exact` executes zero emptiness queries |
| Helper callable | Exact positional-only `conn: sqlite3.Connection` signature resolves and returns `str`; exception initializer has exact positional-only `code: str` and `None` return | Extra/default/keyword-only/variadic parameter, unknown code, or different annotation/return fails |
| Helper success values | Creation returns exactly `"created"`; exact no-op returns exactly `"all_exact"` | `None`, bool, object, count, alternate string, detail payload, no-op DDL, or savepoint fails |
| Helper bounded errors | Every frozen condition maps to its exact stable code/message with `__cause__` and `__context__` both `None` | Raw SQLite message, path, connection, SQL, object name, injected token, extra attribute, wrong precedence, or retained chaining fails |
| Savepoint creation failure | No DDL executes | Caller can roll back without vendor residue |
| Rollback-to failure | Internal failure is surfaced | Caller whole rollback removes all vendor objects |
| Cleanup release failure | Internal failure is surfaced | Caller whole rollback removes all vendor objects |
| Success release failure | Success is not reported | Caller whole rollback removes all vendor objects |
| Same-name savepoint nesting | Helper's innermost frame is isolated | Caller outer same-name frame remains intact |
| Caller transaction | Earlier caller work remains pending after helper success | Helper never commits or connection-wide rolls back it |
| Caller rollback | Explicit caller rollback removes all new objects | No object survives |
| Caller commit | Explicit caller commit preserves exact schema | No extra object or row appears |
| UUID acceptance | Canonical lowercase RFC 9562 UUIDv4 values pass every ID domain | Uppercase, compact, braced, URN, wrong hyphens, version, variant, non-hex, nil, prefix/suffix, numeric, and coerced forms fail |
| Display name | 1–100 characters with at least one non-whitespace character passes | Empty, overlong, and exact frozen whitespace-only cases fail |
| Provenance blank set | Ordinary nonblank and nonblank text surrounded by frozen whitespace pass without storage normalization | For every actor-ID, reason, source, and correlation column, ASCII-space-only, tab-only, LF-only, NBSP-only, and mixed 29-code-point whitespace-only values fail |
| Role/status | Every closed value passes in its table | Unknown, differently cased, empty, null, and wrong-type values fail |
| Stored positive integer | SQL integer `1` and a controlled losslessly coercible text `"1"` both store as INTEGER and satisfy only the physical type/value boundary | Zero, negative, null, and values SQLite cannot losslessly store as INTEGER fail physically |
| Parent row existence | Valid stored positive integer parent IDs pass with fixture parents | Missing and wrong parents fail when disposable FK enforcement is explicitly enabled |
| Foreign-key metadata | Every child/parent/action tuple is exact | Cascade, set-null, wrong parent, wrong action, or missing metadata fails |
| Membership uniqueness | Multiple historical revoked episodes pass | A second active account membership or second pending/active pair fails |
| Assignment uniqueness | Multiple inactive episodes pass | A second active organization/site pair fails |
| Binding uniqueness | Multiple inactive episodes pass | A second active organization/sheet pair fails |
| Linear predecessor | One direct successor passes | Second successor, self-reference, malformed predecessor, and missing predecessor fail where enforceable |
| Runtime-only constraints | Future test fixtures can identify same-pair and transition requirements | DDL presence is not reported as enforcement |
| Table emptiness | All four row counts are zero after bootstrap/migrate | Any created or copied row fails acceptance |
| Legacy preservation | Existing legacy tables and rows are unchanged | Any added legacy column/index or row rewrite fails |
| Canonical DB no-touch | `site.db` and all sidecars are byte/size/mtime equivalent before and after disposable validation | Canonical DB open or sidecar change fails |
| Backend boundary | PostgreSQL attempt count is zero | Any PostgreSQL URL use or connect attempt fails |
| Environment boundary | DEV and Production persistent DB attempts are zero | Any persistent environment access fails |
| Consumer boundary | No runtime reader, writer, pre-bind type validator, API, session, template, report, or authority path references the new schema | Any synthetic runtime validation, claimed proof of future `type(value) is int` behavior, or other consumer wiring fails this slice |

The implementation gate must include focused disposable schema smoke, fresh bootstrap, migration on an existing legacy fixture, exact no-op rerun, and failure injection for every DDL and savepoint stage.

No test may treat schema creation as:

- evidence of real vendor rows;
- evidence of data quality;
- evidence of organization membership;
- evidence of relationship validity;
- evidence of authorization;
- evidence of migration readiness; or
- permission to backfill or switch authority.

## 20. Status and deferred owners

The frozen status is:

```text
VENDOR-ID-002 DOCS-ONLY PHYSICAL SQLITE DDL / MIGRATION FREEZE: COMPLETE
EXACT FOUR-TABLE PROJECTION: FROZEN
UUID / FK / CHECK / PARTIAL-INDEX CONTRACT: FROZEN
MIGRATION / SAVEPOINT CONTRACT: FROZEN
PHYSICAL SCHEMA IMPLEMENTATION: NOT STARTED
BACKFILL / AUTHORITY SWITCH: NOT AUTHORIZED
```

Deferred ownership is:

| Decision or work | Owner after this freeze | Current authorization |
|---|---|---|
| Implement exact SQLite tables/helper | Future separately approved VENDOR-ID-002 implementation gate | Not started |
| Implement dedicated checker | Future separately approved VENDOR-ID-002 implementation gate | Not started |
| Extend schema manifest | Future separately approved VENDOR-ID-002 implementation gate | Not started |
| Add disposable acceptance smoke | Future separately approved VENDOR-ID-002 implementation gate | Not started |
| Vendor-specific ID generator/validator | Product Owner-named future creation/mutation slice | Not authorized |
| Pre-bind application integer-type validation (`type(value) is int`) | Product Owner-named future vendor creation/mutation consumer | Deferred; not implemented or proven by VENDOR-ID-002 |
| Display-name normalization and duplicate review | VENDOR-ID-TBD | Not authorized |
| Read-only vendor discovery | VENDOR-ID-003 | Not started |
| Controlled backfill | VENDOR-ID-004 | Not authorized |
| Organization lifecycle mutation | VENDOR-ID-TBD | Not authorized |
| Membership and owner transfer mutation | VENDOR-ID-TBD | Not authorized |
| Assignment and binding mutation | VENDOR-ID-TBD | Not authorized |
| Audit/event ledger | VENDOR-ID-TBD | Not authorized |
| Runtime authority switch and consumer wiring | VENDOR-ID-TBD | Not authorized |
| PostgreSQL projection or migration | Separately named future owner | Not authorized |

No deferred owner may infer authorization from this document.

The next permissible step is final diff review of this docs-only freeze.
