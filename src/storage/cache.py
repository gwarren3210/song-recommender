
from pathlib import Path
from typing import Optional, Any


class StorageCache:
    """
    Local cache for frequently accessed data.
    
    Caches embeddings and metadata to reduce database queries.
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize cache.
        
        Args:
            cache_dir: Cache directory path (default: ~/.song-recommender/cache)
        """
        if cache_dir is None:
            cache_dir = Path.home() / '.song-recommender' / 'cache'
        else:
            cache_dir = Path(cache_dir)
        
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.embeddings_cache = {}
        self.metadata_cache = {}
    
    def get_embedding(self, song_id: str) -> Optional[Any]:
        return self.embeddings_cache.get(song_id)
    
    def set_embedding(self, song_id: str, embedding: Any):
        self.embeddings_cache[song_id] = embedding
    
    def get_metadata(self, song_id: str) -> Optional[Any]:
        return self.metadata_cache.get(song_id)
    
    def set_metadata(self, song_id: str, metadata: Any):
        self.metadata_cache[song_id] = metadata
    
    def invalidate(self, song_id: str):
        self.embeddings_cache.pop(song_id, None)
        self.metadata_cache.pop(song_id, None)
    
    def clear(self):
        self.embeddings_cache.clear()
        self.metadata_cache.clear()

