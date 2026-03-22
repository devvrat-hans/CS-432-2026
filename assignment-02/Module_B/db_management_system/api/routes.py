import hashlib
import json
import logging
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import Blueprint, Response, g, jsonify, request
from graphviz import Digraph

api = Blueprint("api", __name__)

DB_PATH = Path(__file__).resolve().parent.parent / "module_b.sqlite3"
CORE_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema_core_tables.sql"
PROJECT_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema_project_tables.sql"
INDEXES_PATH = Path(__file__).resolve().parent.parent / "sql" / "indexes.sql"
AUDIT_LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "audit.log"
SESSION_HOURS = 8

AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
audit_logger = logging.getLogger("blinddrop.audit")
if not audit_logger.handlers:
    audit_logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(AUDIT_LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    audit_logger.addHandler(file_handler)
    audit_logger.propagate = False


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _normalize_member_group(value):
    cleaned = (value or "").strip()
    return cleaned or "general"


def _db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


DEFAULT_PROJECT_DATABASE = "blinddrop_core"
DEFAULT_PROJECT_TABLES = [
    {"name": "Member", "schema": ["memberID", "name", "age", "image", "email", "contactNumber"], "search_key": "memberID"},
    {"name": "Device", "schema": ["deviceID", "location", "deviceType", "ipAddress"], "search_key": "deviceID"},
    {"name": "ExpiryPolicy", "schema": ["policyID", "maxLifetimeMinutes", "deleteAfterFirstDownload"], "search_key": "policyID"},
    {"name": "UploadSession", "schema": ["sessionID", "deviceID", "policyID", "uploadTimestamp", "expiryTimestamp", "status"], "search_key": "sessionID"},
    {"name": "FileMetadata", "schema": ["fileID", "sessionID", "fileName", "fileSize", "mimeType", "checksum", "storagePath"], "search_key": "fileID"},
    {"name": "OneTimeToken", "schema": ["tokenID", "sessionID", "tokenValue", "createdAt", "expiryAt", "status"], "search_key": "tokenID"},
    {"name": "DownloadLog", "schema": ["downloadID", "tokenID", "downloadTime", "userDeviceInfo"], "search_key": "downloadID"},
    {"name": "RateLimitLog", "schema": ["requestID", "deviceID", "timestamp", "eventType"], "search_key": "requestID"},
    {"name": "FileIntegrityCheck", "schema": ["checkID", "fileID", "computedChecksum", "verified", "timestamp"], "search_key": "checkID"},
    {"name": "SystemAdmin", "schema": ["adminID", "name", "email"], "search_key": "adminID"},
    {"name": "ErrorLog", "schema": ["errorID", "sessionID", "errorMessage", "timestamp"], "search_key": "errorID"},
    {"name": "AuditTrail", "schema": ["auditID", "action", "sessionID", "timestamp"], "search_key": "auditID"},
]


def _bootstrap_project_catalog(conn, actor_id=None):
    database_count = conn.execute(
        "SELECT COUNT(*) AS count FROM project_databases"
    ).fetchone()["count"]
    if database_count > 0:
        return

    now = _now_iso()
    conn.execute(
        "INSERT INTO project_databases (name, created_at, created_by) VALUES (?, ?, ?)",
        (DEFAULT_PROJECT_DATABASE, now, actor_id),
    )

    for table_def in DEFAULT_PROJECT_TABLES:
        conn.execute(
            """
            INSERT INTO project_tables (database_name, table_name, schema_json, search_key, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                DEFAULT_PROJECT_DATABASE,
                table_def["name"],
                json.dumps(table_def["schema"]),
                table_def["search_key"],
                now,
                actor_id,
            ),
        )


def _ensure_default_project_tables(conn, actor_id=None):
    db_exists = conn.execute(
        "SELECT 1 FROM project_databases WHERE name = ?",
        (DEFAULT_PROJECT_DATABASE,),
    ).fetchone()
    if db_exists is None:
        conn.execute(
            "INSERT INTO project_databases (name, created_at, created_by) VALUES (?, ?, ?)",
            (DEFAULT_PROJECT_DATABASE, _now_iso(), actor_id),
        )

    existing_rows = conn.execute(
        "SELECT table_name FROM project_tables WHERE database_name = ?",
        (DEFAULT_PROJECT_DATABASE,),
    ).fetchall()
    existing_names = {row["table_name"] for row in existing_rows}

    now = _now_iso()
    for table_def in DEFAULT_PROJECT_TABLES:
        if table_def["name"] in existing_names:
            continue
        conn.execute(
            """
            INSERT INTO project_tables (database_name, table_name, schema_json, search_key, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                DEFAULT_PROJECT_DATABASE,
                table_def["name"],
                json.dumps(table_def["schema"]),
                table_def["search_key"],
                now,
                actor_id,
            ),
        )


def _sync_system_admin_records(conn, actor_id=None):
    table_exists = conn.execute(
        """
        SELECT 1
        FROM project_tables
        WHERE database_name = ? AND table_name = 'SystemAdmin'
        """,
        (DEFAULT_PROJECT_DATABASE,),
    ).fetchone()
    if table_exists is None:
        return

    admin_rows = conn.execute(
        """
        SELECT id, full_name, email
        FROM members
        WHERE role = 'admin'
        ORDER BY id
        """
    ).fetchall()

    conn.execute(
        "DELETE FROM project_records WHERE database_name = ? AND table_name = 'SystemAdmin'",
        (DEFAULT_PROJECT_DATABASE,),
    )

    now = _now_iso()
    for admin in admin_rows:
        payload = {
            "adminID": str(admin["id"]),
            "name": admin["full_name"],
            "email": admin["email"],
        }
        conn.execute(
            """
            INSERT INTO project_records
            (database_name, table_name, record_key, payload_json, created_at, updated_at, created_by, updated_by)
            VALUES (?, 'SystemAdmin', ?, ?, ?, ?, ?, ?)
            """,
            (
                DEFAULT_PROJECT_DATABASE,
                payload["adminID"],
                json.dumps(payload),
                now,
                now,
                actor_id,
                actor_id,
            ),
        )


def _ensure_core_identity_links(conn):
    rows = conn.execute(
        """
        SELECT id, username, COALESCE(NULLIF(password_hash, ''), '') AS password_hash, member_group
        FROM members
        """
    ).fetchall()

    now = _now_iso()
    for row in rows:
        password_hash = row["password_hash"]
        if password_hash is None or str(password_hash).strip() == "":
            # Keep legacy databases operational by generating a deterministic fallback hash.
            password_hash = _hash_password(f"{row['username']}123")
            conn.execute(
                "UPDATE members SET password_hash = ? WHERE id = ?",
                (password_hash, row["id"]),
            )

        conn.execute(
            """
            INSERT INTO member_credentials (member_id, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(member_id)
            DO UPDATE SET
                password_hash = excluded.password_hash,
                updated_at = excluded.updated_at
            """,
            (row["id"], password_hash, now, now),
        )
        conn.execute(
            """
            INSERT INTO member_group_mappings (member_id, group_name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(member_id)
            DO UPDATE SET
                group_name = excluded.group_name,
                updated_at = excluded.updated_at
            """,
            (row["id"], _normalize_member_group(row["member_group"]), now, now),
        )

    conn.execute(
        "DELETE FROM member_credentials WHERE member_id NOT IN (SELECT id FROM members)"
    )
    conn.execute(
        "DELETE FROM member_group_mappings WHERE member_id NOT IN (SELECT id FROM members)"
    )


def _ensure_members_compat_columns(conn):
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(members)").fetchall()
    }

    if "password_hash" not in columns:
        conn.execute("ALTER TABLE members ADD COLUMN password_hash TEXT")

        if "password" in columns:
            legacy_rows = conn.execute(
                "SELECT id, password FROM members"
            ).fetchall()
            for row in legacy_rows:
                conn.execute(
                    "UPDATE members SET password_hash = ? WHERE id = ?",
                    (_hash_password(row["password"] or ""), row["id"]),
                )

    if "member_group" not in columns:
        conn.execute("ALTER TABLE members ADD COLUMN member_group TEXT")

    conn.execute(
        "UPDATE members SET member_group = 'general' WHERE member_group IS NULL OR TRIM(member_group) = ''"
    )


def _ensure_project_catalog():
    conn = _db_conn()
    try:
        _ensure_core_identity_links(conn)
        _bootstrap_project_catalog(conn)
        _ensure_default_project_tables(conn)
        _sync_system_admin_records(conn)
        conn.commit()
    finally:
        conn.close()


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
            CREATE TABLE IF NOT EXISTS member_credentials (
                member_id INTEGER PRIMARY KEY,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS member_group_mappings (
                member_id INTEGER PRIMARY KEY,
                group_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE
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
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS project_databases (
                name TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                created_by INTEGER,
                FOREIGN KEY(created_by) REFERENCES members(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS project_tables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                database_name TEXT NOT NULL,
                table_name TEXT NOT NULL,
                schema_json TEXT NOT NULL,
                search_key TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by INTEGER,
                UNIQUE(database_name, table_name),
                FOREIGN KEY(database_name) REFERENCES project_databases(name) ON DELETE CASCADE,
                FOREIGN KEY(created_by) REFERENCES members(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS project_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                database_name TEXT NOT NULL,
                table_name TEXT NOT NULL,
                record_key TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                created_by INTEGER,
                updated_by INTEGER,
                UNIQUE(database_name, table_name, record_key),
                FOREIGN KEY(created_by) REFERENCES members(id),
                FOREIGN KEY(updated_by) REFERENCES members(id)
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_project_tables_db ON project_tables(database_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_project_records_table ON project_records(database_name, table_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_project_records_key ON project_records(database_name, table_name, record_key)"
        )
        if CORE_SCHEMA_PATH.exists():
            conn.executescript(CORE_SCHEMA_PATH.read_text(encoding="utf-8"))
        if PROJECT_SCHEMA_PATH.exists():
            conn.executescript(PROJECT_SCHEMA_PATH.read_text(encoding="utf-8"))
        if INDEXES_PATH.exists():
            conn.executescript(INDEXES_PATH.read_text(encoding="utf-8"))
        _ensure_members_compat_columns(conn)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_uploadsession_device ON UploadSession(deviceID)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_uploadsession_policy ON UploadSession(policyID)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_uploadsession_status ON UploadSession(status)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_filemetadata_session ON FileMetadata(sessionID)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_onetimetoken_session ON OneTimeToken(sessionID)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_onetimetoken_tokenvalue ON OneTimeToken(tokenValue)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_downloadlog_token ON DownloadLog(tokenID)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_downloadlog_time ON DownloadLog(downloadTime)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ratelimit_device ON RateLimitLog(deviceID)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ratelimit_time ON RateLimitLog(timestamp)"
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

        admin_row = cursor.execute(
            "SELECT id FROM members WHERE username = ?",
            ("admin",),
        ).fetchone()

        _bootstrap_project_catalog(conn, actor_id=admin_row["id"] if admin_row else None)
        _sync_system_admin_records(conn, actor_id=admin_row["id"] if admin_row else None)
        _ensure_core_identity_links(conn)
        conn.commit()
    finally:
        conn.close()


def _write_audit(action, target, status, actor_id=None, details=None):
    now = _now_iso()
    audit_logger.info(
        json.dumps(
            {
                "created_at": now,
                "actor_id": actor_id,
                "action": action,
                "target": target,
                "status": status,
                "details": details,
            },
            ensure_ascii=True,
        )
    )

    conn = _db_conn()
    try:
        conn.execute(
            """
            INSERT INTO audit_logs (actor_id, action, target, status, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (actor_id, action, target, status, details, now),
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
            "expires_at": row["expires_at"],
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


def _table_meta(conn, db_name, table_name):
    return conn.execute(
        """
        SELECT database_name, table_name, schema_json, search_key
        FROM project_tables
        WHERE database_name = ? AND table_name = ?
        """,
        (db_name, table_name),
    ).fetchone()


def _record_key_sort(value):
    text = str(value)
    try:
        return (0, float(text))
    except ValueError:
        return (1, text)


def _extract_record_key(record, search_key):
    if search_key in record:
        return str(record[search_key])
    if "id" in record:
        return str(record["id"])
    first_key = next(iter(record), None)
    return str(record[first_key]) if first_key is not None else None


def _is_safe_identifier(value):
    if not value:
        return False
    return value.replace("_", "a").isalnum() and (value[0].isalpha() or value[0] == "_")


def _load_live_table_records(conn, db_name, table_name):
    if db_name != DEFAULT_PROJECT_DATABASE:
        return None

    if table_name == "Member":
        rows = conn.execute(
            """
            SELECT
                id AS memberID,
                full_name AS name,
                NULL AS age,
                '' AS image,
                email,
                member_group AS contactNumber
            FROM members
            ORDER BY id
            """
        ).fetchall()
        return [dict(row) for row in rows]

    if table_name == "SystemAdmin":
        rows = conn.execute(
            """
            SELECT
                id AS adminID,
                full_name AS name,
                email
            FROM members
            WHERE role = 'admin'
            ORDER BY id
            """
        ).fetchall()
        return [dict(row) for row in rows]

    physical_name = table_name
    if not _is_safe_identifier(physical_name):
        return None

    table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (physical_name,),
    ).fetchone()
    if table_exists is None:
        return None

    rows = conn.execute(f'SELECT * FROM "{physical_name}"').fetchall()
    return [dict(row) for row in rows]


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
            """
            SELECT m.*, c.password_hash AS credential_password_hash
            FROM members m
            LEFT JOIN member_credentials c ON c.member_id = m.id
            WHERE m.username = ?
            """,
            (username,),
        ).fetchone()
        expected_hash = member["credential_password_hash"] if member else None
        if expected_hash is None and member is not None:
            expected_hash = member["password_hash"]
        if member is None or expected_hash != _hash_password(password):
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
        now = _now_iso()
        password_hash = _hash_password(payload["password"])
        cursor = conn.execute(
            """
            INSERT INTO members (username, password_hash, role, full_name, email, member_group, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["username"].strip(),
                password_hash,
                role,
                payload["full_name"].strip(),
                payload["email"].strip(),
                _normalize_member_group(payload.get("member_group")),
                now,
            ),
        )
        member_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO member_credentials (member_id, password_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (member_id, password_hash, now, now),
        )
        conn.execute(
            """
            INSERT INTO member_group_mappings (member_id, group_name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (member_id, _normalize_member_group(payload.get("member_group")), now, now),
        )
        _sync_system_admin_records(conn, actor_id=g.current_member["id"])
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
    next_group_name = None

    for field in updatable:
        if field in payload:
            updates.append(f"{field} = ?")
            cleaned_value = (payload[field] or "").strip()
            values.append(cleaned_value)
            if field == "member_group":
                normalized_group = _normalize_member_group(payload[field])
                values[-1] = normalized_group
                next_group_name = normalized_group

    next_password_hash = None
    if "password" in payload and payload["password"]:
        updates.append("password_hash = ?")
        next_password_hash = _hash_password(payload["password"])
        values.append(next_password_hash)

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
        if next_password_hash is not None:
            conn.execute(
                """
                INSERT INTO member_credentials (member_id, password_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(member_id)
                DO UPDATE SET
                    password_hash = excluded.password_hash,
                    updated_at = excluded.updated_at
                """,
                (member_id, next_password_hash, _now_iso(), _now_iso()),
            )
        if next_group_name is not None:
            conn.execute(
                """
                INSERT INTO member_group_mappings (member_id, group_name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(member_id)
                DO UPDATE SET
                    group_name = excluded.group_name,
                    updated_at = excluded.updated_at
                """,
                (member_id, next_group_name, _now_iso(), _now_iso()),
            )
        _sync_system_admin_records(conn, actor_id=current["id"])
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
        conn.execute("DELETE FROM member_credentials WHERE member_id = ?", (member_id,))
        conn.execute("DELETE FROM member_group_mappings WHERE member_id = ?", (member_id,))
        cursor = conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Member not found"}), 404
        _sync_system_admin_records(conn, actor_id=g.current_member["id"])
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


@api.route("/indexing/project-explain", methods=["GET"])
@require_admin
def explain_project_lookup():
    conn = _db_conn()
    try:
        query = "SELECT sessionID, deviceID, status FROM UploadSession WHERE status = ?"
        rows = conn.execute(f"EXPLAIN QUERY PLAN {query}", ("ACTIVE",)).fetchall()
    finally:
        conn.close()
    return jsonify({"query": query, "plan": [dict(r) for r in rows]})


@api.route("/indexing/project-benchmark-comparison", methods=["GET"])
@require_admin
def benchmark_project_index_comparison():
    iterations = request.args.get("iterations", default=1000, type=int)
    iterations = min(max(iterations, 10), 20000)

    conn = _db_conn()
    try:
        start = time.perf_counter()
        for _ in range(iterations):
            conn.execute(
                "SELECT sessionID, deviceID, status FROM UploadSession NOT INDEXED WHERE status = ?",
                ("ACTIVE",),
            ).fetchall()
        no_index = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(iterations):
            conn.execute(
                "SELECT sessionID, deviceID, status FROM UploadSession INDEXED BY idx_uploadsession_status WHERE status = ?",
                ("ACTIVE",),
            ).fetchall()
        with_index = time.perf_counter() - start
    finally:
        conn.close()

    return jsonify(
        {
            "query": "UploadSession lookup by status",
            "iterations": iterations,
            "without_index": {
                "total_seconds": no_index,
                "avg_ms": (no_index / iterations) * 1000,
            },
            "with_index": {
                "total_seconds": with_index,
                "avg_ms": (with_index / iterations) * 1000,
            },
            "improvement_percent": ((no_index - with_index) / no_index * 100) if no_index > 0 else 0,
        }
    )


@api.route("/indexing/dashboard-benchmark-comparison", methods=["GET"])
@require_admin
def benchmark_dashboard_summary_comparison():
    iterations = request.args.get("iterations", default=1000, type=int)
    iterations = min(max(iterations, 10), 20000)

    conn = _db_conn()
    try:
        start = time.perf_counter()
        for _ in range(iterations):
            conn.execute("SELECT COUNT(*) AS count FROM project_databases NOT INDEXED").fetchone()["count"]
            conn.execute("SELECT COUNT(*) AS count FROM project_tables NOT INDEXED").fetchone()["count"]
            conn.execute("SELECT COUNT(*) AS count FROM members NOT INDEXED").fetchone()["count"]
            conn.execute("SELECT COUNT(*) AS count FROM audit_logs NOT INDEXED").fetchone()["count"]
        without_index = time.perf_counter() - start

        start = time.perf_counter()
        for _ in range(iterations):
            conn.execute("SELECT COUNT(*) AS count FROM project_databases").fetchone()["count"]
            conn.execute("SELECT COUNT(*) AS count FROM project_tables INDEXED BY idx_project_tables_db").fetchone()["count"]
            conn.execute("SELECT COUNT(*) AS count FROM members INDEXED BY idx_members_role").fetchone()["count"]
            conn.execute("SELECT COUNT(*) AS count FROM audit_logs INDEXED BY idx_audit_created").fetchone()["count"]
        with_index = time.perf_counter() - start
    finally:
        conn.close()

    return jsonify(
        {
            "query": "dashboard summary aggregate counts",
            "iterations": iterations,
            "without_index": {
                "total_seconds": without_index,
                "avg_ms": (without_index / iterations) * 1000,
            },
            "with_index": {
                "total_seconds": with_index,
                "avg_ms": (with_index / iterations) * 1000,
            },
            "improvement_percent": ((without_index - with_index) / without_index * 100) if without_index > 0 else 0,
            "note": "COUNT(*) summary queries are aggregation-heavy; index impact may be limited compared to filtered lookups.",
        }
    )
    
@api.route('/indexing/api-latency', methods=['GET'])
@require_admin
def benchmark_api_latencies():
    iterations = request.args.get("iterations", default=200, type=int)
    iterations = min(max(iterations, 10), 5000)

    conn = _db_conn()
    try:
        token = g.current_member.get("token")
        current_member_id = g.current_member["id"]

        sample_table_row = conn.execute(
            "SELECT database_name, table_name FROM project_tables ORDER BY id LIMIT 1"
        ).fetchone()
        sample_db = sample_table_row["database_name"] if sample_table_row else DEFAULT_PROJECT_DATABASE
        sample_table = sample_table_row["table_name"] if sample_table_row else "Member"
        sample_record_row = conn.execute(
            "SELECT record_key FROM project_records WHERE database_name = ? AND table_name = ? ORDER BY record_key LIMIT 1",
            (sample_db, sample_table),
        ).fetchone()
        sample_record_key = sample_record_row["record_key"] if sample_record_row else "1"

        def _measure(method, name, query_fn):
            start = time.perf_counter()
            for _ in range(iterations):
                query_fn()
            elapsed = time.perf_counter() - start
            return {
                "method": method,
                "api": name,
                "iterations": iterations,
                "total_seconds": elapsed,
                "avg_ms": (elapsed / iterations) * 1000,
            }

        results = [
            _measure(
                "POST",
                "/auth/login (lookup path)",
                lambda: conn.execute(
                    "SELECT id, username, password_hash, role FROM members WHERE username = ?",
                    (g.current_member["username"],),
                ).fetchone(),
            ),
            _measure(
                "GET",
                "/auth/me",
                lambda: conn.execute(
                    """
                    SELECT s.token, s.expires_at, m.id, m.username, m.role, m.full_name, m.email, m.member_group
                    FROM sessions s
                    JOIN members m ON m.id = s.member_id
                    WHERE s.token = ?
                    """,
                    (token,),
                ).fetchone(),
            ),
            _measure(
                "GET",
                "/members",
                lambda: conn.execute(
                    "SELECT id, username, role, full_name, email, member_group, created_at FROM members ORDER BY id"
                ).fetchall(),
            ),
            _measure(
                "GET",
                "/dashboard/summary",
                lambda: (
                    conn.execute("SELECT COUNT(*) AS count FROM project_databases").fetchone(),
                    conn.execute("SELECT COUNT(*) AS count FROM project_tables").fetchone(),
                    conn.execute("SELECT COUNT(*) AS count FROM members").fetchone(),
                    conn.execute("SELECT COUNT(*) AS count FROM audit_logs").fetchone(),
                ),
            ),
            _measure(
                "GET",
                "/members/portfolio (admin)",
                lambda: conn.execute(
                    "SELECT id, username, full_name, email, role, member_group, created_at FROM members ORDER BY full_name"
                ).fetchall(),
            ),
            _measure(
                "GET",
                "/audit-logs",
                lambda: conn.execute(
                    """
                    SELECT a.id, a.action, a.target, a.status, a.details, a.created_at,
                           m.username AS actor_username, m.role AS actor_role
                    FROM audit_logs a
                    LEFT JOIN members m ON m.id = a.actor_id
                    ORDER BY a.id DESC
                    LIMIT 100
                    """
                ).fetchall(),
            ),
            _measure(
                "GET",
                "/databases",
                lambda: conn.execute("SELECT name FROM project_databases ORDER BY name").fetchall(),
            ),
            _measure(
                "GET",
                "/databases/catalog",
                lambda: conn.execute(
                    """
                    SELECT d.name, t.table_name
                    FROM project_databases d
                    LEFT JOIN project_tables t ON t.database_name = d.name
                    ORDER BY d.name, t.table_name
                    """
                ).fetchall(),
            ),
            _measure(
                "GET",
                "/databases/{db}/tables",
                lambda: conn.execute(
                    "SELECT table_name FROM project_tables WHERE database_name = ? ORDER BY table_name",
                    (sample_db,),
                ).fetchall(),
            ),
            _measure(
                "GET",
                "/databases/{db}/tables/{table}/meta",
                lambda: conn.execute(
                    "SELECT database_name, table_name, schema_json, search_key FROM project_tables WHERE database_name = ? AND table_name = ?",
                    (sample_db, sample_table),
                ).fetchone(),
            ),
            _measure(
                "GET",
                "/databases/{db}/tables/{table}/records",
                lambda: conn.execute(
                    """
                    SELECT payload_json
                    FROM project_records
                    WHERE database_name = ? AND table_name = ?
                    ORDER BY record_key
                    """,
                    (sample_db, sample_table),
                ).fetchall(),
            ),
            _measure(
                "GET",
                "/databases/{db}/tables/{table}/records/{id}",
                lambda: conn.execute(
                    "SELECT payload_json FROM project_records WHERE database_name = ? AND table_name = ? AND record_key = ?",
                    (sample_db, sample_table, sample_record_key),
                ).fetchone(),
            ),
            _measure(
                "POST",
                "/databases/{db}/tables/{table}/range",
                lambda: conn.execute(
                    "SELECT payload_json, record_key FROM project_records WHERE database_name = ? AND table_name = ? ORDER BY record_key",
                    (sample_db, sample_table),
                ).fetchall(),
            ),
            _measure(
                "GET",
                "/databases/{db}/tables/{table}/visualize",
                lambda: conn.execute(
                    "SELECT record_key FROM project_records WHERE database_name = ? AND table_name = ? ORDER BY record_key",
                    (sample_db, sample_table),
                ).fetchall(),
            ),
            _measure(
                "GET",
                "/indexing/explain",
                lambda: conn.execute(
                    "EXPLAIN QUERY PLAN SELECT id, username, role FROM members WHERE username = ?",
                    (g.current_member["username"],),
                ).fetchall(),
            ),
            _measure(
                "GET",
                "/indexing/benchmark",
                lambda: conn.execute(
                    "SELECT id, username, role FROM members WHERE username = ?",
                    (g.current_member["username"],),
                ).fetchone(),
            ),
            _measure(
                "PUT",
                "/members/{id} (self update lookup path)",
                lambda: conn.execute(
                    "SELECT id, username, role, full_name, email, member_group, created_at FROM members WHERE id = ?",
                    (current_member_id,),
                ).fetchone(),
            ),
        ]

    finally:
        conn.close()

    return jsonify({"results": results, "iterations": iterations})


@api.route('/databases', methods=['GET'])
@require_admin
def get_databases():
    _ensure_project_catalog()
    conn = _db_conn()
    try:
        rows = conn.execute("SELECT name FROM project_databases ORDER BY name").fetchall()
    finally:
        conn.close()
    databases = [row["name"] for row in rows]
    return jsonify({"databases": databases, "count": len(databases)})


@api.route('/databases/catalog', methods=['GET'])
@require_admin
def get_databases_catalog():
    _ensure_project_catalog()
    conn = _db_conn()
    try:
        db_rows = conn.execute("SELECT name FROM project_databases ORDER BY name").fetchall()
        catalog = []
        for db_row in db_rows:
            table_rows = conn.execute(
                "SELECT table_name FROM project_tables WHERE database_name = ? ORDER BY table_name",
                (db_row["name"],),
            ).fetchall()
            table_names = [table_row["table_name"] for table_row in table_rows]
            catalog.append(
                {
                    "name": db_row["name"],
                    "table_count": len(table_names),
                    "tables": table_names,
                }
            )
    finally:
        conn.close()

    return jsonify({"catalog": catalog, "count": len(catalog)})


@api.route('/dashboard/summary', methods=['GET'])
@require_admin
def dashboard_summary():
    _ensure_project_catalog()
    conn = _db_conn()
    try:
        database_count = conn.execute("SELECT COUNT(*) AS count FROM project_databases").fetchone()["count"]
        table_count = conn.execute("SELECT COUNT(*) AS count FROM project_tables").fetchone()["count"]
        member_count = conn.execute("SELECT COUNT(*) AS count FROM members").fetchone()["count"]
        audit_count = conn.execute("SELECT COUNT(*) AS count FROM audit_logs").fetchone()["count"]
    finally:
        conn.close()

    return jsonify(
        {
            "database_count": database_count,
            "table_count": table_count,
            "member_count": member_count,
            "audit_count": audit_count,
        }
    )


@api.route('/databases', methods=['POST'])
@require_admin
def create_database():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({"error": "Database name is required"}), 400

    conn = _db_conn()
    try:
        conn.execute(
            "INSERT INTO project_databases (name, created_at, created_by) VALUES (?, ?, ?)",
            (name, _now_iso(), g.current_member["id"]),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Database already exists"}), 400
    finally:
        conn.close()

    _write_audit(
        "create_database",
        "dbms",
        "success",
        g.current_member["id"],
        json.dumps({"database": name}),
    )
    return jsonify({"message": "Database created successfully"}), 201


@api.route('/databases/<db_name>', methods=['DELETE'])
@require_admin
def delete_database(db_name):
    conn = _db_conn()
    try:
        existing_count = conn.execute(
            "SELECT COUNT(*) AS count FROM project_databases"
        ).fetchone()["count"]
        if existing_count <= 1:
            _write_audit(
                "delete_database",
                "dbms",
                "denied",
                g.current_member["id"],
                json.dumps({"database": db_name, "reason": "Cannot delete last database"}),
            )
            return jsonify({"error": "Cannot delete the last available database"}), 400

        conn.execute("DELETE FROM project_records WHERE database_name = ?", (db_name,))
        conn.execute("DELETE FROM project_tables WHERE database_name = ?", (db_name,))
        cursor = conn.execute("DELETE FROM project_databases WHERE name = ?", (db_name,))
        conn.commit()
        deleted = cursor.rowcount > 0
    finally:
        conn.close()

    _write_audit(
        "delete_database",
        "dbms",
        "success" if deleted else "failed",
        g.current_member["id"],
        json.dumps({"database": db_name}),
    )
    if deleted:
        return jsonify({"message": "Database deleted successfully"}), 200
    return jsonify({"error": "Database not found"}), 404


@api.route('/databases/<db_name>/tables', methods=['GET'])
@require_session
def get_tables(db_name):
    conn = _db_conn()
    try:
        db_exists = conn.execute(
            "SELECT 1 FROM project_databases WHERE name = ?",
            (db_name,),
        ).fetchone()
        if db_exists is None:
            return jsonify({"error": "Database not found"}), 404

        rows = conn.execute(
            "SELECT table_name FROM project_tables WHERE database_name = ? ORDER BY table_name",
            (db_name,),
        ).fetchall()
    finally:
        conn.close()

    tables = [row["table_name"] for row in rows]
    return jsonify({"tables": tables, "count": len(tables)})


@api.route('/databases/<db_name>/tables/<table_name>/meta', methods=['GET'])
@require_session
def get_table_meta(db_name, table_name):
    conn = _db_conn()
    try:
        meta = _table_meta(conn, db_name, table_name)
    finally:
        conn.close()

    if meta is None:
        return jsonify({"error": "Table not found"}), 404

    schema = json.loads(meta["schema_json"])
    return jsonify(
        {
            "database": meta["database_name"],
            "table": meta["table_name"],
            "schema": schema,
            "search_key": meta["search_key"],
        }
    )


@api.route('/databases/<db_name>/tables', methods=['POST'])
@require_admin
def create_table(db_name):
    data = request.get_json(silent=True) or {}
    table_name = (data.get('name') or '').strip()
    schema = data.get('schema')

    if not table_name or not isinstance(schema, list) or not schema:
        return jsonify({"error": "Table name and schema are required"}), 400

    cleaned_schema = [str(item).strip() for item in schema if str(item).strip()]
    if not cleaned_schema:
        return jsonify({"error": "Schema must contain at least one column"}), 400

    search_key = (data.get('search_key') or cleaned_schema[0]).strip()
    if search_key not in cleaned_schema:
        return jsonify({"error": "Search key must be part of schema"}), 400

    conn = _db_conn()
    try:
        db_exists = conn.execute(
            "SELECT 1 FROM project_databases WHERE name = ?",
            (db_name,),
        ).fetchone()
        if db_exists is None:
            return jsonify({"error": "Database not found"}), 404

        conn.execute(
            """
            INSERT INTO project_tables (database_name, table_name, schema_json, search_key, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                db_name,
                table_name,
                json.dumps(cleaned_schema),
                search_key,
                _now_iso(),
                g.current_member["id"],
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Table already exists"}), 400
    finally:
        conn.close()

    _write_audit(
        "create_table",
        "dbms",
        "success",
        g.current_member["id"],
        json.dumps({"database": db_name, "table": table_name}),
    )
    return jsonify({"message": "Table created successfully"}), 201


@api.route('/databases/<db_name>/tables/<table_name>', methods=['DELETE'])
@require_admin
def delete_table(db_name, table_name):
    conn = _db_conn()
    try:
        conn.execute(
            "DELETE FROM project_records WHERE database_name = ? AND table_name = ?",
            (db_name, table_name),
        )
        cursor = conn.execute(
            "DELETE FROM project_tables WHERE database_name = ? AND table_name = ?",
            (db_name, table_name),
        )
        conn.commit()
        deleted = cursor.rowcount > 0
    finally:
        conn.close()

    _write_audit(
        "delete_table",
        "dbms",
        "success" if deleted else "failed",
        g.current_member["id"],
        json.dumps({"database": db_name, "table": table_name}),
    )
    if deleted:
        return jsonify({"message": "Table deleted successfully"}), 200
    return jsonify({"error": "Table not found"}), 404


@api.route('/databases/<db_name>/tables/<table_name>/records', methods=['GET'])
@require_session
def get_records(db_name, table_name):
    conn = _db_conn()
    try:
        meta = _table_meta(conn, db_name, table_name)
        if meta is None:
            return jsonify({"error": "Table not found"}), 404

        live_rows = _load_live_table_records(conn, db_name, table_name)
        if live_rows is not None:
            formatted_records = [{"data": row} for row in live_rows]
            return jsonify({"records": formatted_records, "count": len(formatted_records)})

        rows = conn.execute(
            """
            SELECT payload_json
            FROM project_records
            WHERE database_name = ? AND table_name = ?
            ORDER BY record_key
            """,
            (db_name, table_name),
        ).fetchall()
    finally:
        conn.close()

    formatted_records = [{"data": json.loads(row["payload_json"])} for row in rows]
    return jsonify({"records": formatted_records, "count": len(formatted_records)})


@api.route('/databases/<db_name>/tables/<table_name>/records', methods=['POST'])
@require_admin
def create_record(db_name, table_name):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Record data is required"}), 400

    conn = _db_conn()
    try:
        meta = _table_meta(conn, db_name, table_name)
        if meta is None:
            return jsonify({"error": "Table not found"}), 404

        search_key = meta["search_key"]
        now = _now_iso()

        if isinstance(data, list):
            results = []
            success_count = 0
            for record in data:
                if not isinstance(record, dict):
                    results.append({"status": "failed", "result": "Each record must be an object"})
                    continue
                record_key = _extract_record_key(record, search_key)
                if record_key is None:
                    results.append({"status": "failed", "result": f"Missing search key '{search_key}'"})
                    continue
                try:
                    conn.execute(
                        """
                        INSERT INTO project_records
                        (database_name, table_name, record_key, payload_json, created_at, updated_at, created_by, updated_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            db_name,
                            table_name,
                            record_key,
                            json.dumps(record),
                            now,
                            now,
                            g.current_member["id"],
                            g.current_member["id"],
                        ),
                    )
                    results.append({"status": "success", "result": record_key})
                    success_count += 1
                except sqlite3.IntegrityError:
                    results.append({"status": "failed", "result": f"Duplicate record key '{record_key}'"})

            conn.commit()
            status = "success" if success_count else "failed"
            _write_audit("insert_records", "dbms", status, g.current_member["id"], json.dumps({"database": db_name, "table": table_name, "count": len(data)}))
            if success_count:
                return jsonify({"message": f"Processed {len(data)} records", "results": results}), 201
            return jsonify({"error": "No records inserted", "results": results}), 400

        if not isinstance(data, dict):
            return jsonify({"error": "Record data must be an object or list of objects"}), 400

        record_key = _extract_record_key(data, search_key)
        if record_key is None:
            return jsonify({"error": f"Missing search key '{search_key}'"}), 400

        conn.execute(
            """
            INSERT INTO project_records
            (database_name, table_name, record_key, payload_json, created_at, updated_at, created_by, updated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                db_name,
                table_name,
                record_key,
                json.dumps(data),
                now,
                now,
                g.current_member["id"],
                g.current_member["id"],
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Record already exists"}), 400
    finally:
        conn.close()

    _write_audit(
        "insert_record",
        "dbms",
        "success",
        g.current_member["id"],
        json.dumps({"database": db_name, "table": table_name, "record_id": record_key}),
    )
    return jsonify({"message": "Record created successfully", "result": record_key}), 201


@api.route('/databases/<db_name>/tables/<table_name>/records/<record_id>', methods=['GET'])
@require_session
def get_record(db_name, table_name, record_id):
    conn = _db_conn()
    try:
        row = conn.execute(
            """
            SELECT payload_json
            FROM project_records
            WHERE database_name = ? AND table_name = ? AND record_key = ?
            """,
            (db_name, table_name, record_id),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return jsonify({"error": "Record not found"}), 404
    return jsonify({"id": record_id, "data": json.loads(row["payload_json"])})


@api.route('/databases/<db_name>/tables/<table_name>/records/<record_id>', methods=['PUT'])
@require_admin
def update_record(db_name, table_name, record_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "Record data is required"}), 400

    conn = _db_conn()
    try:
        meta = _table_meta(conn, db_name, table_name)
        if meta is None:
            return jsonify({"error": "Table not found"}), 404

        search_key = meta["search_key"]
        existing = conn.execute(
            """
            SELECT payload_json
            FROM project_records
            WHERE database_name = ? AND table_name = ? AND record_key = ?
            """,
            (db_name, table_name, record_id),
        ).fetchone()
        if existing is None:
            return jsonify({"error": "Record not found"}), 404

        payload = json.loads(existing["payload_json"])
        payload.update(data)
        new_record_key = _extract_record_key(payload, search_key)
        if new_record_key is None:
            return jsonify({"error": f"Missing search key '{search_key}'"}), 400
        if new_record_key != str(record_id):
            return jsonify({"error": "Changing record key is not supported"}), 400

        cursor = conn.execute(
            """
            UPDATE project_records
            SET payload_json = ?, updated_at = ?, updated_by = ?
            WHERE database_name = ? AND table_name = ? AND record_key = ?
            """,
            (
                json.dumps(payload),
                _now_iso(),
                g.current_member["id"],
                db_name,
                table_name,
                record_id,
            ),
        )
        conn.commit()
        updated = cursor.rowcount > 0
    finally:
        conn.close()

    _write_audit(
        "update_record",
        "dbms",
        "success" if updated else "failed",
        g.current_member["id"],
        json.dumps({"database": db_name, "table": table_name, "record_id": record_id}),
    )
    if updated:
        return jsonify({"message": "Record updated successfully"})
    return jsonify({"error": "Record not found"}), 404


@api.route('/databases/<db_name>/tables/<table_name>/records/<record_id>', methods=['DELETE'])
@require_admin
def delete_record(db_name, table_name, record_id):
    conn = _db_conn()
    try:
        cursor = conn.execute(
            "DELETE FROM project_records WHERE database_name = ? AND table_name = ? AND record_key = ?",
            (db_name, table_name, record_id),
        )
        conn.commit()
        deleted = cursor.rowcount > 0
    finally:
        conn.close()

    _write_audit(
        "delete_record",
        "dbms",
        "success" if deleted else "failed",
        g.current_member["id"],
        json.dumps({"database": db_name, "table": table_name, "record_id": record_id}),
    )
    if deleted:
        return jsonify({"message": "Record deleted successfully"})
    return jsonify({"error": "Record not found"}), 404


@api.route('/databases/<db_name>/tables/<table_name>/range', methods=['POST'])
@require_session
def range_query(db_name, table_name):
    data = request.get_json(silent=True) or {}
    if 'start' not in data or 'end' not in data:
        return jsonify({"error": "Start and end values are required"}), 400

    start_sort = _record_key_sort(data['start'])
    end_sort = _record_key_sort(data['end'])
    if start_sort > end_sort:
        start_sort, end_sort = end_sort, start_sort

    conn = _db_conn()
    try:
        meta = _table_meta(conn, db_name, table_name)
        if meta is None:
            return jsonify({"error": "Table not found"}), 404

        rows = conn.execute(
            """
            SELECT payload_json, record_key
            FROM project_records
            WHERE database_name = ? AND table_name = ?
            ORDER BY record_key
            """,
            (db_name, table_name),
        ).fetchall()
    finally:
        conn.close()

    filtered = []
    for row in rows:
        key_sort = _record_key_sort(row["record_key"])
        if start_sort <= key_sort <= end_sort:
            filtered.append({"data": json.loads(row["payload_json"])})

    return jsonify({"records": filtered, "count": len(filtered)})


@api.route('/databases/<db_name>/tables/<table_name>/visualize', methods=['GET'])
@require_session
def visualize_tree(db_name, table_name):
    conn = _db_conn()
    try:
        meta = _table_meta(conn, db_name, table_name)
        if meta is None:
            return jsonify({"error": "Table not found"}), 404

        rows = conn.execute(
            """
            SELECT record_key
            FROM project_records
            WHERE database_name = ? AND table_name = ?
            ORDER BY record_key
            """,
            (db_name, table_name),
        ).fetchall()
    finally:
        conn.close()

    dot = Digraph(comment=f"{db_name}.{table_name}")
    dot.attr(rankdir='LR')
    dot.node('root', f"{table_name}\\nsearch_key={meta['search_key']}", shape='box')
    previous = 'root'
    for index, row in enumerate(rows):
        node_id = f"k{index}"
        dot.node(node_id, row['record_key'], shape='ellipse')
        dot.edge(previous, node_id)
        previous = node_id

    svg_data = dot.pipe(format='svg').decode('utf-8')
    return Response(svg_data, mimetype='image/svg+xml')
 
