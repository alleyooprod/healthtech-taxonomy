/**
 * AI discovery, find similar, and chat widget.
 */

let chatOpen = false;

// --- AI Discovery ---
async function startDiscovery() {
    const query = document.getElementById('discoveryQuery').value.trim();
    if (!query) { showToast('Enter a market segment description'); return; }

    if (!acquireAiLock('discovery')) {
        showToast(`Another AI task is running (${aiLock}). Please wait for it to finish.`);
        return;
    }

    const btn = document.getElementById('discoveryBtn');
    btn.disabled = true;
    btn.textContent = 'Searching...';

    document.getElementById('discoveryResults').classList.remove('hidden');
    document.getElementById('discoveryStatus').classList.remove('hidden');
    document.getElementById('discoveryList').innerHTML = '';

    const res = await safeFetch('/api/ai/discover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, project_id: currentProjectId, model: document.getElementById('discoveryModelSelect').value }),
    });
    const data = await res.json();
    pollDiscovery(data.discover_id);
}

let _discoveryPollCount = 0;
const _MAX_DISCOVERY_RETRIES = 60; // 3 minutes at 3s intervals

async function pollDiscovery(discoverId) {
    const res = await safeFetch(`/api/ai/discover/${discoverId}`);
    const data = await res.json();

    if (data.status === 'pending') {
        if (++_discoveryPollCount > _MAX_DISCOVERY_RETRIES) {
            data.status = 'error';
            data.error = 'Discovery timed out. Please try again.';
        } else {
            setTimeout(() => pollDiscovery(discoverId), 3000);
            return;
        }
    }
    _discoveryPollCount = 0;

    releaseAiLock();
    const btn = document.getElementById('discoveryBtn');
    btn.disabled = false;
    btn.textContent = 'Discover';
    document.getElementById('discoveryStatus').classList.add('hidden');

    if (data.status === 'error') {
        document.getElementById('discoveryList').innerHTML = `<p class="re-research-error">${esc(data.error)}</p>`;
        return;
    }

    const companies = data.companies || [];
    if (!companies.length) {
        document.getElementById('discoveryList').innerHTML = '<p class="hint-text">No companies found. Try a different description.</p>';
        return;
    }

    document.getElementById('discoveryList').innerHTML = `
        <p class="hint-text">Found ${companies.length} companies. Select ones to add to your URL processing queue.</p>
        ${companies.map((c, i) => `
            <div class="discovery-result">
                <label>
                    <input type="checkbox" name="discovery_company" value="${esc(c.url)}" checked>
                    <strong>${esc(c.name)}</strong>
                </label>
                <a href="${esc(c.url)}" target="_blank" class="discovery-url">${esc(c.url)}</a>
                <p class="discovery-desc">${esc(c.description || '')}</p>
            </div>
        `).join('')}
        <button class="primary-btn" onclick="addDiscoveredUrls()" style="margin-top:10px">Add selected to URL input</button>
    `;
}

function addDiscoveredUrls() {
    const checked = document.querySelectorAll('input[name="discovery_company"]:checked');
    const urls = Array.from(checked).map(cb => cb.value);
    if (!urls.length) { showToast('Select at least one company'); return; }

    const urlInput = document.getElementById('urlInput');
    const existing = urlInput.value.trim();
    urlInput.value = (existing ? existing + '\n' : '') + urls.join('\n');
    document.getElementById('discoveryResults').classList.add('hidden');
    showUndoToast(`Added ${urls.length} URLs to queue`, null);
}

// --- AI Find Similar ---
async function findSimilar(companyId) {
    const container = document.getElementById(`similarResults-${companyId}`);
    container.classList.remove('hidden');
    container.innerHTML = '<div class="progress-bar"><div class="progress-fill" style="width:50%;animation:pulse 2s infinite"></div></div><p style="font-size:13px">Finding similar companies...</p>';

    const res = await safeFetch('/api/ai/find-similar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_id: companyId, model: document.getElementById('modelSelect').value }),
    });
    const data = await res.json();
    pollSimilar(data.similar_id, companyId);
}

let _similarPollCount = 0;
const _MAX_SIMILAR_RETRIES = 60;

async function pollSimilar(similarId, companyId) {
    const res = await safeFetch(`/api/ai/find-similar/${similarId}`);
    const data = await res.json();

    if (data.status === 'pending') {
        if (++_similarPollCount > _MAX_SIMILAR_RETRIES) {
            data.status = 'error';
            data.error = 'Search timed out. Please try again.';
        } else {
            setTimeout(() => pollSimilar(similarId, companyId), 3000);
            return;
        }
    }
    _similarPollCount = 0;

    const container = document.getElementById(`similarResults-${companyId}`);
    if (data.status === 'error') {
        container.innerHTML = `<p class="re-research-error">${esc(data.error)}</p>`;
        return;
    }

    const companies = data.companies || [];
    if (!companies.length) {
        container.innerHTML = '<p class="hint-text">No similar companies found.</p>';
        return;
    }

    container.innerHTML = `
        <h4>Similar Companies</h4>
        ${companies.map(c => `
            <div class="similar-item">
                <div class="similar-item-header">
                    <strong>${esc(c.name)}</strong>
                    <a href="${esc(c.url)}" target="_blank">${esc(c.url)}</a>
                </div>
                <p class="similar-desc">${esc(c.description || '')}</p>
                ${c.similarity ? `<p class="similar-reason">${esc(c.similarity)}</p>` : ''}
            </div>
        `).join('')}
        <button class="btn" onclick="addSimilarToQueue()" style="margin-top:8px">Add all to URL queue</button>
    `;

    container.dataset.urls = JSON.stringify(companies.map(c => c.url));
}

function addSimilarToQueue() {
    const containers = document.querySelectorAll('.similar-results');
    let urls = [];
    containers.forEach(c => {
        if (c.dataset.urls) urls = urls.concat(JSON.parse(c.dataset.urls));
    });
    if (!urls.length) return;
    showTab('process');
    const urlInput = document.getElementById('urlInput');
    const existing = urlInput.value.trim();
    urlInput.value = (existing ? existing + '\n' : '') + urls.join('\n');
}

// --- AI Chat ---
function toggleChat() {
    const widget = document.getElementById('chatWidget');
    if (chatOpen) {
        closeChat();
    } else {
        widget.classList.remove('hidden');
        chatOpen = true;
        document.getElementById('chatInput').focus();
    }
}

function closeChat() {
    document.getElementById('chatWidget').classList.add('hidden');
    chatOpen = false;
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const question = input.value.trim();
    if (!question) return;

    if (!acquireAiLock('chat')) {
        const body = document.getElementById('chatBody');
        body.innerHTML += `<div class="chat-msg chat-assistant"><em>Another AI task is running (${esc(aiLock)}). Please wait for it to finish.</em></div>`;
        body.scrollTop = body.scrollHeight;
        return;
    }

    const body = document.getElementById('chatBody');
    // Cap chat history at 100 messages to prevent unbounded DOM growth
    const msgs = body.querySelectorAll('.chat-msg');
    if (msgs.length > 98) {
        // Remove oldest messages (keep last 98, about to add 2 more)
        for (let i = 0; i < msgs.length - 98; i++) msgs[i].remove();
    }
    body.innerHTML += `<div class="chat-msg chat-user">${esc(question)}</div>`;
    body.innerHTML += `<div class="chat-msg chat-assistant" id="chatPending"><em>Thinking...</em></div>`;
    body.scrollTop = body.scrollHeight;
    input.value = '';

    try {
        const res = await safeFetch('/api/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, project_id: currentProjectId, model: 'claude-haiku-4-5-20251001' }),
        });
        const data = await res.json();
        const pending = document.getElementById('chatPending');
        if (pending) {
            if (data.error) {
                pending.innerHTML = `<span class="re-research-error">${esc(data.error)}</span>`;
            } else {
                const answer = data.answer || 'No answer';
                if (window.marked) {
                    pending.innerHTML = sanitize(marked.parse(answer, { breaks: true, gfm: true }));
                } else {
                    pending.innerHTML = esc(answer).replace(/\n/g, '<br>');
                }
            }
            pending.removeAttribute('id');
        }
    } catch (err) {
        const pending = document.getElementById('chatPending');
        if (pending) {
            pending.innerHTML = `<span class="re-research-error">Error: ${esc(err.message)}</span>`;
            pending.removeAttribute('id');
        }
    }
    releaseAiLock();
    body.scrollTop = body.scrollHeight;
}
