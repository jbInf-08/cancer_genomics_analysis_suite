"""
API Integrations Module

This module provides integration with external genomics and research APIs
for the Cancer Genomics Analysis Suite. It includes clients for major
databases and services used in cancer genomics research.

Features:
- COSMIC (Catalogue of Somatic Mutations in Cancer) data fetching
- ClinVar variant annotation synchronization
- ENCODE (Encyclopedia of DNA Elements) data downloading
- Scopus research literature client
- Rate limiting and error handling
- Data validation and transformation
- Caching and optimization

Modules:
- cosmic_fetcher: COSMIC database integration for somatic mutations
- clinvar_sync: ClinVar database synchronization for clinical variants
- encode_downloader: ENCODE project data download and processing
- scopus_client: Scopus research database integration

Each integration module provides:
- Authentication and API key management
- Rate limiting and retry logic
- Data validation and error handling
- Caching mechanisms
- Batch processing capabilities
- Progress tracking and logging
"""

from .cosmic_fetcher import COSMICFetcher
from .clinvar_sync import ClinVarSync
from .encode_downloader import ENCODEDownloader
from .scopus_client import ScopusClient

__all__ = [
    'COSMICFetcher',
    'ClinVarSync', 
    'ENCODEDownloader',
    'ScopusClient'
]

# Version information
__version__ = '1.0.0'
__author__ = 'Cancer Genomics Analysis Suite Team'
__description__ = 'API integrations for external genomics databases and services'
