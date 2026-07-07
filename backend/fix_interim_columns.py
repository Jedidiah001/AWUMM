"""
Quick fix to add interim champion columns to database
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'awum.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute('ALTER TABLE championships ADD COLUMN interim_holder_id TEXT')
    print("✅ Added interim_holder_id column")
except Exception as e:
    print(f"interim_holder_id: {e}")

try:
    cursor.execute('ALTER TABLE championships ADD COLUMN interim_holder_name TEXT')
    print("✅ Added interim_holder_name column")
except Exception as e:
    print(f"interim_holder_name: {e}")

conn.commit()
conn.close()

print("\n✅ Database schema updated!")