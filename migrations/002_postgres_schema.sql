-- Postgres schema migration for Song Recommender
-- Migrates from Cassandra Astra to Neon Postgres

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Table for storing song metadata and audio file references
CREATE TABLE IF NOT EXISTS songs (
    song_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename TEXT,
    artist TEXT,
    title TEXT,
    duration DOUBLE PRECISION,
    genre TEXT,
    bpm INTEGER,
    preview_url TEXT,
    track_id BIGINT,
    collection_id BIGINT,
    collection_name TEXT,
    artist_view_url TEXT,
    collection_view_url TEXT,
    track_view_url TEXT,
    artwork_url TEXT,
    release_date TEXT,
    track_time_millis BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Table for vector embeddings with vector search capability
CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    song_id UUID NOT NULL REFERENCES songs(song_id) ON DELETE CASCADE,
    embedding vector(512),  -- CLAP embeddings are 512-dimensional
    model_name TEXT DEFAULT 'laion/clap-htsat-unfused',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing unique genres (for efficient genre lookups)
CREATE TABLE IF NOT EXISTS genres (
    genre TEXT PRIMARY KEY
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_embeddings_song_id ON embeddings(song_id);
CREATE INDEX IF NOT EXISTS idx_songs_genre ON songs(genre);
CREATE INDEX IF NOT EXISTS idx_songs_track_id ON songs(track_id);
CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist);
CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title);

-- Create vector similarity index using HNSW (Hierarchical Navigable Small World)
-- This enables fast approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_songs_updated_at BEFORE UPDATE ON songs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

