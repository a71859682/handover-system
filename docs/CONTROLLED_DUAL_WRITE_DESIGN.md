# Controlled Dual Write Design

This document defines the controlled rollout plan for future dual write behavior.

Current boundary:

- Do not enable `USE_SQLALCHEMY_WRITES=true`
- Do not enable real dual write in this phase
- Do not switch PostgreSQL to primary
- Do not remove SQLite
- Do not change current production write results

## Goal

The goal of controlled dual write is to add PostgreSQL as a mirrored write target in a staged, reversible way while SQLite remains the only formal source of truth during rollout.

## Dual Write Enablement Conditions

Dual write must not be enabled until all of the following are true:

- `USE_SQLALCHEMY_WRITES=false`
- `DUAL_WRITE_DRY_RUN` has been stable in staging and logs are visible
- `python tools/check_postgres_runtime_health.py` returns `PASS`
- rollback steps have been tested and documented
- SQLite remains the only formal production write source
- read-path validation between SQLite and PostgreSQL has been completed

## Rollout Order

Recommended controlled enablement order:

1. `meta` / settings
2. `sheets`
3. `users`
4. `progress`
5. `unit_extra` / `extra_fields` / `unit_extra_values`

Reasoning:

- `meta` has low write frequency and simple keys
- `sheets` has create behavior but limited runtime frequency
- `users` is still manageable but includes credential-sensitive data
- `progress` has the highest operational write frequency
- `unit_extra` and related tables have the broadest branching and relationship surface

## Per-Table Risk Analysis

### `meta`

- Write frequency:
  low
- Foreign keys:
  no
- Rollback difficulty:
  low
- Transaction need:
  usually low, but still preferable inside request transaction scope
- Partial failure tolerance:
  SQLite success with PostgreSQL failure can be tolerated temporarily if logged and reconciled
- Notes:
  best first candidate for controlled dual write

### `sheets`

- Write frequency:
  low
- Foreign keys:
  yes, indirectly through dependent `tasks`, `floors`, `extra_fields`, `units`, `progress`
- Rollback difficulty:
  medium
- Transaction need:
  high for create/delete flows
- Partial failure tolerance:
  SQLite success with PostgreSQL failure should be treated as degraded and require follow-up
- Notes:
  sheet create paths must preserve generated ids and dependent setup order

### `users`

- Write frequency:
  low to medium
- Foreign keys:
  limited direct relational impact
- Rollback difficulty:
  medium
- Transaction need:
  medium
- Partial failure tolerance:
  SQLite success with PostgreSQL failure may be tolerated briefly, but must be logged because admin and audit parity matters
- Notes:
  password hash and role fields must stay identical

### `progress`

- Write frequency:
  high
- Foreign keys:
  yes, to `units` and `tasks`
- Rollback difficulty:
  medium
- Transaction need:
  high
- Partial failure tolerance:
  SQLite success with PostgreSQL failure is risky because reads may already come from PostgreSQL
- Notes:
  this path needs the strongest operational monitoring and replay strategy

### `unit_extra`

- Write frequency:
  medium
- Foreign keys:
  yes
- Rollback difficulty:
  medium
- Transaction need:
  high
- Partial failure tolerance:
  only with explicit degraded-mode logging
- Notes:
  built-in handover state must stay aligned with sheet reads

### `extra_fields`

- Write frequency:
  low
- Foreign keys:
  yes, to `sheets`
- Rollback difficulty:
  medium
- Transaction need:
  high when created together with sheets
- Partial failure tolerance:
  low if dependent values are also being created
- Notes:
  usually safer to dual write together with the parent sheet flow

### `unit_extra_values`

- Write frequency:
  medium
- Foreign keys:
  yes, to `units` and `extra_fields`
- Rollback difficulty:
  medium to high
- Transaction need:
  high
- Partial failure tolerance:
  low in active read-from-PostgreSQL environments
- Notes:
  requires matching upsert semantics and careful field-key resolution

## Feature Flag Design

Recommended future flags:

- `DUAL_WRITE_ENABLED=false`
- `DUAL_WRITE_TABLES=meta,sheets`
- `DUAL_WRITE_STRICT=false`

Suggested meanings:

- `DUAL_WRITE_ENABLED`
  global switch for mirrored PostgreSQL write attempts
- `DUAL_WRITE_TABLES`
  allowlist of tables or write groups currently enabled for dual write
- `DUAL_WRITE_STRICT`
  when `true`, PostgreSQL mirror failure should fail the request instead of only logging degradation

Suggested rollout behavior:

- Start with `DUAL_WRITE_ENABLED=false`
- Enable only one small allowlist group at a time
- Keep `DUAL_WRITE_STRICT=false` in early rollout
- Consider `DUAL_WRITE_STRICT=true` only after sustained parity and operational confidence

## Logging Design

Every real dual write attempt should log:

- `operation`
- `table`
- `key`
- `sqlite_result`
- `postgres_result`
- `error`
- `timestamp`

Recommended log style:

```text
CONTROLLED_DUAL_WRITE operation=<operation> table=<table> key=<key> sqlite_result=<result> postgres_result=<result> error=<error> timestamp=<timestamp>
```

Additional guidance:

- keep one structured line per write attempt
- never log secrets or raw credentials
- log degraded writes clearly when SQLite succeeds and PostgreSQL fails
- ensure logs are visible in Render Logs and local server stderr/stdout

## Failure Handling Model

Recommended early rollout policy:

- SQLite remains authoritative
- SQLite write executes first
- PostgreSQL mirror executes second
- if PostgreSQL mirror fails:
  log the failure with enough context to replay or repair
- only move to strict failure once parity and replay confidence are proven

Questions to answer before implementation:

- should failed PostgreSQL mirror writes go to a retry queue
- should there be a repair tool for specific keys or tables
- how should repeated mirror failures trigger alerts

## Rollback Design

Rollback must be simple and immediate:

1. Set `DUAL_WRITE_ENABLED=false`
2. Keep `USE_SQLALCHEMY_WRITES=false`
3. Confirm SQLite remains the only formal write source
4. Continue reads according to current read flags
5. Review logs for any partial PostgreSQL mirror failures
6. Re-run health and consistency checks before any re-enable

Rollback requirement:

- disabling dual write must not require schema reversal or route changes

## Validation Flow

Run the following before and during any controlled dual write rollout:

- `python tools/check_runtime_flags.py`
- `python tools/check_dual_write_dry_run.py`
- `python tools/check_postgres_runtime_health.py`
- `python tools/check_sqlite_postgres_consistency.py`
- `python tests/smoke_test.py`
- manual verification on settings, users, sheets, progress, and reports

Operational validation checklist:

- confirm `USE_SQLALCHEMY_WRITES=false` before rollout
- confirm PostgreSQL runtime health is `PASS`
- confirm dry-run logs are visible in Render
- enable one write group only
- manually test affected flows
- inspect logs for SQLite success / PostgreSQL mirror outcome
- verify data parity after each rollout step

## Out Of Scope For This Phase

- enabling actual PostgreSQL writes
- changing current write authority away from SQLite
- changing routes or user-facing workflow
- switching PostgreSQL to primary
- deleting or decommissioning SQLite
