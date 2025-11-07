/**
 * CloneAI Desktop - Main Process
 * 
 * Manages the Electron application lifecycle, window creation,
 * Python backend process, and system tray integration.
 */

const { app, BrowserWindow, ipcMain, Tray, Menu, globalShortcut, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

// Global references
let mainWindow;
let pythonProcess;
let tray;
let pythonPort = 8765;

// Check if running in development mode
// In dev, we run from electron-app/ directory
// Detect by checking if we're inside node_modules/electron
const isDev = !app.isPackaged;

/**
 * Check if backend is already running
 */
async function isBackendRunning() {
    try {
        const response = await fetch(`http://127.0.0.1:${pythonPort}/api/health`, {
            method: 'GET',
            signal: AbortSignal.timeout(1000) // 1 second timeout
        });
        return response.ok;
    } catch (error) {
        return false;
    }
}

/**
 * Start Python backend server
 */
async function startPythonBackend() {
    // Check if already running
    const alreadyRunning = await isBackendRunning();
    if (alreadyRunning) {
        console.log('[Python] Backend already running, skipping startup');
        if (mainWindow) {
            mainWindow.webContents.send('python-ready', { port: pythonPort });
        }
        return;
    }
    
    console.log('[Python] Starting backend server...');
    
    // Determine Python path and working directory
    let pythonCmd;
    let pythonArgs;
    let workingDir;
    
    if (isDev) {
        // Development: Use project's virtual environment
        // We're in: CloneAI/electron-app/
        // We need: CloneAI/.venv/
        const projectRoot = path.join(__dirname, '..', '..');
        const venvPath = path.join(projectRoot, '.venv');
        
        if (process.platform === 'win32') {
            pythonCmd = path.join(venvPath, 'Scripts', 'python.exe');
        } else {
            pythonCmd = path.join(venvPath, 'bin', 'python');
        }
        
        pythonArgs = ['-m', 'agent.server.api'];
        workingDir = projectRoot;
        
        console.log(`[Python] Dev mode - Project root: ${projectRoot}`);
        
    } else {
        // Production: Use bundled Python or system Python
        const resourcesPath = process.resourcesPath;
        const venvPath = path.join(resourcesPath, '.venv');
        
        // Try venv first, fall back to system python
        if (process.platform === 'win32') {
            pythonCmd = path.join(venvPath, 'Scripts', 'python.exe');
        } else {
            pythonCmd = path.join(venvPath, 'bin', 'python');
        }
        
        // Check if venv exists, otherwise use system python
        if (!fs.existsSync(pythonCmd)) {
            console.log('[Python] Virtual environment not found, using system Python');
            pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
        }
        
        pythonArgs = ['-m', 'agent.server.api'];
        workingDir = resourcesPath;
    }
    
    console.log(`[Python] Command: ${pythonCmd}`);
    console.log(`[Python] Args: ${pythonArgs.join(' ')}`);
    console.log(`[Python] Working dir: ${workingDir}`);
    
    try {
        // Spawn Python process
        pythonProcess = spawn(pythonCmd, pythonArgs, {
            cwd: workingDir,
            stdio: ['pipe', 'pipe', 'pipe'],
            env: { ...process.env, PYTHONUNBUFFERED: '1' },
            detached: false
        });
        
        console.log(`[Python] Process spawned with PID: ${pythonProcess.pid}`);
    } catch (error) {
        console.error(`[Python] Failed to start: ${error.message}`);
        return;
    }
    
    // Handle stdout
    pythonProcess.stdout.on('data', (data) => {
        const output = data.toString().trim();
        console.log(`[Python] ${output}`);
        
        // Notify renderer when server is ready
        if (output.includes('Uvicorn running')) {
            console.log('[Python] ✓ Backend server ready!');
            if (mainWindow) {
                mainWindow.webContents.send('python-ready', { port: pythonPort });
            }
        }
    });
    
    // Handle stderr
    pythonProcess.stderr.on('data', (data) => {
        const error = data.toString().trim();
        console.error(`[Python Error] ${error}`);
    });
    
    // Handle process exit
    pythonProcess.on('close', (code) => {
        console.log(`[Python] Process exited with code ${code}`);
        pythonProcess = null;
        
        // Notify renderer
        if (mainWindow) {
            mainWindow.webContents.send('python-stopped', { code });
        }
    });
    
    pythonProcess.on('error', (err) => {
        console.error(`[Python] Failed to start: ${err.message}`);
    });
}

/**
 * Stop Python backend server
 */
function stopPythonBackend() {
    if (pythonProcess) {
        console.log('[Python] Stopping backend server...');
        pythonProcess.kill();
        pythonProcess = null;
    }
}

/**
 * Create the main application window
 */
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 600,
        titleBarStyle: 'hiddenInset',
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        // Only set icon if it exists
        ...(fs.existsSync(path.join(__dirname, '../assets/icon.png')) 
            ? { icon: path.join(__dirname, '../assets/icon.png') } 
            : {}),
        show: false // Don't show until ready
    });

    // Load the app
    if (isDev) {
        // Development: Load from local file
        mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
        mainWindow.webContents.openDevTools();
    } else {
        // Production: Load from file
        mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
    }

    // Show window when ready
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        console.log('[Electron] Window ready');
    });

    // Handle window close
    mainWindow.on('close', (event) => {
        // On macOS, hide instead of close
        if (process.platform === 'darwin' && !app.isQuitting) {
            event.preventDefault();
            mainWindow.hide();
        }
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

/**
 * Create system tray icon
 */
function createTray() {
    const trayIconPath = process.platform === 'darwin'
        ? path.join(__dirname, '../assets/tray-icon-Template.png')
        : path.join(__dirname, '../assets/tray-icon.png');
    
    // Fallback if tray icon doesn't exist
    const iconPath = fs.existsSync(trayIconPath)
        ? trayIconPath
        : path.join(__dirname, '../assets/icon.png');
    
    // Skip tray if no icon exists
    if (!fs.existsSync(iconPath)) {
        console.log('[Tray] No icon found, skipping tray creation');
        return;
    }
    
    tray = new Tray(iconPath);
    
    const contextMenu = Menu.buildFromTemplate([
        { 
            label: 'Show CloneAI', 
            click: () => {
                if (mainWindow) {
                    mainWindow.show();
                    mainWindow.focus();
                } else {
                    createWindow();
                }
            }
        },
        { type: 'separator' },
        {
            label: 'Open Workflows Folder',
            click: () => {
                const workflowsDir = path.join(app.getPath('home'), '.clai', 'workflows', 'custom');
                shell.openPath(workflowsDir);
            }
        },
        { type: 'separator' },
        { 
            label: 'Quit', 
            click: () => {
                app.isQuitting = true;
                app.quit();
            }
        }
    ]);
    
    tray.setToolTip('CloneAI Assistant');
    tray.setContextMenu(contextMenu);
    
    // Click tray icon to toggle window
    tray.on('click', () => {
        if (mainWindow) {
            if (mainWindow.isVisible()) {
                mainWindow.hide();
            } else {
                mainWindow.show();
                mainWindow.focus();
            }
        } else {
            createWindow();
        }
    });
}

/**
 * Register global shortcuts
 */
let currentShortcut = 'CommandOrControl+Shift+A';

function registerShortcuts(shortcut = currentShortcut) {
    // Unregister previous shortcut
    globalShortcut.unregisterAll();
    
    // Register new shortcut
    const ret = globalShortcut.register(shortcut, () => {
        if (mainWindow) {
            if (mainWindow.isVisible()) {
                mainWindow.hide();
            } else {
                mainWindow.show();
                mainWindow.focus();
            }
        } else {
            createWindow();
        }
    });
    
    if (ret) {
        currentShortcut = shortcut;
        console.log(`[Shortcuts] Registered: ${shortcut}`);
        return true;
    } else {
        console.log(`[Shortcuts] Failed to register: ${shortcut}`);
        return false;
    }
}

/**
 * Application lifecycle events
 */

app.whenReady().then(async () => {
    console.log('[Electron] App ready');
    console.log(`[Electron] Mode: ${isDev ? 'Development' : 'Production'}`);
    console.log(`[Electron] Platform: ${process.platform}`);
    
    // Always try to start Python backend (checks if already running first)
    console.log('[Electron] Checking/starting Python backend...');
    await startPythonBackend();
    
    // Small delay to let backend initialize
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Create window and UI
    createWindow();
    createTray();
    registerShortcuts();
    
    // macOS: Re-create window when dock icon is clicked
    app.on('activate', () => {
        if (mainWindow === null) {
            createWindow();
        } else if (mainWindow && typeof mainWindow.show === 'function') {
            mainWindow.show();
            mainWindow.focus();
        }
    });
});

// Quit when all windows are closed (except on macOS)
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// Before quit: cleanup
app.on('before-quit', () => {
    console.log('[Electron] Cleaning up...');
    app.isQuitting = true;
    stopPythonBackend();
    globalShortcut.unregisterAll();
});

app.on('will-quit', () => {
    globalShortcut.unregisterAll();
});

/**
 * IPC Handlers
 */

// Execute command
ipcMain.handle('execute-command', async (event, command) => {
    console.log(`[IPC] Execute command: ${command}`);
    return { success: true, message: 'Command will be handled via REST API' };
});

// Get API base URL
ipcMain.handle('get-api-url', async () => {
    return `http://127.0.0.1:${pythonPort}`;
});

// Open external links
ipcMain.handle('open-external', async (event, url) => {
    await shell.openExternal(url);
    return { success: true };
});

// Open workflows folder
ipcMain.handle('open-workflows-folder', async () => {
    const workflowsDir = path.join(app.getPath('home'), '.clai', 'workflows', 'custom');
    await shell.openPath(workflowsDir);
    return { success: true, path: workflowsDir };
});

// Get system info
ipcMain.handle('get-system-info', async () => {
    return {
        platform: process.platform,
        arch: process.arch,
        version: app.getVersion(),
        electronVersion: process.versions.electron,
        nodeVersion: process.versions.node,
        isDev: isDev
    };
});

// Update keyboard shortcut
ipcMain.handle('update-keyboard-shortcut', async (event, shortcut) => {
    try {
        const success = registerShortcuts(shortcut);
        return { success, shortcut: currentShortcut };
    } catch (error) {
        console.error('[IPC] Failed to update shortcut:', error);
        return { success: false, error: error.message };
    }
});

// Get current keyboard shortcut
ipcMain.handle('get-keyboard-shortcut', async () => {
    return { shortcut: currentShortcut };
});

console.log('[Electron] Main process loaded');
