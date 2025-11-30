"""Dashboard page showing statistics and overview."""

import streamlit as st
from src.streamlit_app.cache.statsHelper import compute_stats_from_database


def render_dashboard():
    """Render the dashboard page with real database statistics."""
    st.title("Dashboard")
    st.markdown(
        "**Real-time statistics from your entire music library**"
    )
    
    # Compute stats from entire database
    if 'dashboard_stats' not in st.session_state:
        with st.spinner("Loading database statistics..."):
            st.session_state.dashboard_stats = compute_stats_from_database(
                st.session_state.storage
            )
    
    # Add refresh button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Refresh Stats"):
            with st.spinner("Refreshing statistics..."):
                st.session_state.dashboard_stats = compute_stats_from_database(
                    st.session_state.storage
                )
            st.rerun()
    
    stats = st.session_state.dashboard_stats
    
    if stats['total_songs'] == 0:
        st.info("No songs in database.")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Songs", stats['total_songs'])
    
    with col2:
        st.metric("Unique Artists", stats['unique_artists'])
    
    with col3:
        st.metric("Unique Genres", stats['unique_genres'])
    
    with col4:
        hours = int(stats['total_duration'] // 3600)
        minutes = int((stats['total_duration'] % 3600) // 60)
        duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        st.metric("Total Duration", duration_str)
    
    st.markdown("---")
    
    # Top artists
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Top Artists")
        if stats['top_artists']:
            for artist, count in stats['top_artists']:
                st.write(f"**{artist}**: {count} songs")
        else:
            st.write("No artist data available")
    
    with col2:
        st.subheader("Top Genres")
        if stats['top_genres']:
            for genre, count in stats['top_genres']:
                st.write(f"**{genre}**: {count} songs")
        else:
            st.write("No genre data available")
    
    st.markdown("---")
    
    # Recent songs
    st.subheader("Recently Added Songs")
    if stats['recent_songs']:
        from src.streamlit_app.components.songCard import render_song_card
        for song in stats['recent_songs']:
            render_song_card(song, show_preview=False)
            st.markdown("---")
    else:
        st.write("No recent songs available")

