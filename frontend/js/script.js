// --- INIZIALIZZAZIONE MAPPA ---
const map = L.map('map', { preferCanvas: true }).setView([45.65, 9.9], 8);

// Tile Layer standard (Sfondo)
const cartoLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20
}).addTo(map);

// Stile Unico per Comuni e Frazioni
const commonStyle = {
    color: "#015d15ff",
    weight: 1,
    opacity: 0.8,
    fillColor: "#0e0e0eff",
    fillOpacity: 0.0
};

const styleComuni = commonStyle;
const styleLuoghi = commonStyle;

// --- CONFIGURAZIONE API ---
const API_URL = "/api";

// STATO APPLICAZIONE
let currentSelectedCity = null;

// --- GESTIONE POLIGONI (COMUNI/FRAZIONI) ---

function onEachFeature(feature, layer) {
    if (feature.properties && feature.properties.name) {
        let type = feature.properties.type || "Zona";
        layer.bindPopup(`<b>${feature.properties.name}</b><br>(${type})`);
        layer.bindTooltip(feature.properties.name, { sticky: true, direction: 'center', className: 'my-tooltip' });

        layer.on('click', function (e) {
            L.DomEvent.stopPropagation(e);
            selectLocation({
                name: feature.properties.name,
                type: feature.properties.type || (feature.properties.type === 'comune' ? 'Comune' : 'Zona'),
                feature: feature
            });
        });
    }
}

const layers = {};
const pointLayers = {};

// Carica confini statici
// Carica confini statici
if (typeof comuniData !== 'undefined') {
    // Assegna esplicitamente il tipo "Comune" a tutti gli elementi di comuniData
    // Questo serve perché onEachFeature usa feature.properties.type per capire se aggiornare il filtro città
    if (comuniData.features) {
        comuniData.features.forEach(f => {
            if (f.properties) {
                f.properties.type = "Comune";
            }
        });
    }

    const comuniLayer = L.geoJSON(comuniData, {
        style: styleComuni,
        onEachFeature: onEachFeature
    }).addTo(map);
    layers["Comuni (Livello 8)"] = comuniLayer;
    map.fitBounds(comuniLayer.getBounds());
}

if (typeof luoghiData !== 'undefined') {
    const luoghiLayer = L.geoJSON(luoghiData, {
        style: styleLuoghi,
        onEachFeature: onEachFeature
    }).addTo(map);
    layers["Frazioni / Quartieri"] = luoghiLayer;
}

// --- GESTIONE PUNTI DINAMICI (API) ---

const datasetsConfig = {
    'schools': { id: 'toggle-schools', color: '#3388ff', name: 'Scuola', emoji: '🏫' },
    'pharmacies': { id: 'toggle-pharmacies', color: '#28a745', name: 'Farmacia', emoji: '💊' },
    'structures': { id: 'toggle-structures', color: '#dc3545', name: 'Struttura Sanitaria', emoji: '🏥' },
    'water': { id: 'toggle-water', color: '#17a2b8', name: 'Qualità Acqua', emoji: '💧' }
};

// Inizializza i layer per i punti
Object.keys(datasetsConfig).forEach(key => {
    pointLayers[key] = L.geoJSON(null, {
        pointToLayer: (feature, latlng) => {
            const icon = L.divIcon({
                html: datasetsConfig[key].emoji,
                className: 'emoji-icon',
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            });
            return L.marker(latlng, { icon: icon });
        },
        onEachFeature: (feature, layer) => {
            let popupContent = `<strong>${datasetsConfig[key].name}</strong><br>`;
            if (feature.properties.Name) popupContent += `<b>${feature.properties.Name}</b><br>`;
            if (feature.properties.Type) popupContent += `<i>${feature.properties.Type}</i><br>`;
            if (feature.properties.Address) popupContent += `${feature.properties.Address}<br>`;
            if (feature.properties.City) popupContent += `${feature.properties.City}`;
            if (feature.properties.Manager) popupContent += `<br><small>Gestore: ${feature.properties.Manager}</small>`;
            layer.bindPopup(popupContent);
        }
    });

    const checkbox = document.getElementById(datasetsConfig[key].id);
    if (checkbox) {
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                pointLayers[key].addTo(map);
                updateVisiblePoints();
            } else {
                map.removeLayer(pointLayers[key]);
            }
        });
    }
});

// Funzione per caricare i punti visibili
async function updateVisiblePoints() {
    // OTTIMIZZAZIONE PRESTAZIONI:
    // Non caricare nulla se siamo troppo "lontani" (vista regionale) e non abbiamo selezionato una città specifica.
    // Questo evita di bloccare il browser cercando di disegnare migliaia di punti su tutta la Lombardia.
    if (!currentSelectedCity && map.getZoom() < 12) {
        // Pulisci tutti i layer se usciamo dallo zoom o deselezioniamo la città
        for (const layer of Object.values(pointLayers)) {
            layer.clearLayers();
        }
        return;
    }

    const bounds = map.getBounds();
    const minLat = bounds.getSouth();
    const minLon = bounds.getWest();
    const maxLat = bounds.getNorth();
    const maxLon = bounds.getEast();

    let url = `${API_URL}/points?minLat=${minLat}&minLon=${minLon}&maxLat=${maxLat}&maxLon=${maxLon}`;
    if (currentSelectedCity) {
        url += `&city=${encodeURIComponent(currentSelectedCity)}`;
    }

    // Aggiungi timestamp per evitare caching del browser
    url += `&_t=${new Date().getTime()}`;

    for (const [key, layer] of Object.entries(pointLayers)) {
        if (map.hasLayer(layer)) {
            try {
                const response = await fetch(`${url}&layer=${key}`);
                const data = await response.json();
                layer.clearLayers();
                layer.addData(data);
            } catch (error) {
                console.error(`Errore nel caricamento dei punti per ${key}:`, error);
            }
        }
    }
}

// Aggiorna quando la mappa si muove o cambia zoom
map.on('moveend', updateVisiblePoints);

// --- SEARCH E SIDEBAR ---

let searchableItems = [];

function indexData() {
    searchableItems = [];
    if (typeof comuniData !== 'undefined' && comuniData.features) {
        comuniData.features.forEach(feature => {
            if (feature.properties && feature.properties.name) {
                searchableItems.push({ name: feature.properties.name, type: "Comune", feature: feature });
            }
        });
    }
    if (typeof luoghiData !== 'undefined' && luoghiData.features) {
        luoghiData.features.forEach(feature => {
            if (feature.properties && feature.properties.name) {
                searchableItems.push({ name: feature.properties.name, type: feature.properties.type || "Frazione/Località", feature: feature });
            }
        });
    }
}

function initSearch() {
    indexData();
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        searchResults.innerHTML = '';
        if (query.length < 2) { searchResults.classList.remove('active'); return; }

        const filtered = searchableItems.filter(item => item.name.toLowerCase().includes(query));
        if (filtered.length > 0) {
            searchResults.classList.add('active');
            filtered.slice(0, 50).forEach(item => {
                const div = document.createElement('div');
                div.className = 'result-item';
                div.innerHTML = `<span class="name">${item.name}</span><span class="type">${item.type}</span>`;
                div.addEventListener('click', () => {
                    selectLocation(item);
                    searchResults.classList.remove('active');
                });
                searchResults.appendChild(div);
            });
        } else {
            searchResults.classList.remove('active');
        }
    });

    document.addEventListener('click', (e) => {
        const searchContainer = document.querySelector('.search-container');
        if (searchContainer && !searchContainer.contains(e.target)) searchResults.classList.remove('active');
    });
}

let highlightLayer = null;

async function selectLocation(item) {
    if (highlightLayer) map.removeLayer(highlightLayer);

    // Se clicchiamo su un Comune, lo impostiamo come filtro
    if (item.type === "Comune") {
        currentSelectedCity = item.name;
    } else {
        // Se è una frazione, non filtriamo per il nome della frazione (che nei dati punti è quasi sempre il Comune)
        // Ma potremmo voler filtrare per il Comune di appartenenza se lo avessimo nei metadati dei poligoni luoghi.
        // Per ora, resettiamo o manteniamo? L'utente dice "solo della città che clicco".
        // Assumiamo che se clicca una frazione, vuole vedere i punti di quel "territorio", ma i punti sono censiti per City (Comune).
        // Quindi se clicca una frazione, resettiamo il filtro o lo lasciamo?
        // Facciamo che se clicca una frazione NON cambia il filtro città dei punti per evitare confusione se la frazione ha un nome diverso dal comune.
        // currentSelectedCity = null; 
    }

    highlightLayer = L.geoJSON(item.feature, {
        style: { color: "#ff0000", weight: 4, opacity: 1, fillColor: "#ffff00", fillOpacity: 0.3 }
    }).addTo(map);

    map.fitBounds(highlightLayer.getBounds(), { padding: [50, 50], maxZoom: 16 });

    const infoPanel = document.getElementById('feature-info');

    // Mostra pannello laterale con loading
    infoPanel.innerHTML = `<h3>${item.name}</h3><p class="stats-hint">Caricamento dati...</p>`;

    try {
        const response = await fetch(`${API_URL}/stats?city=${encodeURIComponent(item.name)}&type=${encodeURIComponent(item.type || '')}`);
        const stats = await response.json();

        // Estrai dati immobiliari
        const salePrice = stats.real_estate && stats.real_estate.sale ? `€ ${stats.real_estate.sale}` : 'N/D';
        const rentPrice = stats.real_estate && stats.real_estate.rent ? `€ ${stats.real_estate.rent}` : 'N/D';

        infoPanel.innerHTML = `
            <h3>${item.name}</h3>
            
            <div class="stats-container">
                <h4>Mercato Immobiliare</h4>
                <ul>
                    <li><span class="emoji">🏠</span> Vendita: <strong>${salePrice}</strong></li>
                    <li><span class="emoji">🔑</span> Affitto: <strong>${rentPrice}</strong></li>
                </ul>
            </div>

            <div class="stats-container">
                <h4>Servizi in zona</h4>
                <ul>
                    <li><span class="emoji">🏫</span> Scuole <strong>${stats.schools}</strong></li>
                    <li><span class="emoji">💊</span> Farmacie <strong>${stats.pharmacies}</strong></li>
                    <li><span class="emoji">🏥</span> Strutture Sanitarie <strong>${stats.structures}</strong></li>
                    <li><span class="emoji">💧</span> Qualità Acqua <strong>${stats.water}</strong></li>
                </ul>
            </div>
            <button onclick="clearCityFilter()" class="clear-filter-btn">Mostra tutto</button>
        `;
        // Aggiorna i punti sulla mappa per mostrare solo quelli di questa città
        updateVisiblePoints();

        if (window.innerWidth <= 768) {
            infoPanel.scrollIntoView({ behavior: 'smooth' });
        }

    } catch (error) {
        console.error("Errore nel recupero delle statistiche:", error);
        infoPanel.innerHTML = `
            <h3>${item.name}</h3>
            <p class="error-text">Dati non disponibili al momento.</p>
            <button onclick="clearCityFilter()" class="clear-filter-btn">Mostra tutto</button>
        `;
    }
}

function clearCityFilter() {
    currentSelectedCity = null;
    if (highlightLayer) map.removeLayer(highlightLayer);
    updateVisiblePoints();
    document.getElementById('feature-info').innerHTML = `
        <p class="placeholder-text">Seleziona un Comune o una Frazione per vedere i dettagli.</p>
    `;
}

// Esponi al window per l'onclick dell'HTML generato dinamicamente
window.clearCityFilter = clearCityFilter;

// Avvio
initSearch();
console.log("Mappa pronta con filtro città dinamico");
