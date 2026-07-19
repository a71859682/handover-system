from __future__ import annotations

import datetime as _datetime
import hashlib as _hashlib
import json as _json
import os as _os
import re as _re
import stat as _stat
import sys as _sys
import tempfile as _tempfile
from pathlib import Path as _Path
from typing import Sequence as _Sequence

_REPOSITORY = _Path(__file__).resolve(strict=True).parents[1]
if str(_REPOSITORY) not in _sys.path:
    _sys.path.insert(0, str(_REPOSITORY))

from services.identity_registry_ids import (
    validate_identity_registry_id as _validate_identity_registry_id,
)

__all__ = (
    "IdentityRegistryDiscoveryError",
    "discover_identity_registry_anomalies",
)

_FORMAT = "auth-id-001h-disposable-registry-discovery"
_TOOL_VERSION = "AUTH_ID_001H_DISPOSABLE_DISCOVERY_V1"
_PUBLIC_MESSAGE = "identity registry discovery failed"
_INPUT_MARKER = "AUTH-ID-001H DISCOVERY INPUT REJECTED\n"
_INCOMPLETE_MARKER = "AUTH-ID-001H DISCOVERY INCOMPLETE\n"
_INTERNAL_MARKER = "AUTH-ID-001H DISCOVERY INTERNAL ERROR\n"
_CAPTURED_AT_RE = _re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
_COMMIT_RE = _re.compile(r"[0-9a-f]{40}")
_DRIVE_PATH_RE = _re.compile(r"[A-Za-z]:[\\/]")
_HEADER_MAGIC = b"SQLite format 3\0"
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_DRIVE_FIXED = 3
_EXPECTED_TABLES = (
    "global_identities",
    "login_identifier_aliases",
    "backend_principal_mappings",
)
_SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")

_SCHEMA_OBJECTS_SQL = """SELECT
    "type",
    "name",
    "tbl_name",
    "sql"
FROM sqlite_schema
ORDER BY
    "type",
    "name",
    "tbl_name",
    ("sql" IS NOT NULL),
    "sql\""""
_TABLE_LIST_SQL = """SELECT
    "schema",
    "name",
    "type",
    "ncol",
    "wr",
    "strict"
FROM pragma_table_list
ORDER BY "schema", "name", "type\""""
_TABLE_XINFO_SQL = """SELECT
    "cid",
    "name",
    "type",
    "notnull",
    "dflt_value",
    "pk",
    "hidden"
FROM pragma_table_xinfo(?)
ORDER BY "cid", "name\""""
_FOREIGN_KEY_LIST_SQL = """SELECT
    "id",
    "seq",
    "table",
    "from",
    "to",
    "on_update",
    "on_delete",
    "match"
FROM pragma_foreign_key_list(?)
ORDER BY "id", "seq", "table", "from", "to", "on_update", "on_delete", "match\""""
_INDEX_LIST_SQL = """SELECT
    "seq",
    "name",
    "unique",
    "origin",
    "partial"
FROM pragma_index_list(?)
ORDER BY "name\""""
_INDEX_XINFO_SQL = """SELECT
    "seqno",
    "cid",
    "name",
    "desc",
    "coll",
    "key"
FROM pragma_index_xinfo(?)
ORDER BY "seqno\""""
_QUERY_ONLY_SET_SQL = "PRAGMA query_only=ON"
_QUERY_ONLY_READ_SQL = "PRAGMA query_only"
_BEGIN_SQL = "BEGIN"
_DATABASE_LIST_SQL = "PRAGMA database_list"
_SCHEMA_VERSION_SQL = "PRAGMA schema_version"
_ROLLBACK_SQL = "ROLLBACK"

_NONCANONICAL_ID_SQL = """SELECT "global_identity_id" FROM "global_identities"
UNION ALL
SELECT "login_identifier_alias_id" FROM "login_identifier_aliases"
UNION ALL
SELECT "global_identity_id" FROM "login_identifier_aliases"
UNION ALL
SELECT "backend_principal_mapping_id" FROM "backend_principal_mappings"
UNION ALL
SELECT "global_identity_id" FROM "backend_principal_mappings\""""
_INVALID_STATUS_SQL = """SELECT
  (SELECT count(*) FROM "global_identities"
   WHERE typeof("registry_status") <> 'text'
      OR "registry_status" NOT IN ('active','disabled'))
 + (SELECT count(*) FROM "login_identifier_aliases"
   WHERE typeof("alias_status") <> 'text'
      OR "alias_status" NOT IN ('active','disabled','superseded'))
 + (SELECT count(*) FROM "backend_principal_mappings"
   WHERE typeof("mapping_status") <> 'text'
      OR "mapping_status" NOT IN ('active','disabled'))"""
_INVALID_BACKEND_KEY_SQL = """SELECT count(*) FROM "backend_principal_mappings"
WHERE typeof("backend_kind") <> 'text'
   OR "backend_kind" NOT IN ('internal','vendor')
   OR typeof("backend_principal_key") <> 'integer'
   OR "backend_principal_key" <= 0"""
_ORPHAN_FK_SQL = """SELECT
  (SELECT count(*) FROM "login_identifier_aliases" AS "a"
   WHERE typeof("a"."global_identity_id") <> 'text'
      OR NOT EXISTS (
        SELECT 1 FROM "global_identities" AS "g"
        WHERE typeof("g"."global_identity_id") = 'text'
          AND "g"."global_identity_id" = "a"."global_identity_id"))
 + (SELECT count(*) FROM "backend_principal_mappings" AS "m"
   WHERE typeof("m"."global_identity_id") <> 'text'
      OR NOT EXISTS (
        SELECT 1 FROM "global_identities" AS "g"
        WHERE typeof("g"."global_identity_id") = 'text'
          AND "g"."global_identity_id" = "m"."global_identity_id"))"""
_NORMALIZED_ALIAS_AMBIGUITY_SQL = """SELECT
  count(*),
  (SELECT count(*) FROM "login_identifier_aliases"
   WHERE "alias_status" = 'active'
     AND (typeof("global_identity_id") <> 'text'
       OR typeof("normalization_algorithm_family") <> 'text'
       OR typeof("normalization_profile") <> 'text'
       OR typeof("unicode_data_version") <> 'text'
       OR typeof("trim_conformance_profile") <> 'text'
       OR typeof("normalized_lookup_key") <> 'text'))
FROM (
  SELECT
    "a"."normalization_algorithm_family",
    "a"."normalization_profile",
    "a"."unicode_data_version",
    "a"."trim_conformance_profile",
    "a"."normalized_lookup_key"
  FROM "login_identifier_aliases" AS "a"
  JOIN "global_identities" AS "g"
    ON "g"."global_identity_id" = "a"."global_identity_id"
  WHERE "a"."alias_status" = 'active'
    AND "a"."normalization_algorithm_family" = 'NFKC_CASEFOLD_V1'
    AND "a"."normalization_profile" = 'NFKC_CASEFOLD_V1_UCD16_0_0'
    AND "a"."unicode_data_version" = '16.0.0'
    AND "a"."trim_conformance_profile" = 'PY3146_UCD16_0_0_STRIP_V1'
    AND "g"."registry_status" = 'active'
    AND EXISTS (
      SELECT 1 FROM "backend_principal_mappings" AS "m"
      WHERE "m"."global_identity_id" = "a"."global_identity_id"
        AND "m"."mapping_status" = 'active')
  GROUP BY
    "a"."normalization_algorithm_family",
    "a"."normalization_profile",
    "a"."unicode_data_version",
    "a"."trim_conformance_profile",
    "a"."normalized_lookup_key"
  HAVING count(DISTINCT "a"."global_identity_id") >= 2
)"""
_ACTIVE_EXACT_ALIAS_COLLISION_SQL = """SELECT
  count(*),
  (SELECT count(*) FROM "login_identifier_aliases"
   WHERE "alias_status" = 'active'
     AND (typeof("global_identity_id") <> 'text'
       OR typeof("raw_alias") <> 'text'
       OR typeof("normalized_lookup_key") <> 'text'
       OR typeof("normalization_algorithm_family") <> 'text'
       OR typeof("normalization_profile") <> 'text'
       OR typeof("unicode_data_version") <> 'text'
       OR typeof("trim_conformance_profile") <> 'text'))
FROM (
  SELECT 1
  FROM "login_identifier_aliases"
  WHERE "alias_status" = 'active'
  GROUP BY
    "global_identity_id",
    "raw_alias",
    "normalized_lookup_key",
    "normalization_algorithm_family",
    "normalization_profile",
    "unicode_data_version",
    "trim_conformance_profile"
  HAVING count(*) >= 2
)"""
_INCONSISTENT_MAPPING_SQL = """SELECT
  count(*),
  (SELECT count(*) FROM "backend_principal_mappings"
   WHERE typeof("backend_kind") <> 'text'
      OR "backend_kind" NOT IN ('internal','vendor')
      OR typeof("backend_principal_key") <> 'integer'
      OR "backend_principal_key" <= 0
      OR typeof("global_identity_id") <> 'text')
FROM (
  SELECT 1
  FROM "backend_principal_mappings"
  WHERE typeof("backend_kind") = 'text'
    AND "backend_kind" IN ('internal','vendor')
    AND typeof("backend_principal_key") = 'integer'
    AND "backend_principal_key" > 0
    AND typeof("global_identity_id") = 'text'
  GROUP BY "backend_kind", "backend_principal_key"
  HAVING count(DISTINCT "global_identity_id") >= 2
)"""
_INCOMPATIBLE_CARDINALITY_SQL = """SELECT
  count(*),
  (SELECT count(*) FROM "backend_principal_mappings"
   WHERE typeof("global_identity_id") <> 'text'
      OR typeof("backend_kind") <> 'text'
      OR "backend_kind" NOT IN ('internal','vendor')
      OR typeof("backend_principal_key") <> 'integer'
      OR "backend_principal_key" <= 0)
FROM (
  SELECT 1
  FROM "backend_principal_mappings"
  WHERE typeof("global_identity_id") = 'text'
    AND typeof("backend_kind") = 'text'
    AND "backend_kind" IN ('internal','vendor')
    AND typeof("backend_principal_key") = 'integer'
    AND "backend_principal_key" > 0
  GROUP BY "global_identity_id", "backend_kind"
  HAVING count(DISTINCT "backend_principal_key") >= 2
)"""

_ROW_QUERIES = (
    ("noncanonical_registry_id", _NONCANONICAL_ID_SQL),
    ("invalid_registry_status", _INVALID_STATUS_SQL),
    ("invalid_backend_principal_key", _INVALID_BACKEND_KEY_SQL),
    ("orphan_fk_relationship", _ORPHAN_FK_SQL),
    ("normalized_alias_ambiguity", _NORMALIZED_ALIAS_AMBIGUITY_SQL),
    ("active_exact_alias_collision", _ACTIVE_EXACT_ALIAS_COLLISION_SQL),
    ("backend_principal_inconsistent_mapping", _INCONSISTENT_MAPPING_SQL),
    ("incompatible_backend_cardinality", _INCOMPATIBLE_CARDINALITY_SQL),
)

_ANOMALY_DISPOSITIONS = (
    ("schema_object_drift", "owner_gate_required"),
    ("noncanonical_registry_id", "fail_closed"),
    ("invalid_registry_status", "fail_closed"),
    ("invalid_provenance", "quarantine_recommended"),
    ("invalid_backend_principal_key", "fail_closed"),
    ("orphan_fk_relationship", "quarantine_recommended"),
    ("normalized_alias_ambiguity", "fail_closed"),
    ("active_exact_alias_collision", "fail_closed"),
    ("backend_principal_inconsistent_mapping", "fail_closed"),
    ("incompatible_backend_cardinality", "fail_closed"),
    ("conflicting_principals_different_identities", "manual_review_required"),
    ("disabled_superseded_relationship_inconsistency", "fail_closed"),
    ("source_principal_missing_inactive_stale", "fail_closed"),
    ("snapshot_concurrency_drift", "owner_gate_required"),
    ("unknown_unclassified_anomaly", "fail_closed"),
)

_EXPECTED_COLUMNS = {
    "global_identities": (
        (0, "global_identity_id", "TEXT", True, None, 1, 0),
        (1, "registry_status", "TEXT", True, "'disabled'", 0, 0),
        (2, "created_at", "TEXT", True, "CURRENT_TIMESTAMP", 0, 0),
        (3, "updated_at", "TEXT", True, "CURRENT_TIMESTAMP", 0, 0),
        (4, "created_provenance", "TEXT", True, None, 0, 0),
        (5, "updated_provenance", "TEXT", True, None, 0, 0),
    ),
    "login_identifier_aliases": (
        (0, "login_identifier_alias_id", "TEXT", True, None, 1, 0),
        (1, "global_identity_id", "TEXT", True, None, 0, 0),
        (2, "raw_alias", "TEXT", True, None, 0, 0),
        (3, "normalized_lookup_key", "TEXT", True, None, 0, 0),
        (4, "normalization_algorithm_family", "TEXT", True, None, 0, 0),
        (5, "normalization_profile", "TEXT", True, None, 0, 0),
        (6, "unicode_data_version", "TEXT", True, None, 0, 0),
        (7, "trim_conformance_profile", "TEXT", True, None, 0, 0),
        (8, "alias_status", "TEXT", True, "'active'", 0, 0),
        (9, "created_at", "TEXT", True, "CURRENT_TIMESTAMP", 0, 0),
        (10, "updated_at", "TEXT", True, "CURRENT_TIMESTAMP", 0, 0),
        (11, "created_provenance", "TEXT", True, None, 0, 0),
        (12, "updated_provenance", "TEXT", True, None, 0, 0),
    ),
    "backend_principal_mappings": (
        (0, "backend_principal_mapping_id", "TEXT", True, None, 1, 0),
        (1, "global_identity_id", "TEXT", True, None, 0, 0),
        (2, "backend_kind", "TEXT", True, None, 0, 0),
        (3, "backend_principal_key", "ANY", True, None, 0, 0),
        (4, "mapping_status", "TEXT", True, "'active'", 0, 0),
        (5, "created_at", "TEXT", True, "CURRENT_TIMESTAMP", 0, 0),
        (6, "updated_at", "TEXT", True, "CURRENT_TIMESTAMP", 0, 0),
        (7, "created_provenance", "TEXT", True, None, 0, 0),
        (8, "updated_provenance", "TEXT", True, None, 0, 0),
    ),
}
_EXPECTED_FOREIGN_KEYS = {
    "global_identities": (),
    "login_identifier_aliases": (
        (
            "global_identity_id",
            "global_identities",
            "global_identity_id",
            "NO ACTION",
            "RESTRICT",
            "NONE",
        ),
    ),
    "backend_principal_mappings": (
        (
            "global_identity_id",
            "global_identities",
            "global_identity_id",
            "NO ACTION",
            "RESTRICT",
            "NONE",
        ),
    ),
}
_EXPECTED_TABLE_SQL = {
    "global_identities": "create table global_identities ( global_identity_id text primary key, registry_status text not null default 'disabled', created_at text not null default current_timestamp, updated_at text not null default current_timestamp, created_provenance text not null, updated_provenance text not null, check (registry_status in ('active', 'disabled')) ) strict",
    "login_identifier_aliases": "create table login_identifier_aliases ( login_identifier_alias_id text primary key, global_identity_id text not null, raw_alias text not null, normalized_lookup_key text not null, normalization_algorithm_family text not null, normalization_profile text not null, unicode_data_version text not null, trim_conformance_profile text not null, alias_status text not null default 'active', created_at text not null default current_timestamp, updated_at text not null default current_timestamp, created_provenance text not null, updated_provenance text not null, foreign key (global_identity_id) references global_identities(global_identity_id) on delete restrict on update no action, check (alias_status in ('active', 'disabled', 'superseded')), check (normalization_algorithm_family = 'nfkc_casefold_v1'), check (normalization_profile = 'nfkc_casefold_v1_ucd16_0_0'), check (unicode_data_version = '16.0.0'), check (trim_conformance_profile = 'py3146_ucd16_0_0_strip_v1') ) strict",
    "backend_principal_mappings": "create table backend_principal_mappings ( backend_principal_mapping_id text primary key, global_identity_id text not null, backend_kind text not null, backend_principal_key any not null, mapping_status text not null default 'active', created_at text not null default current_timestamp, updated_at text not null default current_timestamp, created_provenance text not null, updated_provenance text not null, foreign key (global_identity_id) references global_identities(global_identity_id) on delete restrict on update no action, check (backend_kind in ('internal', 'vendor')), check (mapping_status in ('active', 'disabled')), check (typeof(backend_principal_key) = 'integer' and backend_principal_key > 0), unique (backend_kind, backend_principal_key), unique (global_identity_id, backend_kind) ) strict",
}

_EXPECTED_EXPLICIT_INDEXES = {
    "idx_login_identifier_aliases_candidate_lookup": (
        "c",
        False,
        False,
        (
            ("normalization_algorithm_family", "BINARY", False),
            ("normalization_profile", "BINARY", False),
            ("unicode_data_version", "BINARY", False),
            ("trim_conformance_profile", "BINARY", False),
            ("normalized_lookup_key", "BINARY", False),
            ("alias_status", "BINARY", False),
        ),
        "create index idx_login_identifier_aliases_candidate_lookup on login_identifier_aliases ( normalization_algorithm_family, normalization_profile, unicode_data_version, trim_conformance_profile, normalized_lookup_key, alias_status )",
    ),
    "idx_login_identifier_aliases_provenance_reconciliation": (
        "c",
        False,
        False,
        (
            ("normalization_algorithm_family", "BINARY", False),
            ("normalization_profile", "BINARY", False),
            ("unicode_data_version", "BINARY", False),
            ("trim_conformance_profile", "BINARY", False),
            ("global_identity_id", "BINARY", False),
            ("alias_status", "BINARY", False),
        ),
        "create index idx_login_identifier_aliases_provenance_reconciliation on login_identifier_aliases ( normalization_algorithm_family, normalization_profile, unicode_data_version, trim_conformance_profile, global_identity_id, alias_status )",
    ),
    "idx_login_identifier_aliases_active_exact_alias": (
        "c",
        True,
        True,
        (
            ("global_identity_id", "BINARY", False),
            ("raw_alias", "BINARY", False),
            ("normalized_lookup_key", "BINARY", False),
            ("normalization_algorithm_family", "BINARY", False),
            ("normalization_profile", "BINARY", False),
            ("unicode_data_version", "BINARY", False),
            ("trim_conformance_profile", "BINARY", False),
        ),
        "create unique index idx_login_identifier_aliases_active_exact_alias on login_identifier_aliases ( global_identity_id, raw_alias, normalized_lookup_key, normalization_algorithm_family, normalization_profile, unicode_data_version, trim_conformance_profile ) where alias_status = 'active'",
    ),
}
_EXPECTED_GENERATED_INDEXES = {
    "global_identities": (
        ("pk", True, False, (("global_identity_id", "BINARY", False),)),
    ),
    "login_identifier_aliases": (
        ("pk", True, False, (("login_identifier_alias_id", "BINARY", False),)),
    ),
    "backend_principal_mappings": (
        ("pk", True, False, (("backend_principal_mapping_id", "BINARY", False),)),
        (
            "u",
            True,
            False,
            (
                ("backend_kind", "BINARY", False),
                ("backend_principal_key", "BINARY", False),
            ),
        ),
        (
            "u",
            True,
            False,
            (
                ("global_identity_id", "BINARY", False),
                ("backend_kind", "BINARY", False),
            ),
        ),
    ),
}


class IdentityRegistryDiscoveryError(Exception):
    __slots__ = ("_classification",)

    def __init__(self, classification: str):
        super().__init__(_PUBLIC_MESSAGE)
        self._classification = classification


class _Failure(Exception):
    __slots__ = ("classification",)

    def __init__(self, classification: str):
        self.classification = classification


class _Operational(Exception):
    pass


class _Authorizer:
    __slots__ = (
        "_sqlite3",
        "phase",
        "allowed_reads",
        "allowed_pragmas",
        "allowed_functions",
        "required",
        "seen",
        "transaction",
        "violation",
        "active",
    )

    def __init__(self, sqlite3):
        self._sqlite3 = sqlite3
        self.phase = "closed"
        self.allowed_reads = set()
        self.allowed_pragmas = set()
        self.allowed_functions = set()
        self.required = set()
        self.seen = set()
        self.transaction = None
        self.violation = False
        self.active = False

    def configure(
        self,
        phase: str,
        *,
        reads=(),
        pragmas=(),
        functions=(),
        required=(),
        transaction=None,
    ) -> None:
        if self.phase != "closed" or self.active:
            raise _Failure("internal")
        self.phase = phase
        self.allowed_reads = set(reads)
        self.allowed_pragmas = set(pragmas)
        self.allowed_functions = set(functions)
        self.required = set(required)
        self.seen = set()
        self.transaction = transaction
        self.violation = False
        self.active = True

    def close(self) -> None:
        self.phase = "closed"
        self.allowed_reads = set()
        self.allowed_pragmas = set()
        self.allowed_functions = set()
        self.required = set()
        self.transaction = None
        self.active = False

    def verify(self) -> None:
        if self.violation or not self.required <= self.seen:
            raise _Failure("internal")

    def __call__(self, action, arg1, arg2, database, trigger):
        if not self.active or self.phase == "closed":
            self.violation = True
            return self._sqlite3.SQLITE_DENY
        if trigger is not None:
            self.violation = True
            return self._sqlite3.SQLITE_DENY
        if action == self._sqlite3.SQLITE_SELECT:
            key = ("select",)
            if key in self.required or self.phase in {
                "query_only_readback",
                "database_list",
                "schema_objects",
                "table_list",
                "table_xinfo",
                "foreign_key_list",
                "index_list",
                "index_xinfo",
                "bounded_row_query",
            }:
                self.seen.add(key)
                return self._sqlite3.SQLITE_OK
        elif action == self._sqlite3.SQLITE_READ:
            key = ("read", database, arg1, arg2)
            if key in self.allowed_reads:
                self.seen.add(key)
                return self._sqlite3.SQLITE_OK
        elif action == self._sqlite3.SQLITE_PRAGMA:
            key = ("pragma", (arg1 or "").lower(), arg2)
            if key in self.allowed_pragmas:
                self.seen.add(key)
                return self._sqlite3.SQLITE_OK
        elif action == self._sqlite3.SQLITE_FUNCTION:
            name = (arg2 or arg1 or "").lower()
            key = ("function", name)
            if name in self.allowed_functions:
                self.seen.add(key)
                return self._sqlite3.SQLITE_OK
        elif action == self._sqlite3.SQLITE_TRANSACTION:
            operation = (arg1 or "").upper()
            key = ("transaction", operation)
            if self.transaction == operation:
                self.seen.add(key)
                return self._sqlite3.SQLITE_OK
        self.violation = True
        return self._sqlite3.SQLITE_DENY


def _canonical_bytes(value) -> bytes:
    return _json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _normalize_sql(value):
    if value is None:
        return None
    if type(value) is not str:
        raise _Operational
    return " ".join(value.strip().lower().split())


def _runtime():
    if (
        _os.name != "nt"
        or _sys.implementation.name != "cpython"
        or _sys.version_info[:2] != (3, 14)
        or not hasattr(_os.stat_result, "st_mtime_ns")
        or not hasattr(_os.stat_result, "st_nlink")
        or not hasattr(_os.stat_result, "st_file_attributes")
    ):
        raise _Failure("internal")
    try:
        sqlite3 = __import__("sqlite3")
        version = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
    except Exception:
        raise _Failure("internal") from None
    if len(version) != 3 or not ((3, 37, 0) <= version < (4, 0, 0)):
        raise _Failure("internal")
    return sqlite3


def _validate_inputs(db_path, run_id, captured_at, tool_commit) -> None:
    if not isinstance(db_path, _Path):
        raise _Failure("input")
    if type(run_id) is not str:
        raise _Failure("input")
    try:
        _validate_identity_registry_id(run_id)
    except Exception:
        raise _Failure("input") from None
    if type(captured_at) is not str or _CAPTURED_AT_RE.fullmatch(captured_at) is None:
        raise _Failure("input")
    try:
        parsed = _datetime.datetime.strptime(captured_at, "%Y-%m-%dT%H:%M:%SZ")
        round_trip = parsed.replace(
            tzinfo=_datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        raise _Failure("input") from None
    if round_trip != captured_at:
        raise _Failure("input")
    if type(tool_commit) is not str or _COMMIT_RE.fullmatch(tool_commit) is None:
        raise _Failure("input")


def _windows_parts(path: _Path):
    return tuple(part.casefold() for part in path.parts)


def _is_strictly_below(path: _Path, parent: _Path) -> bool:
    child_parts = _windows_parts(path)
    parent_parts = _windows_parts(parent)
    return (
        len(child_parts) > len(parent_parts)
        and child_parts[: len(parent_parts)] == parent_parts
    )


def _lexical_components(path: _Path):
    parts = path.parts
    current = _Path(parts[0])
    yield current
    for part in parts[1:]:
        current = current / part
        yield current


def _check_no_reparse(path: _Path) -> None:
    for component in _lexical_components(path):
        try:
            info = _os.lstat(component)
        except OSError:
            raise _Failure("input") from None
        attributes = getattr(info, "st_file_attributes", None)
        if type(attributes) is not int or attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
            raise _Failure("input")


def _drive_type(root: str) -> int:
    try:
        import ctypes as _ctypes

        function = _ctypes.windll.kernel32.GetDriveTypeW
        function.argtypes = [_ctypes.c_wchar_p]
        function.restype = _ctypes.c_uint
        return int(function(root))
    except Exception:
        raise _Failure("internal") from None


def _read_source(path: _Path, *, initial: bool):
    try:
        data = path.read_bytes()
    except OSError:
        raise _Failure("input" if initial else "internal") from None
    return data


def _checkpoint(db_path: _Path, *, initial: bool):
    lexical = _Path(str(db_path))
    text = str(lexical)
    lowered = text.casefold()
    if (
        "\0" in text
        or not _DRIVE_PATH_RE.match(text)
        or text.startswith(("\\\\", "//", "\\\\?\\", "\\\\.\\"))
        or lowered.startswith(("\\\\?\\", "\\\\.\\"))
        or ":" in text[2:]
        or not lexical.is_absolute()
    ):
        raise _Failure("input")
    temp_lexical = _Path(_tempfile.gettempdir())
    temp_text = str(temp_lexical)
    if (
        not _DRIVE_PATH_RE.match(temp_text)
        or not temp_lexical.is_absolute()
        or text[:2].casefold() != temp_text[:2].casefold()
    ):
        raise _Failure("input")
    drive_root = text[:3]
    if _drive_type(drive_root) != _DRIVE_FIXED:
        raise _Failure("input")
    try:
        resolved = lexical.resolve(strict=True)
        temp_resolved = temp_lexical.resolve(strict=True)
        repository = _Path(__file__).resolve(strict=True).parents[1]
    except OSError:
        raise _Failure("input") from None
    if (
        not _is_strictly_below(resolved, temp_resolved)
        or _is_strictly_below(resolved, repository)
        or resolved == repository
        or resolved.name.casefold()
        in {"site.db", "site.db-wal", "site.db-shm", "site.db-journal"}
    ):
        raise _Failure("input")
    _check_no_reparse(lexical)
    _check_no_reparse(resolved)
    _check_no_reparse(temp_resolved)
    try:
        info = _os.lstat(resolved)
    except OSError:
        raise _Failure("input" if initial else "internal") from None
    attributes = getattr(info, "st_file_attributes", None)
    if (
        not _stat.S_ISREG(info.st_mode)
        or type(info.st_nlink) is not int
        or info.st_nlink != 1
        or type(info.st_mtime_ns) is not int
        or type(attributes) is not int
        or attributes & _FILE_ATTRIBUTE_REPARSE_POINT
    ):
        raise _Failure("input")
    sidecars = tuple((str(resolved) + suffix, _Path(str(resolved) + suffix).exists()) for suffix in _SIDECAR_SUFFIXES)
    if initial and any(exists for _, exists in sidecars):
        raise _Failure("input")
    data = _read_source(resolved, initial=initial)
    if initial and (
        len(data) < 100
        or data[:16] != _HEADER_MAGIC
        or data[18] != 1
        or data[19] != 1
    ):
        raise _Failure("input")
    if len(data) != info.st_size:
        raise _Failure("input" if initial else "internal")
    return {
        "lexical": str(lexical),
        "resolved": resolved,
        "identity": (info.st_dev, info.st_ino),
        "nlink": info.st_nlink,
        "attributes": attributes,
        "sha256": _hashlib.sha256(data).hexdigest(),
        "byte_length": len(data),
        "size": info.st_size,
        "mtime_ns": info.st_mtime_ns,
        "sidecars": sidecars,
    }


def _run_statement(
    connection,
    authorizer,
    sql,
    parameters=(),
    *,
    phase,
    reads=(),
    pragmas=(),
    functions=(),
    required=(),
    transaction=None,
):
    authorizer.configure(
        phase,
        reads=reads,
        pragmas=pragmas,
        functions=functions,
        required=required,
        transaction=transaction,
    )
    try:
        cursor = connection.execute(sql, parameters)
        rows = cursor.fetchall()
        authorizer.verify()
        return rows
    except _Failure:
        raise
    except authorizer._sqlite3.OperationalError:
        if authorizer.violation:
            raise _Failure("internal") from None
        raise _Operational from None
    except Exception:
        raise _Failure("internal") from None
    finally:
        authorizer.close()


def _required_reads(table, columns):
    return tuple(("read", "main", table, column) for column in columns)


def _metadata_reads(virtual_table, columns):
    return tuple(("read", "main", virtual_table, column) for column in columns)


def _validated_rows(rows, length):
    if type(rows) is not list:
        raise _Operational
    for row in rows:
        if type(row) is not tuple or len(row) != length:
            raise _Operational
    return rows


def _capture_projection(connection, authorizer):
    schema_version_rows = _run_statement(
        connection,
        authorizer,
        _SCHEMA_VERSION_SQL,
        phase="schema_objects",
        pragmas=(("pragma", "schema_version", None),),
        required=(("pragma", "schema_version", None),),
    )
    _validated_rows(schema_version_rows, 1)
    schema_version = schema_version_rows[0][0]
    if type(schema_version) is not int or schema_version < 0:
        raise _Operational
    schema_reads = _required_reads(
        "sqlite_master", ("type", "name", "tbl_name", "sql")
    )
    schema_rows = _run_statement(
        connection,
        authorizer,
        _SCHEMA_OBJECTS_SQL,
        phase="schema_objects",
        reads=schema_reads,
        required=(("select",),) + schema_reads,
    )
    _validated_rows(schema_rows, 4)
    objects = []
    object_sql = {}
    for object_type, name, table_name, sql in schema_rows:
        if not all(type(value) is str for value in (object_type, name, table_name)):
            raise _Operational
        if sql is not None and type(sql) is not str:
            raise _Operational
        if name.startswith("sqlite_"):
            continue
        item = {
            "name": name,
            "normalized_sql": _normalize_sql(sql),
            "sql": sql,
            "tbl_name": table_name,
            "type": object_type,
        }
        objects.append(item)
        object_sql[(object_type, name)] = sql
    objects.sort(
        key=lambda item: (
            item["type"],
            item["name"],
            item["tbl_name"],
            item["sql"] is not None,
            item["sql"] or "",
        )
    )
    table_list_columns = ("schema", "name", "type", "ncol", "wr", "strict")
    table_list_reads = _metadata_reads("pragma_table_list", table_list_columns)
    table_rows = _run_statement(
        connection,
        authorizer,
        _TABLE_LIST_SQL,
        phase="table_list",
        reads=table_list_reads,
        pragmas=(("pragma", "table_list", None),),
        required=(("select",), ("pragma", "table_list", None)) + table_list_reads,
    )
    _validated_rows(table_rows, 6)
    table_map = {}
    for schema, name, object_type, ncol, wr, strict in table_rows:
        if (
            type(schema) is not str
            or type(name) is not str
            or type(object_type) is not str
            or type(ncol) is not int
            or type(wr) is not int
            or type(strict) is not int
        ):
            raise _Operational
        if schema == "main" and object_type == "table":
            if name in table_map:
                raise _Operational
            table_map[name] = (wr, strict)
    tables = []
    for table_name in _EXPECTED_TABLES:
        if table_name not in table_map:
            tables.append(
                {
                    "columns": [],
                    "foreign_keys": [],
                    "indexes": [],
                    "name": table_name,
                    "present": False,
                    "strict": None,
                    "without_rowid": None,
                }
            )
            continue
        wr, strict = table_map[table_name]
        xinfo_columns = ("cid", "name", "type", "notnull", "dflt_value", "pk", "hidden")
        xinfo_reads = _metadata_reads("pragma_table_xinfo", xinfo_columns)
        xinfo_rows = _run_statement(
            connection,
            authorizer,
            _TABLE_XINFO_SQL,
            (table_name,),
            phase="table_xinfo",
            reads=xinfo_reads,
            pragmas=(("pragma", "table_xinfo", table_name),),
            required=(("select",), ("pragma", "table_xinfo", table_name))
            + xinfo_reads,
        )
        _validated_rows(xinfo_rows, 7)
        columns = []
        for cid, name, declared_type, notnull, default_sql, pk, hidden in xinfo_rows:
            if (
                type(cid) is not int
                or cid < 0
                or type(name) is not str
                or type(declared_type) is not str
                or type(notnull) is not int
                or (default_sql is not None and type(default_sql) is not str)
                or type(pk) is not int
                or pk < 0
                or type(hidden) is not int
                or hidden < 0
            ):
                raise _Operational
            columns.append(
                {
                    "cid": cid,
                    "default_sql": default_sql,
                    "hidden": hidden,
                    "name": name,
                    "not_null": bool(notnull),
                    "pk_position": pk,
                    "type": declared_type,
                }
            )
        fk_columns = (
            "id",
            "seq",
            "table",
            "from",
            "to",
            "on_update",
            "on_delete",
            "match",
        )
        fk_reads = _metadata_reads("pragma_foreign_key_list", fk_columns)
        fk_rows = _run_statement(
            connection,
            authorizer,
            _FOREIGN_KEY_LIST_SQL,
            (table_name,),
            phase="foreign_key_list",
            reads=fk_reads,
            pragmas=(("pragma", "foreign_key_list", table_name),),
            required=(("select",), ("pragma", "foreign_key_list", table_name))
            + fk_reads,
        )
        _validated_rows(fk_rows, 8)
        foreign_keys = []
        for row in fk_rows:
            id_value, seq, target, source, to, on_update, on_delete, match = row
            if (
                type(id_value) is not int
                or id_value < 0
                or type(seq) is not int
                or seq < 0
                or not all(
                    type(value) is str
                    for value in (target, source, to, on_update, on_delete, match)
                )
            ):
                raise _Operational
            foreign_keys.append(
                {
                    "from": source,
                    "id": id_value,
                    "match": match,
                    "on_delete": on_delete,
                    "on_update": on_update,
                    "seq": seq,
                    "table": target,
                    "to": to,
                }
            )
        index_list_columns = ("seq", "name", "unique", "origin", "partial")
        index_list_reads = _metadata_reads("pragma_index_list", index_list_columns)
        index_rows = _run_statement(
            connection,
            authorizer,
            _INDEX_LIST_SQL,
            (table_name,),
            phase="index_list",
            reads=index_list_reads,
            pragmas=(("pragma", "index_list", table_name),),
            required=(("select",), ("pragma", "index_list", table_name))
            + index_list_reads,
        )
        _validated_rows(index_rows, 5)
        indexes = []
        names = set()
        for seq, index_name, unique, origin, partial in index_rows:
            if (
                type(seq) is not int
                or type(index_name) is not str
                or not index_name
                or "\0" in index_name
                or type(unique) is not int
                or type(origin) is not str
                or type(partial) is not int
                or index_name in names
            ):
                raise _Operational
            names.add(index_name)
            ix_columns = ("seqno", "cid", "name", "desc", "coll", "key")
            ix_reads = _metadata_reads("pragma_index_xinfo", ix_columns)
            ix_rows = _run_statement(
                connection,
                authorizer,
                _INDEX_XINFO_SQL,
                (index_name,),
                phase="index_xinfo",
                reads=ix_reads,
                pragmas=(("pragma", "index_xinfo", index_name),),
                required=(("select",), ("pragma", "index_xinfo", index_name))
                + ix_reads,
            )
            _validated_rows(ix_rows, 6)
            index_columns = []
            for seqno, cid, column_name, descending, collation, key in ix_rows:
                if (
                    type(seqno) is not int
                    or seqno < 0
                    or type(cid) is not int
                    or (column_name is not None and type(column_name) is not str)
                    or type(descending) is not int
                    or type(collation) is not str
                    or type(key) is not int
                ):
                    raise _Operational
                index_columns.append(
                    {
                        "cid": cid,
                        "collation": collation,
                        "descending": bool(descending),
                        "key": bool(key),
                        "name": column_name,
                        "seqno": seqno,
                    }
                )
            sql = object_sql.get(("index", index_name))
            indexes.append(
                {
                    "columns": index_columns,
                    "name": index_name,
                    "normalized_sql": _normalize_sql(sql),
                    "origin": origin,
                    "partial": bool(partial),
                    "sql": sql,
                    "unique": bool(unique),
                }
            )
        indexes.sort(key=lambda item: item["name"])
        tables.append(
            {
                "columns": columns,
                "foreign_keys": foreign_keys,
                "indexes": indexes,
                "name": table_name,
                "present": True,
                "strict": bool(strict),
                "without_rowid": bool(wr),
            }
        )
    return {
        "format": "auth-id-001h-registry-schema-projection",
        "objects": objects,
        "schema_version": 1,
        "sqlite_schema_version": schema_version,
        "tables": tables,
    }


def _fact(kind, owner, subject, attribute, expected, observed):
    return [kind, owner, subject, attribute, expected, observed]


def _schema_facts(projection):
    facts = {}

    def add(value):
        facts[_canonical_bytes(value)] = value

    objects = projection["objects"]
    object_map = {(item["type"], item["name"]): item for item in objects}
    for table in projection["tables"]:
        name = table["name"]
        if not table["present"]:
            add(_fact("table", name, name, "present", True, False))
            continue
        for attribute, expected in (("strict", True), ("without_rowid", False)):
            if table[attribute] != expected:
                add(_fact("table", name, name, attribute, expected, table[attribute]))
        expected_columns = {item[1]: item for item in _EXPECTED_COLUMNS[name]}
        observed_columns = {
            item["name"]: (
                item["cid"],
                item["name"],
                item["type"],
                item["not_null"],
                item["default_sql"],
                item["pk_position"],
                item["hidden"],
            )
            for item in table["columns"]
        }
        for column_name, expected in expected_columns.items():
            observed = observed_columns.get(column_name)
            if observed is None:
                add(_fact("column", name, column_name, "present", list(expected), None))
                continue
            fields = (
                "cid",
                "name",
                "declared_type",
                "not_null",
                "default_sql",
                "pk_position",
                "hidden",
            )
            for index, field in enumerate(fields):
                if expected[index] != observed[index]:
                    add(
                        _fact(
                            "column",
                            name,
                            column_name,
                            field,
                            expected[index],
                            observed[index],
                        )
                    )
        for column_name, observed in observed_columns.items():
            if column_name not in expected_columns:
                add(_fact("column", name, column_name, "present", None, list(observed)))
        observed_fks = {
            (
                item["from"],
                item["table"],
                item["to"],
                item["on_update"],
                item["on_delete"],
                item["match"],
            )
            for item in table["foreign_keys"]
        }
        expected_fks = set(_EXPECTED_FOREIGN_KEYS[name])
        for item in expected_fks - observed_fks:
            add(_fact("foreign_key", name, "foreign_key", "tuple", list(item), None))
        for item in observed_fks - expected_fks:
            add(_fact("foreign_key", name, "foreign_key", "tuple", None, list(item)))
        normalized_table_sql = _normalize_sql(
            object_map.get(("table", name), {}).get("sql")
        )
        if normalized_table_sql != _EXPECTED_TABLE_SQL[name]:
            add(
                _fact(
                    "table_sql",
                    name,
                    name,
                    "normalized_sql",
                    _EXPECTED_TABLE_SQL[name],
                    normalized_table_sql,
                )
            )
        explicit = {}
        generated = set()
        for index in table["indexes"]:
            key_columns = tuple(
                (item["name"], item["collation"], item["descending"])
                for item in index["columns"]
                if item["key"]
            )
            if index["origin"] == "c":
                explicit[index["name"]] = (
                    index["origin"],
                    index["unique"],
                    index["partial"],
                    key_columns,
                    index["normalized_sql"],
                )
            else:
                generated.add(
                    (
                        index["origin"],
                        index["unique"],
                        index["partial"],
                        key_columns,
                    )
                )
        expected_explicit = (
            _EXPECTED_EXPLICIT_INDEXES
            if name == "login_identifier_aliases"
            else {}
        )
        for index_name, expected in expected_explicit.items():
            observed = explicit.get(index_name)
            if observed is None:
                add(
                    _fact(
                        "explicit_index",
                        name,
                        index_name,
                        "present",
                        list(expected),
                        None,
                    )
                )
                continue
            fields = (
                "origin",
                "unique",
                "partial",
                "ordered_key_columns",
                "normalized_sql",
            )
            for position, field in enumerate(fields):
                if expected[position] != observed[position]:
                    expected_value = expected[position]
                    observed_value = observed[position]
                    if type(expected_value) is tuple:
                        expected_value = [list(item) for item in expected_value]
                    if type(observed_value) is tuple:
                        observed_value = [list(item) for item in observed_value]
                    add(
                        _fact(
                            "explicit_index",
                            name,
                            index_name,
                            field,
                            expected_value,
                            observed_value,
                        )
                    )
        for index_name, observed in explicit.items():
            if index_name not in expected_explicit:
                observed_value = list(observed)
                observed_value[3] = [list(item) for item in observed[3]]
                add(
                    _fact(
                        "owned_object",
                        name,
                        index_name,
                        "present",
                        None,
                        observed_value,
                    )
                )
        expected_generated = set(_EXPECTED_GENERATED_INDEXES[name])
        for item in expected_generated - generated:
            value = list(item)
            value[3] = [list(column) for column in item[3]]
            add(_fact("semantic_unique", name, "pk_or_unique", "tuple", value, None))
        for item in generated - expected_generated:
            value = list(item)
            value[3] = [list(column) for column in item[3]]
            add(_fact("semantic_unique", name, "pk_or_unique", "tuple", None, value))
        for item in objects:
            if (
                item["tbl_name"] == name
                and item["type"] in {"view", "trigger"}
            ):
                add(
                    _fact(
                        "owned_object",
                        name,
                        item["name"],
                        "present",
                        None,
                        True,
                    )
                )
    return tuple(facts[key] for key in sorted(facts))


def _row_read_matrix(code):
    columns = {
        "global_identities": set(),
        "login_identifier_aliases": set(),
        "backend_principal_mappings": set(),
    }
    if code == "noncanonical_registry_id":
        columns["global_identities"].add("global_identity_id")
        columns["login_identifier_aliases"].update(
            {"login_identifier_alias_id", "global_identity_id"}
        )
        columns["backend_principal_mappings"].update(
            {"backend_principal_mapping_id", "global_identity_id"}
        )
    elif code == "invalid_registry_status":
        columns["global_identities"].add("registry_status")
        columns["login_identifier_aliases"].add("alias_status")
        columns["backend_principal_mappings"].add("mapping_status")
    elif code == "invalid_backend_principal_key":
        columns["backend_principal_mappings"].update(
            {"backend_kind", "backend_principal_key"}
        )
    elif code == "orphan_fk_relationship":
        columns["global_identities"].add("global_identity_id")
        columns["login_identifier_aliases"].add("global_identity_id")
        columns["backend_principal_mappings"].add("global_identity_id")
    elif code == "normalized_alias_ambiguity":
        columns["global_identities"].update({"global_identity_id", "registry_status"})
        columns["login_identifier_aliases"].update(
            {
                "global_identity_id",
                "alias_status",
                "normalization_algorithm_family",
                "normalization_profile",
                "unicode_data_version",
                "trim_conformance_profile",
                "normalized_lookup_key",
            }
        )
        columns["backend_principal_mappings"].update(
            {"global_identity_id", "mapping_status"}
        )
    elif code == "active_exact_alias_collision":
        columns["login_identifier_aliases"].update(
            {
                "global_identity_id",
                "raw_alias",
                "normalized_lookup_key",
                "normalization_algorithm_family",
                "normalization_profile",
                "unicode_data_version",
                "trim_conformance_profile",
                "alias_status",
            }
        )
    elif code in {
        "backend_principal_inconsistent_mapping",
        "incompatible_backend_cardinality",
    }:
        columns["backend_principal_mappings"].update(
            {"global_identity_id", "backend_kind", "backend_principal_key"}
        )
    reads = []
    for table in _EXPECTED_TABLES:
        reads.extend(_required_reads(table, sorted(columns[table])))
    return tuple(reads)


def _bounded_result(code, rows):
    if code == "noncanonical_registry_id":
        count = 0
        for row in _validated_rows(rows, 1):
            value = row[0]
            invalid = type(value) is not str
            if not invalid:
                try:
                    _validate_identity_registry_id(value)
                except Exception:
                    invalid = True
            if invalid:
                count += 1
        return count, False
    _validated_rows(rows, 1 if code in {
        "invalid_registry_status",
        "invalid_backend_principal_key",
        "orphan_fk_relationship",
    } else 2)
    if code in {
        "invalid_registry_status",
        "invalid_backend_principal_key",
        "orphan_fk_relationship",
    }:
        value = rows[0][0]
        if type(value) is not int or value < 0:
            raise _Operational
        return value, False
    count, invalid = rows[0]
    if type(count) is not int or count < 0 or type(invalid) is not int or invalid < 0:
        raise _Operational
    return count, invalid > 0


def _observation(code, disposition, *, count=None, indeterminate=None):
    if indeterminate is not None:
        return {
            "code": code,
            "state": "indeterminate",
            "disposition": disposition,
            "count": None,
            "reason_code": indeterminate,
        }
    return {
        "code": code,
        "state": "observed" if count else "not_observed",
        "disposition": disposition,
        "count": count,
        "reason_code": (
            "bounded_violation_observed"
            if count
            else "bounded_violation_not_observed"
        ),
    }


def _fixed_observations():
    return {
        "invalid_provenance": {
            "state": "indeterminate",
            "count": None,
            "reason_code": "historical_ledger_unavailable",
        },
        "conflicting_principals_different_identities": {
            "state": "unsupported",
            "count": None,
            "reason_code": "cross_backend_subject_evidence_required",
        },
        "disabled_superseded_relationship_inconsistency": {
            "state": "indeterminate",
            "count": None,
            "reason_code": "historical_ledger_unavailable",
        },
        "source_principal_missing_inactive_stale": {
            "state": "unsupported",
            "count": None,
            "reason_code": "backend_revalidation_required",
        },
        "snapshot_concurrency_drift": {
            "state": "indeterminate",
            "count": None,
            "reason_code": "single_snapshot_cannot_exclude_concurrency_drift",
        },
    }


def _source_read_incomplete_observations():
    observations = {}
    fixed = _fixed_observations()
    for code, disposition in _ANOMALY_DISPOSITIONS:
        if code in fixed:
            continue
        reason = (
            "schema_contract_unavailable"
            if code == "schema_object_drift"
            else "bounded_query_incomplete"
        )
        observations[code] = _observation(
            code, disposition, indeterminate=reason
        )
    return observations


def _assemble_output(
    *,
    run_id,
    captured_at,
    tool_commit,
    source,
    schema_hash,
    observations,
    errors,
):
    items = []
    fixed = _fixed_observations()
    for code, disposition in _ANOMALY_DISPOSITIONS:
        if code in fixed:
            item = {"code": code, "disposition": disposition, **fixed[code]}
        else:
            item = observations[code]
        items.append(item)
    output = {
        "format": _FORMAT,
        "schema_version": 1,
        "run_id": run_id,
        "captured_at": captured_at,
        "tool": {
            "commit": tool_commit,
            "module_sha256": _hashlib.sha256(_Path(__file__).read_bytes()).hexdigest(),
            "version": _TOOL_VERSION,
        },
        "source": {
            "classification": "system-temp-disposable-sqlite-fixture",
            "schema_manifest_sha256": schema_hash,
            "sha256": source["sha256"],
            "size_bytes": source["size"],
        },
        "scope": {
            "backend_revalidation": False,
            "fixture": "system-temp-disposable-sqlite",
            "historical_ledger": False,
            "production": False,
            "snapshot_count": 1,
        },
        "capture_status": "incomplete" if errors else "complete",
        "anomalies": items,
        "errors": sorted(set(errors)),
        "redaction": {"policy": "auth-id-001h-aggregate-only-v1"},
        "integrity": {},
    }
    digest = _hashlib.sha256(_canonical_bytes(output)).hexdigest()
    output["integrity"]["evidence_sha256"] = digest
    encoded = _canonical_bytes(output)
    if b"PASS" in encoded or b"site.db" in encoded:
        raise _Failure("internal")
    return output


def _capture(sqlite3, resolved_path, pre, run_id, captured_at, tool_commit):
    connection = None
    authorizer = None
    errors = set()
    observations = {}
    projection = None
    schema_hash = None
    row_allowed = False
    transaction_started = False
    rollback_failed = False
    setup_failed = False
    try:
        try:
            connection = sqlite3.connect(
                resolved_path.as_uri() + "?mode=ro",
                uri=True,
                cached_statements=0,
            )
        except sqlite3.OperationalError:
            errors.add("source_read_incomplete")
            setup_failed = True
        except Exception:
            raise _Failure("internal") from None
        if connection is not None and not setup_failed:
            try:
                connection.execute(_QUERY_ONLY_SET_SQL)
            except sqlite3.OperationalError:
                errors.add("source_read_incomplete")
                setup_failed = True
            except Exception:
                raise _Failure("internal") from None
        first_read = None
        if connection is not None and not setup_failed:
            try:
                first_read = connection.execute(_QUERY_ONLY_READ_SQL).fetchall()
            except sqlite3.OperationalError:
                errors.add("source_read_incomplete")
                setup_failed = True
            except Exception:
                raise _Failure("internal") from None
        if setup_failed:
            observations = _source_read_incomplete_observations()
        elif (
            type(first_read) is not list
            or first_read != [(1,)]
        ):
            raise _Failure("internal")
        else:
            authorizer = _Authorizer(sqlite3)
            try:
                connection.set_authorizer(authorizer)
            except Exception:
                raise _Failure("internal") from None
            try:
                readback = _run_statement(
                    connection,
                    authorizer,
                    _QUERY_ONLY_READ_SQL,
                    phase="query_only_readback",
                    pragmas=(("pragma", "query_only", None),),
                    required=(("pragma", "query_only", None),),
                )
                if readback != [(1,)]:
                    raise _Failure("internal")
                _run_statement(
                    connection,
                    authorizer,
                    _BEGIN_SQL,
                    phase="transaction_begin",
                    transaction="BEGIN",
                    required=(("transaction", "BEGIN"),),
                )
                transaction_started = True
            except _Operational:
                errors.add("source_read_incomplete")
                observations = _source_read_incomplete_observations()
            if transaction_started:
                database_ok = False
                try:
                    database_rows = _run_statement(
                        connection,
                        authorizer,
                        _DATABASE_LIST_SQL,
                        phase="database_list",
                        pragmas=(("pragma", "database_list", None),),
                        required=(("pragma", "database_list", None),),
                    )
                    _validated_rows(database_rows, 3)
                    if (
                        len(database_rows) != 1
                        or database_rows[0][0] != 0
                        or database_rows[0][1] != "main"
                        or type(database_rows[0][2]) is not str
                    ):
                        errors.add("source_identity_changed")
                    else:
                        actual = _Path(database_rows[0][2]).resolve(strict=True)
                        if _windows_parts(actual) != _windows_parts(resolved_path):
                            errors.add("source_identity_changed")
                        else:
                            database_ok = True
                except _Operational:
                    errors.add("source_read_incomplete")
                if database_ok:
                    try:
                        projection = _capture_projection(connection, authorizer)
                        schema_hash = _hashlib.sha256(
                            _canonical_bytes(projection)
                        ).hexdigest()
                        facts = _schema_facts(projection)
                        observations["schema_object_drift"] = _observation(
                            "schema_object_drift",
                            "owner_gate_required",
                            count=len(facts),
                        )
                        if facts:
                            errors.add("schema_drift")
                        tables_present = all(
                            item["present"] for item in projection["tables"]
                        )
                        exact_columns = all(
                            tuple(
                                (
                                    item["cid"],
                                    item["name"],
                                    item["type"],
                                    item["not_null"],
                                    item["default_sql"],
                                    item["pk_position"],
                                    item["hidden"],
                                )
                                for item in table["columns"]
                            )
                            == _EXPECTED_COLUMNS[table["name"]]
                            for table in projection["tables"]
                            if table["present"]
                        )
                        row_allowed = tables_present and exact_columns
                    except _Operational:
                        errors.add("schema_capture_incomplete")
                        observations["schema_object_drift"] = _observation(
                            "schema_object_drift",
                            "owner_gate_required",
                            indeterminate="schema_contract_unavailable",
                        )
                if not database_ok:
                    observations["schema_object_drift"] = _observation(
                        "schema_object_drift",
                        "owner_gate_required",
                        indeterminate="schema_contract_unavailable",
                    )
                if row_allowed:
                    for code, sql in _ROW_QUERIES:
                        disposition = dict(_ANOMALY_DISPOSITIONS)[code]
                        reads = _row_read_matrix(code)
                        functions = (
                            ("count", "typeof")
                            if code != "noncanonical_registry_id"
                            else ()
                        )
                        required = (("select",),) + reads + tuple(
                            ("function", function) for function in functions
                        )
                        try:
                            rows = _run_statement(
                                connection,
                                authorizer,
                                sql,
                                phase="bounded_row_query",
                                reads=reads,
                                functions=functions,
                                required=required,
                            )
                            count, invalid = _bounded_result(code, rows)
                            if invalid:
                                observations[code] = _observation(
                                    code,
                                    disposition,
                                    indeterminate="bounded_query_incomplete",
                                )
                            else:
                                observations[code] = _observation(
                                    code, disposition, count=count
                                )
                        except _Operational:
                            errors.add("bounded_query_incomplete")
                            observations[code] = _observation(
                                code,
                                disposition,
                                indeterminate="bounded_query_incomplete",
                            )
                for code, disposition in _ANOMALY_DISPOSITIONS:
                    if code in _fixed_observations() or code in observations:
                        continue
                    observations[code] = _observation(
                        code,
                        disposition,
                        indeterminate="schema_contract_unavailable",
                    )
                unknown_reason = (
                    "bounded_query_incomplete"
                    if "bounded_query_incomplete" in errors
                    else (
                        "schema_contract_unavailable"
                        if not row_allowed
                        else None
                    )
                )
                observations["unknown_unclassified_anomaly"] = _observation(
                    "unknown_unclassified_anomaly",
                    "fail_closed",
                    count=0 if unknown_reason is None else None,
                    indeterminate=unknown_reason,
                )
                try:
                    _run_statement(
                        connection,
                        authorizer,
                        _ROLLBACK_SQL,
                        phase="transaction_rollback",
                        transaction="ROLLBACK",
                        required=(("transaction", "ROLLBACK"),),
                    )
                    transaction_started = False
                except _Operational:
                    rollback_failed = True
                    errors.add("source_read_incomplete")
    finally:
        primary_failure = _sys.exception()
        cleanup_internal = False
        if authorizer is not None:
            try:
                authorizer.close()
                connection.set_authorizer(None)
            except Exception:
                if primary_failure is None:
                    cleanup_internal = True
        if connection is not None:
            try:
                connection.close()
            except sqlite3.OperationalError:
                if primary_failure is None:
                    errors.add("source_read_incomplete")
            except Exception:
                if primary_failure is None:
                    cleanup_internal = True
        if cleanup_internal:
            raise _Failure("internal") from None
    if rollback_failed or transaction_started:
        for code, disposition in _ANOMALY_DISPOSITIONS:
            if code in _fixed_observations():
                continue
            if (
                code == "schema_object_drift"
                and observations.get(code, {}).get("state") == "observed"
            ):
                continue
            reason = (
                "schema_contract_unavailable"
                if code == "schema_object_drift"
                else "bounded_query_incomplete"
            )
            observations[code] = _observation(
                code, disposition, indeterminate=reason
            )
    try:
        post = _checkpoint(resolved_path, initial=False)
        identity_keys = (
            "lexical",
            "resolved",
            "identity",
            "nlink",
            "attributes",
            "sha256",
            "byte_length",
            "size",
            "mtime_ns",
        )
        if any(pre[key] != post[key] for key in identity_keys):
            errors.add("source_identity_changed")
        if pre["sidecars"] != post["sidecars"] or any(
            exists for _, exists in post["sidecars"]
        ):
            errors.add("sidecar_state_changed")
    except _Failure:
        errors.add("source_read_incomplete")
    if errors & {
        "source_identity_changed",
        "sidecar_state_changed",
        "source_read_incomplete",
    }:
        for code, disposition in _ANOMALY_DISPOSITIONS:
            if code in _fixed_observations():
                continue
            if (
                rollback_failed
                and code == "schema_object_drift"
                and observations.get(code, {}).get("state") == "observed"
            ):
                continue
            observations[code] = _observation(
                code,
                disposition,
                indeterminate=(
                    "schema_contract_unavailable"
                    if code == "schema_object_drift"
                    else "bounded_query_incomplete"
                ),
            )
    return _assemble_output(
        run_id=run_id,
        captured_at=captured_at,
        tool_commit=tool_commit,
        source=pre,
        schema_hash=schema_hash,
        observations=observations,
        errors=errors,
    )


def discover_identity_registry_anomalies(
    *,
    db_path: _Path,
    run_id: str,
    captured_at: str,
    tool_commit: str,
) -> dict[str, object]:
    classification = None
    try:
        sqlite3 = _runtime()
        _validate_inputs(db_path, run_id, captured_at, tool_commit)
        pre = _checkpoint(db_path, initial=True)
        return _capture(
            sqlite3,
            pre["resolved"],
            pre,
            run_id,
            captured_at,
            tool_commit,
        )
    except _Failure as failure:
        classification = failure.classification
    except Exception:
        classification = "internal"
    error = IdentityRegistryDiscoveryError(classification or "internal")
    error.__cause__ = None
    error.__context__ = None
    raise error from None


def _parse_cli(argv):
    if argv is None:
        argv = _sys.argv[1:]
    if type(argv) not in {list, tuple} or len(argv) != 8:
        raise _Failure("input")
    expected = {"--db", "--run-id", "--captured-at", "--tool-commit"}
    values = {}
    for position in range(0, 8, 2):
        option = argv[position]
        value = argv[position + 1]
        if (
            type(option) is not str
            or type(value) is not str
            or option not in expected
            or option in values
            or value.startswith("-")
        ):
            raise _Failure("input")
        values[option] = value
    if set(values) != expected:
        raise _Failure("input")
    return values


def _main(argv: _Sequence[str] | None = None) -> int:
    stdout = ""
    stderr = ""
    status = 4
    try:
        values = _parse_cli(argv)
        result = discover_identity_registry_anomalies(
            db_path=_Path(values["--db"]),
            run_id=values["--run-id"],
            captured_at=values["--captured-at"],
            tool_commit=values["--tool-commit"],
        )
        if type(result) is not dict or result.get("capture_status") not in {
            "complete",
            "incomplete",
        }:
            raise _Failure("internal")
        stdout = _canonical_bytes(result).decode("utf-8") + "\n"
        if result["capture_status"] == "complete":
            status = 0
        else:
            stderr = _INCOMPLETE_MARKER
            status = 3
    except IdentityRegistryDiscoveryError as error:
        if error._classification == "input":
            stderr = _INPUT_MARKER
            status = 2
        else:
            stderr = _INTERNAL_MARKER
            status = 4
    except _Failure as failure:
        if failure.classification == "input":
            stderr = _INPUT_MARKER
            status = 2
        else:
            stderr = _INTERNAL_MARKER
            status = 4
    except Exception:
        stderr = _INTERNAL_MARKER
        status = 4
    if stdout:
        _sys.stdout.buffer.write(stdout.encode("utf-8"))
    if stderr:
        _sys.stderr.buffer.write(stderr.encode("utf-8"))
    return status


if __name__ == "__main__":
    raise SystemExit(_main())
