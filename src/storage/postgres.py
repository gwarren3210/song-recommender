"""Postgres/Neon storage backend using psycopg2."""

import uuid
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timezone
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor, register_uuid
from psycopg2.pool import ThreadedConnectionPool
import json

from src.storage.backend import StorageBackend
from src.storage.config import StorageConfig

# Register UUID adapter for psycopg2
register_uuid()


class PostgresStorageBackend(StorageBackend):
    """
    Postgres/Neon storage backend for embeddings and metadata.
    
    Uses pgvector extension for vector similarity search.
    """
    
    def __init__(self, config: StorageConfig):
        """
        Initialize Postgres storage backend.
        
        Args:
            config: StorageConfig instance with Postgres connection info
        """
        self.config = config
        
        # Build connection string
        self.conn_string = self._build_connection_string()
        
        # Create connection pool
        self.pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=self.conn_string
        )
        
        # Initialize schema if needed
        self._ensure_schema()
    
    def _build_connection_string(self) -> str:
        """Build Postgres connection string from config."""
        parts = []
        
        if self.config.postgres_host:
            parts.append(f"host={self.config.postgres_host}")
        if self.config.postgres_port:
            parts.append(f"port={self.config.postgres_port}")
        if self.config.postgres_database:
            parts.append(f"dbname={self.config.postgres_database}")
        if self.config.postgres_user:
            parts.append(f"user={self.config.postgres_user}")
        if self.config.postgres_password:
            parts.append(f"password={self.config.postgres_password}")
        if self.config.postgres_sslmode:
            parts.append(f"sslmode={self.config.postgres_sslmode}")
        
        return " ".join(parts)
    
    def _get_connection(self):
        """Get connection from pool."""
        return self.pool.getconn()
    
    def _put_connection(self, conn):
        """Return connection to pool."""
        self.pool.putconn(conn)
    
    def _ensure_schema(self):
        """Ensure database schema exists, including search indexes."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Check and create extensions
                extensions = [
                    ('vector', 'vector'),
                    ('uuid-ossp', 'uuid-ossp'),
                    ('pg_trgm', 'pg_trgm')
                ]
                
                for ext_name, ext_sql in extensions:
                    cur.execute("""
                        SELECT EXISTS(
                            SELECT 1 FROM pg_extension 
                            WHERE extname = %s
                        )
                    """, (ext_name,))
                    has_ext = cur.fetchone()[0]
                    
                    if not has_ext:
                        cur.execute(f'CREATE EXTENSION IF NOT EXISTS "{ext_sql}"')
                        conn.commit()
                        print(f"✓ Created {ext_name} extension")
                
                # Check if search_vector column exists
                cur.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'songs' AND column_name = 'search_vector'
                    )
                """)
                has_search_vector = cur.fetchone()[0]
                
                if not has_search_vector:
                    # Add search_vector column
                    cur.execute("""
                        ALTER TABLE songs
                        ADD COLUMN search_vector tsvector
                            GENERATED ALWAYS AS (
                                setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
                                setweight(to_tsvector('english', COALESCE(artist, '')), 'B')
                            ) STORED
                    """)
                    conn.commit()
                    print("✓ Created search_vector column")
                
                # Check and create search indexes
                indexes_to_create = [
                    ('idx_songs_search_vector', """
                        CREATE INDEX IF NOT EXISTS idx_songs_search_vector
                        ON songs USING GIN (search_vector)
                    """),
                    ('idx_song_title_trgm', """
                        CREATE INDEX IF NOT EXISTS idx_song_title_trgm
                        ON songs USING GIN (title gin_trgm_ops)
                    """),
                    ('idx_song_artist_trgm', """
                        CREATE INDEX IF NOT EXISTS idx_song_artist_trgm
                        ON songs USING GIN (artist gin_trgm_ops)
                    """),
                    ('idx_song_title_artist_trgm', """
                        CREATE INDEX IF NOT EXISTS idx_song_title_artist_trgm
                        ON songs USING GIN ((title || ' ' || COALESCE(artist, '')) gin_trgm_ops)
                    """)
                ]
                
                for idx_name, idx_sql in indexes_to_create:
                    cur.execute("""
                        SELECT EXISTS(
                            SELECT 1 FROM pg_indexes
                            WHERE indexname = %s
                        )
                    """, (idx_name,))
                    has_idx = cur.fetchone()[0]
                    
                    if not has_idx:
                        cur.execute(idx_sql)
                        conn.commit()
                        print(f"✓ Created {idx_name} index")
                        
        except Exception as e:
            print(f"Error ensuring schema: {e}")
            conn.rollback()
        finally:
            self._put_connection(conn)
    
    def _generate_song_id(self) -> str:
        """Generate a new UUID for song ID."""
        return str(uuid.uuid4())
    
    def upload_audio(self, local_path: str, song_id: Optional[str] = None) -> str:
        """
        Upload audio file metadata.
        
        Note: For Postgres, we store the preview_url. The actual file
        should be stored externally (e.g., in object storage).
        """
        if song_id is None:
            song_id = self._generate_song_id()
        
        # Ensure song_id is a string (handle UUID objects)
        if isinstance(song_id, uuid.UUID):
            song_id = str(song_id)
        
        filename = Path(local_path).name
        parts = filename.replace('.m4a', '').replace('.mp3', '').split(' - ', 1)
        artist = parts[0] if len(parts) > 0 else "Unknown"
        title = parts[1] if len(parts) > 1 else filename
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO songs (
                        song_id, filename, artist, title, duration, genre,
                        preview_url, created_at, updated_at, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (song_id) DO NOTHING
                """, (
                    uuid.UUID(song_id), filename, artist, title, None, None,
                    None, datetime.now(timezone.utc), datetime.now(timezone.utc),
                    json.dumps({})
                ))
                conn.commit()
            return song_id
        except Exception as e:
            conn.rollback()
            print(f"Error uploading audio metadata: {e}")
            raise
        finally:
            self._put_connection(conn)
    
    def download_audio(self, song_id: str, local_path: str) -> bool:
        """
        Download audio file from preview_url.
        
        Note: This requires the preview_url to be set in the song metadata.
        """
        song = self.get_metadata(song_id)
        if not song or not song.get('preview_url'):
            print(f"No preview_url found for song_id: {song_id}")
            return False
        
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
        """Delete song and related data (CASCADE handles related records)."""
        # Ensure song_id is a string (handle UUID objects)
        if isinstance(song_id, uuid.UUID):
            song_id = str(song_id)
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM songs WHERE song_id = %s", (uuid.UUID(song_id),))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            conn.rollback()
            print(f"Error deleting song: {e}")
            return False
        finally:
            self._put_connection(conn)
    
    def store_embedding(
        self,
        song_id: str,
        embedding: np.ndarray,
        model_name: str = "laion/clap-htsat-unfused"
    ) -> bool:
        """Store embedding in Postgres using pgvector."""
        # Ensure song_id is a string (handle UUID objects)
        if isinstance(song_id, uuid.UUID):
            song_id = str(song_id)
        
        embedding_id = uuid.uuid4()
        song_uuid = uuid.UUID(song_id)
        
        # Convert numpy array to list for pgvector
        # pgvector accepts Python lists directly
        embedding_list = embedding.tolist()
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Use pgvector format: pass list and cast to vector type
                cur.execute("""
                    INSERT INTO embeddings (
                        embedding_id, song_id, embedding, model_name, created_at
                    ) VALUES (%s, %s, %s::vector, %s, %s)
                    ON CONFLICT (embedding_id) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        model_name = EXCLUDED.model_name
                """, (
                    embedding_id, song_uuid, embedding_list,
                    model_name, datetime.now(timezone.utc)
                ))
                conn.commit()
                return True
        except Exception as e:
            conn.rollback()
            print(f"Error storing embedding: {e}")
            return False
        finally:
            self._put_connection(conn)
    
    def get_embedding(self, song_id: str) -> Optional[np.ndarray]:
        """Get embedding from Postgres."""
        # Ensure song_id is a string (handle UUID objects)
        if isinstance(song_id, uuid.UUID):
            song_id = str(song_id)
        song_uuid = uuid.UUID(song_id)
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT embedding FROM embeddings
                    WHERE song_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (song_uuid,))
                
                result = cur.fetchone()
                if result and result[0] is not None:
                    # pgvector returns as list or array-like object
                    embedding_data = result[0]
                    if isinstance(embedding_data, (list, tuple)):
                        return np.array(embedding_data)
                    else:
                        # Fallback: convert string representation
                        embedding_str = str(embedding_data).strip('[]')
                        embedding_list = [float(x.strip()) for x in embedding_str.split(',')]
                        return np.array(embedding_list)
                return None
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None
        finally:
            self._put_connection(conn)
    
    def search_similar(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        threshold: Optional[float] = None
    ) -> List[Dict]:
        """Search for similar embeddings using pgvector cosine similarity."""
        # Convert numpy array to list for pgvector
        embedding_list = query_embedding.tolist()
        
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Use pgvector cosine distance (1 - cosine similarity)
                # Order by distance ascending (most similar first)
                query = """
                    SELECT 
                        embedding_id,
                        song_id,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM embeddings
                    WHERE embedding IS NOT NULL
                """
                
                params = [embedding_list]
                
                if threshold is not None:
                    # Filter by similarity threshold
                    # similarity >= threshold means distance <= (1 - threshold)
                    query += " AND (1 - (embedding <=> %s::vector)) >= %s"
                    params.extend([embedding_list, threshold])
                
                query += " ORDER BY embedding <=> %s::vector LIMIT %s"
                params.extend([embedding_list, k])
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                # Enrich with metadata in batch (fixes N+1 query problem)
                song_ids = [str(row['song_id']) for row in results]
                metadata_map = self._batch_get_metadata(song_ids)
                
                enriched = []
                for row in results:
                    song_id = str(row['song_id'])
                    item = {
                        'embedding_id': str(row['embedding_id']),
                        'song_id': song_id,
                        'similarity': float(row['similarity']),
                        'metadata': metadata_map.get(song_id, {})
                    }
                    enriched.append(item)
                
                return enriched
        except Exception as e:
            print(f"Error in vector search: {e}")
            return []
        finally:
            self._put_connection(conn)
    
    def _batch_get_metadata(self, song_ids: List[str]) -> Dict[str, Dict]:
        """Batch load metadata for multiple song IDs."""
        if not song_ids:
            return {}
        
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM songs
                    WHERE song_id = ANY(%s::uuid[])
                """, (song_ids,))
                
                results = cur.fetchall()
                metadata_map = {}
                for row in results:
                    song_id = str(row['song_id'])
                    metadata_map[song_id] = dict(row)
                
                return metadata_map
        except Exception as e:
            print(f"Error batch loading metadata: {e}")
            return {}
        finally:
            self._put_connection(conn)
    
    def store_metadata(self, song_id: str, metadata: Dict) -> bool:
        """Store metadata in Postgres."""
        # Ensure song_id is a string (handle UUID objects)
        if isinstance(song_id, uuid.UUID):
            song_id = str(song_id)
        song_uuid = uuid.UUID(song_id)
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Update songs table
                cur.execute("""
                    INSERT INTO songs (
                        song_id, filename, artist, title, duration, genre,
                        preview_url, track_id, collection_id, collection_name,
                        artist_view_url, collection_view_url, track_view_url,
                        artwork_url, release_date, track_time_millis,
                        updated_at, metadata
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (song_id) DO UPDATE SET
                        filename = EXCLUDED.filename,
                        artist = EXCLUDED.artist,
                        title = EXCLUDED.title,
                        duration = EXCLUDED.duration,
                        genre = EXCLUDED.genre,
                        preview_url = EXCLUDED.preview_url,
                        track_id = EXCLUDED.track_id,
                        collection_id = EXCLUDED.collection_id,
                        collection_name = EXCLUDED.collection_name,
                        artist_view_url = EXCLUDED.artist_view_url,
                        collection_view_url = EXCLUDED.collection_view_url,
                        track_view_url = EXCLUDED.track_view_url,
                        artwork_url = EXCLUDED.artwork_url,
                        release_date = EXCLUDED.release_date,
                        track_time_millis = EXCLUDED.track_time_millis,
                        updated_at = EXCLUDED.updated_at,
                        metadata = EXCLUDED.metadata
                """, (
                    song_uuid,
                    metadata.get('filename', ''),
                    metadata.get('artist', ''),
                    metadata.get('title', ''),
                    metadata.get('duration'),
                    metadata.get('genre'),
                    metadata.get('preview_url', ''),
                    metadata.get('trackId') or metadata.get('track_id'),
                    metadata.get('collectionId') or metadata.get('collection_id'),
                    metadata.get('collectionName') or metadata.get('collection_name', ''),
                    metadata.get('artistViewUrl') or metadata.get('artist_view_url', ''),
                    metadata.get('collectionViewUrl') or metadata.get('collection_view_url', ''),
                    metadata.get('trackViewUrl') or metadata.get('track_view_url', ''),
                    metadata.get('artworkUrl') or metadata.get('artwork_url', ''),
                    metadata.get('releaseDate') or metadata.get('release_date', ''),
                    metadata.get('trackTimeMillis') or metadata.get('track_time_millis'),
                    datetime.now(timezone.utc),
                    json.dumps(metadata.get('metadata', {}))
                ))
            
                # Update genres table
                genre = metadata.get('genre')
                if genre:
                    cur.execute("""
                        INSERT INTO genres (genre) VALUES (%s)
                        ON CONFLICT (genre) DO NOTHING
                    """, (genre,))
                
                conn.commit()
                return True
        except Exception as e:
            conn.rollback()
            print(f"Error storing metadata: {e}")
            return False
        finally:
            self._put_connection(conn)
    
    def get_metadata(self, song_id: str) -> Optional[Dict]:
        """Get metadata from Postgres."""
        # Ensure song_id is a string (handle UUID objects)
        if isinstance(song_id, uuid.UUID):
            song_id = str(song_id)
        song_uuid = uuid.UUID(song_id)
        
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM songs WHERE song_id = %s", (song_uuid,))
                result = cur.fetchone()
                
                if result:
                    metadata = dict(result)
                    # Convert UUIDs to strings
                    if 'song_id' in metadata:
                        metadata['song_id'] = str(metadata['song_id'])
                    # Parse JSONB metadata
                    if 'metadata' in metadata and isinstance(metadata['metadata'], dict):
                        pass  # Already a dict
                    elif 'metadata' in metadata:
                        metadata['metadata'] = json.loads(metadata['metadata']) if metadata['metadata'] else {}
                    return metadata
                return None
        except Exception as e:
            print(f"Error getting metadata: {e}")
            return None
        finally:
            self._put_connection(conn)
    
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
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM songs WHERE 1=1"
                params = []
                
                # Apply filters
                if filters:
                    if 'artist' in filters:
                        query += " AND artist = %s"
                        params.append(filters['artist'])
                    if 'genre' in filters:
                        query += " AND genre = %s"
                        params.append(filters['genre'])
                    if 'title' in filters:
                        query += " AND title ILIKE %s"
                        params.append(f'%{filters["title"]}%')
                
                # Apply pagination
                if limit is None:
                    limit = 20
                
                if skip:
                    query += f" OFFSET %s"
                    params.append(skip)
                
                query += f" LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                songs = []
                for row in results:
                    song = dict(row)
                    if 'song_id' in song:
                        song['song_id'] = str(song['song_id'])
                    if 'metadata' in song and isinstance(song['metadata'], str):
                        song['metadata'] = json.loads(song['metadata']) if song['metadata'] else {}
                    songs.append(song)
                
                return songs
        except Exception as e:
            print(f"Error listing songs: {e}")
            return []
        finally:
            self._put_connection(conn)
    
    def find_song_id(
        self,
        song_name: Optional[str] = None,
        song_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Find song_id by searching through songs efficiently using indexes.
        
        Args:
            song_name: Song name to search for
            song_path: Path to song file
            
        Returns:
            song_id if found, None otherwise
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                if song_path:
                    # Search by path in metadata table
                    cur.execute("""
                        SELECT song_id FROM metadata
                        WHERE path = %s OR preview_url = %s
                        LIMIT 1
                    """, (song_path, song_path))
                    result = cur.fetchone()
                    if result:
                        return str(result[0])
                
                if song_name:
                    # Search by name using ILIKE for case-insensitive search
                    query_lower = song_name.lower()
                    cur.execute("""
                        SELECT song_id FROM songs
                        WHERE LOWER(filename) LIKE %s
                           OR LOWER(title) LIKE %s
                           OR LOWER(artist) LIKE %s
                        LIMIT 1
                    """, (f'%{query_lower}%', f'%{query_lower}%', f'%{query_lower}%'))
                    result = cur.fetchone()
                    if result:
                        return str(result[0])
                
                return None
        except Exception as e:
            print(f"Error finding song_id: {e}")
            return None
        finally:
            self._put_connection(conn)
    
    def get_distinct_genres(self) -> List[str]:
        """
        Get all distinct genres from the genres table.
        
        Returns:
            Sorted list of unique genres
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT genre FROM genres ORDER BY genre")
                results = cur.fetchall()
                return [row[0] for row in results if row[0]]
        except Exception as e:
            print(f"Error getting genres: {e}")
            return []
        finally:
            self._put_connection(conn)
    
    def get_database_stats(self) -> Dict:
        """
        Get comprehensive statistics from the entire database.
        
        Returns:
            Dictionary with:
            - total_songs: Total number of songs
            - unique_artists: Number of unique artists
            - unique_genres: Number of unique genres
            - total_duration: Sum of all song durations (in seconds)
            - top_artists: List of (artist, count) tuples, top 10
            - top_genres: List of (genre, count) tuples, top 10
            - recent_songs: List of most recent songs (up to 10)
        """
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get total count and aggregates
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_songs,
                        COUNT(DISTINCT artist) as unique_artists,
                        COUNT(DISTINCT genre) as unique_genres,
                        COALESCE(SUM(duration), 0) as total_duration
                    FROM songs
                """)
                base_stats = cur.fetchone()
                
                # Get top artists
                cur.execute("""
                    SELECT artist, COUNT(*) as count
                    FROM songs
                    WHERE artist IS NOT NULL AND artist != ''
                    GROUP BY artist
                    ORDER BY count DESC
                    LIMIT 10
                """)
                top_artists = [(row['artist'], row['count']) for row in cur.fetchall()]
                
                # Get top genres
                cur.execute("""
                    SELECT genre, COUNT(*) as count
                    FROM songs
                    WHERE genre IS NOT NULL AND genre != ''
                    GROUP BY genre
                    ORDER BY count DESC
                    LIMIT 10
                """)
                top_genres = [(row['genre'], row['count']) for row in cur.fetchall()]
                
                # Get recent songs
                cur.execute("""
                    SELECT *
                    FROM songs
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                recent_songs_raw = cur.fetchall()
                recent_songs = []
                for row in recent_songs_raw:
                    song = dict(row)
                    if 'song_id' in song:
                        song['song_id'] = str(song['song_id'])
                    if 'metadata' in song and isinstance(song['metadata'], str):
                        song['metadata'] = json.loads(song['metadata']) if song['metadata'] else {}
                    recent_songs.append(song)
                
                return {
                    'total_songs': base_stats['total_songs'] or 0,
                    'unique_artists': base_stats['unique_artists'] or 0,
                    'unique_genres': base_stats['unique_genres'] or 0,
                    'total_duration': float(base_stats['total_duration'] or 0),
                    'top_artists': top_artists,
                    'top_genres': top_genres,
                    'recent_songs': recent_songs
                }
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return {
                'total_songs': 0,
                'unique_artists': 0,
                'unique_genres': 0,
                'total_duration': 0,
                'top_artists': [],
                'top_genres': [],
                'recent_songs': []
            }
        finally:
            self._put_connection(conn)
    
    def search_songs(
        self,
        query: str,
        limit: int = 20,
        search_type: str = "hybrid",
        query_embedding: Optional[np.ndarray] = None
    ) -> List[Dict]:
        """
        Advanced search using FTS, trigrams, and optionally vector similarity.
        
        Args:
            query: Search query string
            limit: Maximum results to return
            search_type: "fts", "trigram", "hybrid", or "autocomplete"
            query_embedding: Optional embedding for hybrid/vector search
            
        Returns:
            List of songs sorted by relevance score
        """
        if not query or not query.strip():
            return []
        
        query = query.strip()
        conn = self._get_connection()
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if search_type == "autocomplete":
                    # Fast trigram search for autocomplete (partial matches)
                    # Uses similarity() function with trigram indexes for speed
                    cur.execute("""
                        SELECT 
                            s.*,
                            GREATEST(
                                similarity(s.title, %s),
                                similarity(s.artist, %s),
                                similarity(s.title || ' ' || COALESCE(s.artist, ''), %s)
                            ) as score
                        FROM songs s
                        WHERE 
                            similarity(s.title, %s) > 0.2 OR
                            similarity(s.artist, %s) > 0.2 OR
                            similarity(s.title || ' ' || COALESCE(s.artist, ''), %s) > 0.2
                        ORDER BY score DESC
                        LIMIT %s
                    """, (query, query, query, query, query, query, limit))
                    
                elif search_type == "trigram":
                    # Fuzzy search with trigrams (handles typos)
                    cur.execute("""
                        SELECT 
                            s.*,
                            GREATEST(
                                similarity(s.title, %s),
                                similarity(s.artist, %s)
                            ) as score
                        FROM songs s
                        WHERE 
                            similarity(s.title, %s) > 0.1 OR
                            similarity(s.artist, %s) > 0.1
                        ORDER BY score DESC
                        LIMIT %s
                    """, (query, query, query, query, limit))
                    
                elif search_type == "fts":
                    # Full-text search (exact/keyword matching)
                    cur.execute("""
                        SELECT 
                            s.*,
                            ts_rank(s.search_vector, plainto_tsquery('english', %s)) as score
                        FROM songs s
                        WHERE s.search_vector @@ plainto_tsquery('english', %s)
                        ORDER BY score DESC
                        LIMIT %s
                    """, (query, query, limit))
                    
                elif search_type == "hybrid":
                    # Hybrid: Combine FTS + trigram + optional vector
                    if query_embedding is not None:
                        # Full hybrid: FTS + trigram + vector similarity
                        embedding_list = query_embedding.tolist()
                        cur.execute("""
                            WITH text_matches AS (
                                SELECT 
                                    s.song_id,
                                    s.*,
                                    COALESCE(
                                        0.5 * ts_rank(s.search_vector, plainto_tsquery('english', %s)),
                                        0
                                    ) +
                                    COALESCE(
                                        0.3 * GREATEST(
                                            similarity(s.title, %s),
                                            similarity(s.artist, %s)
                                        ),
                                        0
                                    ) as text_score
                                FROM songs s
                                WHERE 
                                    s.search_vector @@ plainto_tsquery('english', %s) OR
                                    similarity(s.title, %s) > 0.1 OR
                                    similarity(s.artist, %s) > 0.1
                            ),
                            vector_matches AS (
                                SELECT 
                                    e.song_id,
                                    1 - (e.embedding <=> %s::vector) as vector_score
                                FROM embeddings e
                                WHERE e.embedding IS NOT NULL
                                ORDER BY e.embedding <=> %s::vector
                                LIMIT %s
                            )
                            SELECT 
                                tm.*,
                                COALESCE(tm.text_score, 0) + 
                                COALESCE(vm.vector_score * 0.2, 0) as score
                            FROM text_matches tm
                            LEFT JOIN vector_matches vm ON tm.song_id = vm.song_id
                            ORDER BY score DESC
                            LIMIT %s
                        """, (
                            query, query, query, query, query, query,
                            embedding_list, embedding_list, limit * 2, limit
                        ))
                    else:
                        # Text-only hybrid: FTS + trigram
                        cur.execute("""
                            SELECT 
                                s.*,
                                COALESCE(
                                    0.6 * ts_rank(s.search_vector, plainto_tsquery('english', %s)),
                                    0
                                ) +
                                COALESCE(
                                    0.4 * GREATEST(
                                        similarity(s.title, %s),
                                        similarity(s.artist, %s)
                                    ),
                                    0
                                ) as score
                            FROM songs s
                            WHERE 
                                s.search_vector @@ plainto_tsquery('english', %s) OR
                                similarity(s.title, %s) > 0.1 OR
                                similarity(s.artist, %s) > 0.1
                            ORDER BY score DESC
                            LIMIT %s
                        """, (query, query, query, query, query, query, limit))
                    
                else:
                    # Default: hybrid without vector
                    return self.search_songs(query, limit, "hybrid", None)
                
                results = cur.fetchall()
                songs = []
                for row in results:
                    song = dict(row)
                    if 'song_id' in song:
                        song['song_id'] = str(song['song_id'])
                    if 'metadata' in song and isinstance(song['metadata'], str):
                        song['metadata'] = json.loads(song['metadata']) if song['metadata'] else {}
                    # Remove score from metadata if present (internal use only)
                    if 'score' in song:
                        song['_search_score'] = float(song['score'])
                    songs.append(song)
                
                return songs
                
        except Exception as e:
            print(f"Error searching songs: {e}")
            # Fallback to simple ILIKE search
            return self._fallback_search(query, limit)
        finally:
            self._put_connection(conn)
    
    def _fallback_search(self, query: str, limit: int) -> List[Dict]:
        """Fallback search using simple ILIKE if advanced search fails."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query_lower = f'%{query.lower()}%'
                cur.execute("""
                    SELECT * FROM songs
                    WHERE title ILIKE %s OR artist ILIKE %s
                    LIMIT %s
                """, (query_lower, query_lower, limit))
                
                results = cur.fetchall()
                songs = []
                for row in results:
                    song = dict(row)
                    if 'song_id' in song:
                        song['song_id'] = str(song['song_id'])
                    if 'metadata' in song and isinstance(song['metadata'], str):
                        song['metadata'] = json.loads(song['metadata']) if song['metadata'] else {}
                    songs.append(song)
                
                return songs
        except Exception as e:
            print(f"Error in fallback search: {e}")
            return []
        finally:
            self._put_connection(conn)
    
    def close(self):
        """Close database connection pool."""
        if self.pool:
            self.pool.closeall()

