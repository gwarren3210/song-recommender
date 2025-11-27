import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def compute_similarity_matrix(embeddings):
    """
    Args:
        embeddings (np.ndarray): Array of shape (N, D) containing embeddings.
        
    Returns:
        similarity_matrix (np.ndarray): Array of shape (N, N) with similarity scores.
    """
    return cosine_similarity(embeddings)

def get_top_k_similar(similarity_matrix, index, k=5):
    """
    Args:
        similarity_matrix (np.ndarray): The similarity matrix.
        index (int): The index of the query item.
        k (int): Number of similar items to return.
        
    Returns:
        indices (np.ndarray): Indices of the top-k similar items (excluding self).
        scores (np.ndarray): Similarity scores of the top-k items.
    """
    sim_scores = similarity_matrix[index]
    sorted_indices = np.argsort(sim_scores)[::-1]
    
    top_indices = [i for i in sorted_indices if i != index][:k]
    top_scores = sim_scores[top_indices]
    
    return top_indices, top_scores
