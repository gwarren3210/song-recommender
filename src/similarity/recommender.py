import os
import numpy as np
import json
import pandas as pd
from .cosine import compute_similarity_matrix, get_top_k_similar

class Recommender:
    def __init__(self, embeddings_dir):
        self.embeddings_dir = embeddings_dir
        self.embeddings = None
        self.metadata = []
        self.similarity_matrix = None
        self.load_data()

    def load_data(self):
        metadata_path = os.path.join(self.embeddings_dir, 'metadata.json')
        if not os.path.exists(metadata_path):
            print("No metadata found. Please run embedding first.")
            return

        with open(metadata_path, 'r') as f:
            self.metadata = json.load(f)
            
        embedding_list = []
        valid_metadata = []
        
        for meta in self.metadata:
            emb_path = meta.get('embedding_path')
            if emb_path and os.path.exists(emb_path):
                emb = np.load(emb_path)
                embedding_list.append(emb)
                valid_metadata.append(meta)
        
        if embedding_list:
            self.embeddings = np.vstack(embedding_list)
            self.metadata = valid_metadata
            print(f"Loaded {len(self.embeddings)} embeddings.")
            
            self.similarity_matrix = compute_similarity_matrix(self.embeddings)
        else:
            print("No valid embeddings found.")

    def recommend(self, song_name=None, song_path=None, song_index=None, k=5):
        if self.similarity_matrix is None:
            print("Similarity matrix not computed.")
            return []

        if song_index is None:
            if song_path:
                # Try to find by exact path match
                for i, meta in enumerate(self.metadata):
                    # Check if path ends with the provided song_path (to handle relative vs absolute)
                    if meta.get('path', '').endswith(song_path) or song_path.endswith(meta.get('path', '')):
                        song_index = i
                        break
            
            if song_index is None and song_name:
                for i, meta in enumerate(self.metadata):
                    if song_name.lower() in meta.get('filename', '').lower():
                        song_index = i
                        break
        
        if song_index is None:
            print(f"Song '{song_name or song_path}' not found.")
            return []

        indices, scores = get_top_k_similar(self.similarity_matrix, song_index, k)
                    
        recommendations = []
        for idx, score in zip(indices, scores):
            rec = self.metadata[idx].copy()
            rec['similarity_score'] = float(score)
            recommendations.append(rec)
            
        return recommendations
    
    def get_similarity_matrix(self):
        return self.similarity_matrix
