/**
 * Share tokens, notification preferences, and activity log.
 */

// --- Share Tokens ---
async function createShareLink() {
    const label = document.getElementById('shareLinkLabel').value.trim() || 'Shared link';
    const res = await safeFetch('/api/share-tokens', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: currentProjectId, label }),
    });
    const data = await res.json();
    document.getElementById('shareLinkLabel').value = '';
    showUndoToast(`Share link created: ${data.url}`, null);
    loadShareTokens();
}

async function loadShareTokens() {
    const res = await safeFetch(`/api/share-tokens?project_id=${currentProjectId}`);
    const tokens = await res.json();
    const container = document.getElementById('shareTokensList');
    if (!tokens.length) {
        container.innerHTML = '<p style="font-size:13px;color:var(--text-muted);margin-top:8px">No share links yet.</p>';
        return;
    }
    container.innerHTML = tokens.map(t => `
        <div class="share-token-item ${t.is_active ? '' : 'share-revoked'}">
            <div>
                <strong>${esc(t.label)}</strong>
                <code class="share-url">${location.origin}/shared/${esc(t.token)}</code>
                <button class="copy-btn" onclick="navigator.clipboard.writeText('${location.origin}/shared/${esc(t.token)}');this.textContent='Copied!';setTimeout(()=>this.textContent='Copy',1500)">Copy</button>
            </div>
            ${t.is_active ? `<button class="danger-btn" onclick="revokeShareToken(${t.id})" style="font-size:11px;padding:2px 8px">Revoke</button>` : '<span class="share-revoked-label">Revoked</span>'}
        </div>
    `).join('');
}

async function revokeShareToken(tokenId) {
    await safeFetch(`/api/share-tokens/${tokenId}`, { method: 'DELETE' });
    loadShareTokens();
}

// --- Notification Prefs ---
async function loadNotifPrefs() {
    const res = await safeFetch(`/api/notification-prefs?project_id=${currentProjectId}`);
    const prefs = await res.json();
    document.getElementById('slackWebhook').value = prefs.slack_webhook_url || '';
    document.getElementById('notifBatchComplete').checked = !!prefs.notify_batch_complete;
    document.getElementById('notifTaxonomyChange').checked = !!prefs.notify_taxonomy_change;
    document.getElementById('notifNewCompany').checked = !!prefs.notify_new_company;
}

async function saveNotifPrefs() {
    const res = await safeFetch('/api/notification-prefs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            project_id: currentProjectId,
            slack_webhook_url: document.getElementById('slackWebhook').value.trim() || null,
            notify_batch_complete: document.getElementById('notifBatchComplete').checked ? 1 : 0,
            notify_taxonomy_change: document.getElementById('notifTaxonomyChange').checked ? 1 : 0,
            notify_new_company: document.getElementById('notifNewCompany').checked ? 1 : 0,
        }),
    });
    const resultDiv = document.getElementById('notifSaveResult');
    resultDiv.classList.remove('hidden');
    resultDiv.innerHTML = '<p class="re-research-success">Preferences saved.</p>';
    setTimeout(() => resultDiv.classList.add('hidden'), 3000);
}

async function testSlack() {
    const url = document.getElementById('slackWebhook').value.trim();
    if (!url) { showToast('Enter a Slack webhook URL first'); return; }
    const res = await safeFetch('/api/notification-prefs/test-slack', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slack_webhook_url: url }),
    });
    const data = await res.json();
    if (data.ok) showToast('Test message sent!');
    else showToast('Error: ' + (data.error || 'Unknown'));
}

// --- Activity Log ---
async function loadActivity() {
    const container = document.getElementById('activityFeed');
    container.classList.remove('hidden');
    container.innerHTML = '<p>Loading...</p>';
    const res = await safeFetch(`/api/activity?project_id=${currentProjectId}&limit=50`);
    const events = await res.json();

    if (!events.length) {
        container.innerHTML = '<p style="color:var(--text-muted);font-size:13px">No activity recorded yet.</p>';
        return;
    }

    container.innerHTML = events.map(e => `
        <div class="activity-item">
            <span class="activity-action-badge">${esc(e.action)}</span>
            <span>${esc(e.description || '')}</span>
            <span class="activity-time">${new Date(e.created_at).toLocaleString()}</span>
        </div>
    `).join('');
}
