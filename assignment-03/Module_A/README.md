# Assignment 3 – Module A: Advanced Transaction Engine & Crash Recovery using B+ Tree

## Assignment Overview

This submission implements **Module A** of CS 432 Assignment 3, focusing on extending the B+ Tree-based DBMS from Assignment 2 with transaction management, ACID guarantees, and crash recovery. The system ensures reliable operations under normal and failure conditions, demonstrating durability, rollback, and multi-table consistency.

**Key Deliverables:**
- Transaction engine with BEGIN, COMMIT, ROLLBACK (auto-commit model in demos).
- Write-Ahead Logging (WAL) for crash recovery.
- ACID validation through comprehensive tests.
- Multi-table operations across users, products, and orders relations.
- Failure injection and recovery demonstrations.

## What Was Implemented

### Core Components
- **B+ Tree Integration**: Primary storage for all relations, ensuring indexed access and structural integrity.
- **Transaction Management**: `TransactionContext` class for tracking operations, before-images, and status.
- **DB Manager**: Handles staging mutations, WAL logging, and recovery on restart.
- **WAL System**: Logs all changes to `logs/transaction_wal.jsonl` for durability.
- **Recovery Logic**: Replays committed transactions and undoes incomplete ones on system initialization.

### Features Demonstrated
- **ACID Properties**: Atomicity (rollback on failure), Consistency (validation checks), Isolation (serialized execution), Durability (WAL persistence).
- **Multi-Table Transactions**: Operations across users, products, and orders (individual commits in current model).
- **Crash Recovery**: Automatic undo of failed transactions and redo of committed ones.
- **Failure Injection**: Simulated crashes at checkpoints (e.g., after data write) for testing.
- **Edge-Case Handling**: Duplicate keys, constraint violations, and malformed WAL entries.

## Project Structure

```
assignment_3_mA/
├── database/
│   ├── bplustree.py          # B+ Tree implementation for indexing and storage
│   ├── db_manager.py         # Main database manager with transaction and recovery logic
│   ├── table.py              # Table abstraction layer
│   ├── transaction.py        # Transaction context and status management
│   └── performance.py        # Performance utilities (if present)
├── logs/
│   └── transaction_wal.jsonl # Write-ahead log file for recovery
├── Output_Files/             # Directory for output files
├── test_acid_validation.py   # ACID property tests (atomicity, durability, rollback)
├── test_full_system_validation.py  # Full system validation (consistency, isolation, recovery)
├── test_hardening.py         # Hardening and failure tests
├── test_reliability_edge_cases.py  # Edge-case reliability tests
├── test_restart_recovery.py  # Restart and recovery tests
├── test_bplustree_acid.py    # B+ Tree ACID tests
├── test_dbmanager.py         # DB Manager tests
├── demo_transaction.py       # Multi-table transaction demo (auto-commit model)
├── btree_acid_advanced_demo.py  # Advanced B+ Tree ACID demo with failure simulation
├── final_demo_output.txt     # Output from demo runs
├── bplustree.png             # B+ Tree visualization (if present)
└── README.md                 # This file
```

## Installation and Setup

- **Python Version**: Requires Python 3.8 or higher.
- **Dependencies**: Install via `pip install graphviz matplotlib pandas`.
- **Graphviz**: Download from [graphviz.org](https://graphviz.org/download/) and ensure `dot` is in PATH.

## How to Run and Validate

### Run Test Suite
Execute all validation tests to demonstrate ACID compliance:

```bash
python -m unittest test_acid_validation.py test_full_system_validation.py test_hardening.py test_reliability_edge_cases.py test_restart_recovery.py
```

**Output**: `Ran 17 tests in 0.421s - OK` (all tests pass, validating atomicity, durability, isolation, consistency, and recovery).

### Run Demonstrations
Showcase the system's capabilities:

- **Multi-Table Demo**:
  ```bash
  python demo_transaction.py
  ```
  Demonstrates simulated multi-step operations: user balance update, product stock reduction, order insertion (each auto-committed individually).

- **Failure and Recovery Demo**:
  ```bash
  python btree_acid_advanced_demo.py
  ```
  Shows failure injection (e.g., crash after data write), rollback restoration, and successful operations.

**Outputs**: Console logs and `final_demo_output.txt` with state changes and consistency reports.

## ACID Validation Results

The implementation ensures:

- **Atomicity**: Failed operations (e.g., after data write crash) leave no partial state.
- **Consistency**: Validation prevents invalid data (e.g., negative balances) and maintains B+ Tree integrity.
- **Isolation**: Serialized execution isolates transactions; uncommitted changes are not visible.
- **Durability**: WAL ensures committed data persists across restarts; recovery reapplies valid changes.

**Test Evidence**: All 17 tests pass, covering scenarios like rollback on failure, restart durability, and multi-table consistency.

## Crash Recovery Mechanism

- **WAL Format**: JSONL entries with transaction ID, timestamp, type (BEGIN/COMMIT), and mutation details.
- **Recovery on Restart**: `DBManager.__init__()` reads WAL, reapplies committed transactions, and undoes incomplete ones.
- **Failure Handling**: Incomplete transactions are rolled back using before-images; malformed entries are skipped.

**Demonstration**: Restart after operations shows data persistence; inspect `logs/transaction_wal.jsonl` for log entries.

## Demonstration for Evaluation

For viva/video submission:

1. **Run Tests**: Show passing suite (17 tests OK).
2. **Multi-Table Operations**: Execute `demo_transaction.py` to display user balance update, stock reduction, and order creation.
3. **Failure Simulation**: Run `btree_acid_advanced_demo.py` to inject failure and demonstrate rollback.
4. **Recovery**: Restart system and verify committed data remains; explain WAL replay.
5. **Logs Inspection**: View `transaction_wal.jsonl` and recovery summaries.

## Outputs and Artifacts

- **WAL Logs**: `logs/transaction_wal.jsonl` – JSONL format for recovery.
- **Demo Outputs**: `final_demo_output.txt` – Test results and state changes.
- **Recovery Summary**: Accessible via `DBManager.get_recovery_summary()` (committed/incomplete counts).

## Assignment Requirements Met

- ✅ Transaction management (BEGIN, COMMIT, ROLLBACK APIs).
- ✅ ACID guarantees validated through tests.
- ✅ Crash recovery with WAL and restart replay.
- ✅ Multi-table transactions (demonstrated across 3 relations).
- ✅ Isolation via serialized execution.
- ✅ Consistency and referential integrity checks.
- ✅ Comprehensive test coverage (17 passing tests).

## Conclusion

This Module A submission demonstrates a robust transaction engine built on B+ Trees, with WAL ensuring durability and recovery. The system handles failures gracefully, maintains data integrity, and supports multi-table operations, fulfilling the assignment's goals for reliable database behavior.