 # Migration Guide: Cassandra Astra to Neon Postgres

This guide explains how to migrate from Cassandra Astra to Neon Postgres.

## Prerequisites

1. **Neon Postgres Database**: Create a Neon Postgres database and get connection details
2. **Python Dependencies**: Install required packages
   ```bash
   pip install psycopg2-binary
   ```

## Step 1: Create Postgres Schema

Run the Postgres schema migration to create all necessary tables and indexes:

```bash
# Using psql command line
psql "postgresql://user:password@host:port/database?sslmode=require" < migrations/002_postgres_schema.sql
psql 'postgresql://neondb_owner:npg_em1vEtZ2CNqd@ep-little-lab-a4r0amvc-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

# Or using connection string from Neon dashboard
psql "your-neon-connection-string" < migrations/002_postgres_schema.sql
```

This will create:
- `songs` table for song metadata
- `embeddings` table with pgvector support for vector similarity search
- `metadata` table for additional file metadata
- `genres` table for genre lookups
- All necessary indexes including HNSW vector index

## Step 2: Configure Environment Variables

Set the following environment variables for Postgres connection:

```bash
# Storage backend type
export STORAGE_BACKEND=postgres

# Postgres connection details
export POSTGRES_HOST=your-neon-host.neon.tech
export POSTGRES_PORT=5432
export POSTGRES_DATABASE=your-database-name
export POSTGRES_USER=your-username
export POSTGRES_PASSWORD=your-password
export POSTGRES_SSLMODE=require
```

Or add them to your `.env` file:

```env
STORAGE_BACKEND=postgres
POSTGRES_HOST=your-neon-host.neon.tech
POSTGRES_PORT=5432
POSTGRES_DATABASE=your-database-name
POSTGRES_USER=your-username
POSTGRES_PASSWORD=your-password
POSTGRES_SSLMODE=require
```

## Step 3: Run Data Migration

Run the migration script to transfer all data from Astra to Postgres:

```bash
python -m src.scripts.migrateAstraToPostgres
```

This script will:
1. Connect to both Astra and Postgres databases
2. Migrate all songs and metadata
3. Migrate all embeddings
4. Migrate all genres
5. Verify the migration by comparing counts

**Note**: The migration script requires both Astra and Postgres credentials to be configured. Make sure your Astra credentials are still available during migration.

## Step 4: Verify Migration

After migration, verify that all data was transferred correctly:

1. Check song counts match
2. Check embedding counts match
3. Test vector similarity search
4. Test metadata retrieval

You can use the verification output from the migration script, or manually query:

```sql
-- Count songs
SELECT COUNT(*) FROM songs;

-- Count embeddings
SELECT COUNT(*) FROM embeddings;

-- Count genres
SELECT COUNT(*) FROM genres;

-- Test vector search (example)
SELECT song_id, 1 - (embedding <=> '[0.1,0.2,...]'::vector) as similarity
FROM embeddings
ORDER BY embedding <=> '[0.1,0.2,...]'::vector
LIMIT 5;
```

## Step 5: Update Application Configuration

Once migration is complete and verified:

1. Update `STORAGE_BACKEND=postgres` in your environment
2. Test the application with Postgres backend
3. Once everything works, you can decommission the Astra database

## Differences Between Astra and Postgres

### Vector Search

- **Astra**: Uses Data API with vector indexes
- **Postgres**: Uses pgvector extension with HNSW index for fast approximate nearest neighbor search

### Data Types

- **Astra**: Uses UUID, TEXT, MAP types
- **Postgres**: Uses UUID, TEXT, JSONB (for flexible metadata), vector type (for embeddings)

### Performance

- **Astra**: Optimized for distributed NoSQL workloads
- **Postgres**: Optimized for relational queries with vector similarity search

Both backends support the same interface, so the application code doesn't need to change.

## Troubleshooting

### Connection Issues

If you get connection errors:
- Verify your Neon connection string is correct
- Check that SSL mode is set to `require` (default for Neon)
- Ensure your IP is whitelisted in Neon dashboard (if required)

### Schema Creation Issues

If schema creation fails:
- Make sure you have the `vector` extension available in your Postgres instance
- Neon Postgres should have pgvector pre-installed
- Check that you have CREATE EXTENSION permissions

### Migration Issues

If migration fails:
- Check that both Astra and Postgres credentials are correct
- Verify that Postgres schema was created successfully
- Check for any data type mismatches in the logs

### Vector Search Performance

If vector search is slow:
- Ensure the HNSW index was created: `\d embeddings` in psql
- The index is created automatically by the schema migration
- For very large datasets, you may need to tune HNSW parameters

## Rolling Back

If you need to roll back to Astra:

1. Set `STORAGE_BACKEND=astra` in environment
2. Your Astra database should still have all the original data
3. The migration script doesn't delete data from Astra

## Support

For issues or questions:
- Check the migration script logs for detailed error messages
- Verify both databases are accessible
- Ensure all environment variables are set correctly

