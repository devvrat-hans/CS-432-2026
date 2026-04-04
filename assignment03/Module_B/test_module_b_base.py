# pyright: reportMissingImports=false

import secrets
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

MODULE_B_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = MODULE_B_ROOT / "db_management_system"
DB_PATH = BACKEND_ROOT / "module_b.sqlite3"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import app  # noqa: E402


def _extract_status_for_test(result_obj, test_id):
    for failed_test, traceback_text in result_obj.failures:
        if failed_test.id() == test_id:
            return "FAIL", traceback_text
    for error_test, traceback_text in result_obj.errors:
        if error_test.id() == test_id:
            return "ERROR", traceback_text
    return "PASS", ""


class LoggedModuleBTestCase(unittest.TestCase):
    RESULTS_PATH = MODULE_B_ROOT / "test_results_module_b.txt"
    _run_started_at = None
    _result_counts = {"PASS": 0, "FAIL": 0, "ERROR": 0}

    @classmethod
    def _append_result_line(cls, text):
        with cls.RESULTS_PATH.open("a", encoding="utf-8") as results_file:
            results_file.write(text)

    @classmethod
    def setUpClass(cls):
        app.testing = True
        cls._run_started_at = time.perf_counter()
        cls._result_counts = {"PASS": 0, "FAIL": 0, "ERROR": 0}
        cls.RESULTS_PATH.write_text(
            (
                f"{cls.__name__} Results\n"
                f"Run started (UTC): {datetime.now(timezone.utc).isoformat()}\n"
                + "=" * 72
                + "\n"
            ),
            encoding="utf-8",
        )

    @classmethod
    def tearDownClass(cls):
        elapsed_seconds = 0.0
        if cls._run_started_at is not None:
            elapsed_seconds = time.perf_counter() - cls._run_started_at
        total = sum(cls._result_counts.values())
        cls._append_result_line(
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

        self.__class__._append_result_line(f"[{status}] {test_id} ({elapsed_ms:.3f} ms)\n")
        if traceback_text:
            self.__class__._append_result_line("Traceback:\n")
            self.__class__._append_result_line(traceback_text)
            self.__class__._append_result_line("\n" + "-" * 72 + "\n")

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

    def _create_token_fixture(self, token, token_value=None, expires_in_minutes=30):
        candidate_token = token_value or f"fixture-{secrets.token_hex(8)}"
        with app.test_client() as client:
            response = client.post(
                "/api/resilience/token-fixtures",
                headers=self._headers(token),
                json={
                    "token_value": candidate_token,
                    "expires_in_minutes": expires_in_minutes,
                },
            )
        self.assertEqual(response.status_code, 201, response.get_json())
        return candidate_token

    def _consume_token(self, token, token_value, simulate_failure=False):
        with app.test_client() as client:
            return client.post(
                "/api/resilience/consume-token",
                headers=self._headers(token),
                json={
                    "token_value": token_value,
                    "user_device_info": "module-b-test",
                    "simulate_failure": simulate_failure,
                },
            )
