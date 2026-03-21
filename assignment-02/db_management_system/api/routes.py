import hashlib
import json
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import Blueprint, Response, g, jsonify, request

from database.db_manager import DatabaseManager

api = Blueprint("api", __name__)
db_manager = DatabaseManager()

DB_PATH = Path(__file__).resolve().parent.parent / "module_b.sqlite3"
SESSION_HOURS = 8


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _compute_members_snapshot(conn):
    rows = conn.execute(
        """
        SELECT id, username, role, full_name, email, member_group, created_at
        FROM members
        ORDER BY id
        """
    ).fetchall()
    payload = [dict(row) for row in rows]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    snapshot_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return snapshot_hash, len(payload)


def _refresh_members_integrity_snapshot(conn, actor_id=None):
    snapshot_hash, row_count = _compute_members_snapshot(conn)
    conn.execute(
        """
        INSERT INTO integrity_snapshots (table_name, snapshot_hash, row_count, updated_at, updated_by)
        VALUES ('members', ?, ?, ?, ?)
        ON CONFLICT(table_name)
        DO UPDATE SET
            snapshot_hash = excluded.snapshot_hash,
            row_count = excluded.row_count,
            updated_at = excluded.updated_at,
            updated_by = excluded.updated_by
        """,
        (snapshot_hash, row_count, _now_iso(), actor_id),
    )


def _init_module_b_db():
    conn = _db_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                member_group TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                member_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(member_id) REFERENCES members(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(actor_id) REFERENCES members(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS integrity_snapshots (
                table_name TEXT PRIMARY KEY,
                snapshot_hash TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by INTEGER,
                FOREIGN KEY(updated_by) REFERENCES members(id)
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_members_username ON members(username)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_members_role ON members(role)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_member ON sessions(member_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at)"
        )

        admin_exists = cursor.execute(
            "SELECT id FROM members WHERE username = ?", ("admin",)
        ).fetchone()
        if admin_exists is None:
            cursor.execute(
                """
                INSERT INTO members (username, password_hash, role, full_name, email, member_group, created_at)
                VALUES (?, ?, 'admin', ?, ?, ?, ?)
                """,
                (
                    "admin",
                    _hash_password("admin123"),
                    "System Admin",
                    "admin@blinddrop.local",
                    "ops",
                    _now_iso(),
                ),
            )

        _refresh_members_integrity_snapshot(conn, actor_id=admin_exists["id"] if admin_exists else None)
        conn.commit()
    finally:
        conn.close()


def _write_audit(action, target, status, actor_id=None, details=None):
    conn = _db_conn()
    try:
        conn.execute(
            """
            INSERT INTO audit_logs (actor_id, action, target, status, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (actor_id, action, target, status, details, _now_iso()),
        )
        conn.commit()
    finally:
        conn.close()


def _extract_bearer_token():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip()


def require_session(handler):
    @wraps(handler)
    def wrapped(*args, **kwargs):
        token = _extract_bearer_token()
        if not token:
            return jsonify({"error": "Missing Bearer token"}), 401

        conn = _db_conn()
        try:
            row = conn.execute(
                """
                SELECT s.token, s.expires_at, m.id, m.username, m.role, m.full_name, m.email, m.member_group
                FROM sessions s
                JOIN members m ON m.id = s.member_id
                WHERE s.token = ?
                """,
                (token,),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return jsonify({"error": "Invalid session token"}), 401

        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            _write_audit("session_expired", "auth", "denied", row["id"], "Session expired")
            return jsonify({"error": "Session expired"}), 401

        g.current_member = {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
            "full_name": row["full_name"],
            "email": row["email"],
            "member_group": row["member_group"],
            "token": row["token"],
        }
        return handler(*args, **kwargs)

    return wrapped


def require_admin(handler):
    @wraps(handler)
    @require_session
    def wrapped(*args, **kwargs):
        if g.current_member["role"] != "admin":
            _write_audit(
                "rbac_denied",
                request.path,
                "denied",
                g.current_member["id"],
                "Admin role required",
            )
            return jsonify({"error": "Admin privileges required"}), 403
        return handler(*args, **kwargs)

    return wrapped


_init_module_b_db()


def _bootstrap_inmemory_db():
    if db_manager.list_databases():
        return

    db_manager.create_database("blinddrop_core")
    db_manager.create_table(
        "blinddrop_core",
        "member_cache",
        ["id", "full_name", "role"],
        search_key="id",
    )
    table, _ = db_manager.get_table("blinddrop_core", "member_cache")
    table.insert({"id": 1, "full_name": "System Admin", "role": "admin"})

    db_manager.create_table("blinddrop_core", "Member", ["memberID", "name", "age", "image", "email", "contactNumber"], search_key="memberID")
    db_manager.create_table("blinddrop_core", "Device", ["deviceID", "location", "deviceType", "ipAddress"], search_key="deviceID")
    db_manager.create_table("blinddrop_core", "ExpiryPolicy", ["policyID", "maxLifetimeMinutes", "deleteAfterFirstDownload"], search_key="policyID")
    db_manager.create_table("blinddrop_core", "UploadSession", ["sessionID", "deviceID", "policyID", "uploadTimestamp", "expiryTimestamp", "status"], search_key="sessionID")
    db_manager.create_table("blinddrop_core", "FileMetadata", ["fileID", "sessionID", "fileName", "fileSize", "mimeType", "checksum", "storagePath"], search_key="fileID")
    db_manager.create_table("blinddrop_core", "OneTimeToken", ["tokenID", "sessionID", "tokenValue", "createdAt", "expiryAt", "status"], search_key="tokenID")
    db_manager.create_table("blinddrop_core", "DownloadLog", ["downloadID", "tokenID", "downloadTime", "userDeviceInfo"], search_key="downloadID")
    db_manager.create_table("blinddrop_core", "RateLimitLog", ["requestID", "deviceID", "timestamp", "eventType"], search_key="requestID")
    db_manager.create_table("blinddrop_core", "FileIntegrityCheck", ["checkID", "fileID", "computedChecksum", "verified", "timestamp"], search_key="checkID")
    db_manager.create_table("blinddrop_core", "SystemAdmin", ["adminID", "name", "email"], search_key="adminID")
    db_manager.create_table("blinddrop_core", "ErrorLog", ["errorID", "sessionID", "errorMessage", "timestamp"], search_key="errorID")
    db_manager.create_table("blinddrop_core", "AuditTrail", ["auditID", "action", "sessionID", "timestamp"], search_key="auditID")


_bootstrap_inmemory_db()


@api.route("/auth/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    conn = _db_conn()
    try:
        member = conn.execute(
            "SELECT * FROM members WHERE username = ?", (username,)
        ).fetchone()
        if member is None or member["password_hash"] != _hash_password(password):
            _write_audit("login", "auth", "denied", None, f"username={username}")
            return jsonify({"error": "Invalid credentials"}), 401

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
        conn.execute(
            "INSERT INTO sessions (token, member_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (token, member["id"], expires_at.isoformat(), _now_iso()),
        )
        conn.commit()
    finally:
        conn.close()

    _write_audit("login", "auth", "success", member["id"], "Session started")
    return jsonify(
        {
            "token": token,
            "expires_at": expires_at.isoformat(),
            "member": {
                "id": member["id"],
                "username": member["username"],
                "role": member["role"],
                "full_name": member["full_name"],
                "email": member["email"],
                "member_group": member["member_group"],
            },
        }
    )


@api.route("/auth/logout", methods=["POST"])
@require_session
def logout():
    conn = _db_conn()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (g.current_member["token"],))
        conn.commit()
    finally:
        conn.close()

    _write_audit("logout", "auth", "success", g.current_member["id"], "Session ended")
    return jsonify({"message": "Logged out successfully"})


@api.route("/auth/me", methods=["GET"])
@require_session
def get_me():
    return jsonify({"member": g.current_member})


@api.route("/members", methods=["GET"])
@require_session
def list_members():
    conn = _db_conn()
    try:
        if g.current_member["role"] == "admin":
            rows = conn.execute(
                "SELECT id, username, role, full_name, email, member_group, created_at FROM members ORDER BY id"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, username, role, full_name, email, member_group, created_at FROM members WHERE id = ?",
                (g.current_member["id"],),
            ).fetchall()
    finally:
        conn.close()

    return jsonify({"members": [dict(r) for r in rows], "count": len(rows)})


@api.route("/members", methods=["POST"])
@require_admin
def create_member():
    payload = request.get_json(silent=True) or {}
    required_fields = ["username", "password", "full_name", "email", "role"]
    missing = [field for field in required_fields if not payload.get(field)]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    role = payload["role"].strip().lower()
    if role not in {"admin", "user"}:
        return jsonify({"error": "Role must be either 'admin' or 'user'"}), 400

    conn = _db_conn()
    try:
        conn.execute(
            """
            INSERT INTO members (username, password_hash, role, full_name, email, member_group, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["username"].strip(),
                _hash_password(payload["password"]),
                role,
                payload["full_name"].strip(),
                payload["email"].strip(),
                (payload.get("member_group") or "general").strip(),
                _now_iso(),
            ),
        )
        _refresh_members_integrity_snapshot(conn, actor_id=g.current_member["id"])
        conn.commit()
    except sqlite3.IntegrityError as exc:
        return jsonify({"error": f"Member already exists: {str(exc)}"}), 400
    finally:
        conn.close()

    _write_audit("create_member", "members", "success", g.current_member["id"], payload["username"])
    return jsonify({"message": "Member created successfully"}), 201


@api.route("/members/<int:member_id>", methods=["PUT"])
@require_session
def update_member(member_id):
    payload = request.get_json(silent=True) or {}
    current = g.current_member

    if current["role"] != "admin" and current["id"] != member_id:
        _write_audit("update_member", "members", "denied", current["id"], f"target={member_id}")
        return jsonify({"error": "You can only update your own profile"}), 403

    updates = []
    values = []
    updatable = ["full_name", "email", "member_group"]

    for field in updatable:
        if field in payload:
            updates.append(f"{field} = ?")
            values.append((payload[field] or "").strip())

    if "password" in payload and payload["password"]:
        updates.append("password_hash = ?")
        values.append(_hash_password(payload["password"]))

    if "role" in payload:
        if current["role"] != "admin":
            return jsonify({"error": "Only admins can modify roles"}), 403
        role = payload["role"].strip().lower()
        if role not in {"admin", "user"}:
            return jsonify({"error": "Role must be either 'admin' or 'user'"}), 400
        updates.append("role = ?")
        values.append(role)

    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    values.append(member_id)
    conn = _db_conn()
    try:
        cursor = conn.execute(
            f"UPDATE members SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "Member not found"}), 404
        _refresh_members_integrity_snapshot(conn, actor_id=current["id"])
        conn.commit()
    except sqlite3.IntegrityError as exc:
        return jsonify({"error": f"Update failed: {str(exc)}"}), 400
    finally:
        conn.close()

    _write_audit("update_member", "members", "success", current["id"], f"target={member_id}")
    return jsonify({"message": "Member updated successfully"})


@api.route("/members/<int:member_id>", methods=["DELETE"])
@require_admin
def delete_member(member_id):
    if g.current_member["id"] == member_id:
        return jsonify({"error": "You cannot delete your own active account"}), 400

    conn = _db_conn()
    try:
        conn.execute("DELETE FROM sessions WHERE member_id = ?", (member_id,))
        cursor = conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Member not found"}), 404
        _refresh_members_integrity_snapshot(conn, actor_id=g.current_member["id"])
        conn.commit()
    finally:
        conn.close()

    _write_audit("delete_member", "members", "success", g.current_member["id"], f"target={member_id}")
    return jsonify({"message": "Member deleted successfully"})


@api.route("/members/portfolio", methods=["GET"])
@require_session
def member_portfolio():
    conn = _db_conn()
    try:
        if g.current_member["role"] == "admin":
            rows = conn.execute(
                "SELECT id, username, full_name, email, role, member_group, created_at FROM members ORDER BY full_name"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, username, full_name, email, role, member_group, created_at FROM members WHERE id = ?",
                (g.current_member["id"],),
            ).fetchall()
    finally:
        conn.close()

    return jsonify({"portfolio": [dict(r) for r in rows], "count": len(rows)})


@api.route("/audit-logs", methods=["GET"])
@require_admin
def get_audit_logs():
    limit = request.args.get("limit", default=100, type=int)
    limit = min(max(limit, 1), 500)

    conn = _db_conn()
    try:
        rows = conn.execute(
            """
            SELECT a.id, a.action, a.target, a.status, a.details, a.created_at,
                   m.username AS actor_username, m.role AS actor_role
            FROM audit_logs a
            LEFT JOIN members m ON m.id = a.actor_id
            ORDER BY a.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    return jsonify({"logs": [dict(r) for r in rows], "count": len(rows)})


@api.route("/audit-logs/integrity", methods=["GET"])
@require_admin
def check_integrity():
    conn = _db_conn()
    try:
        saved = conn.execute(
            "SELECT table_name, snapshot_hash, row_count, updated_at, updated_by FROM integrity_snapshots WHERE table_name = 'members'"
        ).fetchone()
        current_hash, current_count = _compute_members_snapshot(conn)
    finally:
        conn.close()

    if saved is None:
        _write_audit(
            "integrity_check",
            "members",
            "warning",
            g.current_member["id"],
            "No baseline snapshot available",
        )
        return jsonify(
            {
                "table": "members",
                "status": "warning",
                "authorized": False,
                "message": "No baseline snapshot available. Initialize via API activity.",
            }
        )

    authorized = saved["snapshot_hash"] == current_hash and saved["row_count"] == current_count
    if not authorized:
        _write_audit(
            "direct_db_modification_detected",
            "members",
            "unauthorized",
            g.current_member["id"],
            json.dumps(
                {
                    "saved_hash": saved["snapshot_hash"],
                    "current_hash": current_hash,
                    "saved_row_count": saved["row_count"],
                    "current_row_count": current_count,
                }
            ),
        )

    return jsonify(
        {
            "table": "members",
            "status": "ok" if authorized else "unauthorized",
            "authorized": authorized,
            "baseline": {
                "hash": saved["snapshot_hash"],
                "row_count": saved["row_count"],
                "updated_at": saved["updated_at"],
                "updated_by": saved["updated_by"],
            },
            "current": {
                "hash": current_hash,
                "row_count": current_count,
            },
        }
    )


@api.route("/indexing/explain", methods=["GET"])
@require_admin
def explain_member_lookup():
    conn = _db_conn()
    try:
        query = "SELECT id, username, role FROM members WHERE username = ?"
        rows = conn.execute(f"EXPLAIN QUERY PLAN {query}", ("admin",)).fetchall()
    finally:
        conn.close()
    plan = [dict(r) for r in rows]
    return jsonify({"query": query, "plan": plan})


@api.route("/indexing/benchmark", methods=["GET"])
@require_admin
def benchmark_member_lookup():
    iterations = request.args.get("iterations", default=1000, type=int)
    iterations = min(max(iterations, 10), 20000)

    conn = _db_conn()
    try:
        start = time.perf_counter()
        for _ in range(iterations):
            conn.execute(
                "SELECT id, username, role FROM members WHERE username = ?",
                ("admin",),
            ).fetchone()
        elapsed = time.perf_counter() - start
    finally:
        conn.close()

    return jsonify(
        {
            "iterations": iterations,
            "query": "SELECT id, username, role FROM members WHERE username = ?",
            "total_seconds": elapsed,
            "avg_ms": (elapsed / iterations) * 1000,
        }
    )


@api.route("/indexing/benchmark-comparison", methods=["GET"])
@require_admin
def benchmark_index_comparison():
    iterations = request.args.get("iterations", default=1000, type=int)
    iterations = min(max(iterations, 10), 20000)

    conn = _db_conn()
    try:
        username_target = "admin"

        start = time.perf_counter()
        for _ in range(iterations):
            conn.execute(
                "SELECT id, username, role FROM members NOT INDEXED WHERE username = ?",
                (username_target,),
            ).fetchone()
        members_no_index = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(iterations):
            conn.execute(
                "SELECT id, username, role FROM members INDEXED BY idx_members_username WHERE username = ?",
                (username_target,),
            ).fetchone()
        members_indexed = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(iterations):
            conn.execute(
                "SELECT id, action, created_at FROM audit_logs NOT INDEXED ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
        audit_no_index = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(iterations):
            conn.execute(
                "SELECT id, action, created_at FROM audit_logs INDEXED BY idx_audit_created ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
        audit_indexed = time.perf_counter() - start
    finally:
        conn.close()

    def _result(name, no_idx, idx):
        return {
            "query": name,
            "iterations": iterations,
            "without_index": {
                "total_seconds": no_idx,
                "avg_ms": (no_idx / iterations) * 1000,
            },
            "with_index": {
                "total_seconds": idx,
                "avg_ms": (idx / iterations) * 1000,
            },
            "improvement_percent": ((no_idx - idx) / no_idx * 100) if no_idx > 0 else 0,
        }

    return jsonify(
        {
            "results": [
                _result("members lookup by username", members_no_index, members_indexed),
                _result("audit logs recent order", audit_no_index, audit_indexed),
            ]
        }
    )


@api.route('/databases', methods=['GET'])
@require_admin
def get_databases():
    databases = db_manager.list_databases()
    return jsonify({"databases": databases, "count": len(databases)})


@api.route('/databases/catalog', methods=['GET'])
@require_admin
def get_databases_catalog():
    databases = db_manager.list_databases()
    catalog = []

    for db_name in databases:
        tables, _ = db_manager.list_tables(db_name)
        table_names = tables or []
        catalog.append(
            {
                "name": db_name,
                "table_count": len(table_names),
                "tables": table_names,
            }
        )

    return jsonify({"catalog": catalog, "count": len(catalog)})


@api.route('/dashboard/summary', methods=['GET'])
@require_admin
def dashboard_summary():
    databases = db_manager.list_databases()
    total_tables = 0

    for db_name in databases:
        tables, _ = db_manager.list_tables(db_name)
        if tables is not None:
            total_tables += len(tables)

    conn = _db_conn()
    try:
        member_count = conn.execute("SELECT COUNT(*) AS count FROM members").fetchone()["count"]
        audit_count = conn.execute("SELECT COUNT(*) AS count FROM audit_logs").fetchone()["count"]
    finally:
        conn.close()

    return jsonify(
        {
            "database_count": len(databases),
            "table_count": total_tables,
            "member_count": member_count,
            "audit_count": audit_count,
        }
    )


@api.route('/databases', methods=['POST'])
@require_admin
def create_database():
    data = request.get_json(silent=True) or {}
    if 'name' not in data:
        return jsonify({"error": "Database name is required"}), 400

    success, message = db_manager.create_database(data['name'])
    _write_audit(
        "create_database",
        "dbms",
        "success" if success else "failed",
        g.current_member["id"],
        json.dumps({"database": data['name']}),
    )
    if success:
        return jsonify({"message": message}), 201
    return jsonify({"error": message}), 400


@api.route('/databases/<db_name>', methods=['DELETE'])
@require_admin
def delete_database(db_name):
    success, message = db_manager.delete_database(db_name)
    _write_audit(
        "delete_database",
        "dbms",
        "success" if success else "failed",
        g.current_member["id"],
        json.dumps({"database": db_name}),
    )
    if success:
        return jsonify({"message": message}), 200
    return jsonify({"error": message}), 404


@api.route('/databases/<db_name>/tables', methods=['GET'])
@require_session
def get_tables(db_name):
    tables, message = db_manager.list_tables(db_name)
    if tables is not None:
        return jsonify({"tables": tables, "count": len(tables)})
    return jsonify({"error": message}), 404


@api.route('/databases/<db_name>/tables', methods=['POST'])
@require_session
def create_table(db_name):
    data = request.get_json(silent=True) or {}
    if 'name' not in data or 'schema' not in data:
        return jsonify({"error": "Table name and schema are required"}), 400

    success, message = db_manager.create_table(db_name, data['name'], data['schema'])
    _write_audit(
        "create_table",
        "dbms",
        "success" if success else "failed",
        g.current_member["id"],
        json.dumps({"database": db_name, "table": data['name']}),
    )
    if success:
        return jsonify({"message": message}), 201
    return jsonify({"error": message}), 400


@api.route('/databases/<db_name>/tables/<table_name>', methods=['DELETE'])
@require_admin
def delete_table(db_name, table_name):
    success, message = db_manager.delete_table(db_name, table_name)
    _write_audit(
        "delete_table",
        "dbms",
        "success" if success else "failed",
        g.current_member["id"],
        json.dumps({"database": db_name, "table": table_name}),
    )
    if success:
        return jsonify({"message": message}), 200
    return jsonify({"error": message}), 404


@api.route('/databases/<db_name>/tables/<table_name>/records', methods=['GET'])
@require_session
def get_records(db_name, table_name):
    table, message = db_manager.get_table(db_name, table_name)
    if table is None:
        return jsonify({"error": message}), 404

    records, _ = table.get_all()
    formatted_records = [{"data": record_data} for record_data in records]
    return jsonify({"records": formatted_records, "count": len(formatted_records)})


@api.route('/databases/<db_name>/tables/<table_name>/records', methods=['POST'])
@require_session
def create_record(db_name, table_name):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Record data is required"}), 400

    table, message = db_manager.get_table(db_name, table_name)
    if table is None:
        return jsonify({"error": message}), 404

    if isinstance(data, list):
        results = []
        for record in data:
            success, result = table.insert(record)
            results.append({"status": "success" if success else "failed", "result": result})
        status = "success" if any(r["status"] == "success" for r in results) else "failed"
        _write_audit("insert_records", "dbms", status, g.current_member["id"], json.dumps({"database": db_name, "table": table_name, "count": len(data)}))
        return jsonify({"message": f"Processed {len(data)} records", "results": results}), 201

    success, result = table.insert(data)
    _write_audit(
        "insert_record",
        "dbms",
        "success" if success else "failed",
        g.current_member["id"],
        json.dumps({"database": db_name, "table": table_name}),
    )
    if success:
        return jsonify({"message": "Record created successfully", "result": result}), 201
    return jsonify({"error": result}), 400


@api.route('/databases/<db_name>/tables/<table_name>/records/<record_id>', methods=['GET'])
@require_session
def get_record(db_name, table_name, record_id):
    try:
        table, message = db_manager.get_table(db_name, table_name)
        if table is None:
            return jsonify({"error": message}), 404

        record, _ = table.get(record_id)
        if record:
            return jsonify({"id": record_id, "data": record})
        return jsonify({"error": "Record not found"}), 404
    except Exception as exc:
        return jsonify({"error": f"Internal server error: {str(exc)}"}), 500


@api.route('/databases/<db_name>/tables/<table_name>/records/<record_id>', methods=['PUT'])
@require_session
def update_record(db_name, table_name, record_id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Record data is required"}), 400

    table, message = db_manager.get_table(db_name, table_name)
    if table is None:
        return jsonify({"error": message}), 404

    success, result_message = table.update(record_id, data)
    _write_audit(
        "update_record",
        "dbms",
        "success" if success else "failed",
        g.current_member["id"],
        json.dumps({"database": db_name, "table": table_name, "record_id": record_id}),
    )
    if success:
        return jsonify({"message": result_message})
    return jsonify({"error": result_message}), 404


@api.route('/databases/<db_name>/tables/<table_name>/records/<record_id>', methods=['DELETE'])
@require_session
def delete_record(db_name, table_name, record_id):
    table, message = db_manager.get_table(db_name, table_name)
    if table is None:
        return jsonify({"error": message}), 404

    success, result_message = table.delete(record_id)
    _write_audit(
        "delete_record",
        "dbms",
        "success" if success else "failed",
        g.current_member["id"],
        json.dumps({"database": db_name, "table": table_name, "record_id": record_id}),
    )
    if success:
        return jsonify({"message": result_message})
    return jsonify({"error": result_message}), 404


@api.route('/databases/<db_name>/tables/<table_name>/range', methods=['POST'])
@require_session
def range_query(db_name, table_name):
    data = request.get_json(silent=True) or {}
    if 'start' not in data or 'end' not in data:
        return jsonify({"error": "Start and end values are required"}), 400

    table, message = db_manager.get_table(db_name, table_name)
    if table is None:
        return jsonify({"error": message}), 404

    results, _ = table.range_query(data['start'], data['end'])
    return jsonify({"records": [{"data": r} for r in results], "count": len(results)})


@api.route('/databases/<db_name>/tables/<table_name>/visualize', methods=['GET'])
@require_session
def visualize_tree(db_name, table_name):
    table, message = db_manager.get_table(db_name, table_name)
    if table is None:
        return jsonify({"error": message}), 404

    dot = table.data.visualize_tree()
    svg_data = dot.pipe(format='svg').decode('utf-8')
    return Response(svg_data, mimetype='image/svg+xml')
 
