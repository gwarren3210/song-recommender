"""Schema management for Astra DB using Data API."""

import os
from typing import Optional
from pathlib import Path
from src.astra.client import AstraClient

try:
    from astrapy.info import CreateTableDefinition, ColumnType
    from astrapy.constants import SortMode
    ASTRA_PY_AVAILABLE = True
except ImportError:
    ASTRA_PY_AVAILABLE = False


def create_schema(client: AstraClient):
    """
    Create database schema using Data API.
    
    Args:
        client: AstraClient instance
    """
    if not ASTRA_PY_AVAILABLE:
        raise ImportError("astrapy is required. Install it with: pip install astrapy")
    
    database = client.get_database()
    keyspace = client.keyspace
    
    print(f"Creating schema in keyspace: {keyspace}")
    
    # Create songs table
    print("Creating 'songs' table...")
    songs_definition = (
        CreateTableDefinition.builder()
        .add_column("song_id", ColumnType.UUID)
        .add_column("filename", ColumnType.TEXT)
        .add_column("artist", ColumnType.TEXT)
        .add_column("title", ColumnType.TEXT)
        .add_column("duration", ColumnType.DOUBLE)
        .add_column("genre", ColumnType.TEXT)

        .add_column("preview_url", ColumnType.TEXT)
        .add_column("track_id", ColumnType.BIGINT)
        .add_column("collection_id", ColumnType.BIGINT)
        .add_column("collection_name", ColumnType.TEXT)
        .add_column("artist_view_url", ColumnType.TEXT)
        .add_column("collection_view_url", ColumnType.TEXT)
        .add_column("track_view_url", ColumnType.TEXT)
        .add_column("artwork_url", ColumnType.TEXT)
        .add_column("release_date", ColumnType.TEXT)
        .add_column("track_time_millis", ColumnType.BIGINT)
        .add_column("created_at", ColumnType.TIMESTAMP)
        .add_column("updated_at", ColumnType.TIMESTAMP)
        .add_map_column("metadata", key_type=ColumnType.TEXT, value_type=ColumnType.TEXT)
        .add_partition_by(["song_id"])
    )
    
    try:
        database.create_table("songs", definition=songs_definition, keyspace=keyspace, if_not_exists=True)
        print("✓ Created 'songs' table")
    except Exception as e:
        print(f"Error creating 'songs' table: {e}")
        raise
    
    # Create embeddings table with vector column
    print("Creating 'embeddings' table...")
    embeddings_definition = (
        CreateTableDefinition.builder()
        .add_column("embedding_id", ColumnType.UUID)
        .add_column("song_id", ColumnType.UUID)
        .add_vector_column("embedding", dimension=512)  # CLAP embeddings are 512-dimensional
        .add_column("model_name", ColumnType.TEXT)
        .add_column("created_at", ColumnType.TIMESTAMP)
        .add_partition_by(["embedding_id"])
    )
    
    try:
        database.create_table("embeddings", definition=embeddings_definition, keyspace=keyspace, if_not_exists=True)
        print("✓ Created 'embeddings' table")
    except Exception as e:
        print(f"Error creating 'embeddings' table: {e}")
        raise
    
    # Create vector index for embeddings
    print("Creating vector index on 'embeddings' table...")
    try:
        embeddings_table = database.get_table("embeddings", keyspace=keyspace)
        embeddings_table.create_vector_index(
            "embedding_idx",
            column="embedding",
            if_not_exists=True,
        )
        print("✓ Created vector index 'embedding_idx'")
    except Exception as e:
        print(f"Error creating vector index: {e}")
        # Vector index might already exist or be created automatically
        print("  (This is often expected - vector indexes may be auto-created)")
    
    # Create metadata table
    print("Creating 'metadata' table...")
    metadata_definition = (
        CreateTableDefinition.builder()
        .add_column("song_id", ColumnType.UUID)
        .add_column("filename", ColumnType.TEXT)
        .add_column("path", ColumnType.TEXT)
        .add_column("embedding_path", ColumnType.TEXT)
        .add_column("duration", ColumnType.DOUBLE)
        .add_column("sample_rate", ColumnType.INT)
        .add_column("file_size", ColumnType.BIGINT)
        .add_column("file_hash", ColumnType.TEXT)
        .add_column("artist", ColumnType.TEXT)
        .add_partition_by(["song_id"])
    )
    
    try:
        database.create_table("metadata", definition=metadata_definition, keyspace=keyspace, if_not_exists=True)
        print("✓ Created 'metadata' table")
    except Exception as e:
        print(f"Error creating 'metadata' table: {e}")
        raise
    
    # Create genres table for efficient genre lookups
    print("Creating 'genres' table...")
    genres_definition = (
        CreateTableDefinition.builder()
        .add_column("genre", ColumnType.TEXT)
        .add_partition_by(["genre"])
    )
    
    try:
        database.create_table("genres", definition=genres_definition, keyspace=keyspace, if_not_exists=True)
        print("✓ Created 'genres' table")
    except Exception as e:
        print(f"Error creating 'genres' table: {e}")
        raise
    
    # Create indexes on songs table
    print("Creating indexes on 'songs' table...")
    try:
        songs_table = database.get_table("songs", keyspace=keyspace)
        
        # Create index on track_id for duplicate checking and lookups
        songs_table.create_index(
            "track_id_idx",
            column="track_id",
            if_not_exists=True,
        )
        print("✓ Created index 'track_id_idx'")
        
        # Create index on genre for filtering and distinct queries
        songs_table.create_index(
            "genre_idx",
            column="genre",
            if_not_exists=True,
        )
        print("✓ Created index 'genre_idx'")
    except Exception as e:
        print(f"Error creating songs indexes: {e}")
        # Don't raise - indexes are optional
    
    # Create indexes on metadata table
    print("Creating indexes on 'metadata' table...")
    try:
        metadata_table = database.get_table("metadata", keyspace=keyspace)
        
        # Create text index on filename
        metadata_table.create_index(
            "filename_idx",
            column="filename",
            if_not_exists=True,
        )
        print("✓ Created index 'filename_idx'")
        
        # Create text index on artist
        metadata_table.create_index(
            "artist_idx",
            column="artist",
            if_not_exists=True,
        )
        print("✓ Created index 'artist_idx'")
    except Exception as e:
        print(f"Error creating metadata indexes: {e}")
        # Don't raise - indexes are optional
    
    # Create index on embeddings.song_id for joins
    print("Creating index on 'embeddings.song_id'...")
    try:
        embeddings_table.create_index(
            "song_id_idx",
            column="song_id",
            if_not_exists=True,
        )
        print("✓ Created index 'song_id_idx'")
    except Exception as e:
        print(f"Error creating song_id index: {e}")
        # Don't raise - index is optional
    
    print("\n✓ Schema creation complete!")


def create_genre_index(client: AstraClient):
    """
    Create index on genre column in songs table.
    
    Useful for adding the index to existing databases.
    
    Args:
        client: AstraClient instance
    """
    if not ASTRA_PY_AVAILABLE:
        raise ImportError("astrapy is required. Install it with: pip install astrapy")
    
    database = client.get_database()
    keyspace = client.keyspace
    
    print(f"Creating genre index in keyspace: {keyspace}")
    
    try:
        songs_table = database.get_table("songs", keyspace=keyspace)
        
        songs_table.create_index(
            "genre_idx",
            column="genre",
            if_not_exists=True,
        )
        print("✓ Created index 'genre_idx' on songs.genre")
    except Exception as e:
        print(f"Error creating genre index: {e}")
        raise


def drop_schema(client: AstraClient):
    """
    Drop all database tables using Data API.
    
    Args:
        client: AstraClient instance
    """
    if not ASTRA_PY_AVAILABLE:
        raise ImportError("astrapy is required. Install it with: pip install astrapy")
    
    database = client.get_database()
    keyspace = client.keyspace
    
    print(f"Dropping schema in keyspace: {keyspace}")
    
    tables = ["songs", "embeddings", "metadata", "genres"]
    
    for table_name in tables:
        try:
            print(f"Dropping '{table_name}' table...")
            database.drop_table(table_name, keyspace=keyspace)
            print(f"✓ Dropped '{table_name}' table")
        except Exception as e:
            # Table might not exist, which is fine
            print(f"  Note: {table_name} table may not exist: {e}")
    
    print("\n✓ Schema drop complete!")

