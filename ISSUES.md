# Known Issues, Inefficiencies, and Areas Needing Work

This document catalogs broken functionality, performance issues, and areas that require additional development.

## Critical Issues (Broken Functionality)

### 1. Visualization Command Broken
**Location**: `src/cli.py:73-102`

**Issue**: The `visualize` command attempts to load metadata from `recommender.metadata`, but this list is intentionally kept empty (see `src/similarity/recommender.py:22`). The command will always fail with "No embeddings found" even when embeddings exist in the database.

**Impact**: The visualization feature is completely non-functional.

**Fix Required**:
- Load songs directly from storage backend instead of using `recommender.metadata`
- Implement pagination to load all songs for visualization
- Consider adding a limit option for large libraries

**Example Fix**:
```python
# Instead of:
for meta in recommender.metadata:
    ...

# Should be:
songs = storage.list_songs(limit=10000)  # Or paginate
for song in songs:
    song_id = song.get('song_id')
    ...
```

### 2. Vector Search Implementation May Be Incorrect
**Location**: `src/astra/vectorSearch.py:45-53`

**Issue**: The vector search uses `sort={"embedding": embedding_list}` which may not be the correct way to perform vector similarity search in Astra DB Data API. The fallback method loads ALL embeddings into memory, which is extremely inefficient for large libraries.

**Impact**: 
- Vector search may not be using optimized vector indexes
- Fallback is O(n) and loads entire database into memory
- Performance degrades significantly with large libraries

**Fix Required**:
- Verify correct Astra Data API syntax for vector similarity search
- Consider using `$vectorize` or proper vector search operators
- Implement proper error handling without falling back to full table scan
- Add connection pooling and retry logic

**References**:
- Astra DB Data API documentation for vector search
- Consider using `find()` with proper vector search filters

### 3. Search Functionality is Client-Side Only
**Location**: `src/streamlit_app/cache/songCache.py:76-112`

**Issue**: The `search_songs()` function loads all songs (up to limit) and filters client-side. This is inefficient and doesn't scale.

**Impact**:
- Poor performance with large libraries
- Wastes bandwidth transferring unnecessary data
- Search is limited to first 20 songs only

**Fix Required**:
- Implement server-side search using Astra DB query capabilities
- Add proper text search indexes
- Support pagination for search results
- Consider full-text search features if available

## Performance Issues

### 4. Inefficient Song ID Lookup
**Location**: `src/storage/astra.py:379-442`

**Issue**: `find_song_id()` uses pagination (20 songs per page) and scans through all songs sequentially until a match is found. This is O(n) in worst case.

**Impact**:
- Slow lookups for songs later in the database
- Multiple round trips to database
- No indexing on searchable fields (title, filename)

**Fix Required**:
- Add secondary indexes on `title`, `filename`, and `artist` fields
- Use indexed queries instead of full table scan
- Consider creating a search index or full-text search capability
- Cache frequently looked-up songs

### 5. Pagination Implementation is Inefficient
**Location**: `src/storage/astra.py:297-359`

**Issue**: The `list_songs()` method implements skip by fetching `limit + skip` records and then slicing. This is inefficient for large skip values.

**Impact**:
- Wastes bandwidth fetching unnecessary records
- Slow pagination for later pages
- No cursor-based pagination support

**Fix Required**:
- Implement cursor-based pagination if Astra Data API supports it
- Use proper `skip` parameter if available in Data API
- Consider caching pagination results

### 6. Fallback Vector Search Loads All Embeddings
**Location**: `src/astra/vectorSearch.py:86-129`

**Issue**: When primary vector search fails, the fallback loads ALL embeddings from the database into memory and computes similarity locally.

**Impact**:
- Extremely slow for large libraries
- High memory usage
- Network bandwidth waste
- Should never be used in production

**Fix Required**:
- Remove or significantly improve fallback
- Add proper error handling and logging
- Fail fast with clear error messages instead of falling back
- Consider batch processing if fallback is truly needed

### 7. N+1 Query Problem in Recommendations
**Location**: `src/storage/astra.py:181-197`

**Issue**: The `search_similar()` method enriches results by calling `get_metadata()` for each result individually, causing N+1 queries.

**Impact**:
- Multiple database round trips (one per recommendation)
- Slow performance with many recommendations
- Unnecessary database load

**Fix Required**:
- Batch load metadata for all song_ids at once
- Use a single query with IN clause or batch find
- Cache metadata lookups

### 8. Metadata Loading Strategy
**Location**: `src/similarity/recommender.py:14-22`

**Issue**: Metadata is intentionally not preloaded, but this causes issues with the visualization command and may cause N+1 query problems.

**Impact**:
- Multiple database queries when loading recommendations
- Visualization command broken (see Critical Issue #1)
- Potential performance issues with repeated metadata fetches

**Fix Required**:
- Implement proper caching strategy
- Batch load metadata when needed
- Consider lazy loading with caching

## Code Quality Issues

### 9. Inconsistent Error Handling
**Location**: Throughout codebase

**Issue**: Many functions use `print()` statements for errors instead of proper logging. Some use bare `except:` clauses.

**Examples**:
- `src/storage/astra.py`: Multiple `print(f"Error...")` statements
- `src/cli.py:333`: Bare `except: pass`
- `src/cli.py:341`: Bare `except: pass`

**Impact**:
- Difficult to debug production issues
- No structured logging
- Errors may be silently ignored

**Fix Required**:
- Replace all `print()` with proper logging (use Python `logging` module)
- Remove bare `except:` clauses
- Add proper exception types and error messages
- Implement structured logging with levels (DEBUG, INFO, WARNING, ERROR)

### 10. Missing Input Validation
**Location**: Multiple locations

**Issue**: Many functions don't validate inputs (None checks, type checks, range checks).

**Examples**:
- `src/similarity/recommender.py:24`: No validation of k parameter
- `src/storage/astra.py:54`: No validation of local_path
- `src/astra/vectorSearch.py:25`: No validation of query_embedding shape

**Fix Required**:
- Add input validation to all public methods
- Use type hints consistently
- Add validation decorators or helper functions
- Provide clear error messages for invalid inputs

### 11. Warning Suppression
**Location**: `src/embeddings/preprocessing.py:4-6`

**Issue**: Warnings are globally suppressed, which may hide important issues.

**Impact**:
- May miss important deprecation warnings
- Hides potential compatibility issues

**Fix Required**:
- Suppress warnings only for specific known issues
- Add comments explaining why warnings are suppressed
- Consider fixing underlying issues instead of suppressing

## Incomplete Features

### 12. Audio File Storage Not Fully Implemented
**Location**: `src/storage/astra.py:54-115`

**Issue**: Audio files are stored as URL references only. There's no actual file storage implementation. The `upload_audio()` method only stores metadata, not the actual file.

**Impact**:
- No way to store actual audio files in Astra
- Relies entirely on external URLs (preview_url)
- `download_audio()` depends on external URLs being available

**Fix Required**:
- Document that only URL references are supported
- Consider implementing BLOB storage if needed
- Add clear documentation about storage limitations
- Consider integration with object storage (S3, etc.)

### 13. Missing Migration Tools
**Location**: `src/cli.py:456-512`

**Issue**: The `migrate_to_astra` command exists but may have issues:
- Assumes local file paths exist
- No validation of migration success
- No rollback capability
- No progress tracking for large migrations

**Fix Required**:
- Add progress bars for large migrations
- Add validation and verification steps
- Implement dry-run mode
- Add rollback capability
- Better error handling and recovery

### 14. Schema Management
**Location**: `src/astra/schema.py`

**Issue**: Schema creation has many try/except blocks that silently continue on errors. Index creation may fail silently.

**Impact**:
- Schema may be partially created
- Missing indexes may cause performance issues
- Difficult to diagnose schema issues

**Fix Required**:
- Add schema validation after creation
- Verify all indexes are created
- Add migration versioning
- Implement schema diff/update capabilities

## Configuration and Environment Issues

### 15. Missing Environment Variable Validation
**Location**: `src/storage/config.py`, `src/astra/client.py`

**Issue**: Environment variables may not be validated at startup, leading to cryptic errors later.

**Impact**:
- Poor error messages when config is missing
- Runtime errors instead of startup validation

**Fix Required**:
- Validate all required environment variables at startup
- Provide clear error messages with setup instructions
- Add `.env.example` file (already exists, but verify completeness)

### 16. No Connection Retry Logic
**Location**: `src/astra/client.py`

**Issue**: No retry logic for transient network failures or rate limits.

**Impact**:
- Failures on temporary network issues
- No handling of rate limits
- Poor resilience

**Fix Required**:
- Implement exponential backoff retry logic
- Add rate limit handling
- Add connection pooling
- Implement circuit breaker pattern for repeated failures

## Documentation


### 17. Incomplete Documentation
**Location**: Multiple locations

**Issue**: 
- Some functions lack docstrings
- No API documentation
- Limited examples

**Fix Required**:
- Add comprehensive docstrings to all public methods
- Document expected input/output formats
- Add usage examples
- Create API documentation

## Recommendations Priority

### High Priority (Fix Immediately)
1. Fix visualization command (Critical Issue #1)
2. Fix or verify vector search implementation (Critical Issue #2)
3. Fix N+1 query problem in recommendations (Performance Issue #7)
4. Implement proper logging (Code Quality Issue #9)
5. Add input validation (Code Quality Issue #10)

### Medium Priority (Fix Soon)
6. Implement server-side search (Critical Issue #3)
7. Optimize song ID lookup (Performance Issue #4)
8. Fix pagination (Performance Issue #5)
9. Add environment variable validation (Config Issue #15)

### Low Priority (Nice to Have)
10. Improve fallback vector search (Performance Issue #6)
11. Complete migration tools (Incomplete Feature #13)
12. Add connection retry logic (Config Issue #16)

## Notes

- Many `print()` statements should be replaced with proper logging
- The codebase uses a mix of error handling strategies - should be standardized
- Some features are partially implemented and need completion
- Performance optimizations are needed for production use with large libraries
- Consider adding monitoring and observability for production deployments

