import sqlite3
conn = sqlite3.connect('backend/database.sqlite')
cursor = conn.cursor()
q = "Roma 10 Milano"
safe_q = "".join(c for c in q if c.isalnum() or c.isspace())
fts_query = " ".join(f"{term}*" for term in safe_q.split())
print("FTS Query:", fts_query)
try:
    cursor.execute("SELECT comune, street, number, lat, lon FROM addresses_fts WHERE addresses_fts MATCH ? LIMIT 3", (fts_query,))
    for row in cursor.fetchall():
        print(row)
except Exception as e:
    print(e)
