"""Audio player component for preview playback."""

import streamlit as st
from typing import Optional
import hashlib


def render_audio_player(preview_url: Optional[str], song_id: str):
    """
    Render an audio player for preview.
    
    Uses unique key based on song_id to ensure Streamlit refreshes
    the player when the song changes.
    
    Args:
        preview_url: URL to audio preview file
        song_id: Optional song ID for unique key generation
    """
    if not preview_url:
        st.caption("No preview available")
        return
    
    # Generate unique key for this audio player
    # When song_id changes, the key changes, forcing Streamlit to recreate the player
    unique_key = f"audio_{song_id}"
    
    # Use Streamlit's built-in audio component with unique key
    # The key parameter ensures the player refreshes when song changes
    try:
        st.audio(
            preview_url,
            format="audio/mp4",
            start_time=0,
            key=unique_key
        )
    except Exception:
        # Fallback to HTML with unique ID if st.audio fails
        audio_html = f"""
        <audio id="{unique_key}" controls style="width: 100%;" preload="none">
            <source src="{preview_url}" type="audio/mp4">
            Your browser does not support the audio element.
        </audio>
        <script>
            // Force reload audio when element is recreated
            document.getElementById("{unique_key}").load();
        </script>
        """
        st.markdown(audio_html, unsafe_allow_html=True)

