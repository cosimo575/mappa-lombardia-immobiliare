import sqlite3
import os

# Connect to the database
DB_PATH = 'backend/database.sqlite'

if not os.path.exists(DB_PATH):
    print(f"Error: Database not found at {DB_PATH}")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def test_neighborhood(name):
    print(f"\n--- Testing: {name} ---")
    
    # 1. Exact Match
    cursor.execute("SELECT name, prezzo_vendita, prezzo_affitto FROM milano_neighborhood_stats WHERE name = ?", (name,))
    exact = cursor.fetchone()
    if exact:
        print(f"  [EXACT MATCH] Found: {exact[0]} | Sale: {exact[1]} | Rent: {exact[2]}")
    else:
        print("  [EXACT MATCH] Not found")

    # 2. Fuzzy Match (logic used in backend)
    cursor.execute("SELECT name, prezzo_vendita, prezzo_affitto FROM milano_neighborhood_stats WHERE name LIKE ?", (f"%{name}%",))
    fuzzy = cursor.fetchall()
    
    if fuzzy:
        print(f"  [FUZZY MATCH] Found {len(fuzzy)} matches:")
        for row in fuzzy:
            print(f"    - {row[0]} | Sale: {row[1]} | Rent: {row[2]}")
    else:
        print("  [FUZZY MATCH] Not found")

# Test cases including the user's specific requests
test_cases = [
    "Ticinese",       # User request
    "Inganni",        # User request
    "Isola",          # Check logic for grouped names
    "Sempione",
    "Moscova",
    "Navigli",
    "Brera",
    "Lambrate"
]

for case in test_cases:
    test_neighborhood(case)

conn.close()
