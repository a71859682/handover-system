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
PASS_MARKER = "identity registry reconciliation readiness PASS"
SELF_TEST_MARKER = "identity registry reconciliation readiness self-test PASS"
POLICY_E_PATH = Path("docs/auth_id_001e_registry_schema_baseline.md")
POLICY_F_PATH = Path("docs/auth_id_001f_lifecycle_tombstone_merge_policy.md")
POLICY_G_PATH = Path("docs/auth_id_001g_explicit_cross_backend_linking_baseline.md")
POLICY_H_PATH = Path("docs/auth_id_001h_reconciliation_upgrade_baseline.md")
CHECKER_PATH = Path("tools/check_identity_registry_reconciliation_readiness.py")
DISCOVERY_TOOL_PATH = Path("tools/discover_identity_registry_anomalies.py")
LIFECYCLE_CHECKER_PATH = Path("tools/check_identity_registry_lifecycle_readiness.py")
LINKING_CHECKER_PATH = Path("tools/check_identity_registry_linking_readiness.py")
APPROVED_LIFECYCLE_CHECKER_SHA256 = (
    "5651BDC56222399816941D9BFF25A1BAAA7F8EEFBFC18B01B70FEFC3697466F1"
)
APPROVED_LINKING_CHECKER_SHA256 = (
    "BA87AABC3A5B47BBE51DB5308B509013053842B74495A29A06ED68FE5C39143A"
)

H_POLICY_MARKERS = (
    "Status: design baseline",
    "Scope: docs-only",
    "Implementation status: not started",
    "# AUTH-ID-001H — Registry Reconciliation and Upgrade Design Baseline",
    "Canonical path: `docs/auth_id_001h_reconciliation_upgrade_baseline.md`.",
    "At this baseline, `AUTH-ID-001H` has no implementation, scanner, consumer,",
    "There is currently no H repair authority, and no role or account is assigned",
    "| H discovery | H | scan or report implementation before approval | docs freeze then static readiness guard |",
    "| H plan format | H | executable plan or apply authority | evidence review then plan-format gate |",
    "| H authority | H | role, permission, or apply assignment | separate authority gate |",
    "| H mutation | H with companion owners | repair, correction, or DML | separately approved consumer/mutation gate |",
    "AUTH-ID-001H DOCS-ONLY RECONCILIATION / UPGRADE DESIGN BASELINE",
    "DESIGN STATUS: FROZEN FOR REVIEW",
    "IMPLEMENTATION STATUS: NOT STARTED",
    "DISCOVERY / SCANNER: NOT IMPLEMENTED",
    "REPORT / PLAN FORMAT: NOT IMPLEMENTED",
    "REPAIR AUTHORITY: NOT IMPLEMENTED OR ASSIGNED",
    "RECONCILIATION MUTATION: NOT IMPLEMENTED",
    "NO DATABASE OR ENVIRONMENT ACCESSED",
    "AUTH-ID-001H OVERALL: OPEN — NOT CLOSED",
)

UPSTREAM_OWNER_MARKERS = {
    POLICY_E_PATH: (
        "| registry upgrade / reconciliation workflow | `AUTH-ID-001H` |",
        "Upgrade must preserve provenance, report collision deltas, and must not overwrite or merge in place without isolated gates.",
        "| physical SQLite DDL and migration | `AUTH-ID-001E1` |",
        "| exact ID generation format | `AUTH-ID-001E2` |",
    ),
    POLICY_F_PATH: (
        "| upgrade and reconciliation workflow | `AUTH-ID-001H` |",
        "Must preserve provenance and must not overwrite, merge, or repair in place without isolated gates.",
        "MERGE: UNSUPPORTED",
        "LIVE RELATIONSHIP MOVEMENT: UNSUPPORTED",
    ),
    POLICY_G_PATH: (
        "### 13.3 `AUTH-ID-001H`",
        "- principals mapped to different identities",
        "- existing-state anomalies",
        "`AUTH-ID-001G` must not repair, merge, overwrite, move, or select a winning",
        "identity.",
    ),
}

ANOMALY_CODES = (
    "schema_object_drift",
    "noncanonical_registry_id",
    "invalid_registry_status",
    "invalid_provenance",
    "invalid_backend_principal_key",
    "orphan_fk_relationship",
    "normalized_alias_ambiguity",
    "active_exact_alias_collision",
    "backend_principal_inconsistent_mapping",
    "incompatible_backend_cardinality",
    "conflicting_principals_different_identities",
    "disabled_superseded_relationship_inconsistency",
    "source_principal_missing_inactive_stale",
    "snapshot_concurrency_drift",
    "unknown_unclassified_anomaly",
)

ENTITY_TOKENS = (
    "identity registry",
    "global identity",
    "login identifier alias",
    "backend principal mapping",
    "registry topology",
    "identity relationship",
    "auth id 001h",
)
ACTION_TOKENS = (
    "reconcile",
    "reconciliation",
    "repair",
    "correction",
    "anomaly scan",
    "anomaly scanner",
    "anomaly discovery",
    "registry discovery",
    "evidence report",
    "reconciliation report",
    "reconciliation plan",
    "repair plan",
    "dry run",
    "apply plan",
    "remap",
    "reassign",
    "relationship move",
    "winner",
    "survivor",
    "canonical target",
    "preferred identity",
    "quarantine",
    "upgrade existing registry",
    "hot maintenance",
    "emergency bypass",
)
SENSITIVE_TOKENS = (
    "raw alias",
    "normalized lookup key",
    "backend principal key",
    "credential",
    "password",
    "session",
    "cookie",
    "token",
    "role",
    "site permission",
    "sheet permission",
    "vendor authority",
    "unrestricted row",
    "raw snapshot",
)
REGISTRY_ID_TOKENS = (
    "global identity id",
    "login identifier alias id",
    "backend principal mapping id",
)
CALLER_INPUT_TOKENS = (
    "request json",
    "request get json",
    "request form",
    "request args",
    "request values",
    "session get",
    "argparse",
    "parse args",
)
PRODUCTION_ACCESS_TOKENS = (
    "database url",
    "app db path",
    "var data",
    "production db",
    "production database",
    "render shell",
    "production operator",
    "canonical persistent db",
)
OUTPUT_TOKENS = (
    "jsonify",
    "response",
    "render template",
    "print",
    "logger",
    "logging",
    "report",
    "evidence",
    "plan artifact",
)
AUTHORITY_TOKENS = (
    "repair authority",
    "reconciliation authority",
    "repair permission",
    "reconciliation permission",
    "repair approver",
    "reconciliation approver",
    "apply authority",
    "operator override",
)
WINNER_TOKENS = (
    "winner",
    "survivor",
    "canonical target",
    "preferred identity",
    "newest",
    "oldest",
    "lowest id",
    "highest id",
    "first identity",
    "last identity",
)
WINNER_BASIS_TOKENS = (
    "username",
    "raw alias",
    "normalized lookup key",
    "display name",
    "vendor name",
    "count",
    "severity",
    "confidence",
    "created at",
    "updated at",
)
RELATIONSHIP_TOKENS = (
    "remap",
    "reassign",
    "relationship move",
    "relationship correction",
    "move alias",
    "move mapping",
    "change global identity",
)
HOT_TOKENS = (
    "hot maintenance",
    "hot repair",
    "emergency bypass",
    "production experiment",
    "operator override",
)
SCANNER_TOKENS = (
    "anomaly scanner",
    "anomaly scan",
    "scan registry",
    "discover registry anomalies",
    "registry discovery",
    "inventory registry anomalies",
)
REPORTER_TOKENS = (
    "reconciliation reporter",
    "reconciliation report",
    "anomaly report",
    "registry evidence report",
    "generate evidence bundle",
)
PLAN_TOKENS = (
    "reconciliation plan",
    "repair plan",
    "dry run reconciliation",
    "apply reconciliation plan",
    "execute reconciliation plan",
    "plan artifact",
)
REPAIR_TOKENS = (
    "registry repair",
    "repair registry",
    "reconcile registry state",
    "apply registry correction",
    "quarantine registry",
    "upgrade existing registry",
)
ORACLE_TOKENS = (
    "anomaly exists",
    "anomaly status",
    "registry topology",
    "mapping topology",
    "winner identity",
    "winning identity",
    "conflict subject id",
    "repair candidate",
)
DYNAMIC_CALL_TOKENS = (
    "getattr",
    "globals",
    "locals",
    "eval",
    "build call",
    "build target",
    "resolve handler",
    "dispatch",
    "invoke",
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
        description=(
            "Statically verify the frozen identity-registry reconciliation "
            "and upgrade readiness boundary."
        )
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run system-temp synthetic source and policy scenarios.",
    )
    return parser.parse_args()


def normalized_path(path: Path, root: Path) -> Path:
    return Path(path.resolve().relative_to(root.resolve()).as_posix())


def collapse(value: str) -> str:
    return " ".join(value.split())


def normalized_text(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = value.replace("/", " ").replace("\\", " ")
    return " ".join(re.sub(r"[^A-Za-z0-9]+", " ", value).lower().split())


def dotted_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return None


def static_value(node: ast.AST, scopes: list[dict[str, Any]]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        for scope in reversed(scopes):
            if node.id in scope:
                return scope[node.id]
        return UNKNOWN
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        values = [static_value(item, scopes) for item in node.elts]
        if any(value is UNKNOWN for value in values):
            return UNKNOWN
        return tuple(values)
    if isinstance(node, ast.Dict):
        keys = [static_value(item, scopes) for item in node.keys]
        values = [static_value(item, scopes) for item in node.values]
        if any(value is UNKNOWN for value in keys + values):
            return UNKNOWN
        return dict(zip(keys, values))
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = static_value(node.left, scopes)
        right = static_value(node.right, scopes)
        if isinstance(left, str) and isinstance(right, str):
            return left + right
        return UNKNOWN
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for item in node.values:
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                parts.append(item.value)
            else:
                return UNKNOWN
        return "".join(parts)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "format":
            template = static_value(node.func.value, scopes)
            args = [static_value(arg, scopes) for arg in node.args]
            kwargs = {
                keyword.arg: static_value(keyword.value, scopes)
                for keyword in node.keywords
                if keyword.arg is not None
            }
            if (
                isinstance(template, str)
                and all(value is not UNKNOWN for value in args)
                and all(value is not UNKNOWN for value in kwargs.values())
            ):
                try:
                    return template.format(*args, **kwargs)
                except (IndexError, KeyError, ValueError):
                    return UNKNOWN
        if node.func.attr == "join":
            separator = static_value(node.func.value, scopes)
            if isinstance(separator, str) and len(node.args) == 1:
                items = static_value(node.args[0], scopes)
                if isinstance(items, tuple) and all(isinstance(item, str) for item in items):
                    return separator.join(items)
    if isinstance(node, ast.IfExp):
        left = static_value(node.body, scopes)
        right = static_value(node.orelse, scopes)
        if left == right:
            return left
    return UNKNOWN


def node_evidence(node: ast.AST) -> str:
    fragments: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            fragments.append(child.id)
        elif isinstance(child, ast.Attribute):
            fragments.append(child.attr)
            dotted = dotted_name(child)
            if dotted:
                fragments.append(dotted)
        elif isinstance(child, ast.Constant) and isinstance(child.value, str):
            fragments.append(child.value)
        elif isinstance(child, ast.arg):
            fragments.append(child.arg)
        elif isinstance(child, ast.Return):
            fragments.append("return")
    return normalized_text(" ".join(fragments))


def symbol_name(stack: list[str]) -> str:
    return ".".join(stack) if stack else "<module>"


def contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(normalized_text(token) in text for token in tokens)


def word_tokens(text: str) -> set[str]:
    return set(normalized_text(text).split())


def has_word_family(words: set[str], *stems: str) -> bool:
    return any(
        word == stem or word.startswith(stem)
        for word in words
        for stem in stems
    )


def has_entity_context(text: str) -> bool:
    if contains_any(text, ENTITY_TOKENS):
        return True
    if any(normalized_text(code) in text for code in ANOMALY_CODES):
        return True
    if "registry" in text and "identity" in text:
        return True
    if "registry" in text and "anomal" in text:
        return True
    if "registry" in text and "relationship" in text:
        return True
    if "registry" in text and any(
        token in text for token in ("reconcil", "repair", "winner", "survivor", "quarantine")
    ):
        return True
    return has_dual_backend_principal_context(text)


def has_dual_backend_principal_context(text: str) -> bool:
    internal_vendor = "internal" in text and "vendor" in text
    principal_context = any(
        token in text for token in ("principal", "account", "identity", "mapping")
    )
    return internal_vendor and principal_context


def has_scanner_capability(text: str) -> bool:
    words = word_tokens(text)
    scanner_action = has_word_family(
        words,
        "scan",
        "discover",
        "inventory",
        "inspect",
    )
    anomaly_evidence = has_word_family(words, "anomal", "conflict", "drift")
    return scanner_action and anomaly_evidence


def has_reporter_capability(name: str) -> bool:
    words = word_tokens(name)
    output_action = has_word_family(
        words,
        "build",
        "generate",
        "render",
        "export",
        "emit",
    )
    report_output = has_word_family(words, "report", "evidence", "bundle")
    h_context = has_word_family(
        words,
        "anomal",
        "conflict",
        "drift",
        "quarantine",
        "reconcil",
        "repair",
        "collision",
        "topology",
        "winner",
    )
    return output_action and report_output and h_context


def has_plan_capability(text: str) -> bool:
    words = word_tokens(text)
    plan_action = bool(words.intersection({"plan", "planner"})) or (
        "dry" in words and "run" in words
    ) or (
        has_word_family(words, "apply", "execute") and "plan" in words
    )
    h_context = has_word_family(
        words,
        "reconcil",
        "repair",
        "correct",
        "anomal",
    )
    return plan_action and h_context


def has_hot_maintenance(text: str) -> bool:
    words = word_tokens(text)
    hot_action = "hot" in words and has_word_family(
        words,
        "maintenance",
        "repair",
        "reconcil",
    )
    emergency_bypass = "emergency" in words and "bypass" in words
    return hot_action or emergency_bypass


def has_action_context(text: str) -> bool:
    return (
        contains_any(
            text,
            ACTION_TOKENS
            + SCANNER_TOKENS
            + REPORTER_TOKENS
            + PLAN_TOKENS
            + AUTHORITY_TOKENS
            + WINNER_TOKENS
            + REPAIR_TOKENS
            + RELATIONSHIP_TOKENS
            + HOT_TOKENS,
        )
        or has_scanner_capability(text)
        or has_plan_capability(text)
        or has_hot_maintenance(text)
    )


def has_route_context(node: ast.FunctionDef | ast.AsyncFunctionDef, text: str) -> bool:
    decorators = " ".join(node_evidence(item) for item in node.decorator_list)
    return (
        any(token in decorators for token in ("route", "endpoint", "api"))
        or any(token in text for token in ("request form", "request json", "request args"))
        and any(token in text for token in ("handler", "endpoint"))
    )


def has_cli_context(text: str) -> bool:
    return (
        "argparse" in text
        or "argument parser" in text
        or "parse args" in text
        or re.search(r"\b(?:repair|reconcile|apply|scan|report) option\b", text) is not None
    )


def has_production_access(text: str) -> bool:
    return contains_any(text, PRODUCTION_ACCESS_TOKENS)


def has_authority_capability(text: str) -> bool:
    strong_tokens = (
        "repair authority",
        "reconciliation authority",
        "repair approver",
        "reconciliation approver",
        "apply authority",
        "operator override",
    )
    if contains_any(text, strong_tokens):
        return True
    if "permission error" in text:
        return False
    return contains_any(text, ("repair permission", "reconciliation permission"))


def has_winner_selection(text: str, name: str) -> bool:
    words = word_tokens(text)
    name_words = word_tokens(name)
    explicit = contains_any(text, WINNER_TOKENS)
    selection = bool(
        name_words.intersection({"choose", "select", "pick", "prefer", "rank"})
    ) or (
        any(token in words for token in ("min", "max", "sorted"))
        and any(
            token in name_words
            for token in ("winner", "survivor", "canonical", "preferred")
        )
    ) or any(
        token in name_words for token in ("first", "last")
    )
    candidate = (
        ("global" in words and "identity" in words)
        or ("registry" in words and "identity" in words)
        or ("candidate" in words and "identity" in words)
        or (
            has_word_family(words, "conflict")
            and has_word_family(words, "identity")
        )
        or contains_any(text, REGISTRY_ID_TOKENS)
    )
    basis = (
        contains_any(text, WINNER_BASIS_TOKENS)
        or contains_any(text, REGISTRY_ID_TOKENS)
        or "canonical" in words
        or "newest" in words
        or "oldest" in words
        or "lowest" in words
        or "highest" in words
        or "first" in words
        or "last" in words
        or ("created" in words and "at" in words)
        or ("updated" in words and "at" in words)
    )
    return explicit or (selection and candidate and basis)


def has_output_sink(text: str) -> bool:
    return contains_any(text, OUTPUT_TOKENS) or " return " in f" {text} "


def has_caller_selected_id(text: str) -> bool:
    return contains_any(text, CALLER_INPUT_TOKENS) and contains_any(text, REGISTRY_ID_TOKENS)


def has_sensitive_evidence(text: str) -> bool:
    return contains_any(text, SENSITIVE_TOKENS) and has_output_sink(text)


def has_oracle(text: str) -> bool:
    return contains_any(text, ORACLE_TOKENS) and has_output_sink(text)


def has_unresolved_dynamic(node: ast.AST, text: str) -> bool:
    if not has_entity_context(text) or not has_action_context(text):
        return False
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        call_name = normalized_text(dotted_name(child.func) or "")
        if not call_name or contains_any(call_name, DYNAMIC_CALL_TOKENS):
            return True
        if any(static_value(arg, [{}]) is UNKNOWN for arg in child.args) and any(
            token in call_name for token in ("build", "resolve", "dispatch", "invoke", "handler")
        ):
            return True
    return False


def classify_capability(
    node: ast.AST,
    *,
    name: str,
    text: str,
) -> tuple[str, str] | None:
    entity = has_entity_context(text)
    action = has_action_context(text)
    scanner = has_scanner_capability(text)
    reporter = has_reporter_capability(name)
    plan = has_plan_capability(text)
    winner = has_winner_selection(text, name)
    hot = has_hot_maintenance(text)
    if not (entity and (action or scanner or reporter or plan or winner or hot)):
        return None

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and has_route_context(node, text):
        return (
            "forbidden_reconciliation_route",
            "reconciliation route, API, or form capability is not authorized",
        )
    if has_cli_context(text):
        return (
            "forbidden_reconciliation_cli",
            "reconciliation command-line capability is not authorized",
        )
    if contains_any(text, SCANNER_TOKENS) or scanner:
        return (
            "forbidden_registry_anomaly_scanner",
            "registry anomaly scanner or discovery capability is not authorized",
        )
    if contains_any(text, REPORTER_TOKENS) or reporter:
        return (
            "forbidden_reconciliation_reporter",
            "reconciliation report or evidence generator is not authorized",
        )
    if contains_any(text, PLAN_TOKENS) or plan:
        return (
            "forbidden_reconciliation_plan",
            "reconciliation plan or apply-plan capability is not authorized",
        )
    if has_authority_capability(text):
        return (
            "forbidden_repair_authority",
            "repair or reconciliation authority is not implemented or assigned",
        )
    if has_production_access(text):
        return (
            "forbidden_production_reconciliation_access",
            "Production or persistent-database reconciliation access is not authorized",
        )
    if winner:
        return (
            "forbidden_winner_selection",
            "automatic reconciliation winner selection is forbidden",
        )
    if contains_any(text, HOT_TOKENS) or hot:
        return (
            "forbidden_hot_maintenance",
            "hot-maintenance or emergency reconciliation bypass is forbidden",
        )
    if contains_any(text, RELATIONSHIP_TOKENS):
        return (
            "forbidden_relationship_correction",
            "registry relationship correction or movement is not authorized",
        )
    if contains_any(text, REPAIR_TOKENS) or "repair" in text or (
        "quarantine" in text and "registry" in text
    ):
        return (
            "forbidden_registry_repair",
            "registry repair capability is not authorized",
        )
    if has_caller_selected_id(text):
        return (
            "forbidden_caller_selected_reconciliation_id",
            "caller-selected registry IDs are not accepted by reconciliation",
        )
    if has_sensitive_evidence(text):
        return (
            "forbidden_unredacted_reconciliation_evidence",
            "sensitive reconciliation evidence reached an external output sink",
        )
    if has_oracle(text):
        return (
            "forbidden_reconciliation_oracle",
            "public reconciliation state or winner oracle is forbidden",
        )
    name_text = normalized_text(name)
    if has_entity_context(name_text) and any(
        token in name_text
        for token in (
            "reconcile",
            "reconciliation",
            "upgrade existing registry",
            "repair registry",
            "registry repair",
        )
    ):
        return (
            "forbidden_reconciliation_consumer",
            "reconciliation runtime consumer or orchestrator is not authorized",
        )
    if has_unresolved_dynamic(node, text):
        return (
            "unresolved_reconciliation_capability",
            "dynamic reconciliation capability could not be resolved statically",
        )
    return None


class PythonSourceAnalyzer(ast.NodeVisitor):
    def __init__(self, root: Path, path: Path):
        self.root = root
        self.path = path
        self.relative = normalized_path(path, root)
        self.issues: list[Issue] = []
        self.stack: list[str] = []
        self.reported_nodes: set[int] = set()

    def add_primary(self, node: ast.AST, classification: tuple[str, str] | None) -> None:
        if classification is None or id(node) in self.reported_nodes:
            return
        code, reason = classification
        self.reported_nodes.add(id(node))
        self.issues.append(
            Issue(
                code=code,
                file=self.relative.as_posix(),
                line=int(getattr(node, "lineno", 1)),
                symbol=symbol_name(self.stack),
                reason=reason,
            )
        )

    def inspect_named_node(self, node: ast.AST, name: str) -> None:
        text = normalized_text(name + " " + node_evidence(node))
        self.add_primary(node, classify_capability(node, name=name, text=text))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.stack.append(node.name)
        self.inspect_named_node(node, node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.stack.append(node.name)
        self.inspect_named_node(node, node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.stack.append(node.name)
        self.inspect_named_node(node, node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        names = [dotted_name(target) or "" for target in node.targets]
        name = " ".join(names)
        name_text = normalized_text(name)
        if has_entity_context(name_text) and (
            has_action_context(name_text)
            or contains_any(name_text, AUTHORITY_TOKENS)
            or contains_any(name_text, WINNER_TOKENS)
        ):
            text = normalized_text(name + " " + node_evidence(node.value))
            self.add_primary(node, classify_capability(node, name=name, text=text))
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        name = dotted_name(node.target) or ""
        name_text = normalized_text(name)
        if has_entity_context(name_text) and (
            has_action_context(name_text)
            or contains_any(name_text, AUTHORITY_TOKENS)
            or contains_any(name_text, WINNER_TOKENS)
        ):
            text = normalized_text(
                name + " " + (node_evidence(node.value) if node.value is not None else "")
            )
            self.add_primary(node, classify_capability(node, name=name, text=text))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = dotted_name(node.func) or "<dynamic>"
        text = normalized_text(name + " " + node_evidence(node))
        if (
            has_entity_context(text)
            and has_action_context(text)
            and has_unresolved_dynamic(node, text)
        ):
            self.add_primary(
                node,
                (
                    "unresolved_reconciliation_capability",
                    "dynamic reconciliation capability could not be resolved statically",
                ),
            )
        self.generic_visit(node)


def read_text(
    root: Path,
    relative: Path,
    *,
    missing_code: str,
    read_code: str = "source_read_error",
) -> tuple[str | None, Issue | None]:
    path = root / relative
    if not path.is_file():
        return None, Issue(
            code=missing_code,
            file=relative.as_posix(),
            line=1,
            symbol="<document>",
            reason="required frozen source is missing",
        )
    try:
        return path.read_text(encoding="utf-8"), None
    except (OSError, UnicodeError):
        return None, Issue(
            code=read_code,
            file=relative.as_posix(),
            line=1,
            symbol="<document>",
            reason="required source could not be read as UTF-8",
        )


def check_h_policy(root: Path) -> list[Issue]:
    source, issue = read_text(
        root,
        POLICY_H_PATH,
        missing_code="reconciliation_policy_document_missing",
    )
    if issue:
        return [issue]
    assert source is not None
    issues: list[Issue] = []
    normalized = collapse(source)
    for marker in H_POLICY_MARKERS:
        if collapse(marker) not in normalized:
            issues.append(
                Issue(
                    code="reconciliation_policy_marker_missing",
                    file=POLICY_H_PATH.as_posix(),
                    line=1,
                    symbol="<document>",
                    reason="required frozen reconciliation policy marker is missing",
                )
            )
    for index, line in enumerate(source.splitlines(), 1):
        upper = collapse(line).upper()
        if upper.startswith("IMPLEMENTATION STATUS:") and upper != "IMPLEMENTATION STATUS: NOT STARTED":
            issues.append(
                Issue(
                    code="reconciliation_status_drift",
                    file=POLICY_H_PATH.as_posix(),
                    line=index,
                    symbol="<document>",
                    reason="AUTH-ID-001H implementation status changed",
                )
            )
        if "AUTH-ID-001H" in upper and "CLOSED" in upper and "NOT CLOSED" not in upper:
            issues.append(
                Issue(
                    code="reconciliation_status_drift",
                    file=POLICY_H_PATH.as_posix(),
                    line=index,
                    symbol="<document>",
                    reason="AUTH-ID-001H was marked closed",
                )
            )
        if re.search(
            r"\b(?:SCANNER|REPORT|PLAN|REPAIR AUTHORITY|RECONCILIATION MUTATION)"
            r"\s*:\s*(?:IMPLEMENTED|ENABLED|ASSIGNED|COMPLETE|CLOSED)\b",
            upper,
        ):
            issues.append(
                Issue(
                    code="reconciliation_status_drift",
                    file=POLICY_H_PATH.as_posix(),
                    line=index,
                    symbol="<document>",
                    reason="frozen H document claims an unauthorized implementation capability",
                )
            )
        if re.search(
            r"\bPRODUCTION (?:REGISTRY|DATABASE|DB|ANOMALIES|TOPOLOGY|REPAIR)"
            r".*\b(?:VERIFIED|CONFIRMED|KNOWN|EMPTY|CLEAN|COMPLETE|REPAIRED)\b",
            upper,
        ):
            issues.append(
                Issue(
                    code="reconciliation_production_claim_drift",
                    file=POLICY_H_PATH.as_posix(),
                    line=index,
                    symbol="<document>",
                    reason="Production reconciliation state was claimed without approved evidence",
                )
            )
    return issues


def check_owner_boundaries(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    for path, markers in UPSTREAM_OWNER_MARKERS.items():
        source, issue = read_text(
            root,
            path,
            missing_code="reconciliation_owner_boundary_drift",
            read_code="reconciliation_owner_boundary_drift",
        )
        if issue:
            issues.append(issue)
            continue
        assert source is not None
        normalized = collapse(source)
        for marker in markers:
            if collapse(marker) not in normalized:
                issues.append(
                    Issue(
                        code="reconciliation_owner_boundary_drift",
                        file=path.as_posix(),
                        line=1,
                        symbol="<document>",
                        reason="upstream reconciliation owner boundary marker is missing",
                    )
                )
    return issues


def check_upstream_fingerprint(
    root: Path,
    relative: Path,
    expected_sha256: str,
    issue_code: str,
) -> list[Issue]:
    path = root / relative
    if not path.is_file():
        return [
            Issue(
                code=issue_code,
                file=relative.as_posix(),
                line=1,
                symbol="<module>",
                reason="approved upstream readiness checker is missing",
            )
        ]
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    except OSError:
        digest = "<unreadable>"
    if digest != expected_sha256:
        return [
            Issue(
                code=issue_code,
                file=relative.as_posix(),
                line=1,
                symbol="<module>",
                reason="upstream readiness checker fingerprint changed",
            )
        ]
    return []


DISCOVERY_PUBLIC_EXPORTS = (
    "IdentityRegistryDiscoveryError",
    "discover_identity_registry_anomalies",
)
DISCOVERY_SQL_CONSTANTS = {
    "_SCHEMA_OBJECTS_SQL",
    "_TABLE_LIST_SQL",
    "_TABLE_XINFO_SQL",
    "_FOREIGN_KEY_LIST_SQL",
    "_INDEX_LIST_SQL",
    "_INDEX_XINFO_SQL",
    "_QUERY_ONLY_SET_SQL",
    "_QUERY_ONLY_READ_SQL",
    "_BEGIN_SQL",
    "_DATABASE_LIST_SQL",
    "_SCHEMA_VERSION_SQL",
    "_ROLLBACK_SQL",
    "_NONCANONICAL_ID_SQL",
    "_INVALID_STATUS_SQL",
    "_INVALID_BACKEND_KEY_SQL",
    "_ORPHAN_FK_SQL",
    "_NORMALIZED_ALIAS_AMBIGUITY_SQL",
    "_ACTIVE_EXACT_ALIAS_COLLISION_SQL",
    "_INCONSISTENT_MAPPING_SQL",
    "_INCOMPATIBLE_CARDINALITY_SQL",
}
DISCOVERY_REQUIRED_SOURCE_FRAGMENTS = (
    'expected = {"--db", "--run-id", "--captured-at", "--tool-commit"}',
    'resolved_path.as_uri() + "?mode=ro"',
    "uri=True",
    "cached_statements=0",
    '_HEADER_MAGIC = b"SQLite format 3\\0"',
    "data[18] != 1",
    "data[19] != 1",
    '_QUERY_ONLY_SET_SQL = "PRAGMA query_only=ON"',
    '_QUERY_ONLY_READ_SQL = "PRAGMA query_only"',
    '_BEGIN_SQL = "BEGIN"',
    '_ROLLBACK_SQL = "ROLLBACK"',
    "FROM sqlite_schema",
    "FROM pragma_table_list",
    "FROM pragma_table_xinfo(?)",
    "FROM pragma_foreign_key_list(?)",
    "FROM pragma_index_list(?)",
    "FROM pragma_index_xinfo(?)",
    '"sqlite_master", ("type", "name", "tbl_name", "sql")',
    '("count", "typeof")',
    '"auth-id-001h-disposable-registry-discovery"',
    '"AUTH_ID_001H_DISPOSABLE_DISCOVERY_V1"',
    '"unknown_unclassified_anomaly"',
    '"backend_revalidation_required"',
    '"cross_backend_subject_evidence_required"',
    '"historical_ledger_unavailable"',
    '"single_snapshot_cannot_exclude_concurrency_drift"',
    '"schema_contract_unavailable"',
    '"bounded_query_incomplete"',
    "validate_identity_registry_id as _validate_identity_registry_id",
    "def _source_read_incomplete_observations():",
    "except authorizer._sqlite3.OperationalError:",
    "except sqlite3.OperationalError:",
    "observations = _source_read_incomplete_observations()",
    "item = observations[code]",
    "finally:\n        authorizer.close()",
)
DISCOVERY_FORBIDDEN_SOURCE_FRAGMENTS = (
    "immutable=1",
    "FROM sqlite_master",
    "PRAGMA journal_mode",
    "os.getenv",
    "_os.getenv",
    "os.environ",
    "_os.environ",
    "DATABASE_URL",
    "APP_DB_PATH",
    "import app",
    "from app",
    "capture_schema_manifest",
    "check_identity_registry_schema",
    "requests.",
    "psycopg",
    "sqlalchemy",
)


def discovery_contract_issue(reason: str, line: int = 1) -> Issue:
    return Issue(
        code="discovery_tool_contract_drift",
        file=DISCOVERY_TOOL_PATH.as_posix(),
        line=line,
        symbol="<module>",
        reason=reason,
    )


def top_level_definitions(tree: ast.Module) -> dict[str, ast.AST]:
    result: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result[node.name] = node
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    result[target.id] = node
    return result


def literal_assignment(tree: ast.Module, name: str) -> Any:
    definitions = top_level_definitions(tree)
    node = definitions.get(name)
    if isinstance(node, ast.Assign):
        try:
            return ast.literal_eval(node.value)
        except (TypeError, ValueError):
            return UNKNOWN
    if isinstance(node, ast.AnnAssign) and node.value is not None:
        try:
            return ast.literal_eval(node.value)
        except (TypeError, ValueError):
            return UNKNOWN
    return UNKNOWN


def check_discovery_tool_contract(root: Path) -> list[Issue]:
    path = root / DISCOVERY_TOOL_PATH
    if not path.is_file():
        return [discovery_contract_issue("canonical discovery tool is missing")]
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=DISCOVERY_TOOL_PATH.as_posix())
    except (OSError, UnicodeError, SyntaxError):
        return [discovery_contract_issue("canonical discovery tool is unreadable or invalid")]

    issues: list[Issue] = []

    def add(reason: str, node: ast.AST | None = None) -> None:
        issues.append(
            discovery_contract_issue(reason, int(getattr(node, "lineno", 1)))
        )

    definitions = top_level_definitions(tree)
    exports = literal_assignment(tree, "__all__")
    if exports != DISCOVERY_PUBLIC_EXPORTS:
        add("public export tuple is not exact", definitions.get("__all__"))

    public_definitions = {
        name
        for name, node in definitions.items()
        if not name.startswith("_")
        and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    if public_definitions != set(DISCOVERY_PUBLIC_EXPORTS):
        add("public class/function surface is not exact")

    error_class = definitions.get("IdentityRegistryDiscoveryError")
    if not isinstance(error_class, ast.ClassDef) or len(error_class.bases) != 1:
        add("public exception class shape is not exact", error_class)
    elif not (
        isinstance(error_class.bases[0], ast.Name)
        and error_class.bases[0].id == "Exception"
    ):
        add("public exception must derive only from Exception", error_class)

    callable_node = definitions.get("discover_identity_registry_anomalies")
    if not isinstance(callable_node, ast.FunctionDef):
        add("public discovery callable is missing")
    else:
        arguments = callable_node.args
        if (
            arguments.posonlyargs
            or arguments.args
            or arguments.vararg is not None
            or arguments.kwarg is not None
            or [item.arg for item in arguments.kwonlyargs]
            != ["db_path", "run_id", "captured_at", "tool_commit"]
            or any(default is not None for default in arguments.kw_defaults)
        ):
            add("public callable arguments are not exact", callable_node)
        callable_annotations = {
            argument.arg: (
                ast.unparse(argument.annotation)
                if argument.annotation is not None
                else None
            )
            for argument in arguments.kwonlyargs
        }
        if callable_annotations != {
            "db_path": "_Path",
            "run_id": "str",
            "captured_at": "str",
            "tool_commit": "str",
        } or (
            ast.unparse(callable_node.returns)
            if callable_node.returns is not None
            else None
        ) != "dict[str, object]":
            add("public callable annotations are not exact", callable_node)

    main_node = definitions.get("_main")
    if not isinstance(main_node, ast.FunctionDef):
        add("private CLI entrypoint is missing")
    else:
        arguments = main_node.args
        if (
            arguments.posonlyargs
            or [item.arg for item in arguments.args] != ["argv"]
            or len(arguments.defaults) != 1
            or not isinstance(arguments.defaults[0], ast.Constant)
            or arguments.defaults[0].value is not None
            or arguments.kwonlyargs
            or arguments.vararg is not None
            or arguments.kwarg is not None
        ):
            add("private CLI entrypoint arguments are not exact", main_node)
        elif (
            ast.unparse(arguments.args[0].annotation)
            if arguments.args[0].annotation is not None
            else None
        ) != "_Sequence[str] | None" or (
            ast.unparse(main_node.returns)
            if main_node.returns is not None
            else None
        ) != "int":
            add("private CLI entrypoint annotations are not exact", main_node)

    private_path_alias = False
    private_sequence_alias = False
    public_annotation_names = set(definitions) & {"Path", "Sequence"}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module == "pathlib":
            private_path_alias = any(
                alias.name == "Path" and alias.asname == "_Path"
                for alias in node.names
            )
            if any(
                alias.name == "Path" and alias.asname != "_Path"
                for alias in node.names
            ):
                public_annotation_names.add("Path")
        if node.module == "typing":
            private_sequence_alias = any(
                alias.name == "Sequence" and alias.asname == "_Sequence"
                for alias in node.names
            )
            if any(
                alias.name == "Sequence" and alias.asname != "_Sequence"
                for alias in node.names
            ):
                public_annotation_names.add("Sequence")
    if not private_path_alias or not private_sequence_alias:
        add("private Path and Sequence annotation aliases are not exact")
    if public_annotation_names:
        add("public Path or Sequence annotation alias appeared")

    for fragment in DISCOVERY_REQUIRED_SOURCE_FRAGMENTS:
        if fragment not in source:
            add(f"required immutable discovery evidence is missing: {fragment}")
    for fragment in DISCOVERY_FORBIDDEN_SOURCE_FRAGMENTS:
        if fragment in source:
            add(f"forbidden discovery capability appeared: {fragment}")

    if source.count("sqlite3.connect(") != 1:
        add("SQLite connection call count is not exactly one")
    if source.count('resolved_path.as_uri() + "?mode=ro"') != 1:
        add("single Path.as_uri mode=ro construction drifted")
    if source.count("cached_statements=0") != 1:
        add("statement cache boundary drifted")
    if source.count('"_main"') and "_main" in exports:
        add("private CLI entrypoint became public")

    import_names: set[str] = set()
    imported_e2_validator = False
    sqlite_import_nodes: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_names.add(alias.name)
                if alias.name == "sqlite3":
                    sqlite_import_nodes.append(node)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            import_names.add(module)
            if module == "sqlite3":
                sqlite_import_nodes.append(node)
            if module == "services.identity_registry_ids":
                imported_e2_validator = any(
                    alias.name == "validate_identity_registry_id"
                    and alias.asname == "_validate_identity_registry_id"
                    for alias in node.names
                )
    if sqlite_import_nodes:
        add("sqlite3 must not be imported before the runtime gate", sqlite_import_nodes[0])
    if not imported_e2_validator:
        add("Production-frozen E2 validator import is not exact")
    forbidden_modules = {
        "app",
        "tools.check_identity_registry_schema",
        "tools.capture_schema_manifest",
        "requests",
        "psycopg",
        "sqlalchemy",
    }
    if import_names & forbidden_modules:
        add("forbidden app/schema/serializer/backend import appeared")

    for name in DISCOVERY_SQL_CONSTANTS:
        node = definitions.get(name)
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            add(f"fixed SQL constant is not immutable text: {name}", node)
        elif type(node.value.value) is not str:
            add(f"fixed SQL constant is not a string: {name}", node)
    exact_statement_values = {
        "_QUERY_ONLY_SET_SQL": "PRAGMA query_only=ON",
        "_QUERY_ONLY_READ_SQL": "PRAGMA query_only",
        "_BEGIN_SQL": "BEGIN",
        "_DATABASE_LIST_SQL": "PRAGMA database_list",
        "_SCHEMA_VERSION_SQL": "PRAGMA schema_version",
        "_ROLLBACK_SQL": "ROLLBACK",
    }
    for name, expected in exact_statement_values.items():
        if literal_assignment(tree, name) != expected:
            add(f"fixed operational statement drifted: {name}", definitions.get(name))

    row_queries = definitions.get("_ROW_QUERIES")
    if not isinstance(row_queries, ast.Assign) or not isinstance(
        row_queries.value, (ast.Tuple, ast.List)
    ):
        add("bounded row query registry is not immutable", row_queries)
    else:
        query_names: list[str] = []
        for item in row_queries.value.elts:
            if (
                not isinstance(item, ast.Tuple)
                or len(item.elts) != 2
                or not isinstance(item.elts[0], ast.Constant)
                or type(item.elts[0].value) is not str
                or not isinstance(item.elts[1], ast.Name)
            ):
                add("bounded row query registry entry is dynamic", item)
                continue
            query_names.append(item.elts[0].value)
        if query_names != [
            "noncanonical_registry_id",
            "invalid_registry_status",
            "invalid_backend_principal_key",
            "orphan_fk_relationship",
            "normalized_alias_ambiguity",
            "active_exact_alias_collision",
            "backend_principal_inconsistent_mapping",
            "incompatible_backend_cardinality",
        ]:
            add("bounded row query taxonomy or ordering drifted", row_queries)

    anomaly_dispositions = definitions.get("_ANOMALY_DISPOSITIONS")
    if not isinstance(anomaly_dispositions, ast.Assign):
        add("frozen anomaly taxonomy is missing")
    else:
        try:
            anomaly_value = ast.literal_eval(anomaly_dispositions.value)
        except (TypeError, ValueError):
            anomaly_value = ()
        if len(anomaly_value) != 15 or anomaly_value[-1][0] != "unknown_unclassified_anomaly":
            add("frozen anomaly taxonomy is not exact", anomaly_dispositions)

    runtime_node = definitions.get("_runtime")
    if not isinstance(runtime_node, ast.FunctionDef):
        add("ordered platform/runtime gate is missing")
    else:
        runtime_source = ast.get_source_segment(source, runtime_node) or ""
        positions = [
            runtime_source.find('_os.name != "nt"'),
            runtime_source.find('_sys.implementation.name != "cpython"'),
            runtime_source.find("_sys.version_info[:2] != (3, 14)"),
            runtime_source.find('__import__("sqlite3")'),
            runtime_source.find("(3, 37, 0)"),
            runtime_source.find("(4, 0, 0)"),
        ]
        if any(position < 0 for position in positions) or positions != sorted(positions):
            add("platform/import/SQLite-version gate ordering drifted", runtime_node)

    capture_node = definitions.get("_capture")
    if not isinstance(capture_node, ast.FunctionDef):
        add("single read-only capture implementation is missing")
    else:
        capture_source = ast.get_source_segment(source, capture_node) or ""
        connect_calls = [
            node
            for node in ast.walk(capture_node)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "connect"
        ]
        if len(connect_calls) != 1:
            add("capture must contain exactly one connect call", capture_node)
        else:
            call = connect_calls[0]
            keyword_values = {keyword.arg: keyword.value for keyword in call.keywords}
            if (
                len(call.args) != 1
                or set(keyword_values) != {"uri", "cached_statements"}
                or not isinstance(keyword_values["uri"], ast.Constant)
                or keyword_values["uri"].value is not True
                or not isinstance(keyword_values["cached_statements"], ast.Constant)
                or keyword_values["cached_statements"].value != 0
            ):
                add("exact mode=ro connection options drifted", call)
        sqlite_operational_handlers = [
            node
            for node in ast.walk(capture_node)
            if isinstance(node, ast.ExceptHandler)
            and dotted_name(node.type) == "sqlite3.OperationalError"
        ]
        if len(sqlite_operational_handlers) != 4:
            add(
                "capture SQLite operational handling is not exact",
                capture_node,
            )
        source_incomplete_calls = [
            node
            for node in ast.walk(capture_node)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_source_read_incomplete_observations"
        ]
        if len(source_incomplete_calls) != 2:
            add(
                "pre-transaction source failure observation initialization drifted",
                capture_node,
            )
        if (
            "except _Operational:\n                errors.add(\"source_read_incomplete\")\n"
            "                observations = _source_read_incomplete_observations()"
            not in capture_source
        ):
            add(
                "protected query-only or BEGIN failure lacks complete observations",
                capture_node,
            )

    source_incomplete_node = definitions.get(
        "_source_read_incomplete_observations"
    )
    if not isinstance(source_incomplete_node, ast.FunctionDef):
        add("source-read incomplete observation helper is missing")

    run_statement_node = definitions.get("_run_statement")
    if not isinstance(run_statement_node, ast.FunctionDef):
        add("bounded SQLite statement runner is missing")
    else:
        statement_try = next(
            (
                node
                for node in ast.walk(run_statement_node)
                if isinstance(node, ast.Try)
                and any(
                    isinstance(child, ast.Call)
                    and dotted_name(child.func) == "connection.execute"
                    for child in ast.walk(node)
                )
            ),
            None,
        )
        if statement_try is None:
            add("bounded SQLite statement try boundary is missing", run_statement_node)
        else:
            handler_names = [
                dotted_name(handler.type) for handler in statement_try.handlers
            ]
            if handler_names != [
                "_Failure",
                "authorizer._sqlite3.OperationalError",
                "Exception",
            ]:
                add(
                    "bounded SQLite operational/internal exception split drifted",
                    statement_try,
                )
            else:
                operational_source = (
                    ast.get_source_segment(source, statement_try.handlers[1]) or ""
                )
                internal_source = (
                    ast.get_source_segment(source, statement_try.handlers[2]) or ""
                )
                if (
                    "authorizer.violation" not in operational_source
                    or 'raise _Failure("internal") from None'
                    not in operational_source
                    or "raise _Operational from None" not in operational_source
                ):
                    add(
                        "authorizer violation or SQLite operational mapping drifted",
                        statement_try.handlers[1],
                    )
                if (
                    'raise _Failure("internal") from None' not in internal_source
                    or "raise _Operational" in internal_source
                ):
                    add(
                        "unexpected statement exception is downgraded",
                        statement_try.handlers[2],
                    )

    assemble_node = definitions.get("_assemble_output")
    if not isinstance(assemble_node, ast.FunctionDef):
        add("fail-closed output assembler is missing")
    else:
        observation_subscripts = [
            node
            for node in ast.walk(assemble_node)
            if isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "observations"
        ]
        observation_defaults = [
            node
            for node in ast.walk(assemble_node)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "observations"
            and node.func.attr in {"get", "setdefault"}
        ]
        if len(observation_subscripts) != 1 or observation_defaults:
            add(
                "output assembler no longer fails closed on missing observations",
                assemble_node,
            )

    allowed_output_writes = {
        ("_sys", "stdout", "buffer", "write"),
        ("_sys", "stderr", "buffer", "write"),
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = dotted_name(node.func) or ""
        lowered = name.lower()
        if (
            lowered in {"open", "print"}
            or lowered.endswith(
                (
                    ".open",
                    ".write_text",
                    ".write_bytes",
                    ".commit",
                    ".executemany",
                    ".executescript",
                )
            )
            or ".logging" in lowered
            or ".logger" in lowered
        ):
            parts = tuple(name.split("."))
            if parts not in allowed_output_writes:
                add("artifact, logging, write, or transaction capability appeared", node)

    return sorted(set(issues))


def python_sources(root: Path) -> list[Path]:
    excluded_files = {
        CHECKER_PATH,
        LIFECYCLE_CHECKER_PATH,
        LINKING_CHECKER_PATH,
    }
    result: list[Path] = []
    for path in root.rglob("*.py"):
        relative = normalized_path(path, root)
        if any(part in {".git", ".codex", "__pycache__"} for part in relative.parts):
            continue
        if relative.parts[:1] == ("tests",):
            continue
        if relative in excluded_files:
            continue
        result.append(path)
    return sorted(result)


def analyze_repository(root: Path) -> list[Issue]:
    issues = check_h_policy(root)
    issues.extend(check_owner_boundaries(root))
    discovery_issues = check_discovery_tool_contract(root)
    issues.extend(discovery_issues)
    discovery_authorized = not discovery_issues
    issues.extend(
        check_upstream_fingerprint(
            root,
            LIFECYCLE_CHECKER_PATH,
            APPROVED_LIFECYCLE_CHECKER_SHA256,
            "upstream_lifecycle_guard_drift",
        )
    )
    issues.extend(
        check_upstream_fingerprint(
            root,
            LINKING_CHECKER_PATH,
            APPROVED_LINKING_CHECKER_SHA256,
            "upstream_linking_guard_drift",
        )
    )
    for path in python_sources(root):
        relative = normalized_path(path, root)
        try:
            source = path.read_text(encoding="utf-8")
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
        try:
            tree = ast.parse(source, filename=relative.as_posix())
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
        analyzer = PythonSourceAnalyzer(root, path)
        analyzer.visit(tree)
        source_issues = analyzer.issues
        if relative == DISCOVERY_TOOL_PATH and discovery_authorized:
            authorized_symbols = {
                "IdentityRegistryDiscoveryError",
                "discover_identity_registry_anomalies",
                "_main",
            }
            source_issues = [
                issue
                for issue in source_issues
                if not (
                    issue.code == "forbidden_registry_anomaly_scanner"
                    and issue.symbol in authorized_symbols
                )
            ]
        issues.extend(source_issues)
    return sorted(set(issues))


def render_normal(issues: list[Issue]) -> tuple[int, str]:
    lines = [
        "identity_registry_reconciliation_readiness_scope: static_source_and_frozen_policy_only",
        f"issues_count: {len(issues)}",
        f"scanner_boundary: {'PASS' if not any(i.code == 'forbidden_registry_anomaly_scanner' for i in issues) else 'FAIL'}",
        f"report_and_plan_boundary: {'PASS' if not any(i.code in {'forbidden_reconciliation_reporter', 'forbidden_reconciliation_plan'} for i in issues) else 'FAIL'}",
        f"repair_authority_boundary: {'PASS' if not any(i.code in {'forbidden_repair_authority', 'forbidden_production_reconciliation_access'} for i in issues) else 'FAIL'}",
        f"winner_and_repair_boundary: {'PASS' if not any(i.code in {'forbidden_winner_selection', 'forbidden_registry_repair', 'forbidden_relationship_correction', 'forbidden_hot_maintenance'} for i in issues) else 'FAIL'}",
        f"evidence_and_oracle_boundary: {'PASS' if not any(i.code in {'forbidden_unredacted_reconciliation_evidence', 'forbidden_reconciliation_oracle'} for i in issues) else 'FAIL'}",
        f"frozen_reconciliation_policy_boundary: {'PASS' if not any(i.code.startswith('reconciliation_') for i in issues) else 'FAIL'}",
        f"upstream_lifecycle_guard_boundary: {'PASS' if not any(i.code == 'upstream_lifecycle_guard_drift' for i in issues) else 'FAIL'}",
        f"upstream_linking_guard_boundary: {'PASS' if not any(i.code == 'upstream_linking_guard_drift' for i in issues) else 'FAIL'}",
        "database_access: 0",
        "app_imports: 0",
    ]
    if issues:
        lines.append("FAIL identity registry reconciliation readiness:")
        for issue in issues:
            lines.append(
                f"- {issue.code} file={issue.file} line={issue.line} "
                f"symbol={issue.symbol} reason={issue.reason}"
            )
        return 1, "\n".join(lines) + "\n"
    lines.append(PASS_MARKER)
    return 0, "\n".join(lines) + "\n"


def write_base_tree(root: Path) -> None:
    for relative in (
        POLICY_E_PATH,
        POLICY_F_PATH,
        POLICY_G_PATH,
        POLICY_H_PATH,
        DISCOVERY_TOOL_PATH,
        LIFECYCLE_CHECKER_PATH,
        LINKING_CHECKER_PATH,
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT_DIR / relative, target)
    app_path = root / "app.py"
    app_path.write_text(
        "def index():\n"
        "    return 'ok'\n",
        encoding="utf-8",
        newline="\n",
    )


def add_source(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8", newline="\n")


def decode_synthetic_case_source(source: str) -> str:
    return source.replace("{u}", "_")


def positive_cases() -> list[tuple[str, str, str]]:
    cases = [
        ("ordinary_report", "services/reporting.py", "def build_handover_report(rows):\n    return list(rows)\n"),
        ("accounting_reconciliation", "services/accounting.py", "def reconcile_invoice_form(left, right):\n    return left == right\n"),
        ("alembic_upgrade", "migrations/version.py", "def upgrade():\n    return None\n"),
        ("ui_repair", "services/ui.py", "def repair_broken_button_style(css):\n    return css.replace('red', 'blue')\n"),
        ("generic_conflict", "services/conflict.py", "def handle_write_conflict(version):\n    return version > 0\n"),
        ("snapshot_compare", "services/snapshot.py", "def compare_snapshots(before, after):\n    return before == after\n"),
        ("schema_manifest", "tools/capture_schema_manifest.py", "def classify_schema_drift(manifest_a, manifest_b):\n    return manifest_a == manifest_b\n"),
        ("audit_display", "services/audit.py", "def render_read_only_audit(events):\n    return tuple(events)\n"),
        ("users_sequence_repair", "tools/fix_users_sequence.py", "def repair_users_sequence(value):\n    return value + 1\n"),
        ("dev_anomaly", "tools/dev_preview.py", "def classify_dev_vendor_anomaly(meta):\n    return bool(meta)\n"),
        ("dual_write_dry_run", "services/dual_write.py", "def dual_write_dry_run_enabled(flag):\n    return bool(flag)\n"),
        ("ordinary_admin", "services/admin.py", "def require_admin(user):\n    return user.role == 'admin'\n"),
        ("generic_db", "services/db_health.py", "def inspect_database_connection(conn):\n    return conn is not None\n"),
        (
            "reject_only",
            "services/reject.py",
            "def unsupported_operation():\n"
            "    raise PermissionError('AUTH-ID-001H identity registry reconciliation is unsupported')\n",
        ),
        (
            "display_selection",
            "services/display.py",
            "def select_identity_for_display(rows):\n"
            "    return rows\n",
        ),
        (
            "vendor_preview_inventory",
            "services/vendor_preview.py",
            "def inventory_vendor_preview_metadata(rows):\n"
            "    return list(rows)\n",
        ),
        (
            "application_error_evidence",
            "services/errors.py",
            "def build_application_error_evidence(error):\n"
            "    return str(error)\n",
        ),
        (
            "business_conflict_report",
            "services/business_reporting.py",
            "def export_business_conflict_report(rows):\n"
            "    return rows\n",
        ),
        (
            "application_drift_evidence",
            "services/application_evidence.py",
            "def emit_application_drift_evidence(rows):\n"
            "    return rows\n",
        ),
        (
            "quarantine_help_page",
            "services/help.py",
            "def render_quarantine_help_page(rows):\n"
            "    return rows\n",
        ),
        ("tests_ignored", "tests/test_reconciliation.py", "def repair_global{u}identity{u}registry():\n    return 'synthetic'\n"),
    ]
    return [
        (name, relative, decode_synthetic_case_source(source))
        for name, relative, source in cases
    ]


NEGATIVE_SOURCE_CASES: tuple[tuple[str, str, str, str], ...] = (
        (
            "route",
            "routes/reconciliation.py",
            "@app.route('/identity-registry/reconciliation')\n"
            "def reconcile_global{u}identity{u}registry():\n"
            "    return {}\n",
            "forbidden_reconciliation_route",
        ),
        (
            "api",
            "routes/api.py",
            "@api.endpoint('/global-identity/repair')\n"
            "def repair_global{u}identity_api():\n"
            "    return {}\n",
            "forbidden_reconciliation_route",
        ),
        (
            "form",
            "routes/forms.py",
            "def identity{u}registry_reconciliation_form_handler():\n"
            "    return request.form\n",
            "forbidden_reconciliation_route",
        ),
        (
            "cli",
            "tools/repair_cli.py",
            "import argparse\n"
            "def repair_global{u}identity{u}registry_cli():\n"
            "    parser = argparse.ArgumentParser()\n"
            "    parser.add_argument('--repair')\n"
            "    return parser.parse_args()\n",
            "forbidden_reconciliation_cli",
        ),
        (
            "scanner",
            "services/scanner.py",
            "def scan_registry_for_identity_anomalies(rows):\n"
            "    return list(rows)\n",
            "forbidden_registry_anomaly_scanner",
        ),
        (
            "discovery",
            "services/discovery.py",
            "def discover_registry_anomalies(global_identities):\n"
            "    return global_identities\n",
            "forbidden_registry_anomaly_scanner",
        ),
        (
            "reporter",
            "services/reporter.py",
            "def generate_reconciliation_report_for_identity{u}registry(rows):\n"
            "    return rows\n",
            "forbidden_reconciliation_reporter",
        ),
        (
            "evidence_generator",
            "services/evidence.py",
            "def generate_evidence_bundle_for_registry_reconciliation(rows):\n"
            "    return rows\n",
            "forbidden_reconciliation_reporter",
        ),
        (
            "dry_run_plan",
            "services/planner.py",
            "def dry_run_reconciliation_plan_for_global{u}identity(rows):\n"
            "    return rows\n",
            "forbidden_reconciliation_plan",
        ),
        (
            "apply_plan",
            "services/apply.py",
            "def apply_reconciliation_plan_to_identity{u}registry(plan):\n"
            "    return plan\n",
            "forbidden_reconciliation_plan",
        ),
        (
            "authority_assignment",
            "services/authority.py",
            "IDENTITY{u}REGISTRY_REPAIR_PERMISSION = 'identity{u}registry.repair'\n",
            "forbidden_repair_authority",
        ),
        (
            "approver_assignment",
            "services/authority.py",
            "RECONCILIATION_APPROVER_FOR_GLOBAL{u}IDENTITY = 'admin'\n",
            "forbidden_repair_authority",
        ),
        (
            "operator_authority",
            "services/authority.py",
            "def assign_registry_repair_authority(operator):\n"
            "    operator.repair_authority = True\n",
            "forbidden_repair_authority",
        ),
        (
            "production_access_authority",
            "services/authority.py",
            "def use_production_operator_as_registry_repair_authority(operator):\n"
            "    return operator.is_production_operator\n",
            "forbidden_repair_authority",
        ),
        (
            "production_db_access",
            "services/reconciliation.py",
            "def reconcile_global{u}identity{u}registry_in_production():\n"
            "    return connect(DATABASE_URL)\n",
            "forbidden_production_reconciliation_access",
        ),
        (
            "app_db_path_access",
            "services/reconciliation.py",
            "def repair_identity{u}registry_from_app_db_path():\n"
            "    return open(APP_DB_PATH)\n",
            "forbidden_production_reconciliation_access",
        ),
        (
            "winner",
            "services/winner.py",
            "def select_winner_global{u}identity_for_reconciliation(candidates):\n"
            "    return candidates[0]\n",
            "forbidden_winner_selection",
        ),
        (
            "newest_winner",
            "services/winner.py",
            "def choose_newest_global{u}identity_as_reconciliation_winner(rows):\n"
            "    return max(rows)\n",
            "forbidden_winner_selection",
        ),
        (
            "oldest_winner",
            "services/winner.py",
            "def choose_oldest_global{u}identity_as_reconciliation_winner(rows):\n"
            "    return min(rows)\n",
            "forbidden_winner_selection",
        ),
        (
            "lowest_id_winner",
            "services/winner.py",
            "def choose_lowest_id_global{u}identity_for_reconciliation(rows):\n"
            "    return min(rows, key=lambda row: row.global{u}identity_id)\n",
            "forbidden_winner_selection",
        ),
        (
            "highest_id_winner",
            "services/winner.py",
            "def choose_highest_id_global{u}identity_for_reconciliation(rows):\n"
            "    return max(rows, key=lambda row: row.global{u}identity_id)\n",
            "forbidden_winner_selection",
        ),
        (
            "alias_winner",
            "services/winner.py",
            "def choose_reconciliation_winner_global{u}identity_by_raw_alias(rows):\n"
            "    return sorted(rows, key=lambda row: row.raw_alias)[0]\n",
            "forbidden_winner_selection",
        ),
        (
            "display_vendor_winner",
            "services/winner.py",
            "def choose_registry_reconciliation_winner_by_display_name_vendor_name(rows):\n"
            "    return sorted(rows, key=lambda row: (row.display_name, row.vendor_name))[0]\n",
            "forbidden_winner_selection",
        ),
        (
            "registry_repair",
            "services/repair.py",
            "def repair_global{u}identity{u}registry(rows):\n"
            "    return save(rows)\n",
            "forbidden_registry_repair",
        ),
        (
            "quarantine",
            "services/repair.py",
            "def quarantine_registry_identity_anomaly(row):\n"
            "    return save(row)\n",
            "forbidden_registry_repair",
        ),
        (
            "remap",
            "services/correction.py",
            "def remap_backend{u}principal{u}mapping_for_reconciliation(row):\n"
            "    return row\n",
            "forbidden_relationship_correction",
        ),
        (
            "reassign",
            "services/correction.py",
            "def reassign_login{u}identifier{u}alias_during_reconciliation(row):\n"
            "    return row\n",
            "forbidden_relationship_correction",
        ),
        (
            "move",
            "services/correction.py",
            "def move_alias_relationship_for_registry_reconciliation(row):\n"
            "    return row\n",
            "forbidden_relationship_correction",
        ),
        (
            "correct",
            "services/correction.py",
            "def apply_registry_relationship_correction(row):\n"
            "    return row\n",
            "forbidden_relationship_correction",
        ),
        (
            "hot_maintenance",
            "services/hot.py",
            "def hot_maintenance_registry_reconciliation(rows):\n"
            "    return rows\n",
            "forbidden_hot_maintenance",
        ),
        (
            "emergency_bypass",
            "services/hot.py",
            "def emergency_bypass_for_identity{u}registry_reconciliation(rows):\n"
            "    return rows\n",
            "forbidden_hot_maintenance",
        ),
        (
            "caller_json_id",
            "routes/importer.py",
            "def reconcile_global{u}identity{u}registry_from_json():\n"
            "    global{u}identity_id = request.json['global{u}identity_id']\n"
            "    return import_identity(global{u}identity_id)\n",
            "forbidden_caller_selected_reconciliation_id",
        ),
        (
            "caller_form_id",
            "services/importer.py",
            "def import_registry_reconciliation_selection():\n"
            "    login{u}identifier{u}alias_id = request.form['login{u}identifier{u}alias_id']\n"
            "    return login{u}identifier{u}alias_id\n",
            "forbidden_caller_selected_reconciliation_id",
        ),
        (
            "caller_cli_id",
            "services/importer.py",
            "def reconcile_backend{u}principal{u}mapping_from_cli():\n"
            "    args = parse_args()\n"
            "    return args.backend{u}principal{u}mapping_id\n",
            "forbidden_reconciliation_cli",
        ),
        (
            "raw_alias_leak",
            "services/debug.py",
            "def debug_identity{u}registry_reconciliation(raw_alias):\n"
            "    print(raw_alias)\n",
            "forbidden_unredacted_reconciliation_evidence",
        ),
        (
            "backend_key_leak",
            "services/debug.py",
            "def debug_registry_reconciliation(backend_principal_key):\n"
            "    logger.info(backend_principal_key)\n",
            "forbidden_unredacted_reconciliation_evidence",
        ),
        (
            "credential_leak",
            "services/debug.py",
            "def debug_identity{u}registry_reconciliation(password, session):\n"
            "    return {'password': password, 'session': session}\n",
            "forbidden_unredacted_reconciliation_evidence",
        ),
        (
            "oracle",
            "services/oracle.py",
            "def public_registry_reconciliation_anomaly_status():\n"
            "    return {'anomaly_status': True, 'registry_topology': []}\n",
            "forbidden_reconciliation_oracle",
        ),
        (
            "winner_oracle",
            "services/oracle.py",
            "def public_identity{u}registry_reconciliation_result():\n"
            "    return {'winner_identity': 'opaque'}\n",
            "forbidden_winner_selection",
        ),
        (
            "guard_permission",
            "services/guarded.py",
            "def repair_global{u}identity{u}registry(actor, rows):\n"
            "    if actor is None:\n"
            "        raise PermissionError('denied')\n"
            "    return save(rows)\n",
            "forbidden_registry_repair",
        ),
        (
            "guard_false",
            "services/guarded.py",
            "def build_reconciliation_plan_for_identity{u}registry(actor, rows):\n"
            "    if actor is None:\n"
            "        return False\n"
            "    return rows\n",
            "forbidden_reconciliation_plan",
        ),
        (
            "guard_abort",
            "services/guarded.py",
            "def scan_registry_for_identity_anomalies(actor, rows):\n"
            "    if actor is None:\n"
            "        abort(403)\n"
            "    return rows\n",
            "forbidden_registry_anomaly_scanner",
        ),
        (
            "dynamic",
            "services/dynamic.py",
            "def process_registry_state(action, target):\n"
            "    capability = build_target('reconciliation', 'global{u}identity', action, target)\n"
            "    return capability\n",
            "unresolved_reconciliation_capability",
        ),
        (
            "runtime_test_named",
            "services/test_reconciliation_fixture.py",
            "def repair_global{u}identity{u}registry(rows):\n"
            "    return rows\n",
            "forbidden_registry_repair",
        ),
        (
            "permuted_scan",
            "services/scanner.py",
            "def scan_global{u}identity{u}registry_for_anomalies(rows):\n"
            "    return list(rows)\n",
            "forbidden_registry_anomaly_scanner",
        ),
        (
            "permuted_discovery",
            "services/discovery.py",
            "def discover_global{u}identity{u}registry_anomalies(rows):\n"
            "    return list(rows)\n",
            "forbidden_registry_anomaly_scanner",
        ),
        (
            "permuted_inventory",
            "services/inventory.py",
            "def inventory_global{u}identity{u}registry_anomalies(rows):\n"
            "    return list(rows)\n",
            "forbidden_registry_anomaly_scanner",
        ),
        (
            "permuted_evidence",
            "services/evidence.py",
            "def build_global{u}identity{u}registry_anomaly_evidence(rows):\n"
            "    return tuple(rows)\n",
            "forbidden_reconciliation_reporter",
        ),
        (
            "permuted_repair_plan",
            "services/planner.py",
            "def plan_global{u}identity{u}registry_repair(rows):\n"
            "    return tuple(rows)\n",
            "forbidden_reconciliation_plan",
        ),
        (
            "permuted_hot_repair",
            "services/hot.py",
            "def hot_repair_identity{u}registry(rows):\n"
            "    return save(rows)\n",
            "forbidden_hot_maintenance",
        ),
        (
            "created_at_selection",
            "services/winner.py",
            "def choose_global{u}identity_by_created_at(rows):\n"
            "    return max(rows, key=lambda row: row.created_at)\n",
            "forbidden_winner_selection",
        ),
        (
            "lowest_identity_selection",
            "services/winner.py",
            "def select_lowest_global{u}identity_id(rows):\n"
            "    return min(rows)\n",
            "forbidden_winner_selection",
        ),
        (
            "canonical_identity_selection",
            "services/winner.py",
            "def select_canonical_identity_for_registry_reconciliation(rows):\n"
            "    return rows[0]\n",
            "forbidden_winner_selection",
        ),
        (
            "guarded_permuted_scanner",
            "services/guarded.py",
            "def scan_global{u}identity{u}registry_for_anomalies(actor, rows):\n"
            "    if actor is None:\n"
            "        raise PermissionError('denied')\n"
            "    return list(rows)\n",
            "forbidden_registry_anomaly_scanner",
        ),
        (
            "guarded_permuted_plan",
            "services/guarded.py",
            "def plan_global{u}identity{u}registry_repair(actor, rows):\n"
            "    if actor is None:\n"
            "        return False\n"
            "    return tuple(rows)\n",
            "forbidden_reconciliation_plan",
        ),
        (
            "guarded_permuted_winner",
            "services/guarded.py",
            "def choose_global{u}identity_by_created_at(actor, rows):\n"
            "    if actor is None:\n"
            "        raise PermissionError('denied')\n"
            "    return max(rows, key=lambda row: row.created_at)\n",
            "forbidden_winner_selection",
        ),
        (
            "conflict_report",
            "services/reporter.py",
            "def export_global{u}identity{u}registry_conflict_report(rows):\n"
            "    return rows\n",
            "forbidden_reconciliation_reporter",
        ),
        (
            "drift_evidence",
            "services/evidence.py",
            "def emit_identity{u}registry_drift_evidence(rows):\n"
            "    return rows\n",
            "forbidden_reconciliation_reporter",
        ),
        (
            "quarantine_report",
            "services/reporter.py",
            "def render_identity{u}registry_quarantine_report(rows):\n"
            "    return rows\n",
            "forbidden_reconciliation_reporter",
        ),
)


def negative_source_cases() -> list[tuple[str, str, str, str]]:
    return [
        (name, relative, decode_synthetic_case_source(source), expected_code)
        for name, relative, source, expected_code in NEGATIVE_SOURCE_CASES
    ]


def run_self_test() -> int:
    scenario_count = 0
    with tempfile.TemporaryDirectory(
        prefix="identity-registry-reconciliation-readiness-"
    ) as temp_dir:
        temp_root = Path(temp_dir)
        baseline = temp_root / "baseline"
        write_base_tree(baseline)
        issues = analyze_repository(baseline)
        scenario_count += 1
        if issues:
            raise AssertionError(f"clean baseline failed: {issues!r}")

        for name, relative, source in positive_cases():
            root = temp_root / f"positive-{name}"
            shutil.copytree(baseline, root)
            add_source(root, relative, source)
            issues = analyze_repository(root)
            scenario_count += 1
            if issues:
                raise AssertionError(f"positive scenario {name} failed: {issues!r}")

        for name, relative, source, expected_code in negative_source_cases():
            root = temp_root / f"negative-{name}"
            shutil.copytree(baseline, root)
            add_source(root, relative, source)
            issues = analyze_repository(root)
            status, output = render_normal(issues)
            scenario_count += 1
            if status == 0 or expected_code not in {issue.code for issue in issues}:
                raise AssertionError(
                    f"negative scenario {name} did not fail with {expected_code}: {issues!r}"
                )
            if PASS_MARKER in output:
                raise AssertionError(f"negative scenario {name} emitted normal PASS marker")

        discovery_source = (baseline / DISCOVERY_TOOL_PATH).read_text(encoding="utf-8")
        discovery_mutations = (
            (
                "discovery_extra_export",
                '    "discover_identity_registry_anomalies",\n)',
                '    "discover_identity_registry_anomalies",\n    "extra",\n)',
            ),
            (
                "discovery_cli_option",
                'expected = {"--db", "--run-id", "--captured-at", "--tool-commit"}',
                'expected = {"--database", "--run-id", "--captured-at", "--tool-commit"}',
            ),
            (
                "discovery_uri_extra",
                'resolved_path.as_uri() + "?mode=ro"',
                'resolved_path.as_uri() + "?mode=ro&cache=shared"',
            ),
            (
                "discovery_statement_cache",
                "cached_statements=0",
                "cached_statements=1",
            ),
            (
                "discovery_header_write_version",
                "data[18] != 1",
                "data[18] != 2",
            ),
            (
                "discovery_header_read_version",
                "data[19] != 1",
                "data[19] != 2",
            ),
            (
                "discovery_top_level_sqlite_import",
                "import stat as _stat",
                "import stat as _stat\nimport sqlite3 as _sqlite3",
            ),
            (
                "discovery_direct_master_sql",
                "FROM sqlite_schema",
                "FROM sqlite_master",
            ),
            (
                "discovery_callback_alias",
                '"sqlite_master", ("type", "name", "tbl_name", "sql")',
                '"sqlite_schema", ("type", "name", "tbl_name", "sql")',
            ),
            (
                "discovery_function_allowance",
                '("count", "typeof")',
                '("count", "typeof", "coalesce")',
            ),
            (
                "discovery_app_import",
                "import stat as _stat",
                "import stat as _stat\nimport app",
            ),
            (
                "discovery_environment_fallback",
                "def _validate_inputs(db_path, run_id, captured_at, tool_commit) -> None:",
                "def _validate_inputs(db_path, run_id, captured_at, tool_commit) -> None:\n    _os.getenv('APP_DB_PATH')",
            ),
            (
                "discovery_e2_validator",
                "validate_identity_registry_id as _validate_identity_registry_id",
                "validate_identity_registry_id as _different_validator",
            ),
            (
                "discovery_query_only_write",
                '_QUERY_ONLY_SET_SQL = "PRAGMA query_only=ON"',
                '_QUERY_ONLY_SET_SQL = "PRAGMA query_only=OFF"',
            ),
            (
                "discovery_transaction_commit",
                '_ROLLBACK_SQL = "ROLLBACK"',
                '_ROLLBACK_SQL = "COMMIT"',
            ),
            (
                "discovery_finally_reset",
                "finally:\n        authorizer.close()",
                "if authorizer.active:\n        authorizer.close()",
            ),
            (
                "discovery_extra_public_function",
                "class IdentityRegistryDiscoveryError(Exception):",
                "def extra_discovery_entrypoint():\n    return None\n\n\nclass IdentityRegistryDiscoveryError(Exception):",
            ),
            (
                "discovery_dynamic_schema_sql",
                '_SCHEMA_OBJECTS_SQL = """SELECT',
                '_SCHEMA_OBJECTS_SQL = "SELECT" + """',
            ),
            (
                "discovery_unknown_removed",
                '    ("unknown_unclassified_anomaly", "fail_closed"),',
                "",
            ),
            (
                "discovery_artifact_write",
                "def _canonical_bytes(value) -> bytes:",
                "def _canonical_bytes(value) -> bytes:\n    open('evidence.json', 'w')",
            ),
            (
                "discovery_generic_operational_catch",
                "        except sqlite3.OperationalError:\n"
                '            errors.add("source_read_incomplete")',
                "        except Exception:\n"
                '            errors.add("source_read_incomplete")',
            ),
            (
                "discovery_begin_observations_removed",
                '            except _Operational:\n'
                '                errors.add("source_read_incomplete")\n'
                "                observations = _source_read_incomplete_observations()\n"
                "            if transaction_started:",
                '            except _Operational:\n'
                '                errors.add("source_read_incomplete")\n'
                "            if transaction_started:",
            ),
            (
                "discovery_runtime_downgraded",
                "    except Exception:\n"
                '        raise _Failure("internal") from None\n'
                "    finally:\n"
                "        authorizer.close()",
                "    except Exception:\n"
                "        raise _Operational from None\n"
                "    finally:\n"
                "        authorizer.close()",
            ),
            (
                "discovery_assemble_default",
                "            item = observations[code]",
                "            item = observations.get(code, {})",
            ),
            (
                "discovery_db_path_double_quoted_annotation",
                "    db_path: _Path,",
                '    db_path: "Path",',
            ),
            (
                "discovery_main_double_quoted_annotation",
                "def _main(argv: _Sequence[str] | None = None) -> int:",
                'def _main(argv: "Sequence[str] | None" = None) -> int:',
            ),
            (
                "discovery_db_path_annotation_missing",
                "    db_path: _Path,",
                "    db_path,",
            ),
            (
                "discovery_callable_return_annotation",
                ") -> dict[str, object]:",
                ") -> dict[str, str]:",
            ),
            (
                "discovery_db_path_annotation_str",
                "    db_path: _Path,",
                "    db_path: str,",
            ),
            (
                "discovery_public_path_alias",
                "from pathlib import Path as _Path",
                "from pathlib import Path as _Path\nPath = _Path",
            ),
        )
        for name, old, new in discovery_mutations:
            if old not in discovery_source:
                raise AssertionError(f"discovery self-test mutation source missing: {name}")
            root = temp_root / f"negative-{name}"
            shutil.copytree(baseline, root)
            mutated = discovery_source.replace(old, new, 1)
            add_source(root, DISCOVERY_TOOL_PATH.as_posix(), mutated)
            issues = analyze_repository(root)
            status, output = render_normal(issues)
            scenario_count += 1
            if (
                status == 0
                or "discovery_tool_contract_drift"
                not in {issue.code for issue in issues}
            ):
                raise AssertionError(
                    f"discovery scenario {name} did not fail closed: {issues!r}"
                )
            if PASS_MARKER in output:
                raise AssertionError(
                    f"discovery scenario {name} emitted normal PASS marker"
                )

        special_cases: list[tuple[str, Path, str]] = []

        missing_policy = temp_root / "negative-policy-missing"
        shutil.copytree(baseline, missing_policy)
        (missing_policy / POLICY_H_PATH).unlink()
        special_cases.append(
            ("policy_missing", missing_policy, "reconciliation_policy_document_missing")
        )

        marker_missing = temp_root / "negative-marker-missing"
        shutil.copytree(baseline, marker_missing)
        path = marker_missing / POLICY_H_PATH
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "DISCOVERY / SCANNER: NOT IMPLEMENTED",
                "DISCOVERY / SCANNER: UNRECORDED",
            ),
            encoding="utf-8",
            newline="\n",
        )
        special_cases.append(
            ("marker_missing", marker_missing, "reconciliation_policy_marker_missing")
        )

        implemented = temp_root / "negative-implemented"
        shutil.copytree(baseline, implemented)
        path = implemented / POLICY_H_PATH
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "Implementation status: not started",
                "Implementation status: implemented",
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )
        special_cases.append(("implemented", implemented, "reconciliation_status_drift"))

        closed = temp_root / "negative-closed"
        shutil.copytree(baseline, closed)
        path = closed / POLICY_H_PATH
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\nAUTH-ID-001H OVERALL: CLOSED\n",
            encoding="utf-8",
            newline="\n",
        )
        special_cases.append(("closed", closed, "reconciliation_status_drift"))

        for name, claim in (
            ("scanner_claim", "SCANNER: IMPLEMENTED"),
            ("report_claim", "REPORT: IMPLEMENTED"),
            ("plan_claim", "PLAN: IMPLEMENTED"),
            ("authority_claim", "REPAIR AUTHORITY: ASSIGNED"),
            ("mutation_claim", "RECONCILIATION MUTATION: IMPLEMENTED"),
        ):
            root = temp_root / f"negative-{name}"
            shutil.copytree(baseline, root)
            path = root / POLICY_H_PATH
            path.write_text(
                path.read_text(encoding="utf-8") + f"\n{claim}\n",
                encoding="utf-8",
                newline="\n",
            )
            special_cases.append((name, root, "reconciliation_status_drift"))

        production_claim = temp_root / "negative-production-claim"
        shutil.copytree(baseline, production_claim)
        path = production_claim / POLICY_H_PATH
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\nProduction registry anomalies: verified clean\n",
            encoding="utf-8",
            newline="\n",
        )
        special_cases.append(
            (
                "production_claim",
                production_claim,
                "reconciliation_production_claim_drift",
            )
        )

        for name, policy_path, old, new in (
            (
                "e_owner",
                POLICY_E_PATH,
                "| registry upgrade / reconciliation workflow | `AUTH-ID-001H` |",
                "| registry upgrade / reconciliation workflow | `AUTH-ID-001G` |",
            ),
            (
                "f_owner",
                POLICY_F_PATH,
                "| upgrade and reconciliation workflow | `AUTH-ID-001H` |",
                "| upgrade and reconciliation workflow | `AUTH-ID-001F` |",
            ),
            (
                "g_owner",
                POLICY_G_PATH,
                "### 13.3 `AUTH-ID-001H`",
                "### 13.3 `AUTH-ID-001G`",
            ),
        ):
            root = temp_root / f"negative-{name}"
            shutil.copytree(baseline, root)
            path = root / policy_path
            path.write_text(
                path.read_text(encoding="utf-8").replace(old, new, 1),
                encoding="utf-8",
                newline="\n",
            )
            special_cases.append(
                (name, root, "reconciliation_owner_boundary_drift")
            )

        lifecycle_missing = temp_root / "negative-lifecycle-missing"
        shutil.copytree(baseline, lifecycle_missing)
        (lifecycle_missing / LIFECYCLE_CHECKER_PATH).unlink()
        special_cases.append(
            (
                "lifecycle_missing",
                lifecycle_missing,
                "upstream_lifecycle_guard_drift",
            )
        )

        lifecycle_drift = temp_root / "negative-lifecycle-drift"
        shutil.copytree(baseline, lifecycle_drift)
        path = lifecycle_drift / LIFECYCLE_CHECKER_PATH
        path.write_bytes(path.read_bytes() + b"\n# drift\n")
        special_cases.append(
            ("lifecycle_drift", lifecycle_drift, "upstream_lifecycle_guard_drift")
        )

        linking_missing = temp_root / "negative-linking-missing"
        shutil.copytree(baseline, linking_missing)
        (linking_missing / LINKING_CHECKER_PATH).unlink()
        special_cases.append(
            ("linking_missing", linking_missing, "upstream_linking_guard_drift")
        )

        linking_drift = temp_root / "negative-linking-drift"
        shutil.copytree(baseline, linking_drift)
        path = linking_drift / LINKING_CHECKER_PATH
        path.write_bytes(path.read_bytes() + b"\n# drift\n")
        special_cases.append(
            ("linking_drift", linking_drift, "upstream_linking_guard_drift")
        )

        read_error = temp_root / "negative-read-error"
        shutil.copytree(baseline, read_error)
        path = read_error / "services" / "unreadable.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\xff\xfe\x00")
        special_cases.append(("read_error", read_error, "source_read_error"))

        parse_error = temp_root / "negative-parse-error"
        shutil.copytree(baseline, parse_error)
        add_source(parse_error, "services/invalid.py", "def broken(:\n    pass\n")
        special_cases.append(("parse_error", parse_error, "source_parse_error"))

        for name, root, expected_code in special_cases:
            issues = analyze_repository(root)
            status, output = render_normal(issues)
            scenario_count += 1
            if status == 0 or expected_code not in {issue.code for issue in issues}:
                raise AssertionError(
                    f"special scenario {name} did not fail with {expected_code}: {issues!r}"
                )
            if PASS_MARKER in output:
                raise AssertionError(f"special scenario {name} emitted normal PASS marker")

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
