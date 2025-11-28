# Planning Document: Next Feature
## Song Vectorizer & Music Similarity Explorer

---

## Project Analysis Summary

### Current State

**Core Functionality:**
- Audio embedding using LAION-CLAP model
- Similarity search via cosine similarity
- 2D visualization (UMAP/t-SNE) with interactive Plotly plots
- Apple Music integration for downloading song previews
- CLI interface with Click
- Demo notebook for interactive exploration

**Data Storage:**
- Audio files stored locally in `data/audio/` (49 songs currently)
- Embeddings stored locally in `data/embeddings/` as `.npy` files
- Metadata stored as `metadata.json` in embeddings directory
- All file paths are local filesystem paths

**Architecture:**
- Modular structure with clear separation of concerns
- Components: embeddings, similarity, visualization, apple_api
- Direct file I/O operations throughout
- No abstraction layer for storage

**Limitations:**
- No web interface (despite Streamlit in requirements)
- No cloud storage capability
- Local-only file access
- No multi-user support
- No remote access to embeddings/audio

---

## Feature: Astra DB Integration (Vector DB + Audio Storage)

### Overview
Integrate DataStax Astra DB to serve as both a vector database for embeddings (replacing local similarity matrix computation) and storage for audio files. This provides scalable, cloud-native storage with built-in vector search capabilities, enabling efficient similarity search at scale and centralized data management.

### Goals
1. **Vector Database**: Use Astra's vector search for efficient similarity queries
2. **Unified Storage**: Store both embeddings and audio files in Astra
3. **Scalability**: Handle large music libraries (10k+ songs) efficiently
4. **Performance**: Leverage Astra's optimized vector search instead of computing full similarity matrices
5. **Reliability**: Cloud-native solution with built-in backup and replication

### User Stories

**As a user, I want to:**
- Store my audio library in Astra DB cloud storage
- Access my embeddings and audio files from any device
- Get fast similarity search results without loading all embeddings into memory
- Scale to large music libraries (thousands of songs)
- Sync my library across multiple machines automatically
- Have my data backed up in the cloud

### Technical Requirements

#### Astra DB Schema Design

**Keyspace**: `default`

**Tables:**

1. **songs** (for audio file storage and metadata)
   ```cql
   CREATE TABLE songs (
       song_id UUID PRIMARY KEY,
       filename TEXT,
       artist TEXT,
       title TEXT,
       duration DOUBLE,
       genre TEXT,
       bpm INT,
       audio_blob BLOB,  # Audio file binary data
       audio_url TEXT,   # Alternative: URL if using external storage
       created_at TIMESTAMP,
       updated_at TIMESTAMP,
       metadata MAP<TEXT, TEXT>  # Additional flexible metadata
   );
   ```

2. **embeddings** (for vector embeddings with vector search)
   ```cql
   CREATE TABLE embeddings (
       embedding_id UUID PRIMARY KEY,
       song_id UUID,
       embedding VECTOR<FLOAT, 512>,  # CLAP embeddings are typically 512-dim
       model_name TEXT,
       created_at TIMESTAMP,
       INDEX embedding_idx (embedding) USING SAIS  # Vector similarity index
   );
   ```

3. **metadata** (for additional song metadata and indexing)
   ```cql
   CREATE TABLE metadata (
       song_id UUID PRIMARY KEY,
       filename TEXT,
       path TEXT,
       embedding_path TEXT,
       duration DOUBLE,
       sample_rate INT,
       file_size BIGINT,
       file_hash TEXT,  # For deduplication
       INDEX filename_idx (filename),
       INDEX artist_idx (artist)
   );
   ```

#### Vector Search Integration

- Use Astra's native vector similarity search (SAIS index)
- Replace in-memory similarity matrix computation
- Support ANN (Approximate Nearest Neighbor) search for fast queries
- Configurable similarity threshold and top-k results

#### Storage Abstraction Layer

Create a unified interface that abstracts storage operations:

```python
class StorageBackend:
    # Audio file operations
    def upload_audio(local_path, song_id) -> bool
    def download_audio(song_id, local_path) -> bool
    def get_audio_url(song_id, expires_in) -> str
    def delete_audio(song_id) -> bool
    
    # Embedding operations
    def store_embedding(song_id, embedding, model_name) -> bool
    def get_embedding(song_id) -> np.ndarray
    def search_similar(embedding, k, threshold) -> List[dict]
    
    # Metadata operations
    def store_metadata(song_id, metadata) -> bool
    def get_metadata(song_id) -> dict
    def list_songs(filters) -> List[dict]
```

#### Supported Backends

1. **LocalStorageBackend** (existing functionality)
   - Direct filesystem operations for audio files
   - Local `.npy` files for embeddings
   - JSON metadata file
   - Maintains backward compatibility

2. **AstraStorageBackend** (new)
   - Astra DB integration using cassandra-driver or astrapy
   - Vector search using Astra's SAIS index
   - BLOB storage for audio files (or external URL references)
   - CQL queries for metadata operations

#### Configuration

Environment variables or config file:
```python
STORAGE_BACKEND = "local" | "astra"
ASTRA_DB_ID = "your-database-id"
ASTRA_DB_REGION = "us-east-1"
ASTRA_DB_KEYSPACE = "default"
ASTRA_DB_APPLICATION_TOKEN = "AstraCS:..."  # Secure token
ASTRA_DB_API_ENDPOINT = "https://...datastax.com"
ASTRA_DB_SECURE_BUNDLE_PATH = "./secure-connect-bundle.zip"  # Optional
```

#### Caching Strategy

- **Local Cache**: Store frequently accessed files locally
- **Cache Directory**: `~/.song-recommender/cache/`
- **Cache Policy**: 
  - Cache embeddings (rarely change, but query from Astra)
  - Cache recently accessed audio files
  - Configurable cache size limit
  - LRU eviction policy
  - Invalidate cache on updates


### File Structure

```
src/
├── storage/
│   ├── __init__.py
│   ├── backend.py           # StorageBackend abstract base class
│   ├── local.py             # LocalStorageBackend implementation
│   ├── astra.py             # AstraStorageBackend implementation
│   ├── factory.py           # Backend factory (creates appropriate backend)
│   ├── cache.py             # Local caching layer
│   └── config.py            # Storage configuration management
├── astra/
│   ├── __init__.py
│   ├── client.py            # Astra DB client wrapper
│   ├── schema.py            # CQL schema definitions and migrations
│   ├── queries.py           # CQL query builders
│   └── vectorSearch.py      # Vector similarity search utilities
```

### Implementation Details

#### Vector Search Implementation

```python
# Example vector similarity search query
SELECT song_id, embedding, 
       similarity_cosine(embedding, ?) as similarity
FROM embeddings
WHERE embedding ANN OF ? 
LIMIT ?
```

- Use Astra's native vector search functions
- Support cosine similarity (current implementation)
- Configurable distance metrics
- Efficient ANN search for large libraries

#### Audio File Storage Options

**URL References Only**
- Store only metadata and embeddings in Astra
- Store preview_url in Astra
- Pros: Maximum flexibility
- Cons: Requires external storage setup

#### Error Handling

- Retry logic for transient failures (network, rate limits)
- Exponential backoff with jitter
- Clear error messages with actionable guidance
- Fallback to local storage if Astra unavailable
- Validation of credentials and connection before operations
- Handle vector search errors gracefully

#### Performance Considerations

- **Caching**: Cache frequently accessed embeddings locally
- **Lazy Loading**: Load embeddings only when needed for search
- **Indexing**: Proper indexes on frequently queried fields
- **Vector Index Tuning**: Optimize SAIS index parameters for query patterns

### Integration Points

**Modify Existing Components:**

1. **AudioEmbedder** (`src/embeddings/embedder.py`)
   - Accept `StorageBackend` instance
   - Save embeddings to Astra using vector storage
   - Store audio files in Astra (BLOB or URL)
   - Update metadata in Astra DB
   - Generate UUIDs for new songs

2. **Recommender** (`src/similarity/recommender.py`)
   - **Major Refactor**: Replace similarity matrix computation with vector search
   - Use `storage_backend.search_similar()` instead of computing full matrix
   - Load embeddings on-demand for visualization
   - Cache search results locally
   - Handle missing files gracefully

3. **Similarity Module** (`src/similarity/cosine.py`)
   - Keep for local backend compatibility
   - Add vector search wrapper for Astra backend
   - Abstract similarity computation behind interface

4. **AppleMusicManager** (`src/apple_api/manager.py`) #TODO
   - Upload downloaded files to Astra
   - Generate embeddings and store in vector DB
   - Option to keep local copy or Astra-only

5. **CLI** (`src/cli.py`)
   - Add `--storage-backend` option (local/astra)
   - Add `--sync` command to sync local ↔ Astra
   - Add `--migrate` command to move data
   - Add `--init-astra` command to set up schema

6. **Visualization** (`src/visualization/projector.py`)
   - Load embeddings from Astra for projection 
   - Support batch loading for large libraries
   - Cache projections locally

### Dependencies to Add

```python
# For Astra DB
cassandra-driver>=3.28.0  # Core Cassandra driver
# OR
astrapy>=0.7.0  # Official Astra Python SDK (recommended)


numpy>=1.24.0  # Already in requirements


python-dotenv>=1.0.0  # For .env files
```

### Migration Path

1. **Phase 1**: Set up Astra DB and create schema
   - Design and create tables (songs, embeddings, metadata)
   - Set up vector indexes
   - Test connection and basic operations

2. **Phase 2**: Implement Astra storage backend
   - Create `AstraStorageBackend` class
   - Implement audio file storage (BLOB or URL)
   - Implement embedding storage with vector search
   - Implement metadata operations

3. **Phase 3**: Add storage abstraction layer
   - Create `StorageBackend` interface
   - Refactor `LocalStorageBackend` to implement interface
   - Create backend factory
   - Add configuration management

4. **Phase 4**: Update components to use storage backend
   - Refactor `Recommender` to use vector search
   - Update `AudioEmbedder` to use storage backend
   - Update `AppleMusicManager` for Astra uploads
   - Add caching layer

5. **Phase 5**: Add migration and sync tools
   - CLI command to migrate local → Astra
   - CLI command to sync Astra → local
   - Validation and error handling
   - Progress tracking for large migrations


### Success Metrics

- **Functionality**:
  - All existing functionality works with Astra storage
  - Vector search returns accurate results
  - Audio files can be uploaded and downloaded
  - Metadata operations work correctly

- **Performance**:
  - Vector search is faster than similarity matrix for large libraries (>1k songs)
  - Query latency < 100ms for top-10 recommendations
  - Batch operations complete efficiently
  - Caching reduces redundant queries

- **Reliability**:
  - Successful migration from local to Astra
  - Successful sync operations (bidirectional)
  - Error handling works correctly
  - No data loss during operations

- **Scalability**:
  - System handles 10k+ songs efficiently
  - Vector search performance doesn't degrade with library size
  - Storage costs are free

---

## Implementation Roadmap

### Phase 2: Astra DB Setup & Schema

- [ ] Design database schema (songs, embeddings, metadata tables)
- [ ] Create CQL schema files
- [ ] Set up vector indexes (SAIS)
- [ ] Create Astra client wrapper
- [ ] Document setup process

### Phase 3: Astra Storage Backend (Week 4)

- [ ] Implement AstraStorageBackend class
- [ ] Implement audio file storage (BLOB or URL approach)
- [ ] Implement embedding storage with vector search
- [ ] Implement metadata operations
- [ ] Add vector similarity search queries
- [ ] Create storage abstraction interface
- [ ] Refactor LocalStorageBackend to implement interface
- [ ] Add backend factory
- [ ] Add caching layer
- [ ] Integration testing with test Astra instance

### Phase 4: Component Integration (Week 5)

- [ ] Refactor Recommender to use vector search
- [ ] Update AudioEmbedder to use storage backend
- [ ] Update AppleMusicManager for Astra uploads
- [ ] Update CLI with storage options
- [ ] Add migration tools (local → Astra)
- [ ] Add sync tools (Astra ↔ local)
- [ ] Update visualization to load from Astra

---

##  Technical Considerations

### Breaking Changes

**Storage Integration:**
- Current code assumes local file paths
- Need to update all file I/O operations
- Metadata structure changes (UUIDs instead of paths)
- Path handling needs to be backend-agnostic

**Recommender Refactor:**
- Similarity matrix computation replaced with vector search
- Different query interface (vector search vs. matrix lookup)
- Performance characteristics change (better for large libraries)

**Mitigation:**
- Default to local storage (backward compatible)
- Gradual migration path with validation
- Clear documentation of changes
- Maintain local backend for development/testing

### Performance Impact


**Astra DB:**
- Network latency for queries (mitigated by caching)
- Vector search is optimized but still requires network calls
- Caching essential for acceptable performance
- Batch operations reduce round trips
- Consider connection pooling and keep-alive

### Scalability

**Current Limitations:**
- Loads all embeddings into memory
- Similarity matrix computed for entire library
- May not scale to very large libraries (10k+ songs)

**With Astra DB:**
- Vector search handles large libraries efficiently
- No need to load all embeddings into memory
- Scalable to 100k+ songs with proper indexing

**Future Considerations:**
- Incremental similarity computation (if needed)
- Pagination in UI for large libraries
- Advanced filtering (genre, artist, year) in vector search
- Hybrid search (vector + metadata filters)

### Dependencies Management

- Keep Astra dependencies optional for local-only usage
- Use extras in requirements.txt:
  ```
  [astra]
  astrapy>=0.7.0
  # OR
  cassandra-driver>=3.28.0
  
  [dev]
  python-dotenv>=1.0.0
  ```

---

## Updated File Structure

```
song-recommender/
├── data/                    # Local storage (default)
│   ├── audio/
│   └── embeddings/
├── src/
│   ├── storage/             # NEW: Storage abstraction
│   │   ├── __init__.py
│   │   ├── backend.py
│   │   ├── local.py
│   │   ├── astra.py
│   │   ├── factory.py
│   │   ├── cache.py
│   │   └── config.py
│   ├── astra/               # NEW: Astra DB integration
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── schema.py
│   │   ├── queries.py
│   │   └── vectorSearch.py
│   ├── embeddings/
│   ├── similarity/
│   ├── visualization/
│   ├── apple_api/
│   └── cli.py
├── migrations/              # NEW: Database schema migrations
│   └── 001_initial_schema.cql
├── .env.example             # NEW: Environment variable template
├── config.yaml              # NEW: Optional config file
├── requirements.txt
└── README.md
```

---

##  Success Criteria

### Astra DB Integration
- [ ] Astra DB schema created and tested
- [ ] Vector search returns accurate results
- [ ] Audio files can be stored and retrieved
- [ ] Seamless switching between local and Astra
- [ ] Caching works correctly
- [ ] Migration tools work as expected
- [ ] No data loss during operations
- [ ] Performance is acceptable (vector search faster than matrix for large libraries)
- [ ] System scales to 10k+ songs efficiently

---

## Next Steps After These Features

1. **Vector Database Integration**: For large-scale similarity search
2. **Webpage**: Streamlit simple frontend 
3. **Playlist Management**: Create, save, and share playlists
4. **Advanced Filtering**: Filter recommendations by genre, artist, year
5. **API Server**: REST API for programmatic access
6. **Mobile App**: React Native app using the API

---

## Getting Started


### For Astra DB Development:
```bash
# Install Astra dependencies
pip install astrapy
# OR
pip install cassandra-driver

# Set environment variables
export STORAGE_BACKEND=astra
export ASTRA_DB_ID=your-database-id
export ASTRA_DB_REGION=us-east-1
export ASTRA_DB_KEYSPACE=song_recommender
export ASTRA_DB_APPLICATION_TOKEN=AstraCS:...
export ASTRA_DB_API_ENDPOINT=https://...datastax.com

# Initialize schema (first time)
python src/cli.py init-astra
```

---

**Document Version**: 1.0  
**Last Updated**: 2025
**Status**: Planning Phase

