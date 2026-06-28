from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


TARGET_RULES = {
    "/login": "users login",
    "/admin/users": "users admin list/manage",
    "/api/reset-sheet": "users password verification before reset",
}
HELPER_NAMES = ("get_user_by_username", "get_user_by_id", "list_users", "reset_sheet")
ACTIVE_INLINE_EXPECTATIONS = {
    "login": "get_user_by_username",
    "api_reset_sheet": "get_user_by_id",
    "users": "list_users",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect active and legacy users read paths without modifying runtime behavior."
    )
    return parser.parse_args()


def load_app_module():
    return importlib.import_module("app")


def _route_strings_from_decorator(decorator: ast.expr) -> list[str]:
    if not isinstance(decorator, ast.Call):
        return []
    if not isinstance(decorator.func, ast.Attribute):
        return []
    if decorator.func.attr != "route":
        return []

    routes: list[str] = []
    if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
        routes.append(decorator.args[0].value)
    return routes


def collect_declared_routes(path: Path) -> list[dict[str, object]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    declared: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            for route in _route_strings_from_decorator(decorator):
                declared.append(
                    {
                        "route": route,
                        "function": node.name,
                        "line": node.lineno,
                        "file": str(path),
                    }
                )
    return declared


def collect_users_sql_calls(path: Path) -> list[dict[str, object]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    results: list[dict[str, object]] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.function_stack: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.function_stack.append(node.name)
            self.generic_visit(node)
            self.function_stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.function_stack.append(node.name)
            self.generic_visit(node)
            self.function_stack.pop()

        def visit_Constant(self, node: ast.Constant) -> None:
            if isinstance(node.value, str):
                normalized = " ".join(node.value.lower().split())
                if " from users" in normalized or normalized.startswith("select * from users") or normalized.startswith(
                    "select id, username"
                ):
                    results.append(
                        {
                            "file": str(path),
                            "line": node.lineno,
                            "function": self.function_stack[-1] if self.function_stack else "<module>",
                            "sql": " ".join(node.value.strip().split()),
                        }
                    )
            self.generic_visit(node)

    Visitor().visit(tree)
    return results


def collect_function_reads(path: Path) -> dict[str, dict[str, object]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    summary: dict[str, dict[str, object]] = {}

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.function_name: str | None = None

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            previous = self.function_name
            self.function_name = node.name
            summary.setdefault(node.name, {"calls": set(), "users_sql": []})
            self.generic_visit(node)
            self.function_name = previous

        def visit_Call(self, node: ast.Call) -> None:
            if self.function_name is not None:
                callee_name: str | None = None
                if isinstance(node.func, ast.Name):
                    callee_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    callee_name = node.func.attr
                if callee_name:
                    summary[self.function_name]["calls"].add(callee_name)
            self.generic_visit(node)

        def visit_Constant(self, node: ast.Constant) -> None:
            if self.function_name is not None and isinstance(node.value, str):
                normalized = " ".join(node.value.lower().split())
                if " from users" in normalized and "select " in normalized:
                    summary[self.function_name]["users_sql"].append(" ".join(node.value.strip().split()))
            self.generic_visit(node)

    Visitor().visit(tree)
    return summary


def describe_view_function(view) -> str:
    try:
        source_file = Path(inspect.getsourcefile(view) or "<unknown>")
        _, first_line = inspect.getsourcelines(view)
        return f"{source_file}:{first_line}"
    except (OSError, TypeError):
        return "<unknown>"


def helper_origin(app_module, name: str) -> str:
    value = getattr(app_module, name, None)
    if value is None:
        return "missing_on_app_module"
    try:
        source_file = Path(inspect.getsourcefile(value) or "<unknown>")
        _, first_line = inspect.getsourcelines(value)
        return f"{source_file}:{first_line}"
    except (OSError, TypeError):
        return "<unknown>"


def main() -> int:
    parse_args()
    app_module = load_app_module()
    flask_app = app_module.app

    app_declared = collect_declared_routes(BASE_DIR / "app.py")
    auth_declared = collect_declared_routes(BASE_DIR / "routes" / "auth.py")
    admin_declared = collect_declared_routes(BASE_DIR / "routes" / "admin.py")
    api_declared = collect_declared_routes(BASE_DIR / "routes" / "api.py")
    app_function_reads = collect_function_reads(BASE_DIR / "app.py")

    active_by_rule: dict[str, list[dict[str, object]]] = {}
    for rule in flask_app.url_map.iter_rules():
        active_by_rule.setdefault(rule.rule, []).append(
            {
                "endpoint": rule.endpoint,
                "methods": sorted(method for method in rule.methods if method not in {"HEAD", "OPTIONS"}),
                "view_source": describe_view_function(flask_app.view_functions[rule.endpoint]),
            }
        )

    ambiguities: list[str] = []

    print("Users read route inventory:")
    for rule, label in TARGET_RULES.items():
        print(f"- route: {rule} ({label})")
        active_entries = active_by_rule.get(rule, [])
        if active_entries:
            for entry in active_entries:
                print(
                    "  active_endpoint="
                    f"{entry['endpoint']} methods={entry['methods']} view_source={entry['view_source']}"
                )
        else:
            print("  active_endpoint=missing")

        declared_entries = [
            entry for entry in (*app_declared, *auth_declared, *admin_declared, *api_declared) if entry["route"] == rule
        ]
        for entry in declared_entries:
            print(
                "  declared_route="
                f"{entry['function']} source={entry['file']}:{entry['line']}"
            )

        if len(active_entries) > 1:
            ambiguities.append(f"multiple_active_endpoints_for_{rule}")

    print("Users read helper inventory:")
    for helper_name in HELPER_NAMES:
        origin = helper_origin(app_module, helper_name)
        print(f"- {helper_name}: {origin}")
        if helper_name != "reset_sheet" and origin == "missing_on_app_module":
            ambiguities.append(f"missing_helper_{helper_name}")

    print("Cross-module helper usage:")
    print("- routes.auth.login uses: app.get_user_by_username")
    print(f"  resolved_origin={helper_origin(app_module, 'get_user_by_username')}")
    print("- routes.admin.users GET uses: app.list_users")
    print(f"  resolved_origin={helper_origin(app_module, 'list_users')}")
    print("- services.progress_service.reset_sheet uses: app.get_user_by_id")
    print(f"  resolved_origin={helper_origin(app_module, 'get_user_by_id')}")

    print("Direct SQLite users SELECT call sites:")
    sql_calls = []
    for relative_path in ("app.py", "routes/auth.py", "routes/admin.py", "routes/api.py", "services/progress_service.py"):
        sql_calls.extend(collect_users_sql_calls(BASE_DIR / relative_path))
    if not sql_calls:
        print("- none")
    else:
        for call in sql_calls:
            print(
                f"- {call['file']}:{call['line']} function={call['function']} sql={call['sql']}"
            )

    print("Runtime active path assessment:")
    login_active = active_by_rule.get("/login", [])
    admin_users_active = active_by_rule.get("/admin/users", [])
    reset_active = active_by_rule.get("/api/reset-sheet", [])
    print(
        f"- /login active via: {login_active[0]['endpoint'] if len(login_active) == 1 else 'ambiguous_or_missing'}"
    )
    print(
        f"- /admin/users active via: {admin_users_active[0]['endpoint'] if len(admin_users_active) == 1 else 'ambiguous_or_missing'}"
    )
    print(
        f"- /api/reset-sheet active via: {reset_active[0]['endpoint'] if len(reset_active) == 1 else 'ambiguous_or_missing'}"
    )

    print("Active inline helper usage:")
    for function_name, helper_name in ACTIVE_INLINE_EXPECTATIONS.items():
        function_read = app_function_reads.get(function_name, {"calls": set(), "users_sql": []})
        helper_used = helper_name in function_read["calls"]
        direct_users_select = bool(function_read["users_sql"])
        print(
            f"- {function_name}: helper={helper_name} helper_used={str(helper_used).lower()} "
            f"direct_users_select={str(direct_users_select).lower()}"
        )
        if not helper_used:
            ambiguities.append(f"{function_name}_missing_helper_{helper_name}")
        if direct_users_select:
            ambiguities.append(f"{function_name}_still_contains_direct_users_select")

    print("Legacy/dead path candidates:")
    print("- routes/auth.py login blueprint candidate is not active unless auth_bp is registered.")
    print("- routes/admin.py /admin/users blueprint candidate is not active unless admin_bp is registered.")
    print("- routes/api.py /api/reset-sheet blueprint candidate is not active unless api_bp is registered.")
    print("- Any blueprint path depending on app.get_user_by_username/get_user_by_id/list_users was previously unsafe while helpers were missing.")

    if ambiguities:
        print(f"FAIL users read inventory found ambiguous active users routes: {', '.join(ambiguities)}")
        return 1

    print("PASS users read inventory completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
