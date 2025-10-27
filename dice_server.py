"""
Standalone Dice Roll Server
Independent server that runs only the dice roll API
Shares authentication with the main server
"""

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import os
import sys
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the dice API blueprint and auth database
from dice.routes import dice_api
from models import db, User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dice-server-secret-key'),
    SQLALCHEMY_DATABASE_URI=os.environ.get('AUTH_DATABASE_URL', 'sqlite:///auth.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    DICE_DATABASE_URI='sqlite:///dice_rolls.db',

    # Server configuration
    SERVER_NAME=None,  # Allow any host
    PREFERRED_URL_SCHEME='http',

    # Security settings
    JSONIFY_PRETTYPRINT_REGULAR=True,
    JSON_SORT_KEYS=False,

    # Rate limiting
    RATELIMIT_STORAGE_URI='memory://',
    RATELIMIT_DEFAULT='100 per minute, 1000 per hour',
    RATELIMIT_HEADERS_ENABLED=True,

    # CORS settings
    CORS_ORIGINS=['*'],  # Allow all origins for dice API
    CORS_ALLOW_HEADERS=['Content-Type', 'Authorization', 'X-Requested-With'],
    CORS_ALLOW_METHODS=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    CORS_SUPPORTS_CREDENTIALS=False  # No credentials for standalone server
)

# Initialize extensions
db.init_app(app)

# Initialize CORS
cors = CORS(app,
    origins=app.config['CORS_ORIGINS'],
    allow_headers=app.config['CORS_ALLOW_HEADERS'],
    methods=app.config['CORS_ALLOW_METHODS'],
    supports_credentials=app.config['CORS_SUPPORTS_CREDENTIALS']
)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=app.config['RATELIMIT_DEFAULT'].split(', ')
)

# Register dice API blueprint
app.register_blueprint(dice_api)

# Root endpoint
@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API information"""
    return jsonify({
        'service': 'Dice Roll API Server',
        'version': '1.0.0',
        'status': 'running',
        'timestamp': datetime.utcnow().isoformat(),
        'endpoints': {
            'roll': '/api/dice/roll',
            'bulk_roll': '/api/dice/roll/bulk',
            'history': '/api/dice/history',
            'statistics': '/api/dice/statistics',
            'templates': '/api/dice/templates',
            'parse': '/api/dice/parse',
            'health': '/api/dice/health',
            'docs': '/api/docs'
        }
    }), 200

# API documentation endpoint
@app.route('/api/docs', methods=['GET'])
def api_docs():
    """Return API documentation"""
    docs = {
        'title': 'Dice Roll API Documentation',
        'version': '1.0.0',
        'base_url': '/api/dice',
        'authentication': {
            'type': 'Bearer JWT',
            'header': 'Authorization: Bearer <token>',
            'optional_endpoints': ['/roll', '/history', '/parse', '/health'],
            'required_endpoints': ['/statistics', '/templates']
        },
        'endpoints': [
            {
                'path': '/roll',
                'method': 'POST',
                'description': 'Roll dice based on expression',
                'authentication': 'optional',
                'body': {
                    'expression': 'string (required) - e.g., "3d6+2"',
                    'description': 'string (optional)',
                    'advantage': 'boolean (optional)',
                    'disadvantage': 'boolean (optional)',
                    'campaign_id': 'string (optional)',
                    'session_id': 'string (optional)'
                },
                'response': {
                    'id': 'integer',
                    'expression': 'string',
                    'raw_rolls': 'object',
                    'modifiers': 'array',
                    'total': 'integer',
                    'is_critical': 'boolean',
                    'is_fumble': 'boolean',
                    'breakdown': 'string'
                }
            },
            {
                'path': '/roll/bulk',
                'method': 'POST',
                'description': 'Roll the same expression multiple times',
                'authentication': 'optional',
                'body': {
                    'expression': 'string (required)',
                    'count': 'integer (1-100, default 1)',
                    'description': 'string (optional)'
                }
            },
            {
                'path': '/history',
                'method': 'GET',
                'description': 'Get roll history',
                'authentication': 'optional',
                'query_params': {
                    'limit': 'integer (max 100, default 50)',
                    'offset': 'integer (default 0)',
                    'campaign_id': 'string (optional)'
                }
            },
            {
                'path': '/statistics',
                'method': 'GET',
                'description': 'Get user roll statistics',
                'authentication': 'required'
            },
            {
                'path': '/templates',
                'method': 'GET/POST',
                'description': 'Manage roll templates',
                'authentication': 'required for POST'
            },
            {
                'path': '/templates/<id>/roll',
                'method': 'POST',
                'description': 'Roll using a template',
                'authentication': 'optional'
            },
            {
                'path': '/parse',
                'method': 'POST',
                'description': 'Parse and validate expression without rolling',
                'authentication': 'none',
                'body': {
                    'expression': 'string (required)'
                }
            }
        ],
        'dice_notation': {
            'basic': 'd20, 3d6, 2d10',
            'modifiers': '3d6+2, d20-1',
            'keep_drop': '4d6kh3 (keep highest 3), 2d20kl1 (keep lowest 1)',
            'reroll': '4d6r1 (reroll 1s)',
            'exploding': '3d6! (explode on max)',
            'complex': '3d6+2d8+5'
        },
        'examples': {
            'simple_roll': {
                'request': 'POST /api/dice/roll',
                'body': '{"expression": "3d6+2"}',
                'response': '{"total": 12, "breakdown": "3d6=[4,3,3]=10 +2 = 12"}'
            },
            'advantage': {
                'request': 'POST /api/dice/roll',
                'body': '{"expression": "d20", "advantage": true}',
                'response': '{"total": 17, "breakdown": "2d20kh1=[17,11]=17 = 17"}'
            }
        }
    }
    return jsonify(docs), 200

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    """Health check for monitoring"""
    try:
        # Check database connectivity
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except:
        db_status = 'unhealthy'

    return jsonify({
        'status': 'healthy' if db_status == 'healthy' else 'degraded',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {
            'api': 'healthy',
            'auth_database': db_status,
            'dice_database': 'healthy'  # Dice DB is created on demand
        }
    }), 200 if db_status == 'healthy' else 503

# Error handlers
@app.errorhandler(400)
def handle_bad_request(e):
    logger.warning(f"Bad request: {request.url}")
    return jsonify({'error': 'Invalid request'}), 400

@app.errorhandler(401)
def handle_unauthorized(e):
    logger.warning(f"Unauthorized: {request.url}")
    return jsonify({'error': 'Authentication required'}), 401

@app.errorhandler(403)
def handle_forbidden(e):
    logger.warning(f"Forbidden: {request.url}")
    return jsonify({'error': 'Access denied'}), 403

@app.errorhandler(404)
def handle_not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(429)
def handle_rate_limit(e):
    logger.warning(f"Rate limit exceeded: {request.remote_addr}")
    return jsonify({'error': 'Rate limit exceeded', 'message': str(e.description)}), 429

@app.errorhandler(500)
def handle_internal_error(e):
    logger.error(f"Internal error: {e}", exc_info=True)
    return jsonify({'error': 'Internal server error'}), 500

# Request logging
@app.before_request
def log_request():
    """Log incoming requests"""
    if request.path != '/health':  # Skip health check logging
        logger.info(f"{request.method} {request.path} from {request.remote_addr}")

@app.after_request
def log_response(response):
    """Log response status"""
    if request.path != '/health':  # Skip health check logging
        logger.info(f"Response: {response.status_code} for {request.method} {request.path}")

    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    return response

# Create database tables on startup
with app.app_context():
    try:
        # Create auth database tables (shared with main server)
        db.create_all()
        logger.info("Auth database connected successfully")

        # Initialize dice database
        from dice.models import init_dice_db
        init_dice_db()
        logger.info("Dice database initialized successfully")

    except Exception as e:
        logger.error(f"Database initialization error: {e}")

def main():
    """Run the standalone dice server"""
    port = int(os.environ.get('DICE_SERVER_PORT', 5001))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'

    logger.info(f"Starting Dice Roll API Server on port {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Auth database: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # Run the server
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=debug
    )

if __name__ == '__main__':
    main()