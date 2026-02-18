/**
 * Trash, CSV import, duplicates, merge, XLSX export, PDF export.
 */

// --- Trash ---
async function loadTrash() {
    const container = document.getElementById('trashList');
    container.classList.remove('hidden');
    const res = await safeFetch(`/api/trash?project_id=${currentProjectId}`);
    const items = await res.json();

    if (!items.length) {
        container.innerHTML = '<p style="padding:12px;color:var(--text-muted)">Trash is empty.</p>';
        return;
    }

    container.innerHTML = items.map(c => `
        <div class="trash-item">
            <div>
                <strong>${esc(c.name)}</strong>
                <span style="color:var(--text-muted);font-size:12px;margin-left:8px">Deleted ${new Date(c.deleted_at).toLocaleDateString()}</span>
            </div>
            <div style="display:flex;gap:6px">
                <button class="btn" onclick="restoreFromTrash(${c.id})">Restore</button>
                <button class="danger-btn" onclick="permanentDelete(${c.id})">Delete forever</button>
            </div>
        </div>
    `).join('');
}

async function restoreFromTrash(id) {
    await safeFetch(`/api/companies/${id}/restore`, { method: 'POST' });
    loadTrash();
    loadCompanies();
    loadStats();
}

async function permanentDelete(id) {
    if (!confirm('Permanently delete? This cannot be undone.')) return;
    await safeFetch(`/api/companies/${id}/permanent-delete`, { method: 'DELETE' });
    loadTrash();
}

// --- CSV Import ---
async function importCsv(event) {
    event.preventDefault();
    const file = document.getElementById('csvFile').files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', currentProjectId);

    const res = await safeFetch('/api/import/csv', { method: 'POST', body: formData });
    const data = await res.json();

    const resultDiv = document.getElementById('importResult');
    resultDiv.classList.remove('hidden');
    if (data.error) {
        resultDiv.innerHTML = `<p class="re-research-error">${esc(data.error)}</p>`;
    } else {
        resultDiv.innerHTML = `<p class="re-research-success">Imported ${data.imported} of ${data.total_rows} rows.</p>`;
        loadCompanies();
        loadStats();
    }
}

// --- Duplicates ---
async function findDuplicates() {
    const container = document.getElementById('duplicatesList');
    container.classList.remove('hidden');
    container.innerHTML = '<p>Scanning...</p>';
    const res = await safeFetch(`/api/duplicates?project_id=${currentProjectId}`);
    const dupes = await res.json();

    if (!dupes.length) {
        container.innerHTML = '<p style="padding:12px;color:var(--text-muted)">No duplicates found.</p>';
        return;
    }

    container.innerHTML = dupes.map(d => `
        <div class="duplicate-group">
            <div class="duplicate-header">URL match: ${esc(d.key)}</div>
            ${d.companies.map(c => `
                <div class="duplicate-item">
                    <span>${esc(c.name)}</span>
                    <a href="${esc(c.url)}" target="_blank" style="font-size:12px">${esc(c.url)}</a>
                </div>
            `).join('')}
            ${d.companies.length === 2 ? `
                <button class="filter-action-btn" onclick="mergeCompanies(${d.companies[0].id},${d.companies[1].id})">
                    Merge "${esc(d.companies[1].name)}" into "${esc(d.companies[0].name)}"
                </button>
            ` : ''}
        </div>
    `).join('');
}

async function mergeCompanies(targetId, sourceId) {
    if (!confirm('Merge these companies? The source will be moved to trash.')) return;
    await safeFetch('/api/companies/merge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_id: targetId, source_id: sourceId }),
    });
    findDuplicates();
    loadCompanies();
    loadStats();
}

// --- SheetJS (Excel Export) ---
async function exportXlsx() {
    if (!window.XLSX) { showToast('Excel library still loading...'); return; }

    const [compRes, taxRes] = await Promise.all([
        safeFetch(`/api/companies?project_id=${currentProjectId}`),
        safeFetch(`/api/taxonomy?project_id=${currentProjectId}`),
    ]);
    const companies = await compRes.json();
    const categories = await taxRes.json();
    const topCats = categories.filter(c => !c.parent_id);

    const wb = XLSX.utils.book_new();

    const allData = companies.map(c => ({
        Name: c.name,
        URL: c.url,
        Category: c.category_name || '',
        What: c.what || '',
        Target: c.target || '',
        Products: c.products || '',
        Geography: c.geography || '',
        'HQ City': c.hq_city || '',
        'HQ Country': c.hq_country || '',
        'Funding Stage': c.funding_stage || '',
        'Total Funding': c.total_funding_usd || '',
        'Business Model': c.business_model || '',
        Employees: c.employee_range || '',
        'Founded Year': c.founded_year || '',
        Confidence: c.confidence_score ? Math.round(c.confidence_score * 100) + '%' : '',
        Tags: (c.tags || []).join(', '),
        Starred: c.is_starred ? 'Yes' : '',
    }));
    const wsAll = XLSX.utils.json_to_sheet(allData);
    wsAll['!cols'] = [
        {wch:25},{wch:35},{wch:20},{wch:40},{wch:20},{wch:30},
        {wch:15},{wch:15},{wch:15},{wch:12},{wch:15},{wch:10},
        {wch:10},{wch:10},{wch:10},{wch:20},{wch:6},
    ];
    XLSX.utils.book_append_sheet(wb, wsAll, 'All Companies');

    topCats.forEach(cat => {
        const catCompanies = companies.filter(c => c.category_name === cat.name);
        if (!catCompanies.length) return;
        const data = catCompanies.map(c => ({
            Name: c.name, URL: c.url, What: c.what || '',
            Target: c.target || '', Geography: c.geography || '',
            Stage: c.funding_stage || '', Confidence: c.confidence_score ? Math.round(c.confidence_score*100)+'%' : '',
        }));
        const ws = XLSX.utils.json_to_sheet(data);
        const sheetName = cat.name.substring(0, 31);
        XLSX.utils.book_append_sheet(wb, ws, sheetName);
    });

    XLSX.writeFile(wb, `taxonomy-${formatDate(new Date().toISOString()).replace(/\s/g,'-')}.xlsx`);
    if (notyf) notyf.success('Excel workbook exported!');
}

// --- pdfmake (PDF Export) ---
function exportReportPdfPdfmake() {
    if (!window.pdfMake) {
        exportReportPdf();
        return;
    }
    const reportBody = document.querySelector('#reportContent .report-body');
    if (!reportBody) return;

    const title = document.querySelector('#reportContent .report-header h3')?.textContent || 'Market Report';
    const text = reportBody.innerText;
    const lines = text.split('\n').filter(l => l.trim());

    const content = [
        { text: title, style: 'header', margin: [0, 0, 0, 12] },
        { text: `Generated ${formatDate(new Date().toISOString())}`, style: 'subheader', margin: [0, 0, 0, 20] },
    ];

    lines.forEach(line => {
        if (line.startsWith('##')) {
            content.push({ text: line.replace(/^#+\s*/, ''), style: 'sectionHeader', margin: [0, 12, 0, 6] });
        } else if (line.startsWith('- ') || line.startsWith('* ')) {
            content.push({ text: line, margin: [10, 2, 0, 2], fontSize: 10 });
        } else {
            content.push({ text: line, margin: [0, 2, 0, 2], fontSize: 10 });
        }
    });

    pdfMake.createPdf({
        content,
        defaultStyle: { font: 'Roboto', fontSize: 10, lineHeight: 1.4 },
        styles: {
            header: { fontSize: 18, bold: true, color: '#3D4035' },
            subheader: { fontSize: 11, color: '#888' },
            sectionHeader: { fontSize: 14, bold: true, color: '#bc6c5a' },
        },
    }).download(`${title.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`);
}

// Full project PDF export
async function exportFullPdf() {
    if (!window.pdfMake) { showToast('PDF library still loading...'); return; }

    const [compRes, taxRes] = await Promise.all([
        safeFetch(`/api/companies?project_id=${currentProjectId}`),
        safeFetch(`/api/taxonomy?project_id=${currentProjectId}`),
    ]);
    const companies = await compRes.json();
    const categories = await taxRes.json();
    const topCats = categories.filter(c => !c.parent_id);

    const content = [
        { text: document.getElementById('projectTitle').textContent, style: 'header' },
        { text: `${companies.length} companies across ${topCats.length} categories`, style: 'subheader', margin: [0, 0, 0, 20] },
    ];

    const tableBody = [['Name', 'Category', 'What', 'Geography', 'Stage']];
    companies.forEach(c => {
        tableBody.push([
            c.name || '',
            c.category_name || '',
            (c.what || '').substring(0, 80),
            c.geography || '',
            c.funding_stage || '',
        ]);
    });

    content.push({
        table: { headerRows: 1, widths: ['auto', 'auto', '*', 'auto', 'auto'], body: tableBody },
        layout: 'lightHorizontalLines',
        fontSize: 8,
    });

    pdfMake.createPdf({
        content,
        defaultStyle: { font: 'Roboto', fontSize: 9 },
        styles: {
            header: { fontSize: 20, bold: true },
            subheader: { fontSize: 12, color: '#666' },
        },
        pageOrientation: 'landscape',
    }).download('taxonomy-export.pdf');

    if (notyf) notyf.success('PDF exported!');
}
