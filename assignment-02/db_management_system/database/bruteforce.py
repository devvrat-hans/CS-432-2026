class BruteForceDB:
    def __init__(self):
        self.data = []

    def insert(self, key, value=None):
        self.data.append((key, value))

    def search(self, key):
        for k, v in self.data:
            if k == key:
                return v
        return None

    def delete(self, key):
        for idx, (k, _) in enumerate(self.data):
            if k == key:
                self.data.pop(idx)
                return True
        return False

    def range_query(self, start, end):
        return [(k, v) for k, v in self.data if start <= k <= end]

    def get_all(self):
        return list(self.data)
