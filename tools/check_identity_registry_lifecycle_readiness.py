from __future__ import annotations

import argparse
import ast
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
PASS_MARKER = "identity registry lifecycle readiness PASS"
SELF_TEST_MARKER = "identity registry lifecycle readiness self-test PASS"
POLICY_E_PATH = Path("docs/auth_id_001e_registry_schema_baseline.md")
POLICY_F_PATH = Path("docs/auth_id_001f_lifecycle_tombstone_merge_policy.md")
CHECKER_PATH = Path("tools/check_identity_registry_lifecycle_readiness.py")
REGISTRY_TABLES = (
    "global_identities",
    "login_identifier_aliases",
    "backend_principal_mappings",
)
SQL_CALLS = {"execute", "executemany", "executescript"}
APPROVED_FIXTURE_STATEMENTS = {
    (
        Path("tests/smoke_test.py"),
        "run_identity_registry_schema_smoke",
        "insert",
        "insert into global_identities "
        "(global_identity_id, registry_status) values ('fixture', 'disabled')",
    ),
    (
        Path("tools/check_identity_registry_schema.py"),
        "build_unexpected_row",
        "insert",
        "insert into global_identities "
        "(global_identity_id, registry_status, created_provenance, updated_provenance) "
        "values (?, ?, ?, ?)",
    ),
}
EXPECTED_STATUS_CHECKS = (
    "check (registry_status in ('active', 'disabled'))",
    "check (alias_status in ('active', 'disabled', 'superseded'))",
    "check (mapping_status in ('active', 'disabled'))",
)
FORBIDDEN_SCHEMA_TOKENS = (
    "merged_into",
    "tombstoned_at",
    "tombstone_status",
    "restored_at",
    "relationship_movement",
    "moved_to_identity",
)
POLICY_F_MARKERS = (
    "Status: policy baseline",
    "Implementation status: not started",
    "MERGE: UNSUPPORTED",
    "SPLIT: UNSUPPORTED",
    "RESTORE: UNSUPPORTED",
    "LIVE RELATIONSHIP MOVEMENT: UNSUPPORTED",
    "does not create a runtime consumer",
    "READ-ONLY INVENTORY",
    "DRY-RUN",
    "CONFLICT / AMBIGUITY REPORT",
    "QUARANTINE CLASSIFICATION",
    "PROVENANCE PLAN",
    "CORE IMPLEMENTED / CONSUMER ACCEPTANCE PENDING / OPEN AND PARKED",
)
POLICY_E_MARKERS = (
    "| lifecycle / tombstone / merge policy | `AUTH-ID-001F` |",
    "| legacy alias import | `AUTH-ID-001F` |",
    "Generator / validator core status: implemented and Production-frozen.",
    "Current AUTH-ID-001E2 status: CORE IMPLEMENTED / CONSUMER ACCEPTANCE PENDING.",
    "AUTH-ID-001E2 overall must not be marked CLOSED",
)
SQL_IDENTIFIER = r'(?:[A-Za-z_][A-Za-z0-9_$]*|"(?:[^"]|"")+"|`(?:[^`]|``)+`|\[(?:[^\]]|\]\])+\])'
REGISTRY_TABLE_TOKEN = (
    r'(?:global_identities|login_identifier_aliases|backend_principal_mappings|'
    r'"(?:global_identities|login_identifier_aliases|backend_principal_mappings)"|'
    r'`(?:global_identities|login_identifier_aliases|backend_principal_mappings)`|'
    r'\[(?:global_identities|login_identifier_aliases|backend_principal_mappings)\])'
)
QUALIFIED_REGISTRY_TARGET = rf"(?:(?:{SQL_IDENTIFIER})\s*\.\s*)?{REGISTRY_TABLE_TOKEN}"
MUTATION_PATTERN = re.compile(
    rf"\b(?P<operation>"
    rf"insert(?:\s+or\s+(?:rollback|abort|replace|fail|ignore))?\s+into"
    rf"|replace(?:\s+into)?"
    rf"|update(?:\s+or\s+(?:rollback|abort|replace|fail|ignore))?"
    rf"|delete\s+from"
    rf")\s+(?P<target>{QUALIFIED_REGISTRY_TARGET})(?![A-Za-z0-9_$])",
    re.IGNORECASE,
)
UNRESOLVED_MUTATION_EVIDENCE_PATTERN = re.compile(
    r"\binsert\b|\breplace\b|(?<!on )\bupdate\b|(?<!on )\bdelete\b|\bon\s+conflict\b",
    re.IGNORECASE,
)
REGISTRY_TABLE_EVIDENCE_PATTERN = re.compile(
    r"\b(?:global_identities|login_identifier_aliases|backend_principal_mappings)\b",
    re.IGNORECASE,
)
REASSIGNMENT_COLUMNS = (
    "global_identity_id",
    "backend_kind",
    "backend_principal_key",
)
UNKNOWN = object()


@dataclass(frozen=True, order=True)
class Issue:
    code: str
    file: str
    line: int
    symbol: str
    reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Statically verify the frozen identity-registry lifecycle readiness boundary."
    )
    parser.add_argument("--self-test", action="store_true", help="Run disposable synthetic-source negative controls.")
    return parser.parse_args()


def normalized_path(path: Path, root: Path) -> Path:
    return Path(path.resolve().relative_to(root.resolve()).as_posix())


def static_value(node: ast.AST, scopes: list[dict[str, Any]]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        for scope in reversed(scopes):
            if node.id in scope:
                value = scope[node.id]
                return None if value is UNKNOWN else value
        return None
    if isinstance(node, (ast.Tuple, ast.List)):
        values = [static_value(item, scopes) for item in node.elts]
        if any(value is None for value in values):
            return None
        return tuple(values) if isinstance(node, ast.Tuple) else values
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = static_value(node.left, scopes)
        right = static_value(node.right, scopes)
        if isinstance(left, str) and isinstance(right, str):
            return left + right
        if isinstance(left, (tuple, list)) and isinstance(right, type(left)):
            return left + right
        return None
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for item in node.values:
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                parts.append(item.value)
                continue
            if isinstance(item, ast.FormattedValue):
                value = static_value(item.value, scopes)
                if isinstance(value, (str, int)):
                    parts.append(str(value))
                    continue
            return None
        return "".join(parts)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        owner = static_value(node.func.value, scopes)
        if node.func.attr == "format" and isinstance(owner, str):
            args = [static_value(arg, scopes) for arg in node.args]
            kwargs = {item.arg: static_value(item.value, scopes) for item in node.keywords if item.arg}
            if any(value is None for value in args) or any(value is None for value in kwargs.values()):
                return None
            try:
                return owner.format(*args, **kwargs)
            except (IndexError, KeyError, ValueError):
                return None
        if node.func.attr == "join" and isinstance(owner, str) and len(node.args) == 1:
            values = static_value(node.args[0], scopes)
            if isinstance(values, (tuple, list)) and all(isinstance(value, str) for value in values):
                return owner.join(values)
    return None


def string_fragments(node: ast.AST, scopes: list[dict[str, Any]]) -> list[str]:
    resolved = static_value(node, scopes)
    if isinstance(resolved, str):
        return [resolved]
    fragments: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            fragments.append(child.value)
        elif isinstance(child, ast.Name):
            value = static_value(child, scopes)
            if isinstance(value, str):
                fragments.append(value)
            else:
                fragments.append(child.id)
    return fragments


def symbol_name(stack: list[str]) -> str:
    return ".".join(stack) if stack else "<module>"


def normalized_sql_fingerprint(sql: str) -> str:
    return " ".join(sql.strip().lower().split())


def mutation_operation(match: re.Match[str]) -> str:
    return match.group("operation").split(None, 1)[0].lower()


def registry_table_from_target(target: str) -> str:
    lowered = target.lower()
    for table in REGISTRY_TABLES:
        if re.search(rf"\b{re.escape(table)}\b", lowered):
            return table
    raise AssertionError("matched registry target did not contain a registry table")


class PythonSourceAnalyzer(ast.NodeVisitor):
    def __init__(self, root: Path, path: Path, source: str, tree: ast.AST) -> None:
        self.root = root
        self.path = normalized_path(path, root)
        self.source = source
        self.tree = tree
        self.issues: list[Issue] = []
        self.scopes: list[dict[str, Any]] = [{}]
        self.symbols: list[str] = []

    def add_issue(self, code: str, node: ast.AST, reason: str) -> None:
        self.issues.append(
            Issue(
                code=code,
                file=self.path.as_posix(),
                line=int(getattr(node, "lineno", 1)),
                symbol=symbol_name(self.symbols),
                reason=reason,
            )
        )

    def fixture_statement_allowed(self, sql: str, operation: str) -> bool:
        key = (
            self.path,
            symbol_name(self.symbols),
            operation,
            normalized_sql_fingerprint(sql),
        )
        return key in APPROVED_FIXTURE_STATEMENTS

    def visit_Assign(self, node: ast.Assign) -> None:
        value = static_value(node.value, self.scopes)
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.scopes[-1][target.id] = value if value is not None else UNKNOWN
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.value is not None:
            value = static_value(node.value, self.scopes)
            self.scopes[-1][node.target.id] = value if value is not None else UNKNOWN
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._check_capability(node)
        self.symbols.append(node.name)
        self.scopes.append({})
        for statement in node.body:
            self.visit(statement)
        self.scopes.pop()
        self.symbols.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.symbols.append(node.name)
        self.scopes.append({})
        for statement in node.body:
            self.visit(statement)
        self.scopes.pop()
        self.symbols.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and node.func.attr in SQL_CALLS and node.args:
            self._check_sql_call(node, node.args[0])
        self.generic_visit(node)

    def _check_sql_call(self, call: ast.Call, expression: ast.AST) -> None:
        resolved = static_value(expression, self.scopes)
        if isinstance(resolved, str):
            match = MUTATION_PATTERN.search(resolved)
            if not match:
                return
            operation = mutation_operation(match)
            if self.fixture_statement_allowed(resolved, operation):
                return
            table = registry_table_from_target(match.group("target"))
            self.add_issue(
                "runtime_registry_dml",
                call,
                f"forbidden {operation.upper()} targets {table}",
            )
            normalized = " ".join(resolved.lower().split())
            if operation == "update" and any(
                re.search(rf"\bset\b[^;]*\b{re.escape(column)}\b", normalized)
                for column in REASSIGNMENT_COLUMNS
            ):
                self.add_issue(
                    "forbidden_reassignment",
                    call,
                    "registry relationship ownership or backend reference movement is forbidden",
                )
            return

        fragments = string_fragments(expression, self.scopes)
        mutation_evidence = any(
            UNRESOLVED_MUTATION_EVIDENCE_PATTERN.search(fragment)
            for fragment in fragments
        )
        registry_table_evidence = any(
            REGISTRY_TABLE_EVIDENCE_PATTERN.search(fragment)
            for fragment in fragments
        )
        if mutation_evidence and registry_table_evidence:
            self.add_issue(
                "unresolved_registry_sql",
                call,
                "registry-related mutation SQL could not be resolved statically",
            )

    def _check_capability(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if self.path == CHECKER_PATH or self.path.parts[:1] == ("tests",):
            return
        source = ast.get_source_segment(self.source, node) or node.name
        lowered = source.lower()
        name = node.name.lower()
        registry_context = (
            "identity_registry" in lowered
            or "global_identity" in lowered
            or "login_identifier_alias" in lowered
            or "backend_principal_mapping" in lowered
            or "/registry" in lowered
        )
        if not registry_context:
            return

        decorators = " ".join(ast.unparse(item).lower() for item in node.decorator_list)
        if (".route" in decorators or "api" in name or "form" in name) and any(
            token in lowered
            for token in ("reactivat", "supersed", "disable", "delete", "merge", "split", "restore", "reassign")
        ):
            self.add_issue(
                "forbidden_registry_route",
                node,
                "registry lifecycle route, API, or form handler is not authorized",
            )

        if self.path.parts[:1] == ("tools",) and (
            "argparse" in lowered or "parse_args" in lowered or re.search(r"--(?:reactivate|disable|merge|restore|apply)", lowered)
        ) and any(token in lowered for token in ("reactivat", "supersed", "delete", "merge", "split", "restore", "mutation")):
            self.add_issue(
                "forbidden_registry_cli",
                node,
                "registry lifecycle mutation CLI is not authorized",
            )

        capability_codes = (
            ("hard_delete", "forbidden_hard_delete", "registry hard delete helper is forbidden"),
            ("merge", "forbidden_merge", "registry merge helper is unsupported"),
            ("split", "forbidden_split", "registry split helper is unsupported"),
            ("restore", "forbidden_restore", "registry restore helper is unsupported"),
            ("reassign", "forbidden_reassignment", "registry relationship reassignment helper is forbidden"),
            (
                "relationship_movement",
                "forbidden_relationship_movement",
                "registry relationship movement is unsupported",
            ),
            (
                "legacy_alias_import",
                "forbidden_legacy_import_write",
                "legacy alias import write helper is not authorized",
            ),
            (
                "cross_backend_link",
                "forbidden_cross_backend_link",
                "automatic cross-backend linking is not authorized",
            ),
            ("reactivat", "forbidden_lifecycle_consumer", "registry reactivation consumer is not authorized"),
            ("supersed", "forbidden_lifecycle_consumer", "registry supersede consumer is not authorized"),
        )
        for token, code, reason in capability_codes:
            if token in name:
                self.add_issue(code, node, reason)


def read_text(root: Path, relative_path: Path) -> tuple[str | None, Issue | None]:
    path = root / relative_path
    if not path.is_file():
        return None, Issue(
            code="policy_document_missing",
            file=relative_path.as_posix(),
            line=1,
            symbol="<document>",
            reason="required frozen policy document is missing",
        )
    try:
        return path.read_text(encoding="utf-8"), None
    except (OSError, UnicodeError):
        return None, Issue(
            code="source_read_error",
            file=relative_path.as_posix(),
            line=1,
            symbol="<document>",
            reason="required source could not be read as UTF-8",
        )


def check_policy_markers(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    for path, markers in ((POLICY_F_PATH, POLICY_F_MARKERS), (POLICY_E_PATH, POLICY_E_MARKERS)):
        source, issue = read_text(root, path)
        if issue:
            issues.append(issue)
            continue
        assert source is not None
        lines = source.splitlines()
        for marker in markers:
            if marker not in source:
                issues.append(
                    Issue(
                        code="policy_marker_missing",
                        file=path.as_posix(),
                        line=1,
                        symbol="<document>",
                        reason=f"required frozen marker is missing: {marker}",
                    )
                )
        if path == POLICY_E_PATH:
            for index, line in enumerate(lines, 1):
                normalized = " ".join(line.strip().split()).upper()
                if "AUTH-ID-001E2" in normalized and "CLOSED" in normalized and "MUST NOT" not in normalized:
                    issues.append(
                        Issue(
                            code="e2_status_closed",
                            file=path.as_posix(),
                            line=index,
                            symbol="<document>",
                            reason="AUTH-ID-001E2 was marked CLOSED despite pending consumer acceptance",
                        )
                    )
    return issues


def module_constants(tree: ast.Module) -> dict[str, Any]:
    scope: dict[str, Any] = {}
    scopes = [scope]
    for node in tree.body:
        if isinstance(node, ast.Assign):
            value = static_value(node.value, scopes)
            for target in node.targets:
                if isinstance(target, ast.Name):
                    scope[target.id] = value if value is not None else UNKNOWN
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            value = static_value(node.value, scopes)
            scope[node.target.id] = value if value is not None else UNKNOWN
    return scope


def check_schema_boundary(root: Path) -> list[Issue]:
    app_path = root / "app.py"
    if not app_path.is_file():
        return [
            Issue(
                code="schema_source_missing",
                file="app.py",
                line=1,
                symbol="<module>",
                reason="approved schema source is missing",
            )
        ]
    source = app_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename="app.py")
    except SyntaxError as exc:
        return [
            Issue(
                code="source_parse_error",
                file="app.py",
                line=int(exc.lineno or 1),
                symbol="<module>",
                reason="approved schema source is not valid Python",
            )
        ]
    constants = module_constants(tree)
    statements = constants.get("IDENTITY_REGISTRY_SCHEMA_STATEMENTS")
    if not isinstance(statements, (tuple, list)) or not all(isinstance(item, str) for item in statements):
        return [
            Issue(
                code="schema_statements_unresolved",
                file="app.py",
                line=1,
                symbol="IDENTITY_REGISTRY_SCHEMA_STATEMENTS",
                reason="approved registry schema statements could not be resolved statically",
            )
        ]
    schema = "\n".join(statements)
    normalized = " ".join(schema.lower().split())
    issues: list[Issue] = []
    for table in REGISTRY_TABLES:
        if re.search(rf"\bcreate\s+table\s+if\s+not\s+exists\s+{re.escape(table)}\b", normalized) is None:
            issues.append(
                Issue(
                    code="schema_table_missing",
                    file="app.py",
                    line=1,
                    symbol="IDENTITY_REGISTRY_SCHEMA_STATEMENTS",
                    reason=f"approved registry table is missing: {table}",
                )
            )
    for marker in EXPECTED_STATUS_CHECKS:
        if marker not in normalized:
            issues.append(
                Issue(
                    code="schema_status_drift",
                    file="app.py",
                    line=1,
                    symbol="IDENTITY_REGISTRY_SCHEMA_STATEMENTS",
                    reason=f"frozen lifecycle status set changed: {marker}",
                )
            )
    for token in FORBIDDEN_SCHEMA_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", normalized):
            issues.append(
                Issue(
                    code="schema_capability_drift",
                    file="app.py",
                    line=1,
                    symbol="IDENTITY_REGISTRY_SCHEMA_STATEMENTS",
                    reason=f"unauthorized lifecycle schema capability appeared: {token}",
                )
            )
    return issues


def python_sources(root: Path) -> list[Path]:
    result: list[Path] = []
    for path in root.rglob("*.py"):
        relative = normalized_path(path, root)
        if any(part in {".git", ".codex", "__pycache__"} for part in relative.parts):
            continue
        result.append(path)
    return sorted(result)


def analyze_repository(root: Path) -> list[Issue]:
    issues = check_policy_markers(root)
    issues.extend(check_schema_boundary(root))
    for path in python_sources(root):
        relative = normalized_path(path, root)
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative.as_posix())
        except (OSError, UnicodeError):
            issues.append(
                Issue(
                    code="source_read_error",
                    file=relative.as_posix(),
                    line=1,
                    symbol="<module>",
                    reason="Python source could not be read as UTF-8",
                )
            )
            continue
        except SyntaxError as exc:
            issues.append(
                Issue(
                    code="source_parse_error",
                    file=relative.as_posix(),
                    line=int(exc.lineno or 1),
                    symbol="<module>",
                    reason="Python source could not be parsed",
                )
            )
            continue
        analyzer = PythonSourceAnalyzer(root, path, source, tree)
        analyzer.visit(tree)
        issues.extend(analyzer.issues)
    return sorted(set(issues))


def render_normal(issues: list[Issue]) -> tuple[int, str]:
    lines = [
        "identity_registry_lifecycle_readiness_scope: static_source_and_frozen_policy_only",
        f"issues_count: {len(issues)}",
        f"runtime_registry_dml: {'PASS' if not any(i.code in {'runtime_registry_dml', 'unresolved_registry_sql'} for i in issues) else 'FAIL'}",
        f"forbidden_consumer_drift: {'PASS' if not any(i.code.startswith('forbidden_') for i in issues) else 'FAIL'}",
        f"frozen_policy_boundary: {'PASS' if not any(i.code.startswith('policy_') or i.code == 'e2_status_closed' for i in issues) else 'FAIL'}",
        f"schema_lifecycle_boundary: {'PASS' if not any(i.code.startswith('schema_') for i in issues) else 'FAIL'}",
        "database_access: 0",
        "app_imports: 0",
    ]
    if issues:
        lines.append("FAIL identity registry lifecycle readiness:")
        for issue in issues:
            lines.append(
                f"- {issue.code} file={issue.file} line={issue.line} symbol={issue.symbol} reason={issue.reason}"
            )
        return 1, "\n".join(lines) + "\n"
    lines.append(PASS_MARKER)
    return 0, "\n".join(lines) + "\n"


POSITIVE_APP = """\
IDENTITY_REGISTRY_NORMALIZATION_ALGORITHM_FAMILY = "NFKC_CASEFOLD_V1"
IDENTITY_REGISTRY_NORMALIZATION_PROFILE = "NFKC_CASEFOLD_V1_UCD16_0_0"
IDENTITY_REGISTRY_UNICODE_DATA_VERSION = "16.0.0"
IDENTITY_REGISTRY_TRIM_CONFORMANCE_PROFILE = "PY3146_UCD16_0_0_STRIP_V1"
IDENTITY_REGISTRY_SCHEMA_STATEMENTS = (
    "CREATE TABLE IF NOT EXISTS global_identities (global_identity_id TEXT PRIMARY KEY, registry_status TEXT NOT NULL DEFAULT 'disabled', CHECK (registry_status IN ('active', 'disabled'))) STRICT;",
    "CREATE TABLE IF NOT EXISTS login_identifier_aliases (login_identifier_alias_id TEXT PRIMARY KEY, global_identity_id TEXT NOT NULL, alias_status TEXT NOT NULL DEFAULT 'active', CHECK (alias_status IN ('active', 'disabled', 'superseded'))) STRICT;",
    "CREATE TABLE IF NOT EXISTS backend_principal_mappings (backend_principal_mapping_id TEXT PRIMARY KEY, global_identity_id TEXT NOT NULL, backend_kind TEXT NOT NULL, backend_principal_key ANY NOT NULL, mapping_status TEXT NOT NULL DEFAULT 'active', CHECK (mapping_status IN ('active', 'disabled'))) STRICT;",
)

def ensure_identity_registry_schema(conn):
    for statement in IDENTITY_REGISTRY_SCHEMA_STATEMENTS:
        conn.execute(statement)
"""
POSITIVE_F_POLICY = """\
Status: policy baseline
Implementation status: not started
does not create a runtime consumer
CORE IMPLEMENTED / CONSUMER ACCEPTANCE PENDING / OPEN AND PARKED
MERGE: UNSUPPORTED
SPLIT: UNSUPPORTED
RESTORE: UNSUPPORTED
LIVE RELATIONSHIP MOVEMENT: UNSUPPORTED
READ-ONLY INVENTORY
DRY-RUN
CONFLICT / AMBIGUITY REPORT
QUARANTINE CLASSIFICATION
PROVENANCE PLAN
"""
POSITIVE_E_POLICY = """\
| lifecycle / tombstone / merge policy | `AUTH-ID-001F` |
| legacy alias import | `AUTH-ID-001F` |
Generator / validator core status: implemented and Production-frozen.
Current AUTH-ID-001E2 status: CORE IMPLEMENTED / CONSUMER ACCEPTANCE PENDING.
AUTH-ID-001E2 overall must not be marked CLOSED
"""


def write_synthetic_tree(root: Path) -> None:
    files = {
        Path("app.py"): POSITIVE_APP,
        Path("services/identity_registry_ids.py"): "def generate_global_identity_id():\n    return 'opaque'\n",
        Path("tests/smoke_test.py"): (
            "def run_identity_registry_schema_smoke(conn):\n"
            "    conn.execute(\"INSERT INTO global_identities "
            "(global_identity_id, registry_status) VALUES ('fixture', 'disabled')\")\n"
        ),
        Path("tools/check_identity_registry_schema.py"): (
            "def build_unexpected_row(conn):\n"
            "    conn.execute(\"INSERT INTO global_identities "
            "(global_identity_id, registry_status, created_provenance, updated_provenance) "
            "VALUES (?, ?, ?, ?)\", ('fixture', 'disabled', 'self-test', 'self-test'))\n"
        ),
        Path("tools/capture_schema_manifest.py"): "def capture_schema_manifest():\n    return {'write_attempts': 0}\n",
        POLICY_E_PATH: POSITIVE_E_POLICY,
        POLICY_F_PATH: POSITIVE_F_POLICY,
    }
    for path, content in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")


def replace_file(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def append_file(root: Path, relative: str, content: str) -> None:
    path = root / relative
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def self_test_cases() -> list[tuple[str, str, str, str]]:
    return [
        ("direct_insert", "tools/unauthorized.py", "def run(conn):\n    conn.execute(\"INSERT INTO global_identities VALUES ('x')\")\n", "runtime_registry_dml"),
        ("direct_update", "tools/unauthorized.py", "def run(conn):\n    conn.execute(\"UPDATE global_identities SET registry_status = 'active'\")\n", "runtime_registry_dml"),
        ("direct_delete", "tools/unauthorized.py", "def run(conn):\n    conn.execute(\"DELETE FROM global_identities\")\n", "runtime_registry_dml"),
        ("schema_qualified_insert", "tools/unauthorized.py", "def run(conn):\n    conn.execute(\"INSERT INTO main.global_identities VALUES ('x')\")\n", "runtime_registry_dml"),
        ("schema_qualified_update", "tools/unauthorized.py", "def run(conn):\n    conn.execute(\"UPDATE main.global_identities SET registry_status = 'active'\")\n", "runtime_registry_dml"),
        ("schema_qualified_delete", "tools/unauthorized.py", "def run(conn):\n    conn.execute(\"DELETE FROM temp.global_identities\")\n", "runtime_registry_dml"),
        ("quoted_schema_qualified", "tools/unauthorized.py", "def run(conn):\n    conn.execute('UPDATE \"main\".\"login_identifier_aliases\" SET alias_status = \"disabled\"')\n", "runtime_registry_dml"),
        ("replace", "tools/unauthorized.py", "def run(conn):\n    conn.execute(\"REPLACE INTO global_identities VALUES ('x')\")\n", "runtime_registry_dml"),
        ("upsert", "tools/unauthorized.py", "def run(conn):\n    conn.execute(\"INSERT INTO global_identities VALUES ('x') ON CONFLICT(global_identity_id) DO UPDATE SET registry_status='active'\")\n", "runtime_registry_dml"),
        ("update_or_replace", "tools/unauthorized.py", "def run(conn):\n    conn.execute(\"UPDATE OR REPLACE global_identities SET registry_status = 'active'\")\n", "runtime_registry_dml"),
        ("update_or_rollback", "tools/unauthorized.py", "def run(conn):\n    conn.execute(\"UPDATE OR ROLLBACK global_identities SET registry_status = 'active'\")\n", "runtime_registry_dml"),
        ("update_or_abort", "tools/unauthorized.py", "def run(conn):\n    conn.execute(\"UPDATE OR ABORT global_identities SET registry_status = 'active'\")\n", "runtime_registry_dml"),
        ("update_or_fail", "tools/unauthorized.py", "def run(conn):\n    conn.execute(\"UPDATE OR FAIL global_identities SET registry_status = 'active'\")\n", "runtime_registry_dml"),
        ("update_or_ignore", "tools/unauthorized.py", "def run(conn):\n    conn.execute(\"UPDATE OR IGNORE global_identities SET registry_status = 'active'\")\n", "runtime_registry_dml"),
        ("executescript", "tools/unauthorized.py", "def run(conn):\n    conn.executescript(\"DELETE FROM global_identities;\")\n", "runtime_registry_dml"),
        ("executemany", "tools/unauthorized.py", "def run(conn):\n    conn.executemany(\"INSERT INTO global_identities VALUES (?)\", [])\n", "runtime_registry_dml"),
        ("constant_concat", "tools/unauthorized.py", "TABLE='global_identities'\ndef run(conn):\n    sql='INSERT INTO ' + TABLE + ' VALUES (?)'\n    conn.execute(sql, ('x',))\n", "runtime_registry_dml"),
        ("f_string", "tools/unauthorized.py", "TABLE='global_identities'\ndef run(conn):\n    conn.execute(f\"UPDATE {TABLE} SET registry_status='active'\")\n", "runtime_registry_dml"),
        ("format_sql", "tools/unauthorized.py", "TABLE='global_identities'\ndef run(conn):\n    conn.execute(\"DELETE FROM {table}\".format(table=TABLE))\n", "runtime_registry_dml"),
        ("unresolved_dynamic", "tools/unauthorized.py", "def run(conn, suffix):\n    registry_table='global_identities'\n    conn.execute('INSERT INTO ' + registry_table + suffix)\n", "unresolved_registry_sql"),
        ("unresolved_builder_delete", "tools/unauthorized.py", "def run(conn):\n    conn.execute(build_sql(\"DELETE\", \"global_identities\"))\n", "unresolved_registry_sql"),
        ("unresolved_helper_update", "tools/unauthorized.py", "def run(conn):\n    table_name = \"backend_principal_mappings\"\n    conn.execute(helper(\"UPDATE\", table_name))\n", "unresolved_registry_sql"),
        ("unresolved_helper_insert", "tools/unauthorized.py", "def run(conn):\n    conn.execute(helper(\"INSERT\", \"login_identifier_aliases\"))\n", "unresolved_registry_sql"),
        ("lifecycle_route", "app_extra.py", "@app.route('/registry/reactivate')\ndef reactivate_global_identity():\n    return None\n", "forbidden_registry_route"),
        ("mutation_cli", "tools/registry_cli.py", "import argparse\ndef reactivate_global_identity_cli():\n    parser=argparse.ArgumentParser()\n    parser.add_argument('--reactivate')\n", "forbidden_registry_cli"),
        ("hard_delete", "services/registry_ops.py", "def hard_delete_global_identity():\n    pass\n", "forbidden_hard_delete"),
        ("merge", "services/registry_ops.py", "def merge_global_identity_records():\n    pass\n", "forbidden_merge"),
        ("split", "services/registry_ops.py", "def split_global_identity_record():\n    pass\n", "forbidden_split"),
        ("restore", "services/registry_ops.py", "def restore_global_identity_record():\n    pass\n", "forbidden_restore"),
        ("alias_reassignment", "services/registry_ops.py", "def change_alias(conn):\n    conn.execute(\"UPDATE login_identifier_aliases SET global_identity_id='x'\")\n", "forbidden_reassignment"),
        ("mapping_reassignment", "services/registry_ops.py", "def change_mapping(conn):\n    conn.execute(\"UPDATE backend_principal_mappings SET backend_principal_key=2\")\n", "forbidden_reassignment"),
        ("relationship_movement", "services/registry_ops.py", "def relationship_movement_global_identity():\n    pass\n", "forbidden_relationship_movement"),
        ("automatic_link", "services/registry_ops.py", "def automatic_cross_backend_link_global_identity():\n    pass\n", "forbidden_cross_backend_link"),
        ("legacy_import", "services/registry_ops.py", "def legacy_alias_import_global_identity():\n    pass\n", "forbidden_legacy_import_write"),
        ("unauthorized_tool_fixture", "tools/new_fixture.py", "def build_fixture(conn):\n    conn.execute(\"INSERT INTO global_identities VALUES ('x')\")\n", "runtime_registry_dml"),
        ("runtime_named_fixture", "app.py", POSITIVE_APP + "\ndef run_identity_registry_schema_smoke(conn):\n    conn.execute(\"DELETE FROM global_identities\")\n", "runtime_registry_dml"),
        ("approved_fixture_delete", "tools/check_identity_registry_schema.py", "def build_unexpected_row(conn):\n    conn.execute(\"DELETE FROM global_identities\")\n", "runtime_registry_dml"),
        ("approved_fixture_update", "tools/check_identity_registry_schema.py", "def build_unexpected_row(conn):\n    conn.execute(\"UPDATE global_identities SET registry_status = 'active'\")\n", "runtime_registry_dml"),
        ("approved_fixture_replace", "tools/check_identity_registry_schema.py", "def build_unexpected_row(conn):\n    conn.execute(\"REPLACE INTO global_identities VALUES ('x')\")\n", "runtime_registry_dml"),
        ("approved_fixture_upsert", "tools/check_identity_registry_schema.py", "def build_unexpected_row(conn):\n    conn.execute(\"INSERT INTO global_identities VALUES ('x') ON CONFLICT(global_identity_id) DO UPDATE SET registry_status='active'\")\n", "runtime_registry_dml"),
    ]


def run_self_test() -> int:
    completed = 0
    with tempfile.TemporaryDirectory(prefix="identity-registry-lifecycle-readiness-") as temp_dir:
        base = Path(temp_dir) / "base"
        write_synthetic_tree(base)
        positive_issues = analyze_repository(base)
        if positive_issues:
            raise AssertionError(f"positive synthetic tree failed: {positive_issues!r}")

        for name, relative, content, expected_code in self_test_cases():
            case_root = Path(temp_dir) / name
            shutil.copytree(base, case_root)
            replace_file(case_root, relative, content)
            issues = analyze_repository(case_root)
            status, output = render_normal(issues)
            if status == 0 or expected_code not in {issue.code for issue in issues}:
                raise AssertionError(f"{name} did not fail with {expected_code}: {issues!r}")
            if PASS_MARKER in output:
                raise AssertionError(f"{name} emitted the normal PASS marker")
            completed += 1

        special_cases: list[tuple[str, str]] = []

        missing_policy = Path(temp_dir) / "missing_policy"
        shutil.copytree(base, missing_policy)
        (missing_policy / POLICY_F_PATH).unlink()
        special_cases.append(("missing_policy", "policy_document_missing"))

        changed_marker = Path(temp_dir) / "changed_marker"
        shutil.copytree(base, changed_marker)
        replace_file(changed_marker, POLICY_F_PATH.as_posix(), POSITIVE_F_POLICY.replace("MERGE: UNSUPPORTED", "MERGE: ENABLED"))
        special_cases.append(("changed_marker", "policy_marker_missing"))

        closed_e2 = Path(temp_dir) / "closed_e2"
        shutil.copytree(base, closed_e2)
        append_file(closed_e2, POLICY_E_PATH.as_posix(), "\nAUTH-ID-001E2 overall status: CLOSED\n")
        special_cases.append(("closed_e2", "e2_status_closed"))

        status_drift = Path(temp_dir) / "status_drift"
        shutil.copytree(base, status_drift)
        replace_file(
            status_drift,
            "app.py",
            POSITIVE_APP.replace(
                "CHECK (registry_status IN ('active', 'disabled'))",
                "CHECK (registry_status IN ('active', 'disabled', 'tombstoned'))",
            ),
        )
        special_cases.append(("status_drift", "schema_status_drift"))

        field_drift = Path(temp_dir) / "field_drift"
        shutil.copytree(base, field_drift)
        replace_file(
            field_drift,
            "app.py",
            POSITIVE_APP.replace(
                "registry_status TEXT NOT NULL DEFAULT 'disabled',",
                "registry_status TEXT NOT NULL DEFAULT 'disabled', merged_into TEXT,",
            ),
        )
        special_cases.append(("field_drift", "schema_capability_drift"))

        for name, expected_code in special_cases:
            issues = analyze_repository(Path(temp_dir) / name)
            status, output = render_normal(issues)
            if status == 0 or expected_code not in {issue.code for issue in issues}:
                raise AssertionError(f"{name} did not fail with {expected_code}: {issues!r}")
            if PASS_MARKER in output:
                raise AssertionError(f"{name} emitted the normal PASS marker")
            completed += 1

    print(f"self_test_scenarios: {completed + 1}")
    print("database_access: 0")
    print("app_imports: 0")
    print(SELF_TEST_MARKER)
    return 0


def main() -> int:
    args = parse_args()
    if args.self_test:
        return run_self_test()
    status, output = render_normal(analyze_repository(ROOT_DIR))
    print(output, end="")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
