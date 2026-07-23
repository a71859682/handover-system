from __future__ import annotations

import argparse
import ast
import hashlib
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
PASS_MARKER = "identity registry linking readiness PASS"
SELF_TEST_MARKER = "identity registry linking readiness self-test PASS"
POLICY_E_PATH = Path("docs/auth_id_001e_registry_schema_baseline.md")
POLICY_F_PATH = Path("docs/auth_id_001f_lifecycle_tombstone_merge_policy.md")
POLICY_G_PATH = Path("docs/auth_id_001g_explicit_cross_backend_linking_baseline.md")
CHECKER_PATH = Path("tools/check_identity_registry_linking_readiness.py")
LIFECYCLE_CHECKER_PATH = Path("tools/check_identity_registry_lifecycle_readiness.py")
APPROVED_LIFECYCLE_CHECKER_SHA256 = (
    "5651BDC56222399816941D9BFF25A1BAAA7F8EEFBFC18B01B70FEFC3697466F1"
)

G_POLICY_MARKERS = (
    "Status: design baseline",
    "Scope: docs-only",
    "Implementation status: not started",
    "| explicit cross-backend account linking | `AUTH-ID-001G` |",
    "there is no runtime linking consumer",
    "there is no dedicated link authority",
    "that capability is not currently implemented",
    "that capability is not currently assigned to any role or account",
    "password verification is not linking proof",
    "simultaneous control of both credentials is evidence of control over two "
    "backend accounts, but is not by itself proof that the accounts represent the same subject",
    "| lifecycle, mapping disable/reactivation, and unlink | `AUTH-ID-001F` |",
    "| existing-state anomaly repair, upgrade, and reconciliation | `AUTH-ID-001H` |",
    "| creation-consumer ID collision and transaction acceptance | `AUTH-ID-001E2` |",
    "No G implementation may bypass the F, H, or E2 gates.",
    "Production registry rows, existing mapping topology, and current link state were "
    "not queried during this docs-only slice. They remain unknown.",
    "LINKING IMPLEMENTATION: NOT STARTED",
    "DEDICATED LINK AUTHORITY: NOT IMPLEMENTED OR ASSIGNED",
    "NO LINKING CONSUMER CREATED",
)
G_OWNER_MARKERS = (
    "| explicit cross-backend account linking | `AUTH-ID-001G` |",
    "| lifecycle, mapping disable/reactivation, and unlink | `AUTH-ID-001F` |",
    "| existing-state anomaly repair, upgrade, and reconciliation | `AUTH-ID-001H` |",
    "| creation-consumer ID collision and transaction acceptance | `AUTH-ID-001E2` |",
    "No G implementation may bypass the F, H, or E2 gates.",
)
UPSTREAM_POLICY_MARKERS = {
    POLICY_E_PATH: (
        "| explicit cross-backend account linking | `AUTH-ID-001G` |",
        "| lifecycle / tombstone / merge policy | `AUTH-ID-001F` |",
        "AUTH-ID-001E2 overall must not be marked CLOSED",
    ),
    POLICY_F_PATH: (
        "| explicit cross-backend linking | `AUTH-ID-001G` |",
        "| upgrade and reconciliation workflow | `AUTH-ID-001H` |",
        "MERGE: UNSUPPORTED",
        "LIVE RELATIONSHIP MOVEMENT: UNSUPPORTED",
    ),
}

REGISTRY_ID_FIELDS = (
    "global_identity_id",
    "backend_principal_mapping_id",
    "login_identifier_alias_id",
)
CALLER_INPUT_TOKENS = (
    "request.json",
    "request.get_json",
    "request.form",
    "request.args",
    "request.values",
    "session[",
    "session.get",
    "argparse",
    "parse_args",
)
ORACLE_TOKENS = (
    "account_exists",
    "vendor_exists",
    "association_exists",
    "already_linked",
    "linked",
    "paired",
    "pairing_status",
    "global_identity_id",
    "subject_identity_id",
    "conflicting_identity_id",
    "conflict_subject_id",
    "existing_relation",
    "mapping_topology",
    "link_topology",
    "proof_failure",
    "approver_identity",
)
AUTHORITY_FIELDS = (
    "role",
    "site_permission",
    "sheet_permission",
    "vendor_name",
    "vendor_authority",
    "credential",
    "password",
    "session",
    "workflow_authority",
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
        description="Check the frozen identity-registry linking source and policy boundary."
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run disposable synthetic-source negative and positive controls.",
    )
    return parser.parse_args()


def normalized_path(path: Path, root: Path) -> Path:
    return Path(path.resolve().relative_to(root.resolve()))


def collapse(value: str) -> str:
    return " ".join(value.split())


def static_value(node: ast.AST, scopes: list[dict[str, Any]]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        for scope in reversed(scopes):
            if node.id in scope:
                value = scope[node.id]
                return None if value is UNKNOWN else value
        return None
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for item in node.values:
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                parts.append(item.value)
            elif isinstance(item, ast.FormattedValue):
                value = static_value(item.value, scopes)
                if not isinstance(value, (str, int)):
                    return None
                parts.append(str(value))
            else:
                return None
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = static_value(node.left, scopes)
        right = static_value(node.right, scopes)
        if isinstance(left, str) and isinstance(right, str):
            return left + right
        return None
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        values = [static_value(item, scopes) for item in node.elts]
        if any(value is None for value in values):
            return None
        return tuple(values)
    if isinstance(node, ast.Dict):
        keys = [static_value(item, scopes) for item in node.keys]
        values = [static_value(item, scopes) for item in node.values]
        if any(item is None for item in keys + values):
            return None
        return dict(zip(keys, values))
    return None


def symbol_name(stack: list[str]) -> str:
    return ".".join(stack) if stack else "<module>"


def is_linking_context(text: str, name: str = "") -> bool:
    value = f"{name}\n{text}".lower()
    symbol_value = name.lower()
    action = (
        r"(?:link|bind|binding|unify|associate|association|pair|pairing|"
        r"connect|connection|attach|attachment)"
    )
    entity = r"(?:account|principal|identity|registry|mapping|topology|backend)"
    strong_patterns = (
        r"(?<![a-z0-9])cross[_ -]?backend(?:[_ -]?account)?[_ -]?link",
        r"(?<![a-z0-9])identity[_ -]?link",
        rf"(?<![a-z0-9]){action}[_ -]?{entity}",
        rf"(?<![a-z0-9]){entity}[_ -]?{action}",
        r"(?<![a-z0-9])dedicated[_ -]?link[_ -]?author",
        r"(?<![a-z0-9])link[_ -]?(?:proof|approval|approver|challenge|authority)",
        r"(?<![a-z0-9])(?:association|pairing)[_ -]?(?:proof|token|store|challenge|authority|approver|permission)",
    )
    if any(re.search(pattern, value) for pattern in strong_patterns):
        return True
    registry_context = any(
        token in value
        for token in (
            "global_identity",
            "backend_principal_mapping",
            "login_identifier_alias",
        )
    )
    backend_pair = "internal" in value and "vendor" in value
    core_link_semantics = any(
        token in value
        for token in (
            "link",
            "bind",
            "binding",
            "associate",
            "association",
            "pair",
            "pairing",
            "subject_relation",
            "subject relation",
            "identity_equivalence",
            "identity equivalence",
            "topology",
        )
    )
    broad_synonyms = ("connect", "connection", "attach", "attachment", "unify")
    broad_context_semantics = (registry_context or backend_pair) and any(
        token in symbol_value for token in broad_synonyms
    )
    return (
        (registry_context or backend_pair) and core_link_semantics
    ) or broad_context_semantics


def has_authority_semantics(text: str) -> bool:
    lowered = text.lower().replace("permissionerror", "")
    return any(
        token in lowered
        for token in ("permission", "role", "authority", "approver", "override")
    )


def dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def string_literal(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def session_access_kind(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call):
        name = dotted_name(node.func)
        if name == "session.get" and node.args:
            key = string_literal(node.args[0])
            if key == "user_id":
                return "internal"
            if key == "vendor_account_id":
                return "vendor"
    if isinstance(node, ast.Subscript) and dotted_name(node.value) == "session":
        key = string_literal(node.slice)
        if key == "user_id":
            return "internal"
        if key == "vendor_account_id":
            return "vendor"
    return None


def authority_attributes(node: ast.AST) -> set[str]:
    return {
        item.attr
        for item in ast.walk(node)
        if isinstance(item, ast.Attribute) and item.attr in AUTHORITY_FIELDS
    }


def dict_authority_fields(node: ast.Dict) -> set[str]:
    return {
        key
        for key_node in node.keys
        if (key := string_literal(key_node)) in AUTHORITY_FIELDS
    }


def assignment_moves_authority(node: ast.Assign | ast.AnnAssign) -> bool:
    value = node.value
    if value is None or not authority_attributes(value):
        return False
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    if any(
        isinstance(target, ast.Attribute) and target.attr in AUTHORITY_FIELDS
        for target in targets
    ):
        return True
    if isinstance(value, ast.Dict) and dict_authority_fields(value):
        return True
    if isinstance(value, ast.Call) and any(
        keyword.arg in AUTHORITY_FIELDS
        for keyword in value.keywords
        if keyword.arg is not None
    ):
        return True
    return False


def function_session_evidence(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[set[str], set[str], bool]:
    aliases: dict[str, set[str]] = {}
    direct_kinds: set[str] = set()

    def expression_kinds(expression: ast.AST | None) -> set[str]:
        if expression is None:
            return set()
        direct = session_access_kind(expression)
        if direct:
            return {direct}
        if isinstance(expression, ast.Name):
            return set(aliases.get(expression.id, set()))
        supported = (
            ast.BoolOp,
            ast.Call,
            ast.Dict,
            ast.List,
            ast.Tuple,
            ast.Set,
            ast.BinOp,
            ast.UnaryOp,
            ast.Compare,
            ast.IfExp,
            ast.Attribute,
            ast.Subscript,
        )
        if not isinstance(expression, supported):
            return set()
        kinds: set[str] = set()
        for child in ast.iter_child_nodes(expression):
            kinds.update(expression_kinds(child))
        return kinds

    for item in ast.walk(node):
        kind = session_access_kind(item)
        if kind:
            direct_kinds.add(kind)

    assignments = sorted(
        (
            item
            for item in ast.walk(node)
            if isinstance(item, (ast.Assign, ast.AnnAssign))
        ),
        key=lambda item: int(getattr(item, "lineno", 0)),
    )
    for _ in range(len(assignments) + 1):
        changed = False
        for item in assignments:
            value = item.value
            if value is None:
                continue
            value_kinds = expression_kinds(value)
            if not value_kinds:
                continue
            targets = item.targets if isinstance(item, ast.Assign) else [item.target]
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                previous = aliases.setdefault(target.id, set())
                expanded = previous | value_kinds
                if expanded != previous:
                    aliases[target.id] = expanded
                    changed = True
        if not changed:
            break

    result_uses_both = False
    for item in ast.walk(node):
        if isinstance(item, ast.Return):
            sink_kinds = expression_kinds(item.value)
        elif isinstance(item, ast.Call):
            call_name = (dotted_name(item.func) or "").lower()
            if not any(
                token in call_name
                for token in (
                    "proof",
                    "eligible",
                    "eligibility",
                    "approve",
                    "equivalence",
                )
            ):
                continue
            sink_kinds = set()
            for argument in item.args:
                sink_kinds.update(expression_kinds(argument))
            for keyword in item.keywords:
                sink_kinds.update(expression_kinds(keyword.value))
        elif isinstance(item, (ast.Assign, ast.AnnAssign)):
            targets = item.targets if isinstance(item, ast.Assign) else [item.target]
            target_names = {
                target.id.lower() for target in targets if isinstance(target, ast.Name)
            }
            if not any(
                any(
                    token in target_name
                    for token in (
                        "proof",
                        "eligible",
                        "eligibility",
                        "approval",
                        "equivalence",
                    )
                )
                for target_name in target_names
            ):
                continue
            sink_kinds = expression_kinds(item.value)
        else:
            continue
        if {"internal", "vendor"} <= sink_kinds:
            result_uses_both = True
            break
    return direct_kinds, set(aliases), result_uses_both


def function_moves_authority(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    for item in ast.walk(node):
        if isinstance(item, (ast.Assign, ast.AnnAssign)) and assignment_moves_authority(
            item
        ):
            return True
        if isinstance(item, ast.Return) and item.value is not None:
            value = item.value
            if isinstance(value, ast.Attribute) and value.attr in AUTHORITY_FIELDS:
                return True
            if (
                isinstance(value, ast.Dict)
                and dict_authority_fields(value)
                and authority_attributes(value)
            ):
                return True
            if isinstance(value, ast.Call):
                call_name = (dotted_name(value.func) or "").lower()
                propagation_call = any(
                    token in call_name
                    for token in (
                        "copy",
                        "propagate",
                        "grant",
                        "assign",
                        "transfer",
                        "payload",
                        "result",
                    )
                )
                keyword_payload = any(
                    keyword.arg in AUTHORITY_FIELDS
                    for keyword in value.keywords
                    if keyword.arg is not None
                )
                if authority_attributes(value) and (
                    propagation_call or keyword_payload
                ):
                    return True
    return False


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

    def visit_Assign(self, node: ast.Assign) -> None:
        value = static_value(node.value, self.scopes)
        names: list[str] = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                names.append(target.id)
                self.scopes[-1][target.id] = value if value is not None else UNKNOWN
        source = ast.get_source_segment(self.source, node) or " ".join(names)
        self._check_assignment(node, source, names)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        names: list[str] = []
        if isinstance(node.target, ast.Name):
            names.append(node.target.id)
            if node.value is not None:
                value = static_value(node.value, self.scopes)
                self.scopes[-1][node.target.id] = value if value is not None else UNKNOWN
        source = ast.get_source_segment(self.source, node) or " ".join(names)
        self._check_assignment(node, source, names)
        self.generic_visit(node)

    def _check_assignment(self, node: ast.AST, source: str, names: list[str]) -> None:
        combined = f"{' '.join(names)}\n{source}".lower()
        if not is_linking_context(combined, symbol_name(self.symbols)):
            return
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and assignment_moves_authority(
            node
        ):
            self.add_issue(
                "forbidden_link_authority_inheritance",
                node,
                "linking assignment moves authority-bearing data between subjects",
            )
        if has_authority_semantics(combined):
            self.add_issue(
                "forbidden_link_authority_implementation",
                node,
                "linking authority or approval assignment appeared in runtime source",
            )
        if any(
            token in combined
            for token in ("proof", "token", "store", "challenge", "equivalence")
        ):
            self.add_issue(
                "forbidden_link_proof_implementation",
                node,
                "linking proof, challenge, store, or equivalence capability appeared",
            )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        source = ast.get_source_segment(self.source, node) or node.name
        self._check_function(node, source)
        self.symbols.append(node.name)
        self.scopes.append({})
        for statement in node.body:
            self.visit(statement)
        self.scopes.pop()
        self.symbols.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        source = ast.get_source_segment(self.source, node) or node.name
        lowered = source.lower()
        if is_linking_context(source, node.name):
            if any(token in lowered for token in ("proof", "challenge", "equivalence")):
                self.add_issue(
                    "forbidden_link_proof_implementation",
                    node,
                    "linking proof, challenge, store, or equivalence class appeared",
                )
            elif any(token in lowered for token in ("authority", "approver", "permission")):
                self.add_issue(
                    "forbidden_link_authority_implementation",
                    node,
                    "linking authority or approval class appeared",
                )
            else:
                self.add_issue(
                    "forbidden_linking_consumer",
                    node,
                    "linking service or orchestration class appeared",
                )
        self.symbols.append(node.name)
        self.scopes.append({})
        for statement in node.body:
            self.visit(statement)
        self.scopes.pop()
        self.symbols.pop()

    def _check_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        source: str,
    ) -> None:
        name = node.name.lower()
        lowered = source.lower()
        decorators = " ".join(ast.unparse(item).lower() for item in node.decorator_list)
        if not is_linking_context(source, name + " " + decorators):
            return

        is_route = (
            ".route" in decorators
            or (
                "api" in name
                and any(
                    token in name
                    for token in (
                        "link",
                        "bind",
                        "associate",
                        "pair",
                        "connect",
                        "attach",
                        "identity",
                    )
                )
            )
            or (
                "form" in name
                and any(
                    token in name
                    for token in (
                        "link",
                        "bind",
                        "associate",
                        "pair",
                        "connect",
                        "attach",
                        "identity",
                    )
                )
            )
        )
        is_cli = self.path.parts[:1] == ("tools",) and (
            any(
                option in lowered
                for option in (
                    "--link",
                    "--bind",
                    "--associate",
                    "--pair",
                    "--connect",
                    "--attach",
                )
            )
            or (
                "argparse" in lowered
                and any(
                    token in name
                    for token in (
                        "link",
                        "bind",
                        "associate",
                        "pair",
                        "connect",
                        "attach",
                    )
                )
            )
            or (
                "parse_args" in lowered
                and any(
                    token in lowered
                    for token in (
                        "link",
                        "bind",
                        "associate",
                        "pair",
                        "connect",
                        "attach",
                    )
                )
            )
        )
        proof_context = any(
            token in lowered
            for token in (
                "proof",
                "token",
                "challenge",
                "store",
                "identity_equivalence",
                "identity equivalence",
                "link_equivalence",
                "equivalence_approval",
                "account_control_proof",
            )
        )
        authority_text = lowered.replace("permissionerror", "")
        authority_context = any(
            token in authority_text
            for token in ("authority", "approver", "permission", "override")
        ) or ("authorize" in name and "role" in lowered)

        if is_route:
            self.add_issue(
                "forbidden_linking_route",
                node,
                "linking route, API, or form handler is not authorized",
            )
        if is_cli:
            self.add_issue(
                "forbidden_linking_cli",
                node,
                "linking command-line entry or option is not authorized",
            )
        if authority_context:
            self.add_issue(
                "forbidden_link_authority_implementation",
                node,
                "linking authority, approver, permission, or override capability appeared",
            )
        if proof_context:
            self.add_issue(
                "forbidden_link_proof_implementation",
                node,
                "linking proof, challenge, store, consumption, or equivalence capability appeared",
            )

        caller_source = any(token in lowered for token in CALLER_INPUT_TOKENS)
        caller_id = any(token in lowered for token in REGISTRY_ID_FIELDS)
        if caller_source and caller_id:
            self.add_issue(
                "forbidden_caller_selected_link_id",
                node,
                "linking input accepts a caller-selected registry identifier",
            )

        session_kinds, _session_aliases, result_uses_both_sessions = (
            function_session_evidence(node)
        )
        internal_session = "internal" in session_kinds or any(
            token in lowered
            for token in (
                "internal_session",
                "internal_user_session",
                "session.get(\"user_id\")",
                "session.get('user_id')",
                'session["user_id"]',
                "session['user_id']",
            )
        )
        vendor_session = "vendor" in session_kinds or any(
            token in lowered
            for token in (
                "vendor_session",
                "vendor_account_session",
                "session.get(\"vendor_account_id\")",
                "session.get('vendor_account_id')",
                'session["vendor_account_id"]',
                "session['vendor_account_id']",
            )
        )
        mixed_as_proof = any(
            token in lowered
            for token in (
                "proof",
                "equivalence",
                "eligible",
                "eligibility",
                "approve",
                "authorization",
            )
        ) or result_uses_both_sessions
        if internal_session and vendor_session and mixed_as_proof:
            self.add_issue(
                "forbidden_mixed_session_link_proof",
                node,
                "internal and vendor session state is used as linking proof or eligibility",
            )

        inheritance_subject = any(token in lowered for token in AUTHORITY_FIELDS)
        inheritance_action = any(
            token in lowered
            for token in ("inherit", "copy", "propagate", "grant", "assign", "transfer")
        )
        inheritance_movement = function_moves_authority(node)
        if inheritance_subject and (inheritance_action or inheritance_movement):
            self.add_issue(
                "forbidden_link_authority_inheritance",
                node,
                "linking attempts to inherit credential, session, role, permission, or business authority",
            )

        public_context = is_route or "public" in name or "response" in name
        if public_context and any(token in lowered for token in ORACLE_TOKENS):
            self.add_issue(
                "forbidden_linking_oracle",
                node,
                "public linking response exposes account, proof, identity, or topology state",
            )

        specialized = (
            is_route
            or is_cli
            or authority_context
            or proof_context
            or (caller_source and caller_id)
            or (internal_session and vendor_session and mixed_as_proof)
            or (inheritance_subject and (inheritance_action or inheritance_movement))
        )
        if not specialized:
            self.add_issue(
                "forbidden_linking_consumer",
                node,
                "linking service, helper, resolver, or orchestration capability appeared",
            )


def read_text(root: Path, path: Path, missing_code: str) -> tuple[str | None, Issue | None]:
    target = root / path
    if not target.is_file():
        return None, Issue(
            code=missing_code,
            file=path.as_posix(),
            line=1,
            symbol="<document>",
            reason="required frozen document is missing",
        )
    try:
        return target.read_text(encoding="utf-8"), None
    except (OSError, UnicodeError):
        return None, Issue(
            code=missing_code,
            file=path.as_posix(),
            line=1,
            symbol="<document>",
            reason="required frozen document is not readable UTF-8",
        )


def check_linking_policy(root: Path) -> list[Issue]:
    source, issue = read_text(root, POLICY_G_PATH, "linking_policy_document_missing")
    if issue:
        return [issue]
    assert source is not None
    normalized = collapse(source)
    issues: list[Issue] = []

    for marker in G_POLICY_MARKERS:
        if collapse(marker) not in normalized:
            code = (
                "link_owner_boundary_drift"
                if marker in G_OWNER_MARKERS
                else "linking_policy_marker_missing"
            )
            issues.append(
                Issue(
                    code=code,
                    file=POLICY_G_PATH.as_posix(),
                    line=1,
                    symbol="<document>",
                    reason=f"required frozen linking marker is missing: {marker}",
                )
            )

    metadata = {}
    for index, line in enumerate(source.splitlines()[:8], 1):
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = (value.strip(), index)
    expected_metadata = {
        "Status": "design baseline",
        "Scope": "docs-only",
        "Implementation status": "not started",
    }
    for key, expected in expected_metadata.items():
        value, line = metadata.get(key, ("<missing>", 1))
        if value != expected:
            issues.append(
                Issue(
                    code="linking_status_drift",
                    file=POLICY_G_PATH.as_posix(),
                    line=line,
                    symbol="<document>",
                    reason=f"{key} must remain {expected}",
                )
            )

    for index, line in enumerate(source.splitlines(), 1):
        lowered = collapse(line).lower()
        if re.search(
            r"\bauth-id-001g\b.{0,80}\b(?:implemented|closed)\b",
            lowered,
        ) and not any(token in lowered for token in ("not implemented", "not closed", "must not")):
            issues.append(
                Issue(
                    code="linking_status_drift",
                    file=POLICY_G_PATH.as_posix(),
                    line=index,
                    symbol="<document>",
                    reason="AUTH-ID-001G was marked implemented or closed",
                )
            )
        if re.search(
            r"\bdedicated link authority\s*:\s*(?:assigned|enabled|implemented)\b",
            lowered,
        ) or re.search(
            r"\b(?:administrator|site administrator|production operator|operator)\b"
            r".{0,50}\b(?:has|receives|is assigned)\b.{0,30}\blink authority\b",
            lowered,
        ):
            issues.append(
                Issue(
                    code="link_authority_claim_drift",
                    file=POLICY_G_PATH.as_posix(),
                    line=index,
                    symbol="<document>",
                    reason="frozen document claims an implemented or assigned linking authority",
                )
            )
        if re.search(
            r"\blink(?:ing)? consumer\s*:\s*(?:exists|implemented|enabled)\b",
            lowered,
        ):
            issues.append(
                Issue(
                    code="link_authority_claim_drift",
                    file=POLICY_G_PATH.as_posix(),
                    line=index,
                    symbol="<document>",
                    reason="frozen document claims that a linking consumer exists",
                )
            )
        if re.search(
            r"\bproduction (?:link state|registry rows|mappings|mapping topology)"
            r"\s*:\s*(?:confirmed|verified|known|empty|linked)\b",
            lowered,
        ):
            issues.append(
                Issue(
                    code="link_production_claim_drift",
                    file=POLICY_G_PATH.as_posix(),
                    line=index,
                    symbol="<document>",
                    reason="Production linking or registry state was claimed without evidence",
                )
            )
    return issues


def check_owner_boundaries(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    for path, markers in UPSTREAM_POLICY_MARKERS.items():
        source, issue = read_text(root, path, "link_owner_boundary_drift")
        if issue:
            issues.append(issue)
            continue
        assert source is not None
        normalized = collapse(source)
        for marker in markers:
            if collapse(marker) not in normalized:
                issues.append(
                    Issue(
                        code="link_owner_boundary_drift",
                        file=path.as_posix(),
                        line=1,
                        symbol="<document>",
                        reason=f"upstream owner boundary marker is missing: {marker}",
                    )
                )
    return issues


def canonical_fingerprint_bytes(payload: bytes) -> bytes | None:
    if b"\r" not in payload:
        return payload
    index = 0
    while index < len(payload):
        value = payload[index]
        if value == 13:
            if index + 1 >= len(payload) or payload[index + 1] != 10:
                return None
            index += 2
            continue
        if value == 10:
            return None
        index += 1
    return payload.replace(b"\r\n", b"\n")


def check_lifecycle_guard(root: Path) -> list[Issue]:
    path = root / LIFECYCLE_CHECKER_PATH
    if not path.is_file():
        return [
            Issue(
                code="upstream_lifecycle_guard_drift",
                file=LIFECYCLE_CHECKER_PATH.as_posix(),
                line=1,
                symbol="<module>",
                reason="approved lifecycle readiness checker is missing",
            )
        ]
    try:
        canonical = canonical_fingerprint_bytes(path.read_bytes())
        digest = (
            hashlib.sha256(canonical).hexdigest().upper()
            if canonical is not None
            else "<invalid-line-endings>"
        )
    except OSError:
        digest = "<unreadable>"
    if digest != APPROVED_LIFECYCLE_CHECKER_SHA256:
        return [
            Issue(
                code="upstream_lifecycle_guard_drift",
                file=LIFECYCLE_CHECKER_PATH.as_posix(),
                line=1,
                symbol="<module>",
                reason="lifecycle readiness checker fingerprint changed; independent review is required",
            )
        ]
    return []


def python_sources(root: Path) -> list[Path]:
    result: list[Path] = []
    for path in root.rglob("*.py"):
        relative = normalized_path(path, root)
        if any(part in {".git", ".codex", "__pycache__"} for part in relative.parts):
            continue
        if relative.parts[:1] == ("tests",):
            continue
        if relative in {CHECKER_PATH, LIFECYCLE_CHECKER_PATH}:
            continue
        result.append(path)
    return sorted(result)


def analyze_repository(root: Path) -> list[Issue]:
    issues = check_linking_policy(root)
    issues.extend(check_owner_boundaries(root))
    issues.extend(check_lifecycle_guard(root))
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
    consumer_codes = {
        "forbidden_linking_route",
        "forbidden_linking_cli",
        "forbidden_linking_consumer",
        "forbidden_caller_selected_link_id",
    }
    session_codes = {
        "forbidden_mixed_session_link_proof",
        "forbidden_link_authority_inheritance",
    }
    policy_codes = {
        "linking_policy_document_missing",
        "linking_policy_marker_missing",
        "linking_status_drift",
        "link_authority_claim_drift",
        "link_owner_boundary_drift",
        "link_production_claim_drift",
    }
    lines = [
        "identity_registry_linking_readiness_scope: static_source_and_frozen_policy_only",
        f"issues_count: {len(issues)}",
        f"linking_consumer_boundary: {'PASS' if not any(i.code in consumer_codes for i in issues) else 'FAIL'}",
        f"dedicated_authority_boundary: {'PASS' if not any(i.code == 'forbidden_link_authority_implementation' for i in issues) else 'FAIL'}",
        f"proof_boundary: {'PASS' if not any(i.code == 'forbidden_link_proof_implementation' for i in issues) else 'FAIL'}",
        f"session_and_inheritance_boundary: {'PASS' if not any(i.code in session_codes for i in issues) else 'FAIL'}",
        f"oracle_boundary: {'PASS' if not any(i.code == 'forbidden_linking_oracle' for i in issues) else 'FAIL'}",
        f"frozen_linking_policy_boundary: {'PASS' if not any(i.code in policy_codes for i in issues) else 'FAIL'}",
        f"upstream_lifecycle_guard_boundary: {'PASS' if not any(i.code == 'upstream_lifecycle_guard_drift' for i in issues) else 'FAIL'}",
        "database_access: 0",
        "app_imports: 0",
    ]
    if issues:
        lines.append("FAIL identity registry linking readiness:")
        for issue in issues:
            lines.append(
                f"- {issue.code} file={issue.file} line={issue.line} "
                f"symbol={issue.symbol} reason={issue.reason}"
            )
        return 1, "\n".join(lines) + "\n"
    lines.append(PASS_MARKER)
    return 0, "\n".join(lines) + "\n"


def write_base_tree(root: Path) -> None:
    for relative in (POLICY_E_PATH, POLICY_F_PATH, POLICY_G_PATH, LIFECYCLE_CHECKER_PATH):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT_DIR / relative, target)
    app_source = """\
def html_link(url):
    return '<a href="' + url + '">open</a>'

CSRF_TOKEN_NAME = "csrf_token"
LOGIN_TOKEN_NAME = "login_token"

def reject_mixed_backend_session(internal_session, vendor_session):
    if internal_session and vendor_session:
        raise PermissionError("mixed session denied")
    return False

def read_global_identity_id(row):
    return row["global_identity_id"]
"""
    (root / "app.py").write_text(app_source, encoding="utf-8", newline="\n")


def add_source(root: Path, relative: str, source: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8", newline="\n")


def positive_cases() -> list[tuple[str, str, str]]:
    return [
        (
            "ordinary_html_link",
            "services/html.py",
            "def link_to_page(url):\n    return '<a href=\"' + url + '\">page</a>'\n",
        ),
        (
            "ordinary_url_helper",
            "services/urls.py",
            "def build_account_url(account_id):\n"
            "    return '/accounts/' + str(account_id)\n",
        ),
        (
            "unrelated_network_connection",
            "services/network.py",
            "def connect_network_socket(host, port):\n"
            "    return open_socket(host, port)\n",
        ),
        (
            "unrelated_object_pairing",
            "services/objects.py",
            "def pair_objects(left, right):\n"
            "    return (left, right)\n",
        ),
        (
            "read_only_authority_comparison",
            "services/audit.py",
            "def compare_actor_roles_for_audit(source, target):\n"
            "    return source.role == target.role\n",
        ),
        (
            "ordinary_login_token",
            "services/login_tokens.py",
            "def verify_login_token(login_token):\n    return bool(login_token)\n",
        ),
        (
            "ordinary_csrf_challenge",
            "services/csrf.py",
            "def verify_csrf_challenge(csrf_token):\n    return bool(csrf_token)\n",
        ),
        (
            "server_read_only_id",
            "services/registry_read.py",
            "def read_global_identity_id(row):\n    return row['global_identity_id']\n",
        ),
        (
            "mixed_session_fail_closed",
            "services/session_guard.py",
            "def reject_ambiguous_actor_session(internal_marker, vendor_marker):\n"
            "    if internal_marker and vendor_marker:\n"
            "        raise PermissionError('ambiguous actor session')\n",
        ),
        (
            "unrelated_single_session_alias",
            "services/session_read.py",
            "def current_internal_actor():\n"
            "    internal_actor = session.get('user_id')\n"
            "    decision = internal_actor\n"
            "    return decision\n",
        ),
        (
            "tests_rule_text_ignored",
            "tests/test_linking_rules.py",
            "def test_link_accounts():\n    return {'already_linked': True}\n",
        ),
    ]


def negative_source_cases() -> list[tuple[str, str, str, str]]:
    return [
        (
            "explicit_linking_route",
            "app_extra.py",
            "@app.route('/registry/link')\ndef link_identity_accounts():\n    return {}\n",
            "forbidden_linking_route",
        ),
        (
            "alternate_linking_api",
            "routes/api_extra.py",
            "def api_identity_bind():\n    internal_principal = 1\n    vendor_principal = 2\n    return {'ok': True}\n",
            "forbidden_linking_route",
        ),
        (
            "automatic_cross_backend_helper",
            "services/registry_ops.py",
            "def automatic_cross_backend_link():\n    return True\n",
            "forbidden_linking_consumer",
        ),
        (
            "generic_topology_orchestrator",
            "services/registry_ops.py",
            "def orchestrate_registry_link_topology(internal_principal, vendor_principal):\n    return (internal_principal, vendor_principal)\n",
            "forbidden_linking_consumer",
        ),
        (
            "association_route",
            "routes/association.py",
            "@app.route('/identity/associate')\n"
            "def associate_accounts():\n"
            "    return {}\n",
            "forbidden_linking_route",
        ),
        (
            "pair_internal_vendor_accounts",
            "services/association.py",
            "def pair_internal_vendor_accounts(internal, vendor):\n"
            "    return create_subject_relation(internal, vendor)\n",
            "forbidden_linking_consumer",
        ),
        (
            "attach_backend_principals",
            "services/association.py",
            "def attach_backend_principals(internal, vendor):\n"
            "    return create_subject_relation(internal, vendor)\n",
            "forbidden_linking_consumer",
        ),
        (
            "connect_identity_accounts",
            "services/association.py",
            "def connect_identity_accounts(internal, vendor):\n"
            "    return create_subject_relation(internal, vendor)\n",
            "forbidden_linking_consumer",
        ),
        (
            "binding_backend_principals",
            "services/association.py",
            "def binding_backend_principals(internal, vendor):\n"
            "    return create_subject_relation(internal, vendor)\n",
            "forbidden_linking_consumer",
        ),
        (
            "identity_account_connection",
            "services/association.py",
            "def identity_account_connection(internal, vendor):\n"
            "    return create_subject_relation(internal, vendor)\n",
            "forbidden_linking_consumer",
        ),
        (
            "backend_principal_attachment",
            "services/association.py",
            "def backend_principal_attachment(internal, vendor):\n"
            "    return create_subject_relation(internal, vendor)\n",
            "forbidden_linking_consumer",
        ),
        (
            "subject_relation_consumer",
            "services/association.py",
            "def create_subject_relation(internal, vendor):\n"
            "    return SubjectRelation(internal, vendor)\n",
            "forbidden_linking_consumer",
        ),
        (
            "connect_internal_vendor_accounts",
            "services/association.py",
            "def connect_internal_vendor_accounts(internal, vendor):\n"
            "    return (internal, vendor)\n",
            "forbidden_linking_consumer",
        ),
        (
            "internal_vendor_connection",
            "services/association.py",
            "def internal_vendor_connection(internal, vendor):\n"
            "    return (internal, vendor)\n",
            "forbidden_linking_consumer",
        ),
        (
            "attach_internal_vendor_accounts",
            "services/association.py",
            "def attach_internal_vendor_accounts(internal, vendor):\n"
            "    return (internal, vendor)\n",
            "forbidden_linking_consumer",
        ),
        (
            "internal_vendor_attachment",
            "services/association.py",
            "def internal_vendor_attachment(internal, vendor):\n"
            "    return (internal, vendor)\n",
            "forbidden_linking_consumer",
        ),
        (
            "unify_internal_vendor_accounts",
            "services/association.py",
            "def unify_internal_vendor_accounts(internal, vendor):\n"
            "    return (internal, vendor)\n",
            "forbidden_linking_consumer",
        ),
        (
            "linking_cli",
            "tools/registry_link.py",
            "import argparse\ndef apply_identity_link_cli():\n    parser = argparse.ArgumentParser()\n    parser.add_argument('--link', action='store_true')\n",
            "forbidden_linking_cli",
        ),
        (
            "admin_authority",
            "services/link_auth.py",
            "def authorize_identity_link(actor):\n    link_authority = actor.role == 'admin'\n    return link_authority\n",
            "forbidden_link_authority_implementation",
        ),
        (
            "site_admin_authority",
            "services/link_auth.py",
            "def authorize_identity_link(actor):\n    link_authority = actor.role == 'site-admin'\n    return link_authority\n",
            "forbidden_link_authority_implementation",
        ),
        (
            "operator_override",
            "services/link_auth.py",
            "def identity_link_operator_override(operator):\n    return operator.is_production_operator\n",
            "forbidden_link_authority_implementation",
        ),
        (
            "approval_permission",
            "services/link_auth.py",
            "LINK_APPROVAL_PERMISSION = 'identity.link.approve'\n",
            "forbidden_link_authority_implementation",
        ),
        (
            "dedicated_authority_assignment",
            "services/link_auth.py",
            "DEDICATED_LINK_AUTHORITY = 'admin'\n",
            "forbidden_link_authority_implementation",
        ),
        (
            "association_permission",
            "services/association_auth.py",
            "IDENTITY_ASSOCIATION_PERMISSION = 'identity.associate'\n",
            "forbidden_link_authority_implementation",
        ),
        (
            "pairing_approver_role",
            "services/association_auth.py",
            "ACCOUNT_PAIRING_APPROVER_ROLE = 'admin'\n",
            "forbidden_link_authority_implementation",
        ),
        (
            "pairing_challenge_store",
            "services/association_proof.py",
            "class AccountPairingChallengeStore:\n"
            "    pass\n",
            "forbidden_link_proof_implementation",
        ),
        (
            "association_token",
            "services/association_proof.py",
            "def issue_account_association_token():\n"
            "    return 'token'\n",
            "forbidden_link_proof_implementation",
        ),
        (
            "link_proof_token",
            "services/link_proof.py",
            "def issue_identity_link_proof_token():\n    return 'token'\n",
            "forbidden_link_proof_implementation",
        ),
        (
            "challenge_issue",
            "services/link_proof.py",
            "def issue_link_challenge():\n    return object()\n",
            "forbidden_link_proof_implementation",
        ),
        (
            "challenge_verify",
            "services/link_proof.py",
            "def verify_link_challenge(challenge):\n    return True\n",
            "forbidden_link_proof_implementation",
        ),
        (
            "challenge_consume",
            "services/link_proof.py",
            "def consume_link_challenge(challenge):\n    return True\n",
            "forbidden_link_proof_implementation",
        ),
        (
            "proof_store",
            "services/link_proof.py",
            "class IdentityLinkProofStore:\n    pass\n",
            "forbidden_link_proof_implementation",
        ),
        (
            "equivalence_approval",
            "services/link_proof.py",
            "def approve_identity_link_equivalence(internal_principal, vendor_principal):\n    return True\n",
            "forbidden_link_proof_implementation",
        ),
        (
            "caller_json_global_id",
            "routes/link.py",
            "def api_link_accounts():\n    global_identity_id = request.json['global_identity_id']\n    return global_identity_id\n",
            "forbidden_caller_selected_link_id",
        ),
        (
            "caller_form_mapping_id",
            "routes/link.py",
            "def identity_link_form():\n    backend_principal_mapping_id = request.form['backend_principal_mapping_id']\n    return backend_principal_mapping_id\n",
            "forbidden_caller_selected_link_id",
        ),
        (
            "caller_cli_alias_id",
            "tools/link_cli.py",
            "import argparse\ndef identity_link_cli():\n    parser = argparse.ArgumentParser()\n    parser.add_argument('--link')\n    args = parser.parse_args()\n    return args.login_identifier_alias_id\n",
            "forbidden_caller_selected_link_id",
        ),
        (
            "mixed_session_proof",
            "services/link_proof.py",
            "def identity_link_session_proof(internal_session, vendor_session):\n    return internal_session and vendor_session\n",
            "forbidden_mixed_session_link_proof",
        ),
        (
            "mixed_session_subscript_eligibility",
            "services/link_proof.py",
            "def identity_link_eligibility():\n"
            "    return session['user_id'] and session['vendor_account_id']\n",
            "forbidden_mixed_session_link_proof",
        ),
        (
            "mixed_session_get_aliases",
            "services/link_proof.py",
            "def account_pairing_eligibility():\n"
            "    internal_actor = session.get('user_id')\n"
            "    vendor_actor = session.get('vendor_account_id')\n"
            "    return internal_actor and vendor_actor\n",
            "forbidden_mixed_session_link_proof",
        ),
        (
            "mixed_session_derived_alias_returned",
            "services/link_proof.py",
            "def associate_accounts():\n"
            "    internal_actor = session.get('user_id')\n"
            "    vendor_actor = session.get('vendor_account_id')\n"
            "    decision = internal_actor and vendor_actor\n"
            "    return decision\n",
            "forbidden_mixed_session_link_proof",
        ),
        (
            "mixed_session_derived_alias_proof_call",
            "services/link_proof.py",
            "def account_pairing_eligibility():\n"
            "    internal_actor = session.get('user_id')\n"
            "    vendor_actor = session.get('vendor_account_id')\n"
            "    decision = {'internal': internal_actor, 'vendor': vendor_actor}\n"
            "    return evaluate_link_eligibility(decision)\n",
            "forbidden_mixed_session_link_proof",
        ),
        (
            "mixed_session_bracket_derived_alias",
            "services/link_proof.py",
            "def associate_accounts():\n"
            "    internal_actor = session['user_id']\n"
            "    vendor_actor = session['vendor_account_id']\n"
            "    decision = (internal_actor, vendor_actor)\n"
            "    return decision\n",
            "forbidden_mixed_session_link_proof",
        ),
        (
            "role_inheritance",
            "services/link_ops.py",
            "def link_identity_accounts(source):\n    inherited_role = source.role\n    return inherited_role\n",
            "forbidden_link_authority_inheritance",
        ),
        (
            "site_permission_inheritance",
            "services/link_ops.py",
            "def link_identity_accounts(source):\n    return copy(source.site_permission)\n",
            "forbidden_link_authority_inheritance",
        ),
        (
            "sheet_permission_inheritance",
            "services/link_ops.py",
            "def link_identity_accounts(source):\n    return inherit(source.sheet_permission)\n",
            "forbidden_link_authority_inheritance",
        ),
        (
            "vendor_authority_inheritance",
            "services/link_ops.py",
            "def link_identity_accounts(source):\n    return transfer(source.vendor_authority, source.vendor_name)\n",
            "forbidden_link_authority_inheritance",
        ),
        (
            "credential_inheritance",
            "services/link_ops.py",
            "def link_identity_accounts(source):\n    return copy(source.credential, source.password)\n",
            "forbidden_link_authority_inheritance",
        ),
        (
            "session_inheritance",
            "services/link_ops.py",
            "def link_identity_accounts(source):\n    return propagate(source.session)\n",
            "forbidden_link_authority_inheritance",
        ),
        (
            "direct_role_assignment",
            "services/association.py",
            "def associate_accounts(source, target):\n"
            "    target.role = source.role\n",
            "forbidden_link_authority_inheritance",
        ),
        (
            "direct_site_permission_assignment",
            "services/association.py",
            "def associate_accounts(source, target):\n"
            "    target.site_permission = source.site_permission\n",
            "forbidden_link_authority_inheritance",
        ),
        (
            "direct_sheet_permission_assignment",
            "services/association.py",
            "def associate_accounts(source, target):\n"
            "    target.sheet_permission = source.sheet_permission\n",
            "forbidden_link_authority_inheritance",
        ),
        (
            "direct_vendor_name_assignment",
            "services/association.py",
            "def associate_accounts(source, target):\n"
            "    target.vendor_name = source.vendor_name\n",
            "forbidden_link_authority_inheritance",
        ),
        (
            "direct_session_assignment",
            "services/association.py",
            "def associate_accounts(source, target):\n"
            "    target.session = source.session\n",
            "forbidden_link_authority_inheritance",
        ),
        (
            "authority_dict_payload",
            "services/association.py",
            "def pair_accounts(source, target):\n"
            "    payload = {'role': source.role, 'site_permission': source.site_permission}\n"
            "    return create_subject_relation(target, payload)\n",
            "forbidden_link_authority_inheritance",
        ),
        (
            "authority_object_payload",
            "services/association.py",
            "def pair_accounts(source, target):\n"
            "    return SubjectRelation(target=target, role=source.role)\n",
            "forbidden_link_authority_inheritance",
        ),
        (
            "account_existence_oracle",
            "routes/link.py",
            "@app.route('/registry/link')\ndef public_identity_link_response():\n    return {'account_exists': True}\n",
            "forbidden_linking_oracle",
        ),
        (
            "already_linked_oracle",
            "routes/link.py",
            "@app.route('/registry/link')\ndef public_identity_link_response():\n    return {'already_linked': True}\n",
            "forbidden_linking_oracle",
        ),
        (
            "global_identity_oracle",
            "routes/link.py",
            "@app.route('/registry/link')\ndef public_identity_link_response():\n    return {'global_identity_id': 'x'}\n",
            "forbidden_linking_oracle",
        ),
        (
            "conflicting_identity_oracle",
            "routes/link.py",
            "@app.route('/registry/link')\ndef public_identity_link_response():\n    return {'conflicting_identity_id': 'x'}\n",
            "forbidden_linking_oracle",
        ),
        (
            "proof_failure_oracle",
            "routes/link.py",
            "@app.route('/registry/link')\ndef public_identity_link_response():\n    return {'proof_failure': 'expired'}\n",
            "forbidden_linking_oracle",
        ),
        (
            "association_exists_oracle",
            "routes/association.py",
            "@app.route('/identity/associate')\n"
            "def public_account_association_response():\n"
            "    return {'association_exists': True}\n",
            "forbidden_linking_oracle",
        ),
        (
            "paired_oracle",
            "routes/association.py",
            "@app.route('/identity/pair')\n"
            "def public_account_pairing_response():\n"
            "    return {'paired': True}\n",
            "forbidden_linking_oracle",
        ),
        (
            "pairing_status_oracle",
            "routes/association.py",
            "@app.route('/identity/pair')\n"
            "def public_account_pairing_response():\n"
            "    return {'pairing_status': 'existing'}\n",
            "forbidden_linking_oracle",
        ),
        (
            "subject_identity_oracle",
            "routes/association.py",
            "@app.route('/identity/associate')\n"
            "def public_account_association_response():\n"
            "    return {'subject_identity_id': 'x'}\n",
            "forbidden_linking_oracle",
        ),
        (
            "existing_relation_oracle",
            "routes/association.py",
            "@app.route('/identity/associate')\n"
            "def public_account_association_response():\n"
            "    return {'existing_relation': True}\n",
            "forbidden_linking_oracle",
        ),
        (
            "conflict_subject_oracle",
            "routes/association.py",
            "@app.route('/identity/associate')\n"
            "def public_account_association_response():\n"
            "    return {'conflict_subject_id': 'x'}\n",
            "forbidden_linking_oracle",
        ),
        (
            "runtime_test_named_bypass",
            "services/test_link_fixture.py",
            "def test_link_accounts():\n    return True\n",
            "forbidden_linking_consumer",
        ),
        (
            "guarded_linking_consumer",
            "services/link_ops.py",
            "def link_identity_accounts(actor, internal, vendor):\n"
            "    if actor is None:\n"
            "        raise PermissionError('denied')\n"
            "    return save_subject_relation(internal, vendor)\n",
            "forbidden_linking_consumer",
        ),
        (
            "proof_with_validation_branch",
            "services/link_proof.py",
            "def issue_identity_link_proof_token(actor):\n"
            "    if actor is None:\n"
            "        raise PermissionError('denied')\n"
            "    return 'token'\n",
            "forbidden_link_proof_implementation",
        ),
        (
            "proof_with_no_write_return_branch",
            "services/link_proof.py",
            "def issue_identity_link_proof_token(actor):\n"
            "    if actor is None:\n"
            "        return False\n"
            "    return 'token'\n",
            "forbidden_link_proof_implementation",
        ),
        (
            "guarded_authority_assignment",
            "services/link_auth.py",
            "def authorize_identity_link(actor):\n"
            "    if actor is None:\n"
            "        return False\n"
            "    link_authority = actor.role == 'admin'\n"
            "    return link_authority\n",
            "forbidden_link_authority_implementation",
        ),
        (
            "guarded_mixed_session_proof",
            "services/link_proof.py",
            "def approve_identity_link(internal_session, vendor_session, candidate):\n"
            "    if candidate is None:\n"
            "        return False\n"
            "    proof = internal_session and vendor_session\n"
            "    return proof\n",
            "forbidden_mixed_session_link_proof",
        ),
        (
            "guarded_caller_selected_id",
            "routes/link.py",
            "def api_link_accounts():\n"
            "    if request.json is None:\n"
            "        abort(403)\n"
            "    global_identity_id = request.json['global_identity_id']\n"
            "    return global_identity_id\n",
            "forbidden_caller_selected_link_id",
        ),
        (
            "guarded_authority_inheritance",
            "services/link_ops.py",
            "def link_identity_accounts(source):\n"
            "    if source is None:\n"
            "        raise PermissionError('denied')\n"
            "    return copy(source.role)\n",
            "forbidden_link_authority_inheritance",
        ),
        (
            "guarded_public_oracle",
            "routes/link.py",
            "@app.route('/registry/link')\n"
            "def public_identity_link_response(candidate):\n"
            "    if candidate is None:\n"
            "        return False\n"
            "    return {'account_exists': True}\n",
            "forbidden_linking_oracle",
        ),
    ]


def run_self_test() -> int:
    scenario_count = 0
    with tempfile.TemporaryDirectory(prefix="auth-id-001g-linking-readiness-self-test-") as temp:
        base = Path(temp) / "base"
        base.mkdir()
        write_base_tree(base)
        baseline_issues = analyze_repository(base)
        if baseline_issues:
            raise AssertionError(f"positive baseline failed: {baseline_issues}")
        scenario_count += 1

        for name, relative, source in positive_cases():
            case_root = Path(temp) / f"positive-{name}"
            shutil.copytree(base, case_root)
            add_source(case_root, relative, source)
            issues = analyze_repository(case_root)
            if issues:
                raise AssertionError(f"positive case {name} failed: {issues}")
            scenario_count += 1

        for name, relative, source, expected_code in negative_source_cases():
            case_root = Path(temp) / f"negative-{name}"
            shutil.copytree(base, case_root)
            add_source(case_root, relative, source)
            issues = analyze_repository(case_root)
            codes = {issue.code for issue in issues}
            exit_code, output = render_normal(issues)
            if expected_code not in codes or exit_code == 0 or PASS_MARKER in output:
                raise AssertionError(
                    f"negative case {name} did not fail closed with {expected_code}: {issues}"
                )
            scenario_count += 1

        special_cases: list[tuple[str, Path, str]] = []

        missing_g = Path(temp) / "negative-missing-g"
        shutil.copytree(base, missing_g)
        (missing_g / POLICY_G_PATH).unlink()
        special_cases.append(
            ("missing_g", missing_g, "linking_policy_document_missing")
        )

        status_changed = Path(temp) / "negative-status-changed"
        shutil.copytree(base, status_changed)
        path = status_changed / POLICY_G_PATH
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "Implementation status: not started",
                "Implementation status: implemented",
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )
        special_cases.append(("status_changed", status_changed, "linking_status_drift"))

        marked_closed = Path(temp) / "negative-marked-closed"
        shutil.copytree(base, marked_closed)
        path = marked_closed / POLICY_G_PATH
        path.write_text(
            path.read_text(encoding="utf-8") + "\nAUTH-ID-001G: CLOSED\n",
            encoding="utf-8",
            newline="\n",
        )
        special_cases.append(("marked_closed", marked_closed, "linking_status_drift"))

        authority_assigned = Path(temp) / "negative-authority-assigned"
        shutil.copytree(base, authority_assigned)
        path = authority_assigned / POLICY_G_PATH
        path.write_text(
            path.read_text(encoding="utf-8") + "\nDedicated link authority: assigned\n",
            encoding="utf-8",
            newline="\n",
        )
        special_cases.append(
            ("authority_assigned", authority_assigned, "link_authority_claim_drift")
        )

        consumer_claim = Path(temp) / "negative-consumer-claim"
        shutil.copytree(base, consumer_claim)
        path = consumer_claim / POLICY_G_PATH
        path.write_text(
            path.read_text(encoding="utf-8") + "\nLinking consumer: exists\n",
            encoding="utf-8",
            newline="\n",
        )
        special_cases.append(
            ("consumer_claim", consumer_claim, "link_authority_claim_drift")
        )

        e2_owner_drift = Path(temp) / "negative-e2-owner"
        shutil.copytree(base, e2_owner_drift)
        path = e2_owner_drift / POLICY_G_PATH
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "| creation-consumer ID collision and transaction acceptance | `AUTH-ID-001E2` |",
                "| creation-consumer ID collision and transaction acceptance | `AUTH-ID-001G` |",
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )
        special_cases.append(
            ("e2_owner_drift", e2_owner_drift, "link_owner_boundary_drift")
        )

        f_owner_drift = Path(temp) / "negative-f-owner"
        shutil.copytree(base, f_owner_drift)
        path = f_owner_drift / POLICY_G_PATH
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "| lifecycle, mapping disable/reactivation, and unlink | `AUTH-ID-001F` |",
                "| lifecycle, mapping disable/reactivation, and unlink | `AUTH-ID-001G` |",
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )
        special_cases.append(
            ("f_owner_drift", f_owner_drift, "link_owner_boundary_drift")
        )

        h_owner_drift = Path(temp) / "negative-h-owner"
        shutil.copytree(base, h_owner_drift)
        path = h_owner_drift / POLICY_G_PATH
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "| existing-state anomaly repair, upgrade, and reconciliation | `AUTH-ID-001H` |",
                "| existing-state anomaly repair, upgrade, and reconciliation | `AUTH-ID-001G` |",
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )
        special_cases.append(
            ("h_owner_drift", h_owner_drift, "link_owner_boundary_drift")
        )

        production_claim = Path(temp) / "negative-production-claim"
        shutil.copytree(base, production_claim)
        path = production_claim / POLICY_G_PATH
        path.write_text(
            path.read_text(encoding="utf-8") + "\nProduction link state: confirmed\n",
            encoding="utf-8",
            newline="\n",
        )
        special_cases.append(
            (
                "production_claim",
                production_claim,
                "link_production_claim_drift",
            )
        )

        lifecycle_missing = Path(temp) / "negative-lifecycle-missing"
        shutil.copytree(base, lifecycle_missing)
        (lifecycle_missing / LIFECYCLE_CHECKER_PATH).unlink()
        special_cases.append(
            (
                "lifecycle_missing",
                lifecycle_missing,
                "upstream_lifecycle_guard_drift",
            )
        )

        lifecycle_drift = Path(temp) / "negative-lifecycle-drift"
        shutil.copytree(base, lifecycle_drift)
        path = lifecycle_drift / LIFECYCLE_CHECKER_PATH
        path.write_bytes(path.read_bytes() + b"\n# drift\n")
        special_cases.append(
            (
                "lifecycle_drift",
                lifecycle_drift,
                "upstream_lifecycle_guard_drift",
            )
        )

        lifecycle_payload = canonical_fingerprint_bytes(
            (base / LIFECYCLE_CHECKER_PATH).read_bytes()
        )
        if lifecycle_payload is None:
            raise AssertionError("baseline lifecycle source is not canonicalizable")
        if (
            hashlib.sha256(lifecycle_payload).hexdigest().upper()
            != APPROVED_LIFECYCLE_CHECKER_SHA256
        ):
            raise AssertionError("baseline lifecycle canonical fingerprint drifted")
        representation_scenarios = (
            ("lifecycle_canonical_lf", lifecycle_payload, False),
            (
                "lifecycle_mechanical_crlf",
                lifecycle_payload.replace(b"\n", b"\r\n"),
                False,
            ),
            ("lifecycle_standalone_cr", lifecycle_payload + b"\r", True),
            (
                "lifecycle_mixed_lf_crlf",
                lifecycle_payload.replace(b"\n", b"\r\n", 1),
                True,
            ),
            (
                "lifecycle_malformed_cr_sequence",
                lifecycle_payload + b"\rX",
                True,
            ),
            ("lifecycle_crcrlf", lifecycle_payload + b"\r\r\n", True),
            (
                "lifecycle_semantic_byte_drift",
                lifecycle_payload + b"# semantic drift\n",
                True,
            ),
        )
        representation_scenario_names: list[str] = []
        for name, payload, must_fail in representation_scenarios:
            case_root = Path(temp) / f"representation-{name}"
            shutil.copytree(base, case_root)
            (case_root / LIFECYCLE_CHECKER_PATH).write_bytes(payload)
            issues = check_lifecycle_guard(case_root)
            status, output = render_normal(issues)
            if must_fail:
                if (
                    status == 0
                    or "upstream_lifecycle_guard_drift"
                    not in {issue.code for issue in issues}
                    or PASS_MARKER in output
                ):
                    raise AssertionError(
                        f"representation scenario {name} did not fail closed: {issues}"
                    )
            elif issues or status != 0:
                raise AssertionError(
                    f"representation scenario {name} did not pass: {issues}"
                )
            representation_scenario_names.append(name)
            scenario_count += 1

        canonical_digest = hashlib.sha256(lifecycle_payload).hexdigest().upper()
        mechanical_digest = hashlib.sha256(
            canonical_fingerprint_bytes(
                lifecycle_payload.replace(b"\n", b"\r\n")
            )
        ).hexdigest().upper()
        if canonical_digest != mechanical_digest:
            raise AssertionError("lifecycle LF/CRLF fingerprint parity failed")
        representation_scenario_names.append("lifecycle_lf_crlf_parity")
        scenario_count += 1

        pin_drift_root = Path(temp) / "representation-lifecycle-expected-pin-drift"
        shutil.copytree(base, pin_drift_root)
        (pin_drift_root / LIFECYCLE_CHECKER_PATH).write_bytes(lifecycle_payload)
        original_pin = globals()["APPROVED_LIFECYCLE_CHECKER_SHA256"]
        try:
            globals()["APPROVED_LIFECYCLE_CHECKER_SHA256"] = "0" * 64
            pin_drift_issues = check_lifecycle_guard(pin_drift_root)
        finally:
            globals()["APPROVED_LIFECYCLE_CHECKER_SHA256"] = original_pin
        pin_drift_status, pin_drift_output = render_normal(pin_drift_issues)
        if (
            pin_drift_status == 0
            or "upstream_lifecycle_guard_drift"
            not in {issue.code for issue in pin_drift_issues}
            or PASS_MARKER in pin_drift_output
        ):
            raise AssertionError(
                "lifecycle expected-pin drift did not fail closed: "
                f"{pin_drift_issues}"
            )
        representation_scenario_names.append("lifecycle_expected_pin_drift")
        scenario_count += 1

        for name, case_root, expected_code in special_cases:
            issues = analyze_repository(case_root)
            codes = {issue.code for issue in issues}
            exit_code, output = render_normal(issues)
            if expected_code not in codes or exit_code == 0 or PASS_MARKER in output:
                raise AssertionError(
                    f"negative case {name} did not fail closed with {expected_code}: {issues}"
                )
            scenario_count += 1

    print(
        "representation_self_test_scenarios: "
        + ",".join(representation_scenario_names)
    )
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
    exit_code, output = render_normal(issues)
    print(output, end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
