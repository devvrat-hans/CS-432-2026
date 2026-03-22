from database.bplustree import BPlusTree


class Table:
    def __init__(self, name):
        self.name = name
        self.index = BPlusTree()
        self.count = 0

    # ---------------- INSERT ----------------
    def insert(self, key, value):
        if key is None:
            raise ValueError("Key cannot be None.")

        if self.index.search(key) is not None:
            raise ValueError(f"Duplicate key '{key}'.")

        self.index.insert(key, value)
        self.count += 1

    # ---------------- SEARCH ----------------
    def search(self, key):
        if key is None:
            raise ValueError("Key cannot be None.")

        return self.index.search(key)

    # ---------------- UPDATE ----------------
    def update(self, key, new_value):
        if key is None:
            raise ValueError("Key cannot be None.")

        updated = self.index.update(key, new_value)
        return updated

    # ---------------- DELETE ----------------
    def delete(self, key):
        if key is None:
            raise ValueError("Key cannot be None.")

        if self.index.search(key) is None:
            return False

        deleted = self.index.delete(key)
        if deleted:
            self.count -= 1

        return deleted

    # ---------------- RANGE QUERY ----------------
    def range_query(self, start_key, end_key):
        if start_key is None or end_key is None:
            raise ValueError("Keys cannot be None.")

        if start_key > end_key:
            raise ValueError("start_key cannot be greater than end_key.")

        return self.index.range_query(start_key, end_key)

    # ---------------- GET ALL ----------------
    def get_all(self):
        return self.index.get_all()

    # ---------------- SIZE ----------------
    def size(self):
        return self.count

    # ---------------- CLEAR ----------------
    def clear(self):
        self.index = BPlusTree()
        self.count = 0

    # ---------------- AGGREGATION ----------------
    def min_key(self):
        data = self.get_all()
        return data[0] if data else None

    def max_key(self):
        data = self.get_all()
        return data[-1] if data else None

    def count_records(self):
        return self.count

    # ---------------- STRING ----------------
    def __str__(self):
        return f"Table(name={self.name}, size={self.count})"
