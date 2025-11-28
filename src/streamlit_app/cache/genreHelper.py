"""Helper functions for genre operations."""

from typing import List
import streamlit as st


def get_available_genres(storage) -> List[str]:
    """
    Get all available genres from the database.
    
    Uses storage backend's get_distinct_genres() method which
    efficiently iterates through all songs to collect unique genres.
    
    Args:
        storage: Storage backend (must have get_distinct_genres method)
        
    Returns:
        Sorted list of unique genres
    """
    # Cache genres in session state to avoid repeated queries
    if 'available_genres' not in st.session_state:
        with st.spinner("Loading all genres..."):
            if hasattr(storage, 'get_distinct_genres'):
                st.session_state.available_genres = storage.get_distinct_genres()
            else:
                # Fallback if method doesn't exist
                st.session_state.available_genres = []
    
    return st.session_state.available_genres

