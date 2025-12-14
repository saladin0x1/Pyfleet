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
    enrollment: '⊕',
    status_change: '↻',
    message: '✉',
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
    try {
        socket = io();
        
        socket.on('connect', () => {
            console.log('WebSocket connected');
            updateServerStatus(true);
        });
        
        socket.on('disconnect', () => {
            console.log('WebSocket disconnected');
            updateServerStatus(false);
        });
        
        socket.on('event', (event) => {
            addActivityItem(event);
        });
        
        socket.on('agents_update', (data) => {
            agents = data.agents;
            updateStats(data.stats);
            renderAgentsTable();
        });
    } catch (e) {
        console.error('WebSocket error:', e);
    }
}

function updateServerStatus(connected) {
    const dot = elements.serverStatus.querySelector('.status-dot');
    const text = elements.serverStatus.querySelector('span:last-child');
    
    if (connected) {
        dot.className = 'status-dot online';
        text.textContent = 'Server Online';
    } else {
        dot.className = 'status-dot offline';
        text.textContent = 'Disconnected';
    }
}

// Fetch data
async function fetchAgents() {
    try {
        const [agentsRes, statsRes] = await Promise.all([
            fetch('/api/agents'),
            fetch('/api/stats'),
        ]);
        
        agents = await agentsRes.json();
        const stats = await statsRes.json();
        
        updateStats(stats);
        renderAgentsTable();
    } catch (e) {
        console.error('Fetch error:', e);
    }
}

async function fetchEvents() {
    try {
        const res = await fetch('/api/events');
        const events = await res.json();
        
        // Clear and render events
        elements.activityFeed.innerHTML = '';
        events.reverse().forEach(event => addActivityItem(event, false));
        
        if (events.length === 0) {
            elements.activityFeed.innerHTML = '<div class="activity-empty">Waiting for events...</div>';
        }
    } catch (e) {
        console.error('Events fetch error:', e);
    }
}

// Update UI
function updateStats(stats) {
    elements.statTotal.textContent = stats.total || 0;
    elements.statOnline.textContent = stats.online || 0;
    elements.statDegraded.textContent = stats.degraded || 0;
    elements.statOffline.textContent = stats.offline || 0;
}

function renderAgentsTable() {
    const searchTerm = elements.searchInput.value.toLowerCase();
    
    const filtered = agents.filter(agent => 
        agent.hostname.toLowerCase().includes(searchTerm) ||
        agent.client_id.toLowerCase().includes(searchTerm) ||
        agent.os_type.toLowerCase().includes(searchTerm)
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
        <tr data-id="${agent.client_id}">
            <td>
                <span class="status-badge ${agent.status}">
                    <span class="status-dot ${agent.status}"></span>
                    ${agent.status}
                </span>
            </td>
            <td>${escapeHtml(agent.hostname) || '—'}</td>
            <td>${escapeHtml(agent.os_type) || '—'}</td>
            <td>${escapeHtml(agent.agent_version) || '—'}</td>
            <td>${formatTime(agent.last_seen)}</td>
            <td>${renderTags(agent.tags)}</td>
        </tr>
    `).join('');
    
    // Add click listeners
    elements.agentsTableBody.querySelectorAll('tr').forEach(row => {
        row.addEventListener('click', () => showAgentDetails(row.dataset.id));
    });
}

function renderTags(tags) {
    if (!tags || tags.length === 0) return '—';
    return tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('');
}

function addActivityItem(event, animate = true) {
    // Remove empty message
    const empty = elements.activityFeed.querySelector('.activity-empty');
    if (empty) empty.remove();
    
    const item = document.createElement('div');
    item.className = 'activity-item';
    if (!animate) item.style.animation = 'none';
    
    const icon = activityIcons[event.type] || '•';
    
    item.innerHTML = `
        <div class="activity-icon ${event.type}">${icon}</div>
        <div class="activity-content">
            <div class="activity-message">${escapeHtml(event.message)}</div>
            <div class="activity-time">${formatTime(event.timestamp)}</div>
        </div>
    `;
    
    elements.activityFeed.insertBefore(item, elements.activityFeed.firstChild);
    
    // Limit items
    while (elements.activityFeed.children.length > 50) {
        elements.activityFeed.lastChild.remove();
    }
}

function showAgentDetails(clientId) {
    const agent = agents.find(a => a.client_id === clientId);
    if (!agent) return;
    
    elements.modalTitle.textContent = agent.hostname || 'Agent Details';
    elements.modalBody.innerHTML = `
        <div class="detail-row">
            <span class="detail-label">Client ID</span>
            <span class="detail-value">${escapeHtml(agent.client_id)}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Status</span>
            <span class="detail-value">
                <span class="status-badge ${agent.status}">
                    <span class="status-dot ${agent.status}"></span>
                    ${agent.status}
                </span>
            </span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Hostname</span>
            <span class="detail-value">${escapeHtml(agent.hostname) || '—'}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">OS Type</span>
            <span class="detail-value">${escapeHtml(agent.os_type) || '—'}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">OS Version</span>
            <span class="detail-value">${escapeHtml(agent.os_version) || '—'}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Agent Version</span>
            <span class="detail-value">${escapeHtml(agent.agent_version) || '—'}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">IP Address</span>
            <span class="detail-value">${escapeHtml(agent.ip_address) || '—'}</span>
        </div>
        <div class="detail-row">
            <span class="detail-label">Enrolled At</span>
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
            <span class="detail-label">Tags</span>
            <span class="detail-value">${renderTags(agent.tags)}</span>
        </div>
    `;
    
    elements.agentModal.classList.add('active');
}

// Event listeners
function setupEventListeners() {
    elements.searchInput.addEventListener('input', renderAgentsTable);
    
    elements.clearActivity.addEventListener('click', () => {
        elements.activityFeed.innerHTML = '<div class="activity-empty">Waiting for events...</div>';
    });
    
    elements.modalClose.addEventListener('click', () => {
        elements.agentModal.classList.remove('active');
    });
    
    elements.agentModal.addEventListener('click', (e) => {
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
    if (!isoString) return '—';
    try {
        const date = new Date(isoString);
        const now = new Date();
        const diff = (now - date) / 1000;
        
        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        
        return date.toLocaleString();
    } catch {
        return '—';
    }
}
