import sqlite3


def _fail_if_violations(test_case, phase_name: str, violations: list[str]) -> None:
    if not violations:
        return
    joined = " | ".join(violations)
    test_case.fail(f"[{phase_name}] invariant violation: {joined}")


def assert_table_phase_invariants(
    *,
    test_case,
    app,
    db_path,
    token: str,
    db_name: str,
    table_name: str,
    phase_name: str,
    expected_count: int | None = None,
    key_field: str = "id",
) -> dict:
    violations: list[str] = []

    with app.test_client() as client:
        response = client.get(
            f"/api/databases/{db_name}/tables/{table_name}/records",
            headers=test_case._headers(token),
        )

    body = response.get_json() or {}
    records = body.get("records", [])
    reported_count = body.get("count")

    if response.status_code != 200:
        violations.append(f"records endpoint status={response.status_code}")

    if not isinstance(records, list):
        violations.append("records payload is not a list")
        records = []

    if reported_count != len(records):
        violations.append(
            f"reported_count={reported_count} does not match records_len={len(records)}"
        )

    if expected_count is not None and reported_count != expected_count:
        violations.append(
            f"expected_count={expected_count} but reported_count={reported_count}"
        )

    extracted_keys: list[str] = []
    partial_records = 0
    for item in records:
        data = item.get("data") if isinstance(item, dict) else None
        if not isinstance(data, dict):
            partial_records += 1
            continue

        key_value = data.get(key_field)
        if key_value is None or str(key_value).strip() == "":
            partial_records += 1
            continue

        extracted_keys.append(str(key_value))

    if partial_records > 0:
        violations.append(f"partial_records={partial_records}")

    if len(extracted_keys) != len(set(extracted_keys)):
        violations.append("duplicate_keys_found_in_api_payload")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        count_row = conn.execute(
            """
            SELECT COUNT(*) AS total, COUNT(DISTINCT record_key) AS distinct_keys
            FROM project_records
            WHERE database_name = ? AND table_name = ?
            """,
            (db_name, table_name),
        ).fetchone()

        orphan_row = conn.execute(
            """
            SELECT COUNT(*) AS orphan_count
            FROM project_records r
            LEFT JOIN project_tables t
              ON t.database_name = r.database_name
             AND t.table_name = r.table_name
            WHERE r.database_name = ?
              AND r.table_name = ?
              AND t.id IS NULL
            """,
            (db_name, table_name),
        ).fetchone()

    total_records = count_row["total"] if count_row is not None else None
    distinct_keys = count_row["distinct_keys"] if count_row is not None else None
    orphan_count = orphan_row["orphan_count"] if orphan_row is not None else None

    if count_row is None:
        violations.append("missing_db_count_row")
    else:
        if total_records != distinct_keys:
            violations.append(
                f"db_duplicate_keys total={total_records} distinct={distinct_keys}"
            )
        if expected_count is not None and total_records != expected_count:
            violations.append(
                f"db_total={total_records} differs_from_expected={expected_count}"
            )

    if orphan_row is None:
        violations.append("missing_db_orphan_row")
    elif orphan_count != 0:
        violations.append(f"orphan_records={orphan_count}")

    _fail_if_violations(test_case, phase_name, violations)

    return {
        "reported_count": reported_count,
        "records_len": len(records),
        "db_total": total_records,
        "db_distinct_keys": distinct_keys,
        "orphan_count": orphan_count,
    }


def assert_token_state_transition(
    *,
    test_case,
    phase_name: str,
    before_state: dict,
    after_state: dict,
    expected_before: dict | None = None,
    expected_after: dict | None = None,
) -> None:
    violations: list[str] = []

    if expected_before is not None:
        for key, expected in expected_before.items():
            observed = before_state.get(key)
            if observed != expected:
                violations.append(
                    f"before.{key} expected={expected} observed={observed}"
                )

    if expected_after is not None:
        for key, expected in expected_after.items():
            observed = after_state.get(key)
            if observed != expected:
                violations.append(
                    f"after.{key} expected={expected} observed={observed}"
                )

    token_status = after_state.get("token_status")
    upload_status = after_state.get("upload_status")
    download_count = after_state.get("download_count")

    valid_shape = (
        (token_status == "ACTIVE" and upload_status == "ACTIVE" and download_count == 0)
        or (token_status == "USED" and upload_status == "DOWNLOADED" and download_count == 1)
    )
    if not valid_shape:
        violations.append(
            "after_state has invalid status shape "
            f"(token_status={token_status}, upload_status={upload_status}, download_count={download_count})"
        )

    _fail_if_violations(test_case, phase_name, violations)
