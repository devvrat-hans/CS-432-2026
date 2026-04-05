"""Prune Module B logical databases while keeping blinddrop_core by default."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

MODULE_B_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = MODULE_B_DIR / "db_management_system" / "module_b.sqlite3"
DEFAULT_KEEP = ("blinddrop_core",)


def _normalize_keep_names(values: list[str]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for raw in values:
        for part in raw.split(","):
            name = part.strip()
            if not name or name in seen:
                continue
            names.append(name)
            seen.add(name)
    return names


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _count_rows(conn: sqlite3.Connection, table_name: str, where_clause: str = "", params: tuple = ()) -> int:
    sql = f"SELECT COUNT(*) FROM {table_name}"
    if where_clause:
        sql = f"{sql} WHERE {where_clause}"
    return int(conn.execute(sql, params).fetchone()[0])


def _database_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM project_databases ORDER BY name").fetchall()
    return [row[0] for row in rows]


def _placeholder_block(count: int) -> str:
    return ",".join("?" for _ in range(count))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Remove non-core logical databases from Module B catalog tables. "
            "Use --execute to apply changes; otherwise this runs as dry-run."
        )
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to sqlite database file (default: assignment-03/Module_B/db_management_system/module_b.sqlite3).",
    )
    parser.add_argument(
        "--keep",
        action="append",
        default=list(DEFAULT_KEEP),
        help="Database name(s) to keep. Can be used multiple times or as comma-separated values.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply deletions. Without this flag the script only reports what would be removed.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    db_path = Path(args.db_path).expanduser()
    if not db_path.is_absolute():
        db_path = (MODULE_B_DIR / db_path).resolve()

    keep_names = _normalize_keep_names(args.keep)
    if not keep_names:
        print("No keep names provided after parsing. Aborting.")
        return 1

    if not db_path.exists():
        print(f"Database file not found: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")

        required_tables = ("project_databases", "project_tables", "project_records")
        missing = [table for table in required_tables if not _table_exists(conn, table)]
        if missing:
            print(
                "Missing required catalog tables: "
                + ", ".join(missing)
                + ". Nothing was changed."
            )
            return 1

        before_databases = _count_rows(conn, "project_databases")
        before_tables = _count_rows(conn, "project_tables")
        before_records = _count_rows(conn, "project_records")

        all_names = _database_names(conn)
        to_remove = [name for name in all_names if name not in keep_names]

        print(f"Target file: {db_path}")
        print(f"Keep set: {', '.join(keep_names)}")
        print(f"Logical databases currently present: {before_databases}")
        print(f"Logical databases to remove: {len(to_remove)}")
        if to_remove:
            preview = ", ".join(to_remove[:20])
            if len(to_remove) > 20:
                preview += ", ..."
            print(f"Removal preview: {preview}")

        if not args.execute:
            print("Dry-run complete. Re-run with --execute to apply changes.")
            return 0

        with conn:
            if to_remove:
                placeholders = _placeholder_block(len(to_remove))
                conn.execute(
                    f"DELETE FROM project_records WHERE database_name IN ({placeholders})",
                    to_remove,
                )
                conn.execute(
                    f"DELETE FROM project_tables WHERE database_name IN ({placeholders})",
                    to_remove,
                )
                conn.execute(
                    f"DELETE FROM project_databases WHERE name IN ({placeholders})",
                    to_remove,
                )

            # Guard against any previous orphaned rows.
            conn.execute(
                "DELETE FROM project_records WHERE database_name NOT IN (SELECT name FROM project_databases)"
            )
            conn.execute(
                "DELETE FROM project_tables WHERE database_name NOT IN (SELECT name FROM project_databases)"
            )

            for db_name in keep_names:
                conn.execute(
                    "INSERT OR IGNORE INTO project_databases (name, created_at, created_by) VALUES (?, ?, NULL)",
                    (db_name, "1970-01-01T00:00:00+00:00"),
                )

        after_databases = _count_rows(conn, "project_databases")
        after_tables = _count_rows(conn, "project_tables")
        after_records = _count_rows(conn, "project_records")

        print("Cleanup applied successfully.")
        print(f"project_databases: {before_databases} -> {after_databases}")
        print(f"project_tables:    {before_tables} -> {after_tables}")
        print(f"project_records:   {before_records} -> {after_records}")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
