"""Expiry tests for the Blind Drop file transfer flow.

Validates:
  1. Upload with very short expiry → cleanup marks it EXPIRED and deletes file
  2. Downloading an expired code returns an error
  3. ErrorLog entries created for expired files
"""

import io
import os
import sys
import time
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
ASSIGNMENT_ROOT = TESTS_ROOT.parent
RESULTS_ROOT = ASSIGNMENT_ROOT / "test_results"
BACKEND_ROOT = ASSIGNMENT_ROOT / "db_management_system"

os.environ.setdefault("BLINDDROP_DB_PATH", str(RESULTS_ROOT / "module_b_test_runtime.sqlite3"))

if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import app
from shard_manager import NUM_SHARDS, ShardManager
from cleanup import cleanup_expired_sessions


class TestBlindDropExpiry(unittest.TestCase):
    """Expiry and cleanup integration tests."""

    @classmethod
    def setUpClass(cls):
        """Clear rate limit records so expiry tests can upload freely."""
        import sqlite3
        db_path = os.environ.get("BLINDDROP_DB_PATH", str(BACKEND_ROOT / "module_b.sqlite3"))
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute("DELETE FROM RateLimitLog WHERE eventType = 'public_upload'")
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _upload_file(self, client, expires_in_minutes=30):
        data = {
            "file": (io.BytesIO(b"expiry-test-content"), "expiry_test.txt"),
            "expires_in_minutes": str(expires_in_minutes),
        }
        resp = client.post(
            "/api/public/upload",
            data=data,
            content_type="multipart/form-data",
        )
        return resp, resp.get_json(silent=True)

    def _find_session_on_shard(self, code):
        """Find the shard, sessionID, and storage path for a given code."""
        sm = ShardManager()
        for shard_id in range(NUM_SHARDS):
            conn = sm.get_shard_conn(shard_id)
            token_row = conn.execute(
                "SELECT sessionID FROM OneTimeToken WHERE tokenValue = ?",
                (code,),
            ).fetchone()
            if token_row:
                session_id = token_row["sessionID"]
                file_row = conn.execute(
                    "SELECT storagePath FROM FileMetadata WHERE sessionID = ?",
                    (session_id,),
                ).fetchone()
                storage_path = file_row["storagePath"] if file_row else None
                sm.close_all()
                return shard_id, session_id, storage_path
        sm.close_all()
        return None, None, None

    def _force_expire_session(self, code):
        """Manually set the session's expiryTimestamp to the past."""
        sm = ShardManager()
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        for shard_id in range(NUM_SHARDS):
            conn = sm.get_shard_conn(shard_id)
            token_row = conn.execute(
                "SELECT sessionID FROM OneTimeToken WHERE tokenValue = ?",
                (code,),
            ).fetchone()
            if token_row:
                session_id = token_row["sessionID"]
                conn.execute(
                    "UPDATE UploadSession SET expiryTimestamp = ? WHERE sessionID = ?",
                    (past, session_id),
                )
                conn.execute(
                    "UPDATE OneTimeToken SET expiryAt = ? WHERE tokenValue = ?",
                    (past, code),
                )
                conn.commit()
                break
        sm.close_all()

    # ------------------------------------------------------------------
    # test_01: cleanup marks expired sessions and deletes files
    # ------------------------------------------------------------------

    def test_01_cleanup_marks_expired_and_deletes_file(self):
        with app.test_client() as client:
            resp, data = self._upload_file(client, expires_in_minutes=30)
        self.assertEqual(resp.status_code, 201, data)
        code = data["download_code"]

        # Verify file exists on disk.
        _, session_id, storage_path = self._find_session_on_shard(code)
        self.assertIsNotNone(storage_path, "Storage path should exist")
        self.assertTrue(Path(storage_path).exists(), "File should exist on disk")

        # Force-expire the session.
        self._force_expire_session(code)

        # Run cleanup.
        cleaned = cleanup_expired_sessions()
        self.assertGreaterEqual(cleaned, 1, "At least one session should be cleaned")

        # File should be deleted.
        self.assertFalse(
            Path(storage_path).exists(),
            "File should be deleted after cleanup",
        )

        # Session should be marked EXPIRED.
        sm = ShardManager()
        for shard_id in range(NUM_SHARDS):
            conn = sm.get_shard_conn(shard_id)
            row = conn.execute(
                "SELECT status FROM UploadSession WHERE sessionID = ?",
                (session_id,),
            ).fetchone()
            if row:
                self.assertEqual(row["status"], "EXPIRED")
                break
        sm.close_all()

    # ------------------------------------------------------------------
    # test_02: download expired code returns error
    # ------------------------------------------------------------------

    def test_02_download_expired_code_fails(self):
        with app.test_client() as client:
            resp, data = self._upload_file(client, expires_in_minutes=30)
        self.assertEqual(resp.status_code, 201)
        code = data["download_code"]

        # Force-expire the session and token.
        self._force_expire_session(code)

        # Attempt download — should fail.
        with app.test_client() as client:
            resp = client.get(f"/api/public/download/{code}")
        self.assertIn(resp.status_code, [404, 410], resp.get_json(silent=True))

    # ------------------------------------------------------------------
    # test_03: ErrorLog entries created for expired files
    # ------------------------------------------------------------------

    def test_03_error_log_created_for_expiry(self):
        with app.test_client() as client:
            resp, data = self._upload_file(client, expires_in_minutes=30)
        self.assertEqual(resp.status_code, 201)
        code = data["download_code"]

        _, session_id, _ = self._find_session_on_shard(code)

        # Force-expire and run cleanup.
        self._force_expire_session(code)
        cleanup_expired_sessions()

        # Check ErrorLog for the session.
        sm = ShardManager()
        found = False
        for shard_id in range(NUM_SHARDS):
            conn = sm.get_shard_conn(shard_id)
            rows = conn.execute(
                "SELECT * FROM ErrorLog WHERE sessionID = ?",
                (session_id,),
            ).fetchall()
            if rows:
                found = True
                # Verify the error message mentions expiry.
                self.assertTrue(
                    any("expired" in (r["errorMessage"] or "").lower() for r in rows),
                    "ErrorLog should mention expiry",
                )
                break
        sm.close_all()
        self.assertTrue(found, "ErrorLog entry should exist for expired session")


if __name__ == "__main__":
    unittest.main()
