# Stage 3C Users Create Dual-Write Status

## Final Status

Stage 3C is complete for `users create` controlled dual-write verification.

Verified outcomes:

- Persistent SQLite runtime path is `/var/data/site.db`
- `persistence_status: ok`
- `users create` controlled dual-write wiring is verified
- Render dry-run create verification passed
- Controlled real secondary create succeeded
- PostgreSQL `users_id_seq` was repaired and verified healthy
- SQLite next `users.id` and PostgreSQL next insert id are aligned at `6`
- Users create readiness is currently `PASS`
- `tests/smoke_test.py` passed
- `python -m compileall tools tests` passed

## Final Runtime Flags

Current expected runtime flags:

```text
DUAL_WRITE_ENABLED=true
DUAL_WRITE_DRY_RUN=false
DUAL_WRITE_STRICT=false
USE_SQLALCHEMY_WRITES=false
DUAL_WRITE_TABLES=meta,sheets,extra_fields,units,floors,tasks,users
APP_DB_PATH=/var/data/site.db
```

## Persistent SQLite Runtime Path

Current expected persistent SQLite runtime path:

```text
APP_DB_PATH=/var/data/site.db
persistence_status: ok
```

## Users Create Verification Result

Controlled real secondary create was verified with a single bounded production test.

Verified result:

```text
SQLite id=5 username='dw_test_create_real_20260628'
PostgreSQL id=5 username='dw_test_create_real_20260628'
display_name / role / created_at aligned
postgres_result=success
```

Current ID allocation health:

```text
SQLite next_sqlite_user_id: 6
PostgreSQL users_id_seq next_insert_id: 6
PostgreSQL max_user_id: 5
collision: false
```

Current readiness state:

```text
PASS users create readiness check passed.
```

## PostgreSQL Sequence Repair Result

PostgreSQL `users_id_seq` required post-real-create stabilization because the sequence lagged behind `MAX(users.id)`.

Repair action:

```sql
SELECT setval('public.users_id_seq', 5, true);
```

Verified effect:

```text
last_value: 5
next_insert_id: 6
status: ok
```

## Stable Verification Commands

Use these commands for the current Stage 3C stability check:

```bash
python tools/check_sqlite_runtime_persistence.py
python tools/check_runtime_flags.py
python tools/check_users_create_readiness.py --username dw_test_create_stability_probe_20260628
python tools/check_users_id_allocation.py
python tools/check_postgres_runtime_health.py
python tools/check_controlled_dual_write.py
python tests/smoke_test.py
python -m compileall tools tests
```

## Scope Completed In Stage 3C

Stage 3C completed only the following:

- `users create` controlled dual-write wiring
- Render dry-run create verification
- Persistent disk setup
- SQLite DB path resolution repair
- SQLite `users` sequence bump
- Controlled real secondary create
- PostgreSQL `users_id_seq` repair
- Post-real-create stabilization verification

## Remaining Restrictions

Stage 3C does not authorize expanding scope beyond `users create`.

Do not do the following as part of Stage 3C closeout:

- Do not create more user test accounts
- Do not switch `DUAL_WRITE_STRICT=true`
- Do not switch `USE_SQLALCHEMY_WRITES=true`
- Do not switch the auth read path
- Do not run users backfill
- Do not clean up baseline drift
- Do not implement or validate `delete_user` dual-write
- Do not delete existing test users

## Next-Stage Guardrails

The next phase must not assume Stage 3C covered broader user migration work.

Still out of scope:

- `delete_user`
- auth read-path migration
- `USE_SQLALCHEMY_WRITES=true`
- `DUAL_WRITE_STRICT=true`
- migration or backfill flows
- baseline drift cleanup

If the next phase needs any of the above, open a separate runbook and verification plan first.
