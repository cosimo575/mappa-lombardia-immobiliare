import sqlite3
import csv
import os
import urllib.request
import json
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "database.sqlite")
DATI_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dati")
INDIR_CSV = os.path.join(DATI_DIR, "INDIR_LOMB_20260206.csv")
COMUNI_JSON_URL = "https://raw.githubusercontent.com/matteocontrini/comuni-json/master/comuni.json"

def download_comuni_mapping():
    print("Downloading Italian municipalities mapping...")
    try:
        with urllib.request.urlopen(COMUNI_JSON_URL) as response:
            data = json.loads(response.read().decode())
            # Create a mapping from belfiore_code (CODICE_COMUNE) to name
            mapping = {item["codiceCatastale"].upper(): item["nome"].upper() for item in data}
            return mapping
    except Exception as e:
        print(f"Failed to download comuni mapping: {e}")
        return {}

def migrate_addresses():
    if not os.path.exists(INDIR_CSV):
        print(f"Error: Address CSV not found at {INDIR_CSV}")
        return

    comuni_map = download_comuni_mapping()
    if not comuni_map:
        print("Could not retrieve municipality mapping. Aborting.")
        return

    print("Connecting to database and setting up tables...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create the standard table to store coordinate data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comune TEXT,
            street TEXT,
            number TEXT,
            lat REAL,
            lon REAL
        )
    """)
    
    # We create an index for faster lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_addresses_comune_street ON addresses(comune, street)")

    print("Clearing existing address data to avoid duplicates...")
    cursor.execute("DELETE FROM addresses")
    
    print("Parsing CSV and inserting records (this may take a few minutes)...")
    start_time = time.time()
    
    insert_query = """
        INSERT INTO addresses (comune, street, number, lon, lat)
        VALUES (?, ?, ?, ?, ?)
    """
    
    batch_size = 50000
    batch = []
    total_processed = 0
    total_inserted = 0

    with open(INDIR_CSV, mode="r", encoding="utf-8-sig") as f:
        # The file uses semicolon delimiter
        reader = csv.DictReader(f, delimiter=';')
        
        for row in reader:
            total_processed += 1
            
            belfiore_code = row.get("CODICE_COMUNE", "").strip()
            street = row.get("ODONIMO", "").strip()
            number = row.get("CIVICO", "").strip()
            esponente = row.get("ESPONENTE", "").strip()
            
            # The CSV might use comma as decimal separator
            lon_str = row.get("COORD_X_COMUNE", "").replace(',', '.')
            lat_str = row.get("COORD_Y_COMUNE", "").replace(',', '.')
            
            # Skip rows without coordinates or street name
            if not lat_str or not lon_str or not street or not belfiore_code:
                continue
                
            comune_name = comuni_map.get(belfiore_code.upper())
            if not comune_name:
                continue # Skip if we can't map the municipality

            full_number = f"{number}{esponente}".strip()
            
            try:
                lon = float(lon_str)
                lat = float(lat_str)
                batch.append((comune_name, street, full_number, lon, lat))
            except ValueError:
                continue # Skip invalid coordinate formats
                
            if len(batch) >= batch_size:
                cursor.executemany(insert_query, batch)
                conn.commit()
                total_inserted += len(batch)
                batch = []
                print(f"[{time.time() - start_time:.1f}s] Processed {total_processed} rows, inserted {total_inserted} valid addresses...")

    # Insert remaining rows in the last batch
    if batch:
        cursor.executemany(insert_query, batch)
        conn.commit()
        total_inserted += len(batch)

    conn.close()
    
    end_time = time.time()
    print(f"Address data migration completed in {end_time - start_time:.2f} seconds.")
    print(f"Total rows processed: {total_processed}")
    print(f"Total valid addresses inserted: {total_inserted}")

if __name__ == "__main__":
    migrate_addresses()
