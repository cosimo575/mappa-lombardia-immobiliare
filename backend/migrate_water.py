import sqlite3
import csv
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.sqlite')
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dati', 'Qualità_delle_acque_destinate_al_consumo_umano_-_dettaglio_parametri_20260215.csv')

def migrate_water():
    print(f"Connecting to database at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Creating table water_quality_stats if not exists...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS water_quality_stats (
            comune TEXT PRIMARY KEY,
            total_tests INTEGER,
            conforme_tests INTEGER,
            compliance_percentage REAL
        )
    """)
    
    print("Clearing old data...")
    cursor.execute("DELETE FROM water_quality_stats")
    
    print(f"Reading CSV from {CSV_PATH}")
    
    stats = {} # dict of comune -> {"total": int, "conforme": int}
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            comune = row.get('Comune Punto Prelievo')
            esito = row.get('Esito')
            
            if not comune:
                continue
                
            comune = comune.strip().upper()
            
            if comune not in stats:
                stats[comune] = {"total": 0, "conforme": 0}
                
            stats[comune]["total"] += 1
            if esito and esito.strip().lower() == 'conforme':
                stats[comune]["conforme"] += 1
                
    print(f"Found data for {len(stats)} municipalities.")
    print("Inserting into database...")
    
    for comune, data in stats.items():
        total = data["total"]
        conforme = data["conforme"]
        percentage = (conforme / total * 100) if total > 0 else 0.0
        
        cursor.execute("""
            INSERT INTO water_quality_stats (comune, total_tests, conforme_tests, compliance_percentage)
            VALUES (?, ?, ?, ?)
        """, (comune, total, conforme, percentage))
        
    conn.commit()
    conn.close()
    print("Water quality data migration complete.")

if __name__ == '__main__':
    migrate_water()
