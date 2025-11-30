"""Search page for finding songs with advanced search capabilities."""

import streamlit as st
from src.streamlit_app.components.songCard import render_song_card
from src.streamlit_app.cache.songCache import search_songs, get_cached_song


def _detect_search_type(query: str) -> str:
    """
    Auto-detect best search type based on query characteristics.
    
    Args:
        query: Search query string
        
    Returns:
        Recommended search type
    """
    query = query.strip()
    
    # Very short queries (< 3 chars) -> autocomplete
    if len(query) < 3:
        return "autocomplete"
    
    # Queries with spaces (likely phrases) -> FTS or hybrid
    if ' ' in query:
        return "hybrid"
    
    # Short queries (3-5 chars) -> autocomplete for partial matching
    if len(query) <= 5:
        return "autocomplete"
    
    # Default to hybrid for best results
    return "hybrid"


def render_search():
    """Render the advanced search page."""
    st.title("Search Songs")
    st.markdown(
        "**Spotify-level search** with fuzzy matching, "
        "typo tolerance, and semantic similarity"
    )
    
    # Advanced search options (collapsible)
    with st.expander("Advanced Search Options", expanded=False):
        search_type = st.radio(
            "Search Mode",
            ["Auto (Recommended)", "Hybrid", "Full-Text", "Fuzzy", "Autocomplete"],
            help=(
                "**Auto**: Automatically selects best mode\n"
                "**Hybrid**: Combines text + fuzzy + vector "
                "search (best accuracy)\n"
                "**Full-Text**: Fast keyword/phrase matching\n"
                "**Fuzzy**: Handles typos and partial matches\n"
                "**Autocomplete**: Fast partial matching "
                "for suggestions"
            ),
            index=0
        )
        
        limit = st.slider(
            "Max Results",
            min_value=5,
            max_value=50,
            value=20,
            help="Maximum number of results to return"
        )
    
    # Search input
    search_query = st.text_input(
        "Search by song title or artist",
        placeholder=(
            "Try: 'closer', 'taylor swift', "
            "or 'haylsay' (fuzzy search)..."
        ),
        key="search_input"
    )
    
    # Determine search type
    if search_type == "Auto (Recommended)":
        actual_search_type = (
            _detect_search_type(search_query)
            if search_query
            else "hybrid"
        )
    else:
        type_map = {
            "Hybrid": "hybrid",
            "Full-Text": "fts",
            "Fuzzy": "trigram",
            "Autocomplete": "autocomplete"
        }
        actual_search_type = type_map.get(search_type, "hybrid")
    
    # Perform search
    if search_query:
        with st.spinner(f"Searching using {actual_search_type} mode..."):
            try:
                filtered_songs = search_songs(
                    st.session_state.storage,
                    query=search_query,
                    limit=limit,
                    search_type=actual_search_type
                )
            except Exception as e:
                st.error(f"Search error: {str(e)}")
                st.info("Falling back to basic search...")
                # Fallback
                filtered_songs = search_songs(
                    st.session_state.storage,
                    query=search_query,
                    limit=limit,
                    search_type="hybrid"
                )
    else:
        filtered_songs = []
        actual_search_type = None
    
    # Results section
    st.markdown("---")
    
    if not search_query:
        st.info(
            "**Tip**: Enter a search query above. "
            "Try different search modes for best results!"
        )
        st.markdown("""
        **Search Examples:**
        - `closer` - Find songs with "closer" in title/artist
        - `taylor swift` - Multi-word search
        - `haylsay` - Fuzzy search finds "Halsey" (typo-tolerant)
        - `clos` - Partial match finds "Closer", "Close", etc.
        """)
        return
    
    # Display search info
    if actual_search_type:
        type_display = {
            "hybrid": "Hybrid (Text + Fuzzy + Vector)",
            "fts": "Full-Text Search",
            "trigram": "Fuzzy Search (Typo-Tolerant)",
            "autocomplete": "Autocomplete (Fast Partial)"
        }
        st.caption(
            f"Search Mode: "
            f"{type_display.get(actual_search_type, actual_search_type)}"
        )
    
    st.subheader(f"Results ({len(filtered_songs)} songs)")
    
    if not filtered_songs:
        st.warning("No songs match your search criteria.")
        st.info(
            "**Try:**\n"
            "- Different search terms\n"
            "- Fuzzy search mode for typos\n"
            "- Shorter queries for partial matches"
        )
        return
    
    # Display results with optional score
    show_scores = st.checkbox(
        "Show relevance scores",
        value=False,
        help="Display search relevance scores"
    )
    
    for idx, song in enumerate(filtered_songs, 1):
        # Show score if available and requested
        if show_scores and '_search_score' in song:
            score = song.get('_search_score', 0)
            st.caption(f"Result #{idx} | Relevance: {score:.4f}")
        
        render_song_card(song, show_preview=True)
        st.markdown("---")
    
    # Search tips
    if len(filtered_songs) < limit:
        st.info(
            f"Found {len(filtered_songs)} result(s). "
            "Try different search terms or increase the limit "
            "for more results."
        )

