from __future__ import annotations

import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "site.db"
SEED_PATH = ROOT / "seeds" / "default_seed.json"
TABLES = [
    "users",
    "meta",
    "sheets",
    "tasks",
    "floors",
    "units",
    "progress",
    "unit_extra",
    "extra_fields",
    "unit_extra_values",
]


def export_seed(db_path: Path = DB_PATH, seed_path: Path = SEED_PATH) -> Path:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        payload: dict[str, object] = {
            "source_db": str(db_path.name),
            "tables": {},
        }
        for table in TABLES:
            rows = [dict(row) for row in conn.execute(f"SELECT * FROM {table}")]
            payload["tables"][table] = rows
    finally:
        conn.close()

    seed_path.parent.mkdir(parents=True, exist_ok=True)
    seed_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return seed_path


def main() -> None:
    seed_path = export_seed()
    print(f"Exported seed to {seed_path}")


if __name__ == "__main__":
    main()
