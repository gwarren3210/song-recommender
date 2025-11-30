import click
import os
import sys
import numpy as np
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path so we can run this script directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from src.embeddings.embedder import AudioEmbedder
from src.similarity.recommender import Recommender
from src.visualization.projector import Projector
from src.visualization.plot import (
    plot_embeddings_static,
    plot_embeddings_interactive
)
from src.storage.factory import create_storage_backend
from src.apple_api.manager import AppleMusicManager

@click.group()
def cli():
    """Song Vectorizer & Music Similarity Explorer CLI"""
    pass

@cli.command()
@click.option('--input_dir', required=True, help='Directory containing audio files')
@click.option('--model', default='laion/clap-htsat-unfused', help='CLAP model name')
def embed(input_dir, model):
    """Embeds all audio files and stores in the database."""
    storage = create_storage_backend()
    embedder = AudioEmbedder(storage_backend=storage, model_name=model)
    embedder.embed_library(input_dir)

@cli.command()
@click.option('--song_path', help='Path to the song file to recommend for')
@click.option('--song_name', help='Name of the song to recommend for')
@click.option('--song_id', help='Song ID (preferred if available)')
@click.option('--search', help='Search query to find a song (searches entire database)')
@click.option('--k', default=5, help='Number of recommendations')
@click.option('--interactive', is_flag=True, help='Interactively search and select a song')
def recommend(song_path, song_name, song_id, search, k, interactive):
    """Finds similar songs using vector search in the database."""
    storage = create_storage_backend()
    recommender = Recommender(storage_backend=storage)
    
    # If search query provided, use advanced search to find song
    if search:
        if not hasattr(storage, 'search_songs'):
            click.echo(
                "Error: Search requires Postgres backend with "
                "advanced search enabled."
            )
            return
        
        click.echo(f"Searching for '{search}'...")
        search_results = storage.search_songs(
            query=search,
            limit=10,
            search_type="hybrid"
        )
        
        if not search_results:
            click.echo(f"No songs found matching '{search}'.")
            return
        
        if len(search_results) == 1:
            # Auto-select if only one result
            selected = search_results[0]
            song_id = selected.get('song_id')
            artist = selected.get('artist', 'Unknown')
            title = selected.get('title', 'Unknown')
            click.echo(f"Found: {artist} - {title}")
        else:
            # Let user choose
            click.echo(f"\nFound {len(search_results)} songs:")
            for i, song in enumerate(search_results, 1):
                title = song.get('title', 'Unknown')
                artist = song.get('artist', 'Unknown Artist')
                click.echo(f"{i}. {artist} - {title}")
            
            if interactive:
                choice = click.prompt(
                    f"\nSelect a song (1-{len(search_results)})",
                    type=int
                )
                if 1 <= choice <= len(search_results):
                    selected = search_results[choice - 1]
                    song_id = selected.get('song_id')
                    artist = selected.get('artist', 'Unknown')
                    title = selected.get('title', 'Unknown')
                    click.echo(f"Selected: {artist} - {title}")
                else:
                    click.echo("Invalid selection.")
                    return
            else:
                click.echo(
                    "\nUse --interactive flag to select from multiple "
                    "results, or use --song_id with a specific ID."
                )
                return
    
    # Get recommendations
    recommendations = recommender.recommend(
        song_name=song_name,
        song_path=song_path,
        song_id=song_id,
        k=k
    )
    
    if not recommendations:
        click.echo("No recommendations found.")
        return

    click.echo(f"\nTop {k} recommendations:")
    for i, rec in enumerate(recommendations, 1):
        title = rec.get('title', rec.get('filename', 'Unknown'))
        artist = rec.get('artist', 'Unknown Artist')
        score = rec.get('similarity_score', 0.0)
        click.echo(f"{i}. {artist} - {title} (Score: {score:.4f})")

@cli.command()
@click.option('--query', required=True, help='Search query')
@click.option('--limit', default=10, help='Maximum number of results')
@click.option(
    '--search-type',
    type=click.Choice(['hybrid', 'fts', 'trigram', 'autocomplete']),
    default='hybrid',
    help='Search type: hybrid (default), fts, trigram, or autocomplete'
)
@click.option('--show-scores', is_flag=True, help='Show relevance scores')
def search(query, limit, search_type, show_scores):
    """Search songs using advanced search (FTS, trigram, hybrid)."""
    storage = create_storage_backend()
    
    # Check if search_songs method exists (Postgres backend)
    if not hasattr(storage, 'search_songs'):
        click.echo(
            "Error: Advanced search is only available with "
            "Postgres backend."
        )
        return
    
    click.echo(f"Searching for '{query}' using {search_type} mode...")
    
    try:
        results = storage.search_songs(
            query=query,
            limit=limit,
            search_type=search_type
        )
        
        if not results:
            click.echo("No results found.")
            return
        
        click.echo(f"\nFound {len(results)} result(s):\n")
        for i, song in enumerate(results, 1):
            title = song.get('title', 'Unknown')
            artist = song.get('artist', 'Unknown')
            score = song.get('_search_score', 0.0) if show_scores else None
            
            if score is not None:
                click.echo(f"{i}. {artist} - {title} (Score: {score:.4f})")
            else:
                click.echo(f"{i}. {artist} - {title}")
                
    except Exception as e:
        click.echo(f"Error during search: {e}", err=True)
        import traceback
        traceback.print_exc()

@cli.command()
@click.option(
    '--output_file',
    default='visualization.html',
    help='Output file for visualization'
)
@click.option(
    '--method',
    default='umap',
    type=click.Choice(['umap', 'tsne']),
    help='Projection method'
)
def visualize(output_file, method):
    """Visualizes the embeddings from the database."""
    storage = create_storage_backend()
    recommender = Recommender(storage_backend=storage)
    
    # Load all embeddings for visualization
    # TODO: BROKEN - recommender.metadata is intentionally empty
    # (see recommender.py:22)
    # This will always return empty list. Should load songs directly
    # from storage instead.
    # See ISSUES.md #1 for details.
    embeddings_list = []
    valid_metadata = []
    
    for meta in recommender.metadata:
        song_id = meta.get('song_id')
        if song_id:
            embedding = storage.get_embedding(song_id)
            if embedding is not None:
                embeddings_list.append(embedding)
                valid_metadata.append(meta)
    
    if not embeddings_list:
        click.echo("No embeddings found in the database.")
        return
    
    embeddings_array = np.vstack(embeddings_list)
    projector = Projector(method=method)
    projections = projector.fit_transform(embeddings_array)
    
    if output_file.endswith('.html'):
        plot_embeddings_interactive(
            projections,
            valid_metadata,
            output_path=output_file
        )
    else:
        plot_embeddings_static(projections, valid_metadata, output_path=output_file)

@cli.command()
@click.option(
    '--query',
    required=True,
    help='Search query (e.g. artist or song name)'
)
@click.option('--limit', default=10, help='Number of songs to download')
@click.option(
    '--output_dir',
    default='data/audio',
    help='Temporary directory to save audio files'
)
@click.option(
    '--auto-embed',
    is_flag=True,
    help='Automatically embed and store in database'
)
def download(query, limit, output_dir, auto_embed):
    """Downloads song previews from Apple Music and optionally stores in the database."""
    manager = AppleMusicManager()
    files = manager.download_tracks(query, limit, output_dir)
    click.echo(f"Downloaded {len(files)} files to {output_dir}")
    
    if auto_embed:
        storage = create_storage_backend()
        embedder = AudioEmbedder(storage_backend=storage)
        click.echo("Embedding and uploading to the database...")
        for file_path in files:
            try:
                # Embed and store
                embedding = embedder.embed_file(file_path)
                if embedding is not None:
                    song_id = storage.upload_audio(file_path)
                    storage.store_embedding(song_id, embedding)
                    from src.embeddings.preprocessing import extract_metadata
                    meta = extract_metadata(file_path)
                    meta['filename'] = Path(file_path).name
                    meta['path'] = file_path
                    storage.store_metadata(song_id, meta)
                    filename = Path(file_path).name
                    click.echo(
                        f"Embedded and stored {filename} (ID: {song_id})"
                    )
            except Exception as e:
                click.echo(f"Error processing {file_path}: {e}")

@cli.command()
@click.option(
    '--track-urls-file',
    help=(
        'Path to JSON file containing list of track URLs, '
        'or text file with URLs (one per line)'
    )
)
@click.option(
    '--track-url',
    multiple=True,
    help='Apple Music track URL (can be used multiple times)'
)
@click.option(
    '--temp-dir',
    default='data/temp',
    help=(
        'Temporary directory for audio downloads '
        '(deleted after embedding)'
    )
)
def import_playlist(track_urls_file, track_url, temp_dir):
    """Import songs from Apple Music track URLs using iTunes Lookup API.
    
    Either --track-urls-file (JSON file with list of URLs, or text file
    with one URL per line) or --track-url (can be used multiple times)
    must be provided.
    """
    from src.apple_api.client import AppleMusicClient
    from src.apple_api.downloader import download_preview
    import tempfile
    import shutil
    
    # Collect track URLs
    track_urls = []
    
    if track_urls_file:
        try:
            import json
            
            with open(track_urls_file, 'r', encoding='utf-8') as f:
                # Try to parse as JSON first
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        track_urls = [str(url).strip() for url in data if url]
                    elif isinstance(data, str):
                        track_urls = [str(url).strip() for url in data.split('\n') if url]
                    else:
                        click.echo(f"Invalid JSON format: {data}", err=True)
                        return
                    click.echo(f"Loaded {len(track_urls)} track URLs from JSON file")
                except json.JSONDecodeError:
                    click.echo(f"Error parsing JSON file: {f.read()}", err=True)
                    return
        except Exception as e:
            click.echo(f"Error reading track URLs file: {e}", err=True)
            click.echo(f"File content: {f.read()}", err=True)
            return
    
    if track_url:
        track_urls.extend(track_url)
        click.echo(f"Added {len(track_url)} track URLs from command line")
    
    if not track_urls:
        click.echo("Error: Either --track-urls-file or --track-url must be provided.", err=True)
        return
    
    click.echo(f"Processing {len(track_urls)} track URLs...")
    
    # Initialize clients
    client = AppleMusicClient()
    storage = create_storage_backend()
    embedder = AudioEmbedder(storage_backend=storage)
    
    # Get track data from URLs using iTunes Lookup API
    click.echo("Fetching track data from iTunes Lookup API...")
    tracks = client.get_tracks_from_urls(track_urls)
    
    if not tracks:
        click.echo(
            "No tracks found. Check that the URLs are valid "
            "Apple Music/iTunes track URLs.",
            err=True
        )
        return
    
    click.echo(f"Found {len(tracks)} tracks in playlist")
    
    # Create temp directory
    os.makedirs(temp_dir, exist_ok=True)
    
    # Process each track
    successful = 0
    failed = 0
    skipped = 0
    
    for track_data in tracks:
        try:
            artist = track_data.get("artistName", "Unknown")
            title = track_data.get("trackName", "Unknown")
            preview_url = track_data.get("previewUrl")
            track_id = track_data.get("trackId")
            
            click.echo(f"\nProcessing: {artist} - {title}")
            
            if not preview_url:
                click.echo(f"  No preview URL available")
                failed += 1
                continue
            
            # Check if song already in DB (by track_id)
            track_id = track_data.get("trackId")
            if track_id:
                # Use proper filtering with indexed track_id
                existing_songs = storage.list_songs({"track_id": track_id})
                if existing_songs:
                    click.echo(f"  Already in database (track_id: {track_id})")
                    skipped += 1
                    continue
            
            # Download preview temporarily
            filename = f"{artist.replace('/', '_')} - {title.replace('/', '_')}.m4a"
            temp_path = os.path.join(temp_dir, filename)
            
            click.echo(f"  Downloading preview temporarily...")
            if not download_preview(preview_url, temp_path):
                click.echo(f"  Failed to download preview")
                failed += 1
                continue
            
            try:
                # Generate embedding
                click.echo(f"  Generating embedding...")
                embedding = embedder.embed_file(temp_path)
                
                if embedding is None:
                    click.echo(f"  Failed to generate embedding")
                    failed += 1
                    continue
                
                # Create song record with preview URL (not local path)
                # Generate a new UUID for song ID
                song_id = str(uuid.uuid4())
                
                # Store embedding first
                storage.store_embedding(song_id, embedding)
                
                # Store metadata with preview URL
                from src.embeddings.preprocessing import extract_metadata
                duration_ms = track_data.get("trackTimeMillis")
                meta = extract_metadata(temp_path)
                meta['filename'] = filename
                meta['path'] = preview_url  # Store preview URL as path reference
                meta['artist'] = artist
                meta['title'] = title
                meta['preview_url'] = preview_url
                meta['genre'] = track_data.get("primaryGenreName")
                meta['trackId'] = track_data.get("trackId")
                meta['track_id'] = track_data.get("trackId")
                meta['collectionName'] = track_data.get("collectionName")
                meta['collectionId'] = track_data.get("collectionId")
                meta['collection_name'] = track_data.get("collectionName")
                meta['collection_id'] = track_data.get("collectionId")
                meta['artistViewUrl'] = track_data.get("artistViewUrl")
                meta['artist_view_url'] = track_data.get("artistViewUrl")
                meta['collectionViewUrl'] = track_data.get("collectionViewUrl")
                meta['collection_view_url'] = track_data.get("collectionViewUrl")
                meta['trackViewUrl'] = track_data.get("trackViewUrl")
                meta['track_view_url'] = track_data.get("trackViewUrl")
                meta['artworkUrl'] = track_data.get("artworkUrl100")
                meta['artwork_url'] = track_data.get("artworkUrl100")
                meta['releaseDate'] = track_data.get("releaseDate")
                meta['release_date'] = track_data.get("releaseDate")
                meta['trackTimeMillis'] = duration_ms
                meta['track_time_millis'] = duration_ms
                if duration_ms:
                    meta['duration'] = duration_ms / 1000.0
                
                # Store metadata (this also handles genre insertion)
                storage.store_metadata(song_id, meta)
                
                click.echo(f"  ✓ Stored in database (ID: {song_id})")
                successful += 1
                
            finally:
                # Always delete temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    click.echo(f"  Cleaned up temporary file")
            
        except Exception as e:
            click.echo(f"  Error processing track: {e}", err=True)
            failed += 1
            # Clean up temp file on error
            try:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass
            continue
    
    # Clean up temp directory if empty
    try:
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
    except:
        pass
    
    click.echo(f"\n✓ Processing complete!")
    click.echo(f"  Successful: {successful}")
    click.echo(f"  Skipped: {skipped}")
    click.echo(f"  Failed: {failed}")



@cli.command()
def populate_genres():
    """Populate genres table from existing songs."""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        
        storage = create_storage_backend()
        click.echo("Populating genres table from existing songs...")
        
        # Get all genres from songs (one-time scan)
        genres_set = set()
        page = 1
        max_pages = 500
        
        while page <= max_pages:
            skip = (page - 1) * 20
            songs = storage.list_songs(limit=20, skip=skip)
            
            if not songs:
                break
            
            for song in songs:
                genre = song.get('genre')
                if genre:
                    genres_set.add(genre)
            
            if len(songs) < 20:
                break
            
            page += 1
        
        # Add all genres to genres table
        # Genres are automatically added when storing metadata,
        # but we can add them directly if needed
        # This only works with Postgres backend
        if hasattr(storage, '_get_connection'):
            conn = storage._get_connection()
            try:
                with conn.cursor() as cur:
                    for genre in genres_set:
                        cur.execute("""
                            INSERT INTO genres (genre) VALUES (%s)
                            ON CONFLICT (genre) DO NOTHING
                        """, (genre,))
                conn.commit()
            finally:
                storage._put_connection(conn)
        else:
            # For other backends, genres are added automatically when storing metadata
            click.echo("Note: Genres will be added automatically when storing song metadata")
        
        click.echo(f"✓ Populated genres table with {len(genres_set)} genres")
    except Exception as e:
        click.echo(f"Error populating genres: {e}", err=True)


if __name__ == '__main__':
    cli()

