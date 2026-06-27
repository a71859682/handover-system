from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def prepare_temp_db() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="sheets-orm-check-"))
    db_path = temp_dir / "site.db"
    os.environ["APP_DB_PATH"] = str(db_path)
    return db_path


def main() -> int:
    db_path = prepare_temp_db()

    import app
    from services.sheets_orm_service import (
        get_sheet_orm,
        list_floors_for_sheet_orm,
        list_sheets_orm,
        list_tasks_for_sheet_orm,
        list_units_for_floor_orm,
    )

    app.bootstrap()

    differences: list[str] = []

    with app.db() as conn:
        sqlite_sheets = conn.execute("SELECT id, name, sort_order FROM sheets ORDER BY sort_order, id").fetchall()

        with app.app.app_context():
            orm_sheets = list_sheets_orm()

            if len(sqlite_sheets) != len(orm_sheets):
                differences.append(f"sheet count mismatch: sqlite3={len(sqlite_sheets)} orm={len(orm_sheets)}")

            for sqlite_sheet, orm_sheet in zip(sqlite_sheets, orm_sheets):
                sqlite_sheet_payload = {
                    "id": sqlite_sheet["id"],
                    "name": sqlite_sheet["name"],
                    "sort_order": sqlite_sheet["sort_order"],
                }
                orm_sheet_payload = {
                    "id": orm_sheet.id,
                    "name": orm_sheet.name,
                    "sort_order": orm_sheet.sort_order,
                }
                if sqlite_sheet_payload != orm_sheet_payload:
                    differences.append(
                        f"sheet mismatch for id={sqlite_sheet['id']}: sqlite3={sqlite_sheet_payload!r} orm={orm_sheet_payload!r}"
                    )

                fetched_sheet = get_sheet_orm(sqlite_sheet["id"])
                if not fetched_sheet or fetched_sheet.id != sqlite_sheet["id"]:
                    differences.append(f"get_sheet_orm({sqlite_sheet['id']}) did not return the expected sheet")

                sqlite_tasks = conn.execute(
                    "SELECT id, col_index, name, vendor, location FROM tasks WHERE sheet_id = ? ORDER BY col_index",
                    (sqlite_sheet["id"],),
                ).fetchall()
                orm_tasks = list_tasks_for_sheet_orm(sqlite_sheet["id"])
                if len(sqlite_tasks) != len(orm_tasks):
                    differences.append(
                        f"task count mismatch for sheet {sqlite_sheet['id']}: sqlite3={len(sqlite_tasks)} orm={len(orm_tasks)}"
                    )
                for sqlite_task, orm_task in zip(sqlite_tasks, orm_tasks):
                    sqlite_task_payload = {
                        "id": sqlite_task["id"],
                        "col_index": sqlite_task["col_index"],
                        "name": sqlite_task["name"],
                        "vendor": sqlite_task["vendor"],
                        "location": sqlite_task["location"],
                    }
                    orm_task_payload = {
                        "id": orm_task.id,
                        "col_index": orm_task.col_index,
                        "name": orm_task.name,
                        "vendor": orm_task.vendor,
                        "location": orm_task.location,
                    }
                    if sqlite_task_payload != orm_task_payload:
                        differences.append(
                            f"task mismatch for sheet {sqlite_sheet['id']} task {sqlite_task['id']}: sqlite3={sqlite_task_payload!r} orm={orm_task_payload!r}"
                        )

                sqlite_floors = conn.execute(
                    """
                    SELECT id, name, block_name, unit_count, sort_order
                    FROM floors
                    WHERE sheet_id = ?
                    ORDER BY sort_order
                    """,
                    (sqlite_sheet["id"],),
                ).fetchall()
                orm_floors = list_floors_for_sheet_orm(sqlite_sheet["id"])
                if len(sqlite_floors) != len(orm_floors):
                    differences.append(
                        f"floor count mismatch for sheet {sqlite_sheet['id']}: sqlite3={len(sqlite_floors)} orm={len(orm_floors)}"
                    )
                for sqlite_floor, orm_floor in zip(sqlite_floors, orm_floors):
                    sqlite_floor_payload = {
                        "id": sqlite_floor["id"],
                        "name": sqlite_floor["name"],
                        "block_name": sqlite_floor["block_name"],
                        "unit_count": sqlite_floor["unit_count"],
                        "sort_order": sqlite_floor["sort_order"],
                    }
                    orm_floor_payload = {
                        "id": orm_floor.id,
                        "name": orm_floor.name,
                        "block_name": orm_floor.block_name,
                        "unit_count": orm_floor.unit_count,
                        "sort_order": orm_floor.sort_order,
                    }
                    if sqlite_floor_payload != orm_floor_payload:
                        differences.append(
                            f"floor mismatch for sheet {sqlite_sheet['id']} floor {sqlite_floor['id']}: sqlite3={sqlite_floor_payload!r} orm={orm_floor_payload!r}"
                        )

                    sqlite_units = conn.execute(
                        "SELECT id, name, sort_order FROM units WHERE floor_id = ? ORDER BY sort_order",
                        (sqlite_floor["id"],),
                    ).fetchall()
                    orm_units = list_units_for_floor_orm(sqlite_floor["id"])
                    if len(sqlite_units) != len(orm_units):
                        differences.append(
                            f"unit count mismatch for floor {sqlite_floor['id']}: sqlite3={len(sqlite_units)} orm={len(orm_units)}"
                        )
                    for sqlite_unit, orm_unit in zip(sqlite_units, orm_units):
                        sqlite_unit_payload = {
                            "id": sqlite_unit["id"],
                            "name": sqlite_unit["name"],
                            "sort_order": sqlite_unit["sort_order"],
                        }
                        orm_unit_payload = {
                            "id": orm_unit.id,
                            "name": orm_unit.name,
                            "sort_order": orm_unit.sort_order,
                        }
                        if sqlite_unit_payload != orm_unit_payload:
                            differences.append(
                                f"unit mismatch for floor {sqlite_floor['id']} unit {sqlite_unit['id']}: sqlite3={sqlite_unit_payload!r} orm={orm_unit_payload!r}"
                            )

    print(f"Database: {db_path}")
    if differences:
        print("FAIL")
        for diff in differences:
            print(f"- {diff}")
        return 1

    print("PASS")
    print(f"- sheets: {len(sqlite_sheets)}")
    for sheet in orm_sheets:
        print(f"- sheet id={sheet.id} name={sheet.name!r} sort_order={sheet.sort_order}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
