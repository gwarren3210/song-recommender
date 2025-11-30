"""Helper functions for computing statistics from database."""

from typing import Dict, List
from collections import Counter
from src.streamlit_app.cache.songCache import load_songs_page


def compute_stats_from_database(storage) -> Dict:
    """
    Compute statistics from the entire database.
    
    Uses database aggregations for accurate stats.
    
    Args:
        storage: Storage backend
        
    Returns:
        Dictionary with statistics
    """
    # Use database stats if available (Postgres backend)
    if hasattr(storage, 'get_database_stats'):
        try:
            stats = storage.get_database_stats()
            return stats
        except Exception as e:
            print(f"Error getting database stats: {e}")
            # Fallback to sample method
            return compute_stats_from_sample(storage, sample_size=100)
    
    # Fallback: use sample method for non-Postgres backends
    return compute_stats_from_sample(storage, sample_size=100)


def compute_stats_from_sample(storage, sample_size: int = 100) -> Dict:
    """
    Compute statistics from a sample of songs.
    
    Samples songs across multiple pages to get better representation.
    
    Args:
        storage: Storage backend
        sample_size: Maximum number of songs to sample (default: 100)
        
    Returns:
        Dictionary with statistics
    """
    all_songs: List[Dict] = []
    
    # Sample multiple pages to get better representation
    pages_to_load = min((sample_size + 19) // 20, 5)  # Max 5 pages = 100 songs
    
    for page in range(1, pages_to_load + 1):
        songs = load_songs_page(storage, page=page, page_size=20)
        all_songs.extend(songs)
        
        # Stop if we got less than 20 songs (last page)
        if len(songs) < 20:
            break
        
        # Stop if we've reached sample size
        if len(all_songs) >= sample_size:
            break
    
    if not all_songs:
        return {
            'total_songs': 0,
            'unique_artists': 0,
            'unique_genres': 0,
            'total_duration': 0,
            'top_artists': [],
            'top_genres': [],
            'recent_songs': [],
            'sample_size': 0
        }
    
    # Compute statistics
    artists = [s.get('artist', 'Unknown') for s in all_songs if s.get('artist')]
    genres = [s.get('genre', 'Unknown') for s in all_songs if s.get('genre')]
    durations = [s.get('duration', 0) or 0 for s in all_songs]
    
    artist_counts = Counter(artists)
    genre_counts = Counter(genres)
    
    # Sort by created_at for recent songs
    recent_songs = sorted(
        all_songs,
        key=lambda x: x.get('created_at') or '',
        reverse=True
    )[:10]
    
    return {
        'total_songs': len(all_songs),
        'unique_artists': len(set(artists)),
        'unique_genres': len(set(genres)),
        'total_duration': sum(durations),
        'top_artists': artist_counts.most_common(10),
        'top_genres': genre_counts.most_common(10),
        'recent_songs': recent_songs,
        'sample_size': len(all_songs)
    }

