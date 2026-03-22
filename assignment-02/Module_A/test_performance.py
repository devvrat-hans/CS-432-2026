from database.bplustree import BPlusTree
from database.bruteforce import BruteForceDB
from database.performance import PerformanceAnalyzer
import random

analyzer = PerformanceAnalyzer(BPlusTree, BruteForceDB)

data = random.sample(range(1, 1000000), 20000)

print("\n--- PERFORMANCE TEST ---")

print("Insertion (B+ Tree vs BruteForce):", analyzer.measure_insert(data))
print("Search (B+ Tree vs BruteForce):", analyzer.measure_search(data))
print("Delete (B+ Tree vs BruteForce):", analyzer.measure_delete(data))
print("Range Query (B+ Tree vs BruteForce):", analyzer.measure_range(data))
print("Random Operations:", analyzer.measure_random(data))
print("Memory Usage (bytes):", analyzer.measure_memory(data))