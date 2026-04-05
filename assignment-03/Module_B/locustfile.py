import os
import uuid
from collections import deque

from locust import HttpUser, between, task
from locust.exception import StopUser


class BlindDropModuleBUser(HttpUser):
    abstract = True
    wait_time = between(
        float(os.getenv("LOCUST_WAIT_MIN", "0.1")),
        float(os.getenv("LOCUST_WAIT_MAX", "0.8")),
    )

    username = os.getenv("LOCUST_USERNAME", "admin")
    password = os.getenv("LOCUST_PASSWORD", "admin123")
    database_name = os.getenv("LOCUST_DB_NAME", "locust_blinddrop")
    table_name = os.getenv("LOCUST_TABLE_NAME", "locust_workload")

    def on_start(self):
        self._token = None
        self._session_tag = f"{self.__class__.__name__.lower()}-{uuid.uuid4().hex[:8]}"
        self._known_record_ids = deque(maxlen=500)

        self._authenticate()
        self._ensure_workload_table()

    def _headers(self):
        if not self._token:
            return {}
        return {"Authorization": f"Bearer {self._token}"}

    def _response_json(self, response):
        try:
            return response.json() or {}
        except Exception:
            return {}

    def _authenticate(self):
        with self.client.post(
            "/api/auth/login",
            name="auth.login",
            json={"username": self.username, "password": self.password},
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(
                    f"login failed status={response.status_code} body={response.text[:300]}"
                )
                raise StopUser()

            body = self._response_json(response)
            token = body.get("token")
            if not token:
                response.failure("login response missing token")
                raise StopUser()

            self._token = token
            response.success()

    def _request(self, method, path, *, name, expected_statuses, **kwargs):
        request_fn = getattr(self.client, method.lower())
        with request_fn(
            path,
            name=name,
            headers=self._headers(),
            catch_response=True,
            **kwargs,
        ) as response:
            if response.status_code == 401:
                response.failure("session expired or unauthorized")
                self._authenticate()
                return None

            if response.status_code not in expected_statuses:
                response.failure(
                    f"unexpected status={response.status_code} expected={sorted(expected_statuses)} "
                    f"body={response.text[:300]}"
                )
                return response

            response.success()
            return response

    def _ensure_workload_table(self):
        db_resp = self._request(
            "POST",
            "/api/databases",
            name="workload.db.create_if_missing",
            expected_statuses={201, 400},
            json={"name": self.database_name},
        )
        if db_resp is None:
            raise StopUser()

        table_resp = self._request(
            "POST",
            f"/api/databases/{self.database_name}/tables",
            name="workload.table.create_if_missing",
            expected_statuses={201, 400},
            json={
                "name": self.table_name,
                "schema": ["id", "value", "profile"],
                "search_key": "id",
            },
        )
        if table_resp is None:
            raise StopUser()

    def _new_record_id(self):
        return f"{self._session_tag}-{uuid.uuid4().hex[:10]}"

    def _create_record(self):
        record_id = self._new_record_id()
        response = self._request(
            "POST",
            f"/api/databases/{self.database_name}/tables/{self.table_name}/records",
            name="records.create",
            expected_statuses={201},
            json={
                "id": record_id,
                "value": f"value-{record_id}",
                "profile": self.__class__.__name__,
            },
        )
        if response is not None and response.status_code == 201:
            self._known_record_ids.append(record_id)

    def _update_random_known_record(self):
        if not self._known_record_ids:
            self._create_record()
            return

        record_id = self._known_record_ids[-1]
        self._request(
            "PUT",
            f"/api/databases/{self.database_name}/tables/{self.table_name}/records/{record_id}",
            name="records.update",
            expected_statuses={200, 404},
            json={
                "value": f"updated-{uuid.uuid4().hex[:6]}",
                "profile": self.__class__.__name__,
            },
        )

    def _delete_random_known_record(self):
        if not self._known_record_ids:
            self._create_record()
            return

        record_id = self._known_record_ids.popleft()
        self._request(
            "DELETE",
            f"/api/databases/{self.database_name}/tables/{self.table_name}/records/{record_id}",
            name="records.delete",
            expected_statuses={200, 404},
        )

    def _token_consume_cycle(self):
        token_value = f"{self._session_tag}-token-{uuid.uuid4().hex[:8]}"
        created = self._request(
            "POST",
            "/api/resilience/token-fixtures",
            name="resilience.token.create",
            expected_statuses={201},
            json={
                "token_value": token_value,
                "expires_in_minutes": 30,
            },
        )
        if created is None:
            return

        self._request(
            "POST",
            "/api/resilience/consume-token",
            name="resilience.token.consume",
            expected_statuses={200},
            json={
                "token_value": token_value,
                "user_device_info": self._session_tag,
                "simulate_failure": False,
            },
        )

    def _list_databases(self):
        self._request(
            "GET",
            "/api/databases",
            name="databases.list",
            expected_statuses={200},
        )

    def _list_tables(self):
        self._request(
            "GET",
            f"/api/databases/{self.database_name}/tables",
            name="tables.list",
            expected_statuses={200},
        )

    def _list_records(self):
        self._request(
            "GET",
            f"/api/databases/{self.database_name}/tables/{self.table_name}/records",
            name="records.list",
            expected_statuses={200},
        )

    def _get_dashboard_summary(self):
        self._request(
            "GET",
            "/api/dashboard/summary",
            name="dashboard.summary",
            expected_statuses={200},
        )

    def _list_members(self):
        self._request(
            "GET",
            "/api/members",
            name="members.list",
            expected_statuses={200},
        )

    def _list_audit_logs(self):
        self._request(
            "GET",
            "/api/audit-logs",
            name="audit.logs.list",
            expected_statuses={200},
        )


class ReadHeavyJourney(BlindDropModuleBUser):
    weight = 5

    @task(7)
    def read_databases(self):
        self._list_databases()

    @task(7)
    def read_records(self):
        self._list_records()

    @task(5)
    def read_tables(self):
        self._list_tables()

    @task(4)
    def read_dashboard(self):
        self._get_dashboard_summary()

    @task(2)
    def read_members(self):
        self._list_members()

    @task(1)
    def write_smoke(self):
        self._create_record()


class BalancedJourney(BlindDropModuleBUser):
    weight = 3

    @task(4)
    def list_records(self):
        self._list_records()

    @task(4)
    def create_record(self):
        self._create_record()

    @task(3)
    def update_record(self):
        self._update_random_known_record()

    @task(3)
    def delete_record(self):
        self._delete_random_known_record()

    @task(2)
    def token_flow(self):
        self._token_consume_cycle()

    @task(2)
    def read_dashboard(self):
        self._get_dashboard_summary()

    @task(1)
    def read_audit_logs(self):
        self._list_audit_logs()


class WriteHeavyJourney(BlindDropModuleBUser):
    weight = 2

    @task(7)
    def create_record(self):
        self._create_record()

    @task(6)
    def update_record(self):
        self._update_random_known_record()

    @task(5)
    def delete_record(self):
        self._delete_random_known_record()

    @task(3)
    def token_flow(self):
        self._token_consume_cycle()

    @task(1)
    def read_records(self):
        self._list_records()
