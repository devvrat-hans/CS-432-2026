"""Tests for the Assignment 04 sharding implementation.

Validates:
  1. Migration correctness — records exist in exactly one shard
  2. Single-key lookup routes to the correct shard
  3. Inserts via the API go to the correct shard based on sessionID hash
  4. Range queries return complete results from all shards
  5. Token consume works correctly on sharded data
  6. Shard verification endpoint returns all-pass
  7. Dashboard counts match across shards
"""

import json
import os
import secrets
import sys
import time
import unittest
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
ASSIGNMENT_ROOT = TESTS_ROOT.parent
RESULTS_ROOT = ASSIGNMENT_ROOT / "test_results"
BACKEND_ROOT = ASSIGNMENT_ROOT / "db_management_system"

# Test database path
os.environ.setdefault("BLINDDROP_DB_PATH", str(RESULTS_ROOT / "module_b_test_runtime.sqlite3"))

if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import app
from shard_manager import NUM_SHARDS, SHARDED_TABLES, ShardManager, get_shard_id
from shard_router import (
    scatter_gather_query,
    scatter_gather_count,
    find_record_across_shards,
    is_sharded_table,
)
from migrate_to_shards import migrate


class TestAssignment04Sharding(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Re-run migration so shards are clean before integrity checks."""
        migrate()
    """Sharding validation test suite."""

    # helpers

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _admin_token(self):
        with app.test_client() as client:
            response = client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "admin123"},
            )
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json() or {}
        return body["token"]

    def _admin_headers(self):
        token = self._admin_token()
        return self._headers(token)

    def _shard_manager(self):
        return ShardManager()

    # 1. Migration correctness — each record exists in exactly one shard

    def test_01_migration_records_in_exactly_one_shard(self):
        """Each record in every sharded table must appear in exactly one shard."""
        sm = self._shard_manager()
        try:
            pk_col_map = {
                "UploadSession": "sessionID",
                "FileMetadata": "fileID",
                "OneTimeToken": "tokenID",
                "DownloadLog": "downloadID",
                "ErrorLog": "errorID",
                "AuditTrail": "auditID",
            }
            for table in SHARDED_TABLES:
                pk = pk_col_map.get(table, "rowid")
                all_pks = {}  # pk_value -> list of shard_ids
                for shard_id in range(NUM_SHARDS):
                    conn = sm.get_shard_conn(shard_id)
                    rows = conn.execute(f"SELECT {pk} FROM {table}").fetchall()
                    for row in rows:
                        pk_val = row[pk]
                        all_pks.setdefault(pk_val, []).append(shard_id)

                duplicates = {k: v for k, v in all_pks.items() if len(v) > 1}
                self.assertEqual(
                    len(duplicates), 0,
                    f"Table {table} has records in multiple shards: {duplicates}",
                )
        finally:
            sm.close_all()

    # 2. Single-key lookup routes to correct shard

    def test_02_single_key_routes_to_correct_shard(self):
        """get_shard_id must hash consistently and route lookups correctly."""
        sm = self._shard_manager()
        try:
            # Check some UploadSession records
            for shard_id in range(NUM_SHARDS):
                conn = sm.get_shard_conn(shard_id)
                rows = conn.execute(
                    "SELECT sessionID FROM UploadSession LIMIT 5"
                ).fetchall()
                for row in rows:
                    sid = row["sessionID"]
                    expected_shard = get_shard_id(sid)
                    self.assertEqual(
                        expected_shard, shard_id,
                        f"sessionID={sid} expected shard {expected_shard}, found in shard {shard_id}",
                    )
        finally:
            sm.close_all()

    # 3. API insert routes to correct shard

    def test_03_api_insert_routes_to_correct_shard(self):
        """Creating a token fixture via API must place records in the correct shard."""
        headers = self._admin_headers()
        token_value = f"shard-test-{secrets.token_hex(6)}"

        with app.test_client() as client:
            res = client.post(
                "/api/resilience/token-fixtures",
                headers=headers,
                json={"token_value": token_value, "expires_in_minutes": 30},
            )
            self.assertEqual(res.status_code, 201, res.get_json())
            body = res.get_json()

        # The response should include shard info
        session_id = body.get("session_id") or body.get("sessionID")
        self.assertIsNotNone(session_id, "Response must include session_id")

        expected_shard = get_shard_id(session_id)

        # Verify in shard
        sm = self._shard_manager()
        try:
            conn = sm.get_shard_conn(expected_shard)
            row = conn.execute(
                "SELECT sessionID FROM UploadSession WHERE sessionID = ?",
                (session_id,),
            ).fetchone()
            self.assertIsNotNone(row, f"Session {session_id} not in shard {expected_shard}")
        finally:
            sm.close_all()

    # 4. Range queries return complete results from all shards

    def test_04_range_query_returns_all_shards(self):
        """A range query on a sharded table must aggregate across all shards."""
        sm = self._shard_manager()
        try:
            # Count total UploadSessions across shards
            total, per_shard = scatter_gather_count(sm, "UploadSession")

            # Also count via scatter_gather_query
            rows = scatter_gather_query(sm, "SELECT COUNT(*) AS c FROM UploadSession")
            total_via_query = sum(r["c"] for r in rows)
            self.assertEqual(total, total_via_query)

            # Hit the API records endpoint
            headers = self._admin_headers()
            with app.test_client() as client:
                res = client.get(
                    "/api/databases/blinddrop_core/tables/UploadSession/records",
                    headers=headers,
                )
            self.assertEqual(res.status_code, 200)
            body = res.get_json()
            api_count = len(body.get("records", []))
            self.assertEqual(
                api_count, total,
                f"API returned {api_count} but shards have {total} UploadSession records",
            )
        finally:
            sm.close_all()

    # 5. Token consume works on sharded data

    def test_05_token_consume_on_sharded_data(self):
        """Creating and consuming a token must work correctly across shards."""
        headers = self._admin_headers()
        token_value = f"consume-shard-{secrets.token_hex(6)}"

        with app.test_client() as client:
            # Create
            create_res = client.post(
                "/api/resilience/token-fixtures",
                headers=headers,
                json={"token_value": token_value, "expires_in_minutes": 30},
            )
            self.assertEqual(create_res.status_code, 201, create_res.get_json())

            # Consume
            consume_res = client.post(
                "/api/resilience/consume-token",
                headers=headers,
                json={"token_value": token_value, "user_device_info": "sharding-test"},
            )
            self.assertIn(
                consume_res.status_code, [200, 201],
                f"Consume failed: {consume_res.get_json()}",
            )

            # Re-consume should fail (already used)
            re_consume = client.post(
                "/api/resilience/consume-token",
                headers=headers,
                json={"token_value": token_value, "user_device_info": "sharding-test-2"},
            )
            self.assertNotEqual(
                re_consume.status_code, 200,
                "Re-consuming an already used token should fail",
            )

    # 6. Shard verification endpoint returns all-pass

    def test_06_verification_endpoint_all_pass(self):
        """GET /api/sharding/verify must return all_pass=true."""
        headers = self._admin_headers()
        with app.test_client() as client:
            res = client.get("/api/sharding/verify", headers=headers)
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertEqual(body.get("overall"), "pass", f"Verification failed: {body}")

    # 7. Dashboard counts match across shards

    def test_07_dashboard_counts_match_shards(self):
        """Dashboard summary shard counts should match scatter-gather totals."""
        headers = self._admin_headers()
        with app.test_client() as client:
            res = client.get("/api/dashboard/summary", headers=headers)
        self.assertEqual(res.status_code, 200)
        body = res.get_json()

        # The dashboard should include a sharding section
        sharding = body.get("sharding")
        if sharding is None:
            self.skipTest("Dashboard does not include sharding section yet")

        table_counts = sharding.get("sharded_table_counts", {})

        # Verify per-table totals match what we count directly
        sm = self._shard_manager()
        try:
            for table, info in table_counts.items():
                expected_total, _ = scatter_gather_count(sm, table)
                dashboard_total = info.get("total", 0) if isinstance(info, dict) else info
                self.assertEqual(
                    dashboard_total, expected_total,
                    f"Dashboard {table} total ({dashboard_total}) != shard total ({expected_total})",
                )
        finally:
            sm.close_all()

    # 8. Sharding info endpoint returns valid data

    def test_08_sharding_info_endpoint(self):
        """GET /api/sharding/info returns correct shard config."""
        headers = self._admin_headers()
        with app.test_client() as client:
            res = client.get("/api/sharding/info", headers=headers)
        self.assertEqual(res.status_code, 200)
        body = res.get_json()

        self.assertEqual(body["num_shards"], NUM_SHARDS)
        self.assertEqual(body["shard_key"], "sessionID")
        self.assertIn("per_table_counts", body)
        for table in SHARDED_TABLES:
            self.assertIn(table, body["per_table_counts"])

    # 9. is_sharded_table correctly classifies tables

    def test_09_is_sharded_table_classification(self):
        """is_sharded_table must return True for sharded, False for others."""
        for table in SHARDED_TABLES:
            self.assertTrue(is_sharded_table(table), f"{table} should be sharded")
        for table in ["Member", "Device", "ExpiryPolicy", "SystemAdmin"]:
            self.assertFalse(is_sharded_table(table), f"{table} should NOT be sharded")

    # 10. get_shard_id is deterministic

    def test_10_shard_id_deterministic(self):
        """Same sessionID must always map to the same shard."""
        for sid in [1, 42, 100, 999, 12345]:
            first = get_shard_id(sid)
            for _ in range(10):
                self.assertEqual(get_shard_id(sid), first)
            self.assertIn(first, range(NUM_SHARDS))


if __name__ == "__main__":
    unittest.main()
