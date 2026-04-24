"""
Article Manager Module

This module provides comprehensive functionality for managing and analyzing
scientific articles in a database system for cancer genomics research.

Main Components:
- ArticleDatabaseManager: Core article database management class
- ArticleMetadata: Data class for storing article information
- Advanced search and filtering capabilities
- Collection and tag management
- Topic modeling and similarity analysis
- Interactive dashboard for article management
"""

from .article_db import (
    ArticleDatabaseManager,
    ArticleMetadata,
    create_mock_articles
)
from .manager_dash import create_manager_dashboard

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"

__all__ = [
    'ArticleDatabaseManager',
    'ArticleMetadata',
    'create_mock_articles',
    'create_manager_dashboard'
]

# Module metadata
MODULE_INFO = {
    'name': 'Article Manager',
    'version': __version__,
    'description': 'Comprehensive article database management and analysis for cancer genomics research',
    'features': [
        'Advanced article database management',
        'Full-text search and filtering',
        'Collection and tag organization',
        'Article similarity analysis',
        'Topic modeling and clustering',
        'Citation tracking and analysis',
        'Interactive dashboard interface',
        'Export capabilities (CSV, JSON, Excel)',
        'Statistics and analytics',
        'Search history tracking'
    ],
    'database_features': [
        'SQLite database with full-text search',
        'Article metadata management',
        'Tag and collection organization',
        'Citation relationship tracking',
        'Search history logging',
        'Performance optimization with indexes'
    ],
    'analytics_features': [
        'TF-IDF based similarity analysis',
        'Latent Dirichlet Allocation (LDA) topic modeling',
        'Article clustering and grouping',
        'Citation network analysis',
        'Publication trend analysis',
        'Journal and author statistics'
    ],
    'dependencies': [
        'sqlite3',
        'pandas',
        'numpy',
        'scikit-learn',
        'networkx',
        'json',
        'datetime'
    ]
}
