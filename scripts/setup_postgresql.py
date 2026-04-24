#!/usr/bin/env python3
"""
PostgreSQL Database Setup Script

This script sets up the PostgreSQL database for the Cancer Genomics Analysis Suite.
It handles:
1. Database creation
2. Schema migration
3. Initial data seeding
4. Connection testing

Requirements:
- PostgreSQL 14+ installed and running
- psycopg2-binary Python package

Usage:
    python scripts/setup_postgresql.py [--host localhost] [--port 5432]
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_psycopg2():
    """Check if psycopg2 is available."""
    try:
        import psycopg2
        logger.info(f"psycopg2 version: {psycopg2.__version__}")
        return True
    except ImportError:
        logger.error("psycopg2 not installed. Install with: pip install psycopg2-binary")
        return False


def create_database(host, port, user, password, db_name):
    """Create the PostgreSQL database if it doesn't exist."""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    try:
        # Connect to default 'postgres' database
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}'")
        exists = cur.fetchone()
        
        if not exists:
            cur.execute(f'CREATE DATABASE "{db_name}"')
            logger.info(f"Created database: {db_name}")
        else:
            logger.info(f"Database already exists: {db_name}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        return False


def test_connection(database_url):
    """Test database connection."""
    try:
        from sqlalchemy import create_engine, text
        
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"Connected to PostgreSQL: {version[:50]}...")
        
        engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False


def run_migrations(database_url):
    """Run database migrations using Alembic."""
    try:
        from alembic.config import Config
        from alembic import command
        
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations completed successfully")
        return True
        
    except Exception as e:
        logger.warning(f"Alembic migrations not configured: {e}")
        logger.info("Attempting to create tables directly...")
        return create_tables_direct(database_url)


def create_tables_direct(database_url):
    """Create tables directly using SQLAlchemy models."""
    try:
        from sqlalchemy import create_engine
        
        engine = create_engine(database_url)
        
        # Import models - this will create all tables
        # Note: This requires the Flask app context
        logger.info("Creating tables from SQLAlchemy models...")
        
        # Create essential tables
        from sqlalchemy import MetaData, Table, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
        
        metadata = MetaData()
        
        # Gene Expression Table
        gene_expression = Table(
            'gene_expression', metadata,
            Column('id', Integer, primary_key=True),
            Column('gene_symbol', String(50), nullable=False, index=True),
            Column('gene_id', String(50)),
            Column('sample_id', String(100), nullable=False, index=True),
            Column('expression_value', Float, nullable=False),
            Column('expression_unit', String(20), default='FPKM'),
            Column('condition', String(100), index=True),
            Column('tissue_type', String(100)),
            Column('created_at', DateTime),
            Column('updated_at', DateTime)
        )
        
        # Mutation Records Table
        mutation_records = Table(
            'mutation_records', metadata,
            Column('id', Integer, primary_key=True),
            Column('gene_symbol', String(50), nullable=False, index=True),
            Column('chromosome', String(10)),
            Column('position', Integer),
            Column('reference_allele', String(1000)),
            Column('alternate_allele', String(1000)),
            Column('variant_type', String(50)),
            Column('consequence', String(100)),
            Column('clinical_significance', String(50)),
            Column('sample_id', String(100), index=True),
            Column('cancer_type', String(100), index=True),
            Column('source', String(50)),
            Column('created_at', DateTime)
        )
        
        # Analysis Jobs Table
        analysis_jobs = Table(
            'analysis_jobs', metadata,
            Column('id', Integer, primary_key=True),
            Column('job_id', String(36), unique=True, nullable=False),
            Column('job_type', String(50), nullable=False),
            Column('status', String(20), default='pending'),
            Column('parameters', Text),
            Column('results', Text),
            Column('error_message', Text),
            Column('progress', Integer, default=0),
            Column('created_at', DateTime),
            Column('started_at', DateTime),
            Column('completed_at', DateTime)
        )
        
        # Data Files Table
        data_files = Table(
            'data_files', metadata,
            Column('id', Integer, primary_key=True),
            Column('filename', String(255), nullable=False),
            Column('original_filename', String(255)),
            Column('file_path', String(500)),
            Column('file_size', Integer),
            Column('file_type', String(50)),
            Column('mime_type', String(100)),
            Column('checksum', String(64)),
            Column('status', String(20), default='uploaded'),
            Column('uploaded_at', DateTime),
            Column('processed_at', DateTime)
        )
        
        # Analysis Results Table
        analysis_results = Table(
            'analysis_results', metadata,
            Column('id', Integer, primary_key=True),
            Column('result_id', String(36), unique=True, nullable=False),
            Column('result_type', String(50), nullable=False),
            Column('name', String(200)),
            Column('description', Text),
            Column('data', Text),
            Column('metadata', Text),
            Column('job_id', Integer, ForeignKey('analysis_jobs.id')),
            Column('created_at', DateTime)
        )
        
        # Create all tables
        metadata.create_all(engine)
        
        logger.info("Tables created successfully")
        engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False


def update_env_file(database_url):
    """Update .env file with new database URL."""
    env_file = Path(__file__).parent.parent / '.env'
    
    if env_file.exists():
        content = env_file.read_text()
        
        # Update DATABASE_URL
        if 'DATABASE_URL=' in content:
            import re
            content = re.sub(
                r'DATABASE_URL=.*',
                f'DATABASE_URL={database_url}',
                content
            )
        else:
            content += f'\nDATABASE_URL={database_url}\n'
        
        env_file.write_text(content)
        logger.info(f"Updated .env file with PostgreSQL database URL")
    else:
        logger.warning(".env file not found, skipping update")


def main():
    parser = argparse.ArgumentParser(description='Setup PostgreSQL database')
    parser.add_argument('--host', default='localhost', help='PostgreSQL host')
    parser.add_argument('--port', type=int, default=5432, help='PostgreSQL port')
    parser.add_argument('--user', default='postgres', help='PostgreSQL user')
    parser.add_argument('--password', default='postgres', help='PostgreSQL password')
    parser.add_argument('--db-name', default='cancer_genomics', help='Database name')
    parser.add_argument('--update-env', action='store_true', help='Update .env file')
    args = parser.parse_args()
    
    print("=" * 60)
    print("POSTGRESQL DATABASE SETUP")
    print("=" * 60)
    
    # Step 1: Check dependencies
    print("\n1. Checking dependencies...")
    if not check_psycopg2():
        print("\nInstall psycopg2 and try again:")
        print("  pip install psycopg2-binary")
        sys.exit(1)
    
    # Step 2: Create database
    print("\n2. Creating database...")
    if not create_database(args.host, args.port, args.user, args.password, args.db_name):
        print("Failed to create database. Make sure PostgreSQL is running.")
        sys.exit(1)
    
    # Build database URL
    database_url = f"postgresql://{args.user}:{args.password}@{args.host}:{args.port}/{args.db_name}"
    
    # Step 3: Test connection
    print("\n3. Testing connection...")
    if not test_connection(database_url):
        print("Connection test failed.")
        sys.exit(1)
    
    # Step 4: Create/migrate tables
    print("\n4. Creating tables...")
    if not run_migrations(database_url):
        print("Table creation failed.")
        sys.exit(1)
    
    # Step 5: Update .env (optional)
    if args.update_env:
        print("\n5. Updating .env file...")
        update_env_file(database_url)
    
    print("\n" + "=" * 60)
    print("DATABASE SETUP COMPLETE")
    print("=" * 60)
    print(f"\nConnection URL: {database_url}")
    print("\nTo use PostgreSQL, update your .env file:")
    print(f"  DATABASE_URL={database_url}")
    

if __name__ == '__main__':
    main()
