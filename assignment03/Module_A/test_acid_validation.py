import os
import unittest

from database.db_manager import DBManager


class TestACIDValidation(unittest.TestCase):
    def setUp(self):
        bootstrap = DBManager()
        self.wal_path = bootstrap.wal_path

        if os.path.exists(self.wal_path):
            os.remove(self.wal_path)

        self.db = DBManager()

    def tearDown(self):
        if os.path.exists(self.wal_path):
            os.remove(self.wal_path)

    def _assert_all_tables_consistent(self, db):
        for report in db.get_consistency_report():
            self.assertTrue(report["ok"], f"Consistency failed: {report}")

    def test_atomicity_failure_rolls_back(self):
        self.db.create_table("students")
        self.db.configure_failure_injection("after_data_write", trigger_after_hits=1)

        with self.assertRaises(RuntimeError):
            self.db.insert("students", 1, "Alice")

        self.assertIsNone(self.db.search("students", 1))
        self.assertEqual(self.db.table_size("students"), 0)
        self._assert_all_tables_consistent(self.db)

    def test_consistency_normal_and_rollback_paths(self):
        self.db.create_table("students")
        self.db.insert("students", 1, "Alice")
        self._assert_all_tables_consistent(self.db)

        self.db.configure_failure_injection("before_commit_marker", trigger_after_hits=1)
        with self.assertRaises(RuntimeError):
            self.db.update("students", 1, "Alicia")

        self.assertEqual(self.db.search("students", 1), "Alice")
        self._assert_all_tables_consistent(self.db)

    def test_durability_after_restart(self):
        self.db.create_table("students")
        self.db.insert("students", 1, "Alice")
        self.db.update("students", 1, "Alicia")

        restarted = DBManager()
        self.assertEqual(restarted.search("students", 1), "Alicia")
        self._assert_all_tables_consistent(restarted)

    def test_index_data_sync_after_failure_injection(self):
        self.db.create_table("students")
        self.db.insert("students", 1, "Alice")
        self.db.insert("students", 2, "Bob")

        self.db.configure_failure_injection("after_index_write", trigger_after_hits=1)
        with self.assertRaises(RuntimeError):
            self.db.bulk_insert("students", [(3, "Carol"), (4, "David")])

        self.assertEqual(self.db.get_all("students"), [(1, "Alice"), (2, "Bob")])
        self._assert_all_tables_consistent(self.db)


if __name__ == "__main__":
    unittest.main()
