"""
Authentication routes and utilities for Hex Explorer
"""
import re
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from marshmallow import Schema, fields, validate, ValidationError
from email_validator import validate_email, EmailNotValidError
# CSRF protection exempt for auth endpoints

from models import db, User, LoginAttempt
from functools import wraps
import jwt

# Input validation schemas (moved to top to avoid import issues)
class RegisterSchema(Schema):
    username = fields.Str(
        required=True, 
        validate=[
            validate.Length(min=3, max=20),
            validate.Regexp(r'^[a-zA-Z0-9_]+$', error='Username can only contain letters, numbers, and underscores')
        ]
    )
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))
    role = fields.Str(validate=validate.OneOf(['player', 'game_master']), missing='player')
    color = fields.Str(
        validate=validate.Regexp(r'^#[0-9a-fA-F]{6}$', error='Color must be a valid hex color'),
        missing='#3498db'
    )

class LoginSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=1, max=80))
    password = fields.Str(required=True, validate=validate.Length(min=1, max=128))

class PasswordChangeSchema(Schema):
    current_password = fields.Str(required=True)
    new_password = fields.Str(required=True, validate=validate.Length(min=8, max=128))

# Token authentication decorator for API endpoints
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import current_app
        token = request.headers.get('Authorization')
        
        if not token:
            # Fall back to session-based authentication for web interface
            if current_user.is_authenticated:
                return f(*args, **kwargs)
            return jsonify({'error': 'Authentication required'}), 401
        
        # Remove "Bearer " prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
            
        try:
            # Decode JWT token
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user = User.query.get(payload['user_id'])
            
            if not user:
                return jsonify({'error': 'Invalid token'}), 401
                
            # Set current_user equivalent for the request
            request.current_token_user = user
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
    
    return decorated_function

# Create authentication blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Test endpoint to debug JSON parsing
@auth_bp.route('/test', methods=['POST'])
def test_endpoint():
    """Test endpoint for debugging"""
    try:
        from flask import current_app
        current_app.logger.info(f"Test endpoint called")
        current_app.logger.info(f"Request is_json: {request.is_json}")
        current_app.logger.info(f"Request content_type: {request.content_type}")
        current_app.logger.info(f"Request data: {request.data}")
        
        json_data = request.get_json()
        current_app.logger.info(f"JSON data: {json_data}")
        
        return jsonify({'success': True, 'received': json_data})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Test endpoint error: {e}")
        return jsonify({'error': str(e)}), 400

# Simple test registration endpoint
@auth_bp.route('/register-test', methods=['POST'])
def register_test():
    """Simple test registration endpoint"""
    from flask import current_app
    current_app.logger.info("Register test endpoint called")
    return jsonify({'success': True, 'message': 'Register test endpoint works'})

# Minimal registration endpoint for testing
@auth_bp.route('/register-minimal', methods=['POST'])
def register_minimal():
    """Minimal registration endpoint for testing"""
    from flask import current_app
    import random
    
    try:
        current_app.logger.info("Minimal register called")
        json_data = request.get_json()
        current_app.logger.info(f"Data: {json_data}")
        
        # Create a test user with minimal data
        username = f"testuser_{random.randint(1000, 9999)}"
        user = User(
            username=username,
            email=f"{username}@test.com",
            role='player',
            color='#3498db'
        )
        user.set_password('TestPassword123!')
        
        current_app.logger.info(f"Created user object: {user.username}")
        
        db.session.add(user)
        db.session.commit()
        
        current_app.logger.info("User saved to database")
        
        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error in minimal register: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Test validation endpoint
@auth_bp.route('/register-validate', methods=['POST'])
def register_validate():
    """Test validation only"""
    from flask import current_app
    
    try:
        current_app.logger.info("Validation test called")
        json_data = request.get_json()
        current_app.logger.info(f"Input data: {json_data}")
        
        # Test schema validation
        schema = RegisterSchema()
        current_app.logger.info("Schema created")
        
        data = schema.load(json_data)
        current_app.logger.info(f"Schema validation passed: {data}")
        
        return jsonify({
            'success': True,
            'message': 'Validation passed',
            'validated_data': data
        })
        
    except ValidationError as err:
        current_app.logger.error(f"Validation error: {err.messages}")
        return jsonify({'error': 'Validation failed', 'details': err.messages}), 400
    except Exception as e:
        current_app.logger.error(f"Error in validation test: {e}")
        return jsonify({'error': str(e)}), 500


def validate_password_strength(password):
    """Validate password meets security requirements"""
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'[0-9]', password):
        errors.append("Password must contain at least one number")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    return errors

def log_login_attempt(username, success, failure_reason=None):
    """Log login attempt for security monitoring"""
    attempt = LoginAttempt(
        username=username,
        ip_address=get_remote_address(),
        user_agent=request.headers.get('User-Agent', ''),
        success=success,
        failure_reason=failure_reason
    )
    db.session.add(attempt)
    db.session.commit()

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user account"""
    from flask import current_app
    
    # Check if request has JSON data
    if not request.is_json:
        current_app.logger.error("Request is not JSON")
        return jsonify({'error': 'Request must be JSON'}), 400
        
    json_data = request.get_json()
    if json_data is None:
        current_app.logger.error("No JSON data in request")
        return jsonify({'error': 'No JSON data provided'}), 400
        
    # Debug: log the request data
    current_app.logger.info(f"Registration request data: {json_data}")
    
    # Validate input data
    try:
        schema = RegisterSchema()
        data = schema.load(json_data)
        current_app.logger.info(f"Validation passed, data: {data}")
    except ValidationError as err:
        current_app.logger.error(f"Validation error: {err.messages}")
        return jsonify({'error': 'Validation failed', 'details': err.messages}), 400
    
    # Additional password validation
    password_errors = validate_password_strength(data['password'])
    if password_errors:
        return jsonify({'error': 'Password requirements not met', 'details': password_errors}), 400
    
    # Email validation
    try:
        valid_email = validate_email(data['email'])
        data['email'] = valid_email.email
    except EmailNotValidError as e:
        return jsonify({'error': 'Invalid email address', 'details': str(e)}), 400
    
    # Check if username or email already exists
    existing_user = User.query.filter(
        (User.username == data['username']) | (User.email == data['email'])
    ).first()
    
    if existing_user:
        if existing_user.username == data['username']:
            return jsonify({'error': 'Username already exists'}), 409
        else:
            return jsonify({'error': 'Email already registered'}), 409
    
    # Create new user
    user = User(
        username=data['username'],
        email=data['email'],
        role=data['role'],
        color=data['color']
    )
    user.set_password(data['password'])
    
    try:
        db.session.add(user)
        db.session.commit()
        
        # Log successful registration
        log_login_attempt(data['username'], True)
        
        # Auto-login the user
        login_user(user, remember=False)
        
        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed', 'details': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and create session"""
    schema = LoginSchema()
    
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({'error': 'Validation failed', 'details': err.messages}), 400
    
    username = data['username']
    password = data['password']
    
    # Find user by username or email
    user = User.query.filter(
        (User.username == username) | (User.email == username)
    ).first()
    
    if not user:
        log_login_attempt(username, False, 'user_not_found')
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.is_active:
        log_login_attempt(username, False, 'account_disabled')
        return jsonify({'error': 'Account is disabled'}), 403
    
    if user.is_locked():
        log_login_attempt(username, False, 'account_locked')
        return jsonify({'error': 'Account is temporarily locked due to multiple failed attempts'}), 423
    
    if not user.check_password(password):
        user.increment_failed_login()
        db.session.commit()
        log_login_attempt(username, False, 'invalid_password')
        
        remaining_attempts = 5 - user.failed_login_attempts
        if remaining_attempts > 0:
            return jsonify({
                'error': 'Invalid credentials',
                'remaining_attempts': remaining_attempts
            }), 401
        else:
            return jsonify({'error': 'Account locked due to too many failed attempts'}), 423
    
    # Successful login
    user.reset_failed_login()
    db.session.commit()
    login_user(user, remember=False)
    log_login_attempt(username, True)
    
    # Generate API token for Obsidian plugin (cross-origin compatible)
    import jwt
    from datetime import datetime, timedelta
    from flask import current_app
    
    # Create token payload
    token_payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(hours=24),  # 24 hour expiry
        'iat': datetime.utcnow()
    }
    
    # Generate JWT token
    token = jwt.encode(token_payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    
    current_app.logger.info(f"LOGIN: User {username} logged in, generated token")
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'token': token  # Include token for Obsidian plugin
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Log out current user"""
    username = current_user.username
    logout_user()
    return jsonify({'message': f'User {username} logged out successfully'}), 200

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    """Get current authenticated user info"""
    from flask import current_app, session
    current_app.logger.info(f"ME: Session ID: {session.get('_id', 'None')}")
    current_app.logger.info(f"ME: Session data keys: {list(session.keys())}")
    
    # Use token user if available, otherwise fall back to session user
    user = getattr(request, 'current_token_user', None) or current_user
    current_app.logger.info(f"ME: Token user: {user.username if hasattr(user, 'username') else 'None'}")
    current_app.logger.info(f"ME: User authenticated: {user.is_authenticated if hasattr(user, 'is_authenticated') else 'Token user'}")
    
    if hasattr(user, 'to_dict'):
        return jsonify({'user': user.to_dict()}), 200
    else:
        return jsonify({'error': 'No authenticated user found'}), 401

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    schema = PasswordChangeSchema()
    
    try:
        data = schema.load(request.json)
    except ValidationError as err:
        return jsonify({'error': 'Validation failed', 'details': err.messages}), 400
    
    if not current_user.check_password(data['current_password']):
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    # Validate new password strength
    password_errors = validate_password_strength(data['new_password'])
    if password_errors:
        return jsonify({'error': 'New password requirements not met', 'details': password_errors}), 400
    
    # Update password
    current_user.set_password(data['new_password'])
    db.session.commit()
    
    return jsonify({'message': 'Password changed successfully'}), 200

@auth_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile (color, email)"""
    data = request.json or {}
    
    # Validate color if provided
    if 'color' in data:
        color = data['color']
        if not re.match(r'^#[0-9a-fA-F]{6}$', color):
            return jsonify({'error': 'Invalid color format'}), 400
        current_user.color = color
    
    # Validate email if provided
    if 'email' in data:
        try:
            valid_email = validate_email(data['email'])
            email = valid_email.email
            
            # Check if email is already used by another user
            existing_user = User.query.filter(
                (User.email == email) & (User.id != current_user.id)
            ).first()
            
            if existing_user:
                return jsonify({'error': 'Email already in use'}), 409
            
            current_user.email = email
            
        except EmailNotValidError as e:
            return jsonify({'error': 'Invalid email address', 'details': str(e)}), 400
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Profile updated successfully',
            'user': current_user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Profile update failed', 'details': str(e)}), 500

@auth_bp.route('/users', methods=['GET'])
@login_required
def list_users():
    """Get list of all users (for Game Masters or admin purposes)"""
    if not current_user.is_game_master():
        return jsonify({'error': 'Insufficient privileges'}), 403
    
    users = User.query.filter(User.is_active == True).all()
    return jsonify({
        'users': [user.to_dict() for user in users]
    }), 200

# Simple CORS test endpoint
@auth_bp.route('/cors-test', methods=['GET', 'POST', 'OPTIONS'])
def cors_test():
    """Simple endpoint to test CORS configuration"""
    from flask import current_app, jsonify
    current_app.logger.info(f"🔧 CORS test endpoint called - Method: {request.method}")
    current_app.logger.info(f"   Origin: {request.headers.get('Origin', 'Not provided')}")
    current_app.logger.info(f"   Headers: {dict(request.headers)}")
    
    if request.method == 'OPTIONS':
        current_app.logger.info("   Handling OPTIONS preflight request")
        return '', 200
    
    return jsonify({
        'success': True,
        'method': request.method,
        'origin': request.headers.get('Origin', 'Not provided'),
        'message': 'CORS is working!'
    })

# Explicit OPTIONS handlers for CORS preflight requests
@auth_bp.route('/login', methods=['OPTIONS'])
def login_preflight():
    """Handle preflight requests for login endpoint"""
    from flask import current_app
    current_app.logger.info("🔧 LOGIN OPTIONS preflight request received")
    current_app.logger.info(f"   Origin: {request.headers.get('Origin', 'Not provided')}")
    current_app.logger.info(f"   Headers: {dict(request.headers)}")
    return '', 200

@auth_bp.route('/register', methods=['OPTIONS'])
def register_preflight():
    """Handle preflight requests for register endpoint"""
    from flask import current_app
    current_app.logger.info("🔧 REGISTER OPTIONS preflight request received")
    current_app.logger.info(f"   Origin: {request.headers.get('Origin', 'Not provided')}")
    current_app.logger.info(f"   Headers: {dict(request.headers)}")
    return '', 200

@auth_bp.route('/logout', methods=['OPTIONS'])
def logout_preflight():
    """Handle preflight requests for logout endpoint"""
    return '', 200

@auth_bp.route('/profile', methods=['OPTIONS'])
def profile_preflight():
    """Handle preflight requests for profile endpoint"""
    return '', 200

# Session debug endpoint
@auth_bp.route('/session-debug', methods=['GET'])
def session_debug():
    """Debug session information without authentication"""
    from flask import current_app, session
    current_app.logger.info(f"SESSION DEBUG: Session ID: {session.get('_id', 'None')}")
    current_app.logger.info(f"SESSION DEBUG: Session data keys: {list(session.keys())}")
    current_app.logger.info(f"SESSION DEBUG: Cookie header: {request.headers.get('Cookie', 'Not provided')}")
    current_app.logger.info(f"SESSION DEBUG: User authenticated: {current_user.is_authenticated if current_user else 'No current_user'}")
    
    # Also log authorization header for debugging
    auth_header = request.headers.get('Authorization', 'Not provided')
    current_app.logger.info(f"SESSION DEBUG: Authorization header: {auth_header}")
    
    return jsonify({
        'session_id': session.get('_id', 'None'),
        'session_keys': list(session.keys()),
        'cookie_header': request.headers.get('Cookie', 'Not provided'),
        'authorization_header': auth_header,
        'user_authenticated': current_user.is_authenticated if current_user else False
    })