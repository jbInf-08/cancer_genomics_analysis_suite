"""
AWS S3 Storage Client
"""

import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import List, Optional, Union, BinaryIO
from datetime import datetime
from .base_storage import BaseStorageClient, StorageObject, UploadResult


class S3StorageClient(BaseStorageClient):
    """AWS S3 storage client implementation"""
    
    def __init__(
        self,
        bucket_name: str,
        region: str = 'us-west-2',
        credentials: Optional[dict] = None
    ):
        super().__init__(bucket_name, region)
        
        # Initialize S3 client
        if credentials:
            self.s3_client = boto3.client(
                's3',
                region_name=region,
                aws_access_key_id=credentials.get('access_key_id'),
                aws_secret_access_key=credentials.get('secret_access_key'),
                aws_session_token=credentials.get('session_token')
            )
        else:
            # Use default credentials (environment variables, IAM roles, etc.)
            self.s3_client = boto3.client('s3', region_name=region)
        
        self.s3_resource = boto3.resource('s3', region_name=region)
        self.bucket = self.s3_resource.Bucket(bucket_name)
    
    def upload_file(
        self,
        file_path: str,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> UploadResult:
        """Upload a file to S3"""
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Upload file
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args
            )
            
            # Get object metadata
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            return UploadResult(
                key=object_key,
                etag=response['ETag'].strip('"'),
                size=file_size,
                last_modified=response['LastModified']
            )
            
        except ClientError as e:
            raise Exception(f"Failed to upload file to S3: {e}")
        except NoCredentialsError:
            raise Exception("AWS credentials not found")
    
    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> UploadResult:
        """Upload a file object to S3"""
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Upload file object
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args
            )
            
            # Get object metadata
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            return UploadResult(
                key=object_key,
                etag=response['ETag'].strip('"'),
                size=response['ContentLength'],
                last_modified=response['LastModified']
            )
            
        except ClientError as e:
            raise Exception(f"Failed to upload file object to S3: {e}")
        except NoCredentialsError:
            raise Exception("AWS credentials not found")
    
    def download_file(
        self,
        object_key: str,
        file_path: str
    ) -> None:
        """Download a file from S3"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            self.s3_client.download_file(
                self.bucket_name,
                object_key,
                file_path
            )
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise Exception(f"Object not found: {object_key}")
            raise Exception(f"Failed to download file from S3: {e}")
        except NoCredentialsError:
            raise Exception("AWS credentials not found")
    
    def download_fileobj(
        self,
        object_key: str,
        file_obj: BinaryIO
    ) -> None:
        """Download a file object from S3"""
        try:
            self.s3_client.download_fileobj(
                self.bucket_name,
                object_key,
                file_obj
            )
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise Exception(f"Object not found: {object_key}")
            raise Exception(f"Failed to download file object from S3: {e}")
        except NoCredentialsError:
            raise Exception("AWS credentials not found")
    
    def delete_object(self, object_key: str) -> None:
        """Delete an object from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
        except ClientError as e:
            raise Exception(f"Failed to delete object from S3: {e}")
        except NoCredentialsError:
            raise Exception("AWS credentials not found")
    
    def list_objects(
        self,
        prefix: Optional[str] = None,
        max_keys: Optional[int] = None
    ) -> List[StorageObject]:
        """List objects in S3"""
        try:
            kwargs = {'Bucket': self.bucket_name}
            if prefix:
                kwargs['Prefix'] = prefix
            if max_keys:
                kwargs['MaxKeys'] = max_keys
            
            response = self.s3_client.list_objects_v2(**kwargs)
            
            objects = []
            for obj in response.get('Contents', []):
                objects.append(StorageObject(
                    key=obj['Key'],
                    size=obj['Size'],
                    last_modified=obj['LastModified'],
                    etag=obj['ETag'].strip('"')
                ))
            
            return objects
            
        except ClientError as e:
            raise Exception(f"Failed to list objects in S3: {e}")
        except NoCredentialsError:
            raise Exception("AWS credentials not found")
    
    def object_exists(self, object_key: str) -> bool:
        """Check if an object exists in S3"""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise Exception(f"Failed to check object existence in S3: {e}")
        except NoCredentialsError:
            raise Exception("AWS credentials not found")
    
    def get_object_metadata(self, object_key: str) -> Optional[StorageObject]:
        """Get metadata for an object in S3"""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            return StorageObject(
                key=object_key,
                size=response['ContentLength'],
                last_modified=response['LastModified'],
                etag=response['ETag'].strip('"'),
                content_type=response.get('ContentType'),
                metadata=response.get('Metadata', {})
            )
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            raise Exception(f"Failed to get object metadata from S3: {e}")
        except NoCredentialsError:
            raise Exception("AWS credentials not found")
    
    def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600,
        method: str = 'GET'
    ) -> str:
        """Generate a presigned URL for an object in S3"""
        try:
            if method.upper() == 'GET':
                operation = 'get_object'
            elif method.upper() == 'PUT':
                operation = 'put_object'
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            url = self.s3_client.generate_presigned_url(
                operation,
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expiration
            )
            
            return url
            
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL for S3: {e}")
        except NoCredentialsError:
            raise Exception("AWS credentials not found")
    
    def copy_object(
        self,
        source_key: str,
        dest_key: str,
        metadata: Optional[dict] = None
    ) -> UploadResult:
        """Copy an object within the same S3 bucket"""
        try:
            copy_source = {
                'Bucket': self.bucket_name,
                'Key': source_key
            }
            
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
                extra_args['MetadataDirective'] = 'REPLACE'
            
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=dest_key,
                **extra_args
            )
            
            # Get object metadata
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=dest_key
            )
            
            return UploadResult(
                key=dest_key,
                etag=response['ETag'].strip('"'),
                size=response['ContentLength'],
                last_modified=response['LastModified']
            )
            
        except ClientError as e:
            raise Exception(f"Failed to copy object in S3: {e}")
        except NoCredentialsError:
            raise Exception("AWS credentials not found")
