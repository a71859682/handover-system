from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
APP_PATH = ROOT_DIR / "app.py"


@dataclass(frozen=True)
class InventoryItem:
    route: str
    action: str
    target_tables: tuple[str, ...]
    category: str
    status: str
    risk: str
    site_scoped: str
    current_site_enforced: str
    ownership_validation_required: str
    recommendation: str
    source_markers: tuple[str, ...]


HIGH_RISK_ITEMS: tuple[InventoryItem, ...] = (
    InventoryItem(
        route="/api/progress",
        action="save_progress",
        target_tables=("progress",),
        category="high-risk non-admin site-scoped write path",
        status="ENFORCED",
        risk="high",
        site_scoped="yes",
        current_site_enforced="yes",
        ownership_validation_required="yes",
        recommendation="Current-site, site permission, and unit/task ownership validation are enforced before progress writes.",
        source_markers=(
            '@app.route("/api/progress", methods=["POST"])',
            'progress_context = authorize_progress_write(conn, unit_id=unit_id, task_id=task_id)',
            'return _handle_progress_write_lookup_error(exc)',
        ),
    ),
    InventoryItem(
        route="/api/unit-extra",
        action="save_unit_extra",
        target_tables=("unit_extra", "unit_extra_values"),
        category="high-risk non-admin site-scoped write path",
        status="ENFORCED",
        risk="high",
        site_scoped="yes",
        current_site_enforced="yes",
        ownership_validation_required="yes",
        recommendation="Current-site, site permission, and unit/field ownership validation are enforced before unit-extra writes.",
        source_markers=(
            '@app.route("/api/unit-extra", methods=["POST"])',
            'return _handle_unit_extra_write_lookup_error(exc)',
        ),
    ),
    InventoryItem(
        route="/api/vendor-contact",
        action="save_vendor_contact",
        target_tables=("vendor_contacts",),
        category="high-risk non-admin site-scoped write path",
        status="ENFORCED",
        risk="high",
        site_scoped="yes",
        current_site_enforced="yes",
        ownership_validation_required="yes",
        recommendation="Current-site, site permission, and sheet/vendor ownership validation are enforced before vendor-contact writes.",
        source_markers=(
            '@app.route("/api/vendor-contact", methods=["POST"])',
            'vendor_contact_context = authorize_vendor_contact_write(',
            'resolve_vendor_contact_write_context(',
            'return _handle_vendor_contact_lookup_error(exc)',
        ),
    ),
    InventoryItem(
        route="/api/vendor-work-entry",
        action="save_vendor_work_entry",
        target_tables=("vendor_work_entries",),
        category="high-risk non-admin site-scoped write path",
        status="ENFORCED",
        risk="high",
        site_scoped="yes",
        current_site_enforced="yes",
        ownership_validation_required="yes",
        recommendation="Current-site, site permission, and sheet/vendor ownership validation are enforced before vendor-work-entry writes.",
        source_markers=(
            '@app.route("/api/vendor-work-entry", methods=["POST"])',
            'vendor_work_entry_context = authorize_vendor_work_entry_write(',
            'resolve_vendor_work_entry_write_context(',
            'return _handle_vendor_work_entry_lookup_error(exc)',
        ),
    ),
)


MEDIUM_RISK_ITEMS: tuple[InventoryItem, ...] = (
    InventoryItem(
        route="/api/reset-sheet",
        action="reset_sheet",
        target_tables=("progress", "unit_extra", "unit_extra_values"),
        category="medium-risk admin global/site-scoped write path",
        status="INVENTORY ONLY",
        risk="medium",
        site_scoped="yes",
        current_site_enforced="not_applicable",
        ownership_validation_required="yes",
        recommendation="Define explicit admin global-write policy before formal write isolation enforcement.",
        source_markers=('@app.route("/api/reset-sheet", methods=["POST"])',),
    ),
    InventoryItem(
        route="/admin/table",
        action="create_sheet",
        target_tables=("sheets", "extra_fields"),
        category="medium-risk admin global/site-scoped write path",
        status="INVENTORY ONLY",
        risk="medium",
        site_scoped="yes",
        current_site_enforced="not_applicable",
        ownership_validation_required="yes",
        recommendation="Define explicit admin global-write policy before formal write isolation enforcement.",
        source_markers=('action == "create_sheet"',),
    ),
    InventoryItem(
        route="/admin/table",
        action="delete_sheet",
        target_tables=("sheets", "tasks", "floors", "units", "progress", "unit_extra", "unit_extra_values", "extra_fields"),
        category="medium-risk admin global/site-scoped write path",
        status="INVENTORY ONLY",
        risk="medium",
        site_scoped="yes",
        current_site_enforced="not_applicable",
        ownership_validation_required="yes",
        recommendation="Define explicit admin global-write policy before formal write isolation enforcement.",
        source_markers=('action == "delete_sheet"',),
    ),
    InventoryItem(
        route="/admin/table",
        action="add_task",
        target_tables=("tasks", "progress"),
        category="medium-risk admin global/site-scoped write path",
        status="INVENTORY ONLY",
        risk="medium",
        site_scoped="yes",
        current_site_enforced="not_applicable",
        ownership_validation_required="yes",
        recommendation="Define explicit admin global-write policy before formal write isolation enforcement.",
        source_markers=('action == "add_task"',),
    ),
    InventoryItem(
        route="/admin/table",
        action="delete_task",
        target_tables=("tasks", "progress"),
        category="medium-risk admin global/site-scoped write path",
        status="INVENTORY ONLY",
        risk="medium",
        site_scoped="yes",
        current_site_enforced="not_applicable",
        ownership_validation_required="yes",
        recommendation="Define explicit admin global-write policy before formal write isolation enforcement.",
        source_markers=('action.startswith("delete_task:")',),
    ),
    InventoryItem(
        route="/admin/table",
        action="add_extra_field",
        target_tables=("extra_fields",),
        category="medium-risk admin global/site-scoped write path",
        status="INVENTORY ONLY",
        risk="medium",
        site_scoped="yes",
        current_site_enforced="not_applicable",
        ownership_validation_required="yes",
        recommendation="Define explicit admin global-write policy before formal write isolation enforcement.",
        source_markers=('action == "add_extra_field"',),
    ),
    InventoryItem(
        route="/admin/table",
        action="delete_extra_field",
        target_tables=("extra_fields",),
        category="medium-risk admin global/site-scoped write path",
        status="INVENTORY ONLY",
        risk="medium",
        site_scoped="yes",
        current_site_enforced="not_applicable",
        ownership_validation_required="yes",
        recommendation="Define explicit admin global-write policy before formal write isolation enforcement.",
        source_markers=('action.startswith("delete_extra_field:")',),
    ),
    InventoryItem(
        route="/admin/table",
        action="add_floor",
        target_tables=("floors",),
        category="medium-risk admin global/site-scoped write path",
        status="INVENTORY ONLY",
        risk="medium",
        site_scoped="yes",
        current_site_enforced="not_applicable",
        ownership_validation_required="yes",
        recommendation="Define explicit admin global-write policy before formal write isolation enforcement.",
        source_markers=('action == "add_floor"',),
    ),
    InventoryItem(
        route="/admin/table",
        action="delete_floor",
        target_tables=("floors", "units", "progress", "unit_extra", "unit_extra_values"),
        category="medium-risk admin global/site-scoped write path",
        status="INVENTORY ONLY",
        risk="medium",
        site_scoped="yes",
        current_site_enforced="not_applicable",
        ownership_validation_required="yes",
        recommendation="Define explicit admin global-write policy before formal write isolation enforcement.",
        source_markers=('action.startswith("delete_floor:")',),
    ),
    InventoryItem(
        route="/admin/table",
        action="add_unit",
        target_tables=("units", "progress", "unit_extra"),
        category="medium-risk admin global/site-scoped write path",
        status="INVENTORY ONLY",
        risk="medium",
        site_scoped="yes",
        current_site_enforced="not_applicable",
        ownership_validation_required="yes",
        recommendation="Define explicit admin global-write policy before formal write isolation enforcement.",
        source_markers=('action.startswith("add_unit:")',),
    ),
    InventoryItem(
        route="/admin/table",
        action="delete_unit",
        target_tables=("units", "progress", "unit_extra", "unit_extra_values"),
        category="medium-risk admin global/site-scoped write path",
        status="INVENTORY ONLY",
        risk="medium",
        site_scoped="yes",
        current_site_enforced="not_applicable",
        ownership_validation_required="yes",
        recommendation="Define explicit admin global-write policy before formal write isolation enforcement.",
        source_markers=('action.startswith("delete_unit:")',),
    ),
    InventoryItem(
        route="/admin/table",
        action="default_save",
        target_tables=("sheets", "meta", "tasks", "extra_fields", "floors", "units"),
        category="medium-risk admin global/site-scoped write path",
        status="INVENTORY ONLY",
        risk="medium",
        site_scoped="yes",
        current_site_enforced="not_applicable",
        ownership_validation_required="yes",
        recommendation="Define explicit admin global-write policy before formal write isolation enforcement.",
        source_markers=('@app.route("/admin/table", methods=["GET", "POST"])', 'action = actions[-1] if actions else "save"'),
    ),
)


EXCLUDED_ITEMS: tuple[InventoryItem, ...] = (
    InventoryItem(
        route="/admin/users",
        action="create_user",
        target_tables=("users",),
        category="excluded non-goal path",
        status="EXCLUDED",
        risk="low",
        site_scoped="no",
        current_site_enforced="not_applicable",
        ownership_validation_required="no",
        recommendation="Keep out of P-3B write isolation; covered by user management stages.",
        source_markers=('action == "create_user"',),
    ),
    InventoryItem(
        route="/admin/users",
        action="update_user",
        target_tables=("users",),
        category="excluded non-goal path",
        status="EXCLUDED",
        risk="low",
        site_scoped="no",
        current_site_enforced="not_applicable",
        ownership_validation_required="no",
        recommendation="Keep out of P-3B write isolation; covered by user management stages.",
        source_markers=('action.startswith("update_user:")',),
    ),
    InventoryItem(
        route="/admin/users",
        action="delete_user",
        target_tables=("users", "user_site_permissions"),
        category="excluded non-goal path",
        status="EXCLUDED",
        risk="low",
        site_scoped="no",
        current_site_enforced="not_applicable",
        ownership_validation_required="no",
        recommendation="Keep out of P-3B write isolation; covered by user management stages.",
        source_markers=('action.startswith("delete_user:")',),
    ),
    InventoryItem(
        route="/admin/users",
        action="add_site_permission",
        target_tables=("user_site_permissions",),
        category="excluded non-goal path",
        status="EXCLUDED",
        risk="low",
        site_scoped="no",
        current_site_enforced="not_applicable",
        ownership_validation_required="no",
        recommendation="Keep out of P-3B write isolation; covered by site permission management stages.",
        source_markers=('action.startswith("add_site_permission:")',),
    ),
    InventoryItem(
        route="/admin/users",
        action="update_site_permission",
        target_tables=("user_site_permissions",),
        category="excluded non-goal path",
        status="EXCLUDED",
        risk="low",
        site_scoped="no",
        current_site_enforced="not_applicable",
        ownership_validation_required="no",
        recommendation="Keep out of P-3B write isolation; covered by site permission management stages.",
        source_markers=('action.startswith("update_site_permission:")',),
    ),
    InventoryItem(
        route="/admin/users",
        action="delete_site_permission",
        target_tables=("user_site_permissions",),
        category="excluded non-goal path",
        status="EXCLUDED",
        risk="low",
        site_scoped="no",
        current_site_enforced="not_applicable",
        ownership_validation_required="no",
        recommendation="Keep out of P-3B write isolation; covered by site permission management stages.",
        source_markers=('action.startswith("delete_site_permission:")',),
    ),
    InventoryItem(
        route="/login",
        action="login_session",
        target_tables=("session",),
        category="excluded non-goal path",
        status="EXCLUDED",
        risk="low",
        site_scoped="no",
        current_site_enforced="not_applicable",
        ownership_validation_required="no",
        recommendation="Keep out of P-3B write isolation; covered by auth lifecycle stages.",
        source_markers=('@app.route("/login", methods=["GET", "POST"])',),
    ),
    InventoryItem(
        route="/logout",
        action="logout_session_clear",
        target_tables=("session",),
        category="excluded non-goal path",
        status="EXCLUDED",
        risk="low",
        site_scoped="no",
        current_site_enforced="not_applicable",
        ownership_validation_required="no",
        recommendation="Keep out of P-3B write isolation; covered by auth lifecycle stages.",
        source_markers=('@app.route("/logout", methods=["POST"])',),
    ),
    InventoryItem(
        route="/site-selector",
        action="set_current_site",
        target_tables=("session",),
        category="excluded non-goal path",
        status="EXCLUDED",
        risk="low",
        site_scoped="no",
        current_site_enforced="not_applicable",
        ownership_validation_required="no",
        recommendation="Keep out of P-3B write isolation; covered by current-site lifecycle stages.",
        source_markers=('@app.route("/site-selector", methods=["GET", "POST"])',),
    ),
)


ALL_ITEMS = HIGH_RISK_ITEMS + MEDIUM_RISK_ITEMS + EXCLUDED_ITEMS


def expect(condition: bool, message: str, issues: list[str]) -> None:
    if not condition:
        issues.append(message)


def render_item(item: InventoryItem) -> None:
    print("---")
    print(f"route: {item.route}")
    print(f"action: {item.action}")
    print(f"target_tables: {', '.join(item.target_tables)}")
    print(f"category: {item.category}")
    print(f"status: {item.status}")
    print(f"risk: {item.risk}")
    print(f"site_scoped: {item.site_scoped}")
    print(f"current_site_enforced: {item.current_site_enforced}")
    print(f"ownership_validation_required: {item.ownership_validation_required}")
    print(f"recommendation: {item.recommendation}")


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


def _is_request_get_json_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "get_json"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "request"
    )


def _is_db_with(node: ast.With) -> bool:
    return any(
        isinstance(item.context_expr, ast.Call) and _call_name(item.context_expr) == "db"
        for item in node.items
    )


def _assigns_call_to_actor(node: ast.AST, call: ast.Call) -> bool:
    return (
        isinstance(node, ast.Assign)
        and node.value is call
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "actor"
    )


def _session_user_id_access(node: ast.AST) -> bool:
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "session":
        return isinstance(node.slice, ast.Constant) and node.slice.value == "user_id"
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "session"
        and node.args
    ):
        return isinstance(node.args[0], ast.Constant) and node.args[0].value == "user_id"
    return False


def validate_unit_extra_route_contract(source: str, issues: list[str]) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        issues.append("unit_extra_contract:source_syntax_error")
        return

    routes = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "api_unit_extra"
    ]
    if len(routes) != 1:
        issues.append("unit_extra_contract:route_definition_count")
        return
    route = routes[0]
    route_nodes = list(ast.walk(route))
    calls = [node for node in route_nodes if isinstance(node, ast.Call)]
    resolver_calls = [node for node in calls if _call_name(node) == "resolve_canonical_internal_mutation_actor"]
    request_calls = [node for node in calls if _is_request_get_json_call(node)]
    authorize_calls = [node for node in calls if _call_name(node) == "authorize_unit_extra_write"]

    if len(resolver_calls) != 1:
        issues.append("unit_extra_contract:canonical_resolver_call_count")
    if len(request_calls) != 1:
        issues.append("unit_extra_contract:request_get_json_call_count")
    if len(authorize_calls) != 1:
        issues.append("unit_extra_contract:authorize_call_count")

    resolver_call = resolver_calls[0] if len(resolver_calls) == 1 else None
    request_call = request_calls[0] if len(request_calls) == 1 else None
    authorize_call = authorize_calls[0] if len(authorize_calls) == 1 else None

    if resolver_call is not None and not any(_assigns_call_to_actor(node, resolver_call) for node in route_nodes):
        issues.append("unit_extra_contract:canonical_actor_assignment_required")

    target_withs = [
        node
        for node in route_nodes
        if isinstance(node, ast.With)
        and _is_db_with(node)
        and authorize_call is not None
        and any(descendant is authorize_call for descendant in ast.walk(node))
    ]
    if len(target_withs) != 1:
        issues.append("unit_extra_contract:target_db_context_count")
        target_with = None
    else:
        target_with = target_withs[0]

    if resolver_call is not None and request_call is not None and target_with is not None and authorize_call is not None:
        positions = (
            (resolver_call.lineno, resolver_call.col_offset),
            (request_call.lineno, request_call.col_offset),
            (target_with.lineno, target_with.col_offset),
            (authorize_call.lineno, authorize_call.col_offset),
        )
        if not positions[0] < positions[1] < positions[2] < positions[3]:
            issues.append("unit_extra_contract:source_order_invalid")

    if authorize_call is not None:
        internal_user_keywords = [keyword for keyword in authorize_call.keywords if keyword.arg == "internal_user"]
        if not (
            len(internal_user_keywords) == 1
            and isinstance(internal_user_keywords[0].value, ast.Name)
            and internal_user_keywords[0].value.id == "actor"
        ):
            issues.append("unit_extra_contract:internal_user_actor_required")

    if any(_call_name(node) == "_current_internal_user" for node in calls):
        issues.append("unit_extra_contract:current_internal_user_forbidden")
    if any(_session_user_id_access(node) for node in route_nodes):
        issues.append("unit_extra_contract:direct_session_user_id_forbidden")


def run_unit_extra_contract_self_test() -> int:
    valid_source = '''
def api_unit_extra():
    actor = resolve_canonical_internal_mutation_actor()
    data = request.get_json(force=True)
    with db() as conn:
        context = authorize_unit_extra_write(conn, unit_id=1, field_key="handover", internal_user=actor)
    return context
'''
    valid_issues: list[str] = []
    validate_unit_extra_route_contract(valid_source, valid_issues)
    if valid_issues:
        raise SystemExit(f"FAIL unit-extra checker rejected valid fixture: {valid_issues}")

    negative_fixtures = (
        (
            "missing_internal_user",
            valid_source.replace(', internal_user=actor', ''),
            "unit_extra_contract:internal_user_actor_required",
        ),
        (
            "resolver_after_target_db",
            '''
def api_unit_extra():
    data = request.get_json(force=True)
    with db() as conn:
        actor = resolve_canonical_internal_mutation_actor()
        context = authorize_unit_extra_write(conn, unit_id=1, field_key="handover", internal_user=actor)
    return context
''',
            "unit_extra_contract:source_order_invalid",
        ),
        (
            "current_internal_user_fallback",
            valid_source.replace('data = request.get_json(force=True)', 'fallback = _current_internal_user()\n    data = request.get_json(force=True)'),
            "unit_extra_contract:current_internal_user_forbidden",
        ),
        (
            "direct_session_user_id",
            valid_source.replace('data = request.get_json(force=True)', 'audit_id = session["user_id"]\n    data = request.get_json(force=True)'),
            "unit_extra_contract:direct_session_user_id_forbidden",
        ),
        (
            "comment_only_old_call",
            '''
def api_unit_extra():
    actor = resolve_canonical_internal_mutation_actor()
    data = request.get_json(force=True)
    with db() as conn:
        # unit_extra_context = authorize_unit_extra_write(conn, unit_id=unit_id, field_key=field)
        "unit_extra_context = authorize_unit_extra_write(conn, unit_id=unit_id, field_key=field)"
    return data
''',
            "unit_extra_contract:authorize_call_count",
        ),
    )
    for label, fixture, expected_issue in negative_fixtures:
        fixture_issues: list[str] = []
        validate_unit_extra_route_contract(fixture, fixture_issues)
        if expected_issue not in fixture_issues:
            raise SystemExit(
                f"FAIL unit-extra checker negative fixture {label} missed {expected_issue}: {fixture_issues}"
            )

    print("PASS unit extra readiness checker negative controls passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check site write isolation readiness inventory.")
    parser.add_argument("--self-test", action="store_true", help="Run in-memory unit-extra AST negative controls.")
    args = parser.parse_args()
    if args.self_test:
        return run_unit_extra_contract_self_test()

    print("site_write_isolation_readiness_scope: high_risk_group_full_enforcement")
    print(f"app_source: {APP_PATH}")
    print("WARNING P-3B-2D completes high-risk non-admin write isolation enforcement")
    print("WARNING medium-risk admin/global write paths remain inventory only")
    print("WARNING formal enforcement for medium-risk paths is deferred to a later stage")

    source = APP_PATH.read_text(encoding="utf-8")
    issues: list[str] = []

    expect(APP_PATH.exists(), "app.py_missing", issues)
    expect(len(HIGH_RISK_ITEMS) == 4, "high_risk_inventory_count_mismatch", issues)
    expect(len(MEDIUM_RISK_ITEMS) == 12, "medium_risk_inventory_count_mismatch", issues)
    expect(len(EXCLUDED_ITEMS) == 9, "excluded_inventory_count_mismatch", issues)

    print(f"inventory_total: {len(ALL_ITEMS)}")
    print(f"inventory_high_risk: {len(HIGH_RISK_ITEMS)}")
    print(f"inventory_medium_risk: {len(MEDIUM_RISK_ITEMS)}")
    print(f"inventory_excluded: {len(EXCLUDED_ITEMS)}")

    for item in ALL_ITEMS:
        missing_markers = [marker for marker in item.source_markers if marker not in source]
        expect(not missing_markers, f"missing_source_marker:{item.route}:{item.action}", issues)
        render_item(item)

    validate_unit_extra_route_contract(source, issues)

    print(f"issues_count: {len(issues)}")
    if issues:
        for issue in issues:
            print(f"ISSUE {issue}")
        raise SystemExit("FAIL site write isolation readiness check failed.")

    print("PASS site write isolation readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
