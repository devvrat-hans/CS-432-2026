import concurrent.futures
import secrets
import sqlite3

try:
    from test_module_b_base import DB_PATH, LoggedModuleBTestCase, MODULE_B_ROOT, app
except ModuleNotFoundError:
    from assignment03.Module_B.tests.test_module_b_base import DB_PATH, LoggedModuleBTestCase, MODULE_B_ROOT, app


class TestModuleBConcurrentUsage(LoggedModuleBTestCase):
    RESULTS_PATH = MODULE_B_ROOT / "test_results" / "test_results_concurrent_usage.txt"

    def test_parallel_unique_inserts_preserve_count(self):
        token = self._admin_token()
        db_name = f"cu_db_{secrets.token_hex(4)}"
        table_name = f"cu_table_{secrets.token_hex(4)}"

        with app.test_client() as client:
            self.assertEqual(
                client.post("/api/databases", headers=self._headers(token), json={"name": db_name}).status_code,
                201,
            )
            self.assertEqual(
                client.post(
                    f"/api/databases/{db_name}/tables",
                    headers=self._headers(token),
                    json={"name": table_name, "schema": ["id", "value"], "search_key": "id"},
                ).status_code,
                201,
            )

        request_count = 300
        worker_count = 20

        def insert_worker(index):
            payload = {"id": str(index), "value": f"v-{index}"}
            with app.test_client() as client:
                response = client.post(
                    f"/api/databases/{db_name}/tables/{table_name}/records",
                    headers=self._headers(token),
                    json=payload,
                )
            return response.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            statuses = list(executor.map(insert_worker, range(1, request_count + 1)))

        self.assertEqual(sum(1 for status in statuses if status == 201), request_count)

        with app.test_client() as client:
            records_res = client.get(
                f"/api/databases/{db_name}/tables/{table_name}/records",
                headers=self._headers(token),
            )
        body = records_res.get_json() or {}
        self.assertEqual(records_res.status_code, 200)
        self.assertEqual(body.get("count"), request_count)

    def test_parallel_reads_during_writes_remain_consistent(self):
        token = self._admin_token()
        db_name = f"readwrite_db_{secrets.token_hex(4)}"
        table_name = f"readwrite_table_{secrets.token_hex(4)}"

        with app.test_client() as client:
            self.assertEqual(
                client.post("/api/databases", headers=self._headers(token), json={"name": db_name}).status_code,
                201,
            )
            self.assertEqual(
                client.post(
                    f"/api/databases/{db_name}/tables",
                    headers=self._headers(token),
                    json={"name": table_name, "schema": ["id", "value"], "search_key": "id"},
                ).status_code,
                201,
            )

        write_count = 150
        reader_samples = 40

        def writer(index):
            with app.test_client() as client:
                response = client.post(
                    f"/api/databases/{db_name}/tables/{table_name}/records",
                    headers=self._headers(token),
                    json={"id": str(index), "value": f"writer-{index}"},
                )
            return response.status_code

        def reader(_):
            with app.test_client() as client:
                response = client.get(
                    f"/api/databases/{db_name}/tables/{table_name}/records",
                    headers=self._headers(token),
                )
            body = response.get_json() or {}
            return response.status_code, body.get("count", 0)

        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
            write_futures = [executor.submit(writer, index) for index in range(1, write_count + 1)]
            read_futures = [executor.submit(reader, sample) for sample in range(reader_samples)]

            write_statuses = [future.result() for future in write_futures]
            read_results = [future.result() for future in read_futures]

        self.assertTrue(all(status == 201 for status in write_statuses))
        self.assertTrue(all(status == 200 for status, _ in read_results))

        with app.test_client() as client:
            final_res = client.get(
                f"/api/databases/{db_name}/tables/{table_name}/records",
                headers=self._headers(token),
            )
        final_body = final_res.get_json() or {}
        self.assertEqual(final_body.get("count"), write_count)

    def test_parallel_database_create_duplicate_name_safe(self):
        token = self._admin_token()
        db_name = f"dup_db_{secrets.token_hex(4)}"

        def create_db(_):
            with app.test_client() as client:
                response = client.post(
                    "/api/databases",
                    headers=self._headers(token),
                    json={"name": db_name},
                )
            return response.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=18) as executor:
            statuses = list(executor.map(create_db, range(18)))

        self.assertEqual(sum(1 for status in statuses if status == 201), 1)
        self.assertEqual(sum(1 for status in statuses if status == 400), 17)

    def test_parallel_mixed_create_update_delete_same_record_invariants(self):
        token = self._admin_token()
        db_name = f"mixed_db_{secrets.token_hex(4)}"
        table_name = f"mixed_table_{secrets.token_hex(4)}"
        record_id = "shared-record"

        with app.test_client() as client:
            self.assertEqual(
                client.post("/api/databases", headers=self._headers(token), json={"name": db_name}).status_code,
                201,
            )
            self.assertEqual(
                client.post(
                    f"/api/databases/{db_name}/tables",
                    headers=self._headers(token),
                    json={"name": table_name, "schema": ["id", "value"], "search_key": "id"},
                ).status_code,
                201,
            )
            self.assertEqual(
                client.post(
                    f"/api/databases/{db_name}/tables/{table_name}/records",
                    headers=self._headers(token),
                    json={"id": record_id, "value": "seed"},
                ).status_code,
                201,
            )

        operation_count = 180
        worker_count = 24

        def worker(index):
            op_code = index % 3
            with app.test_client() as client:
                if op_code == 0:
                    response = client.put(
                        f"/api/databases/{db_name}/tables/{table_name}/records/{record_id}",
                        headers=self._headers(token),
                        json={"value": f"update-{index}"},
                    )
                    return "update", response.status_code

                if op_code == 1:
                    response = client.delete(
                        f"/api/databases/{db_name}/tables/{table_name}/records/{record_id}",
                        headers=self._headers(token),
                    )
                    return "delete", response.status_code

                response = client.post(
                    f"/api/databases/{db_name}/tables/{table_name}/records",
                    headers=self._headers(token),
                    json={"id": record_id, "value": f"create-{index}"},
                )
                return "create", response.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            outcomes = list(executor.map(worker, range(operation_count)))

        allowed_statuses = {
            "update": {200, 404},
            "delete": {200, 404},
            "create": {201, 400},
        }
        for operation, status in outcomes:
            self.assertIn(status, allowed_statuses[operation])

        with app.test_client() as client:
            records_res = client.get(
                f"/api/databases/{db_name}/tables/{table_name}/records",
                headers=self._headers(token),
            )
        body = records_res.get_json() or {}
        records = body.get("records", [])

        self.assertEqual(records_res.status_code, 200)
        self.assertIn(body.get("count"), {0, 1})
        self.assertEqual(len(records), body.get("count"))

        keys = [str(item.get("data", {}).get("id")) for item in records]
        self.assertEqual(len(keys), len(set(keys)))
        if records:
            self.assertEqual(records[0].get("data", {}).get("id"), record_id)

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            counts = conn.execute(
                """
                SELECT COUNT(*) AS total, COUNT(DISTINCT record_key) AS distinct_keys
                FROM project_records
                WHERE database_name = ? AND table_name = ?
                """,
                (db_name, table_name),
            ).fetchone()

        self.assertIsNotNone(counts)
        self.assertEqual(counts["total"], counts["distinct_keys"])
        self.assertIn(counts["total"], {0, 1})

    def test_cross_table_contention_preserves_referential_integrity(self):
        token = self._admin_token()
        initial_tokens = [
            self._create_token_fixture(token, f"cross-init-{index}-{secrets.token_hex(4)}")
            for index in range(40)
        ]
        create_count = 40

        def consume_worker(token_value):
            response = self._consume_token(token, token_value, simulate_failure=False)
            return token_value, response.status_code

        def create_worker(index):
            token_value = f"cross-new-{index}-{secrets.token_hex(4)}"
            with app.test_client() as client:
                response = client.post(
                    "/api/resilience/token-fixtures",
                    headers=self._headers(token),
                    json={"token_value": token_value, "expires_in_minutes": 30},
                )
            return token_value, response.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            consume_futures = [executor.submit(consume_worker, value) for value in initial_tokens]
            create_futures = [executor.submit(create_worker, index) for index in range(create_count)]
            consume_results = [future.result() for future in consume_futures]
            create_results = [future.result() for future in create_futures]

        self.assertTrue(all(status == 200 for _, status in consume_results), consume_results)
        self.assertTrue(all(status in {201, 400} for _, status in create_results), create_results)
        self.assertGreater(sum(1 for _, status in create_results if status == 201), 0)

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row

            orphan_upload_device = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM UploadSession u
                LEFT JOIN Device d ON d.deviceID = u.deviceID
                WHERE d.deviceID IS NULL
                """
            ).fetchone()["count"]

            orphan_upload_policy = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM UploadSession u
                LEFT JOIN ExpiryPolicy p ON p.policyID = u.policyID
                WHERE p.policyID IS NULL
                """
            ).fetchone()["count"]

            orphan_token_session = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM OneTimeToken t
                LEFT JOIN UploadSession u ON u.sessionID = t.sessionID
                WHERE u.sessionID IS NULL
                """
            ).fetchone()["count"]

            orphan_download_token = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM DownloadLog d
                LEFT JOIN OneTimeToken t ON t.tokenID = d.tokenID
                WHERE t.tokenID IS NULL
                """
            ).fetchone()["count"]

            token_counts = conn.execute(
                "SELECT COUNT(*) AS total, COUNT(DISTINCT tokenValue) AS distinct_values FROM OneTimeToken"
            ).fetchone()

            invalid_token_status = conn.execute(
                "SELECT COUNT(*) AS count FROM OneTimeToken WHERE status NOT IN ('ACTIVE', 'USED', 'EXPIRED')"
            ).fetchone()["count"]

            placeholders = ",".join("?" for _ in initial_tokens)
            consumed_rows = conn.execute(
                f"""
                SELECT t.tokenValue, t.status, COUNT(d.downloadID) AS download_count
                FROM OneTimeToken t
                LEFT JOIN DownloadLog d ON d.tokenID = t.tokenID
                WHERE t.tokenValue IN ({placeholders})
                GROUP BY t.tokenID
                """,
                tuple(initial_tokens),
            ).fetchall()

        self.assertEqual(orphan_upload_device, 0)
        self.assertEqual(orphan_upload_policy, 0)
        self.assertEqual(orphan_token_session, 0)
        self.assertEqual(orphan_download_token, 0)
        self.assertEqual(token_counts["total"], token_counts["distinct_values"])
        self.assertEqual(invalid_token_status, 0)
        self.assertEqual(len(consumed_rows), len(initial_tokens))
        self.assertTrue(all(row["status"] == "USED" for row in consumed_rows))
        self.assertTrue(all(row["download_count"] == 1 for row in consumed_rows))


if __name__ == "__main__":
    import unittest

    unittest.main()
