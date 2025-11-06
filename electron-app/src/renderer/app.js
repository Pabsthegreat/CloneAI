/**
 * CloneAI Desktop - Renderer Process
 * 
 * Frontend application logic
 */

// State
let apiUrl = 'http://127.0.0.1:8765';
let isBackendReady = false;

// Cache for data
let emailsCache = {
    data: [],
    timestamp: null
};

let calendarCache = {
    data: [],
    timestamp: null
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    console.log('[App] Initializing...');
    
    // Get API URL from main process
    try {
        apiUrl = await window.electronAPI.getApiUrl();
        console.log(`[App] API URL: ${apiUrl}`);
    } catch (error) {
        console.error('[App] Failed to get API URL:', error);
    }
    
    // Set up navigation
    setupNavigation();
    
    // Set up event listeners
    setupEventListeners();
    
    // Wait for backend
    waitForBackend();
    
    // Load system info
    loadSystemInfo();
});

/**
 * Setup navigation between views
 */
function setupNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.view');
    
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const viewName = item.dataset.view;
            
            // Update active nav item
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
            
            // Update active view
            views.forEach(view => view.classList.remove('active'));
            document.getElementById(`${viewName}-view`).classList.add('active');
            
            // Load view data
            loadViewData(viewName);
        });
    });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Chat input
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    
    sendButton.addEventListener('click', sendChatMessage);
    
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
    
    // Refresh buttons (force refresh on click)
    document.getElementById('refresh-emails')?.addEventListener('click', () => loadEmails(true));
    document.getElementById('refresh-calendar')?.addEventListener('click', () => loadCalendarEvents(true));
    document.getElementById('refresh-workflows')?.addEventListener('click', () => loadWorkflows());
    
    // Open workflows folder
    document.getElementById('open-workflows-folder')?.addEventListener('click', async () => {
        try {
            const result = await window.electronAPI.openWorkflowsFolder();
            addChatMessage('system', `✓ Opened workflows folder: ${result.path}`);
        } catch (error) {
            console.error('[App] Failed to open workflows folder:', error);
        }
    });
    
    // Listen for backend events
    window.electronAPI.onPythonReady((data) => {
        console.log('[App] Python backend ready!', data);
        isBackendReady = true;
        updateBackendStatus('connected', 'Backend Connected');
    });
    
    window.electronAPI.onPythonStopped((data) => {
        console.log('[App] Python backend stopped', data);
        isBackendReady = false;
        updateBackendStatus('error', 'Backend Stopped');
    });
    
    window.electronAPI.onWorkflowGenerated((data) => {
        console.log('[App] New workflow generated:', data);
        addChatMessage('system', `✨ New workflow generated: ${data.file}`);
        loadWorkflows();
    });
}

/**
 * Wait for backend to be ready
 */
async function waitForBackend() {
    console.log('[App] Waiting for backend...');
    updateBackendStatus('connecting', 'Connecting...');
    
    let attempts = 0;
    const maxAttempts = 30;
    
    const checkBackend = async () => {
        try {
            const response = await fetch(`${apiUrl}/api/health`);
            if (response.ok) {
                const data = await response.json();
                console.log('[App] Backend health check:', data);
                isBackendReady = true;
                updateBackendStatus('connected', 'Connected');
                return true;
            }
        } catch (error) {
            // Backend not ready yet
        }
        
        attempts++;
        if (attempts < maxAttempts) {
            setTimeout(checkBackend, 1000);
        } else {
            console.error('[App] Backend failed to start');
            updateBackendStatus('error', 'Connection Failed');
            addChatMessage('error', '⚠️ Failed to connect to backend. Please restart the app.');
        }
        return false;
    };
    
    await checkBackend();
}

/**
 * Update backend status indicator
 */
function updateBackendStatus(status, text) {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');
    
    statusDot.className = `status-dot ${status}`;
    statusText.textContent = text;
}

/**
 * Load data for a specific view
 */
function loadViewData(viewName) {
    console.log(`[App] Loading data for: ${viewName}`);
    
    switch (viewName) {
        case 'emails':
            loadEmails();
            break;
        case 'calendar':
            loadCalendarEvents();
            break;
        case 'workflows':
            loadWorkflows();
            break;
        case 'settings':
            loadFeatures();
            break;
    }
}

/**
 * Send chat message
 */
async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) return;
    if (!isBackendReady) {
        addChatMessage('error', '⚠️ Backend not ready. Please wait...');
        return;
    }
    
    // Add user message to chat
    addChatMessage('user', message);
    input.value = '';
    
    // Show loading
    const loadingId = addChatMessage('assistant', '⏳ Thinking...');
    
    try {
        const response = await fetch(`${apiUrl}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                execute: true
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('[Chat] Response:', data);
        
        // Remove loading message
        removeMessage(loadingId);
        
        // Add response
        if (data.executed && data.output) {
            addChatMessage('assistant', `✓ ${data.output}`);
        } else if (data.preview_steps) {
            addChatMessage('assistant', `📋 Plan:\n${data.preview_steps}\n\n(Preview only - not executed)`);
        } else {
            addChatMessage('assistant', `Classification: ${data.classification}\nCategories: ${data.categories.join(', ')}`);
        }
        
    } catch (error) {
        console.error('[Chat] Error:', error);
        removeMessage(loadingId);
        addChatMessage('error', `❌ Error: ${error.message}`);
    }
}

/**
 * Add message to chat
 */
function addChatMessage(type, content) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    const messageId = `msg-${Date.now()}`;
    
    messageDiv.id = messageId;
    messageDiv.className = `message ${type}`;
    messageDiv.innerHTML = `
        <div class="message-content">${escapeHtml(content)}</div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return messageId;
}

/**
 * Remove message from chat
 */
function removeMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}

/**
 * Load emails (with caching)
 */
async function loadEmails(forceRefresh = false) {
    console.log('[Emails] Loading...', forceRefresh ? '(force refresh)' : '(using cache if available)');
    const emailsList = document.getElementById('email-list');
    const loading = document.getElementById('emails-loading');
    
    // Use cache if available and not forcing refresh
    if (!forceRefresh && emailsCache.data.length > 0) {
        console.log('[Emails] Using cached data');
        displayEmails(emailsCache.data);
        return;
    }
    
    loading.style.display = 'flex';
    emailsList.innerHTML = '';
    
    try {
        const response = await fetch(`${apiUrl}/api/emails?count=20`);
        if (!response.ok) throw new Error('Failed to fetch emails');
        
        const data = await response.json();
        console.log('[Emails] Data:', data);
        
        loading.style.display = 'none';
        
        // Cache the data
        emailsCache.data = data.emails || [];
        emailsCache.timestamp = new Date();
        
        displayEmails(emailsCache.data);
        
    } catch (error) {
        console.error('[Emails] Error:', error);
        loading.style.display = 'none';
        emailsList.innerHTML = `<div class="email-item"><p style="color: var(--error-color);">❌ Error loading emails: ${error.message}</p></div>`;
    }
}

/**
 * Display emails in a nice format
 */
function displayEmails(emails) {
    const emailsList = document.getElementById('email-list');
    
    if (!emails || emails.length === 0) {
        emailsList.innerHTML = '<div class="email-item"><p>No emails found</p></div>';
        return;
    }
    
    emailsList.innerHTML = emails.map((email, index) => `
        <div class="email-item" onclick="toggleEmailBody(${index})">
            <div class="email-header">
                <div class="email-from">
                    <strong>From:</strong> ${escapeHtml(email.from || 'Unknown')}
                </div>
                <div class="email-date">${escapeHtml(email.date || '')}</div>
            </div>
            <div class="email-subject">
                ${escapeHtml(email.subject || 'No Subject')}
            </div>
            <div class="email-body" id="email-body-${index}" style="display: none;">
                <hr>
                <div style="white-space: pre-wrap; margin-top: 10px;">
                    ${escapeHtml(email.body || 'No content')}
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Toggle email body visibility
 */
function toggleEmailBody(index) {
    const body = document.getElementById(`email-body-${index}`);
    if (body) {
        body.style.display = body.style.display === 'none' ? 'block' : 'none';
    }
}

/**
 * Load calendar events (with caching)
 */
async function loadCalendarEvents(forceRefresh = false) {
    console.log('[Calendar] Loading...', forceRefresh ? '(force refresh)' : '(using cache if available)');
    const eventsList = document.getElementById('events-list');
    const loading = document.getElementById('calendar-loading');
    
    // Use cache if available and not forcing refresh
    if (!forceRefresh && calendarCache.data.length > 0) {
        console.log('[Calendar] Using cached data');
        displayCalendarEvents(calendarCache.data);
        return;
    }
    
    loading.style.display = 'flex';
    eventsList.innerHTML = '';
    
    try {
        const response = await fetch(`${apiUrl}/api/calendar?count=20`);
        if (!response.ok) throw new Error('Failed to fetch calendar events');
        
        const data = await response.json();
        console.log('[Calendar] Data:', data);
        
        loading.style.display = 'none';
        
        // Cache the data
        calendarCache.data = data.events || [];
        calendarCache.timestamp = new Date();
        
        displayCalendarEvents(calendarCache.data);
        
    } catch (error) {
        console.error('[Calendar] Error:', error);
        loading.style.display = 'none';
        eventsList.innerHTML = `<div class="event-item"><p style="color: var(--error-color);">❌ Error loading events: ${error.message}</p></div>`;
    }
}

/**
 * Display calendar events in Google Calendar style
 */
function displayCalendarEvents(events) {
    const eventsList = document.getElementById('events-list');
    
    if (!events || events.length === 0) {
        eventsList.innerHTML = '<div class="event-item"><p>No upcoming events</p></div>';
        return;
    }
    
    // Group events by date
    const eventsByDate = {};
    events.forEach(event => {
        const dateStr = event.start ? new Date(event.start).toLocaleDateString() : 'Unknown Date';
        if (!eventsByDate[dateStr]) {
            eventsByDate[dateStr] = [];
        }
        eventsByDate[dateStr].push(event);
    });
    
    // Display grouped events
    eventsList.innerHTML = Object.entries(eventsByDate).map(([date, dayEvents]) => `
        <div class="calendar-day">
            <div class="calendar-date-header">${date}</div>
            ${dayEvents.map(event => `
                <div class="calendar-event">
                    <div class="event-time">
                        ${formatEventTime(event.start)} - ${formatEventTime(event.end)}
                    </div>
                    <div class="event-details">
                        <div class="event-title">${escapeHtml(event.title || 'Untitled Event')}</div>
                        ${event.location ? `<div class="event-location">📍 ${escapeHtml(event.location)}</div>` : ''}
                        ${event.description ? `<div class="event-description">${escapeHtml(event.description)}</div>` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
    `).join('');
}

/**
 * Format event time
 */
function formatEventTime(dateStr) {
    if (!dateStr) return 'N/A';
    try {
        const date = new Date(dateStr);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
        return dateStr;
    }
}

/**
 * Load workflows
 */
async function loadWorkflows() {
    console.log('[Workflows] Loading...');
    
    try {
        const response = await fetch(`${apiUrl}/api/workflows`);
        if (!response.ok) throw new Error('Failed to fetch workflows');
        
        const data = await response.json();
        console.log('[Workflows] Data:', data);
        
        // Update stats
        const statsContainer = document.getElementById('workflows-stats');
        statsContainer.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${data.total || 0}</div>
                <div class="stat-label">Total Workflows</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${(data.total || 0) - (data.custom_count || 0)}</div>
                <div class="stat-label">Built-in Workflows</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.custom_count || 0}</div>
                <div class="stat-label">Custom Workflows</div>
            </div>
        `;
        
        // Display built-in workflows
        const builtinContainer = document.getElementById('builtin-workflows');
        if (data.workflows && data.workflows.length > 0) {
            builtinContainer.innerHTML = data.workflows
                .slice(0, 10) // Show first 10
                .map(wf => `
                    <div class="workflow-card">
                        <div class="workflow-name">${wf.namespace}:${wf.action}</div>
                        <div class="workflow-desc">${wf.summary || 'No description'}</div>
                        ${wf.usage ? `<div class="workflow-usage">${escapeHtml(wf.usage)}</div>` : ''}
                    </div>
                `).join('');
        } else {
            builtinContainer.innerHTML = '<p>No workflows found</p>';
        }
        
        // Display custom workflows
        const customContainer = document.getElementById('custom-workflows');
        if (data.custom_workflows && data.custom_workflows.length > 0) {
            customContainer.innerHTML = data.custom_workflows.map(wf => `
                <div class="workflow-card">
                    <div class="workflow-name">📄 ${wf.filename}</div>
                    <div class="workflow-desc">Modified: ${new Date(wf.modified).toLocaleString()}</div>
                    <div class="workflow-usage">${wf.path}</div>
                </div>
            `).join('');
        } else {
            customContainer.innerHTML = '<p style="color: var(--text-secondary);">No custom workflows yet. Generate one using natural language!</p>';
        }
        
    } catch (error) {
        console.error('[Workflows] Error:', error);
    }
}

/**
 * Load system info
 */
async function loadSystemInfo() {
    try {
        const systemInfo = await window.electronAPI.getSystemInfo();
        const apiInfo = await fetch(`${apiUrl}/api/info`).then(r => r.json());
        
        const infoContainer = document.getElementById('system-info');
        infoContainer.innerHTML = `
            <div class="info-item">
                <span class="info-label">Platform</span>
                <span class="info-value">${systemInfo.platform}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Architecture</span>
                <span class="info-value">${systemInfo.arch}</span>
            </div>
            <div class="info-item">
                <span class="info-label">App Version</span>
                <span class="info-value">${systemInfo.version}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Electron Version</span>
                <span class="info-value">${systemInfo.electronVersion}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Config Dir</span>
                <span class="info-value">${apiInfo.config_dir || 'Unknown'}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Workflows Count</span>
                <span class="info-value">${apiInfo.workflows_count || 0}</span>
            </div>
        `;
        
    } catch (error) {
        console.error('[System Info] Error:', error);
    }
}

/**
 * Load available features
 */
async function loadFeatures() {
    try {
        const response = await fetch(`${apiUrl}/api/features`);
        const features = await response.json();
        
        const featuresContainer = document.getElementById('features-list');
        featuresContainer.innerHTML = Object.entries(features)
            .filter(([key]) => !['platform'].includes(key))
            .map(([key, available]) => `
                <div class="feature-item ${available ? 'available' : 'unavailable'}">
                    <span class="feature-status"></span>
                    <span>${key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                </div>
            `).join('');
        
    } catch (error) {
        console.error('[Features] Error:', error);
    }
}

/**
 * Utility: Escape HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/\n/g, '<br>');
}

console.log('[App] Renderer script loaded');
