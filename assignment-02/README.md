# Module B — Blind Drop: API Development, RBAC & Database Optimisation

CS 432 Databases — Track 1, Assignment 2 | IIT Gandhinagar

---

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | Python 3.11 + Flask + psycopg2      |
| Auth       | JWT (PyJWT) + bcrypt                |
| Database   | PostgreSQL 15                        |
| Frontend   | React 18 + Vite + Tailwind CSS      |
| Package Mgr| Yarn (frontend), pip (backend)       |

---

## Directory Structure

```
Module_B/
├── backend/
│   ├── app.py                  Flask entry point
│   ├── config.py               DB + JWT config
│   ├── db.py                   PostgreSQL helpers
│   ├── auth.py                 JWT + decorators
│   ├── logger.py               audit.log writer
│   ├── .env                    Environment variables
│   ├── requirements.txt
│   └── routes/
│       ├── auth_routes.py      /login  /isAuth  /
│       ├── member_routes.py    CRUD /api/members
│       ├── user_routes.py      CRUD /api/users  /api/groups
│       ├── crud_routes.py      All 10 other tables
│       └── benchmark_routes.py GET /api/benchmark
│
├── frontend/
│   ├── package.json            React + Vite + Tailwind
│   ├── src/
│   │   ├── App.jsx             Router + all routes
│   │   ├── pages/              Login, Dashboard, all data pages
│   │   ├── components/         Sidebar, UI primitives
│   │   ├── context/            AuthContext (JWT state)
│   │   └── api/                axios instance with interceptor
│
├── sql/
│   ├── 01_core_tables.sql      UserLogin, UserGroup, UserGroupMapping
│   ├── 02_project_tables.sql   All 12 Assignment 1 tables (unchanged)
│   ├── 03_indexes.sql          20 performance indexes
│   └── 04_seed_data.sql        All seed rows + 16 auth users
│
├── logs/
│   └── audit.log               Auto-generated API audit log
│
└── report/
    └── report.ipynb            Benchmarking + EXPLAIN analysis
```

---

## Quick Setup

### 1. PostgreSQL Database

```bash
# Create the database
psql -U postgres -c "CREATE DATABASE blinddrop;"

# Run SQL scripts in order
psql -U postgres -d blinddrop -f sql/02_project_tables.sql
psql -U postgres -d blinddrop -f sql/01_core_tables.sql
psql -U postgres -d blinddrop -f sql/04_seed_data.sql
# (indexes applied via benchmark endpoint or manually)
psql -U postgres -d blinddrop -f sql/03_indexes.sql
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt

# Edit .env if your PostgreSQL credentials differ
# DB_HOST=localhost  DB_PORT=5432  DB_NAME=blinddrop
# DB_USER=postgres   DB_PASSWORD=postgres

python app.py
# Runs on http://localhost:5000
```

### 3. Frontend

```bash
cd frontend
yarn install
yarn dev
# Runs on http://localhost:5173
```

---

## Default Login Credentials

| Username       | Password     | Role  |
|----------------|--------------|-------|
| `admin`        | `password123`| Admin |
| `aarav.sharma` | `password123`| User  |
| `priya.patel`  | `password123`| User  |
| *(any of 15 member usernames)* | `password123` | User |

---

## API Reference

### Auth (No prefix)
| Method | Endpoint  | Auth     | Description              |
|--------|-----------|----------|--------------------------|
| POST   | /login    | None     | Returns JWT session token |
| GET    | /isAuth   | Bearer   | Validates session         |
| GET    | /         | None     | Welcome message           |

### Members (RBAC enforced)
| Method | Endpoint          | Auth       | Description            |
|--------|-------------------|------------|------------------------|
| GET    | /api/members      | Any user   | List all members       |
| GET    | /api/members/:id  | Own or Admin | Get member profile  |
| POST   | /api/members      | Admin only | Create member          |
| PUT    | /api/members/:id  | Own or Admin | Update member        |
| DELETE | /api/members/:id  | Admin only | Delete member          |

### All Other Tables
Pattern: `GET/POST /api/<table>` and `GET/PUT/DELETE /api/<table>/:id`

Covered: devices, sessions, files, tokens, downloads, ratelimits, integrity, sysadmins, errorlogs, audittrail, policies, users, groups

### Benchmark (Admin only)
| Method | Endpoint        | Description                            |
|--------|-----------------|----------------------------------------|
| GET    | /api/benchmark  | Run before/after index timing + EXPLAIN |

---

## RBAC Summary

| Action                          | Admin | Regular User     |
|---------------------------------|-------|------------------|
| View all members                | ✅    | ✅               |
| View own profile                | ✅    | ✅ (own only)    |
| Create / Delete member          | ✅    | ❌ 403           |
| Update member profile           | ✅    | ✅ (own only)    |
| All write operations            | ✅    | ❌ 403           |
| View sessions / files / tokens  | ✅    | ✅               |
| View error logs                 | ✅    | ❌ 403           |
| View audit trail                | ✅    | ❌ 403           |
| Manage users & roles            | ✅    | ❌ 403           |
| Run benchmark                   | ✅    | ❌ 403           |

---

## Security Logging

Every API write (`POST`, `PUT`, `DELETE`) logs a line to `logs/audit.log`:

```
2026-03-15 10:23:45 | INFO | USER=admin ROLE=admin POST /api/members ACTION=CREATE_MEMBER STATUS=OK DETAIL=memberID=16
2026-03-15 10:24:10 | WARNING | UNAUTHORIZED ip=127.0.0.1 DELETE /api/members/1 REASON=Role 'user' insufficient — admin required
```

Any database modification that does NOT appear in the audit log was made directly (outside the API) and can be flagged as unauthorised during log review.

---

## SQL Indexes Applied

| Index Name                       | Table              | Column(s)              |
|----------------------------------|--------------------|------------------------|
| idx_uploadsession_status         | UploadSession      | status                 |
| idx_uploadsession_deviceid       | UploadSession      | deviceID               |
| idx_uploadsession_policyid       | UploadSession      | policyID               |
| idx_uploadsession_expiry         | UploadSession      | expiryTimestamp        |
| idx_filemetadata_sessionid       | FileMetadata       | sessionID              |
| idx_filemetadata_mimetype        | FileMetadata       | mimeType               |
| idx_onetimetoken_tokenvalue      | OneTimeToken       | tokenValue             |
| idx_onetimetoken_status          | OneTimeToken       | status                 |
| idx_ratelimitlog_deviceid        | RateLimitLog       | deviceID               |
| idx_ratelimitlog_eventtype       | RateLimitLog       | eventType              |
| idx_ratelimitlog_composite       | RateLimitLog       | (deviceID, eventType)  |
| idx_integrity_verified           | FileIntegrityCheck | verified               |
| idx_audittrail_sessionid         | AuditTrail         | sessionID              |
| idx_audittrail_timestamp         | AuditTrail         | timestamp DESC         |
| idx_errorlog_sessionid           | ErrorLog           | sessionID              |
| idx_userlogin_username           | UserLogin          | username               |

---

## Assignment Checklist (Module B)

| Criterion                                    | Status |
|----------------------------------------------|--------|
| Local DB + core/project tables setup         | ✅     |
| CRUD APIs for all project tables             | ✅     |
| Session validation on every API call         | ✅ JWT |
| Member Portfolio UI                          | ✅     |
| Admin role — full access                     | ✅     |
| Regular user — restricted access            | ✅     |
| Deletion integrity (UserLogin cascades)      | ✅     |
| API audit logging to file                    | ✅     |
| Unauthorized access flagging                 | ✅     |
| SQL indexing strategy                        | ✅ 20 indexes |
| EXPLAIN ANALYZE profiling                    | ✅     |
| Before/after benchmarking                    | ✅     |
| Benchmarking charts                          | ✅     |
