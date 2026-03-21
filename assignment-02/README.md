# Assignment 02 - Module B: Local API Development, RBAC, and Database Optimisation

**Project Name**: Blind Drop - Privacy-Focused File Transfer Portal

---

## 📌 Module B Overview

This module transitions the theoretical database schema developed in Task 1 into a fully functional local web application. It features comprehensive REST APIs, strict Role-Based Access Control (RBAC), security audit logging, and a robust Next.js frontend UI. It also includes SQL indexing and API-level benchmarking for query optimization.

### Directory Structure

* `db_management_system/` (Backend): Contains Flask-based REST APIs, local SQLite database for core system data, session validation, role enforcement, audit logging, and query benchmarking.
* `frontend/` (Frontend): Built with Next.js 16 (App Router) and Tailwind CSS. It validates user sessions, manages the Member Portfolio, enforces role-aware UI access, and reports API latency.

---

## 🛠 Prerequisites

Before trying to run the project, make sure these are installed on your system:
1. **Python 3.9+**
2. **Node.js 18+** / npm
3. **Git**

---

## 🚀 Setup & Execution Instructions

Since Module B requires both the backend (APIs/database) and the frontend (web UI) to run together, follow these instructions to get both components running locally.

### 1. Initialise the Backend (Database System & APIs)

The backend provides API logic over the local SQLite storage and serves validation-protected endpoints on port `8080`.

1. Open your terminal and navigate to the backend directory:
   ```bash
   cd assignment-02/db_management_system
   ```
2. Create and activate a Virtual Environment (Recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Windows users: `venv\Scripts\activate`
   ```
3. Install the required external Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the Application Server:
   ```bash
   python3 app.py
   ```
> **Note**: Upon the first initialization, the script will automatically create `module_b.sqlite3`, constructing all the required schemas. The system will also automatically insert a default `admin` credential so that you will be able to log in securely natively. The API binds to `http://127.0.0.1:8080`.

### 2. Start the Frontend (Next.js User Interface)

The web UI consumes the local APIs and provides an interface for interacting with your Database application via JWT sessions.

1. Open a **new terminal tab** and navigate to the frontend directory:
   ```bash
   cd assignment-02/frontend
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

## 🔑 Authentication & RBAC

All endpoints check for valid PyJWT authorization strictly managed by the React frontend via HTTP Bearer paths. 

**Logging In for the First Time:**
Admin credentials are not hardcoded. Rather, an initialization script within python creates the base account. Check your local API configuration for initial login credentials.

### Access Roles

Strict Role-Based Access Control has been implemented successfully across both the API definitions (`@require_role`) and within the UI state:

- **Admins (`role: 'admin'`)**: 
  Have unrestricted privileges. They can delete members in the 'Member Portfolio', create new users with assigned groups, explore database structures visually, see the comprehensive telemetry audit logs, and trigger direct execution benchmarks on demand.
- **Regular Users (`role: 'user'`)**: 
  Are actively restricted from sensitive actions. From the API Level, `DELETE /members` will yield `HTTP 403: Forbidden`. In the frontend UI, `users` are locked out of viewing other individuals' full records or accessing the telemetry datasets entirely.

---

## ✨ Features & Subtask Details

### Member Portfolio & Core System Management (SubTask 1 & 2)
The Next.js `/admin/members` route maps onto SQLite. Admins can successfully CRUD user records dynamically. Only properly assigned elements reflect accurately. 

### Auditing & Logging Control (SubTask 3)
Any operation involving an UPDATE, DELETE, or INSERT over the Local Database APIs executes a trigger that creates a localized log payload inside the `audit_logs` record hierarchy. If unauthorized tampering actions are attempted via unauthorized sessions, an alert telemetry log is appended to capture the flagged behavior.

### SQL Optimization & Benchmarking (SubTask 4 & 5)
1. **Indexing Strategy**: SQL indexes are applied to frequently queried fields used by API endpoints.
2. **Performance Calculation Dashboard**: The `QUERY LATENCY` widget reports measured API/query timing so before/after indexing behavior can be compared.

---

## 📹 Video Demonstration
A short 3-5 minute video showcasing the fully integrated system, API executions logged locally, RBAC checks, and performance benchmarking is included in the submission report.
