import concurrent.futures
import math
import secrets
import sqlite3
import time

try:
    from test_module_b_base import DB_PATH, LoggedModuleBTestCase, MODULE_B_ROOT, app
    from stress_config import DEFAULT_STRESS_THRESHOLDS, get_stress_profile
    from stress_data_utils import deterministic_workspace_names, get_seed_size, managed_stress_workspace
    from stress_invariants import assert_table_phase_invariants, assert_token_state_transition
    from stress_metrics import append_phase_metrics, build_phase_metrics
    from stress_telemetry import PhaseTelemetrySampler
except ModuleNotFoundError:
    from assignment03.Module_B.tests.test_module_b_base import DB_PATH, LoggedModuleBTestCase, MODULE_B_ROOT, app
    from assignment03.Module_B.tests.stress_config import DEFAULT_STRESS_THRESHOLDS, get_stress_profile
    from assignment03.Module_B.tests.stress_data_utils import (
        deterministic_workspace_names,
        get_seed_size,
        managed_stress_workspace,
    )
    from assignment03.Module_B.tests.stress_invariants import (
        assert_table_phase_invariants,
        assert_token_state_transition,
    )
    from assignment03.Module_B.tests.stress_metrics import append_phase_metrics, build_phase_metrics
    from assignment03.Module_B.tests.stress_telemetry import PhaseTelemetrySampler


class TestModuleBStress(LoggedModuleBTestCase):
    RESULTS_PATH = MODULE_B_ROOT / "test_results" / "test_results_stress.txt"
    PHASE_METRICS_PATH = MODULE_B_ROOT / "test_results" / "stress_phase_metrics.jsonl"
    TELEMETRY_PATH = MODULE_B_ROOT / "test_results" / "stress_telemetry.jsonl"
    _ARTIFACTS_INITIALIZED = False

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls._ARTIFACTS_INITIALIZED:
            cls.PHASE_METRICS_PATH.write_text("", encoding="utf-8")
            cls.TELEMETRY_PATH.write_text("", encoding="utf-8")
            cls._ARTIFACTS_INITIALIZED = True

    @classmethod
    def _telemetry_phase(cls, phase_name: str, context: dict | None = None):
        return PhaseTelemetrySampler(
            telemetry_path=cls.TELEMETRY_PATH,
            phase_name=phase_name,
            sample_interval_seconds=0.5,
            context=context,
        )

    @classmethod
    def _persist_phase_metrics(
        cls,
        *,
        phase_name: str,
        statuses: list[int],
        latencies_ms: list[float],
        phase_duration_seconds: float,
        success_statuses: set[int],
        context: dict | None = None,
    ) -> None:
        metrics = build_phase_metrics(
            phase_name=phase_name,
            statuses=statuses,
            latencies_ms=latencies_ms,
            phase_duration_seconds=phase_duration_seconds,
            success_statuses=success_statuses,
        )
        append_phase_metrics(
            metrics_path=cls.PHASE_METRICS_PATH,
            metrics=metrics,
            context=context,
        )

    def _snapshot_token_transaction_state(self, token, token_value):
        with app.test_client() as client:
            status_response = client.get(
                f"/api/resilience/token-status/{token_value}",
                headers=self._headers(token),
            )

        body = status_response.get_json() or {}
        self.assertEqual(status_response.status_code, 200, body)

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            upload_row = conn.execute(
                """
                SELECT u.status AS upload_status
                FROM OneTimeToken t
                JOIN UploadSession u ON u.sessionID = t.sessionID
                WHERE t.tokenValue = ?
                """,
                (token_value,),
            ).fetchone()

        self.assertIsNotNone(upload_row)
        return {
            "token_status": body["token"]["status"],
            "download_count": body["download_count"],
            "upload_status": upload_row["upload_status"],
        }

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

    def test_stress_activity_emits_required_audit_traces(self):
        token = self._admin_token()
        baseline_id = self._max_audit_id()

        db_name, table_name = deterministic_workspace_names(self.id(), namespace="stress_audit")
        with managed_stress_workspace(
            test_case=self,
            app=app,
            token=token,
            db_name=db_name,
            table_name=table_name,
            schema=["id", "value"],
            search_key="id",
        ) as workspace:
            with app.test_client() as client:
                create_response = client.post(
                    f"/api/databases/{workspace.db_name}/tables/{workspace.table_name}/records",
                    headers=self._headers(token),
                    json={"id": "audit-record", "value": "seed"},
                )
                self.assertEqual(create_response.status_code, 201, create_response.get_json())

                update_response = client.put(
                    f"/api/databases/{workspace.db_name}/tables/{workspace.table_name}/records/audit-record",
                    headers=self._headers(token),
                    json={"value": "updated"},
                )
                self.assertEqual(update_response.status_code, 200, update_response.get_json())

                delete_response = client.delete(
                    f"/api/databases/{workspace.db_name}/tables/{workspace.table_name}/records/audit-record",
                    headers=self._headers(token),
                )
                self.assertEqual(delete_response.status_code, 200, delete_response.get_json())

        token_value = self._create_token_fixture(token, f"audit-token-{secrets.token_hex(6)}")
        failed_consume = self._consume_token(
            token,
            token_value,
            simulate_failure=True,
            failure_stage="before_commit",
        )
        self.assertEqual(failed_consume.status_code, 500, failed_consume.get_json())

        successful_consume = self._consume_token(
            token,
            token_value,
            simulate_failure=False,
        )
        self.assertEqual(successful_consume.status_code, 200, successful_consume.get_json())

        new_logs = self._audit_logs_after(baseline_id)
        self.assertGreater(len(new_logs), 0)

        def audit_count(action, status):
            return sum(
                1
                for row in new_logs
                if row["action"] == action and row["status"] == status
            )

        self.assertGreaterEqual(audit_count("create_database", "success"), 1)
        self.assertGreaterEqual(audit_count("create_table", "success"), 1)
        self.assertGreaterEqual(audit_count("insert_record", "success"), 1)
        self.assertGreaterEqual(audit_count("update_record", "success"), 1)
        self.assertGreaterEqual(audit_count("delete_record", "success"), 1)
        self.assertGreaterEqual(audit_count("consume_token", "failed"), 1)
        self.assertGreaterEqual(audit_count("consume_token", "success"), 1)

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            test_activity_rows = conn.execute(
                """
                SELECT action, status, target
                FROM audit_logs
                WHERE action IN ('test_case', 'test_suite')
                ORDER BY id DESC
                LIMIT 200
                """
            ).fetchall()

        self.assertTrue(
            any(
                row["action"] == "test_case"
                and row["status"] in {"started", "success", "failed", "error"}
                and row["target"] == "module_b_tests"
                for row in test_activity_rows
            )
        )

        self.assertTrue(
            any(
                row["action"] == "test_suite"
                and row["status"] in {"started", "success", "failed"}
                and row["target"] == "module_b_tests"
                for row in test_activity_rows
            )
        )

    def test_high_volume_parallel_insert_stress(self):
        token = self._admin_token()
        db_name, table_name = deterministic_workspace_names(self.id(), namespace="stress_parallel")
        ramp_profile = get_stress_profile("ramp")

        request_count = ramp_profile.users * 4
        worker_count = ramp_profile.spawn_rate * 2

        with managed_stress_workspace(
            test_case=self,
            app=app,
            token=token,
            db_name=db_name,
            table_name=table_name,
            schema=["id", "payload"],
            search_key="id",
        ) as workspace:
            def insert_worker(index):
                started_at = time.perf_counter()
                with app.test_client() as client:
                    response = client.post(
                        f"/api/databases/{workspace.db_name}/tables/{workspace.table_name}/records",
                        headers=self._headers(token),
                        json={"id": str(index), "payload": f"load-{index}"},
                    )
                elapsed_ms = (time.perf_counter() - started_at) * 1000
                return response.status_code, elapsed_ms

            with self.__class__._telemetry_phase(
                "high_volume_parallel_insert_stress",
                context={
                    "db_name": workspace.db_name,
                    "table_name": workspace.table_name,
                    "request_count": request_count,
                    "worker_count": worker_count,
                },
            ):
                started_at = time.perf_counter()
                with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
                    outcomes = list(executor.map(insert_worker, range(1, request_count + 1)))
                elapsed = time.perf_counter() - started_at

            statuses = [status for status, _ in outcomes]
            latencies_ms = [latency for _, latency in outcomes]

            self.assertEqual(sum(1 for status in statuses if status == 201), request_count)

            with app.test_client() as client:
                records_response = client.get(
                    f"/api/databases/{workspace.db_name}/tables/{workspace.table_name}/records",
                    headers=self._headers(token),
                )
            body = records_response.get_json() or {}
            self.assertEqual(records_response.status_code, 200)
            self.assertEqual(body.get("count"), request_count)

            avg_ms = (elapsed / request_count) * 1000
            self.assertLess(avg_ms, 250)

            assert_table_phase_invariants(
                test_case=self,
                app=app,
                db_path=DB_PATH,
                token=token,
                db_name=workspace.db_name,
                table_name=workspace.table_name,
                phase_name="high_volume_parallel_insert_stress",
                expected_count=request_count,
                key_field="id",
            )

            self.__class__._persist_phase_metrics(
                phase_name="high_volume_parallel_insert_stress",
                statuses=statuses,
                latencies_ms=latencies_ms,
                phase_duration_seconds=elapsed,
                success_statuses={201},
                context={
                    "db_name": workspace.db_name,
                    "table_name": workspace.table_name,
                    "request_count": request_count,
                    "worker_count": worker_count,
                },
            )

    def test_many_unique_token_consumptions_under_load(self):
        token = self._admin_token()
        token_count = get_seed_size("medium")
        spike_profile = get_stress_profile("spike")
        token_values = [
            self._create_token_fixture(token, f"stress-token-{secrets.token_hex(6)}")
            for _ in range(token_count)
        ]

        def consume_worker(token_value):
            started_at = time.perf_counter()
            response = self._consume_token(token, token_value, simulate_failure=False)
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            return response.status_code, elapsed_ms

        with self.__class__._telemetry_phase(
            "many_unique_token_consumptions_under_load",
            context={
                "token_count": token_count,
                "worker_count": spike_profile.spawn_rate,
            },
        ):
            phase_started_at = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=spike_profile.spawn_rate) as executor:
                outcomes = list(executor.map(consume_worker, token_values))
            phase_duration_seconds = time.perf_counter() - phase_started_at

        statuses = [status for status, _ in outcomes]
        latencies_ms = [latency for _, latency in outcomes]

        self.assertEqual(sum(1 for status in statuses if status == 200), len(token_values))

        self.__class__._persist_phase_metrics(
            phase_name="many_unique_token_consumptions_under_load",
            statuses=statuses,
            latencies_ms=latencies_ms,
            phase_duration_seconds=phase_duration_seconds,
            success_statuses={200},
            context={
                "token_count": token_count,
                "worker_count": spike_profile.spawn_rate,
            },
        )

    def test_thousands_scale_insert_metrics(self):
        token = self._admin_token()
        db_name, table_name = deterministic_workspace_names(self.id(), namespace="stress_scale")
        baseline_profile = get_stress_profile("baseline")
        breakpoint_profile = get_stress_profile("breakpoint")

        request_count = breakpoint_profile.users * 2
        worker_count = baseline_profile.users

        with managed_stress_workspace(
            test_case=self,
            app=app,
            token=token,
            db_name=db_name,
            table_name=table_name,
            schema=["id", "payload"],
            search_key="id",
        ) as workspace:
            def insert_worker(index):
                started_at = time.perf_counter()
                with app.test_client() as client:
                    response = client.post(
                        f"/api/databases/{workspace.db_name}/tables/{workspace.table_name}/records",
                        headers=self._headers(token),
                        json={"id": str(index), "payload": f"payload-{index}"},
                    )
                elapsed_ms = (time.perf_counter() - started_at) * 1000
                return response.status_code, elapsed_ms

            with self.__class__._telemetry_phase(
                "thousands_scale_insert_metrics",
                context={
                    "db_name": workspace.db_name,
                    "table_name": workspace.table_name,
                    "request_count": request_count,
                    "worker_count": worker_count,
                },
            ):
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
                    f"/api/databases/{workspace.db_name}/tables/{workspace.table_name}/records",
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

            self.assertGreaterEqual(success_rate, DEFAULT_STRESS_THRESHOLDS.minimum_success_rate)
            self.assertEqual(invariant_violations, DEFAULT_STRESS_THRESHOLDS.maximum_invariant_violations)
            self.assertLess(average_latency_ms, 500)
            self.assertLess(p95_latency_ms, DEFAULT_STRESS_THRESHOLDS.maximum_p95_latency_ms)
            self.assertLess(total_duration_seconds, 90)

            assert_table_phase_invariants(
                test_case=self,
                app=app,
                db_path=DB_PATH,
                token=token,
                db_name=workspace.db_name,
                table_name=workspace.table_name,
                phase_name="thousands_scale_insert_metrics",
                expected_count=request_count,
                key_field="id",
            )

            self.__class__._persist_phase_metrics(
                phase_name="thousands_scale_insert_metrics",
                statuses=statuses,
                latencies_ms=latencies_ms,
                phase_duration_seconds=total_duration_seconds,
                success_statuses={201},
                context={
                    "db_name": workspace.db_name,
                    "table_name": workspace.table_name,
                    "request_count": request_count,
                    "worker_count": worker_count,
                    "success_rate": success_rate,
                    "invariant_violations": invariant_violations,
                },
            )

    def test_hotspot_contention_detects_no_lost_updates_or_duplicate_commits(self):
        token = self._admin_token()
        db_name, table_name = deterministic_workspace_names(self.id(), namespace="stress_hotspot")
        spike_profile = get_stress_profile("spike")

        shared_record_id = "shared-hotspot-record"
        duplicate_record_id = "duplicate-hotspot-record"

        with managed_stress_workspace(
            test_case=self,
            app=app,
            token=token,
            db_name=db_name,
            table_name=table_name,
            schema=["id", "value"],
            search_key="id",
        ) as workspace:
            with app.test_client() as client:
                seed_response = client.post(
                    f"/api/databases/{workspace.db_name}/tables/{workspace.table_name}/records",
                    headers=self._headers(token),
                    json={"id": shared_record_id, "value": "seed-value"},
                )
            self.assertEqual(seed_response.status_code, 201, seed_response.get_json())

            update_attempts = 180

            def update_worker(index):
                payload_value = f"hotspot-update-{index:04d}"
                started_at = time.perf_counter()
                with app.test_client() as client:
                    response = client.put(
                        f"/api/databases/{workspace.db_name}/tables/{workspace.table_name}/records/{shared_record_id}",
                        headers=self._headers(token),
                        json={"value": payload_value},
                    )
                completed_at = time.perf_counter()
                elapsed_ms = (completed_at - started_at) * 1000
                return response.status_code, payload_value, elapsed_ms, completed_at

            with self.__class__._telemetry_phase(
                "hotspot_parallel_updates",
                context={
                    "db_name": workspace.db_name,
                    "table_name": workspace.table_name,
                    "target_record": shared_record_id,
                    "attempts": update_attempts,
                    "worker_count": spike_profile.spawn_rate,
                },
            ):
                update_phase_started_at = time.perf_counter()
                with concurrent.futures.ThreadPoolExecutor(max_workers=spike_profile.spawn_rate) as executor:
                    update_outcomes = list(executor.map(update_worker, range(1, update_attempts + 1)))
                update_phase_duration_seconds = time.perf_counter() - update_phase_started_at

            self.assertTrue(all(status == 200 for status, _, _, _ in update_outcomes))

            update_statuses = [status for status, _, _, _ in update_outcomes]
            update_latencies_ms = [latency for _, _, latency, _ in update_outcomes]

            successful_updates = [
                (completed_at, payload_value)
                for status, payload_value, _, completed_at in update_outcomes
                if status == 200
            ]
            self.assertEqual(len(successful_updates), update_attempts)
            successful_update_values = {payload_value for _, payload_value in successful_updates}

            with app.test_client() as client:
                final_record_response = client.get(
                    f"/api/databases/{workspace.db_name}/tables/{workspace.table_name}/records/{shared_record_id}",
                    headers=self._headers(token),
                )
            self.assertEqual(final_record_response.status_code, 200)
            final_record_body = final_record_response.get_json() or {}
            final_record_data = final_record_body.get("data", {})
            self.assertEqual(final_record_data.get("id"), shared_record_id)
            self.assertIn(final_record_data.get("value"), successful_update_values)

            create_attempts = 90

            def create_duplicate_worker(index):
                payload_value = f"duplicate-value-{index:03d}"
                started_at = time.perf_counter()
                with app.test_client() as client:
                    response = client.post(
                        f"/api/databases/{workspace.db_name}/tables/{workspace.table_name}/records",
                        headers=self._headers(token),
                        json={"id": duplicate_record_id, "value": payload_value},
                    )
                elapsed_ms = (time.perf_counter() - started_at) * 1000
                return response.status_code, elapsed_ms

            with self.__class__._telemetry_phase(
                "hotspot_duplicate_creates",
                context={
                    "db_name": workspace.db_name,
                    "table_name": workspace.table_name,
                    "target_record": duplicate_record_id,
                    "attempts": create_attempts,
                    "worker_count": spike_profile.spawn_rate,
                },
            ):
                create_phase_started_at = time.perf_counter()
                with concurrent.futures.ThreadPoolExecutor(max_workers=spike_profile.spawn_rate) as executor:
                    create_outcomes = list(executor.map(create_duplicate_worker, range(1, create_attempts + 1)))
                create_phase_duration_seconds = time.perf_counter() - create_phase_started_at

            create_statuses = [status for status, _ in create_outcomes]
            create_latencies_ms = [latency for _, latency in create_outcomes]

            duplicate_commit_successes = sum(1 for status in create_statuses if status == 201)
            duplicate_commit_conflicts = sum(1 for status in create_statuses if status == 400)
            self.assertEqual(duplicate_commit_successes, 1)
            self.assertEqual(duplicate_commit_conflicts, create_attempts - 1)

            with app.test_client() as client:
                records_response = client.get(
                    f"/api/databases/{workspace.db_name}/tables/{workspace.table_name}/records",
                    headers=self._headers(token),
                )
            records_body = records_response.get_json() or {}
            records = records_body.get("records", [])

            self.assertEqual(records_response.status_code, 200)
            self.assertEqual(records_body.get("count"), len(records))

            record_ids = [str(item.get("data", {}).get("id")) for item in records]
            self.assertEqual(len(record_ids), len(set(record_ids)))
            self.assertEqual(record_ids.count(duplicate_record_id), 1)
            self.assertEqual(record_ids.count(shared_record_id), 1)

            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                duplicate_counts = conn.execute(
                    """
                    SELECT COUNT(*) AS total, COUNT(DISTINCT record_key) AS distinct_keys
                    FROM project_records
                    WHERE database_name = ? AND table_name = ?
                    """,
                    (workspace.db_name, workspace.table_name),
                ).fetchone()

            self.assertIsNotNone(duplicate_counts)
            self.assertEqual(duplicate_counts["total"], duplicate_counts["distinct_keys"])

            assert_table_phase_invariants(
                test_case=self,
                app=app,
                db_path=DB_PATH,
                token=token,
                db_name=workspace.db_name,
                table_name=workspace.table_name,
                phase_name="hotspot_contention",
                expected_count=2,
                key_field="id",
            )

            self.__class__._persist_phase_metrics(
                phase_name="hotspot_parallel_updates",
                statuses=update_statuses,
                latencies_ms=update_latencies_ms,
                phase_duration_seconds=update_phase_duration_seconds,
                success_statuses={200},
                context={
                    "db_name": workspace.db_name,
                    "table_name": workspace.table_name,
                    "target_record": shared_record_id,
                    "attempts": update_attempts,
                    "worker_count": spike_profile.spawn_rate,
                },
            )

            self.__class__._persist_phase_metrics(
                phase_name="hotspot_duplicate_creates",
                statuses=create_statuses,
                latencies_ms=create_latencies_ms,
                phase_duration_seconds=create_phase_duration_seconds,
                success_statuses={201, 400},
                context={
                    "db_name": workspace.db_name,
                    "table_name": workspace.table_name,
                    "target_record": duplicate_record_id,
                    "attempts": create_attempts,
                    "worker_count": spike_profile.spawn_rate,
                    "create_successes": duplicate_commit_successes,
                    "create_conflicts": duplicate_commit_conflicts,
                },
            )

    def test_failure_injection_under_parallel_load_rolls_back_and_retry_succeeds(self):
        token = self._admin_token()
        failure_profile = get_stress_profile("failure_under_load")
        failure_stages = [
            "before_status_update",
            "after_token_update",
            "before_commit",
        ]

        failing_count = get_seed_size("small")
        success_count = get_seed_size("small")

        failing_tokens = []
        for index in range(failing_count):
            stage = failure_stages[index % len(failure_stages)]
            token_value = self._create_token_fixture(token, f"load-fail-{stage}-{secrets.token_hex(6)}")
            before_state = self._snapshot_token_transaction_state(token, token_value)
            failing_tokens.append((token_value, stage, before_state))

        successful_tokens = []
        for index in range(success_count):
            token_value = self._create_token_fixture(token, f"load-success-{index}-{secrets.token_hex(6)}")
            before_state = self._snapshot_token_transaction_state(token, token_value)
            successful_tokens.append((token_value, before_state))

        def failing_worker(token_and_stage):
            token_value, stage, before_state = token_and_stage
            started_at = time.perf_counter()
            response = self._consume_token(
                token,
                token_value,
                simulate_failure=True,
                failure_stage=stage,
            )
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            return token_value, stage, before_state, response.status_code, elapsed_ms

        def success_worker(token_and_before_state):
            token_value, before_state = token_and_before_state
            started_at = time.perf_counter()
            response = self._consume_token(
                token,
                token_value,
                simulate_failure=False,
            )
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            return token_value, before_state, response.status_code, elapsed_ms

        with self.__class__._telemetry_phase(
            "failure_under_parallel_load_concurrent",
            context={
                "failing_token_count": failing_count,
                "successful_token_count": success_count,
                "worker_count": max(6, failure_profile.spawn_rate * 2),
            },
        ):
            concurrent_phase_started_at = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=max(6, failure_profile.spawn_rate * 2)) as executor:
                failing_futures = [executor.submit(failing_worker, item) for item in failing_tokens]
                success_futures = [executor.submit(success_worker, item) for item in successful_tokens]

                failing_outcomes = [future.result() for future in failing_futures]
                success_outcomes = [future.result() for future in success_futures]
            concurrent_phase_duration_seconds = time.perf_counter() - concurrent_phase_started_at

        self.assertTrue(all(status == 500 for _, _, _, status, _ in failing_outcomes))
        self.assertTrue(all(status == 200 for _, _, status, _ in success_outcomes))

        failing_statuses = [status for _, _, _, status, _ in failing_outcomes]
        failing_latencies_ms = [latency for _, _, _, _, latency in failing_outcomes]
        success_statuses = [status for _, _, status, _ in success_outcomes]
        success_latencies_ms = [latency for _, _, _, latency in success_outcomes]

        failed_after_states = {}
        for token_value, _, before_state, _, _ in failing_outcomes:
            failed_state = self._snapshot_token_transaction_state(token, token_value)
            self.assertEqual(failed_state["token_status"], "ACTIVE")
            self.assertEqual(failed_state["download_count"], 0)
            self.assertEqual(failed_state["upload_status"], "ACTIVE")
            failed_after_states[token_value] = failed_state

            assert_token_state_transition(
                test_case=self,
                phase_name="failure_under_parallel_load_rollback",
                before_state=before_state,
                after_state=failed_state,
                expected_before={"token_status": "ACTIVE", "download_count": 0, "upload_status": "ACTIVE"},
                expected_after={"token_status": "ACTIVE", "download_count": 0, "upload_status": "ACTIVE"},
            )

        for token_value, before_state, _, _ in success_outcomes:
            success_state = self._snapshot_token_transaction_state(token, token_value)
            self.assertEqual(success_state["token_status"], "USED")
            self.assertEqual(success_state["download_count"], 1)
            self.assertEqual(success_state["upload_status"], "DOWNLOADED")

            assert_token_state_transition(
                test_case=self,
                phase_name="success_under_parallel_load_transition",
                before_state=before_state,
                after_state=success_state,
                expected_before={"token_status": "ACTIVE", "download_count": 0, "upload_status": "ACTIVE"},
                expected_after={"token_status": "USED", "download_count": 1, "upload_status": "DOWNLOADED"},
            )

        retry_statuses = []
        retry_latencies_ms = []
        idempotency_statuses = []
        idempotency_latencies_ms = []

        with self.__class__._telemetry_phase(
            "failure_under_parallel_load_retry",
            context={"retry_token_count": failing_count},
        ):
            for token_value, _, _, _, _ in failing_outcomes:
                retry_started_at = time.perf_counter()
                retry_response = self._consume_token(
                    token,
                    token_value,
                    simulate_failure=False,
                )
                retry_elapsed_ms = (time.perf_counter() - retry_started_at) * 1000
                self.assertEqual(retry_response.status_code, 200, retry_response.get_json())
                retry_statuses.append(retry_response.status_code)
                retry_latencies_ms.append(retry_elapsed_ms)

                retry_state = self._snapshot_token_transaction_state(token, token_value)
                self.assertEqual(retry_state["token_status"], "USED")
                self.assertEqual(retry_state["download_count"], 1)
                self.assertEqual(retry_state["upload_status"], "DOWNLOADED")

                assert_token_state_transition(
                    test_case=self,
                    phase_name="retry_after_failure_transition",
                    before_state=failed_after_states[token_value],
                    after_state=retry_state,
                    expected_before={"token_status": "ACTIVE", "download_count": 0, "upload_status": "ACTIVE"},
                    expected_after={"token_status": "USED", "download_count": 1, "upload_status": "DOWNLOADED"},
                )

                second_retry_started_at = time.perf_counter()
                second_retry_response = self._consume_token(
                    token,
                    token_value,
                    simulate_failure=False,
                )
                self.assertEqual(second_retry_response.status_code, 409, second_retry_response.get_json())
                idempotency_elapsed_ms = (time.perf_counter() - second_retry_started_at) * 1000
                idempotency_statuses.append(second_retry_response.status_code)
                idempotency_latencies_ms.append(idempotency_elapsed_ms)

                final_state = self._snapshot_token_transaction_state(token, token_value)
                assert_token_state_transition(
                    test_case=self,
                    phase_name="retry_idempotency_transition",
                    before_state=retry_state,
                    after_state=final_state,
                    expected_before={"token_status": "USED", "download_count": 1, "upload_status": "DOWNLOADED"},
                    expected_after={"token_status": "USED", "download_count": 1, "upload_status": "DOWNLOADED"},
                )

        self.__class__._persist_phase_metrics(
            phase_name="failure_injection_parallel_path",
            statuses=failing_statuses,
            latencies_ms=failing_latencies_ms,
            phase_duration_seconds=concurrent_phase_duration_seconds,
            success_statuses={500},
            context={
                "token_count": failing_count,
                "worker_count": max(6, failure_profile.spawn_rate * 2),
            },
        )

        self.__class__._persist_phase_metrics(
            phase_name="success_parallel_path",
            statuses=success_statuses,
            latencies_ms=success_latencies_ms,
            phase_duration_seconds=concurrent_phase_duration_seconds,
            success_statuses={200},
            context={
                "token_count": success_count,
                "worker_count": max(6, failure_profile.spawn_rate * 2),
            },
        )

        self.__class__._persist_phase_metrics(
            phase_name="retry_after_failure_path",
            statuses=retry_statuses,
            latencies_ms=retry_latencies_ms,
            phase_duration_seconds=sum(retry_latencies_ms) / 1000 if retry_latencies_ms else 0.0,
            success_statuses={200},
            context={"token_count": failing_count},
        )

        self.__class__._persist_phase_metrics(
            phase_name="retry_idempotency_path",
            statuses=idempotency_statuses,
            latencies_ms=idempotency_latencies_ms,
            phase_duration_seconds=sum(idempotency_latencies_ms) / 1000 if idempotency_latencies_ms else 0.0,
            success_statuses={409},
            context={"token_count": failing_count},
        )

    def test_sustained_read_stress_consistency(self):
        token = self._admin_token()
        db_name, table_name = deterministic_workspace_names(self.id(), namespace="stress_read")
        soak_profile = get_stress_profile("soak")

        with managed_stress_workspace(
            test_case=self,
            app=app,
            token=token,
            db_name=db_name,
            table_name=table_name,
            schema=["id", "value"],
            search_key="id",
            seed_size_name="large",
            seed_payload_key="value",
            seed_payload_prefix="seed",
        ) as workspace:
            iterations = soak_profile.duration_seconds
            statuses = []
            latencies_ms = []
            with self.__class__._telemetry_phase(
                "sustained_read_stress_consistency",
                context={
                    "db_name": workspace.db_name,
                    "table_name": workspace.table_name,
                    "iterations": iterations,
                    "seeded_count": workspace.seeded_count,
                },
            ):
                started_at = time.perf_counter()
                for _ in range(iterations):
                    read_started_at = time.perf_counter()
                    with app.test_client() as client:
                        response = client.get(
                            f"/api/databases/{workspace.db_name}/tables/{workspace.table_name}/records",
                            headers=self._headers(token),
                        )
                        read_elapsed_ms = (time.perf_counter() - read_started_at) * 1000
                        body = response.get_json() or {}
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(body.get("count"), workspace.seeded_count)
                        statuses.append(response.status_code)
                        latencies_ms.append(read_elapsed_ms)
                elapsed = time.perf_counter() - started_at

            avg_ms = (elapsed / iterations) * 1000
            self.assertLess(avg_ms, 300)

            assert_table_phase_invariants(
                test_case=self,
                app=app,
                db_path=DB_PATH,
                token=token,
                db_name=workspace.db_name,
                table_name=workspace.table_name,
                phase_name="sustained_read_stress_consistency",
                expected_count=workspace.seeded_count,
                key_field="id",
            )

            self.__class__._persist_phase_metrics(
                phase_name="sustained_read_stress_consistency",
                statuses=statuses,
                latencies_ms=latencies_ms,
                phase_duration_seconds=elapsed,
                success_statuses={200},
                context={
                    "db_name": workspace.db_name,
                    "table_name": workspace.table_name,
                    "iterations": iterations,
                    "seeded_count": workspace.seeded_count,
                },
            )


if __name__ == "__main__":
    import unittest

    unittest.main()
