import json
import os
import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else "data/memory.db"
if not os.path.exists(db_path):
    print(json.dumps([]))
    sys.exit(0)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
try:
    cursor.execute("SELECT * FROM escalations ORDER BY created_at DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    print(json.dumps(rows))
except Exception:
    print(json.dumps([]))
finally:
    conn.close()
