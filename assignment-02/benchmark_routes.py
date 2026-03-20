import time
from flask import Blueprint, jsonify
from auth import admin_required
from db import get_conn
import psycopg2.extras

benchmark_bp = Blueprint("benchmark", __name__)

QUERIES = [
    {
        "name": "Active Sessions with Files",
        "sql": """SELECT us.sessionID, fm.fileName, us.status
                  FROM UploadSession us
                  JOIN FileMetadata fm ON us.sessionID = fm.sessionID
                  WHERE us.status = 'ACTIVE'"""
    },
    {
        "name": "Token Validation by Value",
        "sql": """SELECT ot.tokenValue, ot.status, fm.fileName
                  FROM OneTimeToken ot
                  JOIN UploadSession us ON ot.sessionID = us.sessionID
                  JOIN FileMetadata fm ON us.sessionID = fm.sessionID
                  WHERE ot.tokenValue = 'TKN-U1V2W3X4Y5' AND ot.status = 'ACTIVE'"""
    },
    {
        "name": "Rate Limit Hits by Device",
        "sql": """SELECT d.location, d.ipAddress, rl.timestamp
                  FROM RateLimitLog rl
                  JOIN Device d ON rl.deviceID = d.deviceID
                  WHERE rl.eventType = 'RATE_LIMIT_HIT'"""
    },
    {
        "name": "Failed Integrity Checks",
        "sql": """SELECT fm.fileName, fic.computedChecksum, fic.timestamp
                  FROM FileIntegrityCheck fic
                  JOIN FileMetadata fm ON fic.fileID = fm.fileID
                  WHERE fic.verified = FALSE"""
    },
    {
        "name": "Audit Trail for Session 1",
        "sql": "SELECT action, timestamp FROM AuditTrail WHERE sessionID = 1 ORDER BY timestamp"
    },
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_uploadsession_status ON UploadSession(status)",
    "CREATE INDEX IF NOT EXISTS idx_uploadsession_deviceid ON UploadSession(deviceID)",
    "CREATE INDEX IF NOT EXISTS idx_filemetadata_sessionid ON FileMetadata(sessionID)",
    "CREATE INDEX IF NOT EXISTS idx_onetimetoken_tokenvalue ON OneTimeToken(tokenValue)",
    "CREATE INDEX IF NOT EXISTS idx_onetimetoken_status ON OneTimeToken(status)",
    "CREATE INDEX IF NOT EXISTS idx_ratelimitlog_deviceid ON RateLimitLog(deviceID)",
    "CREATE INDEX IF NOT EXISTS idx_ratelimitlog_eventtype ON RateLimitLog(eventType)",
    "CREATE INDEX IF NOT EXISTS idx_integrity_verified ON FileIntegrityCheck(verified)",
    "CREATE INDEX IF NOT EXISTS idx_audittrail_sessionid ON AuditTrail(sessionID)",
    "CREATE INDEX IF NOT EXISTS idx_errorlog_sessionid ON ErrorLog(sessionID)",
]

DROP_INDEXES = [
    "DROP INDEX IF EXISTS idx_uploadsession_status",
    "DROP INDEX IF EXISTS idx_uploadsession_deviceid",
    "DROP INDEX IF EXISTS idx_filemetadata_sessionid",
    "DROP INDEX IF EXISTS idx_onetimetoken_tokenvalue",
    "DROP INDEX IF EXISTS idx_onetimetoken_status",
    "DROP INDEX IF EXISTS idx_ratelimitlog_deviceid",
    "DROP INDEX IF EXISTS idx_ratelimitlog_eventtype",
    "DROP INDEX IF EXISTS idx_integrity_verified",
    "DROP INDEX IF EXISTS idx_audittrail_sessionid",
    "DROP INDEX IF EXISTS idx_errorlog_sessionid",
]


def _run_queries_timed(conn):
    results = []
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        for q in QUERIES:
            start = time.perf_counter()
            cur.execute(q["sql"])
            cur.fetchall()
            elapsed = round((time.perf_counter() - start) * 1000, 4)

            cur.execute(f"EXPLAIN ANALYZE {q['sql']}")
            plan = [r[0] for r in cur.fetchall()]

            results.append({
                "query":      q["name"],
                "time_ms":    elapsed,
                "explain":    plan,
            })
    return results


def _apply_indexes(conn, sqls):
    with conn.cursor() as cur:
        for sql in sqls:
            cur.execute(sql)
    conn.commit()


@benchmark_bp.route("/benchmark", methods=["GET"])
@admin_required
def run_benchmark():
    conn = get_conn()
    conn.autocommit = True

    # Drop indexes to get clean before state
    _apply_indexes(conn, DROP_INDEXES)

    before = _run_queries_timed(conn)

    # Apply indexes
    _apply_indexes(conn, INDEXES)

    after = _run_queries_timed(conn)

    conn.close()

    comparison = []
    for b, a in zip(before, after):
        comparison.append({
            "query":       b["query"],
            "before_ms":   b["time_ms"],
            "after_ms":    a["time_ms"],
            "improvement": round(b["time_ms"] - a["time_ms"], 4),
            "speedup_pct": round(
                ((b["time_ms"] - a["time_ms"]) / b["time_ms"] * 100)
                if b["time_ms"] > 0 else 0, 2
            ),
            "explain_before": b["explain"],
            "explain_after":  a["explain"],
        })

    return jsonify({
        "message":    "Benchmarking complete",
        "comparison": comparison,
    }), 200
