/**
 * Company list, detail panel, edit modal, star, sort.
 */

let currentSort = { by: 'name', dir: 'asc' };

function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(loadCompanies, 300);
}

async function loadCompanies() {
    const search = document.getElementById('searchInput').value;
    const starred = document.getElementById('starredFilter').checked;
    const needsEnrichment = document.getElementById('enrichmentFilter').checked;
    let url = `/api/companies?project_id=${currentProjectId}&`;
    if (search) url += `search=${encodeURIComponent(search)}&`;
    if (activeFilters.category_id) url += `category_id=${activeFilters.category_id}&`;
    if (starred) url += `starred=1&`;
    if (needsEnrichment) url += `needs_enrichment=1&`;
    if (activeFilters.tags.length) url += `tags=${encodeURIComponent(activeFilters.tags.join(','))}&`;
    if (activeFilters.geography) url += `geography=${encodeURIComponent(activeFilters.geography)}&`;
    if (activeFilters.funding_stage) url += `funding_stage=${encodeURIComponent(activeFilters.funding_stage)}&`;
    const relFilter = document.getElementById('relationshipFilter').value;
    if (relFilter) url += `relationship_status=${encodeURIComponent(relFilter)}&`;
    url += `sort_by=${currentSort.by}&sort_dir=${currentSort.dir}&`;

    const res = await safeFetch(url);
    const companies = await res.json();

    document.querySelectorAll('.sort-header').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
        if (th.dataset.sort === currentSort.by) {
            th.classList.add(currentSort.dir === 'asc' ? 'sort-asc' : 'sort-desc');
        }
    });

    const tbody = document.getElementById('companyBody');
    if (!companies.length) {
        const search = document.getElementById('searchInput').value;
        const hasFilters = search || activeFilters.category_id || activeFilters.tags.length
            || activeFilters.geography || activeFilters.funding_stage;
        tbody.innerHTML = `<tr><td colspan="9" class="empty-state">
            <div class="empty-state-content">
                <span class="empty-state-icon">&#128269;</span>
                <p class="empty-state-title">${hasFilters ? 'No companies match your filters' : 'No companies yet'}</p>
                <p class="empty-state-desc">${hasFilters
                    ? 'Try adjusting your search or <button class="empty-state-link" onclick="clearAllFilters()">clearing all filters</button>'
                    : 'Go to the <button class="empty-state-link" onclick="showTab(\'process\')">Process tab</button> to add companies'}</p>
            </div>
        </td></tr>`;
    } else {
        tbody.innerHTML = companies.map(c => {
            const compClass = c.completeness >= 0.7 ? 'comp-high' : c.completeness >= 0.4 ? 'comp-mid' : 'comp-low';
            const compPct = Math.round(c.completeness * 100);
            return `
            <tr onclick="showDetail(${c.id})" style="cursor:pointer" data-company-id="${c.id}">
                <td><span class="star-btn ${c.is_starred ? 'starred' : ''}" onclick="event.stopPropagation();toggleStar(${c.id},this)" title="Star">${c.is_starred ? '\u2605' : '\u2606'}</span></td>
                <td>
                    <div class="company-name-cell">
                        <img class="company-logo" src="${c.logo_url || `https://logo.clearbit.com/${extractDomain(c.url)}`}" alt="" onerror="this.style.display='none'">
                        <strong>${esc(c.name)}</strong>
                        <span class="completeness-dot ${compClass}" title="${compPct}% complete"></span>
                        ${c.relationship_status ? `<span class="relationship-dot rel-${c.relationship_status}" title="${relationshipLabel(c.relationship_status)}"></span>` : ''}
                    </div>
                </td>
                <td>${esc(c.category_name || 'N/A')}</td>
                <td><div class="cell-clamp">${esc(c.what || '')}</div></td>
                <td><div class="cell-clamp">${esc(c.target || '')}</div></td>
                <td><div class="cell-clamp">${esc(c.geography || '')}</div></td>
                <td><span class="source-count">${c.source_count || 0} links</span></td>
                <td>${(c.tags || []).map(t => `<span class="tag">${esc(t)}</span>`).join(' ')}</td>
                <td>${c.confidence_score != null ? (c.confidence_score * 100).toFixed(0) + '%' : '-'}</td>
            </tr>`;
        }).join('');
    }
}

async function toggleStar(id, el) {
    const res = await safeFetch(`/api/companies/${id}/star`, { method: 'POST' });
    const data = await res.json();
    el.textContent = data.is_starred ? '\u2605' : '\u2606';
    el.classList.toggle('starred', !!data.is_starred);
}

async function saveRelationship(id) {
    const status = document.getElementById(`relStatus-${id}`).value;
    const note = document.getElementById(`relNote-${id}`).value;
    await safeFetch(`/api/companies/${id}/relationship`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ status: status || null, note })
    });
    loadCompanies();
}

async function showDetail(id) {
    const res = await safeFetch(`/api/companies/${id}`);
    const c = await res.json();

    let sourcesHtml = '';
    if (c.sources && c.sources.length) {
        sourcesHtml = `<div class="detail-field">
            <label>Sources (${c.sources.length})</label>
            <div class="sources-list">
                ${c.sources.map(s => `
                    <div class="source-item">
                        <span class="source-type-badge source-type-${s.source_type}">${esc(s.source_type)}</span>
                        <a href="${esc(s.url)}" target="_blank">${esc(s.url)}</a>
                        <span class="source-date">${new Date(s.added_at).toLocaleDateString()}</span>
                    </div>
                `).join('')}
            </div>
        </div>`;
    }

    const logoUrl = c.logo_url || `https://logo.clearbit.com/${extractDomain(c.url)}`;
    const fundingAmt = c.total_funding_usd ? '$' + Number(c.total_funding_usd).toLocaleString() : null;

    document.getElementById('detailName').textContent = c.name;
    document.getElementById('detailContent').innerHTML = `
        <div class="detail-logo-row">
            <img class="detail-logo" src="${logoUrl}" alt="" onerror="this.style.display='none'">
            <a href="${esc(c.url)}" target="_blank">${esc(c.url)}</a>
            ${c.linkedin_url ? `<a href="${esc(c.linkedin_url)}" target="_blank" class="linkedin-link" title="LinkedIn">in</a>` : ''}
        </div>
        <div class="detail-field"><label>What</label><p>${esc(c.what || 'N/A')}</p></div>
        <div class="detail-field"><label>Target</label><p>${esc(c.target || 'N/A')}</p></div>
        <div class="detail-field"><label>Products</label><p>${esc(c.products || 'N/A')}</p></div>
        <div class="detail-firmographics">
            <div class="detail-field"><label>Funding</label><p>${esc(c.funding || 'N/A')}</p></div>
            <div class="detail-field"><label>Stage</label><p>${esc(c.funding_stage || 'N/A')}</p></div>
            <div class="detail-field"><label>Total Raised</label><p>${fundingAmt || 'N/A'}</p></div>
            <div class="detail-field"><label>Founded</label><p>${c.founded_year || 'N/A'}</p></div>
            <div class="detail-field"><label>Employees</label><p>${esc(c.employee_range || 'N/A')}</p></div>
            <div class="detail-field"><label>HQ</label><p>${esc(c.hq_city || '')}${c.hq_city && c.hq_country ? ', ' : ''}${esc(c.hq_country || 'N/A')}</p></div>
        </div>
        <div class="detail-field"><label>Geography</label><p>${esc(c.geography || 'N/A')}</p></div>
        <div class="detail-field"><label>TAM</label><p>${esc(c.tam || 'N/A')}</p></div>
        <div class="detail-field"><label>Category</label><p>${esc(c.category_name || 'N/A')} / ${esc(c.subcategory_name || 'N/A')}</p></div>
        <div class="detail-field"><label>Tags</label><p>${(c.tags || []).join(', ') || 'None'}</p></div>
        <div class="detail-field"><label>Confidence</label><p>${c.confidence_score != null ? (c.confidence_score * 100).toFixed(0) + '%' : 'N/A'}</p></div>
        <div class="detail-field"><label>Processed</label><p>${c.processed_at || 'N/A'}</p></div>
        ${sourcesHtml}
        ${c.status && c.status !== 'active' ? `<div class="lifecycle-badge lifecycle-${c.status}">${esc(c.status)}</div>` : ''}
        ${c.business_model || c.company_stage || c.primary_focus ? `
        <div class="detail-facets">
            ${c.business_model ? `<span class="facet-badge facet-model">${esc(c.business_model)}</span>` : ''}
            ${c.company_stage ? `<span class="facet-badge facet-stage">${esc(c.company_stage)}</span>` : ''}
            ${c.primary_focus ? `<span class="facet-badge facet-focus">${esc(c.primary_focus)}</span>` : ''}
        </div>` : ''}
        <div class="detail-actions">
            <button class="btn" onclick="openEditModal(${c.id})">Edit</button>
            <button class="btn" onclick="openReResearch(${c.id})">Re-research</button>
            <button class="btn" onclick="findSimilar(${c.id})">Find Similar</button>
            <button class="btn" onclick="showVersionHistory(${c.id})">History</button>
            <button class="danger-btn" onclick="deleteCompany(${c.id})">Delete</button>
        </div>
        <div id="similarResults-${c.id}" class="hidden similar-results"></div>

        <!-- Relationship Section -->
        <div class="relationship-section">
            <label>Relationship</label>
            <div class="relationship-controls">
                <select id="relStatus-${c.id}" class="relationship-select" onchange="saveRelationship(${c.id})">
                    <option value="">-- None --</option>
                    <option value="watching" ${c.relationship_status === 'watching' ? 'selected' : ''}>Watching</option>
                    <option value="to_reach_out" ${c.relationship_status === 'to_reach_out' ? 'selected' : ''}>To Reach Out</option>
                    <option value="in_conversation" ${c.relationship_status === 'in_conversation' ? 'selected' : ''}>In Conversation</option>
                    <option value="met" ${c.relationship_status === 'met' ? 'selected' : ''}>Met</option>
                    <option value="partner" ${c.relationship_status === 'partner' ? 'selected' : ''}>Partner</option>
                    <option value="not_relevant" ${c.relationship_status === 'not_relevant' ? 'selected' : ''}>Not Relevant</option>
                </select>
                ${c.relationship_status ? `<span class="relationship-dot rel-${c.relationship_status}" style="width:10px;height:10px"></span>` : ''}
            </div>
            <textarea id="relNote-${c.id}" class="relationship-note" rows="2" placeholder="Notes about this relationship..."
                onblur="saveRelationship(${c.id})">${esc(c.relationship_note || '')}</textarea>
        </div>

        <!-- Notes Section -->
        <div class="detail-notes">
            <div class="detail-notes-header">
                <label>Notes</label>
                <button class="filter-action-btn" onclick="showAddNote(${c.id})">+ Add note</button>
            </div>
            <div id="addNoteForm-${c.id}" class="hidden" style="margin-bottom:8px">
                <textarea id="newNoteText-${c.id}" rows="2" placeholder="Add a note..."></textarea>
                <div style="display:flex;gap:6px;margin-top:4px">
                    <button class="primary-btn" onclick="addNote(${c.id})">Save</button>
                    <button class="btn" onclick="document.getElementById('addNoteForm-${c.id}').classList.add('hidden')">Cancel</button>
                </div>
            </div>
            <div id="notesList-${c.id}">
                ${(c.notes || []).map(n => `
                    <div class="note-item ${n.is_pinned ? 'note-pinned' : ''}">
                        <div class="note-content">${esc(n.content)}</div>
                        <div class="note-meta">
                            <span>${new Date(n.created_at).toLocaleDateString()}</span>
                            <span class="note-action" onclick="togglePinNote(${n.id},${c.id})">${n.is_pinned ? 'Unpin' : 'Pin'}</span>
                            <span class="note-action note-delete" onclick="deleteNote(${n.id},${c.id})">Delete</span>
                        </div>
                    </div>
                `).join('') || '<p style="font-size:12px;color:var(--text-muted)">No notes yet.</p>'}
            </div>
        </div>

        <!-- Events Section -->
        <div class="detail-events">
            <div class="detail-notes-header">
                <label>Events</label>
                <button class="filter-action-btn" onclick="showAddEvent(${c.id})">+ Add event</button>
            </div>
            <div id="addEventForm-${c.id}" class="hidden" style="margin-bottom:8px">
                <div style="display:flex;gap:6px;flex-wrap:wrap">
                    <select id="newEventType-${c.id}">
                        <option value="funding_round">Funding Round</option>
                        <option value="acquired">Acquired</option>
                        <option value="shut_down">Shut Down</option>
                        <option value="launched">Product Launch</option>
                        <option value="pivot">Pivot</option>
                        <option value="partnership">Partnership</option>
                    </select>
                    <input type="date" id="newEventDate-${c.id}">
                </div>
                <textarea id="newEventDesc-${c.id}" rows="1" placeholder="Description..." style="margin-top:4px"></textarea>
                <div style="display:flex;gap:6px;margin-top:4px">
                    <button class="primary-btn" onclick="addEvent(${c.id})">Save</button>
                    <button class="btn" onclick="document.getElementById('addEventForm-${c.id}').classList.add('hidden')">Cancel</button>
                </div>
            </div>
            <div id="eventsList-${c.id}">
                ${(c.events || []).map(ev => `
                    <div class="event-item">
                        <span class="event-type-badge">${esc(ev.event_type)}</span>
                        <span>${esc(ev.description || '')}</span>
                        <span class="event-date">${ev.event_date || ''}</span>
                        <span class="note-action note-delete" onclick="deleteEvent(${ev.id},${c.id})">Delete</span>
                    </div>
                `).join('') || '<p style="font-size:12px;color:var(--text-muted)">No events yet.</p>'}
            </div>
        </div>

        <div id="reResearchForm-${c.id}" class="re-research-form hidden">
            <label>Additional source URLs (one per line):</label>
            <textarea id="reResearchUrls-${c.id}" rows="3" placeholder="https://example.com/about&#10;https://crunchbase.com/organization/..."></textarea>
            <div class="re-research-actions">
                <button class="primary-btn" onclick="startReResearch(${c.id})">Run Re-research</button>
                <button class="btn" onclick="closeReResearch(${c.id})">Cancel</button>
            </div>
            <div id="reResearchStatus-${c.id}" class="hidden"></div>
        </div>
    `;
    document.getElementById('detailPanel').classList.remove('hidden');
}

function closeDetail() {
    document.getElementById('detailPanel').classList.add('hidden');
}

async function deleteCompany(id) {
    if (!confirm('Delete this company?')) return;
    await safeFetch(`/api/companies/${id}`, { method: 'DELETE' });
    closeDetail();
    loadCompanies();
    loadStats();
}

// --- Re-Research ---
function openReResearch(id) {
    document.getElementById(`reResearchForm-${id}`).classList.remove('hidden');
}

function closeReResearch(id) {
    document.getElementById(`reResearchForm-${id}`).classList.add('hidden');
}

async function startReResearch(companyId) {
    const urlsText = document.getElementById(`reResearchUrls-${companyId}`).value;
    const urls = urlsText.split('\n').map(u => u.trim()).filter(Boolean);
    if (!urls.length) { showToast('Enter at least one URL'); return; }

    const statusDiv = document.getElementById(`reResearchStatus-${companyId}`);
    statusDiv.classList.remove('hidden');
    statusDiv.innerHTML = '<div class="progress-bar"><div class="progress-fill" style="width:30%;animation:pulse 2s infinite"></div></div><p>Re-researching with additional sources...</p>';

    const res = await safeFetch(`/api/companies/${companyId}/re-research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ urls, model: document.getElementById('modelSelect').value }),
    });
    const data = await res.json();
    pollReResearch(companyId, data.research_id);
}

let _reResearchPollCount = 0;
const _MAX_RERESEARCH_RETRIES = 60;

async function pollReResearch(companyId, researchId) {
    const res = await safeFetch(`/api/re-research/${researchId}`);
    const data = await res.json();

    if (data.status === 'pending') {
        if (++_reResearchPollCount > _MAX_RERESEARCH_RETRIES) {
            data.status = 'error';
            data.error = 'Re-research timed out. Please try again.';
        } else {
            setTimeout(() => pollReResearch(companyId, researchId), 3000);
            return;
        }
    }
    _reResearchPollCount = 0;

    const statusDiv = document.getElementById(`reResearchStatus-${companyId}`);
    if (data.status === 'error') {
        statusDiv.innerHTML = `<p class="re-research-error">${esc(data.error)}</p>`;
    } else {
        statusDiv.innerHTML = '<p class="re-research-success">Research updated successfully!</p>';
        setTimeout(() => {
            showDetail(companyId);
            loadCompanies();
            loadStats();
        }, 1000);
    }
}

// --- Edit Modal ---
async function openEditModal(id) {
    const res = await safeFetch(`/api/companies/${id}`);
    const c = await res.json();

    const taxRes = await safeFetch(`/api/taxonomy?project_id=${currentProjectId}`);
    allCategories = await taxRes.json();

    const topLevel = allCategories.filter(c => !c.parent_id);
    const catSelect = document.getElementById('editCategory');
    catSelect.innerHTML = '<option value="">-- Select --</option>' +
        topLevel.map(cat => `<option value="${cat.id}">${esc(cat.name)}</option>`).join('');

    document.getElementById('editId').value = c.id;
    document.getElementById('editName').value = c.name || '';
    document.getElementById('editUrl').value = c.url || '';
    document.getElementById('editWhat').value = c.what || '';
    document.getElementById('editTarget').value = c.target || '';
    document.getElementById('editProducts').value = c.products || '';
    document.getElementById('editFunding').value = c.funding || '';
    document.getElementById('editGeography').value = c.geography || '';
    document.getElementById('editTam').value = c.tam || '';
    document.getElementById('editTags').value = (c.tags || []).join(', ');
    document.getElementById('editEmployeeRange').value = c.employee_range || '';
    document.getElementById('editFoundedYear').value = c.founded_year || '';
    document.getElementById('editFundingStage').value = c.funding_stage || '';
    document.getElementById('editTotalFunding').value = c.total_funding_usd || '';
    document.getElementById('editHqCity').value = c.hq_city || '';
    document.getElementById('editHqCountry').value = c.hq_country || '';
    document.getElementById('editLinkedin').value = c.linkedin_url || '';
    document.getElementById('editBusinessModel').value = c.business_model || '';
    document.getElementById('editCompanyStage').value = c.company_stage || '';
    document.getElementById('editPrimaryFocus').value = c.primary_focus || '';

    catSelect.value = c.category_id || '';
    loadSubcategories();
    document.getElementById('editSubcategory').value = c.subcategory_id || '';

    document.getElementById('editModal').classList.remove('hidden');
    window._editModalFocusTrap = trapFocus(document.getElementById('editModal'));
}

function loadSubcategories() {
    const parentId = parseInt(document.getElementById('editCategory').value);
    const subSelect = document.getElementById('editSubcategory');
    const subs = allCategories.filter(c => c.parent_id === parentId);
    subSelect.innerHTML = '<option value="">-- Select --</option>' +
        subs.map(s => `<option value="${s.id}">${esc(s.name)}</option>`).join('');
}

function closeEditModal() {
    if (window._editModalFocusTrap) { window._editModalFocusTrap(); window._editModalFocusTrap = null; }
    document.getElementById('editModal').classList.add('hidden');
}

async function saveEdit(event) {
    event.preventDefault();
    const id = document.getElementById('editId').value;
    const tagsStr = document.getElementById('editTags').value;
    const tags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(Boolean) : [];

    const prevRes = await safeFetch(`/api/companies/${id}`);
    const prevData = await prevRes.json();

    const fields = {
        name: document.getElementById('editName').value,
        url: document.getElementById('editUrl').value,
        what: document.getElementById('editWhat').value,
        target: document.getElementById('editTarget').value,
        products: document.getElementById('editProducts').value,
        funding: document.getElementById('editFunding').value,
        geography: document.getElementById('editGeography').value,
        tam: document.getElementById('editTam').value,
        category_id: document.getElementById('editCategory').value || null,
        subcategory_id: document.getElementById('editSubcategory').value || null,
        tags: tags,
        project_id: currentProjectId,
        employee_range: document.getElementById('editEmployeeRange').value || null,
        founded_year: document.getElementById('editFoundedYear').value ? parseInt(document.getElementById('editFoundedYear').value) : null,
        funding_stage: document.getElementById('editFundingStage').value || null,
        total_funding_usd: document.getElementById('editTotalFunding').value ? parseFloat(document.getElementById('editTotalFunding').value) : null,
        hq_city: document.getElementById('editHqCity').value || null,
        hq_country: document.getElementById('editHqCountry').value || null,
        linkedin_url: document.getElementById('editLinkedin').value || null,
        business_model: document.getElementById('editBusinessModel').value || null,
        company_stage: document.getElementById('editCompanyStage').value || null,
        primary_focus: document.getElementById('editPrimaryFocus').value || null,
    };

    await safeFetch(`/api/companies/${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fields),
    });

    closeEditModal();
    closeDetail();
    loadCompanies();
    loadStats();

    showUndoToast(`Updated ${fields.name}`, async () => {
        const undoFields = {
            name: prevData.name, url: prevData.url, what: prevData.what,
            target: prevData.target, products: prevData.products, funding: prevData.funding,
            geography: prevData.geography, tam: prevData.tam,
            category_id: prevData.category_id, subcategory_id: prevData.subcategory_id,
            tags: prevData.tags || [], project_id: currentProjectId,
            employee_range: prevData.employee_range, founded_year: prevData.founded_year,
            funding_stage: prevData.funding_stage, total_funding_usd: prevData.total_funding_usd,
            hq_city: prevData.hq_city, hq_country: prevData.hq_country,
            linkedin_url: prevData.linkedin_url,
            business_model: prevData.business_model, company_stage: prevData.company_stage,
            primary_focus: prevData.primary_focus,
        };
        await safeFetch(`/api/companies/${id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(undoFields),
        });
        loadCompanies();
        loadStats();
    });
}

// --- Notes ---
function showAddNote(companyId) {
    document.getElementById(`addNoteForm-${companyId}`).classList.remove('hidden');
}

async function addNote(companyId) {
    const content = document.getElementById(`newNoteText-${companyId}`).value.trim();
    if (!content) return;
    await safeFetch(`/api/companies/${companyId}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
    });
    showDetail(companyId);
}

async function deleteNote(noteId, companyId) {
    await safeFetch(`/api/notes/${noteId}`, { method: 'DELETE' });
    showDetail(companyId);
}

async function togglePinNote(noteId, companyId) {
    await safeFetch(`/api/notes/${noteId}/pin`, { method: 'POST' });
    showDetail(companyId);
}

// --- Events ---
function showAddEvent(companyId) {
    document.getElementById(`addEventForm-${companyId}`).classList.remove('hidden');
}

async function addEvent(companyId) {
    const event_type = document.getElementById(`newEventType-${companyId}`).value;
    const description = document.getElementById(`newEventDesc-${companyId}`).value.trim();
    const event_date = document.getElementById(`newEventDate-${companyId}`).value || null;
    await safeFetch(`/api/companies/${companyId}/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_type, description, event_date }),
    });
    showDetail(companyId);
}

async function deleteEvent(eventId, companyId) {
    await safeFetch(`/api/events/${eventId}`, { method: 'DELETE' });
    showDetail(companyId);
}

// --- Version History ---
async function showVersionHistory(companyId) {
    const res = await safeFetch(`/api/companies/${companyId}/versions`);
    const versions = await res.json();

    let html = '<div class="version-history"><h3>Version History</h3>';
    if (!versions.length) {
        html += '<p style="font-size:13px;color:var(--text-muted)">No version history yet. Versions are created automatically when you edit a company.</p>';
    } else {
        html += versions.map(v => `
            <div class="version-item">
                <div class="version-meta">
                    <span class="version-desc">${esc(v.change_description || 'Edit')}</span>
                    <span class="version-date">${new Date(v.created_at).toLocaleString()}</span>
                </div>
                <button class="filter-action-btn" onclick="restoreVersion(${v.id},${companyId})">Restore</button>
            </div>
        `).join('');
    }
    html += '<button class="btn" onclick="showDetail(' + companyId + ')" style="margin-top:10px">Back</button></div>';
    document.getElementById('detailContent').innerHTML = html;
}

async function restoreVersion(versionId, companyId) {
    if (!confirm('Restore this version? Current state will be saved as a version first.')) return;
    await safeFetch(`/api/versions/${versionId}/restore`, { method: 'POST' });
    showDetail(companyId);
    loadCompanies();
}

// --- Sort Headers ---
document.addEventListener('click', (e) => {
    const th = e.target.closest('.sort-header');
    if (!th) return;
    const sortKey = th.dataset.sort;
    if (currentSort.by === sortKey) {
        currentSort.dir = currentSort.dir === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.by = sortKey;
        currentSort.dir = 'asc';
    }
    loadCompanies();
});
