"""Browse page for exploring all songs."""

import streamlit as st
from src.streamlit_app.components.songCard import render_song_card
from src.streamlit_app.cache.songCache import load_songs_page
from src.streamlit_app.cache.genreHelper import get_available_genres


def render_browse():
    """Render the browse page."""
    st.title("Browse All Songs")
    
    # Initialize page and genre filter in session state
    if 'browse_page' not in st.session_state:
        st.session_state.browse_page = 1
    if 'browse_genre' not in st.session_state:
        st.session_state.browse_genre = "All"
    
    # Genre filter
    with st.spinner("Loading genres..."):
        available_genres = get_available_genres(st.session_state.storage)
    
    selected_genre = st.selectbox(
        "Filter by Genre",
        ["All"] + available_genres,
        index=0 if st.session_state.browse_genre == "All" else (available_genres.index(st.session_state.browse_genre) + 1 if st.session_state.browse_genre in available_genres else 0),
        key="genre_filter"
    )
    
    # Reset page to 1 if genre changed
    if selected_genre != st.session_state.browse_genre:
        st.session_state.browse_genre = selected_genre
        st.session_state.browse_page = 1
        st.rerun()
    
    # Pagination controls
    col1, col2 = st.columns(2)
    
    with col1:
        page = st.number_input(
            "Page",
            min_value=1,
            value=st.session_state.browse_page,
            step=1,
            help="Each page shows up to 20 songs",
            key="page_input"
        )
        if page != st.session_state.browse_page:
            st.session_state.browse_page = page
            st.rerun()
    
    with col2:
        page_size = st.selectbox(
            "Songs per page",
            [10, 20],
            index=1,
            help="Maximum 20 songs per page"
        )
    
    # Build filters
    filters = None
    if selected_genre != "All":
        filters = {"genre": selected_genre}
    
    # Load songs for current page (max 20)
    with st.spinner(f"Loading page {st.session_state.browse_page}..."):
        songs = load_songs_page(
            st.session_state.storage,
            page=st.session_state.browse_page,
            page_size=min(page_size, 20),
            filters=filters
        )
    
    if not songs:
        genre_text = f" for genre '{selected_genre}'" if selected_genre != "All" else ""
        st.info(f"No songs found on this page{genre_text}.")
        return
    
    genre_text = f" (Genre: {selected_genre})" if selected_genre != "All" else ""
    st.markdown(f"Showing {len(songs)} songs (page {st.session_state.browse_page}){genre_text}")
    st.markdown("---")
    
    # Display songs
    for song in songs:
        render_song_card(song, show_preview=True)
        st.markdown("---")
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.browse_page > 1 and st.button("Previous Page"):
            st.session_state.browse_page -= 1
            st.rerun()
    with col2:
        if len(songs) == page_size and st.button("Next Page"):
            st.session_state.browse_page += 1
            st.rerun()

