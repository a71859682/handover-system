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
    temp_dir = Path(tempfile.mkdtemp(prefix="progress-runtime-switch-"))
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


def collect_progress_payload(app_module) -> dict[str, object]:
    sheets = app_module.list_sheets()
    return {
        "progress": app_module.list_progress(),
        "unit_extra": app_module.list_unit_extra(),
        "extra_fields_by_sheet": {
            sheet["id"]: app_module.list_extra_fields_for_sheet(sheet["id"]) for sheet in sheets
        },
        "unit_extra_values_by_sheet": {
            sheet["id"]: app_module.list_unit_extra_values_for_sheet(sheet["id"]) for sheet in sheets
        },
    }


def main() -> int:
    db_path = prepare_temp_db()

    app_sqlite = load_app_with_flag(db_path, use_sqlalchemy_reads=False)
    sqlite_payload = collect_progress_payload(app_sqlite)

    app_orm = load_app_with_flag(db_path, use_sqlalchemy_reads=True)
    orm_payload = collect_progress_payload(app_orm)

    print(f"Database: {db_path}")
    if sqlite_payload != orm_payload:
        print("FAIL")
        print(f"- sqlite3={sqlite_payload!r}")
        print(f"- orm={orm_payload!r}")
        return 1

    print("PASS")
    print(f"- progress count: {len(sqlite_payload['progress'])}")
    print(f"- unit_extra count: {len(sqlite_payload['unit_extra'])}")
    for sheet_id, fields in sqlite_payload["extra_fields_by_sheet"].items():
        print(
            f"- sheet {sheet_id}: extra_fields={len(fields)} unit_extra_values={len(sqlite_payload['unit_extra_values_by_sheet'][sheet_id])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
