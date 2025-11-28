"""Song card component for displaying song information."""

import streamlit as st
from typing import Dict, Optional


def render_song_card(song: Dict, show_preview: bool = True, show_similarity: bool = False):
    """
    Render a song card with artwork, metadata, and preview.
    
    Args:
        song: Song dictionary with metadata
        show_preview: Whether to show audio preview player
        show_similarity: Whether to show similarity score
    """
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Display artwork
        artwork_url = song.get('artwork_url') or song.get('artworkUrl')
        if artwork_url:
            st.image(artwork_url, width=150)
        else:
            st.image("https://via.placeholder.com/150?text=No+Artwork", width=150)
    
    with col2:
        # Song title
        title = song.get('title') or song.get('filename', 'Unknown')
        st.markdown(f"### {title}")
        
        # Artist
        artist = song.get('artist', 'Unknown Artist')
        st.markdown(f"**Artist:** {artist}")
        
        # Genre
        genre = song.get('genre')
        if genre:
            st.markdown(f"**Genre:** {genre}")
        
        # Duration
        duration = song.get('duration')
        if duration:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            st.markdown(f"**Duration:** {minutes}:{seconds:02d}")
        
        # Similarity score
        if show_similarity:
            similarity = song.get('similarity_score', 0.0)
            st.progress(similarity)
            st.caption(f"Similarity: {similarity:.2%}")
        
        # Preview URL
        preview_url = song.get('preview_url')
        if show_preview and preview_url:
            from src.streamlit_app.components.audioPlayer import render_audio_player
            render_audio_player(preview_url)
        
        # Links
        track_view_url = song.get('track_view_url') or song.get('trackViewUrl')
        if track_view_url:
            st.markdown(f"[Open in Apple Music]({track_view_url})")


def render_song_grid(songs: list, cols: int = 3, show_preview: bool = True):
    """
    Render a grid of song cards.
    
    Args:
        songs: List of song dictionaries
        cols: Number of columns in grid
        show_preview: Whether to show audio preview
    """
    if not songs:
        st.info("No songs found.")
        return
    
    for i in range(0, len(songs), cols):
        cols_list = st.columns(cols)
        for j, col in enumerate(cols_list):
            if i + j < len(songs):
                with col:
                    render_song_card(songs[i + j], show_preview=show_preview)

