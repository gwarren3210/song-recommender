"""Main Streamlit application for Song Recommender."""

import streamlit as st
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from src.storage.factory import create_storage_backend
from src.similarity.recommender import Recommender
from src.streamlit_app.components.songCard import render_song_card
from src.streamlit_app.components.audioPlayer import render_audio_player
from src.streamlit_app.pages.dashboard import render_dashboard
from src.streamlit_app.pages.search import render_search
from src.streamlit_app.pages.browse import render_browse
from src.streamlit_app.pages.recommendations import render_recommendations
from src.streamlit_app.cache.songCache import get_song_cache


def init_session_state():
    """Initialize session state variables."""
    if 'storage' not in st.session_state:
        st.session_state.storage = None
    if 'recommender' not in st.session_state:
        st.session_state.recommender = None
    if 'selected_song' not in st.session_state:
        st.session_state.selected_song = None
    if 'song_count' not in st.session_state:
        st.session_state.song_count = 0


def init_backend():
    """Initialize storage backend and recommender."""
    if st.session_state.storage is None:
        try:
            with st.spinner("Connecting to database..."):
                st.session_state.storage = create_storage_backend()
                st.session_state.recommender = Recommender(st.session_state.storage)
                # Don't load all songs upfront - load on demand per page
        except Exception as e:
            st.error(f"Error connecting to database: {e}")
            st.stop()


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Song Recommender",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    init_session_state()
    init_backend()
    
    # Sidebar navigation
    st.sidebar.title("Song Recommender")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Search", "Browse", "Recommendations"],
        index=0
    )
    
    st.sidebar.markdown("---")
    
    # Display cache stats
    cache = get_song_cache()
    st.sidebar.metric("Cached Songs", f"{cache.size()}/100")
    
    # Main content area
    if page == "Dashboard":
        render_dashboard()
    elif page == "Search":
        render_search()
    elif page == "Browse":
        render_browse()
    elif page == "Recommendations":
        render_recommendations()


if __name__ == "__main__":
    main()

