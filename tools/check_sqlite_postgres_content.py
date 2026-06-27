from __future__ import annotations

import argparse
import random
import sqlite3

from psycopg import sql

from _db_migration_common import (
    PRIMARY_KEYS,
    TABLE_ORDER,
    connect_postgres,
    connect_sqlite,
    fetch_postgres_counts,
    fetch_sqlite_columns,
    fetch_sqlite_counts,
    redact_database_url,
    resolved_sqlite_source,
    require_postgres_database_url,
)


PROGRESS_HEAD_LIMIT = 200
PROGRESS_TAIL_LIMIT = 200
PROGRESS_SAMPLE_SIZE = 500
PROGRESS_SAMPLE_SEED = 2402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare SQLite seed content with staging PostgreSQL content."
    )
    return parser.parse_args()


def build_where_clause(columns: tuple[str, ...]) -> sql.Composed:
    return sql.SQL(" AND ").join(
        sql.SQL("{} = {}").format(sql.Identifier(column), sql.Placeholder())
        for column in columns
    )


def build_order_clause(columns: tuple[str, ...]) -> sql.Composed:
    return sql.SQL(", ").join(sql.Identifier(column) for column in columns)


def fetch_postgres_table_rows(pg_conn, table: str, columns: list[str]) -> list[dict[str, object]]:
    primary_keys = PRIMARY_KEYS[table]
    query = sql.SQL("SELECT {columns} FROM {table} ORDER BY {order_by}").format(
        columns=sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        table=sql.Identifier(table),
        order_by=build_order_clause(primary_keys),
    )
    with pg_conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    return [dict(zip(columns, row, strict=False)) for row in rows]


def fetch_sqlite_table_rows(
    sqlite_conn: sqlite3.Connection, table: str, columns: list[str]
) -> list[dict[str, object]]:
    primary_keys = PRIMARY_KEYS[table]
    order_by = ", ".join(primary_keys)
    rows = sqlite_conn.execute(
        f"SELECT {', '.join(columns)} FROM {table} ORDER BY {order_by}"
    ).fetchall()
    return [{column: row[column] for column in columns} for row in rows]


def key_for_row(table: str, row: dict[str, object]) -> tuple[object, ...]:
    return tuple(row[column] for column in PRIMARY_KEYS[table])


def compare_rows(
    table: str,
    sqlite_rows: list[dict[str, object]],
    postgres_rows: list[dict[str, object]],
) -> list[str]:
    sqlite_map = {key_for_row(table, row): row for row in sqlite_rows}
    postgres_map = {key_for_row(table, row): row for row in postgres_rows}
    all_keys = sorted(set(sqlite_map) | set(postgres_map))

    differences: list[str] = []
    for key in all_keys:
        sqlite_row = sqlite_map.get(key)
        postgres_row = postgres_map.get(key)
        if sqlite_row != postgres_row:
            differences.append(
                f"{table} key={key}: sqlite={sqlite_row!r} postgres={postgres_row!r}"
            )
    return differences


def fetch_sqlite_progress_keys(sqlite_conn: sqlite3.Connection) -> list[tuple[object, ...]]:
    rows = sqlite_conn.execute(
        "SELECT unit_id, task_id FROM progress ORDER BY unit_id, task_id"
    ).fetchall()
    return [(row["unit_id"], row["task_id"]) for row in rows]


def select_progress_keys(keys: list[tuple[object, ...]]) -> list[tuple[object, ...]]:
    selected: list[tuple[object, ...]] = []
    selected_set: set[tuple[object, ...]] = set()

    def add_many(items: list[tuple[object, ...]]) -> None:
        for item in items:
            if item not in selected_set:
                selected.append(item)
                selected_set.add(item)

    add_many(keys[:PROGRESS_HEAD_LIMIT])
    if PROGRESS_TAIL_LIMIT:
        add_many(keys[-PROGRESS_TAIL_LIMIT:])

    sample_size = min(PROGRESS_SAMPLE_SIZE, len(keys))
    if sample_size:
        rng = random.Random(PROGRESS_SAMPLE_SEED)
        add_many(rng.sample(keys, sample_size))

    return selected


def fetch_sqlite_row_by_key(
    sqlite_conn: sqlite3.Connection, table: str, columns: list[str], key: tuple[object, ...]
) -> dict[str, object] | None:
    primary_keys = PRIMARY_KEYS[table]
    where_clause = " AND ".join(f"{column} = ?" for column in primary_keys)
    row = sqlite_conn.execute(
        f"SELECT {', '.join(columns)} FROM {table} WHERE {where_clause}",
        key,
    ).fetchone()
    if row is None:
        return None
    return {column: row[column] for column in columns}


def fetch_postgres_row_by_key(pg_conn, table: str, columns: list[str], key: tuple[object, ...]) -> dict[str, object] | None:
    primary_keys = PRIMARY_KEYS[table]
    query = sql.SQL("SELECT {columns} FROM {table} WHERE {where_clause}").format(
        columns=sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        table=sql.Identifier(table),
        where_clause=build_where_clause(primary_keys),
    )
    with pg_conn.cursor() as cur:
        cur.execute(query, key)
        row = cur.fetchone()
    if row is None:
        return None
    return dict(zip(columns, row, strict=False))


def compare_progress(
    sqlite_conn: sqlite3.Connection,
    pg_conn,
    sqlite_counts: dict[str, int],
    postgres_counts: dict[str, int],
) -> list[str]:
    differences: list[str] = []
    if sqlite_counts["progress"] != postgres_counts["progress"]:
        differences.append(
            f"progress count mismatch: sqlite={sqlite_counts['progress']} postgres={postgres_counts['progress']}"
        )

    columns = fetch_sqlite_columns(sqlite_conn, "progress")
    sampled_keys = select_progress_keys(fetch_sqlite_progress_keys(sqlite_conn))
    for key in sampled_keys:
        sqlite_row = fetch_sqlite_row_by_key(sqlite_conn, "progress", columns, key)
        postgres_row = fetch_postgres_row_by_key(pg_conn, "progress", columns, key)
        if sqlite_row != postgres_row:
            differences.append(
                f"progress key={key}: sqlite={sqlite_row!r} postgres={postgres_row!r}"
            )
    return differences


def compare_full_table(sqlite_conn: sqlite3.Connection, pg_conn, table: str) -> list[str]:
    columns = fetch_sqlite_columns(sqlite_conn, table)
    sqlite_rows = fetch_sqlite_table_rows(sqlite_conn, table, columns)
    postgres_rows = fetch_postgres_table_rows(pg_conn, table, columns)
    return compare_rows(table, sqlite_rows, postgres_rows)


def main() -> int:
    parse_args()
    database_url = require_postgres_database_url()

    print(f"PostgreSQL target: {redact_database_url(database_url)}")

    with resolved_sqlite_source() as sqlite_source:
        if sqlite_source.is_temporary_seeded:
            print("using temporary seeded sqlite source")
            print(f"temp db path: {sqlite_source.path}")
        else:
            print(f"SQLite source: {sqlite_source.path}")

        with connect_sqlite(sqlite_source.path) as sqlite_conn, connect_postgres(database_url) as pg_conn:
            sqlite_counts = fetch_sqlite_counts(sqlite_conn)
            postgres_counts = fetch_postgres_counts(pg_conn)

            has_failure = False
            for table in TABLE_ORDER:
                if table == "progress":
                    differences = compare_progress(sqlite_conn, pg_conn, sqlite_counts, postgres_counts)
                else:
                    differences = compare_full_table(sqlite_conn, pg_conn, table)

                if differences:
                    has_failure = True
                    print(f"FAIL {table}")
                    for difference in differences:
                        print(f"  {difference}")
                else:
                    print(f"PASS {table}")

    if has_failure:
        print("FAIL SQLite/PostgreSQL content does not match.")
        return 1

    print("PASS SQLite/PostgreSQL content matches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
