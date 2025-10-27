"""
Flask web application for Hex Map Explorer
"""
from flask import Flask, render_template, jsonify, request, session, send_from_directory, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
from flask_migrate import Migrate
import json
import random
import os
import sys
import logging
import time
from datetime import datetime
from dotenv import load_dotenv
import jwt

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.map import HexMap
from generation.ollama_client import OllamaClient
from generation.manager import GenerationManager
from config.constants import TRANSPORTATION_MODES
from config.security_config import get_config
from models import db, User
from auth import auth_bp, token_required
from validation_schemas import (
    validate_request_data, CreateMapSessionSchema, UpdatePlayerPositionSchema,
    UpdateSessionNameSchema, TeleportPlayerSchema, GenerateHexMapSchema,
    UpdateHexTerrainSchema, ForceSyncWorldSchema, SaveMapForGameSchema,
    GenerateDescriptionSchema, sanitize_session_id, sanitize_string
)
# from session_manager import session_manager  # Temporarily disabled to fix import issues

# Initialize Flask app with security configuration
app = Flask(__name__)
config_class = get_config()
app.config.from_object(config_class)

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

# Initialize security extensions (disable CSRF for API endpoints)
# csrf = CSRFProtect(app)  # Temporarily disabled for API endpoints
# Debug CORS configuration
print("CORS Configuration:")
print(f"  Origins: {app.config.get('CORS_ORIGINS', 'NOT SET')}")
print(f"  Allow Headers: {app.config.get('CORS_ALLOW_HEADERS', 'NOT SET')}")
print(f"  Allow Methods: {app.config.get('CORS_ALLOW_METHODS', 'NOT SET')}")
print(f"  Supports Credentials: {app.config.get('CORS_SUPPORTS_CREDENTIALS', 'NOT SET')}")

# CORS configuration that supports both Obsidian plugin and external clients
# Note: Can't use wildcard (*) with credentials=True for security reasons
cors = CORS(app,
    origins=[
        'app://obsidian.md',           # Obsidian plugin (needs credentials)
        'http://localhost:5000',       # Local development
        'http://127.0.0.1:5000',      # Local development (alt)
        'http://localhost:3000',       # Common dev port
        'http://localhost:8080',       # Common dev port
        'http://localhost:8000',       # Common dev port
    ],
    allow_headers=['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    supports_credentials=True  # Enable credentials for Obsidian plugin
)

# Add a more permissive CORS handler for unlisted origins (external clients)
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')

    # If origin is not in our CORS list, add headers manually (without credentials)
    if origin and origin not in [
        'app://obsidian.md',
        'http://localhost:5000',
        'http://127.0.0.1:5000',
        'http://localhost:3000',
        'http://localhost:8080',
        'http://localhost:8000'
    ]:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,Accept,Origin'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        # Note: No Access-Control-Allow-Credentials for external origins

    return response

# Global OPTIONS handler for debugging
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        print(f"PREFLIGHT REQUEST: {request.url}")
        print(f"   Origin: {request.headers.get('Origin', 'None')}")
        print(f"   Access-Control-Request-Method: {request.headers.get('Access-Control-Request-Method', 'None')}")
        print(f"   Access-Control-Request-Headers: {request.headers.get('Access-Control-Request-Headers', 'None')}")
        
        # Let Flask-CORS handle it, but log what's happening
        return None  # Continue to Flask-CORS handling
# Temporarily disable rate limiter for CORS debugging
# limiter = Limiter(
#     app=app,
#     key_func=get_remote_address,
#     default_limits=app.config['RATELIMIT_DEFAULT'].split(', ')
# )
limiter = None
print("WARNING: Rate limiter temporarily disabled for debugging")

# Initialize Talisman for HTTPS and security headers (disabled in development)
if app.config['FLASK_ENV'] == 'production':
    talisman = Talisman(app, **app.config['SECURITY_HEADERS'])

# Configure SocketIO with secure CORS settings
allowed_origins = app.config.get('CORS_ORIGINS', ['http://localhost:5000'])
# Handle wildcard for development
if '*' in allowed_origins:
    allowed_origins = '*'  # SocketIO accepts '*' as a string, not in a list
else:
    # Add localhost with port to allowed origins for development
    if 'http://localhost:5000' not in allowed_origins:
        allowed_origins.append('http://localhost:5000')
socketio = SocketIO(app, cors_allowed_origins=allowed_origins, ping_timeout=10, ping_interval=5)

# Register authentication blueprint
app.register_blueprint(auth_bp)
print("Auth blueprint registered")

# Debug: Print all registered routes
print("All registered routes:")
for rule in app.url_map.iter_rules():
    print(f"   {rule.methods} {rule.rule}")
print()

# Register plugin API blueprint
from api_compatibility import plugin_api
app.register_blueprint(plugin_api)

# Register dice roll API blueprint
from dice.routes import dice_api
app.register_blueprint(dice_api)
print("Dice API blueprint registered at /api/dice")

# Register dice request API blueprint
from dice.request_routes import dice_request_api
app.register_blueprint(dice_request_api)
print("Dice Request API blueprint registered at /api/dice/requests")

# Register simple chat API blueprint
from dice.simple_chat_routes import simple_chat_api
app.register_blueprint(simple_chat_api)
print("Simple Chat API blueprint registered at /api/chat")

# Serve static files for dice chat interface
@app.route('/dice-chat')
def dice_chat_demo():
    """Serve the simple dice chat demo interface"""
    return send_from_directory('dice/frontend', 'simple-demo.html')

@app.route('/dice-chat/complex')
def dice_chat_complex():
    """Serve the complex dice chat demo interface"""
    return send_from_directory('dice/frontend', 'example-client.html')

@app.route('/dice-chat/<path:filename>')
def dice_chat_static(filename):
    """Serve static files for dice chat"""
    return send_from_directory('dice/frontend', filename)

@app.route('/dice-chat-test')
def dice_chat_multi_test():
    """Serve the multi-client test interface"""
    return send_from_directory('dice/frontend', 'test-multi-client.html')

# Initialize dice request system
from dice.request_models import init_request_db
try:
    init_request_db()
    print("Dice request database initialized successfully")
except Exception as e:
    print(f"Error initializing dice request database: {e}")

# Register WebSocket handlers for dice requests
from dice.websocket_handlers import register_websocket_handlers
register_websocket_handlers(socketio)
print("Dice request WebSocket handlers registered")

# Global error handlers for security
@app.errorhandler(400)
def handle_bad_request(e):
    app.logger.warning(f"Bad request from {request.remote_addr}: {request.url}")
    return jsonify({'error': 'Invalid request'}), 400

@app.errorhandler(401)
def handle_unauthorized(e):
    app.logger.warning(f"Unauthorized access attempt from {request.remote_addr}: {request.url}")
    return jsonify({'error': 'Authentication required'}), 401

@app.errorhandler(403)
def handle_forbidden(e):
    app.logger.warning(f"Forbidden access attempt from {request.remote_addr}: {request.url}")
    return jsonify({'error': 'Access denied'}), 403

@app.errorhandler(404)
def handle_not_found(e):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(429)
def handle_rate_limit(e):
    app.logger.warning(f"Rate limit exceeded from {request.remote_addr}: {request.url}")
    return jsonify({'error': 'Rate limit exceeded'}), 429

@app.errorhandler(500)
def handle_internal_error(e):
    app.logger.error(f"Internal server error: {e}", exc_info=True)
    if app.debug:
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    return jsonify({'error': 'Internal server error'}), 500

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Configure Flask-Login to return JSON for API endpoints
@login_manager.unauthorized_handler
def unauthorized_callback():
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Authentication required'}), 401
    return redirect(url_for('auth.login', next=request.url))

# Store game instances per session (will be moved to database eventually)
games = {}

# Store map session metadata (for session names, types, etc.)
map_sessions = {}

# Create database tables
with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully")
    except Exception as e:
        app.logger.error(f"Error creating database tables: {e}")
        if app.debug:
            print(f"Error creating database tables: {e}")

# Custom logging handler to send logs to connected clients
class SocketIOLogHandler(logging.Handler):
    def emit(self, record):
        try:
            log_entry = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'level': record.levelname.lower(),
                'message': self.format(record),
                'module': record.module
            }
            # Send to all connected clients
            socketio.emit('server_log', log_entry)
        except:
            pass  # Prevent logging errors from breaking the app

# Import and set up production logging
from logging_config import setup_logging, log_request

# Set up comprehensive logging
security_logger = setup_logging(app)
log_request(app)

# Keep SocketIO handler for real-time logs to clients
socket_handler = SocketIOLogHandler()
socket_handler.setLevel(logging.DEBUG)
socket_formatter = logging.Formatter('%(message)s')
socket_handler.setFormatter(socket_formatter)
app.logger.addHandler(socket_handler)

class WebGameSession:
    """Web-based game session"""
    def __init__(self, session_id, seed=None, player_name=None, player_color=None):
        self.session_id = session_id
        self.player_name = player_name or f"Player {session_id[-4:]}"
        self.player_color = player_color or '#FFD700'
        self.ollama = OllamaClient()
        self.gen_manager = GenerationManager(self.ollama)
        self.seed = seed if seed is not None else random.randint(1, 1000000)
        self.hex_map = HexMap(self.gen_manager, seed=self.seed, use_advanced_terrain=False, use_minecraft_biomes=True)
        # HexMap already initializes minecraft_biome_gen in its constructor
        # Don't call initialize_map() - players should only see master's hexes
        self.hex_map.current_position = (0, 0, 0)  # Default starting position
        self.created_at = datetime.now()
        
    def get_map_data(self):
        """Get current map data for client"""
        hexes = []
        total_hexes = len(self.hex_map.hexes)
        visible_count = 0
        for (q, r, s), hex_obj in self.hex_map.hexes.items():
            if hex_obj.visible:
                visible_count += 1
                hexes.append({
                    'q': q, 'r': r, 's': s,
                    'terrain': getattr(hex_obj, 'terrain', 'unknown'),
                    'biome': getattr(hex_obj, 'biome', 'temperate'),
                    'explored': getattr(hex_obj, 'explored', False),
                    'visible': getattr(hex_obj, 'visible', True),
                    'has_location': getattr(hex_obj, 'has_location', False),
                    'location_name': getattr(hex_obj, 'location_name', ''),
                    'elevation': getattr(hex_obj, 'elevation', 0),
                    'description': getattr(hex_obj, 'description', 'An unexplored hex.')
                })
        
        print(f"get_map_data: returning {len(hexes)} visible hexes out of {total_hexes} total hexes")
        if hexes:
            print(f"Sample visible hex: {hexes[0]}")
        else:
            print("No visible hexes to return!")
        
        current_pos = self.hex_map.current_position
        try:
            travel_data = self.hex_map.travel_system.to_dict()
        except:
            travel_data = {}
        
        return {
            'hexes': hexes,
            'current_position': {'q': current_pos[0], 'r': current_pos[1], 's': current_pos[2]},
            'seed': self.seed,
            'travel_data': travel_data,
            'transport_modes': TRANSPORTATION_MODES,
            'north_direction': getattr(self.hex_map, 'north_direction', 0)
        }
    
    def move_to(self, q, r, s):
        """Move to a new hex position with on-demand hex generation"""
        new_pos = (q, r, s)
        
        # Generate/load current hex if it doesn't exist
        if new_pos not in self.hex_map.hexes:
            self._generate_hex_on_demand(q, r, s)
        
        # Only allow movement if hex exists or was successfully generated
        if new_pos in self.hex_map.hexes:
            old_pos = self.hex_map.current_position
            self.hex_map.current_position = new_pos
            
            # Update travel system position if it has the method
            if hasattr(self.hex_map.travel_system, 'move_to'):
                self.hex_map.travel_system.move_to(new_pos)
            elif hasattr(self.hex_map.travel_system, 'current_position'):
                self.hex_map.travel_system.current_position = new_pos
            
            # Mark current hex as explored and visible
            current_hex = self.hex_map.hexes[new_pos]
            current_hex.explored = True
            current_hex.visible = True
            
            # Generate and reveal neighbors on-demand
            neighbors = self.hex_map.coords.get_neighbors(*new_pos)
            for nq, nr, ns in neighbors:
                neighbor_pos = (nq, nr, ns)
                
                # Generate neighbor hex if it doesn't exist
                if neighbor_pos not in self.hex_map.hexes:
                    self._generate_hex_on_demand(nq, nr, ns)
                
                # Make neighbor visible if it exists
                if neighbor_pos in self.hex_map.hexes:
                    self.hex_map.hexes[neighbor_pos].visible = True
            
            return True
        return False
    
    def _generate_hex_on_demand(self, q, r, s):
        """Generate a single hex on-demand using the hex map's generation system"""
        try:
            # First try to load from generator data if available
            if hasattr(self, 'generator_map_data'):
                loaded_hex = self._load_hex_from_generator(q, r, s)
                if loaded_hex:
                    return loaded_hex
            
            # Fallback to procedural generation
            new_hex = self.hex_map.create_hex(q, r, s)
            if new_hex:
                new_hex.visible = False  # Start invisible, will be made visible when revealed
                new_hex.explored = False
                self.hex_map.hexes[(q, r, s)] = new_hex
                return new_hex
        except Exception as e:
            print(f"Error generating hex ({q}, {r}, {s}): {e}")
        return None
    
    def _load_hex_from_generator(self, q, r, s):
        """Load a specific hex from generator data if it exists"""
        if not hasattr(self, 'generator_map_data'):
            app.logger.debug(f"No generator map data available for hex ({q}, {r}, {s})")
            return None
            
        app.logger.debug(f"Searching for hex ({q}, {r}, {s}) in {len(self.generator_map_data)} generator hexes")
        
        # Find the hex in generator data
        for hex_data in self.generator_map_data:
            if hex_data['q'] == q and hex_data['r'] == r and hex_data['s'] == s:
                try:
                    from core.hex import Hex
                    app.logger.info(f"FOUND hex ({q}, {r}, {s}) in generator data: terrain={hex_data.get('terrain', 'unknown')}")
                    hex_obj = Hex.from_dict(hex_data)
                    hex_obj.visible = False  # Start invisible
                    hex_obj.explored = False
                    self.hex_map.hexes[(q, r, s)] = hex_obj
                    app.logger.info(f"Successfully loaded hex ({q}, {r}, {s}) with terrain: {hex_obj.terrain}")
                    return hex_obj
                except Exception as e:
                    app.logger.error(f"Error loading hex from generator data ({q}, {r}, {s}): {e}")
                    import traceback
                    traceback.print_exc()
                break
        print(f"Hex ({q}, {r}, {s}) not found in generator data. Generator has {len(self.generator_map_data)} hexes")
        return None

@app.route('/')
def index():
    """Main menu page"""
    return render_template('index.html')

@app.route('/game')
@login_required
def game():
    """Game page - requires authentication"""
    return render_template('game.html')

@app.route('/generator')
@login_required  
def generator():
    """Map Generator page - requires authentication"""
    if not current_user.is_game_master():
        return render_template('error.html', 
                             error='Access Denied',
                             message='Only Game Masters can access the generator'), 403
    import time
    return render_template('generator.html', cache_bust=int(time.time()))

@app.route('/api/create_map_session', methods=['POST'])
@login_required
def create_map_session():
    """Create a new map session in the generator"""
    try:
        # Validate input data
        validated_data, error_response = validate_request_data(CreateMapSessionSchema, request.json or {})
        if error_response:
            return jsonify(error_response), 400
        
        seed = validated_data.get('seed') or random.randint(1, 1000000)
        session_name = sanitize_string(validated_data.get('name', f'Map_{seed}'))
        
        # Create unique session ID for map
        map_session_id = f"map_{seed}_{random.randint(1000, 9999)}"
        
        # Store in global games dict as a special type
        if map_session_id not in games:
            games[map_session_id] = {
                'type': 'generator',
                'name': session_name,
                'seed': seed,
                'created_at': datetime.now().isoformat(),
                'hexes': [],
                'players': {}  # Track player positions
            }
        
        # Also store metadata in map_sessions
        map_sessions[map_session_id] = {
            'session_name': session_name,
            'session_type': 'generator',  # Default type for new sessions
            'seed': seed,
            'created_at': datetime.now(),
            'last_updated': datetime.now(),
            'creator_id': current_user.id
        }
        
        return jsonify({
            'success': True,
            'session_id': map_session_id,
            'name': session_name,
            'seed': seed
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/list_sessions', methods=['GET'])
@login_required
# # @limiter.limit("30 per minute")  # Temporarily disabled for debugging  # Temporarily disabled for debugging
def list_sessions():
    """List all available map sessions"""
    try:
        session_list = []
        for session_id, session_data in games.items():
            if isinstance(session_data, dict) and session_data.get('type') == 'generator':
                # Get additional metadata from map_sessions if available
                meta_data = map_sessions.get(session_id, {})
                
                session_list.append({
                    'id': session_id,
                    'name': session_data.get('name', 'Unnamed'),
                    'seed': session_data.get('seed', 0),
                    'created_at': session_data.get('created_at', ''),
                    'hex_count': len(session_data.get('hexes', [])),
                    'session_name': meta_data.get('session_name', session_data.get('name', 'Unnamed')),
                    'session_type': meta_data.get('session_type', 'generator'),
                    'last_updated': meta_data.get('last_updated', session_data.get('created_at', ''))
                })
        
        return jsonify({
            'success': True,
            'sessions': session_list
        })
        
    except Exception as e:
        app.logger.error(f"Error listing sessions: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to retrieve sessions'}), 500

@app.route('/api/load_map_session/<session_id>', methods=['GET'])
@token_required
# # @limiter.limit("30 per minute")  # Temporarily disabled for debugging  # Temporarily disabled for debugging
def load_map_session(session_id):
    """Load an existing map session"""
    # Check regular generator sessions first
    if session_id in games and games[session_id].get('type') == 'generator':
        return jsonify({
            'success': True,
            'session': games[session_id]
        })
    # Check master sessions (stored in map_sessions)
    elif session_id in map_sessions:
        session_data = map_sessions[session_id]
        return jsonify({
            'success': True,
            'hexes': session_data.get('hexes', []),
            'seed': session_data.get('seed'),
            'session_name': session_data.get('session_name'),
            'type': session_data.get('type', 'master')
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Session not found'
        })

@app.route('/api/get_player_positions/<session_id>', methods=['GET'])
@token_required
# @limiter.limit("60 per minute")  # Temporarily disabled for debugging
def get_player_positions(session_id):
    """Get all player positions for a map session"""
    player_positions = []

    # Check if this is a master session
    if session_id in map_sessions:
        master_session = map_sessions[session_id]
        # Extract seed from master session to find players
        master_seed = master_session.get('seed')

        # For master sessions, find players who joined with the same seed
        for game_id, game_data in games.items():
            if isinstance(game_data, WebGameSession):
                # Check if player has same seed as master session
                if hasattr(game_data, 'seed') and game_data.seed == master_seed:
                    current_pos = game_data.hex_map.current_position
                    player_data = {
                        'session_id': game_id,
                        'q': current_pos[0],
                        'r': current_pos[1],
                        's': current_pos[2],
                        'name': game_data.player_name,
                        'color': game_data.player_color
                    }
                    player_positions.append(player_data)
    else:
        # Original logic for non-master sessions
        # Find all game sessions with players
        for game_id, game_data in games.items():
            if isinstance(game_data, WebGameSession):
                # Check if this game session matches the map seed
                if hasattr(game_data, 'seed'):
                    # Find the matching map session
                    for map_id, map_data in games.items():
                        if (isinstance(map_data, dict) and
                            map_data.get('type') == 'generator' and
                            map_data.get('seed') == game_data.seed):
                            # Add this player's position
                            current_pos = game_data.hex_map.current_position
                            player_positions.append({
                                'session_id': game_id,
                                'q': current_pos[0],
                                'r': current_pos[1],
                                's': current_pos[2],
                                'name': game_data.player_name,
                                'color': game_data.player_color
                            })
                            break

    return jsonify({
        'success': True,
        'players': player_positions
    })

@app.route('/api/update_player_position', methods=['POST'])
@login_required
# @limiter.limit("120 per minute")  # Temporarily disabled for debugging
def update_player_position():
    """Update a player's position"""
    # Validate input data
    validated_data, error_response = validate_request_data(UpdatePlayerPositionSchema, request.json or {})
    if error_response:
        return jsonify(error_response), 400
    
    # Get session ID from user's active session (more secure than Flask session)
    user_session_id = f"user_{current_user.id}_{session.get('session_suffix', '')}"
    if user_session_id not in games:
        return jsonify({'success': False, 'error': 'No active game session'}), 404
    
    q, r, s = validated_data['q'], validated_data['r'], validated_data['s']
    
    # Update position in game session
    game = games[user_session_id]
    if isinstance(game, WebGameSession):
        game.hex_map.current_position = (q, r, s)
    
    return jsonify({'success': True})

@app.route('/api/update_session_name', methods=['POST'])
@login_required
def update_session_name():
    """Update session name and session type"""
    try:
        # Validate input data
        validated_data, error_response = validate_request_data(UpdateSessionNameSchema, request.json or {})
        if error_response:
            return jsonify(error_response), 400
        
        session_id = sanitize_session_id(validated_data['session_id'])
        session_name = sanitize_string(validated_data['session_name'])
        
        if not session_id or not session_name:
            return jsonify({'success': False, 'error': 'Missing session ID or name'})
        
        # Check if session exists
        if session_id not in map_sessions:
            return jsonify({'success': False, 'error': 'Session not found'})
        
        # Update session name and set as master session type
        map_sessions[session_id]['session_name'] = session_name
        map_sessions[session_id]['session_type'] = 'master'  # Mark as master session
        map_sessions[session_id]['last_updated'] = datetime.now()
        
        app.logger.info("Updated session name and set as master session", extra={
            'session_id': session_id[:8] + '...',  # Truncate for privacy
            'user_id': current_user.id
        })
        
        return jsonify({
            'success': True,
            'session_name': session_name,
            'session_type': 'master'
        })
        
    except Exception as e:
        app.logger.error(f"Error updating session name: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/teleport_player', methods=['POST'])
@token_required
def teleport_player():
    """Teleport a player to a specific hex (master only)"""
    try:
        data = request.json
        session_id = data.get('session_id')
        player_name = data.get('player_name')
        target_hex = data.get('target_hex')
        
        if not session_id or not player_name or not target_hex:
            return jsonify({'success': False, 'error': 'Missing required data'})
        
        # Check if session exists and is a master session
        if session_id not in map_sessions:
            return jsonify({'success': False, 'error': 'Session not found'})
        
        session_info = map_sessions[session_id]
        if session_info.get('session_type') != 'master':
            return jsonify({'success': False, 'error': 'Only master sessions can teleport players'})
        
        # Find the target player's session
        target_session_id = None
        for sid, game in games.items():
            if isinstance(game, WebGameSession) and game.player_name == player_name:
                target_session_id = sid
                break
        
        if not target_session_id:
            return jsonify({'success': False, 'error': f'Player {player_name} not found'})
        
        # Update the player's position using move_to to properly load neighbors
        target_game = games[target_session_id]
        q, r, s = target_hex['q'], target_hex['r'], target_hex['s']
        
        # Use move_to method to properly handle hex generation and neighbor visibility
        success = target_game.move_to(q, r, s)
        
        if not success:
            return jsonify({'success': False, 'error': 'Failed to teleport to target hex'})
        
        # Emit socket event to notify the player of teleportation (similar to map_synced)
        socketio.emit('player_teleported', {
            'session_id': target_session_id,
            'q': q, 'r': r, 's': s,
            'message': f'You have been teleported to hex ({q}, {r}, {s})'
        })
        
        app.logger.info("Player teleported", extra={
            'user_id': current_user.id,
            'target_coordinates': f"({q}, {r}, {s})"
        })
        
        return jsonify({
            'success': True,
            'player': player_name,
            'new_position': {'q': q, 'r': r, 's': s}
        })
        
    except Exception as e:
        app.logger.error(f"Error during teleportation: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/generate_hex_map', methods=['POST'])
@login_required
def generate_hex_map():
    """Generate hex map using the same system as the game"""
    try:
        data = request.json
        seed = data.get('seed', random.randint(1, 1000000))
        session_id = data.get('session_id')  # Map session ID
        
        # Find the map session
        if session_id and session_id in games and games[session_id].get('type') == 'generator':
            map_session = games[session_id]
        else:
            return jsonify({'success': False, 'error': 'Invalid session ID'})
        
        # Use the same generation system as the game
        ollama = OllamaClient()
        gen_manager = GenerationManager(ollama)
        hex_map = HexMap(gen_manager, seed=seed, use_advanced_terrain=False, use_minecraft_biomes=True)
        hex_map.initialize_map()
        
        # Generate hexes efficiently using the predetermined continent locations
        # Get continent information from the biome generator
        biome_gen = hex_map.minecraft_biome_gen
        continents = biome_gen.continents if biome_gen else []
        
        # Generate only land hexes for performance - water becomes background
        for continent in continents:
            # Generate hexes only within continent radius (no ocean buffer)
            for q in range(continent.center_q - continent.radius, continent.center_q + continent.radius + 1):
                for r in range(continent.center_r - continent.radius, continent.center_r + continent.radius + 1):
                    s = -q - r
                    
                    # Check if hex is within continent bounds
                    hex_distance = max(abs(q - continent.center_q), abs(r - continent.center_r), abs(s - continent.center_s))
                    if hex_distance <= continent.radius:
                        if (q, r, s) not in hex_map.hexes:
                            new_hex = hex_map.create_hex(q, r, s)
                            # Only include non-water terrains for rendering
                            if hasattr(new_hex, 'terrain') and new_hex.terrain not in ['water', 'ocean', 'deep_ocean', 'shallow_water']:
                                new_hex.visible = True
                                hex_map.hexes[(q, r, s)] = new_hex
        
        # Convert to web format and store in map session
        hexes = []
        for (q, r, s), hex_obj in hex_map.hexes.items():
            hex_data = {
                'q': q, 'r': r, 's': s,
                'terrain': getattr(hex_obj, 'terrain', 'unknown'),
                'biome': getattr(hex_obj, 'biome', 'temperate'),
                'explored': getattr(hex_obj, 'explored', False),
                'visible': getattr(hex_obj, 'visible', True),
                'elevation': getattr(hex_obj, 'elevation', 0)
            }
            hexes.append(hex_data)
        
        # Update the map session with generated hexes
        map_session['hexes'] = hexes
        
        return jsonify({
            'success': True,
            'seed': seed,
            'hexes': hexes
        })
        
    except Exception as e:
        app.logger.error(f"Error generating map: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Map generation failed'
        }), 500

@app.route('/api/update_hex_terrain', methods=['POST'])
@login_required
# @limiter.limit("60 per minute")  # Temporarily disabled for debugging
def update_hex_terrain():
    """Update hex terrain from generator and sync to active games"""
    try:
        data = request.json
        session_id = data.get('session_id')  # Map session ID
        q, r, s = data.get('q'), data.get('r'), data.get('s')
        terrain = data.get('terrain')
        
        if not session_id or session_id not in games:
            return jsonify({'success': False, 'error': 'Invalid session ID'})
        
        map_session = games[session_id]
        if map_session.get('type') != 'generator':
            return jsonify({'success': False, 'error': 'Not a generator session'})
        
        # Update the hex in the map session
        hex_found = False
        for hex_data in map_session.get('hexes', []):
            if hex_data['q'] == q and hex_data['r'] == r and hex_data['s'] == s:
                hex_data['terrain'] = terrain
                hex_found = True
                break
        
        if not hex_found:
            # Add new hex to map session
            map_session['hexes'].append({
                'q': q, 'r': r, 's': s,
                'terrain': terrain,
                'biome': 'temperate',
                'explored': False,
                'visible': True,
                'elevation': 0
            })
        
        # Find and update all game sessions using this seed
        seed = map_session.get('seed')
        for game_id, game_data in games.items():
            if isinstance(game_data, WebGameSession) and game_data.seed == seed:
                # Update the hex in the game session
                if (q, r, s) in game_data.hex_map.hexes:
                    game_data.hex_map.hexes[(q, r, s)].terrain = terrain
                else:
                    # Create new hex in game
                    new_hex = game_data.hex_map.create_hex(q, r, s)
                    new_hex.terrain = terrain
                    new_hex.visible = True
                    game_data.hex_map.hexes[(q, r, s)] = new_hex
        
        return jsonify({'success': True})
        
    except Exception as e:
        app.logger.error(f"Error updating hex terrain: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to update terrain'}), 500

@app.route('/api/force_sync_world', methods=['POST'])
@login_required
# @limiter.limit("10 per hour")  # Temporarily disabled for debugging
def force_sync_world():
    """Force synchronization of world data from generator to all game sessions"""
    try:
        data = request.json
        session_id = data.get('session_id')  # Map session ID
        
        if not session_id or session_id not in games:
            return jsonify({'success': False, 'error': 'Invalid session ID'})
        
        map_session = games[session_id]
        if map_session.get('type') != 'generator':
            return jsonify({'success': False, 'error': 'Not a generator session'})
        
        # Get the hex data from the request (sent from frontend)
        hexes_data = data.get('hexes', [])
        north_direction = data.get('north_direction', 0)
        
        # Store the hex data in the map session for future use
        map_session['hexes'] = hexes_data
        map_session['north_direction'] = north_direction
        
        app.logger.info(f"Received {len(hexes_data)} hexes from generator for sync")
        
        # Debug: Show coordinate range of received hexes
        if hexes_data:
            all_q = [h['q'] for h in hexes_data]
            all_r = [h['r'] for h in hexes_data]
            all_s = [h['s'] for h in hexes_data]
            app.logger.info(f"Generator hex coordinate ranges: Q({min(all_q)} to {max(all_q)}), R({min(all_r)} to {max(all_r)}), S({min(all_s)} to {max(all_s)})")
            
            # Show some sample hexes
            sample_hexes = hexes_data[:5]
            for hex_data in sample_hexes:
                app.logger.info(f"Sample generator hex: ({hex_data['q']}, {hex_data['r']}, {hex_data['s']}) = {hex_data.get('terrain', 'unknown')}")
        
        # Get the seed for this map session
        seed = map_session.get('seed')
        
        synced_games = 0
        
        # Find all game sessions using this seed and sync them
        for game_id, game_data in games.items():
            if isinstance(game_data, WebGameSession) and game_data.seed == seed:
                app.logger.info(f"Syncing game session {game_id} with map session {session_id}")
                
                # Store the generator map data in the game session for on-demand loading
                game_data.generator_map_data = hexes_data
                game_data.hex_map.north_direction = north_direction
                
                app.logger.info(f"Stored {len(hexes_data)} hexes in game session {game_id} for on-demand loading")
                
                # Remember which hexes were previously explored before clearing
                previously_explored = set()
                previously_visible = set()
                for pos, hex_obj in game_data.hex_map.hexes.items():
                    if hex_obj.explored:
                        previously_explored.add(pos)
                    if hex_obj.visible:
                        previously_visible.add(pos)
                
                app.logger.info(f"Preserving {len(previously_explored)} explored hexes and {len(previously_visible)} visible hexes")
                
                # Clear current hexes to force reload from generator data
                game_data.hex_map.hexes.clear()
                
                # Get current position
                current_pos = game_data.hex_map.current_position
                
                # Reload only the previously explored and visible hexes from generator data
                hexes_to_reload = previously_explored.union(previously_visible)
                
                # Always include current position and immediate neighbors
                hexes_to_reload.add(current_pos)
                neighbors = game_data.hex_map.coords.get_neighbors(*current_pos)
                for nq, nr, ns in neighbors:
                    hexes_to_reload.add((nq, nr, ns))
                
                app.logger.info(f"Reloading {len(hexes_to_reload)} hexes from generator data")
                
                # Load all the hexes that should be available
                for q, r, s in hexes_to_reload:
                    game_data._load_hex_from_generator(q, r, s)
                
                # Restore visibility and exploration status
                for pos in previously_explored:
                    if pos in game_data.hex_map.hexes:
                        game_data.hex_map.hexes[pos].explored = True
                        game_data.hex_map.hexes[pos].visible = True
                
                for pos in previously_visible:
                    if pos in game_data.hex_map.hexes:
                        game_data.hex_map.hexes[pos].visible = True
                
                # Ensure current position is visible and explored
                if current_pos in game_data.hex_map.hexes:
                    game_data.hex_map.hexes[current_pos].visible = True
                    game_data.hex_map.hexes[current_pos].explored = True
                
                synced_games += 1
                app.logger.info(f"Successfully synced game session {game_id}")
                
                # Emit a WebSocket event to notify the game client to refresh
                socketio.emit('map_synced', {
                    'session_id': game_id,
                    'hex_count': len(hexes_data),
                    'message': 'Map data has been synced from generator'
                })
        
        return jsonify({
            'success': True,
            'synced_games': synced_games,
            'message': f'Synced {synced_games} game sessions with {len(hexes_data)} hexes'
        })
        
    except Exception as e:
        app.logger.error(f"Error forcing sync: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Synchronization failed'}), 500

@app.route('/api/test', methods=['GET'])
# @limiter.limit("10 per minute")  # Temporarily disabled for debugging
def test_api():
    """Test API endpoint"""
    return jsonify({
        'success': True,
        'message': 'API is working'
    })

@app.route('/api/new_game', methods=['POST'])
@token_required
def new_game():
    """Start a new game"""
    try:
        data = request.json
        seed = data.get('seed') if data else None
        player_name = data.get('player_name') if data else None
        player_color = data.get('player_color') if data else None
        session_id = session.get('session_id', str(random.randint(1000000, 9999999)))
        session['session_id'] = session_id
        
        print(f"Creating new game with seed: {seed}, session: {session_id}")
        
        # Check if there's an existing map session with this seed
        existing_map_session = None
        for map_id, map_data in games.items():
            if (isinstance(map_data, dict) and 
                map_data.get('type') == 'generator' and
                map_data.get('seed') == seed):
                existing_map_session = map_id
                break
        
        # Clear old game sessions with the same seed to prevent old players appearing
        sessions_to_remove = []
        for game_id, game_data in games.items():
            if (isinstance(game_data, WebGameSession) and 
                hasattr(game_data, 'seed') and game_data.seed == seed):
                sessions_to_remove.append(game_id)
        
        for old_session_id in sessions_to_remove:
            print(f"Removing old game session: {old_session_id}")
            del games[old_session_id]
        
        # Create new game session with streaming exploration
        game = WebGameSession(session_id, seed, player_name, player_color)
        
        if existing_map_session:
            # Store reference to generator map data for on-demand loading
            map_session_data = games[existing_map_session]
            game.generator_map_data = map_session_data.get('hexes', [])
            print(f"Linked to existing map session: {existing_map_session} with {len(game.generator_map_data)} hexes")
        
        # Start at origin or find a good starting position from generator data
        starting_pos = (0, 0, 0)
        if hasattr(game, 'generator_map_data') and game.generator_map_data:
            # Find a good land hex near origin
            best_hex = None
            best_distance = float('inf')
            for hex_data in game.generator_map_data:
                if hex_data.get('terrain', 'water') not in ['water', 'ocean', 'deep_ocean']:
                    q, r, s = hex_data['q'], hex_data['r'], hex_data['s']
                    distance = abs(q) + abs(r) + abs(s)
                    if distance < best_distance:
                        best_distance = distance
                        best_hex = (q, r, s)
            if best_hex:
                starting_pos = best_hex
        
        # Initialize starting area with on-demand exploration
        game._generate_hex_on_demand(*starting_pos)
        game.hex_map.current_position = starting_pos
        
        if starting_pos in game.hex_map.hexes:
            game.hex_map.hexes[starting_pos].explored = True
            game.hex_map.hexes[starting_pos].visible = True
        
        # Generate neighbors but don't explore them yet
        neighbors = game.hex_map.coords.get_neighbors(*starting_pos)
        for nq, nr, ns in neighbors:
            game._generate_hex_on_demand(nq, nr, ns)
            if (nq, nr, ns) in game.hex_map.hexes:
                game.hex_map.hexes[(nq, nr, ns)].visible = True
        
        games[session_id] = game
        
        print(f"Game created successfully")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'map_data': games[session_id].get_map_data()
        })
    except Exception as e:
        print(f"Error creating new game: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/load_game', methods=['POST'])
@login_required
def load_game():
    """Load a saved game"""
    data = request.json
    map_data = data.get('map_data')
    
    if not map_data:
        return jsonify({'success': False, 'error': 'No map data provided'})
    
    # Use authenticated user's session instead of Flask session
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    session_id = f"user_{current_user.id}_{random.randint(1000, 9999)}"
    # Store in Flask session for backward compatibility
    session['session_id'] = session_id
    
    # Create new game session and load data
    game = WebGameSession(session_id)
    
    # Load hexes
    from core.hex import Hex
    game.hex_map.hexes.clear()
    for hex_data in map_data.get('hexes', []):
        hex_obj = Hex.from_dict(hex_data)
        game.hex_map.hexes[(hex_obj.q, hex_obj.r, hex_obj.s)] = hex_obj
    
    # Load position
    if 'current_position' in map_data:
        pos = map_data['current_position']
        game.hex_map.current_position = (pos['q'], pos['r'], pos['s'])
    
    # Load travel data
    if 'travel_data' in map_data:
        game.hex_map.travel_system.load_from_data(map_data['travel_data'])
    
    games[session_id] = game
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'map_data': game.get_map_data()
    })

@app.route('/api/save_map_for_game', methods=['POST'])
@login_required
# @limiter.limit("30 per minute")  # Temporarily disabled for debugging
def save_map_for_game():
    """Save map from generator for game use"""
    try:
        data = request.json
        session_id = data.get('session_id')
        map_data = data.get('map_data')
        
        if not session_id or not map_data:
            return jsonify({'success': False, 'error': 'Missing session_id or map_data'})
        
        # Create new game session with the map data
        game = WebGameSession(session_id)
        
        # Store the generator map data as a reference for on-demand loading
        game.generator_map_data = map_data.get('hexes', [])
        print(f"Stored {len(game.generator_map_data)} hexes from generator in game session")
        
        # Debug: Show sample of generator data
        if game.generator_map_data:
            sample_hex = game.generator_map_data[0]
            print(f"Sample hex data: {sample_hex}")
        
        # Store north direction if provided
        if 'northDirection' in map_data:
            game.hex_map.north_direction = map_data['northDirection']
            print(f"Set north direction to: {map_data['northDirection']}")
        
        # Set a starting position - use first hex from generator data
        if game.generator_map_data:
            # Use the first hex as starting position to ensure it exists
            first_hex = game.generator_map_data[0]
            starting_pos = (first_hex['q'], first_hex['r'], first_hex['s'])
            print(f"Using first hex as starting position: {starting_pos}")
        else:
            starting_pos = (0, 0, 0)
        
        # Load only the starting hex and its immediate neighbors
        game._load_hex_from_generator(starting_pos[0], starting_pos[1], starting_pos[2])
        neighbors = game.hex_map.coords.get_neighbors(*starting_pos)
        for nq, nr, ns in neighbors:
            game._load_hex_from_generator(nq, nr, ns)
        
        game.hex_map.current_position = starting_pos
        if starting_pos in game.hex_map.hexes:
            game.hex_map.hexes[starting_pos].explored = True
            game.hex_map.hexes[starting_pos].visible = True
        
        games[session_id] = game
        
        return jsonify({
            'success': True,
            'message': 'Map saved for game successfully'
        })
        
    except Exception as e:
        print(f"Error saving map for game: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/get_map', methods=['GET'])
@token_required
def get_map():
    """Get current map data"""
    # Try to get session_id from query parameter first, then from Flask session
    session_id = request.args.get('session_id') or session.get('session_id')
    if not session_id or session_id not in games:
        return jsonify({'success': False, 'error': 'No active game session'})
    
    return jsonify({
        'success': True,
        'map_data': games[session_id].get_map_data()
    })

@app.route('/api/move', methods=['POST'])
@token_required
def move():
    """Move to a new hex"""
    # Try to get session_id from query parameter first, then from Flask session
    session_id = request.args.get('session_id') or session.get('session_id')
    if not session_id or session_id not in games:
        return jsonify({'success': False, 'error': 'No active game session'})
    
    data = request.json
    q, r, s = data.get('q'), data.get('r'), data.get('s')
    
    print(f"Move request to ({q}, {r}, {s}) for session {session_id}")
    
    game = games[session_id]
    success = game.move_to(q, r, s)
    
    print(f"Move success: {success}")
    
    if success:
        map_data = game.get_map_data()
        return jsonify({
            'success': True,
            'map_data': map_data
        })
    else:
        return jsonify({'success': False, 'error': 'Invalid move'})

# Movement approval system
movement_requests = {}  # Store pending movement requests

@app.route('/api/request_move', methods=['POST'])
@token_required
def request_move():
    """Request movement that needs master approval"""
    data = request.json
    session_id = data.get('session_id')
    if not session_id or session_id not in games:
        return jsonify({'success': False, 'error': 'No active game session'})
    
    q, r, s = data.get('q'), data.get('r'), data.get('s')
    
    # Get player name from auth token
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(" ")[1] if auth_header else None
    player_name = 'Unknown'
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user = User.query.get(payload['user_id'])
            if user:
                player_name = user.username
        except:
            pass
    
    # Debug logging
    app.logger.info(f"Movement request from session_id: {session_id}, player: {player_name}")
    app.logger.info(f"Available games: {list(games.keys())}")
    app.logger.info(f"Available map_sessions: {list(map_sessions.keys())}")
    
    # Find corresponding map session if this is a game session
    map_session_id = session_id
    if not session_id.startswith('map_'):
        # Look for a map session with the same seed
        game_obj = games.get(session_id)
        seed = None
        if game_obj:
            # Handle both dict and WebGameSession object formats
            if hasattr(game_obj, 'seed'):
                seed = game_obj.seed
            elif isinstance(game_obj, dict):
                seed = game_obj.get('seed')
        
        if seed:
            for ms_id, ms_data in map_sessions.items():
                if ms_data.get('seed') == seed:
                    map_session_id = ms_id
                    app.logger.info(f"Found corresponding map session: {map_session_id}")
                    break
    
    # Store movement request with both session IDs
    request_id = f"{session_id}_{player_name}_{datetime.now().timestamp()}"
    request_data = {
        'session_id': session_id,
        'map_session_id': map_session_id,  # Also store map session for website lookup
        'player_name': player_name,
        'target': (q, r, s),
        'status': 'pending',
        'timestamp': datetime.now()
    }
    
    movement_requests[request_id] = request_data
    
    # Also create an entry with map session ID for easy lookup by website
    if map_session_id != session_id:
        map_request_id = f"{map_session_id}_{player_name}_{datetime.now().timestamp()}"
        movement_requests[map_request_id] = request_data.copy()
        movement_requests[map_request_id]['session_id'] = map_session_id
    
    # Store request ID for this session/player
    if session_id not in games:
        return jsonify({'success': False, 'error': 'Session not found'})
    
    # Store the request ID for this player
    if not hasattr(games[session_id], 'player_requests'):
        games[session_id].player_requests = {}
    games[session_id].player_requests[player_name] = request_id
    
    return jsonify({'success': True, 'request_id': request_id})

@app.route('/api/check_movement_status', methods=['GET'])
@token_required
def check_movement_status():
    """Check if movement request was approved"""
    session_id = request.args.get('session_id')
    if not session_id or session_id not in games:
        return jsonify({'success': False, 'error': 'No active game session'})
    
    # Get player name from auth token
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(" ")[1] if auth_header else None
    player_name = 'Unknown'
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user = User.query.get(payload['user_id'])
            if user:
                player_name = user.username
        except:
            pass
    
    # Check if player has a pending request
    if hasattr(games[session_id], 'player_requests') and player_name in games[session_id].player_requests:
        request_id = games[session_id].player_requests[player_name]
        if request_id in movement_requests:
            status = movement_requests[request_id]['status']
            if status != 'pending':
                # Clean up the request
                del movement_requests[request_id]
                del games[session_id].player_requests[player_name]
            return jsonify({'success': True, 'status': status})
    
    return jsonify({'success': True, 'status': 'none'})

@app.route('/api/cancel_movement_request', methods=['POST'])
@token_required
def cancel_movement_request():
    """Cancel a pending movement request"""
    data = request.json
    session_id = data.get('session_id')
    if not session_id or session_id not in games:
        return jsonify({'success': False, 'error': 'No active game session'})
    
    # Get player name from auth token
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(" ")[1] if auth_header else None
    player_name = 'Unknown'
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user = User.query.get(payload['user_id'])
            if user:
                player_name = user.username
        except:
            pass
    
    # Cancel the request
    if hasattr(games[session_id], 'player_requests') and player_name in games[session_id].player_requests:
        request_id = games[session_id].player_requests[player_name]
        if request_id in movement_requests:
            del movement_requests[request_id]
        del games[session_id].player_requests[player_name]
    
    return jsonify({'success': True})

@app.route('/api/session/<session_id>', methods=['GET'])
@login_required
def get_session_info(session_id):
    """Get session information and check if user is master"""
    if session_id not in map_sessions:
        return jsonify({'success': False, 'error': 'Session not found'})
    
    session_info = map_sessions[session_id]
    
    # Handle legacy sessions that don't have creator_id
    creator_id = session_info.get('creator_id', current_user.id)  # Default to current user for legacy sessions
    is_master = creator_id == current_user.id
    
    return jsonify({
        'success': True,
        'session_id': session_id,
        'session_name': session_info.get('session_name', 'Unnamed Session'),
        'is_master': is_master,
        'creator_id': creator_id
    })

@app.route('/api/get_movement_requests', methods=['GET'])
@token_required
def get_movement_requests():
    """Get all pending movement requests for a session (master only)"""
    session_id = request.args.get('session_id')
    if not session_id or session_id not in map_sessions:
        return jsonify({'success': False, 'error': 'Session not found'})

    # Get current user from token or session
    user = getattr(request, 'current_token_user', None) or current_user

    # Check if user is the master
    creator_id = map_sessions[session_id].get('creator_id', user.id if hasattr(user, 'id') else None)
    if creator_id != (user.id if hasattr(user, 'id') else None):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    # Get all pending requests for this session
    pending = []
    for request_id, req in movement_requests.items():
        # Check both session_id and map_session_id fields
        req_session = req.get('session_id')
        req_map_session = req.get('map_session_id', req_session)
        if (req_session == session_id or req_map_session == session_id) and req['status'] == 'pending':
            pending.append({
                'request_id': request_id,
                'player_name': req['player_name'],
                'target': req['target'],
                'timestamp': req['timestamp'].isoformat()
            })
    
    return jsonify({'success': True, 'requests': pending})

@app.route('/api/approve_movement', methods=['POST'])
@token_required
def approve_movement():
    """Approve a movement request (master only)"""
    data = request.json
    request_id = data.get('request_id')
    session_id = data.get('session_id')
    
    if not session_id or session_id not in map_sessions:
        return jsonify({'success': False, 'error': 'Session not found'})
    
    # Get current user from token or session
    user = getattr(request, 'current_token_user', None) or current_user

    # Check if user is the master
    creator_id = map_sessions[session_id].get('creator_id', user.id if hasattr(user, 'id') else None)
    if creator_id != (user.id if hasattr(user, 'id') else None):
        return jsonify({'success': False, 'error': 'Not authorized'})
    
    if request_id in movement_requests:
        movement_requests[request_id]['status'] = 'approved'
        
        # Actually move the player
        req = movement_requests[request_id]
        if req['session_id'] in games:
            game = games[req['session_id']]
            q, r, s = req['target']
            success = game.move_to(q, r, s)
            
            return jsonify({'success': success})
    
    return jsonify({'success': False, 'error': 'Request not found'})

@app.route('/api/decline_movement', methods=['POST'])
@token_required
def decline_movement():
    """Decline a movement request (master only)"""
    data = request.json
    request_id = data.get('request_id')
    session_id = data.get('session_id')

    if not session_id or session_id not in map_sessions:
        return jsonify({'success': False, 'error': 'Session not found'})

    # Get current user from token or session
    user = getattr(request, 'current_token_user', None) or current_user

    # Check if user is the master
    creator_id = map_sessions[session_id].get('creator_id', user.id if hasattr(user, 'id') else None)
    if creator_id != (user.id if hasattr(user, 'id') else None):
        return jsonify({'success': False, 'error': 'Not authorized'})

    if request_id in movement_requests:
        movement_requests[request_id]['status'] = 'declined'
        return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Request not found'})

# Master-specific API endpoints
@app.route('/api/master/session', methods=['GET'])
@token_required
def get_master_session():
    """Get or check for existing master session"""
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(" ")[1] if auth_header else None

    if not token:
        return jsonify({'success': False, 'error': 'No token provided'}), 401

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(payload['user_id'])

        if not user or user.role != 'game_master':
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        # Find existing master session
        for session_id, session_info in map_sessions.items():
            if session_info.get('creator_id') == user.id and session_info.get('type') == 'master':
                return jsonify({
                    'success': True,
                    'session_id': session_id,
                    'seed': session_info.get('seed'),
                    'session_name': session_info.get('session_name', 'Master Session')
                })

        return jsonify({'success': True, 'session_id': None})
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

@app.route('/api/master/create_session', methods=['POST'])
@token_required
def create_master_session():
    """Create a new master session"""
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(" ")[1] if auth_header else None

    if not token:
        return jsonify({'success': False, 'error': 'No token provided'}), 401

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(payload['user_id'])

        if not user or user.role != 'game_master':
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        data = request.json
        session_name = data.get('session_name', 'Master Session')
        seed = data.get('seed', 12345)  # Default seed is now 12345

        # Create new master session
        session_id = f"master_{user.id}_{int(time.time())}"

        map_sessions[session_id] = {
            'creator_id': user.id,
            'session_name': session_name,
            'seed': seed,
            'type': 'master',
            'created_at': datetime.now().isoformat(),
            'hexes': []
        }

        return jsonify({
            'success': True,
            'session_id': session_id,
            'seed': seed
        })
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

@app.route('/api/master/update_terrain', methods=['POST'])
@token_required
def update_master_terrain():
    """Update terrain data for master session"""
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(" ")[1] if auth_header else None

    if not token:
        return jsonify({'success': False, 'error': 'No token provided'}), 401

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(payload['user_id'])

        if not user or user.role != 'game_master':
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        data = request.json
        session_id = data.get('session_id')
        hexes = data.get('hexes', [])

        if session_id not in map_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404

        if map_sessions[session_id].get('creator_id') != user.id:
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        # Update hexes in session
        existing_hexes = map_sessions[session_id].get('hexes', [])

        # Convert to dict for easier updating
        hex_dict = {(h['q'], h['r']): h for h in existing_hexes}

        # Update with new hex data
        for hex_data in hexes:
            key = (hex_data['q'], hex_data['r'])
            if key in hex_dict:
                hex_dict[key]['terrain'] = hex_data['terrain']
            else:
                hex_dict[key] = hex_data

        # Convert back to list
        map_sessions[session_id]['hexes'] = list(hex_dict.values())

        return jsonify({'success': True})
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

@app.route('/api/master/update_session', methods=['POST'])
@token_required
def update_master_session():
    """Update master session settings"""
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(" ")[1] if auth_header else None

    if not token:
        return jsonify({'success': False, 'error': 'No token provided'}), 401

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(payload['user_id'])

        if not user or user.role != 'game_master':
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        data = request.json
        session_id = data.get('session_id')
        session_name = data.get('session_name')

        if session_id not in map_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404

        if map_sessions[session_id].get('creator_id') != user.id:
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        if session_name:
            map_sessions[session_id]['session_name'] = session_name

        return jsonify({'success': True})
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

@app.route('/api/master/set_seed', methods=['POST'])
@token_required
def set_master_seed():
    """Set seed for master session and regenerate map"""
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(" ")[1] if auth_header else None

    if not token:
        return jsonify({'success': False, 'error': 'No token provided'}), 401

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(payload['user_id'])

        if not user or user.role != 'game_master':
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        data = request.json
        session_id = data.get('session_id')
        seed = data.get('seed')

        if session_id not in map_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404

        if map_sessions[session_id].get('creator_id') != user.id:
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        # Update seed and regenerate basic map
        map_sessions[session_id]['seed'] = seed

        # Generate basic hex map (simplified for now)
        hexes = []
        for q in range(-10, 11):
            for r in range(-10, 11):
                if abs(q + r) <= 10:
                    hexes.append({
                        'q': q,
                        'r': r,
                        's': -(q + r),
                        'terrain': 'plains'  # Default terrain
                    })

        map_sessions[session_id]['hexes'] = hexes

        return jsonify({'success': True})
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

@app.route('/api/master/load_map', methods=['POST'])
@token_required
def load_master_map():
    """Load a map from JSON data"""
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(" ")[1] if auth_header else None

    if not token:
        return jsonify({'success': False, 'error': 'No token provided'}), 401

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(payload['user_id'])

        if not user or user.role != 'game_master':
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        data = request.json
        session_id = data.get('session_id')
        map_data = data.get('map_data')

        if session_id not in map_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404

        if map_sessions[session_id].get('creator_id') != user.id:
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        # Load map data
        if isinstance(map_data, dict):
            map_sessions[session_id]['hexes'] = map_data.get('hexes', [])
            map_sessions[session_id]['seed'] = map_data.get('seed', map_sessions[session_id].get('seed'))

        return jsonify({'success': True})
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

@app.route('/api/master/copy_to_game', methods=['POST'])
@token_required
def copy_master_to_game():
    """Copy master map to game sessions"""
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(" ")[1] if auth_header else None

    if not token:
        return jsonify({'success': False, 'error': 'No token provided'}), 401

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(payload['user_id'])

        if not user or user.role != 'game_master':
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        data = request.json
        session_id = data.get('session_id')

        if session_id not in map_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404

        if map_sessions[session_id].get('creator_id') != user.id:
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        # Copy map data to all game sessions with same seed
        master_seed = map_sessions[session_id].get('seed')
        master_hexes = map_sessions[session_id].get('hexes', [])

        copied_count = 0
        for game_id, game_data in games.items():
            if isinstance(game_data, WebGameSession):
                if game_data.map_seed == master_seed:
                    # Update game map data
                    for hex_data in master_hexes:
                        game_data.map.set_hex_terrain(hex_data['q'], hex_data['r'], hex_data.get('terrain', 'plains'))
                    copied_count += 1

        return jsonify({'success': True, 'copied_to': copied_count})
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

@app.route('/api/master/generate_terrain', methods=['POST'])
@token_required
def generate_master_terrain():
    """Generate terrain for master session using the same system as the website"""
    auth_header = request.headers.get('Authorization')
    token = auth_header.split(" ")[1] if auth_header else None

    if not token:
        return jsonify({'success': False, 'error': 'No token provided'}), 401

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(payload['user_id'])

        if not user or user.role != 'game_master':
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        data = request.json
        session_id = data.get('session_id')
        seed = data.get('seed')

        if not session_id or session_id not in map_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404

        if map_sessions[session_id].get('creator_id') != user.id:
            return jsonify({'success': False, 'error': 'Not authorized'}), 403

        # Use the same generation system as the website
        from generation.ollama_client import OllamaClient
        from generation.manager import GenerationManager
        from core.map import HexMap
        import random

        if not seed:
            seed = 12345  # Default seed for terrain generation

        # Initialize generation system
        ollama = OllamaClient()
        gen_manager = GenerationManager(ollama)
        hex_map = HexMap(gen_manager, seed=seed, use_advanced_terrain=False, use_minecraft_biomes=True)
        hex_map.initialize_map()

        # Generate hexes efficiently using predetermined continent locations
        generated_hexes = []
        biome_gen = hex_map.minecraft_biome_gen
        continents = biome_gen.continents if biome_gen else []

        # Generate only land hexes for performance - water becomes background
        for continent in continents:  # Generate all continents like the website
            for q in range(continent.center_q - continent.radius, continent.center_q + continent.radius + 1):
                for r in range(continent.center_r - continent.radius, continent.center_r + continent.radius + 1):
                    s = -(q + r)

                    # Check if hex is within continent radius
                    distance = max(abs(q - continent.center_q), abs(r - continent.center_r), abs(s - continent.center_s))
                    if distance <= continent.radius:
                        # Generate hex
                        hex_obj = hex_map.create_hex(q, r, s)
                        if hex_obj and hex_obj.terrain != 'water':
                            # Convert cube coordinates (q, r, s) to offset coordinates (x, y)
                            # For flat-top hexagons using axial coordinates
                            x = q
                            y = r

                            generated_hexes.append({
                                'q': q, 'r': r, 's': s,  # Keep original for reference
                                'x': x, 'y': y,          # Offset coordinates for client
                                'terrain': hex_obj.terrain,
                                'biome': hex_obj.biome,
                                'temperature': getattr(hex_obj, 'temperature', 0.5),
                                'humidity': getattr(hex_obj, 'humidity', 0.5),
                                'elevation': getattr(hex_obj, 'elevation', 0.5),
                                'description': getattr(hex_obj, 'description', f"A {hex_obj.terrain} area."),
                                'explored': True  # Master view hexes are always explored (black borders)
                            })

                        # Generate all hexes like the website - no artificial limits

        # Update map session with generated hexes and seed
        map_sessions[session_id]['hexes'] = generated_hexes
        map_sessions[session_id]['seed'] = seed

        return jsonify({
            'success': True,
            'hex_count': len(generated_hexes),
            'seed': seed,
            'hexes': generated_hexes
        })

    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate_description', methods=['POST'])
@login_required
# @limiter.limit("30 per minute")  # Temporarily disabled for debugging
def generate_description():
    """Generate hex description using AI"""
    session_id = session.get('session_id')
    if not session_id or session_id not in games:
        return jsonify({'success': False, 'error': 'No active game session'})
    
    data = request.json
    q, r, s = data.get('q'), data.get('r'), data.get('s')
    
    game = games[session_id]
    hex_obj = game.hex_map.hexes.get((q, r, s))
    
    if not hex_obj:
        return jsonify({'success': False, 'error': 'Hex not found'})
    
    # Generate description
    try:
        if not hex_obj.description or hex_obj.description == "An unexplored hex.":
            description = game.gen_manager.generate_hex_description(hex_obj)
            hex_obj.description = description
        
        return jsonify({
            'success': True,
            'description': hex_obj.description
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'description': f"A {hex_obj.terrain} area with {hex_obj.biome} characteristics."
        })


# Socket.IO events for real-time updates
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    session_id = session.get('session_id')
    # Keep game in memory for reconnection
    print(f'Client disconnected: {session_id}')

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    print("Starting Hex Explorer Web Server...")
    print("Open http://localhost:5000 in your browser")
    print("Or access from LAN using your local IP address on port 5000")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)