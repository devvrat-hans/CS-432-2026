"""Background cleanup module for expired file-transfer sessions.

Periodically scans all shards for ACTIVE UploadSessions whose
expiryTimestamp is past the current time, deletes their physical files
from disk, marks them EXPIRED, and logs the event.
"""

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from shard_manager import NUM_SHARDS, ShardManager
from file_handler import delete_file


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _next_error_id(sm):
    """Get the next ErrorLog ID across all shards."""
    max_id = 0
    for shard_id in range(NUM_SHARDS):
        try:
            conn = sm.get_shard_conn(shard_id)
            row = conn.execute(
                "SELECT COALESCE(MAX(errorID), 0) AS max_id FROM ErrorLog"
            ).fetchone()
            max_id = max(max_id, int(row["max_id"]))
        except Exception:
            pass
    return max_id + 1


def _next_audit_id(sm):
    """Get the next AuditTrail ID across all shards."""
    max_id = 0
    for shard_id in range(NUM_SHARDS):
        try:
            conn = sm.get_shard_conn(shard_id)
            row = conn.execute(
                "SELECT COALESCE(MAX(auditID), 0) AS max_id FROM AuditTrail"
            ).fetchone()
            max_id = max(max_id, int(row["max_id"]))
        except Exception:
            pass
    return max_id + 1


def cleanup_expired_sessions():
    """Scan all shards for expired ACTIVE sessions and clean them up.

    For each expired session:
    - Delete the physical file from disk (if it exists).
    - Mark the UploadSession as EXPIRED.
    - Mark any ACTIVE OneTimeTokens as EXPIRED.
    - Write an ErrorLog entry noting the expiry.
    - Write an AuditTrail entry for the expiry.
    """
    sm = ShardManager()
    now_iso = _now_iso()
    cleaned = 0

    try:
        for shard_id in range(NUM_SHARDS):
            conn = sm.get_shard_conn(shard_id)

            # Find all ACTIVE sessions that have expired.
            expired_rows = conn.execute(
                """
                SELECT sessionID, expiryTimestamp
                FROM UploadSession
                WHERE status = 'ACTIVE' AND expiryTimestamp < ?
                """,
                (now_iso,),
            ).fetchall()

            for row in expired_rows:
                session_id = row["sessionID"]

                # Look up file metadata to delete the physical file.
                file_row = conn.execute(
                    "SELECT fileID, storagePath, fileName FROM FileMetadata WHERE sessionID = ? LIMIT 1",
                    (session_id,),
                ).fetchone()

                if file_row and file_row["storagePath"]:
                    delete_file(file_row["storagePath"])
                    # Clear the storage path.
                    conn.execute(
                        "UPDATE FileMetadata SET storagePath = '' WHERE fileID = ?",
                        (file_row["fileID"],),
                    )

                # Mark session as EXPIRED.
                conn.execute(
                    "UPDATE UploadSession SET status = 'EXPIRED' WHERE sessionID = ?",
                    (session_id,),
                )

                # Mark any ACTIVE tokens for this session as EXPIRED.
                conn.execute(
                    "UPDATE OneTimeToken SET status = 'EXPIRED' WHERE sessionID = ? AND status = 'ACTIVE'",
                    (session_id,),
                )

                # Write ErrorLog entry.
                error_id = _next_error_id(sm)
                conn.execute(
                    """
                    INSERT INTO ErrorLog (errorID, sessionID, errorMessage, timestamp)
                    VALUES (?, ?, ?, ?)
                    """,
                    (error_id, session_id,
                     f"Session expired. File deleted during cleanup.",
                     now_iso),
                )

                # Write AuditTrail entry.
                audit_id = _next_audit_id(sm)
                conn.execute(
                    """
                    INSERT INTO AuditTrail (auditID, sessionID, action, timestamp)
                    VALUES (?, ?, ?, ?)
                    """,
                    (audit_id, session_id, "file_expired", now_iso),
                )

                conn.commit()
                cleaned += 1

    except Exception as exc:
        # Silently absorb errors — this is a background job.
        pass
    finally:
        sm.close_all()

    return cleaned


def start_cleanup_daemon(interval_seconds=60):
    """Start a background daemon thread that runs cleanup on a loop.

    Args:
        interval_seconds: How often to run the cleanup (default 60s).
    """
    def _loop():
        while True:
            time.sleep(interval_seconds)
            try:
                cleanup_expired_sessions()
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True, name="cleanup-daemon")
    t.start()
    return t
