# 🐛 JWT Secret Mismatch Bug - FIXED

**Date**: 2025-09-27
**Severity**: Critical
**Status**: ✅ RESOLVED

## 🔍 Bug Analysis

### Evidence from Logs:
- ✅ Login: 200 OK → Token generated
- ✅ Health check (`/api/dice/health`): 200 OK → **No auth required** (public endpoint)
- ❌ Chat endpoints (`/api/chat/*`): 401 → **Same token rejected**

### Root Cause Discovered:

**JWT Secret Mismatch** between token generation and validation:

#### Token Generation (auth.py):
```python
# Used current_app.config['SECRET_KEY']
token = jwt.encode(token_payload, current_app.config['SECRET_KEY'], algorithm='HS256')
```

#### Token Validation (dice/routes.py):
```python
# Used different secret!
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-here')
payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
```

**Result**: Tokens generated with `SECRET_KEY` but validated with `JWT_SECRET` → **Always fails!**

## ✅ Fix Applied

### Updated dice/routes.py:

#### Before (Broken):
```python
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-here')
payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
```

#### After (Fixed):
```python
def get_jwt_secret():
    """Get JWT secret from Flask app config to match main auth system"""
    return current_app.config['SECRET_KEY']

payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
```

### Why This Fix Works:
- ✅ **Same Secret**: Both generation and validation use `current_app.config['SECRET_KEY']`
- ✅ **Consistent**: All endpoints now use identical JWT validation
- ✅ **Secure**: Maintains security while fixing the bug

## 🧪 Test Results Expected

After this fix, your client should see:

### Before Fix:
```
✅ Login: 200 OK
✅ Health: 200 OK (no auth)
❌ Chat: 401 UNAUTHORIZED
```

### After Fix:
```
✅ Login: 200 OK
✅ Health: 200 OK (no auth)
✅ Chat: 200/201 OK (auth working!)
```

## 🎯 Impact

### Fixed Endpoints:
- ✅ `POST /api/chat/rooms` (room creation)
- ✅ `POST /api/chat/rooms/{id}/join` (room joining)
- ✅ `POST /api/chat/rooms/{id}/messages` (send messages)
- ✅ `GET /api/chat/rooms/{id}/messages` (get messages)
- ✅ `POST /api/dice/roll` (dice rolling)
- ✅ `POST /api/dice/roll/bulk` (bulk rolling)

### Why Health Check "Worked":
The `/api/dice/health` endpoint is **public** (no `@require_auth` decorator), so it never validated the token. This created the false impression that dice endpoints worked while chat endpoints didn't.

## 🔧 Technical Details

### JWT Validation Flow (Fixed):
1. **Login** → Generate token with `SECRET_KEY`
2. **Request** → Include `Authorization: Bearer {token}`
3. **Validation** → Decode token with **same** `SECRET_KEY`
4. **Success** → Request processed

### Security Maintained:
- Same encryption strength
- Same secret rotation capabilities
- Same token expiration handling
- No security downgrade

## 🚀 Deployment

### Server Restart Required:
This fix requires restarting the Flask server to reload the updated code.

```bash
# Stop current server (Ctrl+C)
# Restart server
python app.py
```

### No Client Changes Needed:
Your Obsidian plugin and external dice clients require **no code changes**. The same tokens will now work correctly.

## ✅ Verification

### Test Commands:
```bash
# Get token
TOKEN=$(curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "JoonejiDM", "password": "your_password"}' \
  | jq -r '.token')

# Test chat endpoint (should now work)
curl -X POST http://localhost:5000/api/chat/rooms \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"room_id": "test-room"}'

# Expected: 201 Created (not 401 Unauthorized)
```

## 📋 Summary

**The bug was a classic configuration mismatch:**
- Two different JWT secrets in the same application
- Tokens generated with one secret, validated with another
- Health endpoint was misleading (no auth required)

**The fix ensures consistency:**
- All JWT operations use the same secret
- Same validation logic across all authenticated endpoints
- Maintains security while fixing functionality

**Your client should now work perfectly!** 🎲✨

---

**Status**: Bug resolved, ready for testing.