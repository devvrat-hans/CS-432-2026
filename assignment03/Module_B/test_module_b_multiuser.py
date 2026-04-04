# pyright: reportMissingImports=false

import concurrent.futures
import secrets
import sqlite3
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

MODULE_B_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = MODULE_B_ROOT / "db_management_system"
DB_PATH = BACKEND_ROOT / "module_b.sqlite3"
RESULTS_PATH = MODULE_B_ROOT / "test_module_b_multiuser_results.txt"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import app  # noqa: E402


def _append_result_line(text):
    with RESULTS_PATH.open("a", encoding="utf-8") as results_file:
        results_file.write(text)


def _extract_status_for_test(result_obj, test_id):
    for failed_test, traceback_text in result_obj.failures:
        if failed_test.id() == test_id:
            return "FAIL", traceback_text
    for error_test, traceback_text in result_obj.errors:
        if error_test.id() == test_id:
            return "ERROR", traceback_text
    return "PASS", ""


class TestModuleBMultiUserBehavior(unittest.TestCase):
    _run_started_at = None
    _result_counts = {"PASS": 0, "FAIL": 0, "ERROR": 0}

    @classmethod
    def setUpClass(cls):
        app.testing = True
        cls._run_started_at = time.perf_counter()
        cls._result_counts = {"PASS": 0, "FAIL": 0, "ERROR": 0}
        RESULTS_PATH.write_text(
            (
                "Module B Multi-User Test Results\n"
                f"Run started (UTC): {datetime.now(timezone.utc).isoformat()}\n"
                "=" * 72 + "\n"
            ),
            encoding="utf-8",
        )

    @classmethod
    def tearDownClass(cls):
        elapsed_seconds = 0.0
        if cls._run_started_at is not None:
            elapsed_seconds = time.perf_counter() - cls._run_started_at
        total = sum(cls._result_counts.values())
        _append_result_line(
            (
                "\n" + "=" * 72 + "\n"
                "Run summary\n"
                f"Total: {total}\n"
                f"PASS: {cls._result_counts['PASS']}\n"
                f"FAIL: {cls._result_counts['FAIL']}\n"
                f"ERROR: {cls._result_counts['ERROR']}\n"
                f"Elapsed seconds: {elapsed_seconds:.4f}\n"
            )
        )

    def setUp(self):
        self._test_started_at = time.perf_counter()

    def tearDown(self):
        test_id = self.id()
        status = "PASS"
        traceback_text = ""
        result_obj = getattr(self._outcome, "result", None)
        if result_obj is not None:
            status, traceback_text = _extract_status_for_test(result_obj, test_id)

        self.__class__._result_counts[status] += 1
        elapsed_ms = (time.perf_counter() - self._test_started_at) * 1000

        _append_result_line(f"[{status}] {test_id} ({elapsed_ms:.3f} ms)\n")
        if traceback_text:
            _append_result_line("Traceback:\n")
            _append_result_line(traceback_text)
            _append_result_line("\n" + "-" * 72 + "\n")

    def _admin_token(self):
        with app.test_client() as client:
            response = client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "admin123"},
            )
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json() or {}
        return body["token"]

    def _headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _create_token_fixture(self, token, token_value):
        with app.test_client() as client:
            response = client.post(
                "/api/resilience/token-fixtures",
                headers=self._headers(token),
                json={"token_value": token_value, "expires_in_minutes": 30},
            )
        self.assertEqual(response.status_code, 201, response.get_json())

    def _consume_token(self, token, token_value, simulate_failure=False):
        with app.test_client() as client:
            return client.post(
                "/api/resilience/consume-token",
                headers=self._headers(token),
                json={
                    "token_value": token_value,
                    "user_device_info": "module-b-concurrency-test",
                    "simulate_failure": simulate_failure,
                },
            )

    def test_race_condition_single_consumer_wins(self):
        token = self._admin_token()
        token_value = f"race-{secrets.token_hex(8)}"
        self._create_token_fixture(token, token_value)

        worker_count = 40

        def worker(_):
            response = self._consume_token(token, token_value, simulate_failure=False)
            return response.status_code, response.get_json()

        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            outcomes = list(executor.map(worker, range(worker_count)))

        success_count = sum(1 for status, _ in outcomes if status == 200)
        conflict_count = sum(1 for status, _ in outcomes if status == 409)
        unexpected = [(status, body) for status, body in outcomes if status not in {200, 409}]

        self.assertEqual(success_count, 1, outcomes)
        self.assertEqual(conflict_count, worker_count - 1, outcomes)
        self.assertEqual(unexpected, [], outcomes)

        with app.test_client() as client:
            status_response = client.get(
                f"/api/resilience/token-status/{token_value}",
                headers=self._headers(token),
            )
        self.assertEqual(status_response.status_code, 200, status_response.get_json())
        status_body = status_response.get_json() or {}
        self.assertEqual(status_body["token"]["status"], "USED")
        self.assertEqual(status_body["download_count"], 1)

        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT status FROM OneTimeToken WHERE tokenValue = ?",
                (token_value,),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "USED")

    def test_failure_simulation_rolls_back_without_partial_data(self):
        token = self._admin_token()
        token_value = f"rollback-{secrets.token_hex(8)}"
        self._create_token_fixture(token, token_value)

        failure_response = self._consume_token(token, token_value, simulate_failure=True)
        self.assertEqual(failure_response.status_code, 500, failure_response.get_json())

        with app.test_client() as client:
            status_response = client.get(
                f"/api/resilience/token-status/{token_value}",
                headers=self._headers(token),
            )
        self.assertEqual(status_response.status_code, 200, status_response.get_json())
        status_body = status_response.get_json() or {}
        self.assertEqual(status_body["token"]["status"], "ACTIVE")
        self.assertEqual(status_body["download_count"], 0)

        success_response = self._consume_token(token, token_value, simulate_failure=False)
        self.assertEqual(success_response.status_code, 200, success_response.get_json())

        with app.test_client() as client:
            final_status = client.get(
                f"/api/resilience/token-status/{token_value}",
                headers=self._headers(token),
            )
        final_body = final_status.get_json() or {}
        self.assertEqual(final_body["token"]["status"], "USED")
        self.assertEqual(final_body["download_count"], 1)

    def test_stress_insert_hundreds_of_requests(self):
        token = self._admin_token()
        db_name = f"stress_db_{secrets.token_hex(4)}"
        table_name = f"stress_table_{secrets.token_hex(3)}"

        with app.test_client() as client:
            create_db = client.post(
                "/api/databases",
                headers=self._headers(token),
                json={"name": db_name},
            )
        self.assertEqual(create_db.status_code, 201, create_db.get_json())

        with app.test_client() as client:
            create_table = client.post(
                f"/api/databases/{db_name}/tables",
                headers=self._headers(token),
                json={"name": table_name, "schema": ["id", "payload"], "search_key": "id"},
            )
        self.assertEqual(create_table.status_code, 201, create_table.get_json())

        request_count = 400
        worker_count = 25

        def insert_worker(index):
            payload = {"id": str(index), "payload": f"value-{index}"}
            with app.test_client() as client:
                response = client.post(
                    f"/api/databases/{db_name}/tables/{table_name}/records",
                    headers=self._headers(token),
                    json=payload,
                )
            return response.status_code, response.get_json()

        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            outcomes = list(executor.map(insert_worker, range(1, request_count + 1)))
        elapsed = time.perf_counter() - start

        success_count = sum(1 for status, _ in outcomes if status == 201)
        failures = [(status, body) for status, body in outcomes if status != 201]

        self.assertEqual(success_count, request_count)
        self.assertEqual(failures, [], failures)

        with app.test_client() as client:
            fetch_records = client.get(
                f"/api/databases/{db_name}/tables/{table_name}/records",
                headers=self._headers(token),
            )
        self.assertEqual(fetch_records.status_code, 200, fetch_records.get_json())
        fetched = fetch_records.get_json() or {}
        self.assertEqual(fetched.get("count"), request_count)

        avg_ms = (elapsed / request_count) * 1000
        self.assertLess(avg_ms, 200)


if __name__ == "__main__":
    unittest.main()
