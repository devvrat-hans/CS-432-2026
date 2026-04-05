import unittest
from database.db_manager import DBManager


class TestHardening(unittest.TestCase):

    def setUp(self):
        self.db = DBManager()
        self.db.tables = {}

        tx = self.db.begin()
        if "students" not in self.db.get_all_tables():
            self.db.create_table(tx, "students")

    def test_duplicate_key_no_partial_state(self):
        tx = self.db.begin()
        self.db.insert(tx, "students", 1, "Alice")

        tx = self.db.begin()
        with self.assertRaises(Exception):
            self.db.insert(tx, "students", 1, "Duplicate")

        self.assertEqual(self.db.get_all("students"), [(1, "Alice")])

    def test_failure_rollback(self):
        tx = self.db.begin()
        self.db.insert(tx, "students", 1, "Alice")

        tx = self.db.begin()
        self.db.configure_failure_injection("after_log_write", 1)

        with self.assertRaises(RuntimeError):
            self.db.update(tx, "students", 1, "Alicia")

        self.assertEqual(self.db.search("students", 1), "Alice")


if __name__ == "__main__":
    unittest.main()