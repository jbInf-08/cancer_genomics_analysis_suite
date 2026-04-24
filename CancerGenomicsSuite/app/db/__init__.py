#!/usr/bin/env python3
"""
Database Package for Cancer Genomics Analysis Suite

This package handles database models, migrations, and database-related utilities
for the cancer genomics analysis suite. It provides a centralized interface for
all database operations and model management.

Features:
- Database model definitions and relationships
- Migration management and execution
- Database utility functions
- Model serialization and validation
- Database connection management
- Query optimization helpers

Models:
- AnalysisJob: Tracks analysis jobs and their status
- DataFile: Manages uploaded data files and metadata
- AnalysisResult: Stores analysis results and outputs
- User: User authentication and profile management (from auth package)

Usage:
    from app.db import db, AnalysisJob, DataFile, AnalysisResult
    from app.db.utils import create_tables, run_migrations
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import json

# Import the database instance from the main app
from app import db

# Import all database models
from .models import (
    GeneExpression,
    MutationRecord,
    AnalysisJob,
    DataFile, 
    AnalysisResult,
    Project,
    Dataset
)

# Import utility functions
from .utils import (
    create_tables,
    run_migrations,
    backup_database,
    restore_database,
    get_database_stats,
    cleanup_old_data,
    validate_model_data,
    serialize_model,
    deserialize_model
)

# Configure logging
logger = logging.getLogger(__name__)

# Package version
__version__ = "1.0.0"

# Export all public components
__all__ = [
    # Database instance
    'db',
    
    # Models
    'GeneExpression',
    'MutationRecord',
    'AnalysisJob',
    'DataFile', 
    'AnalysisResult',
    'Project',
    'Dataset',
    
    # Utility functions
    'create_tables',
    'run_migrations',
    'backup_database',
    'restore_database',
    'get_database_stats',
    'cleanup_old_data',
    'validate_model_data',
    'serialize_model',
    'deserialize_model',
    
    # Package info
    '__version__',
    'get_package_info'
]


def get_package_info() -> Dict[str, Any]:
    """
    Get information about the database package.
    
    Returns:
        Dict containing package information
    """
    return {
        'name': 'app.db',
        'version': __version__,
        'description': 'Database package for Cancer Genomics Analysis Suite',
        'models': [
            'GeneExpression',
            'MutationRecord',
            'AnalysisJob',
            'DataFile',
            'AnalysisResult',
            'Project',
            'Dataset'
        ],
        'features': [
            'Model definitions',
            'Migration management',
            'Database utilities',
            'Data validation',
            'Backup and restore',
            'Query optimization'
        ]
    }


def initialize_database_package(app=None) -> bool:
    """
    Initialize the database package with the Flask application.
    
    Args:
        app: Flask application instance (optional)
        
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        if app:
            with app.app_context():
                # Create all tables
                create_tables()
                
                # Run any pending migrations
                run_migrations()
                
                logger.info("Database package initialized successfully")
                return True
        else:
            logger.warning("No Flask app provided for database initialization")
            return False
            
    except Exception as e:
        logger.error(f"Database package initialization failed: {e}")
        return False


def get_model_by_name(model_name: str):
    """
    Get a model class by its name.
    
    Args:
        model_name: Name of the model class
        
    Returns:
        Model class or None if not found
    """
    models = {
        'GeneExpression': GeneExpression,
        'MutationRecord': MutationRecord,
        'AnalysisJob': AnalysisJob,
        'DataFile': DataFile,
        'AnalysisResult': AnalysisResult,
        'Project': Project,
        'Dataset': Dataset
    }
    
    return models.get(model_name)


def get_all_models() -> List[Any]:
    """
    Get all available model classes.
    
    Returns:
        List of model classes
    """
    return [GeneExpression, MutationRecord, AnalysisJob, DataFile, AnalysisResult, Project, Dataset]


def get_model_table_names() -> List[str]:
    """
    Get all table names for the models.
    
    Returns:
        List of table names
    """
    return [model.__tablename__ for model in get_all_models()]


def validate_database_connection() -> bool:
    """
    Validate that the database connection is working.
    
    Returns:
        bool: True if connection is valid, False otherwise
    """
    try:
        # Try to execute a simple query
        # SQLAlchemy 2.0+ requires text() wrapper for raw SQL
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        logger.info("Database connection validated successfully")
        return True
    except Exception as e:
        logger.error(f"Database connection validation failed: {e}")
        return False


def get_database_info() -> Dict[str, Any]:
    """
    Get comprehensive database information.
    
    Returns:
        Dict containing database information
    """
    try:
        # Get database URL (without password for security)
        db_url = str(db.engine.url)
        if '@' in db_url:
            # Hide password in URL
            parts = db_url.split('@')
            if len(parts) == 2:
                user_part = parts[0].split('//')[-1]
                if ':' in user_part:
                    user, _ = user_part.split(':', 1)
                    db_url = db_url.replace(user_part, f"{user}:***")
        
        return {
            'url': db_url,
            'dialect': db.engine.dialect.name,
            'driver': db.engine.dialect.driver,
            'pool_size': db.engine.pool.size(),
            'checked_out': db.engine.pool.checkedout(),
            'overflow': db.engine.pool.overflow(),
            'models': get_model_table_names(),
            'package_version': __version__
        }
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {'error': str(e)}


# Initialize package logging
logger.info(f"Database package v{__version__} loaded successfully")
logger.info(f"Available models: {', '.join(get_model_table_names())}")
