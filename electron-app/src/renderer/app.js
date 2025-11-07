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
            addChatMessage('system', `Opened workflows folder: ${result.path}`);
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
        addChatMessage('system', `New workflow generated: ${data.file}`);
        loadWorkflows();
    });
    
    // Setup new feature handlers
    setupNewFeatureHandlers();
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
            addChatMessage('error', 'Failed to connect to backend. Please restart the app.');
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
        case 'chats-history':
            loadChatHistory();
            break;
        case 'files':
            updateUploadedFilesUI();
            break;
        case 'config':
            loadConfiguration();
            break;
        case 'settings':
            loadSettings();
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
        addChatMessage('error', 'Backend not ready. Please wait...');
        return;
    }
    
    // Add user message to chat
    addChatMessage('user', message);
    input.value = '';
    
    // Show processing message
    const processingId = addProcessingMessage('Processing your request...');
    
    try {
        const response = await fetch(`${apiUrl}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                execute: true,
                attached_files: attachedFiles.map(f => f.file_id)
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('[Chat] Response:', data);
        
        // Remove processing message
        removeMessage(processingId);
        
        // Add response
        if (data.requires_confirmation && data.draft_id) {
            // Email draft requires confirmation
            showEmailConfirmation(data.draft);
        } else if (data.executed && data.multi_step && data.steps_executed) {
            // Multi-step execution - show each step
            let summary = `**Multi-step execution:**\n\n`;
            for (const step of data.steps_executed) {
                if (step.status === 'success') {
                    summary += `[SUCCESS] Step ${step.step}: ${step.description}\n`;
                    if (step.output) {
                        summary += `  Output: ${step.output.substring(0, 200)}${step.output.length > 200 ? '...' : ''}\n`;
                    }
                } else if (step.status === 'failed') {
                    summary += `[FAILED] Step ${step.step}: ${step.description}\n`;
                    summary += `  Error: ${step.error}\n`;
                } else if (step.status === 'expanded') {
                    summary += `[EXPANDED] Step ${step.step}: ${step.description} (expanded into ${step.expanded_steps ? step.expanded_steps.length : 0} steps)\n`;
                }
                summary += '\n';
            }
            if (data.output) {
                summary += `\n**Final Output:**\n${data.output}`;
            }
            addChatMessage('assistant', summary);
        } else if (data.executed && data.output) {
            // Check if response includes an image
            if (data.image_url) {
                addChatMessageWithImage('assistant', data.output, data.image_url);
            } else {
                // Check if this is an email list response
                if (data.output && data.output.includes('From:') && data.output.includes('Subject:')) {
                    displayEmailListInChat(data.output);
                } else {
                    addChatMessage('assistant', data.output);
                }
            }
        } else if (data.error) {
            addChatMessage('error', `Error: ${data.error}`);
        } else if (data.preview_steps) {
            addChatMessage('assistant', `**Plan:**\n${data.preview_steps}\n\n(Preview only - not executed)`);
        } else if (data.local_answer) {
            addChatMessage('assistant', data.local_answer);
        } else {
            addChatMessage('assistant', `Categories: ${data.categories ? data.categories.join(', ') : 'unknown'}`);
        }
        
        // Clear attached files after sending
        if (attachedFiles.length > 0) {
            attachedFiles = [];
            updateAttachedFilesUI();
        }
        
    } catch (error) {
        console.error('[Chat] Error:', error);
        removeMessage(processingId);
        addChatMessage('error', `Error: ${error.message}`);
    }
}

/**
 * Parse markdown-like text to HTML
 */
function parseMarkdown(text) {
    // Bold: **text** or __text__
    text = text.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/__([^_]+)__/g, '<strong>$1</strong>');
    
    // Italic: *text* or _text_
    text = text.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
    text = text.replace(/_([^_]+)_/g, '<em>$1</em>');
    
    // Code: `text`
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Preserve line breaks
    text = text.replace(/\n/g, '<br>');
    
    return text;
}

/**
 * Add message to chat
 */
function addChatMessage(type, content, options = {}) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    const messageId = `msg-${Date.now()}`;
    
    messageDiv.id = messageId;
    messageDiv.className = `message ${type}`;
    
    // Parse markdown if not disabled
    const formattedContent = options.skipMarkdown ? escapeHtml(content) : parseMarkdown(escapeHtml(content));
    
    messageDiv.innerHTML = `
        <div class="message-content">${formattedContent}</div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return messageId;
}

/**
 * Add message with image to chat
 */
function addChatMessageWithImage(type, content, imageUrl) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    const messageId = `msg-${Date.now()}`;
    
    messageDiv.id = messageId;
    messageDiv.className = `message ${type}`;
    
    const formattedContent = parseMarkdown(escapeHtml(content));
    
    messageDiv.innerHTML = `
        <div class="message-content">
            ${formattedContent}
            <div class="message-image">
                <img src="${apiUrl}${imageUrl}" alt="Generated image" />
            </div>
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return messageId;
}

/**
 * Add processing message to chat
 */
function addProcessingMessage(message = 'Processing your request...') {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    const messageId = `msg-processing-${Date.now()}`;
    
    messageDiv.id = messageId;
    messageDiv.className = 'message system processing';
    messageDiv.innerHTML = `
        <div class="message-content">
            <span class="processing-spinner"></span>
            ${escapeHtml(message)}
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return messageId;
}

/**
 * Remove a message from chat
 */
function removeMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
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
        emailsList.innerHTML = `<div class="email-item"><p style="color: var(--error-color);">Error loading emails: ${error.message}</p></div>`;
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
        <div class="email-item">
            <div class="email-header" onclick="toggleEmailBody(${index})">
                <div class="email-from">
                    <strong>From:</strong> ${escapeHtml(email.from || 'Unknown')}
                </div>
                <div class="email-date">${escapeHtml(email.date || '')}</div>
            </div>
            <div class="email-subject" onclick="toggleEmailBody(${index})">
                ${escapeHtml(email.subject || 'No Subject')}
            </div>
            <div class="email-body" id="email-body-${index}" style="display: none;">
                <hr>
                <div class="email-content" style="white-space: pre-wrap; margin: 12px 0;">
                    ${escapeHtml(email.body || 'No content')}
                </div>
                <div class="email-actions">
                    <button class="button-secondary" onclick="replyToEmail(${index}, false)">Reply</button>
                    <button class="button-primary" onclick="replyToEmail(${index}, true)">Reply with AI Assistant</button>
                </div>
            </div>
        </div>
    `).join('');
    
    // Store emails for reply functionality
    window.currentEmails = emails;
}

/**
 * Toggle email body visibility
 */
function toggleEmailBody(index) {
    const body = document.getElementById(`email-body-${index}`);
    if (body) {
        const isHidden = body.style.display === 'none';
        // Close all other email bodies
        document.querySelectorAll('.email-body').forEach(el => el.style.display = 'none');
        // Toggle current
        body.style.display = isHidden ? 'block' : 'none';
    }
}

/**
 * Reply to an email
 */
async function replyToEmail(index, useAI) {
    if (!window.currentEmails || !window.currentEmails[index]) {
        alert('Email not found');
        return;
    }
    
    const email = window.currentEmails[index];
    console.log('[Email] Replying to:', email);
    
    // Switch to chat view
    switchView('chat');
    
    const chatInput = document.getElementById('chat-input');
    
    if (useAI) {
        // Use AI to draft reply
        const prompt = `Reply to this email:\n\nFrom: ${email.from}\nSubject: ${email.subject}\n\nBody:\n${email.body}\n\nDraft a professional reply.`;
        chatInput.value = prompt;
        
        // Auto-send
        setTimeout(() => sendChatMessage(), 100);
    } else {
        // Manual reply - pre-fill with mail:send command
        const replySubject = email.subject.startsWith('Re:') ? email.subject : `Re: ${email.subject}`;
        chatInput.value = `mail:send to:${email.from} subject:"${replySubject}" body:"[Your reply here]"`;
        chatInput.focus();
        
        // Select the placeholder text
        setTimeout(() => {
            const start = chatInput.value.indexOf('[Your reply here]');
            if (start !== -1) {
                chatInput.setSelectionRange(start, start + '[Your reply here]'.length);
            }
        }, 50);
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
        eventsList.innerHTML = `<div class="event-item"><p style="color: var(--error-color);">Error loading events: ${error.message}</p></div>`;
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
        
        if (!data.success) {
            throw new Error('Failed to load workflows');
        }
        
        // Update stats
        const statsContainer = document.getElementById('workflows-stats');
        const namespaces = Object.keys(data.by_namespace || {});
        statsContainer.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${data.total || 0}</div>
                <div class="stat-label">Total Workflows</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${namespaces.length}</div>
                <div class="stat-label">Categories</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.workflows ? data.workflows.filter(w => w.preferred_llm === 'cloud').length : 0}</div>
                <div class="stat-label">Cloud Workflows</div>
            </div>
        `;
        
        // Display workflows grouped by namespace
        const builtinContainer = document.getElementById('builtin-workflows');
        if (data.by_namespace && Object.keys(data.by_namespace).length > 0) {
            let html = '';
            for (const [namespace, workflows] of Object.entries(data.by_namespace)) {
                html += `
                    <div class="workflow-category">
                        <h3 class="category-title">${namespace.toUpperCase()} (${workflows.length})</h3>
                        <div class="workflow-list">
                `;
                
                workflows.forEach(wf => {
                    html += `
                        <div class="workflow-card">
                            <div class="workflow-header">
                                <div class="workflow-name">${escapeHtml(wf.command)}</div>
                                <button class="try-workflow-btn" data-command="${escapeHtml(wf.usage || wf.command)}">
                                    Try Now
                                </button>
                            </div>
                            <div class="workflow-desc">${escapeHtml(wf.summary || wf.description)}</div>
                            ${wf.usage ? `<div class="workflow-usage">Usage: <code>${escapeHtml(wf.usage)}</code></div>` : ''}
                            ${wf.examples && wf.examples.length > 0 ? `
                                <div class="workflow-examples">
                                    <strong>Examples:</strong>
                                    ${wf.examples.map(ex => `<div class="example-item">${escapeHtml(ex)}</div>`).join('')}
                                </div>
                            ` : ''}
                        </div>
                    `;
                });
                
                html += `
                        </div>
                    </div>
                `;
            }
            builtinContainer.innerHTML = html;
            
            // Add event listeners to Try Now buttons
            document.querySelectorAll('.try-workflow-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const command = e.target.dataset.command;
                    console.log('[Workflows] Try workflow:', command);
                    
                    // Switch to chat view
                    switchView('chat');
                    
                    // Fill chat input with command
                    const chatInput = document.getElementById('chat-input');
                    chatInput.value = command;
                    chatInput.focus();
                });
            });
        } else {
            builtinContainer.innerHTML = '<p class="empty-state">No workflows found</p>';
        }
        
        // Display custom workflows section
        const customContainer = document.getElementById('custom-workflows');
        customContainer.innerHTML = '<p class="empty-state">Custom workflow generation coming soon!</p>';
        
    } catch (error) {
        console.error('[Workflows] Error:', error);
        const builtinContainer = document.getElementById('builtin-workflows');
        builtinContainer.innerHTML = `<p class="empty-state">Error loading workflows: ${escapeHtml(error.message)}</p>`;
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

// ============================================================================
// NEW FEATURES
// ============================================================================

/**
 * Chat Sessions Management
 */
let currentChatSession = null;
let attachedFiles = [];

async function createNewChatSession() {
    try {
        const response = await fetch(`${apiUrl}/api/chats/new`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: 'New Chat' })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentChatSession = result.session_id;
            
            // Clear chat messages
            const messagesContainer = document.getElementById('chat-messages');
            messagesContainer.innerHTML = `
                <div class="message system">
                    <div class="message-content">
                        👋 Hello! New chat session started. What can I help you with?
                    </div>
                </div>
            `;
            
            // Clear attached files
            attachedFiles = [];
            updateAttachedFilesUI();
            
            console.log('[Chat] New session created:', result.session_id);
        }
    } catch (error) {
        console.error('[Chat] Failed to create new session:', error);
    }
}

async function loadChatHistory() {
    try {
        const response = await fetch(`${apiUrl}/api/chats`);
        const result = await response.json();
        
        if (result.success) {
            const chatsContainer = document.getElementById('chats-list');
            
            if (result.sessions.length === 0) {
                chatsContainer.innerHTML = '<p class="empty-state">No chat history yet</p>';
                return;
            }
            
            chatsContainer.innerHTML = result.sessions.map(session => `
                <div class="chat-session-card" data-session-id="${session.session_id}">
                    <div class="chat-session-header">
                        <h4>${escapeHtml(session.title)}</h4>
                        <button class="delete-chat" data-session-id="${session.session_id}">Delete</button>
                    </div>
                    <div class="chat-session-meta">
                        <span>💬 ${session.message_count} messages</span>
                        <span>🕒 ${new Date(session.updated_at).toLocaleString()}</span>
                    </div>
                </div>
            `).join('');
            
            // Add click handlers
            document.querySelectorAll('.chat-session-card').forEach(card => {
                card.addEventListener('click', async (e) => {
                    if (e.target.classList.contains('delete-chat')) return;
                    await loadChatSession(card.dataset.sessionId);
                });
            });
            
            document.querySelectorAll('.delete-chat').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    await deleteChatSession(btn.dataset.sessionId);
                });
            });
        }
    } catch (error) {
        console.error('[Chat] Failed to load history:', error);
    }
}

async function loadChatSession(sessionId) {
    try {
        const response = await fetch(`${apiUrl}/api/chats/${sessionId}`);
        const result = await response.json();
        
        if (result.success) {
            currentChatSession = sessionId;
            
            // Switch to chat view
            document.querySelector('.nav-item[data-view="chat"]').click();
            
            // Load messages
            const messagesContainer = document.getElementById('chat-messages');
            messagesContainer.innerHTML = result.session.messages.map(msg => `
                <div class="message ${msg.role}">
                    <div class="message-content">
                        ${escapeHtml(msg.content)}
                    </div>
                    <div class="message-time">${new Date(msg.timestamp).toLocaleTimeString()}</div>
                </div>
            `).join('');
            
            // Scroll to bottom
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    } catch (error) {
        console.error('[Chat] Failed to load session:', error);
    }
}

async function deleteChatSession(sessionId) {
    if (!confirm('Delete this chat session?')) return;
    
    try {
        const response = await fetch(`${apiUrl}/api/chats/${sessionId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            await loadChatHistory();
        }
    } catch (error) {
        console.error('[Chat] Failed to delete session:', error);
    }
}

/**
 * File Upload and Operations
 */
async function handleFileUpload(files) {
    const filesArray = Array.from(files);
    
    for (const file of filesArray) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch(`${apiUrl}/api/files/upload`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                attachedFiles.push({
                    file_id: result.file_id,
                    filename: result.filename,
                    size: result.size
                });
                
                console.log('[Files] Uploaded:', result.filename);
            }
        } catch (error) {
            console.error('[Files] Upload failed:', error);
        }
    }
    
    updateAttachedFilesUI();
    updateUploadedFilesUI();
}

function updateAttachedFilesUI() {
    const container = document.getElementById('attached-files');
    
    if (attachedFiles.length === 0) {
        container.innerHTML = '';
        return;
    }
    
    container.innerHTML = `
        <div class="attached-files-list">
            ${attachedFiles.map(file => `
                <div class="attached-file" data-file-id="${file.file_id}">
                    <span>📎 ${file.filename}</span>
                    <button class="remove-file" data-file-id="${file.file_id}">✕</button>
                </div>
            `).join('')}
        </div>
    `;
    
    // Add remove handlers
    document.querySelectorAll('.remove-file').forEach(btn => {
        btn.addEventListener('click', () => {
            attachedFiles = attachedFiles.filter(f => f.file_id !== btn.dataset.fileId);
            updateAttachedFilesUI();
        });
    });
}

function updateUploadedFilesUI() {
    const container = document.getElementById('uploaded-files-list');
    
    if (attachedFiles.length === 0) {
        container.innerHTML = '<p class="empty-state">No files uploaded yet</p>';
        return;
    }
    
    container.innerHTML = attachedFiles.map(file => `
        <div class="uploaded-file-card">
            <div class="file-icon">📄</div>
            <div class="file-info">
                <div class="file-name">${file.filename}</div>
                <div class="file-size">${formatFileSize(file.size)}</div>
            </div>
            <button class="delete-file" data-file-id="${file.file_id}">Delete</button>
        </div>
    `).join('');
    
    // Add delete handlers
    document.querySelectorAll('.delete-file').forEach(btn => {
        btn.addEventListener('click', async () => {
            await deleteFile(btn.dataset.fileId);
        });
    });
}

async function deleteFile(fileId) {
    try {
        const response = await fetch(`${apiUrl}/api/files/${fileId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            attachedFiles = attachedFiles.filter(f => f.file_id !== fileId);
            updateAttachedFilesUI();
            updateUploadedFilesUI();
        }
    } catch (error) {
        console.error('[Files] Delete failed:', error);
    }
}

async function performFileOperation(operation) {
    if (attachedFiles.length === 0) {
        alert('Please upload files first');
        return;
    }
    
    try {
        const fileIds = attachedFiles.map(f => f.file_id);
        console.log('[Files] Performing operation:', operation, 'on files:', fileIds);
        
        const response = await fetch(`${apiUrl}/api/files/operate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                operation,
                file_ids: fileIds,
                params: {}
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Operation failed');
        }
        
        const result = await response.json();
        console.log('[Files] Operation result:', result);
        
        if (result.success) {
            if (result.result_type === 'text') {
                // Show extracted text
                alert(`Extracted Text:\n\n${result.text}`);
            } else {
                // Download result file
                const downloadUrl = `${apiUrl}/api/files/download/${result.result_file_id}`;
                console.log('[Files] Downloading from:', downloadUrl);
                window.open(downloadUrl, '_blank');
                alert(`Operation successful! File: ${result.result_filename}`);
            }
        } else {
            alert('Operation failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('[Files] Operation failed:', error);
        alert('Operation failed: ' + error.message);
    }
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/**
 * Configuration Management
 */
async function loadConfiguration() {
    const container = document.getElementById('config-list');
    
    try {
        // Show loading indicator
        container.innerHTML = '<div class="loading-indicator">Loading configuration...</div>';
        
        // Add timeout to fetch request (10 seconds)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        const response = await fetch(`${apiUrl}/api/config`, {
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('config-path').textContent = result.config_path;
            
            if (result.keys.length === 0) {
                container.innerHTML = '<p class="empty-state">No configuration keys set</p>';
                return;
            }
            
            container.innerHTML = `
                <div class="config-items">
                    ${result.keys.map(key => `
                        <div class="config-item">
                            <div class="config-key">${key}</div>
                            <div class="config-value">${result.config[key]}</div>
                            <div class="config-actions">
                                <button class="edit-config" data-key="${key}">Edit Edit</button>
                                <button class="delete-config" data-key="${key}">Delete Delete</button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
            
            // Add event handlers
            document.querySelectorAll('.edit-config').forEach(btn => {
                btn.addEventListener('click', () => editConfigKey(btn.dataset.key));
            });
            
            document.querySelectorAll('.delete-config').forEach(btn => {
                btn.addEventListener('click', () => deleteConfigKey(btn.dataset.key));
            });
        }
    } catch (error) {
        console.error('[Config] Load failed:', error);
        if (error.name === 'AbortError') {
            container.innerHTML = '<p class="error-state">Configuration loading timed out. Please check if the backend is running.</p>';
        } else {
            container.innerHTML = '<p class="error-state">Failed to load configuration. Please try again.</p>';
        }
    }
}

// Config modal state
let configModalMode = 'add';
let configModalEditKey = null;

function showConfigModal(mode = 'add', existingKey = null) {
    configModalMode = mode;
    configModalEditKey = existingKey;
    
    const modal = document.getElementById('config-modal');
    const title = document.getElementById('config-modal-title');
    const keySelect = document.getElementById('config-key-select');
    const customKeyGroup = document.getElementById('custom-key-group');
    const valueInput = document.getElementById('config-value-input');
    
    if (mode === 'edit') {
        title.textContent = `Edit ${existingKey}`;
        keySelect.value = 'CUSTOM';
        keySelect.disabled = true;
        customKeyGroup.classList.add('visible');
        document.getElementById('config-key-input').value = existingKey;
        valueInput.value = '';
        valueInput.placeholder = 'Enter new value';
    } else {
        title.textContent = 'Add API Key';
        keySelect.value = '';
        keySelect.disabled = false;
        customKeyGroup.classList.remove('visible');
        document.getElementById('config-key-input').value = '';
        valueInput.value = '';
        valueInput.placeholder = 'Enter your API key';
    }
    
    modal.classList.add('active');
    valueInput.focus();
}

function hideConfigModal() {
    const modal = document.getElementById('config-modal');
    modal.classList.remove('active');
    
    // Reset form
    document.getElementById('config-key-select').value = '';
    document.getElementById('config-key-input').value = '';
    document.getElementById('config-value-input').value = '';
    document.getElementById('config-file-input').value = '';
    document.getElementById('custom-key-group').classList.remove('visible');
    document.getElementById('file-upload-group').classList.remove('visible');
    document.getElementById('text-value-group').classList.remove('hidden');
}

async function saveConfigFromModal() {
    const keySelect = document.getElementById('config-key-select');
    const customKeyInput = document.getElementById('config-key-input');
    const valueInput = document.getElementById('config-value-input');
    const fileInput = document.getElementById('config-file-input');
    
    let key;
    if (configModalMode === 'edit') {
        key = configModalEditKey;
    } else if (keySelect.value === 'CUSTOM') {
        key = customKeyInput.value.trim().toUpperCase();
    } else {
        key = keySelect.value;
    }
    
    if (!key) {
        alert('Please select or enter a key name');
        return;
    }
    
    let value;
    
    // Handle Google Credentials JSON file upload
    if (key === 'GOOGLE_CREDENTIALS' && fileInput.files.length > 0) {
        try {
            const file = fileInput.files[0];
            const text = await file.text();
            const jsonData = JSON.parse(text);
            
            // Store the entire JSON as a string for GOOGLE_CREDENTIALS
            value = JSON.stringify(jsonData);
            
            // Also save to the proper location for Google OAuth
            const credPath = '~/.clai/credentials.json';
            console.log('[Config] Google credentials will be saved to both api_keys.json and ~/.clai/credentials.json');
        } catch (error) {
            alert('Invalid JSON file. Please upload a valid Google Cloud credentials file.');
            console.error('[Config] JSON parse error:', error);
            return;
        }
    } else {
        value = valueInput.value.trim();
    }
    
    if (!value) {
        alert('Please enter a value or upload a file');
        return;
    }
    
    try {
        const response = await fetch(`${apiUrl}/api/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key, value })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // If it's Google credentials, also save to the OAuth credentials file
            if (key === 'GOOGLE_CREDENTIALS') {
                try {
                    const credResponse = await fetch(`${apiUrl}/api/config/google-oauth`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ credentials: value })
                    });
                    const credResult = await credResponse.json();
                    console.log('[Config] Google OAuth credentials saved:', credResult.success);
                } catch (error) {
                    console.warn('[Config] Failed to save Google OAuth credentials separately:', error);
                }
            }
            
            hideConfigModal();
            await loadConfiguration();
        } else {
            alert('Failed to save configuration');
        }
    } catch (error) {
        console.error('[Config] Save failed:', error);
        alert('Failed to save configuration');
    }
}

async function addConfigKey() {
    showConfigModal('add');
}

async function editConfigKey(key) {
    showConfigModal('edit', key);
}

async function deleteConfigKey(key) {
    if (!confirm(`Delete configuration key "${key}"?`)) return;
    
    try {
        const response = await fetch(`${apiUrl}/api/config/${key}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            await loadConfiguration();
        }
    } catch (error) {
        console.error('[Config] Delete failed:', error);
    }
}

async function downloadConfiguration() {
    window.open(`${apiUrl}/api/config/download`, '_blank');
}

/**
 * Settings Management
 */
async function loadCurrentShortcut() {
    try {
        const result = await window.electronAPI.getKeyboardShortcut();
        const shortcutInput = document.getElementById('shortcut-input');
        if (shortcutInput) {
            shortcutInput.value = result.shortcut;
        }
    } catch (error) {
        console.error('[Settings] Failed to load shortcut:', error);
    }
}

async function loadSettings() {
    try {
        const response = await fetch(`${apiUrl}/api/settings`);
        const result = await response.json();
        
        if (result.success) {
            const shortcutInput = document.getElementById('shortcut-input');
            if (shortcutInput) {
                shortcutInput.value = result.settings.keyboard_shortcut || 'CommandOrControl+Shift+A';
            }
            
            const autoStartCheckbox = document.getElementById('auto-start-checkbox');
            if (autoStartCheckbox) {
                autoStartCheckbox.checked = result.settings.auto_start || false;
            }
        }
    } catch (error) {
        console.error('[Settings] Load failed:', error);
    }
}

async function updateSettings(settings) {
    try {
        const response = await fetch(`${apiUrl}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('[Settings] Updated:', settings);
        }
    } catch (error) {
        console.error('[Settings] Update failed:', error);
    }
}

function setupNewFeatureHandlers() {
    // New Chat button
    const newChatBtn = document.getElementById('new-chat-button');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', createNewChatSession);
    }
    
    // Attach File button
    const attachFileBtn = document.getElementById('attach-file-button');
    const fileInput = document.getElementById('file-input');
    if (attachFileBtn && fileInput) {
        attachFileBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileUpload(e.target.files);
            }
        });
    }
    
    // File upload area
    const uploadArea = document.getElementById('file-upload-area');
    const filesInput = document.getElementById('files-input');
    const selectFilesBtn = document.getElementById('select-files-button');
    
    if (uploadArea && filesInput && selectFilesBtn) {
        selectFilesBtn.addEventListener('click', () => filesInput.click());
        filesInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileUpload(e.target.files);
            }
        });
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('drag-over');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            if (e.dataTransfer.files.length > 0) {
                handleFileUpload(e.dataTransfer.files);
            }
        });
    }
    
    // File operations
    document.querySelectorAll('.operation-button').forEach(btn => {
        btn.addEventListener('click', () => {
            performFileOperation(btn.dataset.operation);
        });
    });
    
    // Config management
    const addConfigBtn = document.getElementById('add-config-key');
    if (addConfigBtn) {
        addConfigBtn.addEventListener('click', addConfigKey);
    }
    
    const downloadConfigBtn = document.getElementById('download-config');
    if (downloadConfigBtn) {
        downloadConfigBtn.addEventListener('click', downloadConfiguration);
    }
    
    // Config modal handlers
    const configModal = document.getElementById('config-modal');
    const configModalClose = document.getElementById('config-modal-close');
    const configModalCancel = document.getElementById('config-modal-cancel');
    const configModalSave = document.getElementById('config-modal-save');
    const configKeySelect = document.getElementById('config-key-select');
    
    if (configModalClose) {
        configModalClose.addEventListener('click', hideConfigModal);
    }
    
    if (configModalCancel) {
        configModalCancel.addEventListener('click', hideConfigModal);
    }
    
    if (configModalSave) {
        configModalSave.addEventListener('click', saveConfigFromModal);
    }
    
    // Close modal on background click
    if (configModal) {
        configModal.addEventListener('click', (e) => {
            if (e.target === configModal) {
                hideConfigModal();
            }
        });
    }
    
    // Show/hide custom key input based on selection
    if (configKeySelect) {
        configKeySelect.addEventListener('change', (e) => {
            const customKeyGroup = document.getElementById('custom-key-group');
            const fileUploadGroup = document.getElementById('file-upload-group');
            const textValueGroup = document.getElementById('text-value-group');
            
            // Hide all optional groups first
            customKeyGroup.classList.remove('visible');
            fileUploadGroup.classList.remove('visible');
            textValueGroup.classList.remove('hidden');
            
            if (e.target.value === 'CUSTOM') {
                customKeyGroup.classList.add('visible');
                document.getElementById('config-key-input').focus();
            } else if (e.target.value === 'GOOGLE_CREDENTIALS') {
                fileUploadGroup.classList.add('visible');
                textValueGroup.classList.add('hidden');
            }
        });
    }
    
    // Refresh buttons
    const refreshChatsBtn = document.getElementById('refresh-chats');
    if (refreshChatsBtn) {
        refreshChatsBtn.addEventListener('click', loadChatHistory);
    }
    
    // Settings
    const editShortcutBtn = document.getElementById('edit-shortcut');
    const shortcutInput = document.getElementById('shortcut-input');
    if (editShortcutBtn && shortcutInput) {
        // Load current shortcut
        loadCurrentShortcut();
        
        editShortcutBtn.addEventListener('click', () => {
            shortcutInput.readOnly = false;
            shortcutInput.focus();
            shortcutInput.select();
        });
        
        shortcutInput.addEventListener('blur', async () => {
            shortcutInput.readOnly = true;
            const newShortcut = shortcutInput.value.trim();
            if (newShortcut) {
                try {
                    const result = await window.electronAPI.updateKeyboardShortcut(newShortcut);
                    if (result.success) {
                        await updateSettings({ keyboard_shortcut: result.shortcut });
                        alert(`Shortcut updated to: ${result.shortcut}`);
                    } else {
                        alert('Failed to update shortcut. Please try a different combination.');
                        await loadCurrentShortcut();
                    }
                } catch (error) {
                    console.error('[Settings] Failed to update shortcut:', error);
                    alert('Failed to update shortcut');
                    await loadCurrentShortcut();
                }
            }
        });
    }
    
    const autoStartCheckbox = document.getElementById('auto-start-checkbox');
    if (autoStartCheckbox) {
        autoStartCheckbox.addEventListener('change', async () => {
            await updateSettings({ auto_start: autoStartCheckbox.checked });
        });
    }
}

/**
 * Show email confirmation dialog
 */
function showEmailConfirmation(draft) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    const messageId = `msg-draft-${draft.draft_id}`;
    
    messageDiv.id = messageId;
    messageDiv.className = 'message assistant email-draft';
    messageDiv.innerHTML = `
        <div class="message-content">
            <h4>Email Draft - Review & Confirm</h4>
            <div class="draft-details">
                <div class="draft-field"><strong>To:</strong> ${escapeHtml(draft.to)}</div>
                ${draft.cc ? `<div class="draft-field"><strong>CC:</strong> ${escapeHtml(draft.cc)}</div>` : ''}
                <div class="draft-field"><strong>Subject:</strong> ${escapeHtml(draft.subject)}</div>
                <div class="draft-field draft-body">
                    <strong>Body:</strong>
                    <div class="draft-body-content">${escapeHtml(draft.body)}</div>
                </div>
            </div>
            <div class="draft-actions">
                <button class="button-primary" onclick="confirmSendEmail('${draft.draft_id}', '${messageId}')">
                    Send Email
                </button>
                <button class="button-secondary" onclick="cancelEmailDraft('${draft.draft_id}', '${messageId}')">
                    Cancel
                </button>
            </div>
        </div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

/**
 * Confirm and send email
 */
async function confirmSendEmail(draftId, messageId) {
    const processingId = addProcessingMessage('Sending email...');
    
    try {
        const response = await fetch(`${apiUrl}/api/email/send/${draftId}`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to send email');
        }
        
        const data = await response.json();
        
        removeMessage(processingId);
        removeMessage(messageId);
        
        addChatMessage('assistant', `Email sent successfully!\n\n${data.result}`);
    } catch (error) {
        console.error('[Email] Send failed:', error);
        removeMessage(processingId);
        addChatMessage('error', `Failed to send email: ${error.message}`);
    }
}

/**
 * Cancel email draft
 */
async function cancelEmailDraft(draftId, messageId) {
    try {
        await fetch(`${apiUrl}/api/email/draft/${draftId}`, {
            method: 'DELETE'
        });
        
        removeMessage(messageId);
        addChatMessage('system', 'Email draft cancelled.');
    } catch (error) {
        console.error('[Email] Cancel failed:', error);
        addChatMessage('error', `Failed to cancel draft: ${error.message}`);
    }
}

/**
 * Display email list in chat with nice formatting
 */
function displayEmailListInChat(rawOutput) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    const messageId = `msg-${Date.now()}`;
    
    messageDiv.id = messageId;
    messageDiv.className = 'message assistant email-list-message';
    
    // Parse email entries from raw output
    const emails = [];
    const lines = rawOutput.split('\n');
    let currentEmail = null;
    
    for (const line of lines) {
        if (line.startsWith('From:')) {
            if (currentEmail) emails.push(currentEmail);
            currentEmail = { from: line.substring(5).trim() };
        } else if (currentEmail) {
            if (line.startsWith('Subject:')) {
                currentEmail.subject = line.substring(8).trim();
            } else if (line.startsWith('Date:')) {
                currentEmail.date = line.substring(5).trim();
            } else if (line.startsWith('Body:')) {
                currentEmail.body = line.substring(5).trim();
            }
        }
    }
    if (currentEmail) emails.push(currentEmail);
    
    if (emails.length === 0) {
        // Fallback to plain text
        addChatMessage('assistant', rawOutput);
        return;
    }
    
    // Build nice email cards
    let html = '<div class="chat-email-list">';
    html += `<h4 class="email-list-title">Emails (${emails.length})</h4>`;
    
    emails.forEach((email, index) => {
        html += `
            <div class="chat-email-card">
                <div class="chat-email-header">
                    <strong>${escapeHtml(email.from || 'Unknown')}</strong>
                    <span class="chat-email-date">${escapeHtml(email.date || '')}</span>
                </div>
                <div class="chat-email-subject">${escapeHtml(email.subject || 'No Subject')}</div>
                ${email.body ? `<div class="chat-email-preview">${escapeHtml(email.body.substring(0, 100))}${email.body.length > 100 ? '...' : ''}</div>` : ''}
            </div>
        `;
    });
    
    html += '</div>';
    
    messageDiv.innerHTML = `<div class="message-content">${html}</div>`;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

console.log('[App] Renderer script loaded with new features');
