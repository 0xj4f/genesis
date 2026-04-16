"""Pluggable storage backend for file uploads (avatars, etc.)."""

import os
import shutil
from abc import ABC, abstractmethod

from app.config import get_settings

settings = get_settings()


class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        """Upload data to storage. Returns the public URL."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a file from storage."""
        ...


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: str, base_url: str):
        self.base_dir = base_dir
        self.base_url = base_url.rstrip("/")

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        file_path = os.path.join(self.base_dir, key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(data)
        return f"{self.base_url}/{key}"

    async def delete(self, key: str) -> None:
        file_path = os.path.join(self.base_dir, key)
        if os.path.exists(file_path):
            os.remove(file_path)


class S3StorageBackend(StorageBackend):
    def __init__(self, bucket: str, region: str | None = None, endpoint_url: str | None = None):
        import boto3
        kwargs = {}
        if region:
            kwargs["region_name"] = region
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self.s3 = boto3.client("s3", **kwargs)
        self.bucket = bucket

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        if hasattr(self.s3, "_endpoint"):
            base = self.s3._endpoint.host
            return f"{base}/{self.bucket}/{key}"
        return f"https://{self.bucket}.s3.amazonaws.com/{key}"

    async def delete(self, key: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=key)


def get_storage_backend() -> StorageBackend:
    """Factory: returns the configured storage backend."""
    if settings.STORAGE_BACKEND == "s3" and settings.S3_BUCKET:
        return S3StorageBackend(
            bucket=settings.S3_BUCKET,
            region=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL,
        )
    return LocalStorageBackend(
        base_dir=settings.UPLOAD_DIR,
        base_url=settings.OAUTH_ISSUER,
    )
