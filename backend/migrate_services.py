import sqlite3
import csv
import os
from collections import defaultdict

DB_PATH = os.path.join(os.path.dirname(__file__), "database.sqlite")
DATI_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dati")

def migrate_services():
    print("Migrating services data (schools, pharmacies, structures)...")

    comuni_stats = defaultdict(lambda: {"schools": 0, "pharmacies": 0, "structures": 0})

    # 1. Process Schools
    schools_csv = os.path.join(DATI_DIR, "Anagrafe_Scuole_20260215.csv")
    if os.path.exists(schools_csv):
        with open(schools_csv, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                comune = row.get("Comune")
                if comune:
                    comuni_stats[comune.strip().upper()]["schools"] += 1
    else:
        print(f"Warning: {schools_csv} not found.")

    # 2. Process Pharmacies
    pharmacies_csv = os.path.join(DATI_DIR, "Elenco_Completo_Farmacie_20260215.csv")
    if os.path.exists(pharmacies_csv):
        with open(pharmacies_csv, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                comune = row.get("COMUNE")
                if comune:
                    comuni_stats[comune.strip().upper()]["pharmacies"] += 1
    else:
        print(f"Warning: {pharmacies_csv} not found.")

    # 3. Process Structures
    structures_csv = os.path.join(DATI_DIR, "Georeferenziazione_strutture_20260215.csv")
    if os.path.exists(structures_csv):
        with open(structures_csv, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                comune = row.get("LOCALITA")
                if comune:
                    comuni_stats[comune.strip().upper()]["structures"] += 1
    else:
        print(f"Warning: {structures_csv} not found.")

    # 4. Insert into DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services_stats (
            comune TEXT PRIMARY KEY,
            schools INTEGER DEFAULT 0,
            pharmacies INTEGER DEFAULT 0,
            structures INTEGER DEFAULT 0
        )
    """)
    
    # Clear existing to be safe
    cursor.execute("DELETE FROM services_stats")

    # Insert new aggregated data
    insert_query = """
        INSERT INTO services_stats (comune, schools, pharmacies, structures)
        VALUES (?, ?, ?, ?)
    """
    
    data_to_insert = [
        (comune, stats["schools"], stats["pharmacies"], stats["structures"])
        for comune, stats in comuni_stats.items()
    ]
    
    cursor.executemany(insert_query, data_to_insert)
    conn.commit()
    conn.close()

    print(f"Services data migration completed. Inserted stats for {len(data_to_insert)} municipalities.")

if __name__ == "__main__":
    migrate_services()
