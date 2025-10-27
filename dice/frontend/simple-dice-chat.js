/**
 * Simple Dice Chat Interface
 * Simplified version with dice buttons instead of complex expressions
 */

class SimpleDiceChatInterface {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.getElementById(container) : container;
        this.options = {
            apiBaseUrl: options.apiBaseUrl || 'http://localhost:5000',
            socketUrl: options.socketUrl || 'http://localhost:5000',
            theme: options.theme || 'default',
            userRole: options.userRole || 'player',  // 'dm' or 'player'
            authToken: options.authToken || null,  // JWT token for authentication
            ...options
        };

        this.socket = null;
        this.currentRoom = options.roomId || this.generateRoomId();  // Configurable room ID
        this.currentUser = null;
        this.isConnected = false;
        this.pendingRequests = new Map();
        this.selectedDice = {};  // Track selected dice
        this.lastMessageCount = 0;  // Track message count to prevent flashing
        this.modalOpen = false;  // Track modal state to prevent conflicts
        this.lastMessagesHash = '';  // Track content changes, not just count
        this.activePlayers = new Map();  // Track players in the room

        this.init();
    }

    init() {
        this.createInterface();
        this.bindEvents();
    }

    createInterface() {
        const isDM = this.options.userRole === 'dm';

        this.container.innerHTML = `
            <div class="simple-dice-chat ${this.options.theme}">
                <!-- Header -->
                <div class="chat-header">
                    <h3>${isDM ? '🎭 Dungeon Master' : '⚔️ Player'}</h3>
                    <div class="header-info">
                        <div class="room-info" title="Room ID: ${this.currentRoom}">📍 ${this.currentRoom.substring(0, 8)}...</div>
                        <div class="status" id="connectionStatus">Disconnected</div>
                    </div>
                </div>

                <!-- Messages Area -->
                <div class="messages-container" id="messagesContainer">
                    <div id="messagesList" class="messages-list"></div>
                </div>

                <!-- Pending Dice Requests -->
                <div class="pending-requests" id="pendingRequests" style="display: none;">
                    <div class="requests-header">Pending Dice Requests</div>
                    <div id="requestsList"></div>
                </div>

                <!-- Input Area -->
                <div class="input-area">
                    ${isDM ? this.createDMInterface() : this.createPlayerInterface()}
                </div>

                <!-- Dice Selection Modal -->
                <div class="modal" id="diceSelectionModal" style="display: none;">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h3 id="modalTitle">Select Dice to Roll</h3>
                            <button class="close-btn" id="closeModal">&times;</button>
                        </div>
                        <div class="modal-body">
                            <div class="dice-request-info" id="requestInfo" style="display: none;"></div>

                            <!-- Player Selection (DM only) -->
                            <div class="player-selection" id="playerSelection" style="display: none;">
                                <h4>Select Player:</h4>
                                <select id="targetPlayerSelect" style="width: 100%; padding: 8px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 4px;">
                                    <option value="all">All Players</option>
                                </select>
                            </div>

                            <div class="dice-selection">
                                <h4>Select Dice:</h4>
                                <div class="dice-grid">
                                    <div class="dice-type" data-die="d4">
                                        <div class="die-button">d4</div>
                                        <div class="die-count">
                                            <button class="count-btn" data-action="decrease">−</button>
                                            <span class="count" data-die="d4">0</span>
                                            <button class="count-btn" data-action="increase">+</button>
                                        </div>
                                    </div>
                                    <div class="dice-type" data-die="d6">
                                        <div class="die-button">d6</div>
                                        <div class="die-count">
                                            <button class="count-btn" data-action="decrease">−</button>
                                            <span class="count" data-die="d6">0</span>
                                            <button class="count-btn" data-action="increase">+</button>
                                        </div>
                                    </div>
                                    <div class="dice-type" data-die="d8">
                                        <div class="die-button">d8</div>
                                        <div class="die-count">
                                            <button class="count-btn" data-action="decrease">−</button>
                                            <span class="count" data-die="d8">0</span>
                                            <button class="count-btn" data-action="increase">+</button>
                                        </div>
                                    </div>
                                    <div class="dice-type" data-die="d10">
                                        <div class="die-button">d10</div>
                                        <div class="die-count">
                                            <button class="count-btn" data-action="decrease">−</button>
                                            <span class="count" data-die="d10">0</span>
                                            <button class="count-btn" data-action="increase">+</button>
                                        </div>
                                    </div>
                                    <div class="dice-type" data-die="d12">
                                        <div class="die-button">d12</div>
                                        <div class="die-count">
                                            <button class="count-btn" data-action="decrease">−</button>
                                            <span class="count" data-die="d12">0</span>
                                            <button class="count-btn" data-action="increase">+</button>
                                        </div>
                                    </div>
                                    <div class="dice-type" data-die="d20">
                                        <div class="die-button">d20</div>
                                        <div class="die-count">
                                            <button class="count-btn" data-action="decrease">−</button>
                                            <span class="count" data-die="d20">0</span>
                                            <button class="count-btn" data-action="increase">+</button>
                                        </div>
                                    </div>
                                </div>

                                <div class="modifier-section">
                                    <label>Modifier:</label>
                                    <input type="number" id="diceModifier" value="0" min="-99" max="99">
                                </div>

                                <div class="expression-preview">
                                    Expression: <span id="expressionPreview">Select dice</span>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button class="btn btn-secondary" id="cancelDice">Cancel</button>
                            <button class="btn btn-primary" id="confirmDice">🎲 Roll!</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    createDMInterface() {
        return `
            <div class="dm-controls">
                <div class="message-input-row">
                    <input type="text" id="messageInput" placeholder="Type a message..." maxlength="500">
                    <button class="btn btn-send" id="sendMessageBtn">Send</button>
                </div>
                <div class="dm-actions">
                    <button class="btn btn-dice" id="requestDiceBtn">🎲 Request Dice Roll</button>
                </div>
            </div>
        `;
    }

    createPlayerInterface() {
        return `
            <div class="player-controls">
                <div class="message-input-row">
                    <input type="text" id="messageInput" placeholder="Type a message..." maxlength="500">
                    <button class="btn btn-send" id="sendMessageBtn">Send</button>
                </div>
                <div class="player-actions">
                    <button class="btn btn-dice" id="rollDiceBtn">🎲 Roll Dice</button>
                </div>
            </div>
        `;
    }

    bindEvents() {
        // Message input
        const messageInput = this.container.querySelector('#messageInput');
        const sendBtn = this.container.querySelector('#sendMessageBtn');

        if (messageInput && sendBtn) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });
            sendBtn.addEventListener('click', () => this.sendMessage());
        }

        // Role-specific buttons
        const requestDiceBtn = this.container.querySelector('#requestDiceBtn');
        const rollDiceBtn = this.container.querySelector('#rollDiceBtn');

        if (requestDiceBtn) {
            requestDiceBtn.addEventListener('click', () => this.openDiceRequestModal());
        }

        if (rollDiceBtn) {
            rollDiceBtn.addEventListener('click', () => this.openDiceRollModal());
        }

        // Modal events
        this.bindModalEvents();

        // Dice counter events
        this.bindDiceCounterEvents();
    }

    bindModalEvents() {
        const modal = this.container.querySelector('#diceSelectionModal');
        const closeModal = this.container.querySelector('#closeModal');
        const cancelDice = this.container.querySelector('#cancelDice');
        const confirmDice = this.container.querySelector('#confirmDice');

        if (closeModal) closeModal.addEventListener('click', () => this.closeDiceModal());
        if (cancelDice) cancelDice.addEventListener('click', () => this.closeDiceModal());
        if (confirmDice) confirmDice.addEventListener('click', () => this.confirmDiceAction());

        // Close modal when clicking outside
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeDiceModal();
                }
            });
        }
    }

    bindDiceCounterEvents() {
        const countBtns = this.container.querySelectorAll('.count-btn');
        const modifierInput = this.container.querySelector('#diceModifier');

        countBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                const dieType = e.target.closest('.dice-type').dataset.die;
                this.updateDiceCount(dieType, action);
            });
        });

        if (modifierInput) {
            modifierInput.addEventListener('input', () => this.updateExpressionPreview());
        }
    }

    updateDiceCount(dieType, action) {
        const countSpan = this.container.querySelector(`span[data-die="${dieType}"]`);
        let current = parseInt(countSpan.textContent) || 0;

        if (action === 'increase') {
            current = Math.min(current + 1, 10); // Max 10 of each die
        } else if (action === 'decrease') {
            current = Math.max(current - 1, 0);
        }

        countSpan.textContent = current;
        this.selectedDice[dieType] = current;
        this.updateExpressionPreview();
    }

    updateExpressionPreview() {
        const preview = this.container.querySelector('#expressionPreview');
        const modifier = parseInt(this.container.querySelector('#diceModifier')?.value || 0);

        const diceParts = [];
        for (const [die, count] of Object.entries(this.selectedDice)) {
            if (count > 0) {
                diceParts.push(count === 1 ? die : `${count}${die}`);
            }
        }

        let expression = diceParts.join('+');
        if (modifier !== 0) {
            expression += modifier > 0 ? `+${modifier}` : `${modifier}`;
        }

        preview.textContent = expression || 'Select dice';
        return expression;
    }

    generateRoomId() {
        // Generate a random room ID if not provided
        return 'room-' + Math.random().toString(36).substr(2, 9);
    }

    setRoom(roomId) {
        this.currentRoom = roomId;
        // Update the room display
        const roomInfo = this.container.querySelector('.room-info');
        if (roomInfo) {
            roomInfo.textContent = `📍 ${roomId.substring(0, 8)}...`;
            roomInfo.title = `Room ID: ${roomId}`;
        }
    }

    getRoom() {
        return this.currentRoom;
    }

    // Connection methods
    connect(username, userRole = 'player', roomId = null) {
        this.currentUser = { username, userRole };
        this.options.userRole = userRole;

        // Set custom room if provided
        if (roomId) {
            this.setRoom(roomId);
        }

        // Simulate connection for demo
        setTimeout(() => {
            this.isConnected = true;
            this.updateConnectionStatus('Connected');
            this.joinRoom();
            this.loadMessages();
        }, 500);
    }

    updateConnectionStatus(status) {
        const statusEl = this.container.querySelector('#connectionStatus');
        if (statusEl) {
            statusEl.textContent = status;
            statusEl.className = `status ${this.isConnected ? 'connected' : 'disconnected'}`;
        }
    }

    async joinRoom() {
        try {
            const headers = {
                'Content-Type': 'application/json'
            };

            // Add auth token if available
            if (this.options.authToken) {
                headers['Authorization'] = `Bearer ${this.options.authToken}`;
            }

            const response = await fetch(`${this.options.apiBaseUrl}/api/chat/rooms/${this.currentRoom}/join`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    username: this.currentUser.username,
                    user_role: this.currentUser.userRole
                })
            });

            if (response.ok) {
                console.log('Joined room successfully');
            } else if (response.status === 401) {
                this.handleAuthError();
            }
        } catch (error) {
            console.error('Error joining room:', error);
        }
    }

    hashMessages(messages) {
        // Create a simple hash of message content to detect real changes
        if (!messages || messages.length === 0) return '';

        return messages.map(msg => `${msg.id || msg.timestamp}-${msg.content}`).join('|');
    }

    async loadMessages() {
        try {
            const headers = {};
            if (this.options.authToken) {
                headers['Authorization'] = `Bearer ${this.options.authToken}`;
            }

            const response = await fetch(`${this.options.apiBaseUrl}/api/chat/rooms/${this.currentRoom}/messages?limit=50`, {
                headers: headers
            });
            if (response.ok) {
                const data = await response.json();
                // Only update display if messages actually changed (compare content)
                const messagesHash = this.hashMessages(data.messages);
                if (messagesHash !== this.lastMessagesHash) {
                    this.lastMessagesHash = messagesHash;
                    this.lastMessageCount = data.messages.length;
                    this.displayMessages(data.messages);
                }
            }
        } catch (error) {
            console.error('Error loading messages:', error);
        }

        // Poll for new messages every 3 seconds (reduced frequency)
        setTimeout(() => {
            if (this.isConnected) {
                this.loadMessages();
            }
        }, 3000);
    }

    async sendMessage() {
        const input = this.container.querySelector('#messageInput');
        const content = input.value.trim();

        if (!content) return;

        try {
            const headers = {
                'Content-Type': 'application/json'
            };

            if (this.options.authToken) {
                headers['Authorization'] = `Bearer ${this.options.authToken}`;
            }

            const response = await fetch(`${this.options.apiBaseUrl}/api/chat/rooms/${this.currentRoom}/messages`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    content: content,
                    username: this.currentUser.username,
                    user_role: this.currentUser.userRole
                })
            });

            if (response.ok) {
                input.value = '';
                // Force immediate refresh for sent messages
                setTimeout(() => {
                    this.lastMessagesHash = ''; // Reset to force update
                    this.loadMessages();
                }, 100);
            }
        } catch (error) {
            console.error('Error sending message:', error);
        }
    }

    displayMessages(messages) {
        const messagesList = this.container.querySelector('#messagesList');
        if (!messagesList) return;

        // Track active players for DM targeting
        this.updateActivePlayersList(messages);

        messagesList.innerHTML = '';

        messages.forEach(message => {
            const messageEl = this.createMessageElement(message);
            messagesList.appendChild(messageEl);
        });

        // Scroll to bottom
        const container = this.container.querySelector('#messagesContainer');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }

    createMessageElement(message) {
        const div = document.createElement('div');
        div.className = 'message chat';

        if (message.username === this.currentUser.username) {
            div.classList.add('own-message');
        }

        const timestamp = new Date(message.timestamp || message.created_at).toLocaleTimeString();

        // Check if this is a dice request or dice result based on content
        const isDiceRequest = message.content.includes('**DM requests') && message.content.includes('roll');
        const isDiceResult = message.content.includes('🎯 **') && message.content.includes('rolled');

        if (isDiceRequest && message.user_role === 'dm') {
            div.classList.add('dice-request');

            // Check if this request is targeted to a specific player
            const isTargetedRequest = message.content.includes('requests ') && message.content.includes(' to roll');
            const targetPlayer = this.extractTargetPlayer(message.content);
            const isTargetedToMe = targetPlayer === this.currentUser.username;
            const isForAllPlayers = !isTargetedRequest || targetPlayer === 'all';

            // Make clickable for players only (either targeted to them or for all players)
            const isClickable = this.currentUser.userRole === 'player' && (isTargetedToMe || isForAllPlayers);
            const clickableClass = isClickable ? 'clickable-request' : '';
            const clickHandler = isClickable ? `onclick="window.currentChat.respondToDiceRequest('${message.id}', '${this.extractExpressionFromContent(message.content)}')"` : '';

            // Add visual styling for targeted messages
            const targetedClass = isTargetedRequest && !isForAllPlayers ? 'targeted-request' : '';

            div.innerHTML = `
                <div class="message-header">
                    <span class="sender">${message.username}</span>
                    <span class="timestamp">${timestamp}</span>
                    <span class="badge request">${isTargetedRequest && !isForAllPlayers ? 'Targeted Request' : 'Dice Request'}</span>
                </div>
                <div class="message-content dice-request ${clickableClass} ${targetedClass}" ${clickHandler}>
                    ${this.formatDiceRequestContent(message.content)}
                    ${isClickable ? '<div class="click-hint">👆 Click to roll these dice</div>' : ''}
                    ${isTargetedRequest && !isTargetedToMe && !isForAllPlayers ? '<div class="not-for-you">This request is for another player</div>' : ''}
                </div>
            `;
        } else if (isDiceResult) {
            div.classList.add('dice-result');
            div.innerHTML = `
                <div class="message-header">
                    <span class="sender">${message.username}</span>
                    <span class="timestamp">${timestamp}</span>
                    <span class="badge result">Dice Result</span>
                </div>
                <div class="message-content dice-response">
                    ${this.formatDiceRequestContent(message.content)}
                </div>
            `;
        } else {
            // Regular chat message
            div.innerHTML = `
                <div class="message-header">
                    <span class="sender">${message.username}</span>
                    <span class="timestamp">${timestamp}</span>
                </div>
                <div class="message-content">
                    ${this.formatDiceRequestContent(message.content)}
                </div>
            `;
        }

        return div;
    }

    formatDiceRequestContent(content) {
        return content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                     .replace(/`([^`]+)`/g, '<code>$1</code>')
                     .replace(/\n/g, '<br>')
                     .replace(/\*(.*?)\*/g, '<em>$1</em>');  // Handle italic text
    }

    createRespondButton(message) {
        if (this.currentUser.userRole === 'player' && message.target_user_id === this.currentUser.id) {
            return `<br><button class="btn btn-sm btn-primary respond-btn" onclick="window.currentChat.respondToRequest('${message.dice_request_id}')">🎲 Respond</button>`;
        }
        return '';
    }

    // Modal methods
    openDiceRequestModal() {
        if (this.modalOpen) return; // Prevent multiple modals

        this.resetDiceSelection();
        this.container.querySelector('#modalTitle').textContent = 'Request Dice Roll from Player';
        this.container.querySelector('#requestInfo').style.display = 'none';

        // Show player selection for DMs
        const playerSelection = this.container.querySelector('#playerSelection');
        if (this.options.userRole === 'dm') {
            this.updatePlayerDropdown();
            playerSelection.style.display = 'block';
        } else {
            playerSelection.style.display = 'none';
        }

        this.container.querySelector('#diceSelectionModal').style.display = 'block';
        this.modalMode = 'request';
        this.modalOpen = true;
    }

    openDiceRollModal() {
        if (this.modalOpen) return; // Prevent multiple modals

        this.resetDiceSelection();
        this.container.querySelector('#modalTitle').textContent = 'Roll Dice';
        this.container.querySelector('#requestInfo').style.display = 'none';
        this.container.querySelector('#diceSelectionModal').style.display = 'block';
        this.modalMode = 'roll';
        this.modalOpen = true;
    }

    extractExpressionFromContent(content) {
        // Extract dice expression from the message content
        let match = content.match(/\*\*DM requests dice roll\*\*:\s*([^\n]+)/);
        if (!match) {
            // Try targeted request format
            match = content.match(/\*\*DM requests .+ to roll\*\*:\s*([^\n]+)/);
        }
        return match ? match[1].trim() : '';
    }

    extractTargetPlayer(content) {
        // Extract target player from targeted request content
        const match = content.match(/\*\*DM requests (.+) to roll\*\*/);
        return match ? match[1].trim() : 'all';
    }

    updateActivePlayersList(messages) {
        // Track active players based on recent messages
        this.activePlayers.clear();

        // Look at recent messages to find active users
        messages.slice(-20).forEach(message => {
            if (message.username && message.user_role === 'player' && message.username !== 'System') {
                this.activePlayers.set(message.username, {
                    username: message.username,
                    lastSeen: message.timestamp || message.created_at
                });
            }
        });
    }

    updatePlayerDropdown() {
        const select = this.container.querySelector('#targetPlayerSelect');
        if (!select) return;

        // Clear existing options except "All Players"
        select.innerHTML = '<option value="all">All Players</option>';

        // Add active players to dropdown
        this.activePlayers.forEach((playerInfo, username) => {
            const option = document.createElement('option');
            option.value = username;
            option.textContent = username;
            select.appendChild(option);
        });
    }

    respondToDiceRequest(messageId, expression) {
        if (this.modalOpen) return; // Prevent multiple modals

        // Parse the dice expression and pre-populate the modal
        this.resetDiceSelection();
        this.parseDiceExpression(expression);

        this.container.querySelector('#modalTitle').textContent = 'Roll Requested Dice';
        this.container.querySelector('#requestInfo').innerHTML = `
            <div class="request-details">
                <p><strong>DM requested:</strong> ${expression}</p>
                <p>Dice have been pre-selected. Click "🎲 Roll!" to roll them.</p>
            </div>
        `;
        this.container.querySelector('#requestInfo').style.display = 'block';
        this.container.querySelector('#diceSelectionModal').style.display = 'block';
        this.modalMode = 'respond';
        this.currentRequestId = messageId;
        this.modalOpen = true;
    }

    parseDiceExpression(expression) {
        // Parse an expression like "2d6+1d20+3" and set the dice counts and modifier
        this.selectedDice = {};
        let modifier = 0;

        // Split by + and - while keeping the operators
        const parts = expression.split(/([+-])/);
        let currentSign = 1;

        for (let i = 0; i < parts.length; i++) {
            const part = parts[i].trim();

            if (part === '+') {
                currentSign = 1;
            } else if (part === '-') {
                currentSign = -1;
            } else if (part) {
                if (part.includes('d')) {
                    // This is a dice part like "2d6" or "d20"
                    const match = part.match(/(\d*)d(\d+)/);
                    if (match) {
                        const count = parseInt(match[1]) || 1;
                        const sides = match[2];
                        const dieType = `d${sides}`;

                        // Only add dice types we support
                        if (['d4', 'd6', 'd8', 'd10', 'd12', 'd20'].includes(dieType)) {
                            this.selectedDice[dieType] = (this.selectedDice[dieType] || 0) + (count * currentSign);
                        }
                    }
                } else if (!isNaN(part)) {
                    // This is a number modifier
                    modifier += parseInt(part) * currentSign;
                }
            }
        }

        // Update the UI
        this.updateDiceCountsInUI();

        // Set modifier
        const modifierInput = this.container.querySelector('#diceModifier');
        if (modifierInput) {
            modifierInput.value = modifier;
        }

        this.updateExpressionPreview();
    }

    updateDiceCountsInUI() {
        // Update the dice count displays
        ['d4', 'd6', 'd8', 'd10', 'd12', 'd20'].forEach(dieType => {
            const count = this.selectedDice[dieType] || 0;
            const countSpan = this.container.querySelector(`span[data-die="${dieType}"]`);
            if (countSpan) {
                countSpan.textContent = Math.max(0, count); // Don't show negative counts
            }
        });
    }

    respondToRequest(requestId) {
        // Legacy method - keeping for compatibility
        this.respondToDiceRequest(requestId, '1d20');
    }

    handleAuthError() {
        // Handle authentication errors
        this.updateConnectionStatus('Authentication Required');
        const messagesList = this.container.querySelector('#messagesList');
        if (messagesList) {
            messagesList.innerHTML = `
                <div class="system-message error">
                    <strong>⚠️ Authentication Required</strong><br>
                    You must be logged in to use the chat system.<br>
                    Please login and provide your JWT token when initializing the chat.
                </div>
            `;
        }
        console.error('Authentication required - please provide JWT token');
    }

    setAuthToken(token) {
        // Update auth token dynamically
        this.options.authToken = token;
    }

    closeDiceModal() {
        this.container.querySelector('#diceSelectionModal').style.display = 'none';
        this.resetDiceSelection();
        this.modalOpen = false; // Reset modal state
    }

    resetDiceSelection() {
        this.selectedDice = {};
        const counts = this.container.querySelectorAll('.count');
        counts.forEach(count => count.textContent = '0');

        const modifier = this.container.querySelector('#diceModifier');
        if (modifier) modifier.value = '0';

        this.updateExpressionPreview();
    }

    async confirmDiceAction() {
        const expression = this.updateExpressionPreview();

        if (!expression || expression === 'Select dice') {
            alert('Please select at least one die!');
            return;
        }

        if (this.modalMode === 'request') {
            await this.createDiceRequest(expression);
        } else {
            await this.rollDice(expression);
        }

        this.closeDiceModal();
    }

    async createDiceRequest(expression) {
        const targetPlayer = this.container.querySelector('#targetPlayerSelect')?.value;
        const isTargeted = targetPlayer && targetPlayer !== 'all';

        const description = `Roll ${expression} for skill check`;

        // Format the request message with targeting info
        let requestContent;
        if (isTargeted) {
            requestContent = `🎯 **DM requests ${targetPlayer} to roll**: ${expression}\n**Description**: ${description}\n\n*${targetPlayer}: Click this message to automatically set up the dice and roll!*`;
        } else {
            requestContent = `🎲 **DM requests dice roll**: ${expression}\n**Description**: ${description}\n\n*Any player: Click this message to automatically set up the dice and roll!*`;
        }

        await this.sendDiceMessage(requestContent, 'dice_request', {
            requestedExpression: expression,
            targetPlayer: targetPlayer || 'all'
        });
    }

    async rollDice(expression) {
        try {
            const headers = {
                'Content-Type': 'application/json'
            };

            if (this.options.authToken) {
                headers['Authorization'] = `Bearer ${this.options.authToken}`;
            }

            const response = await fetch(`${this.options.apiBaseUrl}/api/dice/roll`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    expression: expression,
                    description: `${this.currentUser.username} rolled dice`
                })
            });

            if (response.ok) {
                const result = await response.json();
                await this.sendDiceMessage(
                    `🎯 **${this.currentUser.username} rolled ${result.total}**\n` +
                    `**Expression**: \`${expression}\`\n` +
                    `**Breakdown**: ${result.breakdown}` +
                    (result.is_critical ? '\n🔥 **CRITICAL HIT!**' : '') +
                    (result.is_fumble ? '\n💥 **CRITICAL MISS!**' : ''),
                    'dice_response'
                );
            }
        } catch (error) {
            console.error('Error rolling dice:', error);
        }
    }

    async sendDiceMessage(content, messageType = 'dice_request', extraData = {}) {
        // For demo purposes, we'll send it as a regular chat message with special formatting
        try {
            const headers = {
                'Content-Type': 'application/json'
            };

            if (this.options.authToken) {
                headers['Authorization'] = `Bearer ${this.options.authToken}`;
            }

            const response = await fetch(`${this.options.apiBaseUrl}/api/chat/rooms/${this.currentRoom}/messages`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    content: content,
                    username: this.currentUser.username,
                    user_role: this.currentUser.userRole,
                    extra_data: extraData
                })
            });

            if (response.ok) {
                // Force immediate refresh for dice messages
                setTimeout(() => {
                    this.lastMessagesHash = ''; // Reset to force update
                    this.loadMessages();
                }, 100);
            }
        } catch (error) {
            console.error('Error sending dice message:', error);
        }
    }
}

// Global reference for button callbacks
window.currentChat = null;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SimpleDiceChatInterface;
}

window.SimpleDiceChatInterface = SimpleDiceChatInterface;