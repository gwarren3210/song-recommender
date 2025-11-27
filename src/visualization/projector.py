import numpy as np
import umap
from sklearn.manifold import TSNE

class Projector:
    def __init__(self, method='umap', n_components=2, random_state=42):
        self.method = method
        self.n_components = n_components
        self.random_state = random_state
        self.reducer = None

    def fit_transform(self, embeddings):
        """
        Reduces the dimensionality of embeddings.
        
        Args:
            embeddings (np.ndarray): Array of shape (N, D).
            
        Returns:
            projections (np.ndarray): Array of shape (N, n_components).
        """
        if len(embeddings) < 5 and self.method == 'umap':
            print("Warning: Too few samples for UMAP. Switching to t-SNE or just returning first 2 dims if very small.")
            # Fallback logic could be added here
            
        if self.method == 'umap':
            self.reducer = umap.UMAP(
                n_components=self.n_components, 
                random_state=self.random_state,
                n_neighbors=min(15, len(embeddings) - 1) if len(embeddings) > 1 else 1
            )
        elif self.method == 'tsne':
            self.reducer = TSNE(
                n_components=self.n_components, 
                random_state=self.random_state,
                perplexity=min(30, len(embeddings) - 1) if len(embeddings) > 1 else 1
            )
        else:
            raise ValueError(f"Unknown method: {self.method}")
            
        return self.reducer.fit_transform(embeddings)
