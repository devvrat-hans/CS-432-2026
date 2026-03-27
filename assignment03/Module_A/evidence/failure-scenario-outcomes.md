# Failure Scenario Outcomes (Module A)

Scope:
- Deterministic failure injection checkpoints:
  - after_index_write
  - after_log_write
  - after_data_write
  - before_commit_marker

## Scenario Outcomes

1. Mid-operation crash after data write
- Trigger: after_data_write
- Evidence: test_acid_validation.py::test_atomicity_failure_rolls_back
- Outcome: row not persisted, table size unchanged, consistency checks pass.

2. Failure before commit marker
- Trigger: before_commit_marker
- Evidence: test_acid_validation.py::test_consistency_normal_and_rollback_paths
- Outcome: pre-transaction value restored, no dirty commit observed.

3. Bulk insert duplicate-key interleaving
- Trigger: duplicate existing key and duplicate input key pair
- Evidence: test_hardening.py::test_duplicate_key_interleaving_has_no_partial_state
- Outcome: operation rejected, no partial rows inserted.

4. Failure after WAL staged write
- Trigger: after_log_write
- Evidence: test_hardening.py::test_failed_mutation_writes_rollback_wal_and_restores_state
- Outcome: rollback WAL emitted, transaction state restored, no committed status for failed transaction.

5. Repeated crash/recover durability cycles
- Trigger: alternating successful writes + injected failures over restart loops
- Evidence: test_restart_recovery.py::test_repeated_crash_recovery_preserves_commits
- Outcome: committed records remain present after each restart; failed records remain absent.

6. Repeated update/delete with restart recovery
- Trigger: commit update + injected failed delete before commit marker
- Evidence: test_restart_recovery.py::test_repeated_restart_with_update_delete_paths
- Outcome: committed updates preserved, failed deletes rolled back across restart cycles.

7. Malformed WAL plus valid committed transaction replay
- Trigger: malformed JSON line and malformed schema line mixed with valid committed WAL event
- Evidence: test_reliability_edge_cases.py::test_recovery_handles_malformed_wal_entries
- Outcome: malformed entries counted and skipped; valid committed record restored.

8. Repeated manual rollback invocation on same transaction
- Trigger: rollback_transaction called multiple times for the same update transaction
- Evidence: test_reliability_edge_cases.py::test_manual_rollback_is_idempotent
- Outcome: rollback remains idempotent and state stays consistent.

## Final Status
- Consolidated suite outcome: PASS
- Command: /Users/devvrathans/college/semester-06/CS-432-2026/venv/bin/python -m unittest test_bplustree.py test_dbmanager.py test_acid_validation.py test_restart_recovery.py test_observability.py test_hardening.py test_reliability_edge_cases.py
- Result: Ran 13 tests in 0.010s, OK
