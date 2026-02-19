from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sqlite3
import uvicorn
import os

app = FastAPI()

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "backend/database.sqlite"

def get_db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/points")
def get_points(
    layer: str,
    minLat: float,
    minLon: float,
    maxLat: float,
    maxLon: float,
    city: str = None,
    limit: int = 2000
):
    conn = get_db_conn()
    cursor = conn.cursor()
    
    params = [layer, minLat, maxLat, minLon, maxLon]
    city_filter = ""
    if city:
        city_filter = " AND LOWER(city) = ?"
        params.append(city.lower())
    
    params.append(limit)
    
    query = f"""
        SELECT name, address, city, type, manager, lat, lon 
        FROM points 
        WHERE layer = ? 
        AND lat BETWEEN ? AND ? 
        AND lon BETWEEN ? AND ?
        {city_filter}
        LIMIT ?
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["lon"], row["lat"]]
            },
            "properties": {
                "Name": row["name"],
                "Address": row["address"],
                "City": row["city"],
                "Type": row["type"],
                "Manager": row["manager"]
            }
        })
    
    conn.close()
    return {
        "type": "FeatureCollection",
        "features": features
    }

@app.get("/api/stats")
def get_stats(city: str, type: str = None):
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        
        prezzo_vendita = None
        prezzo_affitto = None

        # Check if it's a neighborhood request (or try both)
        # First try to find in milano_neighborhood_stats if type hints it or just by name
        if type in ['quarter', 'neighbourhood', 'suburb', 'hamlet']:
             # Use LIKE to match "Isola" inside "Cenisio, Sarpi, Isola"
             cursor.execute("SELECT prezzo_vendita, prezzo_affitto FROM milano_neighborhood_stats WHERE name LIKE ?", (f"%{city}%",))
             row = cursor.fetchone()
             if row:
                 prezzo_vendita = row[0]
                 prezzo_affitto = row[1]
        
        # If not found or not a neighborhood, try municipality stats
        if prezzo_vendita is None:
            cursor.execute("SELECT prezzo_vendita, prezzo_affitto FROM real_estate_stats WHERE comune = ?", (city,))
            row = cursor.fetchone()
            if row:
                 prezzo_vendita = row[0]
                 prezzo_affitto = row[1]
            
        conn.close()

        # Mock service stats (as per original code)
        import random
        stats = {
            "schools": random.randint(1, 10),
            "pharmacies": random.randint(1, 5),
            "structures": random.randint(0, 3),
            "water": f"{random.randint(90, 100)}%",
            "real_estate": {
                "sale": prezzo_vendita,
                "rent": prezzo_affitto
            }
        }
        
        return stats
    except Exception as e:
        print(f"Error in /api/stats: {e}")
        # Return default structure on error to prevent frontend crash
        return {
            "schools": 0,
            "pharmacies": 0,
            "structures": 0,
            "water": "N/D",
            "real_estate": { "sale": None, "rent": None }
        }

# Temporary endpoint for scraping
@app.post("/api/ingest_data")
def ingest_data(data: dict):
    import json
    import os
    
    file_path = "backend/dati_completi_raw.json"
    
    # Load existing
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                existing = json.load(f)
            except:
                existing = {}
    else:
        existing = {}
    
    # Merge (province by province)
    for province, cities in data.items():
        existing[province] = cities
        
    with open(file_path, 'w') as f:
        json.dump(existing, f, indent=2)
        
    return {"status": "success", "received": len(cities)}

# ... (inside get_comuni etc)
@app.get("/api/comuni")
def get_comuni(
    minLat: float = Query(..., alias="minLat"),
    maxLat: float = Query(..., alias="maxLat"),
    minLon: float = Query(..., alias="minLon"),
    maxLon: float = Query(..., alias="maxLon")
):
    return fetch_features("comuni", minLat, maxLat, minLon, maxLon)

@app.get("/api/sezioni")
def get_sezioni(
    minLat: float = Query(..., alias="minLat"),
    maxLat: float = Query(..., alias="maxLat"),
    minLon: float = Query(..., alias="minLon"),
    maxLon: float = Query(..., alias="maxLon")
):
    return fetch_features("sezioni", minLat, maxLat, minLon, maxLon)

@app.get("/api/luoghi")
def get_luoghi(
    minLat: float = Query(..., alias="minLat"),
    maxLat: float = Query(..., alias="maxLat"),
    minLon: float = Query(..., alias="minLon"),
    maxLon: float = Query(..., alias="maxLon")
):
    return fetch_features("luoghi", minLat, maxLat, minLon, maxLon)

@app.get("/api/adu")
def get_adu(
    minLat: float = Query(..., alias="minLat"),
    maxLat: float = Query(..., alias="maxLat"),
    minLon: float = Query(..., alias="minLon"),
    maxLon: float = Query(..., alias="maxLon")
):
    return fetch_features("adu", minLat, maxLat, minLon, maxLon)

@app.get("/api/fermate")
def get_fermate(
    minLat: float = Query(..., alias="minLat"),
    maxLat: float = Query(..., alias="maxLat"),
    minLon: float = Query(..., alias="minLon"),
    maxLon: float = Query(..., alias="maxLon")
):
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # Query database using spatial index on bounding box
    query = """
        SELECT properties, geometry
        FROM fermate
        WHERE min_lat <= ? AND max_lat >= ? 
        AND min_lon <= ? AND max_lon >= ?
        LIMIT 2000
    """
    cursor.execute(query, (maxLat, minLat, maxLon, minLon))
    rows = cursor.fetchall()
    
    features = []
    for row in rows:
        try:
            features.append({
                "type": "Feature",
                "properties": json.loads(row["properties"]),
                "geometry": json.loads(row["geometry"])
            })
        except Exception as e:
            print(f"Error parsing feature: {e}")
            continue
            
    conn.close()
    return {
        "type": "FeatureCollection",
        "features": features
    }

@app.get("/api/search")
def search_locations(q: str = Query(..., min_length=2)):
    conn = get_db_conn()
    cursor = conn.cursor()
    
    results = []
    
    # Search Comuni
    try:
        cursor.execute("""
            SELECT name, properties, geometry 
            FROM comuni 
            WHERE name LIKE ? 
            LIMIT 20
        """, (f"%{q}%",))
        
        for row in cursor.fetchall():
            results.append({
                "name": row["name"],
                "type": "Comune",
                "feature": {
                    "type": "Feature",
                    "properties": json.loads(row["properties"]),
                    "geometry": json.loads(row["geometry"])
                }
            })
            
        # Search Luoghi
        cursor.execute("""
            SELECT name, properties, geometry 
            FROM luoghi 
            WHERE name LIKE ? 
            LIMIT 20
        """, (f"%{q}%",))
        
        for row in cursor.fetchall():
            results.append({
                "name": row["name"],
                "type": "Zona",
                "feature": {
                    "type": "Feature",
                    "properties": json.loads(row["properties"]),
                    "geometry": json.loads(row["geometry"])
                }
            })
            
    except Exception as e:
        print(f"Search error: {e}")
        
    conn.close()
    return results

# Mount static files
# Robust path resolution: Get the directory of this file (backend/), then go up one level
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_path = os.path.join(base_dir, "frontend")

if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    print(f"WARNING: Frontend path not found at {frontend_path}. Current dir: {os.getcwd()}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
