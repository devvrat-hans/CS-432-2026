import os
import unittest

from database.db_manager import DBManager


class TestObservability(unittest.TestCase):
    def setUp(self):
        bootstrap = DBManager()
        self.wal_path = bootstrap.wal_path

        if os.path.exists(self.wal_path):
            os.remove(self.wal_path)

    def tearDown(self):
        if os.path.exists(self.wal_path):
            os.remove(self.wal_path)

    def test_transaction_trace_logging(self):
        db = DBManager()
        db.create_table("audit_test")
        db.insert("audit_test", 1, "ok")

        db.configure_failure_injection("after_data_write", trigger_after_hits=1)
        with self.assertRaises(RuntimeError):
            db.insert("audit_test", 2, "will_rollback")

        logs = db.get_trace_logs()
        phases = {entry["phase"] for entry in logs}

        self.assertIn("transaction_begin", phases)
        self.assertIn("staged_mutation_start", phases)
        self.assertIn("wal_staged_written", phases)
        self.assertIn("rollback_complete", phases)
        self.assertIn("transaction_rolled_back", phases)

        rollback_logs = [entry for entry in logs if entry["phase"] == "rollback_complete"]
        self.assertTrue(any("error" in entry["details"] for entry in rollback_logs))

    def test_concise_recovery_summary(self):
        db = DBManager()
        db.create_table("audit_test")
        db.insert("audit_test", 1, "persisted")

        restarted = DBManager()
        summary = restarted.get_recovery_summary()

        self.assertIn("summary", summary)
        self.assertIn("committed=", summary["summary"])
        self.assertIn("incomplete=", summary["summary"])
        self.assertIn("malformed=", summary["summary"])
        self.assertGreaterEqual(summary["total_entries"], 1)

        logs = restarted.get_trace_logs(transaction_id="system")
        self.assertTrue(any(log["phase"] == "recovery_complete" for log in logs))


if __name__ == "__main__":
    unittest.main()
