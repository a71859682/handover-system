from __future__ import annotations

import argparse
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
        status="DEFERRED",
        uses_current_site="no",
        current_site_enforced="no",
        can_cross_site_today="yes",
        recommendation="Split mixed save into global meta save and site-scoped content save before admin write isolation enforcement.",
        risk="high",
        notes=("save is mixed: meta + site content",),
        source_markers=(
            'action = actions[-1] if actions else "save"',
            'UPDATE sheets SET name = ? WHERE id = ?',
            "for key in DEFAULT_SETTINGS:",
            "set_setting(conn, key, request.form.get(key, \"\").strip())",
        ),
    ),
    AdminWriteItem(
        action="add_task",
        target_tables=("tasks", "progress"),
        category="SITE_SCOPED",
        status="INVENTORY ONLY",
        uses_current_site="no",
        current_site_enforced="no",
        can_cross_site_today="yes",
        recommendation="Future admin current-site aware site-content action.",
        risk="medium",
        notes=(),
        source_markers=('if action == "add_task":', 'INSERT INTO tasks (sheet_id, col_index, vendor, location, name) VALUES (?, ?, ?, ?, ?)'),
    ),
    AdminWriteItem(
        action="delete_task",
        target_tables=("tasks", "progress"),
        category="SITE_SCOPED",
        status="INVENTORY ONLY",
        uses_current_site="no",
        current_site_enforced="no",
        can_cross_site_today="yes",
        recommendation="Future admin current-site aware site-content action.",
        risk="medium",
        notes=(),
        source_markers=('if action.startswith("delete_task:"):', 'DELETE FROM tasks WHERE id = ? AND sheet_id = ?'),
    ),
    AdminWriteItem(
        action="add_extra_field",
        target_tables=("extra_fields",),
        category="SITE_SCOPED",
        status="INVENTORY ONLY",
        uses_current_site="no",
        current_site_enforced="no",
        can_cross_site_today="yes",
        recommendation="Future admin current-site aware site-content action.",
        risk="medium",
        notes=(),
        source_markers=('if action == "add_extra_field":', "INSERT INTO extra_fields"),
    ),
    AdminWriteItem(
        action="delete_extra_field",
        target_tables=("extra_fields",),
        category="SITE_SCOPED",
        status="INVENTORY ONLY",
        uses_current_site="no",
        current_site_enforced="no",
        can_cross_site_today="yes",
        recommendation="Future admin current-site aware site-content action.",
        risk="medium",
        notes=(),
        source_markers=('if action.startswith("delete_extra_field:"):', "UPDATE extra_fields SET active = 0 WHERE id = ? AND sheet_id = ?"),
    ),
    AdminWriteItem(
        action="add_floor",
        target_tables=("floors",),
        category="SITE_SCOPED",
        status="INVENTORY ONLY",
        uses_current_site="no",
        current_site_enforced="no",
        can_cross_site_today="yes",
        recommendation="Future admin current-site aware site-content action.",
        risk="medium",
        notes=(),
        source_markers=('if action == "add_floor":', 'INSERT INTO floors (sheet_id, sort_order, name, block_name, unit_count) VALUES (?, ?, ?, ?, 0)'),
    ),
    AdminWriteItem(
        action="delete_floor",
        target_tables=("floors", "units", "progress", "unit_extra", "unit_extra_values"),
        category="SITE_SCOPED",
        status="INVENTORY ONLY",
        uses_current_site="no",
        current_site_enforced="no",
        can_cross_site_today="yes",
        recommendation="Treat as future admin current-site aware destructive action; do not enforce in P-3C-1.",
        risk="high",
        notes=(),
        source_markers=('if action.startswith("delete_floor:"):', 'DELETE FROM floors WHERE id = ? AND sheet_id = ?'),
    ),
    AdminWriteItem(
        action="add_unit",
        target_tables=("units", "progress", "unit_extra"),
        category="SITE_SCOPED",
        status="INVENTORY ONLY",
        uses_current_site="no",
        current_site_enforced="no",
        can_cross_site_today="yes",
        recommendation="Future admin current-site aware site-content action.",
        risk="medium",
        notes=(),
        source_markers=('if action.startswith("add_unit:"):', 'INSERT INTO units (floor_id, sort_order, name) VALUES (?, ?, ?)'),
    ),
    AdminWriteItem(
        action="delete_unit",
        target_tables=("units", "progress", "unit_extra", "unit_extra_values"),
        category="SITE_SCOPED",
        status="INVENTORY ONLY",
        uses_current_site="no",
        current_site_enforced="no",
        can_cross_site_today="yes",
        recommendation="Treat as future admin current-site aware destructive action; do not enforce in P-3C-1.",
        risk="high",
        notes=(),
        source_markers=('if action.startswith("delete_unit:"):', 'DELETE FROM units WHERE id = ?'),
    ),
)


FUTURE_CANDIDATES: tuple[str, ...] = (
    "/api/reset-sheet is admin site-scoped destructive write candidate for later stage",
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Check admin write model readiness inventory.")
    parser.parse_args()

    print("admin_write_model_readiness_scope: create_delete_sheet_enforced")
    print(f"app_source: {APP_PATH}")
    print("WARNING P-3C-2A enforces current-site aware behavior for create_sheet and delete_sheet only")
    print("WARNING admin current-site aware behavior is partially implemented for create_sheet and delete_sheet only")
    print("WARNING mixed save split is deferred")
    print("WARNING production behavior changed only for create_sheet and delete_sheet")

    source = APP_PATH.read_text(encoding="utf-8")
    issues: list[str] = []

    expect(APP_PATH.exists(), "app.py_missing", issues)
    expect(len(ADMIN_TABLE_ITEMS) == 11, "admin_table_inventory_count_mismatch", issues)
    expect(any(item.action == "create_sheet" for item in ADMIN_TABLE_ITEMS), "create_sheet_missing", issues)
    expect(any(item.action == "save" and item.category == "MIXED" for item in ADMIN_TABLE_ITEMS), "save_mixed_missing", issues)

    print(f"inventory_total: {len(ADMIN_TABLE_ITEMS)}")
    print("global_only_reference_tables: meta")
    print("site_scoped_reference_tables: sheets, tasks, floors, units, progress, unit_extra, unit_extra_values, extra_fields, vendor_contacts, vendor_work_entries")

    for item in ADMIN_TABLE_ITEMS:
        missing_markers = [marker for marker in item.source_markers if marker not in source]
        expect(not missing_markers, f"missing_source_marker:{item.action}", issues)
        render_item(item)

    print("---")
    print("future_candidates:")
    for candidate in FUTURE_CANDIDATES:
        print(f"- {candidate}")
    print("reset_sheet_status: DEFERRED")
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
