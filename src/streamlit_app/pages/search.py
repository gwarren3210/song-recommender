"""Search page for finding songs."""

import streamlit as st
from src.streamlit_app.components.songCard import render_song_card
from src.streamlit_app.cache.songCache import search_songs, get_cached_song


def render_search():
    """Render the search page."""
    st.title("Search Songs")
    
    # Search input
    search_query = st.text_input(
        "Search by song title or artist",
        placeholder="Enter song name or artist..."
    )
    
    # Perform search (max 20 results)
    if search_query:
        with st.spinner("Searching..."):
            filtered_songs = search_songs(
                st.session_state.storage,
                query=search_query,
                limit=20
            )
    else:
        filtered_songs = []
    
    # Results
    st.markdown("---")
    st.subheader(f"Results ({len(filtered_songs)} songs)")
    
    if not search_query:
        st.info("Enter a search query to find songs.")
        return
    
    if not filtered_songs:
        st.info("No songs match your search criteria.")
        return
    
    # Display results (max 20)
    st.info(f"Showing up to 20 results. Use more specific search terms for better results.")
    
    for song in filtered_songs:
        render_song_card(song, show_preview=True)
        st.markdown("---")

