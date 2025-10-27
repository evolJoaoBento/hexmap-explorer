"""
Production-ready logging configuration for Hex Explorer
"""
import os
import logging
import logging.handlers
from datetime import datetime
from pythonjsonlogger import jsonlogger

def setup_logging(app):
    """Configure comprehensive logging for production"""
    
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Get log level from environment
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # Clear existing handlers
    app.logger.handlers = []
    
    # Set log level
    app.logger.setLevel(getattr(logging, log_level))
    
    # JSON formatter for structured logging
    json_formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        rename_fields={'timestamp': '@timestamp', 'level': 'level'}
    )
    
    # Console formatter for human-readable logs
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation (for all logs)
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'hexexplorer.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(json_formatter)
    
    # Error file handler (for errors only)
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'hexexplorer_errors.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_formatter)
    
    # Security log handler (for authentication and security events)
    security_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'security.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    security_handler.setLevel(logging.INFO)
    security_handler.setFormatter(json_formatter)
    
    # Console handler (for development)
    if app.debug:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(console_formatter)
        app.logger.addHandler(console_handler)
    
    # Add handlers to app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    
    # Create security logger
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)
    security_logger.addHandler(security_handler)
    
    # Log uncaught exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            return
        app.logger.error(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
    
    import sys
    sys.excepthook = handle_exception
    
    # Log application startup
    app.logger.info(
        f"Hex Explorer started - Environment: {os.environ.get('FLASK_ENV', 'production')}"
    )
    
    return security_logger

def log_request(app):
    """Log HTTP requests for audit trail"""
    from flask import request, g
    import time
    
    @app.before_request
    def start_timer():
        g.start = time.time()
    
    @app.after_request
    def log_request_info(response):
        if request.path == '/favicon.ico':
            return response
        
        now = time.time()
        duration = round(now - g.start, 2) if hasattr(g, 'start') else 0
        
        # Skip health check endpoints in logs
        if request.path not in ['/health', '/metrics']:
            app.logger.info({
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'duration': duration,
                'ip': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'user': getattr(g, 'user', None)
            })
        
        return response
    
    @app.errorhandler(Exception)
    def handle_error(error):
        app.logger.error(
            f"Request failed: {str(error)}",
            exc_info=True,
            extra={
                'method': request.method,
                'path': request.path,
                'ip': request.remote_addr
            }
        )
        
        # Don't expose internal errors in production
        if app.config.get('FLASK_ENV') == 'production':
            return {'error': 'Internal server error'}, 500
        else:
            return {'error': str(error)}, 500