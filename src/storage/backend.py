"""Abstract base class for storage backends."""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import numpy as np


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.
    
    Provides unified interface for storing and retrieving audio files,
    embeddings, and metadata.
    """
    
    @abstractmethod
    def upload_audio(self, local_path: str, song_id: Optional[str] = None) -> str:
        """
        Upload an audio file.
        
        Args:
            local_path: Local path to audio file
            song_id: Optional song ID (will generate if not provided)
            
        Returns:
            song_id: The song ID (generated or provided)
        """
        pass
    
    @abstractmethod
    def download_audio(self, song_id: str, local_path: str) -> bool:
        """
        Download an audio file.
        
        Args:
            song_id: Song ID
            local_path: Local path to save the file
            
        Returns:
            success: True if successful
        """
        pass
    
    @abstractmethod
    def get_audio_url(self, song_id: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get a URL to access the audio file.
        
        Args:
            song_id: Song ID
            expires_in: URL expiration time in seconds
            
        Returns:
            url: URL string or None if not available
        """
        pass
    
    @abstractmethod
    def delete_audio(self, song_id: str) -> bool:
        """
        Delete an audio file.
        
        Args:
            song_id: Song ID
            
        Returns:
            success: True if successful
        """
        pass
    
    @abstractmethod
    def store_embedding(
        self,
        song_id: str,
        embedding: np.ndarray,
        model_name: str = "laion/clap-htsat-unfused"
    ) -> bool:
        """
        Store an embedding vector.
        
        Args:
            song_id: Song ID
            embedding: Embedding vector (numpy array)
            model_name: Name of the model used
            
        Returns:
            success: True if successful
        """
        pass
    
    @abstractmethod
    def get_embedding(self, song_id: str) -> Optional[np.ndarray]:
        """
        Get an embedding vector.
        
        Args:
            song_id: Song ID
            
        Returns:
            embedding: Numpy array or None if not found
        """
        pass
    
    @abstractmethod
    def search_similar(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        threshold: Optional[float] = None
    ) -> List[Dict]:
        """
        Search for similar embeddings.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            threshold: Minimum similarity threshold (optional)
            
        Returns:
            List of dictionaries with song_id and similarity score
        """
        pass
    
    @abstractmethod
    def store_metadata(self, song_id: str, metadata: Dict) -> bool:
        """
        Store song metadata.
        
        Args:
            song_id: Song ID
            metadata: Metadata dictionary
            
        Returns:
            success: True if successful
        """
        pass
    
    @abstractmethod
    def get_metadata(self, song_id: str) -> Optional[Dict]:
        """
        Get song metadata.
        
        Args:
            song_id: Song ID
            
        Returns:
            metadata: Dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def list_songs(
        self,
        filters: Optional[Dict] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None
    ) -> List[Dict]:
        """
        List songs with optional filters and pagination.
        
        Args:
            filters: Optional filters (e.g., {'artist': 'Taylor Swift'})
            limit: Maximum number of songs to return
            skip: Number of songs to skip (for pagination)
            
        Returns:
            List of song dictionaries
        """
        pass
    
    @abstractmethod
    def find_song_id(
        self,
        song_name: Optional[str] = None,
        song_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Find song_id by searching through all songs.
        
        Efficiently searches through all songs with minimal data transfer.
        Stops as soon as a match is found.
        
        Args:
            song_name: Song name to search for
            song_path: Path to song file
            
        Returns:
            song_id if found, None otherwise
        """
        pass

