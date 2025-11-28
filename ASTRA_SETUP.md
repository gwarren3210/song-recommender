# Astra DB Setup Guide

## Database Type Selection

Astra DB Serverless offers two types of databases:

### **Serverless (Vector) Database**
- Designed for vector search applications (GenAI, semantic search)
- **Supports both vector AND non-vector data** in the same database
- Can store vectors alongside regular data
- Perfect for RAG applications, chatbots, semantic search, and **music recommendation systems**

### Serverless (Non-Vector) Database
- Designed for generic applications (content management, user auth, transactions)
- **No vector support** - cannot store or search vectors
- Not suitable for this project

**For this song recommender project, create a Serverless (Vector) database** because:
- You need vector search for embeddings (similarity search)
- You also need to store metadata (songs, artists, etc.)
- A Vector database can handle both in one place

## Required Environment Variables

To connect to Astra DB, you need to set the following environment variables:

### **REQUIRED Variables:**

1. **`ASTRA_DB_APPLICATION_TOKEN`** (Required)
   - Your Astra DB application token
   - Format: `AstraCS:xxxxxxxxxxxxx`
   - Get it from: Astra DB Dashboard → Your Database → Token → Generate Token
   - Copy the token (starts with `AstraCS:`)

2. **`ASTRA_DB_ID`** (Required)
   - Your database ID
   - Found in: Astra DB Dashboard → Your Database → Overview
   - Looks like: `abc123def-4567-8901-2345-678901234567`

3. **`ASTRA_DB_REGION`** (Required)
   - The region where your database is hosted
   - Common values: `us-east-1`, `us-west-2`, `eu-west-1`, `ap-south-1`
   - Found in: Astra DB Dashboard → Your Database → Overview

### **Connection Method (Choose ONE):**

**`ASTRA_DB_API_ENDPOINT`** (REQUIRED for Data API)
  - Your database API endpoint URL
  - Format: `https://<database-id>-<region>.apps.astra.datastax.com`
  - Found in: Astra DB Dashboard → Your Database → Connect → API Endpoint
  - **Note:** Data API requires the API endpoint (not the secure bundle)

### **Optional Variables:**

- **`ASTRA_DB_KEYSPACE`** (Optional, defaults to `default`)
  - The keyspace name in your database
  - Default: `default`

## Setup Steps

1. **Create an Astra DB account** (if you don't have one)
   - Go to: https://astra.datastax.com
   - Sign up for a free account

2. **Create a Serverless (Vector) database** ⚠️ **IMPORTANT**
   - Click "Create Database"
   - **Select "Serverless (Vector)"** (NOT "Serverless (Non-Vector)")
   - Choose a name and region
   - Wait for database to be created (2-3 minutes)
   - This database type supports both vector embeddings AND regular metadata

3. **Get your credentials**
   - Go to your database dashboard
   - Copy the Database ID
   - Note the Region
   - Generate an Application Token (Database → Token → Generate Token)

4. **Download Secure Connect Bundle** (Recommended)
   - Go to: Database → Connect → Download Bundle
   - Save `secure-connect-bundle.zip` to your project directory

5. **Set environment variables**

   **Option A: Using `.env` file (Recommended)**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and fill in your values
   nano .env  # or use your preferred editor
   ```

   **Option B: Export in terminal**
   ```bash
   export ASTRA_DB_APPLICATION_TOKEN="AstraCS:your-token-here"
   export ASTRA_DB_ID="your-database-id"
   export ASTRA_DB_REGION="us-east-1"
   export ASTRA_DB_SECURE_BUNDLE_PATH="./secure-connect-bundle.zip"
   export ASTRA_DB_KEYSPACE="default"
   ```

6. **Install dependencies**
   ```bash
   pip install astrapy
   ```
   
   **Note:** This project uses the Data API (astrapy), not CQL (cassandra-driver).

7. **Initialize the schema**
   ```bash
   python src/cli.py init-astra
   ```

## Example `.env` File

```bash
# Required
ASTRA_DB_APPLICATION_TOKEN=AstraCS:abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
ASTRA_DB_ID=abc123def-4567-8901-2345-678901234567
ASTRA_DB_REGION=us-east-1


# Connection method (choose one)
ASTRA_DB_SECURE_BUNDLE_PATH=./secure-connect-bundle.zip
# OR
# ASTRA_DB_API_ENDPOINT=https://abc123def-4567-8901-2345-678901234567-us-east-1.apps.astra.datastax.com

# Optional
ASTRA_DB_KEYSPACE=default
```

## Verification

Test your connection:
```bash
python -c "from src.storage.factory import create_storage_backend; storage = create_storage_backend('astra'); print('Connected successfully!')"
```

## Troubleshooting

- **"ASTRA_DB_APPLICATION_TOKEN is required"**
  - Make sure you've set the token environment variable
  - Check that the token starts with `AstraCS:`

- **"Either ASTRA_DB_SECURE_BUNDLE_PATH or ASTRA_DB_API_ENDPOINT is required"**
  - You need to provide either the bundle path or API endpoint
  - Make sure the bundle file exists if using bundle path

- **Connection timeout**
  - Check your internet connection
  - Verify the database ID and region are correct
  - Make sure your IP is not blocked (check firewall settings)

- **Authentication failed**
  - Verify your application token is correct
  - Make sure the token hasn't expired
  - Regenerate the token if needed

