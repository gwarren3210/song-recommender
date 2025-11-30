"""Song cache manager with LFU eviction."""

import streamlit as st
from typing import List, Dict, Optional
from src.streamlit_app.cache.lfuCache import LFUCache


def get_song_cache() -> LFUCache:
    """Get or create song cache in session state."""
    if 'song_cache' not in st.session_state:
        st.session_state.song_cache = LFUCache(max_size=100)
    return st.session_state.song_cache


def get_cached_song(song_id: str) -> Optional[Dict]:
    """
    Get song from cache.
    
    Args:
        song_id: Song ID
        
    Returns:
        Song dictionary or None
    """
    cache = get_song_cache()
    return cache.get(song_id)


def cache_songs(songs: List[Dict]):
    """
    Add songs to cache.
    
    Args:
        songs: List of song dictionaries
    """
    cache = get_song_cache()
    for song in songs:
        song_id = song.get('song_id')
        if song_id:
            cache.put(song_id, song)


def load_songs_page(
    storage,
    page: int = 1,
    page_size: int = 20,
    filters: Optional[Dict] = None
) -> List[Dict]:
    """
    Load a page of songs with caching.
    
    Args:
        storage: Storage backend
        page: Page number (1-indexed)
        page_size: Number of songs per page (max 20)
        filters: Optional filters
        
    Returns:
        List of song dictionaries
    """
    # Enforce max page size
    page_size = min(page_size, 20)
    
    skip = (page - 1) * page_size
    limit = page_size
    
    # Load from database
    songs = storage.list_songs(filters=filters, limit=limit, skip=skip)
    
    # Cache the songs
    cache_songs(songs)
    
    return songs


def search_songs(
    storage,
    query: str,
    limit: int = 20,
    search_type: str = "hybrid"
) -> List[Dict]:
    """
    Search songs by query with caching.
    
    Uses server-side search if available (Postgres), otherwise falls back
    to client-side filtering.
    
    Args:
        storage: Storage backend
        query: Search query
        limit: Maximum results (max 20)
        search_type: "fts", "trigram", "hybrid", or "autocomplete"
        
    Returns:
        List of matching songs
    """
    # Enforce max limit
    limit = min(limit, 20)
    
    if not query or not query.strip():
        all_songs = storage.list_songs(limit=limit)
        cache_songs(all_songs)
        return all_songs
    
    # Use server-side search if available (Postgres backend)
    if hasattr(storage, 'search_songs'):
        try:
            results = storage.search_songs(
                query=query.strip(),
                limit=limit,
                search_type=search_type
            )
            cache_songs(results)
            return results
        except Exception as e:
            print(f"Error in server-side search, falling back: {e}")
    
    # Fallback: client-side filtering (for non-Postgres backends)
    all_songs = storage.list_songs(limit=limit)
    query_lower = query.lower()
    filtered = [
        s for s in all_songs
        if query_lower in (s.get('title', '') or '').lower()
        or query_lower in (s.get('artist', '') or '').lower()
        or query_lower in (s.get('filename', '') or '').lower()
    ]
    
    cache_songs(filtered)
    return filtered[:limit]

