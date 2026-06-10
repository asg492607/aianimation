import os
import uuid
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, BinaryIO

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageProvider(ABC):
    @abstractmethod
    async def upload(self, file_data: bytes, key: str, content_type: str) -> str:
        """Upload file and return public URL"""
        pass

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download file by key"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete file by key"""
        pass

    @abstractmethod
    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Get a (possibly signed) URL for a key"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    def generate_key(self, folder: str, filename: str) -> str:
        ext = Path(filename).suffix
        unique_name = f"{uuid.uuid4().hex}{ext}"
        return f"{folder}/{unique_name}"


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: str = settings.LOCAL_STORAGE_PATH):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload(self, file_data: bytes, key: str, content_type: str) -> str:
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file_data)
        logger.info("file_uploaded_locally", key=key, size=len(file_data))
        return f"/media/{key}"

    async def download(self, key: str) -> bytes:
        file_path = self.base_path / key
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        with open(file_path, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> bool:
        file_path = self.base_path / key
        if file_path.exists():
            file_path.unlink()
            logger.info("file_deleted_locally", key=key)
            return True
        return False

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        return f"/media/{key}"

    async def exists(self, key: str) -> bool:
        return (self.base_path / key).exists()


class S3StorageProvider(StorageProvider):
    def __init__(self):
        import boto3
        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket = settings.AWS_S3_BUCKET

    async def upload(self, file_data: bytes, key: str, content_type: str) -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        import io
        await loop.run_in_executor(
            None,
            lambda: self.client.upload_fileobj(
                io.BytesIO(file_data),
                self.bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            ),
        )
        return f"https://{self.bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

    async def download(self, key: str) -> bytes:
        import asyncio
        import io
        loop = asyncio.get_event_loop()
        buf = io.BytesIO()
        await loop.run_in_executor(None, lambda: self.client.download_fileobj(self.bucket, key, buf))
        return buf.getvalue()

    async def delete(self, key: str) -> bool:
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self.client.delete_object(Bucket=self.bucket, Key=key))
        return True

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        url = await loop.run_in_executor(
            None,
            lambda: self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            ),
        )
        return url

    async def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


class MinIOStorageProvider(StorageProvider):
    def __init__(self):
        from minio import Minio
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except Exception as e:
            logger.error("minio_bucket_error", error=str(e))

    async def upload(self, file_data: bytes, key: str, content_type: str) -> str:
        import asyncio
        import io
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.client.put_object(
                self.bucket,
                key,
                io.BytesIO(file_data),
                len(file_data),
                content_type=content_type,
            ),
        )
        return f"http://{settings.MINIO_ENDPOINT}/{self.bucket}/{key}"

    async def download(self, key: str) -> bytes:
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: self.client.get_object(self.bucket, key))
        return response.read()

    async def delete(self, key: str) -> bool:
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self.client.remove_object(self.bucket, key))
        return True

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        import asyncio
        from datetime import timedelta
        loop = asyncio.get_event_loop()
        url = await loop.run_in_executor(
            None,
            lambda: self.client.presigned_get_object(self.bucket, key, expires=timedelta(seconds=expires_in)),
        )
        return url

    async def exists(self, key: str) -> bool:
        try:
            self.client.stat_object(self.bucket, key)
            return True
        except Exception:
            return False


def get_storage_provider() -> StorageProvider:
    backend = settings.STORAGE_BACKEND.lower()
    if backend == "s3":
        return S3StorageProvider()
    elif backend == "minio":
        return MinIOStorageProvider()
    return LocalStorageProvider()


storage_provider: StorageProvider = get_storage_provider()
