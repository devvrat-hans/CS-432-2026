# CS 432 Assignment 03 - Module A

## Scope
This module implements and validates transaction behavior, rollback, write-ahead logging,
crash recovery, consistency checks, and deterministic failure injection for the custom
B+ Tree based database engine.

## Core Files
- database/bplustree.py
- database/table.py
- database/transaction.py
- database/db_manager.py

## Validation Tests
- test_bplustree.py
- test_dbmanager.py
- test_acid_validation.py
- test_restart_recovery.py
- test_observability.py
- test_hardening.py
- test_reliability_edge_cases.py

## Evidence Artifacts
- evidence/acid-proof-matrix.md
- evidence/failure-scenario-outcomes.md
- evidence/recovery-correctness-summary.md

## How To Run
From assignment-03/Module_A:

python -m unittest test_bplustree.py test_dbmanager.py test_acid_validation.py test_restart_recovery.py test_observability.py test_hardening.py test_reliability_edge_cases.py
