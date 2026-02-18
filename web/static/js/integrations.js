/**
 * Library integrations and monkey-patches:
 * Notyf, DOMPurify, Day.js, Fuse.js, Tippy.js, Tagify,
 * SortableJS, Motion One, pdfmake override, confetti,
 * Driver.js product tour, enhanced search.
 */

// --- Notyf (Toast Notifications) ---
let notyf = null;
function initNotyf() {
    if (window.Notyf) {
        notyf = new Notyf({
            duration: 4000,
            position: { x: 'right', y: 'bottom' },
            types: [
                { type: 'success', background: '#5a7c5a', icon: false },
                { type: 'error', background: '#bc6c5a', icon: false },
                { type: 'info', background: '#6b7280', className: 'notyf-info', icon: false },
            ],
            ripple: true,
        });
    }
}

// Override showToast to use Notyf when available
const _origShowToast = showToast;
showToast = function(message, duration) {
    if (notyf) {
        notyf.open({ type: 'info', message });
    } else {
        _origShowToast(message, duration);
    }
};

// --- DOMPurify (Sanitize HTML output) ---
function sanitize(html) {
    if (window.DOMPurify) return DOMPurify.sanitize(html);
    // Fallback: strip all HTML tags if DOMPurify CDN failed to load
    const tmp = document.createElement('div');
    tmp.textContent = html;
    return tmp.innerHTML;
}

// --- Day.js (Date Formatting) ---
function initDayjs() {
    if (window.dayjs && window.dayjs_plugin_relativeTime) {
        dayjs.extend(dayjs_plugin_relativeTime);
    }
}
function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    if (window.dayjs) return dayjs(dateStr).format('MMM D, YYYY');
    return new Date(dateStr).toLocaleDateString();
}
function formatRelative(dateStr) {
    if (!dateStr) return '';
    if (window.dayjs) return dayjs(dateStr).fromNow();
    return new Date(dateStr).toLocaleDateString();
}

// --- Fuse.js (Fuzzy Search) ---
let fuseInstance = null;
let allCompaniesCache = [];

async function buildFuseIndex() {
    if (!window.Fuse || !currentProjectId) return;
    const res = await safeFetch(`/api/companies?project_id=${currentProjectId}`);
    allCompaniesCache = await res.json();
    fuseInstance = new Fuse(allCompaniesCache, {
        keys: [
            { name: 'name', weight: 0.4 },
            { name: 'what', weight: 0.2 },
            { name: 'target', weight: 0.15 },
            { name: 'category_name', weight: 0.1 },
            { name: 'geography', weight: 0.1 },
            { name: 'tags', weight: 0.05 },
        ],
        threshold: 0.35,
        includeScore: true,
        ignoreLocation: true,
    });
}

function fuseSearch(query) {
    if (!fuseInstance || !query.trim()) return null;
    return fuseInstance.search(query).map(r => r.item);
}

// --- Tippy.js (Tooltips) ---
function initTooltips() {
    if (!window.tippy) return;
    tippy('[data-tippy-content]', {
        theme: 'light-border',
        placement: 'top',
        animation: 'fade',
        delay: [300, 0],
    });
}

// --- Tagify (Enhanced Tag Input) ---
let tagifyInstance = null;

function initTagify() {
    if (!window.Tagify) return;
    const tagInput = document.getElementById('editTags');
    if (!tagInput || tagInput._tagifyInitialized) return;

    tagifyInstance = new Tagify(tagInput, {
        delimiters: ',',
        maxTags: 20,
        dropdown: { enabled: 1, maxItems: 10, closeOnSelect: true },
        originalInputValueFormat: vals => vals.map(v => v.value).join(', '),
    });
    tagInput._tagifyInitialized = true;
}

// Re-init tagify when edit modal opens
const _origOpenEditModal = openEditModal;
openEditModal = async function(id) {
    await _origOpenEditModal(id);
    if (tagifyInstance) { tagifyInstance.destroy(); tagifyInstance = null; }
    const tagInput = document.getElementById('editTags');
    if (tagInput) tagInput._tagifyInitialized = false;
    initTagify();
};

// --- SortableJS (Enhanced Drag-Drop for Map Tiles) ---
function initSortableMapTiles() {
    if (!window.Sortable) return;
    document.querySelectorAll('.map-tiles').forEach(container => {
        Sortable.create(container, {
            group: 'market-map',
            animation: 200,
            ghostClass: 'sortable-ghost',
            chosenClass: 'sortable-chosen',
            dragClass: 'sortable-drag',
            onEnd: async (evt) => {
                // SortableJS adds smooth animations; actual data update handled by native drag-drop
            },
        });
    });
}

// --- Hotkeys.js (Enhanced Keyboard Shortcuts) ---
let _hotkeysInitialized = false;
function initHotkeys() {
    if (!window.hotkeys || _hotkeysInitialized) return;
    _hotkeysInitialized = true;

    hotkeys('ctrl+k,command+k', (e) => {
        e.preventDefault();
        document.getElementById('searchInput')?.focus();
    });
    hotkeys('ctrl+e,command+e', (e) => {
        e.preventDefault();
        exportXlsx();
    });
    hotkeys('ctrl+shift+p,command+shift+p', (e) => {
        e.preventDefault();
        exportFullPdf();
    });
    hotkeys('g', (e) => {
        if (['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) return;
        e.preventDefault();
        const mapTab = document.getElementById('tab-map');
        if (mapTab && mapTab.classList.contains('active')) switchMapView('geo');
    });
    hotkeys('t', (e) => {
        if (['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) return;
        e.preventDefault();
        const taxTab = document.getElementById('tab-taxonomy');
        if (taxTab && taxTab.classList.contains('active')) switchTaxonomyView('graph');
    });
    hotkeys('shift+/', (e) => {
        // ? key (shift+/)
        if (['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) return;
        e.preventDefault();
        toggleShortcutsOverlay();
    });
    hotkeys('escape', () => {
        const overlay = document.getElementById('shortcutsOverlay');
        if (overlay && !overlay.classList.contains('hidden')) {
            overlay.classList.add('hidden');
        }
    });
}

// --- Driver.js (Product Tour) ---
function startProductTour() {
    if (!window.driver) return;
    const driverObj = driver.js.driver({
        showProgress: true,
        animate: true,
        steps: [
            { element: '#tab-companies', popover: { title: 'Companies Tab', description: 'Browse, search, and manage all researched companies. Use fuzzy search to find companies by name, category, or geography.', position: 'bottom' } },
            { element: '#searchInput', popover: { title: 'Smart Search', description: 'Powered by Fuse.js — type anything and it fuzzy-matches across name, description, category, tags, and geography. Press / to focus.', position: 'bottom' } },
            { element: '#tab-taxonomy', popover: { title: 'Taxonomy Tab', description: 'View your category structure in tree or interactive graph view. Analytics dashboard shows charts for category distribution, funding, and geography.', position: 'bottom' } },
            { element: '#tab-map', popover: { title: 'Map Tab', description: 'Two views: Market Map (drag-drop between categories) and Geographic Map (Leaflet world map showing company locations).', position: 'bottom' } },
            { element: '#tab-reports', popover: { title: 'Reports Tab', description: 'Generate AI-powered market analysis reports. Export as Markdown or PDF (powered by pdfmake).', position: 'bottom' } },
            { element: '#tab-export', popover: { title: 'Export Tab', description: 'Export your data as JSON, Markdown, CSV, or formatted Excel workbooks (powered by SheetJS).', position: 'bottom' } },
            { element: '#chatToggle', popover: { title: 'AI Chat', description: 'Ask questions about your taxonomy data — powered by Claude AI.', position: 'left' } },
            { popover: { title: 'Keyboard Shortcuts', description: 'Press ? for full shortcut list. j/k navigate rows, 1-5 switch tabs, / focuses search, Ctrl+K opens search, Ctrl+E exports Excel.', position: 'center' } },
        ],
    });
    driverObj.drive();
}

// --- canvas-confetti (Batch Complete Celebration) ---
function celebrateBatchComplete() {
    if (!window.confetti) return;
    confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#bc6c5a', '#5a7c5a', '#d4a853', '#6b8fa3'],
    });
}

// Hook confetti into SSE batch_complete
const _origConnectSSE = connectSSE;
connectSSE = function() {
    _origConnectSSE();
    if (eventSource) {
        eventSource.addEventListener('batch_complete', () => {
            celebrateBatchComplete();
            if (notyf) notyf.success('Batch processing complete!');
        });
    }
};

// --- Motion One (Animations) ---
function animateElement(el, keyframes, options) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        // Apply final state immediately for users who prefer reduced motion
        if (keyframes.opacity) el.style.opacity = Array.isArray(keyframes.opacity) ? keyframes.opacity[keyframes.opacity.length-1] : keyframes.opacity;
        if (keyframes.transform) el.style.transform = Array.isArray(keyframes.transform) ? keyframes.transform[keyframes.transform.length-1] : keyframes.transform;
        return;
    }
    if (window.Motion && window.Motion.animate) {
        return Motion.animate(el, keyframes, options);
    }
    if (keyframes.opacity) el.style.opacity = Array.isArray(keyframes.opacity) ? keyframes.opacity[keyframes.opacity.length-1] : keyframes.opacity;
}

// Animate detail panel open
const _origShowDetail = showDetail;
showDetail = async function(id) {
    await _origShowDetail(id);
    const panel = document.getElementById('detailPanel');
    if (panel && !panel.classList.contains('hidden')) {
        animateElement(panel, { opacity: [0, 1], transform: ['translateX(20px)', 'translateX(0)'] }, { duration: 0.25 });
    }
};

// Animate tab switch + refresh charts
const _origShowTab = showTab;
showTab = function(name) {
    _origShowTab(name);
    const tab = document.getElementById('tab-' + name);
    if (tab) {
        animateElement(tab, { opacity: [0, 1] }, { duration: 0.2 });
    }
    if (name === 'taxonomy') refreshDashboardCharts();
};

// --- Enhance loadCompanies with Fuse.js rebuild ---
const _origLoadCompanies = loadCompanies;
loadCompanies = async function() {
    await _origLoadCompanies();
    buildFuseIndex();
    initTooltips();
    if (document.getElementById('tab-map')?.classList.contains('active')) {
        initSortableMapTiles();
    }
};

// --- Enhanced search with Fuse.js ---
const origDebounceSearch = debounceSearch;
debounceSearch = function() {
    clearTimeout(searchTimeout);
    const query = document.getElementById('searchInput').value;
    if (fuseInstance && query.trim().length >= 2) {
        searchTimeout = setTimeout(() => {
            const results = fuseSearch(query);
            if (results) {
                renderFuseResults(results);
            } else {
                _origLoadCompanies();
            }
        }, 200);
    } else {
        searchTimeout = setTimeout(() => _origLoadCompanies(), 300);
    }
};

function renderFuseResults(companies) {
    const tbody = document.getElementById('companyBody');
    tbody.innerHTML = companies.map(c => {
        const compClass = (c.completeness || 0) >= 0.7 ? 'comp-high' : (c.completeness || 0) >= 0.4 ? 'comp-mid' : 'comp-low';
        const compPct = Math.round((c.completeness || 0) * 100);
        return `
        <tr onclick="showDetail(${c.id})" style="cursor:pointer" data-company-id="${c.id}">
            <td><span class="star-btn ${c.is_starred ? 'starred' : ''}" onclick="event.stopPropagation();toggleStar(${c.id},this)" title="Star">${c.is_starred ? '\u2605' : '\u2606'}</span></td>
            <td>
                <div class="company-name-cell">
                    <img class="company-logo" src="${c.logo_url || 'https://logo.clearbit.com/' + extractDomain(c.url)}" alt="" onerror="this.style.display='none'">
                    <strong>${esc(c.name)}</strong>
                    <span class="completeness-dot ${compClass}" title="${compPct}% complete"></span>
                    ${c.relationship_status ? '<span class="relationship-dot rel-' + c.relationship_status + '" title="' + relationshipLabel(c.relationship_status) + '"></span>' : ''}
                </div>
            </td>
            <td>${esc(c.category_name || 'N/A')}</td>
            <td><div class="cell-clamp">${esc(c.what || '')}</div></td>
            <td><div class="cell-clamp">${esc(c.target || '')}</div></td>
            <td><div class="cell-clamp">${esc(c.geography || '')}</div></td>
            <td><span class="source-count">${c.source_count || 0} links</span></td>
            <td>${(c.tags || []).map(t => '<span class="tag">' + esc(t) + '</span>').join(' ')}</td>
            <td>${c.confidence_score != null ? (c.confidence_score * 100).toFixed(0) + '%' : '-'}</td>
        </tr>`;
    }).join('');
}

// --- Override exportReportPdf to use pdfmake when available ---
const _origExportReportPdf = exportReportPdf;
exportReportPdf = function() {
    if (window.pdfMake) {
        exportReportPdfPdfmake();
    } else {
        _origExportReportPdf();
    }
};
