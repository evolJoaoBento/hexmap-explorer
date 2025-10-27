/**
 * Authentication Helper for Dice Chat
 * Provides login/register functionality for demo pages
 */

class AuthHelper {
    constructor(apiBaseUrl = 'http://localhost:5000') {
        this.apiBaseUrl = apiBaseUrl;
        this.token = localStorage.getItem('dice_chat_token');
    }

    async login(username, password) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.token = data.token;
                localStorage.setItem('dice_chat_token', this.token);
                localStorage.setItem('dice_chat_username', username);
                return { success: true, token: this.token };
            } else {
                const error = await response.json();
                return { success: false, error: error.error || 'Login failed' };
            }
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async register(username, password) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            if (response.ok) {
                const data = await response.json();
                // Auto-login after registration
                return await this.login(username, password);
            } else {
                const error = await response.json();
                return { success: false, error: error.error || 'Registration failed' };
            }
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async checkAuth() {
        if (!this.token) {
            return { authenticated: false };
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/api/auth/session-debug`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                return { authenticated: true, user: data };
            } else {
                // Token invalid or expired
                this.logout();
                return { authenticated: false };
            }
        } catch (error) {
            return { authenticated: false, error: error.message };
        }
    }

    logout() {
        this.token = null;
        localStorage.removeItem('dice_chat_token');
        localStorage.removeItem('dice_chat_username');
    }

    getToken() {
        return this.token;
    }

    getStoredUsername() {
        return localStorage.getItem('dice_chat_username');
    }

    createLoginModal() {
        const modal = document.createElement('div');
        modal.innerHTML = `
            <div id="authModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000;">
                <div style="position: relative; background: white; margin: 100px auto; padding: 30px; width: 400px; border-radius: 10px;">
                    <h2 style="margin-top: 0;">🔐 Authentication Required</h2>
                    <p>Please login or register to use the dice chat system.</p>

                    <div id="authForm">
                        <input type="text" id="authUsername" placeholder="Username" style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px;">
                        <input type="password" id="authPassword" placeholder="Password" style="width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px;">

                        <div style="margin: 20px 0;">
                            <button id="loginBtn" style="padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; margin-right: 10px;">Login</button>
                            <button id="registerBtn" style="padding: 10px 20px; background: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer;">Register</button>
                            <button id="cancelAuthBtn" style="padding: 10px 20px; background: #f44336; color: white; border: none; border-radius: 5px; cursor: pointer; float: right;">Cancel</button>
                        </div>
                    </div>

                    <div id="authStatus" style="margin-top: 10px; padding: 10px; display: none;"></div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Bind events
        const authModal = document.getElementById('authModal');
        const authStatus = document.getElementById('authStatus');

        document.getElementById('loginBtn').addEventListener('click', async () => {
            const username = document.getElementById('authUsername').value;
            const password = document.getElementById('authPassword').value;

            if (!username || !password) {
                this.showStatus('Please enter username and password', 'error');
                return;
            }

            this.showStatus('Logging in...', 'info');
            const result = await this.login(username, password);

            if (result.success) {
                this.showStatus('Login successful!', 'success');
                setTimeout(() => {
                    authModal.style.display = 'none';
                    if (window.onAuthSuccess) {
                        window.onAuthSuccess(result.token);
                    }
                }, 1000);
            } else {
                this.showStatus(`Login failed: ${result.error}`, 'error');
            }
        });

        document.getElementById('registerBtn').addEventListener('click', async () => {
            const username = document.getElementById('authUsername').value;
            const password = document.getElementById('authPassword').value;

            if (!username || !password) {
                this.showStatus('Please enter username and password', 'error');
                return;
            }

            if (password.length < 6) {
                this.showStatus('Password must be at least 6 characters', 'error');
                return;
            }

            this.showStatus('Creating account...', 'info');
            const result = await this.register(username, password);

            if (result.success) {
                this.showStatus('Registration successful! Logged in.', 'success');
                setTimeout(() => {
                    authModal.style.display = 'none';
                    if (window.onAuthSuccess) {
                        window.onAuthSuccess(result.token);
                    }
                }, 1000);
            } else {
                this.showStatus(`Registration failed: ${result.error}`, 'error');
            }
        });

        document.getElementById('cancelAuthBtn').addEventListener('click', () => {
            authModal.style.display = 'none';
        });

        // Enter key handling
        document.getElementById('authPassword').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                document.getElementById('loginBtn').click();
            }
        });

        return authModal;
    }

    showStatus(message, type) {
        const authStatus = document.getElementById('authStatus');
        authStatus.style.display = 'block';
        authStatus.innerHTML = message;
        authStatus.style.background = type === 'error' ? '#ffebee' :
                                      type === 'success' ? '#e8f5e9' : '#e3f2fd';
        authStatus.style.color = type === 'error' ? '#c62828' :
                                 type === 'success' ? '#2e7d32' : '#1565c0';
    }

    showLoginModal() {
        let modal = document.getElementById('authModal');
        if (!modal) {
            modal = this.createLoginModal();
        }
        modal.style.display = 'block';
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthHelper;
}

window.AuthHelper = AuthHelper;