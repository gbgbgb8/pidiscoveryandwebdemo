// Pi Control Center - Frontend JavaScript

const API_BASE = '';
let isStreaming = false;
let isRecording = false;
let gpioState = { 17: false, 27: false, 22: false, 23: false };

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    refreshStats();
    loadSystemInfo();
    
    // Auto-refresh stats every 10 seconds
    setInterval(refreshStats, 10000);
});

// Toast notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// API helper
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'API error');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        showToast(error.message, 'error');
        throw error;
    }
}

// System Stats
async function refreshStats() {
    try {
        const data = await apiCall('/api/stats');
        
        document.getElementById('cpu-temp').textContent = `${data.temperature}°C`;
        document.getElementById('ram-usage').textContent = `${data.ram_percent}%`;
        document.getElementById('disk-usage').textContent = `${data.disk_percent}%`;
        document.getElementById('battery-level').textContent = data.battery ? `${data.battery}%` : 'N/A';
        document.getElementById('stats-time').textContent = new Date().toLocaleTimeString();
        
        // Update connection status
        document.getElementById('connection-status').className = 'status connected';
        document.getElementById('connection-status').innerHTML = '<i class="fas fa-circle"></i> Connected';
        
    } catch (error) {
        document.getElementById('connection-status').className = 'status disconnected';
        document.getElementById('connection-status').innerHTML = '<i class="fas fa-circle"></i> Disconnected';
    }
}

// System Info
async function loadSystemInfo() {
    try {
        const data = await apiCall('/api/info');
        
        document.getElementById('hostname').textContent = data.hostname;
        document.getElementById('pi-model').textContent = data.model;
        document.getElementById('pi-os').textContent = data.os;
        document.getElementById('pi-ip').textContent = data.ip;
        document.getElementById('pi-uptime').textContent = data.uptime;
        
    } catch (error) {
        console.error('Failed to load system info');
    }
}

// Camera Controls
function toggleStream() {
    const btn = document.getElementById('btn-stream-toggle');
    const stream = document.getElementById('camera-stream');
    const placeholder = document.getElementById('camera-placeholder');
    
    if (isStreaming) {
        // Stop stream
        stream.src = '';
        stream.style.display = 'none';
        placeholder.style.display = 'flex';
        btn.innerHTML = '<i class="fas fa-play"></i> Start Stream';
        isStreaming = false;
        showToast('Camera stream stopped', 'info');
    } else {
        // Start stream
        stream.src = '/api/camera/stream?' + Date.now();
        stream.style.display = 'block';
        placeholder.style.display = 'none';
        btn.innerHTML = '<i class="fas fa-stop"></i> Stop Stream';
        isStreaming = true;
        showToast('Camera stream started', 'success');
    }
}

async function takePhoto() {
    showToast('Taking photo...', 'info');
    try {
        const response = await fetch('/api/camera/photo');
        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            
            const resultDiv = document.getElementById('photo-result');
            resultDiv.innerHTML = `
                <img src="${url}" alt="Captured photo">
                <a href="${url}" download="pi_photo_${Date.now()}.jpg" class="btn btn-small" style="margin-top:10px;">
                    <i class="fas fa-download"></i> Download
                </a>
            `;
            showToast('Photo captured!', 'success');
        } else {
            throw new Error('Failed to capture photo');
        }
    } catch (error) {
        showToast('Failed to take photo', 'error');
    }
}

// Audio Controls
async function toggleRecording() {
    const btn = document.getElementById('btn-record');
    const status = document.getElementById('recording-status');
    const duration = document.getElementById('record-duration').value;
    
    if (isRecording) return;
    
    isRecording = true;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-circle"></i> Recording...';
    status.textContent = `Recording for ${duration} seconds...`;
    status.className = 'status-text recording';
    
    try {
        const response = await fetch(`/api/audio/record?duration=${duration}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            
            const audio = document.getElementById('recorded-audio');
            audio.src = url;
            audio.style.display = 'block';
            
            showToast('Recording complete!', 'success');
            status.textContent = 'Recording saved. Press play to listen.';
            status.className = 'status-text';
        } else {
            throw new Error('Recording failed');
        }
    } catch (error) {
        showToast('Recording failed', 'error');
        status.textContent = 'Recording failed';
        status.className = 'status-text';
    }
    
    isRecording = false;
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-circle"></i> Record';
}

async function speak() {
    const text = document.getElementById('tts-text').value.trim();
    if (!text) {
        showToast('Please enter text to speak', 'error');
        return;
    }
    
    try {
        await apiCall('/api/audio/speak', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        showToast('Speaking...', 'success');
    } catch (error) {
        showToast('Text-to-speech failed', 'error');
    }
}

async function playSound(sound) {
    try {
        await apiCall(`/api/audio/sound/${sound}`, { method: 'POST' });
        showToast(`Playing ${sound}`, 'success');
    } catch (error) {
        showToast('Failed to play sound', 'error');
    }
}

async function setVolume(value) {
    document.getElementById('volume-value').textContent = `${value}%`;
    try {
        await apiCall('/api/audio/volume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ volume: parseInt(value) })
        });
    } catch (error) {
        console.error('Failed to set volume');
    }
}

// GPIO Controls
async function toggleGPIO(pin) {
    try {
        const newState = !gpioState[pin];
        await apiCall('/api/gpio/set', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin, state: newState })
        });
        
        gpioState[pin] = newState;
        updateLED(pin, newState);
        showToast(`GPIO ${pin} ${newState ? 'ON' : 'OFF'}`, 'success');
        
    } catch (error) {
        showToast(`Failed to toggle GPIO ${pin}`, 'error');
    }
}

function updateLED(pin, state) {
    const led = document.getElementById(`led-${pin}`);
    if (led) {
        led.className = state ? 'led on' : 'led';
    }
}

async function blinkAll() {
    showToast('Blinking all LEDs...', 'info');
    try {
        await apiCall('/api/gpio/blink', { method: 'POST' });
        
        // Visual feedback
        const pins = [17, 27, 22, 23];
        let count = 0;
        const interval = setInterval(() => {
            pins.forEach(pin => {
                updateLED(pin, count % 2 === 0);
            });
            count++;
            if (count > 6) {
                clearInterval(interval);
                pins.forEach(pin => updateLED(pin, gpioState[pin]));
            }
        }, 300);
        
    } catch (error) {
        showToast('Blink failed', 'error');
    }
}

async function allOff() {
    try {
        await apiCall('/api/gpio/off', { method: 'POST' });
        
        [17, 27, 22, 23].forEach(pin => {
            gpioState[pin] = false;
            updateLED(pin, false);
        });
        
        showToast('All GPIOs turned off', 'success');
    } catch (error) {
        showToast('Failed to turn off GPIOs', 'error');
    }
}

// System Controls
async function runDiscovery() {
    showToast('Running discovery...', 'info');
    try {
        const data = await apiCall('/api/discovery/run', { method: 'POST' });
        showToast('Discovery complete!', 'success');
        refreshStats();
        loadSystemInfo();
    } catch (error) {
        showToast('Discovery failed', 'error');
    }
}

function openDashboard() {
    window.open('/dashboard', '_blank');
}

// Terminal
async function runCommand() {
    const input = document.getElementById('terminal-command');
    const output = document.getElementById('terminal-output');
    const command = input.value.trim();
    
    if (!command) return;
    
    // Add command to output
    output.innerHTML += `<div class="terminal-line command">$ ${command}</div>`;
    input.value = '';
    
    try {
        const data = await apiCall('/api/terminal/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command })
        });
        
        // Add output
        if (data.output) {
            const lines = data.output.split('\n');
            lines.forEach(line => {
                output.innerHTML += `<div class="terminal-line">${escapeHtml(line)}</div>`;
            });
        }
        if (data.error) {
            output.innerHTML += `<div class="terminal-line error">${escapeHtml(data.error)}</div>`;
        }
        
    } catch (error) {
        output.innerHTML += `<div class="terminal-line error">Error: ${error.message}</div>`;
    }
    
    // Scroll to bottom
    output.scrollTop = output.scrollHeight;
}

function handleTerminalKey(event) {
    if (event.key === 'Enter') {
        runCommand();
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Settings
async function loadSettings() {
    try {
        const data = await apiCall('/api/settings');
        document.getElementById('toggle-announcement').checked = data.announcement_enabled;
        document.getElementById('toggle-autostart').checked = data.autostart_enabled;
    } catch (error) {
        console.error('Failed to load settings');
    }
}

async function toggleSetting(setting, value) {
    try {
        const body = {};
        body[setting] = value;
        await apiCall('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        
        const label = setting === 'announcement_enabled' ? 'Startup announcement' : 'Start on boot';
        showToast(`${label} ${value ? 'enabled' : 'disabled'}`, 'success');
    } catch (error) {
        showToast('Failed to update setting', 'error');
        // Revert toggle
        loadSettings();
    }
}

async function playAnnouncement() {
    showToast('Playing announcement...', 'info');
    try {
        await apiCall('/api/announce', { method: 'POST' });
        showToast('Announcement played', 'success');
    } catch (error) {
        showToast('Failed to play announcement', 'error');
    }
}

// === AUDIO VISUALIZER ===
let visualizerInterval = null;

async function updateVisualizer() {
    try {
        const data = await fetch('/api/audio/levels').then(r => r.json());
        const level = data.level || 0;
        document.getElementById('visualizer-bar').style.width = level + '%';
        document.getElementById('visualizer-level').textContent = `Level: ${level}%`;
    } catch (error) {
        console.error('Visualizer error');
    }
}

function toggleVisualizer() {
    const btn = document.getElementById('btn-visualizer');
    
    if (visualizerInterval) {
        clearInterval(visualizerInterval);
        visualizerInterval = null;
        btn.innerHTML = '<i class="fas fa-play"></i> Start';
        btn.className = 'btn btn-primary';
        document.getElementById('visualizer-bar').style.width = '0%';
        document.getElementById('visualizer-level').textContent = 'Level: --';
    } else {
        updateVisualizer();
        visualizerInterval = setInterval(updateVisualizer, 500);
        btn.innerHTML = '<i class="fas fa-stop"></i> Stop';
        btn.className = 'btn btn-danger';
    }
}

// === TIMELAPSE ===
let timelapseRunning = false;

async function refreshTimelapse() {
    try {
        const data = await apiCall('/api/timelapse/status');
        timelapseRunning = data.running;
        
        document.getElementById('timelapse-status').textContent = data.running ? 'Running...' : 'Stopped';
        document.getElementById('timelapse-count').textContent = `${data.count} images`;
        
        const btn = document.getElementById('btn-timelapse');
        btn.innerHTML = data.running ? '<i class="fas fa-stop"></i> Stop' : '<i class="fas fa-play"></i> Start';
        btn.className = data.running ? 'btn btn-danger' : 'btn btn-primary';
        
        const gallery = document.getElementById('timelapse-gallery');
        gallery.innerHTML = data.images.map(img => 
            `<img src="/api/timelapse/image/${img.name}" class="timelapse-thumb" onclick="window.open('/api/timelapse/image/${img.name}')" title="${img.name}">`
        ).join('');
    } catch (error) {
        console.error('Failed to refresh timelapse');
    }
}

async function toggleTimelapse() {
    if (timelapseRunning) {
        await apiCall('/api/timelapse/stop', { method: 'POST' });
        showToast('Timelapse stopped', 'success');
    } else {
        const interval = document.getElementById('timelapse-interval').value;
        const duration = document.getElementById('timelapse-duration').value;
        await apiCall('/api/timelapse/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ interval: parseInt(interval), duration: parseInt(duration) })
        });
        showToast('Timelapse started', 'success');
    }
    setTimeout(refreshTimelapse, 1000);
}

async function clearTimelapse() {
    showModal('Clear Timelapse', 'Delete all timelapse images?', async () => {
        await apiCall('/api/timelapse/clear', { method: 'DELETE' });
        showToast('Timelapse cleared', 'success');
        refreshTimelapse();
    });
}

// Refresh timelapse status periodically
setInterval(() => {
    if (timelapseRunning) refreshTimelapse();
}, 5000);

// Load timelapse on page load
document.addEventListener('DOMContentLoaded', () => refreshTimelapse());

// === FILE BROWSER ===
let currentPath = '/home/pi';

async function loadFiles(path = currentPath) {
    currentPath = path;
    const list = document.getElementById('files-list');
    list.innerHTML = '<div class="file-item loading">Loading...</div>';
    
    try {
        const data = await apiCall(`/api/files/list?path=${encodeURIComponent(path)}`);
        updateBreadcrumb(data.path);
        
        if (data.items.length === 0) {
            list.innerHTML = '<div class="file-item loading">Empty directory</div>';
            return;
        }
        
        list.innerHTML = data.items.map(item => `
            <div class="file-item" onclick="${item.is_dir ? `navigateTo('${item.path}')` : `previewFile('${item.path}')`}">
                <i class="fas ${item.is_dir ? 'fa-folder folder' : 'fa-file'} file-icon"></i>
                <span class="file-name">${escapeHtml(item.name)}</span>
                <span class="file-size">${item.size ? formatSize(item.size) : ''}</span>
                <div class="file-actions" onclick="event.stopPropagation()">
                    ${!item.is_dir ? `<button onclick="downloadFile('${item.path}')" class="btn btn-small" title="Download"><i class="fas fa-download"></i></button>` : ''}
                    <button onclick="deleteItem('${item.path}', ${item.is_dir})" class="btn btn-small btn-danger" title="Delete"><i class="fas fa-trash"></i></button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        list.innerHTML = '<div class="file-item loading">Failed to load</div>';
    }
}

function updateBreadcrumb(path) {
    const bc = document.getElementById('files-breadcrumb');
    const parts = path.split('/').filter(p => p);
    let html = '<span class="breadcrumb-item" onclick="navigateTo(\'/\')">/</span>';
    let cumPath = '';
    parts.forEach((part, i) => {
        cumPath += '/' + part;
        const p = cumPath;
        html += `<span class="breadcrumb-sep">/</span><span class="breadcrumb-item" onclick="navigateTo('${p}')">${part}</span>`;
    });
    bc.innerHTML = html;
}

function navigateTo(path) {
    closePreview();
    loadFiles(path);
}

function navigateUp() {
    const parent = currentPath.split('/').slice(0, -1).join('/') || '/';
    navigateTo(parent);
}

function refreshFiles() {
    loadFiles(currentPath);
}

async function previewFile(path) {
    try {
        const data = await apiCall(`/api/files/read?path=${encodeURIComponent(path)}`);
        document.getElementById('preview-filename').textContent = path.split('/').pop();
        document.getElementById('preview-content').textContent = data.content;
        document.getElementById('files-preview').style.display = 'block';
    } catch (error) {
        showToast('Cannot preview this file', 'error');
    }
}

function closePreview() {
    document.getElementById('files-preview').style.display = 'none';
}

function downloadFile(path) {
    window.open(`/api/files/download?path=${encodeURIComponent(path)}`, '_blank');
}

async function uploadFile(input) {
    if (!input.files.length) return;
    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('path', currentPath);
    
    showToast(`Uploading ${file.name}...`, 'info');
    try {
        const resp = await fetch('/api/files/upload', { method: 'POST', body: formData });
        const data = await resp.json();
        if (data.success) {
            showToast('Upload complete', 'success');
            refreshFiles();
        } else {
            showToast(data.error || 'Upload failed', 'error');
        }
    } catch (error) {
        showToast('Upload failed', 'error');
    }
    input.value = '';
}

function showNewFolderDialog() {
    const name = prompt('New folder name:');
    if (name) createFolder(name);
}

async function createFolder(name) {
    try {
        await apiCall('/api/files/mkdir', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: currentPath + '/' + name })
        });
        showToast('Folder created', 'success');
        refreshFiles();
    } catch (error) {
        showToast('Failed to create folder', 'error');
    }
}

function deleteItem(path, isDir) {
    const name = path.split('/').pop();
    showModal(
        'Delete ' + (isDir ? 'Folder' : 'File'),
        `Are you sure you want to delete "${name}"?${isDir ? ' This will delete all contents.' : ''}`,
        async () => {
            try {
                await fetch(`/api/files/delete?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
                showToast('Deleted', 'success');
                refreshFiles();
            } catch (error) {
                showToast('Delete failed', 'error');
            }
        }
    );
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// Load files on page load
document.addEventListener('DOMContentLoaded', () => loadFiles());

// === LOG VIEWER ===
let logAutoRefreshInterval = null;
let allLogLines = [];

async function loadLogs() {
    const source = document.getElementById('log-source').value;
    const lines = document.getElementById('log-lines').value;
    const output = document.getElementById('logs-output');
    
    output.innerHTML = '<div class="log-line">Loading...</div>';
    
    try {
        const data = await apiCall(`/api/logs/read?source=${source}&lines=${lines}`);
        allLogLines = data.content.split('\n');
        renderLogs();
    } catch (error) {
        output.innerHTML = '<div class="log-line">Failed to load logs</div>';
    }
}

function renderLogs() {
    const filter = document.getElementById('log-filter').value.toLowerCase();
    const output = document.getElementById('logs-output');
    
    const filtered = filter 
        ? allLogLines.filter(line => line.toLowerCase().includes(filter))
        : allLogLines;
    
    output.innerHTML = filtered.map(line => {
        const highlighted = filter && line.toLowerCase().includes(filter) ? ' highlight' : '';
        return `<div class="log-line${highlighted}">${escapeHtml(line)}</div>`;
    }).join('');
    
    // Scroll to bottom
    output.scrollTop = output.scrollHeight;
}

function filterLogs() {
    renderLogs();
}

function toggleLogAutoRefresh() {
    const enabled = document.getElementById('log-auto-refresh').checked;
    
    if (enabled) {
        loadLogs();
        logAutoRefreshInterval = setInterval(loadLogs, 5000);
    } else {
        if (logAutoRefreshInterval) {
            clearInterval(logAutoRefreshInterval);
            logAutoRefreshInterval = null;
        }
    }
}

// Modal functions
function showModal(title, message, onConfirm, confirmText = 'Confirm', confirmClass = 'btn-danger') {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-message').textContent = message;
    const confirmBtn = document.getElementById('modal-confirm');
    confirmBtn.textContent = confirmText;
    confirmBtn.className = `btn ${confirmClass}`;
    confirmBtn.onclick = () => {
        closeModal();
        onConfirm();
    };
    document.getElementById('modal-overlay').classList.add('active');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('active');
}

// Power controls
function confirmPower(action) {
    const isReboot = action === 'reboot';
    showModal(
        isReboot ? 'Reboot Pi' : 'Shutdown Pi',
        isReboot ? 'Are you sure you want to reboot? You will lose connection temporarily.' : 'Are you sure you want to shutdown? You will need physical access to turn it back on.',
        () => executePower(action),
        isReboot ? 'Reboot' : 'Shutdown',
        isReboot ? 'btn-warning' : 'btn-danger'
    );
}

async function executePower(action) {
    showToast(`${action === 'reboot' ? 'Rebooting' : 'Shutting down'}...`, 'info');
    try {
        await apiCall(`/api/power/${action}`, { method: 'POST' });
        showToast(`${action === 'reboot' ? 'Reboot' : 'Shutdown'} initiated`, 'success');
    } catch (error) {
        // May fail due to connection loss - that's expected
    }
}

// Load settings on page load
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
});
