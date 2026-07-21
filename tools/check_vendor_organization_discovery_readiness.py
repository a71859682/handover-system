from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import io
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence


_ROOT_DIR = Path(__file__).resolve().parents[1]
_CHECKER_PATH = Path(
    "tools/check_vendor_organization_discovery_readiness.py"
)
_DISCOVERY_PATH = Path("tools/discover_vendor_organization_readiness.py")
_POLICY_PATH = Path(
    "docs/vendor_id_003_read_only_vendor_discovery_baseline.md"
)
_UPSTREAM_CHECKER_PATH = Path("tools/check_vendor_organization_schema.py")
_NON_VENDOR_OUTPUT_SOURCE_PATHS = frozenset(
    (
        Path("tools/check_identity_registry_reconciliation_readiness.py"),
        Path("tools/discover_identity_registry_anomalies.py"),
    )
)
_APPROVED_POLICY_SHA256 = (
    "DE97D2F4459E56FF9F7BE0C8411C2F8E1C897E1B0BD81EF9D8CD87A4475CBB20"
)
_PASS_MARKER = "vendor organization discovery readiness PASS"
_SELF_TEST_MARKER = (
    "vendor organization discovery readiness self-test PASS"
)
_NORMAL_SCOPE = (
    "vendor_discovery_readiness_scope: "
    "static_source_and_frozen_policy_only"
)

_ISSUE_CODES = (
    "vendor_discovery_policy_document_missing",
    "vendor_discovery_policy_marker_missing",
    "vendor_discovery_policy_drift",
    "forbidden_vendor_discovery_module_path",
    "partial_vendor_discovery_implementation",
    "forbidden_vendor_discovery_query",
    "dynamic_vendor_discovery_sql",
    "forbidden_vendor_discovery_sensitive_read",
    "forbidden_vendor_discovery_raw_disclosure",
    "forbidden_vendor_discovery_path_access",
    "forbidden_vendor_discovery_transaction",
    "forbidden_vendor_discovery_authorizer",
    "forbidden_vendor_discovery_error_contract",
    "forbidden_vendor_discovery_output_contract",
    "forbidden_vendor_discovery_artifact",
    "forbidden_vendor_discovery_selection",
    "forbidden_vendor_discovery_mapping",
    "forbidden_vendor_discovery_mutation",
    "forbidden_vendor_discovery_consumer",
    "forbidden_vendor_discovery_production_access",
    "forbidden_vendor_discovery_backend_access",
    "forbidden_vendor_discovery_environment_access",
    "forbidden_vendor_discovery_app_import",
    "checker_exemption_broadening",
    "unresolved_vendor_discovery_capability",
    "upstream_vendor_schema_guard_drift",
    "source_read_error",
    "source_parse_error",
)

_POLICY_MARKERS = (
    "# VENDOR-ID-003 Read-only vendor discovery design baseline",
    "| Slice ID | `VENDOR-ID-003` |",
    (
        "| Canonical path | "
        "`docs/vendor_id_003_read_only_vendor_discovery_baseline.md` |"
    ),
    (
        "| Status | "
        "`DOCS-ONLY CONTRACT PRODUCTION-FROZEN / IMPLEMENTATION NOT STARTED` |"
    ),
    "| Governing baselines | `VENDOR-ID-001`; `VENDOR-ID-002` |",
    "tools/discover_vendor_organization_readiness.py",
    "VendorOrganizationDiscoveryError",
    "discover_vendor_organization_readiness(",
    "The first implementation is transient output only.",
    "VENDOR-ID-003 DOCS-ONLY READ-ONLY VENDOR DISCOVERY DESIGN BASELINE COMPLETE",
    "DISCOVERY CONTRACT：FROZEN",
    "DISCOVERY IMPLEMENTATION：NOT STARTED",
    "REPORT / ARTIFACT：NOT IMPLEMENTED OR AUTHORIZED",
    "MAPPING / BACKFILL：NOT IMPLEMENTED OR AUTHORIZED",
    "RUNTIME CONSUMER / AUTHORITY SWITCH：NOT IMPLEMENTED OR AUTHORIZED",
    "DEV / PRODUCTION DATABASE ACCESS：NOT AUTHORIZED",
)
_POLICY_MARKER_COUNTS = tuple(
    (
        marker,
        2
        if marker
        in {
            "tools/discover_vendor_organization_readiness.py",
            "VendorOrganizationDiscoveryError",
            "DISCOVERY IMPLEMENTATION：NOT STARTED",
            "MAPPING / BACKFILL：NOT IMPLEMENTED OR AUTHORIZED",
            "RUNTIME CONSUMER / AUTHORITY SWITCH：NOT IMPLEMENTED OR AUTHORIZED",
        }
        else 1,
    )
    for marker in _POLICY_MARKERS
)

_ANOMALY_CATEGORIES = (
    "legacy_vendor_label_blank_or_invalid",
    "legacy_label_cross_scope_reuse",
    "multiple_vendor_accounts_ambiguous_label",
    "vendor_account_conflicting_operational_scope",
    "orphan_legacy_label_without_organization_evidence",
    "organization_without_legacy_evidence",
    "ambiguous_legacy_to_organization_candidate",
    "conflicting_existing_organization_candidates",
    "membership_evidence_mismatch",
    "vendor_site_assignment_evidence_mismatch",
    "sheet_vendor_binding_evidence_mismatch",
    "cross_site_relationship_conflict",
    "schema_or_source_unavailable",
    "unknown_unclassified_anomaly",
)

_SOURCE_TABLES = (
    "sites",
    "sheets",
    "tasks",
    "vendor_accounts",
    "vendor_contacts",
    "vendor_work_entries",
    "vendor_organizations",
    "vendor_organization_memberships",
    "vendor_site_assignments",
    "sheet_vendor_bindings",
)
_NEW_TABLES = _SOURCE_TABLES[-4:]
_SENSITIVE_COLUMNS = (
    "username",
    "password",
    "password_hash",
    "contact_person",
    "contact_name",
    "work_payload",
    "work_content",
    "site_name",
    "sheet_name",
)
_CANONICAL_SYMBOLS = (
    "discover_vendor_organization_readiness",
    "VendorOrganizationDiscoveryError",
    "discover_vendor_organization_readiness.py",
)
_CANONICAL_CLI_OPTIONS = (
    "--db-path",
    "--run-id",
    "--captured-at",
    "--tool-commit",
)
_CANONICAL_QUERIES = (
    """SELECT seq, name, file
FROM pragma_database_list
ORDER BY seq;""",
    """SELECT schema, name, type, ncol, wr, strict
FROM pragma_table_list
ORDER BY
    schema COLLATE BINARY,
    name COLLATE BINARY,
    type COLLATE BINARY,
    ncol,
    wr,
    strict;""",
    """SELECT type, name, tbl_name, sql
FROM main.sqlite_schema
ORDER BY
    type COLLATE BINARY,
    name COLLATE BINARY,
    tbl_name COLLATE BINARY,
    sql IS NOT NULL,
    sql COLLATE BINARY;""",
    """SELECT type, name, tbl_name, sql
FROM temp.sqlite_schema
ORDER BY
    type COLLATE BINARY,
    name COLLATE BINARY,
    tbl_name COLLATE BINARY,
    sql IS NOT NULL,
    sql COLLATE BINARY;""",
    """SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('sites', 'main')
ORDER BY cid;""",
    """SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('sheets', 'main')
ORDER BY cid;""",
    """SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('tasks', 'main')
ORDER BY cid;""",
    """SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('vendor_accounts', 'main')
ORDER BY cid;""",
    """SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('vendor_contacts', 'main')
ORDER BY cid;""",
    """SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('vendor_work_entries', 'main')
ORDER BY cid;""",
    """SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('vendor_organizations', 'main')
ORDER BY cid;""",
    """SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('vendor_organization_memberships', 'main')
ORDER BY cid;""",
    """SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('vendor_site_assignments', 'main')
ORDER BY cid;""",
    """SELECT cid, name, type, "notnull", dflt_value, pk, hidden
FROM pragma_table_xinfo('sheet_vendor_bindings', 'main')
ORDER BY cid;""",
    """SELECT id
FROM main.sites
ORDER BY id;""",
    """SELECT id, site_id
FROM main.sheets
ORDER BY id;""",
    """SELECT sheet_id, vendor
FROM main.tasks
ORDER BY
    sheet_id,
    vendor IS NOT NULL,
    vendor COLLATE BINARY;""",
    """SELECT id, vendor_name
FROM main.vendor_accounts
ORDER BY id;""",
    """SELECT sheet_id, vendor_name
FROM main.vendor_contacts
ORDER BY
    sheet_id,
    vendor_name IS NOT NULL,
    vendor_name COLLATE BINARY;""",
    """SELECT sheet_id, vendor_name
FROM main.vendor_work_entries
ORDER BY
    sheet_id,
    vendor_name IS NOT NULL,
    vendor_name COLLATE BINARY;""",
    """SELECT vendor_id, display_name, organization_status
FROM main.vendor_organizations
ORDER BY vendor_id COLLATE BINARY;""",
    """SELECT
    vendor_membership_id,
    vendor_id,
    vendor_account_id,
    membership_role,
    membership_status
FROM main.vendor_organization_memberships
ORDER BY vendor_membership_id COLLATE BINARY;""",
    """SELECT
    vendor_site_assignment_id,
    vendor_id,
    site_id,
    assignment_status
FROM main.vendor_site_assignments
ORDER BY vendor_site_assignment_id COLLATE BINARY;""",
    """SELECT
    sheet_vendor_binding_id,
    vendor_id,
    sheet_id,
    site_id,
    vendor_site_assignment_id,
    binding_status
FROM main.sheet_vendor_bindings
ORDER BY sheet_vendor_binding_id COLLATE BINARY;""",
)
_NORMALIZED_CANONICAL_QUERIES = tuple(
    " ".join(query.lower().split()) for query in _CANONICAL_QUERIES
)
_UPSTREAM_SCHEMA_METADATA_QUERIES = frozenset(_CANONICAL_QUERIES[:14])
_CANONICAL_QUERY_FRAGMENTS = (
    "from pragma_database_list",
    "from pragma_table_list",
    "from main.sqlite_schema",
    "from temp.sqlite_schema",
    "from pragma_table_xinfo('sites', 'main')",
    "from pragma_table_xinfo('sheets', 'main')",
    "from pragma_table_xinfo('tasks', 'main')",
    "from pragma_table_xinfo('vendor_accounts', 'main')",
    "from pragma_table_xinfo('vendor_contacts', 'main')",
    "from pragma_table_xinfo('vendor_work_entries', 'main')",
    "from pragma_table_xinfo('vendor_organizations', 'main')",
    (
        "from pragma_table_xinfo("
        "'vendor_organization_memberships', 'main')"
    ),
    "from pragma_table_xinfo('vendor_site_assignments', 'main')",
    "from pragma_table_xinfo('sheet_vendor_bindings', 'main')",
    "from main.sites",
    "from main.sheets",
    "from main.tasks",
    "from main.vendor_accounts",
    "from main.vendor_contacts",
    "from main.vendor_work_entries",
    "from main.vendor_organizations",
    "from main.vendor_organization_memberships",
    "from main.vendor_site_assignments",
    "from main.sheet_vendor_bindings",
)

_EXCLUDED_TOP_LEVELS = frozenset(
    {
        ".codex",
        ".git",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "docs",
        "env",
        "node_modules",
        "tests",
        "venv",
    }
)
_SQL_SINKS = frozenset(
    {
        "execute",
        "executemany",
        "executescript",
        "query",
        "raw",
        "run_sql",
        "sql",
    }
)
_WRITE_CALLS = frozenset(
    {
        "open",
        "write",
        "write_bytes",
        "write_text",
        "dump",
        "dumps",
        "save",
        "upload",
        "download",
        "export",
    }
)
_BACKEND_ROOTS = frozenset(
    {
        "asyncpg",
        "pg8000",
        "postgres",
        "postgresql",
        "psycopg",
        "psycopg2",
        "psycopg_pool",
        "sqlalchemy",
        "sqlite3",
    }
)
_PROJECT_IMPORT_ROOTS = frozenset(
    {
        "app",
        "config",
        "database",
        "db_compat",
        "migrations",
        "models",
        "routes",
        "services",
        "sqlite_db_path",
    }
)
_UPSTREAM_ALLOWED_NODE_NAMES = (
        "APP_IMPLEMENTATION_NODE_NAMES",
        "APP_IMPLEMENTATION_AST_SHA256",
        "MANIFEST_EXTENSION_NODE_NAMES",
        "MANIFEST_EXTENSION_AST_SHA256",
        "dotted_name",
        "_selected_top_level_nodes",
        "_literal_assignment",
        "_assignment_value",
        "_is_exact_public_helper_signature",
        "check_policy_document",
        "_replace_exact_fragment",
        "_mutate_literal_tuple",
        "validate_exact_app_implementation",
        "validate_exact_manifest_extension",
        "DISCOVERY_READINESS_CHECKER_PATH",
        "DISCOVERY_IMPLEMENTATION_PATH",
        "DISCOVERY_READINESS_KNOWN_ISSUE_CODES",
        "DISCOVERY_READINESS_ALLOWED_V002_ISSUE_CODES",
        "DISCOVERY_READINESS_NODE_NAMES",
        "DISCOVERY_READINESS_AST_SHA256",
        "validate_exact_discovery_readiness_checker",
        "_exercise_discovery_readiness_checker_contract",
)
_EXPECTED_UPSTREAM_ALLOWED_V002_ISSUE_CODES = frozenset(
    {
        "forbidden_vendor_schema_table",
        "forbidden_vendor_schema_index",
        "forbidden_vendor_schema_trigger",
        "forbidden_vendor_schema_migration",
        "forbidden_vendor_schema_dml",
        "forbidden_vendor_schema_consumer",
        "forbidden_vendor_schema_executescript",
        "forbidden_vendor_schema_dynamic_sql",
        "forbidden_vendor_schema_backfill",
        "forbidden_vendor_relationship_mutation",
        "forbidden_vendor_authority_switch",
        "forbidden_vendor_schema_backend",
        "forbidden_vendor_schema_environment_access",
        "unresolved_vendor_schema_capability",
    }
)
_UPSTREAM_STATIC_NODE_HASHES = {
    "APP_IMPLEMENTATION_NODE_NAMES": (
        "CF67080ED4ADE3763F30760C2070959D6311938969BD5DD0DC04F189C8AF5FD3"
    ),
    "APP_IMPLEMENTATION_AST_SHA256": (
        "DFD15F426734B1A17E489160DF6111A5D708D042F2468A0C5D4B07235F04B1CB"
    ),
    "MANIFEST_EXTENSION_NODE_NAMES": (
        "02529FBA01298D25170B49228BAB7F32E4D7CBC09C1FAF513C20826271584F87"
    ),
    "MANIFEST_EXTENSION_AST_SHA256": (
        "6C6AB30D7D598840C4D3B4717F6C8A12114D8299E95ED3889F8E68085EB971FB"
    ),
    "dotted_name": (
        "BFBCAB22E888BF7E85B227FC23A9349126DC0CDF780634BF9E2F1A4AB3EF9135"
    ),
    "_selected_top_level_nodes": (
        "7AB7383CEDD892BEF76511B8620B699915D6950593507C8431AF8EC1A83A3ACD"
    ),
    "_literal_assignment": (
        "FC2C7734427FD447280D0581D2CCAD3A0ED741D41C501CBA56688365189094EE"
    ),
    "_assignment_value": (
        "4B3F24E018D173434B902C177417E670EF343BAB23C4AF9341C1B4AF8239EED0"
    ),
    "_is_exact_public_helper_signature": (
        "55A03B617CF9E1024517C25C1A947F11518B047C4625647874063AE1871AD5DF"
    ),
    "check_policy_document": (
        "404C54DD5C37845AE8DCF3AD1D1DBE7A74BD625642311DD5C526807136F56D87"
    ),
    "_replace_exact_fragment": (
        "CDB4158781204EA126F05DAEC149D37F0697E55BB37E66199FBCFFB91C3F0F0F"
    ),
    "_mutate_literal_tuple": (
        "6DA88D3037675861FACAEF2A6EE7A2EDDFE50F17A907E763E8C5C522F8834DC1"
    ),
    "validate_exact_app_implementation": (
        "174F5B130ECC610E29996224E272832AE80690A4361ED08F181D6659F815A1B2"
    ),
    "validate_exact_manifest_extension": (
        "21D0C3762791A13CF217F0AD5BBB6782A228820DEC2C76BB8722B61C9DF83EDE"
    ),
    "DISCOVERY_READINESS_CHECKER_PATH": (
        "CEC5EE109DE544A5DE1794DC14E04E4AFA3DE3C9330654016B9E6B7D9BAA93B0"
    ),
    "DISCOVERY_IMPLEMENTATION_PATH": (
        "387FDAA868138DD238337BB3F7A0B6D32A53624E048C06AE14088C4DC67923DC"
    ),
    "DISCOVERY_READINESS_KNOWN_ISSUE_CODES": (
        "3DA90B815A92F5FB4262D0CE06A6467B4D440F5A511A095F7F37096D04932828"
    ),
    "DISCOVERY_READINESS_ALLOWED_V002_ISSUE_CODES": (
        "405320F6E86F34D3871CF2C515C8334946CC7BE38161E361DD781BBA9B84535D"
    ),
    "validate_exact_discovery_readiness_checker": (
        "70D84F1649D70062B47E6836127E5171152421B47DA7F2425ADD0D1A5775D798"
    ),
    "_exercise_discovery_readiness_checker_contract": (
        "85986C074B417F6CD83CCBA49A03FA83E818076B2AB56423CB4960DFBE37356B"
    ),
}
_UPSTREAM_INTEGRATION_NODE_SPECS = (
    (
        "analyze_repository",
        (("body", 16),),
        "79E5377B617F25B4454603F193897C00C94884B09F06890C9C631122D58D0791",
    ),
    (
        "analyze_repository",
        (("body", 17),),
        "39CF24EB3B8DCD3937D6E5660F2CE498EA045AD519FA41D4DF58467E9A731CC9",
    ),
    (
        "analyze_repository",
        (("body", 18),),
        "5AD8B3944FC3224BDF81D5F3871953760D051B692F2BFA46F78472CF754EA01D",
    ),
    (
        "write_base_tree",
        (("body", 5),),
        "3699622D2E7D518F649FD380C8B590E636713DE0CC3DAA4230532B6E0D6D2A1F",
    ),
    (
        "write_base_tree",
        (("body", 6),),
        "871D37D2D51328090DC00FA263205535C0B99A290C967051EBB6EA7EADAA9781",
    ),
    (
        "write_base_tree",
        (("body", 7),),
        "1AD720F4845747500566754D49F2976DD46C3023BD3847C7570E767FE38F87D9",
    ),
    (
        "run_self_test",
        (("body", 1), ("body", 8)),
        "ABDF5B6C884880E78783EF0A72B2B21BC90043F118BD86F4024E809021016E05",
    ),
)
_UPSTREAM_INTEGRATION_OWNER_HASHES = {
    "analyze_repository": (
        "078A15779DAC3E0C3DF645258DA7CB05FA363A9A2076E47C795E82E3DCCE2BA0"
    ),
    "write_base_tree": (
        "AF58C54263B82B186D18E1B99372F282A6D61B52422404D007E40ED8616853A9"
    ),
    "run_self_test": (
        "70EA657D8489E8E7A6D4F643D5DFA1178D6DE63CE4C2396CE5731A550FF6E4E1"
    ),
}
_EXACT_FIXTURE_NODE_HASHES = {
    (
        "tools/check_vendor_organization_schema.py",
        "EXPECTED_METADATA_SQL",
    ): "627E28899B04B3BD6A1FCB4263530BD75913EE898DB0CF165B5A869BAF5C4856",
    (
        "app.py",
        "VENDOR_ORGANIZATION_DATABASE_LIST_SQL",
    ): "EA748360331FF84E84781CF0E997C61D9526EB297038F1AAD9F709476E456A2A",
    (
        "tools/check_identity_registry_reconciliation_readiness.py",
        "positive_cases",
    ): "69BA81B427567053D502FDE79AA7445AC9410D8AC44AECE132759392C534F03B",
}
_SELF_AUDIT_NODE_NAMES = (
    "_ROOT_DIR",
    "_CHECKER_PATH",
    "_DISCOVERY_PATH",
    "_POLICY_PATH",
    "_UPSTREAM_CHECKER_PATH",
    "_NON_VENDOR_OUTPUT_SOURCE_PATHS",
    "_APPROVED_POLICY_SHA256",
    "_PASS_MARKER",
    "_SELF_TEST_MARKER",
    "_NORMAL_SCOPE",
    "_ISSUE_CODES",
    "_POLICY_MARKERS",
    "_POLICY_MARKER_COUNTS",
    "_ANOMALY_CATEGORIES",
    "_SOURCE_TABLES",
    "_NEW_TABLES",
    "_SENSITIVE_COLUMNS",
    "_CANONICAL_SYMBOLS",
    "_CANONICAL_CLI_OPTIONS",
    "_CANONICAL_QUERIES",
    "_NORMALIZED_CANONICAL_QUERIES",
    "_UPSTREAM_SCHEMA_METADATA_QUERIES",
    "_CANONICAL_QUERY_FRAGMENTS",
    "_EXCLUDED_TOP_LEVELS",
    "_SQL_SINKS",
    "_WRITE_CALLS",
    "_BACKEND_ROOTS",
    "_PROJECT_IMPORT_ROOTS",
    "_UPSTREAM_ALLOWED_NODE_NAMES",
    "_EXPECTED_UPSTREAM_ALLOWED_V002_ISSUE_CODES",
    "_UPSTREAM_STATIC_NODE_HASHES",
    "_UPSTREAM_INTEGRATION_NODE_SPECS",
    "_UPSTREAM_INTEGRATION_OWNER_HASHES",
    "_EXACT_FIXTURE_NODE_HASHES",
    "_SELF_AUDIT_NODE_NAMES",
    "_SELF_AUDIT_AST_SHA256",
    "_Issue",
    "_Value",
    "_Source",
    "_Callable",
    "_Repository",
    "_normalized",
    "_unique_strings",
    "_merge_values",
    "_dotted_name",
    "_assignment_targets",
    "_binding_path",
    "_binding_names",
    "_assign_binding",
    "_merge_binding_maps",
    "_module_name",
    "_relative_import_module",
    "_node_text",
    "_has_partial_discovery_name",
    "_has_discovery_target",
    "_has_canonical_query",
    "_has_canonical_query_shape",
    "_has_static_boundary_text",
    "_has_boundary_evidence",
    "_is_fixed_unsupported_text",
    "_has_source_reference",
    "_has_new_table_reference",
    "_is_select",
    "_is_mutating_sql",
    "_add_issue",
    "_read_text",
    "_read_python",
    "_section",
    "_check_policy",
    "_top_level_name",
    "_ast_sha256",
    "_ast_bundle_sha256",
    "_compact_ast_bundle_sha256",
    "_literal_assignment",
    "_assignment_value",
    "_selected_named_nodes",
    "_upstream_integration_node_ids",
    "_v002_protected_node_ids",
    "_check_upstream_guard",
    "_runtime_paths",
    "_collect_imports",
    "_imported_class_candidates",
    "_resolve_class_reference",
    "_resolve_method",
    "_call_return_value",
    "_resolve_value",
    "_prepare_repository",
    "_resolve_callable",
    "_call_leaf",
    "_classify_sql",
    "_classify_node",
    "_bind_call",
    "_scan_callable",
    "_apply_container_mutation",
    "_scan_call_node",
    "_callable_for_node",
    "_iterated_value",
    "_bind_match_pattern",
    "_direct_call_nodes",
    "_scan_nodes",
    "_self_audit",
    "_apply_source_boundary_fallback",
    "_scan_repository",
    "_dedupe_issues",
    "_analyze_repository",
    "_render_normal",
    "_parse_args",
    "_write_text",
    "_copy_baseline",
    "_assert_negative",
    "_run_self_test",
    "_main",
)
_SELF_AUDIT_AST_SHA256 = (
    "131804DFD7B54E60F399B9F8E93B66C4BD89370B2E4D83F3F4882FE68F70E884"
)


@dataclass(frozen=True, order=True)
class _Issue:
    code: str
    path: str
    line: int
    symbol: str


@dataclass(frozen=True)
class _Value:
    strings: tuple[str, ...] = ()
    items: tuple["_Value", ...] = ()
    mapping: tuple[tuple[str, "_Value"], ...] = ()
    instances: tuple[str, ...] = ()
    dynamic: bool = False

    @property
    def evidence(self) -> str:
        values = list(self.strings)
        values.extend(self.instances)
        for item in self.items:
            values.append(item.evidence)
        for key, value in self.mapping:
            values.extend((key, value.evidence))
        return " ".join(values)


@dataclass
class _Source:
    path: Path
    module_name: str
    tree: ast.Module
    imports: dict[str, tuple[str, str | None]] = field(default_factory=dict)
    constants: dict[str, _Value] = field(default_factory=dict)
    class_constants: dict[str, dict[str, _Value]] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class _Callable:
    qualified_name: str
    source_module: str
    owner_class: str | None
    binding_kind: str
    node: ast.FunctionDef | ast.AsyncFunctionDef


@dataclass
class _Repository:
    sources: dict[str, _Source]
    callables: dict[str, _Callable]
    issues: list[_Issue]
    class_bases: dict[str, tuple[str, ...]] = field(default_factory=dict)
    allowed_node_ids: set[int] = field(default_factory=set)
    active_calls: list[str] = field(default_factory=list)
    active_value_calls: list[str] = field(default_factory=list)


def _normalized(value: str) -> str:
    return " ".join(value.lower().replace("\\", "/").split())


def _unique_strings(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _merge_values(*values: _Value) -> _Value:
    all_strings = _unique_strings(
        item for value in values for item in value.strings
    )
    boundary_strings = tuple(
        item
        for item in all_strings
        if _has_static_boundary_text(item)
    )
    strings = _unique_strings((*boundary_strings, *all_strings))[:64]
    all_items = tuple(
        dict.fromkeys(item for value in values for item in value.items)
    )
    boundary_items = tuple(
        item for item in all_items if _has_boundary_evidence(item)
    )
    items = tuple(dict.fromkeys((*boundary_items, *all_items)))[:32]
    all_mapping = tuple(
        dict.fromkeys(item for value in values for item in value.mapping)
    )
    boundary_mapping = tuple(
        item
        for item in all_mapping
        if (
            _has_static_boundary_text(item[0])
            or _has_boundary_evidence(item[1])
        )
    )
    mapping = tuple(
        dict.fromkeys((*boundary_mapping, *all_mapping))
    )[:32]
    all_instances = _unique_strings(
        item for value in values for item in value.instances
    )
    boundary_instances = tuple(
        item
        for item in all_instances
        if _has_static_boundary_text(item)
    )
    instances = _unique_strings(
        (*boundary_instances, *all_instances)
    )[:16]
    return _Value(
        strings=strings,
        items=items,
        mapping=mapping,
        instances=instances,
        dynamic=(
            any(value.dynamic for value in values)
            or len(all_strings) > len(strings)
            or len(all_items) > len(items)
            or len(all_mapping) > len(mapping)
            or len(all_instances) > len(instances)
        ),
    )


def _dotted_name(node: ast.AST | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _assignment_targets(node: ast.AST) -> tuple[ast.AST, ...]:
    if isinstance(node, ast.Assign):
        return tuple(node.targets)
    if isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
        return (node.target,)
    return ()


def _binding_path(node: ast.AST) -> str:
    if isinstance(node, (ast.Name, ast.Attribute)):
        return _dotted_name(node)
    if isinstance(node, ast.Subscript):
        base = _binding_path(node.value)
        selector = node.slice
        if (
            base
            and isinstance(selector, ast.Constant)
            and type(selector.value) in {str, int}
        ):
            return f"{base}[{selector.value!r}]"
    return ""


def _binding_names(target: ast.AST) -> tuple[str, ...]:
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, ast.Attribute):
        dotted = _dotted_name(target)
        return (dotted,) if dotted else ()
    if isinstance(target, ast.Subscript):
        path = _binding_path(target)
        return (path,) if path else ()
    if isinstance(target, (ast.Tuple, ast.List)):
        return tuple(
            name
            for child in target.elts
            for name in _binding_names(
                child.value if isinstance(child, ast.Starred) else child
            )
        )
    if isinstance(target, ast.Starred):
        return _binding_names(target.value)
    return ()


def _assign_binding(
    bindings: dict[str, _Value],
    target: ast.AST,
    value: _Value,
) -> None:
    if isinstance(target, ast.Name):
        bindings[target.id] = value
        return
    if isinstance(target, ast.Attribute):
        dotted = _dotted_name(target)
        if dotted:
            bindings[dotted] = value
        return
    if isinstance(target, ast.Subscript):
        path = _binding_path(target)
        if path:
            bindings[path] = value
        base_path = _binding_path(target.value)
        if not base_path:
            return
        base = bindings.get(base_path, _Value())
        if (
            isinstance(target.slice, ast.Constant)
            and type(target.slice.value) is str
        ):
            key = target.slice.value
            mapping = tuple(
                item for item in base.mapping if item[0] != key
            ) + ((key, value),)
            merged = _merge_values(base, value)
            bindings[base_path] = _Value(
                strings=merged.strings,
                items=base.items,
                mapping=mapping[:32],
                instances=merged.instances,
                dynamic=base.dynamic,
            )
        elif (
            isinstance(target.slice, ast.Constant)
            and type(target.slice.value) is int
        ):
            index = target.slice.value
            items = list(base.items)
            if items and -len(items) <= index < len(items):
                items[index] = value
                merged = _merge_values(base, value, *items)
                bindings[base_path] = _Value(
                    strings=merged.strings,
                    items=tuple(items),
                    mapping=base.mapping,
                    instances=merged.instances,
                    dynamic=base.dynamic,
                )
            else:
                merged = _merge_values(base, value)
                bindings[base_path] = _Value(
                    strings=merged.strings,
                    items=base.items,
                    mapping=base.mapping,
                    instances=merged.instances,
                    dynamic=True,
                )
        return
    if isinstance(target, (ast.Tuple, ast.List)):
        expanded = value.items
        if expanded and len(expanded) == len(target.elts):
            for child, item in zip(target.elts, expanded, strict=True):
                _assign_binding(
                    bindings,
                    child.value if isinstance(child, ast.Starred) else child,
                    item,
                )
        else:
            for child in target.elts:
                _assign_binding(
                    bindings,
                    child.value if isinstance(child, ast.Starred) else child,
                    value,
                )
        return
    if isinstance(target, ast.Starred):
        _assign_binding(bindings, target.value, value)


def _merge_binding_maps(
    target: dict[str, _Value],
    *branches: dict[str, _Value],
) -> None:
    for name in sorted({key for branch in branches for key in branch}):
        values = [branch[name] for branch in branches if name in branch]
        if values:
            target[name] = _merge_values(*values)


def _module_name(path: Path) -> str:
    parts = list(path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _relative_import_module(
    source: _Source,
    module_name: str,
    level: int,
) -> str:
    if level <= 0:
        return module_name
    module_parts = source.module_name.split(".")
    package_parts = (
        module_parts
        if source.path.name == "__init__.py"
        else module_parts[:-1]
    )
    ascents = level - 1
    if ascents > len(package_parts):
        return ""
    base = package_parts[: len(package_parts) - ascents]
    return ".".join(
        (*base, *(part for part in module_name.split(".") if part))
    )


def _node_text(node: ast.AST) -> str:
    cache = getattr(_node_text, "_cache", {})
    cached = cache.get(node)
    if isinstance(cached, str):
        cache.pop(node)
        cache[node] = cached
        return cached
    values: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            values.append(child.id)
        elif isinstance(child, ast.Attribute):
            values.append(child.attr)
        elif isinstance(
            child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            values.append(child.name)
        elif isinstance(child, ast.arg):
            values.append(child.arg)
        elif isinstance(child, ast.alias):
            values.extend(
                value
                for value in (child.name, child.asname)
                if value is not None
            )
        elif isinstance(child, ast.Constant) and type(child.value) is str:
            values.append(child.value)
    result = " ".join(values)
    if len(cache) >= 32768:
        cache.pop(next(iter(cache)))
    cache[node] = result
    setattr(_node_text, "_cache", cache)
    return result


def _has_partial_discovery_name(value: str) -> bool:
    for identifier in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", value):
        expanded = re.sub(
            r"([a-z0-9])([A-Z])",
            r"\1_\2",
            identifier,
        )
        words = tuple(
            part
            for part in re.split(r"_+", expanded.lower())
            if part
        )
        if "vendor" not in words:
            continue
        if any(
            word
            in {
                "scan",
                "scanner",
                "analyse",
                "analysis",
                "analyze",
                "classify",
                "classification",
                "discover",
                "discovery",
            }
            for word in words
        ):
            return True
    return False


def _has_discovery_target(value: str) -> bool:
    normalized = _normalized(value)
    if any(_normalized(marker) in normalized for marker in _CANONICAL_SYMBOLS):
        return True
    category_count = sum(
        category in normalized for category in _ANOMALY_CATEGORIES
    )
    if category_count >= 3 or (
        category_count >= 1 and "vendor" in normalized
    ):
        return True
    if all(option in normalized for option in _CANONICAL_CLI_OPTIONS):
        return True
    if _has_partial_discovery_name(value) or any(
        marker in normalized
        for marker in (
            "vendor_discovery",
            "vendor discovery",
            "vendor_organization_discovery",
            "vendor organization discovery",
            "vendor_anomaly",
            "vendor anomaly",
        )
    ):
        return True
    return False


def _has_canonical_query(value: str) -> bool:
    return _normalized(value) in _NORMALIZED_CANONICAL_QUERIES


def _has_canonical_query_shape(value: str) -> bool:
    normalized = _normalized(value)
    for query in _NORMALIZED_CANONICAL_QUERIES:
        projection, remainder = query.split(" from ", 1)
        source, ordering = remainder.split(" order by ", 1)
        source_tokens = tuple(
            re.findall(r"[a-z_][a-z0-9_]*", source)
        )
        if (
            projection in normalized
            and f"order by {ordering}" in normalized
            and all(token in normalized for token in source_tokens)
        ):
            return True
    return False


def _has_static_boundary_text(value: str) -> bool:
    normalized = _normalized(value)
    specific_categories = set(_ANOMALY_CATEGORIES[:-2])
    return (
        any(symbol.lower() in normalized for symbol in _CANONICAL_SYMBOLS)
        or any(
            marker in normalized
            for marker in (
                "vendor_discovery",
                "vendor discovery",
                "vendor_organization_discovery",
                "vendor organization discovery",
                "vendor_anomaly",
                "vendor anomaly",
            )
        )
        or _has_partial_discovery_name(value)
        or any(category in normalized for category in specific_categories)
        or _has_canonical_query_shape(value)
    )


def _has_boundary_evidence(value: _Value | str) -> bool:
    evidence = value.evidence if isinstance(value, _Value) else value
    return (
        _has_static_boundary_text(evidence)
        or _has_new_table_reference(evidence)
        or any(
            _has_canonical_query(candidate)
            for candidate in (
                value.strings if isinstance(value, _Value) else (value,)
            )
        )
        or _has_canonical_query_shape(evidence)
    )


def _is_fixed_unsupported_text(value: str) -> bool:
    normalized = _normalized(value)
    return _has_discovery_target(normalized) and any(
        marker in normalized
        for marker in (
            "not supported",
            "unsupported",
            "not implemented",
            "not authorized",
            "disabled",
        )
    )


def _has_source_reference(value: str) -> bool:
    normalized = _normalized(value)
    return any(
        re.search(rf"\b{re.escape(table)}\b", normalized)
        for table in _SOURCE_TABLES
    )


def _has_new_table_reference(value: str) -> bool:
    normalized = _normalized(value)
    return any(
        re.search(rf"\b{re.escape(table)}\b", normalized)
        for table in _NEW_TABLES
    )


def _is_select(value: str) -> bool:
    return bool(re.search(r"\b(select|with)\b", _normalized(value)))


def _is_mutating_sql(value: str) -> bool:
    return bool(
        re.search(
            (
                r"\b(insert|update|delete|replace|create|alter|drop|"
                r"vacuum|attach|detach|commit)\b"
            ),
            _normalized(value),
        )
    )


def _add_issue(
    issues: list[_Issue],
    code: str,
    path: Path | str,
    node: ast.AST | None = None,
    symbol: str = "-",
) -> None:
    if code not in _ISSUE_CODES:
        raise AssertionError(f"unregistered issue code: {code}")
    issues.append(
        _Issue(
            code,
            path.as_posix() if isinstance(path, Path) else path,
            int(getattr(node, "lineno", 1) or 1),
            symbol or "-",
        )
    )


def _read_text(
    path: Path,
    relative: Path,
    issues: list[_Issue],
) -> str | None:
    try:
        payload = path.read_bytes()
    except OSError:
        _add_issue(issues, "source_read_error", relative, symbol="read")
        return None
    try:
        return payload.decode("utf-8", errors="strict")
    except UnicodeError:
        _add_issue(issues, "source_read_error", relative, symbol="utf8")
        return None


def _read_python(
    path: Path,
    relative: Path,
    issues: list[_Issue],
) -> ast.Module | None:
    source = _read_text(path, relative, issues)
    if source is None:
        return None
    cache = getattr(_read_python, "_ast_cache", {})
    cache_key = (
        relative.as_posix(),
        hashlib.sha256(source.encode("utf-8")).digest(),
    )
    cached = cache.get(cache_key)
    if isinstance(cached, ast.Module):
        cache.pop(cache_key)
        cache[cache_key] = cached
        return cached
    try:
        tree = ast.parse(source, filename=relative.as_posix())
    except SyntaxError as exc:
        _add_issue(
            issues,
            "source_parse_error",
            relative,
            symbol=f"line={int(exc.lineno or 1)}",
        )
        return None
    if len(cache) >= 96:
        cache.pop(next(iter(cache)))
    cache[cache_key] = tree
    setattr(_read_python, "_ast_cache", cache)
    return tree


def _section(text: str, number: int) -> str:
    match = re.search(
        rf"(?ms)^## {number}\..*?(?=^## {number + 1}\.|\Z)",
        text,
    )
    return match.group(0) if match else ""


def _check_policy(root: Path) -> list[_Issue]:
    issues: list[_Issue] = []
    path = root / _POLICY_PATH
    if not path.is_file():
        _add_issue(
            issues,
            "vendor_discovery_policy_document_missing",
            _POLICY_PATH,
            symbol="missing",
        )
        return issues
    text = _read_text(path, _POLICY_PATH, issues)
    if text is None:
        return issues
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest().upper()
    if digest != _APPROVED_POLICY_SHA256:
        _add_issue(
            issues,
            "vendor_discovery_policy_drift",
            _POLICY_PATH,
            symbol=f"sha256={digest}",
        )
    for marker, expected_count in _POLICY_MARKER_COUNTS:
        count = text.count(marker)
        if count != expected_count:
            _add_issue(
                issues,
                "vendor_discovery_policy_marker_missing",
                _POLICY_PATH,
                symbol=hashlib.sha256(marker.encode()).hexdigest()[:12],
            )
    headings = tuple(
        int(value)
        for value in re.findall(r"(?m)^## ([1-9][0-9]*)\.", text)
    )
    if headings != tuple(range(1, 20)):
        _add_issue(
            issues,
            "vendor_discovery_policy_drift",
            _POLICY_PATH,
            symbol="section_order",
        )
    section_nineteen = _section(text, 19)
    if not section_nineteen.startswith(
        "## 19. Production baseline freeze evidence\n"
    ):
        _add_issue(
            issues,
            "vendor_discovery_policy_drift",
            _POLICY_PATH,
            symbol="section_19_title",
        )
    for marker in (
        "DISCOVERY IMPLEMENTATION：NOT STARTED",
        "WINDOWS-ONLY DISCOVERY TOOL：NOT EXECUTED",
        (
            "REPORT / ARTIFACT / MAPPING / BACKFILL："
            "NOT IMPLEMENTED OR AUTHORIZED"
        ),
        (
            "RUNTIME CONSUMER / AUTHORITY SWITCH："
            "NOT IMPLEMENTED OR AUTHORIZED"
        ),
        "NO DATABASE OR ENVIRONMENT ACCESSED",
    ):
        if section_nineteen.count(marker) != 1:
            _add_issue(
                issues,
                "vendor_discovery_policy_marker_missing",
                _POLICY_PATH,
                symbol=(
                    "section_19_"
                    + hashlib.sha256(marker.encode()).hexdigest()[:12]
                ),
            )
    section_five = _section(text, 5)
    policy_queries = tuple(
        _normalized(match)
        for match in re.findall(
            r"(?ms)^```sql\r?\n(.*?)\r?\n```$",
            section_five,
        )
    )
    if policy_queries != _NORMALIZED_CANONICAL_QUERIES:
        _add_issue(
            issues,
            "vendor_discovery_policy_drift",
            _POLICY_PATH,
            symbol="fixed_select_contract",
        )
    if section_five.count("FROM pragma_table_list") != 1:
        _add_issue(
            issues,
            "vendor_discovery_policy_drift",
            _POLICY_PATH,
            symbol="table_list_count",
        )
    if section_five.count("FROM pragma_table_xinfo(") != 10:
        _add_issue(
            issues,
            "vendor_discovery_policy_drift",
            _POLICY_PATH,
            symbol="table_xinfo_count",
        )
    section_six = _section(text, 6)
    ordered = tuple(
        match.group(1)
        for match in re.finditer(
            r"(?m)^(?:[1-9]|1[0-4])\. `([^`]+)`$", section_six
        )
    )
    if ordered != _ANOMALY_CATEGORIES:
        _add_issue(
            issues,
            "vendor_discovery_policy_drift",
            _POLICY_PATH,
            symbol="anomaly_order",
        )
    evidence_rows = tuple(
        match.group(1)
        for match in re.finditer(r"(?m)^\| `([^`]+)` \|", section_six)
        if match.group(1) in _ANOMALY_CATEGORIES
    )
    if evidence_rows[:14] != _ANOMALY_CATEGORIES:
        _add_issue(
            issues,
            "vendor_discovery_policy_drift",
            _POLICY_PATH,
            symbol="evidence_formula_rows",
        )
    for marker in (
        "pre-topology projection",
        "all three topology fields null",
        "0 bytes",
        "one `BEGIN`",
        "one `ROLLBACK`",
    ):
        if marker not in text:
            _add_issue(
                issues,
                "vendor_discovery_policy_marker_missing",
                _POLICY_PATH,
                symbol=marker.replace(" ", "_"),
            )
    return issues


def _top_level_name(node: ast.AST) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    names = tuple(
        name
        for target in _assignment_targets(node)
        for name in _binding_names(target)
    )
    return names[0] if len(names) == 1 else ""


def _ast_sha256(node: ast.AST) -> str:
    cache = getattr(_ast_sha256, "_cache", {})
    cached = cache.get(node)
    if isinstance(cached, str):
        cache.pop(node)
        cache[node] = cached
        return cached
    payload = ast.dump(
        node,
        annotate_fields=True,
        include_attributes=False,
        indent=2,
    ).encode("utf-8")
    result = hashlib.sha256(payload).hexdigest().upper()
    if len(cache) >= 4096:
        cache.pop(next(iter(cache)))
    cache[node] = result
    setattr(_ast_sha256, "_cache", cache)
    return result


def _ast_bundle_sha256(nodes: Iterable[ast.AST]) -> str:
    exact_nodes = tuple(nodes)
    cache = getattr(_ast_bundle_sha256, "_cache", {})
    cached = cache.get(exact_nodes)
    if isinstance(cached, str):
        cache.pop(exact_nodes)
        cache[exact_nodes] = cached
        return cached
    payload = "\n".join(
        ast.dump(
            node,
            annotate_fields=True,
            include_attributes=False,
            indent=2,
        )
        for node in exact_nodes
    ).encode("utf-8")
    result = hashlib.sha256(payload).hexdigest().upper()
    if len(cache) >= 1024:
        cache.pop(next(iter(cache)))
    cache[exact_nodes] = result
    setattr(_ast_bundle_sha256, "_cache", cache)
    return result


def _compact_ast_bundle_sha256(nodes: Iterable[ast.AST]) -> str:
    exact_nodes = tuple(nodes)
    cache = getattr(_compact_ast_bundle_sha256, "_cache", {})
    cached = cache.get(exact_nodes)
    if isinstance(cached, str):
        cache.pop(exact_nodes)
        cache[exact_nodes] = cached
        return cached
    payload = "\n".join(
        ast.dump(
            node,
            annotate_fields=True,
            include_attributes=False,
        )
        for node in exact_nodes
    ).encode("utf-8")
    result = hashlib.sha256(payload).hexdigest().upper()
    if len(cache) >= 1024:
        cache.pop(next(iter(cache)))
    cache[exact_nodes] = result
    setattr(_compact_ast_bundle_sha256, "_cache", cache)
    return result


def _literal_assignment(node: ast.AST) -> object:
    value = _assignment_value(node)
    if value is None:
        raise ValueError("not a literal assignment")
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id in {"frozenset", "set", "tuple", "list"}
        and len(value.args) == 1
        and not value.keywords
    ):
        literal = ast.literal_eval(value.args[0])
        return {
            "frozenset": frozenset,
            "set": set,
            "tuple": tuple,
            "list": list,
        }[value.func.id](literal)
    return ast.literal_eval(value)


def _assignment_value(node: ast.AST) -> ast.AST | None:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        return node.value
    if isinstance(node, ast.AnnAssign):
        return node.value
    return None


def _selected_named_nodes(
    tree: ast.Module,
    names: Sequence[str],
) -> tuple[tuple[ast.AST, ...], bool]:
    by_name: dict[str, list[ast.AST]] = {}
    for node in tree.body:
        name = _top_level_name(node)
        if name:
            by_name.setdefault(name, []).append(node)
    selected: list[ast.AST] = []
    valid = True
    for name in names:
        matches = by_name.get(name, [])
        if len(matches) != 1:
            valid = False
            continue
        selected.append(matches[0])
    return tuple(selected), valid and len(selected) == len(names)


def _upstream_integration_node_ids(
    tree: ast.Module,
) -> tuple[set[int], bool]:
    owners_by_name: dict[str, list[ast.AST]] = {}
    for node in tree.body:
        name = _top_level_name(node)
        if name:
            owners_by_name.setdefault(name, []).append(node)
    owners: dict[str, ast.AST] = {}
    valid = True
    for owner_name, expected_hash in (
        _UPSTREAM_INTEGRATION_OWNER_HASHES.items()
    ):
        matches = owners_by_name.get(owner_name, [])
        if (
            len(matches) != 1
            or _ast_sha256(matches[0]) != expected_hash
        ):
            valid = False
            continue
        owners[owner_name] = matches[0]
    selected: set[int] = set()
    for owner_name, expected_path, expected_hash in (
        _UPSTREAM_INTEGRATION_NODE_SPECS
    ):
        owner = owners.get(owner_name)
        node = owner
        try:
            for field_name, item_index in expected_path:
                value = getattr(node, field_name)
                node = (
                    value
                    if item_index is None
                    else value[item_index]
                )
        except (AttributeError, IndexError, TypeError):
            node = None
        if not isinstance(node, ast.AST) or (
            _ast_sha256(node) != expected_hash
        ):
            valid = False
            continue
        selected.add(id(node))
    return selected, valid


def _v002_protected_node_ids(
    repository: _Repository,
    source: _Source,
) -> set[int]:
    upstream = repository.sources.get(
        _module_name(_UPSTREAM_CHECKER_PATH)
    )
    if upstream is None:
        return set()
    if source.path == Path("app.py"):
        names_constant = "APP_IMPLEMENTATION_NODE_NAMES"
        hash_constant = "APP_IMPLEMENTATION_AST_SHA256"
    elif source.path == Path("tools/capture_schema_manifest.py"):
        names_constant = "MANIFEST_EXTENSION_NODE_NAMES"
        hash_constant = "MANIFEST_EXTENSION_AST_SHA256"
    else:
        return set()
    upstream_nodes, valid = _selected_named_nodes(
        upstream.tree, (names_constant, hash_constant)
    )
    if not valid:
        return set()
    try:
        node_names = tuple(_literal_assignment(upstream_nodes[0]))
        expected_hash = str(_literal_assignment(upstream_nodes[1]))
    except (TypeError, ValueError, SyntaxError):
        if names_constant != "APP_IMPLEMENTATION_NODE_NAMES":
            return set()
        prefix_nodes, prefix_valid = _selected_named_nodes(
            upstream.tree, ("APP_SCHEMA_STATEMENT_NODE_NAMES",)
        )
        value = _assignment_value(upstream_nodes[0])
        if (
            not prefix_valid
            or not isinstance(value, ast.Tuple)
            or not value.elts
            or not isinstance(value.elts[0], ast.Starred)
            or not isinstance(value.elts[0].value, ast.Name)
            or value.elts[0].value.id != "APP_SCHEMA_STATEMENT_NODE_NAMES"
        ):
            return set()
        try:
            prefix = tuple(_literal_assignment(prefix_nodes[0]))
            suffix = tuple(
                ast.literal_eval(element) for element in value.elts[1:]
            )
            node_names = (*prefix, *suffix)
            expected_hash = str(_literal_assignment(upstream_nodes[1]))
        except (TypeError, ValueError, SyntaxError):
            return set()
    selected, selected_valid = _selected_named_nodes(
        source.tree, node_names
    )
    if (
        not selected_valid
        or _compact_ast_bundle_sha256(selected) != expected_hash
    ):
        return set()
    return {id(node) for node in selected}


def _check_upstream_guard(root: Path) -> list[_Issue]:
    issues: list[_Issue] = []
    path = root / _UPSTREAM_CHECKER_PATH
    tree = _read_python(path, _UPSTREAM_CHECKER_PATH, issues)
    if tree is None:
        _add_issue(
            issues,
            "upstream_vendor_schema_guard_drift",
            _UPSTREAM_CHECKER_PATH,
            symbol="missing_or_unparsed",
        )
        return issues
    nodes, valid_inventory = _selected_named_nodes(
        tree, _UPSTREAM_ALLOWED_NODE_NAMES
    )
    if not valid_inventory:
        _add_issue(
            issues,
            "upstream_vendor_schema_guard_drift",
            _UPSTREAM_CHECKER_PATH,
            symbol="integration_inventory",
        )
        return issues
    selected = dict(
        zip(_UPSTREAM_ALLOWED_NODE_NAMES, nodes, strict=True)
    )
    for name, expected_path in (
        (
            "DISCOVERY_READINESS_CHECKER_PATH",
            _CHECKER_PATH.as_posix(),
        ),
        (
            "DISCOVERY_IMPLEMENTATION_PATH",
            _DISCOVERY_PATH.as_posix(),
        ),
    ):
        observed = _assignment_value(selected[name])
        expected = ast.parse(
            f"Path({expected_path!r})", mode="eval"
        ).body
        if (
            observed is None
            or ast.dump(
                observed,
                annotate_fields=True,
                include_attributes=False,
            )
            != ast.dump(
                expected,
                annotate_fields=True,
                include_attributes=False,
            )
        ):
            _add_issue(
                issues,
                "upstream_vendor_schema_guard_drift",
                _UPSTREAM_CHECKER_PATH,
                selected[name],
                name,
            )
    try:
        known_codes = _literal_assignment(
            selected["DISCOVERY_READINESS_KNOWN_ISSUE_CODES"]
        )
    except (ValueError, SyntaxError):
        known_codes = None
    if known_codes != _ISSUE_CODES:
        _add_issue(
            issues,
            "upstream_vendor_schema_guard_drift",
            _UPSTREAM_CHECKER_PATH,
            selected["DISCOVERY_READINESS_KNOWN_ISSUE_CODES"],
            "known_issue_codes",
        )
    try:
        allowed_codes = frozenset(
            _literal_assignment(
                selected[
                    "DISCOVERY_READINESS_ALLOWED_V002_ISSUE_CODES"
                ]
            )
        )
    except (TypeError, ValueError, SyntaxError):
        allowed_codes = frozenset()
    if allowed_codes != _EXPECTED_UPSTREAM_ALLOWED_V002_ISSUE_CODES:
        _add_issue(
            issues,
            "upstream_vendor_schema_guard_drift",
            _UPSTREAM_CHECKER_PATH,
            selected["DISCOVERY_READINESS_ALLOWED_V002_ISSUE_CODES"],
            "allowed_issue_codes",
        )
    checker_tree = _read_python(
        root / _CHECKER_PATH, _CHECKER_PATH, []
    )
    try:
        upstream_node_names = tuple(
            _literal_assignment(
                selected["DISCOVERY_READINESS_NODE_NAMES"]
            )
        )
        upstream_ast_sha = str(
            _literal_assignment(
                selected["DISCOVERY_READINESS_AST_SHA256"]
            )
        )
    except (TypeError, ValueError, SyntaxError):
        upstream_node_names = ()
        upstream_ast_sha = ""
    if checker_tree is None:
        _add_issue(
            issues,
            "upstream_vendor_schema_guard_drift",
            _UPSTREAM_CHECKER_PATH,
            symbol="checker_missing",
        )
    else:
        checker_nodes, checker_inventory_valid = _selected_named_nodes(
            checker_tree, upstream_node_names
        )
        observed_checker_names = tuple(
            _top_level_name(node)
            for node in checker_tree.body
            if _top_level_name(node)
        )
        if (
            not checker_inventory_valid
            or observed_checker_names != upstream_node_names
            or _compact_ast_bundle_sha256(checker_nodes)
            != upstream_ast_sha
        ):
            _add_issue(
                issues,
                "upstream_vendor_schema_guard_drift",
                _UPSTREAM_CHECKER_PATH,
                selected["DISCOVERY_READINESS_AST_SHA256"],
                "checker_ast_fingerprint",
            )
    for name, expected_hash in _UPSTREAM_STATIC_NODE_HASHES.items():
        node = selected.get(name)
        if node is None or _ast_sha256(node) != expected_hash:
            _add_issue(
                issues,
                "upstream_vendor_schema_guard_drift",
                _UPSTREAM_CHECKER_PATH,
                node,
                f"ast={name}",
            )
    _, integration_valid = _upstream_integration_node_ids(tree)
    if not integration_valid:
        _add_issue(
            issues,
            "upstream_vendor_schema_guard_drift",
            _UPSTREAM_CHECKER_PATH,
            symbol="integration_ast_fingerprint",
        )
    runtime_functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "runtime_sources"
    ]
    if len(runtime_functions) != 1:
        _add_issue(
            issues,
            "upstream_vendor_schema_guard_drift",
            _UPSTREAM_CHECKER_PATH,
            symbol="runtime_inventory",
        )
    runtime_text = _node_text(runtime_functions[0]) if runtime_functions else ""
    if "DISCOVERY_READINESS_CHECKER_PATH" in runtime_text:
        _add_issue(
            issues,
            "upstream_vendor_schema_guard_drift",
            _UPSTREAM_CHECKER_PATH,
            symbol="checker_excluded_from_runtime",
        )
    for node in nodes:
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            call_name = _dotted_name(child.func)
            leaf = call_name.rsplit(".", 1)[-1]
            if call_name in {"__import__", "importlib.import_module"}:
                _add_issue(
                    issues,
                    "upstream_vendor_schema_guard_drift",
                    _UPSTREAM_CHECKER_PATH,
                    child,
                    f"dynamic_import={call_name}",
                )
            if leaf in _SQL_SINKS | {
                "connect",
                "create_engine",
                "getenv",
            }:
                _add_issue(
                    issues,
                    "upstream_vendor_schema_guard_drift",
                    _UPSTREAM_CHECKER_PATH,
                    child,
                    f"runtime_sink={leaf}",
                )
    return issues


def _runtime_paths(root: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    for path in root.rglob("*.py"):
        relative = path.relative_to(root)
        if not relative.parts:
            continue
        if relative.parts[0] in _EXCLUDED_TOP_LEVELS:
            continue
        paths.append(relative)
    return tuple(sorted(paths, key=lambda item: item.as_posix()))


def _collect_imports(source: _Source) -> None:
    for node in source.tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".", 1)[0]
                source.imports[local] = (alias.name, None)
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            module = _relative_import_module(
                source,
                module_name,
                node.level,
            )
            for alias in node.names:
                if alias.name == "*":
                    source.imports[f"*:{module}"] = (module, "*")
                    continue
                source.imports[alias.asname or alias.name] = (
                    module,
                    alias.name,
                )


def _imported_class_candidates(
    module: str,
    symbol: str,
    repository: _Repository,
    seen: frozenset[tuple[str, str]] = frozenset(),
) -> tuple[str, ...]:
    key = (module, symbol)
    if key in seen or len(seen) >= 16:
        return ()
    imported_source = repository.sources.get(module)
    if imported_source is None:
        return ()
    candidates: list[str] = []
    if symbol in imported_source.class_constants:
        candidates.append(f"{module}.{symbol}")
    next_seen = seen | {key}
    direct = imported_source.imports.get(symbol)
    if direct and direct[1] not in {None, "*"}:
        candidates.extend(
            _imported_class_candidates(
                direct[0],
                direct[1],
                repository,
                next_seen,
            )
        )
    for local, (star_module, star_symbol) in imported_source.imports.items():
        if local.startswith("*:") and star_symbol == "*":
            candidates.extend(
                _imported_class_candidates(
                    star_module,
                    symbol,
                    repository,
                    next_seen,
                )
            )
    return _unique_strings(candidates)


def _resolve_class_reference(
    node: ast.AST,
    source: _Source,
    repository: _Repository,
    bindings: dict[str, _Value],
) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        bound = bindings.get(node.id) or source.constants.get(node.id)
        if bound and bound.instances:
            return bound.instances
        local = f"{source.module_name}.{node.id}"
        if node.id in source.class_constants:
            return (local,)
        imported = source.imports.get(node.id)
        if imported and imported[1]:
            module, symbol = imported
            direct = f"{module}.{symbol}"
            imported_candidates = _imported_class_candidates(
                module,
                symbol,
                repository,
            )
            if imported_candidates:
                return imported_candidates
            submodule = repository.sources.get(direct)
            if submodule:
                return tuple(
                    f"{direct}.{name}"
                    for name in sorted(submodule.class_constants)
                )
    if isinstance(node, ast.Attribute):
        dotted = _dotted_name(node)
        root_name = dotted.split(".", 1)[0]
        bound = bindings.get(root_name)
        if bound and bound.instances:
            return bound.instances
        imported = source.imports.get(root_name)
        if imported:
            module, symbol = imported
            tail_parts = dotted.split(".")[1:]
            if symbol is None and root_name == module.split(".", 1)[0]:
                module_suffix = module.split(".")[1:]
                if tail_parts[: len(module_suffix)] == module_suffix:
                    tail_parts = tail_parts[len(module_suffix) :]
            tail = ".".join(tail_parts)
            candidate = ".".join(
                part for part in (module, symbol, tail) if part
            )
            owner_module, _, class_name = candidate.rpartition(".")
            owner_source = repository.sources.get(owner_module)
            if owner_source and class_name in owner_source.class_constants:
                return (candidate,)
    if isinstance(node, ast.Call) and _dotted_name(node.func) == "super":
        owner = bindings.get("__owner_class__")
        if owner:
            return tuple(
                base
                for instance in owner.instances
                for base in repository.class_bases.get(instance, ())
            )
    return ()


def _resolve_method(
    class_name: str,
    method_name: str,
    repository: _Repository,
    seen: frozenset[str] = frozenset(),
) -> _Callable | None:
    if class_name in seen:
        return None
    direct = repository.callables.get(f"{class_name}.{method_name}")
    if direct:
        return direct
    next_seen = seen | {class_name}
    for base in repository.class_bases.get(class_name, ()):
        resolved = _resolve_method(base, method_name, repository, next_seen)
        if resolved:
            return resolved
    return None


def _call_return_value(
    callable_info: _Callable,
    call: ast.Call,
    source: _Source,
    repository: _Repository,
    bindings: dict[str, _Value],
    depth: int,
) -> _Value:
    if (
        depth > 10
        or callable_info.qualified_name in repository.active_value_calls
    ):
        argument_values = [
            _resolve_value(
                argument, source, repository, bindings, depth + 1
            )
            for argument in call.args
        ]
        argument_values.extend(
            _resolve_value(
                keyword.value, source, repository, bindings, depth + 1
            )
            for keyword in call.keywords
        )
        merged = _merge_values(*argument_values)
        return _Value(
            strings=merged.strings,
            items=merged.items,
            mapping=merged.mapping,
            instances=merged.instances,
            dynamic=True,
        )
    repository.active_value_calls.append(callable_info.qualified_name)
    try:
        call_bindings, unresolved = _bind_call(
            callable_info,
            call,
            source,
            repository,
            bindings,
            depth + 1,
        )
        callable_source = repository.sources[callable_info.source_module]
        values: list[_Value] = []
        for child in ast.walk(callable_info.node):
            if (
                isinstance(child, (ast.Return, ast.Yield, ast.YieldFrom))
                and child.value is not None
            ):
                values.append(
                    _resolve_value(
                        child.value,
                        callable_source,
                        repository,
                        call_bindings,
                        depth + 1,
                    )
                )
        if not values:
            return _merge_values(*unresolved) if unresolved else _Value()
        merged = _merge_values(*values, *unresolved)
        return _Value(
            strings=merged.strings,
            items=merged.items,
            mapping=merged.mapping,
            instances=merged.instances,
            dynamic=merged.dynamic or len(values) > 1,
        )
    finally:
        repository.active_value_calls.pop()


def _resolve_value(
    node: ast.AST | None,
    source: _Source,
    repository: _Repository,
    bindings: dict[str, _Value] | None = None,
    depth: int = 0,
) -> _Value:
    if node is None:
        return _Value(dynamic=True)
    scope = bindings or {}
    if depth > 12:
        boundary_values: list[_Value] = []
        raw_text = _node_text(node)
        if (
            _has_static_boundary_text(raw_text)
            or _has_new_table_reference(raw_text)
        ):
            boundary_values.append(
                _Value(
                    strings=(raw_text,),
                    instances=("@unresolved:depth",),
                    dynamic=True,
                )
            )
        for child in ast.walk(node):
            if not isinstance(child, ast.Name):
                continue
            candidate = scope.get(child.id) or source.constants.get(child.id)
            if candidate and _has_boundary_evidence(candidate):
                boundary_values.append(candidate)
        if boundary_values:
            merged = _merge_values(*boundary_values)
            return _Value(
                strings=merged.strings,
                items=merged.items,
                mapping=merged.mapping,
                instances=_unique_strings(
                    ("@unresolved:depth", *merged.instances)
                ),
                dynamic=True,
            )
        return _Value(dynamic=True)
    if isinstance(node, ast.Constant):
        if type(node.value) is str:
            return _Value(strings=(node.value,))
        return _Value()
    if isinstance(node, ast.Name):
        if node.id in scope:
            return scope[node.id]
        if node.id in source.constants:
            return source.constants[node.id]
        callable_info = _resolve_callable(
            node, source, repository, scope
        )
        if callable_info is not None:
            return _Value(
                instances=(f"@callable:{callable_info.qualified_name}",)
            )
        imported = source.imports.get(node.id)
        if imported and imported[1]:
            imported_source = repository.sources.get(imported[0])
            if imported_source:
                return imported_source.constants.get(
                    imported[1], _Value(dynamic=True)
                )
        star_values = []
        for local, (module, symbol) in source.imports.items():
            if not local.startswith("*:") or symbol != "*":
                continue
            imported_source = repository.sources.get(module)
            if imported_source and node.id in imported_source.constants:
                star_values.append(imported_source.constants[node.id])
        if star_values:
            merged = _merge_values(*star_values)
            return _Value(
                strings=merged.strings,
                items=merged.items,
                mapping=merged.mapping,
                instances=merged.instances,
                dynamic=merged.dynamic or len(star_values) != 1,
            )
        return _Value(dynamic=True)
    if isinstance(node, ast.Attribute):
        dotted = _dotted_name(node)
        if dotted in scope:
            return scope[dotted]
        if dotted in source.constants:
            return source.constants[dotted]
        root_name = dotted.split(".", 1)[0]
        imported = source.imports.get(root_name)
        if imported:
            module, symbol = imported
            attribute = dotted.rsplit(".", 1)[-1]
            imported_source = repository.sources.get(module)
            if symbol is None and imported_source:
                return imported_source.constants.get(
                    attribute, _Value(dynamic=True)
                )
            if symbol:
                submodule = repository.sources.get(f"{module}.{symbol}")
                if submodule:
                    return submodule.constants.get(
                        attribute, _Value(dynamic=True)
                    )
        class_attribute_values: list[_Value] = []
        for qualified in _resolve_class_reference(
            node.value, source, repository, scope
        ):
            module_name, _, class_name = qualified.rpartition(".")
            owner_source = repository.sources.get(module_name)
            if owner_source:
                value = owner_source.class_constants.get(
                    class_name, {}
                ).get(node.attr)
                if value is not None:
                    class_attribute_values.append(value)
        if class_attribute_values:
            merged = _merge_values(*class_attribute_values)
            return _Value(
                strings=merged.strings,
                items=merged.items,
                mapping=merged.mapping,
                instances=merged.instances,
                dynamic=(
                    merged.dynamic
                    or len(class_attribute_values) != 1
                ),
            )
        if isinstance(node.value, ast.Name):
            owner = node.value.id
            if owner in {"self", "cls"}:
                direct_owner = scope.get(owner)
                if direct_owner and _has_boundary_evidence(direct_owner):
                    return direct_owner
                owner_value = scope.get("__owner_class__", _Value())
                for qualified in owner_value.instances:
                    module_name, _, class_name = qualified.rpartition(".")
                    owner_source = repository.sources.get(module_name)
                    if owner_source:
                        class_values = owner_source.class_constants.get(
                            class_name, {}
                        )
                        if node.attr in class_values:
                            return class_values[node.attr]
            class_values = source.class_constants.get(owner)
            if class_values and node.attr in class_values:
                return class_values[node.attr]
            bound = scope.get(owner)
            if bound:
                for qualified in bound.instances:
                    module_name, _, class_name = qualified.rpartition(".")
                    owner_source = repository.sources.get(module_name)
                    if owner_source:
                        class_values = owner_source.class_constants.get(
                            class_name, {}
                        )
                        if node.attr in class_values:
                            return class_values[node.attr]
        sink_instances = (
            (f"@sink:{node.attr}",) if node.attr in _SQL_SINKS else ()
        )
        callable_info = _resolve_callable(
            node, source, repository, scope
        )
        receiver = _resolve_value(
            node.value, source, repository, scope, depth + 1
        )
        bound_callable = (
            callable_info is not None
            and callable_info.owner_class is not None
            and callable_info.binding_kind != "static"
            and (
                callable_info.binding_kind == "class"
                or callable_info.owner_class in receiver.instances
            )
        )
        callable_instances = (
            (
                (
                    "@boundcallable:"
                    if bound_callable
                    else "@callable:"
                )
                + callable_info.qualified_name,
            )
            if callable_info is not None
            else ()
        )
        return _Value(
            strings=_unique_strings((node.attr, *receiver.strings)),
            items=receiver.items,
            mapping=receiver.mapping,
            instances=(
                *sink_instances,
                *callable_instances,
                *receiver.instances,
            ),
            dynamic=True,
        )
    if isinstance(node, ast.AugAssign):
        left = _resolve_value(
            node.target, source, repository, scope, depth + 1
        )
        right = _resolve_value(
            node.value, source, repository, scope, depth + 1
        )
        if isinstance(node.op, ast.Add):
            combined: list[str] = []
            if left.strings and right.strings:
                for first in left.strings[:8]:
                    for second in right.strings[:8]:
                        combined.append(first + second)
            return _Value(
                strings=_unique_strings(
                    (*combined, *left.strings, *right.strings)
                ),
                items=(*left.items, *right.items),
                mapping=(*left.mapping, *right.mapping),
                instances=_unique_strings(
                    (*left.instances, *right.instances)
                ),
                dynamic=left.dynamic or right.dynamic or not combined,
            )
        merged = _merge_values(left, right)
        return _Value(
            strings=merged.strings,
            items=merged.items,
            mapping=merged.mapping,
            instances=merged.instances,
            dynamic=True,
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _resolve_value(
            node.left, source, repository, scope, depth + 1
        )
        right = _resolve_value(
            node.right, source, repository, scope, depth + 1
        )
        combined: list[str] = []
        if left.strings and right.strings:
            for first in left.strings[:8]:
                for second in right.strings[:8]:
                    combined.append(first + second)
        return _Value(
            strings=_unique_strings((*combined, *left.strings, *right.strings)),
            instances=_unique_strings(
                (*left.instances, *right.instances)
            ),
            dynamic=left.dynamic or right.dynamic or not combined,
        )
    if isinstance(node, ast.JoinedStr):
        parts = []
        candidates = ("",)
        for value in node.values:
            part = _resolve_value(
                value.value if isinstance(value, ast.FormattedValue) else value,
                source,
                repository,
                scope,
                depth + 1,
            )
            parts.append(part)
            next_candidates: list[str] = []
            for prefix in candidates[:8]:
                for suffix in part.strings[:8] or ("",):
                    next_candidates.append(prefix + suffix)
            candidates = tuple(next_candidates) or candidates
        merged = _merge_values(*parts)
        return _Value(
            strings=_unique_strings((*candidates, *merged.strings)),
            items=merged.items,
            mapping=merged.mapping,
            instances=merged.instances,
            dynamic=True,
        )
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        expanded_items: list[_Value] = []
        ambiguous_star = False
        for item in node.elts:
            value = _resolve_value(
                item, source, repository, scope, depth + 1
            )
            if isinstance(item, ast.Starred):
                if value.items:
                    expanded_items.extend(value.items)
                else:
                    expanded_items.append(value)
                    ambiguous_star = True
            else:
                expanded_items.append(value)
        boundary_items = [
            item
            for item in expanded_items
            if _has_boundary_evidence(item)
        ]
        items = (
            tuple(expanded_items)
            if len(expanded_items) <= 32
            else tuple(
                dict.fromkeys((*boundary_items, *expanded_items))
            )[:32]
        )
        return _Value(
            strings=_unique_strings(
                value for item in items for value in item.strings
            ),
            items=items,
            instances=_unique_strings(
                (
                    "@container:tuple"
                    if isinstance(node, ast.Tuple)
                    else (
                        "@container:list"
                        if isinstance(node, ast.List)
                        else "@container:set"
                    ),
                    *(
                        instance
                        for item in items
                        for instance in item.instances
                        if instance.startswith("@unresolved:")
                    ),
                ),
            ),
            dynamic=(
                isinstance(node, ast.Set)
                or ambiguous_star
                or len(expanded_items) > len(items)
                or any(item.dynamic for item in items)
            ),
        )
    if isinstance(node, ast.Dict):
        mapping: list[tuple[str, _Value]] = []
        unpacked: list[_Value] = []
        for key, value in zip(node.keys, node.values):
            if key is None:
                expanded = _resolve_value(
                    value, source, repository, scope, depth + 1
                )
                mapping.extend(expanded.mapping)
                unpacked.append(expanded)
                continue
            key_value = _resolve_value(
                key, source, repository, scope, depth + 1
            )
            value_value = _resolve_value(
                value, source, repository, scope, depth + 1
            )
            for key_string in key_value.strings:
                mapping.append((key_string, value_value))
        return _Value(
            strings=_unique_strings(
                value
                for _, item in mapping
                for value in item.strings
            ),
            mapping=tuple(mapping),
            instances=_unique_strings(
                (
                    "@container:dict",
                    *(
                        instance
                        for value in unpacked
                        for instance in value.instances
                    ),
                )
            ),
            dynamic=not mapping or any(value.dynamic for value in unpacked),
        )
    if isinstance(node, ast.Subscript):
        exact_path = _binding_path(node)
        if exact_path in scope:
            return scope[exact_path]
        if exact_path in source.constants:
            return source.constants[exact_path]
        container = _resolve_value(
            node.value, source, repository, scope, depth + 1
        )
        selector = _resolve_value(
            node.slice, source, repository, scope, depth + 1
        )
        if container.mapping and selector.strings:
            selected = [
                value
                for key, value in container.mapping
                if key in selector.strings
            ]
            return _merge_values(*selected) if selected else _Value(dynamic=True)
        if container.items and isinstance(node.slice, ast.Constant):
            if type(node.slice.value) is int:
                try:
                    return container.items[node.slice.value]
                except IndexError:
                    return _Value(dynamic=True)
        return _Value(
            strings=container.strings,
            dynamic=True,
        )
    if isinstance(node, (ast.BoolOp, ast.IfExp)):
        children: list[ast.AST]
        if isinstance(node, ast.BoolOp):
            children = list(node.values)
        else:
            children = [node.body, node.orelse]
        return _merge_values(
            *(
                _resolve_value(
                    child, source, repository, scope, depth + 1
                )
                for child in children
            )
        )
    if isinstance(node, ast.Starred):
        return _resolve_value(
            node.value, source, repository, scope, depth + 1
        )
    if isinstance(node, ast.Call):
        name = _dotted_name(node.func)
        receiver = (
            _resolve_value(
                node.func.value, source, repository, scope, depth + 1
            )
            if isinstance(node.func, ast.Attribute)
            else _Value()
        )
        arguments = [
            _resolve_value(arg, source, repository, scope, depth + 1)
            for arg in node.args
        ]
        arguments.extend(
            _resolve_value(
                keyword.value, source, repository, scope, depth + 1
            )
            for keyword in node.keywords
        )
        if isinstance(node.func, ast.Name) and node.func.id in {
            "dict",
            "list",
            "set",
            "tuple",
        }:
            merged = _merge_values(*arguments)
            return _Value(
                strings=merged.strings,
                items=merged.items,
                mapping=merged.mapping,
                instances=_unique_strings(
                    (
                        f"@container:{node.func.id}",
                        *merged.instances,
                    )
                ),
                dynamic=merged.dynamic,
            )
        if name.endswith((".format", ".replace", ".join", ".strip")):
            merged = _merge_values(receiver, *arguments)
            return _Value(
                strings=merged.strings,
                items=merged.items,
                mapping=merged.mapping,
                instances=merged.instances,
                dynamic=True,
            )
        classes = _resolve_class_reference(
            node.func, source, repository, scope
        )
        if classes:
            merged = _merge_values(*arguments)
            return _Value(
                strings=merged.strings,
                items=merged.items,
                mapping=merged.mapping,
                instances=classes,
                dynamic=merged.dynamic,
            )
        callable_info = _resolve_callable(
            node.func, source, repository, scope
        )
        if callable_info:
            merged_arguments = _merge_values(*arguments)
            callable_text = _node_text(callable_info.node)
            callable_source = repository.sources[
                callable_info.source_module
            ]
            if (
                _has_boundary_evidence(merged_arguments)
                or _has_static_boundary_text(callable_text)
                or (
                    callable_source.path != _UPSTREAM_CHECKER_PATH
                    and _has_new_table_reference(callable_text)
                )
                or any(
                    _has_canonical_query(item)
                    for item in (
                        child.value
                        for child in ast.walk(callable_info.node)
                        if isinstance(child, ast.Constant)
                        and type(child.value) is str
                    )
                )
            ):
                return _call_return_value(
                    callable_info,
                    node,
                    source,
                    repository,
                    scope,
                    depth + 1,
                )
            return _Value(
                strings=merged_arguments.strings,
                items=merged_arguments.items,
                mapping=merged_arguments.mapping,
                instances=merged_arguments.instances,
                dynamic=True,
            )
        merged = _merge_values(receiver, *arguments)
        return _Value(
            strings=merged.strings,
            items=merged.items,
            mapping=merged.mapping,
            instances=merged.instances,
            dynamic=True,
        )
    return _Value(
        strings=tuple(
            child.value
            for child in ast.walk(node)
            if isinstance(child, ast.Constant)
            and type(child.value) is str
        ),
        dynamic=True,
    )


def _prepare_repository(
    root: Path,
    issues: list[_Issue],
) -> _Repository:
    sources: dict[str, _Source] = {}
    callables: dict[str, _Callable] = {}
    class_nodes: list[tuple[_Source, ast.ClassDef, str]] = []
    for relative in _runtime_paths(root):
        tree = _read_python(root / relative, relative, issues)
        if tree is None:
            continue
        module_name = _module_name(relative)
        source_key = module_name
        if source_key in sources:
            _add_issue(
                issues,
                "source_parse_error",
                relative,
                symbol=f"module_collision:{module_name}",
            )
            source_key = (
                f"{module_name}.__collision_{len(sources)}"
            )
        source = _Source(relative, source_key, tree)
        _collect_imports(source)
        sources[source_key] = source

        def collect(
            nodes: Iterable[ast.AST],
            lexical: tuple[str, ...] = (),
            owner_class: str | None = None,
        ) -> None:
            for node in nodes:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qualified = ".".join(
                        (source_key, *lexical, node.name)
                    )
                    binding_kind = "module"
                    if owner_class:
                        binding_kind = "instance"
                        decorator_names = {
                            _dotted_name(item)
                            for item in node.decorator_list
                        }
                        if "staticmethod" in decorator_names:
                            binding_kind = "static"
                        elif "classmethod" in decorator_names:
                            binding_kind = "class"
                    if qualified in callables:
                        _add_issue(
                            issues,
                            "source_parse_error",
                            relative,
                            node,
                            f"duplicate_callable:{qualified}",
                        )
                    else:
                        callables[qualified] = _Callable(
                            qualified,
                            source_key,
                            owner_class,
                            binding_kind,
                            node,
                        )
                    collect(
                        node.body,
                        (*lexical, node.name),
                        None,
                    )
                elif isinstance(node, ast.ClassDef):
                    class_suffix = ".".join((*lexical, node.name))
                    qualified_class = f"{source_key}.{class_suffix}"
                    if class_suffix in source.class_constants:
                        _add_issue(
                            issues,
                            "source_parse_error",
                            relative,
                            node,
                            f"duplicate_class:{qualified_class}",
                        )
                    class_values: dict[str, _Value] = {}
                    source.class_constants[class_suffix] = class_values
                    source.class_constants.setdefault(
                        node.name, class_values
                    )
                    class_nodes.append((source, node, qualified_class))
                    collect(
                        node.body,
                        (*lexical, node.name),
                        qualified_class,
                    )

        collect(tree.body)
    repository = _Repository(sources, callables, issues)
    assigned_constant_names: dict[str, set[str]] = {
        source.module_name: {
            name
            for node in source.tree.body
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            for target in _assignment_targets(node)
            for name in _binding_names(target)
        }
        for source in sources.values()
    }
    for source, node, qualified_class in class_nodes:
        bases: list[str] = []
        for base in node.bases:
            references = _resolve_class_reference(
                base, source, repository, {}
            )
            bases.extend(references)
        repository.class_bases[qualified_class] = _unique_strings(bases)
    for source in sources.values():
        for node in source.tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value_node = node.value
                value = _resolve_value(value_node, source, repository)
                for target in _assignment_targets(node):
                    for name in _binding_names(target):
                        source.constants[name] = value
    for source, node, qualified_class in class_nodes:
        class_suffix = qualified_class.removeprefix(
            f"{source.module_name}."
        )
        values = source.class_constants[class_suffix]
        for child in node.body:
            if isinstance(child, (ast.Assign, ast.AnnAssign)):
                value = _resolve_value(child.value, source, repository)
                for target in _assignment_targets(child):
                    for name in _binding_names(target):
                        values[name.rsplit(".", 1)[-1]] = value
    propagation_budget = max(
        1,
        1
        + len(class_nodes)
        + sum(
            1
            for source in sources.values()
            for node in ast.walk(source.tree)
            if isinstance(
                node,
                (
                    ast.Assign,
                    ast.AnnAssign,
                    ast.AugAssign,
                    ast.NamedExpr,
                    ast.Import,
                    ast.ImportFrom,
                ),
            )
        ),
    )
    converged = False
    for _ in range(propagation_budget):
        changed = False
        for source in sources.values():
            imported_values: dict[str, list[_Value]] = {}
            for local, (module, symbol) in source.imports.items():
                imported_source = sources.get(module)
                if imported_source is None:
                    continue
                if symbol == "*":
                    for name, value in imported_source.constants.items():
                        if not name.startswith("_"):
                            imported_values.setdefault(name, []).append(value)
                elif symbol is not None:
                    value = imported_source.constants.get(symbol)
                    if value is not None:
                        imported_values.setdefault(local, []).append(value)
            for name, values in imported_values.items():
                if name in assigned_constant_names[source.module_name]:
                    continue
                merged = _merge_values(*values)
                imported_value = _Value(
                    strings=merged.strings,
                    items=merged.items,
                    mapping=merged.mapping,
                    instances=merged.instances,
                    dynamic=merged.dynamic or len(values) != 1,
                )
                if source.constants.get(name) != imported_value:
                    source.constants[name] = imported_value
                    changed = True
            for node in source.tree.body:
                if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                    continue
                value = _resolve_value(node.value, source, repository)
                for target_node in _assignment_targets(node):
                    for name in _binding_names(target_node):
                        if source.constants.get(name) != value:
                            source.constants[name] = value
                            changed = True
        for source, node, qualified_class in class_nodes:
            class_suffix = qualified_class.removeprefix(
                f"{source.module_name}."
            )
            target = source.class_constants[class_suffix]
            inherited: dict[str, _Value] = {}
            for base in repository.class_bases.get(qualified_class, ()):
                module_name, _, base_name = base.rpartition(".")
                parent_source = sources.get(module_name)
                if parent_source:
                    for name, value in parent_source.class_constants.get(
                        base_name,
                        {},
                    ).items():
                        inherited.setdefault(name, value)
            for name, value in inherited.items():
                if name not in target:
                    target[name] = value
                    changed = True
            for child in node.body:
                if not isinstance(child, (ast.Assign, ast.AnnAssign)):
                    continue
                value = _resolve_value(child.value, source, repository)
                for target_node in _assignment_targets(child):
                    for name in _binding_names(target_node):
                        leaf = name.rsplit(".", 1)[-1]
                        if target.get(leaf) != value:
                            target[leaf] = value
                            changed = True
        if not changed:
            converged = True
            break
    if not converged:
        for source in sources.values():
            if any(
                _has_boundary_evidence(value)
                for value in source.constants.values()
            ) or any(
                _has_boundary_evidence(value)
                for values in source.class_constants.values()
                for value in values.values()
            ):
                _add_issue(
                    repository.issues,
                    "unresolved_vendor_discovery_capability",
                    source.path,
                    symbol="constant_fixed_point",
                )
    return repository


def _resolve_callable(
    node: ast.AST,
    source: _Source,
    repository: _Repository,
    bindings: dict[str, _Value] | None = None,
) -> _Callable | None:
    scope = bindings or {}
    dotted = _dotted_name(node)
    if not dotted:
        return None
    if isinstance(node, ast.Name):
        bound = scope.get(node.id) or source.constants.get(node.id)
        if bound:
            callable_names = tuple(
                value.split(":", 1)[1]
                for value in bound.instances
                if value.startswith(("@callable:", "@boundcallable:"))
            )
            if len(set(callable_names)) == 1:
                return repository.callables.get(callable_names[0])
        imported = source.imports.get(node.id)
        if imported and imported[1]:
            return repository.callables.get(
                f"{imported[0]}.{imported[1]}"
            )
        direct = repository.callables.get(f"{source.module_name}.{node.id}")
        if direct:
            return direct
        candidates = [
            item
            for item in repository.callables.values()
            if item.source_module == source.module_name
            and item.node.name == node.id
        ]
        return candidates[0] if len(candidates) == 1 else None
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Call):
        if _dotted_name(node.value.func) == "super":
            for class_name in _resolve_class_reference(
                node.value, source, repository, scope
            ):
                resolved = _resolve_method(
                    class_name, node.attr, repository
                )
                if resolved:
                    return resolved
        class_name = _dotted_name(node.value.func)
        imported = source.imports.get(class_name)
        if imported and imported[1]:
            return repository.callables.get(
                f"{imported[0]}.{imported[1]}.{node.attr}"
            )
        return repository.callables.get(
            f"{source.module_name}.{class_name}.{node.attr}"
        )
    if isinstance(node, ast.Attribute):
        for class_name in _resolve_class_reference(
            node.value, source, repository, scope
        ):
            resolved = _resolve_method(class_name, node.attr, repository)
            if resolved:
                return resolved
        if isinstance(node.value, ast.Name) and node.value.id in {"self", "cls"}:
            owner = scope.get("__owner_class__", _Value())
            for class_name in owner.instances:
                resolved = _resolve_method(
                    class_name, node.attr, repository
                )
                if resolved:
                    return resolved
    parts = dotted.split(".")
    imported = source.imports.get(parts[0])
    if imported:
        module, symbol = imported
        tail = ".".join(parts[1:])
        if symbol:
            return repository.callables.get(
                ".".join(item for item in (module, symbol, tail) if item)
            )
        return repository.callables.get(
            ".".join(item for item in (module, tail) if item)
        )
    if len(parts) == 2:
        direct = repository.callables.get(
            f"{source.module_name}.{parts[0]}.{parts[1]}"
        )
        if direct:
            return direct
    return None


def _call_leaf(
    node: ast.AST,
    source: _Source,
    repository: _Repository,
    bindings: dict[str, _Value],
) -> str:
    if isinstance(node, ast.Name):
        bound = bindings.get(node.id)
        if bound:
            sinks = [
                value.removeprefix("@sink:")
                for value in bound.instances
                if value.startswith("@sink:")
            ]
            if len(set(sinks)) == 1:
                return sinks[0]
    if (
        isinstance(node, ast.Call)
        and _dotted_name(node.func) == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and type(node.args[1].value) is str
        and node.args[1].value in _SQL_SINKS
    ):
        return node.args[1].value
    dotted = _dotted_name(node)
    if dotted:
        return dotted.rsplit(".", 1)[-1]
    resolved = _resolve_value(node, source, repository, bindings)
    sinks = [
        value.removeprefix("@sink:")
        for value in resolved.instances
        if value.startswith("@sink:")
    ]
    return sinks[0] if len(set(sinks)) == 1 else ""


def _classify_sql(
    repository: _Repository,
    source: _Source,
    node: ast.Call,
    value: _Value,
    context: str,
    bindings: dict[str, _Value],
) -> None:
    sink = _call_leaf(node.func, source, repository, bindings)
    evidence = f"{context} {value.evidence}"
    target = (
        _has_static_boundary_text(evidence)
        or _has_new_table_reference(value.evidence)
    )
    source_reference = _has_source_reference(value.evidence)
    if sink not in _SQL_SINKS:
        return
    query_shape = _has_canonical_query_shape(value.evidence)
    if any(
        marker.startswith("@unresolved:")
        for marker in value.instances
    ):
        _add_issue(
            repository.issues,
            "unresolved_vendor_discovery_capability",
            source.path,
            node,
            sink,
        )
    if value.dynamic and (target or query_shape):
        _add_issue(
            repository.issues,
            "dynamic_vendor_discovery_sql",
            source.path,
            node,
            sink,
        )
    for statement in value.strings:
        normalized = _normalized(statement)
        if (
            _has_canonical_query(statement)
            or (
                target
                and any(
                    fragment in normalized
                    for fragment in _CANONICAL_QUERY_FRAGMENTS
                )
            )
            or (target and source_reference and _is_select(statement))
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_query",
                source.path,
                node,
                sink,
            )
        if (
            target
            and source_reference
            and "*" in statement
            and _is_select(statement)
        ):
            _add_issue(
                repository.issues,
                "dynamic_vendor_discovery_sql",
                source.path,
                node,
                "wildcard",
            )
        if target and any(
            column in normalized for column in _SENSITIVE_COLUMNS
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_sensitive_read",
                source.path,
                node,
                sink,
            )
        if target and _is_mutating_sql(statement):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_mutation",
                source.path,
                node,
                sink,
            )
        if target and re.search(
            r"\b(attach|detach|vacuum|commit|pragma)\b", normalized
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_transaction",
                source.path,
                node,
                sink,
            )


def _classify_node(
    repository: _Repository,
    source: _Source,
    node: ast.AST,
    context: str,
    bindings: dict[str, _Value],
) -> None:
    text = f"{context} {_node_text(node)}"
    normalized = _normalized(text)
    target = _has_static_boundary_text(text)
    identity_contract_source = source.path in _NON_VENDOR_OUTPUT_SOURCE_PATHS
    category_hits = tuple(
        category
        for category in _ANOMALY_CATEGORIES
        if category in normalized
    )
    if category_hits and not identity_contract_source:
        _add_issue(
            repository.issues,
            "forbidden_vendor_discovery_output_contract",
            source.path,
            node,
            category_hits[0],
        )
    cli_hits = tuple(
        option for option in _CANONICAL_CLI_OPTIONS if option in normalized
    )
    if cli_hits and not identity_contract_source:
        _add_issue(
            repository.issues,
            "partial_vendor_discovery_implementation",
            source.path,
            node,
            cli_hits[0],
        )
    if isinstance(
        node,
        (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda),
    ) and target:
        _add_issue(
            repository.issues,
            "partial_vendor_discovery_implementation",
            source.path,
            node,
            getattr(node, "name", "lambda"),
        )
    if all(option in normalized for option in _CANONICAL_CLI_OPTIONS):
        _add_issue(
            repository.issues,
            "partial_vendor_discovery_implementation",
            source.path,
            node,
            "canonical_cli",
        )
    candidate_value = _Value()
    if isinstance(
        node,
        (
            ast.Assign,
            ast.AnnAssign,
            ast.AugAssign,
            ast.NamedExpr,
            ast.Return,
            ast.Expr,
            ast.Lambda,
        ),
    ):
        value_node = (
            node if isinstance(node, ast.AugAssign)
            else getattr(node, "value", None)
        )
        candidate_value = _resolve_value(
            value_node, source, repository, bindings
        )
        candidate_normalized = _normalized(candidate_value.evidence)
        if not identity_contract_source:
            resolved_categories = tuple(
                category
                for category in _ANOMALY_CATEGORIES
                if category in candidate_normalized
            )
            if resolved_categories:
                _add_issue(
                    repository.issues,
                    "forbidden_vendor_discovery_output_contract",
                    source.path,
                    node,
                    resolved_categories[0],
                )
            resolved_cli = tuple(
                option
                for option in _CANONICAL_CLI_OPTIONS
                if option in candidate_normalized
            )
            if resolved_cli:
                _add_issue(
                    repository.issues,
                    "partial_vendor_discovery_implementation",
                    source.path,
                    node,
                    resolved_cli[0],
                )
        for statement in candidate_value.strings:
            if (
                _has_canonical_query(statement)
                and not (
                    source.path == _UPSTREAM_CHECKER_PATH
                    and statement in _UPSTREAM_SCHEMA_METADATA_QUERIES
                )
            ) or (
                _has_canonical_query_shape(candidate_value.evidence)
                and source.path != _UPSTREAM_CHECKER_PATH
            ):
                _add_issue(
                    repository.issues,
                    "forbidden_vendor_discovery_query",
                    source.path,
                    node,
                    "fixed_query",
                )
        if (
            _has_static_boundary_text(candidate_value.evidence)
            and not _is_fixed_unsupported_text(candidate_value.evidence)
        ):
            _add_issue(
                repository.issues,
                "partial_vendor_discovery_implementation",
                source.path,
                node,
                "target_value",
            )
    if source.path == _DISCOVERY_PATH:
        _add_issue(
            repository.issues,
            "forbidden_vendor_discovery_module_path",
            source.path,
            node,
            "canonical",
        )
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif node.module:
            modules.append(node.module)
        roots = {module.split(".", 1)[0] for module in modules}
        module_target = _has_discovery_target(source.path.as_posix())
        if target:
            _add_issue(
                repository.issues,
                "partial_vendor_discovery_implementation",
                source.path,
                node,
                "target_import",
            )
        if "app" in roots and (target or module_target):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_app_import",
                source.path,
                node,
                "app",
            )
        if roots & _BACKEND_ROOTS and (target or module_target):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_backend_access",
                source.path,
                node,
                ",".join(sorted(roots & _BACKEND_ROOTS)),
            )
        if roots & _PROJECT_IMPORT_ROOTS and (target or module_target):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_app_import",
                source.path,
                node,
                ",".join(sorted(roots & _PROJECT_IMPORT_ROOTS)),
            )
    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
        value = _resolve_value(node.value, source, repository, bindings)
        evidence = value.evidence
        value_normalized = _normalized(evidence)
        if (
            (
                _has_canonical_query(evidence)
                and not (
                    source.path == _UPSTREAM_CHECKER_PATH
                    and evidence in _UPSTREAM_SCHEMA_METADATA_QUERIES
                )
            )
            or (
                _has_canonical_query_shape(evidence)
                and source.path != _UPSTREAM_CHECKER_PATH
            )
            or (
                target
                and _is_select(evidence)
                and any(
                    fragment in value_normalized
                    for fragment in _CANONICAL_QUERY_FRAGMENTS
                )
            )
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_query",
                source.path,
                node,
                "query_constant",
            )
        elif target and _has_source_reference(evidence) and _is_select(evidence):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_query",
                source.path,
                node,
                "source_query",
            )
            if "*" in evidence:
                _add_issue(
                    repository.issues,
                    "dynamic_vendor_discovery_sql",
                    source.path,
                    node,
                    "wildcard",
                )
        elif (
            _has_static_boundary_text(evidence)
            and not _is_fixed_unsupported_text(evidence)
        ):
            _add_issue(
                repository.issues,
                "partial_vendor_discovery_implementation",
                source.path,
                node,
                "target_constant",
            )
        elif target and not _is_fixed_unsupported_text(evidence):
            _add_issue(
                repository.issues,
                "partial_vendor_discovery_implementation",
                source.path,
                node,
                "partial_constant",
            )
    if target:
        if any(
            word in normalized
            for word in (
                "whole_file",
                "whole_function",
                "wildcard_exemption",
                "ignore_path",
                "allow_all",
                "generic_allowlist",
                "suppress",
            )
        ):
            _add_issue(
                repository.issues,
                "checker_exemption_broadening",
                source.path,
                node,
                "exemption",
            )
        if any(
            word in normalized
            for word in (
                "candidate",
                "winner",
                "ranking",
                "confidence",
                "best_match",
            )
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_selection",
                source.path,
                node,
                "selection",
            )
        if any(
            word in normalized
            for word in ("mapping", "map_vendor", "backfill", "apply_plan")
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_mapping",
                source.path,
                node,
                "mapping",
            )
        if any(
            word in normalized
            for word in (
                "insert",
                "update",
                "delete",
                "repair",
                "mutate",
                "create_organization",
                "create_membership",
                "create_assignment",
                "create_binding",
            )
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_mutation",
                source.path,
                node,
                "mutation",
            )
        if any(
            word in normalized
            for word in (
                "route",
                "api",
                "template",
                "ui",
                "scheduled_job",
                "runtime_consumer",
                "deployment_hook",
            )
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_consumer",
                source.path,
                node,
                "consumer",
            )
        if any(
            word in normalized
            for word in ("production", "render", "live_operator")
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_production_access",
                source.path,
                node,
                "production",
            )
        if any(
            word in normalized
            for word in (
                "database_url",
                "app_db_path",
                "os.environ",
                "getenv",
                "environ",
            )
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_environment_access",
                source.path,
                node,
                "environment",
            )
        if any(
            word in normalized
            for word in (
                "site.db",
                "repository_db",
                "canonical_db",
                "immutable=1",
                "vfs=",
                "cache=shared",
                "nolock=",
            )
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_path_access",
                source.path,
                node,
                "path",
            )
        if any(
            word in normalized
            for word in (
                "output_path",
                "write_text",
                "write_bytes",
                "artifact",
                "report",
                "export",
                "download",
                "upload",
            )
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_artifact",
                source.path,
                node,
                "artifact",
            )
        if any(column in normalized for column in _SENSITIVE_COLUMNS):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_sensitive_read",
                source.path,
                node,
                "sensitive",
            )
        if any(
            word in normalized
            for word in (
                "raw_label",
                "normalized_label",
                "raw_vendor",
                "raw_id",
                "identifier_hash",
                "sql_row",
                "source_path",
                "vendor_id",
                "vendor_account_id",
                "site_id",
                "sheet_id",
            )
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_raw_disclosure",
                source.path,
                node,
                "raw",
            )
        if any(
            word in normalized
            for word in ("authorizer_allow_all", "broad_read", "broad_function")
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_authorizer",
                source.path,
                node,
                "authorizer",
            )
        if any(
            word in normalized
            for word in (
                "transaction",
                "begin",
                "commit",
                "rollback",
                "savepoint",
                "release",
                "attach",
                "detach",
                "vacuum",
                "pragma",
            )
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_transaction",
                source.path,
                node,
                "transaction",
            )
        if any(
            word in normalized
            for word in (
                "emit_partial_json",
                "rollback_ignored",
                "cleanup_ignored",
                "runtimeerror_operational",
                "exception_detail",
                "exception_cause",
                "exception_context",
            )
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_error_contract",
                source.path,
                node,
                "error",
            )
        if any(
            word in normalized
            for word in (
                "unknown_observed",
                "noncanonical_json",
                "noncanonical_hash",
                "reversible_hash",
                "anomaly_reordered",
                "fabricated_topology",
            )
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_output_contract",
                source.path,
                node,
                "output",
            )
    if isinstance(node, ast.Call):
        call_name = _dotted_name(node.func)
        leaf = _call_leaf(node.func, source, repository, bindings)
        values = [
            _resolve_value(arg, source, repository, bindings)
            for arg in node.args
        ]
        keyword_values = [
            _resolve_value(item.value, source, repository, bindings)
            for item in node.keywords
        ]
        merged = _merge_values(*values, *keyword_values)
        merged_normalized = _normalized(merged.evidence)
        if not identity_contract_source:
            resolved_categories = tuple(
                category
                for category in _ANOMALY_CATEGORIES
                if category in merged_normalized
            )
            if resolved_categories:
                _add_issue(
                    repository.issues,
                    "forbidden_vendor_discovery_output_contract",
                    source.path,
                    node,
                    resolved_categories[0],
                )
            resolved_cli = tuple(
                option
                for option in _CANONICAL_CLI_OPTIONS
                if option in merged_normalized
            )
            if resolved_cli:
                _add_issue(
                    repository.issues,
                    "partial_vendor_discovery_implementation",
                    source.path,
                    node,
                    resolved_cli[0],
                )
        if leaf in _SQL_SINKS:
            sql_value = values[0] if values else merged
            _classify_sql(
                repository,
                source,
                node,
                sql_value,
                context,
                bindings,
            )
        if leaf in _WRITE_CALLS and (
            target or _has_discovery_target(merged.evidence)
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_artifact",
                source.path,
                node,
                leaf,
            )
        if target and leaf in {
            "print",
            "log",
            "info",
            "warning",
            "error",
            "debug",
        }:
            argument_text = _normalized(merged.evidence)
            if any(
                marker in argument_text
                for marker in (
                    "vendor_id",
                    "vendor_account_id",
                    "site_id",
                    "sheet_id",
                    "vendor_name",
                    "display_name",
                    "normalized_label",
                    "raw_label",
                )
            ):
                _add_issue(
                    repository.issues,
                    "forbidden_vendor_discovery_raw_disclosure",
                    source.path,
                    node,
                    leaf,
                )
        if call_name in {"os.getenv", "os.environ.get"} and (
            target or _has_discovery_target(merged.evidence)
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_environment_access",
                source.path,
                node,
                call_name,
            )


def _bind_call(
    callable_info: _Callable,
    call: ast.Call,
    source: _Source,
    repository: _Repository,
    bindings: dict[str, _Value],
    depth: int = 0,
) -> tuple[dict[str, _Value], list[_Value]]:
    args = callable_info.node.args
    positional_names = [item.arg for item in (*args.posonlyargs, *args.args)]
    values: list[_Value] = []
    unresolved: list[_Value] = []
    receiver_attributes: dict[str, _Value] = {}
    if (
        callable_info.owner_class
        and callable_info.binding_kind != "static"
        and positional_names
    ):
        receiver = _Value()
        if isinstance(call.func, ast.Attribute):
            receiver = _resolve_value(
                call.func.value,
                source,
                repository,
                bindings,
                depth + 1,
            )
            receiver_path = _dotted_name(call.func.value)
            if receiver_path:
                prefix = receiver_path + "."
                combined_scope = {
                    **source.constants,
                    **bindings,
                }
                receiver_attributes = {
                    name.removeprefix(prefix): value
                    for name, value in sorted(combined_scope.items())
                    if name.startswith(prefix)
                    and name.removeprefix(prefix)
                }
        elif isinstance(call.func, ast.Name):
            alias = (
                bindings.get(call.func.id)
                or source.constants.get(call.func.id)
                or _Value()
            )
            if any(
                value
                == f"@boundcallable:{callable_info.qualified_name}"
                for value in alias.instances
            ):
                receiver = _Value(
                    strings=alias.strings,
                    items=alias.items,
                    mapping=alias.mapping,
                    instances=tuple(
                        value
                        for value in alias.instances
                        if not value.startswith("@")
                    ),
                    dynamic=alias.dynamic,
                )
        if isinstance(call.func, ast.Attribute) or receiver.evidence:
            if not receiver.instances:
                receiver = _Value(
                    strings=receiver.strings,
                    items=receiver.items,
                    mapping=receiver.mapping,
                    instances=(callable_info.owner_class,),
                    dynamic=receiver.dynamic,
                )
            values.append(receiver)
    for argument in call.args:
        value = _resolve_value(
            argument, source, repository, bindings, depth + 1
        )
        if isinstance(argument, ast.Starred):
            if value.items:
                values.extend(value.items)
            else:
                unresolved.append(value)
        else:
            values.append(value)
    result: dict[str, _Value] = {}
    for name, value in zip(positional_names, values):
        result[name] = value
    if (
        callable_info.owner_class
        and callable_info.binding_kind != "static"
        and positional_names
    ):
        receiver_name = positional_names[0]
        for attribute, value in tuple(
            receiver_attributes.items()
        )[:32]:
            result[f"{receiver_name}.{attribute}"] = value
    if len(values) > len(positional_names):
        extras = values[len(positional_names) :]
        if args.vararg:
            result[args.vararg.arg] = _Value(
                strings=_unique_strings(
                    item
                    for value in extras
                    for item in value.strings
                ),
                items=tuple(extras),
                mapping=tuple(
                    item for value in extras for item in value.mapping
                ),
                instances=_unique_strings(
                    item
                    for value in extras
                    for item in value.instances
                ),
                dynamic=any(value.dynamic for value in extras),
            )
        else:
            unresolved.extend(extras)
    extra_keywords: list[tuple[str, _Value]] = []
    for keyword in call.keywords:
        value = _resolve_value(
            keyword.value, source, repository, bindings, depth + 1
        )
        if keyword.arg is None:
            if value.mapping:
                for key, item in value.mapping:
                    if key in positional_names or any(
                        argument.arg == key for argument in args.kwonlyargs
                    ):
                        result[key] = item
                    else:
                        extra_keywords.append((key, item))
            else:
                unresolved.append(value)
        else:
            if keyword.arg in positional_names or any(
                argument.arg == keyword.arg for argument in args.kwonlyargs
            ):
                result[keyword.arg] = value
            else:
                extra_keywords.append((keyword.arg, value))
    defaults = [*args.defaults]
    default_names = positional_names[-len(defaults) :] if defaults else []
    callable_source = repository.sources[callable_info.source_module]
    for name, default in zip(default_names, defaults):
        result.setdefault(
            name,
            _resolve_value(
                default,
                callable_source,
                repository,
                result,
                depth + 1,
            ),
        )
    for name, default in zip(
        (item.arg for item in args.kwonlyargs), args.kw_defaults
    ):
        if default is not None:
            result.setdefault(
                name,
                _resolve_value(
                    default,
                    callable_source,
                    repository,
                    result,
                    depth + 1,
                ),
            )
    if args.kwarg:
        result[args.kwarg.arg] = _Value(
            strings=_unique_strings(
                item
                for _, value in extra_keywords
                for item in value.strings
            ),
            mapping=tuple(extra_keywords),
            instances=_unique_strings(
                item
                for _, value in extra_keywords
                for item in value.instances
            ),
            dynamic=any(value.dynamic for _, value in extra_keywords),
        )
    else:
        unresolved.extend(value for _, value in extra_keywords)
    if callable_info.owner_class:
        result["__owner_class__"] = _Value(
            instances=(callable_info.owner_class,)
        )
    return result, unresolved


def _scan_callable(
    repository: _Repository,
    callable_info: _Callable,
    bindings: dict[str, _Value],
    boundary_values: Sequence[_Value],
) -> None:
    if id(callable_info.node) in repository.allowed_node_ids:
        return
    source = repository.sources[callable_info.source_module]
    if _has_discovery_target(callable_info.qualified_name):
        _add_issue(
            repository.issues,
            "partial_vendor_discovery_implementation",
            source.path,
            callable_info.node,
            callable_info.node.name,
        )
    effective_bindings = dict(bindings)
    args = callable_info.node.args
    positional_names = [item.arg for item in (*args.posonlyargs, *args.args)]
    default_names = (
        positional_names[-len(args.defaults) :] if args.defaults else []
    )
    for name, default in zip(default_names, args.defaults):
        effective_bindings.setdefault(
            name,
            _resolve_value(
                default, source, repository, effective_bindings
            ),
        )
    for argument, default in zip(args.kwonlyargs, args.kw_defaults):
        if default is not None:
            effective_bindings.setdefault(
                argument.arg,
                _resolve_value(
                    default, source, repository, effective_bindings
                ),
            )
    if callable_info.owner_class:
        owner = _Value(instances=(callable_info.owner_class,))
        effective_bindings.setdefault("__owner_class__", owner)
        if (
            callable_info.binding_kind != "static"
            and positional_names
        ):
            effective_bindings.setdefault(positional_names[0], owner)
    effective_boundary = tuple(boundary_values)
    boundary_evidence = tuple(
        value.evidence
        for value in effective_boundary
        if _has_boundary_evidence(value)
    )
    target_boundary = any(
        _has_boundary_evidence(value) for value in effective_boundary
    )
    if (
        callable_info.qualified_name in repository.active_calls
        or len(repository.active_calls) >= 4
    ):
        if target_boundary:
            _add_issue(
                repository.issues,
                "unresolved_vendor_discovery_capability",
                repository.sources[callable_info.source_module].path,
                callable_info.node,
                callable_info.qualified_name,
            )
        return
    repository.active_calls.append(callable_info.qualified_name)
    try:
        context = (
            f"{source.path.as_posix()} {callable_info.qualified_name} "
            + " ".join(boundary_evidence)
        )
        header_nodes: list[ast.AST] = [
            *callable_info.node.decorator_list,
            *args.defaults,
            *(item for item in args.kw_defaults if item is not None),
        ]
        if callable_info.node.returns is not None:
            header_nodes.append(callable_info.node.returns)
        _scan_nodes(
            repository,
            source,
            header_nodes,
            context,
            dict(effective_bindings),
        )
        _scan_nodes(
            repository,
            source,
            callable_info.node.body,
            context,
            effective_bindings,
        )
    finally:
        repository.active_calls.pop()


def _apply_container_mutation(
    node: ast.Call,
    source: _Source,
    repository: _Repository,
    bindings: dict[str, _Value],
) -> tuple[bool, bool]:
    if not isinstance(node.func, ast.Attribute):
        return False, False
    method = node.func.attr
    if method not in {
        "append",
        "add",
        "extend",
        "update",
        "setdefault",
        "__setitem__",
    }:
        return False, False
    receiver_path = _binding_path(node.func.value)
    if not receiver_path or receiver_path not in bindings:
        return False, False
    receiver = bindings[receiver_path]
    container_kinds = {
        value.removeprefix("@container:")
        for value in receiver.instances
        if value.startswith("@container:")
    }
    required_kinds = {
        "append": {"list"},
        "add": {"set"},
        "extend": {"list"},
        "update": {"dict"},
        "setdefault": {"dict"},
        "__setitem__": {"dict", "list"},
    }[method]
    if not (container_kinds & required_kinds) or any(
        not value.startswith("@container:")
        for value in receiver.instances
    ):
        return False, False
    arguments = tuple(
        _resolve_value(arg, source, repository, bindings)
        for arg in node.args
    )
    keyword_values = tuple(
        (
            keyword.arg,
            _resolve_value(
                keyword.value,
                source,
                repository,
                bindings,
            ),
        )
        for keyword in node.keywords
        if keyword.arg is not None
    )
    unresolved = any(keyword.arg is None for keyword in node.keywords)

    def store(
        *,
        items: Sequence[_Value] = receiver.items,
        mapping: Sequence[tuple[str, _Value]] = receiver.mapping,
        dynamic: bool = receiver.dynamic,
    ) -> None:
        item_values = tuple(items)
        boundary_items = tuple(
            item for item in item_values if _has_boundary_evidence(item)
        )
        kept_items = tuple(
            dict.fromkeys((*boundary_items, *item_values))
        )[:32]
        mapping_values = tuple(mapping)
        boundary_mapping = tuple(
            item
            for item in mapping_values
            if (
                _has_static_boundary_text(item[0])
                or _has_boundary_evidence(item[1])
            )
        )
        kept_mapping = tuple(
            dict.fromkeys((*boundary_mapping, *mapping_values))
        )[:32]
        merged = _merge_values(
            receiver,
            *arguments,
            *(value for _, value in keyword_values),
            *kept_items,
            *(value for _, value in kept_mapping),
        )
        bindings[receiver_path] = _Value(
            strings=merged.strings,
            items=kept_items,
            mapping=kept_mapping,
            instances=merged.instances,
            dynamic=(
                dynamic
                or unresolved
                or len(item_values) > len(kept_items)
                or len(mapping_values) > len(kept_mapping)
            ),
        )

    if method in {"append", "add"}:
        if len(arguments) != 1 or keyword_values:
            return True, any(
                _has_boundary_evidence(value) for value in arguments
            )
        store(
            items=(*receiver.items, arguments[0]),
            dynamic=receiver.dynamic or method == "add",
        )
        return True, False
    if method == "extend":
        if len(arguments) != 1 or keyword_values:
            return True, any(
                _has_boundary_evidence(value) for value in arguments
            )
        extension = arguments[0]
        if not extension.items:
            store(dynamic=True)
            return True, _has_boundary_evidence(extension)
        store(items=(*receiver.items, *extension.items))
        return True, False
    if method == "update":
        mapping = dict(receiver.mapping)
        if len(arguments) > 1:
            return True, any(
                _has_boundary_evidence(value) for value in arguments
            )
        if arguments:
            if not arguments[0].mapping:
                unresolved = unresolved or _has_boundary_evidence(arguments[0])
            else:
                mapping.update(arguments[0].mapping)
        mapping.update(keyword_values)
        store(mapping=tuple(mapping.items()), dynamic=unresolved)
        return True, unresolved

    if method == "setdefault":
        if not (1 <= len(arguments) <= 2) or keyword_values:
            return True, any(
                _has_boundary_evidence(value) for value in arguments
            )
        keys = arguments[0].strings
        if len(keys) != 1:
            store(dynamic=True)
            return True, any(
                _has_boundary_evidence(value) for value in arguments
            )
        mapping = dict(receiver.mapping)
        mapping.setdefault(
            keys[0],
            arguments[1] if len(arguments) == 2 else _Value(),
        )
        store(mapping=tuple(mapping.items()))
        return True, False

    if len(arguments) != 2 or keyword_values:
        return True, any(
            _has_boundary_evidence(value) for value in arguments
        )
    if (
        node.args
        and isinstance(node.args[0], ast.Constant)
        and type(node.args[0].value) is int
    ):
        index = node.args[0].value
        items = list(receiver.items)
        if items and -len(items) <= index < len(items):
            items[index] = arguments[1]
            store(items=tuple(items))
            return True, False
        store(dynamic=True)
        return True, _has_boundary_evidence(arguments[1])
    keys = arguments[0].strings
    if len(keys) == 1:
        mapping = dict(receiver.mapping)
        mapping[keys[0]] = arguments[1]
        store(mapping=tuple(mapping.items()))
        return True, False
    store(dynamic=True)
    return True, any(
        _has_boundary_evidence(value) for value in arguments
    )


def _scan_call_node(
    repository: _Repository,
    source: _Source,
    node: ast.Call,
    context: str,
    bindings: dict[str, _Value],
) -> None:
    callable_info = _resolve_callable(
        node.func, source, repository, bindings
    )
    argument_values = [
        _resolve_value(arg, source, repository, bindings)
        for arg in node.args
    ] + [
        _resolve_value(item.value, source, repository, bindings)
        for item in node.keywords
    ]
    values = list(argument_values)
    if isinstance(node.func, ast.Attribute):
        values.append(
            _resolve_value(
                node.func.value, source, repository, bindings
            )
        )
    constructor_classes = _resolve_class_reference(
        node.func, source, repository, bindings
    )
    if constructor_classes:
        for class_name in constructor_classes:
            initializer = _resolve_method(
                class_name, "__init__", repository
            )
            if initializer:
                call_bindings, unresolved = _bind_call(
                    initializer,
                    node,
                    source,
                    repository,
                    bindings,
                )
                bound_values = (
                    *values,
                    *call_bindings.values(),
                    *unresolved,
                )
                if any(
                    _has_boundary_evidence(value)
                    for value in bound_values
                ):
                    _scan_callable(
                        repository,
                        initializer,
                        call_bindings,
                        bound_values,
                    )
    boundary_relevant = any(
        _has_boundary_evidence(value) for value in values
    )
    mutation_handled, mutation_unresolved = _apply_container_mutation(
        node,
        source,
        repository,
        bindings,
    )
    if mutation_unresolved and boundary_relevant:
        _add_issue(
            repository.issues,
            "unresolved_vendor_discovery_capability",
            source.path,
            node,
            _dotted_name(node.func) or "container_mutation",
        )
    leaf_name = _call_leaf(
        node.func, source, repository, bindings
    )
    if boundary_relevant and leaf_name == "query":
        _add_issue(
            repository.issues,
            "dynamic_vendor_discovery_sql",
            source.path,
            node,
            leaf_name,
        )
    safe_builtin_call = (
        isinstance(node.func, ast.Name)
        and leaf_name
        in {
            "print",
            "len",
            "sorted",
            "tuple",
            "list",
            "set",
            "dict",
            "range",
            "enumerate",
            "isinstance",
            "zip",
            "map",
            "filter",
            "any",
            "all",
            "min",
            "max",
            "sum",
        }
    )
    if callable_info:
        call_bindings, unresolved = _bind_call(
            callable_info,
            node,
            source,
            repository,
            bindings,
        )
        bound_values = (
            *values,
            *call_bindings.values(),
            *unresolved,
        )
        if boundary_relevant or any(
            _has_boundary_evidence(value) for value in bound_values
        ):
            _scan_callable(
                repository,
                callable_info,
                call_bindings,
                bound_values,
            )
    elif (
        boundary_relevant
        and not mutation_handled
        and leaf_name not in _SQL_SINKS | _WRITE_CALLS
        and not safe_builtin_call
    ):
        _add_issue(
            repository.issues,
            "unresolved_vendor_discovery_capability",
            source.path,
            node,
            _dotted_name(node.func) or "call",
        )


def _callable_for_node(
    repository: _Repository,
    source: _Source,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> _Callable | None:
    matches = [
        item
        for item in repository.callables.values()
        if item.source_module == source.module_name and item.node is node
    ]
    return matches[0] if len(matches) == 1 else None


def _iterated_value(value: _Value) -> _Value:
    if value.items:
        return _merge_values(*value.items)
    if value.mapping:
        return _merge_values(*(item for _, item in value.mapping))
    return value


def _bind_match_pattern(
    pattern: ast.pattern,
    subject: _Value,
    bindings: dict[str, _Value],
) -> None:
    if isinstance(pattern, ast.MatchAs):
        if pattern.name:
            bindings[pattern.name] = subject
        if pattern.pattern:
            _bind_match_pattern(pattern.pattern, subject, bindings)
    elif isinstance(pattern, ast.MatchStar):
        if pattern.name:
            bindings[pattern.name] = subject
    elif isinstance(pattern, ast.MatchMapping):
        key_values = [
            key.value
            for key in pattern.keys
            if isinstance(key, ast.Constant) and type(key.value) is str
        ]
        mapping = dict(subject.mapping)
        for key, child in zip(key_values, pattern.patterns):
            _bind_match_pattern(
                child, mapping.get(key, subject), bindings
            )
        if pattern.rest:
            bindings[pattern.rest] = subject
    elif isinstance(pattern, (ast.MatchSequence, ast.MatchOr)):
        children = (
            pattern.patterns
            if isinstance(pattern, (ast.MatchSequence, ast.MatchOr))
            else ()
        )
        for index, child in enumerate(children):
            item = (
                subject.items[index]
                if index < len(subject.items)
                else subject
            )
            _bind_match_pattern(child, item, bindings)
    elif isinstance(pattern, ast.MatchClass):
        for child in (*pattern.patterns, *pattern.kwd_patterns):
            _bind_match_pattern(child, subject, bindings)


def _direct_call_nodes(node: ast.AST) -> tuple[ast.Call, ...]:
    calls: list[ast.Call] = []

    class Collector(ast.NodeVisitor):
        def visit_Call(self, child: ast.Call) -> None:
            calls.append(child)
            self.generic_visit(child)

        def visit_FunctionDef(self, child: ast.FunctionDef) -> None:
            return

        def visit_AsyncFunctionDef(
            self, child: ast.AsyncFunctionDef
        ) -> None:
            return

        def visit_ClassDef(self, child: ast.ClassDef) -> None:
            return

        def visit_If(self, child: ast.If) -> None:
            self.visit(child.test)

        def visit_For(self, child: ast.For) -> None:
            self.visit(child.target)
            self.visit(child.iter)

        def visit_AsyncFor(self, child: ast.AsyncFor) -> None:
            self.visit(child.target)
            self.visit(child.iter)

        def visit_While(self, child: ast.While) -> None:
            self.visit(child.test)

        def visit_With(self, child: ast.With) -> None:
            for item in child.items:
                self.visit(item.context_expr)

        def visit_AsyncWith(self, child: ast.AsyncWith) -> None:
            for item in child.items:
                self.visit(item.context_expr)

        def visit_Try(self, child: ast.Try) -> None:
            return

        def visit_Match(self, child: ast.Match) -> None:
            self.visit(child.subject)

    Collector().visit(node)
    return tuple(calls)


def _scan_nodes(
    repository: _Repository,
    source: _Source,
    nodes: Iterable[ast.AST],
    context: str,
    bindings: dict[str, _Value],
) -> None:
    for node in nodes:
        if id(node) in repository.allowed_node_ids:
            continue
        _classify_node(repository, source, node, context, bindings)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            callable_info = _callable_for_node(
                repository, source, node
            )
            if callable_info:
                _scan_callable(
                    repository,
                    callable_info,
                    dict(bindings),
                    (),
                )
            continue
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                _classify_node(
                    repository, source, child, context, bindings
                )
                if isinstance(
                    child, (ast.FunctionDef, ast.AsyncFunctionDef)
                ):
                    callable_info = _callable_for_node(
                        repository, source, child
                    )
                    if callable_info:
                        _scan_callable(
                            repository,
                            callable_info,
                            dict(bindings),
                            (),
                        )
                else:
                    _scan_nodes(
                        repository,
                        source,
                        (child,),
                        context,
                        dict(bindings),
                    )
            continue
        if isinstance(
            node,
            (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr),
        ):
            value = _resolve_value(
                node if isinstance(node, ast.AugAssign) else node.value,
                source,
                repository,
                bindings,
            )
            for target in _assignment_targets(node):
                _assign_binding(bindings, target, value)
        if isinstance(node, ast.ImportFrom):
            module_name = _relative_import_module(
                source,
                node.module or "",
                node.level,
            )
            imported_source = repository.sources.get(module_name)
            if imported_source is not None:
                for alias in node.names:
                    if alias.name == "*":
                        for name, value in imported_source.constants.items():
                            if not name.startswith("_"):
                                bindings[name] = value
                        continue
                    value = imported_source.constants.get(alias.name)
                    if value is not None:
                        bindings[alias.asname or alias.name] = value
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_source = repository.sources.get(alias.name)
                if imported_source is None:
                    continue
                local = alias.asname or alias.name.split(".", 1)[0]
                for name, value in imported_source.constants.items():
                    bindings[f"{local}.{name}"] = value
        if isinstance(node, (ast.For, ast.AsyncFor)):
            iterable = _resolve_value(
                node.iter, source, repository, bindings
            )
            _assign_binding(
                bindings, node.target, _iterated_value(iterable)
            )
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    _assign_binding(
                        bindings,
                        item.optional_vars,
                        _resolve_value(
                            item.context_expr,
                            source,
                            repository,
                            bindings,
                        ),
                    )
        comprehensions: list[ast.AST] = []
        if isinstance(
            node,
            (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp),
        ):
            comprehensions.append(node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            if isinstance(node.value, ast.AST):
                comprehensions.extend(
                    child
                    for child in ast.walk(node.value)
                    if isinstance(
                        child,
                        (
                            ast.ListComp,
                            ast.SetComp,
                            ast.GeneratorExp,
                            ast.DictComp,
                        ),
                    )
                )
        for comprehension in comprehensions:
            comprehension_bindings = dict(bindings)
            for generator in comprehension.generators:
                iterable = _resolve_value(
                    generator.iter,
                    source,
                    repository,
                    comprehension_bindings,
                )
                _assign_binding(
                    comprehension_bindings,
                    generator.target,
                    _iterated_value(iterable),
                )
                _scan_nodes(
                    repository,
                    source,
                    generator.ifs,
                    context,
                    comprehension_bindings,
                )
            payload = (
                (comprehension.key, comprehension.value)
                if isinstance(comprehension, ast.DictComp)
                else (comprehension.elt,)
            )
            _scan_nodes(
                repository,
                source,
                payload,
                context,
                comprehension_bindings,
            )
        call_nodes = _direct_call_nodes(node)
        for call_node in call_nodes:
            if call_node is not node:
                _classify_node(
                    repository,
                    source,
                    call_node,
                    context,
                    bindings,
                )
            _scan_call_node(
                repository,
                source,
                call_node,
                context,
                bindings,
            )
        child_groups: list[list[ast.AST]] = []
        if isinstance(node, ast.If):
            child_groups.extend((node.body, node.orelse))
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            child_groups.extend((node.body, node.orelse))
        elif isinstance(node, ast.Try):
            child_groups.extend((node.body, node.orelse, node.finalbody))
            child_groups.extend(handler.body for handler in node.handlers)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            child_groups.append(node.body)
        branch_bindings: list[dict[str, _Value]] = []
        if isinstance(node, ast.Match):
            subject = _resolve_value(
                node.subject, source, repository, bindings
            )
            for case in node.cases:
                case_bindings = dict(bindings)
                case_subject = subject
                if (
                    isinstance(node.subject, ast.Name)
                    and isinstance(case.pattern, ast.MatchValue)
                ):
                    pattern_value = _resolve_value(
                        case.pattern.value,
                        source,
                        repository,
                        case_bindings,
                    )
                    if _has_boundary_evidence(pattern_value):
                        case_bindings[node.subject.id] = pattern_value
                        case_subject = pattern_value
                _bind_match_pattern(
                    case.pattern, case_subject, case_bindings
                )
                if case.guard is not None:
                    _scan_nodes(
                        repository,
                        source,
                        (case.guard,),
                        context,
                        case_bindings,
                    )
                _scan_nodes(
                    repository,
                    source,
                    case.body,
                    context,
                    case_bindings,
                )
                branch_bindings.append(case_bindings)
            _merge_binding_maps(bindings, *branch_bindings)
            continue
        for group_index, group in enumerate(child_groups):
            group_bindings = dict(bindings)
            if (
                group_index == 0
                and isinstance(node, ast.If)
                and isinstance(node.test, ast.Compare)
                and len(node.test.ops) == 1
                and isinstance(node.test.ops[0], ast.Eq)
                and len(node.test.comparators) == 1
            ):
                left = node.test.left
                right = node.test.comparators[0]
                name_node = (
                    left
                    if isinstance(left, ast.Name)
                    else right if isinstance(right, ast.Name) else None
                )
                value_node = (
                    right
                    if name_node is left
                    else left if name_node is right else None
                )
                if name_node is not None and value_node is not None:
                    compared = _resolve_value(
                        value_node,
                        source,
                        repository,
                        group_bindings,
                    )
                    if _has_boundary_evidence(compared):
                        group_bindings[name_node.id] = compared
            _scan_nodes(
                repository,
                source,
                group,
                context,
                group_bindings,
            )
            branch_bindings.append(group_bindings)
        if branch_bindings:
            _merge_binding_maps(bindings, *branch_bindings)


def _self_audit(root: Path, repository: _Repository) -> set[int]:
    source = repository.sources.get(_module_name(_CHECKER_PATH))
    if source is None:
        _add_issue(
            repository.issues,
            "source_read_error",
            _CHECKER_PATH,
            symbol="checker_missing",
        )
        return set()
    forbidden_imports: set[str] = set()
    for node in source.tree.body:
        if isinstance(node, ast.Import):
            forbidden_imports.update(
                alias.name.split(".", 1)[0]
                for alias in node.names
                if alias.name.split(".", 1)[0]
                in _BACKEND_ROOTS | _PROJECT_IMPORT_ROOTS | {"subprocess"}
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            root_name = node.module.split(".", 1)[0]
            if root_name in (
                _BACKEND_ROOTS | _PROJECT_IMPORT_ROOTS | {"subprocess"}
            ):
                forbidden_imports.add(root_name)
    if forbidden_imports:
        _add_issue(
            repository.issues,
            "forbidden_vendor_discovery_backend_access",
            _CHECKER_PATH,
            symbol=",".join(sorted(forbidden_imports)),
        )
    top_names = {
        _top_level_name(node)
        for node in source.tree.body
        if _top_level_name(node)
    }
    for required in ("_analyze_repository", "_run_self_test", "_main"):
        if required not in top_names:
            _add_issue(
                repository.issues,
                "source_parse_error",
                _CHECKER_PATH,
                symbol=f"missing={required}",
            )
    if "__all__" in top_names:
        _add_issue(
            repository.issues,
            "partial_vendor_discovery_implementation",
            _CHECKER_PATH,
            symbol="public_api",
        )
    observed_names = tuple(
        _top_level_name(node)
        for node in source.tree.body
        if _top_level_name(node)
    )
    if observed_names != _SELF_AUDIT_NODE_NAMES:
        _add_issue(
            repository.issues,
            "checker_exemption_broadening",
            _CHECKER_PATH,
            symbol="self_node_inventory",
        )
        return set()
    hash_nodes = tuple(
        node
        for node in source.tree.body
        if _top_level_name(node) != "_SELF_AUDIT_AST_SHA256"
    )
    if _ast_bundle_sha256(hash_nodes) != _SELF_AUDIT_AST_SHA256:
        _add_issue(
            repository.issues,
            "checker_exemption_broadening",
            _CHECKER_PATH,
            symbol="self_ast_fingerprint",
        )
        return set()
    return {id(node) for node in source.tree.body}


def _apply_source_boundary_fallback(
    repository: _Repository,
    source_allowances: dict[str, set[int]],
) -> None:
    direct_boundary: set[str] = set()
    sql_sinks: dict[str, tuple[ast.Call, ...]] = {}
    for module, source in repository.sources.items():
        allowed = source_allowances[module]
        unallowed_nodes = tuple(
            node for node in source.tree.body if id(node) not in allowed
        )
        evidence = " ".join(_node_text(node) for node in unallowed_nodes)
        if (
            source.path != _UPSTREAM_CHECKER_PATH
            and _has_static_boundary_text(evidence)
        ):
            direct_boundary.add(module)
        sinks = tuple(
            child
            for node in unallowed_nodes
            for child in ast.walk(node)
            if isinstance(child, ast.Call)
            and _dotted_name(child.func).rsplit(".", 1)[-1]
            in _SQL_SINKS
        )
        sql_sinks[module] = sinks
    for module in sorted(direct_boundary):
        sinks = sql_sinks.get(module, ())
        if not sinks:
            continue
        source = repository.sources[module]
        _add_issue(
            repository.issues,
            "unresolved_vendor_discovery_capability",
            source.path,
            sinks[0],
            "source_boundary_flow",
        )


def _scan_repository(
    repository: _Repository,
    root: Path,
    upstream_valid: bool,
) -> None:
    self_allowed = _self_audit(root, repository)
    source_allowances: dict[str, set[int]] = {}
    for source in repository.sources.values():
        allowed_nodes: set[int] = set()
        if source.path == _CHECKER_PATH:
            allowed_nodes.update(self_allowed)
        if source.path == _UPSTREAM_CHECKER_PATH and upstream_valid:
            selected, valid = _selected_named_nodes(
                source.tree, _UPSTREAM_ALLOWED_NODE_NAMES
            )
            if valid:
                allowed_nodes.update(id(node) for node in selected)
                integration_ids, integration_valid = (
                    _upstream_integration_node_ids(source.tree)
                )
                if integration_valid:
                    allowed_nodes.update(integration_ids)
        elif source.path == _UPSTREAM_CHECKER_PATH:
            selected, valid = _selected_named_nodes(
                source.tree, _UPSTREAM_ALLOWED_NODE_NAMES
            )
            if valid:
                for name, node in zip(
                    _UPSTREAM_ALLOWED_NODE_NAMES,
                    selected,
                    strict=True,
                ):
                    expected = _UPSTREAM_STATIC_NODE_HASHES.get(name)
                    if expected and _ast_sha256(node) == expected:
                        allowed_nodes.add(id(node))
        for node in source.tree.body:
            expected_hash = _EXACT_FIXTURE_NODE_HASHES.get(
                (source.path.as_posix(), _top_level_name(node))
            )
            if expected_hash and _ast_sha256(node) == expected_hash:
                allowed_nodes.add(id(node))
        allowed_nodes.update(_v002_protected_node_ids(repository, source))
        source_allowances[source.module_name] = allowed_nodes
        repository.allowed_node_ids.update(allowed_nodes)
    for source in repository.sources.values():
        allowed_nodes = source_allowances[source.module_name]
        module_context = source.path.as_posix()
        module_bindings: dict[str, _Value] = {}
        for node in source.tree.body:
            if id(node) in allowed_nodes:
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if _has_discovery_target(
                    f"{module_context} {node.name}"
                ):
                    _add_issue(
                        repository.issues,
                        "partial_vendor_discovery_implementation",
                        source.path,
                        node,
                        node.name,
                    )
                callable_info = repository.callables.get(
                    f"{source.module_name}.{node.name}"
                )
                if callable_info:
                    _scan_callable(
                        repository,
                        callable_info,
                        dict(module_bindings),
                        (),
                    )
            elif isinstance(node, ast.ClassDef):
                if _has_discovery_target(
                    f"{module_context} {node.name}"
                ):
                    _add_issue(
                        repository.issues,
                        "partial_vendor_discovery_implementation",
                        source.path,
                        node,
                        node.name,
                    )
                for child in node.body:
                    if isinstance(
                        child, (ast.FunctionDef, ast.AsyncFunctionDef)
                    ):
                        callable_info = repository.callables.get(
                            f"{source.module_name}.{node.name}.{child.name}"
                        )
                        if callable_info:
                            _scan_callable(
                                repository,
                                callable_info,
                                dict(module_bindings),
                                (),
                            )
            else:
                _scan_nodes(
                    repository,
                    source,
                    (node,),
                    module_context,
                    module_bindings,
                )
    _apply_source_boundary_fallback(repository, source_allowances)


def _dedupe_issues(issues: Iterable[_Issue]) -> tuple[_Issue, ...]:
    return tuple(sorted(set(issues)))


def _analyze_repository(root: Path, /) -> tuple[_Issue, ...]:
    issues = _check_policy(root)
    upstream_issues = _check_upstream_guard(root)
    issues.extend(upstream_issues)
    repository = _prepare_repository(root, issues)
    for source in repository.sources.values():
        if (
            (
                source.path.name == _DISCOVERY_PATH.name
                or _module_name(source.path) == _module_name(_DISCOVERY_PATH)
            )
            and source.path != _DISCOVERY_PATH
        ):
            _add_issue(
                repository.issues,
                "forbidden_vendor_discovery_module_path",
                source.path,
                symbol="wrong_path",
            )
    _scan_repository(repository, root, not upstream_issues)
    if (root / _DISCOVERY_PATH).exists():
        _add_issue(
            repository.issues,
            "forbidden_vendor_discovery_module_path",
            _DISCOVERY_PATH,
            symbol="present",
        )
    return _dedupe_issues(repository.issues)


def _render_normal(issues: Sequence[_Issue]) -> tuple[int, str]:
    lines = (
        _NORMAL_SCOPE,
        f"issues_count: {len(issues)}",
        (
            "upstream_vendor_schema_guard_boundary: "
            + (
                "FAIL"
                if any(
                    issue.code == "upstream_vendor_schema_guard_drift"
                    for issue in issues
                )
                else "PASS"
            )
        ),
        "database_access: 0",
        "app_imports: 0",
    )
    output = list(lines)
    if issues:
        output.append("FAIL vendor organization discovery readiness:")
        output.extend(
            (
                f"{issue.code}: {issue.path}:{issue.line}:"
                f"{issue.symbol}"
            )
            for issue in issues
        )
        return 1, "\n".join(output) + "\n"
    output.append(_PASS_MARKER)
    return 0, "\n".join(output) + "\n"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Statically verify the frozen VENDOR-ID-003 absence-first "
            "read-only vendor discovery boundary."
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run isolated static source and policy scenarios",
    )
    tokens = list(sys.argv[1:] if argv is None else argv)
    if tokens.count("--self-test") > 1:
        parser.error("--self-test may be specified exactly once")
    return parser.parse_args(tokens)


def _write_text(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _copy_baseline(root: Path) -> None:
    for relative in (
        _POLICY_PATH,
        _UPSTREAM_CHECKER_PATH,
        _CHECKER_PATH,
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_ROOT_DIR / relative, target)


def _assert_negative(
    root: Path,
    expected_code: str,
    name: str,
) -> None:
    issues = _analyze_repository(root)
    if expected_code not in {issue.code for issue in issues}:
        rendered = _render_normal(issues)[1]
        raise AssertionError(
            f"negative scenario {name} missing {expected_code}:\n{rendered}"
        )
    status, rendered = _render_normal(issues)
    if status == 0 or _PASS_MARKER in rendered:
        raise AssertionError(
            f"negative scenario {name} emitted normal PASS"
        )
    for marker in ("database_access: 0", "app_imports: 0"):
        if rendered.count(marker) != 1:
            raise AssertionError(
                f"negative scenario {name} missing {marker}"
            )


def _run_self_test() -> int:
    scenario_count = 0
    with tempfile.TemporaryDirectory(
        prefix="vendor-id-003a-readiness-self-test-"
    ) as temp_value:
        temp_root = Path(temp_value)
        baseline = temp_root / "baseline"
        _copy_baseline(baseline)
        baseline_issues = _analyze_repository(baseline)
        if baseline_issues:
            raise AssertionError(
                "clean absence-first baseline failed:\n"
                + _render_normal(baseline_issues)[1]
            )
        scenario_count += 1

        positive_sources = (
            (
                "services/vendor_business.py",
                (
                    "def read_work(conn):\n"
                    "    return conn.execute("
                    "'SELECT sheet_id, vendor_name "
                    "FROM vendor_work_entries')\n"
                ),
            ),
            (
                "tools/schema_inventory.py",
                (
                    "TABLES = ('vendor_organizations', "
                    "'vendor_site_assignments')\n"
                    "UNSUPPORTED = 'vendor discovery is not supported here'\n"
                ),
            ),
            (
                "services/json_hash.py",
                (
                    "import hashlib\nimport json\n"
                    "def digest(value):\n"
                    "    return hashlib.sha256("
                    "json.dumps(value, sort_keys=True).encode()).hexdigest()\n"
                ),
            ),
            (
                "app.py",
                (
                    "VENDOR_SCHEMA_TABLES = ("
                    "'vendor_organizations', "
                    "'vendor_organization_memberships', "
                    "'vendor_site_assignments', "
                    "'sheet_vendor_bindings')\n"
                    "def ensure_vendor_organization_schema(conn):\n"
                    "    return tuple(VENDOR_SCHEMA_TABLES)\n"
                ),
            ),
            (
                "tools/capture_schema_manifest.py",
                (
                    "VENDOR_SCHEMA_PROJECTION = {"
                    "'vendor_organizations': ('vendor_id',), "
                    "'vendor_site_assignments': ('site_id',)}\n"
                ),
            ),
            (
                "services/multiple_inheritance_positive.py",
                (
                    "class SafeBase:\n"
                    "    TABLE = 'audit_events'\n"
                    "class TargetBase:\n"
                    "    TABLE = 'vendor_organizations'\n"
                    "class Reader(SafeBase, TargetBase):\n"
                    "    def read(self, conn):\n"
                    "        conn.execute('SELECT * FROM ' + self.TABLE)\n"
                    "Reader().read(None)\n"
                ),
            ),
        )
        for name, (relative, source) in enumerate(
            positive_sources, start=1
        ):
            root = temp_root / f"positive-{name}"
            shutil.copytree(baseline, root)
            _write_text(root, relative, source)
            issues = _analyze_repository(root)
            if issues:
                raise AssertionError(
                    f"positive scenario {name} failed:\n"
                    + _render_normal(issues)[1]
                )
            scenario_count += 1

        docs_control = temp_root / "positive-docs-tests"
        shutil.copytree(baseline, docs_control)
        _write_text(
            docs_control,
            "docs/prohibited_examples.py",
            (
                "discover_vendor_organization_readiness = "
                "'documentation only'\n"
            ),
        )
        _write_text(
            docs_control,
            "tests/vendor_discovery_fixture.py",
            "SQL = 'SELECT * FROM vendor_organizations'\n",
        )
        if _analyze_repository(docs_control):
            raise AssertionError("docs/tests positive control failed")
        scenario_count += 1

        scenarios: list[tuple[str, str, str, str]] = [
            (
                "canonical_module",
                _DISCOVERY_PATH.as_posix(),
                "def placeholder():\n    return None\n",
                "forbidden_vendor_discovery_module_path",
            ),
            (
                "wrong_path_symbol",
                "tools/vendor_probe.py",
                "def discover_vendor_organization_readiness():\n    pass\n",
                "partial_vendor_discovery_implementation",
            ),
            (
                "exception_symbol",
                "tools/vendor_probe.py",
                "class VendorOrganizationDiscoveryError(Exception):\n    pass\n",
                "partial_vendor_discovery_implementation",
            ),
            (
                "third_export",
                "tools/vendor_probe.py",
                (
                    "__all__ = ("
                    "'VendorOrganizationDiscoveryError', "
                    "'discover_vendor_organization_readiness', "
                    "'connection_factory')\n"
                ),
                "partial_vendor_discovery_implementation",
            ),
            (
                "cli_surface",
                "tools/vendor_discovery_cli.py",
                (
                    "OPTIONS = ('--db-path', '--run-id', "
                    "'--captured-at', '--tool-commit', '--output')\n"
                ),
                "partial_vendor_discovery_implementation",
            ),
            (
                "fixed_query",
                "tools/vendor_probe.py",
                (
                    "SQL = 'SELECT id, vendor_name "
                    "FROM main.vendor_accounts ORDER BY id;'\n"
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "dynamic_query",
                "tools/vendor_discovery_probe.py",
                (
                    "def run(conn, table):\n"
                    "    return conn.execute('SELECT * FROM ' + table)\n"
                    "run(None, 'vendor_accounts')\n"
                ),
                "dynamic_vendor_discovery_sql",
            ),
            (
                "sensitive_read",
                "tools/vendor_discovery_probe.py",
                (
                    "SQL = 'SELECT username, password_hash "
                    "FROM vendor_accounts'\n"
                ),
                "forbidden_vendor_discovery_sensitive_read",
            ),
            (
                "raw_disclosure",
                "tools/vendor_discovery_probe.py",
                "def emit_raw_label(raw_label):\n    print(raw_label)\n",
                "forbidden_vendor_discovery_raw_disclosure",
            ),
            (
                "environment",
                "tools/vendor_discovery_probe.py",
                (
                    "import os\n"
                    "def load_vendor_discovery():\n"
                    "    return os.environ['APP_DB_PATH']\n"
                ),
                "forbidden_vendor_discovery_environment_access",
            ),
            (
                "path_access",
                "tools/vendor_discovery_probe.py",
                "VENDOR_DISCOVERY_DATABASE = 'site.db'\n",
                "forbidden_vendor_discovery_path_access",
            ),
            (
                "immutable_uri",
                "tools/vendor_discovery_probe.py",
                "VENDOR_DISCOVERY_URI = 'file:source.db?immutable=1'\n",
                "forbidden_vendor_discovery_path_access",
            ),
            (
                "app_import",
                "tools/vendor_discovery_probe.py",
                "import app\nVENDOR_DISCOVERY = True\n",
                "forbidden_vendor_discovery_app_import",
            ),
            (
                "backend",
                "tools/vendor_discovery_probe.py",
                "import sqlite3\nVENDOR_DISCOVERY = True\n",
                "forbidden_vendor_discovery_backend_access",
            ),
            (
                "artifact",
                "tools/vendor_discovery_probe.py",
                (
                    "def write_vendor_discovery_report(output_path):\n"
                    "    output_path.write_text('report')\n"
                ),
                "forbidden_vendor_discovery_artifact",
            ),
            (
                "transaction",
                "tools/vendor_discovery_probe.py",
                "VENDOR_DISCOVERY_TRANSACTION = 'COMMIT'\n",
                "forbidden_vendor_discovery_transaction",
            ),
            (
                "authorizer",
                "tools/vendor_discovery_probe.py",
                (
                    "def vendor_discovery_authorizer_allow_all(action):\n"
                    "    return True\n"
                ),
                "forbidden_vendor_discovery_authorizer",
            ),
            (
                "error_contract",
                "tools/vendor_discovery_probe.py",
                (
                    "def vendor_discovery_exception_detail(exc):\n"
                    "    return str(exc)\n"
                ),
                "forbidden_vendor_discovery_error_contract",
            ),
            (
                "output_contract",
                "tools/vendor_discovery_probe.py",
                "VENDOR_DISCOVERY_OUTPUT = 'unknown_observed'\n",
                "forbidden_vendor_discovery_output_contract",
            ),
            (
                "selection",
                "tools/vendor_discovery_probe.py",
                "def select_vendor_discovery_winner(candidates):\n    return candidates[0]\n",
                "forbidden_vendor_discovery_selection",
            ),
            (
                "mapping",
                "tools/vendor_discovery_probe.py",
                "def build_vendor_discovery_mapping():\n    return {}\n",
                "forbidden_vendor_discovery_mapping",
            ),
            (
                "backfill",
                "tools/vendor_discovery_probe.py",
                "def vendor_discovery_backfill_mapping():\n    return []\n",
                "forbidden_vendor_discovery_mapping",
            ),
            (
                "mutation",
                "tools/vendor_discovery_probe.py",
                "def update_vendor_discovery_organization():\n    return None\n",
                "forbidden_vendor_discovery_mutation",
            ),
            (
                "consumer",
                "services/vendor_discovery_api.py",
                "def vendor_discovery_api_route():\n    return None\n",
                "forbidden_vendor_discovery_consumer",
            ),
            (
                "production",
                "tools/vendor_discovery_probe.py",
                "def vendor_discovery_production_operator():\n    return None\n",
                "forbidden_vendor_discovery_production_access",
            ),
            (
                "exemption",
                "tools/vendor_discovery_probe.py",
                "VENDOR_DISCOVERY_WHOLE_FILE_EXEMPTION = True\n",
                "checker_exemption_broadening",
            ),
            (
                "raw_identifier_log",
                "tools/vendor_discovery_probe.py",
                (
                    "def vendor_discovery_log(vendor_id):\n"
                    "    print(vendor_id)\n"
                ),
                "forbidden_vendor_discovery_raw_disclosure",
            ),
            (
                "parse_error",
                "services/broken.py",
                "def broken(:\n    pass\n",
                "source_parse_error",
            ),
        ]
        for name, relative, source, expected in scenarios:
            root = temp_root / f"negative-{name}"
            shutil.copytree(baseline, root)
            _write_text(root, relative, source)
            _assert_negative(root, expected, name)
            scenario_count += 1

        for index, query in enumerate(_CANONICAL_QUERIES, start=1):
            root = temp_root / f"negative-fixed-query-{index:02d}"
            shutil.copytree(baseline, root)
            _write_text(
                root,
                f"services/fixed_query_{index:02d}.py",
                f"QUERY = {query!r}\n",
            )
            _assert_negative(
                root,
                "forbidden_vendor_discovery_query",
                f"fixed_query_{index:02d}",
            )
            scenario_count += 1

        flow_scenarios: tuple[
            tuple[str, tuple[tuple[str, str], ...], str], ...
        ] = (
            (
                "neutral_cli_bundle",
                (
                    (
                        "services/options.py",
                        (
                            "OPTIONS = ('--db-path', '--run-id', "
                            "'--captured-at', '--tool-commit')\n"
                        ),
                    ),
                ),
                "partial_vendor_discovery_implementation",
            ),
            (
                "empty_wrong_path_module",
                (
                    (
                        "services/discover_vendor_organization_readiness.py",
                        "",
                    ),
                ),
                "forbidden_vendor_discovery_module_path",
            ),
            (
                "imported_target_alias",
                (
                    (
                        "package/api.py",
                        (
                            "def discover_vendor_organization_readiness():\n"
                            "    return None\n"
                        ),
                    ),
                    (
                        "services/use.py",
                        (
                            "from package.api import "
                            "discover_vendor_organization_readiness as probe\n"
                        ),
                    ),
                ),
                "partial_vendor_discovery_implementation",
            ),
            (
                "relative_imported_target_constant",
                (
                    ("package/constants.py", "TABLE = 'vendor_organizations'\n"),
                    (
                        "package/reader.py",
                        (
                            "from .constants import TABLE\n"
                            "def read(conn):\n"
                            "    conn.execute('SELECT * FROM ' + TABLE)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "relative_module_qualified_target_constant",
                (
                    ("package/constants.py", "TABLE = 'vendor_organizations'\n"),
                    (
                        "package/reader.py",
                        (
                            "from . import constants\n"
                            "def read(conn):\n"
                            "    conn.execute("
                            "'SELECT * FROM ' + constants.TABLE)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "star_imported_target_constant",
                (
                    ("package/constants.py", "TABLE = 'vendor_organizations'\n"),
                    (
                        "package/reader.py",
                        (
                            "from package.constants import *\n"
                            "def read(conn):\n"
                            "    conn.execute('SELECT * FROM ' + TABLE)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "nested_target_callable",
                (
                    (
                        "services/nested.py",
                        (
                            "def outer():\n"
                            "    def discover_vendor_organization_readiness():\n"
                            "        return None\n"
                        ),
                    ),
                ),
                "partial_vendor_discovery_implementation",
            ),
            (
                "class_target_method",
                (
                    (
                        "services/nested.py",
                        (
                            "class Reader:\n"
                            "    def discover_vendor_organization_readiness(self):\n"
                            "        return None\n"
                        ),
                    ),
                ),
                "partial_vendor_discovery_implementation",
            ),
            (
                "default_query_argument",
                (
                    (
                        "services/defaults.py",
                        (
                            f"def run(conn, sql={_CANONICAL_QUERIES[0]!r}):\n"
                            "    conn.execute(sql)\n"
                            "run(None)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "default_table_argument",
                (
                    (
                        "services/defaults.py",
                        (
                            "def run(conn, table='vendor_organizations'):\n"
                            "    conn.execute('SELECT * FROM ' + table)\n"
                            "run(None)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "helper_return_query",
                (
                    (
                        "services/returns.py",
                        (
                            f"def sql():\n    return {_CANONICAL_QUERIES[0]!r}\n"
                            "def run(conn):\n"
                            "    conn.execute(sql())\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "helper_return_table",
                (
                    (
                        "services/returns.py",
                        (
                            "def table():\n"
                            "    return 'vendor_organizations'\n"
                            "def run(conn):\n"
                            "    conn.execute('SELECT * FROM ' + table())\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "bound_instance_attribute",
                (
                    (
                        "services/bound.py",
                        (
                            "class Reader:\n"
                            "    def __init__(self, table):\n"
                            "        self.table = table\n"
                            "    def run(self, conn):\n"
                            "        conn.execute('SELECT * FROM ' + self.table)\n"
                            "reader = Reader('vendor_organizations')\n"
                            "reader.run(None)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "loop_query",
                (
                    (
                        "services/loop.py",
                        (
                            f"QUERIES = ({_CANONICAL_QUERIES[0]!r},)\n"
                            "for query in QUERIES:\n"
                            "    conn.execute(query)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "match_mapping_query",
                (
                    (
                        "services/match_query.py",
                        (
                            "def run(conn, payload):\n"
                            "    match payload:\n"
                            "        case {'sql': sql}:\n"
                            "            conn.execute(sql)\n"
                            f"run(None, {{'sql': {_CANONICAL_QUERIES[0]!r}}})\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "keyword_unpack_query",
                (
                    (
                        "services/kwargs.py",
                        (
                            "def run(conn, sql):\n"
                            "    conn.execute(sql)\n"
                            f"KW = {{'sql': {_CANONICAL_QUERIES[0]!r}}}\n"
                            "run(None, **KW)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "starred_target_arguments",
                (
                    (
                        "services/starred.py",
                        (
                            "def sink(conn, table):\n"
                            "    conn.execute('SELECT * FROM ' + table)\n"
                            "def relay(*args):\n"
                            "    sink(*args)\n"
                            "relay(None, 'vendor_organizations')\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "cross_file_starred_target_arguments",
                (
                    (
                        "package/sink.py",
                        (
                            "def sink(conn, table):\n"
                            "    conn.execute('SELECT * FROM ' + table)\n"
                        ),
                    ),
                    (
                        "package/relay.py",
                        (
                            "from package.sink import sink\n"
                            "def relay(*args):\n"
                            "    sink(*args)\n"
                            "relay(None, 'vendor_organizations')\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "bound_method_starred_target_arguments",
                (
                    (
                        "services/bound_starred.py",
                        (
                            "class Reader:\n"
                            "    def read(self, conn, table):\n"
                            "        conn.execute('SELECT * FROM ' + table)\n"
                            "args = (None, 'vendor_organizations')\n"
                            "Reader().read(*args)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "unknown_query_wrapper",
                (
                    (
                        "services/wrapper.py",
                        "store.query('vendor_organizations')\n",
                    ),
                ),
                "dynamic_vendor_discovery_sql",
            ),
            (
                "recursive_new_table_forwarding",
                (
                    (
                        "services/recursive.py",
                        (
                            "def forward(value):\n"
                            "    forward(value)\n"
                            "forward('vendor_organizations')\n"
                        ),
                    ),
                ),
                "unresolved_vendor_discovery_capability",
            ),
            (
                "fifth_level_new_table_forwarding",
                (
                    (
                        "services/depth.py",
                        (
                            "def a(v): b(v)\n"
                            "def b(v): c(v)\n"
                            "def c(v): d(v)\n"
                            "def d(v): e(v)\n"
                            "def e(v): external(v)\n"
                            "a('vendor_organizations')\n"
                        ),
                    ),
                ),
                "unresolved_vendor_discovery_capability",
            ),
            (
                "tuple_destructuring",
                (
                    (
                        "services/tuple_query.py",
                        (
                            "PREFIX, TABLE = "
                            "('SELECT * FROM ', 'vendor_organizations')\n"
                            "conn.execute(PREFIX + TABLE)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "augmented_query_concatenation",
                (
                    (
                        "services/augmented_query.py",
                        (
                            "sql = 'SELECT * FROM '\n"
                            "sql += 'vendor_organizations'\n"
                            "conn.execute(sql)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "instance_attribute_bound_method_flow",
                (
                    (
                        "services/instance_attribute.py",
                        (
                            "class Reader:\n"
                            "    def run(self, conn):\n"
                            "        conn.execute('SELECT * FROM ' + self.table)\n"
                            "reader = Reader()\n"
                            "reader.table = 'vendor_organizations'\n"
                            "reader.run(None)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "literal_subscript_target_assignment",
                (
                    (
                        "services/subscript_assignment.py",
                        (
                            "cfg = {}\n"
                            "cfg['table'] = 'vendor_organizations'\n"
                            "conn.execute('SELECT * FROM ' + cfg['table'])\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "list_append_target_flow",
                (
                    (
                        "services/list_append.py",
                        (
                            "args = []\n"
                            "args.append('vendor_organizations')\n"
                            "external(*args)\n"
                        ),
                    ),
                ),
                "unresolved_vendor_discovery_capability",
            ),
            (
                "dict_update_target_flow",
                (
                    (
                        "services/dict_update.py",
                        (
                            "cfg = {}\n"
                            "cfg.update({'table': 'vendor_organizations'})\n"
                            "external(**cfg)\n"
                        ),
                    ),
                ),
                "unresolved_vendor_discovery_capability",
            ),
            (
                "imported_class_target_attribute",
                (
                    (
                        "package/base.py",
                        "class Base:\n    TABLE = 'vendor_organizations'\n",
                    ),
                    (
                        "package/reader.py",
                        (
                            "from package.base import Base\n"
                            "conn.execute('SELECT * FROM ' + Base.TABLE)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "super_target_attribute",
                (
                    (
                        "services/super_attribute.py",
                        (
                            "class Base:\n"
                            "    TABLE = 'vendor_organizations'\n"
                            "class Reader(Base):\n"
                            "    def read(self, conn):\n"
                            "        conn.execute('SELECT * FROM ' + super().TABLE)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "if_predicate_target_flow",
                (
                    (
                        "services/if_predicate.py",
                        (
                            "def read(conn, table):\n"
                            "    if table == 'vendor_organizations':\n"
                            "        conn.execute('SELECT * FROM ' + table)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "match_value_target_flow",
                (
                    (
                        "services/match_value.py",
                        (
                            "def read(conn, table):\n"
                            "    match table:\n"
                            "        case 'vendor_organizations':\n"
                            "            conn.execute('SELECT * FROM ' + table)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "local_import_target_flow",
                (
                    (
                        "package/constants.py",
                        "TABLE = 'vendor_organizations'\n",
                    ),
                    (
                        "package/reader.py",
                        (
                            "def read(conn):\n"
                            "    from package.constants import TABLE\n"
                            "    conn.execute('SELECT * FROM ' + TABLE)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "closure_target_flow",
                (
                    (
                        "services/closure.py",
                        (
                            "def outer(conn):\n"
                            "    table = 'vendor_organizations'\n"
                            "    def inner():\n"
                            "        conn.execute('SELECT * FROM ' + table)\n"
                            "    inner()\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "generator_target_flow",
                (
                    (
                        "services/generator_return.py",
                        (
                            "def tables():\n"
                            "    yield 'vendor_organizations'\n"
                            "for table in tables():\n"
                            "    conn.execute('SELECT * FROM ' + table)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "unknown_get_target_flow",
                (
                    (
                        "services/unknown_get.py",
                        "external.get('vendor_organizations')\n",
                    ),
                ),
                "unresolved_vendor_discovery_capability",
            ),
            (
                "neutral_partial_output_category",
                (
                    (
                        "services/partial_output.py",
                        (
                            "VALUE = {"
                            f"'{_ANOMALY_CATEGORIES[-1]}': 'observed'}}\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_output_contract",
            ),
            (
                "neutral_partial_cli_option",
                (
                    (
                        "services/partial_cli.py",
                        "OPTIONS = ('--captured-at',)\n",
                    ),
                ),
                "partial_vendor_discovery_implementation",
            ),
            (
                "canonical_package_module",
                (
                    (
                        "tools/discover_vendor_organization_readiness/"
                        "__init__.py",
                        "",
                    ),
                ),
                "forbidden_vendor_discovery_module_path",
            ),
            (
                "module_name_collision",
                (
                    ("services/collision.py", "VALUE = 1\n"),
                    ("services/collision/__init__.py", "VALUE = 2\n"),
                ),
                "source_parse_error",
            ),
            (
                "duplicate_callable_definition",
                (
                    (
                        "services/duplicate_callable.py",
                        (
                            "def reader(conn):\n"
                            "    conn.execute('SELECT * FROM vendor_organizations')\n"
                            "alias = reader\n"
                            "def reader(conn):\n"
                            "    return None\n"
                            "alias(None)\n"
                        ),
                    ),
                ),
                "source_parse_error",
            ),
            (
                "deep_target_expression",
                (
                    (
                        "services/deep_target.py",
                        (
                            "VALUE = [[[[[[[[[[[[[["
                            "'vendor_organizations'"
                            "]]]]]]]]]]]]]]\n"
                            "conn.execute('SELECT * FROM ' + VALUE[0])\n"
                        ),
                    ),
                ),
                "unresolved_vendor_discovery_capability",
            ),
            (
                "callable_alias",
                (
                    (
                        "services/callable_alias.py",
                        (
                            "def reader(conn, table):\n"
                            "    conn.execute('SELECT * FROM ' + table)\n"
                            "alias = reader\n"
                            "alias(None, 'vendor_organizations')\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "bound_method_alias",
                (
                    (
                        "services/bound_alias.py",
                        (
                            "class Reader:\n"
                            "    def read(self, conn, table):\n"
                            "        conn.execute('SELECT * FROM ' + table)\n"
                            "reader = Reader()\n"
                            "alias = reader.read\n"
                            "alias(None, 'vendor_organizations')\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "sink_alias",
                (
                    (
                        "services/sink_alias.py",
                        (
                            "execute = conn.execute\n"
                            f"execute({_CANONICAL_QUERIES[0]!r})\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "getattr_sink",
                (
                    (
                        "services/getattr_sink.py",
                        (
                            "getattr(conn, 'execute')("
                            "'SELECT * FROM vendor_organizations')\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "f_string_query",
                (
                    (
                        "services/f_string.py",
                        (
                            "TABLE = 'vendor_organizations'\n"
                            "conn.execute(f'SELECT * FROM {TABLE}')\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "format_topology_query",
                (
                    (
                        "services/format_query.py",
                        (
                            "SOURCE = 'pragma_database_list'\n"
                            "QUERY = ('SELECT seq, name, file FROM {} "
                            "ORDER BY seq;').format(SOURCE)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "list_comprehension_query",
                (
                    (
                        "services/list_comp.py",
                        (
                            "ROWS = [conn.execute('SELECT * FROM ' + table) "
                            "for table in ('vendor_organizations',)]\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "generator_comprehension_query",
                (
                    (
                        "services/generator.py",
                        (
                            "ROWS = tuple(conn.execute('SELECT * FROM ' + table) "
                            "for table in ('vendor_organizations',))\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "lambda_forwarding",
                (
                    (
                        "services/lambda_forwarding.py",
                        (
                            "reader = lambda conn, table: "
                            "conn.execute('SELECT * FROM ' + table)\n"
                            "reader(None, 'vendor_organizations')\n"
                        ),
                    ),
                ),
                "unresolved_vendor_discovery_capability",
            ),
            (
                "integer_subscript_starred_target_arguments",
                (
                    (
                        "services/integer_subscript_starred.py",
                        (
                            "def sink(conn, table):\n"
                            "    conn.execute('SELECT * FROM ' + table)\n"
                            "args = (None, 'vendor_organizations')\n"
                            "forwarded = (args[0], args[1])\n"
                            "sink(*forwarded)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "unknown_container_append_target_flow",
                (
                    (
                        "services/unknown_append.py",
                        (
                            "values = make_values()\n"
                            "values.append('vendor_organizations')\n"
                            "external(*values)\n"
                        ),
                    ),
                ),
                "unresolved_vendor_discovery_capability",
            ),
            (
                "unknown_container_update_target_flow",
                (
                    (
                        "services/unknown_update.py",
                        (
                            "values = make_values()\n"
                            "values.update({'table': 'vendor_organizations'})\n"
                            "external(**values)\n"
                        ),
                    ),
                ),
                "unresolved_vendor_discovery_capability",
            ),
            (
                "package_relative_reexport_target_constant",
                (
                    (
                        "package/constants.py",
                        "TABLE = 'vendor_organizations'\n",
                    ),
                    (
                        "package/reexports.py",
                        "from .constants import TABLE\n",
                    ),
                    (
                        "package/__init__.py",
                        "from .reexports import TABLE\n",
                    ),
                    (
                        "package/reader.py",
                        (
                            "from package import TABLE\n"
                            "def read(conn):\n"
                            "    conn.execute('SELECT * FROM ' + TABLE)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "package_relative_reexport_unknown_call",
                (
                    (
                        "package/constants.py",
                        "TABLE = 'vendor_organizations'\n",
                    ),
                    (
                        "package/first.py",
                        "from .constants import TABLE\n",
                    ),
                    (
                        "package/second.py",
                        "from .first import TABLE\n",
                    ),
                    (
                        "package/__init__.py",
                        "from .second import TABLE\n",
                    ),
                    (
                        "services/reexport_unknown.py",
                        (
                            "from package import TABLE\n"
                            "external(TABLE)\n"
                        ),
                    ),
                ),
                "unresolved_vendor_discovery_capability",
            ),
            (
                "module_qualified_imported_base_attribute",
                (
                    (
                        "package/base.py",
                        "class Base:\n    TABLE = 'vendor_organizations'\n",
                    ),
                    (
                        "package/reader.py",
                        (
                            "import package.base\n"
                            "class Reader(package.base.Base):\n"
                            "    def read(self, conn):\n"
                            "        conn.execute('SELECT * FROM ' + self.TABLE)\n"
                            "Reader().read(None)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "multiple_inheritance_target_precedence",
                (
                    (
                        "services/multiple_inheritance.py",
                        (
                            "class TargetBase:\n"
                            "    TABLE = 'vendor_organizations'\n"
                            "class SafeBase:\n"
                            "    TABLE = 'audit_events'\n"
                            "class Reader(TargetBase, SafeBase):\n"
                            "    def read(self, conn):\n"
                            "        conn.execute('SELECT * FROM ' + self.TABLE)\n"
                            "Reader().read(None)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "camel_case_vendor_relationship_scanner",
                (
                    (
                        "services/camel_scanner.py",
                        (
                            "def ScanVendorRelationships():\n"
                            "    return None\n"
                        ),
                    ),
                ),
                "partial_vendor_discovery_implementation",
            ),
            (
                "camel_case_vendor_organization_scanner_class",
                (
                    (
                        "services/camel_scanner_class.py",
                        (
                            "class VendorOrganizationScanner:\n"
                            "    pass\n"
                        ),
                    ),
                ),
                "partial_vendor_discovery_implementation",
            ),
            (
                "imported_partial_output_category",
                (
                    (
                        "package/output_constants.py",
                        (
                            f"CATEGORY = '{_ANOMALY_CATEGORIES[-1]}'\n"
                        ),
                    ),
                    (
                        "services/imported_output.py",
                        (
                            "from package.output_constants import CATEGORY\n"
                            "OUTPUT = (CATEGORY,)\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_output_contract",
            ),
            (
                "imported_partial_cli_option",
                (
                    (
                        "package/cli_constants.py",
                        "OPTION = '--captured-at'\n",
                    ),
                    (
                        "services/imported_cli.py",
                        (
                            "from package.cli_constants import OPTION\n"
                            "OPTIONS = (OPTION,)\n"
                        ),
                    ),
                ),
                "partial_vendor_discovery_implementation",
            ),
            (
                "dict_subscript_sql_sink",
                (
                    (
                        "services/dict_sink.py",
                        (
                            "sinks = {'run': conn.execute}\n"
                            "sinks['run']('SELECT * FROM vendor_organizations')\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
            (
                "list_subscript_sql_sink",
                (
                    (
                        "services/list_sink.py",
                        (
                            "sinks = [conn.execute]\n"
                            "sinks[0]('SELECT * FROM vendor_organizations')\n"
                        ),
                    ),
                ),
                "forbidden_vendor_discovery_query",
            ),
        )
        for name, files, expected in flow_scenarios:
            root = temp_root / f"negative-flow-{name}"
            shutil.copytree(baseline, root)
            for relative, source in files:
                _write_text(root, relative, source)
            _assert_negative(root, expected, name)
            scenario_count += 1

        upstream_mutations: tuple[
            tuple[str, Callable[[str], str]], ...
        ] = (
            (
                "upstream_early_return_before_integration",
                lambda source: source.replace(
                    "def analyze_repository(root: Path) -> list[Issue]:\n",
                    (
                        "def analyze_repository(root: Path) -> list[Issue]:\n"
                        "    if root.name:\n"
                        "        return []\n"
                    ),
                    1,
                ),
            ),
            (
                "upstream_dead_branch_before_integration",
                lambda source: source.replace(
                    "def analyze_repository(root: Path) -> list[Issue]:\n",
                    (
                        "def analyze_repository(root: Path) -> list[Issue]:\n"
                        "    if False:\n"
                        "        return []\n"
                    ),
                    1,
                ),
            ),
            (
                "upstream_duplicate_integration_owner",
                lambda source: source
                + "\ndef analyze_repository(root: Path) -> list[Issue]:\n"
                + "    return []\n",
            ),
            (
                "upstream_coordinated_provider_constant_drift",
                lambda source: source.replace(
                    '"ensure_vendor_organization_schema",\n',
                    '"ensure_vendor_organization_schema_drift",\n',
                    1,
                ).replace(
                    (
                        '"BD502BCCFCC0B4D3469D0319A82763691463D62CF'
                        '0609439BF71968B96F11595"\n'
                    ),
                    (
                        '"0000000000000000000000000000000000000000'
                        '000000000000000000000000"\n'
                    ),
                    1,
                ),
            ),
            (
                "upstream_coordinated_manifest_provider_drift",
                lambda source: source.replace(
                    '"vendor_schema_projection",\n',
                    '"vendor_schema_projection_drift",\n',
                    1,
                ).replace(
                    (
                        '"32813A42CB3FBE3FA3071FF85C414EFF611E2BF4'
                        'CBD9CCF5E50B5DC1BB11288F"\n'
                    ),
                    (
                        '"0000000000000000000000000000000000000000'
                        '000000000000000000000000"\n'
                    ),
                    1,
                ),
            ),
            (
                "upstream_dynamic_dunder_import",
                lambda source: source.replace(
                    (
                        "def validate_exact_discovery_readiness_checker(\n"
                        "    tree: ast.Module,\n"
                        ") -> tuple[list[Issue], "
                        "StructuralAllowanceCandidate]:\n"
                    ),
                    (
                        "def validate_exact_discovery_readiness_checker(\n"
                        "    tree: ast.Module,\n"
                        ") -> tuple[list[Issue], "
                        "StructuralAllowanceCandidate]:\n"
                        "    __import__('sqlite3')\n"
                    ),
                    1,
                ),
            ),
            (
                "upstream_dynamic_importlib_import",
                lambda source: source.replace(
                    (
                        "def validate_exact_discovery_readiness_checker(\n"
                        "    tree: ast.Module,\n"
                        ") -> tuple[list[Issue], "
                        "StructuralAllowanceCandidate]:\n"
                    ),
                    (
                        "def validate_exact_discovery_readiness_checker(\n"
                        "    tree: ast.Module,\n"
                        ") -> tuple[list[Issue], "
                        "StructuralAllowanceCandidate]:\n"
                        "    importlib.import_module('sqlite3')\n"
                    ),
                    1,
                ),
            ),
        )
        for name, mutate in upstream_mutations:
            root = temp_root / f"negative-{name}"
            shutil.copytree(baseline, root)
            path = root / _UPSTREAM_CHECKER_PATH
            source = path.read_text(encoding="utf-8")
            mutated = mutate(source)
            if mutated == source:
                raise AssertionError(
                    f"upstream mutation made no change: {name}"
                )
            path.write_text(
                mutated,
                encoding="utf-8",
                newline="\n",
            )
            _assert_negative(
                root,
                "upstream_vendor_schema_guard_drift",
                name,
            )
            scenario_count += 1

        invalid_utf8 = temp_root / "negative-read"
        shutil.copytree(baseline, invalid_utf8)
        bad_path = invalid_utf8 / "services" / "invalid.py"
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_bytes(b"\xff\xfe\x00")
        _assert_negative(invalid_utf8, "source_read_error", "read_error")
        scenario_count += 1

        policy_missing = temp_root / "negative-policy-missing"
        shutil.copytree(baseline, policy_missing)
        (policy_missing / _POLICY_PATH).unlink()
        _assert_negative(
            policy_missing,
            "vendor_discovery_policy_document_missing",
            "policy_missing",
        )
        scenario_count += 1

        stale_policy_sha = temp_root / "negative-stale-policy-sha"
        shutil.copytree(baseline, stale_policy_sha)
        policy_path = stale_policy_sha / _POLICY_PATH
        policy_path.write_text(
            policy_path.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
            newline="\n",
        )
        _assert_negative(
            stale_policy_sha,
            "vendor_discovery_policy_drift",
            "stale_policy_sha",
        )
        scenario_count += 1

        old_policy_status = temp_root / "negative-old-policy-status"
        shutil.copytree(baseline, old_policy_status)
        policy_path = old_policy_status / _POLICY_PATH
        policy_path.write_text(
            policy_path.read_text(encoding="utf-8").replace(
                "DOCS-ONLY CONTRACT PRODUCTION-FROZEN / IMPLEMENTATION NOT STARTED",
                "DOCS-ONLY DESIGN BASELINE / IMPLEMENTATION NOT STARTED",
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )
        _assert_negative(
            old_policy_status,
            "vendor_discovery_policy_marker_missing",
            "old_policy_status",
        )
        scenario_count += 1

        section_nineteen_missing = (
            temp_root / "negative-section-nineteen-missing"
        )
        shutil.copytree(baseline, section_nineteen_missing)
        policy_path = section_nineteen_missing / _POLICY_PATH
        policy_text = policy_path.read_text(encoding="utf-8")
        policy_path.write_text(
            policy_text.split(
                "## 19. Production baseline freeze evidence", 1
            )[0],
            encoding="utf-8",
            newline="\n",
        )
        _assert_negative(
            section_nineteen_missing,
            "vendor_discovery_policy_drift",
            "section_nineteen_missing",
        )
        scenario_count += 1

        section_nineteen_reordered = (
            temp_root / "negative-section-nineteen-reordered"
        )
        shutil.copytree(baseline, section_nineteen_reordered)
        policy_path = section_nineteen_reordered / _POLICY_PATH
        policy_text = policy_path.read_text(encoding="utf-8")
        before_eighteen, section_eighteen = policy_text.split("## 18.", 1)
        section_eighteen_body, section_nineteen = section_eighteen.split(
            "## 19.", 1
        )
        policy_path.write_text(
            (
                before_eighteen
                + "## 19."
                + section_nineteen
                + "## 18."
                + section_eighteen_body
            ),
            encoding="utf-8",
            newline="\n",
        )
        _assert_negative(
            section_nineteen_reordered,
            "vendor_discovery_policy_drift",
            "section_nineteen_reordered",
        )
        scenario_count += 1

        section_nineteen_marker = (
            temp_root / "negative-section-nineteen-marker"
        )
        shutil.copytree(baseline, section_nineteen_marker)
        policy_path = section_nineteen_marker / _POLICY_PATH
        policy_path.write_text(
            policy_path.read_text(encoding="utf-8").replace(
                "NO DATABASE OR ENVIRONMENT ACCESSED",
                "DATABASE OR ENVIRONMENT BOUNDARY DRIFTED",
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )
        _assert_negative(
            section_nineteen_marker,
            "vendor_discovery_policy_marker_missing",
            "section_nineteen_marker",
        )
        scenario_count += 1

        policy_marker = temp_root / "negative-policy-marker"
        shutil.copytree(baseline, policy_marker)
        policy_path = policy_marker / _POLICY_PATH
        policy_path.write_text(
            policy_path.read_text(encoding="utf-8").replace(
                "DISCOVERY CONTRACT：FROZEN", "DISCOVERY CONTRACT：DRIFTED"
            ),
            encoding="utf-8",
            newline="\n",
        )
        _assert_negative(
            policy_marker,
            "vendor_discovery_policy_marker_missing",
            "policy_marker",
        )
        scenario_count += 1

        policy_order = temp_root / "negative-policy-order"
        shutil.copytree(baseline, policy_order)
        policy_path = policy_order / _POLICY_PATH
        policy_text = policy_path.read_text(encoding="utf-8")
        policy_path.write_text(
            policy_text.replace("## 2.", "## 19.", 1),
            encoding="utf-8",
            newline="\n",
        )
        _assert_negative(
            policy_order,
            "vendor_discovery_policy_drift",
            "policy_order",
        )
        scenario_count += 1

        policy_duplicate = temp_root / "negative-policy-duplicate"
        shutil.copytree(baseline, policy_duplicate)
        policy_path = policy_duplicate / _POLICY_PATH
        policy_path.write_text(
            (
                policy_path.read_text(encoding="utf-8")
                + "\nDISCOVERY CONTRACT：FROZEN\n"
            ),
            encoding="utf-8",
            newline="\n",
        )
        _assert_negative(
            policy_duplicate,
            "vendor_discovery_policy_marker_missing",
            "policy_duplicate",
        )
        scenario_count += 1

        checker_broadening = temp_root / "negative-checker-broadening"
        shutil.copytree(baseline, checker_broadening)
        checker_path = checker_broadening / _CHECKER_PATH
        checker_path.write_text(
            (
                checker_path.read_text(encoding="utf-8")
                + "\ndef _hidden_vendor_reader(conn):\n"
                + "    return conn.execute("
                + repr(_CANONICAL_QUERIES[0])
                + ")\n"
            ),
            encoding="utf-8",
            newline="\n",
        )
        _assert_negative(
            checker_broadening,
            "checker_exemption_broadening",
            "checker_broadening",
        )
        scenario_count += 1

        cross_file = temp_root / "negative-cross-file"
        shutil.copytree(baseline, cross_file)
        _write_text(
            cross_file,
            "package/constants.py",
            "TABLE = 'vendor_organizations'\n",
        )
        _write_text(
            cross_file,
            "package/reader.py",
            (
                "from package.constants import TABLE\n"
                "def read(conn, table):\n"
                "    conn.execute('SELECT * FROM ' + table)\n"
                "read(None, TABLE)\n"
            ),
        )
        _assert_negative(
            cross_file,
            "forbidden_vendor_discovery_query",
            "cross_file",
        )
        scenario_count += 1

        module_qualified = temp_root / "negative-module-qualified"
        shutil.copytree(baseline, module_qualified)
        _write_text(
            module_qualified,
            "package/constants.py",
            "TABLE = 'vendor_organizations'\n",
        )
        _write_text(
            module_qualified,
            "package/reader.py",
            (
                "import package.constants as constants\n"
                "def read(conn):\n"
                "    conn.execute('SELECT * FROM ' + constants.TABLE)\n"
            ),
        )
        _assert_negative(
            module_qualified,
            "forbidden_vendor_discovery_query",
            "module_qualified",
        )
        scenario_count += 1

        inherited = temp_root / "negative-inherited"
        shutil.copytree(baseline, inherited)
        _write_text(
            inherited,
            "package/base.py",
            "class Base:\n    TABLE = 'vendor_organizations'\n",
        )
        _write_text(
            inherited,
            "package/reader.py",
            (
                "from package.base import Base\n"
                "class Reader(Base):\n"
                "    def read(self, conn):\n"
                "        conn.execute('SELECT * FROM ' + self.TABLE)\n"
            ),
        )
        _assert_negative(
            inherited,
            "forbidden_vendor_discovery_query",
            "inherited",
        )
        scenario_count += 1

        starred = temp_root / "negative-starred"
        shutil.copytree(baseline, starred)
        _write_text(
            starred,
            "tools/vendor_discovery_starred.py",
            (
                "class Reader:\n"
                "    def read(self, conn, table):\n"
                "        conn.execute('SELECT * FROM ' + table)\n"
                "ARGS = (None, 'vendor_organizations')\n"
                "Reader().read(*ARGS)\n"
            ),
        )
        _assert_negative(
            starred,
            "forbidden_vendor_discovery_query",
            "starred",
        )
        scenario_count += 1

        comment_decoy = temp_root / "positive-comment-decoy"
        shutil.copytree(baseline, comment_decoy)
        _write_text(
            comment_decoy,
            "services/comment_only.py",
            (
                "# discover_vendor_organization_readiness must never run here\n"
                "VALUE = 'ordinary business value'\n"
            ),
        )
        if _analyze_repository(comment_decoy):
            raise AssertionError("comment decoy positive control failed")
        scenario_count += 1

        recursive = temp_root / "negative-recursive"
        shutil.copytree(baseline, recursive)
        _write_text(
            recursive,
            "tools/vendor_discovery_recursive.py",
            (
                "def forward(conn, value):\n"
                "    forward(conn, value)\n"
                "forward(None, 'discover_vendor_organization_readiness')\n"
            ),
        )
        _assert_negative(
            recursive,
            "unresolved_vendor_discovery_capability",
            "recursive",
        )
        scenario_count += 1

        depth = temp_root / "negative-depth"
        shutil.copytree(baseline, depth)
        _write_text(
            depth,
            "tools/vendor_discovery_depth.py",
            (
                "def a(v): b(v)\n"
                "def b(v): c(v)\n"
                "def c(v): d(v)\n"
                "def d(v): e(v)\n"
                "def e(v): external(v)\n"
                "a('discover_vendor_organization_readiness')\n"
            ),
        )
        _assert_negative(
            depth,
            "unresolved_vendor_discovery_capability",
            "depth",
        )
        scenario_count += 1

        cli_cases = (
            ((), False),
            (("--self-test",), False),
            (("--self-test", "--self-test"), True),
            (("--self",), True),
            (("--unknown",), True),
            (("--self-test=value",), True),
            (("positional",), True),
        )
        for arguments, should_fail in cli_cases:
            stderr = io.StringIO()
            failed = False
            with contextlib.redirect_stderr(stderr):
                try:
                    _parse_args(arguments)
                except SystemExit as exc:
                    failed = exc.code == 2
            if failed != should_fail:
                raise AssertionError(
                    f"CLI scenario {arguments!r} mismatch: {failed}"
                )
            scenario_count += 1

    print(f"self_test_scenarios: {scenario_count}")
    print("database_access: 0")
    print("app_imports: 0")
    print(_SELF_TEST_MARKER)
    return 0


def _main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.self_test:
        return _run_self_test()
    issues = _analyze_repository(_ROOT_DIR)
    status, output = _render_normal(issues)
    print(output, end="")
    return status


if __name__ == "__main__":
    raise SystemExit(_main())
