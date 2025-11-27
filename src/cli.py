import click
import os
import sys
import numpy as np

# Add project root to path so we can run this script directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.embeddings.embedder import AudioEmbedder
from src.similarity.recommender import Recommender
from src.visualization.projector import Projector
from src.visualization.plot import plot_embeddings_static, plot_embeddings_interactive

@click.group()
def cli():
    """Song Vectorizer & Music Similarity Explorer CLI"""
    pass

@cli.command()
@click.option('--input_dir', required=True, help='Directory containing audio files')
@click.option('--output_dir', default='data/embeddings', help='Directory to save embeddings')
@click.option('--model', default='laion/clap-htsat-unfused', help='CLAP model name')
def embed(input_dir, output_dir, model):
    """Embeds all audio files in the input directory."""
    embedder = AudioEmbedder(model_name=model)
    embedder.embed_library(input_dir, output_dir)

@cli.command()
@click.option('--embeddings_dir', default='data/embeddings', help='Directory containing embeddings')
@click.option('--song_path', help='Path to the song file to recommend for')
@click.option('--song_name', help='Name of the song to recommend for')
@click.option('--k', default=5, help='Number of recommendations')
def recommend(embeddings_dir, song_path, song_name, k):
    """Finds similar songs."""
    recommender = Recommender(embeddings_dir)
    
    recommendations = recommender.recommend(song_name=song_name, song_path=song_path, k=k)
    
    if not recommendations:
        click.echo("No recommendations found.")
        return

    click.echo(f"Top {k} recommendations:")
    for i, rec in enumerate(recommendations, 1):
        click.echo(f"{i}. {rec.get('filename')} (Score: {rec.get('similarity_score'):.4f})")

@cli.command()
@click.option('--embeddings_dir', default='data/embeddings', help='Directory containing embeddings')
@click.option('--output_file', default='visualization.html', help='Output file for visualization')
@click.option('--method', default='umap', type=click.Choice(['umap', 'tsne']), help='Projection method')
def visualize(embeddings_dir, output_file, method):
    """Visualizes the embeddings."""
    recommender = Recommender(embeddings_dir)
    if recommender.embeddings is None:
        click.echo("No embeddings found.")
        return
        
    projector = Projector(method=method)
    projections = projector.fit_transform(recommender.embeddings)
    
    if output_file.endswith('.html'):
        plot_embeddings_interactive(projections, recommender.metadata, output_path=output_file)
    else:
        plot_embeddings_static(projections, recommender.metadata, output_path=output_file)

from src.apple_api.manager import AppleMusicManager

@cli.command()
@click.option('--query', required=True, help='Search query (e.g. artist or song name)')
@click.option('--limit', default=10, help='Number of songs to download')
@click.option('--output_dir', default='data/audio', help='Directory to save audio files')
def download(query, limit, output_dir):
    """Downloads song previews from Apple Music."""
    manager = AppleMusicManager()
    files = manager.download_tracks(query, limit, output_dir)
    click.echo(f"Downloaded {len(files)} files to {output_dir}")

if __name__ == '__main__':
    cli()

