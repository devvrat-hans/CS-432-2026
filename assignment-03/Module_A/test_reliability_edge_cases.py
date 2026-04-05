import json
import os
import unittest

from database.db_manager import DBManager


class TestReliabilityEdgeCases(unittest.TestCase):
    def setUp(self):
        bootstrap = DBManager()
        self.wal_path = bootstrap.wal_path

        if os.path.exists(self.wal_path):
            os.remove(self.wal_path)

    def tearDown(self):
        if os.path.exists(self.wal_path):
            os.remove(self.wal_path)

    def test_recovery_handles_malformed_wal_entries(self):
        valid_committed_event = {
            "transaction_id": "tx-valid-1",
            "timestamp": "2026-01-01T00:00:00+00:00",
            "operation_type": "insert",
            "table_name": "students",
            "target_entity": "students:1",
            "entity_type": "record",
            "key": 1,
            "status": "committed",
            "before_image": None,
            "after_image": "Alice",
        }

        malformed_json_line = "{bad json\n"
        missing_field_event = {
            "transaction_id": "tx-missing-1",
            "timestamp": "2026-01-01T00:00:01+00:00",
            "operation_type": "insert",
            # missing required status and entity_type
            "table_name": "students",
            "target_entity": "students:2",
            "key": 2,
            "before_image": None,
            "after_image": "Bob",
        }

        with open(self.wal_path, "w", encoding="utf-8") as wal_file:
            wal_file.write(json.dumps(valid_committed_event) + "\n")
            wal_file.write(malformed_json_line)
            wal_file.write(json.dumps(missing_field_event) + "\n")

        db = DBManager()
        summary = db.get_recovery_summary()

        self.assertEqual(db.search("students", 1), "Alice")
        self.assertEqual(summary["applied_committed_transactions"], 1)
        self.assertEqual(summary["malformed_entries"], 2)
        self.assertEqual(summary["total_entries"], 3)

    def test_manual_rollback_is_idempotent(self):
        db = DBManager()
        db.create_table("students")
        db.insert("students", 1, "Alice")
        db.update("students", 1, "Alicia")

        update_tx = db.get_last_transaction()
        self.assertIsNotNone(update_tx)

        db.rollback_transaction(update_tx.transaction_id)
        self.assertEqual(db.search("students", 1), "Alice")

        # Repeating rollback should not corrupt state.
        db.rollback_transaction(update_tx.transaction_id)
        self.assertEqual(db.search("students", 1), "Alice")

        for report in db.get_consistency_report():
            self.assertTrue(report["ok"], f"Consistency failure: {report}")

    def test_failure_injection_trigger_after_hits_is_deterministic(self):
        db = DBManager()
        db.create_table("students")

        db.configure_failure_injection("after_index_write", trigger_after_hits=2)

        db.insert("students", 1, "Alice")
        self.assertEqual(db.search("students", 1), "Alice")

        with self.assertRaises(RuntimeError):
            db.insert("students", 2, "Bob")

        self.assertIsNone(db.search("students", 2))
        self.assertEqual(db.get_all("students"), [(1, "Alice")])


if __name__ == "__main__":
    unittest.main()
