"""
API Compatibility Layer for Obsidian Plugin
Provides endpoints compatible with the Hexcrawl Obsidian plugin
"""
from flask import Blueprint, jsonify, request, session
from functools import wraps
import random
from typing import Dict, Tuple, Optional

# Create blueprint for plugin API
plugin_api = Blueprint('plugin_api', __name__, url_prefix='/api/plugin')

# Direction to cube coordinate mappings
DIRECTION_VECTORS = {
    'n': (0, -1, 1),   # North
    'ne': (1, -1, 0),  # Northeast  
    's': (0, 1, -1),   # South
    'sw': (-1, 1, 0),  # Southwest
    'nw': (-1, 0, 1),  # Northwest
    'se': (1, 0, -1),  # Southeast
}

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

def optional_auth(f):
    """Decorator that makes authentication optional for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Don't require authentication, but use it if available
        return f(*args, **kwargs)
    return decorated_function

@plugin_api.route('/new_game', methods=['POST'])
@optional_auth
def plugin_new_game():
    """Start a new game - Plugin compatible version"""
    from app import games, WebGameSession
    
    try:
        data = request.json or {}
        map_name = data.get('map_name', 'default')
        seed = data.get('seed')
        
        # Generate session ID if not present
        if 'session_id' not in session:
            session['session_id'] = str(random.randint(1000000, 9999999))
        
        session_id = session['session_id']
        
        # Create new game session
        game = WebGameSession(
            session_id=session_id,
            seed=seed,
            player_name=f"Obsidian Player {session_id[-4:]}",
            player_color='#4A90E2'
        )
        
        games[session_id] = game
        
        # Get initial position in offset coordinates
        q, r, s = game.hex_map.current_position
        x, y = cube_to_offset(q, r, s)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': f'New game started with map: {map_name}',
            'player_position': {'x': x, 'y': y}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@plugin_api.route('/get_map', methods=['GET'])
@optional_auth
def plugin_get_map():
    """Get current map data - Plugin compatible version"""
    from app import games
    
    session_id = session.get('session_id')
    if not session_id or session_id not in games:
        return jsonify({'success': False, 'error': 'No active game session'}), 404
    
    try:
        game = games[session_id]
        map_data = game.get_map_data()
        
        # Convert cube coordinates to offset for all hexes
        hexes = []
        for coord, hex_data in map_data['hexes'].items():
            q, r, s = coord
            x, y = cube_to_offset(q, r, s)
            
            hex_info = {
                'x': x,
                'y': y,
                'terrain': hex_data.get('terrain'),
                'biome': hex_data.get('biome'),
                'elevation': hex_data.get('elevation'),
                'description': hex_data.get('description'),
                'explored': hex_data.get('explored', False),
                'features': hex_data.get('features', [])
            }
            hexes.append(hex_info)
        
        # Convert player position
        q, r, s = game.hex_map.current_position
        x, y = cube_to_offset(q, r, s)
        
        return jsonify({
            'success': True,
            'hexes': hexes,
            'player_position': {'x': x, 'y': y},
            'map_name': getattr(game, 'map_name', 'default'),
            'width': 50,  # Default dimensions
            'height': 50
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@plugin_api.route('/move', methods=['POST'])
@optional_auth
def plugin_move():
    """Move player by direction - Plugin compatible version"""
    from app import games
    
    session_id = session.get('session_id')
    if not session_id or session_id not in games:
        return jsonify({'success': False, 'error': 'No active game session'}), 404
    
    try:
        data = request.json or {}
        direction = data.get('direction')
        
        if not direction or direction not in DIRECTION_VECTORS:
            return jsonify({
                'success': False, 
                'message': f'Invalid direction: {direction}'
            }), 400
        
        game = games[session_id]
        current_q, current_r, current_s = game.hex_map.current_position
        
        # Calculate new position
        dq, dr, ds = DIRECTION_VECTORS[direction]
        new_q = current_q + dq
        new_r = current_r + dr
        new_s = current_s + ds
        
        # Attempt to move
        success = game.move_to(new_q, new_r, new_s)
        
        if success:
            # Get new position in offset coordinates
            x, y = cube_to_offset(new_q, new_r, new_s)
            return jsonify({
                'success': True,
                'message': f'Moved {direction}',
                'player_position': {'x': x, 'y': y}
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Cannot move in that direction'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@plugin_api.route('/generate_description', methods=['POST'])
@optional_auth  
def plugin_generate_description():
    """Generate hex description - Plugin compatible version"""
    from app import games
    
    session_id = session.get('session_id')
    if not session_id or session_id not in games:
        return jsonify({'success': False, 'error': 'No active game session'}), 404
    
    try:
        data = request.json or {}
        x = data.get('x')
        y = data.get('y')
        
        if x is None or y is None:
            return jsonify({
                'success': False,
                'error': 'x and y coordinates required'
            }), 400
        
        # Convert offset to cube coordinates
        q, r, s = offset_to_cube(x, y)
        
        game = games[session_id]
        hex_obj = game.hex_map.hexes.get((q, r, s))
        
        if not hex_obj:
            # Generate hex if it doesn't exist
            hex_obj = game.hex_map.create_hex(q, r, s)
            game.hex_map.hexes[(q, r, s)] = hex_obj
        
        # Generate description using AI
        if game.gen_manager and hasattr(game.gen_manager, 'generate_hex_description'):
            description = game.gen_manager.generate_hex_description(hex_obj)
            hex_obj.description = description
        else:
            # Fallback description
            description = f"A {hex_obj.terrain} hex at coordinates {x},{y}."
            hex_obj.description = description
        
        return jsonify({
            'success': True,
            'description': description,
            'coordinates': {'x': x, 'y': y}
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@plugin_api.route('/health', methods=['GET'])
def plugin_health():
    """Health check endpoint for plugin connectivity test"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'plugin_api_version': '1.0.0'
    })