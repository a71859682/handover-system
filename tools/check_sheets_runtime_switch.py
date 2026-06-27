from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def prepare_temp_db() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="sheets-runtime-switch-"))
    return temp_dir / "site.db"


def load_app_with_flag(db_path: Path, use_sqlalchemy_reads: bool):
    os.environ["APP_DB_PATH"] = str(db_path)
    os.environ["USE_SQLALCHEMY_READS"] = "true" if use_sqlalchemy_reads else "false"

    config_module = importlib.import_module("config")
    importlib.reload(config_module)

    app_module = importlib.import_module("app")
    app_module = importlib.reload(app_module)
    app_module.bootstrap()
    return app_module


def collect_sheet_payload(app_module) -> dict[str, object]:
    sheets = app_module.list_sheets()
    payload: dict[str, object] = {"sheets": sheets, "by_sheet": {}}
    by_sheet: dict[int, dict[str, object]] = {}
    for sheet in sheets:
        sheet_id = sheet["id"]
        floors = app_module.list_floors_for_sheet(sheet_id)
        by_sheet[sheet_id] = {
            "sheet": app_module.get_sheet(sheet_id),
            "tasks": app_module.list_tasks_for_sheet(sheet_id),
            "floors": floors,
            "units_by_floor": {
                floor["id"]: app_module.list_units_for_floor(floor["id"]) for floor in floors
            },
        }
    payload["by_sheet"] = by_sheet
    return payload


def main() -> int:
    db_path = prepare_temp_db()

    app_sqlite = load_app_with_flag(db_path, use_sqlalchemy_reads=False)
    sqlite_payload = collect_sheet_payload(app_sqlite)

    app_orm = load_app_with_flag(db_path, use_sqlalchemy_reads=True)
    orm_payload = collect_sheet_payload(app_orm)

    print(f"Database: {db_path}")
    if sqlite_payload != orm_payload:
        print("FAIL")
        print(f"- sqlite3={sqlite_payload!r}")
        print(f"- orm={orm_payload!r}")
        return 1

    print("PASS")
    print(f"- sheets: {len(sqlite_payload['sheets'])}")
    for sheet in sqlite_payload["sheets"]:
        print(f"- sheet id={sheet['id']} name={sheet['name']!r} sort_order={sheet['sort_order']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
