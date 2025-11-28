import librosa
import torch
import numpy as np
import warnings
warnings.filterwarnings("ignore", category=UserWarning, message=".*PySoundFile.*")
warnings.filterwarnings("ignore", category=FutureWarning, message=".*audioread.*")

def load_audio(file_path, target_sr=48000, duration=None):
    """
    Loads an audio file and resamples it to the target sampling rate.
    
    Args:
        file_path (str): Path to the audio file.
        target_sr (int): Target sampling rate (default 48000 for CLAP).
        duration (float): Max duration to load in seconds.
        
    Returns:
        audio (np.ndarray): The loaded audio waveform.
        sr (int): The sampling rate.
    """
    try:
        # mono=True mixes to mono, which is standard for many embeddings
        return librosa.load(file_path, sr=target_sr, mono=True, duration=duration)
    except Exception as e:
        print(f"Error loading audio file {file_path}: {e}")
        return None, None

def preprocess_audio(audio, processor):
    """
    Args:
        audio (np.ndarray): The audio waveform.
        processor (ClapProcessor): The CLAP processor.
        
    Returns:
        inputs (dict): Processed inputs ready for the model.
    """
    # CLAP processor expects a list of audio arrays or a single array
    # sampling_rate should match what the processor expects (usually 48000)
    inputs = processor(audio=audio, sampling_rate=48000, return_tensors="pt")
    return inputs

def extract_metadata(file_path):
    """   
    Args:
        file_path (str): Path to the audio file.
        
    Returns:
        metadata (dict): Dictionary containing metadata (duration, sr, etc).
    """
    try:
        return {
            "duration": librosa.get_duration(path=file_path), 
            "path": file_path,
        }
    except Exception as e:
        print(f"Error extracting metadata from {file_path}: {e}")
        return {"path": file_path, "error": str(e)}
