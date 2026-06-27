from __future__ import annotations

import ast
import os
import sqlite3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_DB_PATH = ROOT / "site.db"
TABLES = [
    "users",
    "sheets",
    "tasks",
    "floors",
    "units",
    "progress",
    "unit_extra",
    "extra_fields",
    "unit_extra_values",
    "meta",
]


def resolve_db_path() -> tuple[Path, bool]:
    configured = os.environ.get("APP_DB_PATH")
    if configured:
        path = Path(configured)
        if path.exists():
            return path, False

    if DEFAULT_DB_PATH.exists():
        return DEFAULT_DB_PATH, False

    temp_dir = Path(tempfile.mkdtemp(prefix="model-schema-check-"))
    temp_db = temp_dir / "site.db"
    os.environ["APP_DB_PATH"] = str(temp_db)
    from app import bootstrap

    bootstrap()
    return temp_db, True


def load_sqlite_schema(db_path: Path) -> dict[str, dict[str, object]]:
    conn = sqlite3.connect(db_path)
    try:
        schema: dict[str, dict[str, object]] = {}
        for table in TABLES:
            columns = {}
            for cid, name, column_type, notnull, default_value, pk in conn.execute(f"PRAGMA table_info({table})"):
                columns[name] = {
                    "type": (column_type or "").upper(),
                    "nullable": False if pk else not bool(notnull),
                    "pk_order": pk,
                    "default": default_value,
                }
            schema[table] = {
                "exists": bool(columns),
                "columns": columns,
                "primary_key": [name for name, info in sorted(columns.items(), key=lambda item: item[1]["pk_order"]) if info["pk_order"]],
            }
        return schema
    finally:
        conn.close()


def _literal(node: ast.AST):
    if isinstance(node, ast.Constant):
        return node.value
    return None


def _name_from_node(node: ast.AST) -> str | None:
    if isinstance(node, ast.Attribute):
        base = _name_from_node(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def _column_type(call: ast.Call) -> str:
    for arg in call.args:
        name = _name_from_node(arg)
        if name and name.startswith("db.") and name not in {"db.ForeignKey", "db.text"}:
            return name.split(".", 1)[1].upper()
    return "UNKNOWN"


def parse_model_schema() -> dict[str, dict[str, object]]:
    module = ast.parse((ROOT / "models.py").read_text(encoding="utf-8"))
    schema: dict[str, dict[str, object]] = {}

    for node in module.body:
        if not isinstance(node, ast.ClassDef):
            continue

        table_name = None
        columns: dict[str, dict[str, object]] = {}

        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        table_name = _literal(item.value)

                if len(item.targets) != 1 or not isinstance(item.targets[0], ast.Name):
                    continue

                column_name = item.targets[0].id
                if not isinstance(item.value, ast.Call):
                    continue
                func_name = _name_from_node(item.value.func)
                if func_name != "db.Column":
                    continue

                info = {
                    "type": _column_type(item.value),
                    "nullable": None,
                    "primary_key": False,
                    "unique": False,
                }

                for keyword in item.value.keywords:
                    if keyword.arg == "nullable":
                        info["nullable"] = bool(_literal(keyword.value))
                    elif keyword.arg == "primary_key":
                        info["primary_key"] = bool(_literal(keyword.value))
                    elif keyword.arg == "unique":
                        info["unique"] = bool(_literal(keyword.value))

                if info["primary_key"] and info["nullable"] is None:
                    info["nullable"] = False
                if info["nullable"] is None:
                    info["nullable"] = True

                columns[column_name] = info

        if table_name in TABLES:
            schema[table_name] = {
                "exists": True,
                "columns": columns,
                "primary_key": [name for name, info in columns.items() if info["primary_key"]],
            }

    for table in TABLES:
        schema.setdefault(table, {"exists": False, "columns": {}, "primary_key": []})

    return schema


def compare_schema(model_schema: dict[str, dict[str, object]], sqlite_schema: dict[str, dict[str, object]]) -> tuple[bool, dict[str, list[str]]]:
    all_ok = True
    diffs: dict[str, list[str]] = {}

    for table in TABLES:
        table_diffs: list[str] = []
        model_table = model_schema[table]
        sqlite_table = sqlite_schema[table]

        if not sqlite_table["exists"]:
            table_diffs.append("table missing in SQLite")
        if not model_table["exists"]:
            table_diffs.append("table missing in models.py")

        model_columns = model_table["columns"]
        sqlite_columns = sqlite_table["columns"]

        missing_in_model = sorted(set(sqlite_columns) - set(model_columns))
        missing_in_db = sorted(set(model_columns) - set(sqlite_columns))
        for column in missing_in_model:
            table_diffs.append(f"column missing in models.py: {column}")
        for column in missing_in_db:
            table_diffs.append(f"column missing in SQLite: {column}")

        shared_columns = sorted(set(model_columns) & set(sqlite_columns))
        for column in shared_columns:
            model_col = model_columns[column]
            sqlite_col = sqlite_columns[column]
            if bool(model_col["nullable"]) != bool(sqlite_col["nullable"]):
                table_diffs.append(
                    f"nullable mismatch for {column}: model={model_col['nullable']} sqlite={sqlite_col['nullable']}"
                )
            if str(model_col["type"]).upper() != str(sqlite_col["type"]).upper():
                table_diffs.append(
                    f"type hint difference for {column}: model={model_col['type']} sqlite={sqlite_col['type']}"
                )

        if model_table["primary_key"] != sqlite_table["primary_key"]:
            table_diffs.append(
                f"primary key mismatch: model={model_table['primary_key']} sqlite={sqlite_table['primary_key']}"
            )

        diffs[table] = table_diffs
        if table_diffs:
            all_ok = False

    return all_ok, diffs


def main() -> int:
    db_path, temporary = resolve_db_path()
    model_schema = parse_model_schema()
    sqlite_schema = load_sqlite_schema(db_path)
    ok, diffs = compare_schema(model_schema, sqlite_schema)

    print(f"Database: {db_path}")
    if temporary:
        print("Note: created temporary SQLite database via bootstrap() for validation.")
    print("PASS" if ok else "FAIL")
    for table in TABLES:
        print(f"\n[{table}]")
        if diffs[table]:
            for diff in diffs[table]:
                print(f"- {diff}")
        else:
            print("- OK")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
