"""
Google Cloud Storage Client
"""

import os
from datetime import datetime, timedelta
from typing import BinaryIO, List, Optional

try:
    from google.cloud import storage
    from google.cloud.exceptions import GoogleCloudError, NotFound

    GCS_AVAILABLE = True
except ImportError:
    # google-cloud-storage is an optional extra ([gcs]). It used to be imported
    # unconditionally, and the package __init__ imports this module first -- so
    # without the Google SDK nothing in cloud_storage loaded, including the S3
    # client and base_storage, which does not use it at all. Now this module
    # always imports, and GCSStorageClient says what is missing when built.
    storage = None
    GCS_AVAILABLE = False

    class GoogleCloudError(Exception):
        """Stand-in so the except clauses below still name a real class.

        Deliberately a distinct class rather than an alias of Exception, which
        would turn every `except GoogleCloudError` into a catch-all.
        """

    class NotFound(GoogleCloudError):
        """Stand-in for google.cloud.exceptions.NotFound."""


from .base_storage import BaseStorageClient, StorageObject, UploadResult


class GCSStorageClient(BaseStorageClient):
    """Google Cloud Storage client implementation"""

    def __init__(
        self,
        bucket_name: str,
        region: str = "us-central1",
        credentials: Optional[dict] = None,
    ):
        if not GCS_AVAILABLE:
            raise ImportError(
                "GCSStorageClient needs the google-cloud-storage package, which is "
                "not installed. Install it with: "
                "pip install 'cancer-genomics-analysis-suite[gcs]'"
            )

        super().__init__(bucket_name, region)

        # Initialize GCS client
        if credentials:
            # Create client with explicit credentials
            from google.oauth2 import service_account

            creds = service_account.Credentials.from_service_account_info(credentials)
            self.client = storage.Client(credentials=creds)
        else:
            # Use default credentials (environment variables, service account, etc.)
            self.client = storage.Client()

        self.bucket = self.client.bucket(bucket_name)

    def upload_file(
        self,
        file_path: str,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> UploadResult:
        """Upload a file to GCS"""
        try:
            blob = self.bucket.blob(object_key)

            # Set content type if provided
            if content_type:
                blob.content_type = content_type

            # Set metadata if provided
            if metadata:
                blob.metadata = metadata

            # Upload file
            blob.upload_from_filename(file_path)

            # Reload to get updated metadata
            blob.reload()

            return UploadResult(
                key=object_key,
                etag=blob.etag,
                size=blob.size,
                last_modified=blob.updated,
            )

        except GoogleCloudError as e:
            raise Exception(f"Failed to upload file to GCS: {e}")

    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> UploadResult:
        """Upload a file object to GCS"""
        try:
            blob = self.bucket.blob(object_key)

            # Set content type if provided
            if content_type:
                blob.content_type = content_type

            # Set metadata if provided
            if metadata:
                blob.metadata = metadata

            # Upload file object
            blob.upload_from_file(file_obj)

            # Reload to get updated metadata
            blob.reload()

            return UploadResult(
                key=object_key,
                etag=blob.etag,
                size=blob.size,
                last_modified=blob.updated,
            )

        except GoogleCloudError as e:
            raise Exception(f"Failed to upload file object to GCS: {e}")

    def download_file(self, object_key: str, file_path: str) -> None:
        """Download a file from GCS"""
        try:
            blob = self.bucket.blob(object_key)

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            blob.download_to_filename(file_path)

        except NotFound:
            raise Exception(f"Object not found: {object_key}")
        except GoogleCloudError as e:
            raise Exception(f"Failed to download file from GCS: {e}")

    def download_fileobj(self, object_key: str, file_obj: BinaryIO) -> None:
        """Download a file object from GCS"""
        try:
            blob = self.bucket.blob(object_key)
            blob.download_to_file(file_obj)

        except NotFound:
            raise Exception(f"Object not found: {object_key}")
        except GoogleCloudError as e:
            raise Exception(f"Failed to download file object from GCS: {e}")

    def delete_object(self, object_key: str) -> None:
        """Delete an object from GCS"""
        try:
            blob = self.bucket.blob(object_key)
            blob.delete()

        except GoogleCloudError as e:
            raise Exception(f"Failed to delete object from GCS: {e}")

    def list_objects(
        self, prefix: Optional[str] = None, max_keys: Optional[int] = None
    ) -> List[StorageObject]:
        """List objects in GCS"""
        try:
            blobs = self.bucket.list_blobs(prefix=prefix, max_results=max_keys)

            objects = []
            for blob in blobs:
                objects.append(
                    StorageObject(
                        key=blob.name,
                        size=blob.size,
                        last_modified=blob.updated,
                        etag=blob.etag,
                        content_type=blob.content_type,
                        metadata=blob.metadata,
                    )
                )

            return objects

        except GoogleCloudError as e:
            raise Exception(f"Failed to list objects in GCS: {e}")

    def object_exists(self, object_key: str) -> bool:
        """Check if an object exists in GCS"""
        try:
            blob = self.bucket.blob(object_key)
            return blob.exists()

        except GoogleCloudError as e:
            raise Exception(f"Failed to check object existence in GCS: {e}")

    def get_object_metadata(self, object_key: str) -> Optional[StorageObject]:
        """Get metadata for an object in GCS"""
        try:
            blob = self.bucket.blob(object_key)

            if not blob.exists():
                return None

            blob.reload()

            return StorageObject(
                key=object_key,
                size=blob.size,
                last_modified=blob.updated,
                etag=blob.etag,
                content_type=blob.content_type,
                metadata=blob.metadata,
            )

        except GoogleCloudError as e:
            raise Exception(f"Failed to get object metadata from GCS: {e}")

    def generate_presigned_url(
        self, object_key: str, expiration: int = 3600, method: str = "GET"
    ) -> str:
        """Generate a presigned URL for an object in GCS"""
        try:
            blob = self.bucket.blob(object_key)

            if method.upper() == "GET":
                url = blob.generate_signed_url(
                    expiration=datetime.utcnow() + timedelta(seconds=expiration),
                    method="GET",
                )
            elif method.upper() == "PUT":
                url = blob.generate_signed_url(
                    expiration=datetime.utcnow() + timedelta(seconds=expiration),
                    method="PUT",
                )
            else:
                raise ValueError(f"Unsupported method: {method}")

            return url

        except GoogleCloudError as e:
            raise Exception(f"Failed to generate presigned URL for GCS: {e}")

    def copy_object(
        self, source_key: str, dest_key: str, metadata: Optional[dict] = None
    ) -> UploadResult:
        """Copy an object within the same GCS bucket"""
        try:
            source_blob = self.bucket.blob(source_key)
            dest_blob = self.bucket.copy_blob(source_blob, self.bucket, dest_key)

            # Update metadata if provided
            if metadata:
                dest_blob.metadata = metadata
                dest_blob.patch()

            # Reload to get updated metadata
            dest_blob.reload()

            return UploadResult(
                key=dest_key,
                etag=dest_blob.etag,
                size=dest_blob.size,
                last_modified=dest_blob.updated,
            )

        except GoogleCloudError as e:
            raise Exception(f"Failed to copy object in GCS: {e}")
