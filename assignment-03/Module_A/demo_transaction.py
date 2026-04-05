from database.db_manager import DBManager
import copy

print("\n=== MULTI-TABLE TRANSACTION DEMO (AUTO-COMMIT MODEL) ===")

db = DBManager()
db.tables = {}

# ---------- CREATE TABLES ----------
for t in ["users", "products", "orders"]:
    tx = db.begin()
    if t not in db.get_all_tables():
        db.create_table(tx, t)

print("\nTables created:", db.get_all_tables())

# ---------- INITIAL DATA ----------
tx = db.begin()
db.insert(tx, "users", 1, {"name": "Alice", "balance": 1000})

tx = db.begin()
db.insert(tx, "products", 10, {"name": "Phone", "stock": 5})

print("\nInitial state:")
print("Users:", db.get_all("users"))
print("Products:", db.get_all("products"))
print("Orders:", db.get_all("orders"))

# ---------- SIMULATED TRANSACTION ----------
print("\n[Simulated Multi-step Operation]")

try:
    tx = db.begin()
    user = copy.deepcopy(db.search("users", 1))
    user["balance"] -= 500
    db.update(tx, "users", 1, user)

    tx = db.begin()
    product = copy.deepcopy(db.search("products", 10))
    product["stock"] -= 1
    db.update(tx, "products", 10, product)

    tx = db.begin()
    db.insert(tx, "orders", 100, {
        "user_id": 1,
        "product_id": 10,
        "amount": 500
    })

    print("\n Operations completed (auto-committed individually)")

except Exception as e:
    print("\n Operation failed:", e)

# ---------- FINAL STATE ----------
print("\nFinal state:")
print("Users:", db.get_all("users"))
print("Products:", db.get_all("products"))
print("Orders:", db.get_all("orders"))

# ---------- CONSISTENCY ----------
print("\nConsistency Report:")
for r in db.get_consistency_report():
    print(r)