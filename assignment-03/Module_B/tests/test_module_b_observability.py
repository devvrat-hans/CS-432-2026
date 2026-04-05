from datetime import datetime
import secrets
import sqlite3

try:
    from test_module_b_base import DB_PATH, LoggedModuleBTestCase, MODULE_B_ROOT, app
except ModuleNotFoundError:
    from assignment03.Module_B.tests.test_module_b_base import DB_PATH, LoggedModuleBTestCase, MODULE_B_ROOT, app


class TestModuleBObservability(LoggedModuleBTestCase):
    RESULTS_PATH = MODULE_B_ROOT / "test_results" / "test_results_observability.txt"

    def _max_audit_id(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM audit_logs").fetchone()
        return int(row["max_id"]) if row is not None else 0

    def _audit_logs_after(self, baseline_id):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, action, target, status, details, created_at
                FROM audit_logs
                WHERE id > ?
                ORDER BY id ASC
                """,
                (baseline_id,),
            ).fetchall()
        return rows

    def _create_regular_user_and_token(self, admin_token):
        username = f"obs_{secrets.token_hex(6)}"
        password = f"Pwd-{secrets.token_hex(6)}"

        with app.test_client() as client:
            create_response = client.post(
                "/api/members",
                headers=self._headers(admin_token),
                json={
                    "username": username,
                    "password": password,
                    "full_name": "Observability User",
                    "email": f"{username}@blinddrop.local",
                    "role": "user",
                    "member_group": "observability",
                },
            )
        self.assertEqual(create_response.status_code, 201, create_response.get_json())

        with app.test_client() as client:
            login_response = client.post(
                "/api/auth/login",
                json={"username": username, "password": password},
            )
        self.assertEqual(login_response.status_code, 200, login_response.get_json())
        body = login_response.get_json() or {}
        return body["token"]

    def test_mutation_audit_logs_cover_success_failure_and_denial(self):
        admin_token = self._admin_token()
        baseline_id = self._max_audit_id()

        token_value = self._create_token_fixture(admin_token, f"obs-token-{secrets.token_hex(6)}")

        failed_response = self._consume_token(
            admin_token,
            token_value,
            simulate_failure=True,
            failure_stage="before_commit",
        )
        self.assertEqual(failed_response.status_code, 500, failed_response.get_json())

        successful_response = self._consume_token(admin_token, token_value, simulate_failure=False)
        self.assertEqual(successful_response.status_code, 200, successful_response.get_json())

        user_token = self._create_regular_user_and_token(admin_token)
        with app.test_client() as client:
            denied_response = client.post(
                "/api/databases",
                headers=self._headers(user_token),
                json={"name": f"forbidden_db_{secrets.token_hex(4)}"},
            )
        self.assertEqual(denied_response.status_code, 403, denied_response.get_json())

        new_logs = self._audit_logs_after(baseline_id)
        self.assertGreater(len(new_logs), 0)

        consume_failed = [
            row
            for row in new_logs
            if row["action"] == "consume_token" and row["status"] == "failed"
        ]
        consume_success = [
            row
            for row in new_logs
            if row["action"] == "consume_token" and row["status"] == "success"
        ]
        rbac_denied = [
            row
            for row in new_logs
            if row["action"] == "rbac_denied" and row["status"] == "denied"
        ]

        self.assertGreaterEqual(len(consume_failed), 1)
        self.assertGreaterEqual(len(consume_success), 1)
        self.assertGreaterEqual(len(rbac_denied), 1)

        observed = [consume_failed[-1], consume_success[-1], rbac_denied[-1]]
        for row in observed:
            self.assertIsNotNone(row["id"])
            self.assertTrue((row["action"] or "").strip())
            self.assertTrue((row["target"] or "").strip())
            self.assertTrue((row["status"] or "").strip())
            self.assertTrue((row["created_at"] or "").strip())
            datetime.fromisoformat(row["created_at"])

        self.assertIn("RuntimeError", consume_failed[-1]["details"] or "")
        self.assertIn("token", consume_success[-1]["details"] or "")
        self.assertIn("Admin role required", rbac_denied[-1]["details"] or "")


if __name__ == "__main__":
    import unittest

    unittest.main()
