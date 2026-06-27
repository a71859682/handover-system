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
    temp_dir = Path(tempfile.mkdtemp(prefix="settings-runtime-switch-"))
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


def main() -> int:
    db_path = prepare_temp_db()

    app_sqlite = load_app_with_flag(db_path, use_sqlalchemy_reads=False)
    with app_sqlite.db() as conn:
        sqlite_settings = app_sqlite.get_settings(conn)
        sqlite_site_title = app_sqlite.get_setting(conn, "site_title")

    app_orm = load_app_with_flag(db_path, use_sqlalchemy_reads=True)
    with app_orm.db() as conn:
        orm_settings = app_orm.get_settings(conn)
        orm_site_title = app_orm.get_setting(conn, "site_title")

    differences: list[str] = []
    if sqlite_site_title != orm_site_title:
        differences.append(
            f"site_title: sqlite3={sqlite_site_title!r} orm={orm_site_title!r}"
        )

    all_keys = sorted(set(sqlite_settings) | set(orm_settings))
    for key in all_keys:
        sqlite_value = sqlite_settings.get(key)
        orm_value = orm_settings.get(key)
        if sqlite_value != orm_value:
            differences.append(f"{key}: sqlite3={sqlite_value!r} orm={orm_value!r}")

    print(f"Database: {db_path}")
    if differences:
        print("FAIL")
        for difference in differences:
            print(f"- {difference}")
        return 1

    print("PASS")
    for key in all_keys:
        print(f"- {key}: {sqlite_settings[key]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
