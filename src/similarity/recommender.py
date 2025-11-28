from typing import Optional
from src.storage.backend import StorageBackend

class Recommender:
    def __init__(self, storage_backend: StorageBackend):
        """        
        Args:
            storage_backend: Storage backend (required)
        """
        self.storage_backend = storage_backend
        self.metadata = []
        self.load_metadata_from_backend()

    def load_metadata_from_backend(self):
        """
        Load metadata from backend.
        
        Note: Metadata is loaded on-demand when needed for recommendations.
        We don't preload all songs to avoid full table scans.
        """
        # Don't preload all songs - load on demand
        self.metadata = []

    def recommend(self, song_name=None, song_path=None, song_id=None, k=5):
        """
        Get recommendations for a song using vector search.
        
        Args:
            song_name: Song name to search for
            song_path: Path to song file
            song_id: Song ID (preferred if available)
            k: Number of recommendations
            
        Returns:
            List of recommendation dictionaries
        """
        # Find song_id if not provided
        if song_id is None:
            song_id = self._find_song_id(song_name, song_path)
        
        if song_id is None:
            print(f"Song '{song_name or song_path}' not found.")
            return []
        
        # Get query embedding
        query_embedding = self.storage_backend.get_embedding(song_id)
        if query_embedding is None:
            print(f"No embedding found for song_id: {song_id}")
            return []
        
        # Search for similar embeddings using vector search
        similar_items = self.storage_backend.search_similar(query_embedding, k=k+1)
        
        # Filter out the query song itself and format results
        recommendations = []
        for item in similar_items:
            if item.get('song_id') != song_id:
                rec = item.get('metadata', {}).copy()
                rec['similarity_score'] = item.get('similarity', 0.0)
                rec['song_id'] = item.get('song_id')
                recommendations.append(rec)
        
        return recommendations[:k]
    
    def _find_song_id(self, song_name=None, song_path=None) -> Optional[str]:
        """
        Find song_id by searching the database.
        
        Uses storage backend's efficient search method that searches
        through all songs with minimal data transfer.
        """
        return self.storage_backend.find_song_id(
            song_name=song_name,
            song_path=song_path
        )
