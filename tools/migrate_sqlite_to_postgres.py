from __future__ import annotations

import argparse
import sqlite3
from typing import Sequence

from psycopg import sql

from _db_migration_common import (
    PRIMARY_KEYS,
    REVERSE_DELETE_ORDER,
    SEQUENCE_TABLES,
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate local SQLite seed data into a staging PostgreSQL database."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete target PostgreSQL rows in reverse FK order before importing.",
    )
    return parser.parse_args()


def build_upsert_statement(table: str, columns: Sequence[str]) -> sql.Composed:
    primary_keys = PRIMARY_KEYS[table]
    non_primary_columns = [column for column in columns if column not in primary_keys]

    insert_sql = sql.SQL(
        "INSERT INTO {table} ({columns}) VALUES ({values})"
    ).format(
        table=sql.Identifier(table),
        columns=sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        values=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )

    if not non_primary_columns:
        return insert_sql + sql.SQL(" ON CONFLICT ({pk}) DO NOTHING").format(
            pk=sql.SQL(", ").join(sql.Identifier(column) for column in primary_keys)
        )

    return insert_sql + sql.SQL(" ON CONFLICT ({pk}) DO UPDATE SET {updates}").format(
        pk=sql.SQL(", ").join(sql.Identifier(column) for column in primary_keys),
        updates=sql.SQL(", ").join(
            sql.SQL("{column} = EXCLUDED.{column}").format(column=sql.Identifier(column))
            for column in non_primary_columns
        ),
    )


def ensure_target_is_empty(postgres_counts: dict[str, int], force: bool) -> None:
    non_empty = {table: count for table, count in postgres_counts.items() if count > 0}
    if non_empty and not force:
        details = ", ".join(f"{table}={count}" for table, count in non_empty.items())
        raise SystemExit(
            "Target PostgreSQL already contains data. "
            f"Refusing to overwrite without --force. Non-empty tables: {details}"
        )


def delete_target_rows(pg_conn) -> None:
    with pg_conn.cursor() as cur:
        for table in REVERSE_DELETE_ORDER:
            cur.execute(sql.SQL("DELETE FROM {}").format(sql.Identifier(table)))


def import_table(sqlite_conn: sqlite3.Connection, pg_conn, table: str) -> int:
    columns = fetch_sqlite_columns(sqlite_conn, table)
    rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
    if not rows:
        return 0

    statement = build_upsert_statement(table, columns)
    payload = [tuple(row[column] for column in columns) for row in rows]
    with pg_conn.cursor() as cur:
        cur.executemany(statement, payload)
    return len(rows)


def reset_postgres_sequences(pg_conn) -> None:
    with pg_conn.cursor() as cur:
        for table in SEQUENCE_TABLES:
            cur.execute(
                sql.SQL(
                    """
                    SELECT setval(
                        pg_get_serial_sequence({table_name}, 'id'),
                        COALESCE(MAX(id), 1),
                        COUNT(*) > 0
                    )
                    FROM {table_ident}
                    """
                ).format(
                    table_name=sql.Literal(table),
                    table_ident=sql.Identifier(table),
                )
            )


def main() -> int:
    args = parse_args()
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

            ensure_target_is_empty(postgres_counts, force=args.force)

            with pg_conn.transaction():
                if args.force:
                    delete_target_rows(pg_conn)

                imported_counts = {
                    table: import_table(sqlite_conn, pg_conn, table) for table in TABLE_ORDER
                }
                reset_postgres_sequences(pg_conn)

            print("Imported rows:")
            for table in TABLE_ORDER:
                print(f"  {table}: {imported_counts[table]} rows")

            final_counts = fetch_postgres_counts(pg_conn)
            print("Final counts:")
            for table in TABLE_ORDER:
                print(f"  {table}: sqlite={sqlite_counts[table]} postgres={final_counts[table]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
