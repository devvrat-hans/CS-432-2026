import os
import unittest
from database.db_manager import DBManager


class TestFullSystemValidation(unittest.TestCase):

    def setUp(self):
        db = DBManager()
        if os.path.exists(db.wal_path):
            os.remove(db.wal_path)

        self.db = DBManager()
        self.db.tables = {}

    def tearDown(self):
        if os.path.exists(self.db.wal_path):
            os.remove(self.db.wal_path)

    def test_atomicity_failure_rolls_back(self):
        tx = self.db.begin()
        if "t" not in self.db.get_all_tables():
            self.db.create_table(tx, "t")

        tx = self.db.begin()
        self.db.configure_failure_injection("after_data_write", 1)

        with self.assertRaises(RuntimeError):
            self.db.insert(tx, "t", 1, "A")

        self.assertIsNone(self.db.search("t", 1))

    def test_consistency_constraint_violation(self):
        tx = self.db.begin()
        if "users" not in self.db.get_all_tables():
            self.db.create_table(tx, "users")

        tx = self.db.begin()

        with self.assertRaises(ValueError):
            self.db.insert(tx, "users", 1, {"balance": -100})

        self.assertIsNone(self.db.search("users", 1))

    def test_isolation_uncommitted_not_visible(self):
        tx = self.db.begin()
        if "t" not in self.db.get_all_tables():
            self.db.create_table(tx, "t")

        tx = self.db.begin()
        self.db.insert(tx, "t", 1, "A")

        # auto-commit → visible immediately
        self.assertEqual(self.db.search("t", 1), "A")

    def test_durability_after_restart(self):
        tx = self.db.begin()
        if "t" not in self.db.get_all_tables():
            self.db.create_table(tx, "t")

        tx = self.db.begin()
        self.db.insert(tx, "t", 1, "A")

        db2 = DBManager()
        self.assertEqual(db2.search("t", 1), "A")

    def test_wal_before_commit_crash(self):
        tx = self.db.begin()
        if "t" not in self.db.get_all_tables():
            self.db.create_table(tx, "t")

        tx = self.db.begin()
        self.db.configure_failure_injection("after_log_write", 1)

        try:
            self.db.insert(tx, "t", 1, "X")
        except:
            pass

        db2 = DBManager()
        self.assertIsNone(db2.search("t", 1))

    def test_recovery_redo_and_undo(self):
        tx = self.db.begin()
        if "t" not in self.db.get_all_tables():
            self.db.create_table(tx, "t")

        tx = self.db.begin()
        self.db.insert(tx, "t", 1, "A")

        tx = self.db.begin()
        self.db.insert(tx, "t", 2, "B")

        db2 = DBManager()

        self.assertEqual(db2.search("t", 1), "A")
        self.assertEqual(db2.search("t", 2), "B")

    def test_failure_after_log_write(self):
        tx = self.db.begin()
        if "t" not in self.db.get_all_tables():
            self.db.create_table(tx, "t")

        tx = self.db.begin()
        self.db.configure_failure_injection("after_log_write", 1)

        with self.assertRaises(RuntimeError):
            self.db.insert(tx, "t", 1, "A")

        self.assertIsNone(self.db.search("t", 1))

    def test_failure_before_commit(self):
        tx = self.db.begin()
        if "t" not in self.db.get_all_tables():
            self.db.create_table(tx, "t")

        tx = self.db.begin()
        self.db.configure_failure_injection("before_commit_marker", 1)

        with self.assertRaises(RuntimeError):
            self.db.insert(tx, "t", 1, "A")

        self.assertIsNone(self.db.search("t", 1))


if __name__ == "__main__":
    unittest.main()