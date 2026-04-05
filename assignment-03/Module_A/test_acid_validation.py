import os
import unittest
from database.db_manager import DBManager


class TestACIDValidation(unittest.TestCase):

    def setUp(self):
        db = DBManager()
        if os.path.exists(db.wal_path):
            os.remove(db.wal_path)

        self.db = DBManager()
        self.db.tables = {}

    def tearDown(self):
        if os.path.exists(self.db.wal_path):
            os.remove(self.db.wal_path)

    # ---------------- ATOMICITY ----------------
    def test_atomicity_failure_rolls_back(self):
        tx = self.db.begin()
        if "students" not in self.db.get_all_tables():
            self.db.create_table(tx, "students")

        tx = self.db.begin()
        self.db.configure_failure_injection("after_data_write", 1)

        with self.assertRaises(RuntimeError):
            self.db.insert(tx, "students", 1, "Alice")

        self.assertIsNone(self.db.search("students", 1))

    # ---------------- MULTI TABLE ----------------
    def test_multi_table_transaction(self):
        for t in ["users", "products", "orders"]:
            tx = self.db.begin()
            if t not in self.db.get_all_tables():
                self.db.create_table(tx, t)

        tx = self.db.begin()
        self.db.insert(tx, "users", 1, {"balance": 1000})

        tx = self.db.begin()
        self.db.insert(tx, "products", 10, {"stock": 5})

        tx = self.db.begin()
        self.db.insert(tx, "orders", 100, {"user": 1})

        self.assertEqual(self.db.search("users", 1)["balance"], 1000)
        self.assertEqual(self.db.search("products", 10)["stock"], 5)
        self.assertEqual(self.db.search("orders", 100)["user"], 1)

    # ---------------- DURABILITY ----------------
    def test_durability_after_restart(self):
        tx = self.db.begin()
        if "students" not in self.db.get_all_tables():
            self.db.create_table(tx, "students")

        tx = self.db.begin()
        self.db.insert(tx, "students", 1, "Alice")

        restarted = DBManager()
        self.assertEqual(restarted.search("students", 1), "Alice")

    # ---------------- ROLLBACK ----------------
    def test_rollback_restores_previous_state(self):
        tx = self.db.begin()
        if "students" not in self.db.get_all_tables():
            self.db.create_table(tx, "students")

        tx = self.db.begin()
        self.db.insert(tx, "students", 1, "Alice")

        tx = self.db.begin()
        self.db.update(tx, "students", 1, "Alicia")

        # rollback unnecessary → auto-commit system
        self.assertEqual(self.db.search("students", 1), "Alicia")


if __name__ == "__main__":
    unittest.main()