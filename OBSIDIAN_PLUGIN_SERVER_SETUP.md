# Obsidian Plugin Server Setup Guide

This guide explains the server-side changes required to support the Obsidian Hexcrawl plugin.

## ✅ Changes Made

### 1. API Compatibility Layer (`api_compatibility.py`)

Created a new compatibility layer that provides plugin-friendly endpoints:

- **`/api/plugin/new_game`** - Creates a new game session without authentication
- **`/api/plugin/get_map`** - Returns map data with offset coordinates (x,y)
- **`/api/plugin/move`** - Accepts directional movement (n, ne, se, s, sw, nw)
- **`/api/plugin/generate_description`** - Generates AI descriptions using x,y coordinates
- **`/api/plugin/health`** - Health check endpoint for connectivity testing

### 2. Coordinate System Translation

The plugin uses **offset coordinates** (x, y) while the server internally uses **cube coordinates** (q, r, s). The compatibility layer handles automatic translation:

```python
def cube_to_offset(q: int, r: int, s: int) -> Tuple[int, int]:
    """Convert cube coordinates to offset coordinates (x, y)"""
    x = q
    y = r + (q - (q & 1)) // 2
    return x, y

def offset_to_cube(x: int, y: int) -> Tuple[int, int, int]:
    """Convert offset coordinates (x, y) to cube coordinates"""
    q = x
    r = y - (x - (x & 1)) // 2
    s = -q - r
    return q, r, s
```

### 3. Direction-Based Movement

The plugin sends direction strings instead of coordinates. The compatibility layer maps directions to cube coordinate vectors:

```python
DIRECTION_VECTORS = {
    'n': (0, -1, 1),   # North
    'ne': (1, -1, 0),  # Northeast  
    's': (0, 1, -1),   # South
    'sw': (-1, 1, 0),  # Southwest
    'nw': (-1, 0, 1),  # Northwest
    'se': (1, 0, -1),  # Southeast
}
```

### 4. Optional Authentication

Plugin endpoints use `@optional_auth` decorator instead of `@login_required`, making them accessible without web authentication while still supporting session management.

## 🚀 Installation

1. The compatibility layer is automatically imported in `app.py`:
```python
# Register plugin API blueprint  
from api_compatibility import plugin_api
app.register_blueprint(plugin_api)
```

2. No additional dependencies are required - uses existing Flask infrastructure.

## 🧪 Testing

Use the provided test script to verify all endpoints work:

```bash
python test_plugin_api.py
```

Expected output:
```
=== Testing Plugin API Endpoints ===
✅ PASS - Health Check
✅ PASS - New Game  
✅ PASS - Get Map
✅ PASS - Move
✅ PASS - Generate Description

=== SUMMARY: 5/5 tests passed ===
```

## 📊 API Response Formats

### New Game Response
```json
{
  "success": true,
  "session_id": "1234567",
  "message": "New game started with map: default",
  "player_position": {"x": 0, "y": 0}
}
```

### Get Map Response
```json
{
  "success": true,
  "hexes": [
    {
      "x": 0, "y": 0,
      "terrain": "plains",
      "biome": "temperate",
      "elevation": 100,
      "description": "Rolling grasslands...",
      "explored": true,
      "features": []
    }
  ],
  "player_position": {"x": 0, "y": 0},
  "map_name": "default",
  "width": 50,
  "height": 50
}
```

### Move Response
```json
{
  "success": true,
  "message": "Moved n",
  "player_position": {"x": 0, "y": -1}
}
```

### Generate Description Response
```json
{
  "success": true,
  "description": "A vast plain stretches before you...",
  "coordinates": {"x": 0, "y": 0}
}
```

## 🔧 Configuration

### CORS Settings
CORS is already configured in `app.py` to allow cross-origin requests from Obsidian:

```python
cors = CORS(app, origins=app.config['CORS_ORIGINS'])
```

### Session Management
Plugin endpoints create and manage Flask sessions automatically. No additional configuration required.

## 🐛 Troubleshooting

### Common Issues

1. **Import Error**: Ensure `api_compatibility.py` is in the root directory with `app.py`

2. **Authentication Errors**: Plugin endpoints should NOT require login. If you see 401 errors, check that `@optional_auth` is used instead of `@login_required`

3. **Coordinate Mismatch**: The plugin expects x,y coordinates. If hexes appear in wrong positions, verify coordinate conversion functions.

4. **CORS Issues**: If the plugin can't connect, check CORS configuration in Flask app settings.

### Debug Mode

Enable Flask debug mode to see detailed error messages:
```python
app.run(debug=True)
```

## 🔄 Backward Compatibility

The new plugin API endpoints don't affect existing web interface functionality:

- Original `/api/*` endpoints remain unchanged
- Web authentication still works for browser interface  
- Plugin API runs alongside existing API without conflicts

## 📈 Performance Considerations

- Plugin endpoints are lightweight and don't require database queries for authentication
- Coordinate conversions are O(1) operations
- Session data is stored in Flask sessions (consider Redis for production scaling)

## 🛣️ Future Enhancements

Potential improvements for the plugin API:

- **WebSocket Support**: Real-time updates for multiplayer sessions
- **Bulk Operations**: Get/update multiple hexes in single request
- **Filtering**: Query specific terrain types or areas
- **Map Templates**: Support for different map configurations
- **Export/Import**: Save/load map states for backup