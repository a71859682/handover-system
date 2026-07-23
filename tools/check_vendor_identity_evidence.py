from __future__ import annotations

import argparse
import ast
import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


_ROOT_DIR = Path(__file__).resolve().parents[1]
_CHECKER_PATH = Path("tools/check_vendor_identity_evidence.py")
_IMPLEMENTATION_PATH = Path("tools/discover_vendor_identity_evidence.py")
_V003_POLICY_PATH = Path(
    "docs/vendor_id_003_read_only_vendor_discovery_baseline.md"
)
_V004B_POLICY_PATH = Path(
    "docs/vendor_id_004b_read_only_vendor_identity_discovery_contract.md"
)
_V003_POLICY_SHA256 = (
    "17363C85B514FA0A66E4A22A8A870F5B92C7AF1248105EC4E8A9076792F6A5F0"
)
_V004B_POLICY_SHA256 = (
    "226C4672F600028320F9395887D28BF9D7FDEF6A3C4BBC7B986C19368C95D414"
)
_PASS_MARKER = "vendor identity evidence readiness PASS"
_SELF_TEST_MARKER = "vendor identity evidence readiness self-test PASS"
_NORMAL_SCOPE = (
    "vendor_identity_evidence_guard_scope: "
    "exact_path_individual_node_source_bound_fail_closed"
)
_ISSUE_CODES = (
    "vendor_identity_evidence_path_drift",
    "vendor_identity_evidence_stage_drift",
    "vendor_identity_evidence_unresolved_target",
    "vendor_identity_evidence_ownership_conflict",
    "vendor_identity_evidence_forbidden_capability",
    "vendor_identity_evidence_checker_exemption",
    "vendor_identity_evidence_guard_contract_drift",
)
_ALLOWED_STAGES = ("004B1", "004B2", "004B3")
_ROUTED_MARKERS = (
    "VENDOR_DISCOVERY_EVIDENCE_NORMALIZATION_V1",
    "HMAC_SHA256_SAFE_REFERENCE_V1",
    "hmac-sha256-v1:",
)
_V003_OWNED_MARKERS = (
    "discover_vendor_organization_readiness",
    "VendorOrganizationDiscoveryError",
    "legacy_vendor_label_blank_or_invalid",
    "schema_or_source_unavailable",
    "unknown_unclassified_anomaly",
)
_FORBIDDEN_WORDS = (
    "approve_mapping",
    "approved_candidate",
    "authority_switch",
    "backfill",
    "canonical_candidate",
    "merge_identity",
    "repair",
    "runtime_consumer",
    "winner",
)
_FORBIDDEN_CALLS = (
    "connect",
    "create_engine",
    "execute",
    "executemany",
    "executescript",
    "getenv",
    "open",
    "putenv",
    "unlink",
    "write",
    "write_bytes",
    "write_text",
)
_FORBIDDEN_IMPORTS = (
    "app",
    "database",
    "flask",
    "models",
    "os",
    "psycopg",
    "psycopg2",
    "sqlalchemy",
    "sqlite3",
    "subprocess",
)
_SELF_AUDIT_NODE_NAMES = (
    "_ROOT_DIR",
    "_CHECKER_PATH",
    "_IMPLEMENTATION_PATH",
    "_V003_POLICY_PATH",
    "_V004B_POLICY_PATH",
    "_V003_POLICY_SHA256",
    "_V004B_POLICY_SHA256",
    "_PASS_MARKER",
    "_SELF_TEST_MARKER",
    "_NORMAL_SCOPE",
    "_ISSUE_CODES",
    "_ALLOWED_STAGES",
    "_ROUTED_MARKERS",
    "_V003_OWNED_MARKERS",
    "_FORBIDDEN_WORDS",
    "_FORBIDDEN_CALLS",
    "_FORBIDDEN_IMPORTS",
    "_SELF_AUDIT_NODE_NAMES",
    "_SELF_AUDIT_AST_SHA256",
    "_Issue",
    "_top_level_name",
    "_ast_sha256",
    "_ast_bundle_sha256",
    "_node_text",
    "_node_key",
    "_add_issue",
    "_read_bytes",
    "_policy_issues",
    "_stage_nodes",
    "_routed_nodes",
    "_inspect_source",
    "_self_audit",
    "_repository_issues",
    "_proof_payload",
    "_canonical_json",
    "_render_normal",
    "_parse_args",
    "_write_fixture",
    "_assert_fixture",
    "_run_self_test",
    "_main",
)
_SELF_AUDIT_AST_SHA256 = (
    "75EB9F7DC2ED6554CFDBE995C13B1E40960B7C534F5761CC37457AE49FC12CF0"
)


@dataclass(frozen=True, order=True)
class _Issue:
    code: str
    path: str
    line: int
    symbol: str


def _top_level_name(node: ast.AST) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        return target.id if isinstance(target, ast.Name) else ""
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return ""


def _ast_sha256(node: ast.AST) -> str:
    payload = ast.dump(
        node, annotate_fields=True, include_attributes=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _ast_bundle_sha256(nodes: Iterable[ast.AST]) -> str:
    payload = "\n".join(
        ast.dump(
            node,
            annotate_fields=True,
            include_attributes=False,
            indent=2,
        )
        for node in nodes
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _node_text(node: ast.AST) -> str:
    return " ".join(
        str(child.value) if isinstance(child, ast.Constant) else child.id
        if isinstance(child, ast.Name)
        else child.attr
        if isinstance(child, ast.Attribute)
        else ""
        for child in ast.walk(node)
    )


def _node_key(node: ast.AST, marker_family: str) -> list[object]:
    return [
        int(getattr(node, "lineno", 0)),
        int(getattr(node, "col_offset", 0)),
        int(getattr(node, "end_lineno", 0)),
        int(getattr(node, "end_col_offset", 0)),
        type(node).__name__,
        marker_family,
        _ast_sha256(node),
    ]


def _add_issue(
    issues: list[_Issue],
    code: str,
    path: Path,
    node: ast.AST | None = None,
    symbol: str = "",
) -> None:
    issues.append(
        _Issue(
            code,
            path.as_posix(),
            int(getattr(node, "lineno", 1)),
            symbol,
        )
    )


def _read_bytes(path: Path, relative: Path, issues: list[_Issue]) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        _add_issue(
            issues,
            "vendor_identity_evidence_guard_contract_drift",
            relative,
            symbol="read",
        )
        return None


def _policy_issues(root: Path) -> list[_Issue]:
    issues: list[_Issue] = []
    for relative, expected, markers in (
        (
            _V003_POLICY_PATH,
            _V003_POLICY_SHA256,
            (
                "## 20. VENDOR-ID-004B0D exact static-guard composition decision",
                "VENDOR-ID-004B0D STATIC GUARD COMPOSITION: FROZEN",
                "VENDOR-ID-004B0S: REQUIRED BEFORE IMPLEMENTATION",
            ),
        ),
        (
            _V004B_POLICY_PATH,
            _V004B_POLICY_SHA256,
            (
                "## 15. VENDOR-ID-004B0D exact static-guard composition decision",
                "VENDOR-ID-004B0D STATIC GUARD COMPOSITION: FROZEN",
                "VENDOR-ID-004B0S: REQUIRED BEFORE IMPLEMENTATION",
            ),
        ),
    ):
        payload = _read_bytes(root / relative, relative, issues)
        if payload is None:
            continue
        canonical_payload = payload.replace(b"\r\n", b"\n")
        digest = hashlib.sha256(canonical_payload).hexdigest().upper()
        if digest != expected:
            _add_issue(
                issues,
                "vendor_identity_evidence_guard_contract_drift",
                relative,
                symbol=f"sha256={digest}",
            )
            continue
        try:
            text = payload.decode("utf-8", errors="strict")
        except UnicodeError:
            _add_issue(
                issues,
                "vendor_identity_evidence_guard_contract_drift",
                relative,
                symbol="utf8",
            )
            continue
        for marker in markers:
            if text.count(marker) != 1:
                _add_issue(
                    issues,
                    "vendor_identity_evidence_guard_contract_drift",
                    relative,
                    symbol=hashlib.sha256(marker.encode()).hexdigest()[:12],
                )
    return issues


def _stage_nodes(tree: ast.Module) -> tuple[ast.AST, ...]:
    return tuple(
        node
        for node in tree.body
        if _top_level_name(node) == "_VENDOR_ID_004B_IMPLEMENTATION_STAGE"
    )


def _routed_nodes(tree: ast.Module) -> tuple[tuple[ast.AST, str], ...]:
    routed: list[tuple[ast.AST, str]] = []
    for node in tree.body:
        text = _node_text(node)
        families = tuple(marker for marker in _ROUTED_MARKERS if marker in text)
        if len(families) == 1:
            routed.append((node, families[0]))
        elif len(families) > 1:
            routed.append((node, "mixed_marker_family"))
    return tuple(routed)


def _inspect_source(
    relative: Path,
    payload: bytes,
) -> tuple[list[_Issue], str | None, list[list[object]]]:
    issues: list[_Issue] = []
    relative_text = relative.as_posix()
    canonical_text = _IMPLEMENTATION_PATH.as_posix()
    if relative_text != canonical_text:
        _add_issue(
            issues,
            "vendor_identity_evidence_path_drift",
            relative,
            symbol="not_canonical",
        )
        if relative_text.lower() == canonical_text.lower():
            _add_issue(
                issues,
                "vendor_identity_evidence_stage_drift",
                relative,
                symbol="case_aliased_path",
            )
    try:
        text = payload.decode("utf-8", errors="strict")
        tree = ast.parse(text, filename=relative.as_posix())
    except (UnicodeError, SyntaxError):
        _add_issue(
            issues,
            "vendor_identity_evidence_unresolved_target",
            relative,
            symbol="unparsed",
        )
        return issues, None, []
    stages = _stage_nodes(tree)
    stage: str | None = None
    if len(stages) != 1:
        _add_issue(
            issues,
            "vendor_identity_evidence_stage_drift",
            relative,
            symbol=f"count={len(stages)}",
        )
    else:
        value = stages[0].value if isinstance(stages[0], ast.Assign) else None
        if not isinstance(value, ast.Constant) or value.value not in _ALLOWED_STAGES:
            _add_issue(
                issues,
                "vendor_identity_evidence_stage_drift",
                relative,
                stages[0],
                "nonliteral_or_invalid",
            )
        else:
            stage = str(value.value)
            if tree.body.index(stages[0]) != 0:
                _add_issue(
                    issues,
                    "vendor_identity_evidence_stage_drift",
                    relative,
                    stages[0],
                    "stage_not_first",
                )
    module_evidence = _node_text(tree)
    module_lower = module_evidence.lower()
    if relative_text != canonical_text and (
        any(marker in module_evidence for marker in _ROUTED_MARKERS)
        or "discover_vendor_identity_evidence" in module_lower
        or "vendor_identity_evidence_normalization" in module_lower
        or "hmac_sha256_safe_reference" in module_lower
    ):
        _add_issue(
            issues,
            "vendor_identity_evidence_unresolved_target",
            relative,
            symbol="marker_outside_canonical_path",
        )
    if any(
        token in module_lower
        for token in (
            "whole_file",
            "whole_function",
            "subtree_exemption",
            "wildcard_exemption",
            "generic_allowlist",
            "ignore_path",
            "allow_all",
        )
    ):
        _add_issue(
            issues,
            "vendor_identity_evidence_checker_exemption",
            relative,
            symbol="broad_exemption",
        )
    unknown_markers = tuple(
        value
        for value in (
            child.value
            for child in ast.walk(tree)
            if isinstance(child, ast.Constant) and isinstance(child.value, str)
        )
        if (
            "VENDOR_DISCOVERY_EVIDENCE_" in value
            or "HMAC_SHA256_SAFE_REFERENCE_" in value
        )
        and value not in _ROUTED_MARKERS
    )
    if unknown_markers:
        _add_issue(
            issues,
            "vendor_identity_evidence_unresolved_target",
            relative,
            symbol="unknown_marker",
        )
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            if any("discover_vendor_identity_evidence" in name for name in names):
                _add_issue(
                    issues,
                    "vendor_identity_evidence_stage_drift",
                    relative,
                    node,
                    "wrapped_or_reexported",
                )
                break
    for node in ast.walk(tree):
        if isinstance(node, (ast.BinOp, ast.JoinedStr)):
            evidence = (
                "".join(
                    str(child.value)
                    for child in ast.walk(node)
                    if isinstance(child, ast.Constant)
                )
                + _node_text(node)
            ).lower()
            if any(
                token in evidence
                for token in (
                    "vendor_discovery_evidence",
                    "hmac_sha256_safe_reference",
                    "discover_vendor_identity_evidence",
                    "_vendor_id_004b_implementation_stage",
                )
            ):
                _add_issue(
                    issues,
                    "vendor_identity_evidence_unresolved_target",
                    relative,
                    node,
                    "dynamic_construction",
                )
                break
    routed = _routed_nodes(tree)
    keys: list[list[object]] = []
    for node, family in routed:
        if family == "mixed_marker_family":
            _add_issue(
                issues,
                "vendor_identity_evidence_ownership_conflict",
                relative,
                node,
                family,
            )
        else:
            keys.append(_node_key(node, family))
    for node in ast.walk(tree):
        evidence = _node_text(node).lower()
        if any(marker.lower() in evidence for marker in _V003_OWNED_MARKERS):
            _add_issue(
                issues,
                "vendor_identity_evidence_ownership_conflict",
                relative,
                node,
                "v003_owned",
            )
            break
        if any(word in evidence for word in _FORBIDDEN_WORDS):
            _add_issue(
                issues,
                "vendor_identity_evidence_forbidden_capability",
                relative,
                node,
                "forbidden_semantics",
            )
            break
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            if any(name.split(".", 1)[0] in _FORBIDDEN_IMPORTS for name in names):
                _add_issue(
                    issues,
                    "vendor_identity_evidence_forbidden_capability",
                    relative,
                    node,
                    "forbidden_import",
                )
                break
        if isinstance(node, ast.Call):
            name = ""
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name in {"eval", "exec", "__import__"}:
                _add_issue(
                    issues,
                    "vendor_identity_evidence_unresolved_target",
                    relative,
                    node,
                    f"dynamic_call={name}",
                )
                break
            if name in _FORBIDDEN_CALLS:
                _add_issue(
                    issues,
                    "vendor_identity_evidence_forbidden_capability",
                    relative,
                    node,
                    f"call={name}",
                )
                break
    if stage == "004B1":
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main":
                _add_issue(
                    issues,
                    "vendor_identity_evidence_stage_drift",
                    relative,
                    node,
                    "004B1_cli",
                )
    keys.sort(key=lambda key: tuple(key))
    return sorted(set(issues)), stage, keys


def _self_audit(root: Path) -> list[_Issue]:
    issues: list[_Issue] = []
    payload = _read_bytes(root / _CHECKER_PATH, _CHECKER_PATH, issues)
    if payload is None:
        return issues
    try:
        tree = ast.parse(payload, filename=_CHECKER_PATH.as_posix())
    except SyntaxError:
        _add_issue(
            issues,
            "vendor_identity_evidence_guard_contract_drift",
            _CHECKER_PATH,
            symbol="parse",
        )
        return issues
    names = tuple(filter(None, (_top_level_name(node) for node in tree.body)))
    if names != _SELF_AUDIT_NODE_NAMES:
        _add_issue(
            issues,
            "vendor_identity_evidence_guard_contract_drift",
            _CHECKER_PATH,
            symbol="node_inventory",
        )
    hash_nodes = tuple(
        node
        for node in tree.body
        if _top_level_name(node) != "_SELF_AUDIT_AST_SHA256"
    )
    if _ast_bundle_sha256(hash_nodes) != _SELF_AUDIT_AST_SHA256:
        _add_issue(
            issues,
            "vendor_identity_evidence_guard_contract_drift",
            _CHECKER_PATH,
            symbol="ast_bundle",
        )
    return issues


def _repository_issues(root: Path) -> tuple[list[_Issue], str]:
    issues = _policy_issues(root)
    issues.extend(_self_audit(root))
    canonical = root / _IMPLEMENTATION_PATH
    implementation_state = "not_started"
    if canonical.exists():
        payload = _read_bytes(canonical, _IMPLEMENTATION_PATH, issues)
        if payload is not None:
            source_issues, stage, _keys = _inspect_source(
                _IMPLEMENTATION_PATH, payload
            )
            issues.extend(source_issues)
            implementation_state = stage or "invalid"
        _add_issue(
            issues,
            "vendor_identity_evidence_forbidden_capability",
            _IMPLEMENTATION_PATH,
            symbol="004B0S_canonical_present",
        )
    for path in root.rglob("*.py"):
        relative = path.relative_to(root)
        relative_text = relative.as_posix()
        if relative_text == _IMPLEMENTATION_PATH.as_posix():
            continue
        if path.name == _IMPLEMENTATION_PATH.name:
            _add_issue(
                issues,
                "vendor_identity_evidence_path_drift",
                relative,
                symbol="same_filename",
            )
        elif (
            relative.parent.as_posix() == _IMPLEMENTATION_PATH.parent.as_posix()
            and "vendor_identity_evidence" in path.name
            and relative_text != _CHECKER_PATH.as_posix()
        ):
            _add_issue(
                issues,
                "vendor_identity_evidence_path_drift",
                relative,
                symbol="renamed_substitute",
            )
    return sorted(set(issues)), implementation_state


def _proof_payload(
    relative_text: str,
    expected_digest: str,
    payload: bytes,
) -> tuple[int, dict[str, object]]:
    relative = Path(relative_text)
    issues: list[_Issue] = []
    stage = "not_started"
    keys: list[list[object]] = []
    source_sha: str | None = None
    if relative_text != _IMPLEMENTATION_PATH.as_posix():
        _add_issue(
            issues,
            "vendor_identity_evidence_path_drift",
            relative,
            symbol="proof_path",
        )
    if expected_digest == "ABSENT":
        if payload:
            _add_issue(
                issues,
                "vendor_identity_evidence_stage_drift",
                relative,
                symbol="absent_with_bytes",
            )
    else:
        source_sha = hashlib.sha256(payload).hexdigest().upper()
        if expected_digest != source_sha or len(expected_digest) != 64:
            _add_issue(
                issues,
                "vendor_identity_evidence_guard_contract_drift",
                relative,
                symbol="source_sha256",
            )
        source_issues, observed_stage, keys = _inspect_source(relative, payload)
        issues.extend(source_issues)
        stage = observed_stage or "invalid"
    proof: dict[str, object] = {
        "canonical_path": _IMPLEMENTATION_PATH.as_posix(),
        "covered_node_keys": keys,
        "implementation_stage": stage,
        "issue_codes": sorted({issue.code for issue in issues}),
        "result": "PASS" if not issues else "FAIL",
        "source_sha256": source_sha,
    }
    return (0 if not issues else 1), proof


def _canonical_json(value: dict[str, object]) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _render_normal(issues: Sequence[_Issue], state: str) -> tuple[int, str]:
    lines = [
        _NORMAL_SCOPE,
        f"implementation_state: {state}",
        f"issues_count: {len(issues)}",
        "database_access: 0",
        "app_imports: 0",
    ]
    for issue in sorted(issues):
        lines.append(
            f"issue: {issue.code} path={issue.path} "
            f"line={issue.line} symbol={issue.symbol}"
        )
    if not issues:
        lines.append(_PASS_MARKER)
    return (0 if not issues else 1), "\n".join(lines) + "\n"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--composition-proof", action="store_true")
    parser.add_argument("canonical_path", nargs="?")
    parser.add_argument("source_sha256", nargs="?")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.composition_proof:
        if args.canonical_path is None or args.source_sha256 is None:
            parser.error("composition proof requires path and digest")
    elif args.canonical_path is not None or args.source_sha256 is not None:
        parser.error("positional arguments require --composition-proof")
    return args


def _write_fixture(root: Path, relative: Path, source: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8", newline="\n")


def _assert_fixture(
    relative: Path,
    source: str,
    expected_code: str | None,
) -> None:
    issues, _stage, _keys = _inspect_source(relative, source.encode("utf-8"))
    codes = {issue.code for issue in issues}
    if expected_code is None:
        if issues:
            raise AssertionError(f"positive fixture failed: {issues!r}")
    elif expected_code not in codes:
        raise AssertionError(
            f"negative fixture {relative.as_posix()} "
            f"missing {expected_code}: {sorted(codes)!r}; "
            f"source_sha256={hashlib.sha256(source.encode()).hexdigest()}"
        )


def _run_self_test() -> int:
    scenarios = 0
    with tempfile.TemporaryDirectory(
        prefix="vendor-id-004b0s-guard-self-test-"
    ) as temp_value:
        root = Path(temp_value)
        for relative in (_V003_POLICY_PATH, _V004B_POLICY_PATH, _CHECKER_PATH):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(_ROOT_DIR / relative, target)
        issues, state = _repository_issues(root)
        if issues or state != "not_started":
            raise AssertionError(_render_normal(issues, state)[1])
        scenarios += 1
        valid = (
            '_VENDOR_ID_004B_IMPLEMENTATION_STAGE = "004B1"\n'
            'NORMALIZATION = "VENDOR_DISCOVERY_EVIDENCE_NORMALIZATION_V1"\n'
        )
        _assert_fixture(_IMPLEMENTATION_PATH, valid, None)
        scenarios += 1
        cases = (
            (Path("services/discover_vendor_identity_evidence.py"), valid, "vendor_identity_evidence_path_drift"),
            (Path("tools/vendor_identity_evidence.py"), valid, "vendor_identity_evidence_path_drift"),
            (Path("tools/Discover_Vendor_Identity_Evidence.py"), valid, "vendor_identity_evidence_stage_drift"),
            (_IMPLEMENTATION_PATH, 'NORMALIZATION = "VENDOR_DISCOVERY_EVIDENCE_NORMALIZATION_V1"\n', "vendor_identity_evidence_stage_drift"),
            (_IMPLEMENTATION_PATH, '_VENDOR_ID_004B_IMPLEMENTATION_STAGE = "004B0S"\n', "vendor_identity_evidence_stage_drift"),
            (_IMPLEMENTATION_PATH, '_VENDOR_ID_004B_IMPLEMENTATION_STAGE = "004B1"\n_VENDOR_ID_004B_IMPLEMENTATION_STAGE = "004B1"\n', "vendor_identity_evidence_stage_drift"),
            (_IMPLEMENTATION_PATH, '_VENDOR_ID_004B_IMPLEMENTATION_STAGE = "004B" + "1"\n', "vendor_identity_evidence_stage_drift"),
            (_IMPLEMENTATION_PATH, 'VALUE = 1\n' + valid, "vendor_identity_evidence_stage_drift"),
            (_IMPLEMENTATION_PATH, '_VENDOR_ID_004B_IMPLEMENTATION_STAGE = "004B1"\nfrom tools.discover_vendor_identity_evidence import VALUE\n', "vendor_identity_evidence_stage_drift"),
            (_IMPLEMENTATION_PATH, '_VENDOR_ID_004B_IMPLEMENTATION_STAGE = "004B1"\nimport tools.discover_vendor_identity_evidence\n', "vendor_identity_evidence_stage_drift"),
            (Path("services/vendor_marker.py"), 'VALUE = "VENDOR_DISCOVERY_EVIDENCE_NORMALIZATION_V1"\n', "vendor_identity_evidence_unresolved_target"),
            (_IMPLEMENTATION_PATH, '_VENDOR_ID_004B_IMPLEMENTATION_STAGE = "004B1"\nVALUE = "VENDOR_DISCOVERY_EVIDENCE_UNKNOWN_V1"\n', "vendor_identity_evidence_unresolved_target"),
            (_IMPLEMENTATION_PATH, '_VENDOR_ID_004B_IMPLEMENTATION_STAGE = "004B" + "1"\nVALUE = "VENDOR_" + "DISCOVERY_EVIDENCE_NORMALIZATION_V1"\n', "vendor_identity_evidence_unresolved_target"),
            (_IMPLEMENTATION_PATH, valid + 'X = "discover_vendor_organization_readiness"\n', "vendor_identity_evidence_ownership_conflict"),
            (_IMPLEMENTATION_PATH, valid + 'X = "legacy_vendor_label_blank_or_invalid"\n', "vendor_identity_evidence_ownership_conflict"),
            (_IMPLEMENTATION_PATH, valid + 'def approve_mapping():\n    return "winner"\n', "vendor_identity_evidence_forbidden_capability"),
            (_IMPLEMENTATION_PATH, valid + 'def merge_identity():\n    return "canonical_candidate"\n', "vendor_identity_evidence_forbidden_capability"),
            (_IMPLEMENTATION_PATH, valid + 'def runtime_consumer():\n    return "authority_switch"\n', "vendor_identity_evidence_forbidden_capability"),
            (_IMPLEMENTATION_PATH, valid + 'def write(value):\n    return value\nwrite("apply")\n', "vendor_identity_evidence_forbidden_capability"),
            (_IMPLEMENTATION_PATH, valid + 'import sqlite3\n', "vendor_identity_evidence_forbidden_capability"),
            (_IMPLEMENTATION_PATH, valid + 'def main():\n    return 0\n', "vendor_identity_evidence_stage_drift"),
            (_IMPLEMENTATION_PATH, valid + 'VALUE = eval("1")\n', "vendor_identity_evidence_unresolved_target"),
            (_IMPLEMENTATION_PATH, valid + 'WHOLE_FILE = "wildcard_exemption"\n', "vendor_identity_evidence_checker_exemption"),
            (_IMPLEMENTATION_PATH, valid + 'A = "HMAC_SHA256_SAFE_REFERENCE_V1"\nB = "VENDOR_DISCOVERY_EVIDENCE_NORMALIZATION_V1"\n', None),
        )
        for relative, source, expected in cases:
            _assert_fixture(relative, source, expected)
            scenarios += 1
        status, proof = _proof_payload(
            _IMPLEMENTATION_PATH.as_posix(), "ABSENT", b""
        )
        expected_absent = {
            "canonical_path": _IMPLEMENTATION_PATH.as_posix(),
            "covered_node_keys": [],
            "implementation_stage": "not_started",
            "issue_codes": [],
            "result": "PASS",
            "source_sha256": None,
        }
        if status != 0 or proof != expected_absent:
            raise AssertionError("absence proof drift")
        scenarios += 1
        digest = hashlib.sha256(valid.encode()).hexdigest().upper()
        status, proof = _proof_payload(
            _IMPLEMENTATION_PATH.as_posix(), digest, valid.encode()
        )
        if status != 0 or proof["result"] != "PASS" or not proof["covered_node_keys"]:
            raise AssertionError("present proof drift")
        scenarios += 1
        status, proof = _proof_payload(
            _IMPLEMENTATION_PATH.as_posix(), "0" * 64, valid.encode()
        )
        if status == 0 or "vendor_identity_evidence_guard_contract_drift" not in proof["issue_codes"]:
            raise AssertionError("digest mismatch did not fail closed")
        scenarios += 1
        _write_fixture(root, _IMPLEMENTATION_PATH, valid)
        present_issues, _present_state = _repository_issues(root)
        if "vendor_identity_evidence_forbidden_capability" not in {
            issue.code for issue in present_issues
        }:
            raise AssertionError("004B0S canonical implementation did not fail")
        (root / _IMPLEMENTATION_PATH).unlink()
        scenarios += 1
        guard_path = root / _CHECKER_PATH
        guard_source = guard_path.read_text(encoding="utf-8")
        guard_path.write_text(
            guard_source + "\n_DRIFT = True\n",
            encoding="utf-8",
            newline="\n",
        )
        drift_issues, _drift_state = _repository_issues(root)
        if "vendor_identity_evidence_guard_contract_drift" not in {
            issue.code for issue in drift_issues
        }:
            raise AssertionError("guard self-audit drift did not fail")
        guard_path.write_text(guard_source, encoding="utf-8", newline="\n")
        scenarios += 1
    print(f"self_test_scenarios: {scenarios}")
    print("database_access: 0")
    print("app_imports: 0")
    print(_SELF_TEST_MARKER)
    return 0


def _main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.self_test:
        return _run_self_test()
    if args.composition_proof:
        payload = sys.stdin.buffer.read()
        status, proof = _proof_payload(
            args.canonical_path, args.source_sha256, payload
        )
        sys.stdout.buffer.write(_canonical_json(proof))
        return status
    issues, state = _repository_issues(_ROOT_DIR)
    status, output = _render_normal(issues, state)
    print(output, end="")
    return status


if __name__ == "__main__":
    raise SystemExit(_main())
