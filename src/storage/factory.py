"""Factory for creating storage backends."""

from typing import Optional
from src.storage.backend import StorageBackend
from src.storage.astra import AstraStorageBackend
from src.storage.config import StorageConfig


def create_storage_backend(
    config: Optional[StorageConfig] = None
) -> StorageBackend:
    """
    Create a storage backend instance.
    
    Args:
        config: StorageConfig instance (if None, loads from environment)
        
    Returns:
        StorageBackend instance
    """
    if config is None:
        config = StorageConfig.from_env()
    return AstraStorageBackend(config)

