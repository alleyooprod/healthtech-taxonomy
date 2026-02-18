/**
 * Market map (drag-drop tiles), compare companies, geographic map (Leaflet).
 */

let compareSelection = new Set();
let leafletMap = null;
let markerClusterGroup = null;

async function loadMarketMap() {
    const [compRes, taxRes] = await Promise.all([
        fetch(`/api/companies?project_id=${currentProjectId}`),
        fetch(`/api/taxonomy?project_id=${currentProjectId}`),
    ]);
    const companies = await compRes.json();
    const categories = await taxRes.json();

    const topLevel = categories.filter(c => !c.parent_id).sort((a, b) => a.name.localeCompare(b.name));

    const byCategory = {};
    companies.forEach(c => {
        const catId = c.category_id || 0;
        byCategory[catId] = byCategory[catId] || [];
        byCategory[catId].push(c);
    });

    const mapDiv = document.getElementById('marketMap');
    mapDiv.innerHTML = topLevel.map(cat => `
        <div class="map-column"
             ondragover="event.preventDefault();this.classList.add('drag-over')"
             ondragleave="this.classList.remove('drag-over')"
             ondrop="handleMapDrop(event, ${cat.id})"
             data-category-id="${cat.id}">
            <div class="map-column-header">${esc(cat.name)} <span class="count">(${(byCategory[cat.id] || []).length})</span></div>
            <div class="map-tiles">
                ${(byCategory[cat.id] || []).sort((a,b) => a.name.localeCompare(b.name)).map(c => `
                    <div class="map-tile ${compareSelection.has(c.id) ? 'tile-selected' : ''}"
                         draggable="true"
                         ondragstart="event.dataTransfer.setData('text/plain', '${c.id}')"
                         onclick="toggleCompareSelect(${c.id}, this)"
                         title="${esc(c.what || '')}">
                        <img class="map-tile-logo" src="${c.logo_url || `https://logo.clearbit.com/${extractDomain(c.url)}`}" alt="" onerror="this.style.display='none'">
                        <span class="map-tile-name">${esc(c.name)}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');

    updateCompareBar();
}

async function handleMapDrop(event, targetCategoryId) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');
    const companyId = event.dataTransfer.getData('text/plain');
    if (!companyId) return;

    await safeFetch(`/api/companies/${companyId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category_id: targetCategoryId, project_id: currentProjectId }),
    });

    loadMarketMap();
    loadTaxonomy();
}

function toggleCompareSelect(id, el) {
    if (compareSelection.has(id)) {
        compareSelection.delete(id);
        el.classList.remove('tile-selected');
    } else if (compareSelection.size < 4) {
        compareSelection.add(id);
        el.classList.add('tile-selected');
    } else {
        showToast('Maximum 4 companies for comparison. Deselect one first.');
    }
    updateCompareBar();
}

function updateCompareBar() {
    const bar = document.getElementById('compareBar');
    if (compareSelection.size > 0) {
        bar.classList.remove('hidden');
        document.getElementById('compareCount').textContent = `${compareSelection.size} selected`;
    } else {
        bar.classList.add('hidden');
    }
}

function clearCompareSelection() {
    compareSelection.clear();
    document.querySelectorAll('.map-tile.tile-selected').forEach(el => el.classList.remove('tile-selected'));
    updateCompareBar();
}

async function runComparison() {
    if (compareSelection.size < 2) { showToast('Select at least 2 companies'); return; }
    const ids = Array.from(compareSelection).join(',');
    const res = await safeFetch(`/api/companies/compare?ids=${ids}`);
    const companies = await res.json();

    const fields = ['what', 'target', 'products', 'funding', 'geography',
        'employee_range', 'founded_year', 'funding_stage', 'total_funding_usd',
        'hq_city', 'hq_country', 'tam'];

    let html = '<table class="compare-table"><thead><tr><th>Field</th>';
    companies.forEach(c => { html += `<th>${esc(c.name)}</th>`; });
    html += '</tr></thead><tbody>';

    const labels = {
        what: 'What', target: 'Target', products: 'Products', funding: 'Funding',
        geography: 'Geography', employee_range: 'Employees', founded_year: 'Founded',
        funding_stage: 'Stage', total_funding_usd: 'Total Raised',
        hq_city: 'HQ City', hq_country: 'HQ Country', tam: 'TAM',
    };

    fields.forEach(f => {
        html += `<tr><td><strong>${labels[f] || f}</strong></td>`;
        companies.forEach(c => {
            let val = c[f];
            if (f === 'total_funding_usd' && val) val = '$' + Number(val).toLocaleString();
            html += `<td>${esc(String(val || 'N/A'))}</td>`;
        });
        html += '</tr>';
    });

    html += '<tr><td><strong>Tags</strong></td>';
    companies.forEach(c => { html += `<td>${(c.tags || []).join(', ') || 'None'}</td>`; });
    html += '</tr>';

    html += '</tbody></table>';

    document.getElementById('compareContent').innerHTML = html;
    document.getElementById('compareSection').classList.remove('hidden');
    document.getElementById('compareSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function clearComparison() {
    document.getElementById('compareSection').classList.add('hidden');
    clearCompareSelection();
}

async function exportMapPng() {
    if (typeof html2canvas === 'undefined') {
        showToast('html2canvas is still loading. Please try again in a moment.');
        return;
    }
    const mapEl = document.getElementById('marketMap');
    const canvas = await html2canvas(mapEl, { backgroundColor: getComputedStyle(document.documentElement).getPropertyValue('--bg-container').trim() });
    const link = document.createElement('a');
    link.download = 'market-map.png';
    link.href = canvas.toDataURL();
    link.click();
}

// --- Geographic Map (Leaflet) ---
const GEO_COORDS = {
    'US': [39.8, -98.5], 'USA': [39.8, -98.5], 'United States': [39.8, -98.5],
    'UK': [54.0, -2.0], 'United Kingdom': [54.0, -2.0], 'GB': [54.0, -2.0],
    'Canada': [56.1, -106.3], 'Germany': [51.2, 10.5], 'France': [46.6, 2.2],
    'Israel': [31.0, 34.8], 'India': [20.6, 78.9], 'Australia': [-25.3, 133.8],
    'Singapore': [1.35, 103.8], 'Japan': [36.2, 138.3], 'China': [35.9, 104.2],
    'Brazil': [-14.2, -51.9], 'South Korea': [35.9, 127.8], 'Netherlands': [52.1, 5.3],
    'Sweden': [60.1, 18.6], 'Switzerland': [46.8, 8.2], 'Spain': [40.5, -3.7],
    'Italy': [41.9, 12.6], 'Ireland': [53.4, -8.2], 'Mexico': [23.6, -102.5],
    'New York': [40.7, -74.0], 'San Francisco': [37.8, -122.4], 'London': [51.5, -0.1],
    'Boston': [42.4, -71.1], 'Los Angeles': [34.1, -118.2], 'Chicago': [41.9, -87.6],
    'Austin': [30.3, -97.7], 'Seattle': [47.6, -122.3], 'Denver': [39.7, -105.0],
    'Toronto': [43.7, -79.4], 'Berlin': [52.5, 13.4], 'Paris': [48.9, 2.3],
    'Tel Aviv': [32.1, 34.8], 'Mumbai': [19.1, 72.9], 'Bangalore': [12.97, 77.6],
    'Sydney': [-33.9, 151.2], 'Tokyo': [35.7, 139.7], 'Shanghai': [31.2, 121.5],
};

function getCoords(company) {
    const city = company.hq_city || '';
    const country = company.hq_country || company.geography || '';
    if (city && GEO_COORDS[city]) return GEO_COORDS[city];
    if (country && GEO_COORDS[country]) return GEO_COORDS[country];
    const firstWord = (country || '').split(',')[0].trim();
    if (GEO_COORDS[firstWord]) return GEO_COORDS[firstWord];
    return null;
}

async function renderGeoMap() {
    if (!window.L) return;
    const container = document.getElementById('geoMap');
    if (!container) return;

    if (!leafletMap) {
        leafletMap = L.map('geoMap').setView([30, 0], 2);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors',
            maxZoom: 18,
        }).addTo(leafletMap);
    }

    if (markerClusterGroup) leafletMap.removeLayer(markerClusterGroup);
    markerClusterGroup = L.markerClusterGroup ? L.markerClusterGroup() : L.layerGroup();

    const res = await safeFetch(`/api/companies?project_id=${currentProjectId}`);
    const companies = await res.json();

    const catColors = {};
    const colorPalette = ['#bc6c5a','#5a7c5a','#6b8fa3','#d4a853','#8b6f8b','#5a8c8c','#a67c52','#7c8c5a','#c4786e','#4a6a4a'];
    let colorIdx = 0;

    companies.forEach(c => {
        const coords = getCoords(c);
        if (!coords) return;
        const cat = c.category_name || 'Unknown';
        if (!catColors[cat]) catColors[cat] = colorPalette[colorIdx++ % colorPalette.length];
        const color = catColors[cat];

        const icon = L.divIcon({
            html: `<div style="background:${color};width:12px;height:12px;border-radius:50%;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.3)"></div>`,
            className: 'geo-marker-icon',
            iconSize: [16, 16],
        });
        const marker = L.marker([coords[0] + (Math.random()-0.5)*0.5, coords[1] + (Math.random()-0.5)*0.5], { icon });
        marker.bindPopup(`<strong>${esc(c.name)}</strong><br>${esc(cat)}<br>${esc(c.geography || '')}`);
        markerClusterGroup.addLayer(marker);
    });

    leafletMap.addLayer(markerClusterGroup);
    setTimeout(() => leafletMap.invalidateSize(), 100);
}

function switchMapView(view) {
    if (view === 'market') {
        document.getElementById('marketMap').classList.remove('hidden');
        document.getElementById('geoMap').classList.add('hidden');
        document.getElementById('marketMapBtn').classList.add('active');
        document.getElementById('geoMapBtn').classList.remove('active');
    } else {
        document.getElementById('marketMap').classList.add('hidden');
        document.getElementById('geoMap').classList.remove('hidden');
        document.getElementById('marketMapBtn').classList.remove('active');
        document.getElementById('geoMapBtn').classList.add('active');
        renderGeoMap();
    }
}
