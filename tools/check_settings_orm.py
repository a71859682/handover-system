from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def prepare_temp_db() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="settings-orm-check-"))
    db_path = temp_dir / "site.db"
    os.environ["APP_DB_PATH"] = str(db_path)
    return db_path


def main() -> int:
    db_path = prepare_temp_db()

    import app
    from services.settings_orm_service import get_settings_orm

    app.bootstrap()

    with app.db() as conn:
        sqlite_settings = app.get_settings(conn)

    with app.app.app_context():
        orm_settings = get_settings_orm(app.DEFAULT_SETTINGS)

    all_keys = sorted(set(sqlite_settings) | set(orm_settings))
    differences = []
    for key in all_keys:
        sqlite_value = sqlite_settings.get(key)
        orm_value = orm_settings.get(key)
        if sqlite_value != orm_value:
            differences.append((key, sqlite_value, orm_value))

    print(f"Database: {db_path}")
    if differences:
        print("FAIL")
        for key, sqlite_value, orm_value in differences:
            print(f"- {key}: sqlite3={sqlite_value!r} orm={orm_value!r}")
        return 1

    print("PASS")
    for key in all_keys:
        print(f"- {key}: {sqlite_settings[key]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
