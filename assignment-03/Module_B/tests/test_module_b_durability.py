import json
import secrets
import subprocess
import sys

try:
    from test_module_b_base import DB_PATH, LoggedModuleBTestCase, MODULE_B_ROOT
except ModuleNotFoundError:
    from assignment03.Module_B.tests.test_module_b_base import DB_PATH, LoggedModuleBTestCase, MODULE_B_ROOT


class TestModuleBDurability(LoggedModuleBTestCase):
    RESULTS_PATH = MODULE_B_ROOT / "test_results" / "test_results_durability.txt"

    def _snapshot_token_state_from_fresh_process(self, token_value):
        code = (
            "import json\n"
            "import sqlite3\n"
            "import sys\n"
            "db_path, token_value = sys.argv[1], sys.argv[2]\n"
            "conn = sqlite3.connect(db_path)\n"
            "conn.row_factory = sqlite3.Row\n"
            "token_row = conn.execute(\"SELECT status, tokenID, sessionID FROM OneTimeToken WHERE tokenValue = ?\", (token_value,)).fetchone()\n"
            "download_count = 0\n"
            "upload_status = None\n"
            "if token_row is not None:\n"
            "    download_count = conn.execute(\"SELECT COUNT(*) AS count FROM DownloadLog WHERE tokenID = ?\", (token_row['tokenID'],)).fetchone()['count']\n"
            "    upload_row = conn.execute(\"SELECT status AS upload_status FROM UploadSession WHERE sessionID = ?\", (token_row['sessionID'],)).fetchone()\n"
            "    upload_status = upload_row['upload_status'] if upload_row is not None else None\n"
            "state = {\n"
            "    'token_status': token_row['status'] if token_row is not None else None,\n"
            "    'download_count': download_count,\n"
            "    'upload_status': upload_status,\n"
            "}\n"
            "conn.close()\n"
            "print(json.dumps(state))\n"
        )

        completed = subprocess.run(
            [sys.executable, "-c", code, str(DB_PATH), token_value],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(completed.stdout.strip())

    def test_committed_data_persists_after_restart_simulation(self):
        token = self._admin_token()
        token_value = self._create_token_fixture(token, f"durability-commit-{secrets.token_hex(6)}")

        consume_response = self._consume_token(token, token_value, simulate_failure=False)
        self.assertEqual(consume_response.status_code, 200, consume_response.get_json())

        persisted_state = self._snapshot_token_state_from_fresh_process(token_value)
        self.assertEqual(persisted_state["token_status"], "USED")
        self.assertEqual(persisted_state["download_count"], 1)
        self.assertEqual(persisted_state["upload_status"], "DOWNLOADED")

    def test_failed_transactions_absent_after_restart_simulation(self):
        token = self._admin_token()
        failure_stages = [
            "before_status_update",
            "after_token_update",
            "before_commit",
        ]

        for stage in failure_stages:
            token_value = self._create_token_fixture(token, f"durability-fail-{stage}-{secrets.token_hex(6)}")

            failed_response = self._consume_token(
                token,
                token_value,
                simulate_failure=True,
                failure_stage=stage,
            )
            self.assertEqual(failed_response.status_code, 500, failed_response.get_json())

            persisted_state = self._snapshot_token_state_from_fresh_process(token_value)
            self.assertEqual(persisted_state["token_status"], "ACTIVE")
            self.assertEqual(persisted_state["download_count"], 0)
            self.assertEqual(persisted_state["upload_status"], "ACTIVE")


if __name__ == "__main__":
    import unittest

    unittest.main()
