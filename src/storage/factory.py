"""Factory for creating storage backends."""

from typing import Optional
from src.storage.backend import StorageBackend
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
        
    Raises:
        ValueError: If backend_type is not supported
    """
    if config is None:
        config = StorageConfig.from_env()
    
    backend_type = config.backend_type.lower()
    
    if backend_type == "postgres" or backend_type == "neon":
        from src.storage.postgres import PostgresStorageBackend
        return PostgresStorageBackend(config)
    else:
        raise ValueError(
            f"Unsupported backend_type: {backend_type}. "
            "Supported types: 'postgres', 'neon'"
        )

