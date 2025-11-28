-- Initial schema for Song Recommender
-- Keyspace: default_keyspace

-- Table for storing song metadata and audio file references
CREATE TABLE IF NOT EXISTS songs (
    song_id UUID PRIMARY KEY,
    filename TEXT,
    artist TEXT,
    title TEXT,
    duration DOUBLE,
    genre TEXT,
    bpm INT,
    preview_url TEXT,  -- URL to audio file (external storage)
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    metadata MAP<TEXT, TEXT>  -- Additional flexible metadata
);

-- Table for vector embeddings with vector search capability
CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id UUID PRIMARY KEY,
    song_id UUID,
    embedding VECTOR<FLOAT, 512>,  -- CLAP embeddings are typically 512-dim
    model_name TEXT,
    created_at TIMESTAMP
);

-- Table for additional metadata and indexing
CREATE TABLE IF NOT EXISTS metadata (
    song_id UUID PRIMARY KEY,
    filename TEXT,
    path TEXT,
    embedding_path TEXT,
    duration DOUBLE,
    sample_rate INT,
    file_size BIGINT,
    file_hash TEXT,  -- For deduplication
    artist TEXT
);

-- Create vector similarity index for efficient ANN search (after table creation)
CREATE CUSTOM INDEX IF NOT EXISTS embedding_idx ON embeddings (embedding) 
USING 'org.apache.cassandra.index.sai.StorageAttachedIndex';

-- Table for storing unique genres (for efficient genre lookups)
CREATE TABLE IF NOT EXISTS genres (
    genre TEXT PRIMARY KEY
);

-- Create secondary indexes for common queries (after table creation)
CREATE INDEX IF NOT EXISTS song_id_idx ON embeddings (song_id);
CREATE INDEX IF NOT EXISTS filename_idx ON metadata (filename);
CREATE INDEX IF NOT EXISTS artist_idx ON metadata (artist);
CREATE INDEX IF NOT EXISTS genre_idx ON songs (genre);

