/**
 * Canvas: visual workspace for arranging companies, notes, and edges with Cytoscape.js.
 */

let _canvasCy = null;
let _currentCanvasId = null;
let _canvasSaveTimeout = null;
let _canvasCompanies = [];

// --- Canvas list ---
async function loadCanvasList() {
    const res = await safeFetch(`/api/canvases?project_id=${currentProjectId}`);
    const items = await res.json();
    const sel = document.getElementById('canvasSelect');
    const currentVal = sel.value;
    sel.innerHTML = '<option value="">Select canvas...</option>' +
        items.map(c => `<option value="${c.id}">${esc(c.title)}</option>`).join('');
    if (currentVal) sel.value = currentVal;

    // Load sidebar companies
    loadCanvasSidebarCompanies();
}

async function loadCanvasSidebarCompanies() {
    const res = await safeFetch(`/api/companies?project_id=${currentProjectId}&limit=500`);
    _canvasCompanies = await res.json();
    renderCanvasSidebar(_canvasCompanies);
}

function renderCanvasSidebar(companies) {
    const container = document.getElementById('canvasCompanyList');
    if (!container) return;
    container.innerHTML = companies.map(c => {
        const color = typeof getCategoryColor === 'function' ? getCategoryColor(c.category_id) : '#999';
        return `<div class="canvas-sidebar-item" draggable="true"
            ondragstart="onCanvasDragStart(event, ${c.id}, '${escAttr(c.name)}', '${escAttr(c.category_name || '')}', '${color}')"
            title="${esc(c.name)}">
            <span class="cat-color-dot" style="background:${color}"></span>
            <span class="canvas-sidebar-name">${esc(c.name)}</span>
        </div>`;
    }).join('');
}

function filterCanvasCompanies() {
    const q = document.getElementById('canvasCompanySearch').value.toLowerCase();
    const filtered = q ? _canvasCompanies.filter(c =>
        c.name.toLowerCase().includes(q) || (c.category_name || '').toLowerCase().includes(q)
    ) : _canvasCompanies;
    renderCanvasSidebar(filtered);
}

// --- Canvas CRUD ---
async function createNewCanvas() {
    const title = prompt('Canvas name:');
    if (!title || !title.trim()) return;
    const res = await safeFetch('/api/canvases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: currentProjectId, title: title.trim() }),
    });
    const data = await res.json();
    if (data.id) {
        await loadCanvasList();
        document.getElementById('canvasSelect').value = data.id;
        loadCanvasFromSelect();
    }
}

function loadCanvasFromSelect() {
    const id = document.getElementById('canvasSelect').value;
    if (id) {
        loadCanvas(parseInt(id));
    } else {
        _currentCanvasId = null;
        if (_canvasCy) { _canvasCy.destroy(); _canvasCy = null; }
        document.getElementById('canvasContainer').classList.add('hidden');
        document.getElementById('canvasEmptyState').classList.remove('hidden');
        setCanvasButtonsEnabled(false);
    }
}

async function loadCanvas(canvasId) {
    _currentCanvasId = canvasId;
    const res = await safeFetch(`/api/canvases/${canvasId}`);
    const canvas = await res.json();
    if (canvas.error) { showToast('Canvas not found'); return; }

    document.getElementById('canvasEmptyState').classList.add('hidden');
    document.getElementById('canvasContainer').classList.remove('hidden');
    setCanvasButtonsEnabled(true);
    initCytoscape(canvas.data);
}

function setCanvasButtonsEnabled(enabled) {
    ['renameCanvasBtn', 'deleteCanvasBtn', 'canvasAddNoteBtn', 'canvasExportBtn'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.disabled = !enabled;
    });
}

async function renameCurrentCanvas() {
    if (!_currentCanvasId) return;
    const title = prompt('New canvas name:');
    if (!title || !title.trim()) return;
    await safeFetch(`/api/canvases/${_currentCanvasId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title.trim() }),
    });
    loadCanvasList();
    showToast('Canvas renamed');
}

async function deleteCurrentCanvas() {
    if (!_currentCanvasId) return;
    if (!confirm('Delete this canvas?')) return;
    await safeFetch(`/api/canvases/${_currentCanvasId}`, { method: 'DELETE' });
    _currentCanvasId = null;
    if (_canvasCy) { _canvasCy.destroy(); _canvasCy = null; }
    document.getElementById('canvasContainer').classList.add('hidden');
    document.getElementById('canvasEmptyState').classList.remove('hidden');
    setCanvasButtonsEnabled(false);
    loadCanvasList();
    showToast('Canvas deleted');
}

// --- Cytoscape initialization ---
function initCytoscape(data) {
    const container = document.getElementById('canvasContainer');
    if (_canvasCy) _canvasCy.destroy();

    const elements = data.elements || [];
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    _canvasCy = cytoscape({
        container: container,
        elements: elements,
        style: [
            {
                selector: 'node[type="company"]',
                style: {
                    'label': 'data(label)',
                    'background-color': 'data(color)',
                    'color': isDark ? '#e0ddd5' : '#3D4035',
                    'text-valign': 'bottom',
                    'text-halign': 'center',
                    'font-size': '11px',
                    'width': 50,
                    'height': 50,
                    'border-width': 2,
                    'border-color': 'data(color)',
                    'background-opacity': 0.15,
                    'text-margin-y': 6,
                    'text-wrap': 'ellipsis',
                    'text-max-width': '80px',
                },
            },
            {
                selector: 'node[type="note"]',
                style: {
                    'label': 'data(label)',
                    'shape': 'round-rectangle',
                    'background-color': isDark ? '#4a4636' : '#FFF8E1',
                    'color': isDark ? '#e0ddd5' : '#3D4035',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'font-size': '12px',
                    'width': 'label',
                    'height': 'label',
                    'padding': '12px',
                    'border-width': 1,
                    'border-color': isDark ? '#6b6550' : '#FFE082',
                    'text-wrap': 'wrap',
                    'text-max-width': '160px',
                },
            },
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': isDark ? '#6b6550' : '#ccc',
                    'target-arrow-color': isDark ? '#6b6550' : '#ccc',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'label': 'data(label)',
                    'font-size': '10px',
                    'text-rotation': 'autorotate',
                    'color': isDark ? '#999' : '#888',
                },
            },
            {
                selector: ':selected',
                style: {
                    'border-width': 3,
                    'border-color': '#BC6C5A',
                },
            },
        ],
        layout: { name: 'preset' },
        wheelSensitivity: 0.3,
        boxSelectionEnabled: true,
    });

    // Drop zone for companies dragged from sidebar
    container.addEventListener('dragover', (e) => e.preventDefault());
    container.addEventListener('drop', onCanvasDrop);

    // Double-click to add note
    _canvasCy.on('dbltap', (e) => {
        if (e.target === _canvasCy) {
            const pos = e.position;
            addNoteAtPosition(pos.x, pos.y);
        }
    });

    // Right-click context menu
    _canvasCy.on('cxttap', 'node', (e) => {
        const node = e.target;
        showCanvasContextMenu(e.renderedPosition, node);
    });

    // Auto-save on any change
    _canvasCy.on('drag free add remove data', () => scheduleCanvasSave());

    // Edge drawing with shift+drag
    let _edgeSourceNode = null;
    _canvasCy.on('mousedown', 'node', (e) => {
        if (e.originalEvent.shiftKey) {
            _edgeSourceNode = e.target;
        }
    });
    _canvasCy.on('mouseup', 'node', (e) => {
        if (_edgeSourceNode && e.target !== _edgeSourceNode) {
            const existingEdge = _canvasCy.edges().filter(
                edge => edge.source().id() === _edgeSourceNode.id() && edge.target().id() === e.target.id()
            );
            if (existingEdge.length === 0) {
                _canvasCy.add({
                    group: 'edges',
                    data: {
                        id: 'e-' + Date.now(),
                        source: _edgeSourceNode.id(),
                        target: e.target.id(),
                        label: '',
                    },
                });
            }
            _edgeSourceNode = null;
        }
    });
    _canvasCy.on('mouseup', (e) => {
        if (e.target === _canvasCy) _edgeSourceNode = null;
    });
}

// --- Drag & Drop from sidebar ---
function onCanvasDragStart(event, companyId, name, categoryName, color) {
    event.dataTransfer.setData('application/json', JSON.stringify({
        companyId, name, categoryName, color,
    }));
}

function onCanvasDrop(event) {
    event.preventDefault();
    if (!_canvasCy) return;

    let dragData;
    try {
        dragData = JSON.parse(event.dataTransfer.getData('application/json'));
    } catch { return; }

    // Check if company already on canvas
    const existing = _canvasCy.getElementById('company-' + dragData.companyId);
    if (existing.length) {
        showToast(`${dragData.name} is already on the canvas`);
        return;
    }

    // Convert screen coordinates to cytoscape model coordinates
    const rect = _canvasCy.container().getBoundingClientRect();
    const pan = _canvasCy.pan();
    const zoom = _canvasCy.zoom();
    const pos = {
        x: (event.clientX - rect.left - pan.x) / zoom,
        y: (event.clientY - rect.top - pan.y) / zoom,
    };

    _canvasCy.add({
        group: 'nodes',
        data: {
            id: 'company-' + dragData.companyId,
            label: dragData.name,
            type: 'company',
            companyId: dragData.companyId,
            categoryName: dragData.categoryName,
            color: dragData.color || '#999',
        },
        position: pos,
    });
}

// --- Notes ---
function addCanvasNote() {
    if (!_canvasCy) return;
    const center = {
        x: _canvasCy.width() / 2,
        y: _canvasCy.height() / 2,
    };
    const pan = _canvasCy.pan();
    const zoom = _canvasCy.zoom();
    const pos = {
        x: (center.x - pan.x) / zoom,
        y: (center.y - pan.y) / zoom,
    };
    addNoteAtPosition(pos.x, pos.y);
}

function addNoteAtPosition(x, y) {
    if (!_canvasCy) return;
    const text = prompt('Note text:');
    if (!text || !text.trim()) return;
    _canvasCy.add({
        group: 'nodes',
        data: {
            id: 'note-' + Date.now(),
            label: text.trim(),
            type: 'note',
        },
        position: { x, y },
    });
}

// --- Context menu ---
let _canvasCtxMenu = null;
function showCanvasContextMenu(renderedPos, node) {
    hideCanvasContextMenu();
    const menu = document.createElement('div');
    menu.className = 'canvas-context-menu';
    menu.id = 'canvasCtxMenu';

    const items = [];
    if (node.data('type') === 'company') {
        items.push({ label: 'Open Detail', icon: 'open_in_new', action: () => { showTab('companies'); showDetail(node.data('companyId')); } });
        items.push({ label: 'Start Research', icon: 'science', action: () => startCompanyResearch(node.data('companyId'), node.data('label')) });
    }
    if (node.data('type') === 'note') {
        items.push({ label: 'Edit Note', icon: 'edit', action: () => {
            const text = prompt('Edit note:', node.data('label'));
            if (text !== null) { node.data('label', text.trim()); scheduleCanvasSave(); }
        }});
    }
    items.push({ label: 'Remove', icon: 'delete', action: () => {
        _canvasCy.remove(node);
        _canvasCy.remove(_canvasCy.edges().filter(e => e.source().id() === node.id() || e.target().id() === node.id()));
    }});

    menu.innerHTML = items.map(item =>
        `<div class="canvas-ctx-item" onclick="event.stopPropagation()">
            <span class="material-symbols-outlined" style="font-size:16px">${item.icon}</span>
            ${esc(item.label)}
        </div>`
    ).join('');

    // Attach click handlers
    const menuItems = menu.querySelectorAll('.canvas-ctx-item');
    items.forEach((item, i) => {
        menuItems[i].addEventListener('click', () => { hideCanvasContextMenu(); item.action(); });
    });

    const container = document.getElementById('canvasContainer');
    menu.style.left = renderedPos.x + 'px';
    menu.style.top = renderedPos.y + 'px';
    container.appendChild(menu);
    _canvasCtxMenu = menu;

    // Close on click outside
    setTimeout(() => {
        document.addEventListener('click', hideCanvasContextMenu, { once: true });
    }, 0);
}

function hideCanvasContextMenu() {
    if (_canvasCtxMenu) {
        _canvasCtxMenu.remove();
        _canvasCtxMenu = null;
    }
}

// --- Auto-save ---
function scheduleCanvasSave() {
    clearTimeout(_canvasSaveTimeout);
    _canvasSaveTimeout = setTimeout(saveCanvas, 2000);
}

async function saveCanvas() {
    if (!_canvasCy || !_currentCanvasId) return;
    const elements = _canvasCy.json().elements;
    await safeFetch(`/api/canvases/${_currentCanvasId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: { elements } }),
    });
}

// --- Export ---
function exportCanvasPng() {
    if (!_canvasCy) return;
    const png = _canvasCy.png({ bg: document.documentElement.getAttribute('data-theme') === 'dark' ? '#1e1e1e' : '#ffffff', full: true, scale: 2 });
    const link = document.createElement('a');
    link.href = png;
    link.download = 'canvas.png';
    link.click();
}
