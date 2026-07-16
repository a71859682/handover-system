from __future__ import annotations

import argparse
import sqlite3
import tempfile
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT_DIR / "site.db"
PASS_MARKER = "PASS identity registry schema check passed."
SELF_TEST_MARKER = "PASS identity registry schema self-test passed."
NORMALIZATION_ALGORITHM_FAMILY = "NFKC_CASEFOLD_V1"
NORMALIZATION_PROFILE = "NFKC_CASEFOLD_V1_UCD16_0_0"
UNICODE_DATA_VERSION = "16.0.0"
TRIM_CONFORMANCE_PROFILE = "PY3146_UCD16_0_0_STRIP_V1"
ALIAS_TABLE_NAME = "login_identifier_aliases"
MAPPING_TABLE_NAME = "backend_principal_mappings"
ALIAS_ALLOWED_EXPLICIT_INDEXES = {
    "idx_login_identifier_aliases_candidate_lookup",
    "idx_login_identifier_aliases_provenance_reconciliation",
    "idx_login_identifier_aliases_active_exact_alias",
}
ALIAS_ALLOWED_PARTIAL_UNIQUE_COLUMNS = (
    "global_identity_id",
    "raw_alias",
    "normalized_lookup_key",
    "normalization_algorithm_family",
    "normalization_profile",
    "unicode_data_version",
    "trim_conformance_profile",
)
ALIAS_ALLOWED_PARTIAL_UNIQUE_WHERE = "alias_status = 'active'"
MAPPING_ALLOWED_UNIQUE_SETS = {
    ("backend_kind", "backend_principal_key"),
    ("global_identity_id", "backend_kind"),
}


VALID_SCHEMA_SQL = f"""
CREATE TABLE global_identities (
    global_identity_id TEXT PRIMARY KEY,
    registry_status TEXT NOT NULL DEFAULT 'disabled',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_provenance TEXT NOT NULL,
    updated_provenance TEXT NOT NULL,
    CHECK (registry_status IN ('active', 'disabled'))
) STRICT;

CREATE TABLE login_identifier_aliases (
    login_identifier_alias_id TEXT PRIMARY KEY,
    global_identity_id TEXT NOT NULL,
    raw_alias TEXT NOT NULL,
    normalized_lookup_key TEXT NOT NULL,
    normalization_algorithm_family TEXT NOT NULL,
    normalization_profile TEXT NOT NULL,
    unicode_data_version TEXT NOT NULL,
    trim_conformance_profile TEXT NOT NULL,
    alias_status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_provenance TEXT NOT NULL,
    updated_provenance TEXT NOT NULL,
    FOREIGN KEY (global_identity_id)
        REFERENCES global_identities(global_identity_id)
        ON DELETE RESTRICT
        ON UPDATE NO ACTION,
    CHECK (alias_status IN ('active', 'disabled', 'superseded')),
    CHECK (normalization_algorithm_family = '{NORMALIZATION_ALGORITHM_FAMILY}'),
    CHECK (normalization_profile = '{NORMALIZATION_PROFILE}'),
    CHECK (unicode_data_version = '{UNICODE_DATA_VERSION}'),
    CHECK (trim_conformance_profile = '{TRIM_CONFORMANCE_PROFILE}')
) STRICT;

CREATE TABLE backend_principal_mappings (
    backend_principal_mapping_id TEXT PRIMARY KEY,
    global_identity_id TEXT NOT NULL,
    backend_kind TEXT NOT NULL,
    backend_principal_key ANY NOT NULL,
    mapping_status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_provenance TEXT NOT NULL,
    updated_provenance TEXT NOT NULL,
    FOREIGN KEY (global_identity_id)
        REFERENCES global_identities(global_identity_id)
        ON DELETE RESTRICT
        ON UPDATE NO ACTION,
    CHECK (backend_kind IN ('internal', 'vendor')),
    CHECK (mapping_status IN ('active', 'disabled')),
    CHECK (typeof(backend_principal_key) = 'integer' AND backend_principal_key > 0),
    UNIQUE (backend_kind, backend_principal_key),
    UNIQUE (global_identity_id, backend_kind)
) STRICT;

CREATE INDEX idx_login_identifier_aliases_candidate_lookup
ON login_identifier_aliases (
    normalization_algorithm_family,
    normalization_profile,
    unicode_data_version,
    trim_conformance_profile,
    normalized_lookup_key,
    alias_status
);

CREATE INDEX idx_login_identifier_aliases_provenance_reconciliation
ON login_identifier_aliases (
    normalization_algorithm_family,
    normalization_profile,
    unicode_data_version,
    trim_conformance_profile,
    global_identity_id,
    alias_status
);

CREATE UNIQUE INDEX idx_login_identifier_aliases_active_exact_alias
ON login_identifier_aliases (
    global_identity_id,
    raw_alias,
    normalized_lookup_key,
    normalization_algorithm_family,
    normalization_profile,
    unicode_data_version,
    trim_conformance_profile
)
WHERE alias_status = 'active';
"""


EXPECTED_TABLES = {
    "global_identities": {
        "strict": True,
        "columns": {
            "global_identity_id": {"type": "TEXT", "notnull": 1, "pk": 1, "default": None},
            "registry_status": {"type": "TEXT", "notnull": 1, "pk": 0, "default": "'disabled'"},
            "created_at": {"type": "TEXT", "notnull": 1, "pk": 0, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TEXT", "notnull": 1, "pk": 0, "default": "CURRENT_TIMESTAMP"},
            "created_provenance": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
            "updated_provenance": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
        },
        "row_count": 0,
        "required_sql_fragments": (
            "check (registry_status in ('active', 'disabled'))",
            "strict",
        ),
    },
    "login_identifier_aliases": {
        "strict": True,
        "columns": {
            "login_identifier_alias_id": {"type": "TEXT", "notnull": 1, "pk": 1, "default": None},
            "global_identity_id": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
            "raw_alias": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
            "normalized_lookup_key": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
            "normalization_algorithm_family": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
            "normalization_profile": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
            "unicode_data_version": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
            "trim_conformance_profile": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
            "alias_status": {"type": "TEXT", "notnull": 1, "pk": 0, "default": "'active'"},
            "created_at": {"type": "TEXT", "notnull": 1, "pk": 0, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TEXT", "notnull": 1, "pk": 0, "default": "CURRENT_TIMESTAMP"},
            "created_provenance": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
            "updated_provenance": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
        },
        "row_count": 0,
        "required_sql_fragments": (
            "foreign key (global_identity_id) references global_identities(global_identity_id) on delete restrict on update no action",
            "check (alias_status in ('active', 'disabled', 'superseded'))",
            f"check (normalization_algorithm_family = '{NORMALIZATION_ALGORITHM_FAMILY.lower()}')",
            f"check (normalization_profile = '{NORMALIZATION_PROFILE.lower()}')",
            f"check (unicode_data_version = '{UNICODE_DATA_VERSION.lower()}')",
            f"check (trim_conformance_profile = '{TRIM_CONFORMANCE_PROFILE.lower()}')",
            "strict",
        ),
        "foreign_keys": {
            ("global_identity_id", "global_identities", "global_identity_id", "NO ACTION", "RESTRICT"),
        },
        "indexes": {
            "idx_login_identifier_aliases_candidate_lookup": {
                "unique": False,
                "columns": (
                    "normalization_algorithm_family",
                    "normalization_profile",
                    "unicode_data_version",
                    "trim_conformance_profile",
                    "normalized_lookup_key",
                    "alias_status",
                ),
                "where": None,
            },
            "idx_login_identifier_aliases_provenance_reconciliation": {
                "unique": False,
                "columns": (
                    "normalization_algorithm_family",
                    "normalization_profile",
                    "unicode_data_version",
                    "trim_conformance_profile",
                    "global_identity_id",
                    "alias_status",
                ),
                "where": None,
            },
            "idx_login_identifier_aliases_active_exact_alias": {
                "unique": True,
                "columns": (
                    "global_identity_id",
                    "raw_alias",
                    "normalized_lookup_key",
                    "normalization_algorithm_family",
                    "normalization_profile",
                    "unicode_data_version",
                    "trim_conformance_profile",
                ),
                "where": "alias_status = 'active'",
            },
        },
    },
    "backend_principal_mappings": {
        "strict": True,
        "columns": {
            "backend_principal_mapping_id": {"type": "TEXT", "notnull": 1, "pk": 1, "default": None},
            "global_identity_id": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
            "backend_kind": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
            "backend_principal_key": {"type": "ANY", "notnull": 1, "pk": 0, "default": None},
            "mapping_status": {"type": "TEXT", "notnull": 1, "pk": 0, "default": "'active'"},
            "created_at": {"type": "TEXT", "notnull": 1, "pk": 0, "default": "CURRENT_TIMESTAMP"},
            "updated_at": {"type": "TEXT", "notnull": 1, "pk": 0, "default": "CURRENT_TIMESTAMP"},
            "created_provenance": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
            "updated_provenance": {"type": "TEXT", "notnull": 1, "pk": 0, "default": None},
        },
        "row_count": 0,
        "required_sql_fragments": (
            "foreign key (global_identity_id) references global_identities(global_identity_id) on delete restrict on update no action",
            "check (backend_kind in ('internal', 'vendor'))",
            "check (mapping_status in ('active', 'disabled'))",
            "check (typeof(backend_principal_key) = 'integer' and backend_principal_key > 0)",
            "unique (backend_kind, backend_principal_key)",
            "unique (global_identity_id, backend_kind)",
            "strict",
        ),
        "foreign_keys": {
            ("global_identity_id", "global_identities", "global_identity_id", "NO ACTION", "RESTRICT"),
        },
        "unique_sets": {
            ("backend_kind", "backend_principal_key"),
            ("global_identity_id", "backend_kind"),
        },
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check identity registry SQLite schema.")
    parser.add_argument("--db", type=Path, help="SQLite database path to inspect.")
    parser.add_argument("--self-test", action="store_true", help="Run disposable self-tests.")
    return parser.parse_args()


def normalize_sql(sql: str | None) -> str:
    if not sql:
        return ""
    return " ".join(sql.strip().lower().split())


def normalize_default(value: object) -> str | None:
    if value is None:
        return None
    return str(value).strip()


def resolve_db_path(arg_path: Path | None) -> Path:
    if arg_path is not None:
        return arg_path.expanduser().resolve()
    import os

    configured = os.environ.get("APP_DB_PATH", "").strip()
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DB_PATH.resolve()


def open_readonly_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = 1")
    return conn


def table_info(conn: sqlite3.Connection, table_name: str) -> dict[str, sqlite3.Row]:
    return {
        row["name"]: row
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def table_sql(conn: sqlite3.Connection, table_name: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row["sql"] if row else ""


def strict_flag(conn: sqlite3.Connection, table_name: str) -> bool:
    for row in conn.execute("PRAGMA table_list").fetchall():
        if row["name"] == table_name:
            return bool(row["strict"])
    return False


def foreign_keys(conn: sqlite3.Connection, table_name: str) -> set[tuple[str, str, str, str, str]]:
    return {
        (row["from"], row["table"], row["to"], row["on_update"], row["on_delete"])
        for row in conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
    }


def index_map(conn: sqlite3.Connection, table_name: str) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for row in conn.execute(f"PRAGMA index_list({table_name})").fetchall():
        name = row["name"]
        sql_row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
            (name,),
        ).fetchone()
        where_clause = None
        if sql_row and sql_row["sql"]:
            normalized = normalize_sql(sql_row["sql"])
            if " where " in normalized:
                where_clause = normalized.split(" where ", 1)[1]
        result[name] = {
            "unique": bool(row["unique"]),
            "columns": tuple(
                info["name"]
                for info in conn.execute(f"PRAGMA index_info({name})").fetchall()
            ),
            "where": where_clause,
            "origin": row["origin"],
        }
    return result


def row_count(conn: sqlite3.Connection, table_name: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()["count"])


def is_alias_pk_autoindex(index_name: str, meta: dict[str, object]) -> bool:
    return meta["origin"] == "pk" and index_name.startswith("sqlite_autoindex_login_identifier_aliases_")


def is_mapping_pk_autoindex(index_name: str, meta: dict[str, object]) -> bool:
    return meta["origin"] == "pk" and index_name.startswith("sqlite_autoindex_backend_principal_mappings_")


def is_forbidden_global_normalized_unique(index_name: str, meta: dict[str, object]) -> bool:
    if not bool(meta["unique"]):
        return False
    if index_name == "idx_login_identifier_aliases_active_exact_alias":
        return False
    columns = tuple(meta["columns"])
    where_clause = normalize_sql(meta["where"])
    if "normalized_lookup_key" not in columns:
        return False
    if columns == ALIAS_ALLOWED_PARTIAL_UNIQUE_COLUMNS and where_clause == ALIAS_ALLOWED_PARTIAL_UNIQUE_WHERE:
        return False
    return "global_identity_id" not in columns or where_clause != ALIAS_ALLOWED_PARTIAL_UNIQUE_WHERE


def validate_schema(conn: sqlite3.Connection) -> list[str]:
    issues: list[str] = []

    for table_name, expected in EXPECTED_TABLES.items():
        sql = table_sql(conn, table_name)
        if not sql:
            issues.append(f"missing_table:{table_name}")
            continue

        if strict_flag(conn, table_name) != bool(expected["strict"]):
            issues.append(f"wrong_strict:{table_name}")

        columns = table_info(conn, table_name)
        expected_columns = expected["columns"]
        if set(columns) != set(expected_columns):
            missing = sorted(set(expected_columns) - set(columns))
            extra = sorted(set(columns) - set(expected_columns))
            if missing:
                issues.append(f"missing_columns:{table_name}:{','.join(missing)}")
            if extra:
                issues.append(f"unexpected_columns:{table_name}:{','.join(extra)}")

        for column_name, column_expected in expected_columns.items():
            row = columns.get(column_name)
            if row is None:
                continue
            if str(row["type"]).upper() != str(column_expected["type"]).upper():
                issues.append(f"wrong_type:{table_name}:{column_name}")
            if int(row["notnull"]) != int(column_expected["notnull"]):
                issues.append(f"wrong_notnull:{table_name}:{column_name}")
            if int(row["pk"]) != int(column_expected["pk"]):
                issues.append(f"wrong_pk:{table_name}:{column_name}")
            if normalize_default(row["dflt_value"]) != normalize_default(column_expected["default"]):
                issues.append(f"wrong_default:{table_name}:{column_name}")

        normalized_table_sql = normalize_sql(sql)
        for fragment in expected.get("required_sql_fragments", ()):
            if fragment not in normalized_table_sql:
                issues.append(f"missing_sql_fragment:{table_name}:{fragment}")

        if row_count(conn, table_name) != int(expected["row_count"]):
            issues.append(f"unexpected_rows:{table_name}")

        expected_fks = expected.get("foreign_keys")
        if expected_fks is not None and foreign_keys(conn, table_name) != expected_fks:
            issues.append(f"wrong_foreign_keys:{table_name}")

        expected_indexes = expected.get("indexes")
        if expected_indexes is not None:
            actual_indexes = index_map(conn, table_name)
            for index_name, index_expected in expected_indexes.items():
                actual = actual_indexes.get(index_name)
                if actual is None:
                    issues.append(f"missing_index:{table_name}:{index_name}")
                    continue
                if bool(actual["unique"]) != bool(index_expected["unique"]):
                    issues.append(f"wrong_index_uniqueness:{table_name}:{index_name}")
                if tuple(actual["columns"]) != tuple(index_expected["columns"]):
                    issues.append(f"wrong_index_columns:{table_name}:{index_name}")
                expected_where = index_expected["where"]
                if normalize_sql(actual["where"]) != normalize_sql(expected_where):
                    issues.append(f"wrong_index_predicate:{table_name}:{index_name}")

            if table_name == ALIAS_TABLE_NAME:
                for index_name, meta in actual_indexes.items():
                    if is_alias_pk_autoindex(index_name, meta):
                        continue
                    if index_name not in ALIAS_ALLOWED_EXPLICIT_INDEXES:
                        issues.append(f"identity_registry_schema:unexpected_alias_index:{index_name}")
                    if is_forbidden_global_normalized_unique(index_name, meta):
                        issues.append(f"identity_registry_schema:forbidden_global_normalized_unique:{index_name}")

        expected_unique_sets = expected.get("unique_sets")
        if expected_unique_sets is not None:
            actual_indexes = index_map(conn, table_name)
            actual_unique_indexes = [
                (index_name, meta)
                for index_name, meta in actual_indexes.items()
                if meta["unique"] and not is_mapping_pk_autoindex(index_name, meta)
            ]
            actual_unique_sets = [tuple(meta["columns"]) for _, meta in actual_unique_indexes]
            actual_unique_set_lookup = set(actual_unique_sets)
            for unique_columns in expected_unique_sets:
                if unique_columns not in actual_unique_set_lookup:
                    issues.append(f"missing_unique:{table_name}:{','.join(unique_columns)}")
            if table_name == MAPPING_TABLE_NAME:
                for index_name, meta in actual_unique_indexes:
                    unique_columns = tuple(meta["columns"])
                    if unique_columns not in MAPPING_ALLOWED_UNIQUE_SETS:
                        issues.append(f"identity_registry_schema:unexpected_mapping_unique:{index_name}")
                if len(actual_unique_indexes) != len(MAPPING_ALLOWED_UNIQUE_SETS):
                    issues.append(
                        f"identity_registry_schema:unexpected_mapping_unique_count:{len(actual_unique_indexes)}"
                    )

    return issues


def create_valid_schema(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(VALID_SCHEMA_SQL)
    finally:
        conn.close()


def run_case(name: str, builder) -> tuple[str, bool, str | None]:
    with tempfile.TemporaryDirectory(prefix=f"identity-registry-{name}-") as tmpdir:
        fixture_path = Path(tmpdir) / "fixture.db"
        error_text: str | None = None
        try:
            builder(fixture_path)
            conn = open_readonly_connection(fixture_path)
            try:
                issues = validate_schema(conn)
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001
            issues = [f"inspection_error:{exc.__class__.__name__}"]
            error_text = repr(exc)
        passed = not issues
        return name, passed, error_text or ",".join(issues)


def build_missing_table(path: Path) -> None:
    create_valid_schema(path)
    conn = sqlite3.connect(path)
    try:
        conn.execute("DROP TABLE backend_principal_mappings")
    finally:
        conn.close()


def build_wrong_column(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            VALID_SCHEMA_SQL.replace("backend_principal_key ANY NOT NULL", "backend_principal_key TEXT NOT NULL")
        )
    finally:
        conn.close()


def build_wrong_default(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            VALID_SCHEMA_SQL.replace("registry_status TEXT NOT NULL DEFAULT 'disabled'", "registry_status TEXT NOT NULL DEFAULT 'active'")
        )
    finally:
        conn.close()


def build_non_strict(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(VALID_SCHEMA_SQL.replace(") STRICT;", ");"))
    finally:
        conn.close()


def build_wrong_fk(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            VALID_SCHEMA_SQL.replace("ON DELETE RESTRICT\n        ON UPDATE NO ACTION", "ON DELETE CASCADE\n        ON UPDATE CASCADE", 1)
        )
    finally:
        conn.close()


def build_wrong_check(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            VALID_SCHEMA_SQL.replace(
                "CHECK (typeof(backend_principal_key) = 'integer' AND backend_principal_key > 0)",
                "CHECK (backend_principal_key > 0)",
            )
        )
    finally:
        conn.close()


def build_wrong_unique(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            VALID_SCHEMA_SQL.replace("UNIQUE (global_identity_id, backend_kind)\n", "")
        )
    finally:
        conn.close()


def build_wrong_index(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            VALID_SCHEMA_SQL.replace(
                "CREATE INDEX idx_login_identifier_aliases_candidate_lookup",
                "CREATE INDEX idx_login_identifier_aliases_candidate_lookup_broken",
            )
        )
    finally:
        conn.close()


def build_wrong_predicate(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            VALID_SCHEMA_SQL.replace(
                "WHERE alias_status = 'active';",
                "WHERE alias_status IN ('active', 'disabled');",
            )
        )
    finally:
        conn.close()


def build_unexpected_row(path: Path) -> None:
    create_valid_schema(path)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "INSERT INTO global_identities (global_identity_id, registry_status, created_provenance, updated_provenance) VALUES (?, ?, ?, ?)",
            ("gid-1", "disabled", "self-test", "self-test"),
        )
        conn.commit()
    finally:
        conn.close()


def build_wrong_provenance(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            VALID_SCHEMA_SQL.replace(
                f"CHECK (trim_conformance_profile = '{TRIM_CONFORMANCE_PROFILE}')",
                "CHECK (trim_conformance_profile IN ('PY3146_UCD16_0_0_STRIP_V1', 'OTHER_PROFILE'))",
            )
        )
    finally:
        conn.close()


def build_invalid_file(path: Path) -> None:
    path.write_text("not a sqlite database", encoding="utf-8")


def build_forbidden_global_normalized_unique(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            VALID_SCHEMA_SQL
            + "\nCREATE UNIQUE INDEX idx_login_identifier_aliases_forbidden_global_norm\n"
            + "ON login_identifier_aliases (normalized_lookup_key);\n"
        )
    finally:
        conn.close()


def build_forbidden_profile_normalized_unique(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            VALID_SCHEMA_SQL
            + "\nCREATE UNIQUE INDEX idx_login_identifier_aliases_forbidden_profile_norm\n"
            + "ON login_identifier_aliases (normalization_profile, normalized_lookup_key);\n"
        )
    finally:
        conn.close()


def build_unexpected_alias_index(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            VALID_SCHEMA_SQL
            + "\nCREATE INDEX idx_login_identifier_aliases_unexpected_extra\n"
            + "ON login_identifier_aliases (raw_alias);\n"
        )
    finally:
        conn.close()


def build_unexpected_mapping_unique(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            VALID_SCHEMA_SQL
            + "\nCREATE UNIQUE INDEX idx_backend_principal_mappings_unexpected_extra\n"
            + "ON backend_principal_mappings (global_identity_id, mapping_status);\n"
        )
    finally:
        conn.close()


def run_self_test() -> int:
    cases = [
        ("valid_exact_schema", create_valid_schema, True),
        ("missing_table", build_missing_table, False),
        ("missing_wrong_column", build_wrong_column, False),
        ("wrong_default", build_wrong_default, False),
        ("non_strict_table", build_non_strict, False),
        ("wrong_fk", build_wrong_fk, False),
        ("wrong_check", build_wrong_check, False),
        ("wrong_unique", build_wrong_unique, False),
        ("wrong_index", build_wrong_index, False),
        ("wrong_partial_index_predicate", build_wrong_predicate, False),
        ("unexpected_registry_row", build_unexpected_row, False),
        ("unsupported_provenance_tuple_schema", build_wrong_provenance, False),
        ("forbidden_global_normalized_unique", build_forbidden_global_normalized_unique, False),
        ("forbidden_profile_normalized_unique", build_forbidden_profile_normalized_unique, False),
        ("unexpected_alias_index", build_unexpected_alias_index, False),
        ("unexpected_mapping_unique", build_unexpected_mapping_unique, False),
        ("schema_inspection_failure", build_invalid_file, False),
    ]
    failures: list[str] = []
    for name, builder, should_pass in cases:
        case_name, passed, details = run_case(name, builder)
        if passed != should_pass:
            failures.append(f"{case_name}:{details}")
    if failures:
        print("FAIL identity registry schema self-test:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(SELF_TEST_MARKER)
    return 0


def main() -> int:
    args = parse_args()
    if args.self_test:
        return run_self_test()

    db_path = resolve_db_path(args.db)
    conn = open_readonly_connection(db_path)
    try:
        issues = validate_schema(conn)
    finally:
        conn.close()

    print("identity_registry_schema_scope: sqlite_registry_schema_readonly")
    print(f"sqlite_path: {db_path}")
    print(f"issues_count: {len(issues)}")
    if issues:
        print("FAIL identity registry schema check:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print(PASS_MARKER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
