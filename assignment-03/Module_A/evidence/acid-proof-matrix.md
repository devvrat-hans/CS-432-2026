# ACID Proof Matrix (Module A)

Test run command:
- python -m unittest test_bplustree.py test_dbmanager.py test_acid_validation.py test_restart_recovery.py test_observability.py test_hardening.py test_reliability_edge_cases.py

Run result:
- Ran 13 tests in 0.010s
- Status: OK

| Property | Scenario | Test Coverage | Expected Behavior | Result |
|---|---|---|---|---|
| Atomicity | Injected crash after data write during insert | test_acid_validation.py::test_atomicity_failure_rolls_back | Failed mutation leaves no partial row persisted | PASS |
| Atomicity | Injected failure before commit marker during update | test_acid_validation.py::test_consistency_normal_and_rollback_paths | Original value restored, no partial commit | PASS |
| Consistency | Normal write path + rollback path consistency checks | test_acid_validation.py::test_consistency_normal_and_rollback_paths | Consistency report remains ok after both paths | PASS |
| Consistency | Duplicate key interleaving rejection with no side effects | test_hardening.py::test_duplicate_key_interleaving_has_no_partial_state | Duplicate conflicts rejected with stable table state | PASS |
| Isolation (single-process staged execution model) | Staged mutation with rollback on failures | test_hardening.py::test_failed_mutation_writes_rollback_wal_and_restores_state | Transaction rollback isolates failed mutation effects | PASS |
| Durability | Restart recovery after committed writes | test_acid_validation.py::test_durability_after_restart | Committed values survive process restart | PASS |
| Durability | Repeated crash/recover cycles with mixed success/failure operations | test_restart_recovery.py::test_repeated_crash_recovery_preserves_commits | Committed data preserved across all restarts | PASS |
| Durability + Consistency | Restart cycles over update/delete paths with injected failures | test_restart_recovery.py::test_repeated_restart_with_update_delete_paths | Committed updates persist; failed deletes do not leak | PASS |
| Durability + Recovery Safety | Malformed WAL handling with valid replay continuity | test_reliability_edge_cases.py::test_recovery_handles_malformed_wal_entries | Valid committed entries replayed while malformed rows are skipped and counted | PASS |
| Atomicity + Rollback Safety | Manual rollback idempotency on repeated calls | test_reliability_edge_cases.py::test_manual_rollback_is_idempotent | Repeated rollback attempts do not corrupt state | PASS |
| Observability | Recovery summary and trace events | test_observability.py::test_transaction_trace_logging, test_observability.py::test_concise_recovery_summary | Recovery summary present and transaction trace phases emitted | PASS |
