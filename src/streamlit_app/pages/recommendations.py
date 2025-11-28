"""Recommendations page for finding similar songs."""

import streamlit as st
from src.streamlit_app.components.songCard import render_song_card
from src.streamlit_app.cache.songCache import load_songs_page, get_cached_song


def render_recommendations():
    """Render the recommendations page."""
    st.title("Get Recommendations")
    
    recommender = st.session_state.recommender
    
    # Load first page of songs for dropdown (max 20)
    with st.spinner("Loading songs..."):
        songs = load_songs_page(st.session_state.storage, page=1, page_size=20)
    
    if not songs:
        st.info("No songs in database.")
        return
    
    # Song selection
    st.subheader("Select a Song")
    
    # Create song options for dropdown
    song_options = {
        f"{s.get('title', s.get('filename', 'Unknown'))} - {s.get('artist', 'Unknown Artist')}": s.get('song_id')
        for s in songs
        if s.get('song_id')
    }
    
    if not song_options:
        st.error("No songs available for recommendations.")
        return
    
    selected_song_label = st.selectbox(
        "Choose a song to get recommendations for",
        list(song_options.keys())
    )
    
    selected_song_id = song_options[selected_song_label]
    
    # Get selected song from cache or storage
    selected_song = get_cached_song(selected_song_id)
    if not selected_song:
        selected_song = next(
            (s for s in songs if s.get('song_id') == selected_song_id),
            None
        )
        if not selected_song:
            selected_song = st.session_state.storage.get_metadata(selected_song_id)
    
    # Number of recommendations
    num_recommendations = st.slider(
        "Number of recommendations",
        min_value=5,
        max_value=20,
        value=10,
        step=5
    )
    
    # Get recommendations button
    if st.button("Get Recommendations", type="primary"):
        with st.spinner("Finding similar songs..."):
            try:
                recommendations = recommender.recommend(
                    song_id=selected_song_id,
                    k=num_recommendations
                )
                
                if recommendations:
                    st.session_state.recommendations = recommendations
                    st.session_state.selected_song_id = selected_song_id
                else:
                    st.warning("No recommendations found.")
            except Exception as e:
                st.error(f"Error getting recommendations: {e}")
    
    # Display selected song
    if 'selected_song_id' in st.session_state:
        st.markdown("---")
        st.subheader("Selected Song")
        if selected_song:
            render_song_card(selected_song, show_preview=True)
    
    # Display recommendations
    if 'recommendations' in st.session_state and st.session_state.recommendations:
        st.markdown("---")
        st.subheader(f"Similar Songs ({len(st.session_state.recommendations)} recommendations)")
        
        for i, rec in enumerate(st.session_state.recommendations, 1):
            st.markdown(f"### #{i}")
            render_song_card(rec, show_preview=True, show_similarity=True)
            st.markdown("---")

