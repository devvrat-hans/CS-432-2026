import secrets
import sqlite3

from test_module_b_base import DB_PATH, LoggedModuleBTestCase, MODULE_B_ROOT, app


class TestModuleBFailureSimulation(LoggedModuleBTestCase):
    RESULTS_PATH = MODULE_B_ROOT / "test_results_failure_simulation.txt"

    def test_injected_failure_rolls_back_token_and_download_log(self):
        token = self._admin_token()
        token_value = self._create_token_fixture(token, f"rollback-{secrets.token_hex(8)}")

        failed_response = self._consume_token(token, token_value, simulate_failure=True)
        self.assertEqual(failed_response.status_code, 500, failed_response.get_json())

        with app.test_client() as client:
            status_response = client.get(
                f"/api/resilience/token-status/{token_value}",
                headers=self._headers(token),
            )

        body = status_response.get_json() or {}
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(body["token"]["status"], "ACTIVE")
        self.assertEqual(body["download_count"], 0)

    def test_injected_failure_followed_by_successful_retry(self):
        token = self._admin_token()
        token_value = self._create_token_fixture(token, f"retry-{secrets.token_hex(8)}")

        first_attempt = self._consume_token(token, token_value, simulate_failure=True)
        self.assertEqual(first_attempt.status_code, 500)

        second_attempt = self._consume_token(token, token_value, simulate_failure=False)
        self.assertEqual(second_attempt.status_code, 200, second_attempt.get_json())

        third_attempt = self._consume_token(token, token_value, simulate_failure=False)
        self.assertEqual(third_attempt.status_code, 409, third_attempt.get_json())

    def test_failure_does_not_mark_upload_session_downloaded(self):
        token = self._admin_token()
        token_value = self._create_token_fixture(token, f"session-rollback-{secrets.token_hex(6)}")

        failed_response = self._consume_token(token, token_value, simulate_failure=True)
        self.assertEqual(failed_response.status_code, 500)

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT u.status AS upload_status
                FROM OneTimeToken t
                JOIN UploadSession u ON u.sessionID = t.sessionID
                WHERE t.tokenValue = ?
                """,
                (token_value,),
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row["upload_status"], "ACTIVE")


if __name__ == "__main__":
    import unittest

    unittest.main()
