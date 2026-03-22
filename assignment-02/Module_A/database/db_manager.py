from database.table import Table


class DBManager:
    def __init__(self):
        self.tables = {}

    # ---------------- TABLE MANAGEMENT ----------------

    def create_table(self, name, schema=None, order=3, search_key=None):
        if not name:
            raise ValueError("Table name cannot be empty.")

        if name in self.tables:
            raise ValueError(f"Table '{name}' already exists in database '__default__'")

        table = Table(name, schema=schema, order=order, search_key=search_key)
        self.tables[name] = table
        return table

    def drop_table(self, name):
        if name not in self.tables:
            raise KeyError(f"Table '{name}' does not exist in database '__default__'")

        del self.tables[name]

    def list_tables(self):
        return list(self.tables.keys())

    def get_table(self, name):
        if name not in self.tables:
            raise KeyError(f"Table '{name}' does not exist in database '__default__'")
        return self.tables[name]

    def _get_table(self, name):
        return self.get_table(name)

    # ---------------- CRUD ----------------

    def insert(self, table_name, key, value):
        table = self._get_table(table_name)
        table.insert(key, value)

    def search(self, table_name, key):
        table = self._get_table(table_name)
        return table.search(key)

    def update(self, table_name, key, new_value):
        table = self._get_table(table_name)

        updated = table.update(key, new_value)
        if not updated:
            raise ValueError(f"Key '{key}' not found in table '{table_name}'")

        return True

    def delete(self, table_name, key):
        table = self._get_table(table_name)

        deleted = table.delete(key)
        if not deleted:
            raise ValueError(f"Key '{key}' not found in table '{table_name}'")

        return True

    # ---------------- QUERY ----------------

    def range_query(self, table_name, start_key, end_key):
        if start_key > end_key:
            raise ValueError("start_key cannot be greater than end_key.")

        table = self._get_table(table_name)
        return table.range_query(start_key, end_key)

    def get_all(self, table_name):
        table = self._get_table(table_name)
        return table.get_all()

    # ---------------- BULK ----------------

    def bulk_insert(self, table_name, records):
        table = self._get_table(table_name)

        keys = [k for k, _ in records]

        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate keys found in bulk input.")

        for key in keys:
            if table.search(key) is not None:
                raise ValueError(f"Key '{key}' already exists in table.")

        for key, value in records:
            table.insert(key, value)

    # ---------------- INFO ----------------

    def table_size(self, table_name):
        return self._get_table(table_name).size()

    def min_key(self, table_name):
        return self._get_table(table_name).min_key()

    def max_key(self, table_name):
        return self._get_table(table_name).max_key()

    def count(self, table_name):
        return self._get_table(table_name).count_records()