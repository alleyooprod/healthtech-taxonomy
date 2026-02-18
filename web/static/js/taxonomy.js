/**
 * Taxonomy tree, review, quality dashboard, and Cytoscape graph.
 */

let reviewChanges = [];
let cyInstance = null;

async function loadTaxonomy() {
    const res = await safeFetch(`/api/taxonomy?project_id=${currentProjectId}`);
    const categories = await res.json();

    const topLevel = categories.filter(c => !c.parent_id);
    const subs = categories.filter(c => c.parent_id);

    document.getElementById('taxonomyTree').innerHTML = topLevel.map(cat => {
        const children = subs.filter(s => s.parent_id === cat.id);
        const childHtml = children.length
            ? `<div class="sub-categories">${children.map(s =>
                `<div class="sub-cat">${esc(s.name)} <span class="count">(${s.company_count})</span></div>`
            ).join('')}</div>`
            : '';
        return `<div class="category-card">
            <div class="cat-header">${esc(cat.name)} <span class="count">(${cat.company_count})</span></div>
            ${childHtml}
        </div>`;
    }).join('');

    // Populate category filter dropdown
    const filter = document.getElementById('categoryFilter');
    filter.innerHTML = '<option value="">+ Category</option>' +
        topLevel.map(c => `<option value="${c.id}">${esc(c.name)} (${c.company_count})</option>`).join('');

    // Populate report category dropdown
    const reportSel = document.getElementById('reportCategorySelect');
    if (reportSel) {
        reportSel.innerHTML = '<option value="">Select a category...</option>' +
            topLevel.map(c => `<option value="${esc(c.name)}">${esc(c.name)} (${c.company_count})</option>`).join('');
    }

    // Load history
    const histRes = await safeFetch(`/api/taxonomy/history?project_id=${currentProjectId}`);
    const history = await histRes.json();
    document.getElementById('taxonomyHistory').innerHTML = history.length
        ? history.map(h => `<div class="history-entry">
            <span class="change-type">${esc(h.change_type)}</span>
            ${esc(h.reason || '')}
            <span class="change-date">${new Date(h.created_at).toLocaleDateString()}</span>
          </div>`).join('')
        : '<p>No taxonomy changes yet.</p>';
}

// --- Taxonomy Review ---
async function startTaxonomyReview() {
    const btn = document.getElementById('reviewBtn');
    btn.disabled = true;
    btn.textContent = 'Reviewing...';

    document.getElementById('reviewStatus').classList.remove('hidden');
    document.getElementById('reviewStatus').innerHTML =
        '<div class="progress-bar"><div id="reviewProgress" class="progress-fill" style="width:30%;animation:pulse 2s infinite"></div></div>' +
        '<p>Claude is analyzing all categories and company placements. This may take 1-3 minutes...</p>';
    document.getElementById('reviewResults').classList.add('hidden');

    const observations = (document.getElementById('reviewObservations').value || '').trim();
    const res = await safeFetch('/api/taxonomy/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: currentProjectId, model: document.getElementById('reviewModelSelect').value, observations }),
    });
    const data = await res.json();

    pollReview(data.review_id);
}

let _reviewPollCount = 0;
const _MAX_REVIEW_RETRIES = 120; // 6 minutes at 3s intervals

async function pollReview(reviewId) {
    const res = await safeFetch(`/api/taxonomy/review/${reviewId}`);
    const data = await res.json();

    if (data.status === 'pending') {
        if (++_reviewPollCount > _MAX_REVIEW_RETRIES) {
            data.status = 'complete';
            data.result = { error: 'Taxonomy review timed out. Please try again.' };
        } else {
            setTimeout(() => pollReview(reviewId), 3000);
            return;
        }
    }
    _reviewPollCount = 0;

    const btn = document.getElementById('reviewBtn');
    btn.disabled = false;
    btn.textContent = 'Review Taxonomy with Claude';
    document.getElementById('reviewStatus').classList.add('hidden');

    const result = data.result;
    if (result.error) {
        document.getElementById('reviewResults').classList.remove('hidden');
        document.getElementById('reviewResults').innerHTML =
            `<div class="review-error">${esc(result.error)}</div>`;
        return;
    }

    reviewChanges = result.changes || [];
    let html = `<div class="review-analysis"><strong>Analysis:</strong> ${esc(result.analysis || '')}</div>`;

    if (result.no_changes_needed || !reviewChanges.length) {
        html += `<p>No changes recommended.</p>`;
    } else {
        html += `<h3>Proposed Changes (${reviewChanges.length})</h3>`;
        html += `<p class="hint-text">Select changes to apply, then click "Apply Selected".</p>`;
        html += reviewChanges.map((c, i) => {
            let desc = '';
            if (c.type === 'move') desc = `Move "${c.category_name}" to ${c.merge_into}`;
            else if (c.type === 'merge') desc = `Merge "${c.category_name}" into "${c.merge_into}"`;
            else if (c.type === 'rename') desc = `Rename "${c.category_name}" to "${c.new_name}"`;
            else if (c.type === 'split') desc = `Split "${c.category_name}" into ${(c.split_into||[]).join(', ')}`;
            else if (c.type === 'add') desc = `Add category: "${c.category_name}"`;
            else if (c.type === 'add_subcategory') desc = `Add subcategory: "${c.category_name}" under "${c.parent_category}"`;
            else desc = `${c.type}: ${c.category_name || ''}`;

            return `<div class="review-change">
                <label>
                    <input type="checkbox" name="review_change" value="${i}" checked>
                    <span class="change-type">${esc(c.type)}</span>
                    ${esc(desc)}
                </label>
                <div class="review-change-reason">${esc(c.reason || '')}</div>
            </div>`;
        }).join('');

        html += `<div class="review-actions">
            <button class="primary-btn" onclick="applyReviewChanges()">Apply Selected</button>
            <button class="btn" onclick="dismissReview()">Dismiss</button>
        </div>`;
    }

    document.getElementById('reviewResults').classList.remove('hidden');
    document.getElementById('reviewResults').innerHTML = html;
}

async function applyReviewChanges() {
    const checkboxes = document.querySelectorAll('input[name="review_change"]:checked');
    const selected = Array.from(checkboxes).map(cb => reviewChanges[parseInt(cb.value)]);

    if (!selected.length) { showToast('No changes selected'); return; }

    const res = await safeFetch('/api/taxonomy/review/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ changes: selected, project_id: currentProjectId }),
    });
    const data = await res.json();

    document.getElementById('reviewResults').innerHTML =
        `<p>${data.applied} changes applied successfully.</p>`;
    loadTaxonomy();
    loadStats();
}

function dismissReview() {
    document.getElementById('reviewResults').classList.add('hidden');
    reviewChanges = [];
}

// --- Taxonomy Quality ---
async function loadTaxonomyQuality() {
    const container = document.getElementById('qualityContent');
    container.classList.remove('hidden');
    container.innerHTML = '<p>Loading...</p>';
    const res = await safeFetch(`/api/taxonomy/quality?project_id=${currentProjectId}`);
    const q = await res.json();

    let html = '<div class="quality-cards">';

    const confColor = q.avg_confidence >= 0.7 ? 'var(--accent-success)' : q.avg_confidence >= 0.4 ? '#e6a817' : 'var(--accent-danger, #dc3545)';
    html += `<div class="quality-card">
        <div class="quality-metric" style="color:${confColor}">${q.avg_confidence != null ? Math.round(q.avg_confidence * 100) + '%' : 'N/A'}</div>
        <div class="quality-label">Avg. Confidence</div>
        <div class="quality-hint">${q.avg_confidence != null && q.avg_confidence < 0.5 ? 'Consider re-researching low-confidence companies' : q.avg_confidence != null && q.avg_confidence < 0.7 ? 'Moderate — review flagged categories' : 'Good coverage'}</div>
    </div>`;

    html += `<div class="quality-card">
        <div class="quality-metric">${q.total_companies}</div>
        <div class="quality-label">Total Companies</div>
        <div class="quality-hint">${q.total_companies < 20 ? 'Add more companies for richer analysis' : 'Solid dataset'}</div>
    </div>`;

    html += `<div class="quality-card">
        <div class="quality-metric">${q.total_categories}</div>
        <div class="quality-label">Categories</div>
        <div class="quality-hint">${q.total_categories > 0 ? Math.round(q.total_companies / q.total_categories) + ' companies per category avg.' : 'No categories'}</div>
    </div>`;

    html += '</div>';

    if (q.empty_categories.length) {
        html += `<div class="quality-issue">
            <div class="quality-issue-header"><strong>Empty categories (${q.empty_categories.length})</strong></div>
            <p class="quality-issue-desc">These categories have no companies. Either add companies or consider removing them.</p>
            <div class="quality-issue-items">${q.empty_categories.map(c =>
                `<span class="quality-chip">${esc(c.name)}
                    <button class="quality-chip-action" onclick="prefillReviewObservation('Remove empty category: ${esc(c.name)}')" title="Suggest removal in review">review</button>
                </span>`
            ).join('')}</div>
        </div>`;
    }
    if (q.overcrowded_categories.length) {
        html += `<div class="quality-issue quality-warn">
            <div class="quality-issue-header"><strong>Overcrowded categories (>15 companies)</strong></div>
            <p class="quality-issue-desc">These categories are too broad. Consider splitting them into subcategories for clearer segmentation.</p>
            <div class="quality-issue-items">${q.overcrowded_categories.map(c =>
                `<span class="quality-chip">${esc(c.name)} <strong>(${c.count})</strong>
                    <button class="quality-chip-action" onclick="prefillReviewObservation('Split overcrowded category ${esc(c.name)} (${c.count} companies) into subcategories')" title="Suggest split in review">split</button>
                </span>`
            ).join('')}</div>
        </div>`;
    }
    if (q.low_confidence_categories.length) {
        html += `<div class="quality-issue quality-warn">
            <div class="quality-issue-header"><strong>Low confidence categories (<50%)</strong></div>
            <p class="quality-issue-desc">Companies in these categories may be misclassified. Re-research or manually review placements.</p>
            <div class="quality-issue-items">${q.low_confidence_categories.map(c =>
                `<span class="quality-chip">${esc(c.name)} <strong>(${Math.round(c.avg_confidence * 100)}%)</strong>
                    <button class="quality-chip-action" onclick="prefillReviewObservation('Review misclassified companies in ${esc(c.name)} (low confidence ${Math.round(c.avg_confidence * 100)}%)')" title="Suggest review">review</button>
                </span>`
            ).join('')}</div>
        </div>`;
    }

    if (!q.empty_categories.length && !q.overcrowded_categories.length && !q.low_confidence_categories.length) {
        html += '<p style="color:var(--accent-success);font-size:13px;margin-top:12px">No quality issues found. Taxonomy is well-structured.</p>';
    }

    container.innerHTML = html;
}

function prefillReviewObservation(text) {
    const textarea = document.getElementById('reviewObservations');
    if (textarea) {
        const current = textarea.value.trim();
        textarea.value = current ? current + '\n' + text : text;
        textarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
        textarea.focus();
    }
}

// --- Cytoscape Graph ---
function renderTaxonomyGraph(categories, companies) {
    if (!window.cytoscape) return;
    const container = document.getElementById('taxonomyGraph');
    if (!container) return;

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    const elements = [];
    const topLevel = categories.filter(c => !c.parent_id);
    const subs = categories.filter(c => c.parent_id);

    elements.push({ data: { id: 'root', label: 'Taxonomy', type: 'root' } });

    topLevel.forEach(cat => {
        elements.push({
            data: {
                id: `cat-${cat.id}`,
                label: `${cat.name}\n(${cat.company_count})`,
                type: 'category',
                count: cat.company_count,
            },
        });
        elements.push({ data: { source: 'root', target: `cat-${cat.id}` } });
    });

    subs.forEach(sub => {
        elements.push({
            data: {
                id: `cat-${sub.id}`,
                label: `${sub.name}\n(${sub.company_count})`,
                type: 'subcategory',
                count: sub.company_count,
            },
        });
        elements.push({ data: { source: `cat-${sub.parent_id}`, target: `cat-${sub.id}` } });
    });

    if (cyInstance) cyInstance.destroy();
    cyInstance = cytoscape({
        container,
        elements,
        style: [
            {
                selector: 'node[type="root"]',
                style: {
                    'background-color': '#bc6c5a',
                    label: 'data(label)',
                    'text-valign': 'center',
                    'font-size': '14px',
                    color: isDark ? '#e8e0d4' : '#3D4035',
                    width: 60, height: 60,
                },
            },
            {
                selector: 'node[type="category"]',
                style: {
                    'background-color': '#5a7c5a',
                    label: 'data(label)',
                    'text-valign': 'center',
                    'text-wrap': 'wrap',
                    'text-max-width': '100px',
                    'font-size': '10px',
                    color: isDark ? '#e8e0d4' : '#3D4035',
                    width: 'mapData(count, 0, 30, 30, 70)',
                    height: 'mapData(count, 0, 30, 30, 70)',
                },
            },
            {
                selector: 'node[type="subcategory"]',
                style: {
                    'background-color': '#6b8fa3',
                    label: 'data(label)',
                    'text-valign': 'center',
                    'text-wrap': 'wrap',
                    'text-max-width': '80px',
                    'font-size': '9px',
                    color: isDark ? '#e8e0d4' : '#3D4035',
                    width: 25, height: 25,
                },
            },
            {
                selector: 'edge',
                style: {
                    width: 2,
                    'line-color': isDark ? '#555' : '#ccc',
                    'target-arrow-color': isDark ? '#555' : '#ccc',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                },
            },
        ],
        layout: { name: 'cose', animate: true, animationDuration: 500, nodeDimensionsIncludeLabels: true },
    });

    cyInstance.on('tap', 'node[type="category"]', (evt) => {
        const catId = evt.target.id().replace('cat-', '');
        const catName = evt.target.data('label').split('\n')[0];
        activeFilters.category_id = catId;
        activeFilters.category_name = catName;
        renderFilterChips();
        showTab('companies');
        loadCompanies();
    });
}

function switchTaxonomyView(view) {
    if (view === 'tree') {
        document.getElementById('taxonomyTree').classList.remove('hidden');
        document.getElementById('taxonomyGraph').classList.add('hidden');
        document.getElementById('treeViewBtn').classList.add('active');
        document.getElementById('graphViewBtn').classList.remove('active');
    } else {
        document.getElementById('taxonomyTree').classList.add('hidden');
        document.getElementById('taxonomyGraph').classList.remove('hidden');
        document.getElementById('treeViewBtn').classList.remove('active');
        document.getElementById('graphViewBtn').classList.add('active');
        safeFetch(`/api/taxonomy?project_id=${currentProjectId}`)
            .then(r => r.json())
            .then(cats => renderTaxonomyGraph(cats, []));
    }
}
