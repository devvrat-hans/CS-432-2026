import hashlib
import sqlite3
from pathlib import Path

NUM_SHARDS = 3

BASE_DIR = Path(__file__).resolve().parent

SHARDED_TABLES = [
    "UploadSession",
    "FileMetadata",
    "OneTimeToken",
    "DownloadLog",
    "ErrorLog",
    "AuditTrail",
]

SHARD_TABLE_SCHEMAS = {
    "UploadSession": """
        CREATE TABLE IF NOT EXISTS UploadSession (
            sessionID INTEGER PRIMARY KEY,
            deviceID INTEGER NOT NULL,
            policyID INTEGER NOT NULL,
            uploadTimestamp TEXT NOT NULL,
            expiryTimestamp TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'DOWNLOADED', 'EXPIRED'))
        )
    """,
    "FileMetadata": """
        CREATE TABLE IF NOT EXISTS FileMetadata (
            fileID INTEGER PRIMARY KEY,
            sessionID INTEGER NOT NULL,
            fileName TEXT NOT NULL,
            fileSize INTEGER NOT NULL,
            mimeType TEXT,
            checksum TEXT,
            storagePath TEXT,
            FOREIGN KEY(sessionID) REFERENCES UploadSession(sessionID)
        )
    """,
    "OneTimeToken": """
        CREATE TABLE IF NOT EXISTS OneTimeToken (
            tokenID INTEGER PRIMARY KEY,
            sessionID INTEGER NOT NULL,
            tokenValue TEXT NOT NULL UNIQUE,
            createdAt TEXT NOT NULL,
            expiryAt TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'USED', 'EXPIRED')),
            FOREIGN KEY(sessionID) REFERENCES UploadSession(sessionID)
        )
    """,
    "DownloadLog": """
        CREATE TABLE IF NOT EXISTS DownloadLog (
            downloadID INTEGER PRIMARY KEY,
            tokenID INTEGER NOT NULL,
            downloadTime TEXT NOT NULL,
            userDeviceInfo TEXT,
            FOREIGN KEY(tokenID) REFERENCES OneTimeToken(tokenID)
        )
    """,
    "ErrorLog": """
        CREATE TABLE IF NOT EXISTS ErrorLog (
            errorID INTEGER PRIMARY KEY,
            sessionID INTEGER,
            errorMessage TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """,
    "AuditTrail": """
        CREATE TABLE IF NOT EXISTS AuditTrail (
            auditID INTEGER PRIMARY KEY,
            action TEXT NOT NULL,
            sessionID INTEGER,
            timestamp TEXT NOT NULL,
            details TEXT
        )
    """,
}

SHARD_TABLE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_uploadsession_device ON UploadSession(deviceID)",
    "CREATE INDEX IF NOT EXISTS idx_uploadsession_policy ON UploadSession(policyID)",
    "CREATE INDEX IF NOT EXISTS idx_uploadsession_status ON UploadSession(status)",
    "CREATE INDEX IF NOT EXISTS idx_filemetadata_session ON FileMetadata(sessionID)",
    "CREATE INDEX IF NOT EXISTS idx_onetimetoken_session ON OneTimeToken(sessionID)",
    "CREATE INDEX IF NOT EXISTS idx_onetimetoken_tokenvalue ON OneTimeToken(tokenValue)",
    "CREATE INDEX IF NOT EXISTS idx_downloadlog_token ON DownloadLog(tokenID)",
    "CREATE INDEX IF NOT EXISTS idx_downloadlog_time ON DownloadLog(downloadTime)",
    "CREATE INDEX IF NOT EXISTS idx_errorlog_session ON ErrorLog(sessionID)",
    "CREATE INDEX IF NOT EXISTS idx_audittrail_session ON AuditTrail(sessionID)",
]


def get_shard_id(session_id):
    """Determine which shard a session belongs to using hash-based routing."""
    key = str(session_id).encode("utf-8")
    hash_val = int(hashlib.md5(key).hexdigest(), 16)
    return hash_val % NUM_SHARDS


def shard_db_path(shard_id):
    """Return the file path for a given shard database."""
    return BASE_DIR / f"shard_{shard_id}.sqlite3"


class ShardManager:
    """Manages connections to the 3 shard SQLite databases."""

    def __init__(self):
        self._connections = {}

    def get_shard_conn(self, shard_id):
        """Get or create a connection to a specific shard database."""
        if shard_id in self._connections:
            return self._connections[shard_id]

        db_path = shard_db_path(shard_id)
        conn = sqlite3.connect(str(db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        self._connections[shard_id] = conn
        return conn

    def get_all_shard_conns(self):
        """Return a list of connections to all shard databases."""
        return [self.get_shard_conn(i) for i in range(NUM_SHARDS)]

    def get_shard_conn_for_session(self, session_id):
        """Return the shard connection for a given session ID."""
        return self.get_shard_conn(get_shard_id(session_id))

    def initialize_shards(self):
        """Create all shard databases and their table schemas and indexes."""
        for shard_id in range(NUM_SHARDS):
            conn = self.get_shard_conn(shard_id)
            cursor = conn.cursor()
            for table_name in SHARDED_TABLES:
                cursor.execute(SHARD_TABLE_SCHEMAS[table_name])
            for index_sql in SHARD_TABLE_INDEXES:
                cursor.execute(index_sql)
            conn.commit()

    def close_all(self):
        """Close all open shard connections."""
        for conn in self._connections.values():
            try:
                conn.close()
            except Exception:
                pass
        self._connections.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all()
        return False
