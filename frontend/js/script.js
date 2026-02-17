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
// let currentSelectedCity = null; // RIMOSSO: Concetto unificato in "currentSelectedFeatureGeometry"

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
    const comuniLayer = L.geoJSON(comuniData, {
        style: styleComuni,
        onEachFeature: (feature, layer) => {
            // FORZATURA TIPO: Assicuriamoci che ogni poligono di questo layer sia un "Comune"
            feature.properties.type = "Comune";
            onEachFeature(feature, layer);
        }
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

// --- IDISE LAYER (Disagio Sociale) ---
// Range: 97.6 - 104.8. Mean: 100.2. 
function getIdiseColor(d) {
    return d > 103.5 ? '#800026' : // Top Critical (approx > 98th percentile)
        d > 102.5 ? '#BD0026' : // Very High 
            d > 101.5 ? '#E31A1C' : // High
                d > 101.0 ? '#FC4E2A' : // Moderately High
                    d > 100.5 ? '#FD8D3C' : // Above Average
                        d > 100 ? '#FEB24C' : // Slightly Above Average
                            'transparent'; // Below Average (Good, so hide)
}

function styleIdise(feature) {
    const val = feature.properties.IDISE || 0;

    // NASCONDI SE VALORE <= 100 (O nullo)
    if (val <= 100) {
        return {
            fillColor: 'transparent',
            weight: 0,
            opacity: 0,
            fillOpacity: 0
        };
    }

    return {
        fillColor: getIdiseColor(val),
        weight: 0.5,
        opacity: 1,
        color: '#000000',
        dashArray: '',
        fillOpacity: 0.6
    };
}

if (typeof sezioniData !== 'undefined') {
    const idiseLayer = L.geoJSON(sezioniData, {
        style: styleIdise,
        onEachFeature: function (feature, layer) {
            let p = feature.properties;
            let content = `<strong>Sezione ${p.SEZ21 || ''}</strong><br>
                           IDISE: <b>${p.IDISE ? p.IDISE.toFixed(2) : "N/A"}</b><br>
                           Popolazione: ${p.POP_TOT || 'N/A'}`;
            layer.bindPopup(content);
        }
    });
});
layers["Disagio IDISE (2021)"] = idiseLayer;
}

// --- ADU LAYER (Aree di Disagio Urbano - Specifiche) ---
if (typeof aduData !== 'undefined') {
    const aduLayer = L.geoJSON(aduData, {
        style: function (feature) {
            return {
                fillColor: feature.properties.fillColor || getIdiseColor(feature.properties.IDISE || 100),
                weight: 2,
                opacity: 1,
                color: '#000',
                fillOpacity: 0.7
            };
        },
        onEachFeature: function (feature, layer) {
            let p = feature.properties;
            let content = `<strong>Area Critica (ADU)</strong><br>
                           IDISE: <b>${p.IDISE ? p.IDISE.toFixed(2) : "N/A"}</b><br>
                           Popolazione: ${p.POP_TOT || 'N/A'}`;
            layer.bindPopup(content);
        }
    });
    layers["Aree Critiche (ADU)"] = aduLayer;

    // Attiva ADU di default
    aduLayer.addTo(map);
}

// Aggiungi i Base Layer al controllo standard di Leaflet (in alto a destra)
L.control.layers(null, layers, { collapsed: true }).addTo(map);

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
        // Disabilita di default all'avvio
        checkbox.disabled = true;
        checkbox.parentElement.style.opacity = "0.5";
        checkbox.parentElement.title = "Seleziona prima una zona sulla mappa";

        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                pointLayers[key].addTo(map);
                // Carica i punti SOLO se abbiamo una ZONA selezionata
                if (currentSelectedFeatureGeometry) {
                    updateVisiblePoints();
                }
            } else {
                map.removeLayer(pointLayers[key]);
            }
        });
    }
});

// Funzione per abilitare/disabilitare i controlli
function updateControlsState(enable) {
    Object.keys(datasetsConfig).forEach(key => {
        const checkbox = document.getElementById(datasetsConfig[key].id);
        if (checkbox) {
            checkbox.disabled = !enable;
            checkbox.parentElement.style.opacity = enable ? "1" : "0.5";
            checkbox.parentElement.title = enable ? "" : "Seleziona prima una zona sulla mappa";

            // Se disabilitiamo, deselezioniamo anche e rimuoviamo il layer
            if (!enable && checkbox.checked) {
                checkbox.checked = false;
                if (map.hasLayer(pointLayers[key])) {
                    map.removeLayer(pointLayers[key]);
                }
            }
        }
    });
}

// --- GEOMETRY UTILS (POINT IN POLYGON) ---
function isPointInPolygon(point, vs) {
    // point = [lon, lat], vs = [[lon, lat], ...]
    var x = point[0], y = point[1];
    var inside = false;
    for (var i = 0, j = vs.length - 1; i < vs.length; j = i++) {
        var xi = vs[i][0], yi = vs[i][1];
        var xj = vs[j][0], yj = vs[j][1];
        var intersect = ((yi > y) != (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
}

function isPointInFeature(point, geometry) {
    if (!geometry || !geometry.coordinates) return true;
    if (geometry.type === 'Polygon') {
        return isPointInPolygon(point, geometry.coordinates[0]);
    } else if (geometry.type === 'MultiPolygon') {
        for (let i = 0; i < geometry.coordinates.length; i++) {
            if (isPointInPolygon(point, geometry.coordinates[i][0])) return true;
        }
    }
    return false;
}

let currentSelectedFeatureGeometry = null;

// Funzione per caricare i punti visibili
async function updateVisiblePoints() {
    // APPROCCIO "TUTTO E' UNA ZONA": 
    // Se non c'è una geometria selezionata, NON caricare nulla.
    if (!currentSelectedFeatureGeometry) {
        for (const layer of Object.values(pointLayers)) {
            layer.clearLayers();
        }
        return;
    }

    // Usiamo il bounding box della GEOMETRIA SELEZIONATA
    // Questo evita di caricare punti fuori dallo schermo se siamo zoomati, 
    // ma soprattutto centra la richiesta sull'area di interesse.
    if (!highlightLayer) return;
    const bounds = highlightLayer.getBounds();
    const minLat = bounds.getSouth();
    const minLon = bounds.getWest();
    const maxLat = bounds.getNorth();
    const maxLon = bounds.getEast();

    let url = `${API_URL}/points?minLat=${minLat}&minLon=${minLon}&maxLat=${maxLat}&maxLon=${maxLon}`;

    // Aggiungi timestamp per evitare caching del browser
    url += `&_t=${new Date().getTime()}`;

    for (const [key, layer] of Object.entries(pointLayers)) {
        if (map.hasLayer(layer)) {
            try {
                const response = await fetch(`${url}&layer=${key}`);
                const data = await response.json();

                let featuresToShow = data.features;

                // FILTRO GEOGRAFICO RIGOROSO
                // Mostra SOLO i punti che cadono esattamente dentro i confini del poligono selezionato.
                if (currentSelectedFeatureGeometry) {
                    featuresToShow = featuresToShow.filter(f =>
                        isPointInFeature(f.geometry.coordinates, currentSelectedFeatureGeometry)
                    );
                }

                layer.clearLayers();
                layer.addData({ type: "FeatureCollection", features: featuresToShow });
            } catch (error) {
                console.error(`Errore nel caricamento dei punti per ${key}:`, error);
            }
        }
    }
}

// RIMOSSO EVENT LISTENER GLOBALE
// map.on('moveend', updateVisiblePoints); <--- QUESTA RIGA È CANCELLATA
// I punti si aggiornano solo quando:
// 1. Selezioni una città (selectLocation)
// 2. Accendi/Spegni un toggle (checkbox change)

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
                // Determine type more gracefully if possible
                let t = feature.properties.type || "Zona";
                searchableItems.push({ name: feature.properties.name, type: t, feature: feature });
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

    // LOGICA SEMPLIFICATA "TUTTO E' UNA ZONA"
    // Non ci preoccupiamo più se è Comune o Frazione. 
    // Salviamo la geometria per il filtro e basta.
    currentSelectedFeatureGeometry = item.feature.geometry;

    highlightLayer = L.geoJSON(item.feature, {
        style: { color: "#ff0000", weight: 4, opacity: 1, fillColor: "#ffff00", fillOpacity: 0.3 }
    }).addTo(map);

    map.fitBounds(highlightLayer.getBounds(), { padding: [50, 50], maxZoom: 16 });

    // ABILITA I CONTROLLI DEI DATI
    updateControlsState(true);

    const infoPanel = document.getElementById('feature-info');

    // Mostra pannello laterale con loading
    infoPanel.innerHTML = `<h3>${item.name}</h3><p class="stats-hint">Caricamento dati zona...</p>`;

    // Su mobile, apri la sidebar per mostrare i dati
    if (typeof openSidebarMobile === 'function') openSidebarMobile();

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
        // Aggiorna i punti sulla mappa per mostrare solo quelli di questa città/zona
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
    // currentSelectedCity = null; // RIMOSSO
    currentSelectedFeatureGeometry = null;
    if (highlightLayer) map.removeLayer(highlightLayer);

    // Pulisci tutti i punti
    for (const layer of Object.values(pointLayers)) {
        layer.clearLayers();
    }

    // DISABILITA I CONTROLLI
    updateControlsState(false);

    document.getElementById('feature-info').innerHTML = `
        <p class="placeholder-text">Seleziona una Zona sulla mappa per vedere i dettagli.</p>
    `;
}

// Esponi al window per l'onclick dell'HTML generato dinamicamente
window.clearCityFilter = clearCityFilter;

// Avvio
initSearch();
console.log("Mappa pronta: Modalità ZONA UNICA attiva");

// --- MOBILE SIDEBAR TOGGLE ---
const sidebar = document.getElementById('sidebar');
const toggleBtn = document.getElementById('sidebar-toggle');

if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('active');
    });

    // Chiudi la sidebar se clicchi fuori (sulla mappa) su mobile
    map.on('click', () => {
        if (window.innerWidth <= 768) {
            sidebar.classList.remove('active');
        }
    });

    // APERTURA TRAMITE HEADER (TENDINA, CLICK & SWIPE)
    const mobileHeader = document.getElementById('mobile-header-click');
    if (mobileHeader) {

        // Gestione Click Semplice
        mobileHeader.addEventListener('click', () => {
            if (window.innerWidth <= 768) {
                sidebar.classList.toggle('active');
            }
        });

        // Gestione Swipe (Touch)
        let startY = 0;

        mobileHeader.addEventListener('touchstart', (e) => {
            startY = e.touches[0].clientY;
        }, { passive: true });

        mobileHeader.addEventListener('touchend', (e) => {
            const endY = e.changedTouches[0].clientY;
            const diff = startY - endY;

            // Se diff > 50 (Swipe verso l'ALTO) -> Apri
            if (diff > 50) {
                sidebar.classList.add('active');
            }
            // Se diff < -50 (Swipe verso il BASSO) -> Chiudi
            else if (diff < -50) {
                sidebar.classList.remove('active');
            }
        }, { passive: true });
    }
}

// Funzione ausiliaria per aprire la sidebar su mobile quando serve (es. selezione città)
function openSidebarMobile() {
    if (window.innerWidth <= 768) {
        sidebar.classList.add('active');
    }
}
