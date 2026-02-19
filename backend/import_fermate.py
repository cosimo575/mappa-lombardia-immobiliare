
import sqlite3
import json
import os

DB_PATH = "backend/database.sqlite"
GEOJSON_PATH = "sample_fermate_milano.geojson"

def get_db_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Create fermate table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fermate (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stop_id INTEGER,
        ubicazione TEXT,
        linee TEXT,
        min_lat REAL,
        max_lat REAL,
        min_lon REAL,
        max_lon REAL,
        properties TEXT,
        geometry TEXT
    )
    """)
    
    # Create spatial index (simple B-Tree on coords for now, or R-Tree if sqlite3 enabled)
    # For this simple app, indexes on min/max lat/lon are sufficient
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fermate_lat ON fermate(min_lat, max_lat)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fermate_lon ON fermate(min_lon, max_lon)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fermate_linee ON fermate(linee)")
    
    conn.commit()
    conn.close()
    print("Database initialized.")

def import_data():
    if not os.path.exists(GEOJSON_PATH):
        print(f"File {GEOJSON_PATH} not found!")
        return

    with open(GEOJSON_PATH, 'r') as f:
        data = json.load(f)

    conn = get_db_conn()
    cursor = conn.cursor()

    count = 0
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        
        if not geom or geom.get("type") != "Point":
            continue

        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            continue
            
        lon, lat = coords[0], coords[1]
        
        # Point bounding box is just the point itself
        min_lat, max_lat = lat, lat
        min_lon, max_lon = lon, lon

        stop_id = props.get("ID")
        ubicazione = props.get("UBICAZIONE")
        linee = props.get("LINEE")
        
        cursor.execute("""
            INSERT INTO fermate (stop_id, ubicazione, linee, min_lat, max_lat, min_lon, max_lon, properties, geometry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            stop_id, 
            ubicazione, 
            linee, 
            min_lat, max_lat, min_lon, max_lon,
            json.dumps(props),
            json.dumps(geom)
        ))
        count += 1

    conn.commit()
    conn.close()
    print(f"Imported {count} fermate into database.")

if __name__ == "__main__":
    init_db()
    import_data()
