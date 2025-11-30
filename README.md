# Song Vectorizer & Music Similarity Explorer

## Project Description
The **Song Vectorizer & Music Similarity Explorer** is a Python-based system designed to analyze and explore music collections mathematically. By converting audio files into high-dimensional vector embeddings, the system can identify musically similar tracks and visualize the relationships between songs in a 2D space.

Unlike generative AI models that create music, this tool focuses on **music intelligence**—understanding the content of audio files to power recommendations and discovery. It uses state-of-the-art audio embedding models (LAION-CLAP) to capture semantic and acoustic features of songs.

## Directory Structure
```
song-reccomender/
├── data/
│   ├── audio/          # Place your .mp3, .wav, .flac files here
│   └── embeddings/     # Generated .npy embeddings and metadata.json
├── notebooks/
│   └── demo.ipynb      # Interactive demo notebook
├── src/
│   ├── apple_api/      # Apple Music integration for downloading song previews
│   │   ├── client.py
│   │   ├── downloader.py
│   │   └── manager.py
│   ├── embeddings/
│   │   ├── embedder.py     # Core embedding logic
│   │   ├── model_loader.py # CLAP model loading
│   │   └── preprocessing.py# Audio loading and processing
│   ├── similarity/
│   │   ├── cosine.py       # Similarity calculations
│   │   └── recommender.py  # Recommendation engine
│   ├── visualization/
│   │   ├── plot.py         # Plotting functions (static & interactive)
│   │   └── projector.py    # Dimensionality reduction (UMAP/t-SNE)
│   ├── streamlit_app/  # Streamlit web interface
│   │   ├── app.py          # Main Streamlit app
│   │   ├── pages/          # Individual pages (dashboard, search, browse, recommendations)
│   │   └── components/     # Reusable UI components (song cards, audio player)
│   └── cli.py              # Command-line interface entry point
├── requirements.txt
└── README.md
```

## Features
- **Audio Embedding**: Uses LAION-CLAP to generate semantic audio embeddings.
- **Similarity Search**: Finds top-k similar songs using cosine similarity.
- **Visualization**: 2D projection of song embeddings using UMAP/t-SNE.
- **Apple Music Integration**: Search and download song previews directly.
- **CLI**: Easy-to-use command line interface.
- **Web Interface**: Interactive Streamlit web application for all features.

## Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Embed Songs
```bash
python src/cli.py embed --input_dir data/audio --output_dir data/embeddings
```

### Download Songs (Apple Music)
```bash
python src/cli.py download --query "Taylor Swift" --limit 10 --output_dir data/audio
```

### Import Playlist from Apple Music

To import songs from an Apple Music playlist:

1. **Extract track URLs from the playlist page:**
   - Open the Apple Music playlist in your browser
   - Open the browser console (F12 or Cmd+Option+I)
   - Run this JavaScript code to extract all track URLs:

```javascript
const items = document.querySelectorAll('.songs-list__col.songs-list__col--time.svelte-t6plbb');

const links = [...items].map(item => {
  const row = item.closest('[role="row"], .songs-list-row, .songs-list-item');
  return row?.querySelector('a[href]')?.href || null;
}).filter(Boolean);

// Turn into pretty JSON
const json = JSON.stringify(links, null, 2);

// Create & download file
const blob = new Blob([json], { type: "application/json" });
const url = URL.createObjectURL(blob);
const a = document.createElement("a");
a.href = url;
a.download = "song_links.json";
a.click();
```

   - This will download a `song_links.json` file with all track URLs

2. **Import the playlist:**
```bash
# Using the standalone script
python src/scripts/importPlaylist.py song_links.json

# Or using the CLI
python src/cli.py import-playlist --track-urls-file song_links.json
```

The script will:
- Extract track IDs from URLs
- Fetch full track metadata from iTunes Lookup API
- Download previews temporarily to generate embeddings
- Store preview URLs and embeddings in the database
- Clean up temporary files

### Recommend
The song name is the split[1] of the file name, so if the file is named "Artist - Song Name.m4a", the song name is "Song Name".
```bash
python src/cli.py recommend --song_name "Song Name"
```

#### How Recommendations Work

The recommendation system uses **vector similarity search** to find musically similar songs:

1. **Embedding Generation**: Each song is converted into a high-dimensional vector embedding using the LAION-CLAP model. The embedding captures acoustic and semantic features of the audio.

2. **Query Processing**: When you request recommendations for a song, the system:
   - Retrieves the embedding vector for the query song
   - Searches the database for songs with similar embedding vectors
   - Uses cosine similarity to measure how similar two embeddings are

3. **Similarity Search**: The system uses PostgreSQL with pgvector extension to perform efficient vector similarity search. It finds the top-k most similar songs based on cosine distance between embedding vectors.

4. **Results**: Recommendations are returned sorted by similarity score, with the most similar songs first.

**Note on Current Limitations**: The recommendation quality is currently limited by several factors:
- **Limited Similar Songs**: The database may not have enough songs that are truly similar to the query song, leading to recommendations that may not feel musically related.
- **Embedding Quality**: The LAION-CLAP embedder may not capture all the musical nuances that make songs feel similar to human listeners. The model focuses on acoustic features but may miss stylistic, genre, or mood similarities.
- **Preview-Only Embeddings**: Songs are embedded using only 30-second preview clips rather than full-length tracks. This means the embedding may not capture the full musical structure, variations, or key moments that define a song's character.

### Visualize
```bash
python src/cli.py visualize --output_file visualization.html
```

### Web Interface (Streamlit)

Launch the interactive web interface:

```bash
# Using the run script
./run_streamlit.sh

# Or directly with streamlit
streamlit run src/streamlit_app/app.py
```

The web interface provides:

- **Dashboard**: Overview statistics, top artists, genres, and recently added songs
- **Search**: Search songs by title, artist, or filename with genre/artist filters
- **Browse**: Browse all songs with sorting and pagination
- **Recommendations**: Get similar song recommendations based on vector similarity

Features:
- Audio preview playback for each song
- Song artwork display
- Similarity scores visualization
- Direct links to Apple Music
- Responsive design with sidebar navigation

## Known Limitations

### Recommendation Quality

The current recommendation system has several limitations that affect recommendation quality:

1. **Limited Similar Songs in Database**: The recommendation system can only suggest songs that exist in the database. If the database lacks diverse songs or songs similar to the query, recommendations may feel unrelated.

2. **Embedding Model Limitations**: The LAION-CLAP embedder may not fully capture the musical characteristics that make songs feel similar to human listeners. While it captures acoustic features well, it may miss:
   - Stylistic similarities (e.g., both songs have a similar "vibe")
   - Genre nuances and sub-genre distinctions
   - Mood and emotional characteristics
   - Production style and instrumentation choices

3. **Preview-Only Embeddings**: Songs are embedded using 30-second preview clips from Apple Music rather than full-length tracks. This limitation means:
   - The embedding may miss key musical moments (chorus, bridge, outro)
   - Variations and dynamics throughout the song are not captured
   - The embedding represents only a small portion of the complete musical work

These limitations mean that while the system can find songs with similar acoustic features, the recommendations may not always align with human perception of musical similarity. Future improvements could include:
- Using full-length track embeddings when available
- Combining multiple embedding models or features
- Incorporating metadata-based recommendations (genre, artist, year)
- Fine-tuning the embedding model on music similarity tasks