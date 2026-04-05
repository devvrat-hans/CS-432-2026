# CS-432-2026 Repository

This repository contains coursework for CS-432 (Databases), including Assignment 03.

## Repository Structure

- assignment-01/
- assignment-02/
- assignment-03/
  - Module_A/
  - Module_B/

## Assignment 03 Module B (Submission Focus)

Path: `assignment-03/Module_B/`

Module B covers high-concurrency API validation and stress/failure reliability checks.

Implemented scope includes:
- concurrent usage correctness
- race-condition safety
- failure injection with rollback validation
- durability checks after restart simulation
- stress validation with phase metrics
- audit-log observability validation

## Module B Quick Start

Backend:

```bash
cd assignment-03/Module_B/db_management_system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Frontend:

```bash
cd assignment-03/Module_B/frontend
npm install
npm run dev
```

## Module B Validation Commands

From repository root:

```bash
python3 assignment-03/Module_B/run_module_b_tests.py
```

From `assignment-03/Module_B/`:

```bash
python3 run_module_b_tests.py
python3 run_module_b_tests.py --run-stress-orchestrator
```

Standalone stress orchestrator:

```bash
python3 run_stress_orchestrator.py
```

## Module B Output Artifacts

Generated under `assignment-03/Module_B/test_results/`:
- per-suite test result files
- stress phase metrics (`stress_phase_metrics.jsonl`)
- stress telemetry (`stress_telemetry.jsonl`)
- phase evaluation summary (`stress_phase_evaluation.json`)
- orchestrator run summary (`stress_orchestrator_results.txt`)

For complete Module B technical details, use:
- `assignment-03/Module_B/README.md`
