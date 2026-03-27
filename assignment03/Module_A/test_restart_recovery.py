import os
import unittest

from database.db_manager import DBManager


class TestRestartRecovery(unittest.TestCase):
    def setUp(self):
        bootstrap = DBManager()
        self.wal_path = bootstrap.wal_path

        if os.path.exists(self.wal_path):
            os.remove(self.wal_path)

    def tearDown(self):
        if os.path.exists(self.wal_path):
            os.remove(self.wal_path)

    def _assert_consistent(self, db):
        for report in db.get_consistency_report():
            self.assertTrue(report["ok"], f"Consistency failure: {report}")

    def _assert_exact_table_state(self, db, table_name, expected):
        expected_items = sorted(expected.items())
        self.assertEqual(db.get_all(table_name), expected_items)
        self.assertEqual(db.table_size(table_name), len(expected_items))

        for key, value in expected_items:
            self.assertEqual(db.search(table_name, key), value)

        self._assert_consistent(db)

    def test_repeated_crash_recovery_preserves_commits(self):
        db = DBManager()
        db.create_table("records")
        expected = {1: "base"}
        db.insert("records", 1, "base")

        failed_keys = []

        for cycle in range(1, 6):
            committed_key = 100 + cycle
            failed_key = 200 + cycle

            db.insert("records", committed_key, f"commit-{cycle}")
            expected[committed_key] = f"commit-{cycle}"

            db.configure_failure_injection("after_data_write", trigger_after_hits=1)
            with self.assertRaises(RuntimeError):
                db.insert("records", failed_key, f"fail-{cycle}")
            failed_keys.append(failed_key)

            db = DBManager()
            self._assert_exact_table_state(db, "records", expected)

            for key in failed_keys:
                self.assertIsNone(db.search("records", key))

    def test_repeated_restart_with_update_delete_paths(self):
        db = DBManager()
        db.create_table("records")
        db.bulk_insert("records", [(1, "v1"), (2, "v2"), (3, "v3")])

        expected = {1: "v1", 2: "v2", 3: "v3"}

        for cycle in range(1, 5):
            expected_value = f"v1-cycle-{cycle}"
            db.update("records", 1, expected_value)
            expected[1] = expected_value

            db.configure_failure_injection("before_commit_marker", trigger_after_hits=1)
            with self.assertRaises(RuntimeError):
                db.delete("records", 2)

            db = DBManager()
            self._assert_exact_table_state(db, "records", expected)
            self.assertEqual(db.search("records", 2), "v2")


if __name__ == "__main__":
    unittest.main()
