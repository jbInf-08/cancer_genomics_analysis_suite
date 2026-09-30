"""
Cloud Storage Module for Cancer Genomics Analysis Suite

This module provides unified interfaces for cloud storage operations
across AWS S3 and Google Cloud Storage (GCS).

Each provider's SDK is optional: install `[s3]` for boto3 and `[gcs]` for
google-cloud-storage. The package and both client classes import without
either; constructing a client whose SDK is missing raises ImportError naming
the extra to install. S3_AVAILABLE and GCS_AVAILABLE report which are usable.
"""

from .gcs_client import GCS_AVAILABLE, GCSStorageClient
from .s3_client import S3_AVAILABLE, S3StorageClient
from .storage_factory import StorageFactory

__all__ = [
    "S3StorageClient",
    "GCSStorageClient",
    "StorageFactory",
    "S3_AVAILABLE",
    "GCS_AVAILABLE",
]
