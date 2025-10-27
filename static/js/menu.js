// Main menu JavaScript
class MainMenu {
    constructor() {
        this.canvas = document.getElementById('background-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.settings = this.loadSettings();
        this.currentSeed = this.generateRandomSeed();
        this.sessions = [];
        this.currentUser = null;
        this.currentTab = 'login';
        
        this.setupCanvas();
        this.setupEventListeners();
        this.createParticles();
        this.animate();
        this.initAuth();
    }
    
    setupCanvas() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
        
        // Handle resize
        window.addEventListener('resize', () => {
            this.canvas.width = window.innerWidth;
            this.canvas.height = window.innerHeight;
            this.createParticles();
        });
    }
    
    setupEventListeners() {
        // Menu buttons
        document.getElementById('new-adventure').addEventListener('click', () => this.newAdventure());
        document.getElementById('map-generator').addEventListener('click', () => this.openMapGenerator());
        document.getElementById('settings').addEventListener('click', () => this.openSettings());
        
        // Session modal controls
        document.getElementById('cancel-session').addEventListener('click', () => this.closeSessionModal());
        document.getElementById('create-new-session').addEventListener('click', () => this.createNewSession());
        document.getElementById('randomize-new-seed').addEventListener('click', () => {
            const newSeed = this.generateRandomSeed();
            document.getElementById('new-seed-input').value = newSeed;
        });
        
        // Settings modal
        document.getElementById('save-settings').addEventListener('click', () => this.saveSettings());
        document.getElementById('cancel-settings').addEventListener('click', () => this.closeSettings());
        document.getElementById('refresh-models').addEventListener('click', () => this.refreshModels());
        
        // Scale controls
        document.getElementById('scale-down').addEventListener('click', () => this.changeScale(-0.1));
        document.getElementById('scale-up').addEventListener('click', () => this.changeScale(0.1));
        
        // Authentication controls
        document.querySelectorAll('.auth-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
        
        document.getElementById('login-btn').addEventListener('click', () => this.handleLogin());
        document.getElementById('register-btn').addEventListener('click', () => this.handleRegister());
        
        // Handle Enter key in forms
        document.getElementById('login-password').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleLogin();
            }
        });
        
        document.getElementById('reg-confirm-password').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleRegister();
            }
        });
        
        // Role selection
        document.querySelectorAll('.role-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.role-btn').forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.playerRole = e.currentTarget.dataset.role;
                
                // Show/hide color selection based on role
                const colorSection = document.getElementById('player-color-section');
                if (this.playerRole === 'player') {
                    colorSection.style.display = 'block';
                } else {
                    colorSection.style.display = 'none';
                }
            });
        });
        
        // Color selection
        document.querySelectorAll('.color-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.color-btn').forEach(b => b.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.playerColor = e.currentTarget.dataset.color;
            });
        });
        
        // File input
        document.getElementById('file-input').addEventListener('change', (e) => this.handleFileLoad(e));
        
        // ESC key to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeSettings();
            }
        });
    }
    
    createParticles() {
        this.particles = [];
        const particleCount = Math.min(50, Math.floor((window.innerWidth * window.innerHeight) / 30000));
        
        for (let i = 0; i < Math.max(10, particleCount); i++) {
            this.particles.push({
                x: Math.random() * window.innerWidth,
                y: Math.random() * window.innerHeight,
                size: Math.random() * 30 + 10,
                speed: Math.random() * 2 + 0.5,
                alpha: Math.random() * 0.4 + 0.1,
                rotation: Math.random() * 360
            });
        }
    }
    
    drawHex(x, y, size, alpha = 0.3) {
        this.ctx.save();
        this.ctx.translate(x, y);
        this.ctx.rotate(this.particles.find(p => p.x === x && p.y === y)?.rotation || 0);
        
        this.ctx.beginPath();
        for (let i = 0; i < 6; i++) {
            const angle = (Math.PI / 3) * i;
            const px = size * Math.cos(angle);
            const py = size * Math.sin(angle);
            
            if (i === 0) {
                this.ctx.moveTo(px, py);
            } else {
                this.ctx.lineTo(px, py);
            }
        }
        this.ctx.closePath();
        
        this.ctx.strokeStyle = `rgba(50, 60, 80, ${alpha})`;
        this.ctx.lineWidth = 1;
        this.ctx.stroke();
        
        this.ctx.fillStyle = `rgba(70, 80, 100, ${alpha * 0.5})`;
        this.ctx.fill();
        
        this.ctx.restore();
    }
    
    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Update and draw particles
        for (let particle of this.particles) {
            particle.y -= particle.speed;
            particle.rotation += 0.01;
            
            if (particle.y < -particle.size * 2) {
                particle.y = this.canvas.height + particle.size * 2;
                particle.x = Math.random() * this.canvas.width;
            }
            
            this.drawHex(particle.x, particle.y, particle.size, particle.alpha);
        }
        
        requestAnimationFrame(() => this.animate());
    }
    
    generateRandomSeed() {
        return Math.floor(Math.random() * 1000000) + 1;
    }
    
    async initAuth() {
        // Check if user is already authenticated
        try {
            const response = await fetch('/api/auth/me', {
                method: 'GET',
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.currentUser = data.user;
                this.showMainMenu();
            } else {
                // User not authenticated, show login modal
                this.showAuthModal();
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            this.showAuthModal();
        }
    }
    
    switchTab(tabName) {
        this.currentTab = tabName;
        
        // Update tab appearance
        document.querySelectorAll('.auth-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });
        
        // Switch forms
        document.querySelectorAll('.auth-form').forEach(form => {
            form.classList.toggle('active', form.id === `${tabName}-form`);
        });
        
        this.clearMessage();
    }
    
    async handleLogin() {
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value;
        
        if (!username || !password) {
            this.showMessage('Please fill in all fields', 'error');
            return;
        }
        
        try {
            this.showMessage('Logging in...', 'info');
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.currentUser = data.user;
                this.showMessage('Login successful!', 'success');
                setTimeout(() => this.showMainMenu(), 1000);
            } else {
                this.showMessage(data.error || 'Login failed', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showMessage('Network error. Please try again.', 'error');
        }
    }
    
    async handleRegister() {
        const username = document.getElementById('reg-username').value.trim();
        const email = document.getElementById('reg-email').value.trim();
        const password = document.getElementById('reg-password').value;
        const confirmPassword = document.getElementById('reg-confirm-password').value;
        const role = document.querySelector('.role-btn.active').dataset.role;
        const color = document.querySelector('.color-btn.active').dataset.color;
        
        // Client-side validation
        if (!username || !email || !password || !confirmPassword) {
            this.showMessage('Please fill in all fields', 'error');
            return;
        }
        
        if (password !== confirmPassword) {
            this.showMessage('Passwords do not match', 'error');
            return;
        }
        
        if (password.length < 8) {
            this.showMessage('Password must be at least 8 characters', 'error');
            return;
        }
        
        try {
            this.showMessage('Creating account...', 'info');
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({ username, email, password, role, color })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.currentUser = data.user;
                this.showMessage('Registration successful!', 'success');
                setTimeout(() => this.showMainMenu(), 1000);
            } else {
                if (data.details && Array.isArray(data.details)) {
                    this.showMessage(data.details.join('. '), 'error');
                } else {
                    this.showMessage(data.error || 'Registration failed', 'error');
                }
            }
        } catch (error) {
            console.error('Registration error:', error);
            this.showMessage('Network error. Please try again.', 'error');
        }
    }
    
    showAuthModal() {
        document.getElementById('auth-modal').classList.add('active');
        document.getElementById('main-menu').classList.add('hidden');
    }
    
    showMainMenu() {
        document.getElementById('auth-modal').classList.remove('active');
        document.getElementById('main-menu').classList.remove('hidden');
        
        // Update menu based on role
        if (this.currentUser && this.currentUser.role === 'game_master') {
            document.getElementById('map-generator').style.display = 'block';
        } else {
            // Hide master-only features for players
            document.getElementById('map-generator').style.display = 'none';
        }
    }
    
    showMessage(message, type = 'info') {
        // Check if we're in auth modal and use auth message div
        const authMessageDiv = document.getElementById('auth-message');
        if (authMessageDiv && !document.getElementById('auth-modal').classList.contains('hidden')) {
            authMessageDiv.textContent = message;
            authMessageDiv.className = `auth-message ${type}`;
            authMessageDiv.classList.remove('hidden');
            return;
        }
        
        // Otherwise create temporary message display
        const messageEl = document.createElement('div');
        messageEl.className = `temp-message ${type}`;
        messageEl.textContent = message;
        messageEl.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: ${type === 'error' ? '#e74c3c' : '#3498db'};
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.3s;
        `;
        document.body.appendChild(messageEl);
        
        // Show message
        setTimeout(() => messageEl.style.opacity = '1', 100);
        
        // Remove message after 3 seconds
        setTimeout(() => {
            messageEl.style.opacity = '0';
            setTimeout(() => document.body.removeChild(messageEl), 300);
        }, 3000);
    }
    
    clearMessage() {
        const messageDiv = document.getElementById('auth-message');
        if (messageDiv) {
            messageDiv.classList.add('hidden');
        }
    }
    
    async logout() {
        try {
            await fetch('/api/auth/logout', {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.currentUser = null;
            this.showAuthModal();
        }
    }
    
    newAdventure() {
        // Show session selection modal
        this.showSessionModal();
    }
    
    openMapGenerator() {
        window.location.href = '/generator';
    }
    
    // Session modal methods
    showSessionModal() {
        // Load existing sessions
        this.loadSessions();
        
        // Set random seed
        const newSeed = this.generateRandomSeed();
        document.getElementById('new-seed-input').value = newSeed;
        
        // Show modal
        document.getElementById('session-modal').classList.add('active');
    }
    
    closeSessionModal() {
        document.getElementById('session-modal').classList.remove('active');
    }
    
    loadSessions() {
        fetch('/api/list_sessions')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.sessions = data.sessions;
                this.renderSessions();
            }
        });
    }
    
    renderSessions() {
        const sessionList = document.getElementById('session-list');
        sessionList.innerHTML = '';
        
        if (this.sessions.length === 0) {
            sessionList.innerHTML = '<p style="color: #b4b4b4; text-align: center;">No existing sessions found</p>';
        } else {
            this.sessions.forEach(session => {
                const sessionItem = document.createElement('div');
                sessionItem.className = 'session-item';
                
                // Determine session type display
                const sessionType = session.session_type || 'unknown';
                const sessionName = session.session_name || session.name || 'Unnamed Session';
                const typeColor = sessionType === 'master' ? '#ffd700' : '#87CEEB';
                const typeIcon = sessionType === 'master' ? '👑' : '🎮';
                
                sessionItem.innerHTML = `
                    <div class="session-header">
                        <h4>${sessionName}</h4>
                        <span class="session-type-badge" style="color: ${typeColor}">${typeIcon} ${sessionType.toUpperCase()}</span>
                    </div>
                    <div class="session-details">
                        <p>Seed: ${session.seed}</p>
                        <p>Created: ${new Date(session.created_at).toLocaleDateString()}</p>
                        <p>Hexes: ${session.hex_count}</p>
                    </div>
                `;
                sessionItem.addEventListener('click', () => this.joinSession(session.id));
                sessionList.appendChild(sessionItem);
            });
        }
    }
    
    joinSession(sessionId) {
        this.showLoading(true);
        // Load session and redirect to game
        fetch(`/api/load_map_session/${sessionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Create a new game with this session's seed
                fetch('/api/new_game', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        seed: data.session.seed,
                        player_name: this.currentUser?.username || 'Player',
                        player_color: this.currentUser?.color || '#3498db'
                    })
                })
                .then(response => response.json())
                .then(gameData => {
                    this.showLoading(false);
                    if (gameData.success) {
                        window.location.href = '/game';
                    }
                });
            } else {
                this.showLoading(false);
            }
        });
    }
    
    createNewSession() {
        const seed = parseInt(document.getElementById('new-seed-input').value) || this.generateRandomSeed();
        
        this.showLoading(true);
        // Create new game with seed
        fetch('/api/new_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                seed: seed,
                player_name: this.currentUser?.username || 'Player',
                player_color: this.currentUser?.color || '#3498db'
            })
        })
        .then(response => response.json())
        .then(data => {
            this.showLoading(false);
            if (data.success) {
                window.location.href = '/game';
            } else {
                alert('Failed to start new adventure: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            this.showLoading(false);
            console.error('Error starting new adventure:', error);
            alert('Failed to start new adventure: ' + error.message);
        });
    }
    
    handleFileLoad(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const mapData = JSON.parse(e.target.result);
                this.loadGameWithMap(mapData);
            } catch (error) {
                alert('Invalid map file: ' + error.message);
            }
        };
        reader.readAsText(file);
    }
    
    loadGameWithMap(mapData) {
        this.showLoading(true);
        
        fetch('/api/load_game', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ map_data: mapData })
        })
        .then(response => response.json())
        .then(data => {
            this.showLoading(false);
            if (data.success) {
                window.location.href = '/game';
            } else {
                alert('Failed to load map: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            this.showLoading(false);
            alert('Network error: ' + error.message);
        });
    }
    
    openSettings() {
        const modal = document.getElementById('settings-modal');
        modal.classList.add('active');
        
        // Load current settings
        document.getElementById('ai-model').value = this.settings.ai_model || 'qwen2.5:3b';
        document.getElementById('vision-model').value = this.settings.vision_model || 'llava:7b';
        document.getElementById('ollama-url').value = this.settings.ollama_url || 'http://localhost:11434';
        document.getElementById('scale-display').textContent = `${this.settings.ui_scale || 1.0}x`;
        
        this.checkConnection();
    }
    
    closeSettings() {
        const modal = document.getElementById('settings-modal');
        modal.classList.remove('active');
    }
    
    saveSettings() {
        this.settings.ai_model = document.getElementById('ai-model').value;
        this.settings.vision_model = document.getElementById('vision-model').value;
        this.settings.ollama_url = document.getElementById('ollama-url').value;
        
        localStorage.setItem('hex_explorer_settings', JSON.stringify(this.settings));
        this.closeSettings();
    }
    
    refreshModels() {
        this.checkConnection();
    }
    
    checkConnection() {
        const url = document.getElementById('ollama-url').value;
        const status = document.getElementById('connection-status');
        
        fetch(url + '/api/tags', { method: 'GET', timeout: 2000 })
        .then(response => response.json())
        .then(data => {
            const models = data.models || [];
            status.textContent = `Ollama: Connected (${models.length} models)`;
            status.className = 'connection-status connected';
            
            // Update model dropdowns
            this.updateModelDropdowns(models);
        })
        .catch(error => {
            status.textContent = 'Ollama: Not connected';
            status.className = 'connection-status';
        });
    }
    
    updateModelDropdowns(models) {
        const aiSelect = document.getElementById('ai-model');
        const visionSelect = document.getElementById('vision-model');
        
        const aiModels = models.filter(m => !this.isVisionModel(m.name));
        const visionModels = models.filter(m => this.isVisionModel(m.name));
        
        this.populateSelect(aiSelect, aiModels.map(m => m.name));
        this.populateSelect(visionSelect, visionModels.map(m => m.name));
    }
    
    isVisionModel(name) {
        const visionHints = ['llava', 'bakllava', 'vision', 'moondream', 'qwen2-vl', 'phi-3-vision'];
        return visionHints.some(hint => name.toLowerCase().includes(hint));
    }
    
    populateSelect(select, options) {
        const currentValue = select.value;
        select.innerHTML = '';
        
        options.forEach(option => {
            const optElement = document.createElement('option');
            optElement.value = option;
            optElement.textContent = option;
            select.appendChild(optElement);
        });
        
        if (options.includes(currentValue)) {
            select.value = currentValue;
        }
    }
    
    changeScale(delta) {
        const current = this.settings.ui_scale || 1.0;
        const newScale = Math.max(0.6, Math.min(1.6, current + delta));
        this.settings.ui_scale = Math.round(newScale * 10) / 10;
        
        document.getElementById('scale-display').textContent = `${this.settings.ui_scale}x`;
        
        // Apply scale to body
        document.body.style.fontSize = `${this.settings.ui_scale}em`;
    }
    
    loadSettings() {
        const stored = localStorage.getItem('hex_explorer_settings');
        if (stored) {
            try {
                return JSON.parse(stored);
            } catch (e) {
                return this.getDefaultSettings();
            }
        }
        return this.getDefaultSettings();
    }
    
    getDefaultSettings() {
        return {
            ai_model: 'qwen2.5:3b',
            vision_model: 'llava:7b',
            ollama_url: 'http://localhost:11434',
            ui_scale: 1.0
        };
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
    new MainMenu();
});