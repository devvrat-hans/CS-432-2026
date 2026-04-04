import concurrent.futures
import secrets
import time

from test_module_b_base import LoggedModuleBTestCase, MODULE_B_ROOT, app


class TestModuleBStress(LoggedModuleBTestCase):
    RESULTS_PATH = MODULE_B_ROOT / "test_results_stress.txt"

    def test_high_volume_parallel_insert_stress(self):
        token = self._admin_token()
        db_name = f"stress_db_{secrets.token_hex(4)}"
        table_name = f"stress_table_{secrets.token_hex(4)}"

        with app.test_client() as client:
            client.post("/api/databases", headers=self._headers(token), json={"name": db_name})
            client.post(
                f"/api/databases/{db_name}/tables",
                headers=self._headers(token),
                json={"name": table_name, "schema": ["id", "payload"], "search_key": "id"},
            )

        request_count = 600
        worker_count = 30

        def insert_worker(index):
            with app.test_client() as client:
                response = client.post(
                    f"/api/databases/{db_name}/tables/{table_name}/records",
                    headers=self._headers(token),
                    json={"id": str(index), "payload": f"load-{index}"},
                )
            return response.status_code

        started_at = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            statuses = list(executor.map(insert_worker, range(1, request_count + 1)))
        elapsed = time.perf_counter() - started_at

        self.assertEqual(sum(1 for status in statuses if status == 201), request_count)

        with app.test_client() as client:
            records_response = client.get(
                f"/api/databases/{db_name}/tables/{table_name}/records",
                headers=self._headers(token),
            )
        body = records_response.get_json() or {}
        self.assertEqual(records_response.status_code, 200)
        self.assertEqual(body.get("count"), request_count)

        avg_ms = (elapsed / request_count) * 1000
        self.assertLess(avg_ms, 250)

    def test_many_unique_token_consumptions_under_load(self):
        token = self._admin_token()
        token_values = [
            self._create_token_fixture(token, f"stress-token-{secrets.token_hex(6)}")
            for _ in range(120)
        ]

        def consume_worker(token_value):
            response = self._consume_token(token, token_value, simulate_failure=False)
            return response.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=35) as executor:
            statuses = list(executor.map(consume_worker, token_values))

        self.assertEqual(sum(1 for status in statuses if status == 200), len(token_values))

    def test_sustained_read_stress_consistency(self):
        token = self._admin_token()
        db_name = f"read_stress_db_{secrets.token_hex(4)}"
        table_name = f"read_stress_table_{secrets.token_hex(4)}"

        with app.test_client() as client:
            client.post("/api/databases", headers=self._headers(token), json={"name": db_name})
            client.post(
                f"/api/databases/{db_name}/tables",
                headers=self._headers(token),
                json={"name": table_name, "schema": ["id", "value"], "search_key": "id"},
            )
            for index in range(1, 301):
                client.post(
                    f"/api/databases/{db_name}/tables/{table_name}/records",
                    headers=self._headers(token),
                    json={"id": str(index), "value": f"seed-{index}"},
                )

        iterations = 700
        started_at = time.perf_counter()
        for _ in range(iterations):
            with app.test_client() as client:
                response = client.get(
                    f"/api/databases/{db_name}/tables/{table_name}/records",
                    headers=self._headers(token),
                )
                body = response.get_json() or {}
                self.assertEqual(response.status_code, 200)
                self.assertEqual(body.get("count"), 300)
        elapsed = time.perf_counter() - started_at

        avg_ms = (elapsed / iterations) * 1000
        self.assertLess(avg_ms, 300)


if __name__ == "__main__":
    import unittest

    unittest.main()
