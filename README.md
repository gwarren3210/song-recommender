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

### Recommend
The song name is the split[1] of the file name, so if the file is named "Artist - Song Name.m4a", the song name is "Song Name".
```bash
python src/cli.py recommend --song_name "Song Name"
```

### Visualize
```bash
python src/cli.py visualize --output_file visualization.html
```
