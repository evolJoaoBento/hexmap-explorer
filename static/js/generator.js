// Hex Map Generator JavaScript
class HexMapGenerator {
    constructor() {
        this.canvas = document.getElementById('generator-canvas');
        this.ctx = this.canvas.getContext('2d');
        
        // Map data
        this.hexData = new Map(); // key: "q,r,s", value: {terrain, biome, etc.}
        this.seed = 12345;
        this.brushSize = 4;
        this.selectedTerrain = 'water';
        this.currentTool = 'normal'; // 'normal', 'brush', or 'teleport'
        this.sessionId = null;
        this.sessionName = null;
        this.playerPositions = []; // Track player positions
        this.selectedPlayer = null; // For teleport mode
        this.teleportTarget = null; // Target hex for teleportation
        this.northDirection = 0; // North direction in degrees (0 = up)
        this.autoSync = true; // Enable auto-sync after master actions
        this.syncDebounceTimer = null; // Debounce timer for auto-sync
        
        // WebSocket connection
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000; // Start with 1 second
        
        // View settings
        this.camera = { x: 0, y: 0 };
        this.zoom = 1.0;
        this.minZoom = 0.1;
        this.maxZoom = 5.0;
        this.hexSize = 25;
        
        // Interaction
        this.isDragging = false;
        this.isPainting = false;
        this.lastMousePos = { x: 0, y: 0 };
        this.hoveredHex = null;
        this.brushPreview = new Set();
        
        // Performance optimizations
        this.renderThrottled = this.throttle(this.render.bind(this), 16); // ~60fps
        this.frameId = null;
        this.lastRenderTime = 0;
        this.renderSkipFrames = 0;
        this.visibleHexes = new Set(); // Cache visible hexes
        
        // Terrain colors
        this.terrainColors = {
            water: '#4682B4',
            forest: '#228B22',
            plains: '#90EE90',
            mountains: '#696969',
            desert: '#F4A460',
            hills: '#8FBC8F',
            swamp: '#556B2F',
            tundra: '#F0F8FF'
        };
        
        // Biomes (simplified for web version)
        this.biomes = [
            'temperate', 'tropical', 'arctic', 'desert', 'mountain', 'coastal'
        ];
        
        this.setupCanvas();
        this.setupEventListeners();
        this.setupSidebarResize(); // Initialize sidebar resize functionality
        this.updateUI();
        this.updateToolUI(); // Initialize tool UI
        this.createSession(); // Create a session for this generator
        this.startPlayerTracking(); // Start tracking player positions
        this.setupServerConsole(); // Initialize server console
        // Initialize session UI after a short delay to ensure DOM is ready
        setTimeout(() => this.updateSessionUI(), 100);
        this.requestRender();
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
        
        // Listen for server logs via WebSocket
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
        // Initialize WebSocket connection with reconnection options
        this.socket = io({
            reconnection: true,
            reconnectionAttempts: this.maxReconnectAttempts,
            reconnectionDelay: this.reconnectDelay,
            reconnectionDelayMax: 10000,
            timeout: 20000,
            transports: ['websocket', 'polling']
        });
        
        // Connection events
        this.socket.on('connect', () => {
            this.reconnectAttempts = 0;
            this.addConsoleLog('success', ['Connected to server WebSocket']);
        });
        
        this.socket.on('disconnect', (reason) => {
            // Only log disconnect once, not repeatedly
            if (this.reconnectAttempts === 0) {
                this.addConsoleLog('warning', [`Disconnected from server: ${reason}`]);
            }
        });
        
        this.socket.on('connect_error', (error) => {
            this.reconnectAttempts++;
            if (this.reconnectAttempts === 1 || this.reconnectAttempts % 10 === 0) {
                // Only log first attempt and every 10th attempt to reduce spam
                this.addConsoleLog('error', [`Connection error (attempt ${this.reconnectAttempts})`]);
            }
        });
        
        this.socket.on('reconnect', (attemptNumber) => {
            this.addConsoleLog('success', [`Reconnected after ${attemptNumber} attempts`]);
            this.reconnectAttempts = 0;
        });
        
        // Server log events
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
        
        // Map sync events
        this.socket.on('map_synced', (data) => {
            if (data.session_id === this.sessionId) {
                this.addConsoleLog('success', [`Map synced: ${data.hex_count} hexes`]);
            }
        });
        
        this.socket.on('player_teleported', (data) => {
            if (data.session_id === this.sessionId) {
                this.addConsoleLog('info', [`Player teleported to hex`]);
            }
        });
    }
    
    setupSidebarResize() {
        const sidebar = document.getElementById('generator-sidebar');
        const resizeHandle = document.getElementById('sidebar-resize-handle');
        const container = document.getElementById('generator-container');
        
        let isResizing = false;
        let startX = 0;
        let startWidth = 0;
        
        // Load saved width from localStorage
        const savedWidth = localStorage.getItem('generator-sidebar-width');
        if (savedWidth) {
            sidebar.style.width = savedWidth + 'px';
        }
        
        resizeHandle.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            startWidth = parseInt(document.defaultView.getComputedStyle(sidebar).width, 10);
            
            resizeHandle.classList.add('dragging');
            document.body.classList.add('resizing');
            
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            
            const width = startWidth + e.clientX - startX;
            const minWidth = 200;
            const maxWidth = Math.min(500, window.innerWidth * 0.6); // Max 60% of screen width
            
            if (width >= minWidth && width <= maxWidth) {
                sidebar.style.width = width + 'px';
                
                // Trigger canvas resize to adjust to new layout
                if (this.canvas) {
                    // Small delay to ensure layout is updated
                    setTimeout(() => {
                        this.setupCanvas();
                        this.render();
                    }, 10);
                }
            }
        });
        
        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                resizeHandle.classList.remove('dragging');
                document.body.classList.remove('resizing');
                
                // Save the new width to localStorage
                const currentWidth = parseInt(document.defaultView.getComputedStyle(sidebar).width, 10);
                localStorage.setItem('generator-sidebar-width', currentWidth);
            }
        });
        
        // Handle window resize
        window.addEventListener('resize', () => {
            const currentWidth = parseInt(document.defaultView.getComputedStyle(sidebar).width, 10);
            const maxWidth = Math.min(500, window.innerWidth * 0.6);
            
            if (currentWidth > maxWidth) {
                sidebar.style.width = maxWidth + 'px';
                localStorage.setItem('generator-sidebar-width', maxWidth);
            }
            
            // Trigger canvas resize
            setTimeout(() => {
                this.setupCanvas();
                this.render();
            }, 100);
        });
    }
    
    setupCanvas() {
        const resizeCanvas = () => {
            const rect = this.canvas.parentElement.getBoundingClientRect();
            this.canvas.width = rect.width;
            this.canvas.height = rect.height;
            this.render();
        };
        
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
    }
    
    setupEventListeners() {
        // Canvas events
        this.canvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.handleMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.handleWheel(e));
        this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
        
        // UI controls
        document.getElementById('load-json-map').addEventListener('click', () => this.loadJSONMap());
        document.getElementById('import-image-map').addEventListener('click', () => this.showImageImportModal());
        document.getElementById('load-continents').addEventListener('click', () => this.loadContinents());
        document.getElementById('set-seed').addEventListener('click', () => this.showSeedModal());
        document.getElementById('random-seed').addEventListener('click', () => this.randomSeed());
        document.getElementById('sync-world').addEventListener('click', () => this.syncWorld());
        document.getElementById('reset-view').addEventListener('click', () => this.resetView());
        document.getElementById('fit-map').addEventListener('click', () => this.fitMapToView());
        document.getElementById('save-json').addEventListener('click', () => this.saveJSON());
        document.getElementById('copy-to-game').addEventListener('click', () => this.copyToGame());
        document.getElementById('take-screenshot').addEventListener('click', () => this.takeScreenshot());
        document.getElementById('return-menu').addEventListener('click', () => this.returnToMenu());
        
        // Session controls
        document.getElementById('update-session-name').addEventListener('click', () => this.updateSessionName());
        document.getElementById('session-name').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.updateSessionName();
            }
        });
        
        // Brush controls
        document.getElementById('brush-size').addEventListener('input', (e) => {
            this.brushSize = parseInt(e.target.value);
            document.getElementById('brush-size-display').textContent = this.brushSize;
        });
        
        // North direction control
        document.getElementById('north-direction').addEventListener('input', (e) => {
            this.northDirection = parseInt(e.target.value);
            document.getElementById('north-direction-display').textContent = this.northDirection + '°';
            this.render(); // Re-render with new orientation
        });
        
        document.getElementById('reset-north').addEventListener('click', () => {
            this.northDirection = 0;
            document.getElementById('north-direction').value = 0;
            document.getElementById('north-direction-display').textContent = '0°';
            this.render();
        });
        
        // Tool selection
        document.querySelectorAll('.tool-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentTool = e.target.dataset.tool;
                this.updateToolUI();
            });
        });
        
        // Terrain selection
        document.querySelectorAll('.terrain-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.terrain-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.selectedTerrain = e.target.dataset.terrain;
            });
        });
        
        // File inputs
        document.getElementById('json-file-input').addEventListener('change', (e) => this.handleJSONFileLoad(e));
        document.getElementById('image-file-input').addEventListener('change', (e) => this.handleImageFileLoad(e));
        
        // Seed modal
        document.getElementById('confirm-seed').addEventListener('click', () => this.confirmSeed());
        document.getElementById('cancel-seed').addEventListener('click', () => this.cancelSeed());
        
        // Color guide modal
        document.getElementById('show-color-guide').addEventListener('click', () => this.showColorGuide());
        document.getElementById('close-color-guide').addEventListener('click', () => this.closeColorGuide());
        
        // Image import modal controls (setup when modal opens to avoid timing issues)
        document.getElementById('cancel-import').addEventListener('click', () => this.closeImageImportModal());
        document.getElementById('import-confirmed').addEventListener('click', () => this.confirmImageImport());
        document.getElementById('update-preview').addEventListener('click', () => this.updatePreview());
        document.getElementById('reset-import-settings').addEventListener('click', () => this.resetImportSettings());
        
        // Individual tolerance sliders
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('tolerance-slider')) {
                const value = e.target.value;
                const toleranceValueElement = e.target.nextElementSibling;
                if (toleranceValueElement && toleranceValueElement.classList.contains('tolerance-value')) {
                    toleranceValueElement.textContent = value;
                }
                // Auto-update preview if image is loaded
                if (this.selectedImageFile) {
                    setTimeout(() => this.updatePreview(), 100);
                }
            }
        });
        
        // Auto-update preview when terrain mappings change
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('terrain-select') && this.selectedImageFile) {
                setTimeout(() => this.updatePreview(), 100);
            }
        });
        
        // Auto-update size display and preview when map size changes
        document.addEventListener('input', (e) => {
            if (e.target.id === 'map-width-miles') {
                this.updateMapSizeDisplay();
                if (this.selectedImageFile) {
                    setTimeout(() => this.updatePreview(), 100);
                }
            }
        });
        
        // Preset button
        document.getElementById('apply-preset').addEventListener('click', () => this.applyPreset());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyDown(e));
    }
    
    handleMouseDown(e) {
        const pos = this.getMousePos(e);
        
        if (this.currentTool === 'brush') {
            if (e.button === 0) { // Left click - paint
                this.isPainting = true;
                this.paintAtPosition(pos);
            } else if (e.button === 1 || e.button === 2) { // Middle or right click - drag
                this.isDragging = true;
                this.lastMousePos = pos;
                this.canvas.classList.add('panning');
            }
        } else if (this.currentTool === 'teleport') {
            if (e.button === 0) { // Left click - select teleport target
                const hex = this.pixelToHex(pos.x, pos.y);
                this.selectTeleportTarget(hex);
            } else if (e.button === 1 || e.button === 2) { // Middle or right click - drag
                this.isDragging = true;
                this.lastMousePos = pos;
                this.canvas.classList.add('panning');
            }
        } else { // normal tool
            if (e.button === 0) { // Left click - drag or hex info
                this.isDragging = true;
                this.lastMousePos = pos;
                this.canvas.classList.add('panning');
            } else if (e.button === 2) { // Right click - hex info
                const hex = this.pixelToHex(pos.x, pos.y);
                this.showHexInfo(hex, pos);
            }
        }
    }
    
    handleMouseMove(e) {
        const pos = this.getMousePos(e);
        
        if (this.isDragging) {
            const dx = pos.x - this.lastMousePos.x;
            const dy = pos.y - this.lastMousePos.y;
            // Scale drag sensitivity with zoom level for consistent feel
            const baseSensitivity = 0.8; // Base sensitivity
            const zoomAdjustedSensitivity = baseSensitivity * Math.pow(this.zoom, 0.5); // Sqrt scaling
            this.camera.x += (dx / this.zoom) * zoomAdjustedSensitivity;
            this.camera.y += (dy / this.zoom) * zoomAdjustedSensitivity;
            this.lastMousePos = pos;
            this.requestRender();
        } else if (this.isPainting && this.currentTool === 'brush') {
            this.paintAtPosition(pos);
        } else {
            this.updateHover(pos);
        }
    }
    
    handleMouseUp(e) {
        this.isDragging = false;
        this.isPainting = false;
        this.canvas.classList.remove('panning');
        
        // Reset cursor based on current tool
        if (this.currentTool === 'brush') {
            this.canvas.style.cursor = 'crosshair';
        } else {
            this.canvas.style.cursor = 'grab';
        }
    }
    
    handleWheel(e) {
        e.preventDefault();
        const pos = this.getMousePos(e);
        const zoomFactor = 1.1;
        const oldZoom = this.zoom;
        
        if (e.deltaY < 0) {
            this.zoom = Math.min(this.zoom * zoomFactor, this.maxZoom);
        } else {
            this.zoom = Math.max(this.zoom / zoomFactor, this.minZoom);
        }
        
        // Zoom towards mouse position
        const zoomRatio = this.zoom / oldZoom;
        this.camera.x = pos.x - (pos.x - this.camera.x) * zoomRatio;
        this.camera.y = pos.y - (pos.y - this.camera.y) * zoomRatio;
        
        this.updateUI();
        this.requestRender();
    }
    
    handleKeyDown(e) {
        switch (e.key) {
            case 'Escape':
                if (document.getElementById('image-import-modal').classList.contains('active')) {
                    this.closeImageImportModal();
                } else if (document.getElementById('color-guide-modal').classList.contains('active')) {
                    this.closeColorGuide();
                } else {
                    this.cancelSeed();
                }
                break;
            case 'Enter':
                if (document.getElementById('seed-modal').classList.contains('active')) {
                    this.confirmSeed();
                }
                break;
        }
    }
    
    getMousePos(e) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }
    
    // Hex coordinate conversion (copied exactly from game's hex-renderer.js)
    hexToPixel(q, r) {
        // Calculate base position
        let x = this.hexSize * (3/2 * q);
        let y = this.hexSize * (Math.sqrt(3)/2 * q + Math.sqrt(3) * r);
        
        // Apply north rotation if set
        if (this.northDirection !== 0) {
            const angle = (this.northDirection * Math.PI) / 180;
            const cos = Math.cos(angle);
            const sin = Math.sin(angle);
            
            const rotatedX = x * cos - y * sin;
            const rotatedY = x * sin + y * cos;
            
            x = rotatedX;
            y = rotatedY;
        }
        
        return { 
            x: x * this.zoom + this.camera.x, 
            y: y * this.zoom + this.camera.y 
        };
    }
    
    pixelToHex(x, y) {
        // Apply inverse camera transformation (exact inverse of hexToPixel)
        let worldX = (x - this.camera.x) / this.zoom;
        let worldY = (y - this.camera.y) / this.zoom;
        
        // Apply inverse north rotation if set
        if (this.northDirection !== 0) {
            const angle = -(this.northDirection * Math.PI) / 180; // Negative for inverse
            const cos = Math.cos(angle);
            const sin = Math.sin(angle);
            
            const rotatedX = worldX * cos - worldY * sin;
            const rotatedY = worldX * sin + worldY * cos;
            
            worldX = rotatedX;
            worldY = rotatedY;
        }
        
        // Convert pixel coordinates to hex coordinates (exact inverse of hexToPixel)
        const q = (2/3 * worldX) / this.hexSize;
        const r = (-1/3 * worldX + Math.sqrt(3)/3 * worldY) / this.hexSize;
        const s = -q - r;
        
        return this.roundHex({ q, r, s });
    }
    
    roundHex(hex) {
        let q = Math.round(hex.q);
        let r = Math.round(hex.r);
        let s = Math.round(hex.s);
        
        const qDiff = Math.abs(q - hex.q);
        const rDiff = Math.abs(r - hex.r);
        const sDiff = Math.abs(s - hex.s);
        
        if (qDiff > rDiff && qDiff > sDiff) {
            q = -r - s;
        } else if (rDiff > sDiff) {
            r = -q - s;
        } else {
            s = -q - r;
        }
        
        return { q, r, s };
    }
    
    // Painting functions
    updateHover(mousePos) {
        const hex = this.pixelToHex(mousePos.x, mousePos.y);
        this.hoveredHex = hex;
        this.updateBrushPreview(hex);
        this.updateTooltip(hex, mousePos);
        this.render();
    }
    
    updateBrushPreview(centerHex) {
        this.brushPreview.clear();
        
        for (let dq = -this.brushSize; dq <= this.brushSize; dq++) {
            for (let dr = Math.max(-this.brushSize, -dq - this.brushSize); 
                 dr <= Math.min(this.brushSize, -dq + this.brushSize); dr++) {
                const ds = -dq - dr;
                const distance = (Math.abs(dq) + Math.abs(dr) + Math.abs(ds)) / 2;
                
                if (distance <= this.brushSize) {
                    const q = centerHex.q + dq;
                    const r = centerHex.r + dr;
                    const s = centerHex.s + ds;
                    this.brushPreview.add(`${q},${r},${s}`);
                }
            }
        }
    }
    
    paintAtPosition(mousePos) {
        const hex = this.pixelToHex(mousePos.x, mousePos.y);
        this.updateBrushPreview(hex);
        
        this.brushPreview.forEach(hexKey => {
            const [q, r, s] = hexKey.split(',').map(Number);
            const hexData = {
                q, r, s,
                terrain: this.selectedTerrain,
                biome: this.getRandomBiome(),
                elevation: Math.floor(Math.random() * 100)
            };
            
            this.hexData.set(hexKey, hexData);
            
            // Sync terrain change to backend and active game sessions
            this.syncTerrainChange(q, r, s, this.selectedTerrain);
        });
        
        this.updateStats();
        this.render();
        this.triggerAutoSync(); // Auto-sync after painting
    }
    
    syncTerrainChange(q, r, s, terrain) {
        if (!this.sessionId) return;
        
        fetch('/api/update_hex_terrain', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: this.sessionId,
                q: q,
                r: r,
                s: s,
                terrain: terrain
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Terrain change synced successfully');
            }
        })
        .catch(error => {
            console.warn('Failed to sync terrain change:', error);
        });
    }
    
    updateTooltip(hex, mousePos) {
        const tooltip = document.getElementById('generator-tooltip');
        const hexKey = `${hex.q},${hex.r},${hex.s}`;
        const hexData = this.hexData.get(hexKey);
        
        document.getElementById('tooltip-coords').textContent = `(${hex.q}, ${hex.r}, ${hex.s})`;
        
        if (hexData) {
            document.getElementById('tooltip-terrain').textContent = `Terrain: ${hexData.terrain}`;
            document.getElementById('tooltip-biome').textContent = `Biome: ${hexData.biome}`;
            tooltip.classList.remove('hidden');
        } else {
            document.getElementById('tooltip-terrain').textContent = 'Terrain: none';
            document.getElementById('tooltip-biome').textContent = 'Biome: none';
            tooltip.classList.remove('hidden');
        }
        
        tooltip.style.left = (mousePos.x + 15) + 'px';
        tooltip.style.top = (mousePos.y - 10) + 'px';
    }
    
    // Session management
    createSession() {
        fetch('/api/create_map_session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                seed: this.seed,
                name: `Map_${this.seed}`
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.sessionId = data.session_id;
                this.sessionName = data.name;
                this.updateSessionUI();
                console.log(`Created session: ${this.sessionId}`);
            }
        })
        .catch(error => {
            console.error('Failed to create session:', error);
        });
    }
    
    loadMap() {
        // This now loads the map with current seed
        this.generateMap();
    }
    
    loadJSONMap() {
        // Trigger the JSON file input
        document.getElementById('json-file-input').click();
    }
    
    showImageImportModal() {
        console.log('Opening image import modal');
        const modal = document.getElementById('image-import-modal');
        console.log('Modal element found:', modal);
        
        if (modal) {
            modal.classList.add('active');
            console.log('Modal classes after adding active:', modal.className);
            
            // Reset preview
            const imagePreview = document.getElementById('image-preview');
            const terrainPreview = document.getElementById('terrain-preview');
            
            if (imagePreview) {
                imagePreview.innerHTML = '<p>Select an image to see preview</p>';
            }
            if (terrainPreview) {
                terrainPreview.innerHTML = '<p>Terrain mapping will appear here</p>';
            }
            
            // Ensure event listeners are attached (in case of timing issues)
            this.setupImportModalEventListeners();
            
            // Update size display
            this.updateMapSizeDisplay();
        } else {
            console.error('Image import modal not found!');
        }
    }
    
    setupImportModalEventListeners() {
        const selectBtn = document.getElementById('select-image-file');
        const fileInput = document.getElementById('image-file-input');
        
        console.log('Setting up import modal listeners, selectBtn:', selectBtn, 'fileInput:', fileInput);
        
        // Clear any existing listeners by cloning and replacing elements
        let newFileInput = fileInput;
        if (fileInput) {
            newFileInput = fileInput.cloneNode(true);
            fileInput.parentNode.replaceChild(newFileInput, fileInput);
            
            newFileInput.addEventListener('change', (e) => {
                console.log('File input changed (new listener):', e.target.files);
                this.handleImageFileSelection(e);
            });
        }
        
        if (selectBtn) {
            const newSelectBtn = selectBtn.cloneNode(true);
            selectBtn.parentNode.replaceChild(newSelectBtn, selectBtn);
            
            newSelectBtn.addEventListener('click', () => {
                console.log('Select image file button clicked (new listener)');
                newFileInput.click(); // Use the new file input reference
            });
        }
    }
    
    updateMapSizeDisplay() {
        const mapWidthMiles = parseInt(document.getElementById('map-width-miles').value) || 300;
        const hexesWide = Math.floor(mapWidthMiles / 3);
        const display = document.getElementById('hex-count-display');
        if (display) {
            display.textContent = `${hexesWide} hexes wide (${mapWidthMiles} miles)`;
        }
    }
    
    closeImageImportModal() {
        document.getElementById('image-import-modal').classList.remove('active');
        // Reset file input
        document.getElementById('image-file-input').value = '';
        document.getElementById('selected-file-name').textContent = 'No file selected';
        this.selectedImageFile = null;
    }
    
    handleImageFileSelection(event) {
        console.log('handleImageFileSelection called');
        console.log('Event target:', event.target);
        console.log('Files:', event.target.files);
        console.log('Files length:', event.target.files ? event.target.files.length : 'no files');
        
        const file = event.target.files && event.target.files.length > 0 ? event.target.files[0] : null;
        console.log('Selected file:', file);
        
        if (!file) {
            console.log('No file selected');
            return;
        }
        
        this.selectedImageFile = file;
        document.getElementById('selected-file-name').textContent = file.name;
        console.log('File name set to:', file.name);
        
        // Show image preview
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = document.createElement('img');
            img.src = e.target.result;
            img.style.maxWidth = '100%';
            img.style.maxHeight = '100%';
            img.style.objectFit = 'contain';
            
            const imagePreview = document.getElementById('image-preview');
            imagePreview.innerHTML = '';
            imagePreview.appendChild(img);
            
            // Auto-update preview
            this.updatePreview();
        };
        reader.readAsDataURL(file);
    }
    
    updatePreview() {
        console.log('updatePreview called, selectedImageFile:', this.selectedImageFile);
        if (!this.selectedImageFile) return;
        
        const reader = new FileReader();
        reader.onload = (e) => {
            console.log('Image file read for preview');
            const img = new Image();
            img.onload = () => {
                console.log('Image loaded for preview, calling generateTerrainPreview');
                try {
                    this.generateTerrainPreview(img);
                } catch (error) {
                    console.error('Error generating preview:', error);
                    document.getElementById('terrain-preview').innerHTML = '<p>Error generating preview</p>';
                }
            };
            img.onerror = () => {
                console.error('Error loading image for preview');
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(this.selectedImageFile);
    }
    
    generateTerrainPreview(img) {
        console.log('Generating terrain preview for image:', img.width, 'x', img.height);
        
        // Create a small canvas for preview
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Limit preview size for performance
        const maxSize = 200;
        const scale = Math.min(maxSize / img.width, maxSize / img.height);
        canvas.width = Math.floor(img.width * scale);
        canvas.height = Math.floor(img.height * scale);
        
        console.log('Preview canvas size:', canvas.width, 'x', canvas.height);
        
        // Draw scaled image
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        
        // Get terrain mappings and tolerances
        const terrainMappings = {};
        const tolerances = {};
        document.querySelectorAll('.terrain-select').forEach(select => {
            const colorKey = select.getAttribute('data-color');
            terrainMappings[colorKey] = select.value;
        });
        
        document.querySelectorAll('.tolerance-slider').forEach(slider => {
            const colorKey = slider.getAttribute('data-color');
            tolerances[colorKey] = parseInt(slider.value);
        });
        
        const defaultTerrain = document.getElementById('default-terrain').value;
        
        // Color patterns
        const colorPatterns = [
            { name: 'water', r: 70, g: 130, b: 180, maps_to: terrainMappings.water, tolerance: tolerances.water || 50 },
            { name: 'forest', r: 34, g: 139, b: 34, maps_to: terrainMappings.forest, tolerance: tolerances.forest || 50 },
            { name: 'plains', r: 144, g: 238, b: 144, maps_to: terrainMappings.plains, tolerance: tolerances.plains || 50 },
            { name: 'mountains', r: 105, g: 105, b: 105, maps_to: terrainMappings.mountains, tolerance: tolerances.mountains || 50 },
            { name: 'desert', r: 244, g: 164, b: 96, maps_to: terrainMappings.desert, tolerance: tolerances.desert || 50 },
            { name: 'hills', r: 143, g: 188, b: 143, maps_to: terrainMappings.hills, tolerance: tolerances.hills || 50 },
            { name: 'swamp', r: 85, g: 107, b: 47, maps_to: terrainMappings.swamp, tolerance: tolerances.swamp || 50 },
            { name: 'tundra', r: 240, g: 248, b: 255, maps_to: terrainMappings.tundra, tolerance: tolerances.tundra || 50 }
        ];
        
        // Process image data
        let imageData, pixels;
        try {
            imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            pixels = imageData.data;
            console.log('Got image data, pixel array length:', pixels.length);
        } catch (error) {
            console.error('Error getting image data:', error);
            document.getElementById('terrain-preview').innerHTML = '<p>Error processing image data</p>';
            return;
        }
        
        // Create terrain-colored version
        for (let i = 0; i < pixels.length; i += 4) {
            const red = pixels[i];
            const green = pixels[i + 1];
            const blue = pixels[i + 2];
            const alpha = pixels[i + 3];
            
            if (alpha < 128) continue; // Skip transparent pixels
            
            let bestMatch = defaultTerrain;
            let bestDistance = Infinity;
            
            for (const pattern of colorPatterns) {
                if (!pattern.maps_to) continue; // Skip if no mapping defined
                
                const distance = Math.sqrt(
                    Math.pow(red - pattern.r, 2) + 
                    Math.pow(green - pattern.g, 2) + 
                    Math.pow(blue - pattern.b, 2)
                );
                
                if (distance < bestDistance && distance <= pattern.tolerance) {
                    bestDistance = distance;
                    bestMatch = pattern.maps_to;
                }
            }
            
            // Apply terrain color - make it more obvious by enhancing contrast
            const terrainColor = this.getTerrainColor(bestMatch);
            pixels[i] = Math.min(255, terrainColor.r * 1.2);     // Boost colors slightly
            pixels[i + 1] = Math.min(255, terrainColor.g * 1.2);
            pixels[i + 2] = Math.min(255, terrainColor.b * 1.2);
            // Keep original alpha
        }
        
        // Update canvas with new colors
        ctx.putImageData(imageData, 0, 0);
        
        console.log('Terrain preview generated, updating DOM');
        
        // Convert canvas to image data URL for better compatibility
        const dataUrl = canvas.toDataURL('image/png');
        
        // Show in preview
        const terrainPreview = document.getElementById('terrain-preview');
        terrainPreview.innerHTML = '';
        
        // Create an image element instead of directly using canvas
        const previewImg = document.createElement('img');
        previewImg.src = dataUrl;
        previewImg.style.maxWidth = '100%';
        previewImg.style.maxHeight = '100%';
        previewImg.style.objectFit = 'contain';
        previewImg.style.display = 'block';
        previewImg.style.border = '1px solid #666';
        
        terrainPreview.appendChild(previewImg);
        
        // Also add a text indicator
        const mapWidthMiles = parseInt(document.getElementById('map-width-miles').value) || 300;
        const hexesWide = Math.floor(mapWidthMiles / 3);
        const aspectRatio = canvas.height / canvas.width;
        const hexesTall = Math.floor(hexesWide * aspectRatio);
        
        const indicator = document.createElement('p');
        indicator.textContent = `Preview: ${hexesWide}×${hexesTall} hexes (${mapWidthMiles} miles wide)`;
        indicator.style.fontSize = '0.8rem';
        indicator.style.color = '#b4b4b4';
        indicator.style.textAlign = 'center';
        indicator.style.margin = '5px 0 0 0';
        terrainPreview.appendChild(indicator);
        
        console.log('Terrain preview image created and appended to DOM');
    }
    
    getTerrainColor(terrain) {
        const colors = {
            water: { r: 70, g: 130, b: 180 },
            forest: { r: 34, g: 139, b: 34 },
            plains: { r: 144, g: 238, b: 144 },
            mountains: { r: 105, g: 105, b: 105 },
            desert: { r: 244, g: 164, b: 96 },
            hills: { r: 143, g: 188, b: 143 },
            swamp: { r: 85, g: 107, b: 47 },
            tundra: { r: 240, g: 248, b: 255 }
        };
        return colors[terrain] || colors.plains;
    }
    
    confirmImageImport() {
        if (!this.selectedImageFile) {
            this.showMessage('Please select an image file first', 'error');
            return;
        }
        
        this.showLoading(true);
        
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                try {
                    this.convertImageToHexMap(img);
                    this.closeImageImportModal();
                } catch (error) {
                    this.showMessage('Error processing image: ' + error.message, 'error');
                    this.showLoading(false);
                }
            };
            img.onerror = () => {
                this.showMessage('Error loading image file', 'error');
                this.showLoading(false);
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(this.selectedImageFile);
    }
    
    resetImportSettings() {
        // Reset individual tolerance sliders to default
        document.querySelectorAll('.tolerance-slider').forEach(slider => {
            slider.value = 50;
            const toleranceValueElement = slider.nextElementSibling;
            if (toleranceValueElement && toleranceValueElement.classList.contains('tolerance-value')) {
                toleranceValueElement.textContent = '50';
            }
        });
        
        // Reset terrain mappings to defaults
        document.querySelector('[data-color="water"]').value = 'water';
        document.querySelector('[data-color="forest"]').value = 'forest';
        document.querySelector('[data-color="plains"]').value = 'plains';
        document.querySelector('[data-color="mountains"]').value = 'mountains';
        document.querySelector('[data-color="desert"]').value = 'desert';
        document.querySelector('[data-color="hills"]').value = 'hills';
        document.querySelector('[data-color="swamp"]').value = 'swamp';
        document.querySelector('[data-color="tundra"]').value = 'tundra';
        
        // Reset default terrain
        document.getElementById('default-terrain').value = 'plains';
        
        // Reset preset
        document.getElementById('color-preset').value = 'default';
        
        // Reset map size
        document.getElementById('map-width-miles').value = 300;
        this.updateMapSizeDisplay();
        
        this.showMessage('Settings reset to defaults', 'success');
        
        // Update preview if image is loaded
        if (this.selectedImageFile) {
            this.updatePreview();
        }
    }
    
    handleJSONFileLoad(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const mapData = JSON.parse(e.target.result);
                this.loadMapFromJSON(mapData);
            } catch (error) {
                this.showMessage('Error loading JSON file: ' + error.message, 'error');
            }
        };
        reader.readAsText(file);
        
        // Reset the input so the same file can be selected again
        event.target.value = '';
    }
    
    handleImageFileLoad(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        this.showMessage('Processing image map...', 'info');
        this.showLoading(true);
        
        const img = new Image();
        img.onload = () => {
            try {
                this.convertImageToHexMap(img);
            } catch (error) {
                this.showMessage('Error processing image: ' + error.message, 'error');
                this.showLoading(false);
            }
        };
        
        img.onerror = () => {
            this.showMessage('Error loading image file', 'error');
            this.showLoading(false);
        };
        
        img.src = URL.createObjectURL(file);
        
        // Reset the input so the same file can be selected again
        event.target.value = '';
    }
    
    convertImageToHexMap(img) {
        // Create a canvas to analyze the image
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Set canvas size to image size
        canvas.width = img.width;
        canvas.height = img.height;
        
        // Draw image to canvas
        ctx.drawImage(img, 0, 0);
        
        // Get image data
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const pixels = imageData.data;
        
        // Clear existing hexes
        this.hexData.clear();
        
        // Get current settings
        const defaultTerrain = document.getElementById('default-terrain').value;
        
        // Get terrain mappings and individual tolerances from UI
        const terrainMappings = {};
        const tolerances = {};
        document.querySelectorAll('.terrain-select').forEach(select => {
            const colorKey = select.getAttribute('data-color');
            const targetTerrain = select.value;
            terrainMappings[colorKey] = targetTerrain;
        });
        
        document.querySelectorAll('.tolerance-slider').forEach(slider => {
            const colorKey = slider.getAttribute('data-color');
            tolerances[colorKey] = parseInt(slider.value);
        });
        
        // Define color patterns with current settings
        const colorPatterns = [
            { name: 'water', r: 70, g: 130, b: 180, maps_to: terrainMappings.water, tolerance: tolerances.water || 50 },      // Steel Blue
            { name: 'forest', r: 34, g: 139, b: 34, maps_to: terrainMappings.forest, tolerance: tolerances.forest || 50 },    // Forest Green
            { name: 'plains', r: 144, g: 238, b: 144, maps_to: terrainMappings.plains, tolerance: tolerances.plains || 50 },  // Light Green
            { name: 'mountains', r: 105, g: 105, b: 105, maps_to: terrainMappings.mountains, tolerance: tolerances.mountains || 50 }, // Dim Gray
            { name: 'desert', r: 244, g: 164, b: 96, maps_to: terrainMappings.desert, tolerance: tolerances.desert || 50 },   // Sandy Brown
            { name: 'hills', r: 143, g: 188, b: 143, maps_to: terrainMappings.hills, tolerance: tolerances.hills || 50 },    // Dark Sea Green
            { name: 'swamp', r: 85, g: 107, b: 47, maps_to: terrainMappings.swamp, tolerance: tolerances.swamp || 50 },      // Dark Olive Green
            { name: 'tundra', r: 240, g: 248, b: 255, maps_to: terrainMappings.tundra, tolerance: tolerances.tundra || 50 }   // Alice Blue
        ];
        
        // Get desired map size in hexes
        const mapWidthMiles = parseInt(document.getElementById('map-width-miles').value) || 300;
        
        // Scale hex count based on image size to capture detail
        // Base calculation on miles
        const baseHexesWide = Math.floor(mapWidthMiles / 3);
        
        // For larger images, increase hex density to capture more detail
        // Minimum 30 pixels per hex, but scale up for larger images
        const optimalPixelsPerHex = 30;
        const imageBasedHexesWide = Math.floor(canvas.width / optimalPixelsPerHex);
        
        // Use the larger value to ensure we capture all image detail
        const hexesWide = Math.max(baseHexesWide, imageBasedHexesWide);
        
        // Calculate height based on image aspect ratio
        const aspectRatio = canvas.height / canvas.width;
        const hexesTall = Math.floor(hexesWide * aspectRatio);
        
        console.log(`Processing: ${hexesWide} wide x ${hexesTall} tall hex map (${mapWidthMiles} miles wide)`);
        
        // Step 1: Create hex coordinates and map them to image positions
        const hexCoordinates = [];
        
        for (let row = 0; row < hexesTall; row++) {
            for (let col = 0; col < hexesWide; col++) {
                // Convert to axial coordinates
                const q = col - Math.floor(row / 2);
                const r = row;
                const s = -q - r;
                
                // Simple direct mapping without rotation
                // Account for hex offset pattern (every other row is offset)
                const xOffset = (row % 2) * 0.5;
                
                // Direct proportional mapping to ensure full coverage
                const imageX = ((col + xOffset) / hexesWide) * canvas.width;
                const imageY = (row / hexesTall) * canvas.height;
                
                hexCoordinates.push({
                    q, r, s,
                    imageX: imageX,
                    imageY: imageY,
                    pixels: []
                });
            }
        }
        
        console.log(`Created ${hexCoordinates.length} hex coordinate mappings`);
        
        // Step 2: Fast sampling - instead of checking every pixel, sample a grid
        // Sample pixels in a reasonable grid based on hex size
        const samplesPerHex = 25; // 5x5 grid of samples per hex for better accuracy
        const hexWidth = canvas.width / hexesWide;
        const hexHeight = canvas.height / hexesTall;
        const sampleRadius = Math.max(hexWidth, hexHeight) / 2;
        
        // For each hex, sample pixels in its region
        for (const hex of hexCoordinates) {
            // Skip hexes that are outside image bounds
            if (hex.imageX < -sampleRadius || hex.imageX > canvas.width + sampleRadius ||
                hex.imageY < -sampleRadius || hex.imageY > canvas.height + sampleRadius) {
                continue;
            }
            
            // Sample in a grid pattern around the hex center
            const gridSize = Math.ceil(Math.sqrt(samplesPerHex));
            for (let dy = -gridSize/2; dy <= gridSize/2; dy++) {
                for (let dx = -gridSize/2; dx <= gridSize/2; dx++) {
                    const sampleX = Math.round(hex.imageX + dx * sampleRadius / gridSize);
                    const sampleY = Math.round(hex.imageY + dy * sampleRadius / gridSize);
                    
                    // Check bounds
                    if (sampleX < 0 || sampleX >= canvas.width || 
                        sampleY < 0 || sampleY >= canvas.height) {
                        continue;
                    }
                    
                    const pixelIndex = (sampleY * canvas.width + sampleX) * 4;
                    const red = pixels[pixelIndex];
                    const green = pixels[pixelIndex + 1];
                    const blue = pixels[pixelIndex + 2];
                    const alpha = pixels[pixelIndex + 3];
                    
                    // Only add non-transparent pixels
                    if (alpha >= 128) {
                        hex.pixels.push({ red, green, blue });
                    }
                }
            }
        }
        
        console.log('Completed fast pixel sampling');
        
        // Step 3: For each hex, average its pixels and determine terrain
        let hexCount = 0;
        for (const hex of hexCoordinates) {
            if (hex.pixels.length === 0) continue; // Skip hexes with no pixels
            
            // Average the colors of all pixels in this hex region
            let avgRed = 0, avgGreen = 0, avgBlue = 0;
            for (const pixel of hex.pixels) {
                avgRed += pixel.red;
                avgGreen += pixel.green;
                avgBlue += pixel.blue;
            }
            avgRed = Math.round(avgRed / hex.pixels.length);
            avgGreen = Math.round(avgGreen / hex.pixels.length);
            avgBlue = Math.round(avgBlue / hex.pixels.length);
            
            // Find closest matching terrain type using averaged color
            let bestMatch = defaultTerrain;
            let bestDistance = Infinity;
            
            for (const pattern of colorPatterns) {
                const distance = Math.sqrt(
                    Math.pow(avgRed - pattern.r, 2) + 
                    Math.pow(avgGreen - pattern.g, 2) + 
                    Math.pow(avgBlue - pattern.b, 2)
                );
                
                if (distance < bestDistance && distance <= pattern.tolerance) {
                    bestDistance = distance;
                    bestMatch = pattern.maps_to;
                }
            }
            
            // Create hex with terrain
            const key = `${hex.q},${hex.r},${hex.s}`;
            this.hexData.set(key, {
                q: hex.q,
                r: hex.r,
                s: hex.s,
                terrain: bestMatch,
                biome: 'temperate',
                elevation: 0,
                visible: true,
                explored: false
            });
            
            hexCount++;
        }
        
        console.log(`Created ${hexCount} hexes with averaged pixel colors`);
        
        // Clean up
        URL.revokeObjectURL(img.src);
        
        // Update display
        this.fitMapToView();
        this.render();
        this.updateStats();
        this.showLoading(false);
        
        this.showMessage(`Successfully converted image to ${hexCount} hexes using pixel averaging!`, 'success');
    }
    
    loadMapFromJSON(mapData) {
        try {
            // Clear existing hexes
            this.hexData.clear();
            
            // Load hexes from JSON data
            if (mapData.hexes) {
                mapData.hexes.forEach(hexData => {
                    const key = `${hexData.q},${hexData.r},${hexData.s}`;
                    this.hexData.set(key, {
                        q: hexData.q,
                        r: hexData.r,
                        s: hexData.s,
                        terrain: hexData.terrain || 'plains',
                        biome: hexData.biome || 'temperate',
                        elevation: hexData.elevation || 0,
                        visible: true,
                        explored: hexData.explored || false
                    });
                });
            }
            
            // Load north direction if provided
            if (mapData.northDirection !== undefined) {
                this.northDirection = mapData.northDirection;
                document.getElementById('north-direction').value = this.northDirection;
                document.getElementById('north-direction-display').textContent = this.northDirection + '°';
            }
            
            // Update seed if provided
            if (mapData.seed) {
                this.seed = mapData.seed;
                document.getElementById('current-seed').textContent = this.seed;
            }
            
            // Center view on the loaded map
            this.fitMapToView();
            this.render();
            this.updateStats();
            
            this.showMessage(`Loaded ${this.hexData.size} hexes from JSON file`, 'success');
        } catch (error) {
            this.showMessage('Error processing map data: ' + error.message, 'error');
        }
    }
    
    // Generation functions
    generateMap() {
        if (!this.sessionId) {
            console.error('No active session for map generation');
            return;
        }
        
        this.showLoading(true);
        
        // Use the backend API to generate with the same system as the game
        fetch('/api/generate_hex_map', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                seed: this.seed,
                session_id: this.sessionId
            })
        })
        .then(response => response.json())
        .then(data => {
            this.showLoading(false);
            if (data.success) {
                this.hexData.clear();
                
                // Load the generated hexes
                data.hexes.forEach(hex => {
                    const hexKey = `${hex.q},${hex.r},${hex.s}`;
                    this.hexData.set(hexKey, hex);
                });
                
                console.log(`Generated ${this.hexData.size} hexes with seed ${data.seed}`);
                this.updateStats();
                this.render();
                this.fitMapToView();
                
                // Auto-sync after map generation
                this.triggerAutoSync();
            } else {
                console.error('Generation failed:', data.error);
                this.showMessage('Generation failed: ' + data.error);
            }
        })
        .catch(error => {
            this.showLoading(false);
            console.error('Network error:', error);
            this.showMessage('Network error: ' + error.message);
        });
    }
    
    generateContinents() {
        const numContinents = 3 + Math.floor(Math.random() * 3);
        
        for (let i = 0; i < numContinents; i++) {
            const centerQ = Math.floor((Math.random() - 0.5) * 100);
            const centerR = Math.floor((Math.random() - 0.5) * 100);
            const radius = 15 + Math.floor(Math.random() * 25);
            
            this.generateContinent(centerQ, centerR, radius);
        }
    }
    
    generateContinent(centerQ, centerR, radius) {
        const terrains = ['forest', 'plains', 'mountains', 'hills'];
        
        // Simple approach - generate in circular pattern
        for (let q = centerQ - radius; q <= centerQ + radius; q++) {
            for (let r = centerR - radius; r <= centerR + radius; r++) {
                const s = -q - r;
                
                // Calculate hex distance from center
                const dq = q - centerQ;
                const dr = r - centerR;
                const ds = s - (-centerQ - centerR);
                const distance = (Math.abs(dq) + Math.abs(dr) + Math.abs(ds)) / 2;
                
                if (distance <= radius) {
                    const noise = Math.random();
                    const distanceFactor = 1 - (distance / radius);
                    
                    // Make sure we generate some hexes
                    if (noise * distanceFactor > 0.2) {
                        const hexKey = `${q},${r},${s}`;
                        let terrain;
                        
                        if (distance < radius * 0.3) {
                            terrain = 'mountains';
                        } else if (distance < radius * 0.6) {
                            terrain = terrains[Math.floor(Math.random() * terrains.length)];
                        } else {
                            terrain = Math.random() > 0.5 ? 'forest' : 'plains';
                        }
                        
                        this.hexData.set(hexKey, {
                            q, r, s,
                            terrain: terrain,
                            biome: this.getRandomBiome(),
                            elevation: Math.floor(Math.random() * 100)
                        });
                    }
                }
            }
        }
        
        // Add water around continent
        this.addWaterBorder(centerQ, centerR, radius + 5);
    }
    
    addWaterBorder(centerQ, centerR, radius) {
        // Simple water border generation
        for (let q = centerQ - radius; q <= centerQ + radius; q++) {
            for (let r = centerR - radius; r <= centerR + radius; r++) {
                const s = -q - r;
                
                const dq = q - centerQ;
                const dr = r - centerR; 
                const ds = s - (-centerQ - centerR);
                const distance = (Math.abs(dq) + Math.abs(dr) + Math.abs(ds)) / 2;
                
                if (distance <= radius && distance > radius - 8) {
                    const hexKey = `${q},${r},${s}`;
                    if (!this.hexData.has(hexKey) && Math.random() > 0.2) {
                        this.hexData.set(hexKey, {
                            q, r, s,
                            terrain: 'water',
                            biome: 'coastal',
                            elevation: 0
                        });
                    }
                }
            }
        }
    }
    
    loadContinents() {
        // Use the same generation as generateMap but with a different seed
        this.generateMap();
    }
    
    getRandomBiome() {
        return this.biomes[Math.floor(Math.random() * this.biomes.length)];
    }
    
    createFallbackPattern() {
        // Create a simple test pattern to ensure something renders
        const terrains = ['water', 'forest', 'plains', 'mountains'];
        
        for (let q = -10; q <= 10; q++) {
            for (let r = -10; r <= 10; r++) {
                const s = -q - r;
                const distance = Math.abs(q) + Math.abs(r) + Math.abs(s);
                
                if (distance <= 15) {
                    const hexKey = `${q},${r},${s}`;
                    let terrain;
                    
                    if (distance < 5) {
                        terrain = 'mountains';
                    } else if (distance < 10) {
                        terrain = 'forest';
                    } else if (distance < 13) {
                        terrain = 'plains';
                    } else {
                        terrain = 'water';
                    }
                    
                    this.hexData.set(hexKey, {
                        q, r, s,
                        terrain: terrain,
                        biome: this.getRandomBiome(),
                        elevation: Math.floor(Math.random() * 100)
                    });
                }
            }
        }
    }
    
    // View controls
    resetView() {
        this.camera = { x: this.canvas.width / 2, y: this.canvas.height / 2 };
        this.zoom = 0.3; // Start more zoomed out to see wider area
        this.updateUI();
        this.requestRender();
    }
    
    fitMapToView() {
        if (this.hexData.size === 0) return;
        
        let minQ = Infinity, maxQ = -Infinity;
        let minR = Infinity, maxR = -Infinity;
        
        this.hexData.forEach((hex) => {
            minQ = Math.min(minQ, hex.q);
            maxQ = Math.max(maxQ, hex.q);
            minR = Math.min(minR, hex.r);
            maxR = Math.max(maxR, hex.r);
        });
        
        const mapWidth = (maxQ - minQ) * this.hexSize * 1.5;
        const mapHeight = (maxR - minR) * this.hexSize * Math.sqrt(3);
        
        const zoomX = this.canvas.width / mapWidth;
        const zoomY = this.canvas.height / mapHeight;
        this.zoom = Math.min(zoomX, zoomY) * 0.6; // More zoomed out to see more
        
        const centerQ = (minQ + maxQ) / 2;
        const centerR = (minR + maxR) / 2;
        
        // Simpler camera centering
        this.camera.x = this.canvas.width / 2;
        this.camera.y = this.canvas.height / 2;
        
        this.updateUI();
        this.requestRender();
    }
    
    // Seed management
    showSeedModal() {
        document.getElementById('seed-input').value = this.seed;
        document.getElementById('seed-modal').classList.add('active');
    }
    
    confirmSeed() {
        const input = document.getElementById('seed-input');
        const newSeed = parseInt(input.value);
        if (newSeed && newSeed > 0) {
            this.seed = newSeed;
            this.updateUI();
        }
        this.cancelSeed();
    }
    
    cancelSeed() {
        document.getElementById('seed-modal').classList.remove('active');
    }
    
    showColorGuide() {
        document.getElementById('color-guide-modal').classList.add('active');
    }
    
    closeColorGuide() {
        document.getElementById('color-guide-modal').classList.remove('active');
    }
    
    
    applyPreset() {
        const preset = document.getElementById('color-preset').value;
        
        switch(preset) {
            case 'default':
                this.resetImportSettings();
                break;
                
            case 'ocean-as-plains':
                // Blue colors map to plains instead of water
                document.querySelector('[data-color="water"]').value = 'plains';
                document.querySelector('[data-color="forest"]').value = 'forest';
                document.querySelector('[data-color="plains"]').value = 'water';
                document.querySelector('[data-color="mountains"]').value = 'mountains';
                document.querySelector('[data-color="desert"]').value = 'desert';
                document.querySelector('[data-color="hills"]').value = 'hills';
                document.querySelector('[data-color="swamp"]').value = 'swamp';
                document.querySelector('[data-color="tundra"]').value = 'tundra';
                document.getElementById('default-terrain').value = 'plains';
                this.showMessage('Preset applied: Ocean as Plains', 'success');
                if (this.selectedImageFile) this.updatePreview();
                break;
                
            case 'inverted':
                // Swap water and land terrains
                document.querySelector('[data-color="water"]').value = 'plains';
                document.querySelector('[data-color="forest"]').value = 'water';
                document.querySelector('[data-color="plains"]').value = 'water';
                document.querySelector('[data-color="mountains"]').value = 'water';
                document.querySelector('[data-color="desert"]').value = 'water';
                document.querySelector('[data-color="hills"]').value = 'water';
                document.querySelector('[data-color="swamp"]').value = 'plains';
                document.querySelector('[data-color="tundra"]').value = 'water';
                document.getElementById('default-terrain').value = 'water';
                this.showMessage('Preset applied: Inverted terrain', 'success');
                if (this.selectedImageFile) this.updatePreview();
                break;
                
            case 'desert-world':
                // Everything becomes desert
                document.querySelector('[data-color="water"]').value = 'desert';
                document.querySelector('[data-color="forest"]').value = 'desert';
                document.querySelector('[data-color="plains"]').value = 'desert';
                document.querySelector('[data-color="mountains"]').value = 'mountains';
                document.querySelector('[data-color="desert"]').value = 'desert';
                document.querySelector('[data-color="hills"]').value = 'hills';
                document.querySelector('[data-color="swamp"]').value = 'desert';
                document.querySelector('[data-color="tundra"]').value = 'desert';
                document.getElementById('default-terrain').value = 'desert';
                this.showMessage('Preset applied: Desert World', 'success');
                if (this.selectedImageFile) this.updatePreview();
                break;
                
            case 'forest-world':
                // Everything becomes forest
                document.querySelector('[data-color="water"]').value = 'forest';
                document.querySelector('[data-color="forest"]').value = 'forest';
                document.querySelector('[data-color="plains"]').value = 'forest';
                document.querySelector('[data-color="mountains"]').value = 'mountains';
                document.querySelector('[data-color="desert"]').value = 'forest';
                document.querySelector('[data-color="hills"]').value = 'hills';
                document.querySelector('[data-color="swamp"]').value = 'swamp';
                document.querySelector('[data-color="tundra"]').value = 'forest';
                document.getElementById('default-terrain').value = 'forest';
                this.showMessage('Preset applied: Forest World', 'success');
                if (this.selectedImageFile) this.updatePreview();
                break;
        }
        
        // Update tolerance display in case it changed
        document.getElementById('tolerance-value').textContent = document.getElementById('color-tolerance').value;
    }
    
    randomSeed() {
        this.seed = Math.floor(Math.random() * 1000000) + 1;
        this.updateUI();
    }
    
    // Export functions
    saveJSON() {
        const mapData = {
            seed: this.seed,
            width: 200,
            height: 200,
            northDirection: this.northDirection, // Save north orientation
            hexes: [],
            created: new Date().toISOString()
        };
        
        this.hexData.forEach(hex => {
            mapData.hexes.push({
                q: hex.q,
                r: hex.r,
                s: hex.s,
                terrain: hex.terrain,
                biome: hex.biome,
                elevation: hex.elevation,
                explored: false,
                visible: true
            });
        });
        
        const blob = new Blob([JSON.stringify(mapData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `hex_map_${this.seed}_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        
        this.showMessage('Map saved successfully!');
    }
    
    copyToGame() {
        if (!this.sessionId) {
            this.showMessage('Please generate or load a map first', 'error');
            return;
        }
        
        // Save map data including north direction
        const mapData = {
            seed: this.seed,
            northDirection: this.northDirection,
            hexes: []
        };
        
        this.hexData.forEach(hex => {
            mapData.hexes.push({
                q: hex.q,
                r: hex.r,
                s: hex.s,
                terrain: hex.terrain,
                biome: hex.biome,
                elevation: hex.elevation || 0,
                visible: true,
                explored: false
            });
        });
        
        console.log(`Sending ${mapData.hexes.length} hexes to game`);
        if (mapData.hexes.length > 0) {
            console.log(`Sample hex being sent:`, mapData.hexes[0]);
        }
        
        // Send to backend to save for game use
        fetch('/api/save_map_for_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: this.sessionId,
                map_data: mapData
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showMessage('Map copied to game! You can now play it from the main menu.', 'success');
            } else {
                this.showMessage('Failed to copy map: ' + (data.error || 'Unknown error'), 'error');
            }
        })
        .catch(error => {
            this.showMessage('Error copying map: ' + error.message, 'error');
        });
    }
    
    takeScreenshot() {
        const link = document.createElement('a');
        link.download = `hex_map_screenshot_${Date.now()}.png`;
        link.href = this.canvas.toDataURL();
        link.click();
        
        this.showMessage('Screenshot saved!');
    }
    
    returnToMenu() {
        window.location.href = '/';
    }
    
    // Rendering
    render() {
        const now = performance.now();
        
        // Skip frames during rapid movement for smoother experience
        if (this.isDragging && now - this.lastRenderTime < 33) { // ~30fps during drag
            this.renderSkipFrames++;
            if (this.renderSkipFrames < 2) return;
        }
        this.renderSkipFrames = 0;
        this.lastRenderTime = now;
        
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Get visible bounds for frustum culling
        const viewBounds = this.getViewBounds();
        let visibleCount = 0;
        
        // Batch drawing operations
        const hexesToDraw = [];
        this.hexData.forEach((hex, hexKey) => {
            // Skip water hexes - they blend with ocean background
            if (hex.terrain !== 'water' && hex.terrain !== 'ocean' && hex.terrain !== 'deep_ocean' && hex.terrain !== 'shallow_water') {
                // Quick bounds check before expensive pixel calculations
                // Remove arbitrary 200 limit - check against actual viewport instead
                const pixel = this.hexToPixel(hex.q, hex.r);
                const margin = this.hexSize * 2;
                if (pixel.x >= -margin && pixel.x <= this.canvas.width + margin &&
                    pixel.y >= -margin && pixel.y <= this.canvas.height + margin) {
                    hexesToDraw.push(hex);
                    visibleCount++;
                }
            }
        });
        
        // Draw in batches by terrain type for better GPU performance
        const terrainBatches = {};
        hexesToDraw.forEach(hex => {
            if (!terrainBatches[hex.terrain]) terrainBatches[hex.terrain] = [];
            terrainBatches[hex.terrain].push(hex);
        });
        
        // Draw each terrain type together
        Object.values(terrainBatches).forEach(batch => {
            batch.forEach(hex => this.drawHex(hex));
        });
        
        // Draw hex grid only at very high zoom levels for performance
        if (this.zoom > 3.0) {
            this.drawHexGrid();
        }
        
        // Draw brush preview only in brush mode
        if (this.hoveredHex && !this.isDragging && this.currentTool === 'brush') {
            this.drawBrushPreview();
        }
        
        // Draw teleport target highlight in teleport mode
        if (this.teleportTarget && this.currentTool === 'teleport') {
            this.drawTeleportTarget();
        }
        
        // Draw player positions
        this.drawPlayers();
    }
    
    drawHex(hex) {
        const pixel = this.hexToPixel(hex.q, hex.r);
        const size = this.hexSize * this.zoom;
        
        // Skip if way off screen (generous margin that scales with zoom)
        const margin = Math.max(size * 3, 200);
        if (pixel.x < -margin || pixel.x > this.canvas.width + margin ||
            pixel.y < -margin || pixel.y > this.canvas.height + margin) {
            return;
        }
        
        this.ctx.save();
        this.ctx.translate(pixel.x, pixel.y);
        
        // Apply rotation to hex shape if north direction is set
        if (this.northDirection !== 0) {
            this.ctx.rotate((this.northDirection * Math.PI) / 180);
        }
        
        // Use simple shapes when zoomed out for performance
        // Changed threshold from 1.5 to 0.8 for earlier hex appearance
        if (this.zoom < 0.8) {
            // Always use circles - much faster and looks better than squares
            this.ctx.beginPath();
            this.ctx.arc(0, 0, size * 0.8, 0, Math.PI * 2);
            this.ctx.fillStyle = this.terrainColors[hex.terrain] || '#666666';
            this.ctx.fill();
        } else {
            // Full hexagon when zoomed in enough to appreciate detail
            this.ctx.beginPath();
            for (let i = 0; i < 6; i++) {
                const angle = Math.PI / 3 * i;
                const x = size * Math.cos(angle);
                const y = size * Math.sin(angle);
                
                if (i === 0) {
                    this.ctx.moveTo(x, y);
                } else {
                    this.ctx.lineTo(x, y);
                }
            }
            this.ctx.closePath();
            this.ctx.fillStyle = this.terrainColors[hex.terrain] || '#666666';
            this.ctx.fill();
            
            // Only draw borders when zoomed in enough
            if (this.zoom > 2.0) {
                this.ctx.strokeStyle = '#333333';
                this.ctx.lineWidth = 1;
                this.ctx.stroke();
            }
        }
        
        this.ctx.restore();
    }
    
    drawBrushPreview() {
        this.brushPreview.forEach(hexKey => {
            const [q, r, s] = hexKey.split(',').map(Number);
            const pixel = this.hexToPixel(q, r);
            const size = this.hexSize * this.zoom;
            
            this.ctx.save();
            this.ctx.translate(pixel.x, pixel.y);
            
            // Apply rotation for brush preview too
            if (this.northDirection !== 0) {
                this.ctx.rotate((this.northDirection * Math.PI) / 180);
            }
            
            this.ctx.globalAlpha = 0.3;
            
            // Use same LOD system for brush preview
            if (this.zoom < 0.8) {
                this.ctx.beginPath();
                this.ctx.arc(0, 0, size * 0.8, 0, Math.PI * 2);
                this.ctx.fillStyle = this.terrainColors[this.selectedTerrain];
                this.ctx.fill();
            } else {
                this.ctx.beginPath();
                for (let i = 0; i < 6; i++) {
                    const angle = Math.PI / 3 * i;
                    const x = size * Math.cos(angle);
                    const y = size * Math.sin(angle);
                    
                    if (i === 0) {
                        this.ctx.moveTo(x, y);
                    } else {
                        this.ctx.lineTo(x, y);
                    }
                }
                this.ctx.closePath();
                this.ctx.fillStyle = this.terrainColors[this.selectedTerrain];
                this.ctx.fill();
                
                if (this.zoom > 2.0) {
                    this.ctx.strokeStyle = '#FFD700';
                    this.ctx.lineWidth = 2;
                    this.ctx.stroke();
                }
            }
            
            this.ctx.restore();
        });
    }
    
    drawHexGrid() {
        // Simplified grid - just draw circles instead of hexagons for performance
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        this.ctx.lineWidth = 0.5;
        
        // Get visible area bounds with larger spacing
        const viewBounds = this.getViewBounds();
        const spacing = Math.max(3, Math.floor(5 / this.zoom)); // Larger spacing at lower zoom
        
        // Draw simple circle grid
        for (let q = viewBounds.minQ; q <= viewBounds.maxQ; q += spacing) {
            for (let r = viewBounds.minR; r <= viewBounds.maxR; r += spacing) {
                const pixel = this.hexToPixel(q, r);
                const size = this.hexSize * this.zoom;
                
                // Quick bounds check
                if (pixel.x > -size && pixel.x < this.canvas.width + size &&
                    pixel.y > -size && pixel.y < this.canvas.height + size) {
                    this.ctx.beginPath();
                    this.ctx.arc(pixel.x, pixel.y, size * 0.8, 0, Math.PI * 2);
                    this.ctx.stroke();
                }
            }
        }
    }
    
    getViewBounds() {
        // Calculate hex coordinates for visible area with generous margins
        const topLeft = this.pixelToHex(0, 0);
        const bottomRight = this.pixelToHex(this.canvas.width, this.canvas.height);
        
        // Use much larger margins that scale with zoom
        const margin = Math.max(20, 100 / this.zoom);
        
        return {
            minQ: Math.floor(topLeft.q) - margin,
            maxQ: Math.ceil(bottomRight.q) + margin,
            minR: Math.floor(topLeft.r) - margin,
            maxR: Math.ceil(bottomRight.r) + margin
        };
    }
    
    // UI updates
    updateUI() {
        document.getElementById('current-seed').textContent = this.seed;
        document.getElementById('zoom-display').textContent = Math.round(this.zoom * 100) + '%';
    }
    
    updateStats() {
        const stats = {};
        this.hexData.forEach(hex => {
            stats[hex.terrain] = (stats[hex.terrain] || 0) + 1;
        });
        
        document.getElementById('hex-count').textContent = this.hexData.size;
        
        const statsDiv = document.getElementById('terrain-stats');
        statsDiv.innerHTML = '';
        
        Object.entries(stats).forEach(([terrain, count]) => {
            const div = document.createElement('div');
            div.innerHTML = `${terrain}: ${count}`;
            div.style.color = this.terrainColors[terrain];
            div.style.fontSize = '0.75rem';
            statsDiv.appendChild(div);
        });
    }
    
    showLoading(show) {
        const loading = document.getElementById('loading');
        if (show) {
            loading.classList.remove('hidden');
        } else {
            loading.classList.add('hidden');
        }
    }
    
    showMessage(message) {
        // Simple message display
        console.log(message);
        // Could add a toast notification here
    }
    
    updateToolUI() {
        const brushControls = document.getElementById('brush-controls');
        const terrainSection = document.getElementById('terrain-section');
        const teleportControls = document.querySelector('.teleport-controls');
        
        if (this.currentTool === 'brush') {
            brushControls.classList.remove('hidden');
            terrainSection.classList.remove('hidden');
            teleportControls.classList.add('hidden');
            this.canvas.style.cursor = 'crosshair';
        } else if (this.currentTool === 'teleport') {
            brushControls.classList.add('hidden');
            terrainSection.classList.add('hidden');
            teleportControls.classList.remove('hidden');
            this.canvas.style.cursor = 'crosshair';
            this.setupTeleportMode();
        } else {
            brushControls.classList.add('hidden');
            terrainSection.classList.add('hidden');
            teleportControls.classList.add('hidden');
            this.canvas.style.cursor = 'grab';
        }
    }
    
    showHexInfo(hex, mousePos) {
        const hexKey = `${hex.q},${hex.r},${hex.s}`;
        const hexData = this.hexData.get(hexKey);
        
        if (hexData) {
            // Show hex information in tooltip
            this.updateTooltip(hex, mousePos);
            
            // Could expand this to show a modal with more details
            console.log(`Hex (${hex.q}, ${hex.r}, ${hex.s}):`, hexData);
        } else {
            console.log(`Empty hex at (${hex.q}, ${hex.r}, ${hex.s})`);
        }
    }
    
    // Teleport functionality
    setupTeleportMode() {
        this.selectedPlayer = null;
        this.teleportTarget = null;
        this.updateTeleportUI();
        this.setupTeleportEventListeners();
    }
    
    setupTeleportEventListeners() {
        // Player selection
        const playerSelect = document.getElementById('teleport-player-select');
        if (playerSelect && !playerSelect.hasAttribute('data-listener-added')) {
            playerSelect.addEventListener('change', (e) => {
                this.selectedPlayer = e.target.value;
                this.updateTeleportButton();
            });
            playerSelect.setAttribute('data-listener-added', 'true');
        }
        
        // Teleport button
        const teleportBtn = document.getElementById('teleport-confirm');
        if (teleportBtn && !teleportBtn.hasAttribute('data-listener-added')) {
            teleportBtn.addEventListener('click', () => this.performTeleport());
            teleportBtn.setAttribute('data-listener-added', 'true');
        }
    }
    
    updateTeleportUI() {
        // Update player dropdown
        const playerSelect = document.getElementById('teleport-player-select');
        if (playerSelect) {
            playerSelect.innerHTML = '<option value="">Select a player...</option>';
            this.playerPositions.forEach(player => {
                const option = document.createElement('option');
                option.value = player.name;
                option.textContent = player.name || 'Unknown Player';
                option.style.color = player.color || '#FFD700';
                playerSelect.appendChild(option);
            });
        }
        
        this.updateTeleportButton();
    }
    
    selectTeleportTarget(hex) {
        this.teleportTarget = hex;
        
        // Update target display
        const targetDisplay = document.getElementById('teleport-target-display');
        if (targetDisplay) {
            targetDisplay.textContent = `Hex: (${hex.q}, ${hex.r}, ${hex.s})`;
        }
        
        this.updateTeleportButton();
        this.render(); // Re-render to show selected hex
    }
    
    updateTeleportButton() {
        const teleportBtn = document.getElementById('teleport-confirm');
        if (teleportBtn) {
            const canTeleport = this.selectedPlayer && this.teleportTarget;
            teleportBtn.disabled = !canTeleport;
            
            if (canTeleport) {
                teleportBtn.textContent = `Teleport ${this.selectedPlayer} to (${this.teleportTarget.q}, ${this.teleportTarget.r}, ${this.teleportTarget.s})`;
            } else {
                teleportBtn.textContent = 'Select player and target hex';
            }
        }
    }
    
    async performTeleport() {
        if (!this.selectedPlayer || !this.teleportTarget) {
            console.error('Missing player or target for teleport');
            return;
        }
        
        try {
            const response = await fetch('/api/teleport_player', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    player_name: this.selectedPlayer,
                    target_hex: {
                        q: this.teleportTarget.q,
                        r: this.teleportTarget.r,
                        s: this.teleportTarget.s
                    }
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log(`Successfully teleported ${this.selectedPlayer} to (${this.teleportTarget.q}, ${this.teleportTarget.r}, ${this.teleportTarget.s})`);
                // Reset selections
                this.selectedPlayer = null;
                this.teleportTarget = null;
                this.updateTeleportUI();
                
                // Update target display
                const targetDisplay = document.getElementById('teleport-target-display');
                if (targetDisplay) {
                    targetDisplay.textContent = 'Click on map to select target';
                }
                
                // Refresh player positions
                this.fetchPlayerPositions();
                
                // Auto-sync after teleportation
                this.triggerAutoSync();
            } else {
                console.error('Failed to teleport player:', result.error);
            }
        } catch (error) {
            console.error('Error during teleport:', error);
        }
    }
    
    // Player tracking
    startPlayerTracking() {
        // Fetch player positions every 2 seconds
        this.fetchPlayerPositions();
        setInterval(() => this.fetchPlayerPositions(), 2000);
    }
    
    fetchPlayerPositions() {
        if (!this.sessionId) return;
        
        fetch(`/api/get_player_positions/${this.sessionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.playerPositions = data.players;
                this.requestRender(); // Re-render to show updated positions
            }
        })
        .catch(error => {
            console.error('Failed to fetch player positions:', error);
        });
    }
    
    triggerAutoSync() {
        if (!this.autoSync) return;
        
        // Clear existing timer
        if (this.syncDebounceTimer) {
            clearTimeout(this.syncDebounceTimer);
        }
        
        // Set new timer - sync after 1 second of no changes
        this.syncDebounceTimer = setTimeout(() => {
            console.log('Auto-syncing world after master action...');
            this.syncWorld(true); // Pass true to indicate auto-sync
        }, 1000);
    }
    
    syncWorld(isAutoSync = false) {
        if (!this.sessionId) {
            if (!isAutoSync) {
                this.showMessage('No active session to sync', 'error');
            }
            return;
        }
        
        this.showLoading(true);
        const message = isAutoSync ? 'Auto-syncing world...' : 'Syncing world with active game sessions...';
        this.showMessage(message, 'info');
        
        // First, prepare the hex data to send
        const hexData = [];
        this.hexData.forEach(hex => {
            hexData.push({
                q: hex.q,
                r: hex.r,
                s: hex.s,
                terrain: hex.terrain,
                biome: hex.biome || 'temperate',
                elevation: hex.elevation || 0,
                visible: hex.visible !== false,
                explored: hex.explored || false
            });
        });
        
        console.log(`Syncing ${hexData.length} hexes to backend`);
        
        // Send hex data along with sync request
        fetch('/api/force_sync_world', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: this.sessionId,
                hexes: hexData,
                north_direction: this.northDirection
            })
        })
        .then(response => response.json())
        .then(data => {
            this.showLoading(false);
            if (data.success) {
                this.showMessage(`Successfully synced ${data.synced_games} game sessions!`, 'success');
                console.log(`Synced ${hexData.length} hexes to ${data.synced_games} game sessions`);
            } else {
                this.showMessage('Sync failed: ' + (data.error || 'Unknown error'), 'error');
            }
        })
        .catch(error => {
            this.showLoading(false);
            console.error('Sync error:', error);
            this.showMessage('Network error during sync: ' + error.message, 'error');
        });
    }
    
    updateSessionName() {
        const nameInput = document.getElementById('session-name');
        const newName = nameInput.value.trim();
        
        console.log('Update session name called:', newName, 'Session ID:', this.sessionId);
        
        if (!newName) {
            this.showMessage('Please enter a session name', 'error');
            return;
        }
        
        if (!this.sessionId) {
            this.showMessage('No active session to update', 'error');
            return;
        }
        
        fetch('/api/update_session_name', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: this.sessionId,
                session_name: newName
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.sessionName = newName;
                this.updateSessionUI();
                this.showMessage(`Session name updated to "${newName}"`, 'success');
            } else {
                this.showMessage('Failed to update session name: ' + (data.error || 'Unknown error'), 'error');
            }
        })
        .catch(error => {
            console.error('Session name update error:', error);
            this.showMessage('Network error: ' + error.message, 'error');
        });
    }
    
    updateSessionUI() {
        const nameInput = document.getElementById('session-name');
        const statusElement = document.getElementById('session-status');
        
        if (this.sessionName) {
            nameInput.value = this.sessionName;
        }
        
        if (this.sessionId) {
            statusElement.textContent = `Active (ID: ${this.sessionId})`;
            statusElement.className = 'session-status';
        } else {
            statusElement.textContent = 'Inactive';
            statusElement.className = 'session-status inactive';
        }
    }
    
    drawPlayers() {
        // Draw each player as a special marker
        this.playerPositions.forEach(player => {
            const pixel = this.hexToPixel(player.q, player.r);
            const size = this.hexSize * this.zoom;
            
            // Skip if off screen
            if (pixel.x < -size || pixel.x > this.canvas.width + size ||
                pixel.y < -size || pixel.y > this.canvas.height + size) {
                return;
            }
            
            this.ctx.save();
            this.ctx.translate(pixel.x, pixel.y);
            
            // Draw player marker
            this.ctx.beginPath();
            this.ctx.arc(0, 0, size * 0.4, 0, Math.PI * 2);
            this.ctx.fillStyle = player.color || '#FFD700'; // Use player's color or default gold
            this.ctx.fill();
            this.ctx.strokeStyle = '#000000';
            this.ctx.lineWidth = 2;
            this.ctx.stroke();
            
            // Draw player icon (simple triangle)
            this.ctx.beginPath();
            this.ctx.moveTo(0, -size * 0.25);
            this.ctx.lineTo(-size * 0.15, size * 0.15);
            this.ctx.lineTo(size * 0.15, size * 0.15);
            this.ctx.closePath();
            this.ctx.fillStyle = '#000000';
            this.ctx.fill();
            
            // Draw player name (always visible but scale with zoom)
            this.ctx.fillStyle = '#FFFFFF';
            this.ctx.strokeStyle = '#000000';
            this.ctx.lineWidth = Math.max(2, this.zoom * 2);
            this.ctx.font = `bold ${Math.max(12, size * 0.3)}px Arial`;
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'top';
            const text = player.name || 'Player';
            this.ctx.strokeText(text, 0, size * 0.6);
            this.ctx.fillText(text, 0, size * 0.6);
            
            this.ctx.restore();
        });
    }
    
    drawTeleportTarget() {
        const pixel = this.hexToPixel(this.teleportTarget.q, this.teleportTarget.r);
        const size = this.hexSize * this.zoom;
        
        // Skip if off screen
        if (pixel.x < -size || pixel.x > this.canvas.width + size ||
            pixel.y < -size || pixel.y > this.canvas.height + size) {
            return;
        }
        
        this.ctx.save();
        this.ctx.translate(pixel.x, pixel.y);
        
        // Draw pulsing highlight ring
        const time = Date.now() * 0.003; // Slower pulsing
        const pulseSize = 0.6 + 0.2 * Math.sin(time);
        
        // Outer glow effect
        this.ctx.beginPath();
        this.ctx.arc(0, 0, size * pulseSize, 0, Math.PI * 2);
        this.ctx.strokeStyle = '#87CEEB';
        this.ctx.lineWidth = 4;
        this.ctx.globalAlpha = 0.6;
        this.ctx.stroke();
        
        // Inner bright ring
        this.ctx.beginPath();
        this.ctx.arc(0, 0, size * (pulseSize - 0.1), 0, Math.PI * 2);
        this.ctx.strokeStyle = '#FFD700';
        this.ctx.lineWidth = 2;
        this.ctx.globalAlpha = 1.0;
        this.ctx.stroke();
        
        // Target crosshairs
        this.ctx.strokeStyle = '#FFD700';
        this.ctx.lineWidth = 3;
        const crossSize = size * 0.3;
        
        // Horizontal line
        this.ctx.beginPath();
        this.ctx.moveTo(-crossSize, 0);
        this.ctx.lineTo(crossSize, 0);
        this.ctx.stroke();
        
        // Vertical line
        this.ctx.beginPath();
        this.ctx.moveTo(0, -crossSize);
        this.ctx.lineTo(0, crossSize);
        this.ctx.stroke();
        
        this.ctx.restore();
    }
    
    // Performance optimizations
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    }
    
    centerOnHex(x, y) {
        // Calculate hex position in pixels
        const hexWidth = Math.sqrt(3) * this.hexRadius;
        const hexHeight = 2 * this.hexRadius;
        
        const pixelX = x * hexWidth * 0.75;
        const pixelY = y * hexHeight + (x % 2) * hexHeight / 2;
        
        // Center the view on this position
        this.panX = -pixelX + this.canvas.width / 2;
        this.panY = -pixelY + this.canvas.height / 2;
        
        this.requestRender();
    }
    
    requestRender() {
        if (this.frameId) {
            cancelAnimationFrame(this.frameId);
        }
        this.frameId = requestAnimationFrame(() => {
            this.render();
            this.frameId = null;
        });
    }
}

// Movement Approval Queue Manager (for Master view)
class MovementApprovalManager {
    constructor() {
        console.log('MovementApprovalManager initialized');
        this.sessionId = null;
        this.pollInterval = null;
        this.queueElement = document.getElementById('movement-approval-queue');
        this.listElement = document.getElementById('approval-list');
        this.toggleBtn = document.getElementById('toggle-approval-queue');
        
        if (this.toggleBtn) {
            this.toggleBtn.addEventListener('click', () => this.toggleQueue());
        }
        
        // Check if user is master and has an active session
        this.checkMasterStatus();
    }
    
    async checkMasterStatus() {
        // Wait for the hex map generator to initialize
        setTimeout(async () => {
            // Get session ID from the generator instance
            if (window.hexMapGenerator && window.hexMapGenerator.sessionId) {
                this.sessionId = window.hexMapGenerator.sessionId;
                console.log('Found session ID from generator:', this.sessionId);
            }
            
            // Also try URL params as fallback
            if (!this.sessionId) {
                const urlParams = new URLSearchParams(window.location.search);
                this.sessionId = urlParams.get('session_id');
            }
            
            if (!this.sessionId) {
                console.log('No session ID found, approval queue hidden');
                return;
            }
            
            console.log('Checking master status for session:', this.sessionId);
            
            // Check if user is the master of this session
            try {
                const response = await fetch(`/api/session/${this.sessionId}`);
                const data = await response.json();
                
                console.log('Master status response:', data);
                
                if (data.success && data.is_master) {
                    console.log('User is master, showing approval queue');
                    this.showQueue();
                    this.startPolling();
                } else {
                    console.log('User is not master or session not found');
                }
            } catch (error) {
                console.error('Failed to check master status:', error);
            }
        }, 2000); // Wait 2 seconds for the generator to initialize
    }
    
    showQueue() {
        if (this.queueElement) {
            this.queueElement.style.display = 'block';
        }
    }
    
    toggleQueue() {
        if (this.listElement) {
            this.listElement.classList.toggle('collapsed');
            this.toggleBtn.textContent = this.listElement.classList.contains('collapsed') ? '▶' : '▼';
        }
    }
    
    startPolling() {
        // Poll for movement requests every 3 seconds
        this.pollInterval = setInterval(() => this.fetchRequests(), 3000);
        this.fetchRequests(); // Initial fetch
    }
    
    async fetchRequests() {
        if (!this.sessionId) return;
        
        try {
            const response = await fetch(`/api/get_movement_requests?session_id=${this.sessionId}`);
            const data = await response.json();
            
            if (data.success) {
                this.updateRequestList(data.requests);
            }
        } catch (error) {
            console.error('Failed to fetch movement requests:', error);
        }
    }
    
    updateRequestList(requests) {
        if (!this.listElement) return;
        
        if (requests.length === 0) {
            this.listElement.innerHTML = '<div style="color: #888; text-align: center; padding: 10px;">No pending requests</div>';
            return;
        }
        
        this.listElement.innerHTML = '';
        
        requests.forEach(request => {
            const item = document.createElement('div');
            item.className = 'approval-item';
            
            const playerSpan = document.createElement('span');
            playerSpan.className = 'approval-player';
            playerSpan.textContent = request.player_name;
            
            const targetSpan = document.createElement('span');
            targetSpan.className = 'approval-target';
            const [q, r, s] = request.target;
            targetSpan.textContent = `→ Hex (${q}, ${r})`;
            
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'approval-actions';
            
            const approveBtn = document.createElement('button');
            approveBtn.className = 'approval-btn approve';
            approveBtn.textContent = 'Approve';
            approveBtn.onclick = () => this.approveRequest(request.request_id);
            
            const declineBtn = document.createElement('button');
            declineBtn.className = 'approval-btn decline';
            declineBtn.textContent = 'Decline';
            declineBtn.onclick = () => this.declineRequest(request.request_id);
            
            const centerBtn = document.createElement('button');
            centerBtn.className = 'approval-btn center';
            centerBtn.textContent = 'Center';
            centerBtn.onclick = () => this.centerOnHex(q, r, s);
            
            actionsDiv.appendChild(approveBtn);
            actionsDiv.appendChild(declineBtn);
            actionsDiv.appendChild(centerBtn);
            
            item.appendChild(playerSpan);
            item.appendChild(targetSpan);
            item.appendChild(actionsDiv);
            
            this.listElement.appendChild(item);
        });
    }
    
    async approveRequest(requestId) {
        try {
            const response = await fetch('/api/approve_movement', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    request_id: requestId,
                    session_id: this.sessionId
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.fetchRequests(); // Refresh the list
            }
        } catch (error) {
            console.error('Failed to approve request:', error);
        }
    }
    
    async declineRequest(requestId) {
        try {
            const response = await fetch('/api/decline_movement', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    request_id: requestId,
                    session_id: this.sessionId
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.fetchRequests(); // Refresh the list
            }
        } catch (error) {
            console.error('Failed to decline request:', error);
        }
    }
    
    centerOnHex(q, r, s) {
        // Find the hex map generator instance and center on the hex
        if (window.hexMapGenerator) {
            // Convert cube to offset coordinates for centering
            const x = q;
            const y = r + (q - (q & 1)) / 2;
            window.hexMapGenerator.centerOnHex(x, y);
        }
    }
    
    destroy() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    const generator = new HexMapGenerator();
    window.hexMapGenerator = generator; // Store globally for access
    
    // Initialize approval manager for master view
    const approvalManager = new MovementApprovalManager();
});