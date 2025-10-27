// Hex map renderer for web
class HexRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.hexSize = 30;
        this.hexes = new Map();
        this.currentPosition = { q: 0, r: 0, s: 0 };
        this.camera = { x: 0, y: 0, zoom: 1 };
        this.isDragging = false;
        this.lastMousePos = { x: 0, y: 0 };
        this.hoveredHex = null;
        this.fogEnabled = true;
        this.northDirection = 0; // North direction in degrees
        
        this.terrainColors = {
            water: '#4682B4',
            grassland: '#90EE90',
            forest: '#228B22',
            hills: '#8FBC8F',
            mountains: '#696969',
            desert: '#F4A460',
            swamp: '#556B2F',
            tundra: '#F0F8FF',
            coastal: '#87CEEB',
            ocean: '#191970'
        };
        
        this.setupEventListeners();
        this.resizeCanvas();
    }
    
    setupEventListeners() {
        // Mouse events
        this.canvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.handleMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.handleWheel(e));
        this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
        
        // Touch events for mobile
        this.canvas.addEventListener('touchstart', (e) => this.handleTouchStart(e));
        this.canvas.addEventListener('touchmove', (e) => this.handleTouchMove(e));
        this.canvas.addEventListener('touchend', (e) => this.handleTouchEnd(e));
        
        // Window resize
        window.addEventListener('resize', () => this.resizeCanvas());
    }
    
    resizeCanvas() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        this.centerView();
    }
    
    centerView() {
        const currentHex = this.hexToPixel(this.currentPosition.q, this.currentPosition.r);
        this.camera.x = -currentHex.x + this.canvas.width / 2;
        this.camera.y = -currentHex.y + this.canvas.height / 2;
    }
    
    // Coordinate conversion
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
        
        return { x, y };
    }
    
    pixelToHex(x, y) {
        // Apply camera transformation
        let worldX = (x - this.camera.x) / this.camera.zoom;
        let worldY = (y - this.camera.y) / this.camera.zoom;
        
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
    
    // Mouse handling
    getMousePos(e) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }
    
    handleMouseDown(e) {
        const pos = this.getMousePos(e);
        
        if (e.button === 0) { // Left click
            const hex = this.pixelToHex(pos.x, pos.y);
            const hexKey = `${hex.q},${hex.r},${hex.s}`;
            
            if (this.hexes.has(hexKey) && this.hexes.get(hexKey).visible) {
                // Hex click - emit event
                this.onHexClick(hex);
            } else {
                // Start dragging
                this.isDragging = true;
                this.lastMousePos = pos;
                this.canvas.classList.add('grabbing');
            }
        }
    }
    
    handleMouseMove(e) {
        const pos = this.getMousePos(e);
        
        if (this.isDragging) {
            const dx = pos.x - this.lastMousePos.x;
            const dy = pos.y - this.lastMousePos.y;
            
            this.camera.x += dx;
            this.camera.y += dy;
            
            this.lastMousePos = pos;
        } else {
            // Update hovered hex
            const hex = this.pixelToHex(pos.x, pos.y);
            const hexKey = `${hex.q},${hex.r},${hex.s}`;
            
            if (this.hexes.has(hexKey) && this.hexes.get(hexKey).visible) {
                this.hoveredHex = hex;
                this.onHexHover(hex, pos);
            } else {
                this.hoveredHex = null;
                this.onHexHover(null);
            }
        }
    }
    
    handleMouseUp(e) {
        this.isDragging = false;
        this.canvas.classList.remove('grabbing');
    }
    
    handleWheel(e) {
        e.preventDefault();
        
        const pos = this.getMousePos(e);
        const zoomFactor = 1.1;
        const oldZoom = this.camera.zoom;
        
        if (e.deltaY < 0) {
            this.camera.zoom = Math.min(this.camera.zoom * zoomFactor, 3);
        } else {
            this.camera.zoom = Math.max(this.camera.zoom / zoomFactor, 0.3);
        }
        
        // Zoom towards mouse position
        const zoomRatio = this.camera.zoom / oldZoom;
        this.camera.x = pos.x - (pos.x - this.camera.x) * zoomRatio;
        this.camera.y = pos.y - (pos.y - this.camera.y) * zoomRatio;
    }
    
    // Touch handling for mobile
    handleTouchStart(e) {
        e.preventDefault();
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            this.handleMouseDown({ 
                clientX: touch.clientX, 
                clientY: touch.clientY, 
                button: 0 
            });
        }
    }
    
    handleTouchMove(e) {
        e.preventDefault();
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            this.handleMouseMove({ 
                clientX: touch.clientX, 
                clientY: touch.clientY 
            });
        }
    }
    
    handleTouchEnd(e) {
        e.preventDefault();
        this.handleMouseUp({ button: 0 });
    }
    
    // Drawing methods
    drawHex(q, r, s, hexData) {
        const pixel = this.hexToPixel(q, r);
        const x = pixel.x * this.camera.zoom + this.camera.x;
        const y = pixel.y * this.camera.zoom + this.camera.y;
        const size = this.hexSize * this.camera.zoom;
        
        // Skip if off-screen (with margin)
        const margin = size * 2;
        if (x < -margin || x > this.canvas.width + margin || 
            y < -margin || y > this.canvas.height + margin) {
            return;
        }
        
        this.ctx.save();
        this.ctx.translate(x, y);
        
        // Apply rotation to hex shape if north direction is set
        if (this.northDirection !== 0) {
            this.ctx.rotate((this.northDirection * Math.PI) / 180);
        }
        
        // Draw hex shape
        this.ctx.beginPath();
        for (let i = 0; i < 6; i++) {
            const angle = Math.PI / 3 * i;
            const hx = size * Math.cos(angle);
            const hy = size * Math.sin(angle);
            
            if (i === 0) {
                this.ctx.moveTo(hx, hy);
            } else {
                this.ctx.lineTo(hx, hy);
            }
        }
        this.ctx.closePath();
        
        // Fill with terrain color
        let fillColor = this.terrainColors[hexData.terrain] || '#888888';
        
        // Apply fog if not explored
        if (this.fogEnabled && !hexData.explored) {
            fillColor = this.adjustColorBrightness(fillColor, 0.3);
        }
        
        this.ctx.fillStyle = fillColor;
        this.ctx.fill();
        
        // Draw border
        if (q === this.currentPosition.q && r === this.currentPosition.r && s === this.currentPosition.s) {
            // Current position - special border
            this.ctx.strokeStyle = '#FFD700';
            this.ctx.lineWidth = 3 * this.camera.zoom;
        } else if (this.hoveredHex && q === this.hoveredHex.q && r === this.hoveredHex.r && s === this.hoveredHex.s) {
            // Hovered hex
            this.ctx.strokeStyle = '#FFFFFF';
            this.ctx.lineWidth = 2 * this.camera.zoom;
        } else {
            // Normal border
            this.ctx.strokeStyle = '#666666';
            this.ctx.lineWidth = 1 * this.camera.zoom;
        }
        this.ctx.stroke();
        
        // Draw location marker if present
        if (hexData.has_location && size > 15) {
            this.ctx.fillStyle = '#FF6B6B';
            this.ctx.beginPath();
            this.ctx.arc(0, 0, size * 0.2, 0, Math.PI * 2);
            this.ctx.fill();
        }
        
        // Draw coordinates if zoomed in enough
        if (this.camera.zoom > 1.5 && size > 20) {
            this.ctx.fillStyle = '#FFFFFF';
            this.ctx.font = `${Math.max(8, size * 0.2)}px Arial`;
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText(`${q},${r}`, 0, 0);
        }
        
        this.ctx.restore();
    }
    
    adjustColorBrightness(color, factor) {
        // Simple brightness adjustment
        const hex = color.replace('#', '');
        const r = parseInt(hex.substr(0, 2), 16);
        const g = parseInt(hex.substr(2, 2), 16);
        const b = parseInt(hex.substr(4, 2), 16);
        
        const newR = Math.floor(r * factor);
        const newG = Math.floor(g * factor);
        const newB = Math.floor(b * factor);
        
        return `rgb(${newR}, ${newG}, ${newB})`;
    }
    
    // Public methods
    updateMapData(mapData) {
        this.hexes.clear();
        
        for (const hex of mapData.hexes) {
            const key = `${hex.q},${hex.r},${hex.s}`;
            this.hexes.set(key, hex);
        }
        
        this.currentPosition = mapData.current_position;
        
        // Load north direction if provided
        if (mapData.north_direction !== undefined) {
            this.setNorthDirection(mapData.north_direction);
        }
    }
    
    render() {
        // Clear canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw hexes
        for (const [key, hexData] of this.hexes) {
            if (hexData.visible) {
                this.drawHex(hexData.q, hexData.r, hexData.s, hexData);
            }
        }
        
        // Draw grid lines if zoomed in
        if (this.camera.zoom > 2) {
            this.drawGrid();
        }
    }
    
    drawGrid() {
        // Optional: draw hex grid lines
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        this.ctx.lineWidth = 0.5;
        
        // This would require more complex math to draw proper hex grid lines
        // For now, we'll skip this feature
    }
    
    toggleFog() {
        this.fogEnabled = !this.fogEnabled;
    }
    
    zoomTo(zoom) {
        this.camera.zoom = Math.max(0.3, Math.min(3, zoom));
    }
    
    setNorthDirection(degrees) {
        this.northDirection = degrees || 0;
    }
    
    // Event callbacks (to be overridden)
    onHexClick(hex) {
        // Override this method
    }
    
    onHexHover(hex, mousePos = null) {
        // Override this method
    }
}