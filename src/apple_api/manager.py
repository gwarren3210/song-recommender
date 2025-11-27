import os
from .client import AppleMusicClient
from .downloader import batch_download

class AppleMusicManager:
    def __init__(self):
        self.client = AppleMusicClient()

    def download_tracks(self, query, limit=10, output_dir="data/audio"):
        """
        Args:
            query (str): Search query.
            limit (int): Number of tracks to download.
            output_dir (str): Directory to save audio files.
            
        Returns:
            downloaded_files (list): List of paths to downloaded files.
        """
        print(f"Searching for '{query}'...")
        tracks = self.client.search(query, limit=limit)
        
        if not tracks:
            print("No tracks found.")
            return []
            
        print(f"Found {len(tracks)} tracks. Starting download...")
        downloaded_files = batch_download(tracks, output_dir)
        
        return downloaded_files
