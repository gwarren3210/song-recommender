"""Astra DB storage backend using Data API."""

import uuid
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timezone
from pathlib import Path
from src.storage.backend import StorageBackend
from src.storage.config import StorageConfig
from src.astra.client import AstraClient
from src.astra.vectorSearch import VectorSearcher


class AstraStorageBackend(StorageBackend):
    """
    Astra DB storage backend for embeddings and metadata using Data API.
    
    Audio files are stored as URL references (preview_url).
    """
    
    def __init__(self, config: StorageConfig):
        """
        Initialize Astra storage backend.
        
        Args:
            config: StorageConfig instance
        """
        self.config = config
        
        # Initialize Astra client
        self.client = AstraClient(
            database_id=config.astra_db_id,
            region=config.astra_db_region,
            keyspace=config.astra_db_keyspace,
            application_token=config.astra_db_application_token,
            api_endpoint=config.astra_db_api_endpoint
        )
        
        # Get database and tables (specify keyspace when getting tables)
        self.database = self.client.get_database()
        keyspace = self.client.keyspace
        self.songs_table = self.database.get_table("songs", keyspace=keyspace)
        self.embeddings_table = self.database.get_table("embeddings", keyspace=keyspace)
        self.metadata_table = self.database.get_table("metadata", keyspace=keyspace)
        self.genres_table = self.database.get_table("genres", keyspace=keyspace)
        
        # Initialize vector searcher
        self.vector_searcher = VectorSearcher(self.client)
    
    def _generate_song_id(self) -> str:
        """Generate a new UUID for song ID."""
        return str(uuid.uuid4())
    
    def upload_audio(self, local_path: str, song_id: Optional[str] = None) -> str:
        """
        Upload audio file metadata.
        
        Note: For Astra, we store the preview_url. The actual file
        should be stored externally (e.g., in object storage).
        """
        if song_id is None:
            song_id = self._generate_song_id()
        
        # Extract metadata from filename
        filename = Path(local_path).name
        # Try to parse artist - title from filename
        parts = filename.replace('.m4a', '').replace('.mp3', '').split(' - ', 1)
        artist = parts[0] if len(parts) > 0 else "Unknown"
        title = parts[1] if len(parts) > 1 else filename
        
        # Store song record with preview_url (to be set externally)
        song_data = {
            "song_id": uuid.UUID(song_id),
            "filename": filename,
            "artist": artist,
            "title": title,
            "duration": None,  # Will be updated when embedding is created
            "genre": None,
            "preview_url": None,  # Should be set to actual URL
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "metadata": {}
        }
        
        try:
            self.songs_table.insert_one(song_data)
            return song_id
        except Exception as e:
            print(f"Error uploading audio metadata: {e}")
            raise
    
    def download_audio(self, song_id: str, local_path: str) -> bool:
        """
        Download audio file from preview_url.
        
        Note: This requires the preview_url to be set in the song metadata.
        """
        song = self.get_metadata(song_id)
        if not song or not song.get('preview_url'):
            print(f"No preview_url found for song_id: {song_id}")
            return False
        
        # Download from URL
        import requests
        try:
            response = requests.get(song['preview_url'], stream=True)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            print(f"Error downloading audio: {e}")
            return False
    
    def get_audio_url(self, song_id: str, expires_in: int = 3600) -> Optional[str]:
        """Get audio file URL."""
        song = self.get_metadata(song_id)
        if song:
            return song.get('preview_url')
        return None
    
    def delete_audio(self, song_id: str) -> bool:
        """Delete song and related data."""
        song_uuid = uuid.UUID(song_id)
        
        try:
            # Delete from all tables
            self.songs_table.delete_one({"song_id": song_uuid})
            self.embeddings_table.delete_one({"song_id": song_uuid})
            self.metadata_table.delete_one({"song_id": song_uuid})
            return True
        except Exception as e:
            print(f"Error deleting song: {e}")
            return False
    
    def store_embedding(
        self,
        song_id: str,
        embedding: np.ndarray,
        model_name: str = "laion/clap-htsat-unfused"
    ) -> bool:
        """Store embedding in Astra DB."""
        embedding_id = uuid.uuid4()
        song_uuid = uuid.UUID(song_id)
        
        # Convert numpy array to list for Data API
        embedding_list = embedding.tolist()
        
        embedding_data = {
            "embedding_id": embedding_id,
            "song_id": song_uuid,
            "embedding": embedding_list,
            "model_name": model_name,
            "created_at": datetime.now(timezone.utc)
        }
        
        try:
            self.embeddings_table.insert_one(embedding_data)
            return True
        except Exception as e:
            print(f"Error storing embedding: {e}")
            return False
    
    def get_embedding(self, song_id: str) -> Optional[np.ndarray]:
        """Get embedding from Astra DB."""
        song_uuid = uuid.UUID(song_id)
        
        try:
            result = self.embeddings_table.find_one({"song_id": song_uuid})
            
            if result and result.get('embedding'):
                # Convert list to numpy array
                return np.array(result['embedding'])
            return None
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None
    
    def search_similar(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        threshold: Optional[float] = None
    ) -> List[Dict]:
        """Search for similar embeddings using vector search."""
        results = self.vector_searcher.search_similar(query_embedding, k, threshold)
        
        # TODO: N+1 QUERY PROBLEM - Enriching results one by one causes multiple DB queries
        # Should batch load metadata for all song_ids at once. See ISSUES.md #7 for details.
        enriched = []
        for item in results:
            song_meta = self.get_metadata(item['song_id'])
            item['metadata'] = song_meta or {}
            enriched.append(item)
        
        return enriched
    
    def store_metadata(self, song_id: str, metadata: Dict) -> bool:
        """Store metadata in Astra DB."""
        song_uuid = uuid.UUID(song_id)
        
        try:
            # Update songs table
            song_update = {
                "$set": {
                    "filename": metadata.get('filename', ''),
                    "artist": metadata.get('artist', ''),
                    "title": metadata.get('title', ''),
                    "duration": metadata.get('duration'),
                    "genre": metadata.get('genre'),
                    "track_id": metadata.get('trackId') or metadata.get('track_id'),
                    "collection_id": metadata.get('collectionId') or metadata.get('collection_id'),
                    "collection_name": metadata.get('collectionName') or metadata.get('collection_name'),
                    "artist_view_url": metadata.get('artistViewUrl') or metadata.get('artist_view_url'),
                    "collection_view_url": metadata.get('collectionViewUrl') or metadata.get('collection_view_url'),
                    "track_view_url": metadata.get('trackViewUrl') or metadata.get('track_view_url'),
                    "artwork_url": metadata.get('artworkUrl') or metadata.get('artwork_url'),
                    "release_date": metadata.get('releaseDate') or metadata.get('release_date'),
                    "track_time_millis": metadata.get('trackTimeMillis') or metadata.get('track_time_millis'),
                    "updated_at": datetime.now(timezone.utc),
                    "metadata": metadata.get('metadata', {})
                }
            }
            self.songs_table.update_one(
                {"song_id": song_uuid},
                song_update
            )
            
            # Store/update metadata table (use upsert - insert or update)
            metadata_data = {
                "song_id": song_uuid,
                "filename": metadata.get('filename', ''),
                "path": metadata.get('path', ''),
                "embedding_path": metadata.get('embedding_path', ''),
                "duration": metadata.get('duration'),
                "sample_rate": metadata.get('sample_rate'),
                "file_size": metadata.get('file_size'),
                "file_hash": metadata.get('file_hash', ''),
                "artist": metadata.get('artist', '')
            }
            # Check if metadata exists, then update or insert
            existing = self.metadata_table.find_one({"song_id": song_uuid})
            if existing:
                self.metadata_table.update_one(
                    {"song_id": song_uuid},
                    {"$set": metadata_data}
                )
            else:
                self.metadata_table.insert_one(metadata_data)
            
            # Update genres table when genre is present
            genre = metadata.get('genre')
            if genre:
                self._add_genre(genre)
            
            return True
        except Exception as e:
            print(f"Error storing metadata: {e}")
            return False
    
    def get_metadata(self, song_id: str) -> Optional[Dict]:
        """Get metadata from Astra DB."""
        song_uuid = uuid.UUID(song_id)
        
        try:
            result = self.songs_table.find_one({"song_id": song_uuid})
            
            if result:
                # Convert UUIDs to strings and handle None values
                return {
                    'song_id': str(result.get('song_id', '')),
                    'filename': result.get('filename', ''),
                    'artist': result.get('artist', ''),
                    'title': result.get('title', ''),
                    'duration': result.get('duration'),
                    'genre': result.get('genre', ''),
                    'preview_url': result.get('preview_url', ''),
                    'track_id': result.get('track_id'),
                    'collection_id': result.get('collection_id'),
                    'collection_name': result.get('collection_name', ''),
                    'artist_view_url': result.get('artist_view_url', ''),
                    'collection_view_url': result.get('collection_view_url', ''),
                    'track_view_url': result.get('track_view_url', ''),
                    'artwork_url': result.get('artwork_url', ''),
                    'release_date': result.get('release_date', ''),
                    'track_time_millis': result.get('track_time_millis'),
                    'created_at': result.get('created_at'),
                    'updated_at': result.get('updated_at'),
                    'metadata': result.get('metadata', {})
                }
            return None
        except Exception as e:
            print(f"Error getting metadata: {e}")
            return None
    
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
            limit: Maximum number of songs to return (default: 20)
            skip: Number of songs to skip (for pagination)
        """
        try:
            filter_dict = filters or {}
            
            # Default limit to 20 if not specified
            if limit is None:
                limit = 20
            
            # Build find query with pagination
            # Data API find() supports limit directly
            # For skip, we fetch more and slice (not ideal but works for small skips)
            fetch_limit = limit
            if skip and skip > 0:
                fetch_limit = limit + skip
            
            results = self.songs_table.find(filter_dict, limit=fetch_limit)
            
            # Apply skip if needed
            if skip and skip > 0:
                results_list = list(results)
                results = results_list[skip:skip+limit] if skip < len(results_list) else []
            
            songs = []
            for row in results:
                songs.append({
                    'song_id': str(row.get('song_id', '')),
                    'filename': row.get('filename', ''),
                    'artist': row.get('artist', ''),
                    'title': row.get('title', ''),
                    'duration': row.get('duration'),
                    'genre': row.get('genre', ''),
                    'preview_url': row.get('preview_url', ''),
                    'track_id': row.get('track_id'),
                    'collection_id': row.get('collection_id'),
                    'collection_name': row.get('collection_name', ''),
                    'artist_view_url': row.get('artist_view_url', ''),
                    'collection_view_url': row.get('collection_view_url', ''),
                    'track_view_url': row.get('track_view_url', ''),
                    'artwork_url': row.get('artwork_url', ''),
                    'release_date': row.get('release_date', ''),
                    'track_time_millis': row.get('track_time_millis'),
                    'created_at': row.get('created_at'),
                    'updated_at': row.get('updated_at'),
                    'metadata': row.get('metadata', {})
                })
            
            return songs
        except Exception as e:
            print(f"Error listing songs: {e}")
            return []
    
    def _add_genre(self, genre: str):
        """
        Add genre to genres table if it doesn't exist.
        
        Args:
            genre: Genre name
        """
        if not genre:
            return
        
        try:
            # Use insert_one with if_not_exists behavior
            # Since genre is the primary key, duplicates are ignored
            self.genres_table.insert_one({"genre": genre})
        except Exception as e:
            # Genre might already exist, which is fine
            pass
    
    def find_song_id(
        self,
        song_name: Optional[str] = None,
        song_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Find song_id by searching through all songs efficiently.
        
        TODO: INEFFICIENT - Uses pagination and scans sequentially (O(n) worst case).
        Should use indexed queries instead. See ISSUES.md #4 for details.
        
        Searches through all songs with pagination, fetching only
        song_id, title, filename, and path fields. Stops as soon
        as a match is found.
        
        Args:
            song_name: Song name to search for
            song_path: Path to song file
            
        Returns:
            song_id if found, None otherwise
        """
        if not song_name and not song_path:
            return None
        
        page = 1
        max_pages = 500  # Safety limit
        
        try:
            while page <= max_pages:
                skip = (page - 1) * 20
                # Fetch only essential fields by getting full records but checking early
                songs = self.list_songs(limit=20, skip=skip)
                
                if not songs:
                    break
                
                # Check each song for match
                for song in songs:
                    # Check path match
                    if song_path:
                        path = song.get('path') or song.get('preview_url', '')
                        if path and (song_path == path or song_path.endswith(path) or path.endswith(song_path)):
                            return song.get('song_id')
                    
                    # Check name match
                    if song_name:
                        query_lower = song_name.lower()
                        filename = (song.get('filename', '') or '').lower()
                        title = (song.get('title', '') or '').lower()
                        artist = (song.get('artist', '') or '').lower()
                        
                        if (query_lower in filename or 
                            query_lower in title or
                            query_lower in artist):
                            return song.get('song_id')
                
                # Stop if we got less than 20 songs (last page)
                if len(songs) < 20:
                    break
                
                page += 1
            
            return None
        except Exception as e:
            print(f"Error finding song_id: {e}")
            return None
    
    def get_distinct_genres(self) -> List[str]:
        """
        Get all distinct genres from the genres table.
        
        This is much more efficient than scanning all songs.
        
        Returns:
            Sorted list of unique genres
        """
        try:
            # Query genres table directly - much faster!
            results = self.genres_table.find({})
            
            genres = []
            for row in results:
                genre = row.get('genre')
                if genre:
                    genres.append(genre)
            
            return sorted(genres)
        except Exception as e:
            print(f"Error getting genres: {e}")
            # Fallback: return empty list
            return []
    
    def close(self):
        """Close database connection (Data API is stateless)."""
        pass
