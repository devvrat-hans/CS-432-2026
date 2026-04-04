CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    member_group TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    member_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(member_id) REFERENCES members(id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id INTEGER,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(actor_id) REFERENCES members(id)
);

CREATE TABLE IF NOT EXISTS project_databases (
    name TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    created_by INTEGER,
    FOREIGN KEY(created_by) REFERENCES members(id)
);

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
);

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
);
