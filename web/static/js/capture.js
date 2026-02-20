/**
 * Capture UI — evidence management and capture controls.
 * Phase 2.7 of the Research Workbench.
 *
 * Sub-section within the Process tab. Shows evidence stats,
 * entity evidence list, capture triggers, upload, and job progress.
 */

// Capture state
let _captureStats = null;
let _captureJobs = [];
let _bulkCaptureJobId = null;
let _bulkCapturePolling = false;

/**
 * Initialize capture section — called when Process tab shown.
 */
async function initCaptureUI() {
    if (!currentProjectId) return;
    await Promise.all([
        _loadCaptureStats(),
        _loadCaptureJobs(),
    ]);
    // Resume polling if a bulk job is in progress
    if (_bulkCaptureJobId) {
        _pollBulkCapture();
    }
}

// ── Evidence Stats ───────────────────────────────────────────

async function _loadCaptureStats() {
    if (!currentProjectId) return;
    try {
        const resp = await fetch(`/api/evidence/stats?project_id=${currentProjectId}`, {
            headers: { 'X-CSRFToken': CSRF_TOKEN },
        });
        if (!resp.ok) return;
        _captureStats = await resp.json();
        _renderCaptureStats();
    } catch (e) {
        console.warn('Failed to load capture stats:', e);
    }
}

function _renderCaptureStats() {
    const el = document.getElementById('captureStats');
    if (!el || !_captureStats) return;

    const total = _captureStats.total_count || 0;
    const sizeMb = _captureStats.total_size_mb || 0;
    const byType = _captureStats.by_type || {};

    el.innerHTML = `
        <div class="cap-stat-row">
            <div class="cap-stat">
                <span class="cap-stat-value">${total}</span>
                <span class="cap-stat-label">Evidence Files</span>
            </div>
            <div class="cap-stat">
                <span class="cap-stat-value">${sizeMb}</span>
                <span class="cap-stat-label">MB Stored</span>
            </div>
            ${Object.entries(byType).map(([type, data]) => `
                <div class="cap-stat">
                    <span class="cap-stat-value">${data.count}</span>
                    <span class="cap-stat-label">${type}</span>
                </div>
            `).join('')}
        </div>
    `;
}

// ── Capture Jobs ─────────────────────────────────────────────

async function _loadCaptureJobs() {
    try {
        const resp = await fetch('/api/capture/jobs', {
            headers: { 'X-CSRFToken': CSRF_TOKEN },
        });
        if (!resp.ok) return;
        _captureJobs = await resp.json();
        _renderCaptureJobs();
    } catch (e) {
        console.warn('Failed to load capture jobs:', e);
    }
}

function _renderCaptureJobs() {
    const el = document.getElementById('captureJobsList');
    if (!el) return;

    if (!_captureJobs.length) {
        el.innerHTML = '<div class="cap-no-jobs">No recent capture jobs</div>';
        return;
    }

    // Show most recent 20 jobs
    const recent = _captureJobs.slice(0, 20);
    el.innerHTML = recent.map(j => `
        <div class="cap-job-row cap-job-${j.status}">
            <span class="cap-job-type">${esc(j.type || 'capture')}</span>
            <span class="cap-job-url" title="${escAttr(j.url || '')}">${esc(_truncateCaptureUrl(j.url || ''))}</span>
            <span class="cap-job-status">${j.status}</span>
        </div>
    `).join('');
}

function _truncateCaptureUrl(url) {
    if (!url || url.length <= 50) return url;
    try {
        const u = new URL(url);
        return u.hostname + u.pathname.substring(0, 30) + '...';
    } catch {
        return url.substring(0, 47) + '...';
    }
}

// ── Single Capture ───────────────────────────────────────────

async function captureEntityUrl() {
    if (!currentProjectId) return;

    const url = await showPromptDialog(
        'Capture URL',
        'Enter URL to capture (screenshot + HTML):',
        '',
    );
    if (!url || !url.trim()) return;

    // Get entity to link to
    const entities = await _getProjectEntities();
    if (!entities.length) {
        if (window.notyf) window.notyf.error('No entities in project — create one first');
        return;
    }

    const options = entities.map(e => ({
        value: String(e.id),
        label: e.name,
    }));

    const entityId = await showSelectDialog(
        'Link to Entity',
        'Which entity should this evidence be linked to?',
        options,
    );
    if (!entityId) return;

    try {
        const resp = await fetch('/api/capture/website', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN,
            },
            body: JSON.stringify({
                url: url.trim(),
                entity_id: parseInt(entityId),
                project_id: currentProjectId,
                async: true,
            }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            if (window.notyf) window.notyf.error(err.error || 'Capture failed');
            return;
        }
        const data = await resp.json();
        if (window.notyf) window.notyf.success('Capture started');
        // Reload jobs
        setTimeout(() => _loadCaptureJobs(), 1000);
        setTimeout(() => { _loadCaptureJobs(); _loadCaptureStats(); }, 5000);
    } catch (e) {
        console.error('Capture failed:', e);
        if (window.notyf) window.notyf.error('Capture failed');
    }
}

// ── Bulk Capture ─────────────────────────────────────────────

async function bulkCaptureStart() {
    if (!currentProjectId) return;

    const urlsInput = await showPromptDialog(
        'Bulk Capture',
        'Enter URLs to capture (one per line).\nEach URL will be captured as screenshot + HTML.',
        '',
    );
    if (!urlsInput || !urlsInput.trim()) return;

    const urls = urlsInput.split('\n')
        .map(u => u.trim())
        .filter(u => u && (u.startsWith('http://') || u.startsWith('https://')));

    if (!urls.length) {
        if (window.notyf) window.notyf.error('No valid URLs found');
        return;
    }

    // Get entity to link to (all URLs go to the same entity for bulk)
    const entities = await _getProjectEntities();
    if (!entities.length) {
        if (window.notyf) window.notyf.error('No entities in project — create one first');
        return;
    }

    const options = entities.map(e => ({
        value: String(e.id),
        label: e.name,
    }));

    const entityId = await showSelectDialog(
        'Link Evidence to Entity',
        `Capture ${urls.length} URLs. Link evidence to which entity?`,
        options,
    );
    if (!entityId) return;

    const items = urls.map(url => ({
        url,
        entity_id: parseInt(entityId),
        capture_type: 'website',
    }));

    try {
        const resp = await fetch('/api/capture/bulk', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN,
            },
            body: JSON.stringify({
                project_id: currentProjectId,
                items,
            }),
        });
        if (!resp.ok) {
            const err = await resp.json();
            if (window.notyf) window.notyf.error(err.error || 'Bulk capture failed');
            return;
        }
        const data = await resp.json();
        _bulkCaptureJobId = data.job_id;
        if (window.notyf) window.notyf.success(`Bulk capture started: ${urls.length} URLs`);
        _renderBulkProgress({ status: 'running', total: urls.length, completed: 0, succeeded: 0, failed: 0 });
        _pollBulkCapture();
    } catch (e) {
        console.error('Bulk capture failed:', e);
        if (window.notyf) window.notyf.error('Bulk capture failed');
    }
}

function _pollBulkCapture() {
    if (!_bulkCaptureJobId || _bulkCapturePolling) return;
    _bulkCapturePolling = true;

    const interval = setInterval(async () => {
        try {
            const resp = await fetch(`/api/capture/bulk/${_bulkCaptureJobId}`, {
                headers: { 'X-CSRFToken': CSRF_TOKEN },
            });
            if (!resp.ok) {
                clearInterval(interval);
                _bulkCapturePolling = false;
                return;
            }
            const data = await resp.json();
            _renderBulkProgress(data);

            if (data.status === 'complete' || data.status === 'error') {
                clearInterval(interval);
                _bulkCapturePolling = false;
                _bulkCaptureJobId = null;
                _loadCaptureStats();
                _loadCaptureJobs();
                if (data.status === 'complete') {
                    if (window.notyf) window.notyf.success(`Bulk capture done: ${data.succeeded}/${data.total} succeeded`);
                }
            }
        } catch (e) {
            console.warn('Bulk poll failed:', e);
        }
    }, 3000);
}

function _renderBulkProgress(data) {
    const el = document.getElementById('captureBulkProgress');
    if (!el) return;

    if (!data || data.status === 'pending') {
        el.innerHTML = '';
        return;
    }

    const total = data.total || 0;
    const completed = data.completed || 0;
    const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
    const isDone = data.status === 'complete';

    el.innerHTML = `
        <div class="cap-bulk-progress">
            <div class="cap-bulk-bar">
                <div class="cap-bulk-fill" style="width: ${pct}%"></div>
            </div>
            <div class="cap-bulk-info">
                <span>${completed}/${total} captured</span>
                <span>${data.succeeded || 0} succeeded, ${data.failed || 0} failed</span>
                ${isDone ? '<span class="cap-bulk-done">Complete</span>' : '<span class="cap-bulk-running">Running...</span>'}
            </div>
        </div>
    `;
}

// ── Upload ───────────────────────────────────────────────────

async function uploadEvidence() {
    if (!currentProjectId) return;

    // Get entity
    const entities = await _getProjectEntities();
    if (!entities.length) {
        if (window.notyf) window.notyf.error('No entities in project — create one first');
        return;
    }

    const options = entities.map(e => ({
        value: String(e.id),
        label: e.name,
    }));

    const entityId = await showSelectDialog(
        'Upload Evidence',
        'Which entity should this file be linked to?',
        options,
    );
    if (!entityId) return;

    // Create hidden file input and trigger click
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.png,.jpg,.jpeg,.gif,.webp,.svg,.pdf,.doc,.docx,.xls,.xlsx,.html,.htm,.mp4,.mov,.webm,.json,.csv,.txt,.md';
    input.multiple = true;

    input.onchange = async () => {
        if (!input.files.length) return;

        for (const file of input.files) {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('entity_id', entityId);
            formData.append('project_id', String(currentProjectId));

            try {
                const resp = await fetch('/api/evidence/upload', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': CSRF_TOKEN },
                    body: formData,
                });
                if (resp.ok) {
                    if (window.notyf) window.notyf.success(`Uploaded "${file.name}"`);
                } else {
                    const err = await resp.json();
                    if (window.notyf) window.notyf.error(err.error || `Upload failed: ${file.name}`);
                }
            } catch (e) {
                console.error('Upload failed:', e);
                if (window.notyf) window.notyf.error(`Upload failed: ${file.name}`);
            }
        }
        _loadCaptureStats();
    };

    input.click();
}

// ── Helpers ──────────────────────────────────────────────────

async function _getProjectEntities() {
    if (!currentProjectId) return [];
    try {
        const resp = await fetch(`/api/entities?project_id=${currentProjectId}&limit=200`, {
            headers: { 'X-CSRFToken': CSRF_TOKEN },
        });
        if (!resp.ok) return [];
        const data = await resp.json();
        return data.entities || data || [];
    } catch {
        return [];
    }
}

// Make functions globally accessible
window.initCaptureUI = initCaptureUI;
window.captureEntityUrl = captureEntityUrl;
window.bulkCaptureStart = bulkCaptureStart;
window.uploadEvidence = uploadEvidence;
