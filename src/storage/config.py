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
    
    backend_type: str = "postgres"
    # Local storage config
    local_audio_dir: str = "data/audio"
    local_embeddings_dir: str = "data/embeddings"
    
    # Postgres/Neon config
    postgres_host: Optional[str] = None
    postgres_port: Optional[int] = None
    postgres_database: Optional[str] = None
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_sslmode: str = "require"  # Default to require SSL for Neon
    
    @classmethod
    def from_env(cls) -> 'StorageConfig':
        """
        Create config from environment variables.
        
        Returns:
            StorageConfig instance
        """
        postgres_port = os.getenv('POSTGRES_PORT')
        return cls(
            backend_type=os.getenv('STORAGE_BACKEND', 'postgres'),
            local_audio_dir=os.getenv('LOCAL_AUDIO_DIR', 'data/audio'),
            local_embeddings_dir=os.getenv('LOCAL_EMBEDDINGS_DIR', 'data/embeddings'),
            postgres_host=os.getenv('POSTGRES_HOST'),
            postgres_port=int(postgres_port) if postgres_port else None,
            postgres_database=os.getenv('POSTGRES_DATABASE'),
            postgres_user=os.getenv('POSTGRES_USER'),
            postgres_password=os.getenv('POSTGRES_PASSWORD'),
            postgres_sslmode=os.getenv('POSTGRES_SSLMODE', 'require'),
        )
    
    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            'backend_type': self.backend_type,
            'local_audio_dir': self.local_audio_dir,
            'local_embeddings_dir': self.local_embeddings_dir,
            'postgres_host': self.postgres_host,
            'postgres_port': self.postgres_port,
            'postgres_database': self.postgres_database,
            'postgres_user': self.postgres_user,
            'postgres_password': self.postgres_password,
            'postgres_sslmode': self.postgres_sslmode,
        }

