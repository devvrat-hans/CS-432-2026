import time
import random
import sys


class PerformanceAnalyzer:
    def __init__(self, bplustree_class, bruteforce_class):
        self.bpt_class = bplustree_class
        self.bf_class = bruteforce_class

    # ---------------- CREATE FRESH STRUCTURES ----------------
    def _fresh(self):
        return self.bpt_class(), self.bf_class()

    # ---------------- INSERT ----------------
    def measure_insert(self, data):
        bpt, bf = self._fresh()

        start = time.perf_counter()
        for k in data:
            bpt.insert(k, k)
        bpt_time = time.perf_counter() - start

        start = time.perf_counter()
        for k in data:
            bf.insert(k, k)
        bf_time = time.perf_counter() - start

        return bpt_time, bf_time

    # ---------------- SEARCH ----------------
    def measure_search(self, data):
        bpt, bf = self._fresh()

        for k in data:
            bpt.insert(k, k)
            bf.insert(k, k)

        keys = random.sample(data, min(100, len(data)))

        start = time.perf_counter()
        for k in keys:
            bpt.search(k)
        bpt_time = time.perf_counter() - start

        start = time.perf_counter()
        for k in keys:
            bf.search(k)
        bf_time = time.perf_counter() - start

        return bpt_time, bf_time

    # ---------------- DELETE ----------------
    def measure_delete(self, data):
        bpt, bf = self._fresh()

        for k in data:
            bpt.insert(k, k)
            bf.insert(k, k)

        keys = random.sample(data, min(100, len(data)))

        start = time.perf_counter()
        for k in keys:
            if bpt.search(k) is not None:
                bpt.delete(k)
        bpt_time = time.perf_counter() - start

        start = time.perf_counter()
        for k in keys:
            bf.delete(k)
        bf_time = time.perf_counter() - start

        return bpt_time, bf_time

    # ---------------- RANGE QUERY ----------------
    def measure_range(self, data):
        bpt, bf = self._fresh()

        for k in data:
            bpt.insert(k, k)
            bf.insert(k, k)

        start_key = random.choice(data)
        end_key = start_key + (max(data) - min(data)) // 10

        start = time.perf_counter()
        bpt.range_query(start_key, end_key)
        bpt_time = time.perf_counter() - start

        start = time.perf_counter()
        bf.range_query(start_key, end_key)
        bf_time = time.perf_counter() - start

        return bpt_time, bf_time

    # ---------------- RANDOM WORKLOAD ----------------
    def measure_random(self, data):
        bpt, bf = self._fresh()

        operations = ["insert", "search", "delete"]

        start = time.perf_counter()
        for k in data:
            op = random.choice(operations)

            if op == "insert":
                bpt.insert(k, k)
            elif op == "search":
                bpt.search(k)
            elif op == "delete":
                if bpt.search(k) is not None:
                    bpt.delete(k)

        bpt_time = time.perf_counter() - start

        start = time.perf_counter()
        for k in data:
            op = random.choice(operations)

            if op == "insert":
                bf.insert(k, k)
            elif op == "search":
                bf.search(k)
            elif op == "delete":
                bf.delete(k)

        bf_time = time.perf_counter() - start

        return bpt_time, bf_time

    # ---------------- MEMORY USAGE ----------------
    def measure_memory(self, data):
        bpt, bf = self._fresh()

        for k in data:
            bpt.insert(k, k)
            bf.insert(k, k)

        bpt_mem = self._bpt_size(bpt.root)
        bf_mem = sys.getsizeof(bf.data) + sum(sys.getsizeof(i) for i in bf.data)

        return bpt_mem, bf_mem

    # ---------------- B+ TREE MEMORY RECURSION ----------------
    def _bpt_size(self, node):
        size = sys.getsizeof(node)
        size += sys.getsizeof(node.keys)
        size += sys.getsizeof(node.values)
        size += sys.getsizeof(node.children)

        if not node.leaf:
            for child in node.children:
                size += self._bpt_size(child)

        return size