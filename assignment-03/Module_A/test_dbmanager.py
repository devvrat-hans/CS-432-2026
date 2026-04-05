from database.db_manager import DBManager

db = DBManager()

print("\n--- CREATE TABLE ---")
db.create_table("students")
print("Tables:", db.list_tables())

print("\n--- INSERT ---")
db.insert("students", 1, "Alice")
db.insert("students", 2, "Bob")
print("Inserted records")

print("\n--- SEARCH ---")
print("Search 1:", db.search("students", 1))
print("Search 2:", db.search("students", 2))
print("Search 3 (not exists):", db.search("students", 3))

print("\n--- UPDATE ---")
db.update("students", 1, "Alicia")
print("Updated 1:", db.search("students", 1))

print("\n--- DELETE ---")
db.delete("students", 2)
print("After delete 2:", db.search("students", 2))

print("\n--- RANGE QUERY ---")
db.insert("students", 3, "Charlie")
db.insert("students", 4, "David")
print("Range 1-3:", db.range_query("students", 1, 3))

print("\n--- GET ALL ---")
print("All records:", db.get_all("students"))

print("\n--- DUPLICATE INSERT (EDGE CASE) ---")
try:
    db.insert("students", 1, "Duplicate")
except Exception as e:
    print("Duplicate handled:", e)

print("\n--- UPDATE NON-EXISTING ---")
try:
    db.update("students", 100, "Ghost")
except Exception as e:
    print("Update error handled:", e)

print("\n--- DELETE NON-EXISTING ---")
try:
    db.delete("students", 100)
except Exception as e:
    print("Delete error handled:", e)

print("\n--- INVALID RANGE ---")
try:
    db.range_query("students", 5, 1)
except Exception as e:
    print("Range error handled:", e)

print("\n--- TABLE SIZE ---")
print("Size:", db.table_size("students"))

print("\n--- VISUALIZATION ---")
tree = db._get_table("students").index.visualize_tree()
tree

print("\n--- DROP TABLE ---")
db.drop_table("students")
print("Tables after drop:", db.list_tables())

print("\n--- ACCESS DROPPED TABLE ---")
try:
    db.search("students", 1)
except Exception as e:
    print("Access error handled:", e)