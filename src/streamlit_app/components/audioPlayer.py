"""Audio player component for preview playback."""

import streamlit as st
from typing import Optional


def render_audio_player(preview_url: Optional[str]):
    """
    Render an HTML5 audio player for preview.
    
    Args:
        preview_url: URL to audio preview file
    """
    if not preview_url:
        st.caption("No preview available")
        return
    
    # Use HTML audio element for better control
    audio_html = f"""
    <audio controls style="width: 100%;">
        <source src="{preview_url}" type="audio/mp4">
        Your browser does not support the audio element.
    </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

