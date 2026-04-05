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
assignment-03/Module_B/
├── README.md
├── run_module_b_tests.py
├── run_stress_orchestrator.py
├── locustfile.py
├── tests/
│   ├── test_module_b_base.py
│   ├── test_module_b_concurrent_usage.py
│   ├── test_module_b_race_conditions.py
│   ├── test_module_b_failure_simulation.py
│   ├── test_module_b_durability.py
│   ├── test_module_b_observability.py
│   ├── test_module_b_stress.py
│   ├── stress_config.py
│   ├── stress_data_utils.py
│   ├── stress_invariants.py
│   ├── stress_metrics.py
│   ├── stress_telemetry.py
│   ├── stress_phase_evaluator.py
│   └── test_module_b_multiuser.py
├── test_results/
│   ├── test_results_concurrent_usage.txt
│   ├── test_results_race_conditions.txt
│   ├── test_results_failure_simulation.txt
│   ├── test_results_durability.txt
│   ├── test_results_observability.txt
│   ├── test_results_stress.txt
│   ├── test_module_b_multiuser_results.txt
│   ├── stress_phase_metrics.jsonl
│   ├── stress_telemetry.jsonl
│   ├── stress_phase_evaluation.json
│   └── stress_orchestrator_results.txt
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
4. Locust (installed via `db_management_system/requirements.txt`)

## Setup

### Backend

```bash
cd assignment-03/Module_B/db_management_system
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
cd assignment-03/Module_B/frontend
npm install
cp .env.example .env
npm run dev
```

Default frontend API base:
- `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8080/api`

## Test Execution

### 1. Standard Module B test suite

From repository root:

```bash
python3 assignment-03/Module_B/run_module_b_tests.py
```

From Module_B directory:

```bash
python3 run_module_b_tests.py
```

### 2. Full suite + integrated stress orchestrator

```bash
python3 run_module_b_tests.py --run-stress-orchestrator
```

Optional orchestrator controls through the main runner:

```bash
python3 run_module_b_tests.py \
   --run-stress-orchestrator \
   --stress-phases baseline,ramp,spike,soak,breakpoint,failure-under-load,final-durability \
   --stress-fast-fail \
   --stress-verbosity 1
```

### 3. Standalone stress orchestrator

```bash
python3 run_stress_orchestrator.py
```

List phases:

```bash
python3 run_stress_orchestrator.py --list-phases
```

Run selected phases with reliability controls:

```bash
python3 run_stress_orchestrator.py \
   --phases ramp,spike,breakpoint \
   --phase-timeout-seconds 120 \
   --phase-retry-limit 1 \
   --fast-fail
```

### 4. Locust workload entrypoint (scenario-driven API load)

```bash
locust -f locustfile.py --host=http://127.0.0.1:8080
```

Environment variables supported by `locustfile.py`:
- `LOCUST_USERNAME`
- `LOCUST_PASSWORD`
- `LOCUST_DB_NAME`
- `LOCUST_TABLE_NAME`
- `LOCUST_WAIT_MIN`
- `LOCUST_WAIT_MAX`

## What the Main Runner Covers

The Module B test runner executes:
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

## Stress Framework Details

The stress framework is now structured around reusable modules:

1. `tests/stress_config.py`
- Central stress profiles: baseline, ramp, spike, soak, breakpoint, failure-under-load
- Shared threshold defaults: success-rate minimum, p95 maximum, invariant-violation maximum

2. `tests/stress_data_utils.py`
- Deterministic stress workspace setup
- Deterministic seed sizes (small/medium/large)
- Cleanup guaranteed in failure paths

3. `tests/stress_invariants.py`
- Per-phase invariant checks
- Count consistency, uniqueness, and orphan/partial state validation
- Immediate failure on invariant breach

4. `tests/stress_metrics.py`
- Structured per-phase metrics generation
- Throughput, avg latency, p95, p99, error rate, phase duration
- JSONL persistence to `test_results/stress_phase_metrics.jsonl`

5. `tests/stress_telemetry.py`
- Timestamped system/process telemetry sampling during phase execution
- CPU/user/system time, memory (max RSS), load averages, thread count
- Phase start/sample/end event boundaries

6. `tests/stress_phase_evaluator.py`
- Threshold-based phase outcome classification
- `pass`, `conditional_pass`, `fail`
- Machine-readable summary generation in `test_results/stress_phase_evaluation.json`

7. `run_stress_orchestrator.py`
- Ordered phase execution pipeline
- Selective phase execution
- Fast-fail mode
- Reliability safeguards for long runs:
   - per-phase timeout
   - per-phase retry-limit
   - graceful cancellation handling
   - clear surfaced errors
   - partial artifact writing even on failure/interruption

## Auditability Guarantees

Stress validation now explicitly verifies audit traces for:
- API mutation paths (`create_database`, `create_table`, `insert_record`, `update_record`, `delete_record`, `consume_token`)
- Failure and rollback paths (`consume_token` with `failed` and `success` states)
- Test execution traces (`test_case`, `test_suite` actions on `module_b_tests` target)

Missing expected audit traces fail the stress suite.

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
- hotspot contention tests for lost-update/duplicate-commit invalid-state detection
- failure-under-load with rollback + retry verification
- correctness under load and structured latency metrics (avg, p95, p99, duration, throughput)
- success-rate and invariant-violation tracking
- telemetry correlation with phase boundaries
- threshold-based phase outcome evaluation

### 5. Observability Integrity

Implemented evidence:
- `tests/test_module_b_observability.py`

What is validated:
- mutation audit logs include success, failure, and denial paths
- audit records contain integrity fields (action, target, status, timestamp, details)
- test execution activity is captured with dedicated `test_case` and `test_suite` audit actions

## Generated Artifacts

During stress/orchestrator runs, the following artifacts are produced in `test_results/`:
- `stress_phase_metrics.jsonl` (machine-parsable per-phase metrics)
- `stress_telemetry.jsonl` (timestamped phase telemetry samples and boundaries)
- `stress_phase_evaluation.json` (phase threshold evaluation: pass/conditional_pass/fail)
- `stress_orchestrator_results.txt` (human-readable orchestrator attempt and outcome log)

## Deliverables and Rubric Mapping

Assignment deliverables:
- Report PDF (`group_name_report.pdf`)
- Short video demonstration

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
   - this README + test artifacts + final report + demo video
