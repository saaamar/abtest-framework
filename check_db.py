import sqlite3
import os

DB_PATH = os.path.join("webapp", "ab_demo.db")

print(f"Checking database at: {DB_PATH}")
print(f"File exists: {os.path.exists(DB_PATH)}")

if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]
    print(f"Tables: {tables}")
    conn.close()
    
    if not tables or 'experiments' not in tables:
        print("\nTables missing! Deleting corrupted database...")
        os.remove(DB_PATH)
        print("Database deleted. It will be recreated on next app start.")
else:
    print("Database file doesn't exist. It will be created on next app start.")
