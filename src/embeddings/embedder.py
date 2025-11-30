import os
import torch
import numpy as np
import json
import uuid
from tqdm import tqdm
from typing import Optional
from src.embeddings.model_loader import load_model
from src.embeddings.preprocessing import (
    load_audio,
    preprocess_audio,
    extract_metadata
)
from src.storage.backend import StorageBackend

class AudioEmbedder:
    def __init__(self, storage_backend: StorageBackend, model_name="laion/clap-htsat-unfused"):
        """
        Initialize AudioEmbedder.
        
        Args:
            storage_backend: Storage backend (required)
            model_name: CLAP model name
        """
        self.model, self.processor = load_model(model_name)
        self.device = self.model.device
        self.storage_backend = storage_backend

    def embed_file(self, file_path):
        """
        Generates an embedding for a single audio file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            numpy.ndarray: Normalized embedding vector, or None on error
        """
        audio, _ = load_audio(file_path)
        if audio is None:
            return None
        
        try:
            inputs = preprocess_audio(audio, self.processor)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model.get_audio_features(**inputs)
            
            embedding = outputs[0].cpu().numpy()
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
                
            return embedding
        except Exception as e:
            print(f"Error embedding file {file_path}: {e}")
            return None

    def embed_library(self, input_dir):
        """
        Embeds all audio files in a directory and stores in the database.
        
        Args:
            input_dir: Directory containing audio files
        """
        audio_extensions = ('.mp3', '.wav', '.flac', '.m4a')
        files = [
            f for f in os.listdir(input_dir)
            if f.lower().endswith(audio_extensions)
        ]
        
        metadata_list = []
        
        print(f"Found {len(files)} audio files in {input_dir}")
        
        for file in tqdm(files, desc="Embedding songs"):
            file_path = os.path.join(input_dir, file)
            
            # Generate embedding
            embedding = self.embed_file(file_path)
            if embedding is not None:
                # Upload to storage backend
                song_id = self.storage_backend.upload_audio(file_path)
                
                # Store embedding
                self.storage_backend.store_embedding(
                    song_id,
                    embedding,
                    model_name="laion/clap-htsat-unfused"
                )
                
                # Store metadata
                meta = extract_metadata(file_path)
                meta['filename'] = file
                meta['path'] = file_path
                self.storage_backend.store_metadata(song_id, meta)
                
                metadata_list.append({**meta, 'song_id': song_id})
        
        print(
            f"Finished embedding. {len(metadata_list)} songs "
            "processed and stored in the database."
        )
