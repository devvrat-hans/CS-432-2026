from database.bplustree import BPlusTree

bpt = BPlusTree()

print("\n--- INSERT ---")
bpt.insert(10, "A")
bpt.insert(20, "B")
bpt.insert(5, "C")
bpt.insert(15, "D")

print("All after insert:", bpt.get_all())

print("\n--- SEARCH ---")
print("Search 10:", bpt.search(10))
print("Search 99 (not exists):", bpt.search(99))

print("\n--- UPDATE ---")
bpt.update(10, "Z")
print("Updated 10:", bpt.search(10))

print("\n--- DELETE ---")
bpt.delete(10)
print("After delete 10:", bpt.search(10))

print("\n--- RANGE QUERY ---")
print("Range 1-30:", bpt.range_query(1, 30))

print("\n--- GET ALL ---")
print("All records:", bpt.get_all())

print("\n--- VISUALIZATION ---")
dot = bpt.visualize_tree()
dot