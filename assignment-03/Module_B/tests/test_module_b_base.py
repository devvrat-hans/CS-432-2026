import secrets
import os
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
MODULE_B_ROOT = TESTS_ROOT.parent
RESULTS_ROOT = MODULE_B_ROOT / "test_results"
BACKEND_ROOT = MODULE_B_ROOT / "db_management_system"
TEST_RUNTIME_DB_PATH = RESULTS_ROOT / "module_b_test_runtime.sqlite3"

# Keep test mutations in a dedicated sqlite file rather than the main runtime database.
os.environ.setdefault("BLINDDROP_DB_PATH", str(TEST_RUNTIME_DB_PATH))
DB_PATH = Path(os.environ["BLINDDROP_DB_PATH"]).expanduser()
if not DB_PATH.is_absolute():
    DB_PATH = (MODULE_B_ROOT / DB_PATH).resolve()

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import app

try:
    from api.routes import _write_audit
except ModuleNotFoundError:
    from assignment03.Module_B.db_management_system.api.routes import _write_audit


def _extract_status_for_test(result_obj, test_id):
    for failed_test, traceback_text in result_obj.failures:
        if failed_test.id() == test_id:
            return "FAIL", traceback_text
    for error_test, traceback_text in result_obj.errors:
        if error_test.id() == test_id:
            return "ERROR", traceback_text
    return "PASS", ""


def _safe_write_test_audit(action, status, details):
    try:
        _write_audit(
            action=action,
            target="module_b_tests",
            status=status,
            actor_id=None,
            details=details,
        )
    except Exception:
        # Test execution should not fail if audit logging itself is unavailable.
        pass


class LoggedModuleBTestCase(unittest.TestCase):
    RESULTS_PATH = RESULTS_ROOT / "test_results_module_b.txt"
    _run_started_at = None
    _result_counts = {"PASS": 0, "FAIL": 0, "ERROR": 0}

    @classmethod
    def _append_result_line(cls, text):
        with cls.RESULTS_PATH.open("a", encoding="utf-8") as results_file:
            results_file.write(text)

    @classmethod
    def setUpClass(cls):
        app.testing = True
        RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
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
        _safe_write_test_audit(
            action="test_suite",
            status="started",
            details=f"suite={cls.__name__}",
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
        _safe_write_test_audit(
            action="test_suite",
            status="success" if cls._result_counts["FAIL"] == 0 and cls._result_counts["ERROR"] == 0 else "failed",
            details=(
                f"suite={cls.__name__};"
                f"total={total};"
                f"pass={cls._result_counts['PASS']};"
                f"fail={cls._result_counts['FAIL']};"
                f"error={cls._result_counts['ERROR']};"
                f"elapsed_seconds={elapsed_seconds:.4f}"
            ),
        )

    def setUp(self):
        self._test_started_at = time.perf_counter()
        _safe_write_test_audit(
            action="test_case",
            status="started",
            details=f"test={self.id()}",
        )

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

        audit_status_map = {"PASS": "success", "FAIL": "failed", "ERROR": "error"}
        _safe_write_test_audit(
            action="test_case",
            status=audit_status_map.get(status, "unknown"),
            details=f"test={test_id};elapsed_ms={elapsed_ms:.3f}",
        )

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

    def _consume_token(self, token, token_value, simulate_failure=False, failure_stage=None):
        payload = {
            "token_value": token_value,
            "user_device_info": "module-b-test",
            "simulate_failure": simulate_failure,
        }
        if failure_stage:
            payload["failure_stage"] = failure_stage

        with app.test_client() as client:
            return client.post(
                "/api/resilience/consume-token",
                headers=self._headers(token),
                json=payload,
            )
