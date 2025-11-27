import requests
import urllib.parse

class AppleMusicClient:
    BASE_URL = "https://itunes.apple.com/search"

    def __init__(self):
        pass

    def search(self, term, limit=20, entity="song", media="music"):
        """
        Searches for tracks on Apple Music/iTunes.
        
        Args:
            term (str): The search query (e.g., "Taylor Swift").
            limit (int): Max number of results.
            entity (str): The entity type to search for.
            media (str): The media type.
            
        Returns:
            results (list): List of track dictionaries.
        """
        params = {
            "term": term,
            "limit": limit,
            "entity": entity,
            "media": media
        }
        
        try:
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            print(f"Error searching Apple Music: {e}")
            return []
