from database.table import Table

class DatabaseManager:
    def __init__(self):
        self.databases = {}  # {db_name: {table_name: Table instance}}

    def create_database(self, db_name):
        if db_name in self.databases:
            return False, f"Database '{db_name}' already exists."
        self.databases[db_name] = {}
        return True, f"Database '{db_name}' created successfully."

    def delete_database(self, db_name):
        if db_name not in self.databases:
            return False, f"Database '{db_name}' not found."
        del self.databases[db_name]
        return True, f"Database '{db_name}' deleted successfully."

    def list_databases(self):
        return list(self.databases.keys())

    def create_table(self, db_name, table_name, schema, order=8, search_key=None):
        if db_name not in self.databases:
            return False, f"Database '{db_name}' not found."
        if table_name in self.databases[db_name]:
            return False, f"Table '{table_name}' already exists in database '{db_name}'."
        
        # default search key to the first field if not provided
        if search_key is None and schema:
            if isinstance(schema, list):
                search_key = schema[0]
            elif isinstance(schema, dict):
                search_key = list(schema.keys())[0]

        self.databases[db_name][table_name] = Table(table_name, schema, order, search_key)
        return True, f"Table '{table_name}' created successfully in database '{db_name}'."

    def delete_table(self, db_name, table_name):
        if db_name not in self.databases:
            return False, f"Database '{db_name}' not found."
        if table_name not in self.databases[db_name]:
            return False, f"Table '{table_name}' not found in database '{db_name}'."
        del self.databases[db_name][table_name]
        return True, f"Table '{table_name}' deleted successfully from database '{db_name}'."

    def list_tables(self, db_name):
        if db_name not in self.databases:
            return None, f"Database '{db_name}' not found."
        return list(self.databases[db_name].keys()), "Success"

    def get_table(self, db_name, table_name):
        if db_name not in self.databases:
            return None, f"Database '{db_name}' not found."
        if table_name not in self.databases[db_name]:
            return None, f"Table '{table_name}' not found in database '{db_name}'."
        return self.databases[db_name][table_name], "Success"
