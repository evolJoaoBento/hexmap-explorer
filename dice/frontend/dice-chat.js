/**
 * Modular Dice Roll Chat Interface
 * A reusable chat component with dice request functionality
 */

class DiceChatInterface {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.getElementById(container) : container;
        this.options = {
            apiBaseUrl: options.apiBaseUrl || 'http://localhost:5000',
            socketUrl: options.socketUrl || 'http://localhost:5000',
            theme: options.theme || 'default',
            enableSounds: options.enableSounds !== false,
            autoScroll: options.autoScroll !== false,
            ...options
        };

        this.socket = null;
        this.currentRoom = null;
        this.currentUser = null;
        this.token = null;
        this.isConnected = false;
        this.typingTimeout = null;
        this.pendingRequests = new Map();

        this.init();
    }

    init() {
        this.createInterface();
        this.bindEvents();
        this.loadTheme();
    }

    createInterface() {
        this.container.innerHTML = `
            <div class="dice-chat-interface ${this.options.theme}">
                <!-- Connection Status -->
                <div class="connection-status" id="connectionStatus">
                    <span class="status-indicator"></span>
                    <span class="status-text">Disconnected</span>
                </div>

                <!-- Room Header -->
                <div class="room-header" id="roomHeader">
                    <h3 class="room-name" id="roomName">No Room Selected</h3>
                    <div class="room-actions">
                        <button class="btn btn-sm" id="roomMembersBtn">👥 Members</button>
                        <button class="btn btn-sm" id="leaveRoomBtn">🚪 Leave</button>
                    </div>
                </div>

                <!-- Messages Area -->
                <div class="messages-container" id="messagesContainer">
                    <div class="messages" id="messagesList"></div>
                    <div class="typing-indicators" id="typingIndicators"></div>
                </div>

                <!-- Dice Request Panel -->
                <div class="dice-requests-panel" id="diceRequestsPanel">
                    <div class="panel-header">
                        <h4>Dice Requests</h4>
                        <span class="request-count" id="requestCount">0</span>
                    </div>
                    <div class="requests-list" id="requestsList"></div>
                </div>

                <!-- Message Input -->
                <div class="message-input-area">
                    <div class="input-controls">
                        <button class="btn btn-dice" id="diceRequestBtn" title="Request Dice Roll">🎲</button>
                        <button class="btn btn-template" id="templateBtn" title="Use Template">📋</button>
                    </div>
                    <div class="input-wrapper">
                        <input type="text" id="messageInput" placeholder="Type a message..." maxlength="1000">
                        <button class="btn btn-send" id="sendBtn">Send</button>
                    </div>
                </div>

                <!-- Dice Request Modal -->
                <div class="modal" id="diceRequestModal">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h3>Request Dice Roll</h3>
                            <button class="modal-close" id="closeModal">&times;</button>
                        </div>
                        <div class="modal-body">
                            <div class="form-group">
                                <label for="targetUser">Target Player:</label>
                                <select id="targetUser" class="form-control">
                                    <option value="">Select a player...</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="diceExpression">Dice Expression:</label>
                                <input type="text" id="diceExpression" class="form-control" placeholder="3d6+2" pattern="[0-9d+\\-x*khlr!]+">
                                <small class="help-text">Examples: d20, 3d6+2, 4d6kh3, 2d20kh1</small>
                            </div>
                            <div class="form-group">
                                <label for="rollDescription">Description:</label>
                                <input type="text" id="rollDescription" class="form-control" placeholder="Attack roll">
                            </div>
                            <div class="form-group">
                                <label for="rollReason">Reason:</label>
                                <textarea id="rollReason" class="form-control" placeholder="You're attacking the orc" rows="2"></textarea>
                            </div>
                            <div class="form-group">
                                <div class="checkbox-group">
                                    <label><input type="checkbox" id="allowAdvantage" checked> Allow Advantage</label>
                                    <label><input type="checkbox" id="allowDisadvantage" checked> Allow Disadvantage</label>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button class="btn btn-secondary" id="cancelRequest">Cancel</button>
                            <button class="btn btn-primary" id="sendRequest">Send Request</button>
                        </div>
                    </div>
                </div>

                <!-- Dice Response Modal -->
                <div class="modal" id="diceResponseModal">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h3 id="responseTitle">Dice Roll Request</h3>
                            <button class="modal-close" id="closeResponseModal">&times;</button>
                        </div>
                        <div class="modal-body">
                            <div class="request-details" id="requestDetails"></div>
                            <div class="roll-controls">
                                <div class="advantage-controls">
                                    <label><input type="radio" name="rollType" value="normal" checked> Normal</label>
                                    <label><input type="radio" name="rollType" value="advantage"> Advantage</label>
                                    <label><input type="radio" name="rollType" value="disadvantage"> Disadvantage</label>
                                </div>
                                <div class="form-group">
                                    <label for="playerComment">Your Comment:</label>
                                    <textarea id="playerComment" class="form-control" placeholder="Optional comment..." rows="2"></textarea>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button class="btn btn-secondary" id="declineRequest">Decline</button>
                            <button class="btn btn-primary" id="rollDice">🎲 Roll!</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    bindEvents() {
        // Message sending
        const messageInput = this.container.querySelector('#messageInput');
        const sendBtn = this.container.querySelector('#sendBtn');

        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            } else {
                this.handleTyping();
            }
        });

        sendBtn.addEventListener('click', () => this.sendMessage());

        // Dice request modal
        const diceRequestBtn = this.container.querySelector('#diceRequestBtn');
        const diceRequestModal = this.container.querySelector('#diceRequestModal');
        const closeModal = this.container.querySelector('#closeModal');
        const cancelRequest = this.container.querySelector('#cancelRequest');
        const sendRequest = this.container.querySelector('#sendRequest');

        diceRequestBtn.addEventListener('click', () => this.openDiceRequestModal());
        closeModal.addEventListener('click', () => this.closeDiceRequestModal());
        cancelRequest.addEventListener('click', () => this.closeDiceRequestModal());
        sendRequest.addEventListener('click', () => this.sendDiceRequest());

        // Dice response modal
        const closeResponseModal = this.container.querySelector('#closeResponseModal');
        const declineRequest = this.container.querySelector('#declineRequest');
        const rollDice = this.container.querySelector('#rollDice');

        closeResponseModal.addEventListener('click', () => this.closeDiceResponseModal());
        declineRequest.addEventListener('click', () => this.declineDiceRequest());
        rollDice.addEventListener('click', () => this.respondToDiceRequest());

        // Room actions
        const leaveRoomBtn = this.container.querySelector('#leaveRoomBtn');
        leaveRoomBtn.addEventListener('click', () => this.leaveRoom());

        // Auto-scroll messages
        if (this.options.autoScroll) {
            const messagesContainer = this.container.querySelector('#messagesContainer');
            messagesContainer.addEventListener('scroll', () => {
                const { scrollTop, scrollHeight, clientHeight } = messagesContainer;
                this.isNearBottom = scrollTop + clientHeight >= scrollHeight - 50;
            });
        }
    }

    loadTheme() {
        // Load CSS theme if not already loaded
        const themeId = `dice-chat-theme-${this.options.theme}`;
        if (!document.getElementById(themeId)) {
            const link = document.createElement('link');
            link.id = themeId;
            link.rel = 'stylesheet';
            link.href = `${this.options.apiBaseUrl}/static/dice-chat-${this.options.theme}.css`;
            document.head.appendChild(link);
        }
    }

    // Connection Management
    connect(token, userId, username) {
        this.token = token;
        this.currentUser = { id: userId, username: username };

        if (this.socket) {
            this.disconnect();
        }

        this.socket = io(this.options.socketUrl, {
            query: { token: token }
        });

        this.socket.on('connect', () => {
            this.isConnected = true;
            this.updateConnectionStatus('Connected', 'connected');
            this.socket.emit('authenticate', { token: token });
        });

        this.socket.on('disconnect', () => {
            this.isConnected = false;
            this.updateConnectionStatus('Disconnected', 'disconnected');
        });

        this.socket.on('authenticated', (data) => {
            this.updateConnectionStatus(`Connected as ${data.username}`, 'authenticated');
        });

        this.socket.on('error', (error) => {
            this.showError(error.message);
        });

        // Message events
        this.socket.on('new_message', (message) => {
            this.addMessage(message);
        });

        this.socket.on('user_typing', (data) => {
            this.handleTypingIndicator(data);
        });

        // Dice request events
        this.socket.on('dice_request_received', (request) => {
            this.handleDiceRequest(request);
        });

        this.socket.on('dice_request_completed', (data) => {
            this.handleDiceRequestCompleted(data);
        });

        this.socket.on('dice_roll_result', (data) => {
            this.showDiceRollResult(data);
        });

        this.socket.on('pending_requests', (data) => {
            this.updatePendingRequests(data.requests);
        });
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        this.isConnected = false;
        this.updateConnectionStatus('Disconnected', 'disconnected');
    }

    // Room Management
    joinRoom(roomId, roomName) {
        if (!this.isConnected) {
            this.showError('Not connected to server');
            return;
        }

        this.currentRoom = { id: roomId, name: roomName };
        this.socket.emit('join_room', { room_id: roomId });

        this.socket.on('joined_room', () => {
            this.updateRoomHeader(roomName);
            this.loadRoomMessages(roomId);
            this.loadRoomMembers(roomId);
        });
    }

    leaveRoom() {
        if (this.currentRoom && this.isConnected) {
            this.socket.emit('leave_room', { room_id: this.currentRoom.id });
            this.currentRoom = null;
            this.updateRoomHeader('No Room Selected');
            this.clearMessages();
        }
    }

    // Message Handling
    sendMessage() {
        const messageInput = this.container.querySelector('#messageInput');
        const content = messageInput.value.trim();

        if (!content || !this.currentRoom || !this.isConnected) {
            return;
        }

        this.socket.emit('send_message', {
            room_id: this.currentRoom.id,
            content: content
        });

        messageInput.value = '';
    }

    addMessage(message) {
        const messagesList = this.container.querySelector('#messagesList');
        const messageElement = this.createMessageElement(message);
        messagesList.appendChild(messageElement);

        if (this.options.autoScroll && this.isNearBottom !== false) {
            this.scrollToBottom();
        }

        if (this.options.enableSounds && message.sender_id !== this.currentUser.id) {
            this.playNotificationSound();
        }
    }

    createMessageElement(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.message_type}`;

        if (message.sender_id === this.currentUser.id) {
            messageDiv.classList.add('own-message');
        }

        const timestamp = new Date(message.created_at).toLocaleTimeString();

        if (message.message_type === 'dice_request') {
            messageDiv.innerHTML = `
                <div class="message-header">
                    <span class="sender">${message.sender_username}</span>
                    <span class="timestamp">${timestamp}</span>
                    <span class="message-type-badge">Dice Request</span>
                </div>
                <div class="message-content dice-request-content">
                    ${this.formatMessageContent(message.content)}
                </div>
            `;
        } else if (message.message_type === 'dice_response') {
            messageDiv.innerHTML = `
                <div class="message-header">
                    <span class="sender">${message.sender_username}</span>
                    <span class="timestamp">${timestamp}</span>
                    <span class="message-type-badge dice-result">Dice Result</span>
                </div>
                <div class="message-content dice-response-content">
                    ${this.formatMessageContent(message.content)}
                </div>
            `;
        } else if (message.is_system) {
            messageDiv.className = 'message system';
            messageDiv.innerHTML = `
                <div class="system-message">
                    <span class="timestamp">${timestamp}</span>
                    ${message.content}
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="message-header">
                    <span class="sender">${message.sender_username}</span>
                    <span class="timestamp">${timestamp}</span>
                </div>
                <div class="message-content">
                    ${this.formatMessageContent(message.content)}
                </div>
            `;
        }

        return messageDiv;
    }

    formatMessageContent(content) {
        // Convert markdown-like formatting and dice expressions
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>')
            .replace(/(d\d+|\d+d\d+(?:[+\-]\d+)?)/gi, '<span class="dice-notation">$1</span>');
    }

    // Dice Request Handling
    openDiceRequestModal() {
        const modal = this.container.querySelector('#diceRequestModal');
        this.loadRoomMembersForRequest();
        modal.style.display = 'block';
    }

    closeDiceRequestModal() {
        const modal = this.container.querySelector('#diceRequestModal');
        modal.style.display = 'none';
        this.clearDiceRequestForm();
    }

    async sendDiceRequest() {
        const targetUserId = this.container.querySelector('#targetUser').value;
        const expression = this.container.querySelector('#diceExpression').value.trim();
        const description = this.container.querySelector('#rollDescription').value.trim();
        const reason = this.container.querySelector('#rollReason').value.trim();
        const allowAdvantage = this.container.querySelector('#allowAdvantage').checked;
        const allowDisadvantage = this.container.querySelector('#allowDisadvantage').checked;

        if (!targetUserId || !expression) {
            this.showError('Please select a target and enter a dice expression');
            return;
        }

        // Validate dice expression
        const isValid = await this.validateDiceExpression(expression);
        if (!isValid) {
            this.showError('Invalid dice expression');
            return;
        }

        this.socket.emit('request_dice_roll', {
            room_id: this.currentRoom.id,
            target_id: parseInt(targetUserId),
            expression: expression,
            description: description || `Roll ${expression}`,
            reason: reason,
            allow_advantage: allowAdvantage,
            allow_disadvantage: allowDisadvantage
        });

        this.closeDiceRequestModal();
    }

    handleDiceRequest(request) {
        this.pendingRequests.set(request.id, request);
        this.updatePendingRequestsDisplay();
        this.showDiceRequestNotification(request);
    }

    showDiceRequestNotification(request) {
        // Show browser notification if permissions granted
        if (Notification.permission === 'granted') {
            new Notification(`Dice Roll Request from ${request.requester_username}`, {
                body: request.description,
                icon: '/static/dice-icon.png'
            });
        }

        // Auto-open modal if only one pending request
        if (this.pendingRequests.size === 1) {
            this.openDiceResponseModal(request);
        }
    }

    openDiceResponseModal(request) {
        const modal = this.container.querySelector('#diceResponseModal');
        const title = this.container.querySelector('#responseTitle');
        const details = this.container.querySelector('#requestDetails');

        title.textContent = `Dice Request from ${request.requester_username}`;
        details.innerHTML = `
            <div class="request-info">
                <p><strong>Roll:</strong> <code>${request.expression}</code></p>
                <p><strong>Description:</strong> ${request.description}</p>
                ${request.reason ? `<p><strong>Reason:</strong> ${request.reason}</p>` : ''}
                <p><strong>Options:</strong>
                    ${request.allow_advantage ? '✓ Advantage allowed' : '✗ No advantage'}
                    ${request.allow_disadvantage ? ', ✓ Disadvantage allowed' : ', ✗ No disadvantage'}
                </p>
            </div>
        `;

        // Set up radio buttons based on allowed options
        const advantageRadio = this.container.querySelector('input[value="advantage"]');
        const disadvantageRadio = this.container.querySelector('input[value="disadvantage"]');

        advantageRadio.disabled = !request.allow_advantage;
        disadvantageRadio.disabled = !request.allow_disadvantage;

        modal.dataset.requestId = request.id;
        modal.style.display = 'block';
    }

    closeDiceResponseModal() {
        const modal = this.container.querySelector('#diceResponseModal');
        modal.style.display = 'none';
    }

    async respondToDiceRequest() {
        const modal = this.container.querySelector('#diceResponseModal');
        const requestId = modal.dataset.requestId;
        const rollType = this.container.querySelector('input[name="rollType"]:checked').value;
        const comment = this.container.querySelector('#playerComment').value.trim();

        const advantage = rollType === 'advantage';
        const disadvantage = rollType === 'disadvantage';

        this.socket.emit('respond_to_dice_request', {
            request_id: requestId,
            advantage: advantage,
            disadvantage: disadvantage,
            comment: comment
        });

        this.pendingRequests.delete(requestId);
        this.updatePendingRequestsDisplay();
        this.closeDiceResponseModal();
    }

    // UI Helper Methods
    updateConnectionStatus(text, status) {
        const statusIndicator = this.container.querySelector('.status-indicator');
        const statusText = this.container.querySelector('.status-text');

        statusText.textContent = text;
        statusIndicator.className = `status-indicator ${status}`;
    }

    updateRoomHeader(roomName) {
        const roomNameElement = this.container.querySelector('#roomName');
        roomNameElement.textContent = roomName;
    }

    updatePendingRequestsDisplay() {
        const requestCount = this.container.querySelector('#requestCount');
        const requestsList = this.container.querySelector('#requestsList');

        requestCount.textContent = this.pendingRequests.size;

        requestsList.innerHTML = '';
        for (const [id, request] of this.pendingRequests) {
            const requestElement = this.createRequestElement(request);
            requestsList.appendChild(requestElement);
        }

        // Show/hide panel
        const panel = this.container.querySelector('#diceRequestsPanel');
        panel.style.display = this.pendingRequests.size > 0 ? 'block' : 'none';
    }

    createRequestElement(request) {
        const div = document.createElement('div');
        div.className = 'dice-request-item';
        div.innerHTML = `
            <div class="request-summary">
                <strong>${request.requester_username}</strong> requests:
                <code>${request.expression}</code>
            </div>
            <div class="request-description">${request.description}</div>
            <div class="request-actions">
                <button class="btn btn-sm btn-primary" onclick="diceChatInterface.openDiceResponseModal(${JSON.stringify(request).replace(/"/g, '&quot;')})">
                    🎲 Respond
                </button>
            </div>
        `;
        return div;
    }

    scrollToBottom() {
        const messagesContainer = this.container.querySelector('#messagesContainer');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    showError(message) {
        console.error('Dice Chat Error:', message);
        // Could show a toast notification or modal
    }

    playNotificationSound() {
        if (this.options.enableSounds) {
            // Play a subtle notification sound
            const audio = new Audio('/static/notification.mp3');
            audio.volume = 0.3;
            audio.play().catch(() => {}); // Ignore errors
        }
    }

    async validateDiceExpression(expression) {
        try {
            const response = await fetch(`${this.options.apiBaseUrl}/api/dice/parse`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ expression: expression })
            });

            const data = await response.json();
            return data.is_valid;
        } catch (error) {
            return false;
        }
    }

    // Public API
    setTheme(theme) {
        this.options.theme = theme;
        this.container.querySelector('.dice-chat-interface').className =
            `dice-chat-interface ${theme}`;
        this.loadTheme();
    }

    getCurrentRoom() {
        return this.currentRoom;
    }

    getPendingRequests() {
        return Array.from(this.pendingRequests.values());
    }

    clearMessages() {
        const messagesList = this.container.querySelector('#messagesList');
        messagesList.innerHTML = '';
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DiceChatInterface;
}

// Global variable for direct usage
window.DiceChatInterface = DiceChatInterface;