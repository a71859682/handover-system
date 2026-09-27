"""Internal SQLite roster storage. No paths, connections, app imports or grants.

The caller enables foreign_keys BEFORE BEGIN, owns the transaction, explicitly
initializes the supplemental schema, and commits/rolls back. Every mutation uses
a nested savepoint; even a successful call never commits the caller's transaction.
"""

from __future__ import annotations

from contextlib import contextmanager
import json
import re
import sqlite3
import uuid


class RosterError(ValueError):
    """Rejected input, connection, or schema; no service changes are retained."""


class RosterConflict(RosterError):
    """Existing identity or assignment disagrees with the proposed batch."""


_SCHEMA = {
    "vendor_profiles": """CREATE TABLE vendor_profiles (
        vendor_id TEXT NOT NULL PRIMARY KEY
            REFERENCES vendor_organizations(vendor_id) ON DELETE RESTRICT,
        tax_id TEXT NOT NULL UNIQUE
            CHECK(length(tax_id) = 8 AND tax_id NOT GLOB '*[^0-9]*'),
        legal_name TEXT NOT NULL CHECK(length(trim(legal_name)) > 0),
        display_name TEXT NOT NULL CHECK(length(trim(display_name)) BETWEEN 1 AND 100),
        aliases_json TEXT NOT NULL
            CHECK(json_valid(aliases_json) AND json_type(aliases_json) = 'array'),
        source_json TEXT NOT NULL
            CHECK(json_valid(source_json) AND json_type(source_json) = 'object')
    ) STRICT""",
    "task_vendor_assignments": """CREATE TABLE task_vendor_assignments (
        task_id INTEGER NOT NULL PRIMARY KEY REFERENCES tasks(id) ON DELETE RESTRICT,
        vendor_id TEXT NOT NULL REFERENCES vendor_profiles(vendor_id) ON DELETE RESTRICT,
        matched_name TEXT NOT NULL CHECK(length(trim(matched_name)) > 0),
        match_basis TEXT NOT NULL CHECK(match_basis = 'explicit_name_exact_trim'),
        source_json TEXT NOT NULL
            CHECK(json_valid(source_json) AND json_type(source_json) = 'object')
    ) STRICT""",
}


def _connection(conn: sqlite3.Connection, *, writing: bool = False) -> None:
    if not isinstance(conn, sqlite3.Connection):
        raise RosterError("sqlite_connection_required")
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise RosterError("foreign_keys_must_be_enabled_before_transaction")
    if writing and not conn.in_transaction:
        raise RosterError("caller_transaction_required")


@contextmanager
def _savepoint(conn):
    _connection(conn, writing=True)
    name = "vr1_" + uuid.uuid4().hex
    conn.execute(f"SAVEPOINT {name}")
    try:
        yield
        conn.execute(f"RELEASE SAVEPOINT {name}")
    except BaseException:
        # Never conn.rollback(): unrelated work belongs to the caller.
        conn.execute(f"ROLLBACK TO SAVEPOINT {name}")
        conn.execute(f"RELEASE SAVEPOINT {name}")
        raise


def _sql_key(sql):
    return " ".join(sql.split()).rstrip(";")


def _check_schema(conn, *, allow_absent=False):
    # Triggers could alter protected rows or roll back the caller's transaction.
    for schema in ("main", "temp"):
        trigger = conn.execute(f"""SELECT name FROM {schema}.sqlite_schema
            WHERE type = 'trigger' AND tbl_name IN
            ('vendor_profiles', 'task_vendor_assignments', 'vendor_organizations')""").fetchone()
        if trigger is not None:
            raise RosterError(f"unexpected_write_trigger:{trigger[0]}")
    for name, sql in _SCHEMA.items():
        row = conn.execute(
            "SELECT type, sql FROM main.sqlite_schema WHERE name = ?", (name,)
        ).fetchone()
        if row is None and allow_absent:
            continue
        if row is None or row[0] != "table" or _sql_key(row[1]) != _sql_key(sql):
            raise RosterError(f"supplemental_schema_mismatch:{name}")


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Create only the two supplemental tables, inside the caller's transaction.

    Existing core tables must already exist; the caller retains responsibility
    for their existing exact guard. Incompatible supplemental tables are rejected.
    """
    with _savepoint(conn):
        for table, columns in (
            ("vendor_organizations", {"vendor_id", "display_name", "organization_status"}),
            ("tasks", {"id", "vendor", "sheet_id"}),
        ):
            actual = {row[1] for row in conn.execute(f"PRAGMA main.table_info({table})")}
            if not columns <= actual:
                raise RosterError(f"missing_core_schema:{table}")
        _check_schema(conn, allow_absent=True)
        for name, sql in _SCHEMA.items():
            if conn.execute("SELECT 1 FROM main.sqlite_schema WHERE name = ?", (name,)).fetchone() is None:
                conn.execute(sql)
        _check_schema(conn)


def _json(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise RosterError("invalid_json_provenance") from exc


def _label(value, field, *, limit=None):
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise RosterError(f"invalid_{field}")
    if value != value.strip() or (limit is not None and len(value) > limit):
        raise RosterError(f"invalid_{field}")
    return value


def _entry(entry):
    keys = {"tax_id", "legal_name", "display_name", "aliases", "source"}
    if not isinstance(entry, dict) or set(entry) != keys:
        raise RosterError("invalid_roster_entry_fields")
    tax_id = entry["tax_id"]
    if not isinstance(tax_id, str) or re.fullmatch(r"[0-9]{8}", tax_id) is None:
        raise RosterError("tax_id_requires_eight_ascii_digits_as_text")
    legal_name = _label(entry["legal_name"], "legal_name")
    display_name = _label(entry["display_name"], "display_name", limit=100)
    aliases = entry["aliases"]
    if not isinstance(aliases, list):
        raise RosterError("aliases_require_list")
    for alias in aliases:
        _label(alias, "alias")
    source = entry["source"]
    if not isinstance(source, dict):
        raise RosterError("source_requires_object")
    for field in ("document", "version", "sheet", "source_original_name"):
        _label(source.get(field), f"source_{field}")
    if type(source.get("row")) is not int or source["row"] < 1:
        raise RosterError("source_row_requires_positive_integer")
    return (tax_id, legal_name, display_name, _json(aliases), _json(source))


def _task_ids(task_ids):
    if not isinstance(task_ids, (list, tuple)):
        raise RosterError("task_ids_require_list_or_tuple")
    if any(type(value) is not int or value <= 0 for value in task_ids):
        raise RosterError("task_ids_require_positive_integers")
    if len(task_ids) != len(set(task_ids)):
        raise RosterError("duplicate_task_id")
    return tuple(task_ids)


def _profiles(conn):
    rows = conn.execute("""SELECT p.vendor_id, p.tax_id, p.legal_name,
        p.display_name, p.aliases_json, p.source_json, o.display_name,
        o.organization_status FROM main.vendor_profiles AS p
        LEFT JOIN main.vendor_organizations AS o ON o.vendor_id = p.vendor_id
        ORDER BY p.tax_id""").fetchall()
    profiles = {}
    for row in rows:
        vendor_id, tax_id, legal, display, aliases, source, org_display, status = row
        try:
            parsed_id = uuid.UUID(vendor_id)
            if parsed_id.version != 4 or str(parsed_id) != vendor_id:
                raise ValueError("not canonical uuid4")
            entry = _entry({"tax_id": tax_id, "legal_name": legal, "display_name": display,
                            "aliases": json.loads(aliases), "source": json.loads(source)})
        except (ValueError, TypeError, AttributeError) as exc:
            raise RosterConflict(f"invalid_existing_profile:{tax_id}") from exc
        if org_display != display or status not in {"disabled", "active", "retired"}:
            raise RosterConflict(f"profile_organization_conflict:{tax_id}")
        profiles[tax_id] = (vendor_id, entry)
    return profiles


def apply_roster(conn: sqlite3.Connection, entries: list[dict], *, task_ids=()) -> dict:
    """Import a whole batch and match explicitly selected tasks atomically.

    Matching includes ALL persisted profiles plus this batch, so a partial import
    cannot conceal another candidate. Empty task_ids imports only the roster.
    Unassigned unmatched/ambiguous tasks receive no assignment. An existing
    assignment must remain the unique candidate; otherwise the entire batch is
    rejected. No existing row is updated, including organization status.
    """
    if not isinstance(entries, list):
        raise RosterError("roster_requires_list")
    normalized = [_entry(entry) for entry in entries]
    if len({entry[0] for entry in normalized}) != len(normalized):
        raise RosterError("duplicate_tax_id")
    ids = _task_ids(task_ids)
    with _savepoint(conn):
        _check_schema(conn)
        profiles = _profiles(conn)
        new_profiles = []
        vendor_ids = {}
        for entry in normalized:
            tax_id = entry[0]
            if tax_id in profiles:
                vendor_id, previous = profiles[tax_id]
                if previous != entry:
                    raise RosterConflict(f"tax_id_content_conflict:{tax_id}")
            else:
                vendor_id = str(uuid.uuid4())
                profiles[tax_id] = (vendor_id, entry)
                new_profiles.append((vendor_id, entry))
            vendor_ids[tax_id] = vendor_id

        candidates = {}
        for vendor_id, entry in profiles.values():
            for name in {entry[1], entry[2], *json.loads(entry[3])}:
                candidates.setdefault(name.strip(), set()).add(vendor_id)
        for table in _SCHEMA:
            if conn.execute(f"PRAGMA main.foreign_key_check({table})").fetchone() is not None:
                raise RosterConflict(f"invalid_existing_relationship:{table}")

        outcomes, assignments = [], []
        by_id = {vendor_id: entry for vendor_id, entry in profiles.values()}
        for task_id in ids:
            task = conn.execute("SELECT vendor FROM main.tasks WHERE id = ?", (task_id,)).fetchone()
            if task is None:
                raise RosterError(f"task_not_found:{task_id}")
            name = task[0].strip() if isinstance(task[0], str) else ""
            matches = sorted(candidates.get(name, ()))
            old = conn.execute("SELECT vendor_id FROM main.task_vendor_assignments WHERE task_id = ?", (task_id,)).fetchone()
            old_id = old[0] if old is not None else None
            if old_id is not None and matches != [old_id]:
                raise RosterConflict(f"task_assignment_conflict:{task_id}")
            status = "unmatched" if not matches else "ambiguous"
            assigned_id = old_id
            if len(matches) == 1:
                assigned_id = matches[0]
                status = "already_assigned" if old_id else "matched"
                if old_id is None:
                    assignments.append((task_id, assigned_id, name, "explicit_name_exact_trim", by_id[assigned_id][4]))
            outcomes.append({"task_id": task_id, "status": status, "vendor_id": assigned_id,
                             "candidate_vendor_ids": matches, "pending": assigned_id is None})

        # All input, existing identity, FK and assignment checks precede writes.
        for vendor_id, entry in new_profiles:
            audit = ("migration", "004F-VR1", "explicit roster import", "vendor_roster_service", vendor_id)
            conn.execute("""INSERT INTO main.vendor_organizations (
                vendor_id, display_name, organization_status,
                created_actor_kind, created_actor_id, created_reason, created_source, created_correlation_id,
                updated_actor_kind, updated_actor_id, updated_reason, updated_source, updated_correlation_id
            ) VALUES (?, ?, 'disabled', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (vendor_id, entry[2], *audit, *audit))
            conn.execute("""INSERT INTO main.vendor_profiles
                (vendor_id, tax_id, legal_name, display_name, aliases_json, source_json)
                VALUES (?, ?, ?, ?, ?, ?)""", (vendor_id, *entry))
        conn.executemany("""INSERT INTO main.task_vendor_assignments
            (task_id, vendor_id, matched_name, match_basis, source_json) VALUES (?, ?, ?, ?, ?)""", assignments)
        return {"vendor_ids": vendor_ids, "created_vendor_ids": [row[0] for row in new_profiles],
                "assignments_created": [row[0] for row in assignments], "tasks": outcomes}


def list_profiles(conn: sqlite3.Connection) -> list[dict]:
    """Read persisted profiles, verifying their organization correspondence."""
    _connection(conn)
    _check_schema(conn)
    return [{"vendor_id": vendor_id, "tax_id": entry[0], "legal_name": entry[1],
             "display_name": entry[2], "aliases": json.loads(entry[3]), "source": json.loads(entry[4])}
            for vendor_id, entry in _profiles(conn).values()]


def list_task_assignments(conn: sqlite3.Connection, *, task_ids=None) -> list[dict]:
    """Read actual task IDs, sheet/site context and pending state; grants nothing."""
    _connection(conn)
    _check_schema(conn)
    selected = None if task_ids is None else set(_task_ids(task_ids))
    rows = conn.execute("""SELECT t.id, t.sheet_id, s.site_id, t.name, t.vendor,
        a.vendor_id, a.matched_name, a.match_basis, a.source_json
        FROM main.tasks AS t LEFT JOIN main.sheets AS s ON s.id = t.sheet_id
        LEFT JOIN main.task_vendor_assignments AS a ON a.task_id = t.id ORDER BY t.id""")
    result = []
    for row in rows:
        if selected is None or row[0] in selected:
            result.append(dict(zip(("task_id", "sheet_id", "site_id", "task_name", "vendor_text",
                                    "vendor_id", "matched_name", "match_basis", "source"), row)))
            result[-1]["source"] = json.loads(row[8]) if row[8] is not None else None
            result[-1]["pending"] = row[5] is None
    if selected is not None and len(result) != len(selected):
        raise RosterError("task_not_found")
    return result
