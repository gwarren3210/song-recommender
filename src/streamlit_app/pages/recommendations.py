"""Recommendations page for finding similar songs."""

import streamlit as st
from src.streamlit_app.components.songCard import render_song_card
from src.streamlit_app.cache.songCache import search_songs, get_cached_song


def render_recommendations():
    """Render the recommendations page with search-based song selection."""
    st.title("Get Recommendations")
    st.markdown(
        "Search for any song in the database to get "
        "similar recommendations"
    )
    
    recommender = st.session_state.recommender
    
    # Initialize session state
    if 'recommendation_search_query' not in st.session_state:
        st.session_state.recommendation_search_query = ""
    if 'recommendation_search_results' not in st.session_state:
        st.session_state.recommendation_search_results = []
    if 'selected_song_for_recommendation' not in st.session_state:
        st.session_state.selected_song_for_recommendation = None
    
    # Song search interface
    st.subheader("Search for a Song")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_query = st.text_input(
            "Search by song title or artist",
            placeholder="Enter song name or artist...",
            value=st.session_state.recommendation_search_query,
            key="recommendation_search_input"
        )
    
    with col2:
        search_limit = st.number_input(
            "Max results",
            min_value=5,
            max_value=50,
            value=20,
            step=5,
            help="Maximum search results to show"
        )
    
    # Perform search
    if search_query:
        with st.spinner("Searching songs..."):
            search_results = search_songs(
                st.session_state.storage,
                query=search_query,
                limit=search_limit,
                search_type="hybrid"
            )
            st.session_state.recommendation_search_results = search_results
            st.session_state.recommendation_search_query = search_query
    elif st.session_state.recommendation_search_query:
        # Use cached results if query hasn't changed
        search_results = st.session_state.recommendation_search_results
    else:
        search_results = []
    
    # Display search results and allow selection
    if search_results:
        st.markdown(
            f"**Found {len(search_results)} song(s)** - "
            "Select one to get recommendations:"
        )
        
        # Create selection interface
        song_options = {}
        for song in search_results:
            song_id = song.get('song_id')
            if song_id:
                title = song.get('title', song.get('filename', 'Unknown'))
                artist = song.get('artist', 'Unknown Artist')
                label = f"{artist} - {title}"
                song_options[label] = song
        
        if song_options:
            selected_label = st.selectbox(
                "Choose a song",
                list(song_options.keys()),
                key="recommendation_song_select"
            )
            
            selected_song = song_options[selected_label]
            st.session_state.selected_song_for_recommendation = selected_song
            
            # Show selected song preview
            st.markdown("---")
            st.subheader("Selected Song")
            render_song_card(selected_song, show_preview=True)
        else:
            st.warning("No valid songs found in search results.")
            selected_song = None
    elif search_query:
        st.info("No songs found. Try a different search query.")
        selected_song = None
    else:
        st.info(
            "**Enter a search query above to find songs "
            "in the database.**"
        )
        st.markdown("""
        **Examples:**
        - Search for "closer" to find "Closer" by The Chainsmokers
        - Search for "taylor swift" to find songs by Taylor Swift
        - Search for artist names or song titles
        """)
        selected_song = None
    
    # Recommendations section
    if selected_song and st.session_state.selected_song_for_recommendation:
        st.markdown("---")
        st.subheader("Get Recommendations")
        
        # Number of recommendations
        num_recommendations = st.slider(
            "Number of recommendations",
            min_value=5,
            max_value=20,
            value=10,
            step=5
        )
        
        selected_song_id = selected_song.get('song_id')
        
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
                        st.success(f"Found {len(recommendations)} recommendations!")
                    else:
                        st.warning(
                            "No recommendations found. "
                            "The song may not have an embedding."
                        )
                except Exception as e:
                    st.error(f"Error getting recommendations: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        # Display recommendations
        if ('recommendations' in st.session_state and
                st.session_state.recommendations):
            st.markdown("---")
            num_recs = len(st.session_state.recommendations)
            st.subheader(
                f"Similar Songs ({num_recs} recommendations)"
            )
            
            for i, rec in enumerate(st.session_state.recommendations, 1):
                st.markdown(f"### #{i}")
                render_song_card(rec, show_preview=True, show_similarity=True)
                st.markdown("---")

