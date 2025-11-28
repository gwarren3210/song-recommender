"""Astra DB client wrapper using Data API."""

import os
from typing import Optional
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

try:
    from astrapy import DataAPIClient
    ASTRA_PY_AVAILABLE = True
except ImportError:
    ASTRA_PY_AVAILABLE = False


class AstraClient:
    """
    Wrapper for Astra DB using Data API.
    
    Uses astrapy library for Data API access.
    """
    
    def __init__(
        self,
        database_id: Optional[str] = None,
        region: Optional[str] = None,
        keyspace: Optional[str] = None,
        application_token: Optional[str] = None,
        api_endpoint: Optional[str] = None
    ):
        """
        Initialize Astra DB client using Data API.
        
        Args:
            database_id: Astra database ID
            region: Database region (not used with Data API, but kept for compatibility)
            keyspace: Keyspace name (default: 'default_keyspace')
            application_token: Astra application token
            api_endpoint: API endpoint URL (required for Data API)
        """
        if not ASTRA_PY_AVAILABLE:
            raise ImportError(
                "astrapy is required. Install it with: pip install astrapy"
            )
        
        # Ensure .env is loaded
        try:
            from dotenv import load_dotenv
            env_path = Path(__file__).parent.parent.parent / '.env'
            if env_path.exists():
                load_dotenv(env_path, override=False)
        except ImportError:
            pass
        
        self.database_id = database_id or os.getenv('ASTRA_DB_ID')
        self.region = region or os.getenv('ASTRA_DB_REGION', 'us-east-1')
        self.keyspace = keyspace or os.getenv('ASTRA_DB_KEYSPACE', 'default_keyspace')
        self.application_token = application_token or os.getenv('ASTRA_DB_APPLICATION_TOKEN')
        self.api_endpoint = api_endpoint or os.getenv('ASTRA_DB_API_ENDPOINT')
        
        if not self.application_token:
            raise ValueError("ASTRA_DB_APPLICATION_TOKEN is required. Make sure it's set in your .env file or environment variables.")
        
        if not self.api_endpoint:
            raise ValueError("ASTRA_DB_API_ENDPOINT is required for Data API. Get it from: Astra Dashboard → Database → Connect → API Endpoint")
        
        # Initialize Data API client
        self.client = DataAPIClient(token=self.application_token)
        # Get database - pass keyspace to get_database
        self.database = self.client.get_database(
            api_endpoint=self.api_endpoint,
            keyspace=self.keyspace
        )
    
    def get_database(self):
        """Get the database object for table operations."""
        return self.database
    
    def get_table(self, table_name: str):
        """Get a table object."""
        return self.database.get_table(table_name)
    
    def close(self):
        """Close the connection (Data API is stateless, so this is a no-op)."""
        pass
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
