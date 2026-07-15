from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
APP_PATH = ROOT_DIR / "app.py"


@dataclass(frozen=True)
class AdminWriteItem:
    action: str
    target_tables: tuple[str, ...]
    category: str
    status: str
    uses_current_site: str
    current_site_enforced: str
    can_cross_site_today: str
    recommendation: str
    risk: str
    notes: tuple[str, ...]
    source_markers: tuple[str, ...]
    global_settings_path: str | None = None
    site_content_path: str | None = None
    site_content_current_site_enforced: str | None = None
    template_split: str | None = None
    ui_action_split: str | None = None


ADMIN_TABLE_ITEMS: tuple[AdminWriteItem, ...] = (
    AdminWriteItem(
        action="create_sheet",
        target_tables=("sheets", "extra_fields"),
        category="SITE_SCOPED",
        status="ENFORCED",
        uses_current_site="yes",
        current_site_enforced="yes",
        can_cross_site_today="no",
        recommendation="New sheets are now written to current_site_id for admin site-scoped content writes.",
        risk="medium",
        notes=("writes new sheet to current_site_id",),
        source_markers=(
            '@app.route("/admin/table", methods=["GET", "POST"])',
            'if action == "create_sheet":',
            'create_sheet_context = authorize_admin_create_sheet_site(conn)',
            'def authorize_admin_create_sheet_site(conn: sqlite3.Connection) -> dict[str, int]:',
            'INSERT INTO sheets (name, sort_order, site_id) VALUES (?, ?, ?)',
        ),
    ),
    AdminWriteItem(
        action="delete_sheet",
        target_tables=("sheets", "tasks", "floors", "units", "progress", "unit_extra", "unit_extra_values", "extra_fields"),
        category="SITE_SCOPED",
        status="ENFORCED",
        uses_current_site="yes",
        current_site_enforced="yes",
        can_cross_site_today="no",
        recommendation="Sheet delete is now blocked unless the target sheet belongs to current_site_id.",
        risk="high",
        notes=(),
        source_markers=(
            'if action == "delete_sheet":',
            'delete_sheet_context = authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)',
            'def authorize_admin_site_scoped_write(conn: sqlite3.Connection, *, sheet_id: int) -> dict[str, int]:',
            'DELETE FROM sheets WHERE id = ?',
        ),
    ),
    AdminWriteItem(
        action="save",
        target_tables=("sheets", "meta", "tasks", "extra_fields", "floors", "units"),
        category="MIXED",
        status="INTERNAL_SPLIT",
        uses_current_site="site_content_only",
        current_site_enforced="site_content_only",
        can_cross_site_today="no",
        recommendation="Save keeps a single route/action, but now separates global meta updates from current-site-enforced site content updates.",
        risk="high",
        notes=("save is mixed: meta + site content", "final explicit action split deferred"),
        source_markers=(
            'action = actions[-1] if actions else "save"',
            'def save_admin_global_settings(conn: sqlite3.Connection, *, form) -> None:',
            'def save_admin_site_content(conn: sqlite3.Connection, *, sheet_id: int, form) -> None:',
            'authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)',
            'save_admin_global_settings(conn, form=request.form)',
            'save_admin_site_content(conn, sheet_id=sheet_id, form=request.form)',
        ),
        global_settings_path="yes",
        site_content_path="yes",
        site_content_current_site_enforced="yes",
        template_split="no",
        ui_action_split="no",
    ),
    AdminWriteItem(
        action="add_task",
        target_tables=("tasks", "progress"),
        category="SITE_SCOPED",
        status="ENFORCED",
        uses_current_site="yes",
        current_site_enforced="yes",
        can_cross_site_today="no",
        recommendation="Task create is now blocked unless the target sheet belongs to current_site_id.",
        risk="medium",
        notes=(),
        source_markers=(
            'if action == "add_task":',
            'authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)',
            'INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?)',
        ),
    ),
    AdminWriteItem(
        action="delete_task",
        target_tables=("tasks", "progress"),
        category="SITE_SCOPED",
        status="ENFORCED",
        uses_current_site="yes",
        current_site_enforced="yes",
        can_cross_site_today="no",
        recommendation="Task delete is now blocked unless the target task belongs to route sheet and current_site_id.",
        risk="medium",
        notes=("task delete validates task_id belongs to route sheet",),
        source_markers=(
            'if action.startswith("delete_task:"):',
            'task_row = resolve_task_sheet_for_admin_write(conn, task_id=task_id)',
            'raise LookupError("task_sheet_mismatch")',
            'DELETE FROM tasks WHERE id = ? AND sheet_id = ?',
        ),
    ),
    AdminWriteItem(
        action="add_extra_field",
        target_tables=("extra_fields",),
        category="SITE_SCOPED",
        status="ENFORCED",
        uses_current_site="yes",
        current_site_enforced="yes",
        can_cross_site_today="no",
        recommendation="Extra-field create is now blocked unless the target sheet belongs to current_site_id.",
        risk="medium",
        notes=(),
        source_markers=(
            'if action == "add_extra_field":',
            'authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)',
            "INSERT INTO extra_fields",
        ),
    ),
    AdminWriteItem(
        action="delete_extra_field",
        target_tables=("extra_fields",),
        category="SITE_SCOPED",
        status="ENFORCED",
        uses_current_site="yes",
        current_site_enforced="yes",
        can_cross_site_today="no",
        recommendation="Extra-field delete is now blocked unless the target field belongs to route sheet and current_site_id.",
        risk="medium",
        notes=("extra-field delete validates field_id belongs to route sheet",),
        source_markers=(
            'if action.startswith("delete_extra_field:"):',
            'field_row = resolve_extra_field_sheet_for_admin_write(conn, field_id=field_id)',
            'raise LookupError("extra_field_sheet_mismatch")',
            "UPDATE extra_fields SET active = 0 WHERE id = ? AND sheet_id = ?",
        ),
    ),
    AdminWriteItem(
        action="add_floor",
        target_tables=("floors",),
        category="SITE_SCOPED",
        status="ENFORCED",
        uses_current_site="yes",
        current_site_enforced="yes",
        can_cross_site_today="no",
        recommendation="Floor create is now blocked unless the target sheet belongs to current_site_id.",
        risk="medium",
        notes=(),
        source_markers=(
            'if action == "add_floor":',
            'authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)',
            'INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, 0)',
        ),
    ),
    AdminWriteItem(
        action="delete_floor",
        target_tables=("floors", "units", "progress", "unit_extra", "unit_extra_values"),
        category="SITE_SCOPED",
        status="ENFORCED",
        uses_current_site="yes",
        current_site_enforced="yes",
        can_cross_site_today="no",
        recommendation="Floor delete is now blocked unless the target floor belongs to route sheet and current_site_id.",
        risk="high",
        notes=("floor delete validates floor_id belongs to route sheet",),
        source_markers=(
            'if action.startswith("delete_floor:"):',
            'floor_row = resolve_floor_sheet_for_admin_write(conn, floor_id=floor_id)',
            'raise LookupError("floor_sheet_mismatch")',
            'DELETE FROM floors WHERE id = ? AND sheet_id = ?',
        ),
    ),
    AdminWriteItem(
        action="add_unit",
        target_tables=("units", "progress", "unit_extra"),
        category="SITE_SCOPED",
        status="ENFORCED",
        uses_current_site="yes",
        current_site_enforced="yes",
        can_cross_site_today="no",
        recommendation="Unit create is now blocked unless the target floor belongs to route sheet and current_site_id.",
        risk="medium",
        notes=(),
        source_markers=(
            'if action.startswith("add_unit:"):',
            'floor_row = resolve_floor_sheet_for_admin_write(conn, floor_id=floor_id)',
            'INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?)',
            'INSERT INTO unit_extra (unit_id, handover) VALUES (?, ?)',
            'UPDATE floors SET unit_count = (SELECT COUNT(*) FROM units WHERE floor_id = ?) WHERE id = ?',
        ),
    ),
    AdminWriteItem(
        action="delete_unit",
        target_tables=("units", "progress", "unit_extra", "unit_extra_values"),
        category="SITE_SCOPED",
        status="ENFORCED",
        uses_current_site="yes",
        current_site_enforced="yes",
        can_cross_site_today="no",
        recommendation="Unit delete is now blocked unless the target unit belongs to route sheet and current_site_id.",
        risk="high",
        notes=("unit delete validates unit_id belongs to route sheet",),
        source_markers=(
            'if action.startswith("delete_unit:"):',
            'unit_row = resolve_unit_sheet_for_admin_write(conn, unit_id=unit_id)',
            'raise LookupError("unit_sheet_mismatch")',
            'DELETE FROM units WHERE id = ?',
        ),
    ),
    AdminWriteItem(
        action="reset_sheet",
        target_tables=("progress", "unit_extra", "unit_extra_values"),
        category="SITE_SCOPED",
        status="ENFORCED",
        uses_current_site="yes",
        current_site_enforced="yes",
        can_cross_site_today="no",
        recommendation="Reset sheet is now blocked unless the target sheet belongs to current_site_id.",
        risk="high",
        notes=("destructive_candidate resolved",),
        source_markers=(
            '@app.route("/api/reset-sheet", methods=["POST"])',
            'authorize_admin_site_scoped_write(conn, sheet_id=sheet_id)',
            'UPDATE progress',
            'UPDATE unit_extra',
            'DELETE FROM unit_extra_values',
        ),
    ),
)


def expect(condition: bool, message: str, issues: list[str]) -> None:
    if not condition:
        issues.append(message)


def render_item(item: AdminWriteItem) -> None:
    print("---")
    print(f"action: {item.action}")
    print(f"target_tables: {', '.join(item.target_tables)}")
    print(f"category: {item.category}")
    print(f"status: {item.status}")
    print(f"uses_current_site: {item.uses_current_site}")
    print(f"current_site_enforced: {item.current_site_enforced}")
    print(f"can_cross_site_today: {item.can_cross_site_today}")
    print(f"recommendation: {item.recommendation}")
    print(f"risk: {item.risk}")
    if item.notes:
        print(f"notes: {'; '.join(item.notes)}")
    if item.global_settings_path is not None:
        print(f"global_settings_path: {item.global_settings_path}")
    if item.site_content_path is not None:
        print(f"site_content_path: {item.site_content_path}")
    if item.site_content_current_site_enforced is not None:
        print(f"site_content_current_site_enforced: {item.site_content_current_site_enforced}")
    if item.template_split is not None:
        print(f"template_split: {item.template_split}")
    if item.ui_action_split is not None:
        print(f"ui_action_split: {item.ui_action_split}")


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    return None


def _is_request_form_access(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute) and node.attr == "form":
        return isinstance(node.value, ast.Name) and node.value.id == "request"
    return False


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


def _session_accesses_role(node: ast.AST) -> bool:
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "session":
        return isinstance(node.slice, ast.Constant) and node.slice.value == "role"
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "session"
        and node.args
    ):
        return isinstance(node.args[0], ast.Constant) and node.args[0].value == "role"
    return False


def _session_accesses_user_id(node: ast.AST) -> bool:
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


def _actor_role_access(node: ast.AST) -> bool:
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "actor"
        and node.func.attr == "get"
        and node.args
    ):
        return isinstance(node.args[0], ast.Constant) and node.args[0].value == "role"
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "actor":
        return isinstance(node.slice, ast.Constant) and node.slice.value == "role"
    return False


def _is_actor_role_non_admin_test(node: ast.AST) -> bool:
    if not isinstance(node, ast.Compare):
        return False
    if len(node.ops) != 1 or len(node.comparators) != 1:
        return False
    comparator = node.comparators[0]
    if not (isinstance(comparator, ast.Constant) and comparator.value == "admin"):
        return False
    if not isinstance(node.ops[0], ast.NotEq):
        return False
    candidate = node.left
    if isinstance(candidate, ast.Call):
        if not (
            isinstance(candidate.func, ast.Attribute)
            and candidate.func.attr == "strip"
            and not candidate.args
            and not candidate.keywords
        ):
            return False
        strip_target = candidate.func.value
        if (
            isinstance(strip_target, ast.Call)
            and isinstance(strip_target.func, ast.Name)
            and strip_target.func.id == "str"
            and len(strip_target.args) == 1
            and not strip_target.keywords
        ):
            strip_target = strip_target.args[0]
        if not isinstance(strip_target, ast.BoolOp) or not isinstance(strip_target.op, ast.Or):
            return False
        if len(strip_target.values) != 2:
            return False
        if not _actor_role_access(strip_target.values[0]):
            return False
        fallback = strip_target.values[1]
        return isinstance(fallback, ast.Constant) and fallback.value == ""
    return _actor_role_access(candidate)


def _position(node: ast.AST) -> tuple[int, int]:
    return (node.lineno, node.col_offset)


def _find_post_block(route: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt] | None:
    for node in route.body:
        if isinstance(node, ast.If):
            test = node.test
            if (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Attribute)
                and isinstance(test.left.value, ast.Name)
                and test.left.value.id == "request"
                and test.left.attr == "method"
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Eq)
                and len(test.comparators) == 1
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value == "POST"
            ):
                return node.body
    return None


def _is_direct_return_helper_statement(stmt: ast.stmt, helper_name: str) -> bool:
    if not isinstance(stmt, ast.Return):
        return False
    value = stmt.value
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == helper_name
        and not value.args
        and not value.keywords
    )


def _except_handler_returns_helper(handler: ast.ExceptHandler, helper_name: str) -> bool:
    if handler.type is None:
        return False
    handler_type = handler.type
    if isinstance(handler_type, ast.Name):
        is_lookup_error = handler_type.id == "LookupError"
    else:
        is_lookup_error = False
    if not is_lookup_error:
        return False
    return len(handler.body) == 1 and _is_direct_return_helper_statement(handler.body[0], helper_name)


def _is_exact_canonical_resolver_assignment(stmt: ast.stmt) -> bool:
    if not isinstance(stmt, ast.Assign):
        return False
    if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
        return False
    if stmt.targets[0].id != "actor" or not isinstance(stmt.value, ast.Call):
        return False
    return (
        _call_name(stmt.value) == "resolve_canonical_internal_mutation_actor"
        and not stmt.value.args
        and not stmt.value.keywords
    )


def _is_exact_canonical_resolver_guard(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.Try)
        and len(stmt.body) == 1
        and _is_exact_canonical_resolver_assignment(stmt.body[0])
        and len(stmt.handlers) == 1
        and _except_handler_returns_helper(
            stmt.handlers[0], "_redirect_admin_users_auth_required"
        )
        and not stmt.orelse
        and not stmt.finalbody
    )


def _is_exact_canonical_role_guard(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.If)
        and _is_actor_role_non_admin_test(stmt.test)
        and len(stmt.body) == 1
        and _is_direct_return_helper_statement(
            stmt.body[0], "_redirect_admin_users_admin_required"
        )
        and not stmt.orelse
    )


def _find_resolver_guard_statement(post_block: list[ast.stmt]) -> tuple[int | None, ast.Try | None]:
    for index, stmt in enumerate(post_block):
        if not isinstance(stmt, ast.Try):
            continue
        resolver_calls = [
            node for node in ast.walk(ast.Module(body=stmt.body, type_ignores=[]))
            if isinstance(node, ast.Call) and _call_name(node) == "resolve_canonical_internal_mutation_actor"
        ]
        if len(resolver_calls) != 1:
            continue
        resolver_call = resolver_calls[0]
        if not any(_assigns_call_to_actor(node, resolver_call) for node in stmt.body):
            continue
        if any(_except_handler_returns_helper(handler, "_redirect_admin_users_auth_required") for handler in stmt.handlers):
            return index, stmt
    return None, None


def _find_role_guard_statement(post_block: list[ast.stmt]) -> tuple[int | None, ast.If | None]:
    for index, stmt in enumerate(post_block):
        if not isinstance(stmt, ast.If):
            continue
        if not _is_actor_role_non_admin_test(stmt.test):
            continue
        return index, stmt
    return None, None


def _stmt_contains_request_form(stmt: ast.stmt) -> bool:
    return any(_is_request_form_access(node) for node in ast.walk(stmt))


def _stmt_contains_db_with(stmt: ast.stmt) -> bool:
    return any(isinstance(node, ast.With) and _is_db_with(node) for node in ast.walk(stmt))


def _stmt_contains_dual_write(stmt: ast.stmt) -> bool:
    return any(
        isinstance(node, ast.Call)
        and _call_name(node) in {
            "maybe_dual_write_user_create",
            "maybe_dual_write_user_role_update",
            "maybe_dual_write_user_delete",
        }
        for node in ast.walk(stmt)
    )


def _stmt_contains_mutation_capable_operation(stmt: ast.stmt) -> bool:
    sqlite_mutators = {
        "create_user_sqlite",
        "update_user_role_sqlite",
        "delete_user_sqlite",
        "create_user_site_permission_sqlite",
        "update_user_site_permission_role_sqlite",
        "delete_user_site_permission_sqlite",
        "create_user_postgres",
        "update_user_role_postgres",
        "delete_user_postgres",
        "get_primary_postgres_connection",
        "maybe_dual_write_user_create",
        "maybe_dual_write_user_role_update",
        "maybe_dual_write_user_delete",
    }
    for node in ast.walk(stmt):
        if isinstance(node, ast.Call):
            if _call_name(node) in sqlite_mutators:
                return True
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "execute"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                sql = " ".join(node.args[0].value.lower().split())
                if sql.startswith(("insert ", "update ", "delete ", "replace ")):
                    return True
        if isinstance(node, ast.With) and _is_db_with(node):
            return True
    return False


def validate_admin_users_route_contract(source: str, issues: list[str]) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        issues.append("admin_users_contract:source_syntax_error")
        return

    routes = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "users"
    ]
    if len(routes) != 1:
        issues.append("admin_users_contract:route_definition_count")
        return
    route = routes[0]
    post_block = _find_post_block(route)
    if post_block is None:
        issues.append("admin_users_contract:missing_post_block")
        return

    if (
        len(post_block) < 2
        or not _is_exact_canonical_resolver_guard(post_block[0])
        or not _is_exact_canonical_role_guard(post_block[1])
    ):
        issues.append("admin_users_contract:canonical_guard_safe_prefix")

    post_module = ast.Module(body=post_block, type_ignores=[])
    post_nodes = list(ast.walk(post_module))
    post_calls = [node for node in post_nodes if isinstance(node, ast.Call)]
    resolver_calls = [node for node in post_calls if _call_name(node) == "resolve_canonical_internal_mutation_actor"]
    auth_redirect_calls = [node for node in post_calls if _call_name(node) == "_redirect_admin_users_auth_required"]
    admin_redirect_calls = [node for node in post_calls if _call_name(node) == "_redirect_admin_users_admin_required"]
    dual_write_calls = [
        node
        for node in post_calls
        if _call_name(node) in {
            "maybe_dual_write_user_create",
            "maybe_dual_write_user_role_update",
            "maybe_dual_write_user_delete",
        }
    ]
    db_withs = [node for node in post_nodes if isinstance(node, ast.With) and _is_db_with(node)]
    request_form_nodes = [node for node in post_nodes if _is_request_form_access(node)]
    actor_role_nodes = [node for node in post_nodes if _actor_role_access(node)]

    if len(resolver_calls) != 1:
        issues.append("admin_users_contract:canonical_resolver_call_count")
    if len(auth_redirect_calls) != 1:
        issues.append("admin_users_contract:auth_redirect_call_count")
    if len(admin_redirect_calls) != 1:
        issues.append("admin_users_contract:admin_redirect_call_count")
    if not db_withs:
        issues.append("admin_users_contract:target_db_context_missing")
    if not request_form_nodes:
        issues.append("admin_users_contract:request_form_access_missing")
    if not actor_role_nodes:
        issues.append("admin_users_contract:actor_role_gate_missing")
    if len(dual_write_calls) != 3:
        issues.append("admin_users_contract:dual_write_call_inventory")

    resolver_stmt_index, resolver_stmt = _find_resolver_guard_statement(post_block)
    role_stmt_index, role_stmt = _find_role_guard_statement(post_block)
    if resolver_stmt is None:
        issues.append("admin_users_contract:invalid_actor_guard_enforcement")
    if role_stmt is None:
        issues.append("admin_users_contract:canonical_role_guard_enforcement")

    resolver_call = resolver_calls[0] if len(resolver_calls) == 1 else None
    if resolver_call is not None and not any(_assigns_call_to_actor(node, resolver_call) for node in post_nodes):
        issues.append("admin_users_contract:canonical_actor_assignment_required")

    if resolver_stmt is not None:
        if resolver_stmt.orelse or resolver_stmt.finalbody:
            issues.append("admin_users_contract:invalid_actor_guard_enforcement")
        if len(resolver_stmt.body) != 1 or not any(_assigns_call_to_actor(node, resolver_call) for node in resolver_stmt.body):
            issues.append("admin_users_contract:invalid_actor_guard_enforcement")
        if not any(_except_handler_returns_helper(handler, "_redirect_admin_users_auth_required") for handler in resolver_stmt.handlers):
            issues.append("admin_users_contract:invalid_actor_guard_enforcement")

    if role_stmt is not None:
        if role_stmt.orelse:
            issues.append("admin_users_contract:canonical_role_guard_enforcement")
        if not _is_actor_role_non_admin_test(role_stmt.test):
            issues.append("admin_users_contract:canonical_role_guard_enforcement")
        if len(role_stmt.body) != 1 or not _is_direct_return_helper_statement(
            role_stmt.body[0], "_redirect_admin_users_admin_required"
        ):
            issues.append("admin_users_contract:canonical_role_guard_enforcement")

    if resolver_call is not None and request_form_nodes:
        first_form_access = min(request_form_nodes, key=_position)
        if not _position(resolver_call) < _position(first_form_access):
            issues.append("admin_users_contract:resolver_must_precede_request_form")

    if actor_role_nodes and request_form_nodes:
        first_role_access = min(actor_role_nodes, key=_position)
        first_form_access = min(request_form_nodes, key=_position)
        if not _position(first_role_access) < _position(first_form_access):
            issues.append("admin_users_contract:role_gate_must_precede_request_form")

    if resolver_call is not None and db_withs:
        first_db_with = min(db_withs, key=_position)
        if not _position(resolver_call) < _position(first_db_with):
            issues.append("admin_users_contract:resolver_must_precede_target_db")

    if actor_role_nodes and db_withs:
        first_role_access = min(actor_role_nodes, key=_position)
        first_db_with = min(db_withs, key=_position)
        if not _position(first_role_access) < _position(first_db_with):
            issues.append("admin_users_contract:role_gate_must_precede_target_db")

    if db_withs and dual_write_calls:
        first_db_with = min(db_withs, key=_position)
        first_dual_write = min(dual_write_calls, key=_position)
        if not _position(first_db_with) < _position(first_dual_write):
            issues.append("admin_users_contract:dual_write_must_follow_target_db")

    if any(_call_name(node) == "_current_internal_user" for node in post_calls):
        issues.append("admin_users_contract:current_internal_user_forbidden")
    if any(_session_accesses_role(node) for node in post_nodes):
        issues.append("admin_users_contract:direct_session_role_forbidden")
    if any(_session_accesses_user_id(node) for node in post_nodes):
        issues.append("admin_users_contract:direct_session_user_id_forbidden")

    request_form_stmt_indices = [index for index, stmt in enumerate(post_block) if _stmt_contains_request_form(stmt)]
    db_stmt_indices = [index for index, stmt in enumerate(post_block) if _stmt_contains_db_with(stmt)]
    mutation_stmt_indices = [index for index, stmt in enumerate(post_block) if _stmt_contains_mutation_capable_operation(stmt)]
    dual_write_stmt_indices = [index for index, stmt in enumerate(post_block) if _stmt_contains_dual_write(stmt)]

    first_form_stmt_index = min(request_form_stmt_indices, default=None)
    first_db_stmt_index = min(db_stmt_indices, default=None)
    first_mutation_stmt_index = min(mutation_stmt_indices, default=None)
    first_dual_write_stmt_index = min(dual_write_stmt_indices, default=None)

    if resolver_stmt_index is not None and role_stmt_index is not None:
        if not resolver_stmt_index < role_stmt_index:
            issues.append("admin_users_contract:canonical_guard_dominance")
        if first_form_stmt_index is not None and not role_stmt_index < first_form_stmt_index:
            issues.append("admin_users_contract:canonical_guard_dominance")
        if first_db_stmt_index is not None and not role_stmt_index < first_db_stmt_index:
            issues.append("admin_users_contract:mutation_before_canonical_guard")
        if first_mutation_stmt_index is not None and not role_stmt_index < first_mutation_stmt_index:
            issues.append("admin_users_contract:mutation_before_canonical_guard")
        if first_dual_write_stmt_index is not None and not role_stmt_index < first_dual_write_stmt_index:
            issues.append("admin_users_contract:mutation_before_canonical_guard")

    if resolver_stmt_index is not None and role_stmt_index is not None:
        for index, stmt in enumerate(post_block):
            if index > role_stmt_index:
                break
            if index in {resolver_stmt_index, role_stmt_index}:
                continue
            if _stmt_contains_request_form(stmt) or _stmt_contains_db_with(stmt) or _stmt_contains_mutation_capable_operation(stmt):
                issues.append("admin_users_contract:mutation_before_canonical_guard")
                break

    if issues:
        seen: set[str] = set()
        deduped = []
        for issue in issues:
            if issue in seen:
                continue
            seen.add(issue)
            deduped.append(issue)
        issues[:] = deduped


def run_admin_users_contract_self_test() -> int:
    valid_source = '''
from flask import request

def users():
    if request.method == "POST":
        try:
            actor = resolve_canonical_internal_mutation_actor()
        except LookupError:
            return _redirect_admin_users_auth_required()
        if str(actor.get("role") or "").strip() != "admin":
            return _redirect_admin_users_admin_required()
        action = request.form.get("action", "create_user")
        if action == "create_user":
            with db() as conn:
                create_user_sqlite(conn, username="x", display_name="x", password_hash="h", role="member")
            maybe_dual_write_user_create({"id": 1})
        elif action.startswith("update_user:"):
            with db() as conn:
                update_user_role_sqlite(conn, 2, role="member")
            maybe_dual_write_user_role_update(2, role="member")
        elif action.startswith("delete_user:"):
            with db() as conn:
                delete_user_sqlite(conn, 2)
            maybe_dual_write_user_delete({"id": 2})
'''
    valid_issues: list[str] = []
    validate_admin_users_route_contract(valid_source, valid_issues)
    if valid_issues:
        raise SystemExit(f"FAIL admin-users checker rejected valid fixture: {valid_issues}")

    negative_fixtures = (
        (
            "unknown_call_between_guards",
            valid_source.replace(
                "        if str(actor.get(\"role\") or \"\").strip() != \"admin\":",
                "        dangerous_write()\n"
                "        if str(actor.get(\"role\") or \"\").strip() != \"admin\":",
            ),
            "admin_users_contract:canonical_guard_safe_prefix",
        ),
        (
            "unknown_call_before_resolver",
            valid_source.replace(
                "        try:\n            actor = resolve_canonical_internal_mutation_actor()",
                "        dangerous_write()\n"
                "        try:\n            actor = resolve_canonical_internal_mutation_actor()",
            ),
            "admin_users_contract:canonical_guard_safe_prefix",
        ),
        (
            "unknown_call_inside_resolver_try",
            valid_source.replace(
                "            actor = resolve_canonical_internal_mutation_actor()",
                "            actor = resolve_canonical_internal_mutation_actor()\n"
                "            dangerous_write()",
                1,
            ),
            "admin_users_contract:canonical_guard_safe_prefix",
        ),
        (
            "unknown_call_inside_lookup_handler",
            valid_source.replace(
                "        except LookupError:\n"
                "            return _redirect_admin_users_auth_required()",
                "        except LookupError:\n"
                "            dangerous_write()\n"
                "            return _redirect_admin_users_auth_required()",
            ),
            "admin_users_contract:canonical_guard_safe_prefix",
        ),
        (
            "helper_assignment_between_guards",
            valid_source.replace(
                "        if str(actor.get(\"role\") or \"\").strip() != \"admin\":",
                "        value = unknown_helper()\n"
                "        if str(actor.get(\"role\") or \"\").strip() != \"admin\":",
            ),
            "admin_users_contract:canonical_guard_safe_prefix",
        ),
        (
            "role_guard_nested_in_branch",
            valid_source.replace(
                "        if str(actor.get(\"role\") or \"\").strip() != \"admin\":\n"
                "            return _redirect_admin_users_admin_required()",
                "        if allow_guard:\n"
                "            if str(actor.get(\"role\") or \"\").strip() != \"admin\":\n"
                "                return _redirect_admin_users_admin_required()",
            ),
            "admin_users_contract:canonical_guard_safe_prefix",
        ),
        (
            "resolver_try_with_else",
            valid_source.replace(
                "        except LookupError:\n"
                "            return _redirect_admin_users_auth_required()",
                "        except LookupError:\n"
                "            return _redirect_admin_users_auth_required()\n"
                "        else:\n"
                "            pass",
            ),
            "admin_users_contract:canonical_guard_safe_prefix",
        ),
        (
            "resolver_try_with_finally",
            valid_source.replace(
                "        except LookupError:\n"
                "            return _redirect_admin_users_auth_required()",
                "        except LookupError:\n"
                "            return _redirect_admin_users_auth_required()\n"
                "        finally:\n"
                "            pass",
            ),
            "admin_users_contract:canonical_guard_safe_prefix",
        ),
        (
            "broad_exception_instead_of_lookup_error",
            valid_source.replace("except LookupError:", "except Exception:", 1),
            "admin_users_contract:canonical_guard_safe_prefix",
        ),
        (
            "additional_broad_exception_handler",
            valid_source.replace(
                "        except LookupError:\n"
                "            return _redirect_admin_users_auth_required()",
                "        except LookupError:\n"
                "            return _redirect_admin_users_auth_required()\n"
                "        except Exception:\n"
                "            pass",
            ),
            "admin_users_contract:canonical_guard_safe_prefix",
        ),
        (
            "missing_resolver",
            '''
from flask import request
def users():
    if request.method == "POST":
        action = request.form.get("action", "create_user")
        if action == "create_user":
            with db() as conn:
                create_user_sqlite(conn, username="x", display_name="x", password_hash="h", role="member")
            maybe_dual_write_user_create({"id": 1})
''',
            "admin_users_contract:canonical_resolver_call_count",
        ),
        (
            "resolver_after_request_form",
            '''
from flask import request
def users():
    if request.method == "POST":
        action = request.form.get("action", "create_user")
        actor = resolve_canonical_internal_mutation_actor()
        if str(actor.get("role") or "").strip() != "admin":
            return _redirect_admin_users_admin_required()
        if action == "create_user":
            with db() as conn:
                create_user_sqlite(conn, username="x", display_name="x", password_hash="h", role="member")
            maybe_dual_write_user_create({"id": 1})
''',
            "admin_users_contract:resolver_must_precede_request_form",
        ),
        (
            "resolver_after_target_db",
            '''
from flask import request
def users():
    if request.method == "POST":
        action = request.form.get("action", "create_user")
        with db() as conn:
            actor = resolve_canonical_internal_mutation_actor()
            create_user_sqlite(conn, username="x", display_name="x", password_hash="h", role="member")
        maybe_dual_write_user_create({"id": 1})
''',
            "admin_users_contract:resolver_must_precede_target_db",
        ),
        (
            "resolver_not_used_for_role_gate",
            valid_source.replace('actor.get("role")', 'session.get("role")'),
            "admin_users_contract:actor_role_gate_missing",
        ),
        (
            "session_role_final_authority",
            valid_source.replace('actor.get("role")', 'session.get("role")').replace(
                '        if str(actor.get("role") or "").strip() != "admin":\n            return _redirect_admin_users_admin_required()\n',
                '        if session.get("role") != "admin":\n            return _redirect_admin_users_admin_required()\n',
            ),
            "admin_users_contract:direct_session_role_forbidden",
        ),
        (
            "current_user_fallback",
            valid_source.replace(
                '        action = request.form.get("action", "create_user")',
                '        fallback = _current_internal_user()\n        action = request.form.get("action", "create_user")',
            ),
            "admin_users_contract:current_internal_user_forbidden",
        ),
        (
            "duplicate_resolver",
            '''
from flask import request
def users():
    if request.method == "POST":
        try:
            actor = resolve_canonical_internal_mutation_actor()
        except LookupError:
            return _redirect_admin_users_auth_required()
        actor = resolve_canonical_internal_mutation_actor()
        if str(actor.get("role") or "").strip() != "admin":
            return _redirect_admin_users_admin_required()
        action = request.form.get("action", "create_user")
        if action == "create_user":
            with db() as conn:
                create_user_sqlite(conn, username="x", display_name="x", password_hash="h", role="member")
            maybe_dual_write_user_create({"id": 1})
''',
            "admin_users_contract:canonical_resolver_call_count",
        ),
        (
            "ineffective_role_guard",
            '''
from flask import request
def users():
    if request.method == "POST":
        try:
            actor = resolve_canonical_internal_mutation_actor()
        except LookupError:
            return _redirect_admin_users_auth_required()
        if str(actor.get("role") or "").strip() != "admin":
            pass
        if False:
            return _redirect_admin_users_admin_required()
        action = request.form.get("action", "create_user")
        if action == "create_user":
            with db() as conn:
                create_user_sqlite(conn, username="x", display_name="x", password_hash="h", role="member")
            maybe_dual_write_user_create({"id": 1})
        elif action.startswith("update_user:"):
            with db() as conn:
                update_user_role_sqlite(conn, 2, role="member")
            maybe_dual_write_user_role_update(2, role="member")
        elif action.startswith("delete_user:"):
            with db() as conn:
                delete_user_sqlite(conn, 2)
            maybe_dual_write_user_delete({"id": 2})
''',
            "admin_users_contract:canonical_role_guard_enforcement",
        ),
        (
            "helper_called_not_returned",
            '''
from flask import request
def users():
    if request.method == "POST":
        try:
            actor = resolve_canonical_internal_mutation_actor()
        except LookupError:
            return _redirect_admin_users_auth_required()
        if str(actor.get("role") or "").strip() != "admin":
            _redirect_admin_users_admin_required()
        action = request.form.get("action", "create_user")
        if action == "create_user":
            with db() as conn:
                create_user_sqlite(conn, username="x", display_name="x", password_hash="h", role="member")
            maybe_dual_write_user_create({"id": 1})
        elif action.startswith("update_user:"):
            with db() as conn:
                update_user_role_sqlite(conn, 2, role="member")
            maybe_dual_write_user_role_update(2, role="member")
        elif action.startswith("delete_user:"):
            with db() as conn:
                delete_user_sqlite(conn, 2)
            maybe_dual_write_user_delete({"id": 2})
''',
            "admin_users_contract:canonical_role_guard_enforcement",
        ),
        (
            "wrong_role_redirect_helper",
            '''
from flask import request
def users():
    if request.method == "POST":
        try:
            actor = resolve_canonical_internal_mutation_actor()
        except LookupError:
            return _redirect_admin_users_auth_required()
        if str(actor.get("role") or "").strip() != "admin":
            return _redirect_admin_users_auth_required()
        action = request.form.get("action", "create_user")
        if action == "create_user":
            with db() as conn:
                create_user_sqlite(conn, username="x", display_name="x", password_hash="h", role="member")
            maybe_dual_write_user_create({"id": 1})
        elif action.startswith("update_user:"):
            with db() as conn:
                update_user_role_sqlite(conn, 2, role="member")
            maybe_dual_write_user_role_update(2, role="member")
        elif action.startswith("delete_user:"):
            with db() as conn:
                delete_user_sqlite(conn, 2)
            maybe_dual_write_user_delete({"id": 2})
''',
            "admin_users_contract:canonical_role_guard_enforcement",
        ),
        (
            "nested_non_dominating_role_guard",
            '''
from flask import request
def users():
    if request.method == "POST":
        try:
            actor = resolve_canonical_internal_mutation_actor()
        except LookupError:
            return _redirect_admin_users_auth_required()
        action = request.form.get("action", "create_user")
        if action == "create_user":
            if str(actor.get("role") or "").strip() != "admin":
                return _redirect_admin_users_admin_required()
            with db() as conn:
                create_user_sqlite(conn, username="x", display_name="x", password_hash="h", role="member")
            maybe_dual_write_user_create({"id": 1})
        elif action.startswith("update_user:"):
            with db() as conn:
                update_user_role_sqlite(conn, 2, role="member")
            maybe_dual_write_user_role_update(2, role="member")
        elif action.startswith("delete_user:"):
            with db() as conn:
                delete_user_sqlite(conn, 2)
            maybe_dual_write_user_delete({"id": 2})
''',
            "admin_users_contract:canonical_role_guard_enforcement",
        ),
        (
            "mutation_before_role_guard",
            '''
from flask import request
def users():
    if request.method == "POST":
        try:
            actor = resolve_canonical_internal_mutation_actor()
        except LookupError:
            return _redirect_admin_users_auth_required()
        action = request.form.get("action", "create_user")
        if action == "create_user":
            with db() as conn:
                create_user_sqlite(conn, username="x", display_name="x", password_hash="h", role="member")
            maybe_dual_write_user_create({"id": 1})
        if str(actor.get("role") or "").strip() != "admin":
            return _redirect_admin_users_admin_required()
        elif action.startswith("update_user:"):
            with db() as conn:
                update_user_role_sqlite(conn, 2, role="member")
            maybe_dual_write_user_role_update(2, role="member")
        elif action.startswith("delete_user:"):
            with db() as conn:
                delete_user_sqlite(conn, 2)
            maybe_dual_write_user_delete({"id": 2})
''',
            "admin_users_contract:mutation_before_canonical_guard",
        ),
        (
            "ineffective_invalid_actor_guard",
            '''
from flask import request
def users():
    if request.method == "POST":
        try:
            actor = resolve_canonical_internal_mutation_actor()
        except LookupError:
            pass
        if False:
            return _redirect_admin_users_auth_required()
        if str(actor.get("role") or "").strip() != "admin":
            return _redirect_admin_users_admin_required()
        action = request.form.get("action", "create_user")
        if action == "create_user":
            with db() as conn:
                create_user_sqlite(conn, username="x", display_name="x", password_hash="h", role="member")
            maybe_dual_write_user_create({"id": 1})
        elif action.startswith("update_user:"):
            with db() as conn:
                update_user_role_sqlite(conn, 2, role="member")
            maybe_dual_write_user_role_update(2, role="member")
        elif action.startswith("delete_user:"):
            with db() as conn:
                delete_user_sqlite(conn, 2)
            maybe_dual_write_user_delete({"id": 2})
''',
            "admin_users_contract:invalid_actor_guard_enforcement",
        ),
        (
            "comment_only_marker",
            '''
from flask import request
def users():
    if request.method == "POST":
        # actor = resolve_canonical_internal_mutation_actor()
        "actor = resolve_canonical_internal_mutation_actor()"
        action = request.form.get("action", "create_user")
        return action
''',
            "admin_users_contract:canonical_resolver_call_count",
        ),
        (
            "missing_route",
            valid_source.replace("def users():", "def not_users():"),
            "admin_users_contract:route_definition_count",
        ),
        (
            "duplicate_route",
            valid_source + "\n\ndef users():\n    return None\n",
            "admin_users_contract:route_definition_count",
        ),
        (
            "syntax_error",
            "def users(:\n    pass\n",
            "admin_users_contract:source_syntax_error",
        ),
    )
    for label, fixture, expected_issue in negative_fixtures:
        fixture_issues: list[str] = []
        validate_admin_users_route_contract(fixture, fixture_issues)
        if expected_issue not in fixture_issues:
            raise SystemExit(
                f"FAIL admin-users checker negative fixture {label} missed {expected_issue}: {fixture_issues}"
            )

    print("PASS admin users readiness checker negative controls passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check admin write model readiness inventory.")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run in-memory admin-users AST negative controls.",
    )
    args = parser.parse_args()

    if args.self_test:
        return run_admin_users_contract_self_test()

    print("admin_write_model_readiness_scope: admin_site_content_enforced_save_internal_split_reset_sheet_enforced")
    print(f"app_source: {APP_PATH}")
    print("WARNING P-3C-3B keeps action == save but splits internal save paths into global settings and current-site-enforced site content")
    print("WARNING final explicit action split remains deferred")
    print("WARNING /api/reset-sheet is now current-site enforced while preserving the existing success response contract")
    print("WARNING production behavior changed for save internals and admin destructive reset-sheet authorization")

    source = APP_PATH.read_text(encoding="utf-8")
    issues: list[str] = []

    expect(APP_PATH.exists(), "app.py_missing", issues)
    expect(len(ADMIN_TABLE_ITEMS) == 12, "admin_table_inventory_count_mismatch", issues)
    expect(any(item.action == "create_sheet" for item in ADMIN_TABLE_ITEMS), "create_sheet_missing", issues)
    expect(any(item.action == "save" and item.category == "MIXED" for item in ADMIN_TABLE_ITEMS), "save_mixed_missing", issues)
    expect(any(item.action == "reset_sheet" and item.status == "ENFORCED" for item in ADMIN_TABLE_ITEMS), "reset_sheet_enforced_missing", issues)

    print(f"inventory_total: {len(ADMIN_TABLE_ITEMS)}")
    print("global_only_reference_tables: meta")
    print("site_scoped_reference_tables: sheets, tasks, floors, units, progress, unit_extra, unit_extra_values, extra_fields, vendor_contacts, vendor_work_entries")

    for item in ADMIN_TABLE_ITEMS:
        missing_markers = [marker for marker in item.source_markers if marker not in source]
        expect(not missing_markers, f"missing_source_marker:{item.action}", issues)
        render_item(item)

    validate_admin_users_route_contract(source, issues)

    print("---")
    print("future_candidates:")
    print("- final explicit action split for save remains deferred")
    print("reset_sheet_status: ENFORCED")
    print("reset_sheet_destructive_candidate: resolved")
    expect('@app.route("/api/reset-sheet", methods=["POST"])' in source, "reset_sheet_route_missing", issues)

    print(f"issues_count: {len(issues)}")
    if issues:
        for issue in issues:
            print(f"ISSUE {issue}")
        raise SystemExit("FAIL admin write model readiness check failed.")

    print("PASS admin write model readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
