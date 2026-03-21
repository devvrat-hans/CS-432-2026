from database.bplustree import BPlusTree

class Table:
    def __init__(self, name, schema, order=8, search_key=None):
        self.name = name
        self.schema = schema
        self.order = order
        self.data = BPlusTree(order=order)
        self.search_key = search_key

    def validate_record(self, record):
        if not isinstance(record, dict):
            return False, "Record must be a dictionary matching the schema."
        # skip strict typing for simple implementation
        return True, ""

    def insert(self, record):
        valid, msg = self.validate_record(record)
        if not valid:
            return False, msg
        
        key = record.get(self.search_key)
        if key is None:
            return False, f"Record must contain search key '{self.search_key}'"
            
        # Since B+ tree returns None or existing, let's just insert
        self.data.insert(key, record)
        return True, f"Record with key {key} inserted."

    def get(self, record_id):
        res = self.data.search(record_id)
        if res is not None:
            return res, "Success"
        return None, "Record not found."

    def get_all(self):
        records = self.data.get_all()
        return [val for k, val in records], "Success"

    def update(self, record_id, new_record):
        existing, _ = self.get(record_id)
        if existing is None:
            return False, "Record not found."
        # overwrite
        self.data.update(record_id, new_record)
        return True, "Record updated."

    def delete(self, record_id):
        res, _ = self.get(record_id)
        if res is None:
            return False, "Record not found."
        self.data.delete(record_id)
        return True, "Record deleted."

    def range_query(self, start_value, end_value):
        res = self.data.range_query(start_value, end_value)
        return [val for k, val in res], "Success"
