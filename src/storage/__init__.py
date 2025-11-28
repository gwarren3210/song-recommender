"""Storage abstraction layer for audio files and embeddings."""

from src.storage.backend import StorageBackend
from src.storage.astra import AstraStorageBackend
from src.storage.factory import create_storage_backend
from src.storage.config import StorageConfig

__all__ = [
    'StorageBackend',
    'AstraStorageBackend',
    'create_storage_backend',
    'StorageConfig',
]

