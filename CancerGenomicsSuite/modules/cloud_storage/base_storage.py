"""
Base storage client interface
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Union, BinaryIO
from dataclasses import dataclass
from datetime import datetime


@dataclass
class StorageObject:
    """Represents a storage object"""
    key: str
    size: int
    last_modified: datetime
    etag: Optional[str] = None
    content_type: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class UploadResult:
    """Result of an upload operation"""
    key: str
    etag: str
    size: int
    last_modified: datetime


class BaseStorageClient(ABC):
    """Base class for cloud storage clients"""
    
    def __init__(self, bucket_name: str, region: str):
        self.bucket_name = bucket_name
        self.region = region
    
    @abstractmethod
    def upload_file(
        self,
        file_path: str,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> UploadResult:
        """
        Upload a file to storage
        
        Args:
            file_path: Local path to the file
            object_key: Key for the object in storage
            content_type: MIME type of the file
            metadata: Additional metadata
            
        Returns:
            Upload result
        """
        pass
    
    @abstractmethod
    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> UploadResult:
        """
        Upload a file object to storage
        
        Args:
            file_obj: File-like object
            object_key: Key for the object in storage
            content_type: MIME type of the file
            metadata: Additional metadata
            
        Returns:
            Upload result
        """
        pass
    
    @abstractmethod
    def download_file(
        self,
        object_key: str,
        file_path: str
    ) -> None:
        """
        Download a file from storage
        
        Args:
            object_key: Key of the object to download
            file_path: Local path to save the file
        """
        pass
    
    @abstractmethod
    def download_fileobj(
        self,
        object_key: str,
        file_obj: BinaryIO
    ) -> None:
        """
        Download a file object from storage
        
        Args:
            object_key: Key of the object to download
            file_obj: File-like object to write to
        """
        pass
    
    @abstractmethod
    def delete_object(self, object_key: str) -> None:
        """
        Delete an object from storage
        
        Args:
            object_key: Key of the object to delete
        """
        pass
    
    @abstractmethod
    def list_objects(
        self,
        prefix: Optional[str] = None,
        max_keys: Optional[int] = None
    ) -> List[StorageObject]:
        """
        List objects in storage
        
        Args:
            prefix: Prefix to filter objects
            max_keys: Maximum number of objects to return
            
        Returns:
            List of storage objects
        """
        pass
    
    @abstractmethod
    def object_exists(self, object_key: str) -> bool:
        """
        Check if an object exists in storage
        
        Args:
            object_key: Key of the object to check
            
        Returns:
            True if object exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_object_metadata(self, object_key: str) -> Optional[StorageObject]:
        """
        Get metadata for an object
        
        Args:
            object_key: Key of the object
            
        Returns:
            Storage object metadata or None if not found
        """
        pass
    
    @abstractmethod
    def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600,
        method: str = 'GET'
    ) -> str:
        """
        Generate a presigned URL for an object
        
        Args:
            object_key: Key of the object
            expiration: URL expiration time in seconds
            method: HTTP method ('GET' or 'PUT')
            
        Returns:
            Presigned URL
        """
        pass
    
    @abstractmethod
    def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[dict] = None
    ) -> UploadResult:
        """
        Copy an object within the same bucket
        
        Args:
            source_key: Source object key
            dest_key: Destination object key
            metadata: Additional metadata for the copy
            
        Returns:
            Upload result
        """
        pass
