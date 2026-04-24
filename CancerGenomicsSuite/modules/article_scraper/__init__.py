"""
Article Scraper Module

This module provides comprehensive functionality for scraping and analyzing
scientific articles from various sources in cancer genomics research.

Main Components:
- ArticleScraper: Core article scraping and management class
- Article: Data class for storing article information
- Multiple source support (PubMed, arXiv, Google Scholar, RSS feeds)
- Database storage and retrieval
- Search and export capabilities
- Interactive dashboard for article management
"""

from .scraper import (
    ArticleScraper,
    Article,
    create_mock_articles
)
from .scraper_dash import create_scraper_dashboard

__version__ = "1.0.0"
__author__ = "Cancer Genomics Analysis Suite"

__all__ = [
    'ArticleScraper',
    'Article',
    'create_mock_articles',
    'create_scraper_dashboard'
]

# Module metadata
MODULE_INFO = {
    'name': 'Article Scraper',
    'version': __version__,
    'description': 'Comprehensive article scraping and management for cancer genomics research',
    'features': [
        'Multi-source article scraping (PubMed, arXiv, Google Scholar, RSS)',
        'Article data management and storage',
        'Advanced search and filtering capabilities',
        'Database integration with SQLite',
        'Export functionality (CSV, JSON, Excel)',
        'Interactive dashboard for article management',
        'Rate limiting and error handling',
        'Article deduplication and validation'
    ],
    'supported_sources': [
        'PubMed (via E-utilities API)',
        'arXiv (via API)',
        'Google Scholar (basic scraping)',
        'RSS Feeds',
        'Custom web scraping'
    ],
    'export_formats': [
        'CSV',
        'JSON',
        'Excel',
        'Database (SQLite)'
    ],
    'dependencies': [
        'requests',
        'pandas',
        'beautifulsoup4',
        'feedparser',
        'lxml',
        'sqlite3'
    ]
}
