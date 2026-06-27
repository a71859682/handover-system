from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def prepare_temp_db() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="progress-orm-check-"))
    db_path = temp_dir / "site.db"
    os.environ["APP_DB_PATH"] = str(db_path)
    return db_path


def main() -> int:
    db_path = prepare_temp_db()

    import app
    from services.progress_orm_service import (
        list_extra_fields_for_sheet_orm,
        list_progress_orm,
        list_unit_extra_orm,
        list_unit_extra_values_for_sheet_orm,
    )

    app.bootstrap()
    differences: list[str] = []

    with app.db() as conn:
        sqlite_progress = conn.execute(
            """
            SELECT unit_id, task_id, value
            FROM progress
            ORDER BY unit_id, task_id
            """
        ).fetchall()
        sqlite_unit_extra = conn.execute(
            """
            SELECT unit_id, initial_check, recheck_1, recheck_2, handover, updated_by, updated_at
            FROM unit_extra
            ORDER BY unit_id
            """
        ).fetchall()
        sqlite_sheets = conn.execute("SELECT id FROM sheets ORDER BY sort_order, id").fetchall()

        with app.app.app_context():
            orm_progress = list_progress_orm()
            orm_unit_extra = list_unit_extra_orm()

            if len(sqlite_progress) != len(orm_progress):
                differences.append(f"progress count mismatch: sqlite3={len(sqlite_progress)} orm={len(orm_progress)}")

            for sqlite_row, orm_row in zip(sqlite_progress[:100], orm_progress[:100]):
                sqlite_payload = {
                    "unit_id": sqlite_row["unit_id"],
                    "task_id": sqlite_row["task_id"],
                    "value": sqlite_row["value"],
                }
                orm_payload = {
                    "unit_id": orm_row.unit_id,
                    "task_id": orm_row.task_id,
                    "value": orm_row.value,
                }
                if sqlite_payload != orm_payload:
                    differences.append(
                        f"progress mismatch: sqlite3={sqlite_payload!r} orm={orm_payload!r}"
                    )

            if len(sqlite_unit_extra) != len(orm_unit_extra):
                differences.append(
                    f"unit_extra count mismatch: sqlite3={len(sqlite_unit_extra)} orm={len(orm_unit_extra)}"
                )

            for sqlite_row, orm_row in zip(sqlite_unit_extra[:100], orm_unit_extra[:100]):
                sqlite_payload = {
                    "unit_id": sqlite_row["unit_id"],
                    "initial_check": sqlite_row["initial_check"],
                    "recheck_1": sqlite_row["recheck_1"],
                    "recheck_2": sqlite_row["recheck_2"],
                    "handover": sqlite_row["handover"],
                    "updated_by": sqlite_row["updated_by"],
                    "updated_at": sqlite_row["updated_at"],
                }
                orm_payload = {
                    "unit_id": orm_row.unit_id,
                    "initial_check": orm_row.initial_check,
                    "recheck_1": orm_row.recheck_1,
                    "recheck_2": orm_row.recheck_2,
                    "handover": orm_row.handover,
                    "updated_by": orm_row.updated_by,
                    "updated_at": orm_row.updated_at,
                }
                if sqlite_payload != orm_payload:
                    differences.append(
                        f"unit_extra mismatch: sqlite3={sqlite_payload!r} orm={orm_payload!r}"
                    )

            for sheet in sqlite_sheets:
                sheet_id = sheet["id"]
                sqlite_extra_fields = conn.execute(
                    """
                    SELECT field_key, name, field_type, sort_order, active, is_builtin
                    FROM extra_fields
                    WHERE sheet_id = ?
                    ORDER BY sort_order, id
                    """,
                    (sheet_id,),
                ).fetchall()
                orm_extra_fields = list_extra_fields_for_sheet_orm(sheet_id)
                if len(sqlite_extra_fields) != len(orm_extra_fields):
                    differences.append(
                        f"extra_fields count mismatch for sheet {sheet_id}: sqlite3={len(sqlite_extra_fields)} orm={len(orm_extra_fields)}"
                    )
                for sqlite_row, orm_row in zip(sqlite_extra_fields, orm_extra_fields):
                    sqlite_payload = {
                        "field_key": sqlite_row["field_key"],
                        "name": sqlite_row["name"],
                        "field_type": sqlite_row["field_type"],
                        "sort_order": sqlite_row["sort_order"],
                        "active": sqlite_row["active"],
                        "is_builtin": sqlite_row["is_builtin"],
                    }
                    orm_payload = {
                        "field_key": orm_row.field_key,
                        "name": orm_row.name,
                        "field_type": orm_row.field_type,
                        "sort_order": orm_row.sort_order,
                        "active": orm_row.active,
                        "is_builtin": orm_row.is_builtin,
                    }
                    if sqlite_payload != orm_payload:
                        differences.append(
                            f"extra_fields mismatch for sheet {sheet_id}: sqlite3={sqlite_payload!r} orm={orm_payload!r}"
                        )

                sqlite_unit_extra_values = conn.execute(
                    """
                    SELECT v.unit_id, v.field_key, v.value
                    FROM unit_extra_values v
                    JOIN units u ON u.id = v.unit_id
                    JOIN floors f ON f.id = u.floor_id
                    WHERE f.sheet_id = ?
                    ORDER BY v.unit_id, v.field_key
                    """,
                    (sheet_id,),
                ).fetchall()
                orm_unit_extra_values = list_unit_extra_values_for_sheet_orm(sheet_id)
                if len(sqlite_unit_extra_values) != len(orm_unit_extra_values):
                    differences.append(
                        f"unit_extra_values count mismatch for sheet {sheet_id}: sqlite3={len(sqlite_unit_extra_values)} orm={len(orm_unit_extra_values)}"
                    )
                for sqlite_row, orm_row in zip(sqlite_unit_extra_values, orm_unit_extra_values):
                    sqlite_payload = {
                        "unit_id": sqlite_row["unit_id"],
                        "field_key": sqlite_row["field_key"],
                        "value": sqlite_row["value"],
                    }
                    orm_payload = {
                        "unit_id": orm_row.unit_id,
                        "field_key": orm_row.field_key,
                        "value": orm_row.value,
                    }
                    if sqlite_payload != orm_payload:
                        differences.append(
                            f"unit_extra_values mismatch for sheet {sheet_id}: sqlite3={sqlite_payload!r} orm={orm_payload!r}"
                        )

    print(f"Database: {db_path}")
    if differences:
        print("FAIL")
        for diff in differences:
            print(f"- {diff}")
        return 1

    print("PASS")
    print(f"- progress count: {len(sqlite_progress)}")
    print(f"- unit_extra count: {len(sqlite_unit_extra)}")
    for sheet in sqlite_sheets:
        print(f"- checked extra_fields and unit_extra_values for sheet {sheet['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
