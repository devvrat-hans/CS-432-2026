# Assignment 02 - Module B: Local API Development, RBAC, and Database Optimisation

**Project Name**: Blind Drop - Privacy-Focused File Transfer Portal

---

## Module B Overview

This module transitions the theoretical database schema developed in Task 1 into a fully functional local web application. It features comprehensive REST APIs, strict Role-Based Access Control (RBAC), security audit logging, and a robust Next.js frontend UI. It also includes SQL indexing and API-level benchmarking for query optimization.

### Project Structure

Module B is organized into two runtime parts: a Flask backend and a Next.js frontend.

```text
Module_B/
├── README.md
├── db_management_system/
│   ├── app.py
│   ├── requirements.txt
│   ├── module_b.sqlite3
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── database/
│   ├── logs/
│   │   └── audit.log
│   └── sql/
│       ├── schema_core_tables.sql
│       ├── schema_project_tables.sql
│       └── indexes.sql
└── frontend/
    ├── package.json
    ├── .env.example
    ├── src/
    │   ├── app/
    │   │   ├── login/
    │   │   ├── admin/
    │   │   │   ├── page.tsx
    │   │   │   ├── databases/
    │   │   │   ├── members/
    │   │   │   └── audit-logs/
    │   │   └── (dashboard)/
    │   └── components/
    └── ...
```

What each major folder is responsible for:

1. `db_management_system/`
   Backend runtime for Module B. It exposes authenticated REST APIs, enforces RBAC, manages SQLite persistence, and writes audit/security logs.

2. `db_management_system/api/routes.py`
   Main API implementation file. It includes session validation, role checks, member/admin routes, database/table routes, indexing benchmarks, and audit logging logic.

3. `db_management_system/sql/`
   SQL assets used for schema/index setup and reference:
   - `schema_project_tables.sql` is loaded by backend initialization.
   - `schema_core_tables.sql` and `indexes.sql` are kept as explicit SQL artifacts for submission and manual DB setup/reference.

4. `frontend/src/app/login/`
   Authentication UI that collects credentials and requests backend token issuance.

5. `frontend/src/app/(dashboard)/`
   Normal user-facing dashboard pages.

6. `frontend/src/app/admin/`
   RBAC-protected admin pages for analytics, member management, database registry, and audit logs.

7. `frontend/src/components/`
   Shared UI primitives such as sidebars/header/auth wrappers used by both dashboard and admin pages.

---

## Prerequisites

Before trying to run the project, make sure these are installed on your system:
1. **Python 3.13+**
2. **Node.js 18+** / npm
3. **Git**

---

## Setup & Execution Instructions

Since Module B requires both the backend (APIs/database) and the frontend (web UI) to run together, follow these instructions to get both components running locally.

### 1. Initialise the Backend (Database System & APIs)

The backend provides API logic over the local SQLite storage and serves validation-protected endpoints on port `8080`.

1. Open your terminal and navigate to the backend directory:
   ```bash
   cd assignment-02/Module_B/db_management_system
   ```
2. Create and activate a Virtual Environment (Recommended):
   ```bash
   python3.13 -m venv venv
   source venv/bin/activate  # Windows users: `venv\Scripts\activate`
   ```
3. Install the required external Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the Application Server:
   ```bash
   python3.13 app.py
   ```
> **Note**: Upon the first initialization, the script will automatically create `module_b.sqlite3`, constructing all the required schemas. The system will also automatically insert a default `admin` credential so that you will be able to log in securely natively. The API binds to `http://127.0.0.1:8080`.
>
> Default initial login:
> - Username: `admin`
> - Password: `admin123`

### 2. Start the Frontend (Next.js User Interface)

The web UI consumes the local APIs and provides an interface for interacting with your Database application via JWT sessions.

1. Open a **new terminal tab** and navigate to the frontend directory:
   ```bash
   cd assignment-02/Module_B/frontend
   ```
2. Install the necessary NPM dependencies:
   ```bash
   npm install
   ```
3. Configure frontend environment variables:
   ```bash
   cp .env.example .env
   ```
   Default value:
   - `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8080/api`
4. Run the Next.js Development Server:
   ```bash
   npm run dev
   ```
5. Finally, open a browser and enter [http://localhost:3000](http://localhost:3000).

### Environment Variables (Module B)

Frontend (`frontend/.env`):
- `NEXT_PUBLIC_API_BASE`: Base URL for backend APIs.

Backend (`db_management_system/`):
- No additional `.env` variables are required for the current Module B implementation.

---

## Authentication & RBAC

All endpoints check for valid PyJWT authorization strictly managed by the React frontend via HTTP Bearer paths. 

**Logging In for the First Time:**
The backend initialization creates a default admin account for first-run access:
- Username: `admin`
- Password: `admin123`

### Access Roles

Strict Role-Based Access Control has been implemented across backend decorators (`@require_session`, `@require_admin`) and frontend route behavior:

- **Admins (`role: 'admin'`)**: 
  Have unrestricted privileges. They can delete members in the 'Member Portfolio', create new users with assigned groups, explore database structures visually, see the comprehensive telemetry audit logs, and trigger direct execution benchmarks on demand.
- **Regular Users (`role: 'user'`)**: 
  Are actively restricted from sensitive actions. From the API Level, `DELETE /members` will yield `HTTP 403: Forbidden`. In the frontend UI, `users` are locked out of viewing other individuals' full records or accessing the telemetry datasets entirely.

---

## Features & Subtask Details

### Member Portfolio & Core System Management (SubTask 1 & 2)
The Next.js `/admin/members` route maps onto SQLite. Admins can successfully CRUD user records dynamically. Only properly assigned elements reflect accurately. 

### Auditing & Logging Control (SubTask 3)
Any operation involving UPDATE/DELETE/INSERT over local APIs writes explicit audit entries into `audit_logs` and the local audit logger stream. Unauthorized session attempts are logged and rejected.

### SQL Optimization & Benchmarking (SubTask 4 & 5)
1. **Indexing Strategy**: SQL indexes are applied to frequently queried fields used by API endpoints.
2. **Performance Calculation Dashboard**: The `QUERY LATENCY` widget reports measured API/query timing so before/after indexing behavior can be compared.

---

## SubTask 6: Video Demonstration with Audio Explanation

This subtask requires a 3-5 minute screen recording with voice-over. Use the checklist below while recording so your submission matches the rubric.

### Recording Checklist

1. Start backend and frontend locally.
2. Open login page and authenticate as admin.
3. Show admin dashboard live counters and query/index metrics.
4. Open Member Portfolio and perform at least one create and one delete action.
5. Open Databases and perform project-table CRUD:
   - Create record
   - Read records
   - Update one record
   - Delete one record
6. Show RBAC enforcement:
   - Login as regular user
   - Demonstrate restricted/denied access for admin-only actions
7. Open Audit Logs page and show:
   - Recorded mutation actions
8. Trigger indexing/performance endpoints from dashboard and explain before-vs-after values.
9. End with a quick codebase structure recap (backend, frontend, sql, logs).

### Suggested Audio Script Flow

1. Introduce Module B scope and stack.
2. Explain local authentication and session validation.
3. Explain RBAC roles and why unauthorized actions are blocked.
4. Demonstrate audit logging visibility for admin traceability.
5. Explain indexing strategy and benchmark comparison results.
6. Conclude with compliance against SubTasks 1-5.

### Submission Note

Upload the final video to Google Drive or YouTube (Unlisted) and add the share link in your final report submission.
