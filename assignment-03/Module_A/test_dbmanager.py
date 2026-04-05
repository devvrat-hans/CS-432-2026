from database.db_manager import DBManager

db = DBManager()
db.tables = {}

print("\n=== DB MANAGER DEMO ===")

# create table
tx = db.begin()
if "students" not in db.get_all_tables():
    db.create_table(tx, "students")

# insert
tx = db.begin()
db.insert(tx, "students", 1, "Alice")

tx = db.begin()
db.insert(tx, "students", 2, "Bob")

print("After insert:", db.get_all("students"))

# update
tx = db.begin()
db.update(tx, "students", 1, "Alicia")

print("After update:", db.get_all("students"))

# delete
tx = db.begin()
db.delete(tx, "students", 2)

print("After delete:", db.get_all("students"))

print("Range query:", db.range_query("students", 1, 3))

print(" DEMO COMPLETED")