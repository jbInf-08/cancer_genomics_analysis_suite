"""
Storage Factory for creating cloud storage clients
"""

import os
from typing import Optional, Union
from .s3_client import S3StorageClient
from .gcs_client import GCSStorageClient
from .base_storage import BaseStorageClient


class StorageFactory:
    """Factory class for creating cloud storage clients"""
    
    @staticmethod
    def create_storage_client(
        provider: str,
        bucket_name: str,
        region: Optional[str] = None,
        credentials: Optional[dict] = None
    ) -> BaseStorageClient:
        """
        Create a storage client based on the provider
        
        Args:
            provider: Storage provider ('s3' or 'gcs')
            bucket_name: Name of the storage bucket
            region: Region for the storage (optional)
            credentials: Credentials for authentication (optional)
            
        Returns:
            Storage client instance
            
        Raises:
            ValueError: If provider is not supported
        """
        provider = provider.lower()
        
        if provider == 's3':
            return S3StorageClient(
                bucket_name=bucket_name,
                region=region or os.getenv('AWS_REGION', 'us-west-2'),
                credentials=credentials
            )
        elif provider == 'gcs':
            return GCSStorageClient(
                bucket_name=bucket_name,
                region=region or os.getenv('GCP_REGION', 'us-central1'),
                credentials=credentials
            )
        else:
            raise ValueError(f"Unsupported storage provider: {provider}")
    
    @staticmethod
    def create_storage_client_from_env() -> Optional[BaseStorageClient]:
        """
        Create a storage client from environment variables
        
        Returns:
            Storage client instance or None if no provider is configured
        """
        # Check for S3 configuration
        s3_bucket = os.getenv('S3_BUCKET_NAME')
        if s3_bucket:
            return StorageFactory.create_storage_client(
                provider='s3',
                bucket_name=s3_bucket
            )
        
        # Check for GCS configuration
        gcs_bucket = os.getenv('GCS_BUCKET_NAME')
        if gcs_bucket:
            return StorageFactory.create_storage_client(
                provider='gcs',
                bucket_name=gcs_bucket
            )
        
        return None
