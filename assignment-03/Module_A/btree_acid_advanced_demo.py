import os
import copy
from database.db_manager import DBManager

print("\n=== ADVANCED B+ TREE ACID DEMO ===")

# reset WAL
temp_db = DBManager()
if os.path.exists(temp_db.wal_path):
    os.remove(temp_db.wal_path)

db = DBManager()
db.tables = {}

# create tables
for t in ["users", "products", "orders"]:
    tx = db.begin()
    if t not in db.get_all_tables():
        db.create_table(tx, t)

# initial data
tx = db.begin()
db.insert(tx, "users", 1, {"name": "Alice", "balance": 1000})

tx = db.begin()
db.insert(tx, "products", 10, {"name": "Phone", "stock": 5})

print("\nInitial State:")
print("Users:", db.get_all("users"))
print("Products:", db.get_all("products"))

# failure simulation
print("\n[Failure Simulation]")
try:
    db.configure_failure_injection("after_data_write", 1)

    tx = db.begin()
    user = copy.deepcopy(db.search("users", 1))
    user["balance"] -= 500
    db.update(tx, "users", 1, user)

except:
    print(" Failure handled internally")

print("\nState after failure:")
print("Users:", db.get_all("users"))

# success
tx = db.begin()
user = copy.deepcopy(db.search("users", 1))
user["balance"] -= 500
db.update(tx, "users", 1, user)

print("\nFinal State:")
print("Users:", db.get_all("users"))

print("\n=== DEMO COMPLETE ===")