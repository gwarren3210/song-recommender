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