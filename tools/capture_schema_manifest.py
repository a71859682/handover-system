from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SERIALIZER_VERSION = "AUTH_ID_001E1_SCHEMA_MANIFEST_V1"
TRANSPORT_VERSION = "AUTH_ID_001E1_SCHEMA_MANIFEST_TRANSPORT_V1"
MANIFEST_ID_RECIPE = "sha256(canonical_json_bytes(manifest_payload_v1))"
MANIFEST_PAYLOAD_JSON_RECIPE = "json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))"
MANIFEST_PAYLOAD_ENCODING = "utf-8"
PASS_MARKER = "PASS schema manifest serializer self-test passed."
REGISTRY_TABLES = (
    "global_identities",
    "login_identifier_aliases",
    "backend_principal_mappings",
)
REGISTRY_EXPLICIT_INDEXES = (
    "idx_login_identifier_aliases_candidate_lookup",
    "idx_login_identifier_aliases_provenance_reconciliation",
    "idx_login_identifier_aliases_active_exact_alias",
)
BUSINESS_TABLES = (
    "extra_fields",
    "floors",
    "formal_approval_events",
    "formal_approvals",
    "meta",
    "progress",
    "scheduling_entries",
    "sheets",
    "sites",
    "tasks",
    "unit_extra",
    "unit_extra_values",
    "units",
    "user_site_permissions",
    "users",
    "vendor_accounts",
    "vendor_contacts",
    "vendor_work_entries",
)
WRITABLE_PRAGMAS = {
    "foreign_keys",
    "journal_mode",
    "locking_mode",
    "synchronous",
}
ALWAYS_DENIED_PRAGMAS = {
    "wal_checkpoint",
    "incremental_vacuum",
    "optimize",
}
REQUIRED_ARTIFACT_FILES = (
    "legacy_manifest_v1.json",
    "manifest_payload_v1.json",
    "manifest_checksums_v1.json",
)
REQUIRED_LEGACY_RECORD_KEYS = ("name", "sql", "tbl_name", "type")
CHECKSUM_OUTPUT_FILES = ("legacy_manifest_v1.json", "manifest_payload_v1.json")
REQUIRED_CHUNK_KEYS = ("length", "sequence", "sha256", "text")
REQUIRED_BUNDLE_ENTRY_KEYS = ("base64", "name", "sha256", "size")
REQUIRED_CHECKSUM_KEYS = (
    "legacy_manifest_sha256",
    "manifest_id",
    "manifest_id_recipe",
    "manifest_payload_sha256",
    "output_files",
    "serializer_version",
    "tool_source_sha256",
)
REQUIRED_CAPTURE_FIELDS = (
    "serializer_version",
    "manifest_id_recipe",
    "manifest_payload_json_recipe",
    "manifest_payload_encoding",
    "tool_source_sha256",
    "sqlite_runtime_version",
    "source_db_masked_identifier",
    "schema_version",
    "table_inventory",
    "index_inventory",
    "index_table_mapping",
    "legacy_manifest_sha256",
    "business_row_counts",
    "registry_object_presence",
    "registry_row_counts",
    "file_size",
    "mtime_ns",
    "sidecar_existence",
    "query_only_status",
    "authorizer_status",
    "total_changes_before",
    "total_changes_after",
    "write_attempts",
    "postgresql_attempts",
    "concurrent_runtime_change_observed",
    "file_size_after",
    "mtime_ns_after",
    "sidecar_existence_after",
)
WRITE_ACTION_CODES = {
    getattr(sqlite3, "SQLITE_INSERT", -1),
    getattr(sqlite3, "SQLITE_UPDATE", -1),
    getattr(sqlite3, "SQLITE_DELETE", -1),
    getattr(sqlite3, "SQLITE_CREATE_TABLE", -1),
    getattr(sqlite3, "SQLITE_CREATE_INDEX", -1),
    getattr(sqlite3, "SQLITE_CREATE_TRIGGER", -1),
    getattr(sqlite3, "SQLITE_CREATE_VIEW", -1),
    getattr(sqlite3, "SQLITE_DROP_TABLE", -1),
    getattr(sqlite3, "SQLITE_DROP_INDEX", -1),
    getattr(sqlite3, "SQLITE_DROP_TRIGGER", -1),
    getattr(sqlite3, "SQLITE_DROP_VIEW", -1),
    getattr(sqlite3, "SQLITE_ALTER_TABLE", -1),
    getattr(sqlite3, "SQLITE_ATTACH", -1),
    getattr(sqlite3, "SQLITE_DETACH", -1),
    getattr(sqlite3, "SQLITE_REINDEX", -1),
    getattr(sqlite3, "SQLITE_ANALYZE", -1),
    getattr(sqlite3, "SQLITE_CREATE_TEMP_TABLE", -1),
    getattr(sqlite3, "SQLITE_CREATE_TEMP_INDEX", -1),
    getattr(sqlite3, "SQLITE_CREATE_TEMP_TRIGGER", -1),
    getattr(sqlite3, "SQLITE_CREATE_TEMP_VIEW", -1),
    getattr(sqlite3, "SQLITE_DROP_TEMP_TABLE", -1),
    getattr(sqlite3, "SQLITE_DROP_TEMP_INDEX", -1),
    getattr(sqlite3, "SQLITE_DROP_TEMP_TRIGGER", -1),
    getattr(sqlite3, "SQLITE_DROP_TEMP_VIEW", -1),
}
WRITE_ACTION_CODES.discard(-1)


@dataclass
class FileState:
    size: int
    mtime_ns: int
    sidecars: dict[str, bool]


class GuardedConnection:
    def __init__(self, db_path: Path, *, readonly: bool = True) -> None:
        self.db_path = db_path
        self.write_attempts = 0
        self.authorizer_enabled = False
        self.readonly = readonly
        if readonly:
            self.conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        else:
            self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA query_only=1")
        self.authorizer_enabled = True
        self.conn.set_authorizer(self._authorizer)

    def _authorizer(self, action: int, arg1: str | None, arg2: str | None, db_name: str | None, source: str | None) -> int:
        del db_name, source
        denied = getattr(sqlite3, "SQLITE_DENY", 1)
        ok = getattr(sqlite3, "SQLITE_OK", 0)
        if action in WRITE_ACTION_CODES:
            self.write_attempts += 1
            return denied
        if action == getattr(sqlite3, "SQLITE_PRAGMA", 19):
            pragma_name = (arg1 or "").lower()
            if pragma_name in ALWAYS_DENIED_PRAGMAS:
                self.write_attempts += 1
                return denied
            if pragma_name in WRITABLE_PRAGMAS and arg2 is not None:
                self.write_attempts += 1
                return denied
        return ok

    def close(self) -> None:
        self.conn.close()

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture, compare, and transport schema manifest artifacts.")
    subparsers = parser.add_subparsers(dest="command")

    capture = subparsers.add_parser("capture", help="Capture manifest artifacts from a read-only SQLite database.")
    capture.add_argument("--db", type=Path, required=True, help="Explicit SQLite database path.")
    capture.add_argument("--output-dir", type=Path, required=True, help="Explicit output directory for artifacts.")

    compare = subparsers.add_parser("compare", help="Compare two manifest artifact directories.")
    compare.add_argument("--pre-dir", type=Path, required=True, help="Baseline artifact directory.")
    compare.add_argument("--post-dir", type=Path, required=True, help="Candidate artifact directory.")

    pack = subparsers.add_parser("pack-transport", help="Create a binary-safe transport bundle from artifact files.")
    pack.add_argument("--input-dir", type=Path, required=True, help="Artifact directory to pack.")
    pack.add_argument("--output-dir", type=Path, required=True, help="Output directory for transport files.")
    pack.add_argument("--chunk-size", type=int, default=1024, help="Fixed chunk size in ASCII characters.")

    reconstruct = subparsers.add_parser("reconstruct-transport", help="Reconstruct artifacts from a transport bundle.")
    reconstruct.add_argument("--transport-file", type=Path, required=True, help="Transport JSON produced by pack-transport.")
    reconstruct.add_argument("--output-dir", type=Path, required=True, help="Output directory for reconstructed artifacts.")

    parser.add_argument("--self-test", action="store_true", help="Run disposable self-tests.")
    return parser.parse_args()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_state(db_path: Path) -> FileState:
    stat = db_path.stat()
    return FileState(
        size=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        sidecars={
            "journal": Path(f"{db_path}-journal").exists(),
            "wal": Path(f"{db_path}-wal").exists(),
            "shm": Path(f"{db_path}-shm").exists(),
        },
    )


def tool_source_sha256() -> str:
    return sha256_hex(Path(__file__).read_bytes())


def masked_source_db_identifier(db_path: Path) -> str:
    resolved = str(db_path.resolve())
    masked = sha256_hex(resolved.encode("utf-8"))[:16]
    return f"path:{db_path.name}:{masked}"


def ensure_capture_paths(db_path: Path, output_dir: Path) -> tuple[Path, Path]:
    resolved_db = db_path.resolve()
    if not resolved_db.exists():
        raise SystemExit(f"FAIL source DB does not exist: {resolved_db}")
    resolved_output = output_dir.resolve()
    db_dir = resolved_db.parent
    if resolved_output == db_dir or db_dir in resolved_output.parents:
        raise SystemExit("FAIL output directory must not be inside the source DB directory.")
    resolved_output.mkdir(parents=True, exist_ok=True)
    return resolved_db, resolved_output


def fetch_master_rows(conn: sqlite3.Connection, sql: str) -> list[sqlite3.Row]:
    return list(conn.execute(sql))


def project_legacy_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": record["type"],
        "name": record["name"],
        "tbl_name": record["tbl_name"],
        "sql": record["sql"],
    }


def build_index_inventory(conn: sqlite3.Connection, table_inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index_rows = fetch_master_rows(
        conn,
        "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE type='index' ORDER BY name, tbl_name",
    )
    inventory: list[dict[str, Any]] = []
    for row in index_rows:
        idx_meta = conn.execute(f"PRAGMA index_list('{row['tbl_name']}')").fetchall()
        meta = next((item for item in idx_meta if item["name"] == row["name"]), None)
        inventory.append(
            {
                "type": row["type"],
                "name": row["name"],
                "tbl_name": row["tbl_name"],
                "sql": row["sql"],
                "unique": int(meta["unique"]) if meta else 0,
                "origin": str(meta["origin"]) if meta else "",
                "partial": int(meta["partial"]) if meta else 0,
            }
        )
    inventory.sort(key=lambda item: (item["name"], item["tbl_name"]))
    return inventory


def build_capture_payload(db_path: Path) -> tuple[dict[str, Any], bytes, bytes]:
    before = file_state(db_path)
    guarded = GuardedConnection(db_path)
    try:
        conn = guarded.conn
        total_changes_before = conn.total_changes
        schema_version = conn.execute("PRAGMA schema_version").fetchone()[0]
        query_only_status = conn.execute("PRAGMA query_only").fetchone()[0]

        table_rows = fetch_master_rows(
            conn,
            "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name",
        )
        table_inventory = [
            {
                "type": row["type"],
                "name": row["name"],
                "tbl_name": row["tbl_name"],
                "sql": row["sql"],
            }
            for row in table_rows
        ]
        all_tables = [row["name"] for row in table_rows]
        legacy_tables = [name for name in all_tables if name not in REGISTRY_TABLES]

        index_inventory = build_index_inventory(conn, table_inventory)
        index_table_mapping = [{"name": row["name"], "tbl_name": row["tbl_name"]} for row in index_inventory]
        legacy_records = [
            project_legacy_record(row) for row in table_inventory if row["name"] in legacy_tables
        ] + [
            project_legacy_record(row) for row in index_inventory if row["tbl_name"] in legacy_tables
        ]
        legacy_records.sort(key=lambda item: (item["type"], item["name"], item["tbl_name"]))
        legacy_manifest_bytes = canonical_json_bytes(legacy_records)
        legacy_manifest_sha256 = sha256_hex(legacy_manifest_bytes)

        business_row_counts = {
            table: int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in BUSINESS_TABLES
            if table in all_tables
        }
        registry_object_presence = {
            "tables": {table: table in all_tables for table in REGISTRY_TABLES},
            "explicit_indexes": {
                name: any(item["name"] == name for item in index_inventory)
                for name in REGISTRY_EXPLICIT_INDEXES
            },
        }
        registry_row_counts = {
            table: int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            if table in all_tables
            else None
            for table in REGISTRY_TABLES
        }

        total_changes_after = conn.total_changes
        after = file_state(db_path)
    finally:
        guarded.close()

    payload = {
        "serializer_version": SERIALIZER_VERSION,
        "manifest_id_recipe": MANIFEST_ID_RECIPE,
        "manifest_payload_json_recipe": MANIFEST_PAYLOAD_JSON_RECIPE,
        "manifest_payload_encoding": MANIFEST_PAYLOAD_ENCODING,
        "tool_source_sha256": tool_source_sha256(),
        "sqlite_runtime_version": sqlite3.sqlite_version,
        "source_db_masked_identifier": masked_source_db_identifier(db_path),
        "schema_version": schema_version,
        "table_inventory": table_inventory,
        "index_inventory": index_inventory,
        "index_table_mapping": index_table_mapping,
        "legacy_manifest_sha256": legacy_manifest_sha256,
        "business_row_counts": business_row_counts,
        "registry_object_presence": registry_object_presence,
        "registry_row_counts": registry_row_counts,
        "file_size": before.size,
        "mtime_ns": before.mtime_ns,
        "sidecar_existence": before.sidecars,
        "query_only_status": int(query_only_status),
        "authorizer_status": {"enabled": True},
        "total_changes_before": total_changes_before,
        "total_changes_after": total_changes_after,
        "write_attempts": guarded.write_attempts,
        "postgresql_attempts": 0,
        "concurrent_runtime_change_observed": int(
            before.size != after.size or before.mtime_ns != after.mtime_ns or before.sidecars != after.sidecars
        ),
        "file_size_after": after.size,
        "mtime_ns_after": after.mtime_ns,
        "sidecar_existence_after": after.sidecars,
    }
    payload_bytes = canonical_json_bytes(payload)
    return payload, legacy_manifest_bytes, payload_bytes


def write_capture_artifacts(db_path: Path, output_dir: Path) -> dict[str, Any]:
    resolved_db, resolved_output = ensure_capture_paths(db_path, output_dir)
    payload, legacy_manifest_bytes, payload_bytes = build_capture_payload(resolved_db)
    manifest_id = sha256_hex(payload_bytes)
    checksums = {
        "serializer_version": SERIALIZER_VERSION,
        "manifest_id": manifest_id,
        "tool_source_sha256": payload["tool_source_sha256"],
        "legacy_manifest_sha256": sha256_hex(legacy_manifest_bytes),
        "manifest_payload_sha256": sha256_hex(payload_bytes),
        "manifest_id_recipe": payload["manifest_id_recipe"],
        "output_files": {
            "legacy_manifest_v1.json": {
                "size": len(legacy_manifest_bytes),
                "sha256": sha256_hex(legacy_manifest_bytes),
            },
            "manifest_payload_v1.json": {
                "size": len(payload_bytes),
                "sha256": sha256_hex(payload_bytes),
            },
        },
    }
    checksums_bytes = canonical_json_bytes(checksums)

    (resolved_output / "legacy_manifest_v1.json").write_bytes(legacy_manifest_bytes)
    (resolved_output / "manifest_payload_v1.json").write_bytes(payload_bytes)
    (resolved_output / "manifest_checksums_v1.json").write_bytes(checksums_bytes)

    return {
        "serializer_version": SERIALIZER_VERSION,
        "manifest_id": manifest_id,
        "legacy_manifest_sha256": checksums["output_files"]["legacy_manifest_v1.json"]["sha256"],
        "manifest_payload_sha256": checksums["output_files"]["manifest_payload_v1.json"]["sha256"],
        "manifest_checksums_sha256": sha256_hex(checksums_bytes),
        "output_dir": str(resolved_output),
        "artifact_files": list(REQUIRED_ARTIFACT_FILES),
        "source_db_unchanged": (
            payload["file_size"] == payload["file_size_after"]
            and payload["mtime_ns"] == payload["mtime_ns_after"]
            and payload["sidecar_existence"] == payload["sidecar_existence_after"]
            and payload["write_attempts"] == 0
            and payload["postgresql_attempts"] == 0
        ),
    }


def parse_json_bytes(data: bytes, label: str) -> Any:
    try:
        return json.loads(data)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"FAIL invalid JSON in {label}: {exc}") from exc


def validate_legacy_records(legacy_records: Any) -> None:
    if not isinstance(legacy_records, list):
        raise SystemExit("FAIL legacy manifest must be a list.")
    seen_keys: set[tuple[str, str, str]] = set()
    observed_keys: list[tuple[str, str, str]] = []
    for index, record in enumerate(legacy_records):
        if not isinstance(record, dict):
            raise SystemExit(f"FAIL legacy record at index {index} must be an object.")
        if tuple(sorted(record.keys())) != REQUIRED_LEGACY_RECORD_KEYS:
            raise SystemExit(f"FAIL legacy record at index {index} must contain exactly type,name,tbl_name,sql.")
        if record["type"] not in {"table", "index"}:
            raise SystemExit(f"FAIL legacy record at index {index} has invalid type: {record['type']!r}")
        if not isinstance(record["name"], str) or not record["name"]:
            raise SystemExit(f"FAIL legacy record at index {index} must have non-empty string name.")
        if not isinstance(record["tbl_name"], str) or not record["tbl_name"]:
            raise SystemExit(f"FAIL legacy record at index {index} must have non-empty string tbl_name.")
        if record["sql"] is not None and not isinstance(record["sql"], str):
            raise SystemExit(f"FAIL legacy record at index {index} sql must be string or null.")
        key = (record["type"], record["name"], record["tbl_name"])
        if key in seen_keys:
            raise SystemExit(f"FAIL duplicate legacy record key detected: {key}.")
        seen_keys.add(key)
        observed_keys.append(key)
    if observed_keys != sorted(observed_keys):
        raise SystemExit("FAIL legacy manifest records must be sorted by (type,name,tbl_name).")


def validate_artifact_set_names(names: list[str], context: str) -> None:
    for name in names:
        candidate = Path(name)
        if candidate.is_absolute() or ".." in candidate.parts or len(candidate.parts) != 1:
            raise SystemExit(f"FAIL invalid artifact path in {context}: {name}")
    if len(names) != len(set(names)):
        raise SystemExit(f"FAIL duplicate artifact file name detected in {context}.")
    if sorted(names) != sorted(REQUIRED_ARTIFACT_FILES):
        raise SystemExit(f"FAIL artifact file set mismatch in {context}.")


def validate_manifest_dir_data(directory: Path, files: dict[str, bytes]) -> dict[str, Any]:
    if sorted(files.keys()) != sorted(REQUIRED_ARTIFACT_FILES):
        raise SystemExit(f"FAIL required files mismatch in artifact directory: {directory}")
    payload = parse_json_bytes(files["manifest_payload_v1.json"], "manifest_payload_v1.json")
    checksums = parse_json_bytes(files["manifest_checksums_v1.json"], "manifest_checksums_v1.json")
    legacy_records = parse_json_bytes(files["legacy_manifest_v1.json"], "legacy_manifest_v1.json")
    if canonical_json_bytes(payload) != files["manifest_payload_v1.json"]:
        raise SystemExit("FAIL manifest_payload_v1.json is not canonical JSON.")
    if canonical_json_bytes(checksums) != files["manifest_checksums_v1.json"]:
        raise SystemExit("FAIL manifest_checksums_v1.json is not canonical JSON.")
    if canonical_json_bytes(legacy_records) != files["legacy_manifest_v1.json"]:
        raise SystemExit("FAIL legacy_manifest_v1.json is not canonical JSON.")
    if payload.get("serializer_version") != SERIALIZER_VERSION:
        raise SystemExit("FAIL unsupported serializer version in manifest payload.")
    if checksums.get("serializer_version") != SERIALIZER_VERSION:
        raise SystemExit("FAIL unsupported serializer version in manifest checksums.")
    if set(payload.keys()) != set(REQUIRED_CAPTURE_FIELDS):
        missing_fields = sorted(set(REQUIRED_CAPTURE_FIELDS) - set(payload.keys()))
        unexpected_fields = sorted(set(payload.keys()) - set(REQUIRED_CAPTURE_FIELDS))
        raise SystemExit(f"FAIL manifest payload key set mismatch: missing={missing_fields} unexpected={unexpected_fields}")
    if set(checksums.keys()) != set(REQUIRED_CHECKSUM_KEYS):
        missing_fields = sorted(set(REQUIRED_CHECKSUM_KEYS) - set(checksums.keys()))
        unexpected_fields = sorted(set(checksums.keys()) - set(REQUIRED_CHECKSUM_KEYS))
        raise SystemExit(f"FAIL manifest checksums key set mismatch: missing={missing_fields} unexpected={unexpected_fields}")
    validate_legacy_records(legacy_records)
    if tuple(sorted(checksums.get("output_files", {}).keys())) != CHECKSUM_OUTPUT_FILES:
        raise SystemExit("FAIL manifest checksums output_files must contain exactly legacy_manifest_v1.json and manifest_payload_v1.json.")
    if payload["manifest_id_recipe"] != MANIFEST_ID_RECIPE or checksums["manifest_id_recipe"] != MANIFEST_ID_RECIPE:
        raise SystemExit("FAIL manifest ID recipe mismatch.")
    if payload["manifest_payload_json_recipe"] != MANIFEST_PAYLOAD_JSON_RECIPE:
        raise SystemExit("FAIL manifest payload JSON recipe mismatch.")
    if payload["manifest_payload_encoding"] != MANIFEST_PAYLOAD_ENCODING:
        raise SystemExit("FAIL manifest payload encoding mismatch.")
    if checksums["manifest_id"] != sha256_hex(files["manifest_payload_v1.json"]):
        raise SystemExit("FAIL manifest ID mismatch against payload bytes.")
    if payload["legacy_manifest_sha256"] != sha256_hex(files["legacy_manifest_v1.json"]):
        raise SystemExit("FAIL legacy manifest hash mismatch against payload.")
    if checksums.get("manifest_payload_sha256") != sha256_hex(files["manifest_payload_v1.json"]):
        raise SystemExit("FAIL manifest payload hash mismatch against checksums.")
    if checksums.get("legacy_manifest_sha256") != sha256_hex(files["legacy_manifest_v1.json"]):
        raise SystemExit("FAIL legacy manifest hash mismatch against checksums.")
    if checksums["tool_source_sha256"] != payload["tool_source_sha256"]:
        raise SystemExit("FAIL tool source hash mismatch between payload and checksums.")
    if checksums["legacy_manifest_sha256"] != payload["legacy_manifest_sha256"]:
        raise SystemExit("FAIL legacy manifest hash cross-field mismatch.")
    if checksums["manifest_id_recipe"] != payload["manifest_id_recipe"]:
        raise SystemExit("FAIL manifest recipe cross-field mismatch.")
    for name in CHECKSUM_OUTPUT_FILES:
        entry = checksums["output_files"][name]
        if not isinstance(entry, dict) or set(entry.keys()) != {"sha256", "size"}:
            raise SystemExit(f"FAIL invalid checksum entry format for {name}.")
        if entry["size"] != len(files[name]):
            raise SystemExit(f"FAIL artifact size mismatch for {name}.")
        if entry["sha256"] != sha256_hex(files[name]):
            raise SystemExit(f"FAIL artifact hash mismatch for {name}.")
    return {
        "payload": payload,
        "checksums": checksums,
        "legacy_records": legacy_records,
    }


def load_manifest_dir(directory: Path) -> dict[str, Any]:
    resolved = directory.resolve()
    actual_files = sorted(path.name for path in resolved.iterdir() if path.is_file()) if resolved.exists() else []
    validate_artifact_set_names(actual_files, str(resolved))
    files: dict[str, bytes] = {}
    for name in REQUIRED_ARTIFACT_FILES:
        path = resolved / name
        if not path.exists():
            raise SystemExit(f"FAIL missing artifact file: {path}")
        files[name] = path.read_bytes()
    validated = validate_manifest_dir_data(resolved, files)
    return {
        "dir": resolved,
        "legacy_bytes": files["legacy_manifest_v1.json"],
        "payload_bytes": files["manifest_payload_v1.json"],
        "checksums_bytes": files["manifest_checksums_v1.json"],
        "payload": validated["payload"],
        "checksums": validated["checksums"],
        "legacy_records": validated["legacy_records"],
    }


def classify_compare(pre: dict[str, Any], post: dict[str, Any]) -> dict[str, Any]:
    pre_payload = pre["payload"]
    post_payload = post["payload"]
    pre_legacy_bytes = pre["legacy_bytes"]
    post_legacy_bytes = post["legacy_bytes"]
    pre_legacy_records = pre["legacy_records"]
    post_legacy_records = post["legacy_records"]

    classifications: list[str] = []
    semantic_comparison_performed = True
    if (
        pre_payload["serializer_version"] != post_payload["serializer_version"]
        or pre_payload["tool_source_sha256"] != post_payload["tool_source_sha256"]
        or pre_payload["manifest_id_recipe"] != post_payload["manifest_id_recipe"]
        or pre_payload["manifest_payload_json_recipe"] != post_payload["manifest_payload_json_recipe"]
        or pre_payload["manifest_payload_encoding"] != post_payload["manifest_payload_encoding"]
    ):
        classifications.append("serializer/version mismatch")
        semantic_comparison_performed = False

    missing = []
    extra = []
    changed = []
    business_diffs = {}
    registry_count_diffs = {}
    if semantic_comparison_performed:
        pre_by_key = {(item["type"], item["name"], item["tbl_name"]): item for item in pre_legacy_records}
        post_by_key = {(item["type"], item["name"], item["tbl_name"]): item for item in post_legacy_records}
        missing = [pre_by_key[key] for key in sorted(pre_by_key.keys() - post_by_key.keys())]
        extra = [post_by_key[key] for key in sorted(post_by_key.keys() - pre_by_key.keys())]
        for key in sorted(pre_by_key.keys() & post_by_key.keys()):
            if pre_by_key[key]["sql"] != post_by_key[key]["sql"]:
                changed.append(
                    {
                        "type": key[0],
                        "name": key[1],
                        "tbl_name": key[2],
                        "pre_sql": pre_by_key[key]["sql"],
                        "post_sql": post_by_key[key]["sql"],
                    }
                )
        for key in sorted(set(pre_payload["business_row_counts"].keys()) | set(post_payload["business_row_counts"].keys())):
            pre_value = pre_payload["business_row_counts"].get(key)
            post_value = post_payload["business_row_counts"].get(key)
            if post_value != pre_value:
                business_diffs[key] = {"pre": pre_value, "post": post_value}
        for key in sorted(set(pre_payload["registry_row_counts"].keys()) | set(post_payload["registry_row_counts"].keys())):
            pre_value = pre_payload["registry_row_counts"].get(key)
            post_value = post_payload["registry_row_counts"].get(key)
            if post_value != pre_value:
                registry_count_diffs[key] = {"pre": pre_value, "post": post_value}
        if missing or extra or changed or pre_legacy_bytes != post_legacy_bytes:
            classifications.append("legacy schema drift")
        if business_diffs:
            classifications.append("business data drift")
        if pre_payload["concurrent_runtime_change_observed"] or post_payload["concurrent_runtime_change_observed"]:
            classifications.append("concurrent runtime change")
        pre_registry_presence = pre_payload["registry_object_presence"]
        post_registry_presence = post_payload["registry_object_presence"]
        pre_registry_absent = not any(pre_registry_presence["tables"].values()) and not any(pre_registry_presence["explicit_indexes"].values())
        post_registry_present = all(post_registry_presence["tables"].values()) and all(post_registry_presence["explicit_indexes"].values())
        registry_only_expected = (
            pre_registry_absent
            and post_registry_present
            and pre_payload["legacy_manifest_sha256"] == post_payload["legacy_manifest_sha256"]
            and not business_diffs
            and post_payload["schema_version"] - pre_payload["schema_version"] == 6
        )
        if registry_only_expected:
            classifications.append("expected registry-only schema delta")
        if not classifications:
            classifications.append("identical")

    return {
        "serializer_version_pre": pre_payload["serializer_version"],
        "serializer_version_post": post_payload["serializer_version"],
        "tool_source_sha256_pre": pre_payload["tool_source_sha256"],
        "tool_source_sha256_post": post_payload["tool_source_sha256"],
        "semantic_comparison_performed": semantic_comparison_performed,
        "legacy_manifest_byte_equality": pre_legacy_bytes == post_legacy_bytes,
        "legacy_manifest_sha256_pre": pre_payload["legacy_manifest_sha256"],
        "legacy_manifest_sha256_post": post_payload["legacy_manifest_sha256"],
        "missing_legacy_records": missing,
        "extra_legacy_records": extra,
        "changed_legacy_records": changed,
        "table_inventory_pre": pre_payload["table_inventory"],
        "table_inventory_post": post_payload["table_inventory"],
        "index_inventory_pre": pre_payload["index_inventory"],
        "index_inventory_post": post_payload["index_inventory"],
        "index_table_mapping_pre": pre_payload["index_table_mapping"],
        "index_table_mapping_post": post_payload["index_table_mapping"],
        "business_row_count_differences": business_diffs,
        "registry_object_delta": {
            "pre": pre_payload["registry_object_presence"],
            "post": post_payload["registry_object_presence"],
        },
        "registry_row_count_differences": registry_count_diffs,
        "schema_version_delta": {
            "pre": pre_payload["schema_version"],
            "post": post_payload["schema_version"],
            "delta": post_payload["schema_version"] - pre_payload["schema_version"],
        },
        "classifications": classifications,
    }


def build_transport_bundle(input_dir: Path, chunk_size: int) -> dict[str, Any]:
    if chunk_size <= 0:
        raise SystemExit("FAIL chunk size must be positive.")
    validated = load_manifest_dir(input_dir)
    bundle_files = []
    for name in REQUIRED_ARTIFACT_FILES:
        data = {
            "legacy_manifest_v1.json": validated["legacy_bytes"],
            "manifest_payload_v1.json": validated["payload_bytes"],
            "manifest_checksums_v1.json": validated["checksums_bytes"],
        }[name]
        bundle_files.append(
            {
                "name": name,
                "size": len(data),
                "sha256": sha256_hex(data),
                "base64": base64.b64encode(data).decode("ascii"),
            }
        )
    bundle_files.sort(key=lambda item: item["name"])
    bundle_bytes = canonical_json_bytes(
        {
            "transport_version": TRANSPORT_VERSION,
            "serializer_version": SERIALIZER_VERSION,
            "files": bundle_files,
        }
    )
    compressed_bytes = gzip.compress(bundle_bytes, compresslevel=9, mtime=0)
    payload_ascii = base64.b64encode(compressed_bytes).decode("ascii")
    chunks = []
    for start in range(0, len(payload_ascii), chunk_size):
        text = payload_ascii[start : start + chunk_size]
        chunks.append(
            {
                "sequence": len(chunks) + 1,
                "length": len(text),
                "sha256": sha256_hex(text.encode("ascii")),
                "text": text,
            }
        )
    return {
        "transport_version": TRANSPORT_VERSION,
        "serializer_version": SERIALIZER_VERSION,
        "chunk_size": chunk_size,
        "total_chunk_count": len(chunks),
        "concatenated_payload_length": len(payload_ascii),
        "concatenated_payload_sha256": sha256_hex(payload_ascii.encode("ascii")),
        "decoded_bundle_sha256": sha256_hex(bundle_bytes),
        "compressed_payload_ascii_sha256": sha256_hex(payload_ascii.encode("ascii")),
        "compressed_payload_character_length": len(payload_ascii),
        "chunks": chunks,
    }


def verify_chunk_sequences(chunks: list[dict[str, Any]], chunk_size: int) -> str:
    if not isinstance(chunk_size, int) or chunk_size <= 0:
        raise SystemExit("FAIL invalid chunk size.")
    sequences = [chunk["sequence"] for chunk in chunks]
    if len(sequences) != len(set(sequences)):
        raise SystemExit("FAIL duplicate chunk sequence detected.")
    if sequences != list(range(1, len(chunks) + 1)):
        raise SystemExit("FAIL missing or reordered chunk sequence detected.")
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict) or tuple(sorted(chunk.keys())) != REQUIRED_CHUNK_KEYS:
            raise SystemExit("FAIL malformed chunk object.")
        if not isinstance(chunk["sequence"], int) or not isinstance(chunk["length"], int):
            raise SystemExit("FAIL malformed chunk object.")
        if not isinstance(chunk["sha256"], str) or not isinstance(chunk["text"], str):
            raise SystemExit("FAIL malformed chunk object.")
        text = chunk["text"]
        if len(text) != chunk["length"]:
            raise SystemExit(f"FAIL chunk length mismatch at sequence {chunk['sequence']}.")
        expected_length = chunk_size if index < len(chunks) - 1 else len(text)
        if index < len(chunks) - 1 and len(text) != chunk_size:
            raise SystemExit(f"FAIL non-final chunk length mismatch at sequence {chunk['sequence']}.")
        if index == len(chunks) - 1 and (len(text) < 1 or len(text) > chunk_size):
            raise SystemExit(f"FAIL final chunk length mismatch at sequence {chunk['sequence']}.")
        if sha256_hex(text.encode("ascii")) != chunk["sha256"]:
            raise SystemExit(f"FAIL chunk hash mismatch at sequence {chunk['sequence']}.")
    return "".join(chunk["text"] for chunk in chunks)


def reconstruct_transport(transport_file: Path, output_dir: Path) -> dict[str, Any]:
    transport = parse_json_bytes(transport_file.read_bytes(), str(transport_file))
    required_transport_keys = {
        "chunk_size",
        "chunks",
        "compressed_payload_ascii_sha256",
        "compressed_payload_character_length",
        "concatenated_payload_length",
        "concatenated_payload_sha256",
        "decoded_bundle_sha256",
        "serializer_version",
        "total_chunk_count",
        "transport_version",
    }
    if set(transport.keys()) != required_transport_keys:
        raise SystemExit("FAIL malformed transport envelope.")
    if transport.get("transport_version") != TRANSPORT_VERSION:
        raise SystemExit("FAIL unsupported transport version.")
    if transport.get("serializer_version") != SERIALIZER_VERSION:
        raise SystemExit("FAIL unsupported serializer version.")
    if not isinstance(transport["chunks"], list):
        raise SystemExit("FAIL malformed transport envelope.")
    if transport["total_chunk_count"] != len(transport["chunks"]):
        raise SystemExit("FAIL incorrect total chunk count.")
    payload_ascii = verify_chunk_sequences(transport["chunks"], transport["chunk_size"])
    if len(payload_ascii) != transport["concatenated_payload_length"]:
        raise SystemExit("FAIL payload length mismatch.")
    if transport["compressed_payload_character_length"] != len(payload_ascii):
        raise SystemExit("FAIL incorrect compressed payload character length.")
    if sha256_hex(payload_ascii.encode("ascii")) != transport["concatenated_payload_sha256"]:
        raise SystemExit("FAIL payload hash mismatch.")
    if transport["compressed_payload_ascii_sha256"] != transport["concatenated_payload_sha256"]:
        raise SystemExit("FAIL incorrect compressed payload ASCII hash.")
    try:
        compressed_bytes = base64.b64decode(payload_ascii.encode("ascii"), validate=True)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"FAIL invalid base64 payload: {exc}") from exc
    try:
        bundle_bytes = gzip.decompress(compressed_bytes)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"FAIL decompression error: {exc}") from exc
    if sha256_hex(bundle_bytes) != transport["decoded_bundle_sha256"]:
        raise SystemExit("FAIL decompressed bundle hash mismatch.")
    bundle = parse_json_bytes(bundle_bytes, "transport bundle")
    if bundle.get("transport_version") != TRANSPORT_VERSION:
        raise SystemExit("FAIL unsupported transport version in decoded bundle.")
    if bundle.get("serializer_version") != SERIALIZER_VERSION:
        raise SystemExit("FAIL unsupported serializer version.")
    entries = bundle.get("files")
    if not isinstance(entries, list):
        raise SystemExit("FAIL transport bundle files must be a list.")
    validate_artifact_set_names([str(entry.get("name", "")) for entry in entries], "decoded bundle")
    reconstructed_files: dict[str, bytes] = {}
    for entry in bundle["files"]:
        if not isinstance(entry, dict) or tuple(sorted(entry.keys())) != REQUIRED_BUNDLE_ENTRY_KEYS:
            raise SystemExit("FAIL malformed bundle entry.")
        if not isinstance(entry["name"], str) or not isinstance(entry["base64"], str):
            raise SystemExit("FAIL malformed bundle entry.")
        if not isinstance(entry["size"], int) or entry["size"] < 0 or not isinstance(entry["sha256"], str):
            raise SystemExit("FAIL malformed bundle entry.")
        try:
            data = base64.b64decode(entry["base64"].encode("ascii"), validate=True)
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"FAIL corrupted artifact payload: {exc}") from exc
        if len(data) != entry["size"] or sha256_hex(data) != entry["sha256"]:
            raise SystemExit(f"FAIL corrupted artifact payload for {entry['name']}.")
        reconstructed_files[entry["name"]] = data
    validate_manifest_dir_data(output_dir.resolve(), reconstructed_files)
    output_dir.mkdir(parents=True, exist_ok=True)
    written = {}
    for name in REQUIRED_ARTIFACT_FILES:
        data = reconstructed_files[name]
        (output_dir / name).write_bytes(data)
        written[name] = {"size": len(data), "sha256": sha256_hex(data)}
    return {
        "serializer_version": SERIALIZER_VERSION,
        "reconstructed_files": written,
        "output_dir": str(output_dir.resolve()),
    }


def create_sample_sqlite(path: Path, *, include_registry: bool = False, reorder_legacy: bool = False, business_variant: bool = False) -> None:
    conn = sqlite3.connect(path)
    legacy_table_statements = [
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);",
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, role TEXT NOT NULL);",
        "CREATE TABLE sheets (id INTEGER PRIMARY KEY, name TEXT NOT NULL);",
        "CREATE TABLE sites (id INTEGER PRIMARY KEY, name TEXT NOT NULL);",
        "CREATE TABLE tasks (id INTEGER PRIMARY KEY, sheet_id INTEGER NOT NULL, name TEXT NOT NULL);",
        "CREATE TABLE floors (id INTEGER PRIMARY KEY, sheet_id INTEGER NOT NULL, name TEXT NOT NULL);",
        "CREATE TABLE units (id INTEGER PRIMARY KEY, floor_id INTEGER NOT NULL, name TEXT NOT NULL);",
        "CREATE TABLE progress (unit_id INTEGER NOT NULL, task_id INTEGER NOT NULL, value TEXT NOT NULL, PRIMARY KEY (unit_id, task_id));",
        "CREATE TABLE extra_fields (id INTEGER PRIMARY KEY, sheet_id INTEGER NOT NULL, field_key TEXT NOT NULL UNIQUE, name TEXT NOT NULL);",
        "CREATE TABLE unit_extra (unit_id INTEGER PRIMARY KEY, handover TEXT NOT NULL DEFAULT 'X');",
        "CREATE TABLE unit_extra_values (unit_id INTEGER NOT NULL, field_key TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY (unit_id, field_key));",
        "CREATE TABLE vendor_accounts (id INTEGER PRIMARY KEY, vendor_name TEXT NOT NULL UNIQUE);",
        "CREATE TABLE vendor_contacts (id INTEGER PRIMARY KEY, sheet_id INTEGER NOT NULL, vendor_name TEXT NOT NULL, contact_name TEXT NOT NULL);",
        "CREATE TABLE vendor_work_entries (id INTEGER PRIMARY KEY, sheet_id INTEGER NOT NULL, vendor_name TEXT NOT NULL, business_date TEXT NOT NULL);",
        "CREATE TABLE formal_approvals (id INTEGER PRIMARY KEY, sheet_id INTEGER NOT NULL, action TEXT NOT NULL);",
        "CREATE TABLE formal_approval_events (id INTEGER PRIMARY KEY, approval_id INTEGER NOT NULL, event_type TEXT NOT NULL);",
        "CREATE TABLE scheduling_entries (id INTEGER PRIMARY KEY, sheet_id INTEGER NOT NULL, scheduled_date TEXT NOT NULL);",
        "CREATE TABLE user_site_permissions (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, site_id INTEGER NOT NULL);",
    ]
    legacy_index_statements = [
        "CREATE INDEX idx_vendor_contacts_sheet_vendor ON vendor_contacts (sheet_id, vendor_name);",
        "CREATE INDEX idx_vendor_work_entries_sheet_vendor_date ON vendor_work_entries (sheet_id, vendor_name, business_date);",
    ]
    if reorder_legacy:
        legacy_table_statements = list(reversed(legacy_table_statements))
    legacy_statements = legacy_table_statements + legacy_index_statements
    for statement in legacy_statements:
        conn.execute(statement)
    if include_registry:
        conn.executescript(
            """
            CREATE TABLE global_identities (
                global_identity_id TEXT PRIMARY KEY,
                registry_status TEXT NOT NULL DEFAULT 'disabled',
                created_provenance TEXT NOT NULL,
                updated_provenance TEXT NOT NULL
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
                created_provenance TEXT NOT NULL,
                updated_provenance TEXT NOT NULL,
                FOREIGN KEY (global_identity_id) REFERENCES global_identities(global_identity_id) ON DELETE RESTRICT ON UPDATE NO ACTION
            ) STRICT;
            CREATE TABLE backend_principal_mappings (
                backend_principal_mapping_id TEXT PRIMARY KEY,
                global_identity_id TEXT NOT NULL,
                backend_kind TEXT NOT NULL,
                backend_principal_key ANY NOT NULL,
                mapping_status TEXT NOT NULL DEFAULT 'active',
                created_provenance TEXT NOT NULL,
                updated_provenance TEXT NOT NULL,
                FOREIGN KEY (global_identity_id) REFERENCES global_identities(global_identity_id) ON DELETE RESTRICT ON UPDATE NO ACTION,
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
        )
    conn.execute("INSERT INTO meta (key, value) VALUES ('site_title', 'demo')")
    conn.execute("INSERT INTO meta (key, value) VALUES ('unit_layout_version', 'v1')")
    conn.execute("INSERT INTO users (id, username, role) VALUES (1, 'admin', 'admin')")
    conn.execute("INSERT INTO users (id, username, role) VALUES (2, 'member', 'member')")
    conn.execute("INSERT INTO sheets (id, name) VALUES (1, 'Sheet A')")
    conn.execute("INSERT INTO sites (id, name) VALUES (1, 'Main Site')")
    conn.execute("INSERT INTO tasks (id, sheet_id, name) VALUES (1, 1, 'Task A')")
    conn.execute("INSERT INTO floors (id, sheet_id, name) VALUES (1, 1, '1F')")
    conn.execute("INSERT INTO units (id, floor_id, name) VALUES (1, 1, '101')")
    conn.execute("INSERT INTO progress (unit_id, task_id, value) VALUES (1, 1, 'X')")
    conn.execute("INSERT INTO extra_fields (id, sheet_id, field_key, name) VALUES (1, 1, 'handover', 'Handover')")
    conn.execute("INSERT INTO unit_extra (unit_id, handover) VALUES (1, 'X')")
    conn.execute("INSERT INTO unit_extra_values (unit_id, field_key, value) VALUES (1, 'handover', 'X')")
    if business_variant:
        conn.execute("INSERT INTO tasks (id, sheet_id, name) VALUES (2, 1, 'Task B')")
        conn.execute("INSERT INTO progress (unit_id, task_id, value) VALUES (1, 2, 'Y')")
    conn.commit()
    conn.close()


def expect_fail(fn: Any, expected_fragment: str) -> None:
    try:
        fn()
    except BaseException as exc:
        if expected_fragment not in str(exc):
            raise AssertionError(f"Expected {expected_fragment!r} in {exc!r}")
    else:
        raise AssertionError(f"Expected failure containing {expected_fragment!r}")


def rewrite_checksums_for_payload(payload: dict[str, Any], legacy_bytes: bytes) -> bytes:
    payload_bytes = canonical_json_bytes(payload)
    checksums = {
        "serializer_version": SERIALIZER_VERSION,
        "manifest_id": sha256_hex(payload_bytes),
        "tool_source_sha256": payload["tool_source_sha256"],
        "legacy_manifest_sha256": sha256_hex(legacy_bytes),
        "manifest_payload_sha256": sha256_hex(payload_bytes),
        "manifest_id_recipe": payload["manifest_id_recipe"],
        "output_files": {
            "legacy_manifest_v1.json": {
                "size": len(legacy_bytes),
                "sha256": sha256_hex(legacy_bytes),
            },
            "manifest_payload_v1.json": {
                "size": len(payload_bytes),
                "sha256": sha256_hex(payload_bytes),
            },
        },
    }
    return canonical_json_bytes(checksums)


def run_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="schema-manifest-self-test-") as tmpdir:
        root = Path(tmpdir)
        db_root = root / "db"
        artifact_root = root / "artifacts"
        db_root.mkdir()
        artifact_root.mkdir()
        base_db = db_root / "base.db"
        create_sample_sqlite(base_db)

        capture_a = artifact_root / "capture-a"
        capture_b = artifact_root / "capture-b"
        summary_a = write_capture_artifacts(base_db, capture_a)
        summary_b = write_capture_artifacts(base_db, capture_b)
        if (capture_a / "legacy_manifest_v1.json").read_bytes() != (capture_b / "legacy_manifest_v1.json").read_bytes():
            raise AssertionError("Deterministic legacy manifest capture failed.")
        if (capture_a / "manifest_payload_v1.json").read_bytes() != (capture_b / "manifest_payload_v1.json").read_bytes():
            raise AssertionError("Deterministic payload capture failed.")

        reordered_db = db_root / "reordered.db"
        create_sample_sqlite(reordered_db, reorder_legacy=True)
        reordered_capture = artifact_root / "reordered-capture"
        write_capture_artifacts(reordered_db, reordered_capture)
        if json.loads((capture_a / "legacy_manifest_v1.json").read_text("utf-8")) != json.loads(
            (reordered_capture / "legacy_manifest_v1.json").read_text("utf-8")
        ):
            raise AssertionError("Legacy record sorting is not deterministic.")
        if b'"sql":null' not in (capture_a / "legacy_manifest_v1.json").read_bytes():
            raise AssertionError("SQLite autoindex sql=NULL was not preserved.")

        registry_db = db_root / "registry.db"
        create_sample_sqlite(registry_db, include_registry=True)
        registry_capture = artifact_root / "registry-capture"
        write_capture_artifacts(registry_db, registry_capture)
        base_payload = json.loads((capture_a / "manifest_payload_v1.json").read_text("utf-8"))
        registry_payload = json.loads((registry_capture / "manifest_payload_v1.json").read_text("utf-8"))
        if base_payload["legacy_manifest_sha256"] != registry_payload["legacy_manifest_sha256"]:
            raise AssertionError("Registry-only schema changed legacy digest.")
        compare_registry = classify_compare(load_manifest_dir(capture_a), load_manifest_dir(registry_capture))
        if "expected registry-only schema delta" not in compare_registry["classifications"]:
            raise AssertionError("Registry-only addition classification failed.")

        schema_drift_db = db_root / "schema-drift.db"
        create_sample_sqlite(schema_drift_db)
        conn = sqlite3.connect(schema_drift_db)
        conn.execute("CREATE INDEX idx_meta_value ON meta (value)")
        conn.commit()
        conn.close()
        schema_drift_capture = artifact_root / "schema-drift-capture"
        write_capture_artifacts(schema_drift_db, schema_drift_capture)
        compare_schema_drift = classify_compare(load_manifest_dir(capture_a), load_manifest_dir(schema_drift_capture))
        if "legacy schema drift" not in compare_schema_drift["classifications"]:
            raise AssertionError("Legacy index drift was not detected.")

        business_drift_db = db_root / "business-drift.db"
        create_sample_sqlite(business_drift_db, business_variant=True)
        business_drift_capture = artifact_root / "business-drift-capture"
        write_capture_artifacts(business_drift_db, business_drift_capture)
        compare_business = classify_compare(load_manifest_dir(capture_a), load_manifest_dir(business_drift_capture))
        if "business data drift" not in compare_business["classifications"]:
            raise AssertionError("Business row-count drift was not detected.")

        expect_fail(
            lambda: write_capture_artifacts(db_root / "missing.db", artifact_root / "missing-out"),
            "source DB does not exist",
        )

        guarded = GuardedConnection(base_db, readonly=False)
        try:
            for sql in ("PRAGMA foreign_keys", "PRAGMA schema_version", "PRAGMA query_only"):
                guarded.conn.execute(sql).fetchall()
            read_attempts = guarded.write_attempts
            for sql in (
                "PRAGMA foreign_keys=OFF",
                "PRAGMA journal_mode=WAL",
                "PRAGMA wal_checkpoint(TRUNCATE)",
                "INSERT INTO meta (key, value) VALUES ('blocked', '1')",
                "UPDATE meta SET value = 'blocked' WHERE key = 'site_title'",
                "DELETE FROM meta WHERE key = 'site_title'",
                "CREATE TABLE blocked_table (id INTEGER PRIMARY KEY)",
                "CREATE INDEX blocked_index ON meta (value)",
                "DROP TABLE users",
                "ALTER TABLE meta ADD COLUMN blocked TEXT",
                "ATTACH DATABASE ':memory:' AS extra",
                "DETACH DATABASE extra",
            ):
                before_attempts = guarded.write_attempts
                try:
                    guarded.conn.execute(sql)
                except sqlite3.DatabaseError:
                    pass
                if guarded.write_attempts != before_attempts + 1:
                    raise AssertionError(f"Authorizer did not count blocked statement: {sql}")
            if guarded.write_attempts <= read_attempts:
                raise AssertionError("Authorizer did not record blocked write attempts.")
        finally:
            guarded.close()

        payload_after_capture = json.loads((capture_a / "manifest_payload_v1.json").read_text("utf-8"))
        if payload_after_capture["file_size"] != payload_after_capture["file_size_after"]:
            raise AssertionError("Source DB file size changed during capture.")
        if payload_after_capture["mtime_ns"] != payload_after_capture["mtime_ns_after"]:
            raise AssertionError("Source DB mtime changed during capture.")
        if payload_after_capture["business_row_counts"] != base_payload["business_row_counts"]:
            raise AssertionError("Business row counts changed during capture.")

        transport_dir = artifact_root / "transport"
        transport_dir.mkdir()
        transport = build_transport_bundle(capture_a, 1024)
        transport_file = transport_dir / "transport_chunks_v1.json"
        transport_file.write_bytes(canonical_json_bytes(transport))
        reconstructed_dir = artifact_root / "reconstructed"
        reconstruct_transport(transport_file, reconstructed_dir)
        for name in REQUIRED_ARTIFACT_FILES:
            if (capture_a / name).read_bytes() != (reconstructed_dir / name).read_bytes():
                raise AssertionError(f"Transport reconstruction mismatch for {name}.")

        def write_mutated_transport(name: str, mutate: Any) -> Path:
            mutated = json.loads(transport_file.read_text("utf-8"))
            mutate(mutated)
            path = transport_dir / name
            path.write_text(json.dumps(mutated, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            return path

        def write_mutated_manifest_dir(name: str, mutate: Any) -> Path:
            target = artifact_root / name
            target.mkdir()
            for artifact_name in REQUIRED_ARTIFACT_FILES:
                (target / artifact_name).write_bytes((capture_a / artifact_name).read_bytes())
            mutate(target)
            return target

        def rewrite_bundle(mutated_transport: dict[str, Any], bundle_mutate: Any) -> None:
            payload_ascii = "".join(chunk["text"] for chunk in mutated_transport["chunks"])
            compressed_bytes = base64.b64decode(payload_ascii.encode("ascii"))
            bundle = json.loads(gzip.decompress(compressed_bytes).decode("utf-8"))
            bundle_mutate(bundle)
            bundle_bytes = canonical_json_bytes(bundle)
            compressed_bytes = gzip.compress(bundle_bytes, compresslevel=9, mtime=0)
            payload_ascii = base64.b64encode(compressed_bytes).decode("ascii")
            chunk_size = int(mutated_transport["chunk_size"])
            chunks = []
            for start in range(0, len(payload_ascii), chunk_size):
                text = payload_ascii[start : start + chunk_size]
                chunks.append(
                    {
                        "sequence": len(chunks) + 1,
                        "length": len(text),
                        "sha256": sha256_hex(text.encode("ascii")),
                        "text": text,
                    }
                )
            mutated_transport["chunks"] = chunks
            mutated_transport["total_chunk_count"] = len(chunks)
            mutated_transport["concatenated_payload_length"] = len(payload_ascii)
            mutated_transport["concatenated_payload_sha256"] = sha256_hex(payload_ascii.encode("ascii"))
            mutated_transport["decoded_bundle_sha256"] = sha256_hex(bundle_bytes)
            mutated_transport["compressed_payload_ascii_sha256"] = sha256_hex(payload_ascii.encode("ascii"))
            mutated_transport["compressed_payload_character_length"] = len(payload_ascii)

        def update_manifest_payload(target: Path, mutate: Any) -> None:
            payload = json.loads((target / "manifest_payload_v1.json").read_text("utf-8"))
            legacy_bytes = (target / "legacy_manifest_v1.json").read_bytes()
            mutate(payload)
            payload_bytes = canonical_json_bytes(payload)
            (target / "manifest_payload_v1.json").write_bytes(payload_bytes)
            (target / "manifest_checksums_v1.json").write_bytes(rewrite_checksums_for_payload(payload, legacy_bytes))

        def update_legacy_manifest(target: Path, mutate: Any) -> None:
            legacy_records = json.loads((target / "legacy_manifest_v1.json").read_text("utf-8"))
            mutate(legacy_records)
            legacy_bytes = canonical_json_bytes(legacy_records)
            (target / "legacy_manifest_v1.json").write_bytes(legacy_bytes)
            payload = json.loads((target / "manifest_payload_v1.json").read_text("utf-8"))
            payload["legacy_manifest_sha256"] = sha256_hex(legacy_bytes)
            payload_bytes = canonical_json_bytes(payload)
            (target / "manifest_payload_v1.json").write_bytes(payload_bytes)
            (target / "manifest_checksums_v1.json").write_bytes(rewrite_checksums_for_payload(payload, legacy_bytes))

        missing_chunk = write_mutated_transport("missing.json", lambda data: data["chunks"].pop())
        duplicate_chunk = write_mutated_transport(
            "duplicate.json",
            lambda data: (
                data["chunks"].append(dict(data["chunks"][0])),
                data.__setitem__("total_chunk_count", len(data["chunks"])),
            ),
        )
        reordered_chunk = write_mutated_transport("reordered.json", lambda data: data["chunks"].reverse())
        truncated_quartet = write_mutated_transport("truncated.json", lambda data: data["chunks"][-1].__setitem__("text", data["chunks"][-1]["text"][:-1]))
        invalid_base64 = write_mutated_transport("invalid.json", lambda data: data["chunks"][0].__setitem__("text", "!" + data["chunks"][0]["text"][1:]))
        payload_hash_mismatch = write_mutated_transport(
            "payload-hash.json",
            lambda data: data.__setitem__("concatenated_payload_sha256", "0" * 64),
        )
        compressed_hash_mismatch = write_mutated_transport(
            "compressed-hash.json",
            lambda data: data.__setitem__("compressed_payload_ascii_sha256", "1" * 64),
        )
        compressed_length_mismatch = write_mutated_transport(
            "compressed-length.json",
            lambda data: data.__setitem__("compressed_payload_character_length", data["compressed_payload_character_length"] + 1),
        )
        incorrect_total_chunk_count = write_mutated_transport(
            "wrong-count.json",
            lambda data: data.__setitem__("total_chunk_count", data["total_chunk_count"] + 1),
        )
        invalid_chunk_size = write_mutated_transport(
            "invalid-chunk-size.json",
            lambda data: data.__setitem__("chunk_size", 0),
        )
        malformed_chunk_object = write_mutated_transport(
            "malformed-chunk.json",
            lambda data: data["chunks"][0].pop("sha256"),
        )
        bundle_hash_mismatch = write_mutated_transport(
            "bundle-hash.json",
            lambda data: data.__setitem__("decoded_bundle_sha256", "F" * 64),
        )
        unsupported_transport_version = write_mutated_transport(
            "unsupported.json",
            lambda data: data.__setitem__("transport_version", "UNSUPPORTED"),
        )
        top_level_serializer_mismatch = write_mutated_transport(
            "top-level-serializer-mismatch.json",
            lambda data: data.__setitem__("serializer_version", "UNSUPPORTED"),
        )
        bundle_serializer_mismatch = write_mutated_transport(
            "bundle-serializer-mismatch.json",
            lambda data: rewrite_bundle(data, lambda bundle: bundle.__setitem__("serializer_version", "UNSUPPORTED")),
        )
        duplicate_artifact = write_mutated_transport(
            "duplicate-artifact.json",
            lambda data: rewrite_bundle(data, lambda bundle: bundle["files"].append(dict(bundle["files"][0]))),
        )
        missing_artifact = write_mutated_transport(
            "missing-artifact.json",
            lambda data: rewrite_bundle(data, lambda bundle: bundle["files"].pop()),
        )
        extra_artifact = write_mutated_transport(
            "extra-artifact.json",
            lambda data: rewrite_bundle(
                data,
                lambda bundle: bundle["files"].append(
                    {"name": "extra.json", "size": 2, "sha256": sha256_hex(b"{}"), "base64": base64.b64encode(b"{}").decode("ascii")}
                ),
            ),
        )
        path_traversal_artifact = write_mutated_transport(
            "path-traversal.json",
            lambda data: rewrite_bundle(data, lambda bundle: bundle["files"][0].__setitem__("name", "../escape.json")),
        )
        malformed_bundle_entry = write_mutated_transport(
            "malformed-entry.json",
            lambda data: rewrite_bundle(data, lambda bundle: bundle["files"][0].pop("sha256")),
        )
        corrupted_artifact = write_mutated_transport(
            "corrupted-artifact.json",
            lambda data: data["chunks"][0].__setitem__("sha256", "A" * 64),
        )

        expect_fail(lambda: reconstruct_transport(missing_chunk, artifact_root / "missing-out"), "incorrect total chunk count")
        expect_fail(lambda: reconstruct_transport(duplicate_chunk, artifact_root / "duplicate-out"), "duplicate chunk sequence")
        expect_fail(lambda: reconstruct_transport(reordered_chunk, artifact_root / "reordered-out"), "missing or reordered chunk sequence")
        expect_fail(lambda: reconstruct_transport(truncated_quartet, artifact_root / "truncated-out"), "chunk length mismatch")
        expect_fail(lambda: reconstruct_transport(invalid_base64, artifact_root / "invalid-out"), "chunk hash mismatch")
        expect_fail(lambda: reconstruct_transport(payload_hash_mismatch, artifact_root / "payload-hash-out"), "payload hash mismatch")
        expect_fail(lambda: reconstruct_transport(compressed_hash_mismatch, artifact_root / "compressed-hash-out"), "incorrect compressed payload ASCII hash")
        expect_fail(lambda: reconstruct_transport(compressed_length_mismatch, artifact_root / "compressed-length-out"), "incorrect compressed payload character length")
        expect_fail(lambda: reconstruct_transport(incorrect_total_chunk_count, artifact_root / "wrong-count-out"), "incorrect total chunk count")
        expect_fail(lambda: reconstruct_transport(invalid_chunk_size, artifact_root / "invalid-chunk-size-out"), "invalid chunk size")
        expect_fail(lambda: reconstruct_transport(malformed_chunk_object, artifact_root / "malformed-chunk-out"), "malformed chunk object")
        expect_fail(lambda: reconstruct_transport(bundle_hash_mismatch, artifact_root / "bundle-hash-out"), "decompressed bundle hash mismatch")
        expect_fail(lambda: reconstruct_transport(unsupported_transport_version, artifact_root / "unsupported-out"), "unsupported transport version")
        expect_fail(lambda: reconstruct_transport(top_level_serializer_mismatch, artifact_root / "top-level-serializer-out"), "unsupported serializer version")
        expect_fail(lambda: reconstruct_transport(bundle_serializer_mismatch, artifact_root / "bundle-serializer-out"), "unsupported serializer version")
        expect_fail(lambda: reconstruct_transport(duplicate_artifact, artifact_root / "duplicate-artifact-out"), "duplicate artifact file name")
        expect_fail(lambda: reconstruct_transport(missing_artifact, artifact_root / "missing-artifact-out"), "artifact file set mismatch")
        expect_fail(lambda: reconstruct_transport(extra_artifact, artifact_root / "extra-artifact-out"), "artifact file set mismatch")
        expect_fail(lambda: reconstruct_transport(path_traversal_artifact, artifact_root / "path-traversal-out"), "invalid artifact path")
        expect_fail(lambda: reconstruct_transport(malformed_bundle_entry, artifact_root / "malformed-entry-out"), "malformed bundle entry")
        expect_fail(lambda: reconstruct_transport(corrupted_artifact, artifact_root / "corrupted-out"), "chunk hash mismatch")
        corrupted_output = artifact_root / "corrupted-check"
        expect_fail(lambda: reconstruct_transport(malformed_bundle_entry, corrupted_output), "malformed bundle entry")
        if corrupted_output.exists() and any(corrupted_output.iterdir()):
            raise AssertionError("Reconstruction failure must not leave partial artifacts.")

        payload_without_checksums = write_mutated_manifest_dir(
            "payload-without-checksums-update",
            lambda target: (target / "manifest_payload_v1.json").write_bytes(
                canonical_json_bytes({**json.loads((target / "manifest_payload_v1.json").read_text("utf-8")), "tool_source_sha256": "F" * 64})
            ),
        )
        legacy_without_checksums = write_mutated_manifest_dir(
            "legacy-without-checksums-update",
            lambda target: (
                lambda records: (
                    records[0].__setitem__("sql", (records[0]["sql"] or "") + " "),
                    (target / "legacy_manifest_v1.json").write_bytes(canonical_json_bytes(records)),
                )
            )(json.loads((target / "legacy_manifest_v1.json").read_text("utf-8"))),
        )
        manifest_id_only = write_mutated_manifest_dir(
            "manifest-id-only",
            lambda target: (target / "manifest_checksums_v1.json").write_bytes(
                canonical_json_bytes({**json.loads((target / "manifest_checksums_v1.json").read_text("utf-8")), "manifest_id": "0" * 64})
            ),
        )
        tool_hash_only = write_mutated_manifest_dir(
            "tool-hash-only",
            lambda target: update_manifest_payload(target, lambda payload: payload.__setitem__("tool_source_sha256", "E" * 64)),
        )
        recipe_only = write_mutated_manifest_dir(
            "recipe-only",
            lambda target: update_manifest_payload(target, lambda payload: payload.__setitem__("manifest_id_recipe", "different recipe")),
        )
        changed_value_count = write_mutated_manifest_dir(
            "changed-count",
            lambda target: update_manifest_payload(target, lambda payload: payload["business_row_counts"].__setitem__("tasks", payload["business_row_counts"]["tasks"] + 1)),
        )
        post_only_count = write_mutated_manifest_dir(
            "post-only-count",
            lambda target: update_manifest_payload(target, lambda payload: payload["business_row_counts"].__setitem__("post_only", 7)),
        )
        pre_only_registry_count = write_mutated_manifest_dir(
            "pre-only-registry-count",
            lambda target: (
                (target / "legacy_manifest_v1.json").write_bytes((registry_capture / "legacy_manifest_v1.json").read_bytes()),
                (target / "manifest_payload_v1.json").write_bytes((registry_capture / "manifest_payload_v1.json").read_bytes()),
                (target / "manifest_checksums_v1.json").write_bytes((registry_capture / "manifest_checksums_v1.json").read_bytes()),
                update_manifest_payload(target, lambda payload: payload["registry_row_counts"].pop("backend_principal_mappings")),
            ),
        )
        unexpected_payload_field = write_mutated_manifest_dir(
            "unexpected-payload-field",
            lambda target: (target / "manifest_payload_v1.json").write_bytes(
                canonical_json_bytes({**json.loads((target / "manifest_payload_v1.json").read_text("utf-8")), "unexpected": True})
            ),
        )
        unexpected_checksums_field = write_mutated_manifest_dir(
            "unexpected-checksums-field",
            lambda target: (target / "manifest_checksums_v1.json").write_bytes(
                canonical_json_bytes({**json.loads((target / "manifest_checksums_v1.json").read_text("utf-8")), "unexpected": True})
            ),
        )
        unsorted_legacy = write_mutated_manifest_dir(
            "unsorted-legacy",
            lambda target: (target / "legacy_manifest_v1.json").write_bytes(canonical_json_bytes(list(reversed(json.loads((target / "legacy_manifest_v1.json").read_text("utf-8")))))),
        )
        invalid_legacy_type = write_mutated_manifest_dir(
            "invalid-legacy-type",
            lambda target: update_legacy_manifest(target, lambda records: records[0].__setitem__("type", "view")),
        )
        invalid_legacy_name = write_mutated_manifest_dir(
            "invalid-legacy-name",
            lambda target: update_legacy_manifest(target, lambda records: records[0].__setitem__("name", "")),
        )

        expect_fail(lambda: load_manifest_dir(payload_without_checksums), "manifest ID mismatch")
        expect_fail(lambda: load_manifest_dir(legacy_without_checksums), "legacy manifest hash mismatch")
        expect_fail(lambda: load_manifest_dir(manifest_id_only), "manifest ID mismatch")
        expect_fail(lambda: load_manifest_dir(unexpected_payload_field), "manifest payload key set mismatch")
        expect_fail(lambda: load_manifest_dir(unexpected_checksums_field), "manifest checksums key set mismatch")
        expect_fail(lambda: load_manifest_dir(unsorted_legacy), "legacy manifest records must be sorted")
        expect_fail(lambda: load_manifest_dir(invalid_legacy_type), "invalid type")
        expect_fail(lambda: load_manifest_dir(invalid_legacy_name), "non-empty string name")
        expect_fail(lambda: load_manifest_dir(recipe_only), "manifest ID recipe mismatch")
        expect_fail(lambda: build_transport_bundle(payload_without_checksums, 1024), "manifest ID mismatch")
        expect_fail(lambda: classify_compare(load_manifest_dir(capture_a), load_manifest_dir(payload_without_checksums)), "manifest ID mismatch")
        expect_fail(lambda: build_transport_bundle(unsorted_legacy, 1024), "legacy manifest records must be sorted")

        mismatch_tool_compare = classify_compare(load_manifest_dir(capture_a), load_manifest_dir(tool_hash_only))
        if mismatch_tool_compare["semantic_comparison_performed"] is not False or mismatch_tool_compare["classifications"] != ["serializer/version mismatch"]:
            raise AssertionError("Tool source mismatch must only classify as serializer/version mismatch.")
        changed_count_compare = classify_compare(load_manifest_dir(capture_a), load_manifest_dir(changed_value_count))
        if changed_count_compare["business_row_count_differences"].get("tasks") != {"pre": 1, "post": 2}:
            raise AssertionError("Changed business count was not detected.")
        post_only_compare = classify_compare(load_manifest_dir(capture_a), load_manifest_dir(post_only_count))
        if post_only_compare["business_row_count_differences"].get("post_only") != {"pre": None, "post": 7}:
            raise AssertionError("Post-only business count key was not detected.")
        pre_only_compare = classify_compare(load_manifest_dir(registry_capture), load_manifest_dir(pre_only_registry_count))
        if pre_only_compare["registry_row_count_differences"].get("backend_principal_mappings") != {"pre": 0, "post": None}:
            raise AssertionError("Pre-only registry count key was not detected.")

        if summary_a["source_db_unchanged"] is not True:
            raise AssertionError("Source DB no-write proof failed.")

    print(PASS_MARKER)


def main() -> int:
    args = parse_args()
    if args.self_test:
        run_self_test()
        return 0

    if args.command == "capture":
        db_path, output_dir = ensure_capture_paths(args.db, args.output_dir)
        result = write_capture_artifacts(db_path, output_dir)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0

    if args.command == "compare":
        result = classify_compare(load_manifest_dir(args.pre_dir), load_manifest_dir(args.post_dir))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0

    if args.command == "pack-transport":
        input_dir = args.input_dir.resolve()
        output_dir = args.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        transport = build_transport_bundle(input_dir, args.chunk_size)
        output_file = output_dir / "transport_chunks_v1.json"
        output_file.write_bytes(canonical_json_bytes(transport))
        result = {
            "transport_version": TRANSPORT_VERSION,
            "serializer_version": SERIALIZER_VERSION,
            "transport_file": str(output_file),
            "total_chunk_count": transport["total_chunk_count"],
            "chunk_size": transport["chunk_size"],
            "concatenated_payload_length": transport["concatenated_payload_length"],
            "concatenated_payload_sha256": transport["concatenated_payload_sha256"],
            "decoded_bundle_sha256": transport["decoded_bundle_sha256"],
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0

    if args.command == "reconstruct-transport":
        result = reconstruct_transport(args.transport_file.resolve(), args.output_dir.resolve())
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0

    raise SystemExit("FAIL explicit command required unless --self-test is used.")


if __name__ == "__main__":
    raise SystemExit(main())
