# Blind Drop — Privacy-Focused File Transfer Portal

**No login. No trace. Auto-deleted after download.**

## Problem Statement

Transferring files from public computers (libraries, colleges, cybercafes) to personal devices is risky. Logging into email, Drive, or WhatsApp on a shared machine risks password theft or forgotten sessions. USB drives spread viruses. Existing temporary file-sharing sites keep files on servers for days and generate guessable links.

Blind Drop solves this: upload a file, receive a one-time 6-character download code, and the file is permanently deleted the moment it is downloaded — no account, no login, no trace left behind.

## Architecture

```
┌──────────────────────┐         ┌──────────────────────────────────┐
│   Next.js Frontend   │  HTTP   │         Flask Backend            │
│   (port 3000)        │◄───────►│         (port 8080)              │
│                      │         │                                  │
│  /           Landing │         │  POST /api/public/upload         │
│  /upload     Upload  │         │  GET  /api/public/status/<code>  │
│  /download   Download│         │  GET  /api/public/download/<code>│
│  /download/X Direct  │         │  GET  /api/admin/transfer-stats  │
│  /admin      Admin   │         │  GET  /api/sharding/info         │
│  /admin/sharding     │         │  GET  /api/sharding/verify       │
└──────────────────────┘         └───────────┬──────────────────────┘
                                             │
                          ┌──────────────────┼──────────────────┐
                          │                  │                  │
                    ┌─────┴─────┐     ┌──────┴────┐     ┌──────┴────┐
                    │  shard_0  │     │  shard_1  │     │  shard_2  │
                    │  .sqlite3 │     │  .sqlite3 │     │  .sqlite3 │
                    └───────────┘     └───────────┘     └───────────┘
                                             │
                                    ┌────────┴────────┐
                                    │  module_b.sqlite3│
                                    │  (unsharded)     │
                                    └─────────────────┘
                                             │
                                    ┌────────┴────────┐
                                    │    uploads/      │
                                    │  (file storage)  │
                                    └─────────────────┘
```

### Backend (Flask + SQLite)

- **Flask** REST API on port 8080
- **Hash-based horizontal sharding** across 3 SQLite databases using `md5(sessionID) % 3`
- **File storage** on disk in `uploads/` with UUID filenames and SHA-256 checksums
- **Background cleanup daemon** runs every 60 seconds, expiring stale sessions and deleting files
- **CORS** restricted to `localhost:3000` for public endpoints
- **Security headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy`, `Cache-Control: no-store` on public routes

### Frontend (Next.js + TypeScript + Tailwind)

- **Public pages** (no auth): Landing (`/`), Upload (`/upload`), Download (`/download`), Direct download (`/download/<code>`)
- **Admin dashboard** (auth required): Database management, member management, audit logs, shard topology visualization, transfer stats
- **Navbar** with branding, navigation links, and auth-aware user dropdown
- Black & white minimalist design with uppercase tracking-widest typography

### Sharding

**Shard key**: `sessionID` — high cardinality, query-aligned, stable, evenly distributed via MD5 hash.

**Sharded tables (6)**: UploadSession, FileMetadata, OneTimeToken, DownloadLog, ErrorLog, AuditTrail

**Unsharded tables (6)**: Member, Device, ExpiryPolicy, SystemAdmin, RateLimitLog, FileIntegrityCheck

| Database | Contents |
|----------|----------|
| `shard_0.sqlite3` | Sharded records where `md5(sessionID) % 3 == 0` |
| `shard_1.sqlite3` | Sharded records where `md5(sessionID) % 3 == 1` |
| `shard_2.sqlite3` | Sharded records where `md5(sessionID) % 3 == 2` |
| `module_b.sqlite3` | Unsharded tables (Member, Device, etc.) |

### File Storage

- **Location**: `db_management_system/uploads/`
- **Max file size**: 100 MB
- **Naming**: UUID4-based filenames preserving original extension
- **Integrity**: SHA-256 checksum computed at upload, verified at download
- **Lifecycle**: File deleted from disk immediately after download or on expiry

## Upload / Download User Flow

### Upload

1. User visits `/upload` — no login required
2. Drags or selects a file (max 100 MB)
3. Chooses expiry: 15 min, 30 min, 1 hour, or 24 hours
4. Clicks UPLOAD — XHR request with real-time progress bar
5. Server saves file, creates UploadSession + FileMetadata + OneTimeToken on the correct shard
6. User receives a **6-character download code** + QR code linking to `/download/<code>`
7. User shares the code or scans QR on their personal device

### Download

1. User visits `/download` and enters the code, or navigates directly to `/download/<code>`
2. System checks token status via scatter-gather across shards
3. If valid: shows file name + size, user clicks DOWNLOAD
4. File is served, then **immediately**:
   - Token marked `USED`
   - Session marked `DOWNLOADED`
   - Physical file deleted from disk
   - DownloadLog created
5. Code can never be used again

### Expiry

- Background daemon scans all shards every 60 seconds
- Sessions past their `expiryTimestamp` are marked `EXPIRED`
- Associated tokens marked `EXPIRED`
- Physical files deleted
- ErrorLog + AuditTrail records created

## API Reference

### Public Endpoints (No Auth)

#### `POST /api/public/upload`

Upload a file anonymously. Rate limited to 20 uploads per hour per IP.

```
Content-Type: multipart/form-data
Body:
  file: <binary>          (required, max 100 MB)
  expires_in_minutes: 30  (optional, default 30)
```

**201 Created**:
```json
{
  "download_code": "A1B2C3",
  "expires_at": "2026-04-10T15:30:00",
  "file_name": "report.pdf",
  "file_size": 204800
}
```

**413**: File exceeds 100 MB  
**429**: Rate limit exceeded

#### `GET /api/public/status/<code>`

Check validity of a download code.

**200 OK**:
```json
{
  "valid": true,
  "file_name": "report.pdf",
  "file_size": 204800,
  "expires_at": "2026-04-10T15:30:00"
}
```

If invalid: `"valid": false` with `"reason"` field.

#### `GET /api/public/download/<code>`

Download the file. One-time use — file is deleted after serving.

**200 OK**: Binary file content with appropriate Content-Type  
**404**: Invalid code  
**410**: Code already used or expired

### Admin Endpoints (Auth Required)

#### `GET /api/admin/transfer-stats`

Aggregate file transfer statistics across all shards.

```json
{
  "active_files": 42,
  "downloaded_files": 156,
  "expired_files": 23,
  "uploads_today": 15,
  "downloads_today": 28,
  "tokens_today": 67
}
```

#### `GET /api/sharding/info`

Shard configuration and per-table record counts.

```json
{
  "num_shards": 3,
  "shard_key": "sessionID",
  "partitioning_strategy": "hash-based (md5(sessionID) % num_shards)",
  "sharded_tables": ["UploadSession", "FileMetadata", "OneTimeToken", "DownloadLog", "ErrorLog", "AuditTrail"],
  "unsharded_tables": ["Member", "Device", "ExpiryPolicy", "SystemAdmin", "RateLimitLog", "FileIntegrityCheck"],
  "per_table_counts": {
    "UploadSession": { "total": 100, "per_shard": {"0": 33, "1": 34, "2": 33} }
  }
}
```

#### `GET /api/sharding/verify`

Integrity checks per sharded table: record count, duplicate detection, hash consistency.

#### `POST /api/resilience/token-fixtures`

Create token fixtures for testing. Accepts optional `token_value` and `expires_in_minutes`.

#### `POST /api/resilience/consume-token`

Atomically consume a token with optional failure simulation (`simulate_failure`, `failure_stage`).

#### `GET /api/resilience/token-status/<token_value>`

Token inspection: status, download count, timestamps.

#### Other Admin Endpoints

- `POST /api/auth/login` — Authenticate, returns Bearer token
- `GET /api/auth/me` — Get current user info
- `POST /api/auth/logout` — Sign out
- `GET /api/dashboard/summary` — Dashboard aggregate counts
- `GET/POST /api/members` — Member CRUD
- `GET/POST /api/databases` — Database management
- `GET/POST /api/databases/<db>/tables/<table>/records` — Record CRUD
- `GET /api/audit-logs` — Audit log viewer
- `GET /api/indexing/benchmark` — Indexing performance benchmarks

## Security Measures

| Measure | Implementation |
|---------|---------------|
| No login required | Public endpoints bypass auth entirely |
| One-time download | Token marked USED + file deleted after single download |
| Auto-expiry | Background daemon deletes files after chosen expiry window |
| Rate limiting | 20 uploads/hour per IP, logged to ErrorLog |
| File integrity | SHA-256 checksum at upload, verified at download |
| No file traces | UUID filenames, no original names on disk |
| Security headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, CSP |
| No caching | `Cache-Control: no-store` on all public API responses |
| CORS | Public endpoints restricted to `localhost:3000` only |
| File size limit | 100 MB maximum enforced server-side |

## Project Layout

```
blinddrop/
├── db_management_system/
│   ├── app.py                        # Flask app, CORS, security headers
│   ├── api/routes.py                 # All API endpoints (shard-aware)
│   ├── file_handler.py               # File save/delete/checksum
│   ├── cleanup.py                    # Background expiry daemon
│   ├── shard_manager.py              # Shard infra (NUM_SHARDS=3)
│   ├── shard_router.py               # Query routing layer
│   ├── requirements.txt
│   ├── module_b.sqlite3              # Unsharded tables
│   ├── shard_{0,1,2}.sqlite3         # Sharded data
│   ├── uploads/                      # Temporary file storage
│   ├── logs/                         # Application logs
│   └── sql/                          # DDL schemas
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── layout.tsx            # Root layout with Navbar
│       │   ├── page.tsx              # Landing page (public)
│       │   ├── upload/page.tsx       # Upload UI (public)
│       │   ├── download/page.tsx     # Download UI (public)
│       │   ├── download/[code]/page.tsx  # Direct download link
│       │   ├── login/page.tsx        # Admin login
│       │   ├── admin/                # Admin dashboard pages
│       │   └── (dashboard)/          # Protected dashboard routes
│       └── components/
│           ├── Navbar.tsx            # Global nav with auth-aware dropdown
│           ├── UploadDropzone.tsx    # Drag-and-drop file input
│           ├── AuthGate.tsx          # Public route bypass
│           ├── Header.tsx            # Admin header
│           ├── AdminSidebar.tsx      # Admin sidebar navigation
│           └── Sidebar.tsx           # Sidebar component
├── README.md
└── .gitignore
```

## Prerequisites

- Python 3.13+
- Node.js 18+ and npm

## Setup

### Backend

```bash
cd blinddrop/db_management_system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Shard databases are auto-initialized on first startup. Default admin account: `admin` / `admin123`

### Frontend

```bash
cd blinddrop/frontend
npm install
npm run dev
```

Open `http://localhost:3000` — the landing page requires no login.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13+, Flask, SQLite |
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Sharding | MD5 hash-based, 3 SQLite shard databases |
| File Storage | Disk-based, UUID filenames, SHA-256 checksums |
| QR Codes | qrcode.react |
| Icons | Lucide React |
