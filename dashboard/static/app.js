/**
 * PyFleet Dashboard - Frontend JavaScript
 */

// State
let agents = [];
let socket = null;

// Elements
const elements = {
    statTotal: document.getElementById('statTotal'),
    statOnline: document.getElementById('statOnline'),
    statDegraded: document.getElementById('statDegraded'),
    statOffline: document.getElementById('statOffline'),
    agentsTableBody: document.getElementById('agentsTableBody'),
    activityFeed: document.getElementById('activityFeed'),
    searchInput: document.getElementById('searchInput'),
    clearActivity: document.getElementById('clearActivity'),
    agentModal: document.getElementById('agentModal'),
    modalTitle: document.getElementById('modalTitle'),
    modalBody: document.getElementById('modalBody'),
    modalClose: document.getElementById('modalClose'),
    serverStatus: document.getElementById('serverStatus'),
};

// Icons for activity types
const activityIcons = {
    enrollment: '+',
    status_change: '~',
    message: '>',
    broadcast: '!',
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initWebSocket();
    fetchAgents();
    fetchEvents();
    setupEventListeners();

    // Refresh periodically as backup
    setInterval(fetchAgents, 10000);
});

// WebSocket connection
function initWebSocket() {
    socket = io();

    socket.on('connect', () => {
        console.log('WebSocket connected');
    });

    socket.on('agents_update', (data) => {
        agents = data.agents || [];
        updateStats(data.stats);
        renderAgentsTable();
    });

    socket.on('event', (event) => {
        addActivityItem(event);
    });

    socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
    });
}

// Fetch agents from API
async function fetchAgents() {
    try {
        const res = await fetch('/api/agents');
        agents = await res.json();
        renderAgentsTable();

        // Also fetch stats
        const statsRes = await fetch('/api/stats');
        const stats = await statsRes.json();
        updateStats(stats);
    } catch (e) {
        console.error('Fetch agents error:', e);
    }
}

// Fetch events from API
async function fetchEvents() {
    try {
        const res = await fetch('/api/events');
        const events = await res.json();
        events.forEach(event => addActivityItem(event, false));
    } catch (e) {
        console.error('Fetch events error:', e);
    }
}

// Update stats display
function updateStats(stats) {
    if (!stats) return;
    elements.statTotal.textContent = stats.total || 0;
    elements.statOnline.textContent = stats.online || 0;
    elements.statDegraded.textContent = stats.degraded || 0;
    elements.statOffline.textContent = stats.offline || 0;
}

// Render agents table
function renderAgentsTable() {
    const search = elements.searchInput?.value.toLowerCase() || '';
    const filtered = agents.filter(a =>
        a.hostname?.toLowerCase().includes(search) ||
        a.client_id?.toLowerCase().includes(search) ||
        a.os_type?.toLowerCase().includes(search)
    );

    if (filtered.length === 0) {
        elements.agentsTableBody.innerHTML = `
            <tr class="empty-row">
                <td colspan="6">${agents.length === 0 ? 'No agents connected' : 'No matching agents'}</td>
            </tr>
        `;
        return;
    }

    elements.agentsTableBody.innerHTML = filtered.map(agent => `
        <tr data-id="${agent.client_id}" onclick="showAgentDetail('${agent.client_id}')">
            <td>
                <span class="status-dot ${agent.status}"></span>
                ${agent.status}
            </td>
            <td>${escapeHtml(agent.hostname)}</td>
            <td>${escapeHtml(agent.os_type)} ${escapeHtml(agent.os_version)}</td>
            <td>${escapeHtml(agent.agent_version)}</td>
            <td>${formatTime(agent.last_seen)}</td>
            <td>${(agent.tags || []).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}</td>
        </tr>
    `).join('');
}

// Add activity item
function addActivityItem(event, prepend = true) {
    // Remove empty message if present
    const emptyMsg = elements.activityFeed.querySelector('.activity-empty');
    if (emptyMsg) emptyMsg.remove();

    const icon = activityIcons[event.type] || '*';
    const item = document.createElement('div');
    item.className = `activity-item ${event.type}`;
    item.innerHTML = `
        <span class="activity-icon">${icon}</span>
        <div class="activity-content">
            <div class="activity-message">${escapeHtml(event.message)}</div>
            <div class="activity-time">${formatTime(event.timestamp)}</div>
        </div>
    `;

    if (prepend) {
        elements.activityFeed.prepend(item);
    } else {
        elements.activityFeed.appendChild(item);
    }

    // Limit items
    while (elements.activityFeed.children.length > 50) {
        elements.activityFeed.lastChild.remove();
    }
}

// Show agent detail modal
function showAgentDetail(clientId) {
    const agent = agents.find(a => a.client_id === clientId);
    if (!agent) return;

    elements.modalTitle.textContent = agent.hostname;
    elements.modalBody.innerHTML = `
        <div class="detail-row">
            <span class="detail-label">Client ID</span>
            <span class="detail-value"><code>${escapeHtml(agent.client_id)}</code></span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Status</span>
            <span class="detail-value">
                <span class="status-dot ${agent.status}"></span> ${agent.status}
            </span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Hostname</span>
            <span class="detail-value">${escapeHtml(agent.hostname)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">IP Address</span>
            <span class="detail-value">${escapeHtml(agent.ip_address)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">OS</span>
            <span class="detail-value">${escapeHtml(agent.os_type)} ${escapeHtml(agent.os_version)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Agent Version</span>
            <span class="detail-value">${escapeHtml(agent.agent_version)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Enrolled</span>
            <span class="detail-value">${formatTime(agent.enrolled_at)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Last Seen</span>
            <span class="detail-value">${formatTime(agent.last_seen)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Messages</span>
            <span class="detail-value">${agent.message_count || 0}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Errors</span>
            <span class="detail-value">${agent.error_count || 0}</span>
        </div>
    `;

    elements.agentModal.classList.add('active');
}

// Setup event listeners
function setupEventListeners() {
    // Search
    elements.searchInput?.addEventListener('input', renderAgentsTable);

    // Clear activity
    elements.clearActivity?.addEventListener('click', () => {
        elements.activityFeed.innerHTML = `<div class="activity-empty">Waiting for events...</div>`;
    });

    // Modal close
    elements.modalClose?.addEventListener('click', () => {
        elements.agentModal.classList.remove('active');
    });

    elements.agentModal?.addEventListener('click', (e) => {
        if (e.target === elements.agentModal) {
            elements.agentModal.classList.remove('active');
        }
    });
}

// Utilities
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatTime(isoString) {
    if (!isoString) return '-';
    try {
        const date = new Date(isoString);
        const now = new Date();
        const diff = (now - date) / 1000;

        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;

        return date.toLocaleString();
    } catch {
        return '-';
    }
}

// ========================
// Token Management
// ========================

let tokens = [];

async function fetchTokens() {
    try {
        const res = await fetch('/api/tokens');
        tokens = await res.json();
        renderTokensTable();
    } catch (e) {
        console.error('Fetch tokens error:', e);
    }
}

function renderTokensTable() {
    const tbody = document.getElementById('tokensTableBody');
    if (!tbody) return;

    if (tokens.length === 0) {
        tbody.innerHTML = `<tr class="empty-row"><td colspan="6">No tokens. Click "Generate Token" to create one.</td></tr>`;
        return;
    }

    tbody.innerHTML = tokens.map(t => `
        <tr>
            <td><strong>${escapeHtml(t.name)}</strong></td>
            <td><code>${escapeHtml(t.token_preview)}</code></td>
            <td>${t.max_uses === -1 ? 'Unlimited' : `${t.use_count}/${t.max_uses}`}</td>
            <td>${t.expires_at ? formatTime(t.expires_at) : 'Never'}</td>
            <td><span class="status-badge ${t.active ? 'online' : 'offline'}">${t.active ? 'Active' : 'Revoked'}</span></td>
            <td>${t.active ? `<button class="btn-sm" onclick="revokeToken('${t.id}')">Revoke</button>` : ''}</td>
        </tr>
    `).join('');
}

function showCreateTokenModal() {
    elements.modalTitle.textContent = 'Generate Enrollment Token';
    elements.modalBody.innerHTML = `
        <form id="tokenForm">
            <div class="form-group">
                <label>Name</label>
                <input type="text" class="input full-width" id="tokenName" value="Enrollment Token" required>
            </div>
            <div class="form-group">
                <label>Expires in (hours, blank = never)</label>
                <input type="number" class="input full-width" id="tokenExpires" placeholder="Optional">
            </div>
            <div class="form-group">
                <label>Max uses (-1 = unlimited)</label>
                <input type="number" class="input full-width" id="tokenMaxUses" value="-1">
            </div>
            <div class="form-actions">
                <button type="submit" class="btn-primary">Generate</button>
            </div>
        </form>
    `;
    elements.agentModal.classList.add('active');

    document.getElementById('tokenForm').onsubmit = async (e) => {
        e.preventDefault();
        const name = document.getElementById('tokenName').value;
        const expires = document.getElementById('tokenExpires').value;
        const maxUses = parseInt(document.getElementById('tokenMaxUses').value) || -1;

        const res = await fetch('/api/tokens', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, expires_hours: expires || null, max_uses: maxUses })
        });
        const token = await res.json();
        showTokenCreated(token);
        fetchTokens();
    };
}

function showTokenCreated(token) {
    // Auto-detect server URL
    const serverUrl = window.location.hostname + ':9999';
    const cmd = `python3 run_client.py --server=${serverUrl} --token=${token.token}`;

    elements.modalTitle.textContent = 'Token Created';
    elements.modalBody.innerHTML = `
        <div style="text-align:center">
            <p><strong>Token generated successfully</strong></p>
            <p style="color:var(--muted-foreground);font-size:13px">Enrollment command (click to copy):</p>
            <div class="code-block-container">
                <pre class="code-block" style="cursor:pointer" onclick="copyCmd(this)">${escapeHtml(cmd)}</pre>
            </div>
            <p style="color:var(--status-degraded);font-size:12px;margin-top:16px">Save this token now - you won't see it again.</p>
            <div style="margin-top:12px;padding:12px;background:var(--secondary);border-radius:4px;text-align:left">
                <div><strong>Token:</strong> <code style="font-size:11px;word-break:break-all">${token.token}</code></div>
            </div>
        </div>
    `;
}

function copyCmd(el) {
    navigator.clipboard.writeText(el.textContent).then(() => {
        const original = el.textContent;
        el.textContent = 'Copied!';
        el.style.color = 'var(--status-online)';
        setTimeout(() => {
            el.textContent = original;
            el.style.color = '';
        }, 1500);
    });
}

async function revokeToken(id) {
    if (!confirm('Revoke this token?')) return;
    await fetch(`/api/tokens/${id}/revoke`, { method: 'POST' });
    fetchTokens();
}

// Create Token Button
document.getElementById('createToken')?.addEventListener('click', showCreateTokenModal);

// ========================
// Broadcast Management
// ========================

let broadcasts = [];

async function fetchBroadcasts() {
    try {
        const res = await fetch('/api/broadcasts');
        broadcasts = await res.json();
        renderBroadcastsTable();
    } catch (e) {
        console.error('Fetch broadcasts error:', e);
    }
}

function renderBroadcastsTable() {
    const tbody = document.getElementById('broadcastsTableBody');
    if (!tbody) return;

    if (broadcasts.length === 0) {
        tbody.innerHTML = `<tr class="empty-row"><td colspan="5">No active broadcasts</td></tr>`;
        return;
    }

    tbody.innerHTML = broadcasts.map(b => `
        <tr>
            <td><code>${escapeHtml((b.id || '?').slice(0, 8))}...</code></td>
            <td><strong>${escapeHtml(b.message_type || '?')}</strong></td>
            <td>${(b.required_labels || []).map(l => `<span class="tag">${escapeHtml(l)}</span>`).join(' ') || '—'}</td>
            <td>${b.expires_at ? formatTime(b.expires_at) : 'Never'}</td>
            <td><button class="btn-sm" onclick="deleteBroadcast('${b.id}')">Delete</button></td>
        </tr>
    `).join('');
}

async function createBroadcast(messageType, labels, data) {
    const res = await fetch('/api/broadcasts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message_type: messageType,
            required_labels: labels,
            data: data
        })
    });
    if (res.ok) {
        fetchBroadcasts();
        return true;
    }
    return false;
}

async function deleteBroadcast(id) {
    if (!confirm('Delete this broadcast?')) return;
    await fetch(`/api/broadcasts/${id}`, { method: 'DELETE' });
    fetchBroadcasts();
}

// Broadcast form handler
document.getElementById('broadcastForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const messageType = document.getElementById('broadcastType').value;
    const labelsStr = document.getElementById('broadcastLabels').value;
    const data = document.getElementById('broadcastData').value;

    // Parse labels
    const labels = labelsStr.split(',').map(s => s.trim()).filter(s => s);

    if (await createBroadcast(messageType, labels, data)) {
        document.getElementById('broadcastForm').reset();
    }
});

// Refresh button
document.getElementById('refreshBroadcasts')?.addEventListener('click', fetchBroadcasts);

// Update tab handler to also fetch broadcasts
document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.getElementById(`page-${tab.dataset.page}`).classList.add('active');

        if (tab.dataset.page === 'tokens') fetchTokens();
        if (tab.dataset.page === 'broadcasts') fetchBroadcasts();
        if (tab.dataset.page === 'settings') fetchSettings();
    });
});

// ==================
// SETTINGS
// ==================

async function fetchSettings() {
    try {
        const res = await fetch('/api/settings');
        const settings = await res.json();

        document.getElementById('heartbeatTimeout').value = settings.heartbeat_timeout || 30;
        document.getElementById('offlineTimeout').value = settings.offline_timeout || 90;

        // Show server info
        document.getElementById('serverInfo').innerHTML = `
            <p><strong>Service:</strong> ${settings.service_name || 'pyfleet'}</p>
            <p><strong>Listen Address:</strong> ${settings.listen_address || '?'}</p>
            <p><strong>Heartbeat Timeout:</strong> ${settings.heartbeat_timeout}s</p>
            <p><strong>Offline Timeout:</strong> ${settings.offline_timeout}s</p>
        `;
    } catch (e) {
        console.error('Fetch settings error:', e);
    }
}

document.getElementById('settingsForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();

    const heartbeatTimeout = parseFloat(document.getElementById('heartbeatTimeout').value);
    const offlineTimeout = parseFloat(document.getElementById('offlineTimeout').value);

    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                heartbeat_timeout: heartbeatTimeout,
                offline_timeout: offlineTimeout
            })
        });

        if (res.ok) {
            const saved = document.getElementById('settingsSaved');
            saved.style.display = 'inline';
            setTimeout(() => saved.style.display = 'none', 2000);
            fetchSettings();  // Refresh displayed values
        }
    } catch (e) {
        console.error('Save settings error:', e);
    }
});
