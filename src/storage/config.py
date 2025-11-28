"""Storage configuration management."""

import os
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    # Load .env from project root
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, skip loading .env
    pass


@dataclass
class StorageConfig:
    """Configuration for storage backends."""
    
    backend_type: str = "local"
    # Local storage config
    local_audio_dir: str = "data/audio"
    local_embeddings_dir: str = "data/embeddings"
    
    # Astra DB config
    astra_db_id: Optional[str] = None
    astra_db_region: Optional[str] = None
    astra_db_keyspace: str = "default_keyspace"
    astra_db_application_token: Optional[str] = None
    astra_db_api_endpoint: Optional[str] = None
    astra_db_secure_bundle_path: Optional[str] = None  # Not used with Data API, kept for compatibility
    
    @classmethod
    def from_env(cls) -> 'StorageConfig':
        """
        Create config from environment variables.
        
        Returns:
            StorageConfig instance
        """
        return cls(
            backend_type=os.getenv('STORAGE_BACKEND', 'local'),
            local_audio_dir=os.getenv('LOCAL_AUDIO_DIR', 'data/audio'),
            local_embeddings_dir=os.getenv('LOCAL_EMBEDDINGS_DIR', 'data/embeddings'),
            astra_db_id=os.getenv('ASTRA_DB_ID'),
            astra_db_region=os.getenv('ASTRA_DB_REGION', 'us-east-1'),
            astra_db_keyspace=os.getenv('ASTRA_DB_KEYSPACE', 'default_keyspace'),
            astra_db_application_token=os.getenv('ASTRA_DB_APPLICATION_TOKEN'),
            astra_db_api_endpoint=os.getenv('ASTRA_DB_API_ENDPOINT'),
            astra_db_secure_bundle_path=os.getenv('ASTRA_DB_SECURE_BUNDLE_PATH'),
        )
    
    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            'backend_type': self.backend_type,
            'local_audio_dir': self.local_audio_dir,
            'local_embeddings_dir': self.local_embeddings_dir,
            'astra_db_id': self.astra_db_id,
            'astra_db_region': self.astra_db_region,
            'astra_db_keyspace': self.astra_db_keyspace,
            'astra_db_application_token': self.astra_db_application_token,
            'astra_db_api_endpoint': self.astra_db_api_endpoint,
            'astra_db_secure_bundle_path': self.astra_db_secure_bundle_path,
        }

