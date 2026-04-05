#!/usr/bin/env python3
"""Prune Module B audit logs and test members, keeping blinddrop_core-related audits only."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

MODULE_B_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = MODULE_B_DIR / "db_management_system" / "module_b.sqlite3"
DEFAULT_KEEP_DATABASE = "blinddrop_core"
DEFAULT_KEEP_USERNAMES = ("admin",)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _count_rows(conn: sqlite3.Connection, table_name: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _placeholder_block(count: int) -> str:
    return ",".join("?" for _ in range(count))


def _details_mentions_database(details_text: str | None, keep_database: str) -> bool:
    if not details_text:
        return False

    if keep_database in details_text:
        return True

    try:
        payload = json.loads(details_text)
    except json.JSONDecodeError:
        return False

    def _contains_database_reference(value) -> bool:
        if isinstance(value, dict):
            for key, nested_value in value.items():
                key_text = str(key).lower()
                if key_text in {"database", "database_name", "db"} and str(nested_value) == keep_database:
                    return True
                if _contains_database_reference(nested_value):
                    return True
            return False
        if isinstance(value, list):
            return any(_contains_database_reference(item) for item in value)
        return str(value) == keep_database

    return _contains_database_reference(payload)


def _member_ids_by_usernames(conn: sqlite3.Connection, usernames: list[str]) -> set[int]:
    if not usernames:
        return set()
    placeholders = _placeholder_block(len(usernames))
    rows = conn.execute(
        f"SELECT id FROM members WHERE username IN ({placeholders})",
        usernames,
    ).fetchall()
    return {int(row[0]) for row in rows}


def _member_ids_referenced_by_catalog(conn: sqlite3.Connection) -> set[int]:
    referenced: set[int] = set()
    queries = [
        "SELECT created_by FROM project_databases WHERE created_by IS NOT NULL",
        "SELECT created_by FROM project_tables WHERE created_by IS NOT NULL",
        "SELECT created_by FROM project_records WHERE created_by IS NOT NULL",
        "SELECT updated_by FROM project_records WHERE updated_by IS NOT NULL",
    ]

    for query in queries:
        rows = conn.execute(query).fetchall()
        for row in rows:
            referenced.add(int(row[0]))

    return referenced


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Keep only audit logs related to a chosen database (default blinddrop_core) "
            "and remove unneeded members created during testing."
        )
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="Path to sqlite database file.",
    )
    parser.add_argument(
        "--keep-database",
        default=DEFAULT_KEEP_DATABASE,
        help="Database name to retain in audit log filtering.",
    )
    parser.add_argument(
        "--keep-user",
        action="append",
        default=list(DEFAULT_KEEP_USERNAMES),
        help="Username(s) to keep even if not otherwise referenced.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply deletions. Without this flag, script runs in dry-run mode.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    db_path = Path(args.db_path).expanduser()
    if not db_path.is_absolute():
        db_path = (MODULE_B_DIR / db_path).resolve()

    if not db_path.exists():
        print(f"Database file not found: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")

        required_tables = (
            "members",
            "sessions",
            "audit_logs",
            "project_databases",
            "project_tables",
            "project_records",
            "member_credentials",
            "member_group_mappings",
        )
        missing = [table for table in required_tables if not _table_exists(conn, table)]
        if missing:
            print("Missing required tables: " + ", ".join(missing))
            return 1

        before_members = _count_rows(conn, "members")
        before_sessions = _count_rows(conn, "sessions")
        before_audits = _count_rows(conn, "audit_logs")

        audit_rows = conn.execute(
            "SELECT id, actor_id, details FROM audit_logs ORDER BY id"
        ).fetchall()

        kept_audit_ids: list[int] = []
        actor_ids_in_kept_logs: set[int] = set()

        for row in audit_rows:
            if _details_mentions_database(row["details"], args.keep_database):
                kept_audit_ids.append(int(row["id"]))
                if row["actor_id"] is not None:
                    actor_ids_in_kept_logs.add(int(row["actor_id"]))

        keep_member_ids = _member_ids_by_usernames(conn, args.keep_user)
        keep_member_ids.update(actor_ids_in_kept_logs)
        keep_member_ids.update(_member_ids_referenced_by_catalog(conn))

        all_member_ids = {
            int(row[0])
            for row in conn.execute("SELECT id FROM members").fetchall()
        }
        removable_member_ids = sorted(all_member_ids - keep_member_ids)

        print(f"Target file: {db_path}")
        print(f"Keep database for audit filtering: {args.keep_database}")
        print(f"Requested keep users: {', '.join(args.keep_user)}")
        print(f"Audit rows before: {before_audits}")
        print(f"Audit rows kept: {len(kept_audit_ids)}")
        print(f"Audit rows to delete: {before_audits - len(kept_audit_ids)}")
        print(f"Members before: {before_members}")
        print(f"Members to delete: {len(removable_member_ids)}")
        print(f"Sessions before: {before_sessions}")

        if removable_member_ids:
            sample_usernames = conn.execute(
                f"SELECT username FROM members WHERE id IN ({_placeholder_block(min(15, len(removable_member_ids)))}) ORDER BY id",
                removable_member_ids[:15],
            ).fetchall()
            preview = ", ".join(row[0] for row in sample_usernames)
            if len(removable_member_ids) > 15:
                preview += ", ..."
            print(f"Member removal preview: {preview}")

        if not args.execute:
            print("Dry-run complete. Re-run with --execute to apply changes.")
            return 0

        with conn:
            if kept_audit_ids:
                placeholders = _placeholder_block(len(kept_audit_ids))
                conn.execute(
                    f"DELETE FROM audit_logs WHERE id NOT IN ({placeholders})",
                    kept_audit_ids,
                )
            else:
                conn.execute("DELETE FROM audit_logs")

            if removable_member_ids:
                placeholders = _placeholder_block(len(removable_member_ids))
                conn.execute(
                    f"DELETE FROM sessions WHERE member_id IN ({placeholders})",
                    removable_member_ids,
                )
                conn.execute(
                    f"DELETE FROM members WHERE id IN ({placeholders})",
                    removable_member_ids,
                )

            # Hard cleanup in case legacy rows bypassed FK cascades.
            conn.execute(
                "DELETE FROM member_credentials WHERE member_id NOT IN (SELECT id FROM members)"
            )
            conn.execute(
                "DELETE FROM member_group_mappings WHERE member_id NOT IN (SELECT id FROM members)"
            )
            conn.execute(
                "DELETE FROM sessions WHERE member_id NOT IN (SELECT id FROM members)"
            )

        after_members = _count_rows(conn, "members")
        after_sessions = _count_rows(conn, "sessions")
        after_audits = _count_rows(conn, "audit_logs")

        print("Cleanup applied successfully.")
        print(f"audit_logs: {before_audits} -> {after_audits}")
        print(f"members:    {before_members} -> {after_members}")
        print(f"sessions:   {before_sessions} -> {after_sessions}")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
