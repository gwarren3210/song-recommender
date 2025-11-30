-- Migration 003: Add advanced search capabilities
-- Enables Spotify-level search using FTS, trigrams, and hybrid ranking

-- Enable pg_trgm extension for fuzzy/partial matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Add full-text search vector column (auto-generated from title + artist)
ALTER TABLE songs
ADD COLUMN IF NOT EXISTS search_vector tsvector
    GENERATED ALWAYS AS (
        setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(artist, '')), 'B')
    ) STORED;

-- Create GIN index for full-text search (fast ranked queries)
CREATE INDEX IF NOT EXISTS idx_songs_search_vector
    ON songs USING GIN (search_vector);

-- Create trigram indexes for fuzzy/partial matching
-- Enables "clos" -> "Closer" and typo tolerance
CREATE INDEX IF NOT EXISTS idx_song_title_trgm
    ON songs USING GIN (title gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_song_artist_trgm
    ON songs USING GIN (artist gin_trgm_ops);

-- Composite index for common search patterns (title + artist together)
CREATE INDEX IF NOT EXISTS idx_song_title_artist_trgm
    ON songs USING GIN ((title || ' ' || COALESCE(artist, '')) gin_trgm_ops);

-- Note: Vector similarity search already exists via idx_embeddings_vector
-- Hybrid search will combine FTS + vector similarity in application code

