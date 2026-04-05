import concurrent.futures
import math
import secrets
import time

try:
    from test_module_b_base import LoggedModuleBTestCase, MODULE_B_ROOT, app
except ModuleNotFoundError:
    from assignment03.Module_B.tests.test_module_b_base import LoggedModuleBTestCase, MODULE_B_ROOT, app


class TestModuleBStress(LoggedModuleBTestCase):
    RESULTS_PATH = MODULE_B_ROOT / "test_results" / "test_results_stress.txt"

    def test_high_volume_parallel_insert_stress(self):
        token = self._admin_token()
        db_name = f"stress_db_{secrets.token_hex(4)}"
        table_name = f"stress_table_{secrets.token_hex(4)}"

        with app.test_client() as client:
            self.assertEqual(
                client.post("/api/databases", headers=self._headers(token), json={"name": db_name}).status_code,
                201,
            )
            self.assertEqual(
                client.post(
                    f"/api/databases/{db_name}/tables",
                    headers=self._headers(token),
                    json={"name": table_name, "schema": ["id", "payload"], "search_key": "id"},
                ).status_code,
                201,
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

    def test_thousands_scale_insert_metrics(self):
        token = self._admin_token()
        db_name = f"stress_k_db_{secrets.token_hex(4)}"
        table_name = f"stress_k_table_{secrets.token_hex(4)}"

        with app.test_client() as client:
            self.assertEqual(
                client.post("/api/databases", headers=self._headers(token), json={"name": db_name}).status_code,
                201,
            )
            self.assertEqual(
                client.post(
                    f"/api/databases/{db_name}/tables",
                    headers=self._headers(token),
                    json={"name": table_name, "schema": ["id", "payload"], "search_key": "id"},
                ).status_code,
                201,
            )

        request_count = 1000
        worker_count = 24

        def insert_worker(index):
            started_at = time.perf_counter()
            with app.test_client() as client:
                response = client.post(
                    f"/api/databases/{db_name}/tables/{table_name}/records",
                    headers=self._headers(token),
                    json={"id": str(index), "payload": f"payload-{index}"},
                )
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            return response.status_code, elapsed_ms

        test_started_at = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            outcomes = list(executor.map(insert_worker, range(1, request_count + 1)))
        total_duration_seconds = time.perf_counter() - test_started_at

        statuses = [status for status, _ in outcomes]
        latencies_ms = [latency for _, latency in outcomes]

        success_count = sum(1 for status in statuses if status == 201)
        success_rate = success_count / request_count

        with app.test_client() as client:
            records_response = client.get(
                f"/api/databases/{db_name}/tables/{table_name}/records",
                headers=self._headers(token),
            )
        records_body = records_response.get_json() or {}
        records = records_body.get("records", [])

        record_ids = [str(item.get("data", {}).get("id")) for item in records]
        invariant_violations = 0
        if records_response.status_code != 200:
            invariant_violations += 1
        if records_body.get("count") != request_count:
            invariant_violations += 1
        if len(record_ids) != len(set(record_ids)):
            invariant_violations += 1

        average_latency_ms = sum(latencies_ms) / len(latencies_ms)
        sorted_latencies = sorted(latencies_ms)
        p95_index = max(0, math.ceil(0.95 * len(sorted_latencies)) - 1)
        p95_latency_ms = sorted_latencies[p95_index]

        self.__class__._append_result_line(
            (
                "[METRICS] thousands_scale_insert "
                f"success_rate={success_rate:.4f} "
                f"invariant_violations={invariant_violations} "
                f"avg_ms={average_latency_ms:.3f} "
                f"p95_ms={p95_latency_ms:.3f} "
                f"total_seconds={total_duration_seconds:.3f}\n"
            )
        )

        self.assertGreaterEqual(success_rate, 0.99)
        self.assertEqual(invariant_violations, 0)
        self.assertLess(average_latency_ms, 500)
        self.assertLess(p95_latency_ms, 1000)
        self.assertLess(total_duration_seconds, 90)

    def test_sustained_read_stress_consistency(self):
        token = self._admin_token()
        db_name = f"read_stress_db_{secrets.token_hex(4)}"
        table_name = f"read_stress_table_{secrets.token_hex(4)}"

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
            for index in range(1, 301):
                self.assertEqual(
                    client.post(
                        f"/api/databases/{db_name}/tables/{table_name}/records",
                        headers=self._headers(token),
                        json={"id": str(index), "value": f"seed-{index}"},
                    ).status_code,
                    201,
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
