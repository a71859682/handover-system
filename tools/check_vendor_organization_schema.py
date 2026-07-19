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
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
CHECKER_PATH = Path("tools/check_vendor_organization_schema.py")
VENDOR_POLICY_PATH = Path(
    "docs/vendor_id_001_vendor_organization_owner_member_design.md"
)
SCHEMA_POLICY_PATH = Path(
    "docs/vendor_id_002_physical_sqlite_schema_migration_baseline.md"
)
PASS_MARKER = "vendor organization schema readiness PASS"
SELF_TEST_MARKER = "vendor organization schema readiness self-test PASS"

APPROVED_VENDOR_POLICY_BLOB = "4c3f6c19415c5ea79c2bae0d2ff8c55f5e0f2b8e"
APPROVED_SCHEMA_POLICY_BLOB = "c8ddd13fc3cc8b80cc7e8145ace31e6c1468afa8"
APPROVED_SCHEMA_POLICY_SHA256 = (
    "889FFA9AA2418DE5EA1C519B617F01262AAD8106BBD75D9FED2331B74897BBA2"
)

TARGET_TABLES = (
    "vendor_organizations",
    "vendor_organization_memberships",
    "vendor_site_assignments",
    "sheet_vendor_bindings",
)
TARGET_INDEXES = (
    "idx_vendor_organizations_status",
    "uq_vendor_organization_memberships_active_account",
    "uq_vendor_organization_memberships_current_pair",
    "idx_vendor_organization_memberships_vendor_status",
    "idx_vendor_organization_memberships_account_status",
    "uq_vendor_organization_memberships_predecessor",
    "uq_vendor_site_assignments_active_pair",
    "idx_vendor_site_assignments_vendor_status",
    "idx_vendor_site_assignments_site_status",
    "uq_vendor_site_assignments_predecessor",
    "uq_sheet_vendor_bindings_active_pair",
    "idx_sheet_vendor_bindings_vendor_status",
    "idx_sheet_vendor_bindings_sheet_status",
    "idx_sheet_vendor_bindings_assignment",
    "uq_sheet_vendor_bindings_predecessor",
)
TARGET_AUTOINDEXES = tuple(
    f"sqlite_autoindex_{table}_1" for table in TARGET_TABLES
)
TARGET_TOKENS = TARGET_TABLES + TARGET_INDEXES + TARGET_AUTOINDEXES

VENDOR_POLICY_MARKERS = (
    "Status: design baseline",
    "Implementation status: not started",
    "## 15. Migration and authority-switch sequencing",
    "## 18. Future implementation acceptance matrix",
    "physical schema started;",
    "backfill was authorized;",
    "runtime authority changed;",
)
SCHEMA_POLICY_MARKERS = (
    "Status: design baseline",
    "Implementation status: not started",
    "## 5. Exact table inventory and creation order",
    "## 10. Exact index inventory and predicates",
    "## 15. Migration transaction and savepoint contract",
    "## 20. Status and deferred owners",
    "EXACT FOUR-TABLE PROJECTION: FROZEN",
    "MIGRATION / SAVEPOINT CONTRACT: FROZEN",
    "PHYSICAL SCHEMA IMPLEMENTATION: NOT STARTED",
    "BACKFILL / AUTHORITY SWITCH: NOT AUTHORIZED",
)

FIXED_RUNTIME_FILES = (
    Path("app.py"),
    Path("models.py"),
    Path("database.py"),
    Path("sqlite_db_path.py"),
)
EXCLUDED_TOP_LEVEL_RUNTIME_NAMES = (
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
)

SCHEMA_VERBS = (
    "create table",
    "alter table",
    "drop table",
    "create index",
    "create unique index",
    "drop index",
    "create trigger",
    "drop trigger",
)
SQL_SINKS = {"execute", "executemany", "executescript"}
BACKEND_ROOTS = {
    "alembic",
    "psycopg",
    "psycopg2",
    "sqlalchemy",
}
MIGRATION_WORDS = {
    "apply",
    "bootstrap",
    "classifier",
    "compare",
    "ddl",
    "ensure",
    "expected",
    "index",
    "inventory",
    "manifest",
    "metadata",
    "migrate",
    "migration",
    "projection",
    "savepoint",
    "schema",
    "table",
}
CONSUMER_WORDS = {
    "api",
    "cli",
    "command",
    "create",
    "delete",
    "endpoint",
    "form",
    "handler",
    "job",
    "route",
    "schedule",
    "submit",
    "update",
    "write",
}
BACKFILL_WORDS = {
    "backfill",
    "copy",
    "legacy",
    "reconcile",
    "reconciliation",
    "transform",
}
AUTHORITY_WORDS = {
    "authority",
    "authorize",
    "permission",
    "principal",
    "routing",
    "switch",
}
RELATIONSHIP_WORDS = {
    "activate",
    "assign",
    "assignment",
    "bind",
    "binding",
    "demote",
    "member",
    "membership",
    "owner",
    "promote",
    "reactivate",
    "revoke",
    "transfer",
    "transition",
}
EXEMPTION_WORDS = {
    "allowlist",
    "exempt",
    "ignore",
    "safe_prefix",
    "skip",
    "suppress",
    "wildcard",
}


@dataclass(frozen=True, order=True)
class Issue:
    code: str
    path: str
    line: int
    symbol: str


@dataclass(frozen=True)
class Value:
    strings: tuple[str, ...] = ()
    sequence: tuple[str, ...] | None = None
    mapping: tuple[tuple[str, Value], ...] = ()
    dynamic: bool = False

    @property
    def evidence(self) -> str:
        mapping_evidence = [
            item
            for key, value in self.mapping
            for item in (key, *value.strings)
        ]
        return " ".join((*self.strings, *mapping_evidence))


@dataclass(frozen=True)
class CallableInfo:
    qualified_name: str
    module_name: str
    path: Path
    node: ast.FunctionDef | ast.AsyncFunctionDef
    owner_class: str | None
    binding_kind: str


@dataclass
class RepositoryContext:
    callables: dict[str, CallableInfo]
    module_scopes: dict[str, dict[str, Value]]
    analyzers: dict[str, PythonSourceAnalyzer]
    active_calls: list[str]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check that VENDOR-ID-002 physical schema capability is absent.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run isolated static-analysis scenarios",
    )
    tokens = list(sys.argv[1:] if argv is None else argv)
    if tokens.count("--self-test") > 1:
        parser.error("--self-test may be specified exactly once")
    return parser.parse_args(tokens)


def assert_cli_parser_contract() -> int:
    scenario_count = 0
    for argv, expected_self_test in (
        ([], False),
        (["--self-test"], True),
    ):
        parsed = parse_args(argv)
        if parsed.self_test is not expected_self_test:
            raise AssertionError(f"CLI positive scenario failed: {argv!r}")
        scenario_count += 1

    for argv in (
        ["--self"],
        ["--self-t"],
        ["--self-test", "--self-test"],
        ["positional"],
        ["--unknown"],
        ["--self-test=true"],
    ):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            try:
                parse_args(argv)
            except SystemExit as exc:
                if exc.code != 2:
                    raise AssertionError(
                        f"CLI rejection used unexpected exit for {argv!r}: {exc.code}"
                    )
            else:
                raise AssertionError(f"CLI negative scenario was accepted: {argv!r}")
        if not stderr.getvalue():
            raise AssertionError(f"CLI rejection emitted no diagnostic: {argv!r}")
        scenario_count += 1
    return scenario_count


def git_blob_id(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def normalized_identifier_text(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r'["`\[\]]', "", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def words(value: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9_]+", value.lower())
    result = set(tokens)
    for token in tokens:
        result.update(part for part in token.split("_") if part)
    return result


def dotted_name(node: ast.AST | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def bounded_unique(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))[:32]


def merge_values(*values: Value, dynamic: bool = False) -> Value:
    strings: list[str] = []
    mapping: dict[str, Value] = {}
    for value in values:
        strings.extend(value.strings)
        if value.sequence:
            strings.extend(value.sequence)
        mapping.update(dict(value.mapping))
        dynamic = dynamic or value.dynamic
    return Value(
        bounded_unique(strings),
        mapping=tuple(sorted(mapping.items())),
        dynamic=dynamic,
    )


def resolve_value(
    node: ast.AST | None,
    scopes: list[dict[str, Value]],
    helper_returns: dict[str, Value],
    depth: int = 0,
) -> Value:
    if node is None or depth > 12:
        return Value(dynamic=True)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return Value((node.value,))
        if isinstance(node.value, (int, float, bool)) or node.value is None:
            return Value((repr(node.value),))
        return Value(dynamic=True)
    if isinstance(node, ast.Name):
        for scope in reversed(scopes):
            if node.id in scope:
                return scope[node.id]
        return Value((node.id,), dynamic=True)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        items = [
            resolve_value(item, scopes, helper_returns, depth + 1)
            for item in node.elts
        ]
        sequence: list[str] = []
        dynamic = False
        for item in items:
            dynamic = dynamic or item.dynamic or len(item.strings) != 1
            sequence.extend(item.strings)
        return Value(
            bounded_unique(sequence),
            sequence=tuple(sequence) if not dynamic else None,
            dynamic=dynamic,
        )
    if isinstance(node, ast.Dict):
        mapping: dict[str, Value] = {}
        values: list[Value] = []
        dynamic = False
        for key_node, value_node in zip(node.keys, node.values):
            key = resolve_value(key_node, scopes, helper_returns, depth + 1)
            value = resolve_value(value_node, scopes, helper_returns, depth + 1)
            values.extend((key, value))
            if len(key.strings) == 1 and not key.dynamic:
                mapping[key.strings[0]] = value
            else:
                dynamic = True
        merged = merge_values(*values, dynamic=dynamic)
        return Value(
            merged.strings,
            mapping=tuple(sorted(mapping.items())),
            dynamic=merged.dynamic,
        )
    if isinstance(node, ast.Subscript):
        container = resolve_value(node.value, scopes, helper_returns, depth + 1)
        key = resolve_value(node.slice, scopes, helper_returns, depth + 1)
        if len(key.strings) == 1:
            selected = dict(container.mapping).get(key.strings[0])
            if selected is not None:
                return selected
            if (
                container.sequence is not None
                and key.strings[0].lstrip("-").isdigit()
            ):
                index = int(key.strings[0])
                if -len(container.sequence) <= index < len(container.sequence):
                    return Value((container.sequence[index],))
        return merge_values(container, key, dynamic=True)
    if isinstance(node, ast.BinOp):
        left = resolve_value(node.left, scopes, helper_returns, depth + 1)
        right = resolve_value(node.right, scopes, helper_returns, depth + 1)
        if (
            isinstance(node.op, ast.Add)
            and not left.dynamic
            and not right.dynamic
            and len(left.strings) == 1
            and len(right.strings) == 1
        ):
            return Value((left.strings[0] + right.strings[0],), dynamic=True)
        if (
            isinstance(node.op, ast.Mod)
            and not left.dynamic
            and len(left.strings) == 1
        ):
            return merge_values(left, right, dynamic=True)
        return merge_values(left, right, dynamic=True)
    if isinstance(node, ast.JoinedStr):
        pieces: list[str] = []
        dynamic = False
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                pieces.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                resolved = resolve_value(
                    value.value, scopes, helper_returns, depth + 1
                )
                pieces.extend(resolved.strings)
                dynamic = True
        return Value(("".join(pieces),), dynamic=dynamic)
    if isinstance(node, ast.IfExp):
        return merge_values(
            resolve_value(node.body, scopes, helper_returns, depth + 1),
            resolve_value(node.orelse, scopes, helper_returns, depth + 1),
            dynamic=True,
        )
    if isinstance(node, ast.BoolOp):
        return merge_values(
            *(
                resolve_value(value, scopes, helper_returns, depth + 1)
                for value in node.values
            ),
            dynamic=True,
        )
    if isinstance(node, ast.Starred):
        return resolve_value(
            node.value,
            scopes,
            helper_returns,
            depth + 1,
        )
    if isinstance(node, ast.Call):
        call_name = dotted_name(node.func)
        short_name = call_name.rsplit(".", 1)[-1]
        if short_name in helper_returns:
            return helper_returns[short_name]
        if isinstance(node.func, ast.Attribute) and node.func.attr == "format":
            base = resolve_value(
                node.func.value, scopes, helper_returns, depth + 1
            )
            args = [
                resolve_value(arg, scopes, helper_returns, depth + 1)
                for arg in node.args
            ]
            return merge_values(base, *args, dynamic=True)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "join":
            separator = resolve_value(
                node.func.value, scopes, helper_returns, depth + 1
            )
            joined = (
                resolve_value(node.args[0], scopes, helper_returns, depth + 1)
                if node.args
                else Value(dynamic=True)
            )
            if (
                len(separator.strings) == 1
                and joined.sequence is not None
                and not separator.dynamic
                and not joined.dynamic
            ):
                return Value((separator.strings[0].join(joined.sequence),))
            return merge_values(separator, joined, dynamic=True)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "replace":
            receiver = resolve_value(
                node.func.value, scopes, helper_returns, depth + 1
            )
            args = [
                resolve_value(arg, scopes, helper_returns, depth + 1)
                for arg in node.args
            ]
            if (
                len(receiver.strings) == 1
                and len(args) >= 2
                and len(args[0].strings) == 1
                and len(args[1].strings) == 1
                and not receiver.dynamic
                and not args[0].dynamic
                and not args[1].dynamic
            ):
                return Value(
                    (
                        receiver.strings[0].replace(
                            args[0].strings[0],
                            args[1].strings[0],
                        ),
                    ),
                    dynamic=len(args) > 2,
                )
            return merge_values(receiver, *args, dynamic=True)
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            "casefold",
            "lower",
            "lstrip",
            "rstrip",
            "strip",
            "upper",
        }:
            receiver = resolve_value(
                node.func.value, scopes, helper_returns, depth + 1
            )
            args = [
                resolve_value(arg, scopes, helper_returns, depth + 1)
                for arg in node.args
            ]
            if len(receiver.strings) == 1 and not receiver.dynamic and not args:
                method = getattr(receiver.strings[0], node.func.attr)
                return Value((method(),))
            return merge_values(receiver, *args, dynamic=True)
        receiver = (
            resolve_value(node.func.value, scopes, helper_returns, depth + 1)
            if isinstance(node.func, ast.Attribute)
            else Value()
        )
        return merge_values(
            receiver,
            *(
                resolve_value(arg, scopes, helper_returns, depth + 1)
                for arg in node.args
            ),
            *(
                resolve_value(keyword.value, scopes, helper_returns, depth + 1)
                for keyword in node.keywords
            ),
            dynamic=True,
        )
    if isinstance(node, ast.Attribute):
        name = dotted_name(node)
        for scope in reversed(scopes):
            if name in scope:
                return scope[name]
        receiver = resolve_value(node.value, scopes, helper_returns, depth + 1)
        return merge_values(receiver, Value((name,)), dynamic=True)
    return Value(dynamic=True)


def node_structural_evidence(node: ast.AST) -> str:
    evidence: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            evidence.append(child.id)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            evidence.append(child.name)
        elif isinstance(child, ast.arg):
            evidence.append(child.arg)
        elif isinstance(child, ast.Attribute):
            evidence.append(child.attr)
        elif isinstance(child, ast.Constant) and isinstance(child.value, str):
            evidence.append(child.value)
    return normalized_identifier_text(" ".join(evidence))


def has_target(value: str) -> bool:
    normalized = normalized_identifier_text(value)
    return any(token in normalized for token in TARGET_TOKENS)


def has_schema_verb(value: str) -> bool:
    normalized = normalized_identifier_text(value)
    return any(verb in normalized for verb in SCHEMA_VERBS)


def python_module_name(relative_path: Path) -> str:
    parts = list(relative_path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


class PythonSourceAnalyzer:
    def __init__(
        self,
        relative_path: Path,
        tree: ast.Module,
        context: RepositoryContext | None = None,
    ):
        self.path = relative_path.as_posix()
        self.relative_path = relative_path
        self.tree = tree
        self.context = context
        self.module_name = python_module_name(relative_path)
        self.issues: list[Issue] = []
        self.module_scope: dict[str, Value] = {}
        self.helper_returns: dict[str, Value] = {}
        self.created_tables: set[str] = set()
        self.module_evidence = node_structural_evidence(tree)
        self.import_roots = self._import_roots()
        self.import_aliases = self._import_aliases()
        self.class_names = {
            node.name for node in tree.body if isinstance(node, ast.ClassDef)
        }
        self.class_bases = {
            node.name: tuple(
                dotted_name(base)
                for base in node.bases
                if dotted_name(base)
            )
            for node in tree.body
            if isinstance(node, ast.ClassDef)
        }
        self.instance_types: dict[str, str] = {}
        self.exported_scope_keys: set[str] = set()
        self.function_defs = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.active_calls: list[str] = []
        self.prepared = False

    def _import_roots(self) -> set[str]:
        roots: set[str] = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".", 1)[0])
        return roots

    def _import_aliases(self) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for node in self.tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    bound = alias.asname or alias.name.split(".", 1)[0]
                    aliases[bound] = alias.name if alias.asname else bound
            elif isinstance(node, ast.ImportFrom):
                module = self._resolved_import_from_module(node)
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    bound = alias.asname or alias.name
                    aliases[bound] = ".".join(
                        part for part in (module, alias.name) if part
                    )
        return aliases

    def _resolved_import_from_module(self, node: ast.ImportFrom) -> str:
        module_parts = node.module.split(".") if node.module else []
        if not node.level:
            return ".".join(module_parts)
        current_parts = self.module_name.split(".")
        package_parts = (
            current_parts
            if self.relative_path.name == "__init__.py"
            else current_parts[:-1]
        )
        keep = max(0, len(package_parts) - (node.level - 1))
        return ".".join((*package_parts[:keep], *module_parts))

    def _propagate_imported_values(self) -> bool:
        if self.context is None:
            return False
        changed = False

        def store(name: str, value: Value, *, exported: bool = True) -> None:
            nonlocal changed
            if self.module_scope.get(name) != value:
                self.module_scope[name] = value
                changed = True
            if exported:
                self.exported_scope_keys.add(name)

        def exported_items(module: str) -> tuple[tuple[str, Value], ...]:
            imported_scope = self.context.module_scopes.get(module)
            imported_analyzer = self.context.analyzers.get(module)
            if imported_scope is None or imported_analyzer is None:
                return ()
            return tuple(
                (key, imported_scope[key])
                for key in sorted(imported_analyzer.exported_scope_keys)
                if key in imported_scope
            )

        for node in self.tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_values = exported_items(alias.name)
                    if not imported_values:
                        continue
                    local_prefix = alias.asname or alias.name
                    for key, value in imported_values:
                        store(f"{local_prefix}.{key}", value)
            elif isinstance(node, ast.ImportFrom):
                module = self._resolved_import_from_module(node)
                imported_values = dict(exported_items(module))
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    local_name = alias.asname or alias.name
                    direct = imported_values.get(alias.name)
                    if direct is not None:
                        store(local_name, direct)
                    prefix = f"{alias.name}."
                    for key, value in tuple(imported_values.items()):
                        if key.startswith(prefix):
                            store(f"{local_name}.{key[len(prefix):]}", value)
                    submodule = ".".join(
                        part for part in (module, alias.name) if part
                    )
                    for key, value in exported_items(submodule):
                        store(f"{local_name}.{key}", value)
        return changed

    def _propagate_inherited_values(self) -> bool:
        changed = False
        for class_name, bases in self.class_bases.items():
            for base in bases:
                base_prefix = f"{base}."
                for key, value in tuple(self.module_scope.items()):
                    if not key.startswith(base_prefix):
                        continue
                    inherited_key = f"{class_name}.{key[len(base_prefix):]}"
                    if inherited_key not in self.module_scope:
                        self.module_scope[inherited_key] = value
                        self.exported_scope_keys.add(inherited_key)
                        changed = True
        return changed

    def add(self, code: str, node: ast.AST, symbol: str = "") -> None:
        self.issues.append(
            Issue(code, self.path, getattr(node, "lineno", 1), symbol or "-")
        )

    def _record_assignment(
        self,
        target: ast.AST,
        value: Value,
        scope: dict[str, Value],
    ) -> None:
        if isinstance(target, ast.Name):
            scope[target.id] = value
        elif isinstance(target, ast.Attribute):
            scope[dotted_name(target)] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                if isinstance(element, (ast.Name, ast.Attribute)):
                    scope[dotted_name(element)] = value

    def _classify_sql(
        self,
        node: ast.AST,
        value: Value,
        sink: str | None,
        symbol: str,
    ) -> None:
        combined = normalized_identifier_text(value.evidence)
        if not has_target(combined):
            return

        found_specific = False
        candidates = [*value.strings]
        if combined and combined not in candidates:
            candidates.append(combined)
        for text in candidates:
            normalized = normalized_identifier_text(text)
            target_tables = {table for table in TARGET_TABLES if table in normalized}
            table_statement = bool(
                re.search(r"\b(?:create|alter|drop)\s+table\b", normalized)
            )
            index_statement = bool(
                re.search(
                    r"\b(?:create\s+(?:unique\s+)?index|drop\s+index)\b",
                    normalized,
                )
            )
            trigger_statement = bool(
                re.search(
                    r"\b(?:create|drop)\s+(?:(?:temp|temporary)\s+)?trigger\b",
                    normalized,
                )
            )
            read_statement = bool(
                sink and re.search(r"\b(?:select|with)\b", normalized)
            )
            dml_statement = bool(
                sink
                and re.search(
                    r"\b(?:"
                    r"insert(?:\s+or\s+(?:rollback|abort|replace|fail|ignore))?\s+into"
                    r"|update(?:\s+or\s+(?:rollback|abort|replace|fail|ignore))?"
                    r"|delete\s+from"
                    r"|replace\s+into"
                    r")\b",
                    normalized,
                )
            )

            if table_statement and target_tables:
                found_specific = True
                self.created_tables.update(target_tables)
                self.add("forbidden_vendor_schema_table", node, symbol)
            if index_statement and (
                any(index in normalized for index in TARGET_INDEXES)
                or any(
                    re.search(rf"\bon\s+(?:main\.)?{re.escape(table)}\b", normalized)
                    for table in TARGET_TABLES
                )
                or any(autoindex in normalized for autoindex in TARGET_AUTOINDEXES)
            ):
                found_specific = True
                self.add("forbidden_vendor_schema_index", node, symbol)
            if trigger_statement and target_tables:
                found_specific = True
                self.add("forbidden_vendor_schema_trigger", node, symbol)
            if any(autoindex in normalized for autoindex in TARGET_AUTOINDEXES):
                found_specific = True
                self.add("forbidden_vendor_schema_index", node, symbol)
            if "savepoint" in normalized and target_tables:
                found_specific = True
                self.add("forbidden_vendor_schema_migration", node, symbol)
            if target_tables and any(
                token in normalized
                for token in (
                    "pragma",
                    "sqlite_schema",
                    "sqlite_master",
                    "table_info",
                    "table_xinfo",
                    "index_list",
                    "index_xinfo",
                    "foreign_key_list",
                )
            ):
                found_specific = True
                self.add("forbidden_vendor_schema_migration", node, symbol)
            if target_tables and dml_statement:
                found_specific = True
                self.add("forbidden_vendor_schema_dml", node, symbol)
            elif target_tables and read_statement:
                found_specific = True
                self.add("forbidden_vendor_schema_consumer", node, symbol)

        if sink == "executescript" and (
            found_specific or has_schema_verb(combined)
        ):
            self.add("forbidden_vendor_schema_executescript", node, symbol)
        if value.dynamic and (found_specific or has_schema_verb(combined)):
            self.add("forbidden_vendor_schema_dynamic_sql", node, symbol)
        if sink and not found_specific and (
            value.dynamic or any(word in combined for word in MIGRATION_WORDS)
        ):
            self.add("unresolved_vendor_schema_capability", node, symbol)

    def _classify_symbol(self, node: ast.AST, symbol: str) -> None:
        structural_node: ast.AST = node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            structural_node = ast.Tuple(
                elts=[*node.decorator_list, *node.args.defaults],
                ctx=ast.Load(),
            )
        elif isinstance(node, ast.ClassDef):
            structural_node = ast.Tuple(
                elts=[*node.decorator_list, *node.bases],
                ctx=ast.Load(),
            )
        elif isinstance(node, ast.Call):
            structural_node = node.func
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            structural_node = ast.Tuple(elts=[], ctx=ast.Load())
        evidence = normalized_identifier_text(
            f"{symbol} {node_structural_evidence(structural_node)}"
        )
        evidence_words = words(evidence)
        target_context = has_target(evidence) or (
            "vendor" in evidence_words
            and bool(
                {
                    "organization",
                    "organizations",
                    "membership",
                    "memberships",
                    "assignment",
                    "assignments",
                    "binding",
                    "bindings",
                }
                & evidence_words
            )
        )
        if not target_context:
            return

        if evidence_words & MIGRATION_WORDS:
            self.add("forbidden_vendor_schema_migration", node, symbol)
        if evidence_words & BACKFILL_WORDS:
            self.add("forbidden_vendor_schema_backfill", node, symbol)
        if evidence_words & AUTHORITY_WORDS:
            self.add("forbidden_vendor_authority_switch", node, symbol)
        if evidence_words & RELATIONSHIP_WORDS and evidence_words & CONSUMER_WORDS:
            self.add("forbidden_vendor_relationship_mutation", node, symbol)
        elif evidence_words & CONSUMER_WORDS:
            self.add("forbidden_vendor_schema_consumer", node, symbol)
        if evidence_words & EXEMPTION_WORDS:
            self.add("unresolved_vendor_schema_capability", node, symbol)

    @staticmethod
    def _merge_scope_union(
        scope: dict[str, Value],
        branches: list[dict[str, Value]],
    ) -> None:
        for name in sorted(
            set(scope).union(*(set(branch) for branch in branches))
        ):
            values = [
                branch.get(name, scope.get(name, Value(dynamic=True)))
                for branch in branches
            ]
            if not values:
                continue
            scope[name] = merge_values(
                *values,
                dynamic=len(set(values)) > 1 or any(
                    value.dynamic for value in values
                ),
            )

    def _scan_block(
        self,
        body: list[ast.stmt],
        scopes: list[dict[str, Value]],
        owner: str,
    ) -> None:
        scope = scopes[-1]
        for node in body:
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                value_node = node.value
                value = resolve_value(
                    value_node, scopes, self.helper_returns
                )
                targets: list[ast.AST]
                if isinstance(node, ast.Assign):
                    targets = list(node.targets)
                else:
                    targets = [node.target]
                for target in targets:
                    self._record_assignment(target, value, scope)
                    target_name = dotted_name(target)
                    if owner in self.class_names and isinstance(target, ast.Name):
                        self.module_scope[f"{owner}.{target_name}"] = value
                        scope[f"{owner}.{target_name}"] = value
                        scope[f"self.{target_name}"] = value
                        scope[f"cls.{target_name}"] = value
                    self._classify_symbol(node, target_name)
                    if (
                        target_name.rsplit(".", 1)[-1] == "__tablename__"
                        and has_target(value.evidence)
                    ):
                        self.add(
                            "forbidden_vendor_schema_backend",
                            node,
                            target_name,
                        )
                    if (
                        isinstance(value_node, ast.Call)
                        and isinstance(target, ast.Name)
                    ):
                        constructor = dotted_name(value_node.func)
                        mapped_constructor = self.import_aliases.get(
                            constructor,
                            constructor,
                        )
                        constructor_short = mapped_constructor.rsplit(".", 1)[-1]
                        if constructor_short in self.class_names:
                            self.instance_types[target_name] = (
                                f"{self.module_name}.{constructor_short}"
                            )
                        elif (
                            self.context is not None
                            and any(
                                key.startswith(f"{mapped_constructor}.")
                                for key in self.context.callables
                            )
                        ):
                            self.instance_types[target_name] = mapped_constructor
                if not isinstance(value_node, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
                    self._classify_sql(node, value, None, owner)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_owner = (
                    f"{owner}.{node.name}"
                    if owner
                    else node.name
                )
                self._classify_symbol(node, function_owner)
                local: dict[str, Value] = {}
                if owner in self.class_names:
                    for key, class_value in self.module_scope.items():
                        prefix = f"{owner}."
                        if key.startswith(prefix):
                            attribute = key[len(prefix):]
                            local[f"self.{attribute}"] = class_value
                            local[f"cls.{attribute}"] = class_value
                            local[key] = class_value
                self._scan_block(
                    node.body,
                    [*scopes, local],
                    function_owner,
                )
            elif isinstance(node, ast.ClassDef):
                class_owner = f"{owner}.{node.name}" if owner else node.name
                self._classify_symbol(node, class_owner)
                self._scan_block(node.body, [*scopes, {}], class_owner)
            elif isinstance(node, ast.Expr):
                if isinstance(node.value, ast.Call):
                    self._scan_call(node.value, scopes, owner)
            elif isinstance(node, ast.If):
                body_scope = dict(scope)
                else_scope = dict(scope)
                self._scan_block(
                    node.body,
                    [*scopes[:-1], body_scope],
                    owner,
                )
                self._scan_block(
                    node.orelse,
                    [*scopes[:-1], else_scope],
                    owner,
                )
                self._merge_scope_union(scope, [body_scope, else_scope])
            elif isinstance(node, (ast.While, ast.For, ast.AsyncFor)):
                branch_scope = dict(scope)
                self._scan_block(
                    node.body,
                    [*scopes[:-1], branch_scope],
                    owner,
                )
                self._merge_scope_union(scope, [dict(scope), branch_scope])
                if node.orelse:
                    else_scope = dict(scope)
                    self._scan_block(
                        node.orelse,
                        [*scopes[:-1], else_scope],
                        owner,
                    )
                    self._merge_scope_union(scope, [dict(scope), else_scope])
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                branch_scope = dict(scope)
                self._scan_block(
                    node.body,
                    [*scopes[:-1], branch_scope],
                    owner,
                )
                self._merge_scope_union(scope, [dict(scope), branch_scope])
            elif isinstance(node, ast.Try):
                branches: list[dict[str, Value]] = []
                body_scope = dict(scope)
                self._scan_block(
                    node.body,
                    [*scopes[:-1], body_scope],
                    owner,
                )
                branches.append(body_scope)
                for handler in node.handlers:
                    handler_scope = dict(scope)
                    self._scan_block(
                        handler.body,
                        [*scopes[:-1], handler_scope],
                        owner,
                    )
                    branches.append(handler_scope)
                if node.orelse:
                    else_scope = dict(body_scope)
                    self._scan_block(
                        node.orelse,
                        [*scopes[:-1], else_scope],
                        owner,
                    )
                    branches.append(else_scope)
                self._merge_scope_union(scope, branches)
                self._scan_block(node.finalbody, scopes, owner)
            elif isinstance(node, ast.Match):
                branches = [dict(scope)]
                for case in node.cases:
                    case_scope = dict(scope)
                    self._scan_block(
                        case.body,
                        [*scopes[:-1], case_scope],
                        owner,
                    )
                    branches.append(case_scope)
                self._merge_scope_union(scope, branches)

            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.Call) and not (
                    isinstance(node, ast.Expr) and child is node.value
                ):
                    self._scan_call(child, scopes, owner)

    def _repository_callable_candidates(
        self,
        node: ast.Call,
        raw_callable_names: set[str],
        owner: str,
    ) -> tuple[list[tuple[CallableInfo, bool | None]], bool]:
        if self.context is None:
            return [], False
        names: set[tuple[str, bool | None]] = set()
        receiver_specific: set[tuple[str, bool | None]] = set()
        imported_reference = False
        owner_class = owner.split(".", 1)[0] if owner else None

        def add_name(raw_name: str, bound: bool | None = False) -> None:
            nonlocal imported_reference
            if not raw_name:
                return
            parts = raw_name.split(".")
            first = parts[0]
            if raw_name in self.import_aliases:
                imported_reference = True
                names.add((self.import_aliases[raw_name], bound))
                return
            if first in self.import_aliases:
                imported_reference = True
                mapped = self.import_aliases[first]
                suffix = ".".join(parts[1:])
                names.add((f"{mapped}.{suffix}" if suffix else mapped, bound))
                return
            if raw_name.startswith(("self.", "cls.")) and owner_class:
                suffix = raw_name.split(".", 1)[1]
                names.add((f"{self.module_name}.{owner_class}.{suffix}", True))
                return
            if first in self.instance_types and len(parts) > 1:
                suffix = ".".join(parts[1:])
                receiver_specific.add(
                    (
                        f"{self.instance_types[first]}.{suffix}",
                        True,
                    )
                )
                return
            if first in self.class_names and len(parts) > 1:
                names.add((f"{self.module_name}.{raw_name}", False))
                return
            if "." not in raw_name:
                if owner:
                    names.add((f"{self.module_name}.{owner}.{raw_name}", False))
                names.add((f"{self.module_name}.{raw_name}", False))
            else:
                names.add((raw_name, bound))
                names.add((f"{self.module_name}.{raw_name}", bound))

        for raw_name in raw_callable_names:
            add_name(raw_name)

        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr
            receiver = node.func.value
            if isinstance(receiver, ast.Call):
                constructor = dotted_name(receiver.func)
                mapped_constructor = self.import_aliases.get(
                    constructor,
                    constructor,
                )
                constructor_short = mapped_constructor.rsplit(".", 1)[-1]
                if constructor_short in self.class_names:
                    receiver_specific.add(
                        (
                            f"{self.module_name}.{constructor_short}.{method_name}",
                            True,
                        )
                    )
                elif "." in mapped_constructor:
                    imported_reference = True
                    receiver_specific.add(
                        (f"{mapped_constructor}.{method_name}", True)
                    )
            elif isinstance(receiver, ast.Name):
                receiver_name = receiver.id
                if receiver_name in self.instance_types:
                    receiver_specific.add(
                        (
                            f"{self.module_name}.{self.instance_types[receiver_name]}.{method_name}",
                            True,
                        )
                    )
                elif receiver_name in self.class_names:
                    receiver_specific.add(
                        (
                            f"{self.module_name}.{receiver_name}.{method_name}",
                            False,
                        )
                    )

        if receiver_specific:
            names = receiver_specific

        resolved: list[tuple[CallableInfo, bool | None]] = []
        for qualified, bound_hint in sorted(names):
            info = self.context.callables.get(qualified)
            if info is None:
                continue
            bound = bound_hint
            if info.binding_kind == "static":
                bound = False
            elif info.binding_kind == "class" and info.owner_class is not None:
                bound = True
            resolved.append((info, bound))
        return resolved, imported_reference

    def _scan_bound_callable(
        self,
        info: CallableInfo,
        positional_values: list[Value],
        keyword_values: list[tuple[str | None, Value]],
        bound: bool | None,
        unresolved_positional_values: list[Value] | None = None,
    ) -> None:
        if self.context is None:
            return
        boundary_values = [
            *positional_values,
            *(value for _, value in keyword_values),
            *(unresolved_positional_values or ()),
        ]
        if (
            info.qualified_name in self.context.active_calls
            or len(self.context.active_calls) >= 4
        ):
            if any(has_target(value.evidence) for value in boundary_values):
                self.add(
                    "unresolved_vendor_schema_capability",
                    info.node,
                    info.qualified_name,
                )
            return
        self._collect_helpers()
        positional_parameters = [
            *info.node.args.posonlyargs,
            *info.node.args.args,
        ]
        skip = 0
        if info.binding_kind in {"instance", "class"}:
            if bound is None:
                evidence = merge_values(*positional_values)
                if has_target(evidence.evidence):
                    self.add(
                        "unresolved_vendor_schema_capability",
                        info.node,
                        info.qualified_name,
                    )
                return
            if bound:
                skip = 1
        effective_parameters = positional_parameters[skip:]
        accepted_parameters = {
            parameter.arg
            for parameter in (
                *effective_parameters,
                *info.node.args.kwonlyargs,
            )
        }
        call_has_target = any(
            has_target(value.evidence)
            for value in boundary_values
        )
        bindings: dict[str, Value] = {}
        for parameter, argument in zip(effective_parameters, positional_values):
            bindings[parameter.arg] = argument
        unresolved_call_values: list[Value] = []
        unresolved_shape = bool(unresolved_positional_values)
        unresolved_call_values.extend(unresolved_positional_values or ())
        for keyword_name, keyword_value in keyword_values:
            if keyword_name is None:
                if info.node.args.kwarg is not None:
                    bindings[info.node.args.kwarg.arg] = merge_values(
                        bindings.get(info.node.args.kwarg.arg, Value()),
                        keyword_value,
                        dynamic=True,
                    )
                else:
                    unresolved_call_values.append(keyword_value)
                    unresolved_shape = True
            elif keyword_name in accepted_parameters:
                bindings[keyword_name] = keyword_value
            elif info.node.args.kwarg is not None:
                bindings[info.node.args.kwarg.arg] = merge_values(
                    bindings.get(info.node.args.kwarg.arg, Value()),
                    keyword_value,
                    dynamic=True,
                )
            else:
                unresolved_call_values.append(keyword_value)
                unresolved_shape = True
        extra_positional = positional_values[len(effective_parameters):]
        if extra_positional:
            if info.node.args.vararg:
                bindings[info.node.args.vararg.arg] = merge_values(
                    *extra_positional,
                    dynamic=True,
                )
            else:
                unresolved_call_values.extend(extra_positional)
                unresolved_shape = True

        positional_defaults = {
            parameter.arg: default
            for parameter, default in zip(
                positional_parameters[-len(info.node.args.defaults):],
                info.node.args.defaults,
            )
        } if info.node.args.defaults else {}
        keyword_defaults = {
            parameter.arg: default
            for parameter, default in zip(
                info.node.args.kwonlyargs,
                info.node.args.kw_defaults,
            )
            if default is not None
        }
        for parameter in (*effective_parameters, *info.node.args.kwonlyargs):
            if parameter.arg in bindings:
                continue
            default = positional_defaults.get(
                parameter.arg,
                keyword_defaults.get(parameter.arg),
            )
            if default is not None:
                bindings[parameter.arg] = resolve_value(
                    default,
                    [self.module_scope],
                    self.helper_returns,
                )
            else:
                bindings[parameter.arg] = Value(dynamic=True)
                unresolved_shape = True

        if (
            any(has_target(value.evidence) for value in unresolved_call_values)
            or (unresolved_shape and call_has_target)
        ):
            self.add(
                "unresolved_vendor_schema_capability",
                info.node,
                info.qualified_name,
            )
        if info.owner_class:
            prefix = f"{info.owner_class}."
            for key, class_value in self.module_scope.items():
                if key.startswith(prefix):
                    attribute = key[len(prefix):]
                    bindings[f"self.{attribute}"] = class_value
                    bindings[f"cls.{attribute}"] = class_value
                    bindings[key] = class_value
        self.context.active_calls.append(info.qualified_name)
        try:
            owner = ".".join(
                part
                for part in (
                    info.owner_class,
                    info.node.name,
                )
                if part
            )
            self._scan_block(
                info.node.body,
                [self.module_scope, bindings],
                owner,
            )
        finally:
            self.context.active_calls.pop()

    def _scan_call(
        self,
        node: ast.Call,
        scopes: list[dict[str, Value]],
        owner: str,
    ) -> None:
        call_name = dotted_name(node.func)
        callable_value = resolve_value(node.func, scopes, self.helper_returns)
        raw_callable_names = {
            call_name,
            *callable_value.strings,
        }
        raw_callable_names.discard("")
        callable_names = {
            normalized_identifier_text(item)
            for item in raw_callable_names
        }
        callable_names.discard("")
        short_names = {
            name.rsplit(".", 1)[-1]
            for name in callable_names
        }
        short_name = call_name.rsplit(".", 1)[-1]
        self._classify_symbol(node, f"{owner}.{call_name}".strip("."))
        positional_values: list[Value] = []
        unresolved_positional_values: list[Value] = []
        for argument in node.args:
            if isinstance(argument, ast.Starred):
                expanded = resolve_value(
                    argument.value,
                    scopes,
                    self.helper_returns,
                )
                if expanded.sequence is not None and not expanded.dynamic:
                    positional_values.extend(
                        Value((item,))
                        for item in expanded.sequence
                    )
                else:
                    unresolved_positional_values.append(expanded)
                continue
            positional_values.append(
                resolve_value(argument, scopes, self.helper_returns)
            )
        keyword_values = [
            resolve_value(keyword.value, scopes, self.helper_returns)
            for keyword in node.keywords
        ]
        argument_values = [*positional_values, *keyword_values]
        aggregate = merge_values(
            *argument_values,
            *unresolved_positional_values,
            dynamic=(
                bool(unresolved_positional_values)
                or any(value.dynamic for value in argument_values)
            ),
        )

        sink_names = short_names & SQL_SINKS
        if sink_names:
            sink = sorted(sink_names)[0]
            self._classify_sql(node, aggregate, sink, owner)

        call_words = words(" ".join(callable_names))
        if has_target(aggregate.evidence):
            if (
                {"table", "create_table", "create_index", "drop_table", "drop_index"}
                & short_names
                or "metadata" in call_words
                or "model" in call_words
                or "declarative" in call_words
                or {
                    "alembic",
                    "backend",
                    "postgres",
                    "postgresql",
                    "psycopg",
                    "sqlalchemy",
                }
                & call_words
            ):
                self.add(
                    "forbidden_vendor_schema_backend",
                    node,
                    call_name or sorted(callable_names)[0],
                )
            if {"create_table", "drop_table"} & short_names:
                self.created_tables.update(
                    table
                    for table in TARGET_TABLES
                    if table in normalized_identifier_text(aggregate.evidence)
                )
                self.add(
                    "forbidden_vendor_schema_table",
                    node,
                    call_name or sorted(callable_names)[0],
                )
            if {"create_index", "drop_index"} & short_names:
                self.add(
                    "forbidden_vendor_schema_index",
                    node,
                    call_name or sorted(callable_names)[0],
                )

        repository_candidates, imported_reference = (
            self._repository_callable_candidates(
                node,
                raw_callable_names,
                owner,
            )
        )
        for info, bound in repository_candidates:
            if self.context is None:
                continue
            callee = self.context.analyzers.get(info.module_name)
            if callee is not None:
                callee._scan_bound_callable(
                    info,
                    positional_values,
                    [
                        (keyword.arg, value)
                        for keyword, value in zip(
                            node.keywords,
                            keyword_values,
                        )
                    ],
                    bound,
                    unresolved_positional_values,
                )
        if (
            has_target(aggregate.evidence)
            and not repository_candidates
            and not sink_names
        ):
            self.add(
                "unresolved_vendor_schema_capability",
                node,
                call_name or "unresolved_callable",
            )

    def _collect_helpers(self) -> None:
        if self.prepared:
            return
        for node in self.tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = resolve_value(
                    node.value, [self.module_scope], self.helper_returns
                )
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    self._record_assignment(target, value, self.module_scope)
            elif isinstance(node, ast.ClassDef):
                class_scope: dict[str, Value] = {}
                for statement in node.body:
                    if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                        value = resolve_value(
                            statement.value,
                            [self.module_scope, class_scope],
                            self.helper_returns,
                        )
                        targets = (
                            statement.targets
                            if isinstance(statement, ast.Assign)
                            else [statement.target]
                        )
                        for target in targets:
                            if isinstance(target, ast.Name):
                                class_scope[target.id] = value
                                self.module_scope[
                                    f"{node.name}.{target.id}"
                                ] = value

        for _ in range(4):
            inherited_changed = self._propagate_inherited_values()
            changed = False
            for node in self.tree.body:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                local = dict(self.module_scope)
                for statement in node.body:
                    if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                        value = resolve_value(
                            statement.value,
                            [self.module_scope, local],
                            self.helper_returns,
                        )
                        targets = (
                            statement.targets
                            if isinstance(statement, ast.Assign)
                            else [statement.target]
                        )
                        for target in targets:
                            self._record_assignment(target, value, local)
                returns = [
                    resolve_value(
                        returned.value,
                        [self.module_scope, local],
                        self.helper_returns,
                    )
                    for returned in ast.walk(node)
                    if isinstance(returned, ast.Return)
                ]
                if returns:
                    value = merge_values(*returns)
                    if self.helper_returns.get(node.name) != value:
                        self.helper_returns[node.name] = value
                        changed = True
            if not changed:
                if not inherited_changed:
                    break
        self.prepared = True
        self.exported_scope_keys.update(self.module_scope)

    def analyze(self) -> list[Issue]:
        self._collect_helpers()
        self._scan_block(self.tree.body, [self.module_scope], "")

        if 0 < len(self.created_tables) < len(TARGET_TABLES):
            self.issues.append(
                Issue(
                    "partial_vendor_schema_implementation",
                    self.path,
                    1,
                    ",".join(sorted(self.created_tables)),
                )
            )

        if has_target(self.module_evidence):
            if self.import_roots & BACKEND_ROOTS:
                self.issues.append(
                    Issue(
                        "forbidden_vendor_schema_backend",
                        self.path,
                        1,
                        ",".join(sorted(self.import_roots & BACKEND_ROOTS)),
                    )
                )
            if "database_url" in self.module_evidence or (
                "app_db_path" in self.module_evidence
                and any(word in self.module_evidence for word in MIGRATION_WORDS)
            ):
                self.issues.append(
                    Issue(
                        "forbidden_vendor_schema_environment_access",
                        self.path,
                        1,
                        "environment",
                    )
                )
            if (
                "production" in self.module_evidence
                and any(word in self.module_evidence for word in MIGRATION_WORDS)
            ):
                self.issues.append(
                    Issue(
                        "forbidden_vendor_schema_backend",
                        self.path,
                        1,
                        "production",
                    )
                )

        return sorted(set(self.issues))


def read_source(path: Path, relative: Path) -> tuple[ast.Module | None, list[Issue]]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None, [Issue("source_read_error", relative.as_posix(), 1, "-")]
    try:
        return ast.parse(source, filename=relative.as_posix()), []
    except SyntaxError as exc:
        return None, [
            Issue(
                "source_parse_error",
                relative.as_posix(),
                exc.lineno or 1,
                "-",
            )
        ]


def check_policy_document(
    root: Path,
    relative: Path,
    approved_blob: str,
    approved_sha256: str | None,
    markers: tuple[str, ...],
) -> list[Issue]:
    path = root / relative
    if not path.is_file():
        return [
            Issue(
                "vendor_schema_policy_document_missing",
                relative.as_posix(),
                1,
                "-",
            )
        ]
    try:
        data = path.read_bytes()
        text = data.decode("utf-8")
    except (OSError, UnicodeError):
        return [
            Issue(
                "vendor_schema_policy_drift",
                relative.as_posix(),
                1,
                "unreadable",
            )
        ]

    issues: list[Issue] = []
    if git_blob_id(data) != approved_blob or (
        approved_sha256
        and hashlib.sha256(data).hexdigest().upper() != approved_sha256
    ):
        issues.append(
            Issue("vendor_schema_policy_drift", relative.as_posix(), 1, "fingerprint")
        )
    for marker in markers:
        if text.count(marker) != 1:
            issues.append(
                Issue(
                    "vendor_schema_policy_marker_missing",
                    relative.as_posix(),
                    1,
                    marker,
                )
            )
    if relative == SCHEMA_POLICY_PATH:
        if sum(
            1
            for line in text.splitlines()
            if re.match(r"^CREATE TABLE\s+", line)
        ) != 4:
            issues.append(
                Issue(
                    "vendor_schema_policy_drift",
                    relative.as_posix(),
                    1,
                    "four_table_projection",
                )
            )
        if sum(
            1
            for line in text.splitlines()
            if re.match(r"^CREATE (?:UNIQUE )?INDEX\s+", line)
        ) != 15:
            issues.append(
                Issue(
                    "vendor_schema_policy_drift",
                    relative.as_posix(),
                    1,
                    "fifteen_index_projection",
                )
            )
        for token in TARGET_TABLES + TARGET_INDEXES:
            if token not in text:
                issues.append(
                    Issue(
                        "vendor_schema_policy_marker_missing",
                        relative.as_posix(),
                        1,
                        token,
                    )
                )
    return issues


def runtime_sources(root: Path) -> list[Path]:
    sources: set[Path] = set()
    excluded_top_levels = set(EXCLUDED_TOP_LEVEL_RUNTIME_NAMES)
    for path in root.rglob("*.py"):
        relative = path.relative_to(root)
        if not relative.parts:
            continue
        if relative.parts[0] in excluded_top_levels:
            continue
        if relative == CHECKER_PATH:
            continue
        sources.add(relative)
    return sorted(sources, key=lambda item: item.as_posix())


def callable_binding_kind(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    owner_class: str | None,
) -> str:
    if owner_class is None:
        return "function"
    decorators = {
        dotted_name(decorator).rsplit(".", 1)[-1]
        for decorator in node.decorator_list
    }
    if "staticmethod" in decorators:
        return "static"
    if "classmethod" in decorators:
        return "class"
    return "instance"


def collect_callable_infos(
    relative: Path,
    tree: ast.Module,
) -> dict[str, CallableInfo]:
    module_name = python_module_name(relative)
    collected: dict[str, CallableInfo] = {}

    def walk(
        statements: list[ast.stmt],
        prefix: tuple[str, ...] = (),
        owner_class: str | None = None,
    ) -> None:
        for statement in statements:
            if isinstance(statement, ast.ClassDef):
                walk(
                    statement.body,
                    (*prefix, statement.name),
                    statement.name,
                )
            elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualified_parts = (module_name, *prefix, statement.name)
                qualified = ".".join(part for part in qualified_parts if part)
                immediate_class = (
                    owner_class
                    if owner_class is not None and prefix[-1:] == (owner_class,)
                    else None
                )
                collected[qualified] = CallableInfo(
                    qualified,
                    module_name,
                    relative,
                    statement,
                    immediate_class,
                    callable_binding_kind(statement, immediate_class),
                )
                walk(
                    statement.body,
                    (*prefix, statement.name),
                    None,
                )
            elif isinstance(statement, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                walk(statement.body, prefix, owner_class)
                walk(statement.orelse, prefix, owner_class)
            elif isinstance(statement, ast.Try):
                walk(statement.body, prefix, owner_class)
                for handler in statement.handlers:
                    walk(handler.body, prefix, owner_class)
                walk(statement.orelse, prefix, owner_class)
                walk(statement.finalbody, prefix, owner_class)
            elif isinstance(statement, (ast.With, ast.AsyncWith)):
                walk(statement.body, prefix, owner_class)
            elif isinstance(statement, ast.Match):
                for case in statement.cases:
                    walk(case.body, prefix, owner_class)

    walk(tree.body)
    return collected


def analyze_repository(root: Path) -> list[Issue]:
    issues = check_policy_document(
        root,
        VENDOR_POLICY_PATH,
        APPROVED_VENDOR_POLICY_BLOB,
        None,
        VENDOR_POLICY_MARKERS,
    )
    issues.extend(
        check_policy_document(
            root,
            SCHEMA_POLICY_PATH,
            APPROVED_SCHEMA_POLICY_BLOB,
            APPROVED_SCHEMA_POLICY_SHA256,
            SCHEMA_POLICY_MARKERS,
        )
    )
    for relative in FIXED_RUNTIME_FILES:
        if not (root / relative).is_file():
            issues.append(
                Issue("source_read_error", relative.as_posix(), 1, "missing")
            )
    parsed: dict[Path, ast.Module] = {}
    for relative in runtime_sources(root):
        tree, source_issues = read_source(root / relative, relative)
        issues.extend(source_issues)
        if tree is not None:
            parsed[relative] = tree

    callables: dict[str, CallableInfo] = {}
    for relative, tree in parsed.items():
        callables.update(collect_callable_infos(relative, tree))
    context = RepositoryContext(callables, {}, {}, [])
    for relative, tree in parsed.items():
        analyzer = PythonSourceAnalyzer(relative, tree, context)
        context.analyzers[analyzer.module_name] = analyzer
    for module_name, analyzer in context.analyzers.items():
        analyzer._collect_helpers()
        context.module_scopes[module_name] = analyzer.module_scope
    for _ in range(4):
        changed = False
        for analyzer in context.analyzers.values():
            changed = analyzer._propagate_imported_values() or changed
        for analyzer in context.analyzers.values():
            changed = analyzer._propagate_inherited_values() or changed
        if not changed:
            break
    for analyzer in context.analyzers.values():
        analyzer.analyze()
    for analyzer in context.analyzers.values():
        issues.extend(analyzer.issues)
    return sorted(set(issues))


def render_normal(issues: list[Issue]) -> tuple[int, str]:
    lines = [
        "vendor_schema_readiness_scope: static_source_and_frozen_policy_only",
        f"issues_count: {len(issues)}",
        "database_access: 0",
        "app_imports: 0",
    ]
    for issue in sorted(issues):
        lines.append(
            f"issue: {issue.code} path={issue.path} line={issue.line} symbol={issue.symbol}"
        )
    if not issues:
        lines.append(PASS_MARKER)
    return (0 if not issues else 1), "\n".join(lines) + "\n"


def write_base_tree(root: Path) -> None:
    for relative in (VENDOR_POLICY_PATH, SCHEMA_POLICY_PATH):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT_DIR / relative, destination)
    for relative in FIXED_RUNTIME_FILES:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("", encoding="utf-8", newline="\n")
    checker = root / CHECKER_PATH
    checker.parent.mkdir(parents=True, exist_ok=True)
    checker.write_text(
        "TARGETS = ('vendor_organizations', 'sheet_vendor_bindings')\n",
        encoding="utf-8",
        newline="\n",
    )


def add_source(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8", newline="\n")


def positive_cases() -> list[tuple[str, str, str]]:
    return [
        ("clean_baseline", "services/clean.py", "VALUE = 1\n"),
        (
            "comments_target_names",
            "services/comments.py",
            "# CREATE TABLE vendor_organizations (vendor_id TEXT)\nVALUE = 1\n",
        ),
        (
            "ordinary_target_text",
            "services/text.py",
            'MESSAGE = "vendor_organizations is discussed in a future design"\n',
        ),
        (
            "unrelated_sqlite",
            "services/sqlite.py",
            'SQL = "CREATE TABLE audit_events (id INTEGER PRIMARY KEY)"\n'
            'INDEX = "CREATE INDEX idx_audit_events_created ON audit_events(created_at)"\n',
        ),
        (
            "legacy_vendor_accounts",
            "services/legacy.py",
            'SQL = "CREATE TABLE vendor_accounts (id INTEGER PRIMARY KEY)"\n',
        ),
        (
            "ordinary_vendor_name",
            "services/vendor_name.py",
            "def read_vendor_name(row):\n    return row['vendor_name']\n",
        ),
        (
            "unrelated_postgresql",
            "services/postgres.py",
            "import psycopg\n\ndef load_audit_events():\n    return []\n",
        ),
        (
            "unrelated_executescript",
            "services/script.py",
            'def setup(conn):\n    conn.executescript("CREATE TABLE audit_log (id INTEGER)")\n',
        ),
        (
            "unrelated_report_plan",
            "services/report.py",
            "def create_business_report_plan():\n    return {'status': 'draft'}\n",
        ),
        (
            "tests_excluded",
            "tests/vendor_fixture.py",
            'SQL = "CREATE TABLE vendor_organizations (vendor_id TEXT)"\n',
        ),
        (
            "docs_excluded",
            "docs/synthetic.py",
            'SQL = "CREATE TABLE vendor_organizations (vendor_id TEXT)"\n',
        ),
        (
            "unrelated_select_dml",
            "routes/audit_sql.py",
            "def work(conn):\n"
            '    conn.execute("SELECT * FROM audit_events")\n'
            '    conn.execute("INSERT INTO audit_events(id) VALUES (?)", (1,))\n'
            '    conn.execute("UPDATE audit_events SET id = ?", (2,))\n'
            '    conn.execute("DELETE FROM audit_events")\n',
        ),
        (
            "unrelated_orm_model",
            "package/audit_model.py",
            "class AuditEvent(db.Model):\n"
            '    __tablename__ = "audit_events"\n',
        ),
        (
            "unrelated_root_module",
            "root_audit_helper.py",
            "def read_audit_event():\n    return None\n",
        ),
        (
            "unrelated_temporary_trigger",
            "package/audit_trigger.py",
            'SQL = "CREATE TEMPORARY TRIGGER audit_guard AFTER INSERT ON audit_events BEGIN SELECT 1; END"\n',
        ),
        (
            "generic_helper_without_vendor_target",
            "package/sql_helper.py",
            "def execute_statement(conn, statement):\n"
            "    return conn.execute(statement)\n",
        ),
        (
            "unrelated_control_flow_union",
            "package/audit_flow.py",
            "def read(conn, flag, manager, value):\n"
            '    target = "audit_events"\n'
            "    try:\n"
            "        if flag:\n"
            '            target = "audit_log"\n'
            "    except LookupError:\n"
            '        target = "audit_failures"\n'
            "    finally:\n"
            "        target = target or 'audit_events'\n"
            "    with manager:\n"
            "        match value:\n"
            "            case 1:\n"
            '                target = "audit_one"\n'
            "            case _:\n"
            '                target = "audit_other"\n'
            '    conn.execute("SELECT * FROM " + target)\n',
        ),
        (
            "unrelated_bound_methods",
            "package/audit_builder.py",
            "class AuditBuilder:\n"
            '    TABLE = "audit_events"\n'
            "    def read(self, conn):\n"
            '        conn.execute("SELECT * FROM " + self.TABLE)\n'
            "    @classmethod\n"
            "    def remove(cls, conn):\n"
            '        conn.execute("DELETE FROM " + cls.TABLE)\n'
            "    @staticmethod\n"
            "    def create(conn, table):\n"
            '        conn.execute("CREATE TABLE " + table + " (id INTEGER)")\n'
            "AuditBuilder().read(None)\n"
            "AuditBuilder.remove(None)\n"
            'AuditBuilder.create(None, "audit_archive")\n',
        ),
        (
            "unrelated_boolop",
            "package/audit_boolop.py",
            "def read(conn, selected, fallback):\n"
            '    table = selected and "audit_events" or fallback\n'
            '    conn.execute("SELECT * FROM " + table)\n',
        ),
    ]


def negative_source_cases() -> list[tuple[str, str, str, str]]:
    cases: list[tuple[str, str, str, str]] = []
    for table in TARGET_TABLES:
        cases.append(
            (
                f"create_{table}",
                "app.py",
                f'SQL = "CREATE TABLE {table} (id TEXT)"\n',
                "forbidden_vendor_schema_table",
            )
        )
    for index, table in (
        (TARGET_INDEXES[0], TARGET_TABLES[0]),
        (TARGET_INDEXES[1], TARGET_TABLES[1]),
        (TARGET_INDEXES[6], TARGET_TABLES[2]),
        (TARGET_INDEXES[10], TARGET_TABLES[3]),
    ):
        cases.append(
            (
                f"index_{index}",
                "app.py",
                f'SQL = "CREATE INDEX {index} ON {table}(id)"\n',
                "forbidden_vendor_schema_index",
            )
        )
    cases.extend(
        [
            (
                "partial_tables",
                "app.py",
                'SQL = "CREATE TABLE vendor_organizations (id TEXT)"\n',
                "partial_vendor_schema_implementation",
            ),
            (
                "arbitrary_index",
                "app.py",
                'SQL = "CREATE INDEX arbitrary_name ON vendor_organizations(vendor_id)"\n',
                "forbidden_vendor_schema_index",
            ),
            (
                "arbitrary_trigger",
                "app.py",
                'SQL = "CREATE TRIGGER arbitrary_name AFTER INSERT ON vendor_organizations BEGIN SELECT 1; END"\n',
                "forbidden_vendor_schema_trigger",
            ),
            (
                "temp_trigger",
                "app.py",
                'SQL = "CREATE TEMP TRIGGER arbitrary_name AFTER INSERT ON main.vendor_organizations BEGIN SELECT 1; END"\n',
                "forbidden_vendor_schema_trigger",
            ),
            (
                "quoted_qualified",
                "app.py",
                'SQL = \'CREATE TABLE main."vendor_organizations" (id TEXT)\'\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "alter_table",
                "app.py",
                'SQL = "ALTER TABLE vendor_organizations ADD COLUMN x TEXT"\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "drop_table",
                "app.py",
                'SQL = "DROP TABLE vendor_organizations"\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "assigned_execute",
                "app.py",
                'SQL = "CREATE TABLE vendor_organizations (id TEXT)"\n'
                "def apply(conn):\n    conn.execute(SQL)\n",
                "forbidden_vendor_schema_table",
            ),
            (
                "adjacent_literals",
                "app.py",
                'SQL = ("CREATE TABLE " "vendor_organizations" " (id TEXT)")\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "concatenated_execute",
                "app.py",
                'PREFIX = "CREATE TABLE "\nNAME = "vendor_organizations"\n'
                "def apply(conn):\n    conn.execute(PREFIX + NAME + ' (id TEXT)')\n",
                "forbidden_vendor_schema_dynamic_sql",
            ),
            (
                "percent_sql",
                "app.py",
                'NAME = "vendor_organizations"\n'
                'def apply(conn):\n    conn.execute("CREATE TABLE %s (id TEXT)" % NAME)\n',
                "forbidden_vendor_schema_dynamic_sql",
            ),
            (
                "format_sql",
                "app.py",
                'NAME = "vendor_organizations"\n'
                'def apply(conn):\n    conn.execute("CREATE TABLE {} (id TEXT)".format(NAME))\n',
                "forbidden_vendor_schema_dynamic_sql",
            ),
            (
                "fstring_sql",
                "app.py",
                'NAME = "vendor_organizations"\n'
                'def apply(conn):\n    conn.execute(f"CREATE TABLE {NAME} (id TEXT)")\n',
                "forbidden_vendor_schema_dynamic_sql",
            ),
            (
                "join_sql",
                "app.py",
                'PARTS = ["CREATE TABLE", "vendor_organizations", "(id TEXT)"]\n'
                'def apply(conn):\n    conn.execute(" ".join(PARTS))\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "helper_returned_sql",
                "app.py",
                'def statement():\n    return "CREATE TABLE vendor_organizations (id TEXT)"\n'
                "def apply(conn):\n    conn.execute(statement())\n",
                "forbidden_vendor_schema_table",
            ),
            (
                "cursor_alias",
                "app.py",
                'SQL = "CREATE TABLE vendor_organizations (id TEXT)"\n'
                "def apply(conn):\n    cursor_alias = conn.cursor()\n    cursor_alias.execute(SQL)\n",
                "forbidden_vendor_schema_table",
            ),
            (
                "unresolved_dynamic_sql",
                "app.py",
                'TARGET = "vendor_organizations"\n'
                "def apply(conn, prefix):\n    conn.execute(prefix + TARGET)\n",
                "unresolved_vendor_schema_capability",
            ),
            (
                "executemany",
                "app.py",
                'SQL = "CREATE TABLE vendor_organizations (id TEXT)"\n'
                "def apply(conn):\n    conn.executemany(SQL, [])\n",
                "forbidden_vendor_schema_table",
            ),
            (
                "executescript",
                "app.py",
                'def apply(conn):\n    conn.executescript("CREATE TABLE vendor_organizations (id TEXT)")\n',
                "forbidden_vendor_schema_executescript",
            ),
            (
                "migration_helper",
                "services/vendor_schema.py",
                "def migrate_vendor_organizations_schema(conn):\n    return conn\n",
                "forbidden_vendor_schema_migration",
            ),
            (
                "metadata_classifier",
                "services/vendor_schema.py",
                'SQL = "SELECT * FROM pragma_table_xinfo(\'vendor_organizations\')"\n',
                "forbidden_vendor_schema_migration",
            ),
            (
                "expected_projection",
                "services/vendor_schema.py",
                "VENDOR_ORGANIZATION_EXPECTED_TABLES = ('vendor_organizations',)\n",
                "forbidden_vendor_schema_migration",
            ),
            (
                "pk_autoindex_assumption",
                "services/vendor_schema.py",
                'EXPECTED = "sqlite_autoindex_vendor_organizations_1"\n',
                "forbidden_vendor_schema_index",
            ),
            (
                "savepoint_apply",
                "services/vendor_schema.py",
                'SQL = "SAVEPOINT vendor_organization_schema_migration"\n'
                "def apply_vendor_organizations_schema(conn):\n    conn.execute(SQL)\n",
                "forbidden_vendor_schema_migration",
            ),
            (
                "route_consumer",
                "services/vendor_routes.py",
                "def create_vendor_organization_route():\n    return None\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "api_consumer",
                "services/vendor_api.py",
                "def update_vendor_organization_api():\n    return None\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "form_consumer",
                "services/vendor_form.py",
                "def submit_vendor_organization_form():\n    return None\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "cli_consumer",
                "tools/vendor_cli.py",
                "def create_vendor_organization_cli():\n    return None\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "backfill",
                "services/vendor_backfill.py",
                "def backfill_legacy_vendor_organizations():\n    return None\n",
                "forbidden_vendor_schema_backfill",
            ),
            (
                "organization_consumer",
                "services/vendor_org.py",
                "def create_vendor_organization():\n    return None\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "membership_consumer",
                "services/vendor_member.py",
                "def create_vendor_organization_membership():\n    return None\n",
                "forbidden_vendor_relationship_mutation",
            ),
            (
                "assignment_consumer",
                "services/vendor_assignment.py",
                "def create_vendor_site_assignment():\n    return None\n",
                "forbidden_vendor_relationship_mutation",
            ),
            (
                "binding_consumer",
                "services/vendor_binding.py",
                "def create_sheet_vendor_binding():\n    return None\n",
                "forbidden_vendor_relationship_mutation",
            ),
            (
                "authority_switch",
                "services/vendor_authority.py",
                "def switch_vendor_organization_authority():\n    return None\n",
                "forbidden_vendor_authority_switch",
            ),
            (
                "database_url",
                "services/vendor_schema.py",
                'TARGET = "vendor_organizations"\nDATABASE_URL = "not-read"\n',
                "forbidden_vendor_schema_environment_access",
            ),
            (
                "postgres_projection",
                "services/vendor_schema.py",
                'import psycopg\nTARGET = "vendor_organizations"\n',
                "forbidden_vendor_schema_backend",
            ),
            (
                "orm_projection",
                "models.py",
                'import sqlalchemy\nTABLE = "vendor_organizations"\n',
                "forbidden_vendor_schema_backend",
            ),
            (
                "alembic_projection",
                "migrations/vendor.py",
                'import alembic\nTABLE = "vendor_organizations"\n',
                "forbidden_vendor_schema_backend",
            ),
            (
                "production_migration",
                "services/vendor_schema.py",
                'TARGET = "vendor_organizations"\n'
                "def production_schema_migration():\n    return TARGET\n",
                "forbidden_vendor_schema_backend",
            ),
            (
                "generic_allowlist",
                "tools/vendor_guard.py",
                "VENDOR_ORGANIZATION_SCHEMA_ALLOWLIST = ['vendor_organizations']\n",
                "unresolved_vendor_schema_capability",
            ),
            (
                "wildcard_exemption",
                "tools/vendor_guard.py",
                "VENDOR_ORGANIZATION_SCHEMA_WILDCARD = 'vendor_*'\n",
                "unresolved_vendor_schema_capability",
            ),
            (
                "whole_function_exemption",
                "tools/vendor_guard.py",
                "def ignore_vendor_organizations_function():\n    return True\n",
                "unresolved_vendor_schema_capability",
            ),
            (
                "comment_exemption",
                "tools/vendor_guard.py",
                "# vendor_schema_ignore\n"
                "def suppress_vendor_organizations_schema():\n    return True\n",
                "unresolved_vendor_schema_capability",
            ),
        ]
    )
    for name, sql, expected_code in (
        (
            "target_select",
            "SELECT * FROM vendor_organizations",
            "forbidden_vendor_schema_consumer",
        ),
        (
            "target_join",
            "SELECT a.id FROM audit_events a JOIN vendor_organizations v ON v.vendor_id = a.id",
            "forbidden_vendor_schema_consumer",
        ),
        (
            "target_cte",
            "WITH vendors AS (SELECT * FROM vendor_organizations) SELECT * FROM vendors",
            "forbidden_vendor_schema_consumer",
        ),
        (
            "target_insert",
            "INSERT INTO vendor_organizations(vendor_id) VALUES (?)",
            "forbidden_vendor_schema_dml",
        ),
        (
            "target_insert_or_replace",
            "INSERT OR REPLACE INTO vendor_organizations(vendor_id) VALUES (?)",
            "forbidden_vendor_schema_dml",
        ),
        (
            "target_update",
            "UPDATE vendor_organizations SET organization_status = ?",
            "forbidden_vendor_schema_dml",
        ),
        (
            "target_delete",
            "DELETE FROM vendor_organizations",
            "forbidden_vendor_schema_dml",
        ),
        (
            "target_replace",
            "REPLACE INTO vendor_organizations(vendor_id) VALUES (?)",
            "forbidden_vendor_schema_dml",
        ),
        (
            "target_upsert",
            "INSERT INTO vendor_organizations(vendor_id) VALUES (?) "
            "ON CONFLICT(vendor_id) DO UPDATE SET organization_status = excluded.organization_status",
            "forbidden_vendor_schema_dml",
        ),
    ):
        cases.append(
            (
                name,
                "package/vendor_sql.py",
                f'def run(conn):\n    conn.execute("{sql}")\n',
                expected_code,
            )
        )
    for action in ("ROLLBACK", "ABORT", "REPLACE", "FAIL", "IGNORE"):
        cases.append(
            (
                f"target_insert_conflict_{action.lower()}",
                "package/vendor_sql.py",
                "def run(conn):\n"
                f'    conn.execute("INSERT OR {action} INTO vendor_organizations'
                '(vendor_id) VALUES (?)")\n',
                "forbidden_vendor_schema_dml",
            )
        )
        cases.append(
            (
                f"target_update_or_{action.lower()}",
                "package/vendor_sql.py",
                "def run(conn):\n"
                f'    conn.execute("UPDATE OR {action} vendor_organizations '
                'SET organization_status = ?")\n',
                "forbidden_vendor_schema_dml",
            )
        )
    cases.extend(
        [
            (
                "assembled_target_read",
                "package/vendor_sql.py",
                'PREFIX = "SELECT * FROM "\nTABLE = "vendor_organizations"\n'
                "def run(conn):\n    conn.execute(PREFIX + TABLE)\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "fstring_target_dml",
                "package/vendor_sql.py",
                'TABLE = "vendor_organizations"\n'
                'def run(conn):\n    conn.execute(f"DELETE FROM {TABLE}")\n',
                "forbidden_vendor_schema_dml",
            ),
            (
                "fstring_target_read",
                "package/vendor_sql.py",
                'TABLE = "vendor_organizations"\n'
                'def run(conn):\n    conn.execute(f"SELECT * FROM {TABLE}")\n',
                "forbidden_vendor_schema_consumer",
            ),
            (
                "assembled_target_dml",
                "package/vendor_sql.py",
                'PREFIX = "DELETE FROM "\nTABLE = "vendor_organizations"\n'
                "def run(conn):\n    conn.execute(PREFIX + TABLE)\n",
                "forbidden_vendor_schema_dml",
            ),
            (
                "helper_returned_read",
                "package/vendor_sql.py",
                'def statement():\n    return "SELECT * FROM vendor_organizations"\n'
                "def run(conn):\n    conn.execute(statement())\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "helper_returned_dml",
                "package/vendor_sql.py",
                'def statement():\n    return "DELETE FROM vendor_organizations"\n'
                "def run(conn):\n    conn.execute(statement())\n",
                "forbidden_vendor_schema_dml",
            ),
            (
                "guarded_target_read",
                "package/vendor_sql.py",
                "def rejected(conn, allowed):\n"
                "    if not allowed:\n"
                '        conn.execute("SELECT * FROM vendor_organizations")\n',
                "forbidden_vendor_schema_consumer",
            ),
            (
                "guarded_target_dml",
                "package/vendor_sql.py",
                "def rejected(conn, allowed):\n"
                "    if not allowed:\n"
                '        conn.execute("DELETE FROM vendor_organizations")\n',
                "forbidden_vendor_schema_dml",
            ),
            (
                "metadata_target_second_argument",
                "package/vendor_meta.py",
                'META_SQL = "SELECT * FROM pragma_table_xinfo(?)"\n'
                'TABLE = "vendor_organizations"\n'
                "def inspect(conn):\n    conn.execute(META_SQL, (TABLE,))\n",
                "forbidden_vendor_schema_migration",
            ),
            (
                "helper_positional_target",
                "package/vendor_helper.py",
                "def create_schema(conn, table_name):\n"
                '    conn.execute("CREATE TABLE " + table_name + " (id TEXT)")\n'
                "def run(conn):\n"
                '    create_schema(conn, "vendor_organizations")\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "helper_keyword_target",
                "package/vendor_helper.py",
                "def create_schema(conn, table_name):\n"
                '    conn.execute("CREATE TABLE " + table_name + " (id TEXT)")\n'
                "def run(conn):\n"
                '    create_schema(conn=conn, table_name="vendor_organizations")\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "second_level_helper_target",
                "package/vendor_helper.py",
                "def create_schema(conn, table_name):\n"
                '    conn.execute("CREATE TABLE " + table_name + " (id TEXT)")\n'
                "def forward(conn, target):\n    create_schema(conn, target)\n"
                "def run(conn):\n"
                '    forward(conn, "vendor_organizations")\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "nested_local_helper_target",
                "package/vendor_helper.py",
                "def run(conn):\n"
                "    def create_schema(table_name):\n"
                '        conn.execute("CREATE TABLE " + table_name + " (id TEXT)")\n'
                '    create_schema("vendor_organizations")\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "helper_alias_target",
                "package/vendor_helper.py",
                "def create_schema(conn, table_name):\n"
                '    conn.execute("CREATE TABLE " + table_name + " (id TEXT)")\n'
                "alias = create_schema\n"
                "def run(conn):\n"
                '    alias(conn, "vendor_organizations")\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "branch_alias_target",
                "package/vendor_helper.py",
                "def create_schema(conn, table_name):\n"
                '    conn.execute("CREATE TABLE " + table_name + " (id TEXT)")\n'
                "def run(conn, flag):\n"
                "    if flag:\n"
                '        target = "vendor_organizations"\n'
                "    else:\n"
                '        target = "audit_events"\n'
                "    create_schema(conn, target)\n",
                "forbidden_vendor_schema_table",
            ),
            (
                "metadata_helper_target",
                "package/vendor_helper.py",
                "def inspect_table(conn, table_name):\n"
                '    conn.execute("SELECT * FROM pragma_table_xinfo(?)", (table_name,))\n'
                "def run(conn):\n"
                '    inspect_table(conn, "vendor_organizations")\n',
                "forbidden_vendor_schema_migration",
            ),
            (
                "execute_wrapper_target",
                "package/vendor_helper.py",
                "def execute_wrapper(conn, statement):\n"
                "    conn.execute(statement)\n"
                "def run(conn):\n"
                '    execute_wrapper(conn, "DELETE FROM vendor_organizations")\n',
                "forbidden_vendor_schema_dml",
            ),
            (
                "caller_selected_statement",
                "package/vendor_helper.py",
                "def execute_wrapper(conn, statement):\n"
                "    conn.execute(statement)\n"
                "def run(conn, statement):\n"
                "    execute_wrapper(conn, statement)\n"
                'run(None, "SELECT * FROM vendor_organizations")\n',
                "forbidden_vendor_schema_consumer",
            ),
            (
                "caller_selected_index",
                "package/vendor_helper.py",
                "def create_index(conn, index_name, table_name):\n"
                '    conn.execute("CREATE INDEX " + index_name + " ON " + table_name + "(id)")\n'
                "def run(conn):\n"
                '    create_index(conn, "arbitrary_idx", "vendor_organizations")\n',
                "forbidden_vendor_schema_index",
            ),
            (
                "root_runtime_module",
                "vendor_schema.py",
                'SQL = "CREATE TABLE vendor_organizations (id TEXT)"\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "routes_runtime_module",
                "routes/vendor_schema.py",
                'SQL = "CREATE TABLE vendor_organizations (id TEXT)"\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "arbitrary_nested_runtime_module",
                "package/deep/nested/vendor_schema.py",
                'SQL = "CREATE TABLE vendor_organizations (id TEXT)"\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "root_module_imported_by_app",
                "vendor_runtime.py",
                'SQL = "CREATE TABLE vendor_organizations (id TEXT)"\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "nested_module_imported_by_service",
                "package/vendor_runtime.py",
                'SQL = "CREATE TABLE vendor_organizations (id TEXT)"\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "orm_without_import",
                "package/vendor_model.py",
                "class VendorOrganization(db.Model):\n"
                '    __tablename__ = "vendor_organizations"\n',
                "forbidden_vendor_schema_backend",
            ),
            (
                "table_projection_without_import",
                "package/vendor_model.py",
                'TABLE = Table("vendor_organizations", metadata)\n',
                "forbidden_vendor_schema_backend",
            ),
            (
                "alembic_create_table_without_import",
                "package/vendor_migration.py",
                'op.create_table("vendor_organizations", column)\n',
                "forbidden_vendor_schema_backend",
            ),
            (
                "alembic_create_index_without_import",
                "package/vendor_migration.py",
                'op.create_index("arbitrary", "vendor_organizations", ["vendor_id"])\n',
                "forbidden_vendor_schema_backend",
            ),
            (
                "migration_operation_alias",
                "package/vendor_migration.py",
                "create = op.create_table\n"
                'create("vendor_organizations", column)\n',
                "forbidden_vendor_schema_backend",
            ),
            (
                "postgres_wrapper_without_import",
                "package/vendor_backend.py",
                "def run(conn):\n"
                '    postgres_execute(conn, "SELECT * FROM vendor_organizations")\n',
                "forbidden_vendor_schema_backend",
            ),
            (
                "backend_selector_alias",
                "package/vendor_backend.py",
                'TARGET = "vendor_organizations"\n'
                'BACKEND_SELECTOR = "DATABASE_URL"\n',
                "forbidden_vendor_schema_environment_access",
            ),
            (
                "replace_assembly",
                "package/vendor_sql.py",
                'TEMPLATE = "SELECT * FROM __TABLE__"\n'
                'SQL = TEMPLATE.replace("__TABLE__", "vendor_organizations")\n'
                "def run(conn):\n    conn.execute(SQL)\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "chained_replace_assembly",
                "package/vendor_sql.py",
                'TEMPLATE = "SELECT __COLUMNS__ FROM __TABLE__"\n'
                'SQL = TEMPLATE.replace("__COLUMNS__", "*").replace("__TABLE__", "vendor_organizations")\n'
                "def run(conn):\n    conn.execute(SQL)\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "strip_normalization",
                "package/vendor_sql.py",
                'SQL = " SELECT * FROM vendor_organizations ".strip()\n'
                "def run(conn):\n    conn.execute(SQL)\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "conditional_assembly",
                "package/vendor_sql.py",
                'TARGET = "vendor_organizations"\n'
                "def run(conn, flag):\n"
                '    sql = ("SELECT * FROM " + TARGET) if flag else "SELECT 1"\n'
                "    conn.execute(sql)\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "dict_lookup",
                "package/vendor_sql.py",
                'STATEMENTS = {"read": "SELECT * FROM vendor_organizations"}\n'
                "def run(conn):\n"
                '    conn.execute(STATEMENTS["read"])\n',
                "forbidden_vendor_schema_consumer",
            ),
            (
                "attribute_alias",
                "package/vendor_sql.py",
                "def run(conn, holder):\n"
                '    holder.statement = "DELETE FROM vendor_organizations"\n'
                "    conn.execute(holder.statement)\n",
                "forbidden_vendor_schema_dml",
            ),
            (
                "temporary_trigger",
                "package/vendor_trigger.py",
                'SQL = "CREATE TEMPORARY TRIGGER vendor_guard AFTER INSERT ON vendor_organizations BEGIN SELECT 1; END"\n',
                "forbidden_vendor_schema_trigger",
            ),
            (
                "temporary_quoted_trigger",
                "package/vendor_trigger.py",
                'SQL = \'CREATE TEMPORARY TRIGGER "reserved_vendor_guard" AFTER INSERT ON main."vendor_organizations" BEGIN SELECT 1; END\'\n',
                "forbidden_vendor_schema_trigger",
            ),
            (
                "try_except_union_target",
                "package/vendor_flow.py",
                "def create(conn, flag):\n"
                '    table = "audit_events"\n'
                "    try:\n"
                "        if flag:\n"
                '            table = "audit_log"\n'
                "    except LookupError:\n"
                '        table = "vendor_organizations"\n'
                '    conn.execute("CREATE TABLE " + table + " (id INTEGER)")\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "try_finally_union_target",
                "package/vendor_flow.py",
                "def remove(conn):\n"
                '    table = "audit_events"\n'
                "    try:\n"
                "        pass\n"
                "    finally:\n"
                '        table = "vendor_organizations"\n'
                '    conn.execute("DELETE FROM " + table)\n',
                "forbidden_vendor_schema_dml",
            ),
            (
                "with_union_target",
                "package/vendor_flow.py",
                "def read(conn, manager):\n"
                '    table = "audit_events"\n'
                "    with manager:\n"
                '        table = "vendor_organizations"\n'
                '    conn.execute("SELECT * FROM " + table)\n',
                "forbidden_vendor_schema_consumer",
            ),
            (
                "async_with_union_target",
                "package/vendor_flow.py",
                "async def read(conn, manager):\n"
                '    table = "audit_events"\n'
                "    async with manager:\n"
                '        table = "vendor_organizations"\n'
                '    conn.execute("SELECT * FROM " + table)\n',
                "forbidden_vendor_schema_consumer",
            ),
            (
                "match_union_target",
                "package/vendor_flow.py",
                "def inspect(conn, value):\n"
                '    table = "audit_events"\n'
                "    match value:\n"
                "        case 1:\n"
                '            table = "vendor_organizations"\n'
                "        case _:\n"
                '            table = "audit_log"\n'
                '    conn.execute("SELECT * FROM pragma_table_xinfo(?)", (table,))\n',
                "forbidden_vendor_schema_migration",
            ),
            (
                "boolop_and_target",
                "package/vendor_flow.py",
                "def read(conn, enabled):\n"
                '    table = enabled and "vendor_organizations"\n'
                '    conn.execute("SELECT * FROM " + table)\n',
                "forbidden_vendor_schema_consumer",
            ),
            (
                "boolop_or_target",
                "package/vendor_flow.py",
                "def remove(conn, preferred):\n"
                '    table = preferred or "vendor_organizations"\n'
                '    conn.execute("DELETE FROM " + table)\n',
                "forbidden_vendor_schema_dml",
            ),
            (
                "multilevel_conditional_boolop",
                "package/vendor_flow.py",
                "def read(conn, first, second):\n"
                '    selected = ("vendor_organizations" if first else "audit_events")\n'
                '    table = (second and selected) or "audit_fallback"\n'
                '    conn.execute("SELECT * FROM " + table)\n',
                "forbidden_vendor_schema_consumer",
            ),
            (
                "nested_helper_in_try",
                "package/vendor_flow.py",
                "def run(conn):\n"
                "    try:\n"
                "        def create(table):\n"
                '            conn.execute("CREATE TABLE " + table + " (id INTEGER)")\n'
                '        create("vendor_organizations")\n'
                "    except LookupError:\n"
                "        pass\n",
                "forbidden_vendor_schema_table",
            ),
            (
                "bound_instance_method",
                "package/vendor_method.py",
                "class Builder:\n"
                "    def create(self, conn, table):\n"
                '        conn.execute("CREATE TABLE " + table + " (id INTEGER)")\n'
                'Builder().create(None, "vendor_organizations")\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "bound_class_method",
                "package/vendor_method.py",
                "class Builder:\n"
                "    @classmethod\n"
                "    def remove(cls, conn, table):\n"
                '        conn.execute("DELETE FROM " + table)\n'
                'Builder.remove(None, "vendor_organizations")\n',
                "forbidden_vendor_schema_dml",
            ),
            (
                "bound_instance_read_method",
                "package/vendor_method.py",
                "class Builder:\n"
                "    def read(self, conn, table):\n"
                '        conn.execute("SELECT * FROM " + table)\n'
                'Builder().read(None, "vendor_organizations")\n',
                "forbidden_vendor_schema_consumer",
            ),
            (
                "bound_static_method",
                "package/vendor_method.py",
                "class Builder:\n"
                "    @staticmethod\n"
                "    def read(conn, table):\n"
                '        conn.execute("SELECT * FROM " + table)\n'
                'Builder.read(None, "vendor_organizations")\n',
                "forbidden_vendor_schema_consumer",
            ),
            (
                "bound_instance_variable",
                "package/vendor_method.py",
                "class Builder:\n"
                "    def inspect(self, conn, table):\n"
                '        conn.execute("SELECT * FROM pragma_table_xinfo(?)", (table,))\n'
                "builder = Builder()\n"
                'builder.inspect(None, "vendor_organizations")\n',
                "forbidden_vendor_schema_migration",
            ),
            (
                "class_attribute_via_self",
                "package/vendor_method.py",
                "class Builder:\n"
                '    TABLE = "vendor_organizations"\n'
                "    def read(self, conn):\n"
                '        conn.execute("SELECT * FROM " + self.TABLE)\n'
                "Builder().read(None)\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "class_attribute_via_class",
                "package/vendor_method.py",
                "class Builder:\n"
                '    TABLE = "vendor_organizations"\n'
                "    @staticmethod\n"
                "    def read(conn):\n"
                '        conn.execute("SELECT * FROM " + Builder.TABLE)\n'
                "Builder.read(None)\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "class_attribute_via_cls",
                "package/vendor_method.py",
                "class Builder:\n"
                '    TABLE = "vendor_organizations"\n'
                "    @classmethod\n"
                "    def remove(cls, conn):\n"
                '        conn.execute("DELETE FROM " + cls.TABLE)\n'
                "Builder.remove(None)\n",
                "forbidden_vendor_schema_dml",
            ),
            (
                "instance_attribute_alias",
                "package/vendor_method.py",
                "class Builder:\n"
                "    def read(self, conn):\n"
                '        self.table = "vendor_organizations"\n'
                "        selected = self.table\n"
                '        conn.execute("SELECT * FROM " + selected)\n'
                "Builder().read(None)\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "inherited_class_attribute",
                "package/vendor_method.py",
                "class BaseBuilder:\n"
                '    TABLE = "vendor_organizations"\n'
                "class Builder(BaseBuilder):\n"
                "    def read(self, conn):\n"
                '        conn.execute("SELECT * FROM " + self.TABLE)\n'
                "Builder().read(None)\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "duplicate_method_name_qualified",
                "package/vendor_method.py",
                "def execute(conn, table):\n"
                "    return None\n"
                "class Builder:\n"
                "    def execute(self, conn, table):\n"
                '        conn.execute("CREATE TABLE " + table + " (id INTEGER)")\n'
                'Builder().execute(None, "vendor_organizations")\n',
                "forbidden_vendor_schema_table",
            ),
            (
                "unresolved_receiver_target",
                "package/vendor_method.py",
                "def run(factory):\n"
                '    factory.create_schema("vendor_organizations")\n',
                "unresolved_vendor_schema_capability",
            ),
            (
                "unresolved_bare_callable_target",
                "package/vendor_method.py",
                "def run():\n"
                '    external_operation("vendor_organizations")\n',
                "unresolved_vendor_schema_capability",
            ),
            (
                "default_target_parameter",
                "package/vendor_helper.py",
                "def read(conn, table='vendor_organizations'):\n"
                '    conn.execute("SELECT * FROM " + table)\n'
                "read(None)\n",
                "forbidden_vendor_schema_consumer",
            ),
            (
                "keyword_only_target_parameter",
                "package/vendor_helper.py",
                "def remove(conn, *, table):\n"
                '    conn.execute("DELETE FROM " + table)\n'
                'remove(None, table="vendor_organizations")\n',
                "forbidden_vendor_schema_dml",
            ),
            (
                "recursive_target_forwarding",
                "package/vendor_helper.py",
                "def forward(conn, table):\n"
                "    forward(conn, table)\n"
                'forward(None, "vendor_organizations")\n',
                "unresolved_vendor_schema_capability",
            ),
            (
                "starred_target_arguments",
                "package/vendor_helper.py",
                "def create(conn, table):\n"
                '    conn.execute("CREATE TABLE " + table + " (id INTEGER)")\n'
                'arguments = (None, "vendor_organizations")\n'
                "create(*arguments)\n",
                "forbidden_vendor_schema_table",
            ),
            (
                "bound_method_starred_target_arguments",
                "package/vendor_helper.py",
                "class Builder:\n"
                "    def create(self, conn, table):\n"
                '        conn.execute("CREATE TABLE " + table + " (id INTEGER)")\n'
                'arguments = (None, "vendor_organizations")\n'
                "Builder().create(*arguments)\n",
                "forbidden_vendor_schema_table",
            ),
        ]
    )
    return cases


def cross_file_cases() -> list[
    tuple[str, tuple[tuple[str, str], ...], str | None]
]:
    generic_create = (
        "def create_schema(conn, table):\n"
        '    conn.execute("CREATE TABLE " + table + " (id INTEGER)")\n'
    )
    generic_read = (
        "def read_table(conn, table):\n"
        '    conn.execute("SELECT * FROM " + table)\n'
    )
    generic_remove = (
        "def remove_table(conn, table):\n"
        '    conn.execute("DELETE FROM " + table)\n'
    )
    generic_metadata = (
        "def inspect_table(conn, table):\n"
        '    conn.execute("SELECT * FROM pragma_table_xinfo(?)", (table,))\n'
    )
    return [
        (
            "cross_from_import_ddl",
            (
                ("package/helpers.py", generic_create),
                (
                    "app.py",
                    "from package.helpers import create_schema\n"
                    'create_schema(None, "vendor_organizations")\n',
                ),
            ),
            "forbidden_vendor_schema_table",
        ),
        (
            "cross_import_alias_read",
            (
                ("package/helpers.py", generic_read),
                (
                    "app.py",
                    "from package.helpers import read_table as inspect\n"
                    'inspect(None, "vendor_organizations")\n',
                ),
            ),
            "forbidden_vendor_schema_consumer",
        ),
        (
            "cross_module_qualified_dml",
            (
                ("package/helpers.py", generic_remove),
                (
                    "app.py",
                    "import package.helpers as helpers\n"
                    'helpers.remove_table(None, "vendor_organizations")\n',
                ),
            ),
            "forbidden_vendor_schema_dml",
        ),
        (
            "cross_metadata",
            (
                ("package/helpers.py", generic_metadata),
                (
                    "app.py",
                    "from package.helpers import inspect_table\n"
                    'inspect_table(None, "vendor_organizations")\n',
                ),
            ),
            "forbidden_vendor_schema_migration",
        ),
        (
            "cross_second_level_forwarding",
            (
                ("package/helpers.py", generic_create),
                (
                    "package/forwarders.py",
                    "from package.helpers import create_schema\n"
                    "def forward(conn, table):\n"
                    "    create_schema(conn, table)\n",
                ),
                (
                    "app.py",
                    "from package.forwarders import forward\n"
                    'forward(None, "vendor_organizations")\n',
                ),
            ),
            "forbidden_vendor_schema_table",
        ),
        (
            "cross_four_level_forwarding",
            (
                ("package/helpers.py", generic_create),
                (
                    "package/level_one.py",
                    "from package.helpers import create_schema\n"
                    "def level_one(conn, table):\n"
                    "    create_schema(conn, table)\n",
                ),
                (
                    "package/level_two.py",
                    "from package.level_one import level_one\n"
                    "def level_two(conn, table):\n"
                    "    level_one(conn, table)\n",
                ),
                (
                    "package/level_three.py",
                    "from package.level_two import level_two\n"
                    "def level_three(conn, table):\n"
                    "    level_two(conn, table)\n",
                ),
                (
                    "app.py",
                    "from package.level_three import level_three\n"
                    'level_three(None, "vendor_organizations")\n',
                ),
            ),
            "forbidden_vendor_schema_table",
        ),
        (
            "fifth_level_target_forwarding",
            (
                ("package/helpers.py", generic_create),
                (
                    "package/level_one.py",
                    "from package.helpers import create_schema\n"
                    "def level_one(conn, table):\n"
                    "    create_schema(conn, table)\n",
                ),
                (
                    "package/level_two.py",
                    "from package.level_one import level_one\n"
                    "def level_two(conn, table):\n"
                    "    level_one(conn, table)\n",
                ),
                (
                    "package/level_three.py",
                    "from package.level_two import level_two\n"
                    "def level_three(conn, table):\n"
                    "    level_two(conn, table)\n",
                ),
                (
                    "package/level_four.py",
                    "from package.level_three import level_three\n"
                    "def level_four(conn, table):\n"
                    "    level_three(conn, table)\n",
                ),
                (
                    "app.py",
                    "from package.level_four import level_four\n"
                    'level_four(None, "vendor_organizations")\n',
                ),
            ),
            "unresolved_vendor_schema_capability",
        ),
        (
            "imported_target_constant",
            (
                (
                    "package/constants.py",
                    'TABLE = "vendor_organizations"\n',
                ),
                (
                    "app.py",
                    "from package.constants import TABLE\n"
                    "def read(conn):\n"
                    '    conn.execute("SELECT * FROM " + TABLE)\n',
                ),
            ),
            "forbidden_vendor_schema_consumer",
        ),
        (
            "module_qualified_imported_target_constant",
            (
                (
                    "package/constants.py",
                    'TABLE = "vendor_organizations"\n',
                ),
                (
                    "app.py",
                    "import package.constants as constants\n"
                    "def read(conn):\n"
                    '    conn.execute("SELECT * FROM " + constants.TABLE)\n',
                ),
            ),
            "forbidden_vendor_schema_consumer",
        ),
        (
            "relative_imported_target_constant",
            (
                (
                    "package/constants.py",
                    'TABLE = "vendor_organizations"\n',
                ),
                (
                    "package/reader.py",
                    "from .constants import TABLE\n"
                    "def read(conn):\n"
                    '    conn.execute("SELECT * FROM " + TABLE)\n',
                ),
            ),
            "forbidden_vendor_schema_consumer",
        ),
        (
            "cross_module_inherited_target_attribute",
            (
                (
                    "package/base.py",
                    "class Base:\n"
                    '    TABLE = "vendor_organizations"\n',
                ),
                (
                    "package/reader.py",
                    "from .base import Base\n"
                    "class Reader(Base):\n"
                    "    def read(self, conn):\n"
                    '        conn.execute("SELECT * FROM " + self.TABLE)\n',
                ),
            ),
            "forbidden_vendor_schema_consumer",
        ),
        (
            "cross_file_starred_target_arguments",
            (
                ("package/helpers.py", generic_create),
                (
                    "app.py",
                    "from package.helpers import create_schema\n"
                    'arguments = (None, "vendor_organizations")\n'
                    "create_schema(*arguments)\n",
                ),
            ),
            "forbidden_vendor_schema_table",
        ),
        (
            "cross_caller_sql_callee_target",
            (
                (
                    "package/helpers.py",
                    'TABLE = "vendor_organizations"\n'
                    "def execute_statement(conn, statement):\n"
                    "    conn.execute(statement + TABLE)\n",
                ),
                (
                    "app.py",
                    "from package.helpers import execute_statement\n"
                    'execute_statement(None, "SELECT * FROM ")\n',
                ),
            ),
            "forbidden_vendor_schema_consumer",
        ),
        (
            "cross_caller_target_callee_verb",
            (
                (
                    "package/helpers.py",
                    "def execute_statement(conn, table):\n"
                    '    conn.execute("DELETE FROM " + table)\n',
                ),
                (
                    "app.py",
                    "from package.helpers import execute_statement\n"
                    'execute_statement(None, "vendor_organizations")\n',
                ),
            ),
            "forbidden_vendor_schema_dml",
        ),
        (
            "cross_imported_bound_method",
            (
                (
                    "package/builders.py",
                    "class Builder:\n"
                    "    def create(self, conn, table):\n"
                    '        conn.execute("CREATE TABLE " + table + " (id INTEGER)")\n',
                ),
                (
                    "app.py",
                    "from package.builders import Builder\n"
                    'Builder().create(None, "vendor_organizations")\n',
                ),
            ),
            "forbidden_vendor_schema_table",
        ),
        (
            "cross_imported_bound_instance_variable",
            (
                (
                    "package/builders.py",
                    "class Builder:\n"
                    "    def read(self, conn, table):\n"
                    '        conn.execute("SELECT * FROM " + table)\n',
                ),
                (
                    "app.py",
                    "from package.builders import Builder\n"
                    "builder = Builder()\n"
                    'builder.read(None, "vendor_organizations")\n',
                ),
            ),
            "forbidden_vendor_schema_consumer",
        ),
        (
            "cross_relative_import",
            (
                ("package/helpers.py", generic_create),
                (
                    "package/caller.py",
                    "from .helpers import create_schema\n"
                    'create_schema(None, "vendor_organizations")\n',
                ),
            ),
            "forbidden_vendor_schema_table",
        ),
        (
            "cross_unaliased_dotted_import",
            (
                ("package/helpers.py", generic_read),
                (
                    "app.py",
                    "import package.helpers\n"
                    'package.helpers.read_table(None, "vendor_organizations")\n',
                ),
            ),
            "forbidden_vendor_schema_consumer",
        ),
        (
            "cross_unresolved_imported_callable",
            (
                (
                    "app.py",
                    "from external.vendor_helpers import create_schema\n"
                    'create_schema(None, "vendor_organizations")\n',
                ),
            ),
            "unresolved_vendor_schema_capability",
        ),
        (
            "cross_unrelated_forwarding",
            (
                ("package/helpers.py", generic_read),
                (
                    "app.py",
                    "from package.helpers import read_table\n"
                    'read_table(None, "audit_events")\n',
                ),
            ),
            None,
        ),
    ]


def assert_scenario(
    root: Path,
    expected_code: str | None,
    name: str,
) -> None:
    issues = analyze_repository(root)
    status, output = render_normal(issues)
    if expected_code is None:
        if status != 0 or issues or output.count(PASS_MARKER) != 1:
            raise AssertionError(f"positive scenario {name} failed: {issues!r}")
        return
    codes = {issue.code for issue in issues}
    if status == 0 or expected_code not in codes:
        raise AssertionError(
            f"negative scenario {name} missed {expected_code}: {issues!r}"
        )
    if PASS_MARKER in output:
        raise AssertionError(f"negative scenario {name} emitted normal PASS")
    if output.count("database_access: 0") != 1:
        raise AssertionError(f"negative scenario {name} lost DB counter")
    if output.count("app_imports: 0") != 1:
        raise AssertionError(f"negative scenario {name} lost import counter")


def run_self_test() -> int:
    scenario_count = assert_cli_parser_contract()
    with tempfile.TemporaryDirectory(
        prefix="vendor-id-002a-schema-readiness-"
    ) as temp_value:
        temp_root = Path(temp_value)
        baseline = temp_root / "baseline"
        baseline.mkdir()
        write_base_tree(baseline)

        for name, relative, source in positive_cases():
            root = temp_root / f"positive-{name}"
            shutil.copytree(baseline, root)
            add_source(root, relative, source)
            assert_scenario(root, None, name)
            scenario_count += 1

        for name, relative, source, expected_code in negative_source_cases():
            root = temp_root / f"negative-{name}"
            shutil.copytree(baseline, root)
            add_source(root, relative, source)
            assert_scenario(root, expected_code, name)
            scenario_count += 1

        for name, sources, expected_code in cross_file_cases():
            polarity = "positive" if expected_code is None else "negative"
            root = temp_root / f"{polarity}-{name}"
            shutil.copytree(baseline, root)
            for relative, source in sources:
                add_source(root, relative, source)
            assert_scenario(root, expected_code, name)
            scenario_count += 1

        special: list[tuple[str, Path, str]] = []

        missing_vendor = temp_root / "negative-missing-vendor-policy"
        shutil.copytree(baseline, missing_vendor)
        (missing_vendor / VENDOR_POLICY_PATH).unlink()
        special.append(
            (
                "missing_vendor_policy",
                missing_vendor,
                "vendor_schema_policy_document_missing",
            )
        )

        missing_schema = temp_root / "negative-missing-schema-policy"
        shutil.copytree(baseline, missing_schema)
        (missing_schema / SCHEMA_POLICY_PATH).unlink()
        special.append(
            (
                "missing_schema_policy",
                missing_schema,
                "vendor_schema_policy_document_missing",
            )
        )

        marker_drift = temp_root / "negative-marker-drift"
        shutil.copytree(baseline, marker_drift)
        path = marker_drift / SCHEMA_POLICY_PATH
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "PHYSICAL SCHEMA IMPLEMENTATION: NOT STARTED",
                "PHYSICAL SCHEMA IMPLEMENTATION: STARTED",
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )
        special.append(
            (
                "marker_drift",
                marker_drift,
                "vendor_schema_policy_marker_missing",
            )
        )

        vendor_drift = temp_root / "negative-vendor-fingerprint"
        shutil.copytree(baseline, vendor_drift)
        path = vendor_drift / VENDOR_POLICY_PATH
        path.write_bytes(path.read_bytes() + b"\n")
        special.append(
            ("vendor_fingerprint", vendor_drift, "vendor_schema_policy_drift")
        )

        schema_drift = temp_root / "negative-schema-fingerprint"
        shutil.copytree(baseline, schema_drift)
        path = schema_drift / SCHEMA_POLICY_PATH
        path.write_bytes(path.read_bytes() + b"\n")
        special.append(
            ("schema_fingerprint", schema_drift, "vendor_schema_policy_drift")
        )

        read_error = temp_root / "negative-read-error"
        shutil.copytree(baseline, read_error)
        path = read_error / "services" / "unreadable.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\xff\xfe\x00")
        special.append(("read_error", read_error, "source_read_error"))

        parse_error = temp_root / "negative-parse-error"
        shutil.copytree(baseline, parse_error)
        add_source(parse_error, "services/invalid.py", "def broken(:\n    pass\n")
        special.append(("parse_error", parse_error, "source_parse_error"))

        imported_root = temp_root / "negative-imported-root-runtime"
        shutil.copytree(baseline, imported_root)
        add_source(imported_root, "app.py", "import vendor_runtime\n")
        add_source(
            imported_root,
            "vendor_runtime.py",
            'SQL = "CREATE TABLE vendor_organizations (id TEXT)"\n',
        )
        special.append(
            (
                "imported_root_runtime",
                imported_root,
                "forbidden_vendor_schema_table",
            )
        )

        imported_nested = temp_root / "negative-imported-nested-runtime"
        shutil.copytree(baseline, imported_nested)
        add_source(
            imported_nested,
            "services/loader.py",
            "import package.vendor_runtime\n",
        )
        add_source(
            imported_nested,
            "package/vendor_runtime.py",
            'SQL = "CREATE TABLE vendor_organizations (id TEXT)"\n',
        )
        special.append(
            (
                "imported_nested_runtime",
                imported_nested,
                "forbidden_vendor_schema_table",
            )
        )

        for name, root, expected_code in special:
            assert_scenario(root, expected_code, name)
            scenario_count += 1

    print(f"self_test_scenarios: {scenario_count}")
    print("database_access: 0")
    print("app_imports: 0")
    print(SELF_TEST_MARKER)
    return 0


def main() -> int:
    args = parse_args()
    if args.self_test:
        return run_self_test()
    issues = analyze_repository(ROOT_DIR)
    status, output = render_normal(issues)
    print(output, end="")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
