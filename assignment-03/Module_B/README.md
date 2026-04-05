# Assignment 03 - Module B

Blind Drop: High-Concurrency API Load Testing and Failure Simulation

## Module Objective

Module B focuses on reliability when many users operate concurrently.

Core goals from Assignment 03:
- Concurrent usage correctness
- Race-condition safety
- Failure simulation with rollback
- Stress behavior at high load
- ACID-oriented verification for API behavior

## Project Layout

```text
assignment03/Module_B/
├── README.md
├── run_module_b_tests.py
├── tests/
│   ├── test_module_b_base.py
│   ├── test_module_b_concurrent_usage.py
│   ├── test_module_b_race_conditions.py
│   ├── test_module_b_failure_simulation.py
│   ├── test_module_b_durability.py
│   ├── test_module_b_observability.py
│   ├── test_module_b_stress.py
│   └── test_module_b_multiuser.py
├── test_results/
│   ├── test_results_concurrent_usage.txt
│   ├── test_results_race_conditions.txt
│   ├── test_results_failure_simulation.txt
│   ├── test_results_durability.txt
│   ├── test_results_observability.txt
│   ├── test_results_stress.txt
│   └── test_module_b_multiuser_results.txt
├── db_management_system/
│   ├── app.py
│   ├── api/routes.py
│   ├── requirements.txt
│   └── sql/
└── frontend/
```

## Prerequisites

1. Python 3.13+
2. Node.js 18+ and npm
3. Git

## Setup

### Backend

```bash
cd assignment03/Module_B/db_management_system
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3.13 app.py
```

Default admin account created at first run:
- Username: admin
- Password: admin123

### Frontend

```bash
cd assignment03/Module_B/frontend
npm install
cp .env.example .env
npm run dev
```

Default frontend API base:
- `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8080/api`

## Test Instructions

Run the complete backend validation in one command.

From repository root:

```bash
python3 assignment03/Module_B/run_module_b_tests.py
```

From Module_B directory:

```bash
python3 run_module_b_tests.py
```

This runner executes:
- concurrent usage tests
- race-condition tests
- failure simulation tests
- durability tests (restart/reload simulation)
- observability and audit-log integrity tests
- stress tests (including thousands-scale metrics)
- multi-user isolation and RBAC tests

Each executed test case also writes test execution audit events to `audit_logs`
using `test_case` and `test_suite` actions (started/success/failed/error),
so test activity is traceable alongside API mutation audit events.

## Proof Strategy

### 1. Concurrency Correctness

Implemented evidence:
- `tests/test_module_b_concurrent_usage.py`
- `tests/test_module_b_race_conditions.py`
- `tests/test_module_b_multiuser.py`

What is validated:
- single-winner behavior for shared critical resources
- parallel create/update/delete contention invariants
- admin/user concurrent isolation with RBAC enforcement

### 2. Failure and Rollback Safety

Implemented evidence:
- `tests/test_module_b_failure_simulation.py`

What is validated:
- injected failures at multiple transaction stages
- rollback leaves no partial state
- retry-after-failure succeeds cleanly without residue

### 3. Durability Across Restart/Reload

Implemented evidence:
- `tests/test_module_b_durability.py`

What is validated:
- committed transaction state persists when verified from a fresh Python process
- failed transaction effects do not appear after restart simulation

### 4. Stress and Performance Behavior

Implemented evidence:
- `tests/test_module_b_stress.py`

What is validated:
- hundreds-scale and thousands-scale workloads
- correctness under load and latency metrics (avg, p95, total runtime)
- success-rate and invariant-violation tracking

### 5. Observability Integrity

Implemented evidence:
- `tests/test_module_b_observability.py`

What is validated:
- mutation audit logs include success, failure, and denial paths
- audit records contain integrity fields (action, target, status, timestamp, details)
- test execution activity is captured with dedicated `test_case` and `test_suite` audit actions

## Deliverables and Rubric Mapping

Assignment deliverables:
- Report PDF (`group_name_report.pdf`)
- Short video demonstration

Submission links (placeholders, replace before final submission):
- Repository link placeholder: `https://github.com/your-username/your-repo/tree/main/assignment03/Module_B`
- Report link placeholder: `https://example.com/REPLACE_WITH_FINAL_REPORT_PDF_LINK`
- Video link placeholder: `https://example.com/REPLACE_WITH_FINAL_VIDEO_LINK`

Rubric-aligned technical mapping:

1. Correctness of transaction behavior:
   - failure simulation, race-condition, and rollback suites
2. Proper handling of failures:
   - staged failure injection and retry validations
3. Multi-user safety and isolation:
   - concurrent admin/user RBAC tests and shared-resource contention tests
4. System robustness under load:
   - stress suites with deterministic thresholds and metrics
5. Clarity of explanation:
   - this README + test artifacts + final report and demo video

## Demo Checklist (For Submission Video)

1. Start backend and frontend.
2. Log in as admin and show dashboard.
3. Demonstrate concurrent operations and race safety.
4. Demonstrate injected failure and rollback (no partial commit).
5. Demonstrate retry success after rollback.
6. Demonstrate RBAC denial for regular user actions.
7. Show audit logs for success/failure/denial.
8. Show stress/latency evidence and summarize observations.
