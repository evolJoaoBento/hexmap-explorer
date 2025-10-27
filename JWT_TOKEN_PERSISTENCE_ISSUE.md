# JWT Token Persistence Issue in Obsidian Hexcrawl Plugin

## Project Overview
This is an Obsidian plugin that connects to a Flask-based hexcrawl gaming server. The plugin allows users to authenticate, join game sessions, and interact with hex-based maps through Obsidian's interface.

**Architecture:**
- **Frontend**: TypeScript Obsidian plugin (`obsidian-hexcrawl-plugin/`)
- **Backend**: Flask REST API server (`app.py`) with JWT authentication
- **Communication**: HTTP requests via Axios client with JWT Bearer tokens

## Problem Description
Users cannot maintain persistent authentication sessions despite successful login. The "Remember Me" functionality fails, requiring users to re-authenticate repeatedly.

### Symptoms
1. User logs in successfully with "Remember Me" checked
2. JWT token is generated and stored by server
3. Subsequent API calls fail with 401 Unauthorized errors
4. Plugin loses authentication state unexpectedly
5. Server logs show JWT token validation failures after successful login

### Technical Details

**Authentication Flow:**
1. User enters credentials in `authView.ts`
2. Login request sent to `/auth/login` endpoint
3. Server responds with JWT token
4. Token stored in plugin settings (Base64 encoded)
5. Axios client configured with Authorization header
6. Subsequent requests should use stored token

**Current Implementation Files:**
- `src/main.ts` - Main plugin class with API client management
- `src/authView.ts` - Authentication interface
- `src/types.ts` - TypeScript interfaces including `HexcrawlSettings`
- `app.py` - Flask server with JWT authentication

### Root Cause Analysis
The issue occurs in the `saveSettings()` method in `main.ts`. Every time settings are saved (which happens after login), the method calls `initializeApiClient()`, creating a new Axios instance that loses the JWT token from the previous instance.

**Problematic Code Pattern:**
```typescript
async saveSettings() {
    await this.saveData(this.settings);
    this.initializeApiClient(); // This always recreates Axios client, losing JWT token
}
```

**Expected Behavior:**
The API client should only be reinitialized when the server URL changes, not on every settings save.

### Attempted Fix
Modified `saveSettings()` to conditionally reinitialize:
```typescript
async saveSettings() {
    const currentApiBaseUrl = this.apiClient?.defaults?.baseURL;
    await this.saveData(this.settings);
    
    if (currentApiBaseUrl !== this.settings.serverUrl) {
        console.log('🔄 Server URL changed, reinitializing API client...');
        this.initializeApiClient();
    } else {
        console.log('💾 Settings saved without reinitializing API client (URL unchanged)');
    }
}
```

### Current Status
Despite implementing the fix above, the authentication persistence issue continues. The problem may involve:

1. **Token Storage**: JWT tokens may not be properly persisted to plugin settings
2. **Token Restoration**: Saved tokens may not be correctly restored on plugin reload
3. **API Client Lifecycle**: Additional scenarios where API client gets reinitialized
4. **Server-Side Issues**: JWT token validation or session management problems
5. **Timing Issues**: Race conditions between authentication and subsequent API calls

### Debugging Information Needed

**Plugin Side:**
- Verify JWT token is actually saved to plugin settings after login
- Confirm token is restored when plugin initializes
- Check if `initializeApiClient()` is called from other locations
- Monitor Axios client state throughout plugin lifecycle

**Server Side:**
- Validate JWT token generation and signature
- Check token expiration times and refresh logic
- Verify CORS and authentication middleware order
- Monitor token validation in request headers

### Test Reproduction Steps
1. Install and enable the Obsidian Hexcrawl plugin
2. Start Flask server (`python app.py`)
3. Open plugin authentication view
4. Login with valid credentials and "Remember Me" checked
5. Observe successful login response
6. Try any subsequent API call (join session, load map, etc.)
7. Observe 401 authentication failure

### Environment Details
- **Platform**: Windows 11
- **Obsidian**: Latest version
- **Node.js/TypeScript**: Plugin development environment
- **Python/Flask**: Backend server with JWT authentication
- **Database**: SQLite for user/session storage

### Related Code Files
- `obsidian-hexcrawl-plugin/src/main.ts` - Plugin lifecycle and API client
- `obsidian-hexcrawl-plugin/src/authView.ts` - Authentication UI
- `obsidian-hexcrawl-plugin/src/types.ts` - Settings interface
- `app.py` - Flask server with authentication endpoints
- `auth.py` - JWT authentication logic (if exists)

### Success Criteria
A successful fix should allow:
1. User logs in once with "Remember Me"
2. Plugin maintains authentication across Obsidian sessions
3. All API calls succeed without re-authentication
4. JWT tokens persist properly in plugin settings
5. Token restoration works after plugin reload/Obsidian restart

This issue prevents the plugin from being usable in practice, as users cannot maintain game sessions or interact with the hexcrawl system effectively.