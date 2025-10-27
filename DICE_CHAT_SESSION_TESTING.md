# 🎲 Dice Chat Session Testing Guide

## New Features Added

### 1. **Configurable Room IDs**

The dice chat system now supports custom room IDs instead of being locked to 'demo-room':

- **Generate Random Room**: System creates unique room IDs like `room-a3f2k9x1b`
- **Custom Room IDs**: Enter any room ID you want
- **Room Display**: Room ID shown in chat header (hover for full ID)
- **Room Sharing**: Copy and share room IDs between clients

### 2. **Session Information Display**

#### Main Demo Page (`/dice-chat`)
- Shows session ID prominently at the top
- **Copy Button**: One-click copy of session ID
- **Room ID Fields**: Both DM and Player can enter custom room IDs
- **Auto-join**: Player automatically joins DM's room if no room specified

### 3. **Multi-Client Test Interface**

New comprehensive testing page at `/dice-chat-test`:

#### Features:
- **Session Management**: Create/set room IDs
- **Multiple Clients**: Add unlimited DM, Player, or Spectator clients
- **Same Page Testing**: Test multiple connections on one screen
- **Status Tracking**: See connection status for each client
- **Share Links**: Generate shareable URLs with room ID

## How to Use

### Basic Testing (Two Panels)

1. **Access**: `http://localhost:5000/dice-chat`
2. **DM Setup**:
   - Enter username
   - Leave Room ID empty (generates new) or enter custom
   - Click "Connect as DM"
3. **Player Setup**:
   - Enter username
   - Enter the same Room ID (or leave empty if on same page)
   - Click "Connect as Player"
4. **Copy Session**: Use the copy button to share session ID

### Advanced Multi-Client Testing

1. **Access**: `http://localhost:5000/dice-chat-test`
2. **Create Room**:
   - Click "Generate Random" or enter custom room ID
   - Click "Set Room ID"
3. **Add Clients**:
   - Click "➕ Add DM Client"
   - Click "➕ Add Player Client" (multiple times for multiple players)
   - Click "👁️ Add Spectator" for view-only clients
4. **Connect Each Client**:
   - Enter unique username for each
   - Click "Connect" for each client
5. **Test Interactions**:
   - DM creates dice requests
   - Players click requests to auto-populate dice
   - All clients see messages in real-time

### Cross-Browser/Device Testing

1. **Create Session**: Start a session on one device
2. **Copy Room ID**: Use the copy button
3. **Share Link**:
   - Direct: `http://localhost:5000/dice-chat`
   - With Room: `http://localhost:5000/dice-chat-test?room=YOUR_ROOM_ID`
4. **Join from Other Device**: Enter same room ID

## API Integration

### JavaScript SDK

```javascript
// Create chat with specific room
const chat = new SimpleDiceChatInterface(container, {
    apiBaseUrl: 'http://localhost:5000',
    userRole: 'player',
    roomId: 'my-custom-room-123'  // Specify room ID
});

// Connect to specific room
chat.connect('PlayerName', 'player', 'my-custom-room-123');

// Get current room
const currentRoom = chat.getRoom();

// Change room
chat.setRoom('new-room-456');
```

### Direct API Calls

```bash
# Join specific room
curl -X POST http://localhost:5000/api/chat/rooms/my-room-123/join \
  -H "Content-Type: application/json" \
  -d '{"username": "TestPlayer", "user_role": "player"}'

# Send message to specific room
curl -X POST http://localhost:5000/api/chat/rooms/my-room-123/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello from API!", "username": "TestPlayer"}'

# Get messages from specific room
curl http://localhost:5000/api/chat/rooms/my-room-123/messages
```

## Room ID Formats

### Recommended Patterns:
- **Campaign-based**: `campaign-waterdeep-session-3`
- **Date-based**: `game-2024-01-25-evening`
- **Random**: `room-x7k3n9p2` (auto-generated)
- **Simple**: `bobs-game`, `friday-dnd`

### Rules:
- **Characters**: Letters, numbers, hyphens, underscores
- **Length**: 1-100 characters
- **Case**: Case-insensitive (treated as lowercase)

## Database Integration

Currently, the system uses:
- **Simple usernames**: Not tied to database accounts
- **Room persistence**: Messages stored in `simple_chat_messages` table
- **No authentication required**: Optional JWT support exists

### Future Database Account Support

To integrate with actual database accounts:

1. **Enable Authentication**: Require JWT tokens
2. **User Lookup**: Validate usernames against user table
3. **Permissions**: Add role-based access control
4. **History**: Link messages to user accounts

## Testing Scenarios

### 1. Basic DM-Player Interaction
- DM creates dice request
- Player clicks to auto-fill dice
- Player rolls
- Both see results

### 2. Multiple Players
- Create 3+ player clients
- DM requests different rolls from each
- Test simultaneous rolls
- Verify all see results

### 3. Persistence Testing
- Create room with messages
- Disconnect all clients
- Reconnect with same room ID
- Verify message history loads

### 4. Cross-Device Testing
- Start session on computer
- Join from phone/tablet
- Test responsiveness
- Verify real-time sync

## Troubleshooting

### "Cannot connect"
- Check server is running: `python app.py`
- Verify URL: `http://localhost:5000`
- Check browser console for errors

### "Room not found"
- Room IDs are case-sensitive in URLs
- Verify exact room ID copied
- Check for spaces/special characters

### "Messages not updating"
- 3-second polling delay is normal
- Check network tab for API calls
- Verify same room ID for all clients

### "Dice not auto-filling"
- Only works for Player role clicking DM requests
- Ensure expression format is supported (d4-d20)
- Check browser console for parsing errors

## Performance Notes

- **Polling Interval**: 3 seconds (reduces server load)
- **Message Limit**: 50 recent messages loaded
- **Room Limit**: Unlimited rooms supported
- **Client Limit**: 10-20 simultaneous clients recommended per room

## Next Steps

1. **WebSocket Support**: Replace polling with real-time WebSocket
2. **Database Accounts**: Full user authentication integration
3. **Hexcrawl Integration**: Link rooms to hexcrawl campaigns
4. **Persistent Rooms**: Save room configurations
5. **Admin Tools**: Room management interface