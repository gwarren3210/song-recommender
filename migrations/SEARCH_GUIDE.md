# Advanced Search System Guide

## Overview

The song recommender now supports **Spotify-level search** using a combination of:

1. **Full-Text Search (FTS)** - Fast, ranked keyword matching
2. **Trigram Fuzzy Search** - Handles typos and partial matches
3. **Vector Similarity Search** - Semantic similarity (already existed)
4. **Hybrid Search** - Combines all three for best results

## Setup

### 1. Run the Migration

Apply the search indexes migration:

```bash
# Connect to your Postgres database and run:
psql -d your_database -f migrations/003_search_indexes.sql
```

Or apply via Python:

```python
from src.storage.postgres import PostgresStorageBackend
from src.storage.config import StorageConfig

config = StorageConfig.from_env()
storage = PostgresStorageBackend(config)
# Extensions and indexes are created automatically on first connection
```

### 2. Verify Indexes

Check that indexes were created:

```sql
-- Check extensions
SELECT * FROM pg_extension WHERE extname IN ('pg_trgm', 'vector');

-- Check indexes
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'songs' 
AND indexname LIKE '%search%' OR indexname LIKE '%trgm%';
```

## Usage

### Python API

```python
from src.storage.postgres import PostgresStorageBackend
from src.storage.config import StorageConfig

config = StorageConfig.from_env()
storage = PostgresStorageBackend(config)

# Hybrid search (default - best for most cases)
results = storage.search_songs(
    query="closer",
    limit=20,
    search_type="hybrid"
)

# Full-text search (exact/keyword matching)
results = storage.search_songs(
    query="taylor swift",
    limit=20,
    search_type="fts"
)

# Trigram search (fuzzy/typo-tolerant)
results = storage.search_songs(
    query="haylsay",  # Finds "Halsey"
    limit=20,
    search_type="trigram"
)

# Autocomplete (fast partial matches)
results = storage.search_songs(
    query="clos",  # Finds "Closer", "Close", etc.
    limit=10,
    search_type="autocomplete"
)

# Hybrid with vector similarity (requires query embedding)
import numpy as np
query_embedding = np.array([...])  # Your embedding vector
results = storage.search_songs(
    query="dance music",
    limit=20,
    search_type="hybrid",
    query_embedding=query_embedding
)
```

### Streamlit UI

The search page automatically uses the new search system:

```python
# In src/streamlit_app/pages/search.py
# The search_songs() function now uses server-side search
```

## Search Types Comparison

| Type | Best For | Speed | Typo Tolerance | Partial Matches |
|------|----------|-------|----------------|------------------|
| **autocomplete** | Typeahead, suggestions | ⚡⚡⚡ Fastest | ✅ Yes | ✅ Yes |
| **trigram** | Fuzzy search, typos | ⚡⚡ Fast | ✅✅ Excellent | ✅ Yes |
| **fts** | Exact keywords, phrases | ⚡⚡ Fast | ❌ No | ❌ No |
| **hybrid** | General search (default) | ⚡ Moderate | ✅ Yes | ✅ Yes |

## Performance Notes

- **Autocomplete**: Optimized for <10ms response times with LIMIT 10
- **Trigram**: Fast with GIN indexes, handles millions of songs
- **FTS**: Very fast with GIN index, language-aware (English)
- **Hybrid**: Slightly slower but most accurate, combines multiple signals

## Architecture Details

### Full-Text Search (FTS)

- Uses `tsvector` column (auto-generated from `title` + `artist`)
- Weighted: title (A) > artist (B)
- Language-aware (English)
- Ranked by `ts_rank()`

### Trigram Search

- Uses `pg_trgm` extension
- GIN indexes on `title`, `artist`, and composite
- Similarity threshold: 0.1-0.2 (configurable)
- Handles: typos, partial matches, case-insensitive

### Vector Search

- Uses existing `pgvector` extension
- HNSW index for fast approximate nearest neighbor
- Cosine similarity
- Best for "songs like this" queries

### Hybrid Search

Combines scores:
- FTS score: 50-60% weight
- Trigram score: 30-40% weight  
- Vector score: 20% weight (if provided)

Final score = weighted sum, sorted descending.

## Troubleshooting

### Search returns no results

1. Check indexes exist:
   ```sql
   SELECT * FROM pg_indexes WHERE tablename = 'songs';
   ```

2. Verify `search_vector` column exists:
   ```sql
   SELECT search_vector FROM songs LIMIT 1;
   ```

3. Test trigram extension:
   ```sql
   SELECT similarity('hello', 'helo');  -- Should return ~0.8
   ```

### Slow search performance

1. Ensure indexes are created (see Setup)
2. Use `EXPLAIN ANALYZE` to check query plans
3. For autocomplete, use `search_type="autocomplete"` with small limit
4. Consider increasing `work_mem` for large result sets

### Migration fails

If migration fails, check:
- Postgres version >= 12 (for generated columns)
- `pg_trgm` extension available
- Sufficient disk space for indexes
- Proper permissions on database

## Future Enhancements

Potential improvements:
- [ ] Multi-language FTS support
- [ ] Configurable similarity thresholds
- [ ] Search result caching
- [ ] Faceted search (by genre, year, etc.)
- [ ] Search analytics/ranking tuning

