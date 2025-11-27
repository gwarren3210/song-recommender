import os
import torch
import numpy as np
import json
from tqdm import tqdm
from .model_loader import load_model
from .preprocessing import load_audio, preprocess_audio, extract_metadata

class AudioEmbedder:
    def __init__(self, model_name="laion/clap-htsat-unfused"):
        self.model, self.processor = load_model(model_name)
        self.device = self.model.device

    def embed_file(self, file_path):
        """
        Generates an embedding for a single audio file.
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

    def embed_library(self, input_dir, output_dir):
        """
        Embeds all audio files in a directory and saves them to output_dir.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        audio_extensions = ('.mp3', '.wav', '.flac', '.m4a')
        files = [f for f in os.listdir(input_dir) if f.lower().endswith(audio_extensions)]
        
        metadata_list = []
        
        print(f"Found {len(files)} audio files in {input_dir}")
        
        for file in tqdm(files, desc="Embedding songs"):
            file_path = os.path.join(input_dir, file)
            file_base = os.path.splitext(file)[0]
            npy_path = os.path.join(output_dir, f"{file_base}.npy")
            
            if os.path.exists(npy_path):
                meta = extract_metadata(file_path)
                meta['embedding_path'] = npy_path
                meta['filename'] = file
                metadata_list.append(meta)
                continue
            
            embedding = self.embed_file(file_path)
            if embedding is not None:
                np.save(npy_path, embedding)
                
                meta = extract_metadata(file_path)
                meta['embedding_path'] = npy_path
                meta['filename'] = file
                metadata_list.append(meta)
        
        with open(os.path.join(output_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata_list, f, indent=2)
            
        print(f"Finished embedding. Metadata saved to {os.path.join(output_dir, 'metadata.json')}")
