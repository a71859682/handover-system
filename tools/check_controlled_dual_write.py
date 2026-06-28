from __future__ import annotations

import argparse
import ast
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
APP_PATH = ROOT_DIR / "app.py"


REQUIRED_FUNCTIONS = {
    "update_floor_fields_sqlite",
    "update_floor_fields_postgres",
    "maybe_dual_write_floor_update",
    "update_user_display_name_sqlite",
    "update_user_display_name_postgres",
    "maybe_dual_write_user_display_name_update",
    "update_user_role_sqlite",
    "update_user_role_postgres",
    "maybe_dual_write_user_role_update",
    "controlled_dual_write_enabled",
}
REQUIRED_LOG_SNIPPETS = [
    "DUAL_WRITE_DRY_RUN operation=update table=floors",
    "DUAL_WRITE_FLOORS_SECONDARY table=floors strategy=reuse_primary_postgres_connection",
    "event=SAVEPOINT_START",
    "event=SAVEPOINT_OK",
    "event=EXECUTE_SQL_START",
    "event=EXECUTE_SQL_OK",
    "event=RELEASE_SAVEPOINT_OK",
    "DUAL_WRITE operation=update table=floors",
    "DUAL_WRITE_DRY_RUN operation=update table=users",
    "DUAL_WRITE_USERS_SECONDARY table=users strategy=reuse_primary_postgres_connection",
    "DUAL_WRITE operation=update table=users",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the controlled dual-write wiring for floors/users update-only."
    )
    return parser.parse_args()


def assert_required_functions(source: str) -> None:
    module = ast.parse(source, filename=str(APP_PATH))
    function_names = {node.name for node in module.body if isinstance(node, ast.FunctionDef)}
    missing = sorted(REQUIRED_FUNCTIONS - function_names)
    if missing:
        raise AssertionError(f"Missing required app.py functions: {', '.join(missing)}")


def assert_required_logs(source: str) -> None:
    missing = [snippet for snippet in REQUIRED_LOG_SNIPPETS if snippet not in source]
    if missing:
        raise AssertionError(f"Missing required dual-write log snippets: {missing}")


def assert_route_wiring(source: str) -> None:
    floors_loop = 'for floor in conn.execute("SELECT id FROM floors WHERE sheet_id = ?", (sheet_id,)):'
    units_loop = 'for unit in conn.execute("SELECT u.id FROM units u JOIN floors f ON f.id = u.floor_id WHERE f.sheet_id = ?", (sheet_id,)):'
    sqlite_call = "update_floor_fields_sqlite(conn, floor_id, name=floor_name, block_name=floor_block_name)"
    dual_write_call = "maybe_dual_write_floor_update(floor_id, name=floor_name, block_name=floor_block_name)"

    for snippet in (floors_loop, units_loop, sqlite_call, dual_write_call):
        if snippet not in source:
            raise AssertionError(f"Missing required route snippet: {snippet}")

    floors_loop_index = source.index(floors_loop)
    route_tail = source[floors_loop_index:]
    sqlite_call_index = route_tail.index(sqlite_call)
    dual_write_call_index = route_tail.index(dual_write_call)
    units_loop_index = route_tail.index(units_loop)

    if not (sqlite_call_index < dual_write_call_index < units_loop_index):
        raise AssertionError("floors dual-write is not scoped correctly ahead of the units loop.")

    self_role_block = 'flash("\\u672c\\u968e\\u6bb5\\u4e0d\\u5141\\u8a31\\u4fee\\u6539\\u81ea\\u5df1\\u7684\\u89d2\\u8272", "error")'
    sqlite_role_call = "update_user_role_sqlite(conn, user_id, role=role)"
    dual_write_role_call = "maybe_dual_write_user_role_update(user_id, role=role)"

    for snippet in (
        'elif action.startswith("update_user:"):',
        self_role_block,
        sqlite_role_call,
        dual_write_role_call,
    ):
        if snippet not in source:
            raise AssertionError(f"Missing required route snippet: {snippet}")

    user_route_index = source.index('elif action.startswith("update_user:"):')
    user_route_tail = source[user_route_index:]
    self_role_block_index = user_route_tail.index(self_role_block)
    sqlite_role_index = user_route_tail.index(sqlite_role_call)
    dual_write_role_index = user_route_tail.index(dual_write_role_call)

    if not (self_role_block_index < sqlite_role_index < dual_write_role_index):
        raise AssertionError("users role dual-write/update-only wiring is not ordered correctly.")


def main() -> int:
    parse_args()
    source = APP_PATH.read_text(encoding="utf-8")

    assert_required_functions(source)
    assert_required_logs(source)
    assert_route_wiring(source)

    print("PASS controlled dual-write floors/users update-only wiring looks correct.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
