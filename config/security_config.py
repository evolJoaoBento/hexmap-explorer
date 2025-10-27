"""
Security Configuration for Hex Explorer
"""
import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration with security settings"""
    
    # Flask Core
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///hexexplorer.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or secrets.token_hex(32)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ.get('SESSION_LIFETIME_HOURS', 24)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_SECURE = True  # Require HTTPS in production
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_COOKIE_SAMESITE = 'Lax'
    
    # Session Configuration
    SESSION_TYPE = 'redis' if os.environ.get('REDIS_URL') else 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.environ.get('SESSION_LIFETIME_HOURS', 24)))
    SESSION_COOKIE_SECURE = True  # Require HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'hexexplorer_session'
    
    # Redis Configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Security Settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB default
    
    # Password Policy
    PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', 8))
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBERS = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', REDIS_URL)
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    RATELIMIT_HEADERS_ENABLED = True
    
    # Login Security
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
    LOGIN_LOCKOUT_DURATION = timedelta(minutes=15)
    
    # CORS Settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin']
    CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_EXPOSE_HEADERS = ['Content-Range', 'X-Content-Range']
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_SEND_WILDCARD = False
    CORS_MAX_AGE = 86400
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/hexexplorer.log')
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 10
    
    # Email Configuration (optional)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME')
    
    # Application Settings
    APP_NAME = 'Hex Explorer'
    APP_VERSION = '1.0.0'
    OLLAMA_API_URL = os.environ.get('OLLAMA_API_URL', 'http://localhost:11434')
    
    # Security Headers (for Talisman)
    SECURITY_HEADERS = {
        'force_https': True,
        'strict_transport_security': True,
        'strict_transport_security_max_age': 31536000,
        'frame_options': 'SAMEORIGIN',
        'content_security_policy': {
            'default-src': "'self'",
            'script-src': "'self' 'unsafe-inline' 'unsafe-eval' https://cdn.socket.io",
            'style-src': "'self' 'unsafe-inline'",
            'img-src': "'self' data: https:",
            'connect-src': "'self' wss: ws:",
            'font-src': "'self' data:",
        }
    }


class DevelopmentConfig(Config):
    """Development configuration with relaxed security"""
    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False  # Disable CSRF for easier testing
    JWT_COOKIE_SECURE = False  # Allow HTTP in development
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = None  # Allow cross-origin cookies for Obsidian
    SECURITY_HEADERS = {
        'force_https': False,
        'frame_options': 'SAMEORIGIN',
    }
    CORS_ORIGINS = ['*']  # Allow all origins in development


class ProductionConfig(Config):
    """Production configuration with maximum security"""
    DEBUG = False
    TESTING = False
    # Ensure critical values are set
    if not os.environ.get('SECRET_KEY'):
        raise ValueError("SECRET_KEY environment variable must be set in production")
    if not os.environ.get('DATABASE_URL'):
        raise ValueError("DATABASE_URL environment variable must be set in production")


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


# Configuration selector
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])