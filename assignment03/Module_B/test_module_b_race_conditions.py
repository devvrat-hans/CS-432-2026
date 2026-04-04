import concurrent.futures
import secrets

from test_module_b_base import LoggedModuleBTestCase, MODULE_B_ROOT, app


class TestModuleBRaceConditions(LoggedModuleBTestCase):
    RESULTS_PATH = MODULE_B_ROOT / "test_results_race_conditions.txt"

    def test_single_winner_on_token_consume(self):
        token = self._admin_token()
        token_value = self._create_token_fixture(token, f"race-{secrets.token_hex(8)}")

        def worker(_):
            response = self._consume_token(token, token_value, simulate_failure=False)
            return response.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
            statuses = list(executor.map(worker, range(40)))

        self.assertEqual(sum(1 for status in statuses if status == 200), 1)
        self.assertEqual(sum(1 for status in statuses if status == 409), 39)

    def test_single_winner_on_duplicate_record_key_insert(self):
        token = self._admin_token()
        db_name = f"race_db_{secrets.token_hex(4)}"
        table_name = f"race_table_{secrets.token_hex(4)}"

        with app.test_client() as client:
            client.post("/api/databases", headers=self._headers(token), json={"name": db_name})
            client.post(
                f"/api/databases/{db_name}/tables",
                headers=self._headers(token),
                json={"name": table_name, "schema": ["id", "value"], "search_key": "id"},
            )

        def worker(_):
            with app.test_client() as client:
                response = client.post(
                    f"/api/databases/{db_name}/tables/{table_name}/records",
                    headers=self._headers(token),
                    json={"id": "same-key", "value": "race"},
                )
            return response.status_code

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            statuses = list(executor.map(worker, range(30)))

        self.assertEqual(sum(1 for status in statuses if status == 201), 1)
        self.assertEqual(sum(1 for status in statuses if status == 400), 29)

    def test_repeated_race_rounds_consistent(self):
        token = self._admin_token()

        for round_index in range(1, 6):
            token_value = self._create_token_fixture(token, f"round-{round_index}-{secrets.token_hex(6)}")

            def worker(_):
                response = self._consume_token(token, token_value, simulate_failure=False)
                return response.status_code

            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                statuses = list(executor.map(worker, range(20)))

            self.assertEqual(sum(1 for status in statuses if status == 200), 1)
            self.assertEqual(sum(1 for status in statuses if status == 409), 19)


if __name__ == "__main__":
    import unittest

    unittest.main()
