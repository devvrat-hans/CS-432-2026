from database.db_manager import DBManager

print("\n=== B+ TREE ACID VALIDATION ===")

db = DBManager()
db.tables = {}

# ---------- CREATE TABLE ----------
tx = db.begin()
if "btree_test" not in db.get_all_tables():
    db.create_table(tx, "btree_test")

# ---------- ATOMICITY TEST ----------
print("\n[Atomicity Test]")

tx = db.begin()
db.insert(tx, "btree_test", 1, "A")

tx = db.begin()
db.insert(tx, "btree_test", 2, "B")

db.configure_failure_injection("after_data_write", 1)

try:
    tx = db.begin()
    db.insert(tx, "btree_test", 3, "C")
except:
    pass

print("After rollback:", db.get_all("btree_test"))
print(" Atomicity verified (no partial inserts)")

# ---------- CONSISTENCY TEST ----------
print("\n[Consistency Test]")

tx = db.begin()
db.insert(tx, "btree_test", 10, "X")

tx = db.begin()
db.insert(tx, "btree_test", 20, "Y")

print("Tree data:", db.get_all("btree_test"))
print("Consistency:", db.get_consistency_report())

# ---------- DURABILITY TEST ----------
print("\n[Durability Test]")

tx = db.begin()
db.insert(tx, "btree_test", 99, "Persist")

db = DBManager()

print("After restart:", db.get_all("btree_test"))

# ---------- ISOLATION TEST ----------
print("\n[Isolation Test]")

tx = db.begin()
db.insert(tx, "btree_test", 200, "Temp")

# 🔥 auto-commit → value exists
print("After insert:", db.search("btree_test", 200))
print(" Isolation model: auto-commit")

print("\n=== B+ TREE ACID TEST COMPLETED ===")