import os
import unittest
from database.db_manager import DBManager


class TestReliabilityEdgeCases(unittest.TestCase):

    def setUp(self):
        db = DBManager()
        if os.path.exists(db.wal_path):
            os.remove(db.wal_path)

        self.db = DBManager()
        self.db.tables = {}

    def tearDown(self):
        if os.path.exists(self.db.wal_path):
            os.remove(self.db.wal_path)

    def test_recovery_after_operations(self):
        tx = self.db.begin()
        if "records" not in self.db.get_all_tables():
            self.db.create_table(tx, "records")

        tx = self.db.begin()
        self.db.insert(tx, "records", 1, "value")

        db2 = DBManager()

        self.assertEqual(db2.search("records", 1), "value")


if __name__ == "__main__":
    unittest.main()