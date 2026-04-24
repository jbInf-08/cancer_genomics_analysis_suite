# config/__init__.py
"""
Cancer Genomics Analysis Suite - Configuration Package

This package provides comprehensive configuration management for the cancer
genomics analysis suite. It includes settings for database connections,
external APIs, security, logging, and feature flags.

Usage:
    from config import settings
    print(settings.app_name)
    
    # Access specific configuration sections
    db_url = settings.database.url
    api_key = settings.external_apis.cosmic_api_key
"""

import os
import logging
from typing import Optional, Dict, Any

# Import the main settings instance
try:
    from .settings import settings, configure_logging
except ImportError as e:
    # Fallback for when dependencies are not available
    logging.warning(f"Could not import settings: {e}")
    
    # Create a minimal settings object for basic functionality
    class MinimalSettings:
        def __init__(self):
            self.app_name = "Cancer Genomics Analysis Suite"
            self.app_version = "1.0.0"
            self.host = "0.0.0.0"
            self.port = 8050
            self.dash_debug_mode = True
            self.flask_env = "development"
            self.testing = False
            
            # Minimal database settings
            self.database = type('Database', (), {
                'url': 'sqlite:///cancer_genomics.db',
                'pool_size': 10,
                'max_overflow': 20
            })()
            
            # Minimal security settings
            self.security = type('Security', (), {
                'secret_key': 'dev-secret-key-change-in-production',
                'enable_authentication': False
            })()
            
            # Minimal feature flags
            self.features = type('Features', (), {
                'enable_gene_expression_analysis': True,
                'enable_mutation_analysis': True,
                'enable_machine_learning': True,
                'enable_pathway_analysis': True,
                'enable_multi_omics_integration': True
            })()
            
            # Minimal external APIs
            self.external_apis = type('ExternalAPIs', (), {
                'cosmic_api_key': os.getenv('COSMIC_API_KEY', ''),
                'cosmic_api_token': os.getenv('COSMIC_API_TOKEN', ''),
                'scopus_api_key': os.getenv('SCOPUS_API_KEY', ''),
                'encode_api_base': os.getenv('ENCODE_API_BASE', 'https://www.encodeproject.org'),
                'ncbi_api_key': os.getenv('NCBI_API_KEY', ''),
                'ensembl_api_url': 'https://rest.ensembl.org',
                'uniprot_api_url': 'https://www.uniprot.org',
                'pubmed_api_url': 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'
            })()
        
        def is_development(self) -> bool:
            return self.flask_env.lower() == "development"
        
        def is_production(self) -> bool:
            return self.flask_env.lower() == "production"
        
        def is_testing(self) -> bool:
            return self.testing
    
    settings = MinimalSettings()
    
    def configure_logging():
        """Minimal logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

# Environment detection
def get_environment() -> str:
    """Get the current environment (development, production, testing)."""
    return os.getenv('FLASK_ENV', 'development').lower()

def is_development() -> bool:
    """Check if running in development mode."""
    return get_environment() == 'development'

def is_production() -> bool:
    """Check if running in production mode."""
    return get_environment() == 'production'

def is_testing() -> bool:
    """Check if running in testing mode."""
    return get_environment() == 'testing'

# Configuration validation
def validate_configuration() -> Dict[str, Any]:
    """
    Validate the current configuration and return validation results.
    
    Returns:
        Dict with validation results including errors, warnings, and status
    """
    results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'info': []
    }
    
    try:
        # Check database configuration
        if hasattr(settings, 'database'):
            if not hasattr(settings.database, 'url') or not settings.database.url:
                results['errors'].append("Database URL is not configured")
                results['valid'] = False
            else:
                results['info'].append(f"Database configured: {settings.database.url[:20]}...")
        
        # Check security configuration
        if hasattr(settings, 'security'):
            if settings.security.secret_key == 'dev-secret-key-change-in-production':
                if is_production():
                    results['errors'].append("Production secret key not configured")
                    results['valid'] = False
                else:
                    results['warnings'].append("Using development secret key")
        
        # Check external API configurations
        if hasattr(settings, 'external_apis'):
            api_configs = [
                ('ensembl_api_url', 'Ensembl API'),
                ('uniprot_api_url', 'UniProt API'),
                ('pubmed_api_url', 'PubMed API')
            ]
            
            for attr, name in api_configs:
                if hasattr(settings.external_apis, attr):
                    url = getattr(settings.external_apis, attr)
                    if url:
                        results['info'].append(f"{name} configured: {url}")
                    else:
                        results['warnings'].append(f"{name} URL not configured")
        
        # Check feature flags
        if hasattr(settings, 'features'):
            enabled_features = []
            for attr in dir(settings.features):
                if attr.startswith('enable_') and getattr(settings.features, attr):
                    enabled_features.append(attr.replace('enable_', '').replace('_', ' ').title())
            
            if enabled_features:
                results['info'].append(f"Enabled features: {', '.join(enabled_features)}")
        
        # Check file storage
        if hasattr(settings, 'file_storage'):
            upload_folder = getattr(settings.file_storage, 'upload_folder', 'uploads')
            if not os.path.exists(upload_folder):
                try:
                    os.makedirs(upload_folder, exist_ok=True)
                    results['info'].append(f"Created upload directory: {upload_folder}")
                except Exception as e:
                    results['warnings'].append(f"Could not create upload directory: {e}")
        
    except Exception as e:
        results['errors'].append(f"Configuration validation error: {e}")
        results['valid'] = False
    
    return results

# Configuration utilities
def get_database_url() -> str:
    """Get the database URL for the current environment."""
    if hasattr(settings, 'get_database_url'):
        return settings.get_database_url()
    elif hasattr(settings, 'database') and hasattr(settings.database, 'url'):
        return settings.database.url
    else:
        return 'sqlite:///cancer_genomics.db'

def get_redis_url() -> Optional[str]:
    """Get the Redis URL if Redis is enabled."""
    if hasattr(settings, 'get_redis_url'):
        return settings.get_redis_url()
    elif hasattr(settings, 'redis') and hasattr(settings.redis, 'enabled'):
        if settings.redis.enabled and hasattr(settings.redis, 'url'):
            return settings.redis.url
    return None

def get_feature_status(feature_name: str) -> bool:
    """Get the status of a specific feature flag."""
    if hasattr(settings, 'get_feature_status'):
        return settings.get_feature_status(feature_name)
    elif hasattr(settings, 'features'):
        return getattr(settings.features, feature_name, False)
    return False

def get_api_config(service: str) -> Dict[str, Any]:
    """
    Get configuration for a specific external API service.
    
    Args:
        service: Name of the API service (e.g., 'ensembl', 'uniprot', 'pubmed')
        
    Returns:
        Dict with API configuration
    """
    if not hasattr(settings, 'external_apis'):
        return {}
    
    api_config = {}
    service_attrs = {
        'ensembl': ['ensembl_api_url', 'ensembl_api_timeout', 'ensembl_api_rate_limit'],
        'uniprot': ['uniprot_api_url', 'uniprot_api_timeout', 'uniprot_api_rate_limit'],
        'pubmed': ['pubmed_api_url', 'pubmed_api_timeout', 'pubmed_api_rate_limit'],
        'clinvar': ['clinvar_api_url', 'clinvar_api_timeout'],
        'cosmic': ['cosmic_api_url', 'cosmic_api_timeout', 'cosmic_api_key']
    }
    
    if service in service_attrs:
        for attr in service_attrs[service]:
            if hasattr(settings.external_apis, attr):
                api_config[attr] = getattr(settings.external_apis, attr)
    
    return api_config

# Configuration reloading
def reload_configuration():
    """Reload configuration from environment variables and config files."""
    try:
        # Clear any cached settings
        if 'config.settings' in globals():
            import importlib
            importlib.reload(globals()['config.settings'])
        
        # Reconfigure logging
        configure_logging()
        
        logging.info("Configuration reloaded successfully")
        return True
    except Exception as e:
        logging.error(f"Failed to reload configuration: {e}")
        return False

# Export the main components
__all__ = [
    'settings',
    'configure_logging',
    'get_environment',
    'is_development',
    'is_production',
    'is_testing',
    'validate_configuration',
    'get_database_url',
    'get_redis_url',
    'get_feature_status',
    'get_api_config',
    'reload_configuration'
]

# Initialize logging when the package is imported
try:
    configure_logging()
except Exception as e:
    logging.warning(f"Could not configure logging: {e}")

# Log configuration status
logger = logging.getLogger(__name__)
logger.info(f"Configuration package loaded for {settings.app_name} v{settings.app_version}")
logger.info(f"Environment: {get_environment()}")
logger.info(f"Debug mode: {getattr(settings, 'dash_debug_mode', False)}")

# Validate configuration on import
validation_results = validate_configuration()
if not validation_results['valid']:
    logger.error("Configuration validation failed:")
    for error in validation_results['errors']:
        logger.error(f"  - {error}")

if validation_results['warnings']:
    logger.warning("Configuration warnings:")
    for warning in validation_results['warnings']:
        logger.warning(f"  - {warning}")

if validation_results['info']:
    logger.info("Configuration info:")
    for info in validation_results['info']:
        logger.info(f"  - {info}")
