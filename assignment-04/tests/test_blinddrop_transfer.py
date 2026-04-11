"""Integration tests for the Blind Drop file transfer flow.

Validates:
  1. Upload a file → 201 + download code returned
  2. Status check → valid=true with correct file info
  3. Download → file content matches original
  4. Re-download same code → fails (already consumed)
  5. Physical file deleted from disk after download
  6. AuditTrail and DownloadLog entries created on the correct shard
  7. Upload oversized file → 413
  8. Rate limiting → 429 after too many uploads
"""

import io
import json
import os
import sys
import unittest
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
MODULE_B_ROOT = TESTS_ROOT.parent
RESULTS_ROOT = MODULE_B_ROOT / "test_results"
BACKEND_ROOT = MODULE_B_ROOT / "db_management_system"
UPLOADS_DIR = BACKEND_ROOT / "uploads"

os.environ.setdefault("BLINDDROP_DB_PATH", str(RESULTS_ROOT / "module_b_test_runtime.sqlite3"))

if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import app
from shard_manager import NUM_SHARDS, ShardManager, get_shard_id


class TestBlindDropTransfer(unittest.TestCase):
    """End-to-end file transfer integration tests."""

    TEST_FILE_CONTENT = b"Hello, Blind Drop! This is a test file."
    TEST_FILE_NAME = "testfile.txt"

    @classmethod
    def setUpClass(cls):
        """Clear rate limit records so transfer tests can upload freely."""
        import sqlite3
        db_path = os.environ.get("BLINDDROP_DB_PATH", str(BACKEND_ROOT / "module_b.sqlite3"))
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute("DELETE FROM RateLimitLog WHERE eventType = 'public_upload'")
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _upload_file(self, client, content=None, filename=None, expires_in_minutes=30):
        """Upload a file and return (response, json_data)."""
        content = content or self.TEST_FILE_CONTENT
        filename = filename or self.TEST_FILE_NAME
        data = {
            "file": (io.BytesIO(content), filename),
            "expires_in_minutes": str(expires_in_minutes),
        }
        resp = client.post(
            "/api/public/upload",
            data=data,
            content_type="multipart/form-data",
        )
        return resp, resp.get_json(silent=True)

    # ------------------------------------------------------------------
    # test_01: upload returns 201 with download code
    # ------------------------------------------------------------------

    def test_01_upload_returns_code(self):
        with app.test_client() as client:
            resp, data = self._upload_file(client)
        self.assertEqual(resp.status_code, 201, data)
        self.assertIn("download_code", data)
        self.assertEqual(len(data["download_code"]), 6)
        self.assertIn("expires_at", data)
        self.assertIn("file_name", data)
        self.assertIn("file_size", data)
        self.assertEqual(data["file_name"], self.TEST_FILE_NAME)
        self.assertEqual(data["file_size"], len(self.TEST_FILE_CONTENT))

    # ------------------------------------------------------------------
    # test_02: status check returns valid info
    # ------------------------------------------------------------------

    def test_02_status_check_valid(self):
        with app.test_client() as client:
            _, upload_data = self._upload_file(client)
            code = upload_data["download_code"]
            resp = client.get(f"/api/public/status/{code}")
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(data["valid"])
        self.assertEqual(data["file_name"], self.TEST_FILE_NAME)
        self.assertEqual(data["file_size"], len(self.TEST_FILE_CONTENT))
        self.assertIn("expires_at", data)

    # ------------------------------------------------------------------
    # test_03: download returns correct file content
    # ------------------------------------------------------------------

    def test_03_download_content_matches(self):
        with app.test_client() as client:
            _, upload_data = self._upload_file(client)
            code = upload_data["download_code"]
            resp = client.get(f"/api/public/download/{code}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, self.TEST_FILE_CONTENT)

    # ------------------------------------------------------------------
    # test_04: re-download same code fails (consumed)
    # ------------------------------------------------------------------

    def test_04_redownload_fails(self):
        with app.test_client() as client:
            _, upload_data = self._upload_file(client)
            code = upload_data["download_code"]
            # First download succeeds.
            resp1 = client.get(f"/api/public/download/{code}")
            self.assertEqual(resp1.status_code, 200)
            # Second download should fail.
            resp2 = client.get(f"/api/public/download/{code}")
            self.assertIn(resp2.status_code, [404, 410])

    # ------------------------------------------------------------------
    # test_05: physical file deleted after download
    # ------------------------------------------------------------------

    def test_05_file_deleted_after_download(self):
        with app.test_client() as client:
            _, upload_data = self._upload_file(client)
            code = upload_data["download_code"]

            # Find the storage path from the shard before downloading.
            sm = ShardManager()
            storage_path = None
            for shard_id in range(NUM_SHARDS):
                conn = sm.get_shard_conn(shard_id)
                row = conn.execute(
                    "SELECT tokenValue, sessionID FROM OneTimeToken WHERE tokenValue = ?",
                    (code,),
                ).fetchone()
                if row:
                    frow = conn.execute(
                        "SELECT storagePath FROM FileMetadata WHERE sessionID = ?",
                        (row["sessionID"],),
                    ).fetchone()
                    if frow:
                        storage_path = frow["storagePath"]
                    break
            sm.close_all()

            self.assertIsNotNone(storage_path, "Could not find storage path on any shard")
            self.assertTrue(Path(storage_path).exists(), "File should exist before download")

            # Download the file.
            resp = client.get(f"/api/public/download/{code}")
            self.assertEqual(resp.status_code, 200)

            # File should be deleted.
            self.assertFalse(Path(storage_path).exists(), "File should be deleted after download")

    # ------------------------------------------------------------------
    # test_06: AuditTrail and DownloadLog entries created
    # ------------------------------------------------------------------

    def test_06_audit_and_download_log_created(self):
        with app.test_client() as client:
            _, upload_data = self._upload_file(client)
            code = upload_data["download_code"]

            # Download.
            resp = client.get(f"/api/public/download/{code}")
            self.assertEqual(resp.status_code, 200)

        # Find the session across shards and check logs.
        sm = ShardManager()
        found_download_log = False
        found_audit = False
        for shard_id in range(NUM_SHARDS):
            conn = sm.get_shard_conn(shard_id)
            token_row = conn.execute(
                "SELECT sessionID, tokenID FROM OneTimeToken WHERE tokenValue = ?",
                (code,),
            ).fetchone()
            if token_row:
                # Check DownloadLog for this token.
                dl_row = conn.execute(
                    "SELECT * FROM DownloadLog WHERE tokenID = ?",
                    (token_row["tokenID"],),
                ).fetchone()
                if dl_row:
                    found_download_log = True

                # Check AuditTrail for file_download action.
                audit_rows = conn.execute(
                    "SELECT * FROM AuditTrail WHERE sessionID = ? AND action = 'file_download'",
                    (token_row["sessionID"],),
                ).fetchall()
                if audit_rows:
                    found_audit = True
                break
        sm.close_all()
        self.assertTrue(found_download_log, "DownloadLog entry should exist after download")
        self.assertTrue(found_audit, "AuditTrail entry should exist after download")

    # ------------------------------------------------------------------
    # test_07: oversized file returns 413
    # ------------------------------------------------------------------

    def test_07_oversized_file_rejected(self):
        # Patch the MAX_FILE_SIZE in the routes module (where it's actually used)
        # since it's imported as a name binding, not a reference to file_handler.
        import api.routes as routes_mod
        original = routes_mod.MAX_FILE_SIZE
        try:
            routes_mod.MAX_FILE_SIZE = 10  # 10 bytes limit
            with app.test_client() as client:
                resp, data = self._upload_file(
                    client,
                    content=b"A" * 20,  # 20 bytes > 10 byte limit
                    filename="big.bin",
                )
            self.assertEqual(resp.status_code, 413, data)
        finally:
            routes_mod.MAX_FILE_SIZE = original

    # ------------------------------------------------------------------
    # test_08: rate limiting returns 429
    # ------------------------------------------------------------------

    def test_08_rate_limit(self):
        # Temporarily lower the rate limit for testing.
        with app.test_client() as client:
            # Upload many times from the same IP (test client uses 127.0.0.1).
            last_status = None
            for i in range(25):
                resp, data = self._upload_file(
                    client,
                    content=f"file-{i}".encode(),
                    filename=f"rl-test-{i}.txt",
                    expires_in_minutes=30,
                )
                last_status = resp.status_code
                if last_status == 429:
                    break

            # We should have hit the rate limit at some point.
            self.assertEqual(last_status, 429, "Rate limiting should kick in")


if __name__ == "__main__":
    unittest.main()
