import json
import os
import unittest

from database.db_manager import DBManager


class TestHardening(unittest.TestCase):
    def setUp(self):
        bootstrap = DBManager()
        self.wal_path = bootstrap.wal_path

        if os.path.exists(self.wal_path):
            os.remove(self.wal_path)

        self.db = DBManager()
        self.db.create_table("students")

    def tearDown(self):
        if os.path.exists(self.wal_path):
            os.remove(self.wal_path)

    def test_duplicate_key_interleaving_has_no_partial_state(self):
        self.db.insert("students", 1, "Alice")

        with self.assertRaises(ValueError):
            self.db.bulk_insert("students", [(2, "Bob"), (1, "Duplicate")])

        self.assertEqual(self.db.get_all("students"), [(1, "Alice")])

        with self.assertRaises(ValueError):
            self.db.bulk_insert("students", [(3, "Carol"), (3, "Carol-dup")])

        self.assertEqual(self.db.get_all("students"), [(1, "Alice")])

    def test_failed_mutation_writes_rollback_wal_and_restores_state(self):
        self.db.insert("students", 1, "Alice")

        self.db.configure_failure_injection("after_log_write", trigger_after_hits=1)
        with self.assertRaises(RuntimeError):
            self.db.update("students", 1, "Alicia")

        self.assertEqual(self.db.search("students", 1), "Alice")

        with open(self.wal_path, "r", encoding="utf-8") as wal_file:
            events = [json.loads(line) for line in wal_file if line.strip()]

        failed_tx_id = None
        for event in reversed(events):
            if event.get("status") == "rolled_back":
                failed_tx_id = event.get("transaction_id")
                break

        self.assertIsNotNone(failed_tx_id)

        failed_events = [
            event for event in events if event.get("transaction_id") == failed_tx_id
        ]
        statuses = {event.get("status") for event in failed_events}
        self.assertIn("staged", statuses)
        self.assertIn("rolled_back", statuses)
        self.assertNotIn("committed", statuses)


if __name__ == "__main__":
    unittest.main()
