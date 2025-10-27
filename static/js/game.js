// Main game controller
class GameController {
    constructor() {
        this.canvas = document.getElementById('game-canvas');
        this.renderer = new HexRenderer(this.canvas);
        this.socket = io();
        this.gameData = null;
        this.selectedHex = null;
        this.tooltip = null;
        this.pendingExploreHex = null;
        
        // Override renderer callbacks
        this.renderer.onHexClick = (hex) => this.handleHexClick(hex);
        this.renderer.onHexHover = (hex, mousePos) => this.handleHexHover(hex, mousePos);
        
        this.setupEventListeners();
        this.setupSocketEvents();
        this.setupServerConsole();
        this.loadGame();
        this.startRenderLoop();
    }
    
    setupEventListeners() {
        // Bottom controls
        document.getElementById('return-menu').addEventListener('click', () => this.returnToMenu());
        document.getElementById('toggle-fog').addEventListener('click', () => this.toggleFog());
        document.getElementById('center-view').addEventListener('click', () => this.centerView());
        
        // Hex info panel
        document.getElementById('generate-description').addEventListener('click', () => this.generateDescription());
        
        // Exploration modal
        document.getElementById('confirm-explore').addEventListener('click', () => this.confirmExploration());
        document.getElementById('cancel-explore').addEventListener('click', () => this.cancelExploration());
        
        // Close modal when clicking outside
        document.getElementById('exploration-modal').addEventListener('click', (e) => {
            if (e.target.id === 'exploration-modal') {
                this.cancelExploration();
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeydown(e));
    }
    
    setupSocketEvents() {
        this.socket.on('connected', (data) => {
            console.log('Connected to server:', data);
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
        });
        
        this.socket.on('map_synced', (data) => {
            console.log('Map synced from generator:', data);
            this.showMessage(`Map synced! ${data.hex_count} hexes loaded from generator.`, 'success');
            // Reload the map data
            this.loadGame();
        });
        
        this.socket.on('player_teleported', (data) => {
            // Only handle if this teleport is for the current session
            const currentSessionId = sessionStorage.getItem('session_id');
            if (data.session_id && data.session_id === currentSessionId) {
                console.log('Player teleported:', data);
                this.showMessage(data.message, 'info');
                
                // Reload the game data to get the fresh position (same as sync button)
                this.loadGame();
                
                // Center view on the new position after data loads
                setTimeout(() => {
                    if (this.gameData && this.gameData.player_position) {
                        this.renderer.centerOnHex(
                            this.gameData.player_position.q, 
                            this.gameData.player_position.r
                        );
                    }
                }, 100);
            }
        });
    }
    
    setupServerConsole() {
        this.consoleLogs = [];
        this.maxConsoleLogs = 100;
        
        // Console controls
        document.getElementById('toggle-console').addEventListener('click', () => {
            const console = document.getElementById('server-console');
            console.classList.toggle('minimized');
            const btn = document.getElementById('toggle-console');
            btn.textContent = console.classList.contains('minimized') ? '▼' : '▲';
        });
        
        document.getElementById('clear-console').addEventListener('click', () => {
            this.consoleLogs = [];
            document.getElementById('console-output').innerHTML = '';
        });
        
        // Override console methods to capture logs
        this.originalConsole = {
            log: console.log,
            error: console.error,
            warn: console.warn,
            info: console.info,
            debug: console.debug
        };
        
        // Intercept console calls
        console.log = (...args) => {
            this.addConsoleLog('info', args);
            this.originalConsole.log.apply(console, args);
        };
        
        console.error = (...args) => {
            this.addConsoleLog('error', args);
            this.originalConsole.error.apply(console, args);
        };
        
        console.warn = (...args) => {
            this.addConsoleLog('warning', args);
            this.originalConsole.warn.apply(console, args);
        };
        
        console.info = (...args) => {
            this.addConsoleLog('info', args);
            this.originalConsole.info.apply(console, args);
        };
        
        console.debug = (...args) => {
            this.addConsoleLog('debug', args);
            this.originalConsole.debug.apply(console, args);
        };
        
        // Initial log
        this.addConsoleLog('success', ['Server console initialized']);
        
        // Listen for server logs via WebSocket (using existing socket)
        this.setupServerLogListener();
    }
    
    addConsoleLog(type, args) {
        const timestamp = new Date().toLocaleTimeString();
        const message = args.map(arg => {
            if (typeof arg === 'object') {
                try {
                    return JSON.stringify(arg, null, 2);
                } catch (e) {
                    return String(arg);
                }
            }
            return String(arg);
        }).join(' ');
        
        const log = { timestamp, type, message };
        this.consoleLogs.push(log);
        
        // Limit logs
        if (this.consoleLogs.length > this.maxConsoleLogs) {
            this.consoleLogs.shift();
        }
        
        // Update UI
        this.updateConsoleDisplay(log);
    }
    
    updateConsoleDisplay(log) {
        const output = document.getElementById('console-output');
        const logElement = document.createElement('div');
        logElement.className = `console-log ${log.type}`;
        logElement.innerHTML = `
            <span class="console-timestamp">[${log.timestamp}]</span>
            <span>${this.escapeHtml(log.message)}</span>
        `;
        
        output.appendChild(logElement);
        
        // Auto-scroll to bottom
        output.scrollTop = output.scrollHeight;
        
        // Remove old logs from display if too many
        while (output.children.length > this.maxConsoleLogs) {
            output.removeChild(output.firstChild);
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    setupServerLogListener() {
        // Use existing socket connection
        this.socket.on('server_log', (data) => {
            // Map server log levels to console types
            const levelMap = {
                'debug': 'debug',
                'info': 'info',
                'warning': 'warning',
                'error': 'error',
                'critical': 'error'
            };
            
            const type = levelMap[data.level] || 'info';
            const message = `[SERVER:${data.module}] ${data.message}`;
            
            // Add to console without going through console.log to avoid recursion
            const log = { 
                timestamp: data.timestamp, 
                type: type, 
                message: message 
            };
            
            this.consoleLogs.push(log);
            
            // Limit logs
            if (this.consoleLogs.length > this.maxConsoleLogs) {
                this.consoleLogs.shift();
            }
            
            // Update UI
            this.updateConsoleDisplay(log);
        });
    }
    
    loadGame() {
        this.showLoading(true);
        
        fetch('/api/get_map')
        .then(response => response.json())
        .then(data => {
            this.showLoading(false);
            if (data.success) {
                this.gameData = data.map_data;
                this.renderer.updateMapData(this.gameData);
                this.updateUI();
            } else {
                this.showMessage('Error loading game: ' + (data.error || 'Unknown error'), 'error');
                setTimeout(() => this.returnToMenu(), 2000);
            }
        })
        .catch(error => {
            this.showLoading(false);
            this.showMessage('Network error: ' + error.message, 'error');
        });
    }
    
    startRenderLoop() {
        const render = () => {
            this.renderer.render();
            requestAnimationFrame(render);
        };
        render();
    }
    
    handleHexClick(hex) {
        const hexKey = `${hex.q},${hex.r},${hex.s}`;
        const hexData = this.renderer.hexes.get(hexKey);
        
        if (!hexData || !hexData.visible) return;
        
        // Check if this is an adjacent hex for movement
        const current = this.gameData.current_position;
        const distance = this.getHexDistance(current, hex);
        
        if (distance === 1) {
            // Show custom exploration modal
            this.showExplorationModal(hex, hexData);
        } else {
            // Select hex for information
            this.selectHex(hex);
        }
    }
    
    handleHexHover(hex, mousePos) {
        if (hex && mousePos) {
            const hexKey = `${hex.q},${hex.r},${hex.s}`;
            const hexData = this.renderer.hexes.get(hexKey);
            
            if (hexData && hexData.visible) {
                this.showTooltip(hexData, mousePos);
            } else {
                this.hideTooltip();
            }
        } else {
            this.hideTooltip();
        }
    }
    
    showTooltip(hexData, mousePos) {
        if (!this.tooltip) {
            this.tooltip = document.createElement('div');
            this.tooltip.className = 'hex-tooltip';
            document.body.appendChild(this.tooltip);
        }
        
        this.tooltip.innerHTML = `
            <strong>${hexData.terrain}</strong><br>
            Biome: ${hexData.biome}<br>
            Position: (${hexData.q}, ${hexData.r}, ${hexData.s})<br>
            ${hexData.explored ? 'Explored' : 'Unexplored'}
        `;
        
        this.tooltip.style.left = (mousePos.x + 10) + 'px';
        this.tooltip.style.top = (mousePos.y - 10) + 'px';
        this.tooltip.style.display = 'block';
    }
    
    hideTooltip() {
        if (this.tooltip) {
            this.tooltip.style.display = 'none';
        }
    }
    
    getHexDistance(hex1, hex2) {
        return (Math.abs(hex1.q - hex2.q) + Math.abs(hex1.q + hex1.r - hex2.q - hex2.r) + Math.abs(hex1.r - hex2.r)) / 2;
    }
    
    moveToHex(hex) {
        this.showLoading(true);
        
        fetch('/api/move', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ q: hex.q, r: hex.r, s: hex.s })
        })
        .then(response => response.json())
        .then(data => {
            this.showLoading(false);
            if (data.success) {
                this.gameData = data.map_data;
                this.renderer.updateMapData(this.gameData);
                this.updateUI();
                this.showMessage(`Moved to (${hex.q}, ${hex.r}, ${hex.s})`);
                this.selectHex(hex);
                
                // Report position change for map view tracking
                this.updatePlayerPosition(hex.q, hex.r, hex.s);
            } else {
                this.showMessage('Cannot move there: ' + (data.error || 'Invalid move'), 'error');
            }
        })
        .catch(error => {
            this.showLoading(false);
            this.showMessage('Network error: ' + error.message, 'error');
        });
    }
    
    selectHex(hex) {
        this.selectedHex = hex;
        const hexKey = `${hex.q},${hex.r},${hex.s}`;
        const hexData = this.renderer.hexes.get(hexKey);
        
        if (hexData) {
            this.showHexInfo(hexData);
        }
    }
    
    showHexInfo(hexData) {
        const panel = document.getElementById('hex-info-panel');
        panel.classList.remove('hidden');
        
        document.getElementById('hex-title').textContent = `${hexData.terrain} Hex (${hexData.q}, ${hexData.r}, ${hexData.s})`;
        document.getElementById('hex-description').textContent = hexData.description || 'No description available.';
        
        document.getElementById('detail-terrain').textContent = hexData.terrain;
        document.getElementById('detail-biome').textContent = hexData.biome;
        document.getElementById('detail-elevation').textContent = hexData.elevation || 0;
        document.getElementById('detail-explored').textContent = hexData.explored ? 'Yes' : 'No';
    }
    
    showExplorationModal(hex, hexData) {
        this.pendingExploreHex = hex;
        
        const terrain = hexData.terrain || 'unknown';
        const biome = hexData.biome || 'unknown';
        
        document.getElementById('exploration-terrain').textContent = `Terrain: ${terrain}`;
        document.getElementById('exploration-biome').textContent = `Biome: ${biome}`;
        document.getElementById('exploration-position').textContent = `Position: (${hex.q}, ${hex.r}, ${hex.s})`;
        
        document.getElementById('exploration-modal').classList.add('active');
    }
    
    confirmExploration() {
        if (this.pendingExploreHex) {
            this.moveToHex(this.pendingExploreHex);
            this.cancelExploration();
        }
    }
    
    cancelExploration() {
        document.getElementById('exploration-modal').classList.remove('active');
        this.pendingExploreHex = null;
    }
    
    
    generateDescription() {
        if (!this.selectedHex) {
            this.showMessage('Please select a hex first', 'error');
            return;
        }
        
        this.showLoading(true);
        
        fetch('/api/generate_description', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(this.selectedHex)
        })
        .then(response => response.json())
        .then(data => {
            this.showLoading(false);
            if (data.success) {
                document.getElementById('hex-description').textContent = data.description;
                this.showMessage('AI description generated');
            } else {
                this.showMessage('Failed to generate description: ' + (data.error || 'AI service unavailable'), 'error');
                if (data.description) {
                    document.getElementById('hex-description').textContent = data.description;
                }
            }
        })
        .catch(error => {
            this.showLoading(false);
            this.showMessage('Network error: ' + error.message, 'error');
        });
    }
    
    
    returnToMenu() {
        window.location.href = '/';
    }
    
    toggleFog() {
        this.renderer.toggleFog();
        this.showMessage(`Fog ${this.renderer.fogEnabled ? 'enabled' : 'disabled'}`);
    }
    
    centerView() {
        this.renderer.centerView();
        this.showMessage('View centered on current position');
    }
    
    handleKeydown(e) {
        // Check if exploration modal is open
        const modal = document.getElementById('exploration-modal');
        if (modal.classList.contains('active')) {
            switch (e.key) {
                case 'Escape':
                    this.cancelExploration();
                    break;
                case 'Enter':
                    this.confirmExploration();
                    break;
            }
            return;
        }
        
        switch (e.key) {
            case 'Escape':
                document.getElementById('hex-info-panel').classList.add('hidden');
                this.selectedHex = null;
                break;
            case 'c':
            case 'C':
                this.centerView();
                break;
            case 'f':
            case 'F':
                this.toggleFog();
                break;
        }
    }
    
    updateUI() {
        if (!this.gameData) return;
        
        // Update position info
        const pos = this.gameData.current_position;
        document.getElementById('position-info').textContent = `Position: (${pos.q}, ${pos.r}, ${pos.s})`;
        
        // Update terrain info
        const currentHexKey = `${pos.q},${pos.r},${pos.s}`;
        const currentHex = this.renderer.hexes.get(currentHexKey);
        if (currentHex) {
            document.getElementById('terrain-info').textContent = `Terrain: ${currentHex.terrain} (${currentHex.biome})`;
        }
        
        
        // Update time info (placeholder)
        document.getElementById('time-info').textContent = 'Day 1, Morning';
    }
    
    updatePlayerPosition(q, r, s) {
        // Report player position change to server for map tracking
        fetch('/api/update_player_position', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ q: q, r: r, s: s })
        })
        .catch(error => {
            console.warn('Failed to update player position:', error);
        });
    }
    
    showMessage(message, type = 'info') {
        const messageBox = document.getElementById('message-box');
        messageBox.textContent = message;
        messageBox.className = `visible ${type}`;
        
        setTimeout(() => {
            messageBox.classList.remove('visible');
        }, 3000);
    }
    
    showLoading(show) {
        const loading = document.getElementById('loading');
        if (show) {
            loading.classList.remove('hidden');
        } else {
            loading.classList.add('hidden');
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    new GameController();
});