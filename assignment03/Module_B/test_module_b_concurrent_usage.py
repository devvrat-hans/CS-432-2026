import concurrent.futures
import secrets

from test_module_b_base import LoggedModuleBTestCase, MODULE_B_ROOT, app


class TestModuleBConcurrentUsage(LoggedModuleBTestCase):
    RESULTS_PATH = MODULE_B_ROOT / "test_results_concurrent_usage.txt"

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
            client.post("/api/databases", headers=self._headers(token), json={"name": db_name})
            client.post(
                f"/api/databases/{db_name}/tables",
                headers=self._headers(token),
                json={"name": table_name, "schema": ["id", "value"], "search_key": "id"},
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


if __name__ == "__main__":
    import unittest

    unittest.main()
