"""Migrate existing data from module_b.sqlite3 into the 3 shard databases.

Usage:
    python3 migrate_to_shards.py          # migrate + verify
    python3 migrate_to_shards.py --verify  # verify only (no migration)
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

# Ensure the package directory is on sys.path so shard_manager can be imported
# regardless of the working directory.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from shard_manager import (
    NUM_SHARDS,
    SHARDED_TABLES,
    ShardManager,
    get_shard_id,
)

MAIN_DB_PATH = _THIS_DIR / "module_b.sqlite3"

# Column lists for each sharded table (order must match the INSERT statements).
TABLE_COLUMNS = {
    "UploadSession": [
        "sessionID", "deviceID", "policyID",
        "uploadTimestamp", "expiryTimestamp", "status",
    ],
    "FileMetadata": [
        "fileID", "sessionID", "fileName",
        "fileSize", "mimeType", "checksum", "storagePath",
    ],
    "OneTimeToken": [
        "tokenID", "sessionID", "tokenValue",
        "createdAt", "expiryAt", "status",
    ],
    "DownloadLog": [
        "downloadID", "tokenID", "downloadTime", "userDeviceInfo",
    ],
    "ErrorLog": [
        "errorID", "sessionID", "errorMessage", "timestamp",
    ],
    "AuditTrail": [
        "auditID", "action", "sessionID", "timestamp",
    ],
}

# Tables whose shard is determined indirectly via a FK lookup.
# key = table name, value = (fk_column, parent_table, parent_pk, parent_session_col)
FK_SESSION_LOOKUP = {
    "DownloadLog": ("tokenID", "OneTimeToken", "tokenID", "sessionID"),
}


def _open_main_db():
    conn = sqlite3.connect(str(MAIN_DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_exists(conn, table_name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _build_token_session_map(main_conn):
    """Build a mapping of tokenID -> sessionID for DownloadLog routing."""
    rows = main_conn.execute(
        "SELECT tokenID, sessionID FROM OneTimeToken"
    ).fetchall()
    return {row["tokenID"]: row["sessionID"] for row in rows}


def migrate():
    """Read records from main DB and distribute them across shards."""
    main_conn = _open_main_db()
    sm = ShardManager()
    sm.initialize_shards()

    token_session_map = _build_token_session_map(main_conn)

    stats = {}  # table -> {original: int, per_shard: {0: int, 1: int, 2: int}}

    for table_name in SHARDED_TABLES:
        if not _table_exists(main_conn, table_name):
            print(f"  [skip] {table_name} — table does not exist in main DB")
            continue

        columns = TABLE_COLUMNS[table_name]
        col_list = ", ".join(columns)
        placeholders = ", ".join(["?"] * len(columns))

        rows = main_conn.execute(f"SELECT {col_list} FROM {table_name}").fetchall()
        original_count = len(rows)
        per_shard = {i: 0 for i in range(NUM_SHARDS)}

        # Clear existing data in shards for this table to allow re-runs.
        for shard_id in range(NUM_SHARDS):
            shard_conn = sm.get_shard_conn(shard_id)
            shard_conn.execute("PRAGMA foreign_keys = OFF")
            shard_conn.execute(f"DELETE FROM {table_name}")
            shard_conn.execute("PRAGMA foreign_keys = ON")

        for row in rows:
            record = dict(row)

            # Determine the sessionID used for shard routing.
            if table_name in FK_SESSION_LOOKUP:
                fk_col, _, _, _ = FK_SESSION_LOOKUP[table_name]
                fk_value = record[fk_col]
                session_id = token_session_map.get(fk_value)
                if session_id is None:
                    # Orphan row — put in shard 0 as fallback.
                    session_id = 0
            else:
                session_id = record.get("sessionID", 0)

            shard_id = get_shard_id(session_id)
            shard_conn = sm.get_shard_conn(shard_id)

            values = tuple(record[c] for c in columns)
            shard_conn.execute(
                f"INSERT OR IGNORE INTO {table_name} ({col_list}) VALUES ({placeholders})",
                values,
            )
            per_shard[shard_id] += 1

        # Commit each shard.
        for shard_id in range(NUM_SHARDS):
            sm.get_shard_conn(shard_id).commit()

        stats[table_name] = {"original": original_count, "per_shard": per_shard}
        total_migrated = sum(per_shard.values())
        print(
            f"  {table_name}: {original_count} records → "
            + ", ".join(f"shard_{i}={per_shard[i]}" for i in range(NUM_SHARDS))
            + f" (total={total_migrated})"
        )

    main_conn.close()
    sm.close_all()
    return stats


def verify():
    """Verify that shard data matches the main DB: counts, no duplicates, no loss."""
    main_conn = _open_main_db()
    sm = ShardManager()

    all_ok = True

    for table_name in SHARDED_TABLES:
        if not _table_exists(main_conn, table_name):
            continue

        pk_col = TABLE_COLUMNS[table_name][0]  # First column is always the PK.
        original_count = main_conn.execute(
            f"SELECT COUNT(*) AS c FROM {table_name}"
        ).fetchone()["c"]

        shard_total = 0
        all_pks = []
        per_shard_counts = {}

        for shard_id in range(NUM_SHARDS):
            shard_conn = sm.get_shard_conn(shard_id)
            count = shard_conn.execute(
                f"SELECT COUNT(*) AS c FROM {table_name}"
            ).fetchone()["c"]
            per_shard_counts[shard_id] = count
            shard_total += count

            pks = [
                r[pk_col]
                for r in shard_conn.execute(
                    f"SELECT {pk_col} FROM {table_name}"
                ).fetchall()
            ]
            all_pks.extend(pks)

        # Check 1: Total count matches.
        count_ok = shard_total == original_count
        # Check 2: No duplicates.
        dup_ok = len(all_pks) == len(set(all_pks))

        status = "OK" if (count_ok and dup_ok) else "FAIL"
        if not (count_ok and dup_ok):
            all_ok = False

        dist = ", ".join(f"shard_{i}={per_shard_counts[i]}" for i in range(NUM_SHARDS))
        print(
            f"  [{status}] {table_name}: original={original_count}, "
            f"shard_total={shard_total}, duplicates={'NO' if dup_ok else 'YES'}, "
            f"distribution=[{dist}]"
        )

    main_conn.close()
    sm.close_all()

    if all_ok:
        print("\n  Verification PASSED: all tables correctly sharded, no data loss or duplication.")
    else:
        print("\n  Verification FAILED: see above for details.")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Migrate data to shards")
    parser.add_argument(
        "--verify", action="store_true",
        help="Only run verification, skip migration",
    )
    args = parser.parse_args()

    if args.verify:
        print("=== Shard Verification ===")
        ok = verify()
        sys.exit(0 if ok else 1)
    else:
        print("=== Migrating data to shards ===")
        migrate()
        print("\n=== Verifying migration ===")
        ok = verify()
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
