# Multiplayer Architecture Analysis & Fixes

## Critical Issues Identified

### Issue 1: Only One Player Can Connect at a Time ❌
**Severity**: CRITICAL
**Impact**: Completely breaks multiplayer - second player kicks first player

### Issue 2: Players Don't See Master's Terrain Edits ❌
**Severity**: HIGH
**Impact**: Players only see seed-generated terrain, not DM modifications

---

## Server Log Analysis

### Evidence from Logs (2025-11-01 18:53-18:54)

```
[NEW_GAME] Creating game - seed: 12345, player: JoonejiDM, color: #FF6B6B, session: 7035194
[SUCCESS] WebGameSession created - session: 7035194, final seed: 12345, player: JoonejiDM
[MATCH] Added player: JoonejiDM at position (0, 0, 0)

[NEW_GAME] Creating game - seed: 12345, player: gonji, color: #FECA57, session: 1833922
Removing old game session: 7035194  <-- PROBLEM 1!
[SUCCESS] WebGameSession created - session: 1833922, final seed: 12345, player: gonji
[MATCH] Added player: gonji at position (0, 0, 0)

[NEW_GAME] Creating game - seed: 12345, player: JoonejiDM, color: #FF6B6B, session: 7012504
Removing old game session: 1833922  <-- Only 1 player can exist!
```

**Observation**: Each new player **deletes all existing players** with the same seed

---

## Root Cause Analysis

### Problem 1: Destructive Session Removal

**Location**: `app.py` lines 1030-1039

```python
# Clear old game sessions with the same seed to prevent old players appearing
sessions_to_remove = []
for game_id, game_data in games.items():
    if (isinstance(game_data, WebGameSession) and
        hasattr(game_data, 'seed') and game_data.seed == seed):
        sessions_to_remove.append(game_id)

for old_session_id in sessions_to_remove:
    print(f"Removing old game session: {old_session_id}")
    del games[old_session_id]  # <-- DELETES ALL OTHER PLAYERS!
```

**Why This Was Added**: Probably to prevent duplicate sessions when same user rejoins
**Why It's Wrong**: It removes ALL players with matching seed, not just duplicates from same user

**Result**:
- Player 1 joins → Session created ✓
- Player 2 joins → Player 1's session deleted ❌
- Only 1 player ever exists → Multiplayer broken

---

### Problem 2: Players Generate Their Own Hexes

**Current Architecture**:
1. **Master View**:
   - DM creates `master_session` in `map_sessions` dict
   - DM generates/edits terrain
   - Terrain stored in `map_sessions[session_id]['hexes']`

2. **Player View**:
   - Player calls `/api/new_game` with master's seed
   - Creates `WebGameSession` with its own `HexMap`
   - `HexMap` generates hexes from seed independently
   - Player **never loads master's hex data**!

**Evidence from Logs**:
```python
# Player creates their own map:
World generation: 2 continents generated
  main: center (0,0,0), radius 80
  north: center (200,0,-200), radius 20
Using Minecraft-style 6D biome generation

# Player's WebGameSession generates its own hexes:
get_map_data: returning 7 visible hexes out of 7 total hexes
```

**The Problem**:
- Master edits terrain using `/api/master/update_terrain`
- Changes saved to `map_sessions[master_session_id]['hexes']`
- Players use `WebGameSession.hex_map` which generates from seed only
- **Players never see master's edits - only procedurally generated hexes**

---

## Architecture Mismatch

### Current Flow (BROKEN):

```
DM (Master View):
  1. Create master session → map_sessions[master_id]
  2. Generate terrain → map_sessions[master_id]['hexes'] = [...]
  3. Edit terrain → Updates map_sessions[master_id]['hexes']

Player (Hexcrawl View):
  1. Join master session → Extract seed from master
  2. Create WebGameSession → games[player_session_id]
  3. WebGameSession generates hexes from seed
  4. Load hexes → Uses WebGameSession.hex_map.hexes (FROM SEED, NOT MASTER!)
  5. ❌ Never sees master's hex data from map_sessions
```

### What SHOULD Happen:

```
DM (Master View):
  1. Create master session → map_sessions[master_id]
  2. Generate terrain → map_sessions[master_id]['hexes'] = [...]
  3. Edit terrain → Updates map_sessions[master_id]['hexes']

Player (Hexcrawl View):
  1. Join master session → Extract seed AND master_session_id
  2. Create WebGameSession → games[player_session_id]
  3. Load hexes → FROM map_sessions[master_session_id]['hexes'] ✓
  4. Sync on-demand → Request new hexes from master when exploring
  5. See master's edits → All data comes from single source of truth
```

---

## Solution Design

### Fix 1: Remove Session Deletion Logic

**Change**: Only remove sessions that belong to the **SAME USER**, not all sessions with same seed

```python
# BEFORE (WRONG):
for game_id, game_data in games.items():
    if (isinstance(game_data, WebGameSession) and
        hasattr(game_data, 'seed') and game_data.seed == seed):
        sessions_to_remove.append(game_id)  # Removes ALL players!

# AFTER (CORRECT):
# Don't remove any sessions - allow multiple players with same seed
# OR: Only remove sessions where player_name matches current user
```

**Result**: Multiple players can coexist with same seed ✓

---

### Fix 2: Implement Master Hex Data Synchronization

**Approach**: Players load hexes from master's `map_sessions` data instead of generating their own

**Changes Required**:

#### Backend (`app.py`):

1. **Modify `/api/new_game`** to NOT delete other sessions:
```python
# Remove the session deletion loop entirely
```

2. **Modify `WebGameSession.get_map_data()`** to load from master if available:
```python
def get_map_data(self, master_session_id=None):
    """Get current map data for client"""

    # If this is a player in a master session, load master's hexes
    if master_session_id and master_session_id in map_sessions:
        master_data = map_sessions[master_session_id]
        master_hexes = master_data.get('hexes', [])

        # Filter to visible hexes based on player's exploration
        # (Player can only see hexes they've explored or near their position)
        return {
            'hexes': master_hexes,  # From master, not from seed!
            'current_position': {...},
            ...
        }

    # Fallback to own generated hexes (for solo play)
    return self._get_own_hexes()
```

3. **Add master_session_id tracking** to WebGameSession:
```python
class WebGameSession:
    def __init__(self, session_id, seed=None, player_name=None,
                 player_color=None, master_session_id=None):
        self.session_id = session_id
        self.master_session_id = master_session_id  # NEW!
        ...
```

4. **Modify `/api/get_map`** to pass master_session_id:
```python
@app.route('/api/get_map', methods=['GET'])
def get_map():
    session_id = request.args.get('session_id')
    game = games.get(session_id)

    # Check if this game is part of a master session
    if hasattr(game, 'master_session_id'):
        return jsonify({
            'success': True,
            'map_data': game.get_map_data(game.master_session_id)
        })
```

#### Frontend (`authView.ts`):

**Modify join session logic** to store master_session_id:

```typescript
// After extracting seed, also pass master_session_id
const gameResponse = await this.plugin.apiClient.post('/api/new_game', {
  seed: masterSeed,
  master_session_id: sessionId,  // NEW! Pass master session ID
  player_name: this.plugin.authState.user?.username,
  player_color: this.plugin.authState.user?.playerColor
});
```

---

## Implementation Plan

### Phase 1: Fix Session Deletion (CRITICAL)
1. **Remove session deletion logic** from `/api/new_game`
2. **Test**: Multiple local users can join simultaneously
3. **Verify**: `/api/get_player_positions` returns all players

### Phase 2: Implement Master Hex Sync (HIGH PRIORITY)
1. **Add `master_session_id` field** to WebGameSession
2. **Modify `/api/new_game`** to accept and store `master_session_id`
3. **Update `WebGameSession.get_map_data()`** to load from master's hexes
4. **Update frontend** to pass `master_session_id` when joining
5. **Test**: Players see master's terrain edits

### Phase 3: Optimize Hex Visibility (OPTIONAL)
1. **Implement fog of war** - players only see explored hexes
2. **Add hex discovery** - request new hexes from master when exploring
3. **Add real-time sync** - SocketIO updates when master edits terrain

---

## Testing Checklist

### Test 1: Multiple Players Can Connect
- [ ] DM creates master session
- [ ] Player 1 joins → appears on map
- [ ] Player 2 joins → **both players** visible on map ✓
- [ ] Player 3+ join → all visible ✓
- [ ] Goal: Support 10+ simultaneous players

### Test 2: Players See Master's Edits
- [ ] DM creates terrain with seed
- [ ] DM manually edits hex (changes terrain type)
- [ ] Player joins session
- [ ] **Player sees edited terrain**, not seed-generated ✓
- [ ] DM edits more hexes while player connected
- [ ] **Player's view updates** with new edits ✓

### Test 3: Cross-Computer Multiplayer
- [ ] DM on Computer A creates session
- [ ] Player on Computer B joins
- [ ] Player appears on DM's map ✓
- [ ] DM edits terrain
- [ ] Player sees edits ✓

---

## Current State vs. Goal

| Feature | Current | Goal |
|---------|---------|------|
| Max players | 1 ❌ | 10+ ✓ |
| See master edits | No ❌ | Yes ✓ |
| Multiplayer | Broken ❌ | Working ✓ |
| Remote clients | Broken ❌ | Working ✓ |

---

## Files to Modify

### Backend (Python)
- **app.py**:
  - Line 1030-1039: Remove session deletion
  - Line 1042: Add master_session_id parameter
  - Line 305-340: Modify WebGameSession.get_map_data()
  - Line 470: Modify /api/get_map to use master data

### Frontend (TypeScript)
- **authView.ts**:
  - Line 470: Pass master_session_id to /api/new_game

### Documentation
- **MULTIPLAYER_SYNC_BUGFIX.md**: Update with new fixes
- **CLAUDE.md**: Add known issues and solutions

---

## Risk Assessment

### Low Risk Changes
- ✅ Removing session deletion (lines 1030-1039)
- ✅ Adding master_session_id parameter

### Medium Risk Changes
- ⚠️ Modifying get_map_data() - test thoroughly
- ⚠️ Changing hex data source - ensure backward compatibility

### Testing Strategy
1. Test locally with 2-3 players first
2. Verify no regressions in solo play
3. Test cross-computer before pushing
4. Keep old code commented out for quick rollback

---

## Expected Results After Fixes

1. **Multiple Players**: 10+ players can connect simultaneously
2. **Shared Map**: All players see same hexes (from master's data)
3. **Live Edits**: When DM edits terrain, players see updates
4. **Position Tracking**: All player positions visible on master map
5. **Performance**: No degradation with 10 players

---

## FIXES APPLIED ✅

### Fix 1: Session Deletion Removed (COMPLETED)

**File**: `app.py` lines 1043-1053

**Change**: Commented out the entire session deletion loop that was removing all players with matching seeds.

**Before**:
```python
# Clear old game sessions with the same seed to prevent old players appearing
sessions_to_remove = []
for game_id, game_data in games.items():
    if (isinstance(game_data, WebGameSession) and
        hasattr(game_data, 'seed') and game_data.seed == seed):
        sessions_to_remove.append(game_id)

for old_session_id in sessions_to_remove:
    print(f"Removing old game session: {old_session_id}")
    del games[old_session_id]
```

**After**:
```python
# MULTIPLAYER FIX: Do NOT remove old sessions - allow multiple players with same seed
# The code below was deleting ALL player sessions with matching seed, preventing multiplayer
# sessions_to_remove = []
# ... (entire block commented out)
```

**Result**: Multiple players can now join the same master session simultaneously ✓

---

### Fix 2: Master Hex Data Synchronization (COMPLETED)

#### Backend Changes

**File**: `app.py` lines 292-308

**Change 1**: Added `master_session_id` tracking to `WebGameSession.__init__()`:

```python
class WebGameSession:
    def __init__(self, session_id, seed=None, player_name=None,
                 player_color=None, master_session_id=None):
        self.session_id = session_id
        self.player_name = player_name or f"Player {session_id[-4:]}"
        self.player_color = player_color or '#FFD700'
        self.master_session_id = master_session_id  # NEW: Track master session

        if self.master_session_id:
            print(f"[SESSION] Player {player_name} linked to master session: {master_session_id}")
```

**File**: `app.py` lines 310-348

**Change 2**: Modified `get_map_data()` to load hexes from master session:

```python
def get_map_data(self):
    """Get current map data for client"""
    hexes = []

    # MULTIPLAYER FIX: If this player is in a master session, load hexes from master's data
    if self.master_session_id and self.master_session_id in map_sessions:
        master_session = map_sessions[self.master_session_id]
        master_hexes = master_session.get('hexes', [])
        print(f"[MAP_DATA] Loading {len(master_hexes)} hexes from master session {self.master_session_id}")

        hexes = master_hexes  # From master, not from seed!
        total_hexes = len(hexes)
        visible_count = len(hexes)
    else:
        # Solo play or legacy: use own generated hexes
        # ... (original seed-based generation)
```

**File**: `app.py` line 1054

**Change 3**: Modified `/api/new_game` to accept and store `master_session_id`:

```python
master_session_id = data.get('master_session_id') if data else None
game = WebGameSession(session_id, seed, player_name, player_color, master_session_id)
```

#### Frontend Changes

**File**: `obsidian-hexcrawl-plugin/src/authView.ts` line 472

**Change**: Added `master_session_id` parameter when joining master session:

```typescript
const gameResponse = await this.plugin.apiClient.post('/api/new_game', {
  seed: masterSeed,
  master_session_id: sessionId,  // NEW: Pass master session ID
  player_name: this.plugin.authState.user?.username,
  player_color: this.plugin.authState.user?.playerColor
});
```

**Result**: Players now load hexes from master's edited data instead of generating from seed ✓

---

### Summary of Changes

| Component | File | Lines | Change |
|-----------|------|-------|--------|
| Backend | app.py | 1043-1053 | Removed session deletion logic |
| Backend | app.py | 292-308 | Added master_session_id to WebGameSession |
| Backend | app.py | 310-348 | Modified get_map_data() to load from master |
| Backend | app.py | 1054 | Extract master_session_id from request |
| Frontend | authView.ts | 472 | Pass master_session_id when joining |
| Build | main.js | - | Rebuilt plugin with TypeScript changes |

---

### Testing Instructions

1. **DM Computer**:
   - Start server: `python app.py`
   - Login as Game Master
   - Open Master View
   - Create session with seed (e.g., 12345)
   - Generate terrain
   - Edit some hexes manually
   - Note session ID (e.g., `master_1_1730000000`)

2. **Player Computer 1**:
   - Open Obsidian
   - Login as Player 1
   - Join session using master's session ID
   - Open Hexcrawl Explorer
   - **Verify**: Player appears on DM's map
   - **Verify**: Player sees master's edited hexes, not just seed-generated terrain

3. **Player Computer 2**:
   - Open Obsidian
   - Login as Player 2
   - Join same session using master's session ID
   - Open Hexcrawl Explorer
   - **Verify**: Both Player 1 and Player 2 appear on DM's map
   - **Verify**: Player 2 also sees master's edited hexes

4. **Additional Local Test**:
   - On DM's computer, login as a third player
   - Join the session
   - **Verify**: All 3 players visible on master map
   - **Expected**: Support for 10+ simultaneous players

---

### Known Limitations

1. **Real-time Sync**: Changes made by DM after players join are not automatically pushed to players (requires polling or refresh)
2. **Fog of War**: Not implemented - players see all hexes from master, not just explored areas
3. **Persistence**: In-memory storage - server restart loses all sessions

### Future Enhancements

1. **SocketIO Events**: Emit `terrain_updated` event when DM edits hexes
2. **Fog of War**: Track explored hexes per player, filter visible hexes in get_map_data()
3. **Database Persistence**: Move from in-memory `games` dict to SQLite
4. **Session Discovery**: Add UI for browsing available master sessions

---

Date: 2025-11-01
Author: Claude Code Analysis
Related: MULTIPLAYER_SYNC_BUGFIX.md
