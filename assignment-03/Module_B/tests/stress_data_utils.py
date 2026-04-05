from contextlib import contextmanager
from dataclasses import dataclass
import re
from typing import Iterator


SEED_SIZES = {
    "small": 40,
    "medium": 120,
    "large": 300,
}


@dataclass(frozen=True)
class StressWorkspace:
    db_name: str
    table_name: str
    seeded_count: int


def get_seed_size(size_name: str) -> int:
    try:
        return SEED_SIZES[size_name]
    except KeyError as exc:
        available = ", ".join(sorted(SEED_SIZES.keys()))
        raise ValueError(f"Unknown seed size '{size_name}'. Available: {available}") from exc


def deterministic_workspace_names(test_id: str, namespace: str = "stress") -> tuple[str, str]:
    method_name = test_id.split(".")[-1]
    normalized = re.sub(r"[^a-z0-9]+", "_", method_name.lower()).strip("_")
    suffix = normalized or "case"
    return f"{namespace}_{suffix}_db", f"{namespace}_{suffix}_table"


def _delete_database_best_effort(test_case, app, token: str, db_name: str, strict: bool) -> None:
    with app.test_client() as client:
        response = client.delete(
            f"/api/databases/{db_name}",
            headers=test_case._headers(token),
        )

    allowed_statuses = {200, 404}
    if response.status_code in allowed_statuses:
        return

    message = (
        f"database cleanup status {response.status_code} for '{db_name}'"
        f" with body={response.get_json()}"
    )
    if strict:
        test_case.fail(message)

    test_case.__class__._append_result_line(f"[WARN] {message}\n")


def seed_table_records(
    test_case,
    app,
    token: str,
    db_name: str,
    table_name: str,
    size_name: str,
    payload_key: str,
    payload_prefix: str,
) -> int:
    total_records = get_seed_size(size_name)

    with app.test_client() as client:
        for index in range(1, total_records + 1):
            response = client.post(
                f"/api/databases/{db_name}/tables/{table_name}/records",
                headers=test_case._headers(token),
                json={
                    "id": str(index),
                    payload_key: f"{payload_prefix}-{index}",
                },
            )
            test_case.assertEqual(response.status_code, 201, response.get_json())

    return total_records


@contextmanager
def managed_stress_workspace(
    test_case,
    app,
    token: str,
    db_name: str,
    table_name: str,
    schema: list[str],
    search_key: str,
    seed_size_name: str | None = None,
    seed_payload_key: str = "value",
    seed_payload_prefix: str = "seed",
) -> Iterator[StressWorkspace]:
    seeded_count = 0

    # Pre-cleaning keeps setup deterministic if a prior run left residue.
    _delete_database_best_effort(test_case, app, token, db_name, strict=True)

    try:
        with app.test_client() as client:
            db_response = client.post(
                "/api/databases",
                headers=test_case._headers(token),
                json={"name": db_name},
            )
            test_case.assertEqual(db_response.status_code, 201, db_response.get_json())

            table_response = client.post(
                f"/api/databases/{db_name}/tables",
                headers=test_case._headers(token),
                json={"name": table_name, "schema": schema, "search_key": search_key},
            )
            test_case.assertEqual(table_response.status_code, 201, table_response.get_json())

        if seed_size_name is not None:
            seeded_count = seed_table_records(
                test_case=test_case,
                app=app,
                token=token,
                db_name=db_name,
                table_name=table_name,
                size_name=seed_size_name,
                payload_key=seed_payload_key,
                payload_prefix=seed_payload_prefix,
            )

        yield StressWorkspace(
            db_name=db_name,
            table_name=table_name,
            seeded_count=seeded_count,
        )
    finally:
        # Cleanup runs regardless of assertion failures inside the context body.
        _delete_database_best_effort(test_case, app, token, db_name, strict=False)
