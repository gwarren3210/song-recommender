"""Dashboard page showing statistics and overview."""

import streamlit as st
from src.streamlit_app.cache.statsHelper import compute_stats_from_sample


def render_dashboard():
    """Render the dashboard page with statistics."""
    st.title("Dashboard")
    
    # Compute stats from sample (max 100 songs across 5 pages)
    if 'dashboard_stats' not in st.session_state:
        with st.spinner("Computing statistics from sample..."):
            st.session_state.dashboard_stats = compute_stats_from_sample(
                st.session_state.storage,
                sample_size=100
            )
    
    stats = st.session_state.dashboard_stats
    
    if stats['total_songs'] == 0:
        st.info("No songs in database.")
        return
    
    st.info(f"Statistics computed from sample of {stats['sample_size']} songs (sampled across multiple pages).")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Songs Sampled", stats['sample_size'])
    
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
        for song in stats['recent_songs']:
            title = song.get('title') or song.get('filename', 'Unknown')
            artist = song.get('artist', 'Unknown Artist')
            st.write(f"**{title}** by {artist}")
    else:
        st.write("No recent songs available")

