"""Script to import songs from Apple Music track URLs into the database using iTunes Lookup API."""

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

from src.apple_api.client import AppleMusicClient
from src.apple_api.downloader import download_preview
from src.storage.factory import create_storage_backend
from src.embeddings.embedder import AudioEmbedder
from src.embeddings.preprocessing import extract_metadata
from tqdm import tqdm


def process_tracks(track_urls_file: str, temp_dir: str = "data/temp"):
    """
    Process Apple Music track URLs using iTunes Lookup API.
    Downloads temporarily to generate embeddings, then stores preview URLs in DB.
    
    Args:
        track_urls_file (str): Path to JSON file containing list of track URLs, or text file with URLs (one per line)
        temp_dir (str): Temporary directory for audio downloads (deleted after embedding)
    """
    print(f"Processing track URLs from: {track_urls_file}")
    
    # Load track URLs from file (JSON or text)
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
                    print(f"Invalid JSON format: {data}")
                    return
                print(f"Loaded {len(track_urls)} track URLs from JSON file")
            except json.JSONDecodeError:
                print(f"Error parsing JSON file: {f.read()}")
                return
    except Exception as e:
        print(f"Error reading track URLs file: {e}")
        return
    
    # Initialize clients
    client = AppleMusicClient()
    storage = create_storage_backend()
    embedder = AudioEmbedder(storage_backend=storage)
    
    # Get track data from URLs using iTunes Lookup API
    print("Fetching track data from iTunes Lookup API...")
    tracks = client.get_tracks_from_urls(track_urls)
    
    if not tracks:
        print("No tracks found. Check that the URLs are valid Apple Music/iTunes track URLs.")
        return
    
    print(f"Found {len(tracks)} tracks")
    
    # Create temp directory
    os.makedirs(temp_dir, exist_ok=True)
    
    # Process each track with batching
    successful = 0
    failed = 0
    skipped = 0
    
    # Batch collections for insert_many
    batch_size = 20
    songs_batch = []
    embeddings_batch = []
    metadata_batch = []
    
    def flush_batch():
        """Flush current batch to database."""
        nonlocal songs_batch, embeddings_batch, metadata_batch
        if songs_batch:
            try:
                storage.songs_table.insert_many(songs_batch, ordered=False)
                tqdm.write(f"  ✓ Inserted {len(songs_batch)} songs in batch")
            except Exception as e:
                tqdm.write(f"  Error inserting songs batch: {e}")
        if embeddings_batch:
            try:
                storage.embeddings_table.insert_many(embeddings_batch, ordered=False)
                tqdm.write(f"  ✓ Inserted {len(embeddings_batch)} embeddings in batch")
            except Exception as e:
                tqdm.write(f"  Error inserting embeddings batch: {e}")
        if metadata_batch:
            try:
                storage.metadata_table.insert_many(metadata_batch, ordered=False)
                tqdm.write(f"  ✓ Inserted {len(metadata_batch)} metadata in batch")
            except Exception as e:
                tqdm.write(f"  Error inserting metadata batch: {e}")
        songs_batch = []
        embeddings_batch = []
        metadata_batch = []
    
    for track_data in tqdm(tracks, desc="Processing tracks", position=0, leave=True):
        try:
            artist = track_data.get("artistName", "Unknown")
            title = track_data.get("trackName", "Unknown")
            preview_url = track_data.get("previewUrl")
            track_id = track_data.get("trackId")
            
            tqdm.write(f"\nProcessing: {artist} - {title}")
            
            if not preview_url:
                tqdm.write(f"  No preview URL available")
                failed += 1
                continue
            
            # Check if song already in DB (by track_id)
            track_id = track_data.get("trackId")
            if track_id:
                # Use proper filtering with indexed track_id
                existing_songs = storage.list_songs({"track_id": track_id})
                if existing_songs:
                    tqdm.write(f"  Already in database (track_id: {track_id})")
                    skipped += 1
                    continue
            
            # Download preview temporarily
            filename = f"{artist.replace('/', '_')} - {title.replace('/', '_')}.m4a"
            temp_path = os.path.join(temp_dir, filename)
            
            tqdm.write(f"  Downloading preview temporarily...")
            if not download_preview(preview_url, temp_path):
                tqdm.write(f"  Failed to download preview")
                failed += 1
                continue
            
            try:
                # Generate embedding
                tqdm.write(f"  Generating embedding...")
                embedding = embedder.embed_file(temp_path)
                
                if embedding is None:
                    tqdm.write(f"  Failed to generate embedding")
                    failed += 1
                    continue
                
                # Create song record with preview URL (not local path)
                # Generate a new UUID for song ID
                song_id_uuid = uuid.uuid4()
                song_id = str(song_id_uuid)  # String version for logging/display
                
                # Store song metadata with preview URL
                duration_ms = track_data.get("trackTimeMillis")
                song_data = {
                    "song_id": song_id_uuid,
                    "filename": filename,  # Keep for reference, but file is not stored
                    "artist": artist,
                    "title": title,
                    "duration": duration_ms / 1000.0 if duration_ms else None,
                    "genre": track_data.get("primaryGenreName"),
                    "preview_url": preview_url,  # Store preview URL, not local path
                    "track_id": track_data.get("trackId"),
                    "collection_id": track_data.get("collectionId"),
                    "collection_name": track_data.get("collectionName"),
                    "artist_view_url": track_data.get("artistViewUrl"),
                    "collection_view_url": track_data.get("collectionViewUrl"),
                    "track_view_url": track_data.get("trackViewUrl"),
                    "artwork_url": track_data.get("artworkUrl100"),
                    "release_date": track_data.get("releaseDate"),
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "metadata": {}
                }
                
                # Prepare embedding data
                embedding_id = uuid.uuid4()
                embedding_list = embedding.tolist()
                embedding_data = {
                    "embedding_id": embedding_id,
                    "song_id": song_id_uuid,
                    "embedding": embedding_list,
                    "model_name": "laion/clap-htsat-unfused",
                    "created_at": datetime.now(timezone.utc)
                }
                
                # Store additional metadata
                meta = extract_metadata(temp_path)
                meta['filename'] = filename
                meta['path'] = preview_url  # Store preview URL as path reference
                meta['artist'] = artist
                meta['title'] = title
                meta['preview_url'] = preview_url
                meta['genre'] = track_data.get("primaryGenreName")
                meta['track_id'] = track_data.get("trackId")
                meta['collectionName'] = track_data.get("collectionName")
                meta['collectionId'] = track_data.get("collectionId")
                meta['artistViewUrl'] = track_data.get("artistViewUrl")
                meta['collectionViewUrl'] = track_data.get("collectionViewUrl")
                meta['trackViewUrl'] = track_data.get("trackViewUrl")
                meta['artworkUrl'] = track_data.get("artworkUrl100")
                meta['releaseDate'] = track_data.get("releaseDate")
                if duration_ms:
                    meta['duration'] = duration_ms / 1000.0
                
                metadata_data = {
                    "song_id": song_id_uuid,
                    "filename": meta.get('filename', ''),
                    "path": meta.get('path', ''),
                    "embedding_path": meta.get('embedding_path', ''),
                    "duration": meta.get('duration'),
                    "sample_rate": meta.get('sample_rate'),
                    "file_size": meta.get('file_size'),
                    "file_hash": meta.get('file_hash', ''),
                    "artist": meta.get('artist', '')
                }
                
                # Add to batches
                songs_batch.append(song_data)
                embeddings_batch.append(embedding_data)
                metadata_batch.append(metadata_data)
                
                # Flush batch when it reaches batch_size
                if len(songs_batch) >= batch_size:
                    flush_batch()
                
                tqdm.write(f"  ✓ Queued for batch insert (ID: {song_id})")
                successful += 1
                
            finally:
                # Always delete temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    tqdm.write(f"  Cleaned up temporary file")
            
        except Exception as e:
            tqdm.write(f"  Error processing track: {e}")
            failed += 1
            # Clean up temp file on error
            try:
                if 'temp_path' in locals() and os.path.exists(temp_path):
                    os.remove(temp_path)
            except:
                pass
            continue
    
    # Flush any remaining items in batch
    flush_batch()
    
    # Clean up temp directory if empty
    try:
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
    except:
        pass
    
    print(f"\n✓ Processing complete!")
    print(f"  Successful: {successful}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {failed}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Import songs from Apple Music track URLs using iTunes Lookup API")
    parser.add_argument("track_urls_file", help="Path to JSON file containing list of track URLs, or text file with URLs (one per line)")
    parser.add_argument("--temp-dir", default="data/temp", help="Temporary directory for audio downloads (deleted after embedding)")
    
    args = parser.parse_args()
    
    process_tracks(args.track_urls_file, args.temp_dir)


if __name__ == "__main__":
    main()

