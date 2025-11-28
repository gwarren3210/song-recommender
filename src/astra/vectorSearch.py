"""Vector similarity search utilities for Astra DB using Data API."""

import numpy as np
from typing import List, Dict, Optional
from src.astra.client import AstraClient


class VectorSearcher:
    """
    Handles vector similarity search operations using Data API.
    """
    
    def __init__(self, client: AstraClient):
        """
        Initialize vector searcher.
        
        Args:
            client: AstraClient instance
        """
        self.client = client
        self.database = client.get_database()
        keyspace = client.keyspace
        self.embeddings_table = self.database.get_table("embeddings", keyspace=keyspace)
    
    def search_similar(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        threshold: Optional[float] = None
    ) -> List[Dict]:
        """
        Search for similar embeddings using vector similarity search.
        
        Args:
            query_embedding: Query embedding vector (numpy array)
            k: Number of results to return
            threshold: Minimum similarity threshold (optional)
            
        Returns:
            List of dictionaries with song_id, embedding_id, and similarity score
        """
        # Convert numpy array to list for Data API
        embedding_list = query_embedding.tolist()
        
        try:
            # Use Data API vector search
            # TODO: POTENTIALLY INCORRECT - Verify this is the correct syntax for Astra vector search
            # The sort parameter may not perform true vector similarity search using indexes
            # May need to use $vectorize or proper vector search operators instead
            # See ISSUES.md #2 for details. Fallback loads ALL embeddings which is very inefficient.
            results = self.embeddings_table.find(
                {},
                sort={"embedding": embedding_list},  # Sort by embedding column
                limit=k,
            )
            
            similar_items = []
            query_vec = query_embedding / np.linalg.norm(query_embedding)
            
            for row in results:
                embedding = row.get('embedding')
                if embedding:
                    # Compute cosine similarity
                    emb_vec = np.array(embedding)
                    emb_vec = emb_vec / np.linalg.norm(emb_vec)
                    similarity = float(np.dot(query_vec, emb_vec))
                else:
                    # If no embedding, skip
                    continue
                
                # Apply threshold if specified
                if threshold is None or similarity >= threshold:
                    similar_items.append({
                        'embedding_id': str(row.get('embedding_id', '')),
                        'song_id': str(row.get('song_id', '')),
                        'similarity': similarity
                    })
            
            # Sort by similarity (descending) and return top k
            similar_items.sort(key=lambda x: x['similarity'], reverse=True)
            return similar_items[:k]
            
        except Exception as e:
            print(f"Error in vector search: {e}")
            # Fallback: try alternative syntax
            return self._fallback_search(query_embedding, k, threshold)
    
    def _fallback_search(
        self,
        query_embedding: np.ndarray,
        k: int,
        threshold: Optional[float]
    ) -> List[Dict]:
        """
        Fallback search method if primary vector search fails.
        
        WARNING: This loads ALL embeddings and computes similarity locally.
        This is extremely inefficient for large libraries and should be avoided.
        See ISSUES.md #6 for details.
        """
        print("Using fallback search (loading all embeddings)...")
        
        # Get all embeddings
        results = self.embeddings_table.find({})
        
        similarities = []
        query_vec = query_embedding / np.linalg.norm(query_embedding)
        
        for row in results:
            embedding = row.get('embedding')
            if embedding is None:
                continue
            
            # Convert embedding to numpy array
            if isinstance(embedding, list):
                emb_vec = np.array(embedding)
            else:
                continue
            
            # Normalize and compute cosine similarity
            emb_vec = emb_vec / np.linalg.norm(emb_vec)
            similarity = float(np.dot(query_vec, emb_vec))
            
            if threshold is None or similarity >= threshold:
                similarities.append({
                    'embedding_id': str(row.get('embedding_id', '')),
                    'song_id': str(row.get('song_id', '')),
                    'similarity': similarity
                })
        
        # Sort and return top k
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities[:k]
