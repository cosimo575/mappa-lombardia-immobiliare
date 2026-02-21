# Lombardy Real Estate Map (Mappa Lombardia Immobiliare)

An interactive web application displaying municipalities, neighborhoods, services, and real estate data across Lombardy.

## Prerequisites
- Python 3.9+
- SQLite

## Setup & Running the Backend

The project uses a local SQLite database (`backend/database.sqlite`) which is **not tracked in Git** due to its large size (>150MB) after full data integration.

To recreate the database and populate it with data locally:

1. **Install Dependencies**:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. **Download Required Data**:
Ensure the following CSV files are present in the `dati/` folder:
- `Anagrafe_Scuole_20260215.csv` (Schools)
- `Elenco_Completo_Farmacie_20260215.csv` (Pharmacies)
- `Georeferenziazione_strutture_20260215.csv` (Healthcare)
- `Qualità_delle_acque_destinate_al_consumo_umano_-_dettaglio_parametri_20260215.csv` (Water Quality)
- `INDIR_LOMB_20260206.csv` (Address Directory)

3. **Run Data Migrations**:
```bash
# This script creates tables and ingests basic data, water quality, and services
python backend/migrate_data.py

# This script parses the address directory and creates the FTS5 tables for geocoding
python backend/migrate_addresses.py
```

4. **Start the Server**:
```bash
python backend/main.py
```
The application will be served at `http://localhost:8000`.

## Features
- **Interactive Map**: View boundaries for Comuni and Frazioni of Lombardy.
- **Dynamic Search**: Instantly search for municipalities, specific regions, or exact street addresses (e.g., *Via Roma 10, Milano*) utilizing an FTS5 virtual SQLite table.
- **Services Data**: View real aggregated counts of Schools, Pharmacies, and Healthcare Structures per municipality.
- **Water Quality**: View exact water compliance percentages based on laboratory samples.
