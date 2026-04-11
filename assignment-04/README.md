# Assignment 04 — Sharding Implementation

**CS-432 Databases | IIT Gandhinagar | Semester II 2025-2026**

## Overview

This assignment implements horizontal scaling through **hash-based sharding** on the Blind Drop file transfer application (developed in Assignments 1-3). Data is partitioned across 3 SQLite databases using `md5(sessionID) % 3`, with query routing logic integrated into all API endpoints.

## Shard Key Selection & Justification

**Shard key**: `sessionID` (UUID string from `UploadSession`)

| Criterion | Justification |
|-----------|---------------|
| **High Cardinality** | UUID-based, effectively infinite distinct values — ensures even distribution |
| **Query-Aligned** | Every file operation (upload, download, status check) routes through sessionID |
| **Stable** | UUIDs are assigned at creation and never change |

**Strategy**: Hash-based partitioning — `shard_id = md5(sessionID) % 3`

Chosen over range-based (UUIDs are not sortable) and directory-based (unnecessary complexity for this workload).

## Data Partitioning

### Sharded Tables (6)

Tables where records are partitioned across shards based on sessionID:

| Table | Shard Key Relationship |
|-------|----------------------|
| `UploadSession` | Direct — `sessionID` is own column |
| `FileMetadata` | FK — `sessionID` references UploadSession |
| `OneTimeToken` | FK — `sessionID` references UploadSession |
| `DownloadLog` | FK — `sessionID` references UploadSession |
| `ErrorLog` | FK — `relatedSessionID` references UploadSession |
| `AuditTrail` | FK — `relatedSessionID` references UploadSession |

### Unsharded Tables (6)

Reference/config tables that remain in the main database (`module_b.sqlite3`):

`Member`, `Device`, `ExpiryPolicy`, `SystemAdmin`, `RateLimitLog`, `FileIntegrityCheck`

### Shard Layout

| Database | Contents |
|----------|----------|
| `shard_0.sqlite3` | Records where `md5(sessionID) % 3 == 0` |
| `shard_1.sqlite3` | Records where `md5(sessionID) % 3 == 1` |
| `shard_2.sqlite3` | Records where `md5(sessionID) % 3 == 2` |
| `module_b.sqlite3` | Unsharded reference tables |

## Query Routing

Implemented in `shard_router.py` with three routing patterns:

### 1. Single-Key Lookup
When session ID is known, compute `get_shard_id(sessionID)` and query only that shard.
```python
shard_id = get_shard_id(session_id)
conn = ShardManager.get_connection(shard_id)
row = conn.execute("SELECT * FROM UploadSession WHERE sessionID = ?", (session_id,)).fetchone()
```

### 2. Insert Operations
New records are routed to the correct shard at insertion time:
```python
shard_id = get_shard_id(new_session_id)
conn = ShardManager.get_connection(shard_id)
conn.execute("INSERT INTO UploadSession (...) VALUES (...)", params)
```

### 3. Range / Scatter-Gather Queries
For queries without a known shard key (e.g., "find token by code"), all shards are queried and results merged:
```python
for shard_id in range(NUM_SHARDS):
    conn = ShardManager.get_connection(shard_id)
    rows = conn.execute("SELECT * FROM OneTimeToken WHERE tokenValue = ?", (code,)).fetchall()
    if rows:
        return rows[0], shard_id
```

All existing API endpoints from Assignment 2 are modified to use these routing patterns.

## Migration

`migrate_to_shards.py` handles one-time migration:
1. Reads all records from the main database
2. Computes shard ID for each record based on sessionID
3. Inserts into the appropriate shard database
4. Verifies no records lost or duplicated

## Scalability & Trade-offs Analysis

### Horizontal vs. Vertical Scaling
Sharding distributes data across multiple databases (horizontal), unlike upgrading a single server (vertical). Each shard handles ~33% of the data, reducing per-node I/O and improving throughput.

### Consistency
All shards are on the same server with SQLite, so consistency is maintained through serial access. In a true distributed setup, cross-shard queries (scatter-gather) could return stale data if shards have replication lag.

### Availability
If one shard goes down, ~33% of upload sessions become inaccessible. Unsharded tables (members, rate limits) remain available. The system degrades gracefully — file operations for the affected shard fail while others continue.

### Partition Tolerance
The current SQLite-based design doesn't face network partitions (single machine). In a distributed deployment, the hash-based strategy means no single point of failure per shard. Missing shards are detected and reported via the `/api/sharding/verify` endpoint.

## Verification

### Sharding Tests (`test_module_b_sharding.py` — 10 tests)

1. Migration correctness — each record exists in exactly one shard
2. Single-key lookup routes to correct shard
3. API inserts go to correct shard based on sessionID hash
4. Range queries aggregate from all shards
5. Token consume works across shards
6. Shard verification endpoint returns all-pass
7. Dashboard counts match scatter-gather totals
8. Sharding info endpoint returns valid config
9. Table classification (sharded vs unsharded) is correct
10. Shard ID computation is deterministic

### Integration Tests

- `test_blinddrop_transfer.py` — Upload → download → delete with shard-aware routing (8 tests)
- `test_blinddrop_expiry.py` — Expiry cleanup across all shards (3 tests)

### Running Tests

```bash
cd assignment-04
python3 run_module_b_tests.py
```

## Project Structure

```
assignment-04/
├── db_management_system/
│   ├── app.py                    # Flask application entry point
│   ├── api/routes.py             # All API endpoints (shard-aware)
│   ├── shard_manager.py          # Shard infrastructure (NUM_SHARDS=3, connections)
│   ├── shard_router.py           # Query routing (lookup, insert, scatter-gather)
│   ├── migrate_to_shards.py      # One-time data migration script
│   ├── file_handler.py           # File I/O operations
│   ├── cleanup.py                # Background expiry daemon (shard-aware)
│   ├── sql/                      # DDL schemas
│   └── requirements.txt
├── frontend/                     # Next.js frontend (demonstrates working app)
├── tests/
│   ├── test_module_b_sharding.py # Shard integrity tests (10)
│   ├── test_blinddrop_transfer.py # End-to-end transfer tests (8)
│   ├── test_blinddrop_expiry.py  # Expiry tests (3)
│   └── test_module_b_base.py     # Base CRUD tests
├── test_results/
├── run_module_b_tests.py         # Test runner
├── README.md
└── links.md
```

## Setup

### Backend

```bash
cd assignment-04/db_management_system
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 migrate_to_shards.py    # Run migration first
python3 app.py                  # Start server on port 8080
```

### Frontend

```bash
cd assignment-04/frontend
npm install
npm run dev     # Start on port 3000
```

## API Endpoints for Sharding

| Endpoint | Description |
|----------|-------------|
| `GET /api/sharding/info` | Shard config, per-table record counts per shard |
| `GET /api/sharding/verify` | Integrity checks: count, duplicates, hash consistency |
| `GET /api/admin/transfer-stats` | Aggregate stats across all shards |
