"""Storage adapters for file and image storage."""

from .image_storage import (
    LocalStorageAdapter,
    S3StorageAdapter,
    StorageAdapter,
    download_image,
    get_storage_adapter,
    storage_adapter,
)

__all__ = [
    "StorageAdapter",
    "LocalStorageAdapter",
    "S3StorageAdapter",
    "get_storage_adapter",
    "download_image",
    "storage_adapter",
]
