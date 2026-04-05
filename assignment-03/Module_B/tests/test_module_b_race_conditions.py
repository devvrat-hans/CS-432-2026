# pyright: reportMissingImports=false

import concurrent.futures
import random
import secrets

try:
    from test_module_b_base import LoggedModuleBTestCase, MODULE_B_ROOT, app
except ModuleNotFoundError:
    from assignment03.Module_B.tests.test_module_b_base import LoggedModuleBTestCase, MODULE_B_ROOT, app


class TestModuleBRaceConditions(LoggedModuleBTestCase):
    RESULTS_PATH = MODULE_B_ROOT / "test_results" / "test_results_race_conditions.txt"

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

        # Seeded randomness keeps the test deterministic while varying race patterns.
        rng = random.Random(4326)
        total_rounds = 10

        for round_index in range(1, total_rounds + 1):
            scenario = rng.choice(["token-consume", "duplicate-insert"])
            worker_count = rng.randint(12, 24)

            if scenario == "token-consume":
                token_value = self._create_token_fixture(token, f"round-{round_index}-{secrets.token_hex(6)}")

                def consume_worker(_):
                    response = self._consume_token(token, token_value, simulate_failure=False)
                    return response.status_code

                with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
                    statuses = list(executor.map(consume_worker, range(worker_count)))

                self.assertTrue(all(status in {200, 409} for status in statuses), statuses)
                self.assertEqual(sum(1 for status in statuses if status == 200), 1)
                self.assertEqual(sum(1 for status in statuses if status == 409), worker_count - 1)

                with app.test_client() as client:
                    status_response = client.get(
                        f"/api/resilience/token-status/{token_value}",
                        headers=self._headers(token),
                    )
                body = status_response.get_json() or {}
                self.assertEqual(status_response.status_code, 200, body)
                self.assertEqual(body["token"]["status"], "USED")
                self.assertEqual(body["download_count"], 1)
                continue

            db_name = f"rand_race_db_{round_index}_{secrets.token_hex(4)}"
            table_name = f"rand_race_table_{round_index}_{secrets.token_hex(4)}"

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

            def insert_worker(_):
                with app.test_client() as client:
                    response = client.post(
                        f"/api/databases/{db_name}/tables/{table_name}/records",
                        headers=self._headers(token),
                        json={"id": "same-key", "value": f"round-{round_index}"},
                    )
                return response.status_code

            with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
                statuses = list(executor.map(insert_worker, range(worker_count)))

            self.assertTrue(all(status in {201, 400} for status in statuses), statuses)
            self.assertEqual(sum(1 for status in statuses if status == 201), 1)
            self.assertEqual(sum(1 for status in statuses if status == 400), worker_count - 1)

            with app.test_client() as client:
                records_response = client.get(
                    f"/api/databases/{db_name}/tables/{table_name}/records",
                    headers=self._headers(token),
                )
            records_body = records_response.get_json() or {}
            records = records_body.get("records", [])

            self.assertEqual(records_response.status_code, 200, records_body)
            self.assertEqual(records_body.get("count"), 1)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["data"].get("id"), "same-key")


if __name__ == "__main__":
    import unittest

    unittest.main()
