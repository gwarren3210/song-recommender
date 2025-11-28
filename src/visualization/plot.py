import matplotlib.pyplot as plt
import plotly.express as px
import pandas as pd
import os

def plot_embeddings_static(projections, metadata, output_path=None):
    """
    Creates a static scatter plot using matplotlib.
    """
    plt.figure(figsize=(10, 8))
    x = projections[:, 0]
    y = projections[:, 1]
    
    plt.scatter(x, y, alpha=0.7)
    plt.title("Song Embeddings Projection")
    plt.xlabel("Dim 1")
    plt.ylabel("Dim 2")
    
    if output_path:
        plt.savefig(output_path)
        print(f"Saved static plot to {output_path}")
    else:
        plt.show()
    plt.close()

def plot_embeddings_interactive(projections, metadata, output_path=None):
    """
    Creates an interactive scatter plot using plotly.
    """
    df = pd.DataFrame(projections, columns=['x', 'y'])
    
    filenames = [m.get('filename', 'Unknown') for m in metadata]
    df['filename'] = filenames
    
    durations = [f"{m.get('duration', 0):.2f}s" for m in metadata]
    df['duration'] = durations
    
    fig = px.scatter(
        df, 
        x='x', 
        y='y', 
        hover_data=['filename', 'duration'],
        title='Song Embeddings Projection'
    )
    
    if output_path:
        fig.write_html(output_path)
        print(f"Saved interactive plot to {output_path}")
    else:
        fig.show()
