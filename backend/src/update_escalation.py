import json
import os
import sqlite3
import sys

db_path = sys.argv[1]
ref_id = sys.argv[2]
status = sys.argv[3]

if not os.path.exists(db_path):
    print(json.dumps({"success": False}))
    sys.exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
try:
    cursor.execute(
        "UPDATE escalations SET status = ? WHERE UPPER(ref_id) = ?",
        (status.lower(), ref_id.upper()),
    )
    conn.commit()
    print(json.dumps({"success": cursor.rowcount > 0}))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
finally:
    conn.close()
