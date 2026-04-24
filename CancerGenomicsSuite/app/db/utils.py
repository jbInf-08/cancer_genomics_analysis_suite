#!/usr/bin/env python3
"""
Database Utilities for Cancer Genomics Analysis Suite

This module provides utility functions for database operations, migrations,
backup/restore, and data management for the cancer genomics analysis suite.

Features:
- Database table creation and management
- Migration execution and management
- Database backup and restore operations
- Data cleanup and maintenance
- Model validation and serialization
- Database statistics and monitoring
"""

import os
import json
import logging
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Type
from datetime import datetime, timedelta
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

# Import database instance and models
from app import db
from .models import AnalysisJob, DataFile, AnalysisResult

# Configure logging
logger = logging.getLogger(__name__)


def create_tables() -> bool:
    """
    Create all database tables.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db.create_all()
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        return False


def drop_tables() -> bool:
    """
    Drop all database tables.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db.drop_all()
        logger.info("Database tables dropped successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        return False


def run_migrations() -> bool:
    """
    Run database migrations from the migrations directory.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        migrations_dir = Path(__file__).parent / 'migrations'
        
        if not migrations_dir.exists():
            logger.info("No migrations directory found")
            return True
        
        # Get all SQL migration files
        migration_files = sorted(migrations_dir.glob('*.sql'))
        
        if not migration_files:
            logger.info("No migration files found")
            return True
        
        logger.info(f"Found {len(migration_files)} migration files")
        
        for migration_file in migration_files:
            logger.info(f"Running migration: {migration_file.name}")
            
            with open(migration_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Split SQL commands by semicolon
            commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip()]
            
            for command in commands:
                if command:
                    try:
                        db.session.execute(text(command))
                        db.session.commit()
                    except SQLAlchemyError as e:
                        logger.warning(f"Migration command failed: {e}")
                        db.session.rollback()
        
        logger.info("Database migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration execution failed: {e}")
        return False


def backup_database(backup_path: Optional[str] = None) -> Optional[str]:
    """
    Create a backup of the database.
    
    Args:
        backup_path: Path where to save the backup (optional)
        
    Returns:
        str: Path to the backup file, or None if failed
    """
    try:
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_{timestamp}.sql"
        
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get database URL
        db_url = str(db.engine.url)
        
        if db_url.startswith('sqlite'):
            # SQLite backup
            import sqlite3
            
            source_db = db_url.replace('sqlite:///', '')
            backup_db = str(backup_path)
            
            # Create backup using SQLite backup API
            source_conn = sqlite3.connect(source_db)
            backup_conn = sqlite3.connect(backup_db)
            source_conn.backup(backup_conn)
            source_conn.close()
            backup_conn.close()
            
        else:
            # For other databases, use pg_dump or mysqldump
            logger.warning(f"Backup not implemented for database type: {db_url}")
            return None
        
        logger.info(f"Database backup created: {backup_path}")
        return str(backup_path)
        
    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        return None


def restore_database(backup_path: str) -> bool:
    """
    Restore database from a backup file.
    
    Args:
        backup_path: Path to the backup file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        # Get database URL
        db_url = str(db.engine.url)
        
        if db_url.startswith('sqlite'):
            # SQLite restore
            import sqlite3
            
            source_db = db_url.replace('sqlite:///', '')
            
            # Close existing connections
            db.session.close()
            db.engine.dispose()
            
            # Copy backup to database location
            shutil.copy2(backup_path, source_db)
            
            # Reconnect
            db.engine.connect()
            
        else:
            # For other databases, use psql or mysql
            logger.warning(f"Restore not implemented for database type: {db_url}")
            return False
        
        logger.info(f"Database restored from: {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"Database restore failed: {e}")
        return False


def get_database_stats() -> Dict[str, Any]:
    """
    Get database statistics and information.
    
    Returns:
        Dict containing database statistics
    """
    try:
        stats = {
            'connection_info': {
                'url': str(db.engine.url).replace(db.engine.url.password or '', '***'),
                'dialect': db.engine.dialect.name,
                'driver': db.engine.dialect.driver,
            },
            'pool_info': {
                'size': db.engine.pool.size(),
                'checked_out': db.engine.pool.checkedout(),
                'overflow': db.engine.pool.overflow(),
                'checked_in': db.engine.pool.checkedin(),
            },
            'table_counts': {},
            'database_size': None
        }
        
        # Get table row counts
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        
        for table_name in table_names:
            try:
                result = db.session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                stats['table_counts'][table_name] = count
            except Exception as e:
                logger.warning(f"Failed to get count for table {table_name}: {e}")
                stats['table_counts'][table_name] = 'error'
        
        # Get database size (SQLite specific)
        if db.engine.dialect.name == 'sqlite':
            try:
                db_path = str(db.engine.url).replace('sqlite:///', '')
                if os.path.exists(db_path):
                    stats['database_size'] = os.path.getsize(db_path)
            except Exception as e:
                logger.warning(f"Failed to get database size: {e}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {'error': str(e)}


def cleanup_old_data(days_old: int = 30) -> Dict[str, int]:
    """
    Clean up old data from the database.
    
    Args:
        days_old: Number of days old data to clean up
        
    Returns:
        Dict with counts of deleted records
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        deleted_counts = {}
        
        # Clean up old analysis jobs
        old_jobs = AnalysisJob.query.filter(
            AnalysisJob.created_at < cutoff_date,
            AnalysisJob.status.in_(['completed', 'failed'])
        ).all()
        
        for job in old_jobs:
            db.session.delete(job)
        
        deleted_counts['analysis_jobs'] = len(old_jobs)
        
        # Clean up old data files (optional - be careful with this)
        # old_files = DataFile.query.filter(
        #     DataFile.upload_date < cutoff_date,
        #     DataFile.is_processed == True
        # ).all()
        # 
        # for file in old_files:
        #     # Also delete the actual file
        #     if os.path.exists(file.file_path):
        #         os.remove(file.file_path)
        #     db.session.delete(file)
        # 
        # deleted_counts['data_files'] = len(old_files)
        
        # Clean up old analysis results
        old_results = AnalysisResult.query.filter(
            AnalysisResult.created_at < cutoff_date
        ).all()
        
        for result in old_results:
            db.session.delete(result)
        
        deleted_counts['analysis_results'] = len(old_results)
        
        db.session.commit()
        
        logger.info(f"Cleaned up old data: {deleted_counts}")
        return deleted_counts
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")
        db.session.rollback()
        return {'error': str(e)}


def validate_model_data(model_class: Type, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate data for a model before saving.
    
    Args:
        model_class: The model class to validate against
        data: Dictionary of data to validate
        
    Returns:
        Dict with validation results
    """
    try:
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Get model columns
        columns = model_class.__table__.columns
        
        # Check required fields
        for column in columns:
            if not column.nullable and column.name not in data:
                validation_result['errors'].append(f"Required field '{column.name}' is missing")
                validation_result['valid'] = False
        
        # Check data types and constraints
        for field_name, value in data.items():
            if hasattr(model_class, field_name):
                column = getattr(model_class, field_name)
                
                # Check string length constraints
                if hasattr(column.type, 'length') and isinstance(value, str):
                    if len(value) > column.type.length:
                        validation_result['errors'].append(
                            f"Field '{field_name}' exceeds maximum length of {column.type.length}"
                        )
                        validation_result['valid'] = False
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Model validation failed: {e}")
        return {
            'valid': False,
            'errors': [f"Validation error: {str(e)}"],
            'warnings': []
        }


def serialize_model(model_instance) -> Dict[str, Any]:
    """
    Serialize a model instance to a dictionary.
    
    Args:
        model_instance: The model instance to serialize
        
    Returns:
        Dict containing serialized model data
    """
    try:
        if hasattr(model_instance, 'to_dict'):
            return model_instance.to_dict()
        else:
            # Fallback serialization
            result = {}
            for column in model_instance.__table__.columns:
                value = getattr(model_instance, column.name)
                if isinstance(value, datetime):
                    result[column.name] = value.isoformat()
                else:
                    result[column.name] = value
            return result
            
    except Exception as e:
        logger.error(f"Model serialization failed: {e}")
        return {'error': str(e)}


def deserialize_model(model_class: Type, data: Dict[str, Any]) -> Any:
    """
    Deserialize data to a model instance.
    
    Args:
        model_class: The model class to deserialize to
        data: Dictionary of data to deserialize
        
    Returns:
        Model instance or None if failed
    """
    try:
        # Filter data to only include valid columns
        valid_columns = {col.name for col in model_class.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_columns}
        
        # Create model instance
        instance = model_class(**filtered_data)
        return instance
        
    except Exception as e:
        logger.error(f"Model deserialization failed: {e}")
        return None


def get_table_info(table_name: str) -> Dict[str, Any]:
    """
    Get information about a specific table.
    
    Args:
        table_name: Name of the table
        
    Returns:
        Dict containing table information
    """
    try:
        inspector = inspect(db.engine)
        
        if table_name not in inspector.get_table_names():
            return {'error': f"Table '{table_name}' not found"}
        
        columns = inspector.get_columns(table_name)
        indexes = inspector.get_indexes(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)
        
        return {
            'name': table_name,
            'columns': [
                {
                    'name': col['name'],
                    'type': str(col['type']),
                    'nullable': col['nullable'],
                    'primary_key': col.get('primary_key', False),
                    'default': col.get('default')
                }
                for col in columns
            ],
            'indexes': [
                {
                    'name': idx['name'],
                    'columns': idx['column_names'],
                    'unique': idx['unique']
                }
                for idx in indexes
            ],
            'foreign_keys': [
                {
                    'constrained_columns': fk['constrained_columns'],
                    'referred_table': fk['referred_table'],
                    'referred_columns': fk['referred_columns']
                }
                for fk in foreign_keys
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get table info for '{table_name}': {e}")
        return {'error': str(e)}


def optimize_database() -> Dict[str, Any]:
    """
    Optimize database performance.
    
    Returns:
        Dict with optimization results
    """
    try:
        results = {
            'vacuum': False,
            'analyze': False,
            'reindex': False
        }
        
        if db.engine.dialect.name == 'sqlite':
            # SQLite specific optimizations
            db.session.execute(text('VACUUM'))
            results['vacuum'] = True
            
            db.session.execute(text('ANALYZE'))
            results['analyze'] = True
            
            db.session.execute(text('REINDEX'))
            results['reindex'] = True
            
        elif db.engine.dialect.name == 'postgresql':
            # PostgreSQL specific optimizations
            db.session.execute(text('VACUUM ANALYZE'))
            results['vacuum'] = True
            results['analyze'] = True
            
        db.session.commit()
        
        logger.info("Database optimization completed")
        return results
        
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        db.session.rollback()
        return {'error': str(e)}


def check_database_health() -> Dict[str, Any]:
    """
    Check database health and connectivity.
    
    Returns:
        Dict with health check results
    """
    try:
        health_status = {
            'connection': False,
            'tables_exist': False,
            'can_query': False,
            'pool_status': 'unknown',
            'errors': []
        }
        
        # Test connection
        try:
            db.session.execute(text('SELECT 1'))
            health_status['connection'] = True
            health_status['can_query'] = True
        except Exception as e:
            health_status['errors'].append(f"Connection test failed: {e}")
        
        # Check if tables exist
        try:
            inspector = inspect(db.engine)
            table_names = inspector.get_table_names()
            expected_tables = ['analysis_jobs', 'data_files', 'analysis_results', 'users']
            
            missing_tables = [t for t in expected_tables if t not in table_names]
            if missing_tables:
                health_status['errors'].append(f"Missing tables: {missing_tables}")
            else:
                health_status['tables_exist'] = True
                
        except Exception as e:
            health_status['errors'].append(f"Table check failed: {e}")
        
        # Check pool status
        try:
            pool = db.engine.pool
            health_status['pool_status'] = {
                'size': pool.size(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'checked_in': pool.checkedin()
            }
        except Exception as e:
            health_status['errors'].append(f"Pool check failed: {e}")
        
        # Overall health
        health_status['healthy'] = (
            health_status['connection'] and 
            health_status['tables_exist'] and 
            health_status['can_query'] and
            len(health_status['errors']) == 0
        )
        
        return health_status
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            'healthy': False,
            'connection': False,
            'tables_exist': False,
            'can_query': False,
            'pool_status': 'unknown',
            'errors': [f"Health check failed: {e}"]
        }
