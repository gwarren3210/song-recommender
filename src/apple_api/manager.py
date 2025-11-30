import os
from src.apple_api.client import AppleMusicClient
from src.apple_api.downloader import batch_download

class AppleMusicManager:
    """Manager for Apple Music operations."""
    
    def __init__(self):
        """Initialize Apple Music manager."""
        self.client = AppleMusicClient()

    def download_tracks(self, query, limit=10, output_dir="data/audio"):
        """
        Search and download track previews.
        
        Args:
            query: Search query
            limit: Number of tracks to download
            output_dir: Directory to save audio files
            
        Returns:
            list: List of paths to downloaded files
        """
        print(f"Searching for '{query}'...")
        tracks = self.client.search(query, limit=limit)
        
        if not tracks:
            print("No tracks found.")
            return []
            
        print(f"Found {len(tracks)} tracks. Starting download...")
        downloaded_files = batch_download(tracks, output_dir)
        
        return downloaded_files
