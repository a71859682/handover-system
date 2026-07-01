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


def main() -> int:
    parser = argparse.ArgumentParser(description="Check admin write model readiness inventory.")
    parser.parse_args()

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
