"""
Cloud Storage Module for Cancer Genomics Analysis Suite

This module provides unified interfaces for cloud storage operations
across AWS S3 and Google Cloud Storage (GCS).
"""

from .gcs_client import GCSStorageClient
from .s3_client import S3StorageClient
from .storage_factory import StorageFactory

__all__ = ["S3StorageClient", "GCSStorageClient", "StorageFactory"]
