#!/usr/bin/env python3
"""
Cancer Genomics Analysis Suite - Flask Application Factory

This module provides the Flask application factory pattern for the cancer
genomics analysis suite. It initializes all necessary extensions, registers
blueprints, and configures the application for different environments.

Features:
- Application factory pattern for flexible configuration
- Extension initialization (SQLAlchemy, CORS, Login, etc.)
- Blueprint registration for modular architecture
- Error handling and middleware configuration
- Database initialization and migration support
- Environment-specific configuration loading
"""

import os
import logging
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import LoginManager
from werkzeug.exceptions import HTTPException

# Import configuration
from CancerGenomicsSuite.config.settings import settings

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
cors = CORS()

# Configure logging
logger = logging.getLogger(__name__)


def create_app(config_class=None):
    """
    Create and configure the Flask application.
    
    Args:
        config_class: Configuration class to use (defaults to settings)
        
    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    if config_class:
        app.config.from_object(config_class)
    else:
        # Use settings from config module
        app.config.update({
            'SECRET_KEY': settings.security.secret_key,
            'SQLALCHEMY_DATABASE_URI': settings.get_database_url(),
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SQLALCHEMY_ENGINE_OPTIONS': {
                'pool_size': settings.database.pool_size,
                'max_overflow': settings.database.max_overflow,
                'pool_timeout': settings.database.pool_timeout,
                'pool_recycle': settings.database.pool_recycle,
            },
            'SESSION_COOKIE_SECURE': settings.security.session_cookie_secure,
            'SESSION_COOKIE_HTTPONLY': settings.security.session_cookie_httponly,
            'SESSION_COOKIE_SAMESITE': settings.security.session_cookie_samesite,
            'PERMANENT_SESSION_LIFETIME': settings.security.permanent_session_lifetime,
            'MAX_CONTENT_LENGTH': settings.file_storage.max_content_length,
            'UPLOAD_FOLDER': settings.file_storage.upload_folder,
        })
    
    # Initialize extensions with app
    initialize_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Configure logging
    configure_app_logging(app)
    
    # Create upload directory if it doesn't exist
    create_upload_directory(app)
    
    # Initialize database
    initialize_database(app)
    
    logger.info(f"Flask application '{app.name}' created successfully")
    logger.info(f"Environment: {settings.flask_env}")
    logger.info(f"Debug mode: {settings.dash_debug_mode}")
    
    return app


def initialize_extensions(app):
    """Initialize Flask extensions with the application."""
    
    # Initialize SQLAlchemy
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Initialize CORS
    cors.init_app(app, 
                  origins=settings.security.cors_origins,
                  methods=settings.security.cors_methods,
                  headers=settings.security.cors_headers,
                  supports_credentials=True)
    
    logger.info("Flask extensions initialized successfully")


def register_blueprints(app):
    """Register application blueprints."""
    
    # Import blueprints
    from .auth.routes import auth_bp
    from .dashboard.routes import dashboard_bp
    
    # Register blueprints with URL prefixes
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    
    # Register root routes
    @app.route('/')
    def index():
        """Root endpoint - redirect to dashboard or login."""
        return render_template('index.html', 
                             app_name=settings.app_name,
                             app_version=settings.app_version)
    
    @app.route('/health')
    def health_check():
        """Health check endpoint for monitoring."""
        return jsonify({
            'status': 'healthy',
            'app_name': settings.app_name,
            'version': settings.app_version,
            'environment': settings.flask_env
        })
    
    @app.route('/api/status')
    def api_status():
        """API status endpoint with feature flags."""
        celery_status = 'unavailable'
        if CELERY_AVAILABLE:
            try:
                from .celery_config import get_worker_stats
                stats = get_worker_stats()
                celery_status = 'operational' if not stats.get('error') else 'error'
            except Exception as e:
                celery_status = f'error: {str(e)}'
        
        return jsonify({
            'status': 'operational',
            'features': {
                'gene_expression_analysis': settings.get_feature_status('enable_gene_expression_analysis'),
                'mutation_analysis': settings.get_feature_status('enable_mutation_analysis'),
                'machine_learning': settings.get_feature_status('enable_machine_learning'),
                'pathway_analysis': settings.get_feature_status('enable_pathway_analysis'),
                'multi_omics_integration': settings.get_feature_status('enable_multi_omics_integration'),
            },
            'external_services': {
                'redis_enabled': settings.redis.enabled,
                'email_enabled': settings.email.enabled,
                'cloud_storage_enabled': settings.file_storage.enable_cloud_storage,
                'celery_status': celery_status,
            }
        })
    
    @app.route('/api/celery/status')
    def celery_status():
        """Celery-specific status endpoint."""
        if not CELERY_AVAILABLE:
            return jsonify({
                'status': 'unavailable',
                'message': 'Celery is not configured or available'
            }), 503
        
        try:
            from .celery_config import get_worker_stats, get_queue_lengths, health_check
            
            # Get health check result
            health_result = health_check.delay()
            health_data = health_result.get(timeout=10)
            
            # Get worker stats
            worker_stats = get_worker_stats()
            
            # Get queue lengths
            queue_lengths = get_queue_lengths()
            
            return jsonify({
                'status': 'operational',
                'health_check': health_data,
                'worker_stats': worker_stats,
                'queue_lengths': queue_lengths,
                'broker_url': settings.celery.broker_url,
                'result_backend': settings.celery.result_backend
            })
            
        except Exception as e:
            logger.error(f"Celery status check failed: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    logger.info("Application blueprints registered successfully")


def register_error_handlers(app):
    """Register error handlers for the application."""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad request errors."""
        return jsonify({
            'error': 'Bad Request',
            'message': 'The request could not be understood by the server.',
            'status_code': 400
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle unauthorized access errors."""
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication is required to access this resource.',
            'status_code': 401
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle forbidden access errors."""
        return jsonify({
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource.',
            'status_code': 403
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle not found errors."""
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found.',
            'status_code': 404
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle method not allowed errors."""
        return jsonify({
            'error': 'Method Not Allowed',
            'message': 'The method is not allowed for the requested resource.',
            'status_code': 405
        }), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors."""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An internal server error occurred.',
            'status_code': 500
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle general HTTP exceptions."""
        return jsonify({
            'error': error.name,
            'message': error.description,
            'status_code': error.code
        }), error.code
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle general exceptions."""
        logger.error(f"Unhandled exception: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred.',
            'status_code': 500
        }), 500
    
    logger.info("Error handlers registered successfully")


def configure_app_logging(app):
    """Configure application-specific logging."""
    
    if not app.debug and not app.testing:
        # Configure file logging for production
        if settings.logging.file:
            import logging.handlers
            
            file_handler = logging.handlers.RotatingFileHandler(
                settings.logging.file,
                maxBytes=settings.logging.max_size,
                backupCount=settings.logging.backup_count
            )
            file_handler.setFormatter(logging.Formatter(settings.logging.format))
            file_handler.setLevel(getattr(logging, settings.logging.level.upper()))
            app.logger.addHandler(file_handler)
            app.logger.setLevel(getattr(logging, settings.logging.level.upper()))
            app.logger.info(f"{settings.app_name} startup")


def create_upload_directory(app):
    """Create upload directory if it doesn't exist."""
    
    upload_folder = Path(app.config['UPLOAD_FOLDER'])
    upload_folder.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories for different file types
    subdirs = ['clinical', 'expression', 'mutation', 'pathway', 'structure', 'temp']
    for subdir in subdirs:
        (upload_folder / subdir).mkdir(exist_ok=True)
    
    logger.info(f"Upload directory created: {upload_folder}")


def initialize_database(app):
    """Initialize database tables and run migrations."""
    
    with app.app_context():
        try:
            # Import all models to ensure they are registered
            from .orm.models import GeneExpression, MutationRecord, AnalysisJob, DataFile, AnalysisResult, Project, Dataset
            from .auth.models import User
            
            # Create all tables
            from .orm.utils import create_tables
            create_tables()
            logger.info("Database tables created successfully")
            
            # Run any pending migrations
            run_migrations(app)
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise


def run_migrations(app):
    """Run database migrations if available."""
    
    migrations_dir = Path(app.root_path) / 'orm' / 'migrations'
    
    if migrations_dir.exists():
        try:
            # Simple migration runner for SQL files
            migration_files = sorted(migrations_dir.glob('*.sql'))
            
            for migration_file in migration_files:
                logger.info(f"Running migration: {migration_file.name}")
                
                with open(migration_file, 'r') as f:
                    sql_commands = f.read().split(';')
                    
                for command in sql_commands:
                    command = command.strip()
                    if command:
                        try:
                            db.engine.execute(command)
                        except Exception as e:
                            logger.warning(f"Migration command failed: {e}")
                            
            logger.info("Database migrations completed")
            
        except Exception as e:
            logger.warning(f"Migration execution failed: {e}")


# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login."""
    from .auth.models import User
    return User.query.get(int(user_id))


# Context processors for templates
def register_template_context_processors(app):
    """Register template context processors."""
    
    @app.context_processor
    def inject_app_info():
        """Inject application information into templates."""
        return {
            'app_name': settings.app_name,
            'app_version': settings.app_version,
            'environment': settings.flask_env,
            'features': {
                'gene_expression_analysis': settings.get_feature_status('enable_gene_expression_analysis'),
                'mutation_analysis': settings.get_feature_status('enable_mutation_analysis'),
                'machine_learning': settings.get_feature_status('enable_machine_learning'),
                'pathway_analysis': settings.get_feature_status('enable_pathway_analysis'),
                'multi_omics_integration': settings.get_feature_status('enable_multi_omics_integration'),
            }
        }
    
    @app.context_processor
    def inject_user_info():
        """Inject user information into templates."""
        from flask_login import current_user
        return {
            'current_user': current_user,
            'is_authenticated': current_user.is_authenticated if current_user else False
        }


# Import Celery configuration
try:
    from .celery_config import celery_app
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logger.warning("Celery not available - background tasks disabled")

# Export the create_app function and db instance
__all__ = ['create_app', 'db', 'login_manager', 'cors']
