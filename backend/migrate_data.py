import sqlite3
import json
import ijson
import math
import os
import re
from migrate_water import migrate_water
from migrate_services import migrate_services

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.sqlite')
DATA_DIR = "dati/json_sources"

def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables(conn):
    cursor = conn.cursor()
    
    # Comuni
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comuni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            properties TEXT,
            geometry TEXT,
            min_lat REAL,
            max_lat REAL,
            min_lon REAL,
            max_lon REAL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comuni_bbox ON comuni (min_lat, max_lat, min_lon, max_lon)")
    
    # Sezioni (Censimento)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sezioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sez_id TEXT,
            properties TEXT,
            geometry TEXT,
            min_lat REAL,
            max_lat REAL,
            min_lon REAL,
            max_lon REAL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sezioni_bbox ON sezioni (min_lat, max_lat, min_lon, max_lon)")

    # Luoghi (qualsiasi tipo di area non comune/sezione)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS luoghi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            properties TEXT,
            geometry TEXT,
            min_lat REAL,
            max_lat REAL,
            min_lon REAL,
            max_lon REAL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_luoghi_bbox ON luoghi (min_lat, max_lat, min_lon, max_lon)")

    # ADU (Aree di Urbanistiche? - Check actual content)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS adu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            adu_id TEXT,
            properties TEXT,
            geometry TEXT,
            min_lat REAL,
            max_lat REAL,
            min_lon REAL,
            max_lon REAL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_adu_bbox ON adu (min_lat, max_lat, min_lon, max_lon)")
    
    conn.commit()
    print("Tables created.")

def calculate_bbox(geometry):
    # Simply iterate all coordinates to find min/max
    min_lon, min_lat = float('inf'), float('inf')
    max_lon, max_lat = float('-inf'), float('-inf')
    
    def extract_coords(coords):
        nonlocal min_lon, min_lat, max_lon, max_lat
        if isinstance(coords[0], (int, float)):
            lon, lat = coords
            if lon < min_lon: min_lon = lon
            if lon > max_lon: max_lon = lon
            if lat < min_lat: min_lat = lat
            if lat > max_lat: max_lat = lat
        else:
            for c in coords:
                extract_coords(c)

    extract_coords(geometry['coordinates'])
    return min_lat, max_lat, min_lon, max_lon

def load_js_file(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return None
        
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Remove "const variableName = " and trailing ";"
        # Heuristic: find first '{' and last '}'
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            json_str = content[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"JSON Parse Error in {filename}: {e}")
                return None
    return None

def migrate_file(conn, filename, table_name, name_field='name', id_field=None):
    print(f"Migrating {filename} into {table_name}...")
    data = load_js_file(filename)
    if not data:
        return

    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table_name}") # Clear existing for clean reload
    
    features = data.get('features', [])
    print(f"Found {len(features)} features in {filename}")
    
    valid_count = 0
    for feature in features:
        props = feature.get('properties', {})
        geom = feature.get('geometry')
        
        if not geom:
            continue
            
        try:
            min_lat, max_lat, min_lon, max_lon = calculate_bbox(geom)
            
            name = props.get(name_field)
            rec_id = props.get(id_field) if id_field else None
            
            # Prepare row
            if table_name == 'comuni':
                cursor.execute("""
                    INSERT INTO comuni (name, properties, geometry, min_lat, max_lat, min_lon, max_lon)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (name, json.dumps(props), json.dumps(geom), min_lat, max_lat, min_lon, max_lon))
            elif table_name == 'sezioni':
                cursor.execute("""
                    INSERT INTO sezioni (sez_id, properties, geometry, min_lat, max_lat, min_lon, max_lon)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (rec_id, json.dumps(props), json.dumps(geom), min_lat, max_lat, min_lon, max_lon))
            elif table_name == 'luoghi':
                cursor.execute("""
                    INSERT INTO luoghi (name, properties, geometry, min_lat, max_lat, min_lon, max_lon)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (name, json.dumps(props), json.dumps(geom), min_lat, max_lat, min_lon, max_lon))
            elif table_name == 'adu':
                cursor.execute("""
                    INSERT INTO adu (adu_id, properties, geometry, min_lat, max_lat, min_lon, max_lon)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (rec_id, json.dumps(props), json.dumps(geom), min_lat, max_lat, min_lon, max_lon))
                
            valid_count += 1
        except Exception as e:
            print(f"Error inserting feature: {e}")
            
    conn.commit()
    print(f"Inserted {valid_count} rows into {table_name}")

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = get_db_conn()
    try:
        create_tables(conn)
        
        # Migrate Comuni
        migrate_file(conn, "data-comuni.js", "comuni", name_field="name")
        
        # Migrate Sezioni (ID might be 'SEZ2011' or similar, assume check properties later if needed)
        # Using a generic approach, defaulting to None for specific ID if not strictly known, 
        # or we check a likely field. Usually sezioni have 'SEZ' or similar.
        # Let's inspect properties dynamically or just dump props.
        # Actually for 'sezioni' table I defined 'sez_id'.
        migrate_file(conn, "data-sezioni.js", "sezioni", id_field="SEZ2011") 
        
        # Migrate Luoghi
        migrate_file(conn, "data-luoghi.js", "luoghi", name_field="name")
        
        # Migrate ADU
        migrate_file(conn, "data-adu.js", "adu", id_field="ID_NIL") # Typical for Milan NILs

        # Migrate Water stats
        print("Migrating water quality stats...")
        migrate_water()

        # Migrate Services stats
        print("Migrating services stats...")
        migrate_services()

    finally:
        conn.close()

if __name__ == "__main__":
    main()
