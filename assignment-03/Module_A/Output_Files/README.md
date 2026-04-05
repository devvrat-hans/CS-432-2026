# Module A Evidence and Demonstration Report

## 1. Objective
This report demonstrates that the system satisfies Module A requirements for the CS 432 Assignment 3 transaction engine:

- Transaction management with `BEGIN`, `COMMIT`, and `ROLLBACK`
- ACID guarantees for a B+ Tree-backed storage engine
- Crash recovery through write-ahead logging (WAL)
- Multi-table transactions across separate relation B+ Trees
- Serialized concurrency safety and isolation of failure effects
- Consistency and referential integrity after normal and failure paths

## 2. Implementation Summary

### Core Engine
- `database/db_manager.py` implements transaction staging, WAL logging, and recovery.
- `database/transaction.py` defines `TransactionContext` and `TransactionStatus`.
- Each relation is stored in its own B+ Tree and accessed only through the DB manager.

### WAL and Recovery
- WAL file: `logs/transaction_wal.jsonl`
- Recovery is executed on `DBManager` initialization and reconstructs committed state while undoing incomplete transactions.
- The system tracks committed and incomplete transactions in recovery metrics.

### Transaction Model
- Transactions are started via `DBManager.begin()`.
- Mutations are staged and logged before being committed.
- Rollback restores prior values using before-images stored in the transaction context.
- A global lock ensures serialized execution and avoids shared data corruption.

### Multi-Table Support
- The current implementation uses separate tables such as `users`, `products`, and `orders`.
- Multi-table operations are validated through combined insert/update scenarios and cross-table consistency checks.

## 3. Test Evidence

### Command and Result
- Command: `python -m unittest test_acid_validation.py test_full_system_validation.py test_hardening.py test_reliability_edge_cases.py test_restart_recovery.py`
- Result: Ran 17 tests in 0.421s
- Status: OK

### ACID Proof Matrix

| Property | Scenario | Test Coverage | Expected Behavior | Result |
|---|---|---|---|---|
| Atomicity | Crash after data write during insert | `test_acid_validation.py::test_atomicity_failure_rolls_back` | Partial write is not persisted | PASS |
| Atomicity | Multi-table insert transaction | `test_acid_validation.py::test_multi_table_transaction` | All relation inserts succeed consistently | PASS |
| Durability | Restart after committed write | `test_acid_validation.py::test_durability_after_restart` | Committed data survives restart | PASS |
| Consistency | Reject invalid insert data | `test_full_system_validation.py::test_consistency_constraint_violation` | Invalid state prevented and no partial rows | PASS |
| Isolation | Uncommitted writes visibility | `test_full_system_validation.py::test_isolation_uncommitted_not_visible` | No unsafe intermediate state visible | PASS |
| Durability | Crash before commit marker | `test_full_system_validation.py::test_wal_before_commit_crash` | Transaction aborted and not persisted | PASS |
| Recovery | Redo/undo replay after restart | `test_full_system_validation.py::test_recovery_redo_and_undo` | Committed writes persist; failed operations are excluded | PASS |
| Failure handling | Failure after WAL write | `test_full_system_validation.py::test_failure_after_log_write` | Failed transaction is rolled back cleanly | PASS |
| Robustness | Duplicate-key conflict rejection | `test_hardening.py::test_duplicate_key_no_partial_state` | Duplicate insert rejected with stable state | PASS |
| Rollback safety | Failure rollback restoration | `test_hardening.py::test_failure_rollback` | Original row remains after failure | PASS |
| Durability | Restart recovery normal operations | `test_reliability_edge_cases.py::test_recovery_after_operations` | Committed row remains after restart | PASS |
| Durability | Restart recovery after failure | `test_restart_recovery.py::test_recovery_with_failure` | Failed row does not reappear after restart | PASS |
| Durability | Recovery after normal operations | `test_restart_recovery.py::test_recovery_after_operations` | Committed row persists consistently | PASS |

## 4. Failure Scenario Outcomes

### 4.1 Mid-operation crash after data write
- Trigger: `after_data_write` failure injection
- Evidence: `test_acid_validation.py::test_atomicity_failure_rolls_back`
- Outcome: No partial row is persisted; database state remains unchanged.

### 4.2 Failure before commit marker
- Trigger: `before_commit_marker` failure injection
- Evidence: `test_full_system_validation.py::test_failure_before_commit`
- Outcome: Transaction aborts cleanly; no dirty commit or partial record remains.

### 4.3 Duplicate-key conflict rejection
- Trigger: duplicate insert into an existing table
- Evidence: `test_hardening.py::test_duplicate_key_no_partial_state`
- Outcome: Duplicate key is rejected and no partial state is written.

### 4.4 Failure after WAL write during update
- Trigger: `after_log_write` failure injection
- Evidence: `test_full_system_validation.py::test_failure_after_log_write`
- Outcome: The failed transaction is rolled back and WAL integrity is preserved.

### 4.5 Recovery after failed transaction
- Trigger: injected failure followed by restart
- Evidence: `test_restart_recovery.py::test_recovery_with_failure`
- Outcome: Failed row remains absent after restart; committed state persists.

### 4.6 Normal restart durability
- Trigger: restart after a committed write
- Evidence: `test_restart_recovery.py::test_recovery_after_operations`
- Outcome: Committed data remains available after restart.

### 4.7 Constraint violation consistency
- Trigger: invalid negative-value insert
- Evidence: `test_full_system_validation.py::test_consistency_constraint_violation`
- Outcome: Bad input is rejected; integrity is maintained.

## 5. Demonstration Plan

To demonstrate Module A clearly, show the following sequence:

1. Run the test suite and confirm all tests pass.
   - `python -m unittest test_acid_validation.py test_full_system_validation.py test_hardening.py test_reliability_edge_cases.py test_restart_recovery.py`
2. Show `final_demo_output.txt` or execute `python demo_transaction.py` and `python btree_acid_advanced_demo.py` to display end-to-end transaction execution.
3. Explain WAL recovery:
   - WAL is written in `logs/transaction_wal.jsonl`
   - `DBManager` performs replay on startup
   - committed entries are retained; incomplete entries are undone
4. Point to concrete failure scenarios:
   - `after_data_write`, `after_log_write`, `before_commit_marker`
   - verify rollback behavior in tests
5. Show multi-table transaction correctness in `test_acid_validation.py` with `users`, `products`, and `orders`.

## 6. Observability and Artifacts

- `final_demo_output.txt` confirms the implementation passes ACID validation and recovery demonstration.
- `logs/transaction_wal.jsonl` is the persistent recovery artifact.
- Demonstration scripts:
  - `demo_transaction.py`
  - `btree_acid_advanced_demo.py`
- The current repository does not include `test_observability.py`, so observable trace tests are not available in this workspace.

## 7. Verification Sources

- `test_acid_validation.py`
- `test_full_system_validation.py`
- `test_hardening.py`
- `test_reliability_edge_cases.py`
- `test_restart_recovery.py`
- `final_demo_output.txt`

## 8. Conclusion

This Module A implementation satisfies the assignment requirements for:

- atomicity and rollback safety
- consistency and constraint validation
- isolation and serialized transaction execution
- durability through WAL and restart recovery
- multi-table transaction correctness

All current validation tests pass and the evidence report documents the failure mode handling, recovery behavior, and proof of ACID compliance.
