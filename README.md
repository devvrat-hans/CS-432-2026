# CS-432-2026 Repository

This repository contains coursework for CS-432 (Databases) across multiple assignments,
including Assignment 03 implementation work.

## Repository Structure

- assignment-01/
  - SQL schema, inserts, queries, and result notes.
- assignment-02/
  - Earlier assignment deliverables (Module A and Module B).
- assignment03/
  - Active Assignment 03 working directory.
  - Module_A includes transaction engine, WAL, rollback, crash recovery,
    consistency validation, failure injection, observability, and comprehensive tests.

## Assignment 03 Focus

Path: assignment03/

### Module A

Path: assignment03/Module_A/

Implemented:
- Transaction context lifecycle and staged mutations
- Write-ahead logging with structured events
- Rollback engine (including idempotent rollback support)
- Crash recovery for committed and incomplete transactions
- Consistency checks between data and B+ Tree index
- Deterministic failure injection checkpoints
- Transaction-level trace logging and recovery summaries
- Evidence artifacts for report/video support

Core tests:
- test_bplustree.py
- test_dbmanager.py
- test_acid_validation.py
- test_restart_recovery.py
- test_observability.py
- test_hardening.py
- test_reliability_edge_cases.py

Run Module A validation:

/Users/devvrathans/college/semester-06/CS-432-2026/venv/bin/python -m unittest test_bplustree.py test_dbmanager.py test_acid_validation.py test_restart_recovery.py test_observability.py test_hardening.py test_reliability_edge_cases.py

## Notes

- Local-only helper files are intentionally untracked via .gitignore.
- Build/cache artifacts and virtual environments are excluded from version control.
