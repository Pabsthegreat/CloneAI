/**
 * CloneAI Desktop - Preload Script
 * 
 * Security bridge between main process and renderer process.
 * Exposes only safe, controlled APIs to the renderer.
 */

const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
    /**
     * Execute a command
     */
    executeCommand: (command) => ipcRenderer.invoke('execute-command', command),
    
    /**
     * Get API base URL
     */
    getApiUrl: () => ipcRenderer.invoke('get-api-url'),
    
    /**
     * Open external URL
     */
    openExternal: (url) => ipcRenderer.invoke('open-external', url),
    
    /**
     * Open workflows folder in file explorer
     */
    openWorkflowsFolder: () => ipcRenderer.invoke('open-workflows-folder'),
    
    /**
     * Get system information
     */
    getSystemInfo: () => ipcRenderer.invoke('get-system-info'),
    
    /**
     * Event listeners
     */
    onPythonReady: (callback) => {
        ipcRenderer.on('python-ready', (event, data) => callback(data));
    },
    
    onPythonStopped: (callback) => {
        ipcRenderer.on('python-stopped', (event, data) => callback(data));
    },
    
    onWorkflowGenerated: (callback) => {
        ipcRenderer.on('workflow-generated', (event, data) => callback(data));
    },
    
    onNotification: (callback) => {
        ipcRenderer.on('notification', (event, data) => callback(data));
    },
    
    /**
     * Remove event listeners
     */
    removeAllListeners: (channel) => {
        ipcRenderer.removeAllListeners(channel);
    }
});

console.log('[Preload] Context bridge established');
