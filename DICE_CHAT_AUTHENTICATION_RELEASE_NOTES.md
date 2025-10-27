# 🔐 Dice Chat Authentication Update - Release Notes

**Version**: 2.0.0
**Date**: 2025-09-27
**Breaking Change**: Yes - Authentication now required for all chat and dice operations

## 🚨 BREAKING CHANGES

### Authentication Now Required

All dice chat and roll API endpoints now require JWT authentication. Anonymous access has been disabled for security.

**Affected Endpoints:**
- `/api/chat/rooms/{room_id}/messages` (GET, POST)
- `/api/chat/rooms/{room_id}/join` (POST)
- `/api/dice/roll` (POST)
- `/api/dice/roll/bulk` (POST)

## 📋 Changes Summary

### 1. **Authentication Required**
- All chat operations require valid JWT token
- All dice roll operations require valid JWT token
- Health check endpoints remain public

### 2. **Username Flexibility Maintained**
- Users can still use any display username
- Custom usernames override authenticated username
- Room access is unrestricted (any authenticated user can join any room)

### 3. **User Tracking**
- All messages linked to authenticated user ID
- Username can be customized per session
- Audit trail maintained via user_id

## 🔧 Required Client Changes

### JavaScript/TypeScript Clients

#### Before (No Authentication):
```javascript
// Old approach - no authentication needed
const response = await fetch('/api/chat/rooms/demo-room/messages', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        content: 'Hello!',
        username: 'Player1'
    })
});
```

#### After (Authentication Required):
```javascript
// New approach - JWT token required
const token = localStorage.getItem('jwt_token'); // Must obtain via login

const response = await fetch('/api/chat/rooms/demo-room/messages', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`  // REQUIRED
    },
    body: JSON.stringify({
        content: 'Hello!',
        username: 'Player1'  // Optional - will use auth username if omitted
    })
});

if (response.status === 401) {
    // Handle authentication failure
    // Redirect to login or refresh token
}
```

### Obsidian Plugin Changes

```typescript
// Ensure token is included in all requests
class DiceChatClient {
    private token: string;

    constructor(token: string) {
        this.token = token;
    }

    async sendMessage(roomId: string, content: string, displayName?: string) {
        const response = await fetch(`/api/chat/rooms/${roomId}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`  // REQUIRED
            },
            body: JSON.stringify({
                content,
                username: displayName  // Optional custom display name
            })
        });

        if (response.status === 401) {
            throw new Error('Authentication required - please login');
        }

        return response.json();
    }
}
```

### Python Clients

```python
import requests

class DiceChatClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'  # REQUIRED
        }

    def send_message(self, room_id, content, username=None):
        data = {'content': content}
        if username:
            data['username'] = username  # Optional custom display name

        response = requests.post(
            f'{self.base_url}/api/chat/rooms/{room_id}/messages',
            headers=self.headers,
            json=data
        )

        if response.status_code == 401:
            raise Exception('Authentication required - please login')

        return response.json()
```

## 🔑 Authentication Flow

### 1. **Login First**
```javascript
// Login to get JWT token
const loginResponse = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        username: 'registered_user',
        password: 'user_password'
    })
});

const { token } = await loginResponse.json();
// Store token for use in all subsequent requests
localStorage.setItem('jwt_token', token);
```

### 2. **Use Token in All Requests**
```javascript
const token = localStorage.getItem('jwt_token');

// Include in every API call
headers: {
    'Authorization': `Bearer ${token}`
}
```

### 3. **Handle Token Expiration**
```javascript
if (response.status === 401) {
    // Token expired or invalid
    // Option 1: Redirect to login
    window.location.href = '/login';

    // Option 2: Refresh token (if refresh endpoint available)
    await refreshToken();
}
```

## 📝 Username Behavior

### Authenticated Username vs Display Username

- **Authenticated Username**: From JWT token (e.g., "john_doe")
- **Display Username**: Can be customized per request (e.g., "Sir John the Brave")

```javascript
// Using authenticated username (from token)
await fetch('/api/chat/rooms/room1/messages', {
    headers: { 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({
        content: 'Hello!'
        // No username field - uses "john_doe" from token
    })
});

// Using custom display name
await fetch('/api/chat/rooms/room1/messages', {
    headers: { 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({
        content: 'Hello!',
        username: 'Sir John the Brave'  // Custom display name
    })
});
```

## 🚀 Migration Guide

### Step 1: Update Authentication
1. Implement login flow if not already present
2. Store JWT token after successful login
3. Add token refresh mechanism for long sessions

### Step 2: Update API Calls
1. Add `Authorization` header to all requests
2. Handle 401 responses appropriately
3. Test with valid and expired tokens

### Step 3: Update Error Handling
```javascript
class AuthenticatedChatClient {
    async makeRequest(url, options = {}) {
        const token = this.getToken();
        if (!token) {
            throw new Error('Not authenticated - please login first');
        }

        const response = await fetch(url, {
            ...options,
            headers: {
                ...options.headers,
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401) {
            // Try to refresh token
            const newToken = await this.refreshToken();
            if (newToken) {
                // Retry with new token
                return this.makeRequest(url, options);
            } else {
                // Redirect to login
                this.redirectToLogin();
            }
        }

        return response;
    }
}
```

## 🧪 Testing Your Integration

### Test Authentication Required
```bash
# This should return 401 Unauthorized
curl -X POST http://localhost:5000/api/chat/rooms/test/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Test message"}'

# Response: {"error": "Authentication required"}
```

### Test With Valid Token
```bash
# First login
TOKEN=$(curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass"}' \
  | jq -r '.token')

# Use token in request
curl -X POST http://localhost:5000/api/chat/rooms/test/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"content": "Authenticated message!"}'

# Success!
```

## 🔍 Debugging Common Issues

### Issue 1: "Authentication required" errors
**Solution**: Ensure JWT token is included in Authorization header

### Issue 2: Username not showing correctly
**Solution**: Pass custom username in request body if needed

### Issue 3: Token expiration during session
**Solution**: Implement token refresh or re-login flow

### Issue 4: CORS errors with Authorization header
**Solution**: Server already configured for CORS with auth headers

## 📊 API Response Changes

### Error Response (401 Unauthorized)
```json
{
    "error": "Authentication required"
}
```

### Success Response (No Change)
```json
{
    "id": 123,
    "content": "Message content",
    "username": "DisplayName",
    "user_id": 456,
    "timestamp": "2025-09-27T10:00:00Z"
}
```

## 🔄 Backwards Compatibility

**NOT MAINTAINED** - All clients must update to include authentication.

For testing/development only, you can temporarily create a user:
```bash
# Create test user via API
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'
```

## 📚 Additional Resources

- **Auth API Docs**: `/api/auth` endpoints for login/register
- **JWT Spec**: Standard JWT Bearer token format
- **Support**: Report issues in the GitHub repository

## 🎯 Benefits of This Change

1. **Security**: All actions tied to authenticated users
2. **Audit Trail**: Complete history of who did what
3. **User Management**: Ban/restrict problematic users
4. **Statistics**: Track per-user dice roll stats
5. **Privacy**: Room messages only visible to authenticated users

## 📅 Deprecation Timeline

- **Immediate**: Authentication required on all endpoints
- **No Grace Period**: Update clients before deploying
- **Test Environment**: Use local instance for testing migration

---

**Questions?** Check the main documentation or open an issue on GitHub.