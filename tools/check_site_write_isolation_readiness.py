from __future__ import annotations

import argparse
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
        status="INVENTORY ONLY",
        risk="high",
        site_scoped="yes",
        current_site_enforced="no",
        ownership_validation_required="yes",
        recommendation="Add current_site + site permission + target ownership enforcement in a future write isolation stage.",
        source_markers=('@app.route("/api/unit-extra", methods=["POST"])',),
    ),
    InventoryItem(
        route="/api/vendor-contact",
        action="save_vendor_contact",
        target_tables=("vendor_contacts",),
        category="high-risk non-admin site-scoped write path",
        status="INVENTORY ONLY",
        risk="high",
        site_scoped="yes",
        current_site_enforced="no",
        ownership_validation_required="yes",
        recommendation="Add current_site + site permission + vendor ownership enforcement in a future write isolation stage.",
        source_markers=('@app.route("/api/vendor-contact", methods=["POST"])',),
    ),
    InventoryItem(
        route="/api/vendor-work-entry",
        action="save_vendor_work_entry",
        target_tables=("vendor_work_entries",),
        category="high-risk non-admin site-scoped write path",
        status="INVENTORY ONLY",
        risk="high",
        site_scoped="yes",
        current_site_enforced="no",
        ownership_validation_required="yes",
        recommendation="Add current_site + site permission + vendor ownership enforcement in a future write isolation stage.",
        source_markers=('@app.route("/api/vendor-work-entry", methods=["POST"])',),
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Check site write isolation readiness inventory.")
    parser.parse_args()

    print("site_write_isolation_readiness_scope: staged_enforcement")
    print(f"app_source: {APP_PATH}")
    print("WARNING P-3B-2A applies enforcement only to /api/progress")
    print("WARNING remaining high-risk paths are not yet enforced")
    print("WARNING formal write isolation is deferred to a later stage")

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

    print(f"issues_count: {len(issues)}")
    if issues:
        for issue in issues:
            print(f"ISSUE {issue}")
        raise SystemExit("FAIL site write isolation readiness check failed.")

    print("PASS site write isolation readiness check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
